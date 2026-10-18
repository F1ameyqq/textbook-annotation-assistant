"""No business imports: an active SQLite transaction ends via events and join."""
import os
from pathlib import Path
import sqlite3
import sys
import threading
import time
from capture import Boundary, capture_databases, sha, write


def run(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = root / 'fixture.sqlite3'
    db = sqlite3.connect(str(source))
    db.execute('CREATE TABLE fixture(value INTEGER)')
    db.commit()
    db.close()
    active, finish, closed = threading.Event(), threading.Event(), threading.Event()
    events, errors = [], []

    def writer():
        conn = sqlite3.connect(str(source))
        try:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('INSERT INTO fixture VALUES(7)')
            events.append({'event': 'transaction-open', 'at_ns': time.time_ns()})
            active.set()
            assert finish.wait(5), 'fixture writer boundary timeout'
            conn.commit()
            events.append({'event': 'committed', 'at_ns': time.time_ns(), 'in_transaction': conn.in_transaction})
        except BaseException as error:
            errors.append(repr(error))
        finally:
            conn.close()
            events.append({'event': 'connection-closed', 'at_ns': time.time_ns()})
            closed.set()

    thread = threading.Thread(target=writer, name='fixture-owned-writer', daemon=False)
    thread.start()

    def stop_join():
        events.append({'event': 'finish-requested', 'at_ns': time.time_ns()})
        finish.set()
        thread.join(5)
        assert closed.is_set() and not thread.is_alive() and not errors

    boundary = Boundary(stop_join=stop_join,
        status=lambda: {'writer_alive': thread.is_alive(), 'connection_closed': closed.is_set(),
                        'owned_async_writers': int(thread.is_alive())})
    try:
        assert active.wait(5), 'fixture transaction-open barrier timeout'
        journal = Path(str(source) + '-journal')
        assert journal.exists(), 'expected active rollback journal'
        write(root / 'active-transaction-barrier.json', {'pid': os.getpid(), 'thread_alive': thread.is_alive(),
            'journal_size': journal.stat().st_size, 'journal_sha256_at_barrier': sha(journal.read_bytes()),
            'claim': 'active sidecar observation only; not a quiescent database snapshot'})
        values = capture_databases(root / 'captured', {'fixture': source}, boundary=boundary)
        assert values['fixture']['tables']['fixture'] == [{'value': 7}]
        assert source.read_bytes() == (root / 'captured/fixture.sqlite3').read_bytes()
        write(root / 'result.json', {'author_assertions': 'PASS', 'business_calls': 0, 'thread_joined': True,
            'connection_closed': True, 'errors': errors, 'events': events,
            'synchronization': 'transaction-open Event -> finish Event -> commit/close -> join -> raw copy -> immutable copy SQL',
            'sleep_calls': 0, 'sidecar_deletions': 0, 'raw_byte_copy': True})
    finally:
        finish.set()
        thread.join(5)
        assert not thread.is_alive()


if __name__ == '__main__':
    run(Path(sys.argv[1]))
