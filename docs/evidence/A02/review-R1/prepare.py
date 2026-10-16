"""Raw immutable R1 export and independent delivery/preservation audit."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path('D:/1800')
OUT=Path(__file__).resolve().parent
REPO=Path('C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800')
COMMIT='38aca9dcc8d027409b95193e9cc142c2336b76d3'
BASE='5c9285720c8628c5198bedeadfc9f6bc7826a914'
SOURCE=OUT/'source-38aca9dc'
PATHS=['src/annotation','examples/a02','examples/contracts','tests/fixtures/a02','tests/fixtures/contracts',
       'tests/test_a02.py','tests/test_a02_r1.py','tests/test_contracts.py','tests/test_contracts_platform_refs.py','pyproject.toml']

def git(*args):return subprocess.check_output(['git','-C',str(REPO),*args])
def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def tree(commit):
    result={}
    for rec in git('ls-tree','-r','-z',commit).split(b'\0'):
        if rec:
            meta,name=rec.split(b'\t',1);mode,kind,oid=meta.decode().split()
            assert kind=='blob' and mode in ('100644','100755')
            result[name.decode('utf-8')]=oid
    return result

class Blobs:
    def __init__(self):
        self.p=subprocess.Popen(['git','-C',str(REPO),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    def read(self,oid):
        self.p.stdin.write(oid.encode()+b'\n');self.p.stdin.flush()
        header=self.p.stdout.readline().decode().split();assert header[:2]==[oid,'blob']
        data=self.p.stdout.read(int(header[2]));assert self.p.stdout.read(1)==b'\n'
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid
        return data
    def close(self):self.p.stdin.close();self.p.wait()

def main():
    SOURCE.mkdir(parents=True,exist_ok=False)
    current,old=tree(COMMIT),tree(BASE)
    selected=git('ls-tree','-r','--name-only',COMMIT,*PATHS).decode().splitlines()
    changed=git('diff','--name-only',BASE,COMMIT).decode().splitlines()
    allowed=('src/annotation/delivery/mock/','tests/fixtures/a02/R1/','examples/a02/R1/','docs/evidence/A02/execution/R1/')
    invalid=[p for p in changed if not(p.startswith(allowed) or p=='docs/tasks/A02-rework-R1-report.md' or (p.startswith('tests/test_a02') and p.endswith('.py')))]
    assert not invalid,invalid
    source_entries=[];b=Blobs()
    try:
        for path in selected:
            data=b.read(current[path]);dest=SOURCE/path
            dest.resolve().relative_to(SOURCE.resolve());dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
            assert sha(dest.read_bytes())==sha(data)
            source_entries.append({'path':path,'git_blob':current[path],'sha256':sha(data),'bytes':len(data)})
        manifest_path='docs/evidence/A02/execution/R1/freeze-sha256-manifest.json'
        raw=b.read(current[manifest_path]);assert sha(raw)=='9df33152c66e3e0ea2cb72ff3bc4162063961412e6fd007d06a6ff343fa61ea0'
        freeze=json.loads(raw)
        freeze_checks=[]
        for path,digest in freeze['files_sha256'].items():
            blob=b.read(current[path]);disk=(REPO/path).read_bytes()
            freeze_checks.append({'path':path,'sha256':digest,'git_matches':sha(blob)==digest,'disk_matches':sha(disk)==digest})
        assert all(e['git_matches'] and e['disk_matches'] for e in freeze_checks)
        report_path='docs/tasks/A02-rework-R1-report.md'
        report=b.read(current[report_path]);assert sha(report)=='3b903c24e09a186b778c04f30354dea6c41f3925f4b8cafcf3be4b04b0516167'
        save(OUT/'delivery-manifest-check.json',{'target_commit':COMMIT,'freeze_manifest_sha256':sha(raw),'report_sha256':sha(report),'entries':freeze_checks,
            'historical_manifest_exception':'Initial 960-entry manifest report pointer is pre-final; not used to verify final report. Final freeze manifest covers final report and immutable initial manifest.'})
    finally:b.close()
    preserved=[]
    for path,oid in old.items():
        if path.startswith(('docs/evidence/A02/execution/','tests/fixtures/a02/','examples/a02/')) or path=='docs/tasks/A02-execution-report.md':
            preserved.append({'path':path,'base_blob':oid,'current_blob':current.get(path),'unchanged':current.get(path)==oid})
    assert all(e['unchanged'] for e in preserved)
    old_review={}
    for index in (ROOT/'docs/evidence/A02/review/sha256-manifest.json',ROOT/'docs/evidence/A02/review/formal/sha256-manifest.json'):
        old_review[index.relative_to(ROOT).as_posix()]=sha(index.read_bytes())
        for item in json.loads(index.read_text(encoding='utf-8'))['files']:
            assert sha((ROOT/item['path']).read_bytes())==item['sha256'],item['path']
            old_review[item['path']]=item['sha256']
    save(OUT/'old-review-preservation.json',{'files_sha256':old_review,'count':len(old_review)})
    production_diff=git('diff',BASE,COMMIT,'--','src/annotation').decode()
    (OUT/'production.diff.txt').write_text(production_diff,encoding='utf-8')
    ancestors={ref:subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',ref,COMMIT]).returncode
        for ref in (BASE,'13ddf83083224ffafc17a4f57cf2c1a1a1ae02b2','4e42668ab28eda37a37285285d2f6c595d3bba12')}
    assert not any(ancestors.values())
    save(OUT/'frozen-export.json',{'target_commit':COMMIT,'base_commit':BASE,'source_root':str(SOURCE),'checkout_commit':None,
        'files':source_entries,'changed_paths':changed,'out_of_scope':invalid,'ancestor_exit_codes':ancestors,'old_delivery_artifacts':preserved,
        'source_worktree_head':git('rev-parse','HEAD').decode().strip(),'source_worktree_status':git('status','--short').decode().splitlines()})
    print(json.dumps({'source_files_verified':len(source_entries),'changed_paths':len(changed),'final_manifest_entries':len(freeze_checks),
        'old_delivery_artifacts_preserved':len(preserved),'old_review_files_preserved':len(old_review),'source_root':str(SOURCE)}))

if __name__=='__main__':main()
