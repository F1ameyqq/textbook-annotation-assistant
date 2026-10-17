# -*- coding: utf-8 -*-
import hashlib
import json
from pathlib import Path
import re
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R8-R2-projection';REPORT=ROOT/'docs/tasks/A03-P2-R8-R2-projection-review-report.md'
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
    assert len(rows)==expected['count'] and sum(r[1] for r in rows)==expected['bytes'] and digest==expected['inventory_sha256']
    return {'count':len(rows),'bytes':sum(r[1] for r in rows),'inventory_sha256':digest}
def own_processes(skip=()):
    rows=[]
    for d in sorted((OUT/'runs').iterdir()):
        if d.name in skip:continue
        pre=load(d/'registration.json');start=load(d/'started.json');end=load(d/'completion.json')
        assert pre['argv']==end['argv'] and pre['cwd']==end['cwd'] and 0<pre['timeout_seconds']<=60
        assert pre['entry_sha256']==sha(d/'entry-source.py') and start['pid']==end['pid']
        assert end['exit_code']==0 and not end['timed_out'] and not end['alive_after_wait']
        rows.append({'run':d.name,'pid':end['pid'],'exit_code':0,'alive':False,'timed_out':False,
          'registration_sha256':sha(d/'registration.json'),'completion_sha256':sha(d/'completion.json'),
          'entry_sha256':pre['entry_sha256'],'stdout_sha256':sha(d/'stdout.log'),'stderr_sha256':sha(d/'stderr.log')})
    return rows
