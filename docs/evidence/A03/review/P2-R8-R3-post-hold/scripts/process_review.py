# -*- coding: utf-8 -*-
import json
import difflib
import re
from evidence import OUT,EV,raw,text,document,sha,write
release=document(EV+'process-release.json')['records'];assert len(release)==34
records=[]
for row in release:
    directory=row['path'].rsplit('/',1)[0];p=EV+directory+'/'
    pre=document(p+'preregistered.json');start=document(p+'started.json');end=document(p+'completed.json')
    assert pre['argv'] and pre['cwd'] and 0<pre['timeout_seconds']<=120
    assert row['pid']==start['pid']==end['pid'] and row['exit_code']==end['exit_code']
    key='timed_out' if 'timed_out' in end else 'timeout';assert key in end
    assert not row['alive'] and not row['timeout'] and not end['alive'] and not end[key]
    streams={s:raw(p+s+'.txt') for s in ('stdout','stderr')}
    for s,b in streams.items():
        if s+'_sha256' in end:assert end[s+'_sha256']==sha(b)
    records.append({'record':directory,'pid':row['pid'],'exit_code':end['exit_code'],'argv':pre['argv'],'cwd':pre['cwd'],
      'timeout_seconds':pre['timeout_seconds'],'alive':False,'timed_out':False,'stdout_sha256':sha(streams['stdout']),'stderr_sha256':sha(streams['stderr'])})
groups=('local','N1','N2','N3','N4','N5','N7','C01','A02','R7');indices=[raw(EV+'runs/'+g+'/product-source-index.json') for g in groups]
assert len({sha(b) for b in indices})==1
script_identities=[]
critical=('src/annotation/runtime/storage/__init__.py','src/annotation/runtime/storage/native.py','src/annotation/contracts/recovery.py',
 'src/annotation/quality/synthetic_precheck.py','src/annotation/contracts/a03_native/data/profile.json','src/annotation/contracts/a03_native/data/adoption.json')
for g in groups:
    p=EV+'runs/'+g+'/';pre=document(p+'preregistered.json');assert pre['product_source_index_sha256']==sha(indices[0])
    for source in critical:assert sha(raw(p+'product-snapshot/'+source))==sha(raw(source))
    for source,d in pre['script_pins'].items():
        snapshot=raw(p+'script-snapshots/'+source.rsplit('/',1)[1]);current=raw(source)
        assert d==sha(snapshot)
        identity={'group':g,'source':source,'registered_snapshot_sha256':d,'target_sha256':sha(current),'byte_equal_to_target':snapshot==current}
        if snapshot!=current:
            identity['only_CRLF_representation']=snapshot.replace(b'\r\n',b'\n')==current.replace(b'\r\n',b'\n')
            identity['text_diff']=list(difflib.unified_diff(snapshot.decode('utf8').splitlines(),current.decode('utf8').splitlines(),fromfile=g+'/snapshot',tofile='target/'+source,lineterm=''))
            if g in ('N1','N2') and source=='tests/test_a03_r8_r3_post_hold.py':
                before=snapshot.decode('utf8');after=current.decode('utf8')
                assert before.split('    def test_N4',1)[0]==after.split('    def test_N4',1)[0]
                assert before.split("if __name__ == '__main__':",1)[1]==after.split("if __name__ == '__main__':",1)[1]
                identity['executed_N1_N2_helpers_and_methods_unchanged']=True
        script_identities.append(identity)
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
child=document(EV+'validation/native-r3-01/processes/n1-child/completed.json')
assert child['exit_code']==87 and child['barrier_released']
assert document(EV+'runs/N1/completed.json')['exit_code']==0 and text(EV+'runs/N1/stderr.txt').rstrip().endswith('OK')
assert document(EV+'runs/N2/completed.json')['exit_code']==0 and text(EV+'runs/N2/stderr.txt').rstrip().endswith('OK')
assert document(EV+'runs/N7/completed.json')['exit_code']==1 and 'FAILED (failures=1)' in text(EV+'runs/N7/stderr.txt')
start4=document(EV+'runs/N4/started.json')['started_at_ns'];end4=document(EV+'runs/N4/completed.json')['ended_at_ns'];end7=document(EV+'runs/N7/completed.json')['ended_at_ns']
assert start4<end7<end4
value={'status':'34_AUTHOR_RECORDS_AND_COMPATIBILITY_RECONCILED','records':records,'compatibility':compat,'C01_expected_rejections':negatives,
 'source_index_sha256':sha(indices[0]),'N1_child':child,'N1_parent_exit':0,'N2_parent_exit':0,'N7_parent_exit':1,
 'actual_script_identity':script_identities,
 'reviewer_first_audit_failure':'author-process-review-01 initially required every script snapshot to equal final target; original failure retained',
 'N4_started_before_N7_failed_and_finished_after':{'N4_started_ns':start4,'N7_ended_ns':end7,'N4_ended_ns':end4},'candidate_tests_rerun':0,
 'release_basis':'frozen completion records and raw bytes only; no live OS/profile scan'}
write(OUT/'author-process-review.json',value)
print(json.dumps({'status':value['status'],'processes':34,'compatibility':[r['tests'] for r in compat],'C01_expected_exit1':3,'N7_original':'FAILED','N4_not_a_rerun':True}))
