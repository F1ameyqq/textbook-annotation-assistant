"""Frozen A12-R1 independent D1-D8 only. One durable run directory, no retry.

Only one real synthetic protocol child. No browser, server, profile, credentials,
occupancy scan, original suite, or product patching. Fakes replace external page,
context and runtime objects; real product observation/error/finalization code runs.
"""
import argparse
import asyncio
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
RUN = OUT / 'run'
PRODUCT = ROOT / 'tools/headless_native_reuse_probe_r1.py'
THREAD_ID = '01a157a5-495a-7bf3-bc17-299ad85c48a7'
PRODUCT_COMMIT = 'd45ed25a98361002ddb28985c1d27687c4421a17'
FINAL_COMMIT = '81fab23e3e7e9e32a36d3857a253afc69b5bd3e1'
EXPECTED_TARGET = 'https://www.usense.com/qieti/annotateUnified'
EXPECTED_VIEWER = '.pdf-zones-container:visible'
ORDER = tuple('D' + str(n) for n in range(1, 9))
# Exactly eight task-defined independent rejects, frozen before any product behavior.
REJECTS = (
    ('nonzero_count', b'{"count":7}\n', b'', 0),
    ('negative_count', b'{"count":-3}\n', b'', 0),
    ('boolean_count', b'{"count":true}\n', b'', 0),
    ('extra_field', b'{"count":0,"unused":1}\n', b'', 0),
    ('multiple_records', b'{"count":0}\n{"count":0}\n', b'', 0),
    ('trailing_garbage', b'{"count":0}\nZ', b'', 0),
    ('stderr', b'{"count":0}\n', b'SYNTHETIC_ERROR', 0),
    ('nonzero_exit', b'{"count":0}\n', b'', 9),
)
CHILD = None
KERNEL = None
CHILD_RELEASE = {'state': 'NOT_CREATED', 'handle_closed': False, 'pipes_closed': False}
CHILD_LOCK = threading.RLock()
DONE = threading.Event()
RESULT = {
    'review_thread_id': THREAD_ID, 'product_commit': PRODUCT_COMMIT, 'final_commit': FINAL_COMMIT,
    'status': 'RUNNING', 'cases': {k: {'status': 'NOT_RUN'} for k in ORDER},
    'first_unexpected_failure': None, 'active_case': None,
    'counters': {'independent_delta_runs': 1, 'protocol_children': 0,
                 'browser_launches': 0, 'fixture_servers': 0, 'platform_requests': 0,
                 'real_occupancy_scans': 0, 'profile_or_credential_accesses': 0,
                 'login_actions': 0, 'business_writes': 0, 'original_suite_runs': 0,
                 'author_driver_runs': 0, 'product_modifications': 0, 'external_messages': 0},
}

def utc():
    return datetime.now(timezone.utc).isoformat()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def put(name, value):
    data = (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + '\n').encode('utf-8')
    with (RUN / name).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())

def check(condition, code):
    if not condition:
        raise AssertionError(code)

def fixed_error(error):
    return {'exception_type': type(error).__name__,
            'code': str(error) if isinstance(error, AssertionError) else 'UNEXPECTED_LOCAL_EXCEPTION'}

class ExactHandleQueries:
    """Four queries on the retained Popen handle; no process enumeration/OpenProcess."""
    def __init__(self):
        check(os.name == 'nt', 'WINDOWS_REQUIRED')
        self.dll = ctypes.WinDLL('kernel32', use_last_error=True)
        signatures = {
            'GetProcessId': ([wintypes.HANDLE], wintypes.DWORD),
            'GetProcessTimes': ([wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4, wintypes.BOOL),
            'WaitForSingleObject': ([wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
            'GetExitCodeProcess': ([wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.dll, name)
            fn.argtypes, fn.restype = args, result

    def identity(self, handle):
        pid = int(self.dll.GetProcessId(handle))
        created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
        check(bool(pid) and bool(self.dll.GetProcessTimes(handle, ctypes.byref(created),
              ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user))), 'CHILD_TIMES_UNKNOWN')
        state = int(self.dll.WaitForSingleObject(handle, 0))
        check(state in (0, 258), 'CHILD_WAIT_UNKNOWN')
        exit_code = wintypes.DWORD()
        check(bool(self.dll.GetExitCodeProcess(handle, ctypes.byref(exit_code))), 'CHILD_EXIT_UNKNOWN')
        filetime = lambda v: (int(v.dwHighDateTime) << 32) | int(v.dwLowDateTime)
        check(filetime(created) > 0, 'CHILD_CREATION_UNKNOWN')
        if state == 0:
            check(filetime(exited) > 0, 'CHILD_EXIT_TIME_UNKNOWN')
        return {'pid': pid, 'created_filetime': filetime(created),
                'exit_observed': state == 0, 'exit_code': int(exit_code.value) if state == 0 else None,
                'exited_filetime': filetime(exited) if state == 0 else None}

def release_child():
    global CHILD
    with CHILD_LOCK:
        child = CHILD
        if child is None:
            return
        try:
            if child.poll() is None:
                CHILD_RELEASE['terminated_exact_retained_child'] = True
                child.kill()
                child.wait(timeout=1)
            CHILD_RELEASE['after'] = KERNEL.identity(int(child._handle))
            before, after = CHILD_RELEASE['before'], CHILD_RELEASE['after']
            CHILD_RELEASE['same_pid_and_creation'] = (before['pid'] == after['pid'] and
                before['created_filetime'] == after['created_filetime'])
        finally:
            for stream in (child.stdout, child.stderr):
                if stream is not None and not stream.closed:
                    stream.close()
            CHILD_RELEASE['pipes_closed'] = child.stdout.closed and child.stderr.closed
            child._handle.Close()
            CHILD_RELEASE['handle_closed'] = True
            CHILD = None
            CHILD_RELEASE['state'] = ('RELEASED' if CHILD_RELEASE.get('same_pid_and_creation') and
                CHILD_RELEASE.get('after', {}).get('exit_observed') and
                CHILD_RELEASE['pipes_closed'] and CHILD_RELEASE['handle_closed'] else 'UNKNOWN')

def fail(case, error):
    failure = {'case': case, **fixed_error(error)}
    if RESULT['first_unexpected_failure'] is None:
        RESULT['first_unexpected_failure'] = failure
    if case in RESULT['cases'] and RESULT['cases'][case]['status'] == 'NOT_RUN':
        RESULT['cases'][case] = {'status': 'FAIL', 'error': failure}

def watchdog():
    if DONE.is_set():
        return
    fail(RESULT['active_case'], AssertionError('OUTER_55_SECOND_CLEANUP_RESERVE'))
    try:
        release_child()
    finally:
        try:
            put('watchdog-event.json', {'at': utc(), 'result': RESULT, 'release': CHILD_RELEASE})
        finally:
            os._exit(124)

def load_product():
    spec = importlib.util.spec_from_file_location('independent_r1_product', PRODUCT)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    return probe

def d1(probe):
    global CHILD, KERNEL
    check(os.name == 'nt', 'D1_NOT_WINDOWS')
    check(RESULT['counters']['protocol_children'] == 0, 'PROTOCOL_CHILD_LIMIT')
    KERNEL = ExactHandleQueries()
    command = [sys.executable, '-B', str(OUT / 'protocol_child.py')]
    with CHILD_LOCK:
        CHILD = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, creationflags=0x08000000,
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONIOENCODING': 'utf-8'})
        RESULT['counters']['protocol_children'] += 1
        CHILD_RELEASE['state'] = 'OWNED'
        CHILD_RELEASE['before'] = KERNEL.identity(int(CHILD._handle))
    output = errors = b''
    exit_code = None
    try:
        output, errors = CHILD.communicate(timeout=4)
        exit_code = CHILD.returncode
        accepted = probe.accept_occupancy_zero(output, errors, exit_code)
        check(accepted == 0 and output == b'{"count":0}\n' and not errors and exit_code == 0,
              'D1_NOT_CANONICAL_ACCEPTED_ZERO')
    finally:
        release_child()
        put('protocol-child-release.json', CHILD_RELEASE)
        put('D1-protocol-raw.json', {'stdout_hex': output.hex(), 'stderr_hex': errors.hex(),
            'stdout_length': len(output), 'exit_code': exit_code, 'argv': command})
    check(CHILD_RELEASE['state'] == 'RELEASED' and CHILD_RELEASE['after']['exit_code'] == 0,
          'D1_RELEASE_UNPROVEN')
    return {'status': 'PASS', 'stdout_hex': output.hex(), 'stderr_hex': errors.hex(),
            'exit_code': exit_code, 'accepted_zero': accepted, 'release': dict(CHILD_RELEASE)}

def d2(probe):
    observations = []
    check(len(REJECTS) == 8, 'D2_FIXED_INPUT_COUNT')
    for name, output, errors, code in REJECTS:
        entry = {'name': name, 'stdout_hex': output.hex(), 'stderr_hex': errors.hex(), 'exit_code': code}
        try:
            probe.accept_occupancy_zero(output, errors, code)
        except probe.StopProbe as error:
            entry['observed_error'] = str(error)
            check(str(error) == 'PROFILE_OCCUPANCY_UNPROVEN', 'D2_WRONG_REJECTION_' + name)
            entry['result'] = 'REJECTED'
        else:
            entry['result'] = 'ACCEPTED_UNEXPECTEDLY'
            observations.append(entry)
            put('D2-rejects.json', observations)
            raise AssertionError('D2_ACCEPTED_' + name)
        observations.append(entry)
    put('D2-rejects.json', observations)
    return {'status': 'PASS', 'fixed_inputs': len(observations), 'observations': observations}

class PageBoundary:
    def __init__(self, probe, case, trace):
        self.probe, self.case, self.trace = probe, case, trace
        self.url = EXPECTED_TARGET
        self.guard = None
        self.calls = {'goto': 0, 'password': 0, 'viewer': 0, 'login_actions': 0}

    async def goto(self, url, *, wait_until, timeout):
        check(url == EXPECTED_TARGET and wait_until == 'domcontentloaded' and timeout == 45000,
              'FAKE_GOTO_CONTRACT')
        self.calls['goto'] += 1
        self.trace.append({'event': 'goto.await'})
        await asyncio.sleep(0)

    def get_by_placeholder(self, value, *, exact):
        check(value == '\u8bf7\u8f93\u5165\u5bc6\u7801' and exact is True, 'FAKE_PASSWORD_CONTRACT')
        return VisibilityBoundary(self, 'password')

    def locator(self, selector):
        check(selector == EXPECTED_VIEWER, 'FAKE_VIEWER_CONTRACT')
        return VisibilityBoundary(self, 'viewer')

    def inject(self, kind):
        if self.case == 'D5' and kind == 'password':
            self.guard.block_seen()
            self.trace.append({'event': 'password.await.guard.block_seen', 'failure': self.guard.failure})
        if self.case == 'D6' and kind == 'viewer':
            self.guard.record_failure(self.probe.StopProbe('REVIEW_VIEWER_FIRST_FAILURE'))
            self.trace.append({'event': 'viewer.await.guard.record_failure', 'failure': self.guard.failure})

class VisibilityBoundary:
    def __init__(self, page, kind):
        self.page, self.kind = page, kind
        self.first = self

    async def is_visible(self):
        self.page.calls[self.kind] += 1
        self.page.trace.append({'event': self.kind + '.await.begin'})
        asyncio.get_running_loop().call_soon(self.page.inject, self.kind)
        await asyncio.sleep(0)
        self.page.trace.append({'event': self.kind + '.await.end'})
        return self.page.case == 'D4' if self.kind == 'password' else True

class ContextBoundary:
    def __init__(self, page):
        self.page, self.calls = page, 0

    async def close(self):
        self.calls += 1
        p = self.page
        p.trace.append({'event': 'context.close.await.begin', 'shutdown_started': p.guard.shutdown_started})
        await asyncio.sleep(0)
        if p.case == 'D6':
            p.guard.record_failure(p.probe.StopProbe('REVIEW_VIEWER_LATER_CLOSE_FAILURE'))
            p.trace.append({'event': 'context.close.later_guard_error', 'failure': p.guard.failure})
        if p.case == 'D8':
            p.guard.record_failure(p.probe.StopProbe('REVIEW_SHUTDOWN_FIRST_FAILURE'))
            p.trace.append({'event': 'context.close.first_guard_error', 'failure': p.guard.failure})
        p.trace.append({'event': 'context.close.await.end'})

class RuntimeBoundary:
    def __init__(self, page):
        self.page, self.calls = page, 0

    async def stop(self):
        self.calls += 1
        p = self.page
        p.trace.append({'event': 'runtime.stop.await.begin'})
        await asyncio.sleep(0)
        if p.case == 'D8':
            p.guard.record_failure(p.probe.StopProbe('REVIEW_SHUTDOWN_LATER_FAILURE'))
            p.trace.append({'event': 'runtime.stop.second_guard_error', 'failure': p.guard.failure})
        p.trace.append({'event': 'runtime.stop.await.end'})

async def dom_case(probe, case):
    baseline_tasks = set(asyncio.all_tasks())
    trace = []
    page = PageBoundary(probe, case, trace)
    context, runtime = ContextBoundary(page), RuntimeBoundary(page)
    guard = probe.NativeGuard(context, page, probe.NativePolicy())
    page.guard = guard
    state = {'guard': guard, 'context': context, 'runtime': runtime, 'release': probe.initial_release()}
    state['release']['context_created'] = True  # In-memory boundary, no real context is acquired.
    result = probe.initial_observation()
    if case == 'D7':
        guard.record_failure(probe.StopProbe('REVIEW_PREEXISTING_FIRST_FAILURE'))
        trace.append({'event': 'before.observe.guard.record_failure', 'failure': guard.failure})
    try:
        await probe.observe_page(page, guard, result)
    except BaseException as error:
        trace.append({'event': 'observe.exception', 'sanitized': probe.safe_error(error)})
        probe.record_observation_error(result, state, error)
    provisional = json.loads(json.dumps(result))
    trace.append({'event': 'observe.complete', 'outcome': result['outcome']})
    output = RUN / (case + '-observation.json')
    code = await probe.finalize_observation(state, result, output)
    raw = output.read_bytes()
    saved = json.loads(raw)
    trace.append({'event': 'serialized', 'outcome': saved['outcome'], 'exit_code': code,
                  'observation_sha256': sha(raw)})
    put(case + '-trace.json', trace)
    check(saved == result, case + '_SERIALIZED_RESULT_DIFFERS')
    pre, final = saved['guard_state_pre_shutdown'], saved['guard_state_at_serialization']
    check(saved['successors'] == 'NOT_RUN' and saved['login_submissions'] == saved['business_writes'] == 0,
          case + '_SCOPE_COUNTERS')
    check(context.calls == runtime.calls == 1 and saved['release']['state'] == 'RELEASED',
          case + '_FAKE_RELEASE_INCOMPLETE')
    check(not pre['shutdown_started'] and final['shutdown_started'] and final['stopped'],
          case + '_SHUTDOWN_SNAPSHOT_INCORRECT')
    check(final['pending_tasks'] == 0 and not guard.tasks, case + '_GUARD_TASKS_REMAIN')
    if case in ('D3', 'D4'):
        expected = 'AUTHENTICATED_VIEWER_OBSERVED' if case == 'D3' else 'LOGIN_REQUIRED'
        check(saved['outcome'] == expected and code == 0 and saved['error'] is None and
              saved['guard_failure'] is None and not pre['stopped'] and not pre['terminal_stopped'] and
              not final['terminal_stopped'] and final['failure'] is None,
              case + '_CLEAN_SHUTDOWN_MISCLASSIFIED')
    else:
        check(saved['outcome'] == 'ERROR' and code == 2 and final['terminal_stopped'],
              case + '_TERMINAL_GUARD_NOT_AUTHORITATIVE')
        if case == 'D5':
            check(pre['stopped'] and pre['terminal_stopped'] and pre['failure'] is None and
                  final['failure'] is None and saved['guard_failure'] is None and
                  saved['error']['codes'] == ['NETWORK_GUARD_STOPPED'] and page.calls['viewer'] == 0,
                  'D5_STOP_WITHOUT_ERROR_LOST')
        else:
            first = {'D6': 'REVIEW_VIEWER_FIRST_FAILURE', 'D7': 'REVIEW_PREEXISTING_FIRST_FAILURE',
                     'D8': 'REVIEW_SHUTDOWN_FIRST_FAILURE'}[case]
            check(saved['error']['codes'] == saved['guard_failure']['codes'] == final['failure']['codes'] == [first],
                  case + '_FIRST_ORIGINAL_GUARD_ERROR_LOST')
        if case == 'D7':
            check(page.calls['goto'] == page.calls['password'] == page.calls['viewer'] == 0 and
                  saved['navigation_intents'] == 0, 'D7_NOT_RUN_BOUNDARY_BROKEN')
        if case == 'D8':
            check(provisional['outcome'] == 'AUTHENTICATED_VIEWER_OBSERVED' and not pre['stopped'] and
                  pre['failure'] is None and not pre['terminal_stopped'] and final['failure'] is not None,
                  'D8_FINALIZATION_WINDOW_NOT_EXERCISED')
    check(page.calls['goto'] == (0 if case == 'D7' else 1), case + '_NAVIGATION_COUNT')
    check(page.calls['login_actions'] == 0, case + '_LOGIN_ACTION')
    pending = [t for t in asyncio.all_tasks() if t not in baseline_tasks and not t.done()]
    check(not pending, case + '_ASYNC_TASKS_REMAIN')
    return {'status': 'PASS', 'exit_code': code, 'provisional_outcome': provisional['outcome'],
            'final_outcome': saved['outcome'], 'calls': page.calls, 'pre_shutdown': pre,
            'at_serialization': final, 'error': saved['error'], 'guard_failure': saved['guard_failure'],
            'context_close_calls': context.calls, 'runtime_stop_calls': runtime.calls,
            'observation_sha256': sha(raw), 'production_functions': ['NativeGuard', 'observe_page',
                'record_observation_error (if exception)', 'finalize_observation', 'close_owned', 'save_new']}

async def sequential_async(probe):
    for case in ORDER[2:]:
        if RESULT['first_unexpected_failure'] is not None:
            break
        RESULT['active_case'] = case
        try:
            RESULT['cases'][case] = await dom_case(probe, case)
        except BaseException as error:
            fail(case, error)
            break

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze-sha256', required=True)
    args = parser.parse_args()
    frozen_raw = (OUT / 'independent-freeze.json').read_bytes()
    check(sha(frozen_raw) == args.freeze_sha256, 'INDEPENDENT_FREEZE_BINDING')
    frozen = json.loads(frozen_raw)
    for item in frozen['frozen_output_inputs']:
        check(sha((OUT / item['path']).read_bytes()) == item['sha256'], 'FROZEN_REVIEW_INPUT_CHANGED')
    for item in frozen['fixed_product_inputs']:
        check(sha((ROOT / item['path']).read_bytes()) == item['sha256'], 'FROZEN_PRODUCT_INPUT_CHANGED')
    # This exact durable directory is created before the first behavior import.
    RUN.mkdir(exist_ok=False)
    started = time.monotonic()
    put('suite-started.json', {'at': utc(), 'thread_id': THREAD_ID, 'pid': os.getpid(),
        'freeze_sha256': args.freeze_sha256, 'case_order': ORDER, 'product_commit': PRODUCT_COMMIT,
        'final_commit': FINAL_COMMIT, 'independent_delta_limit': 1, 'protocol_child_limit': 1,
        'outer_seconds': 60, 'behavior_executions_before_this_intent': 0,
        'command': [sys.executable, '-B', str(Path(__file__).resolve()), '--freeze-sha256', args.freeze_sha256]})
    soft = threading.Timer(55, watchdog)
    hard = threading.Timer(60, lambda: None if DONE.is_set() else os._exit(124))
    soft.daemon = hard.daemon = True
    soft.start()
    hard.start()
    try:
        probe = load_product()  # First product behavior; quota is now consumed.
        for case, action in (('D1', d1), ('D2', d2)):
            RESULT['active_case'] = case
            try:
                RESULT['cases'][case] = action(probe)
            except BaseException as error:
                fail(case, error)
                break
        if RESULT['first_unexpected_failure'] is None:
            asyncio.run(asyncio.wait_for(sequential_async(probe), max(0.01, 50 - (time.monotonic() - started))))
    except BaseException as error:
        fail(RESULT['active_case'], error)
    finally:
        try:
            release_child()
        except BaseException as error:
            fail(RESULT['active_case'], error)
        RESULT['active_case'] = None
        RESULT['duration_ms'] = round((time.monotonic() - started) * 1000)
        RESULT['finished_at'] = utc()
        RESULT['freeze_sha256'] = args.freeze_sha256
        RESULT['protocol_child_release'] = CHILD_RELEASE
        RESULT['status'] = ('PASS_FINITE_OFFLINE_DELTA' if RESULT['first_unexpected_failure'] is None and
            all(v['status'] == 'PASS' for v in RESULT['cases'].values()) else 'REWORK')
        put('suite-result.json', RESULT)
        put('independent-release.json', {'at': utc(), 'state': CHILD_RELEASE['state'],
            'protocol_child': CHILD_RELEASE, 'real_browser_platform_profile_resources': 0,
            'fake_resources': {k: {'context_close_calls': v.get('context_close_calls'),
                                  'runtime_stop_calls': v.get('runtime_stop_calls')}
                               for k, v in RESULT['cases'].items() if k in ORDER[2:] and v['status'] == 'PASS'},
            'remaining_independent_delta_runs': 0, 'remaining_protocol_children': 0,
            'further_action': 'STOPPED_NO_RETRY_NO_LIVE'})
        DONE.set()
        soft.cancel()
        hard.cancel()
    print(json.dumps({'status': RESULT['status'], 'duration_ms': RESULT['duration_ms'],
                      'cases': {k: v['status'] for k, v in RESULT['cases'].items()},
                      'first_unexpected_failure': RESULT['first_unexpected_failure']}))
    return 0 if RESULT['status'] == 'PASS_FINITE_OFFLINE_DELTA' else 2

if __name__ == '__main__':
    raise SystemExit(main())
