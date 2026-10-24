"""One authorized continuation of the frozen ordinary book/range preparation.

Copies the frozen prepared workspace, reuses raw OCR/source caches, calls the
same customer prepare_section function, and never calls production or login.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def require(test,message):
    if not test:raise ValueError(message)


def activated(authority):
    require(authority.get('schema')=='A30ContinuationPreparationAuthority/v1' and authority.get('activated') is True,'NEW_ACTIVATION_REQUIRED')
    require(authority.get('executor')=='01a16bf6-ed2d-7950-b2c9-9df30e7e6bd6','EXECUTOR_CHANGED')
    maximum=authority.get('maximum_additional_pages')
    require(type(maximum) is int and 1<=maximum<=4,'BOUNDED_ADDITIONAL_PAGES_REQUIRED')
    require(authority.get('limits')=={'api_gets':4*maximum,'original_gets':maximum,'contexts':maximum,
        'navigations':maximum,'new_ocr_pages':maximum,'saves':0,'login':0,'retries':0},'LIMITS_CHANGED')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--authority',required=True,type=Path);parser.add_argument('--sha256',required=True)
    args=parser.parse_args(argv);require(sha(args.authority)==args.sha256,'AUTHORITY_CHANGED');authority=read(args.authority);activated(authority)
    start,end=map(datetime.fromisoformat,(authority['not_before'],authority['expires_at']))
    require(start.tzinfo and end.tzinfo and 0<(end-start).total_seconds()<=900 and start<=datetime.now(timezone.utc)<end,'WINDOW_INVALID')
    require(sha(authority['manifest_path'])==authority['manifest_sha256'],'FIXED_MANIFEST_CHANGED')
    manifest=read(authority['manifest_path']);require(manifest['scope']=='A30_INTEGRATED_CUSTOMER_FLOW','INTEGRATED_MANIFEST_REQUIRED')
    declared=set()
    for row in manifest['source_files']:
        relative=Path(row['path']);path=(ROOT/relative).resolve()
        require(path.is_relative_to(ROOT.resolve()) and relative.as_posix() not in declared and sha(path)==row['sha256'],'FIXED_SOURCE_CHANGED')
        declared.add(relative.as_posix())
    actual={p.relative_to(ROOT).as_posix() for folder in ('src','tools') for p in (ROOT/folder).rglob('*.py')}
    require(actual<=declared and 'tools/customer_section_prepare_once.py' in declared,'UNDECLARED_EXECUTABLE_SOURCE')
    require(sha(authority['scope_path'])==authority['scope_sha256'],'NEXT_SCOPE_CHANGED')
    scope=read(authority['scope_path'])
    require(scope['book_id']==authority['book_id'] and scope['directory_id']==authority['directory_id']
        and scope['base_job']==authority['base_job'] and scope['base_head']==authority['base_head'],'TARGET_CHANGED')
    require(authority['maximum_additional_pages']<=scope['maximum_additional_pages'],'SCOPE_BUDGET_EXPANDED')
    source=Path(authority['input_workspace']).resolve();output=Path(authority['workspace']).resolve()
    require(not output.exists() and not output.is_relative_to(ROOT.parent.resolve()) and not source.is_relative_to(output),'FRESH_EXTERNAL_WORKSPACE_REQUIRED')
    bound={Path(row['path']).resolve():row for row in manifest['evidence']}
    files=[p for p in source.rglob('*') if p.is_file()]
    require(files and all(p.resolve() in bound and sha(p)==bound[p.resolve()]['sha256'] for p in files),'INPUT_WORKSPACE_NOT_FROZEN')
    settings=read(source/'settings.json');require(settings.get('platform_enabled') is True and settings.get('proxy_server') is None and settings.get('tls_reference'),'ORIGINAL_DIRECT_SETTINGS_REQUIRED')
    profile=Path(settings['profile']).resolve();require(not output.is_relative_to(profile) and not profile.is_relative_to(output),'PROFILE_OUTPUT_OVERLAP')
    sys.path.insert(0,str(ROOT/'src'))
    from annotation.customer.store import Store,encoded
    from annotation.runtime.usense_live.core import profile_identity
    _,fingerprint=profile_identity(settings['profile']);require(fingerprint==authority['profile_fingerprint'],'PROFILE_IDENTITY_CHANGED')
    marker=Path(authority['consumption_path']).resolve();require(not marker.is_relative_to(ROOT.parent.resolve()) and not marker.is_relative_to(profile),'CONSUMPTION_LOCATION_INVALID')
    with marker.open('xb') as stream:
        stream.write(encoded({'authority_id':authority['authority_id'],'authority_sha256':args.sha256,'spent':1,'remaining':0,'at':datetime.now(timezone.utc).isoformat()}));stream.flush();os.fsync(stream.fileno())
    output.mkdir(parents=True,exist_ok=False)
    for path in files:
        target=output/path.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);require(sha(target)==sha(path),'WORKSPACE_COPY_CHANGED')
    store=Store(output);job,head=store.job(authority['base_job']);require(head==authority['base_head'],'BASE_HEAD_CHANGED')
    require(job['book_id']==authority['book_id'] and job['platform_status']=='NOT_RUN' and job['metrics']['review_actions']==0,'UNREVIEWED_UNSENT_PREPARATION_REQUIRED')
    from annotation.customer.recognition_cache import cached_page
    unused={p['asset_id'] for p in job.get('unused_source_pages',[])}
    for page in job['pages']:
        if page['asset_id'] not in unused:require(cached_page(store,page,job['book_id']) is not None,'OLD_PAGE_CACHE_REQUIRED_NO_REPLAY')
    settings={**settings,'authorization_reference':str(args.authority.resolve())+'#sha256='+args.sha256,'expires_at':authority['expires_at']}
    (output/'settings.json').write_bytes(encoded(settings))
    value=store.get(job['platform_source_ref']);require(value['plan']['directory_id']==authority['directory_id'],'DIRECTORY_CHANGED')
    with store.connect() as db:before={key for (key,) in db.execute("SELECT key FROM operations WHERE kind='recognition'")}
    try:
        from annotation.customer.platform_source import prepare_section
        result=prepare_section(store,settings,value,allow_local_ocr=True,maximum_additional_pages=authority['maximum_additional_pages'])
        with store.connect() as db:new=[{'key':key,'state':state,'output':ref} for key,state,ref in db.execute("SELECT key,state,output FROM operations WHERE kind='recognition'") if key not in before]
        require(len(new)<=authority['limits']['new_ocr_pages'],'MODEL_BUDGET_EXCEEDED')
        summary={'schema':'A30ContinuationPreparationResult/v1','status':result['status'],'job_id':result['id'],
            'source_scope_complete':result.get('source_scope_complete',False),'observed_question_count':len(result['candidates']),
            'remaining_source_roles':result.get('remaining_source_roles'),'source_discovery':result.get('source_discovery'),
            'new_ocr_operations':new,'save_attempts':0,'old_success_resaves':0,'spent':1,'remaining':0,
            'successors':'NOT_RUN','workspace':str(output)}
    except BaseException as exc:
        summary={'schema':'A30ContinuationPreparationResult/v1','status':'FAILED_NO_RETRY','type':type(exc).__name__,'message':str(exc),
            'successors':'NOT_RUN','spent':1,'remaining':0,'workspace':str(output)}
        with (output/'continuation-round-result.json').open('xb') as stream:stream.write(encoded(summary))
        raise
    with (output/'continuation-round-result.json').open('xb') as stream:stream.write(encoded(summary))
    print(json.dumps(summary,ensure_ascii=False));return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'status':'STOPPED_NO_RETRY','type':type(exc).__name__,'message':str(exc)},ensure_ascii=False),file=sys.stderr);raise SystemExit(2)
