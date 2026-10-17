"""Byte-only failure package helpers. Never imports or calls the candidate."""
import hashlib
import json
import re
from pathlib import Path
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'docs/tasks/A03-P2-R11-crash-cuts-review-report.md'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def parents(skip=()):
    result=[]
    for d in sorted((OUT/'runs').iterdir()):
        if d.name in skip:continue
        pre=load(d/'registration.json');start=load(d/'started.json');end=load(d/'completion.json')
        assert pre['argv']==end['argv'] and pre['cwd']==end['cwd'] and start['pid']==end['pid']
        assert pre['entry_sha256']==sha(d/'entry-source.py') and not end['timed_out'] and not end['alive_after_wait']
        expected=1 if d.name in ('process-audit-01','report-01') else 0
        assert end['exit_code']==expected and 0<pre['timeout_seconds']<=90
        result.append({'record':d.relative_to(OUT).as_posix(),'pid':end['pid'],'exit_code':end['exit_code'],
         'failure_kind':'STATIC_ARCHIVE_FAILURE_RETAINED' if expected else None,'argv':pre['argv'],'cwd':pre['cwd'],
         'timeout_seconds':pre['timeout_seconds'],'alive':False,'timed_out':False,'entry_sha256':pre['entry_sha256'],
         'registration_sha256':sha(d/'registration.json'),'completion_sha256':sha(d/'completion.json'),
         'stdout_sha256':sha(d/'stdout.log'),'stderr_sha256':sha(d/'stderr.log')})
    return result
def git_records():
    result=[]
    for d in sorted((OUT/'git-processes').iterdir()):
        pre=load(d/'preregistered.json');start=load(d/'started.json');end=load(d/'completed.json')
        assert start['pid']==end['pid'] and end['exit_code']==0 and not end['alive'] and not end['timed_out']
        assert pre['entry_source_sha256']==sha(OUT/'runs/freeze-01/entry-source.py') and pre['stdin_sha256']==sha(d/'stdin.bin')
        assert end['stdout_sha256']==sha(d/'stdout.bin') and end['stderr_sha256']==sha(d/'stderr.bin')
        result.append({'record':d.relative_to(OUT).as_posix(),'pid':end['pid'],'exit_code':0,'argv':pre['argv'],'cwd':pre['cwd'],
         'timeout_seconds':pre['timeout_seconds'],'alive':False,'timed_out':False,'registration_sha256':sha(d/'preregistered.json'),
         'completion_sha256':sha(d/'completed.json'),'stdout_sha256':sha(d/'stdout.bin'),'stderr_sha256':sha(d/'stderr.bin')})
    return result
def nested_records():
    rows=load(OUT/'process-and-import-review.json')['independent_nested'];root=Path(load(OUT/'independent-run.json')['run_root'])
    assert {r['record'] for r in rows}=={p.parent.relative_to(OUT).as_posix() for p in root.rglob('started.json')}
    for r in rows:
        d=OUT/r['record'];pre=load(d/'preregistered.json');start=load(d/'started.json');end=load(d/'completed.json')
        assert start['pid']==end['pid']==r['pid'] and end['exit_code']==r['exit_code'] and not end['alive'] and not end.get('timed_out',end.get('timeout',True))
        for name in ('registration','completion','stdout','stderr'):
            f={'registration':'preregistered.json','completion':'completed.json','stdout':'stdout.txt','stderr':'stderr.txt'}[name]
            assert sha(d/f)==r[name+'_sha256']
    return rows
def history():
    rows=[]
    for p in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
        if p.is_file() and not p.is_relative_to(OUT):rows.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p)])
    for p in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
        if p!=REPORT:rows.append([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p)])
    rows.sort();digest=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    previous=load(OUT/'historical-preservation.json')
    assert len(rows)==previous['count'] and sum(r[1] for r in rows)==previous['bytes'] and digest==previous['inventory_sha256']
    return previous
def links(pending=()):
    rows=[]
    for ref in re.findall(r'\[[^\]]+\]\(([^)]+)\)',REPORT.read_text(encoding='utf8')):
        p=(REPORT.parent/ref).resolve();assert p.is_relative_to(ROOT) and (p.exists() or p in pending)
        rows.append({'ref':ref,'exists':p.exists()})
    return rows
