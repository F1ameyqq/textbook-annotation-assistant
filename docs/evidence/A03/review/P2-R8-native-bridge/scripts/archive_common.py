# -*- coding: utf-8 -*-
"""Byte-only archive helpers, without candidate imports or live process scans."""
import hashlib
import json
from pathlib import Path
import re
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R8-native-bridge'
REPORT=ROOT/'docs/tasks/A03-P2-R8-native-bridge-review-report.md'
def load(path):return json.loads(path.read_bytes())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    with path.open('x',encoding='utf8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def links(pending=()):
    result=[]
    for ref in re.findall(r'\[[^\]]+\]\(([^)]+)\)',REPORT.read_text(encoding='utf8')):
        assert '://' not in ref
        path=(REPORT.parent/ref).resolve();assert path.is_relative_to(ROOT)
        assert path.exists() or path in pending,ref
        result.append({'reference':ref,'exists':path.exists()})
    return result
def preservation():
    rows=[]
    for path in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
        if path.is_file() and not path.is_relative_to(OUT):rows.append([path.relative_to(ROOT).as_posix(),path.stat().st_size,sha(path)])
    for path in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
        if path!=REPORT:rows.append([path.relative_to(ROOT).as_posix(),path.stat().st_size,sha(path)])
    rows.sort();digest=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    expected=load(OUT/'historical-preservation.json')
    assert len(rows)==expected['count'] and sum(r[1] for r in rows)==expected['bytes']
    assert digest==expected['inventory_sha256']
    return {'count':len(rows),'bytes':sum(r[1] for r in rows),'inventory_sha256':digest}
def own_processes(skip=()):
    result=[]
    for directory in sorted((OUT/'runs').iterdir()):
        if directory.name in skip:continue
        pre=load(directory/'registration.json');started=load(directory/'started.json');end=load(directory/'completion.json')
        assert pre['argv']==end['argv'] and pre['cwd']==end['cwd']
        assert 0<pre['timeout_seconds']<=45
        assert started['pid']==end['pid'] and not end['alive_after_wait'] and not end['timed_out']
        assert end['exit_code']==(1 if directory.name=='process-review-01' else 0)
        assert sha(directory/'entry-source.py')==pre['entry_sha256']
        result.append({'run':directory.name,'pid':end['pid'],'exit_code':end['exit_code'],'alive':False,'timed_out':False,
          'entry_sha256':pre['entry_sha256'],'registration_sha256':sha(directory/'registration.json'),
          'completion_sha256':sha(directory/'completion.json'),
          'stdout_sha256':sha(directory/'stdout.log'),'stderr_sha256':sha(directory/'stderr.log')})
    assert [r['run'] for r in result if r['exit_code']]==['process-review-01']
    return result
