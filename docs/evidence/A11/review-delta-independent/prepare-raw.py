"""Static raw-Git verification/export for the one authorized A11 review delta."""
import datetime, hashlib, json, os, subprocess
from pathlib import Path
REPO=Path('D:/1800')
REPORT=Path('D:/1800-worktrees/a11-delta-review')
RUN=Path('D:/1800-worktrees/a11-delta-run')
E=REPORT/'docs/evidence/A11/review-delta-independent'
FINAL='541d6b76cfa42655a224aeed0aab5a79a0b281aa'
PRODUCT='8ff44619b955983cc84041525c7b9176d45660f2'
BASE='c580ca63ada9e452fd5ee71e5272cf0d047d4574'
ENV=dict(os.environ,GIT_NO_LAZY_FETCH='1')
def git(*args,input=None):
    return subprocess.check_output(['git','-c','core.longpaths=true',*args],cwd=REPO,env=ENV,input=input)
def tree(ref):
    result={}
    for line in git('ls-tree','-r','-z',ref).split(b'\0'):
        if not line: continue
        meta,p=line.split(b'\t',1)
        mode,kind,sha=meta.decode().split()
        result[p.decode('utf-8')]={'mode':mode,'type':kind,'blob':sha}
    return result
def save(name,value):
    (E/name).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def blobs(ids):
    data=git('cat-file','--batch',input=('\n'.join(ids)+'\n').encode('ascii'))
    cursor=0; out={}
    for requested in ids:
        end=data.index(b'\n',cursor)
        oid,kind,size=data[cursor:end].decode().split()
        assert oid==requested and kind=='blob'
        size=int(size); cursor=end+1
        out[oid]=data[cursor:cursor+size]
        cursor+=size
        assert data[cursor:cursor+1]==b'\n'
        cursor+=1
    assert cursor==len(data)
    return out
base,final,product=tree(BASE),tree(FINAL),tree(PRODUCT)
modified=sorted(p for p in base if final.get(p)!=base[p])
expected=['docs/live-pilot-runbook.md','src/annotation/quality/live_pilot.py',
          'src/annotation/runtime/live_pilot/journal.py','src/annotation/runtime/live_pilot/runner.py']
assert modified==expected and all(p in final for p in base)
added=set(final)-set(base)
assert len(added)==111 and len(base)-len(modified)==30407
mp='docs/evidence/A11/review-delta-execution/delivery-raw-manifest.json'
raw_manifest=git('show',FINAL+':'+mp)
assert hashlib.sha256(raw_manifest).hexdigest()=='dba093ca1a7ea63f75fd6acff59a7e44f1693779cf2f6a72f4958b14de67a7e2'
manifest=json.loads(raw_manifest)['members_excluding_this_envelope']
assert len(manifest)==114 and {x['path'] for x in manifest}==set(modified)|(added-{mp})
runpaths=sorted(p for p in product if p.startswith('src/annotation/') or
    p.startswith('tests/fixtures/live_pilot/') or p in ('tests/test_live_pilot_review_delta.py',
    'docs/evidence/A11/review-delta-execution/run-delta.py',
    'docs/evidence/A11/review-delta-execution/case-catalog.json',
    'docs/evidence/A11/review-delta-execution/fixture-manifest.json',
    'docs/evidence/A11/review-delta-execution/archive-source-manifest.json'))
assert all(product[p]==final[p] for p in runpaths)
reportpaths=sorted(set(runpaths)|set(modified)|added|{'项目交接说明.md','docs/contracts-v1.md',
    'docs/tasks/A11-limited-live-runner-offline-core.md','docs/tasks/A11-limited-live-runner-execution-report.md',
    'docs/evidence/A11/execution/attempt-2/result.json'})
allids=sorted({final[p]['blob'] for p in reportpaths}|{x['blob'] for x in manifest})
data=blobs(allids)
total=0
for member in manifest:
    raw=data[member['blob']]
    assert final[member['path']]=={k:member[k] for k in ('mode','type','blob')}
    assert len(raw)==member['bytes'] and hashlib.sha256(raw).hexdigest()==member['sha256']
    total+=len(raw)
assert total==6871732
exports=[]
for root,paths in ((RUN,runpaths),(REPORT,reportpaths)):
    for p in paths:
        raw=data[final[p]['blob']]
        dest=root/p
        assert not dest.exists()
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(raw)
        assert dest.read_bytes()==raw
        if root==RUN: exports.append(dict(path=p,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),**final[p]))
for ref,path in [('088cc790','docs/tasks/A11-review-delta-independent-dispatch.md'),
                 ('73ded167','docs/tasks/A11-review-findings-correction.md'),
                 ('088cc790','docs/evidence/coordinator/a11-review-delta-20261020/preflight.json')]:
    (E/('dispatch-'+Path(path).name)).write_bytes(git('show',ref+':'+path))
save('run-export-manifest.json',{'product_commit':PRODUCT,'run_root':str(RUN),'members':exports})
save('integrity-preflight.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'author_final':FINAL,'product_commit':PRODUCT,'author_base':BASE,'modified_allowed_paths':modified,
    'protected_old_paths':30407,'added_paths':111,'raw_members':114,'raw_member_bytes':total,
    'author_manifest_sha256':hashlib.sha256(raw_manifest).hexdigest(),
    'runtime_raw_members':len(exports),'runtime_product_to_final_unchanged':True,'suite_invocations':0,
    'raw_git_export':True,'all_git_lazy_fetch_disabled':True})
print(json.dumps({'raw_verified':114,'bytes':total,'protected':30407,'modified':modified,
                  'added':111,'runtime_exported':len(exports)}))
