# -*- coding: utf-8 -*-
import hashlib
import json
from pathlib import Path
import re
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R9-failure';REPORT=ROOT/'docs/tasks/A03-P2-R9-failure-review-report.md'
FIELD_RESET='NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'
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
    assert len(rows)==expected['count']==7030 and sum(r[1] for r in rows)==expected['bytes']==156577683
    assert digest==expected['inventory_sha256']=='cf681152d911e43219f15371e238ce9c7c72a3c9a60fb05185888e3a1c4f3194'
    return {'count':len(rows),'bytes':sum(r[1] for r in rows),'inventory_sha256':digest}
def processes(skip=()):
    rows=[]
    for d in sorted((OUT/'runs').iterdir()):
        if d.name in skip:continue
        pre=load(d/'registration.json');start=load(d/'started.json');end=load(d/'completion.json')
        expected=1 if d.name=='independent-review-01' else 0
        assert pre['argv']==end['argv'] and pre['cwd']==end['cwd'] and 0<pre['timeout_seconds']<=45
        assert pre['entry_sha256']==sha(d/'entry-source.py') and start['pid']==end['pid']
        assert end['exit_code']==expected and not end['timed_out'] and not end['alive_after_wait']
        rows.append({'run':d.name,'pid':end['pid'],'exit_code':end['exit_code'],'alive':False,'timed_out':False,
          'argv':pre['argv'],'cwd':pre['cwd'],'timeout_seconds':pre['timeout_seconds'],'entry_sha256':pre['entry_sha256'],
          'registration_sha256':sha(d/'registration.json'),'completion_sha256':sha(d/'completion.json'),
          'stdout_sha256':sha(d/'stdout.log'),'stderr_sha256':sha(d/'stderr.log'),
          'classification':'REVIEWER_READONLY_ASSERTION_FAILURE_RETAINED' if expected else 'COMPLETED'})
    assert sum(r['exit_code']==1 for r in rows)==1
    return rows
def git_processes():
    rows=[]
    for d in sorted((OUT/'git-processes').iterdir()):
        pre=load(d/'preregistered.json');start=load(d/'started.json');end=load(d/'completed.json')
        assert start['pid']==end['pid'] and end['exit_code']==0 and not end['timed_out'] and not end['alive']
        assert pre['stdin_sha256']==sha(d/'stdin.bin') and pre['entry_source_sha256']==sha(OUT/'runs/freeze-01/entry-source.py')
        assert pre['timeout_seconds']==30 and pre['argv'][:3]==['git','-c','core.longpaths=true']
        assert end['stdout_sha256']==sha(d/'stdout.bin') and end['stderr_sha256']==sha(d/'stderr.bin')
        rows.append({'record':d.relative_to(OUT).as_posix(),'argv':pre['argv'],'cwd':pre['cwd'],'pid':end['pid'],'exit_code':0,
          'alive':False,'timed_out':False,'stdin_sha256':pre['stdin_sha256'],'stdout_sha256':end['stdout_sha256'],'stderr_sha256':end['stderr_sha256'],
          'registration_sha256':sha(d/'preregistered.json'),'completion_sha256':sha(d/'completed.json')})
    assert len(rows)==5
    return rows
