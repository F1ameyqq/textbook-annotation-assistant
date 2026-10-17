# -*- coding: utf-8 -*-
"""Collect only the known bounded run records and unchanged bytes, no OS scan."""
import json
from pathlib import Path
from evidence import OUT,WORK,EV,load,raw,sha,write
identity=load(OUT/'independent-run.json');root=Path(identity['run_root']).resolve();assert root.is_relative_to(WORK)
phases=('local','N1','N2','N3','N4','N5');results=[]
for phase in phases:
    r=load(OUT/('result-'+phase+'.json'));assert r['successful'] and r['tests_run']==r['rounds']==1 and not r['N6_N7_or_compatibility_run'];results.append(r)
    imports=load(OUT/('imports-'+phase+'.json'));assert all(Path(m['actual_file']).resolve().is_relative_to(WORK/'src') and sha(Path(m['actual_file']).read_bytes())==m['sha256'] for m in imports['modules'])
seed=load(OUT/'isolated-source-index.json')['files'];assert len(seed)==121
for row in seed:assert sha((OUT/row['file']).read_bytes())==row['sha256']
started=sorted(root.rglob('started.json'));records=[]
for path in started:
    d=path.parent;pre=load(d/'preregistered.json');start=load(path);end=load(d/'completed.json')
    assert pre['argv'] and pre['cwd'] and 0<pre['timeout_seconds']<=45
    assert start['pid']==end['pid'] and not end['alive']
    timeout='timed_out' if 'timed_out' in end else 'timeout';assert timeout in end and not end[timeout]
    child=d==root/'processes/n1-child';expected=87 if child else 0;assert end['exit_code']==expected
    source='tests/test_a03_r8_r3_post_hold.py' if child else 'src/annotation/runtime/recovery/native_observation.py'
    digest=sha(raw(source));assert pre['script_sha256']==digest and sha((d/'script-snapshot.py').read_bytes())==digest
    if 'input_sha256' in pre:assert sha((d/'request.json').read_bytes())==pre['input_sha256']
    streams={name:(d/(name+'.txt')).read_bytes() for name in ('stdout','stderr')}
    for name,b in streams.items():
        if name+'_sha256' in end:assert sha(b)==end[name+'_sha256']
    records.append({'record':d.relative_to(OUT).as_posix(),'pid':end['pid'],'exit_code':end['exit_code'],'argv':pre['argv'],'cwd':pre['cwd'],
      'timeout_seconds':pre['timeout_seconds'],'alive':False,'timed_out':False,'source':source,'source_sha256':digest,
      'preregistered_sha256':sha((d/'preregistered.json').read_bytes()),'completed_sha256':sha((d/'completed.json').read_bytes()),
      'stdout_sha256':sha(streams['stdout']),'stderr_sha256':sha(streams['stderr'])})
assert len(started)==len(list(root.rglob('preregistered.json')))==len(list(root.rglob('completed.json')))
child=load(root/'processes/n1-child/completed.json');marker=load(root/'cases/N1/effect-committed.barrier.json')
assert child['exit_code']==87 and child['barrier_released'] and marker['pid']==child['pid'] and marker['point']=='AFTER_TARGET_EFFECT_COMMIT'
assert not list((root/'cases').glob('N6*')) and not list((root/'cases').glob('N7*'))
for p in root.rglob('*'):
    if p.is_file() and (p.name.endswith('-wal') or p.name.endswith('-journal')):assert p.stat().st_size==0
write(OUT/'independent-nested-release.json',{'status':'OWN_BOUNDED_NESTED_CHILDREN_EXITED','count':len(records),'records':records,
 'basis':'known preregistration/start/wait-completion and raw streams, no OS/profile scan'})
files=[{'file':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(root.rglob('*')) if p.is_file()]
write(OUT/'independent-output-index.json',{'run_id':identity['run_id'],'files':files,'phases_once':list(phases),'N6_N7_run':False})
write(OUT/'independent-run-summary.json',{'status':'LOCAL_N1_N2_N3_N4_N5_LIMITED_PASSED','run_id':identity['run_id'],'results':results,
 'seed_files_unchanged':121,'nested_processes':len(records),'N1_effects':1,'POST_HOLD_admissions':2,'N6':'NOT_RUN','N7':'READ_ONLY_ORIGINAL_FAILURE_ONLY',
 'N3_trace':'non-mutating input/output capture around actual schema and comparison calls; no additional candidate calls',
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print(json.dumps({'status':'LOCAL_N1_N2_N3_N4_N5_LIMITED_PASSED','nested':len(records),'generated_files':len(files),'seed_files':121}))
