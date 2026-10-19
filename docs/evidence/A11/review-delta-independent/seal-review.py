"""Package only the authorized new independent delta report and evidence as raw blobs."""
import datetime,hashlib,json,os,re,subprocess
from pathlib import Path
ROOT=Path('D:/1800-worktrees/a11-delta-review')
E=ROOT/'docs/evidence/A11/review-delta-independent'
BASE='541d6b76cfa42655a224aeed0aab5a79a0b281aa'
ENV=dict(os.environ,GIT_NO_LAZY_FETCH='1')
def git(*args,input=None):
    return subprocess.check_output(['git','-c','core.longpaths=true',*args],cwd=ROOT,env=ENV,input=input)
def tree(ref):
    out={}
    for line in git('ls-tree','-r','-z',ref).split(b'\0'):
        if line:
            meta,path=line.split(b'\t',1); out[path.decode('utf-8')]=meta.decode()
    return out
def save(name,value):
    (E/name).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
baseline=tree(BASE)
report=ROOT/'docs/tasks/A11-review-delta-independent-report.md'
links=[]
for target in re.findall(r'\]\(([^)]+)\)',report.read_text(encoding='utf-8')):
    if '://' in target: continue
    path=(report.parent/target.split('#')[0]).resolve()
    if path==E/'review-raw-manifest.json': continue
    assert path.exists(),target
    links.append(target)
save('scope-and-document-check.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'author_final':BASE,'author_final_paths':len(baseline),'report_links_checked':links,'missing_links':[],
    'allowed_additions':['docs/evidence/A11/review-delta-independent/','docs/tasks/A11-review-delta-independent-report.md'],
    'product_or_test_invocations':0})
paths=sorted([p for p in E.rglob('*') if p.is_file() and p.name!='review-raw-manifest.json']+[report])
members=[]
for path in paths:
    rel=path.relative_to(ROOT).as_posix(); raw=path.read_bytes()
    assert rel not in baseline
    members.append({'path':rel,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                    'mode':'100644','type':'blob','blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()})
save('review-raw-manifest.json',{'author_final':BASE,'running_product':'8ff44619b955983cc84041525c7b9176d45660f2',
    'decision':'PASS_R01_R02_LIMITED_OFFLINE_DELTA','delta_suite_runs':1,'delta_tests_passed':6,
    'old_suite_runs':0,'raw_members_excluding_this_manifest':len(members),
    'raw_member_bytes_excluding_this_manifest':sum(x['bytes'] for x in members),'members':members})
paths.append(E/'review-raw-manifest.json')
rels=[p.relative_to(ROOT).as_posix() for p in paths]
ids=git('hash-object','-w','--no-filters','--stdin-paths',input=('\n'.join(rels)+'\n').encode('utf-8')).decode().splitlines()
assert len(ids)==len(paths)
git('update-index','-z','--index-info',input=b''.join(('100644 '+oid+'\t'+rel+'\0').encode('utf-8') for oid,rel in zip(ids,rels)))
tree_id=git('write-tree').decode().strip(); staged=tree(tree_id)
assert all(staged.get(p)==value for p,value in baseline.items())
assert set(staged)-set(baseline)==set(rels)
raw=git('cat-file','--batch',input=('\n'.join(ids)+'\n').encode('ascii')); cursor=0
for oid,path in zip(ids,paths):
    end=raw.index(b'\n',cursor); actual,kind,size=raw[cursor:end].decode().split()
    assert actual==oid and kind=='blob'; size=int(size); cursor=end+1
    assert raw[cursor:cursor+size]==path.read_bytes(); cursor+=size
    assert raw[cursor:cursor+1]==b'\n'; cursor+=1
assert cursor==len(raw)
digest=hashlib.sha256((E/'review-raw-manifest.json').read_bytes()).hexdigest()
print(json.dumps({'raw_members_excluding_manifest':len(members),
    'raw_bytes_excluding_manifest':sum(x['bytes'] for x in members),'manifest_sha256':digest,
    'added_paths':len(rels),'old_author_final_paths_preserved':len(baseline),'staged_tree':tree_id}))
