"""Reconcile actual frozen author processes and current owned process/import records."""
from pathlib import Path
import json
from evidence import OUT,WORK,EV,TARGET,BASE,INDEX,MAP,load,raw,document,author_key,sha,write
root=Path(load(OUT/'independent-run.json')['run_root']).resolve()
CRLF={'src/annotation/__init__.py','src/annotation/contracts/__main__.py','src/annotation/contracts/cli.py','src/annotation/contracts/integrity.py','src/annotation/contracts/models.py'}
def author_source(source,digest):
    b=raw(source,TARGET if (TARGET,source) in MAP else BASE)
    if sha(b)==digest:return 'RAW_GIT_BYTES'
    assert source in CRLF and b'\r\n' not in b and sha(b.replace(b'\n',b'\r\n'))==digest
    return 'EXPLICIT_EXISTING_LF_TO_CRLF'

author=[]
release=document(EV+'process-release.json')
for row in release['records']:
    d=EV+row['path'].rsplit('/',1)[0]+'/'
    pre=document(d+'preregistered.json');start=document(d+'started.json');end=document(d+'completed.json')
    assert row['pid']==start['pid']==end['pid'] and row['exit_code']==end['exit_code']
    assert end['exit_code'] in (0,90) and not row['alive'] and not row['timed_out'] and not end['alive'] and not end.get('timed_out',end.get('timeout',True))
    assert 0<pre['timeout_seconds']<=90 and pre['argv'] and pre['cwd']
    if 'script_pins' in pre:
        for source,digest in pre['script_pins'].items():
            assert author_source(source,digest)=='RAW_GIT_BYTES' and sha(raw(d+'script-snapshots/'+Path(source).name))==digest
        assert sha(raw(d+'product-source-index.json'))==pre['product_source_index_sha256']
        for value in document(d+'product-source-index.json'):author_source(value['path'],value['sha256'])
    else:
        source='tests/test_a03_p2_r11_crash_cuts.py' if '/processes/' in d else 'src/annotation/runtime/recovery/native_observation.py'
        assert sha(raw(source))==pre['script_sha256']==sha(raw(d+'script-snapshot.py'))
        if 'input_sha256' in pre:
            assert sha(raw(d+'request.json'))==pre['input_sha256'] and pre['retries']==0 and pre['timeout_seconds']==2
            response=json.loads(raw(d+'stdout.txt'));assert response['ok'] and response['pid']==end['pid']
    for stream in ('stdout','stderr'):
        if stream+'_sha256' in end:assert sha(raw(d+stream+'.txt'))==end[stream+'_sha256']
    author.append({'path':d,'pid':end['pid'],'exit_code':end['exit_code'],'timeout_seconds':pre['timeout_seconds'],'alive':False,
      'registration_sha256':sha(raw(d+'preregistered.json')),'completion_sha256':sha(raw(d+'completed.json')),
      'stdout_sha256':sha(raw(d+'stdout.txt')),'stderr_sha256':sha(raw(d+'stderr.txt'))})
assert sum(x['exit_code']==90 for x in author)==4 and len(author)==19

imports=[]
for label in ('author','independent'):
    for g in ('F1','F2','F3','F4'):
        documents=[(EV+'validation/r11-01/cases/'+g+'/before-run.json','imports'),(EV+'validation/r11-01/imports/'+g+'-query.json',None)] if label=='author' else [(root/'cases'/g/'before-run.json','imports'),(root/'imports'/(g+'-query.json'),None)]
        for path,key in documents:
            data=document(path) if label=='author' else load(path)
            if key:data=data[key]
            for name,m in data['modules'].items():
                if label=='author':representation=author_source(author_key(m['path']),m['sha256'])
                else:
                    p=Path(m['path']).resolve()
                    if p==OUT/'scripts/crash_driver.py':assert sha(p.read_bytes())==load(OUT/'driver-preregistration.json')['driver_sha256']==m['sha256']
                    else:
                        assert p.is_relative_to(WORK)
                        source=p.relative_to(WORK).as_posix();assert sha(p.read_bytes())==m['sha256']==MAP[(TARGET,source)]['sha256']
                    representation='EXACT_ISOLATED_RAW_BYTES_OR_FROZEN_REVIEW_DRIVER'
                imports.append({'label':label,'group':g,'record':str(path),'pid':data['pid'],'module':name,'actual_path':m['path'],'sha256':m['sha256'],'representation':representation})
        if label=='independent':assert not (root/'imports'/(g+'-crash.json')).exists()

nested=[]
starts=sorted(root.rglob('started.json'))
assert len(starts)==len(list(root.rglob('preregistered.json')))==len(list(root.rglob('completed.json')))
for p in starts:
    d=p.parent;pre=load(d/'preregistered.json');start=load(p);end=load(d/'completed.json');direct=d.parent==root/'processes'
    assert start['pid']==end['pid'] and not end['alive'] and not end.get('timed_out',end.get('timeout',True))
    if direct:
        crash=d.name.endswith('-crash');expected=90 if crash else 0
        assert end['exit_code']==pre['expected_exit']==expected and pre['timeout_seconds']==45
        assert pre['script_sha256']==sha((OUT/'scripts/crash_driver.py').read_bytes())==sha((d/'script-snapshot.py').read_bytes())
        assert pre['inputs_sha256']==sha(raw(EV+'inputs.json'))
        for path,digest in pre['helpers'].items():assert sha(Path(path).read_bytes())==digest
    else:
        expected=0;assert end['exit_code']==0 and pre['timeout_seconds']==2 and pre['retries']==0
        assert pre['script_sha256']==sha(raw('src/annotation/runtime/recovery/native_observation.py'))==sha((d/'script-snapshot.py').read_bytes())
        assert pre['input_sha256']==sha((d/'request.json').read_bytes())
        request=load(d/'request.json');response=load(d/'stdout.txt');assert response['pid']==end['pid'] and response['ok']
        assert request['observation_id']==response['observation']['observation_id']
        group=next(g for g in ('F1','F2','F3','F4') if d.is_relative_to(root/'cases'/g))
        state=load(root/(group+'-final-SQL.json'));target_rows=state['target']['tables']['observations']
        actual=next(json.loads(v['body']) for v in target_rows if v['observation_id']==request['observation_id'])
        # PersistentMockSession persists the observation body, then enriches the
        # returned wrapper with these four Resource/path fields (lines 476-479).
        value=response['observation']
        assert set(value)-set(actual)=={'resource','readback','asset_root','effect_log_resource'}
        assert {k:value[k] for k in actual}==actual
        assert value['resource']==value['readback']
        assets=Path(value['asset_root']).resolve();assert assets.is_relative_to(root/'cases'/group)
        for field in ('resource','effect_log_resource'):
            resource=value[field];path=(assets/resource['path']).resolve();assert path.is_relative_to(assets)
            body=path.read_bytes();assert sha(body)==resource['sha256']
            assert json.loads(body)==(actual if field=='resource' else {'origin':'SYNTHETIC','effect_log':actual['effect_log']})
        before=load(root/'cases'/group/'before-run.json');opened=load(root/'cases'/group/'reopened-before.json')
        assert start['parent_pid'] in (before['pid'],opened['pid'])
    for stream in ('stdout','stderr'):
        if stream+'_sha256' in end:assert sha((d/(stream+'.txt')).read_bytes())==end[stream+'_sha256']
    nested.append({'record':d.relative_to(OUT).as_posix(),'pid':end['pid'],'exit_code':end['exit_code'],'argv':pre['argv'],'cwd':pre['cwd'],
      'timeout_seconds':pre['timeout_seconds'],'alive':False,'timed_out':False,'source_sha256':pre['script_sha256'],
      'registration_sha256':sha((d/'preregistered.json').read_bytes()),'completion_sha256':sha((d/'completed.json').read_bytes()),
      'stdout_sha256':sha((d/'stdout.txt').read_bytes()),'stderr_sha256':sha((d/'stderr.txt').read_bytes())})
assert {p.parent.name for p in starts if p.parent.parent==root/'processes'}=={g+'-'+p for g in ('F1','F2','F3','F4') for p in ('crash','query')}
write(OUT/'process-and-import-review.json',{'status':'ALL_ACTUAL_RECORDS_RECONCILED','author_processes':author,'independent_nested':nested,'actual_imports':imports,
 'author_process_count':len(author),'independent_nested_count':len(nested),'actual_import_module_records':len(imports),
 'crash_exit_finally_imports_absent_not_fabricated':True,'native_worker_basis':'exact module snapshot, request SHA, parent PID, raw stdout pid/observation and SQLite target row',
 'current_OS_PID_scan':False,'auditor_product_calls':0})
print(json.dumps({'status':'ALL_ACTUAL_RECORDS_RECONCILED','author_processes':len(author),'independent_nested':len(nested),'actual_import_records':len(imports),'product_calls':0}))
