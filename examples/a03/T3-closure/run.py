"""Only the adopted five M cases. Candidate/raw view and process evidence first."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import faulthandler
import threading

CASES = ('M1', 'M2-sufficient', 'M2-insufficient', 'M3-new-plan', 'M3-final-drift')
# A03-R1 engineering watchdogs. Runtime read/gate/lease/PRE deadlines are
# unchanged. Frozen with each candidate; never extended after a case starts.
CHILD_SECONDS = 180
PARENT_SECONDS = 240
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DIAGNOSTIC_RELATIVE = Path('docs/evidence/A03/T3/execution/M1-diagnostic')
VALIDATION_R1_RELATIVE = Path('docs/evidence/A03/T3/execution/M-validation-R1')


class DiagnosticTrace:
    """Call boundaries only: never inspect a target or check/renew a lease."""
    def __init__(self, case):
        self.stream = (case / 'calls.jsonl').open('xb')
        self.stacks = (case / 'stacks.txt').open('xb')
        self.keeper_state = lambda: None
        self.armed = False
        self.imports_pending = False
        self.event('worker', 'ENTER')

    def event(self, call, event, **fields):
        value = dict(call=call, event=event, time_ns=time.time_ns(), monotonic_ns=time.monotonic_ns(),
            process_time_ns=time.process_time_ns(), thread_time_ns=time.thread_time_ns(),
            pid=os.getpid(), thread_ident=threading.get_ident(), native_thread_id=threading.get_native_id(),
            keeper_memory=self.keeper_state(), **fields)
        self.stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)+'\n').encode('utf-8'))
        self.stream.flush()

    def call(self, name, operation, **fields):
        self.event(name, 'ENTER', **fields)
        try:
            result = operation()
        except BaseException as error:
            self.event(name, 'ERROR', error=repr(error), **fields)
            raise
        self.event(name, 'EXIT', **fields)
        return result

    def arm(self):
        self.event('faulthandler', 'ENTER', interval_seconds=5, repeat=True)
        faulthandler.dump_traceback_later(5, repeat=True, file=self.stacks, exit=False)
        self.armed = True
        self.event('faulthandler', 'EXIT')

    def cancel(self):
        if self.armed:
            faulthandler.cancel_dump_traceback_later()
            self.armed = False
            self.event('faulthandler', 'CANCELLED')

    def close(self):
        self.cancel()
        self.stream.close()
        self.stacks.close()


def log_snapshot(paths):
    """One read per already-flushed log; active snapshots are non-atomic."""
    rows = []
    for path in paths:
        if path.exists():
            raw = path.read_bytes()
            rows.append({'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)})
        else:
            rows.append({'path': str(path), 'missing': True})
    return {'time_ns': time.time_ns(), 'files': rows}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + '\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)


def run_child(folder, argv, *, cwd, env, timeout, diagnostic_logs=None):
    folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'preregistered.json', {'argv': argv, 'cwd': str(cwd), 'timeout': timeout,
        'driver_sha256': sha(Path(__file__).read_bytes()), 'parent_pid': os.getpid(),
        'PYTHONPATH': env.get('PYTHONPATH'), 'input_candidate': env.get('A03_M_CANDIDATE')})
    started = time.monotonic()
    forced = False
    with (folder / 'stdout.txt').open('xb') as stdout, (folder / 'stderr.txt').open('xb') as stderr:
        process = subprocess.Popen(argv, cwd=str(cwd), env=env, stdout=stdout, stderr=stderr)
        write(folder / 'started.json', {'pid': process.pid, 'parent_pid': os.getpid(), 'started_at_ns': time.time_ns()})
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            forced = True
            if diagnostic_logs:
                value = log_snapshot(diagnostic_logs)
                value['active_non_atomic'] = True
                write(folder / 'logs-before-kill.json', value)
            process.kill()
            code = process.wait(timeout=5)
    result = {'pid': process.pid, 'exit_code': code, 'timeout': forced,
        'alive': process.poll() is None, 'elapsed_seconds': time.monotonic()-started, 'waited': True}
    write(folder / 'completed.json', result)
    if diagnostic_logs:
        value = log_snapshot(diagnostic_logs)
        value['after_child_wait'] = True
        write(folder / 'logs-after-wait.json', value)
    return result


def diagnostic_preflight(args):
    """One stdlib/path/AST check, with zero product imports or targets."""
    import ast
    output = args.output.resolve()
    assert output == (ROOT / DIAGNOSTIC_RELATIVE).resolve()
    output.mkdir(parents=True, exist_ok=False)
    preflight = output / 'preflight'
    preflight.mkdir()
    for name in ('dump_traceback_later', 'cancel_dump_traceback_later'):
        assert callable(getattr(faulthandler, name))
    with (preflight / 'stdlib-stack-probe.txt').open('xb') as stream:
        faulthandler.dump_traceback_later(5, repeat=True, file=stream, exit=False)
        faulthandler.cancel_dump_traceback_later()
    for name in ('run.py', 'diagnostic_release.py'):
        path = HERE / name
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        compile(path.read_text(encoding='utf-8'), str(path), 'exec')
    write(preflight / 'check.json', {'status':'STDLIB_PATH_AST_OK_ONLY', 'pid':os.getpid(),
        'driver_sha256':sha(Path(__file__).read_bytes()),
        'release_sha256':sha((HERE / 'diagnostic_release.py').read_bytes()),
        'argv':sys.argv, 'cwd':str(Path.cwd()), 'product_imports':0, 'business_starts':0,
        'stdlib_timer_cancelled':True, 'new_python_threads':0})
    print('STDLIB_PATH_AST_OK_ONLY; business_starts=0')


def diagnostic(args):
    """90s parent watchdog captures raw parent streams and actual exit."""
    output = args.output.resolve()
    assert output == (ROOT / DIAGNOSTIC_RELATIVE).resolve()
    assert {p.name for p in output.iterdir()} == {'preflight'}, 'Existing diagnostic scene: stop'
    result = run_child(output/'parent-process', [sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),
        '--diagnostic-parent','--candidate',args.candidate,'--output',str(output)],
        cwd=ROOT,env=dict(os.environ,A03_M_CANDIDATE=args.candidate),timeout=90)
    print(json.dumps({'mode':'ONE_DIAGNOSTIC_ONLY','parent':result}))
    if result['exit_code'] != 0 or result['timeout']:
        raise RuntimeError('diagnostic parent failed; no retry')


def diagnostic_parent(args):
    """One new M1 execute, followed only by byte preservation/normal release."""
    output = args.output.resolve()
    assert output == (ROOT / DIAGNOSTIC_RELATIVE).resolve()
    assert {p.name for p in output.iterdir()} == {'preflight','parent-process'}, 'Existing diagnostic scene: stop'
    preflight = json.loads((output / 'preflight/check.json').read_bytes())
    assert preflight['driver_sha256'] == sha(Path(__file__).read_bytes())
    assert preflight['business_starts'] == 0
    run = output / 'run'
    run.mkdir(exist_ok=False)
    started = time.monotonic()
    write(run / 'parent-started.json', {'pid':os.getpid(),'argv':sys.argv,'cwd':str(Path.cwd()),
        'candidate':args.candidate,'started_at_ns':time.time_ns(), 'new_targets_upper':1,
        'dispatch_upper':3,'effects_upper':3,'child_seconds':45,'parent_seconds':90,
        'publisher':0,'finish':0,'reconcile':0})
    view = raw_view(args.candidate, run)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(view/'src'),str(view/'examples/a03/T1-capture')]),
        PYTHONDONTWRITEBYTECODE='1', A03_M_CANDIDATE=args.candidate,
        A03_DIAGNOSTIC_CASE=str(run/'case'))
    driver = view / 'examples/a03/T3-closure/run.py'
    case = run / 'case'
    case.mkdir(exist_ok=False)
    write(case/'request.json',{'case':'M1','candidate':args.candidate,
        'mode':'DIAGNOSTIC_EXECUTE_ONLY','publisher':0,'finish':0})
    logs = [case/'calls.jsonl', case/'stacks.txt']
    result = run_child(case/'processes/execute', [sys.executable,'-X','utf8','-B',str(driver),
        '--diagnostic-worker','--phase','execute','--case','M1','--output',str(case)], cwd=ROOT, env=env,
        timeout=45, diagnostic_logs=logs)
    write(run / 'business-result.json', {'worker':result,'no_next_scene':True,'no_functional_acceptance':True})
    if (case / 'anchor.json').is_file():
        cleanup = run_child(run/'processes/release', [sys.executable,'-X','utf8','-B',
            str(view/'examples/a03/T3-closure/diagnostic_release.py'),'--case',str(case),
            '--output',str(run/'release')], cwd=ROOT, env=env,
            timeout=max(1,min(45,85-(time.monotonic()-started))))
    else:
        cleanup = {'status':'NOT_RUN_NO_ANCHOR'}
    write(run / 'parent-finished.json', {'pid':os.getpid(),'finished_at_ns':time.time_ns(),
        'worker':result,'cleanup':cleanup,'extra_business_runs':0})
    print(json.dumps({'status':'DIAGNOSTIC_ENDED_NOT_M1_ACCEPTANCE','worker':result,'cleanup':cleanup}))


def raw_view(candidate, output):
    """Raw Git, no checkout normalization and no install. Log actual Git PIDs."""
    view = output / 'runtime-view'
    view.mkdir()
    git_calls = []
    def git(args, data=None):
        argv = ['git', '-c', 'core.longpaths=true', '-C', str(ROOT)] + args
        p = subprocess.Popen(argv, cwd=str(ROOT), stdin=subprocess.PIPE if data is not None else None,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate(data, timeout=45)
        git_calls.append({'argv': argv, 'cwd': str(ROOT), 'pid': p.pid, 'exit_code': p.returncode,
            'waited': True, 'stdout_sha256': sha(out), 'stderr': err.decode('utf-8','replace')})
        assert p.returncode == 0
        return out
    paths = git(['ls-tree', '-r', '--name-only', candidate, 'src/annotation', 'examples/a03/T3-closure', 'examples/a03/R1', 'tests/test_a03_t3_closure.py', 'tests/test_a03_r1_validation.py', 'examples/a03/T1-capture/capture.py']).decode('utf-8').splitlines()
    request = ''.join(candidate + ':' + p + '\n' for p in paths).encode('utf-8')
    packed = git(['cat-file', '--batch'], request)
    position, identities = 0, []
    for path in paths:
        end = packed.index(b'\n', position)
        header = packed[position:end].decode().split()
        assert len(header) == 3 and header[1] == 'blob', (path, header)
        size = int(header[2]); position = end + 1
        raw = packed[position:position+size]; position += size + 1
        dest = view / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        identities.append({'path': path, 'raw_sha256': sha(raw), 'git_blob': header[0], 'bytes': size})
    profile = json.loads((view / 'src/annotation/contracts/a03_native/data/profile.json').read_bytes())
    base = view / 'src/annotation/contracts/a03_native'
    for path, expected in profile['implementation_pins']:
        file = view / ('src/' + path[1:]) if path.startswith('@') else base / path
        assert sha(file.read_bytes()) == expected, ('implementation-pin', path)
    for path, expected in profile['schema_pins']:
        assert sha((base / 'data' / path).read_bytes()) == expected, ('schema-pin', path)
    assert sha((view / 'examples/a03/T1-capture/capture.py').read_bytes()) == '3e07d56f409d8203c42f252f7a2900e902e31f56e1ff5fc7475335d33d0b042b'
    write(output / 'runtime-identities.json', {'candidate': candidate, 'files': identities,
        'raw_equals_execution': True, 'pins': 'PASS_BEFORE_IMPORT', 'git_processes': git_calls})
    return view


def batch(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'batch-preregistration.json', {'candidate': args.candidate,
        'cases': list(CASES), 'fresh_targets_upper': 5, 'dispatch_upper': 11,
        'child_seconds': CHILD_SECONDS, 'parent_seconds': PARENT_SECONDS, 'case_once': True,
        'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
    view = raw_view(args.candidate, output)
    env = dict(os.environ)
    env.update(PYTHONPATH=os.pathsep.join([str(view / 'src'), str(view / 'examples/a03/T1-capture')]),
        PYTHONDONTWRITEBYTECODE='1', A03_M_CANDIDATE=args.candidate)
    driver = view / 'examples/a03/T3-closure/run.py'
    matrix = []
    try:
        for case in CASES:
            case_path = output / 'cases' / case
            argv = [sys.executable, '-X', 'utf8', '-B', str(driver), '--watchdog',
                '--case', case, '--output', str(case_path)]
            result = run_child(output / 'processes' / case, argv, cwd=ROOT, env=env, timeout=PARENT_SECONDS)
            matrix.append(dict(case=case, process=result))
            if result['exit_code'] != 0 or result['timeout']:
                raise RuntimeError('First case failure: ' + case)
    finally:
        write(output / 'matrix.json', {'actual': matrix,
            'not_run': [c for c in CASES if c not in [r['case'] for r in matrix]],
            'candidate': args.candidate})
    print(json.dumps({'status':'AUTHOR_REVIEW', 'cases':len(matrix), 'candidate':args.candidate}))


def watchdog(args):
    case = args.output.resolve()
    case.mkdir(parents=True, exist_ok=False)
    write(case / 'request.json', {'case':args.case, 'candidate':os.environ['A03_M_CANDIDATE']})
    for phase in ('execute', 'finish'):
        argv = [sys.executable, '-X', 'utf8', '-B', str(Path(__file__).resolve()),
            '--phase', phase, '--case', args.case, '--output', str(case)]
        result = run_child(case / 'processes' / phase, argv, cwd=Path.cwd(), env=dict(os.environ), timeout=CHILD_SECONDS)
        if result['exit_code'] != 0 or result['timeout']:
            raise RuntimeError('business phase failed: ' + phase)


def validation_r1(args):
    """Original five-case batch, first failure stops and releases only its scene."""
    root = args.output.resolve()
    assert root == (ROOT/VALIDATION_R1_RELATIVE).resolve()
    assert {p.name for p in root.iterdir()} == {'preflight'}, 'Existing business scene: stop'
    from contextlib import redirect_stdout, redirect_stderr
    write(root/'parent-started.json',{'pid':os.getpid(),'argv':sys.argv,'cwd':str(Path.cwd()),
        'candidate':args.candidate,'started_at_ns':time.time_ns(),'starts_upper':5,'dispatch_upper':11})
    args.output = root/'business'
    with (root/'parent-stdout.txt').open('x',encoding='utf-8')as stdout, (root/'parent-stderr.txt').open('x',encoding='utf-8')as stderr:
        with redirect_stdout(stdout),redirect_stderr(stderr):
            try:
                batch(args)
            except BaseException as error:
                traceback.print_exc()
                write(root/'first-business-failure.json',{'error':repr(error),'traceback':traceback.format_exc(),
                    'no_retry':True,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
                matrix=json.loads((args.output/'matrix.json').read_bytes())
                failed=matrix['actual'][-1]['case'] if matrix['actual'] else None
                if failed and (args.output/'cases'/failed/'anchor.json').exists():
                    view=args.output/'runtime-view'
                    env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(view/'src'),str(view/'examples/a03/T1-capture')]),
                        PYTHONDONTWRITEBYTECODE='1',A03_M_CANDIDATE=args.candidate,A03_R1_ROOT=str(root))
                    cleanup=run_child(root/'release-process'/failed,[sys.executable,'-X','utf8','-B',
                        str(view/'examples/a03/T3-closure/run.py'),'--validation-r1-release',
                        '--state',str(args.output/'cases'/failed),'--output',str(root/'release'/failed)],
                        cwd=ROOT,env=env,timeout=45)
                    write(root/'failure-release-result.json',cleanup)
                write(root/'parent-finished.json',{'pid':os.getpid(),'finished_at_ns':time.time_ns(),
                    'status':'REWORK_FIRST_FAILURE','expected_process_exit':1,'no_next_scene':True})
                raise
            else:
                write(root/'parent-finished.json',{'pid':os.getpid(),'finished_at_ns':time.time_ns(),
                    'status':'AUTHOR_REVIEW_FIVE_CASES_ENDED','expected_process_exit':0})


def validation_r1_release(args):
    """Byte preservation then at most one normal claim/release; never recovery."""
    case,output=args.state.resolve(),args.output.resolve()
    root=Path(os.environ['A03_R1_ROOT']).resolve()
    legacy = root.name == 'M-validation-R1'
    replacement = root.parent == ROOT/'docs/evidence/A03/R1/execution' and root.name in ('candidate-1', 'candidate-2')
    assert (legacy or replacement) and case.parent==root/'business/cases' and case.name in CASES
    assert output==root/'release'/case.name
    output.mkdir(parents=True,exist_ok=False)
    phases=[]
    for p in (case/'processes').glob('*/completed.json'):
        value=json.loads(p.read_bytes());assert value['alive']is False and value['waited']
        phases.append(value)
    assert phases
    for p in (case/'target/process-audit').glob('*/started.json'):
        assert json.loads(p.with_name('completed.json').read_bytes())['alive']is False
    records=[]
    folder=output/'termination-bytes';folder.mkdir()
    for label,source in [('runtime',case/'runtime/runtime.sqlite3'),('target',case/'target/target.sqlite3')]:
        for suffix in ('','-journal','-wal','-shm'):
            file=Path(str(source)+suffix)
            if file.exists():
                raw=file.read_bytes();dest=folder/(label+'.sqlite3'+suffix)
                write(dest,raw);assert sha(file.read_bytes())==sha(raw)
                records.append({'source':str(file),'retained':str(dest),'bytes':len(raw),'sha256':sha(raw)})
    write(output/'termination-index.json',{'files':records,'phases':phases,'original_SQLite_opened':False,
        'cross_database_atomic':False,'sidecars_deleted':False,'pid':os.getpid()})
    store=None
    try:
        from annotation.runtime.storage.native import open_native_state
        from annotation.runtime.storage.native_target import NativeTargetSession
        from capture import capture,Boundary
        descriptor=json.loads((case/'anchor.json').read_bytes())
        store=open_native_state(case/'anchor.json',expected_ledger_id=descriptor['ledger_id'],
            expected_target_store_id=descriptor['target_store_id'])
        reg=store.registration('registration-M');key=store.target_key('registration-M')
        observer=NativeTargetSession.open(reg['target_dir'],expected_store_id=store.target_store_id,
            expected_target_session_id=reg['session'],expected_target_key=key,expected_scope_id=reg['scope'],
            expected_source_ref=json.loads(reg['source']))
        before=store.status('registration-M');target_before=dict(observer.export_book_context(key))
        write(output/'before-release.json',{'status':before,'target':target_before,'stage':'AFTER_NORMAL_OPEN'})
        claimed=False
        if before['owner_id']is not None:
            delay=max(0,before['lease_until']-time.time()+.03);assert delay<=10.1
            write(output/'lease-wait.json',{'seconds':delay,'extension':False,'loops':0})
            if delay:time.sleep(delay)
            claim=store.claim(key,observer=observer);claimed=True
            store.release(key,owner_id=claim.owner_id,generation=claim.generation)
        sql=capture(case,'after-R1-failure-release',boundary=Boundary())
        after=store.status('registration-M');target_after=dict(observer.export_book_context(key))
        write(output/'after-release.json',{'status':after,'target':target_after,
            'runtime_counts':{k:len(v)for k,v in sql['runtime']['tables'].items()},
            'target_counts':{k:len(v)for k,v in sql['target']['tables'].items()},
            'threads':[t.name for t in threading.enumerate()]})
        assert before['actions']==after['actions'] and target_before['effect_log']==target_after['effect_log']
        assert after['owner_id']is None and after['owner_phase']=='RELEASED'and after['lease_until']==0
        write(output/'release-proof.json',{'owner_released':True,'claimed_once':claimed,'actions_effects_unchanged':True,
            'dispatch':0,'reconcile':0,'publisher':0,'PRE':0,'pid':os.getpid()})
    except BaseException as error:
        write(output/'first-error.json',{'error':repr(error),'traceback':traceback.format_exc(),'no_retry':True})
        if store is not None:write(output/'residual-status.json',store.status('registration-M'))
        raise


def query_export(args):
    """Explicit read-only CLI operations; never init, claim, reconcile or publish."""
    from annotation.runtime.storage.native import open_native_state
    from annotation.runtime.recovery import open_observer
    from annotation.runtime.storage.common import plain
    state = args.state.resolve()
    descriptor = json.loads((state / 'anchor.json').read_bytes())
    args.output.mkdir(parents=True, exist_ok=False)
    store = open_native_state(state / 'anchor.json', expected_ledger_id=descriptor['ledger_id'],
        expected_target_store_id=descriptor['target_store_id'])
    observer = open_observer(store, 'registration-M')
    write(args.output / 'status.json', store.status('registration-M'))
    write(args.output / 'target-status.json', plain(observer.export_book_context(store.target_key('registration-M'))))
    if args.operation == 'export': write(args.output / 'export.json', store.export('registration-M'))


def imports(case, label):
    found = []
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, '__file__', None)
        if name.startswith('annotation') and path and Path(path).is_file():
            found.append({'module':name,'file':str(Path(path).resolve()),'sha256':sha(Path(path).read_bytes())})
    write(case / ('imports-' + label + '.json'), {'pid':os.getpid(), 'python':sys.version,
        'executable':sys.executable, 'cwd':str(Path.cwd()), 'modules':found,
        'capture_file':str(Path(sys.modules['capture'].__file__).resolve()),
        'capture_sha256':sha(Path(sys.modules['capture'].__file__).read_bytes())})


def phase(args):
    diagnostic_mode = args.diagnostic_worker
    if diagnostic_mode:
        assert args.case == 'M1' and args.phase == 'execute'
    trace = DiagnosticTrace(args.output.resolve()) if diagnostic_mode else None
    try:
        if trace:
            trace.imports_pending = True
            trace.event('imports', 'ENTER')
        try:
            return phase_body(args, trace)
        except BaseException as error:
            if trace:
                if trace.imports_pending:
                    trace.event('imports', 'ERROR', error=repr(error))
                trace.event('worker', 'ERROR', error=repr(error))
            raise
        finally:
            if trace:
                trace.event('worker', 'EXIT')
    finally:
        if trace:
            trace.close()


def phase_body(args, trace=None):
    phase_start = (time.monotonic(), time.process_time())
    timings = []
    # All product imports are below this point, after the immutable candidate,
    # raw view, pins and input preregistration have been checked by batch().
    from capture import capture, LeaseBoundary, Boundary
    from annotation.contracts import artifact_ref, policy_ref, validate_bundle
    from annotation.runtime.storage.native import init_native_state, open_native_state
    from annotation.runtime.storage.common import now, plain, reference, digest, RuntimeFailure
    from annotation.runtime.recovery import run_plan, reconcile, open_observer, publish_quality
    from annotation.runtime.recovery.lease import LeaseKeeper
    from annotation.delivery.mock.persistent import PersistentMockSession
    from annotation.quality.synthetic_precheck import produce_a03_pre_run, admit_a03_pre_run
    from annotation.quality.targetcheck import SimulationConfig, check_target
    from annotation.delivery.planner import create_plan, compare_action_effect
    if trace:
        trace.event('imports', 'EXIT')
        trace.imports_pending = False
    case = args.output.resolve()
    store = observer = claim = boundary = None
    if trace:
        trace.keeper_state = lambda: None if boundary is None else boundary.snapshot()
    imports(case, args.phase + '-before')
    def measured(name, operation, **fields):
        started = (time.monotonic(), time.process_time())
        try:
            return trace.call(name, operation, **fields) if trace else operation()
        finally:
            timings.append(dict(call=name, wall_seconds=time.monotonic()-started[0],
                cpu_seconds=time.process_time()-started[1], **fields))
    def snap(stage):
        return measured('capture:'+stage, lambda: capture(case, stage, boundary=boundary or Boundary()))
    def get_artifacts():
        return store.bundle('registration-M')['artifacts']
    def pre_plan(label, kind='INITIAL', hold=None):
        actual = store.begin_native_pre('registration-M', owner_id=claim.owner_id, generation=claim.generation,
            observer=observer, kind=kind)
        artifacts = actual.bundle.artifacts
        source = next(a for a in artifacts if a.kind=='SourceBundle')
        evidence = next(a for a in artifacts if a.kind=='EvidenceBundle')
        graph = next(a for a in artifacts if a.kind=='QuestionGraph')
        bundle, pre_ref = produce_a03_pre_run(actual.bundle, artifact_ref(source), artifact_ref(evidence),
            artifact_ref(graph), policy_ref(actual.bundle.policies[0]), bridge_context=actual.bundle.bridge_context,
            registered_run_handle=actual.handle, actual_snapshot_ref=actual.snapshot_ref, actual_observation=actual.observation,
            asset_root=package_root, artifact_id='pre-M-'+label, created_at=now())
        admit_a03_pre_run(bundle, pre_ref, bridge_context=bundle.bridge_context, registered_run_handle=actual.handle,
            actual_snapshot_ref=actual.snapshot_ref, asset_root=package_root)
        bundle = check_target(bundle, artifact_ref(graph), actual.snapshot_ref, actual.snapshot_ref,
            policy_ref(bundle.policies[0]), config, artifact_id='target-M-'+label, created_at=now(), bridge_context=bundle.bridge_context)
        target_ref = artifact_ref(bundle.artifacts[-1])
        bundle = create_plan(bundle, artifact_ref(graph), pre_ref, target_ref, actual.snapshot_ref, actual.snapshot_ref,
            policy_ref(bundle.policies[0]), config, artifact_id='plan-M-'+label, created_at=now(), bridge_context=bundle.bridge_context)
        plan = plain(bundle.artifacts[-1])
        if hold:
            head = store.status('registration-M')['event_head']
            store.record_hold_candidate('registration-M', bundle, reference(plan), config, hold_id=hold,
                owner_id=claim.owner_id, generation=claim.generation, expected_head=head)
        else:
            store.record_native_plan('registration-M', bundle, reference(plan), config,
                owner_id=claim.owner_id, generation=claim.generation)
        return plan
    def execute_api(plan, unknown_index=None, not_applied=False):
        measured('accept_plan', lambda: store.accept_plan('registration-M', reference(plan), owner_id=claim.owner_id, generation=claim.generation))
        records = []
        for index, action in enumerate(plan['payload']['actions']):
            fields = {'action_id':action['action_id'], 'index':index}
            context = measured('context-load', lambda: store.load_book_context(store.target_key('registration-M'),
                owner_id=claim.owner_id, generation=claim.generation), **fields)
            measured('context-import', lambda: observer.import_book_context(context, authority=store), **fields)
            bundle = measured('validate', lambda: store._validate(store.bundle('registration-M'), asset_root=package_root), **fields)
            prepared = measured('prepare', lambda: observer.prepare_action(bundle, reference(plan), action['action_id'], config,
                current_snapshot_ref=plan['payload']['snapshot'], asset_root=package_root, bridge_context=bundle.bridge_context), **fields)
            intent = measured('commit_intent', lambda: store.commit_intent(prepared, owner_id=claim.owner_id, generation=claim.generation), **fields)
            permit = measured('permit', lambda: store.issue_first_dispatch(intent['intent_ref'], owner_id=claim.owner_id,
                generation=claim.generation, plan_ref=reference(plan), action_id=action['action_id'], observation_binding=prepared['observation_binding']), **fields)
            measured('dispatch', lambda: observer.dispatch_action(prepared, committed_intent=intent, dispatch_permit=permit, authority=store,
                effect_fault='not_applied' if not_applied and index==unknown_index else None), **fields)
            observation = measured('observe', lambda: observer.observe_target(store.target_key('registration-M'), observation_id='M-execute-'+args.case+'-'+str(index),
                read_fault='unavailable' if index==unknown_index else None), **fields)
            comparison = measured('compare', lambda: compare_action_effect(prepared['action'], prepared['observation'], observation), **fields)
            result = measured('commit_action_result', lambda: store.commit_action_result(intent, prepared, observation, comparison,
                owner_id=claim.owner_id, generation=claim.generation), **fields)
            records.append(plain(result))
            if result['result']['outcome'] != 'APPLIED':
                break
        return records
    try:
        if args.phase=='execute':
            tag = 'three' if args.case.startswith(('M1','M2')) else 'single'
            source_root = case / 'input'
            shutil.copytree(HERE / 'inputs' / tag, source_root)
            raw = json.loads((source_root / 'initial.json').read_bytes())
            store = measured('init', lambda: init_native_state(case / 'anchor.json', case / 'runtime',
                expected_ledger_id='ledger-'+args.case, expected_target_store_id='store-'+args.case))
            context = measured('initial-bridge', lambda: store.bridge_for(raw, source_root))
            bundle = measured('initial-validate', lambda: validate_bundle(raw, asset_root=source_root, bridge_context=context))
            source, evidence, graph, snapshot = bundle.artifacts
            key = {'platform_namespace':'a03-M', 'target_id':snapshot.payload.target_id, 'book_id':source.book_id}
            config = SimulationConfig(source.book_id, snapshot.payload.target_id, source.scope_id, {'directory-M':'platform-M'})
            registered = measured('register', lambda: store.register_book(bundle, target_key=key, target_dir=case / 'target',
                target_session_id='session-'+args.case, source_ref=artifact_ref(source), asset_root=source_root,
                config=vars(config), registration_id='registration-M'))
            package_root = Path(registered.package_root)
            observer = measured('target-create', lambda: PersistentMockSession.create(case / 'target', bundle, artifact_ref(snapshot), platform_namespace='a03-M',
                source_ref=artifact_ref(source), asset_root=package_root, expected_store_id=store.target_store_id,
                target_session_id='session-'+args.case, bridge_context=store.bridge_for(bundle, package_root)))
            claim = measured('claim', lambda: store.claim(key, observer=observer))
            boundary = LeaseBoundary(LeaseKeeper(store,key,claim.owner_id,claim.generation).start())
            snap('initialized')
            plan = measured('pre_plan', lambda: pre_plan(args.case+'-original'))
            write(case / 'original-plan.json', plan)
            snap('before-execute')
            if trace:
                trace.arm()
            try:
                records = measured('execute_api', lambda: execute_api(plan,
                    unknown_index=1 if args.case.startswith('M2') else 0 if args.case.startswith('M3') else None,
                    not_applied=args.case.startswith('M3')))
            finally:
                if trace:
                    trace.cancel()
            write(case / 'execution.json', {'records':records, 'status':store.status('registration-M')})
            snap('after-diagnostic-execute' if trace else 'unknown-established' if args.case!='M1' else 'before-report')
            if args.case=='M1' and trace is None:
                report = publish_quality(store,'registration-M',owner_id=claim.owner_id,generation=claim.generation)
                write(case / 'report.json', plain(report))
                snap('after-report')
        else:
            store = open_native_state(case / 'anchor.json', expected_ledger_id='ledger-'+args.case, expected_target_store_id='store-'+args.case)
            observer = open_observer(store,'registration-M')
            reg = store.registration('registration-M')
            package_root = Path(reg['package_root'])
            config = SimulationConfig(**dict(json.loads(reg['config']), allowed_operations=tuple(json.loads(reg['config'])['allowed_operations'])))
            plan = json.loads((case / 'original-plan.json').read_bytes())
            snap('reopened-before-action')
            if args.case=='M1':
                before = plain(observer.export_book_context(store.target_key('registration-M')))
                try:
                    run_plan(store,'registration-M')
                except RuntimeFailure as error:
                    assert error.code=='REPLAY_FORBIDDEN', (error.code,str(error))
                    write(case / 'replay-refusal.json', {'code':error.code,'message':str(error),'before':before,
                        'after':plain(observer.export_book_context(store.target_key('registration-M')))})
                else:
                    raise AssertionError('old plan unexpectedly ran')
            elif args.case.startswith('M2'):
                key = store.target_key('registration-M')
                claim = store.claim(key,observer=observer)
                boundary = LeaseBoundary(LeaseKeeper(store,key,claim.owner_id,claim.generation).start())
                action = plan['payload']['actions'][2]
                request = {'registration_id':'registration-M', 'plan_ref':reference(plan), 'action_id':action['action_id'],
                    'action_digest':digest(action),'expected_event_head':store.status('registration-M')['event_head'],
                    'entry_id':'entry-'+args.case,'parent_call_id':'entry-parent-'+args.case}
                if args.case=='M2-insufficient': request['read_fault']='truncated'
                write(case / 'entry-request.json',request)
                result = store.commit_unattempted_absence(store.bundle('registration-M'), request,
                    owner_id=claim.owner_id,generation=claim.generation,asset_root=package_root,observer=observer)
                write(case / 'entry-result.json',plain(result))
                assert result['status']==('NOT_APPLIED' if args.case=='M2-sufficient' else 'INCONCLUSIVE')
                assert result['read_count']==(3 if args.case=='M2-sufficient' else 2)
                snap('after-readonly-entry')
                try:
                    store.commit_unattempted_absence(store.bundle('registration-M'), request,
                        owner_id=claim.owner_id,generation=claim.generation,asset_root=package_root,observer=observer)
                except RuntimeFailure as error:
                    assert error.code=='READONLY_ENTRY_CONSUMED'
                    write(case / 'entry-reopen-refusal.json', {'code':error.code,'message':str(error)})
                else: raise AssertionError('entry budget reset')
            else:
                result = reconcile(store,'registration-M',call_id='M-call-'+args.case,max_attempts=1)
                write(case / 'reconciliation.json',plain(result))
                assert result['attempt_count']==1 and result['resolutions'][0]['status']=='RESOLVED_NOT_APPLIED'
                snap('after-reconcile')
                key = store.target_key('registration-M')
                claim = store.claim(key,observer=observer)
                boundary = LeaseBoundary(LeaseKeeper(store,key,claim.owner_id,claim.generation).start())
                observer.synthetic_external_add_directory('synthetic-external-M-first')
                hold = store.detect_target_drift(key,owner_id=claim.owner_id,generation=claim.generation,observer=observer)
                assert hold.created
                candidate = pre_plan(args.case+'-hold-candidate',kind='POST_HOLD',hold=hold.hold_id)
                write(case / 'hold-candidate.json',candidate)
                snap('hold-candidate-indexed')
                if args.case=='M3-final-drift': observer.synthetic_external_add_directory('synthetic-external-M-final')
                try:
                    cleared = store.clear_target_drift_hold(hold.hold_id,candidate['payload']['snapshot'],
                        candidate['payload']['precheck'],candidate['payload']['targetcheck'],reference(candidate),
                        owner_id=claim.owner_id,generation=claim.generation)
                except RuntimeFailure as error:
                    if args.case!='M3-final-drift' or error.code!='TARGET_CHANGED': raise
                    write(case / 'final-drift-refusal.json',{'code':error.code,'message':str(error)})
                    snap('final-drift-hold-preserved')
                else:
                    assert args.case=='M3-new-plan'
                    write(case / 'hold-cleared.json',plain(cleared))
                    snap('after-hold-clear')
                    try:
                        from annotation.contracts import assert_plan_ready
                        b=store._validate(store.bundle('registration-M'),asset_root=package_root)
                        assert_plan_ready(b,reference(candidate),candidate['payload']['snapshot'],bridge_context=b.bridge_context)
                    except RuntimeFailure as error:
                        assert error.code in ('NATIVE_RUN_CURRENTNESS','NATIVE_RUN_STALE_HEAD')
                        write(case / 'old-hold-proof-refusal.json',{'code':error.code,'message':str(error)})
                    else: raise AssertionError('old POST_HOLD proof survived clear')
                    newplan=pre_plan(args.case+'-fresh-initial')
                    write(case / 'new-plan.json',newplan)
                    snap('new-INITIAL-before-execute')
                    boundary.stop(); boundary=None
                    output=run_plan(store,'registration-M',owner_id=claim.owner_id,generation=claim.generation,config=vars(config))
                    write(case / 'new-execution.json',plain(output))
                    snap('new-execution-and-report-released')
        write(case / ('phase-'+args.phase+'-result.json'), {'status':store.status('registration-M'),
            'artifacts':get_artifacts(), 'target':plain(observer.export_book_context(store.target_key('registration-M')))})
    except BaseException as error:
        write(case / ('first-failure-'+args.phase+'.json'),{'error':repr(error),'traceback':traceback.format_exc()})
        if store is not None and observer is not None:
            try: snap('first-failure-'+args.phase)
            except BaseException as capture_error: write(case / ('failure-capture-error-'+args.phase+'.json'),{'error':repr(capture_error)})
        raise
    finally:
        if trace:
            trace.cancel()
        if boundary is not None:
            boundary.stop()
        if store is not None and observer is not None:
            if claim is not None:
                status=store.status('registration-M')
                if status['owner_id']==claim.owner_id:
                    store.release(store.target_key('registration-M'),owner_id=claim.owner_id,generation=claim.generation)
            capture(case,'after-release-'+args.phase,boundary=Boundary())
            write(case / ('release-'+args.phase+'.json'),{'status':store.status('registration-M'),
                'owned_threads':[t.name for t in __import__('threading').enumerate()],
                'keeper':None if boundary is None else boundary.snapshot()})
        imports(case,args.phase+'-after')
        write(case / ('metrics-'+args.phase+'.json'), dict(
            wall_seconds=time.monotonic()-phase_start[0], cpu_seconds=time.process_time()-phase_start[1],
            stages=timings, validation=None if store is None else store.native_registry.validation_counts))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--batch',action='store_true')
    parser.add_argument('--watchdog',action='store_true')
    parser.add_argument('--diagnostic-preflight',action='store_true')
    parser.add_argument('--diagnostic',action='store_true')
    parser.add_argument('--diagnostic-parent',action='store_true')
    parser.add_argument('--diagnostic-worker',action='store_true')
    parser.add_argument('--validation-r1',action='store_true')
    parser.add_argument('--validation-r1-release',action='store_true')
    parser.add_argument('--candidate')
    parser.add_argument('--case',choices=CASES)
    parser.add_argument('--phase',choices=('execute','finish'))
    parser.add_argument('--operation', choices=('query','export'))
    parser.add_argument('--state',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.validation_r1: validation_r1(args)
    elif args.validation_r1_release: validation_r1_release(args)
    elif args.diagnostic_preflight: diagnostic_preflight(args)
    elif args.diagnostic: diagnostic(args)
    elif args.diagnostic_parent: diagnostic_parent(args)
    elif args.operation: query_export(args)
    elif args.batch: batch(args)
    elif args.watchdog: watchdog(args)
    else: phase(args)


if __name__=='__main__':
    main()
