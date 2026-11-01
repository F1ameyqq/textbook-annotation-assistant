"""Frozen author execution entry for an independently accepted source-only round.

No default profile, authority, plan, workspace or launch. The customer UI calls
the same acquisition function; this bounded entry only consumes a root-issued
one-shot authorization. It never prepares, recognizes, saves or exports.
"""
from pathlib import Path
import argparse,hashlib,json,sys
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]

def read(path): return json.loads(Path(path).read_bytes())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(test,message):
    if not test: raise ValueError(message)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--authority',required=True,type=Path);p.add_argument('--sha256',required=True)
    a=p.parse_args(argv)
    require(sha(a.authority)==a.sha256,'AUTHORITY_RAW_CHANGED')
    authority=read(a.authority)
    require(authority.get('schema')=='A30SourceAuthority/v1' and authority.get('activated') is True,'EXPLICIT_ACTIVATION_REQUIRED')
    require(authority.get('executor')=='01a16bf6-ed2d-7950-b2c9-9df30e7e6bd6','EXECUTOR_CHANGED')
    start=datetime.fromisoformat(authority['not_before']);end=datetime.fromisoformat(authority['expires_at'])
    require(start.tzinfo is not None and end.tzinfo is not None and 0<(end-start).total_seconds()<=900
            and start<=datetime.now(timezone.utc)<end,'AUTHORITY_WINDOW_INVALID')
    require(sha(authority['manifest_path'])==authority['manifest_sha256'],'FIXED_MANIFEST_CHANGED')
    manifest=read(authority['manifest_path'])
    require(manifest['scope']=='A30_SOURCE_ONLY','SOURCE_ONLY_MANIFEST_REQUIRED')
    declared=set()
    for row in manifest['source_files']:
        relative=Path(row['path']);path=(ROOT/relative).resolve()
        require(relative.as_posix() not in declared and path.is_relative_to(ROOT.resolve()),'INVALID_MANIFEST_PATH')
        declared.add(relative.as_posix());require(sha(path)==row['sha256'],'FIXED_SOURCE_CHANGED:'+relative.as_posix())
    actual={f.relative_to(ROOT).as_posix() for folder in ('src','tools') for f in (ROOT/folder).rglob('*.py')}
    require(actual.issubset(declared) and 'tools/customer_source_once.py' in declared,'UNDECLARED_EXECUTABLE_SOURCE')
    require(sha(authority['plan_path'])==authority['plan_sha256'] and sha(authority['settings_path'])==authority['settings_sha256'],'BOUND_INPUT_CHANGED')
    plan=read(authority['plan_path']);settings=read(authority['settings_path'])
    sys.path.insert(0,str(ROOT/'src'))
    from annotation.customer.platform_source import acquire,validate_plan
    from annotation.customer.store import Store,encoded
    from annotation.runtime.usense_live.core import profile_identity
    validate_plan(plan)
    require(authority['book_id']==plan['book_id'] and authority['directory_id']==plan['directory_id'],'AUTHORITY_TARGET_CHANGED')
    require(authority['limits']=={'api_gets':plan['maximum_api_gets'],'original_gets':plan['maximum_original_gets'],
        'contexts':1,'navigations':1,'ocr':0,'saves':0,'login':0,'retries':0},'AUTHORITY_LIMITS_CHANGED')
    _,fingerprint=profile_identity(settings['profile'])
    require(fingerprint==authority['profile_fingerprint'],'PROFILE_IDENTITY_CHANGED')
    require(settings['platform_enabled'] is True and settings['proxy_server'] is None and settings['tls_reference'], 'BOUND_DIRECT_SETTINGS_REQUIRED')
    workspace=Path(authority['workspace']).resolve()
    require(not workspace.is_relative_to(ROOT.resolve()),'OUTPUT_OUTSIDE_FIXED_PACKAGE_REQUIRED')
    workspace.mkdir(parents=True,exist_ok=True)
    # The authority intent is published before constructing Store or transport.
    with (workspace/'source-authority-used.json').open('xb') as f:
        f.write(encoded({'authority_path':str(a.authority.resolve()),'sha256':a.sha256,'spent':1,'remaining':0,
                         'at':datetime.now(timezone.utc).isoformat()}));f.flush()
        import os;os.fsync(f.fileno())
    settings={**settings,'authorization_reference':str(a.authority.resolve())+'#sha256='+a.sha256,'expires_at':authority['expires_at']}
    try:
        result=acquire(Store(workspace),settings,plan)
        value={'status':'SOURCE_ACQUIRED_ONLY','source':result,'model_calls':0,'save_attempts':0,'successors':'NOT_RUN'}
    except BaseException as exc:
        value={'status':'FAILED_NO_RETRY','type':type(exc).__name__,'message':str(exc),'successors':'NOT_RUN'}
        with (workspace/'source-round-result.json').open('xb') as f:f.write(encoded(value))
        raise
    with (workspace/'source-round-result.json').open('xb') as f:f.write(encoded(value))
    print(json.dumps({'status':value['status'],'result':str(workspace/'source-round-result.json')},ensure_ascii=False))
    return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'status':'STOPPED_NO_RETRY','type':type(exc).__name__,'message':str(exc)},ensure_ascii=False),file=sys.stderr)
        raise SystemExit(2)
