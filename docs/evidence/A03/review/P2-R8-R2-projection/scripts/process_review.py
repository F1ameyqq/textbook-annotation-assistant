# -*- coding: utf-8 -*-
import json
import re
from evidence import OUT,EV,raw,text,document,sha,write
release=document(EV+'process-release.json')['records'];assert len(release)==26
records=[]
for row in release:
    directory=row['path'].rsplit('/',1)[0];p=EV+directory+'/'
    pre=document(p+'preregistered.json');start=document(p+'started.json');end=document(p+'completed.json')
    assert pre['argv'] and pre['cwd'] and 0<pre['timeout_seconds']<=60
    assert row['pid']==start['pid']==end['pid'] and row['exit_code']==end['exit_code']
    key='timed_out' if 'timed_out' in end else 'timeout';assert key in end
    assert not row['alive'] and not row['timeout'] and not end['alive'] and not end[key]
    streams={s:raw(p+s+'.txt') for s in ('stdout','stderr')}
    for s,b in streams.items():
        if s+'_sha256' in end:assert end[s+'_sha256']==sha(b)
    records.append({'record':directory,'pid':row['pid'],'exit_code':end['exit_code'],'argv':pre['argv'],'cwd':pre['cwd'],
      'timeout_seconds':pre['timeout_seconds'],'alive':False,'timed_out':False,'stdout_sha256':sha(streams['stdout']),'stderr_sha256':sha(streams['stderr'])})
groups=('minimal','N1','N2','C01','A02','R7');indices=[raw(EV+'runs/'+g+'/product-source-index.json') for g in groups]
assert len({sha(b) for b in indices})==1
critical=('src/annotation/runtime/storage/__init__.py','src/annotation/runtime/storage/native.py','src/annotation/contracts/recovery.py',
 'src/annotation/quality/synthetic_precheck.py','src/annotation/contracts/a03_native/data/profile.json','src/annotation/contracts/a03_native/data/adoption.json')
for g in groups:
    p=EV+'runs/'+g+'/';pre=document(p+'preregistered.json');assert pre['product_source_index_sha256']==sha(indices[0])
    for source in critical:assert sha(raw(p+'product-snapshot/'+source))==sha(raw(source))
    for source,d in pre['script_pins'].items():
        assert d==sha(raw(source))==sha(raw(p+'script-snapshots/'+source.rsplit('/',1)[1]))
compat=[]
for g,n in [('C01',70),('A02',52),('R7',13)]:
    log=text(EV+'runs/'+g+'/stderr.txt');assert re.search(r'Ran '+str(n)+r' tests? in ',log) and log.rstrip().endswith('OK') and 'skipped=' not in log
    compat.append({'group':g,'tests':n,'stderr_sha256':sha(log.encode()),'source_index_sha256':sha(indices[0])})
negatives=[]
for r in records:
    if r['record'].startswith('nested-processes/C01/') and r['exit_code']:
        issue=document(EV+r['record']+'/stderr.txt');assert issue['valid'] is False and all(i['code']=='MISSING_REFERENCE' for i in issue['issues'])
        negatives.append({'record':r['record'],'issues':issue['issues'],'classification':'EXPECTED_C01_REJECTION'})
assert len(negatives)==3
child=document(EV+'validation/native-r2-01/processes/n1-child/completed.json')
assert child['exit_code']==87 and child['barrier_released']
assert document(EV+'runs/N1/completed.json')['exit_code']==0 and text(EV+'runs/N1/stderr.txt').rstrip().endswith('OK')
assert document(EV+'runs/N2/completed.json')['exit_code']==1 and 'FAILED (errors=1)' in text(EV+'runs/N2/stderr.txt')
bootstrap=document(EV+'preparation-command-failure.json')
assert bootstrap['pid'] is None and bootstrap['exit_code']==1 and bootstrap['product_or_test_execution'] is False
assert 'not raw' in bootstrap['transcript_limit']
value={'status':'26_AUTHOR_RECORDS_AND_COMPATIBILITY_RECONCILED','records':records,'compatibility':compat,'C01_expected_rejections':negatives,
 'source_index_sha256':sha(indices[0]),'N1_child':child,'N1_parent_exit':0,'N2_parent_exit':1,
 'bootstrap_failure_evidence_limit':bootstrap,'bootstrap_not_in_26_PID_records':True,'candidate_tests_rerun':0,
 'release_basis':'frozen completion records and raw bytes only; no live OS/profile scan'}
write(OUT/'author-process-review.json',value)
print(json.dumps({'status':value['status'],'processes':26,'compatibility':[r['tests'] for r in compat],'C01_expected_exit1':3,'bootstrap_PID':None}))
