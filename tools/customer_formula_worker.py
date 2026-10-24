"""One pinned local formula-ROI invocation; no fallback, network or retry."""
from pathlib import Path
from contextlib import contextmanager
import argparse
import hashlib
import io
import json
import math
import platform
import socket
import sys
import time

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP/'src'))
WORKER_STATE={'phase':'SOURCE_AND_RUNTIME_VALIDATION','model_initialization':'NOT_RUN',
              'engine_calls_started':0,'engine_calls_completed':0}


class LocalOnlyGuard:
    def __init__(self,state):
        self.state=state
        self.record={'blocked_attempts':0,'blocked_events':[],'local_hostname_reads':0,
                     'ipv6_import_probe':'NOT_ENTERED'}
    def audit(self,event,arguments):
        # gethostname reads the local computer name; it does not create a
        # socket, resolve a destination or connect. Never retain its value.
        if event=='socket.gethostname':
            self.record['local_hostname_reads']+=1
            return
        if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.posix_spawn'}:
            self.record['blocked_attempts']+=1
            if len(self.record['blocked_events'])<16:
                self.record['blocked_events'].append({'event':event,'phase':self.state['phase']})
            raise RuntimeError('FORMULA_WORKER_NETWORK_OR_CHILD_PROCESS_FORBIDDEN')
    def require_clean(self):
        if self.record['blocked_attempts']:
            raise RuntimeError('FORMULA_WORKER_BLOCKED_ATTEMPT_RETAINED')
    @contextmanager
    def local_imports(self):
        # urllib3 otherwise probes an IPv6 bind while importing requests.
        # Disable only that feature probe in this owned process. The audit
        # guard still denies every socket creation/bind/connect/DNS call.
        previous=socket.has_ipv6;socket.has_ipv6=False
        previous_ver=None
        if sys.platform=='win32':
            previous_ver=platform._syscmd_ver
            # Python 3.11 win32_ver normally launches `ver` first. Its built-in
            # fallback uses sys.getwindowsversion when no shell text is present.
            # Select that existing fallback, without permitting a child process.
            def no_shell_ver(system='',release='',version='',supported_platforms=('win32','win16','dos')):
                return system,release,version
            platform._syscmd_ver=no_shell_ver
            self.record['windows_version_probe']='BUILTIN_FALLBACK_DURING_LOCAL_BACKEND_IMPORT'
        self.record['ipv6_import_probe']='DISABLED_DURING_LOCAL_BACKEND_IMPORT'
        try:yield
        finally:
            socket.has_ipv6=previous
            self.record['ipv6_flag_restored']=socket.has_ipv6==previous
            if previous_ver is not None:
                platform._syscmd_ver=previous_ver
                self.record['windows_version_function_restored']=platform._syscmd_ver is previous_ver


def failure_record(exc):
    return {'schema':'CustomerFormulaWorkerFailure/v1','status':'FAILED_NO_RETRY',
            'type':type(exc).__name__,'message':str(exc),**WORKER_STATE}


def main():
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--sha256',required=True)
    parser.add_argument('--validate-only',action='store_true')
    args=parser.parse_args()
    from annotation.customer.store import byte_hash
    from annotation.customer.formula_roi_cache import build_request,digest
    from annotation.customer.formula_runtime import local_identity
    raw=args.input.read_bytes()
    if byte_hash(raw)!=args.sha256:raise ValueError('WORKER_INPUT_CHANGED')
    envelope=json.loads(raw);request=envelope['request']
    if envelope['schema']!='CustomerFormulaWorkerInput/v1':raise ValueError('WORKER_INPUT_SCHEMA')
    if Path(sys.executable).resolve()!=Path(envelope['python_executable']).resolve():raise ValueError('WRONG_FORMULA_RUNTIME')
    model,python,model_dir=local_identity({'runtime':{'formula_python':sys.executable,'formula_models':envelope['model_directory']}})
    if model!=request['model_identity']:raise ValueError('MODEL_RUNTIME_OR_CODE_CHANGED')
    from PIL import Image
    source=request['source'];original_raw=Path(envelope['source_path']).read_bytes();roi_raw=Path(envelope['roi_path']).read_bytes()
    if byte_hash(original_raw)!=source['sha256']:raise ValueError('ORIGINAL_SOURCE_CHANGED')
    with Image.open(io.BytesIO(original_raw)) as original:
        if original.size!=(source['width'],source['height']):raise ValueError('ORIGINAL_SIZE_CHANGED')
        exact=original.convert('RGB').crop(tuple(request['roi_identity']['source_bbox']))
        with Image.open(io.BytesIO(roi_raw)) as retained:
            if retained.format!='PNG' or retained.convert('RGB').tobytes()!=exact.tobytes() or retained.size!=exact.size:
                raise ValueError('ROI_IS_NOT_EXACT_ORIGINAL_CROP')
    rebuilt=build_request(source,request['roi_identity']['source_bbox'],roi_raw,exact.tobytes(),model)
    if rebuilt!=request:raise ValueError('ROI_REQUEST_BINDING_CHANGED')
    if args.validate_only:
        print(json.dumps({'status':'LOCAL_SOURCE_ROI_RUNTIME_VERIFIED','roi_key':request['roi_key'],'engine_calls':0,'model_initialization':'NOT_RUN'}));return
    guard=LocalOnlyGuard(WORKER_STATE);WORKER_STATE['network']=guard.record
    sys.addaudithook(guard.audit)
    WORKER_STATE['phase']='LOCAL_BACKEND_IMPORT'
    with guard.local_imports():
        from annotation.recognition.formula_backend import _local_cpu_backend
        from rapid_latex_ocr import LaTeXOCR  # Import only; constructor below.
        import numpy as np
    guard.require_clean()
    WORKER_STATE.update(phase='MODEL_INITIALIZATION',model_initialization='STARTED_NOT_CONFIRMED_COMPLETE')
    started=time.perf_counter();engine,backend=_local_cpu_backend(model_dir)
    WORKER_STATE['model_initialization']='COMPLETE';guard.require_clean()
    # Exactly one backend invocation for the retained, unpadded RGB crop.
    WORKER_STATE.update(phase='INFERENCE',engine_calls_started=1)
    latex,elapsed=engine(np.asarray(exact))
    WORKER_STATE['engine_calls_completed']=1
    if type(latex) is not str or not latex.strip() or type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0:
        raise ValueError('INVALID_OR_EMPTY_FORMULA_OBSERVATION')
    guard.require_clean();WORKER_STATE['phase']='OBSERVATION_COMPLETE'
    print(json.dumps({'schema':'CustomerFormulaROIObservation/v1','roi_key':request['roi_key'],
        'cache_key':request['cache_key'],'model_identity_sha256':digest(model),'source_verified':True,'roi_verified':True,
        'owned_os_release_confirmed':False,'recognition_error':None,'engine_calls':1,'execution_kind':'LOCAL_CPU_FORMULA_ROI',
        'raw_latex':latex,'raw_latex_definition':'Unchanged return value from the pinned backend; no manual normalization.',
        'backend_elapsed_seconds':elapsed,'worker_elapsed_seconds':time.perf_counter()-started,'backend':backend,
        'network':guard.record,'phase':WORKER_STATE['phase'],'model_initialization':WORKER_STATE['model_initialization'],
        'content_approved':False,'alternate_variants':0},ensure_ascii=False))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps(failure_record(exc),ensure_ascii=False),file=sys.stderr)
        raise SystemExit(2)
