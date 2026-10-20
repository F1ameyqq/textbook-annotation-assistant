"""A14 single strict TLS diagnostic. Raw streams remain private. No retries."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
import winreg

PUBLIC = Path('D:/1800-worktrees/a14-tls-diagnostic/execution-output')
PRIVATE = Path('D:/1800/.local/stages/a14-tls-diagnostic')
THREAD_ID = '01a157e6-628a-75d2-b685-6cb98e5fb0af'
REG_PATH = r'Software\Microsoft\Windows\CurrentVersion\Internet Settings'
K32 = ctypes.WinDLL('kernel32', use_last_error=True)
K32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
K32.GetProcessTimes.restype = wintypes.BOOL
K32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
K32.WaitForSingleObject.restype = wintypes.DWORD
K32.GetHandleInformation.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
K32.GetHandleInformation.restype = wintypes.BOOL

def utc():
    return datetime.now(timezone.utc).isoformat()

def digest(path):
    data = Path(path).read_bytes()
    return {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(path, data):
    with Path(path).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

def proxy_metadata():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
        def val(name, default):
            try:
                return winreg.QueryValueEx(key, name)[0]
            except FileNotFoundError:
                return default
        enabled, server, pac = val('ProxyEnable', 0), val('ProxyServer', ''), val('AutoConfigURL', '')
    if enabled != 1 or not isinstance(server, str) or not isinstance(pac, str) or pac.strip():
        raise ValueError('PROXY_DISABLED_OR_PAC_OR_INVALID_TYPE')
    if not server or '@' in server or any(c.isspace() for c in server):
        raise ValueError('PROXY_AUTH_OR_WHITESPACE_OR_EMPTY')
    if '=' in server:
        items = server.split(';')
        mapping = {}
        for item in items:
            if item.count('=') != 1:
                raise ValueError('PROXY_PROTOCOL_AMBIGUITY')
            protocol, endpoint = item.split('=')
            if protocol not in ('http', 'https', 'ftp', 'socks') or protocol in mapping:
                raise ValueError('PROXY_PROTOCOL_AMBIGUITY')
            mapping[protocol] = endpoint
        if 'https' not in mapping:
            raise ValueError('PROXY_HTTPS_MISSING')
        endpoint, kind = mapping['https'], 'per-protocol-explicit-https'
    else:
        endpoint, kind = server, 'windows-single-fixed-http-proxy'
    m = re.fullmatch(r'(127\.0\.0\.1|localhost|\[::1\]):([0-9]{1,5})', endpoint, flags=re.I)
    if not m or not 1 <= int(m.group(2)) <= 65535:
        raise ValueError('PROXY_NOT_EXACT_LOOPBACK_OR_INVALID_PORT')
    host, port = m.group(1).lower(), int(m.group(2))
    return {'enabled': True, 'pac_present': False, 'authentication_syntax_present': False,
            'kind': kind, 'host': host, 'port': port, 'endpoint': host + ':' + str(port),
            'proxy_server_sha256': hashlib.sha256(server.encode('utf-8')).hexdigest(),
            'registry_path_sha256': hashlib.sha256(('HKCU/' + REG_PATH).encode('utf-8')).hexdigest()}

def safe_env():
    env = {k: os.environ[k] for k in ('SystemRoot', 'WINDIR', 'SystemDrive', 'TEMP', 'TMP') if k in os.environ}
    env['PATH'] = 'C:/Program Files/Git/mingw64/bin;' + os.environ.get('SystemRoot', 'C:/Windows') + '/System32'
    return env

def times(handle):
    values = [wintypes.FILETIME() for _ in range(4)]
    if not K32.GetProcessTimes(wintypes.HANDLE(int(handle)), *[ctypes.byref(v) for v in values]):
        return {'status': 'UNKNOWN', 'winerror': ctypes.get_last_error()}
    nums = [(v.dwHighDateTime << 32) | v.dwLowDateTime for v in values]
    return {'status': 'OBSERVED_EXACT_RETAINED_HANDLE', 'creation_filetime': nums[0],
            'exit_filetime': nums[1], 'kernel_100ns': nums[2], 'user_100ns': nums[3]}

def invalid_handle(handle):
    flags = wintypes.DWORD()
    ctypes.set_last_error(0)
    ok = K32.GetHandleInformation(wintypes.HANDLE(int(handle)), ctypes.byref(flags))
    err = ctypes.get_last_error()
    return {'valid': bool(ok), 'winerror': err, 'invalid_handle_confirmed': not ok and err == 6}

def main():
    start = float(sys.argv[1])
    deadline = start + 22.0
    wait_cutoff = start + 20.0
    intent = json.loads((PUBLIC / 'launch-intent.json').read_text(encoding='utf-8'))
    save(PRIVATE / 'wrapper-claim.json', {'at': utc(), 'thread_id': THREAD_ID, 'pid': os.getpid(),
                                        'intent_sha256': digest(PUBLIC / 'launch-intent.json')['sha256']})
    result = {'status': 'BLOCKED', 'started_utc': utc(), 'thread_id': THREAD_ID,
              'tls_process_launches': 0, 'tls_handshake_intents': 0, 'target_http_requests': 0,
              'stdin_bytes_written': 0, 'browser_profile_login_business_actions': 0,
              'timeout': False, 'first_failure': None, 'successors': 'NOT_RUN',
              'elapsed_ms_at_release': None, 'signals': [], 'streams': {}, 'release': {}}
    p = None
    threads = []
    signal = threading.Event()
    lock = threading.Lock()
    handles = {}
    try:
        for path, expected in intent['bindings'].items():
            if digest(path) != expected:
                raise ValueError('FROZEN_BINDING_MISMATCH')
        if proxy_metadata() != intent['proxy']:
            raise ValueError('FROZEN_PROXY_METADATA_MISMATCH')
        if time.perf_counter() >= wait_cutoff:
            raise ValueError('PRELAUNCH_BUDGET_EXHAUSTED')
        argv = intent['tls_argv']
        expected_argv = [intent['openssl_path'], 's_client', '-connect', 'www.usense.com:443',
                         '-servername', 'www.usense.com', '-verify_hostname', 'www.usense.com',
                         '-verify_return_error', '-showcerts', '-prexit', '-CAfile', intent['ca_path'],
                         '-proxy', intent['proxy']['endpoint'], '-no_ign_eof']
        if argv != expected_argv or intent['thread_id'] != THREAD_ID:
            raise ValueError('FROZEN_COMMAND_OR_ID_MISMATCH')
        for name in ('stdout', 'stderr'):
            if (PRIVATE / ('s_client.' + name + '.bin')).exists():
                raise ValueError('RAW_OUTPUT_ALREADY_EXISTS')
        result['tls_handshake_intents'] = 1
        result['launch_utc'] = utc()
        result['launch_elapsed_ms'] = round((time.perf_counter() - start) * 1000, 3)
        p = subprocess.Popen(argv, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, bufsize=0, close_fds=True, env=safe_env(),
                             cwd=str(PRIVATE), creationflags=subprocess.CREATE_NO_WINDOW)
        result['tls_process_launches'] = 1
        result['pid'] = p.pid
        result['process_creation'] = times(p._handle)
        result['process_handle'] = int(p._handle)
        for name in ('stdin', 'stdout', 'stderr'):
            handles[name] = msvcrt.get_osfhandle(getattr(p, name).fileno())
        def drain(name):
            src = getattr(p, name)
            info = {'bytes': 0, 'sha256': None, 'eof_observed': False, 'file_closed': False,
                    'reader_error_type': None}
            h = hashlib.sha256()
            tail = b''
            try:
                with (PRIVATE / ('s_client.' + name + '.bin')).open('xb') as sink:
                    while True:
                        chunk = os.read(src.fileno(), 8192)
                        if not chunk:
                            info['eof_observed'] = True
                            break
                        sink.write(chunk)
                        h.update(chunk)
                        info['bytes'] += len(chunk)
                        scan = tail + chunk
                        category = None
                        if re.search(rb'verify error:num=\d+', scan) or b'certificate verify failed' in scan.lower():
                            category = 'EXPLICIT_CERTIFICATE_VERIFICATION_FAILURE'
                        elif re.search(rb'SSL handshake has read \d+ bytes and written \d+ bytes', scan):
                            category = 'HANDSHAKE_SUMMARY_OBSERVED'
                        elif b'CONNECTION ESTABLISHED' in scan:
                            category = 'CONNECTION_ESTABLISHED_OBSERVED'
                        if category:
                            with lock:
                                if not result['signals']:
                                    result['signals'].append({'stream': name, 'category': category,
                                                             'elapsed_ms': round((time.perf_counter() - start) * 1000, 3)})
                            signal.set()
                        tail = scan[-512:]
                info['file_closed'] = sink.closed
            except Exception as e:
                info['reader_error_type'] = type(e).__name__
                signal.set()
            finally:
                info['sha256'] = h.hexdigest()
                result['streams'][name] = info
        for name in ('stdout', 'stderr'):
            t = threading.Thread(target=drain, args=(name,), daemon=True)
            t.start()
            threads.append(t)
        eof_reason = None
        while p.poll() is None and time.perf_counter() < wait_cutoff:
            if signal.is_set() and not p.stdin.closed:
                p.stdin.close()
                eof_reason = 'EXPLICIT_RESULT_OR_READER_ERROR'
                result['stdin_eof_elapsed_ms'] = round((time.perf_counter() - start) * 1000, 3)
            time.sleep(min(0.01, max(0, wait_cutoff - time.perf_counter())))
        if not p.stdin.closed:
            p.stdin.close()
            eof_reason = 'CHILD_EXIT' if p.poll() is not None else 'FIXED_20_SECOND_CUTOFF'
            result['stdin_eof_elapsed_ms'] = round((time.perf_counter() - start) * 1000, 3)
        result['stdin_eof_reason'] = eof_reason
        if p.poll() is None:
            result['timeout'] = True
            result['first_failure'] = 'TLS_PROCESS_DID_NOT_EXIT_BEFORE_FIXED_20_SECOND_CUTOFF'
            p.kill()
            result['exact_handle_kill_issued'] = True
        p.wait(timeout=max(0, deadline - time.perf_counter() - 0.15))
        result['exit_code'] = p.returncode
        result['process_exit'] = times(p._handle)
        result['wait_signaled'] = K32.WaitForSingleObject(wintypes.HANDLE(int(p._handle)), 0) == 0
        for t in threads:
            t.join(timeout=max(0, deadline - time.perf_counter() - 0.15))
        result['readers_joined'] = all(not t.is_alive() for t in threads)
        if not result['readers_joined']:
            result['first_failure'] = result['first_failure'] or 'PIPE_READER_NOT_JOINED_WITHIN_TOTAL_BUDGET'
        result['status'] = 'REVIEW'
    except Exception as e:
        result['first_failure'] = result['first_failure'] or type(e).__name__ + ':' + str(e) if isinstance(e, ValueError) else result['first_failure'] or type(e).__name__
    finally:
        if p is not None:
            if not p.stdin.closed:
                p.stdin.close()
            if p.poll() is None and time.perf_counter() < deadline:
                p.kill()
                result['exact_handle_kill_issued'] = True
                try:
                    p.wait(timeout=max(0, deadline - time.perf_counter() - 0.1))
                except subprocess.TimeoutExpired:
                    pass
            result['exit_code'] = p.poll()
            result['process_exit'] = times(p._handle)
            result['wait_signaled'] = K32.WaitForSingleObject(wintypes.HANDLE(int(p._handle)), 0) == 0
            for t in threads:
                t.join(timeout=max(0, deadline - time.perf_counter() - 0.1))
            result['readers_joined'] = all(not t.is_alive() for t in threads)
            for name in ('stdin', 'stdout', 'stderr'):
                pipe = getattr(p, name)
                pipe.close()
                result['release'][name] = {'closed': pipe.closed, 'handle': handles[name],
                                           'post_close': invalid_handle(handles[name])}
            ph = int(p._handle)
            p._handle.Close()
            result['release']['process_handle'] = {'handle': ph, 'close_called': True,
                                                    'post_close': invalid_handle(ph)}
        else:
            result['release']['process'] = 'NOT_CREATED'
        result['elapsed_ms_at_release'] = round((time.perf_counter() - start) * 1000, 3)
        result['within_total_22_seconds'] = time.perf_counter() <= deadline
        result['finished_utc'] = utc()
        save(PUBLIC / 'process-result.json', result)
    return 0 if result['status'] == 'REVIEW' else 2

if __name__ == '__main__':
    sys.exit(main())
