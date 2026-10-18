"""Cooperative writer shutdown and sequential, byte-exact SQLite evidence.

No SQL is executed against an original database. Call only between synchronous
business calls, in an isolated case with all writers accounted for by boundary.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading
import time


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False,
        sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)


def threads():
    return [{'name': t.name, 'ident': t.ident, 'alive': t.is_alive()}
            for t in threading.enumerate()]


class Boundary:
    """A stop/join callback must return after transactions AND connections close.

    resume runs only after all raw copies and immutable-copy audits finish.
    No retry, sleep, checkpoint, sidecar deletion, or database backup is used.
    """
    def __init__(self, stop_join=None, resume=None, status=None):
        self.stop_join = stop_join
        self.resume = resume
        self.status = status or (lambda: {'owned_async_writers': 0})
        self.events = []
        self.control_thread = threading.get_ident()

    @contextmanager
    def quiet(self):
        assert threading.get_ident() == self.control_thread
        record = {'requested_at_ns': time.time_ns(), 'before': self.status(),
                  'business_call_in_flight': False, 'threads_before': threads()}
        self.events.append(record)
        try:
            if self.stop_join:
                self.stop_join()
            record.update(joined_at_ns=time.time_ns(), quiescent=self.status(), threads_quiet=threads())
            assert all(t is threading.current_thread() for t in threading.enumerate()), 'unaccounted live thread'
            yield record
        finally:
            record['copy_boundary_ended_at_ns'] = time.time_ns()
            if self.resume:
                self.resume()
            record.update(after=self.status(), resumed_at_ns=time.time_ns())


class LeaseBoundary(Boundary):
    """Own the existing LeaseKeeper; replace its thread after joined captures.

    Owner/generation and the product's 2s renewal/10s lease remain unchanged.
    stop() must be used for final release; the original keeper becomes obsolete.
    """
    def __init__(self, keeper):
        self.keeper = keeper
        self.keepers = [keeper]
        super().__init__(self.stop, self.start, self.snapshot)

    def snapshot(self):
        return {'owned_async_writers': int(self.keeper.thread.is_alive()),
                'keeper_alive': self.keeper.thread.is_alive(),
                'owner_id': self.keeper.owner_id, 'generation': self.keeper.generation,
                'keepers_created': len(self.keepers),
                'all_keeper_threads': [{'ident': k.thread.ident, 'alive': k.thread.is_alive(),
                    'error': None if k.error is None else repr(k.error)} for k in self.keepers]}

    def stop(self):
        self.keeper.stop()
        assert not self.keeper.thread.is_alive()
        self.keeper.check()

    def start(self):
        from annotation.runtime.recovery.lease import LeaseKeeper
        old = self.keeper
        assert not old.thread.is_alive()
        self.keeper = LeaseKeeper(old.store, old.target_key, old.owner_id, old.generation).start()
        self.keepers.append(self.keeper)


def sql_copy(path):
    """Only the retained quiescent raw COPY is opened with immutable=1."""
    before = sha(path.read_bytes())
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    db.row_factory = sqlite3.Row
    try:
        assert db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
        names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        result = {'application_id': db.execute('PRAGMA application_id').fetchone()[0],
                  'user_version': db.execute('PRAGMA user_version').fetchone()[0],
                  'tables': {name: [dict(r) for r in db.execute('SELECT * FROM "' +
                      name.replace('"', '""') + '" ORDER BY rowid')] for name in names}}
    finally:
        db.close()
    assert sha(path.read_bytes()) == before
    return result


def capture_databases(folder, sources, *, boundary=None):
    """Return SQL values and retain originals, SQL, lifecycle, and first errors.

    sources maps labels to original paths. Copies are sequential, not a cross-DB
    atomic snapshot. An unexpected sidecar fails *after* writer synchronization.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    boundary = boundary or Boundary()
    values = {}
    evidence = {'pid': os.getpid(), 'cross_database_atomic': False,
                'SQL_reads_only_retained_immutable_copies': True, 'records': []}
    try:
        with boundary.quiet() as lifecycle:
            evidence['writer_boundary'] = lifecycle
            for label, source in sources.items():
                source = Path(source).resolve()
                record = {'kind': label, 'source': str(source), 'captured_at_ns': time.time_ns()}
                evidence['records'].append(record)
                sidecars = {s: {'size': Path(str(source) + s).stat().st_size,
                               'sha256': sha(Path(str(source) + s).read_bytes())}
                            for s in ('-journal', '-wal', '-shm') if Path(str(source) + s).exists()}
                record['sidecars_after_writer_join'] = sidecars
                assert not sidecars, 'unexpected sidecar after writer join: ' + str(source)
                raw = source.read_bytes()
                destination = folder / (label + '.sqlite3')
                write(destination, raw)
                record.update(size=len(raw), sha256=sha(raw), retained=str(destination.resolve()),
                    source_sha256_after_copy=sha(source.read_bytes()))
                assert record['sha256'] == record['source_sha256_after_copy']
                values[label] = sql_copy(destination)
                record['source_sha256_after_copy_audit'] = sha(source.read_bytes())
                assert record['sha256'] == record['source_sha256_after_copy_audit']
                assert not any(Path(str(source) + s).exists() for s in ('-journal', '-wal', '-shm'))
        write(folder / 'SQL.json', values)
        evidence['status'] = 'RAW_COPIES_RETAINED'
        return values
    except BaseException as error:
        evidence.update(status='CAPTURE_FAILED', error=repr(error))
        raise
    finally:
        evidence['boundary_events'] = boundary.events
        write(folder / 'capture.json', evidence)


def capture(case, stage, *, boundary=None):
    return capture_databases(Path(case) / 'captures' / stage,
        {'runtime': Path(case) / 'runtime/runtime.sqlite3',
         'target': Path(case) / 'target/target.sqlite3'}, boundary=boundary)
