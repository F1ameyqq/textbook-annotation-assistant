# -*- coding: utf-8 -*-
"""Byte-only final archive helpers; no product imports, SQL or process scan."""
import hashlib
import json
from pathlib import Path
import re
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R8-R4-remaining'
REPORT=ROOT/'docs/tasks/A03-P2-R8-R4-remaining-review-report.md'
FAILURES={'author-process-review-01','author-process-review-02'};PHASES=('N1','N6','N7')
FIELD_RESET='NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def links(pending=()):
    rows=[]
    for ref in re.findall(r'\[[^\]]+\]\(([^)]+)\)',REPORT.read_text(encoding='utf8')):
        assert '://' not in ref
        p=(REPORT.parent/ref).resolve();assert p.is_relative_to(ROOT) and (p.exists() or p in pending),ref
        rows.append({'reference':ref,'exists':p.exists()})
    return rows
def preservation():
    rows=[]
    for p in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
        if p.is_file() and not p.is_relative_to(OUT):rows.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p)])
    for p in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
        if p!=REPORT:rows.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p)])
    rows.sort();digest=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    expected=load(OUT/'historical-preservation.json')
    assert len(rows)==expected['count']==6368 and sum(r[1] for r in rows)==expected['bytes']==144516343
    assert digest==expected['inventory_sha256']=='75f7fc0667aa094fd59cd8fa8ff2a9cb4638e46df0921b8dc370f4cc41da9adb'
    return {'count':len(rows),'bytes':sum(r[1] for r in rows),'inventory_sha256':digest}
def own_processes(skip=()):
    rows=[]
    for d in sorted((OUT/'runs').iterdir()):
        if d.name in skip:continue
        pre=load(d/'registration.json');start=load(d/'started.json');end=load(d/'completion.json')
        assert pre['argv']==end['argv'] and pre['cwd']==end['cwd'] and 0<pre['timeout_seconds']<=60
        assert pre['entry_sha256']==sha(d/'entry-source.py') and start['pid']==end['pid']
        expected=1 if d.name in FAILURES else 0
        assert end['exit_code']==expected and not end['timed_out'] and not end['alive_after_wait'],d.name
        if 'phase' in pre:assert pre['phase'] in PHASES and pre['functional_round']==1 and not pre['product_clock_or_deadline_modified']
        rows.append({'run':d.name,'pid':end['pid'],'exit_code':end['exit_code'],'alive':False,'timed_out':False,
          'argv':pre['argv'],'cwd':pre['cwd'],'timeout_seconds':pre['timeout_seconds'],
          'registration_sha256':sha(d/'registration.json'),'completion_sha256':sha(d/'completion.json'),
          'entry_sha256':pre['entry_sha256'],'stdout_sha256':sha(d/'stdout.log'),'stderr_sha256':sha(d/'stderr.log'),
          'classification':'REVIEWER_METADATA_FAILURE_RETAINED' if expected else 'COMPLETED'})
    assert {r['run'] for r in rows if r['exit_code']}==FAILURES
    return rows
