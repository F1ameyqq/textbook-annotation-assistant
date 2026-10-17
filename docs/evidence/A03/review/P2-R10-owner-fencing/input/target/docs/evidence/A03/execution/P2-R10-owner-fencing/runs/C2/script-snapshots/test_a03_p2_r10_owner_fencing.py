"""Two fresh bounded process cases; product authority is never fabricated."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import traceback

import test_a03_r8_r3_post_hold as helper

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
OUT = ROOT / 'docs/evidence/A03/execution/P2-R10-owner-fencing'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


def tick():
    return time.time_ns()


def imports():
    return {'pid': os.getpid(), 'executable': sys.executable, 'modules': {
        name: {'path': str(Path(module.__file__).resolve()), 'sha256': sha(Path(module.__file__).read_bytes())}
        for name, module in list(sys.modules.items()) if getattr(module, '__file__', None)
        and Path(module.__file__).is_file() and (name.startswith('annotation') or name in ('__main__', 'test_a03_r8_r3_post_hold'))}}


def wait_file(path, *, abort=None, seconds=5):
    deadline = time.monotonic() + seconds
    while not path.is_file():
        if abort and abort.is_file():
            raise RuntimeError('parent aborted this owned worker')
        if time.monotonic() >= deadline:
            raise TimeoutError('bounded driver barrier: ' + str(path))
        time.sleep(.01)


def read_db(path, immutable=False):
    if not path.is_file():
        return {'status': 'NOT_CREATED'}
    before = path.read_bytes()
    uri = path.as_uri() + ('?mode=ro&immutable=1' if immutable else '?mode=ro')
    with sqlite3.connect(uri, uri=True, timeout=1) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        rows = {name: [dict(r) for r in db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')] for name in names}
        quick = db.execute('PRAGMA quick_check').fetchone()[0]
    after = path.read_bytes()
    if immutable:
        assert before == after
    return {'path': path.relative_to(ROOT).as_posix(), 'raw_sha256_before': sha(before), 'raw_sha256_after': sha(after),
        'bytes': len(after), 'quick_check': quick, 'immutable': immutable,
        'counts': {k: len(v) for k, v in rows.items()}, 'tables': rows}


def state(case, immutable=False):
    runtime = read_db(case / 'runtime/runtime.sqlite3', immutable)
    target = read_db(case / 'target/target.sqlite3', immutable)
    result = {'recorded_at_ns': tick(), 'runtime': runtime, 'target': target,
        'snapshot_limit': 'Each SQLite read transaction is consistent; two databases and raw-byte reads are sequential, not an atomic cross-database snapshot.'}
    if 'tables' in runtime and runtime['tables']['books']:
        result['book'] = runtime['tables']['books'][0]
    if 'tables' in target:
        meta = {r['key']: r['value'] for r in target['tables'].get('meta', [])}
        target_state = json.loads(meta['state']) if 'state' in meta else {}
        result['target_fence'] = {k: target_state.get(k) for k in ('fence_owner_id', 'fence_generation')}
    return result


def bootstrap_claim_case(case):
    from annotation.contracts import artifact_ref, validate_bundle
    from annotation.runtime.storage.native import init_native_state
    from annotation.quality.targetcheck import SimulationConfig
    from annotation.delivery.mock.persistent import PersistentMockSession
    case.mkdir(parents=True, exist_ok=False)
    shutil.copytree(helper.FIXTURE, case / 'input')
    raw = json.loads((case / 'input/initial.json').read_bytes())
    store = init_native_state(case / 'anchor.json', case / 'runtime', expected_ledger_id='ledger-r10-C1', expected_target_store_id='store-r10-C1')
    context = store.bridge_for(raw, case / 'input')
    bundle = validate_bundle(raw, asset_root=case / 'input', bridge_context=context)
    source, evidence, graph, snapshot = bundle.artifacts
    key = {'platform_namespace': 'a03-r10', 'target_id': snapshot.payload.target_id, 'book_id': source.book_id}
    config = SimulationConfig(source.book_id, snapshot.payload.target_id, source.scope_id, {'directory-r8-r3': 'platform-r8-r3'})
    reg = store.register_book(bundle, target_key=key, target_dir=case / 'target', target_session_id='session-r10-C1',
        source_ref=artifact_ref(source), asset_root=case / 'input', config=vars(config), registration_id='registration-r10-C1')
    root = Path(reg.package_root)
    context = store.bridge_for(store.bundle(reg.registration_id), root)
    PersistentMockSession.create(case / 'target', bundle, artifact_ref(snapshot), platform_namespace='a03-r10',
        source_ref=artifact_ref(source), asset_root=root, expected_store_id=store.target_store_id,
        target_session_id='session-r10-C1', bridge_context=context)
    write(case / 'bootstrap.json', {'state': state(case, True), 'imports': imports(), 'claim_calls': 0})


def open_case(case):
    if case.name == 'C1':
        from annotation.runtime.storage.native import open_native_state
        return open_native_state(case / 'anchor.json', expected_ledger_id='ledger-r10-C1', expected_target_store_id='store-r10-C1')
    return helper.open_case(case)


def qualify_old_owner(case):
    from annotation.contracts import artifact_ref, policy_ref
    from annotation.quality.targetcheck import check_target
    from annotation.delivery.planner import create_plan
    from annotation.runtime.storage.common import now
    store, observer, claim, keeper, bundle, pre_ref, actual, admitted, config = helper.setup_pre(case)
    try:
        reg = store.registration()
        graph = next(a for a in bundle.artifacts if a.kind == 'QuestionGraph')
        bundle = check_target(bundle, artifact_ref(graph), actual.snapshot_ref, actual.snapshot_ref, policy_ref(bundle.policies[0]),
            config, artifact_id='target-r10-C2', created_at=now(), bridge_context=bundle.bridge_context)
        target = artifact_ref(bundle.artifacts[-1])
        bundle = create_plan(bundle, artifact_ref(graph), pre_ref, target, actual.snapshot_ref, actual.snapshot_ref,
            policy_ref(bundle.policies[0]), config, artifact_id='plan-r10-C2', created_at=now(), bridge_context=bundle.bridge_context)
        plan = bundle.artifacts[-1]
        assert len(plan.payload.actions) == 1 and plan.payload.actions[0].operation == 'CREATE_FRAMES'
        store.record_native_plan(reg['id'], bundle, artifact_ref(plan), config, owner_id=claim.owner_id, generation=claim.generation)
        qualified = state(case)
        assert all(qualified['runtime']['counts'][name] == 0 for name in ('plans', 'intents', 'permits'))
        assert qualified['target']['counts']['effects'] == 0
        return store, claim, keeper, config, {'plan_ref': artifact_ref(plan), 'pre_ref': pre_ref,
            'native_pre_run_id': admitted.run_id, 'snapshot_ref': actual.snapshot_ref, 'state': qualified, 'imports': imports()}
    except BaseException:
        keeper.stop()
        raise


def c1_worker(case, control, role):
    from annotation.runtime.recovery import open_observer
    from annotation.runtime.recovery.lease import LeaseKeeper
    from annotation.runtime.storage.common import FaultController, plain
    store = open_case(case)
    reg = store.registration()
    observer = open_observer(store, reg['id'])
    key = store.target_key(reg['id'])
    write(control / (role + '-ready.json'), {'pid': os.getpid(), 'instance': store.instance, 'owner_id': store.owner_id, 'at_ns': tick(), 'imports': imports()})
    store.fault = FaultController({'point': 'BEFORE_CLAIM', 'mode': 'barrier',
        'marker': str(control / (role + '-BEFORE_CLAIM.json')), 'release': str(control / 'claim-go.barrier')})
    claim = keeper = None
    try:
        try:
            claim = store.claim(key, observer=observer)
        except Exception as error:
            write(control / (role + '-claim-result.json'), {'outcome': 'REFUSED', 'pid': os.getpid(), 'instance': store.instance,
                'code': getattr(error, 'code', None), 'type': type(error).__name__, 'message': str(error),
                'traceback': traceback.format_exc(), 'at_ns': tick()})
        else:
            keeper = LeaseKeeper(store, key, claim.owner_id, claim.generation).start()
            write(control / (role + '-claim-result.json'), {'outcome': 'ACTIVE', 'pid': os.getpid(), 'instance': store.instance,
                'claim': plain(claim), 'state': state(case), 'at_ns': tick()})
        wait_file(control / (role + '-finish.barrier'), abort=control / 'abort.barrier')
    finally:
        if keeper is not None:
            keeper.stop()
            store.release(key, owner_id=claim.owner_id, generation=claim.generation)
            write(control / (role + '-released.json'), {'pid': os.getpid(), 'claim': plain(claim), 'state': state(case), 'at_ns': tick()})


def c2_worker(case, control, role):
    from annotation.runtime.recovery import open_observer, run_plan
    from annotation.runtime.recovery.lease import LeaseKeeper
    from annotation.runtime.storage.common import plain
    if role == 'A':
        store, claim, keeper, config, qualified = qualify_old_owner(case)
        released = False
        try:
            write(control / 'A-qualified.json', {'pid': os.getpid(), 'instance': store.instance, 'claim': plain(claim), 'at_ns': tick(), **qualified})
            wait_file(control / 'A-release.barrier', abort=control / 'abort.barrier')
            keeper.stop()
            store.release(store.target_key(store.registration()['id']), owner_id=claim.owner_id, generation=claim.generation)
            released = True
            write(control / 'A-released.json', {'pid': os.getpid(), 'old_claim': plain(claim), 'state': state(case), 'at_ns': tick()})
            wait_file(control / 'A-stale-attempt.barrier', abort=control / 'abort.barrier')
            before = state(case)
            assert before['book']['generation'] > claim.generation and before['book']['phase'] == 'ACTIVE'
            try:
                run_plan(store, store.registration()['id'], owner_id=claim.owner_id, generation=claim.generation, config=vars(config))
            except Exception as error:
                frames = traceback.extract_tb(error.__traceback__)
                refusal = {'code': getattr(error, 'code', None), 'type': type(error).__name__, 'message': str(error),
                    'traceback': traceback.format_exc(), 'root_lease_guard_reached': any(f.name == '_lease' for f in frames)}
                assert refusal['root_lease_guard_reached'], 'stale call failed before reaching the lease guard'
            else:
                raise AssertionError('live stale owner reached run_plan without refusal')
            after = state(case)
            for name in ('plans', 'intents', 'permits'):
                assert before['runtime']['counts'][name] == after['runtime']['counts'][name] == 0
            assert after['target']['counts']['effects'] == before['target']['counts']['effects'] == 0
            assert all(before['book'][k] == after['book'][k] for k in ('owner', 'generation', 'phase', 'pid', 'process_id'))
            assert after['target_fence'] == before['target_fence']
            write(control / 'A-stale-result.json', {'pid': os.getpid(), 'old_claim': plain(claim), 'refusal': refusal,
                'before': before, 'after': after, 'at_ns': tick(), 'old_owner_renew_or_release_after_handover': 0})
            wait_file(control / 'A-finish.barrier', abort=control / 'abort.barrier')
        finally:
            keeper.stop()
            if not released:
                store.release(store.target_key(store.registration()['id']), owner_id=claim.owner_id, generation=claim.generation)
    else:
        wait_file(control / 'A-released.json', abort=control / 'abort.barrier')
        store = open_case(case)
        reg = store.registration()
        observer = open_observer(store, reg['id'])
        claim = store.claim(store.target_key(reg['id']), observer=observer)
        keeper = LeaseKeeper(store, store.target_key(reg['id']), claim.owner_id, claim.generation).start()
        try:
            write(control / 'B-active.json', {'pid': os.getpid(), 'instance': store.instance, 'claim': plain(claim), 'state': state(case), 'at_ns': tick(), 'imports': imports()})
            wait_file(control / 'B-finish.barrier', abort=control / 'abort.barrier')
        finally:
            keeper.stop()
            store.release(store.target_key(reg['id']), owner_id=claim.owner_id, generation=claim.generation)
            write(control / 'B-released.json', {'pid': os.getpid(), 'claim': plain(claim), 'state': state(case), 'at_ns': tick()})


class OwnedProcesses:
    def __init__(self, root, group):
        self.root, self.group, self.records = root, group, []

    def start(self, role):
        folder = self.root / 'processes' / (self.group + '-' + role)
        folder.mkdir(parents=True, exist_ok=False)
        argv = [sys.executable, '-X', 'utf8', '-B', str(SCRIPT), self.group, '--worker', role,
            '--output-root', self.root.relative_to(ROOT).as_posix()]
        write(folder / 'preregistered.json', {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 45,
            'script_sha256': sha(SCRIPT.read_bytes()), 'inputs_sha256': sha((OUT / 'inputs.json').read_bytes()),
            'helper_sha256': sha(Path(helper.__file__).read_bytes())})
        write(folder / 'script-snapshot.py', SCRIPT.read_bytes())
        stdout, stderr = (folder / 'stdout.txt').open('xb'), (folder / 'stderr.txt').open('xb')
        started = time.monotonic()
        process = subprocess.Popen(argv, cwd=ROOT, stdout=stdout, stderr=stderr)
        write(folder / 'started.json', {'pid': process.pid, 'parent_pid': os.getpid(), 'started_at_ns': tick()})
        self.records.append((role, folder, process, stdout, stderr, started))
        return process

    def finish(self):
        results = []
        for role, folder, process, stdout, stderr, start in self.records:
            timed_out = False
            try:
                code = process.wait(timeout=max(.01, 45 - (time.monotonic() - start)))
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                code = process.wait(timeout=5)
            stdout.close()
            stderr.close()
            result = {'role': role, 'pid': process.pid, 'exit_code': code, 'timed_out': timed_out,
                'alive': process.poll() is None, 'ended_at_ns': tick(), 'stdout_sha256': sha((folder / 'stdout.txt').read_bytes()),
                'stderr_sha256': sha((folder / 'stderr.txt').read_bytes())}
            write(folder / 'completed.json', result)
            results.append(result)
        return results


def parent(root, group):
    case, control = root / 'cases' / group, root / 'control' / group
    control.mkdir(parents=True, exist_ok=False)
    owned = OwnedProcesses(root, group)
    try:
        if group == 'C1':
            bootstrap_claim_case(case)
            a, b = owned.start('A'), owned.start('B')
            for name in ('A-ready.json', 'B-ready.json', 'A-BEFORE_CLAIM.json', 'B-BEFORE_CLAIM.json'):
                wait_file(control / name)
            assert a.poll() is None and b.poll() is None
            for role, process in (('A', a), ('B', b)):
                assert json.loads((control / (role + '-ready.json')).read_bytes())['pid'] == process.pid
                assert json.loads((control / (role + '-BEFORE_CLAIM.json')).read_bytes())['pid'] == process.pid
            write(control / 'before-common-release.json', {'at_ns': tick(), 'A_pid': a.pid, 'B_pid': b.pid,
                'both_alive': True, 'markers': {n: json.loads((control / n).read_bytes()) for n in ('A-BEFORE_CLAIM.json', 'B-BEFORE_CLAIM.json')}})
            write(control / 'claim-go.barrier', {'at_ns': tick(), 'participants_ready_before_release': True})
            for role in ('A', 'B'):
                wait_file(control / (role + '-claim-result.json'))
            claims = {role: json.loads((control / (role + '-claim-result.json')).read_bytes()) for role in ('A', 'B')}
            winners = [role for role in claims if claims[role]['outcome'] == 'ACTIVE']
            assert len(winners) == 1 and sum(r['outcome'] == 'REFUSED' for r in claims.values()) == 1
            loser = next(r for r in claims.values() if r['outcome'] == 'REFUSED')
            assert 'OWNER_BUSY' in loser['traceback'], 'refusal did not reach the existing busy-owner guard'
            assert a.poll() is None and b.poll() is None, 'winner or loser exited before competition observation'
            observed = state(case)
            winner = claims[winners[0]]
            assert observed['book']['owner'] == winner['claim']['owner_id'] and observed['book']['pid'] == winner['pid']
            assert observed['book']['process_id'] == winner['instance']
            assert observed['book']['phase'] == 'ACTIVE'
            assert observed['book']['lease'] > time.time()
            assert observed['target_fence'] == {'fence_owner_id': winner['claim']['owner_id'], 'fence_generation': winner['claim']['generation']}
            events = [json.loads(r['body'])['event'] for r in observed['runtime']['tables']['events']]
            assert events.count('OWNER_CLAIM_RESERVED') == events.count('OWNER_ACTIVE') == 1
            assert observed['target']['counts']['effects'] == 0
            write(control / 'simultaneous-competition.json', {'at_ns': tick(), 'both_processes_still_alive': True,
                'A_pid': a.pid, 'B_pid': b.pid, 'claims': claims, 'observed_state': observed, 'winner': winners[0]})
            for role in ('A', 'B'):
                write(control / (role + '-finish.barrier'), {'at_ns': tick(), 'competition_observation_saved': True})
        else:
            a = owned.start('A')
            wait_file(control / 'A-qualified.json', seconds=30)
            b = owned.start('B')
            write(control / 'A-release.barrier', {'at_ns': tick()})
            wait_file(control / 'A-released.json')
            wait_file(control / 'B-active.json')
            assert a.poll() is None and b.poll() is None
            qualified = json.loads((control / 'A-qualified.json').read_bytes())
            active = json.loads((control / 'B-active.json').read_bytes())
            assert active['claim']['generation'] > qualified['claim']['generation']
            assert active['state']['target_fence'] == {'fence_owner_id': active['claim']['owner_id'], 'fence_generation': active['claim']['generation']}
            write(control / 'before-stale-call.json', {'at_ns': tick(), 'A_pid': a.pid, 'B_pid': b.pid,
                'both_alive': True, 'old_claim': qualified['claim'], 'new_claim': active['claim'], 'state': state(case)})
            write(control / 'A-stale-attempt.barrier', {'at_ns': tick(), 'B_active_saved_before_old_call': True})
            wait_file(control / 'A-stale-result.json')
            assert a.poll() is None and b.poll() is None
            observed = state(case)
            assert observed['book']['owner'] == active['claim']['owner_id'] and observed['book']['generation'] == active['claim']['generation']
            assert observed['book']['phase'] == 'ACTIVE' and observed['target']['counts']['effects'] == 0
            write(control / 'after-stale-live-observation.json', {'at_ns': tick(), 'both_alive': True, 'state': observed})
            for role in ('A', 'B'):
                write(control / (role + '-finish.barrier'), {'at_ns': tick(), 'stale_call_observation_saved': True})
    except BaseException:
        write(root / (group + '-first-failure-state.json'), {'state': state(case), 'traceback': traceback.format_exc(), 'at_ns': tick()})
        write(control / 'abort.barrier', {'at_ns': tick(), 'no_further_business_calls': True})
        raise
    finally:
        results = owned.finish()
        write(root / (group + '-process-results.json'), results)
    assert all(r['exit_code'] == 0 and not r['timed_out'] for r in results), 'worker failed; retain first outputs'
    final = state(case, True)
    assert final['book']['phase'] == 'RELEASED' and final['book']['owner'] is None
    assert final['target']['counts']['effects'] == 0
    write(root / (group + '-result.json'), {'status': 'REVIEW', 'final_state': final,
        'coverage': 'claim mutual exclusion only' if group == 'C1' else 'live former owner refused after actual normal release/claim',
        'product_modifications': 0, 'field_reset_probe': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('group', choices=('C1', 'C2'))
    parser.add_argument('--worker', choices=('A', 'B'))
    parser.add_argument('--output-root', default='docs/evidence/A03/execution/P2-R10-owner-fencing/validation/r10-01')
    args = parser.parse_args()
    root = (ROOT / args.output_root).resolve()
    assert root.is_relative_to(OUT)
    if args.worker:
        try:
            (c1_worker if args.group == 'C1' else c2_worker)(root / 'cases' / args.group, root / 'control' / args.group, args.worker)
        finally:
            write(root / 'imports' / (args.group + '-' + args.worker + '.json'), imports())
    else:
        parent(root, args.group)
