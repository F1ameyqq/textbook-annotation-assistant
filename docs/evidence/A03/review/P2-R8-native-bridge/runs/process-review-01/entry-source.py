# -*- coding: utf-8 -*-
"""Interpret frozen process and compatibility evidence without rerunning tests."""
import json
import re
from evidence import OUT,EV,document,raw,text,sha,write

release=document(EV+'process-release.json');rows=release['owned_processes']
assert len(rows)==28 and len({r['path'] for r in rows})==28
records=[]
for row in rows:
    directory=row['path'].rsplit('/',1)[0];prefix=EV+directory+'/'
    pre=document(prefix+'preregistered.json');started=document(prefix+'started.json');end=document(prefix+'completed.json')
    assert pre['argv'] and pre['cwd'] and 0<pre['timeout_seconds']<=60
    assert row['pid']==started['pid']==end['pid']
    assert row['exit_code']==end['exit_code']
    assert not row['alive'] and not row['timeout'] and not end['alive'] and not end['timed_out']
    stdout=raw(prefix+'stdout.txt');stderr=raw(prefix+'stderr.txt')
    if 'stdout_sha256' in end:assert end['stdout_sha256']==sha(stdout)
    if 'stderr_sha256' in end:assert end['stderr_sha256']==sha(stderr)
    records.append({'record':directory,'pid':row['pid'],'exit_code':end['exit_code'],'argv':pre['argv'],
      'cwd':pre['cwd'],'timeout_seconds':pre['timeout_seconds'],'alive':False,'timed_out':False,
      'preregistered_sha256':sha(raw(prefix+'preregistered.json')),
      'completed_sha256':sha(raw(prefix+'completed.json')),
      'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr),
      'barrier_released':end.get('barrier_released')})
compat=[]
for group,count,pattern in [('C01',70,'test_contracts*.py'),('A02',52,'test_a02*.py'),('R7',13,'test_a03_r7_readonly_codec.py')]:
    prefix=EV+'runs/'+group+'/'
    log=text(prefix+'stderr.txt');pre=document(prefix+'preregistered.json');end=document(prefix+'completed.json')
    assert pattern in pre['argv'] and end['exit_code']==0
    assert re.search(r'Ran '+str(count)+r' tests? in ',log) and log.rstrip().endswith('OK')
    assert 'FAILED (' not in log and 'skipped=' not in log
    assert pre['product_source_index_sha256']==sha(raw(prefix+'product-source-index.json'))
    assert pre['input_index_sha256']==sha(raw(EV+'inputs.json'))
    compat.append({'group':group,'tests':count,'exit_code':0,'raw_stderr_sha256':sha(raw(prefix+'stderr.txt')),
      'source_index_sha256':pre['product_source_index_sha256'],'final_native_fix_covered':False})
initial_index=sha(raw(EV+'runs/N1-initial/product-source-index.json'))
assert all(r['source_index_sha256']==initial_index for r in compat)
assert sha(raw(EV+'runs/N1-local-fix/product-source-index.json'))!=initial_index
negative=[]
for row in records:
    if not row['record'].startswith('nested-processes/C01/') or row['exit_code']==0:continue
    stderr=text(EV+row['record']+'/stderr.txt')
    issue=json.loads(stderr)
    assert issue['valid'] is False and issue['issues']
    assert 'validate' in row['argv']
    child=row['record'].rsplit('/',1)[1]
    if child=='child-01':
        assert row['argv'][-1].endswith('invalid.json') and 'fragment_ids' in stderr
        purpose='test_cli_rejects_invalid_exchange_with_nonzero_exit_and_location; missing-fragment mutation'
    else:
        assert child in ('child-07','child-08')
        assert all(i['code']=='MISSING_REFERENCE' for i in issue['issues'])
        purpose='test_contracts_platform_refs formal platform-reference negative; expected MISSING_REFERENCE'
    negative.append({'record':row['record'],'exit_code':1,'purpose':purpose,'issues':issue['issues'],
      'classification':'EXPECTED_C01_CLI_REJECTION','stderr_sha256':sha(stderr.encode())})
assert len(negative)==3
assert 'self.assertNotEqual(completed.returncode, 0)' in text('tests/test_contracts.py')
assert 'self.assertNotEqual(completed.returncode, 0, completed.stdout)' in text('tests/test_contracts_platform_refs.py')
for group,label in [('N1-initial','bounded-01'),('N1-local-fix','bounded-02')]:
    parent=document(EV+'runs/'+group+'/completed.json')
    child=document(EV+'validation/'+label+'/processes/n1-child/completed.json')
    assert parent['exit_code']==child['exit_code']==1 and child['barrier_released'] is False
    assert not parent['alive'] and not child['alive']
    assert 'FAILED (failures=1)' in text(EV+'runs/'+group+'/stderr.txt')
value={'status':'FROZEN_PROCESS_AND_COMPATIBILITY_EVIDENCE_RECONCILED','records':records,
 'record_count':len(records),'nonzero_records':[r['record'] for r in records if r['exit_code']],
 'compatibility':compat,'C01_expected_negative_children':negative,
 'compatibility_before_final_fix_only':True,'compatibility_tests_rerun':0,
 'both_N1_parent_child_pairs_are_real_failures':True,'neither_effect_barrier_released':True,
 'release_basis':'frozen wait/completion and raw logs only; no live OS or profile scan',
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'process-and-compatibility-review.json',value)
print(json.dumps({'status':value['status'],'processes':len(records),'C01_expected_exit1':len(negative),
 'compatibility_counts':[r['tests'] for r in compat],'nonzero_records':value['nonzero_records']}))
