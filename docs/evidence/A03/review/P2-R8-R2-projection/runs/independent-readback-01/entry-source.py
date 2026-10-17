# -*- coding: utf-8 -*-
"""Independent readback after the sole N1 execution; never call product APIs."""
import json
from pathlib import Path
from evidence import OUT,WORK,EV,load,sha,write
from verify_case import verify_case
run=load(OUT/'independent-run.json');root=Path(run['run_root']).resolve();case=Path(run['case']).resolve()
assert root.is_relative_to(WORK) and case==root/'cases/N1'
assert load(OUT/'independent-test-result.json')['successful']
assert load(OUT/'runs/independent-n1-01/completion.json')['exit_code']==0
def read(path):
    p=Path(path)
    if not p.is_absolute():p=WORK/p
    p=p.resolve();assert p.is_relative_to(root),p
    return p.read_bytes()
for role in ('runtime','target'):
    database=case/role/(role+'.sqlite3')
    for suffix in ('-wal','-journal'):
        sidecar=Path(str(database)+suffix)
        assert not sidecar.exists() or sidecar.stat().st_size==0,sidecar
result=verify_case('independent',read,str(case/'runtime/runtime.sqlite3'),str(case/'target/target.sqlite3'),False)
expected=load(OUT/'author-boundary-review.json')
assert result['formal_receipt_ref']!=expected['formal_receipt_ref'] and result['terminal_head_ref']!=expected['terminal_head_ref']
assert result['current_bundle_sha256']!=expected['current_bundle_sha256']
source_result=json.loads(read(root/'N1-result.json'))
assert source_result['formal_receipt_ref']==result['formal_receipt_ref'] and source_result['quality']['postcheck_ref']==result['POST_ref']
assert source_result['quality']['batch_ref']==result['Batch_ref'] and source_result['effect_count']==result['effect_count']==1
assert not [p for p in (root/'cases').iterdir() if p.name!='N1']
started=sorted(root.rglob('started.json'));records=[]
for path in started:
    d=path.parent;pre=load(d/'preregistered.json');start=load(path);end=load(d/'completed.json')
    assert pre['argv'] and pre['cwd'] and 0<pre['timeout_seconds']<=45
    assert start['pid']==end['pid'] and not end['alive']
    timeout_key='timed_out' if 'timed_out' in end else 'timeout';assert timeout_key in end and not end[timeout_key]
    expected_code=87 if d==root/'processes/n1-child' else 0;assert end['exit_code']==expected_code
    streams={s:(d/(s+'.txt')).read_bytes() for s in ('stdout','stderr')}
    for s,b in streams.items():
        if s+'_sha256' in end:assert sha(b)==end[s+'_sha256']
    records.append({'record':d.relative_to(OUT).as_posix(),'pid':end['pid'],'argv':pre['argv'],'cwd':pre['cwd'],
      'timeout_seconds':pre['timeout_seconds'],'exit_code':end['exit_code'],'alive':False,'timed_out':False,
      'script_sha256':pre.get('script_sha256'),'preregistered_sha256':sha((d/'preregistered.json').read_bytes()),
      'completed_sha256':sha((d/'completed.json').read_bytes()),'stdout_sha256':sha(streams['stdout']),'stderr_sha256':sha(streams['stderr'])})
assert len(started)==len(list(root.rglob('preregistered.json')))==len(list(root.rglob('completed.json')))
child=load(root/'processes/n1-child/completed.json');marker=load(case/'effect-committed.barrier.json')
assert child['exit_code']==87 and child['barrier_released'] and marker['pid']==child['pid'] and marker['point']=='AFTER_TARGET_EFFECT_COMMIT'
imports=load(OUT/'independent-imports.json')
assert all(Path(r['actual_file']).resolve().is_relative_to(WORK/'src') for r in imports['modules'])
write(OUT/'independent-nested-release.json',{'status':'ALL_OWN_N1_NESTED_CHILDREN_WAITED_AND_EXITED','records':records,
 'count':len(records),'basis':'original preregistration/start/completion and raw streams; no system/profile scan'})
files=[]
for p in sorted(root.rglob('*')):
    if p.is_file():files.append({'file':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())})
write(OUT/'independent-output-index.json',{'run_id':run['run_id'],'files':files,'one_N1_round':True,'other_test_groups_run':False})
print(json.dumps({'status':'INDEPENDENT_N1_FORMAL_BOUNDARIES_VERIFIED','effects':result['effect_count'],
 'formal_receipt':result['formal_receipt_ref'],'material_progress':len(result['material_progress']),
 'POST':result['POST_ref'],'Batch':result['Batch_ref'],'nested_children':len(records),'generated_files':len(files)}))
