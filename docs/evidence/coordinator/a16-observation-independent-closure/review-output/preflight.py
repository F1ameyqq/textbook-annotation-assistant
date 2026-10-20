"""Independent raw/preservation verification for the observation-only candidate."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

REPO=Path('D:/1800');ROOT=Path('D:/1800-worktrees/a16-observation-review')
OUT=ROOT/'docs/evidence/A16/independent-observation-review'
E=ROOT/'docs/evidence/A16/current-readonly/revisions/observation-only'
FINAL='2453c71c070c153a22a49b772bb2696b3858f5d4';PARENT='8ab0944116b5230b8e69c2f129b635435c243d55'
BASE='7432122b9fd5602785ebfb2b3f24e407fdf76eda'
env=dict(os.environ,GIT_NO_LAZY_FETCH='1')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','-c','core.longpaths=true']+list(args),cwd=str(REPO),env=env)
def save(name,data):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as stream:json.dump(data,stream,ensure_ascii=False,indent=2);stream.write('\n')
def tree(commit):
    result={}
    for row in git('ls-tree','-rz',commit).split(b'\0'):
        if row:
            header,path=row.split(b'\t',1);result[path.decode()]=header.decode().split()
    return result

raw=(REPO/'docs/evidence/coordinator/a16-observation-delivery/input-raw-manifest.json').read_bytes()
assert sha(raw)=='2d64b70fc893868a517a2e9eafddb267f21fe657af49e3d27e67d9828048bc32'
with (OUT/'input-raw-manifest.coordinator.json').open('xb') as stream:stream.write(raw)
items=json.loads(raw)['members'];assert len(items)==59
base,parent,final=tree(BASE),tree(PARENT),tree(FINAL)
verified=[]
for item in items:
    path=item['path'];data=(ROOT/path).read_bytes();mode,kind,blob=final[path]
    assert len(data)==item['size'] and sha(data)==item['sha256'],path
    assert data==git('cat-file','blob',blob),path
    verified.append({**item,'mode':mode,'type':kind,'blob':blob})
for filename,digest in [('candidate-manifest.json','e66e9f96197871f7123ebe2ed981a587262c50fb3f6e62cdc300f8e96be5a63f'),
    ('delivery-manifest.json','ae37099d56f8462db27145ce755ec5305fceafd9ebc14ead1a1c3cd966ba8622'),
    ('author-report.json','55c1c75068f52447bb3579887819376cfc3d07ae10d8e0c5fc71307317a0cf92')]:
    assert sha((E/filename).read_bytes())==digest
for filename,count in [('candidate-manifest.json',16),('delivery-manifest.json',50)]:
    members=json.loads((E/filename).read_bytes())['members'];assert len(members)==count
    for item in members:
        data=(ROOT/item['path']).read_bytes()
        assert len(data)==item['size'] and sha(data)==item['sha256'],item['path']
assert len(base)==31259 and all(final.get(p)==v for p,v in base.items())
evidence=[p for p in parent if p.startswith('docs/evidence/A16/')]
assert len(evidence)==136 and all(final.get(p)==parent[p] for p in evidence)
added=sorted(set(final)-set(parent));deleted=sorted(set(parent)-set(final))
modified=sorted(p for p in parent if p in final and parent[p]!=final[p])
assert len(added)==48 and len(modified)==3 and not deleted
assert modified==['src/annotation/source/usense/current_readonly/gate.py',
    'src/annotation/source/usense/current_readonly/policy.py','tools/a16_current_state_probe.py']
dispatch=git('show','988a72998b4b6d8f293f21a96056db1343ceecb8:docs/tasks/A16-observation-only-fixed-independent-review.md')
assert sha(dispatch)=='e1d4b217c332f9f53dcd7b05a6ca429576feb5c2013b6a5d13be90debc038974'
with (OUT/'dispatch.raw.md').open('xb') as stream:stream.write(dispatch)
old=REPO/'docs/evidence/coordinator/a16-revision-rework/review-output'
assert sha((old/'raw-manifest.json').read_bytes())=='4f7d35c301412ea8877bb4ca1db94a74ea201003856b34417e47000a91735795'
assert sha((old/'REPORT.md').read_bytes())=='0779d6030752e01824a6b129c1fc805c4822ce004aef0369eca0c47b05d59d92'
save('input-raw-manifest.independent.json',{'task':'A16','scope':'OBSERVATION_ONLY','final':FINAL,'members':verified})
save('preflight-result.json',{'result':'PASS_RAW_ONLY','raw_verified':59,'candidate_members':16,'delivery_members':50,
    'base31259_preserved':True,'old_A16_evidence136_preserved':True,'diff_added':48,'diff_modified':modified,
    'diff_deleted':deleted,'parent_initializer_raw73_present':len((ROOT/'src/annotation/__init__.py').read_bytes())==73,
    'original_R02_REWORK_report_manifest_unchanged':True,'author_activity_read':False,'product_run':False,
    'git_lazy_fetch':False,'semantic_acceptance':'NOT_ASSESSED_BY_THIS_CHECK'})
print(json.dumps({'status':'PASS_RAW_ONLY','raw':59,'candidate':16,'delivery':50,'old_base':31259,'old_evidence':136}))
