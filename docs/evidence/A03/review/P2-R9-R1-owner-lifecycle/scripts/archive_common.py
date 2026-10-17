# -*- coding: utf-8 -*-
"""Archive actual saved records; leave failed collector unchanged/unrerun."""
import hashlib
import json
from pathlib import Path
import re
from evidence import WORK,EV,TARGET,MAP,raw
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R9-R1-owner-lifecycle';REPORT=ROOT/'docs/tasks/A03-P2-R9-R1-owner-lifecycle-review-report.md'
FIELD_RESET='NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION';FAILURES={'case-boundaries-review-01','release-review-01'}
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def links(pending=()):
    rows=[]
    for ref in re.findall(r'\[[^\]]+\]\(([^)]+)\)',REPORT.read_text(encoding='utf8')):
        assert '://' not in ref;p=(REPORT.parent/ref).resolve();assert p.is_relative_to(ROOT) and (p.exists() or p in pending),ref
        rows.append({'reference':ref,'exists':p.exists()})
    return rows
def preservation():
    rows=[]
    for p in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
        if p.is_file() and not p.is_relative_to(OUT):rows.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p)])
    for p in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
        if p!=REPORT:rows.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p)])
    rows.sort();digest=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest();expected=load(OUT/'historical-preservation.json')
    assert len(rows)==expected['count']==7383 and sum(r[1] for r in rows)==expected['bytes']==186511736
    assert digest==expected['inventory_sha256']=='43da522f7c5df481023e02891354dd098f6b2f4daf6597420c864db7dfdde4f0'
    return {'count':len(rows),'bytes':sum(r[1] for r in rows),'inventory_sha256':digest}
def processes(skip=()):
    rows=[]
    for d in sorted((OUT/'runs').iterdir()):
        if d.name in skip:continue
        pre=load(d/'registration.json');start=load(d/'started.json');end=load(d/'completion.json');expected=1 if d.name in FAILURES else 0
        assert pre['argv']==end['argv'] and pre['cwd']==end['cwd'] and 0<pre['timeout_seconds']<=90
        assert pre['entry_sha256']==sha(d/'entry-source.py') and start['pid']==end['pid']
        assert end['exit_code']==expected and not end['timed_out'] and not end['alive_after_wait']
        if 'group' in pre:assert pre['functional_round']==1 and not pre['product_clock_or_deadline_modified']
        rows.append({'record':d.relative_to(OUT).as_posix(),'pid':end['pid'],'exit_code':end['exit_code'],'argv':pre['argv'],'cwd':pre['cwd'],
          'timeout_seconds':pre['timeout_seconds'],'alive':False,'timed_out':False,'entry_sha256':pre['entry_sha256'],
          'registration_sha256':sha(d/'registration.json'),'completion_sha256':sha(d/'completion.json'),
          'stdout_sha256':sha(d/'stdout.log'),'stderr_sha256':sha(d/'stderr.log'),
          'classification':'REVIEW_AUDIT_ASSERTION_CORRECTED_ONCE' if d.name=='case-boundaries-review-01' else 'COLLECTOR_FAILURE_RETAINED_UNCORRECTED' if d.name=='release-review-01' else 'COMPLETED'})
    assert {r['record'].split('/')[-1] for r in rows if r['exit_code']}==FAILURES
    return rows
def git_processes():
    rows=[]
    for d in sorted((OUT/'git-processes').iterdir()):
        pre=load(d/'preregistered.json');start=load(d/'started.json');end=load(d/'completed.json')
        assert start['pid']==end['pid'] and end['exit_code']==0 and not end['timed_out'] and not end['alive']
        assert pre['stdin_sha256']==sha(d/'stdin.bin') and pre['entry_source_sha256']==sha(OUT/'runs/freeze-01/entry-source.py')
        assert pre['timeout_seconds']==30 and pre['argv'][:3]==['git','-c','core.longpaths=true']
        assert end['stdout_sha256']==sha(d/'stdout.bin') and end['stderr_sha256']==sha(d/'stderr.bin')
        rows.append({'record':d.relative_to(OUT).as_posix(),'pid':end['pid'],'exit_code':0,'argv':pre['argv'],'cwd':pre['cwd'],'alive':False,'timed_out':False,
          'stdin_sha256':pre['stdin_sha256'],'stdout_sha256':end['stdout_sha256'],'stderr_sha256':end['stderr_sha256'],
          'registration_sha256':sha(d/'preregistered.json'),'completion_sha256':sha(d/'completed.json')})
    assert len(rows)==5;return rows
def nested_records():
    root=Path(load(OUT/'independent-run.json')['run_root']).resolve();own=load(OUT/'independent-driver.json');rows=[]
    assert root.is_relative_to(WORK)
    starts=sorted(root.rglob('started.json'))
    assert len(starts)==len(list(root.rglob('preregistered.json')))==len(list(root.rglob('completed.json')))==16
    for p in starts:
        d=p.parent;pre=load(d/'preregistered.json');start=load(p);end=load(d/'completed.json');direct=d.parent==root/'processes'
        expected=90 if direct and d.name=='D2-execute' else 0
        assert start['pid']==end['pid'] and end['exit_code']==expected and not end['alive'] and not end.get('timed_out',end.get('timeout',True))
        assert pre['argv'] and pre['cwd'] and 0<pre['timeout_seconds']<=45
        source=own['file'] if direct else 'src/annotation/runtime/recovery/native_observation.py'
        digest=own['sha256'] if direct else hashlib.sha256(raw(source)).hexdigest()
        assert pre['script_sha256']==digest==sha(d/'script-snapshot.py')
        if direct:assert pre['expected_exit']==expected and pre['inputs_sha256']==hashlib.sha256(raw(EV+'inputs.json')).hexdigest()
        elif 'input_sha256' in pre:assert sha(d/'request.json')==pre['input_sha256']
        for s in ('stdout','stderr'):
            if s+'_sha256' in end:assert sha(d/(s+'.txt'))==end[s+'_sha256']
        rows.append({'record':d.relative_to(OUT).as_posix(),'pid':end['pid'],'exit_code':expected,'argv':pre['argv'],'cwd':pre['cwd'],
          'timeout_seconds':pre['timeout_seconds'],'alive':False,'timed_out':False,'source':source,'source_sha256':digest,
          'registration_sha256':sha(d/'preregistered.json'),'completion_sha256':sha(d/'completed.json'),
          'stdout_sha256':sha(d/'stdout.txt'),'stderr_sha256':sha(d/'stderr.txt')})
    assert sum(r['exit_code']==90 for r in rows)==1;return rows
