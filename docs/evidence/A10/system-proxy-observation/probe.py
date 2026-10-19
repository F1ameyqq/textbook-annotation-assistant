"""Frozen explicit-system-proxy observation after new user context. No default run."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
TARGET = 'https://www.usense.com/qieti/annotateUnified'
WORKFLOW = '9ff37e3f3084df7272ab671b56e4f4c235346e57'
TYPES = {'Error', 'TimeoutError', 'OSError', 'TypeError', 'ValueError', 'ImportError', 'ModuleNotFoundError'}
CODES = (
    'ENOTFOUND', 'EAI_AGAIN', 'ECONNREFUSED', 'ECONNRESET', 'ETIMEDOUT',
    'ENETUNREACH', 'EHOSTUNREACH', 'ERR_NAME_NOT_RESOLVED',
    'ERR_PROXY_CONNECTION_FAILED', 'ERR_TUNNEL_CONNECTION_FAILED',
    'ERR_CERT_AUTHORITY_INVALID', 'ERR_CERT_COMMON_NAME_INVALID',
    'ERR_CERT_DATE_INVALID', 'ERR_TLS_CERT_ALTNAME_INVALID', 'CERT_HAS_EXPIRED',
    'UNABLE_TO_VERIFY_LEAF_SIGNATURE', 'UNABLE_TO_GET_ISSUER_CERT_LOCALLY',
    'DEPTH_ZERO_SELF_SIGNED_CERT', 'SELF_SIGNED_CERT_IN_CHAIN',
)
PHRASES = (
    ('unable to verify the first certificate', 'TLS_CHAIN_UNVERIFIED'),
    ('unable to get local issuer certificate', 'TLS_ISSUER_UNAVAILABLE'),
    ('self-signed certificate', 'TLS_SELF_SIGNED'),
)


def utc():
    return datetime.now(timezone.utc).isoformat()


def save_new(name, value):
    # Every runtime artifact is append-only/one-shot, never an old evidence edit.
    data = (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('utf-8')
    with (HERE / name).open('xb') as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())


def safe_error(error):
    kind = type(error).__name__
    kind = kind if kind in TYPES else 'OTHER'
    try:
        detail = str(error)
        found = [code for code in CODES if re.search(r'(?<![A-Z0-9_])' + re.escape(code) + r'(?![A-Z0-9_])', detail)]
        lower = detail.lower()
        found += [code for phrase, code in PHRASES if phrase in lower]
    except Exception:
        found = []
    return {'exception_type': kind, 'codes': found[:4] or ['UNKNOWN']}


def worker():
    # No Playwright import/start, network, or child creation before the Job gate.
    if sys.stdin.readline() != 'GO\n':
        return 71
    runtime = context = None
    stage = 'START_RUNTIME'
    calls = 0
    outcome = None
    sealed = False
    cleanup = {'context_disposed': False, 'runtime_stopped': False, 'errors': []}
    try:
        from playwright.sync_api import sync_playwright
        runtime = sync_playwright().start()
        stage = 'NEW_REQUEST_CONTEXT'
        # Revalidate only the specific non-secret system-proxy facts before GET.
        # No PAC evaluation, credentials, browser/profile or system mutation.
        import winreg
        stage = 'VERIFY_SYSTEM_PROXY'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
            def setting(name):
                try:
                    return winreg.QueryValueEx(key, name)[0]
                except FileNotFoundError:
                    return None
            if setting('ProxyEnable') != 1 or setting('AutoConfigURL'):
                raise ValueError()
            if setting('ProxyServer') not in (
                '127.0.0.1:7897', 'http://127.0.0.1:7897',
                'localhost:7897', 'http://localhost:7897',
            ):
                raise ValueError()
        stage = 'NEW_REQUEST_CONTEXT'
        context = runtime.request.new_context(
            ignore_https_errors=False, timeout=30000,
            proxy={'server': 'http://127.0.0.1:7897'})
        stage = 'GET'
        # Durable invocation intent: at most one GET call; this is not a wire count.
        save_new('get-started.json', {'stage': stage, 'get_invocations_reserved': 1, 'utc': utc()})
        calls = 1
        response = context.get(TARGET, timeout=30000, ignore_https_errors=False,
                               max_redirects=0, max_retries=0, fail_on_status_code=False)
        status = response.status
        if type(status) is not int or not 100 <= status <= 599:
            raise ValueError()
        outcome = {'stage': stage, 'exception_type': None, 'codes': [], 'http_status': status}
    except Exception as error:
        outcome = {'stage': stage, **safe_error(error), 'http_status': None}
    finally:
        # Seal first HTTP outcome/error before any cleanup; never replace it.
        if outcome is not None:
            outcome.update({'get_invocations_reserved': calls, 'utc': utc()})
            try:
                save_new('first-outcome.json', outcome)
                sealed = True
            except Exception:
                cleanup['errors'].append({'stage': 'SEAL_FIRST_OUTCOME', 'exception_type': 'OTHER', 'codes': ['UNKNOWN']})
        if context is not None:
            try:
                context.dispose()
                cleanup['context_disposed'] = True
            except Exception as error:
                cleanup['errors'].append({'stage': 'DISPOSE', **safe_error(error)})
        if runtime is not None:
            try:
                runtime.stop()
                cleanup['runtime_stopped'] = True
            except Exception as error:
                cleanup['errors'].append({'stage': 'STOP_RUNTIME', **safe_error(error)})
        cleanup['context_created'] = context is not None
        cleanup['runtime_created'] = runtime is not None
        save_new('worker-release.json', cleanup)
    return 0 if sealed and outcome and outcome['http_status'] is not None and not cleanup['errors'] else 70


def verify_inputs(expected_hash):
    raw = (HERE / 'candidate-raw-manifest.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError()
    manifest = json.loads(raw)
    if manifest['workflow'] != WORKFLOW:
        raise ValueError()
    if set(manifest['files']) != {'probe.py', 'owned_job.py', 'input-bindings.json', 'preparation-report.md', 'static-check.json'}:
        raise ValueError()
    for name, record in manifest['files'].items():
        if Path(name).name != name:
            raise ValueError()
        data = (HERE / name).read_bytes()
        if len(data) != record['size'] or hashlib.sha256(data).hexdigest() != record['sha256']:
            raise ValueError()
    bindings = json.loads((HERE / 'input-bindings.json').read_bytes())
    if sys.executable != bindings['python_executable']:
        raise ValueError()
    from importlib.metadata import version
    if version('playwright') != bindings['playwright_version']:
        raise ValueError()
    for record in bindings['local_dependency_sources']:
        data = Path(record['path']).read_bytes()
        if len(data) != record['size'] or hashlib.sha256(data).hexdigest() != record['sha256']:
            raise ValueError()


def supervise(candidate, manifest_hash):
    started = time.monotonic()
    # No OS/native/network setup occurs until source hashes and once-marker pass.
    verify_inputs(manifest_hash)
    save_new('run-once-marker.json', {'stage': 'START', 'utc': utc(), 'candidate_commit': candidate,
                                     'workflow': WORKFLOW, 'candidate_manifest_sha256': manifest_hash,
                                     'maximum_get_invocations': 1})
    record = {'stage': 'OWNED_JOB_SETUP', 'utc': utc(), 'owned_identity': None,
              'job_assigned': False, 'gate_sent': False, 'worker_exit_observed': False,
              'job_active_zero_observed': False, 'stdin_closed': False,
              'process_handle_closed': False, 'job_handle_closed': False,
              'termination_requested': False, 'errors': []}
    record['worker_exit_code'] = None
    child = job = None
    try:
        if os.name != 'nt' or not Path(r'C:\Windows').is_dir():
            raise OSError()
        from owned_job import OwnedJob
        job = OwnedJob()
        job.create()
        # Fixed child environment: no read/copy of ambient values, proxy or secrets.
        child = subprocess.Popen([sys.executable, '-I', '-B', str(HERE / 'probe.py'), '--worker'],
                                 stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 cwd=str(HERE), creationflags=subprocess.CREATE_NO_WINDOW,
                                 env={'SystemRoot': r'C:\Windows', 'WINDIR': r'C:\Windows',
                                      'NODE_TLS_REJECT_UNAUTHORIZED': '1', 'PYTHONIOENCODING': 'utf-8'})
        record['owned_identity'] = job.identity(child)
        job.assign(child)
        record['job_assigned'] = True
        if time.monotonic() - started >= 10:
            raise TimeoutError()
        child.stdin.write(b'GO\n')
        child.stdin.flush()
        record['gate_sent'] = True
        child.stdin.close()
        record['stdin_closed'] = True
        record['stage'] = 'WAIT_WORKER'
        while time.monotonic() - started < 50:
            if job.exited(child):
                record['worker_exit_observed'] = True
                break
            time.sleep(0.05)
        if not record['worker_exit_observed']:
            raise TimeoutError()
    except Exception as error:
        record['errors'].append({'stage': record['stage'], **safe_error(error)})
    finally:
        record['stage'] = 'OWNED_RELEASE'
        if child is not None and job is not None:
            try:
                record['worker_exit_observed'] = job.exited(child)
                active = job.active_count() if record['job_assigned'] else 0
                if not record['worker_exit_observed'] or active:
                    job.terminate(child, record['job_assigned'])
                    record['termination_requested'] = True
                while time.monotonic() - started < 57:
                    record['worker_exit_observed'] = job.exited(child)
                    active = job.active_count() if record['job_assigned'] else 0
                    if record['worker_exit_observed'] and active == 0:
                        record['job_active_zero_observed'] = True
                        record['worker_exit_code'] = job.exit_code(child)
                        break
                    time.sleep(0.05)
            except Exception as error:
                record['errors'].append({'stage': 'OWNED_RELEASE', **safe_error(error)})
        # Each close is independent; unknown exit is never overwritten by close success.
        if child is not None:
            try:
                if not record['stdin_closed']:
                    child.stdin.close()
                    record['stdin_closed'] = True
            except Exception as error:
                record['errors'].append({'stage': 'CLOSE_STDIN', **safe_error(error)})
        if job is not None:
            try:
                job.close()
                record['job_handle_closed'] = job.handle is None
            except Exception as error:
                record['errors'].append({'stage': 'CLOSE_JOB_HANDLE', **safe_error(error)})
        if child is not None:
            try:
                child._handle.Close()
                record['process_handle_closed'] = True
                child._child_created = False  # No destructor polling after this original handle is closed.
            except Exception as error:
                record['errors'].append({'stage': 'CLOSE_PROCESS_HANDLE', **safe_error(error)})
        record['elapsed_seconds'] = round(time.monotonic() - started, 3)
        record['within_60_seconds'] = record['elapsed_seconds'] <= 60
        record['cleanup_proven'] = bool(child is not None and record['worker_exit_observed']
                                       and record['job_active_zero_observed'] and record['stdin_closed']
                                       and record['process_handle_closed'] and record['job_handle_closed']
                                       and record['within_60_seconds'])
        record['get_invocations_reserved'] = int((HERE / 'get-started.json').exists())
        record['first_outcome_sealed'] = (HERE / 'first-outcome.json').exists()
        save_new('supervisor-release.json', record)
    return 0 if (record['cleanup_proven'] and record['first_outcome_sealed']
                 and record['worker_exit_code'] == 0 and not record['errors']) else 72


def main():
    # No default run; coordinator must first review the frozen commit and signal.
    if sys.argv[1:] == ['--worker']:
        return worker()
    if (len(sys.argv) == 4 and sys.argv[1] == '--run-once-after-coordinator-review'
            and re.fullmatch(r'[0-9a-f]{40}', sys.argv[2])
            and re.fullmatch(r'[0-9a-f]{64}', sys.argv[3])):
        return supervise(sys.argv[2], sys.argv[3])
    return 64


if __name__ == '__main__':
    try:
        code = main()
    except BaseException:
        # Never print tracebacks or free text, including setup/persistence errors.
        code = 73
    sys.exit(code)
