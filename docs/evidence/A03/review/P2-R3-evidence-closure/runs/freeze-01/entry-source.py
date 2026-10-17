"""Raw Git isolation only. Does not execute delivery code or open databases."""
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT = Path('D:/1800')
OUT = ROOT / 'docs/evidence/A03/review/P2-R3-evidence-closure'
STAGE = OUT / 'input/checkout'
WF = '3ad5269fdb87802cc56c2c171e4ba69d8efafab0'
BASE = '526d264284f36f856c306db88c1d7e71c04152e1'
DELIVERY = '87606b73e0754fa670491d9fb958a416c26bfe88'
EX = 'examples/a03/P2-R3-evidence-closure/'
EV = 'docs/evidence/A03/execution/P2-R3-evidence-closure/'
REPORT = 'docs/tasks/A03-P2-R3-evidence-closure-delivery.md'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def git(*args, data=None):
    return subprocess.run(['git', *args], cwd=ROOT, input=data, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True).stdout
def tree(rev):
    result = {}
    for row in git('ls-tree', '-rz', '--full-tree', rev).split(b'\0'):
        if not row: continue
        meta, name = row.split(b'\t', 1)
        mode, typ, oid = meta.decode().split()
        result[name.decode('utf8')] = {'mode':mode, 'type':typ, 'oid':oid}
    return result
def batch(items):
    wanted = sorted(set(items))
    raw = git('cat-file', '--batch', data=('\n'.join(wanted)+'\n').encode())
    result = {}; pos = 0
    for spec in wanted:
        end = raw.index(b'\n', pos); head = raw[pos:end].decode().split(); pos = end+1
        assert len(head)==3 and head[1]=='blob', (spec, head)
        size = int(head[2]); body=raw[pos:pos+size]; pos += size
        assert raw[pos:pos+1]==b'\n'; pos += 1
        assert hashlib.sha1(b'blob '+str(size).encode()+b'\0'+body).hexdigest()==head[0]
        result[spec]=(head[0],body)
    assert pos==len(raw)
    return result
def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')

before, after, workflow = tree(BASE), tree(DELIVERY), tree(WF)
assert all(after.get(k)==v for k,v in before.items())
added = sorted(set(after)-set(before)); assert len(added)==126
assert all(p.startswith((EX,EV)) or p==REPORT for p in added)
first=batch([DELIVERY+':'+EV+'sha256-manifest.json',DELIVERY+':'+EV+'r2-input-pins.json'])
manifest_raw=first[DELIVERY+':'+EV+'sha256-manifest.json'][1]
assert sha(manifest_raw)=='16909b0445495e8a1dbbc0af8831947a06907c29714cbe8a8e6d218aeee64d72'
manifest=json.loads(manifest_raw); assert len(manifest['files'])==125
assert {x['path'] for x in manifest['files']}==set(added)-{EV+'sha256-manifest.json'}
pins=json.loads(first[DELIVERY+':'+EV+'r2-input-pins.json'][1]); assert len(pins['inputs'])==53
workflow_paths = ['AGENTS.md','docs/architecture.md','docs/contracts-v1.md','docs/coordination.md',
 'docs/tasks/A03-P2-R3-evidence-closure-review-handoff.md',
 'docs/tasks/A03-P2-R3-evidence-closure-rework.md',
 'docs/tasks/A03-P2-R2-proposal-review-report.md',
 'docs/tasks/A03-P2-R2-proposal-coordinator-decision.md',
 'docs/evidence/coordinator/heartbeat-20261017-0834/A03-R3-delivery-preflight.json',
 'docs/evidence/A03/review/P2-R2-proposal/ordinary-reference-authority.json']
workflow_paths += ['docs/evidence/A03/review/P2-R2-proposal/counterexample/evidence-id-consumer/'+p
                   for p in ['bundle.json','inner.json','outer.json','result.json','current-consumer-confirmation.json']]
requests=[DELIVERY+':'+p for p in added]
requests += [x['commit']+':'+x['path'] for x in pins['inputs']]
requests += [WF+':'+p for p in workflow_paths]
blobs=batch(requests)
for x in manifest['files']:
    oid,body=blobs[DELIVERY+':'+x['path']]
    assert len(body)==x['bytes'] and sha(body)==x['sha256']
    assert oid==after[x['path']]['oid']
assert sha(blobs[DELIVERY+':'+REPORT][1])=='c4831f0ceec0036b0bccfcc596a4a704b802f6a0ed31b9a500d341b52a0bc328'
assert sha(blobs[WF+':docs/tasks/A03-P2-R3-evidence-closure-review-handoff.md'][1])=='32f94a69537080e62624a5870820e144267e6a4584f275a8829cd1a2cec5f197'
for x in pins['inputs']:
    oid,body=blobs[x['commit']+':'+x['path']]
    assert oid==x['raw_git_sha1'] and len(body)==x['bytes'] and sha(body)==x['sha256']
    assert after[x['path']]==before[x['path']]

# Only current code, cases, output diagnostics and process receipts. No 7MB historical baseline.
chosen=[p for p in added if p.startswith(EX) or p==REPORT or
        p in [EV+x for x in ['sha256-manifest.json','r2-input-pins.json','input-index.json',
                             'process-release.json','delivery-verification.json','runner.py']] or
        p.startswith((EV+'inputs/',EV+'controls/')) or
        (p.startswith(EV+'runs/') and not '/source-snapshot/' in p and
         Path(p).name in ['exit.json','started.json','registration.json','stdout.txt','stderr.txt'])]
index=[]
def export(rev,p,dest,role):
    oid,raw=blobs[rev+':'+p]; dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f: f.write(raw)
    index.append({'commit':rev,'path':p,'file':dest.relative_to(OUT).as_posix(),
                  'bytes':len(raw),'raw_git_sha1':oid,'sha256':sha(raw),'role':role})
for p in chosen: export(DELIVERY,p,STAGE/p,'current_delivery')
for x in pins['inputs']: export(x['commit'],x['path'],STAGE/x['path'],'R2_fixed_reused')
for p in workflow_paths: export(WF,p,OUT/'input/workflow'/p,'frozen_workflow')
# Exact original proof identity, independently from workflow and delivery copies.
for p in ['bundle.json','inner.json','outer.json','result.json','current-consumer-confirmation.json']:
    original=blobs[WF+':docs/evidence/A03/review/P2-R2-proposal/counterexample/evidence-id-consumer/'+p][1]
    assert original==blobs[DELIVERY+':'+EV+'inputs/counterexample/'+p][1]

protected=[]
for path in sorted((ROOT/'docs/evidence/A03/review').rglob('*')):
    if path.is_file() and not path.is_relative_to(OUT):
        raw=path.read_bytes(); protected.append({'path':path.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':sha(raw)})
for path in sorted((ROOT/'docs/tasks').glob('A03*review*.md')):
    raw=path.read_bytes(); protected.append({'path':path.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':sha(raw)})
write(OUT/'protected-old-review-files.json',{'files':protected,'method':'raw bytes only, no database query'})
write(OUT/'input-index.json',{'workflow':WF,'base':BASE,'delivery':DELIVERY,'files':index})
write(OUT/'delivery-byte-index.json',{'workflow':WF,'base':BASE,'delivery':DELIVERY,
 'unchanged_old_git_paths':len(before),'added_paths':len(added),'author_manifest_entries':len(manifest['files']),
 'raw_files':[dict(path=p,raw_git_sha1=blobs[DELIVERY+':'+p][0],bytes=len(blobs[DELIVERY+':'+p][1]),sha256=sha(blobs[DELIVERY+':'+p][1]))for p in added],
 'frozen_at':datetime.now(timezone.utc).isoformat()})
print(json.dumps({'result':'RAW_GIT_FROZEN','added':len(added),'old_unchanged':len(before),
                  'exports':len(index),'old_review_files_protected':len(protected)}))
