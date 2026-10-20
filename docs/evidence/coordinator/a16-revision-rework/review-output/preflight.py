"""Verify the frozen revision, exact raw inputs and preservation without product execution."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

REPO=Path('D:/1800')
ROOT=Path('D:/1800-worktrees/a16-r1-review')
OUT=ROOT/'docs/evidence/A16/independent-r1-review'
E=ROOT/'docs/evidence/A16/current-readonly/revisions/frame-binding-r1'
FINAL='8ab0944116b5230b8e69c2f129b635435c243d55'
OLD='4fe417d5246f20fbbbedc577495c7ca400d4ded8'
BASE='7432122b9fd5602785ebfb2b3f24e407fdf76eda'
env=dict(os.environ,GIT_NO_LAZY_FETCH='1')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','-c','core.longpaths=true']+list(args),cwd=str(REPO),env=env)
def save(name,value):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
def tree(commit):
    result={}
    for entry in git('ls-tree','-rz',commit).split(b'\0'):
        if entry:
            header,path=entry.split(b'\t',1);result[path.decode()]=header.decode().split()
    return result

raw=(REPO/'docs/evidence/coordinator/a16-revision-delivery/input-raw-manifest.json').read_bytes()
assert sha(raw)=='35d82218dd9c39db340b9d78f2dce4801af430db92e5c2e3ca6738f9b9bf4562'
with (OUT/'input-raw-manifest.coordinator.json').open('xb') as stream:stream.write(raw)
manifest=json.loads(raw);assert len(manifest['members'])==111
trees={name:tree(name) for name in (BASE,OLD,FINAL)}
members=[]
for item in manifest['members']:
    path=item['path'];data=(ROOT/path).read_bytes()
    assert len(data)==item['bytes'] and sha(data)==item['sha256'],path
    mode,kind,blob=trees[FINAL][path]
    assert data==git('cat-file','blob',blob),path
    members.append({**item,'mode':mode,'type':kind,'blob':blob})
for filename,expected in [('candidate-manifest.json','071340237c76a7159bd90485e17a774c2f870114baef0199172a2fc5f9547efc'),
    ('delivery-manifest.json','91d126dcd7204f71bedc3e9b3ca64a84421c536da177376b5a92c36a35ed5c59'),
    ('author-report.json','4607e8333e552f1a843c3486616871c7f3bb5498be7d03776d3e1ce7f4d77918')]:
    data=(E/filename).read_bytes();assert sha(data)==expected
for filename,count in [('candidate-manifest.json',19),('delivery-manifest.json',104)]:
    data=json.loads((E/filename).read_bytes());assert len(data['members'])==count
    for item in data['members']:
        content=(ROOT/item['path']).read_bytes()
        assert len(content)==item['size'] and sha(content)==item['sha256'],item['path']
base_changed=[p for p,value in trees[BASE].items() if trees[FINAL].get(p)!=value]
assert len(trees[BASE])==31259 and not base_changed
old_evidence=[p for p in trees[OLD] if p.startswith('docs/evidence/A16/current-readonly/')]
assert len(old_evidence)==39 and all(trees[OLD][p]==trees[FINAL].get(p) for p in old_evidence)
added=sorted(set(trees[FINAL])-set(trees[OLD]))
deleted=sorted(set(trees[OLD])-set(trees[FINAL]))
modified=sorted(p for p in trees[OLD] if p in trees[FINAL] and trees[OLD][p]!=trees[FINAL][p])
assert len(added)==100 and len(modified)==5 and not deleted
dispatch=git('show','ed182f685db56be8b98d3d97782ee44ee71c0981:docs/tasks/A16-revision-fixed-independent-review.md')
assert sha(dispatch)=='6a28c1e52cb231b28e42016a6af74833fd01902e758f53e7fad7642189bc2da5'
with (OUT/'dispatch.raw.md').open('xb') as stream:stream.write(dispatch)
save('input-raw-manifest.independent.json',{'task':'A16','revision':'R01-R04','final':FINAL,'members':members})
save('preflight-result.json',{'result':'PASS_RAW_ONLY','raw_verified':111,'candidate_dependencies_verified':19,
    'delivery_members_verified':104,'base_members_preserved':31259,'original_A16_evidence_preserved':39,
    'diff_added':100,'diff_modified':modified,'diff_deleted':deleted,'parent_initializer_present':True,
    'product_run':False,'author_directory_read':False,'lazy_fetch':False,
    'tooling_note':'An initial git diff from raw directory had no repository; no product ran. Corrected read uses D:/1800 explicitly.'})
print(json.dumps({'raw':111,'candidate_dependencies':19,'delivery_members':104,
    'base_preserved':31259,'old_A16_evidence':39,'status':'PASS_RAW_ONLY'}))
