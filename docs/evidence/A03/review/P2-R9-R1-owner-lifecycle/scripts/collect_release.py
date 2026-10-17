# -*- coding: utf-8 -*-
"""Known-child release and file/import identity, no candidate calls or OS scan."""
import json
from pathlib import Path
from evidence import OUT,WORK,EV,TARGET,MAP,load,raw,sha,write
identity=load(OUT/'independent-run.json');root=Path(identity['run_root']).resolve();assert root.is_relative_to(WORK)
own=load(OUT/'independent-driver.json');source_index=load(OUT/'review-source-index.json')['files'];assert len(source_index)==78
for r in source_index:assert sha((OUT/r['file']).read_bytes())==r['sha256'] and (OUT/r['file']).stat().st_size==r['bytes']
results=[]
for group in ('D1','standalone','borrow','D2'):
    r=load(OUT/('result-'+group+'.json'));assert r['exit_code']==0 and r['functional_rounds']==1 and not r['other_groups_or_prior_R3_R4_replayed'];results.append(r)
modules=[]
for entry in sorted((root/'imports').glob('*.json')):
    data=load(entry)
    for name,m in data['modules'].items():
        p=Path(m['path']).resolve();assert p.is_relative_to(WORK);source=p.relative_to(WORK).as_posix();digest=sha(p.read_bytes())
        expected=own['sha256'] if p==OUT/own['file'] else MAP[(TARGET,source)]['sha256']
        assert m['sha256']==digest==expected
        modules.append({'record':entry.relative_to(OUT).as_posix(),'module':name,'actual_file':str(p),'source':source,'sha256':digest})
assert len(list((root/'imports').glob('*.json')))==6
records=[]
for start_path in sorted(root.rglob('started.json')):
    d=start_path.parent;pre=load(d/'preregistered.json');start=load(start_path);end=load(d/'completed.json')
    assert pre['argv'] and pre['cwd'] and 0<pre['timeout_seconds']<=45 and start['pid']==end['pid']
    assert not end['alive'] and not end.get('timed_out',end.get('timeout',True))
    direct=d.parent==root/'processes';expected=90 if d.name=='D2-execute' and direct else 0;assert end['exit_code']==expected
    source=own['file'] if direct else 'src/annotation/runtime/recovery/native_observation.py'
    digest=own['sha256'] if direct else sha(raw(source));assert pre['script_sha256']==digest==sha((d/'script-snapshot.py').read_bytes())
    if direct:
        assert pre['inputs_sha256']==sha(raw(EV+'inputs.json')) and pre['original_R9_driver_sha256']==sha(raw('tests/test_a03_p2_r9_minimal_demos.py')) and pre['expected_exit']==expected
    elif 'input_sha256' in pre:assert sha((d/'request.json').read_bytes())==pre['input_sha256']
    for stream in ('stdout','stderr'):
        digest_stream=sha((d/(stream+'.txt')).read_bytes())
        if stream+'_sha256' in end:assert digest_stream==end[stream+'_sha256']
    records.append({'record':d.relative_to(OUT).as_posix(),'pid':end['pid'],'exit_code':end['exit_code'],'argv':pre['argv'],'cwd':pre['cwd'],
      'timeout_seconds':pre['timeout_seconds'],'alive':False,'timed_out':False,'source':source,'source_sha256':digest,
      'registration_sha256':sha((d/'preregistered.json').read_bytes()),'completion_sha256':sha((d/'completed.json').read_bytes()),
      'stdout_sha256':sha((d/'stdout.txt').read_bytes()),'stderr_sha256':sha((d/'stderr.txt').read_bytes())})
assert len(records)==len(list(root.rglob('preregistered.json')))==len(list(root.rglob('completed.json')))==15
assert sum(r['exit_code']==90 for r in records)==1
marker=load(root/'cases/D2/after-intent-commit.marker.json');child=load(root/'processes/D2-execute/completed.json')
assert marker['pid']==child['pid'] and marker['point']=='AFTER_INTENT_COMMIT' and child['exit_code']==90
assert {p.name for p in (root/'cases').iterdir()}=={'D1','standalone','borrow','D2'}
for previous in ('P2-R8-R3-post-hold','P2-R9-minimal-demos'):
    assert not (WORK/'docs/evidence/A03/execution'/previous/'validation').exists()
for p in root.rglob('*'):
    if p.is_file() and p.name.endswith(('-wal','-journal')):assert p.stat().st_size==0
files=[{'file':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(root.rglob('*')) if p.is_file()]
write(OUT/'independent-output-index.json',{'run_id':identity['run_id'],'files':files,'four_groups_once':['D1','standalone','borrow','D2']})
write(OUT/'independent-imports-review.json',{'status':'ALL_ACTUAL_MODULES_BOUND_TO_RAW_ISOLATED_SOURCE_OR_PREREGISTERED_OWN_DRIVER','modules':modules,'normal_import':True,'author_tree_imported':False})
write(OUT/'independent-nested-release.json',{'status':'FIFTEEN_KNOWN_CHILDREN_WAITED_AND_EXITED','records':records,'count':15,'real_D2_exit90':True,
 'basis':'known preregistered Popen wait/completion records and raw streams; no OS/profile scan'})
write(OUT/'independent-run-summary.json',{'status':'FOUR_OWNER_LIFECYCLE_GROUPS_LIMITED_PASSED','run_id':identity['run_id'],'results':results,
 'source_files_unchanged':78,'generated_files':len(files),'nested_children':15,'effect_counts':[1,1,1,0],'formal_report_reads':[1,1,1,0],
 'author_borrow':'FAILED_PRESERVED','author_D2':'NOT_RUN','independent_D2':'REAL_EXIT90_ABSENT_OLD_PLAN_REFUSED',
 'overall_A03':'REWORK','I01_released':False,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print(json.dumps({'status':'FOUR_OWNER_LIFECYCLE_GROUPS_LIMITED_PASSED','own_source_files':78,'generated':len(files),'imports':len(modules),'nested_children':15}))
