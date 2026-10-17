"""Independent exact-blob export and bounded R2 delivery/preservation audit."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parent
REPO=Path('C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800')
COMMIT='a1e5be00909172429d792b6c41bdaf384258694e'
PATCH='ad71284f3b6ffc8454ee1d1e30933c8e39d7c1d8'
BASE='38aca9dcc8d027409b95193e9cc142c2336b76d3'
WORKFLOW='3ed8dcba2f921c7a89b7f1d2ef9f6ace40aed583'
STAGE=ROOT/'.local/stages/A02-review-portability-R2'/COMMIT
SELECTION=['src/annotation','examples/a02','tests/fixtures/a02','tests/fixtures/contracts/unknown',
           'tests/test_a02.py','tests/test_a02_r1.py','tests/test_a02_portability_r2.py','pyproject.toml']
IDENTITY='examples/a02/R1/identity.py'
def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def git(*args):return subprocess.check_output(['git','-C',str(REPO),*args])
def tree(commit):
    result={}
    for row in git('ls-tree','-r','-z',commit).split(b'\0'):
        if row:
            metadata,name=row.split(b'\t',1);mode,kind,oid=metadata.decode().split()
            assert kind=='blob' and mode in ('100644','100755')
            result[name.decode('utf-8')]=oid
    return result
class Blobs:
    def __init__(self):self.p=subprocess.Popen(['git','-C',str(REPO),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    def read(self,oid):
        self.p.stdin.write(oid.encode()+b'\n');self.p.stdin.flush()
        header=self.p.stdout.readline().decode().split();assert header[:2]==[oid,'blob']
        data=self.p.stdout.read(int(header[2]));assert self.p.stdout.read(1)==b'\n'
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid
        return data
    def close(self):self.p.stdin.close();self.p.wait()
def main():
    STAGE.mkdir(parents=True,exist_ok=False)
    before,after,patch=tree(BASE),tree(COMMIT),tree(PATCH)
    modified=[p for p in before if before[p]!=after.get(p)]
    assert modified==[IDENTITY],modified
    changed=git('diff','--name-only',BASE,COMMIT).decode().splitlines()
    allowed=('examples/a02/portability-R2/','docs/evidence/A02/execution/portability-R2/')
    assert all(p in (IDENTITY,'tests/test_a02_portability_r2.py','docs/tasks/A02-portability-R2-execution-report.md') or p.startswith(allowed) for p in changed)
    delivery_only=git('diff','--name-only',PATCH,COMMIT).decode().splitlines()
    assert all(p.startswith('docs/evidence/A02/execution/portability-R2/') or p=='docs/tasks/A02-portability-R2-execution-report.md' for p in delivery_only)
    b=Blobs();exports={}
    try:
        for label,commit,mapping in [('base',BASE,before),('candidate',COMMIT,after)]:
            target=STAGE/('raw '+label+' no Git')
            target.mkdir()
            paths=git('ls-tree','-r','--name-only',commit,*SELECTION).decode().splitlines()
            entries=[]
            for p in paths:
                data=b.read(mapping[p]);dest=target/p
                dest.resolve().relative_to(target.resolve());dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
                assert sha(dest.read_bytes())==sha(data)
                entries.append({'path':p,'git_blob':mapping[p],'sha256':sha(data),'bytes':len(data)})
            exports[label]={'commit':commit,'root':str(target),'checkout_commit':None,'files':entries}
        manifestpath='docs/evidence/A02/execution/portability-R2/sha256-manifest.json'
        manifestraw=b.read(after[manifestpath]);assert sha(manifestraw)=='6a1c4fd174d4f2a44ae975da0995bfca0fae4b6c853406343ab98d9036b529e9'
        manifest=json.loads(manifestraw);checks=[]
        for p,h in manifest['files_sha256'].items():
            raw=b.read(after[p]);checks.append({'path':p,'sha256':h,'git_matches':sha(raw)==h})
        assert all(c['git_matches'] for c in checks)
        reportpath='docs/tasks/A02-portability-R2-execution-report.md'
        reportraw=b.read(after[reportpath]);assert sha(reportraw)=='afb339fda44156cbb2ba1aaf4589b65e0746afedc3b2f3aa2a88403eae9b1a34'
        save(OUT/'delivery-manifest.json',{'target_commit':COMMIT,'manifest_sha256':sha(manifestraw),'report_sha256':sha(reportraw),'entries':checks})
        save(OUT/'retained-author-failures.json',{'target_commit':COMMIT,'files':[{'path':p,'git_blob':after[p],'sha256':sha(b.read(after[p]))} for p in after if p.startswith('docs/evidence/A02/execution/portability-R2/') and ('before' in p or 'encoding' in p or 'audit' in p or 'freeze' in p)],
            'note':'Retained by exact final Git object; not rewritten or normalized. New functional evidence is independent.'})
        old_identity=b.read(before[IDENTITY]);new_identity=b.read(after[IDENTITY])
        def function(raw):
            txt=raw.decode();node=next(n for n in ast.parse(txt).body if isinstance(n,ast.FunctionDef) and n.name=='source_binding')
            return ''.join(txt.splitlines(keepends=True)[node.lineno-1:node.end_lineno])
        assert function(old_identity)==function(new_identity)
        handoff=git('show',WORKFLOW+':docs/tasks/A02-portability-R2-review-handoff.md')
        (OUT/'frozen-handoff.md').write_bytes(handoff)
    finally:b.close()
    ancestor={c:subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',c,COMMIT]).returncode for c in (BASE,PATCH)}
    assert not any(ancestor.values())
    checkpoints={}
    for p in ('docs/evidence/A02/review/sha256-manifest.json','docs/evidence/A02/review/formal/sha256-manifest.json',
              'docs/evidence/A02/review-R1/sha256-manifest.json','docs/evidence/A02/review-portability-R2-preparation/sha256-manifest.json'):
        index=ROOT/p;checkpoints[p]=sha(index.read_bytes())
        for item in json.loads(index.read_text(encoding='utf-8'))['files']:
            assert sha((ROOT/item['path']).read_bytes())==item['sha256'],item['path']
            checkpoints[item['path']]=item['sha256']
    save(OUT/'preserved-review-index.json',{'files_sha256':checkpoints,'unique_files':len(checkpoints)})
    (OUT/'identity.diff.txt').write_bytes(git('diff',BASE,COMMIT,'--',IDENTITY))
    result={'base':BASE,'patch':PATCH,'target_commit':COMMIT,'dispatch_workflow':'6b77c436742cf2826083b109d8ed86b85539cba6','handoff_workflow':WORKFLOW,
        'stage':str(STAGE),'exports':exports,'changed_paths':changed,'delivery_only_paths':delivery_only,
        'existing_files_modified':modified,'old_git_files_preserved':len(before)-len(modified),'source_binding_function_bytes_unchanged':True,
        'ancestor_exit_codes':ancestor,'source_worktree_head':git('rev-parse','HEAD').decode().strip(),'source_worktree_status':git('status','--short').decode().splitlines()}
    assert result['source_worktree_head']==COMMIT and not result['source_worktree_status']
    save(OUT/'bootstrap.json',result)
    print(json.dumps({'changed_paths':len(changed),'manifest_entries':len(checks),'old_git_files_preserved':len(before)-1,'review_files_preserved':len(checkpoints),
        'exported':{k:len(v['files']) for k,v in exports.items()},'source_binding_unchanged':True}))
if __name__=='__main__':main()
