# -*- coding: utf-8 -*-
"""Raw frozen author process, module, script and source identity reconciliation."""
import json
from pathlib import Path
from evidence import OUT,WORK,EV,TARGET,BASE,MAP,raw,document,sha,write,author_key
release=document(EV+'process-release.json');assert len(release['records'])==8 and release['all_recorded_owned_processes_waited_and_ended']
records=[]
for row in release['records']:
    p=EV+row['path'].rsplit('/',1)[0]+'/'
    pre=document(p+'preregistered.json');start=document(p+'started.json');end=document(p+'completed.json')
    assert pre['argv'] and pre['cwd'] and 0<pre['timeout_seconds']<=60
    assert row['pid']==start['pid']==end['pid'] and row['exit_code']==end['exit_code']
    assert not row['alive'] and not row['timed_out'] and not end['alive'] and not end.get('timed_out',end.get('timeout',True))
    expected=87 if 'processes/n1-child/' in p else 0;assert end['exit_code']==expected
    streams={n:raw(p+n+'.txt') for n in ('stdout','stderr')}
    for n,b in streams.items():
        if n+'_sha256' in end:assert sha(b)==end[n+'_sha256']
    snapshots=[]
    if 'script_pins' in pre:
        for path,digest in pre['script_pins'].items():
            source=author_key(path);rev=TARGET if (TARGET,source) in MAP else BASE
            assert sha(raw(source,rev))==digest and sha(raw(p+'script-snapshots/'+Path(source).name))==digest
            snapshots.append({'path':source,'sha256':digest,'frozen_commit':rev})
    else:
        source='tests/test_a03_r8_r3_post_hold.py' if expected==87 else 'src/annotation/runtime/recovery/native_observation.py'
        digest=sha(raw(source));assert pre['script_sha256']==digest and sha(raw(p+'script-snapshot.py'))==digest
        snapshots.append({'path':source,'sha256':digest,'frozen_commit':TARGET})
        if 'input_sha256' in pre:assert sha(raw(p+'request.json'))==pre['input_sha256']
    records.append({'record':p[len(EV):-1],'argv':pre['argv'],'cwd':pre['cwd'],'timeout_seconds':pre['timeout_seconds'],
      'pid':end['pid'],'exit_code':end['exit_code'],'alive':False,'timed_out':False,'script_snapshots':snapshots,
      'preregistration_sha256':sha(raw(p+'preregistered.json')),'completion_sha256':sha(raw(p+'completed.json')),
      'stdout_sha256':sha(streams['stdout']),'stderr_sha256':sha(streams['stderr'])})
indices=[];module_records=[]
for group in ('N1','N6','N7'):
    p=EV+'runs/'+group+'/';pre=document(p+'preregistered.json');source_raw=raw(p+'product-source-index.json');indices.append(sha(source_raw))
    assert pre['product_source_index_sha256']==sha(source_raw)
    source_index=json.loads(source_raw)
    expected_source_paths={r['path'] for r in __import__('evidence').INDEX if r['commit']==TARGET and r['file'].startswith('isolation/workspace/src/annotation/') and Path(r['path']).suffix in ('.py','.json')}
    assert {r['path'] for r in source_index}==expected_source_paths
    for r in source_index:assert sha(raw(r['path']))==r['sha256'] and len(raw(r['path']))==r['bytes']
    assert sha(raw(p+'fixture-index.json'))==pre['fixture_index_sha256']
    for r in document(p+'fixture-index.json'):assert sha(raw(r['path']))==r['sha256']
    imports=document(EV+'validation/r4-native-01/imports/'+group+'.json')
    for name,r in imports['modules'].items():
        source=author_key(r['path']);assert sha(raw(source))==r['sha256']
        module_records.append({'phase':group,'module':name,'actual_file':r['path'],'source':source,'sha256':r['sha256']})
assert len(set(indices))==1
for group in ('N1','N6','N7'):
    log=raw(EV+'runs/'+group+'/stderr.txt').decode();assert 'Ran 1 test in ' in log and log.rstrip().endswith('OK') and 'skipped' not in log
child=document(EV+'validation/r4-native-01/processes/n1-child/completed.json')
assert child['exit_code']==87 and child['barrier_released']
write(OUT/'author-process-review.json',{'status':'ALL_8_FROZEN_AUTHOR_PROCESSES_AND_IMPORTS_RECONCILED','records':records,
 'source_index_sha256':indices[0],'actual_modules':module_records,'N1_child_effect_barrier_released':True,
 'original_R3_N7_stderr_sha256':sha(raw('docs/evidence/A03/execution/P2-R8-R3-post-hold/runs/N7/stderr.txt',BASE)),
 'original_R3_N7_status':'FAILED_PRESERVED','product_tests_rerun_by_this_auditor':0,'OS_profile_scan':False,
 'reviewer_first_audit_failure':'author-process-review-01 assumed source index included all 68 package files; author index intentionally selects .py/.json. v2 verifies the complete selected path set and bytes; no product rerun.',
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print(json.dumps({'status':'ALL_8_FROZEN_AUTHOR_PROCESSES_AND_IMPORTS_RECONCILED','processes':8,'actual_modules':len(module_records)}))
