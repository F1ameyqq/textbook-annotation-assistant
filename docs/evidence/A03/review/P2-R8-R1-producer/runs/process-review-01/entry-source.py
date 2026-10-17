# -*- coding: utf-8 -*-
"""Reconcile 23 original processes and final-candidate source identity, read-only."""
import json
import re
from evidence import OUT,EV,document,raw,text,sha,write
release=document(EV+'process-release.json')['records'];assert len(release)==23
records=[]
for row in release:
    directory=row['path'].rsplit('/',1)[0];p=EV+directory+'/'
    pre=document(p+'preregistered.json');start=document(p+'started.json');end=document(p+'completed.json')
    assert pre['argv'] and pre['cwd'] and 0<pre['timeout_seconds']<=60
    assert row['pid']==start['pid']==end['pid'] and row['exit_code']==end['exit_code']
    timeout_key='timed_out' if 'timed_out' in end else 'timeout';assert timeout_key in end
    assert not row['alive'] and not row['timeout'] and not end['alive'] and not end[timeout_key]
    streams={s:raw(p+s+'.txt') for s in ('stdout','stderr')}
    for s,b in streams.items():
        if s+'_sha256' in end:assert end[s+'_sha256']==sha(b)
    records.append({'record':directory,'pid':row['pid'],'exit_code':end['exit_code'],'argv':pre['argv'],'cwd':pre['cwd'],
      'timeout_seconds':pre['timeout_seconds'],'timed_out':False,'alive':False,
      'stdout_sha256':sha(streams['stdout']),'stderr_sha256':sha(streams['stderr']),
      'preregistered_sha256':sha(raw(p+'preregistered.json')),'completed_sha256':sha(raw(p+'completed.json'))})
groups=('minimal','N1','C01','A02','R7');indexes=[raw(EV+'runs/'+g+'/product-source-index.json') for g in groups]
assert len({sha(b) for b in indexes})==1
source_index={r['path']:r for r in json.loads(indexes[0])}
critical=('src/annotation/quality/synthetic_precheck.py','src/annotation/contracts/a03_native/data/profile.json',
 'src/annotation/contracts/a03_native/data/adoption.json','src/annotation/runtime/storage/__init__.py',
 'src/annotation/runtime/storage/native.py','src/annotation/contracts/recovery.py','src/annotation/quality/targetcheck/__init__.py')
for g in groups:
    p=EV+'runs/'+g+'/'
    pre=document(p+'preregistered.json')
    assert pre['product_source_index_sha256']==sha(indexes[0])
    assert pre['input_index_sha256']==sha(raw(EV+'inputs.json'))
    for source in critical:
        assert source_index[source]['sha256']==sha(raw(source))
        assert sha(raw(p+'product-snapshot/'+source))==sha(raw(source))
    for source,digest in pre['script_pins'].items():
        assert digest==sha(raw(source))
        assert digest==sha(raw(p+'script-snapshots/'+source.rsplit('/',1)[1]))
compat=[]
for g,count in [('C01',70),('A02',52),('R7',13)]:
    log=text(EV+'runs/'+g+'/stderr.txt')
    assert re.search(r'Ran '+str(count)+r' tests? in ',log) and log.rstrip().endswith('OK')
    assert 'FAILED (' not in log and 'skipped=' not in log
    compat.append({'group':g,'tests':count,'exit_code':document(EV+'runs/'+g+'/completed.json')['exit_code'],
      'final_candidate_source_index_sha256':sha(indexes[0]),'stderr_sha256':sha(log.encode())})
negative=[]
for row in records:
    if not row['record'].startswith('nested-processes/C01/') or row['exit_code']==0:continue
    body=json.loads(text(EV+row['record']+'/stderr.txt'))
    assert body['valid'] is False and body['issues'] and all(i['code']=='MISSING_REFERENCE' for i in body['issues'])
    negative.append({'record':row['record'],'exit_code':1,'issues':body['issues'],'classification':'EXPECTED_C01_CLI_REJECTION'})
assert len(negative)==3
assert 'self.assertNotEqual(completed.returncode, 0)' in text('tests/test_contracts.py')
assert 'self.assertNotEqual(completed.returncode, 0, completed.stdout)' in text('tests/test_contracts_platform_refs.py')
child=EV+'validation/native-r1-01/processes/n1-child/'
end=document(child+'completed.json');assert end['exit_code']==87 and end['barrier_released']
assert document(EV+'runs/N1/completed.json')['exit_code']==1
assert 'FAILED (errors=1)' in text(EV+'runs/N1/stderr.txt')
marker=document(EV+'validation/native-r1-01/cases/N1/effect-committed.barrier.json')
assert marker['point']=='AFTER_TARGET_EFFECT_COMMIT' and marker['pid']==end['pid']
assert raw(EV+'validation/native-r1-01/cases/N1/release.barrier')==b'release after independent effect count\n'
before=document(EV+'validation/native-r1-01/cases/N1/before-dispatch.json')
assert before['product_import'].replace('\\','/').endswith('/1800/src/annotation')
value={'status':'23_FROZEN_PROCESSES_AND_FINAL_CANDIDATE_COMPATIBILITY_RECONCILED','records':records,
 'compatibility':compat,'C01_expected_rejections':negative,'product_source_index_sha256':sha(indexes[0]),
 'seven_critical_snapshot_files_per_group_verified':list(critical),'groups_same_final_source':list(groups),
 'N1_child_exit87_after_effect_barrier':end,'N1_parent_exit1_is_real_error':True,'effect_marker':marker,
 'actual_import':before['product_import'],'candidate_tests_or_native_API_rerun':0,
 'release_basis':'historical wait/completion and original raw logs, no current OS/profile scan',
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'process-review.json',value)
print(json.dumps({'status':value['status'],'processes':len(records),'compatibility_counts':[r['tests'] for r in compat],
 'C01_expected_exit1':len(negative),'N1_child_exit':end['exit_code'],'N1_parent_exit':1}))
