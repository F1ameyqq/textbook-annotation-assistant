"""Raw fixed final delta export and legitimate, released own L1 routing."""
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE=Path('D:/1800')
ROOT=Path('D:/1800-worktrees/a03-r1-final-review-19ab03c8')
PREVIOUS=Path('D:/1800-worktrees/a03-r1-review-54e86adf')
OUT=SOURCE/'docs/evidence/A03/R1/final-review'
FINAL='19ab03c849bfab3dcde2dc86be37c59f3add1ebe'
FROZEN='9992cd8aba10987d25dd0dc0d0874abec02b27ef'
PRODUCT='6097a06de937fee8876feccedf46920510850b83'
CALLS=[]

def sha(v):return hashlib.sha256(v).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb')as stream:stream.write((json.dumps(value,indent=2)+'\n').encode())
def run(argv,data=None):
    p=subprocess.Popen(argv,cwd=SOURCE,stdin=subprocess.PIPE if data is not None else None,
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=p.communicate(data,timeout=60)
    CALLS.append(dict(argv=argv,pid=p.pid,exit_code=p.returncode,waited=True,alive=False,
        stdout_sha256=sha(stdout),stderr=stderr.decode('utf-8','replace')))
    assert p.returncode==0,CALLS[-1]
    return stdout
def git(*args,data=None):return run(['git','-c','core.longpaths=true','-C',str(SOURCE),*args],data)

def main():
    assert not ROOT.exists(),'New review execution directory already exists'
    run(['git','-c','core.longpaths=true','clone','--shared','--no-checkout',str(SOURCE),str(ROOT)])
    run(['git','-C',str(ROOT),'symbolic-ref','HEAD','refs/heads/a03-r1-final-delta-review'])
    run(['git','-C',str(ROOT),'update-ref','HEAD',FINAL])
    prefixes=('src/annotation/','examples/a03/R1/','examples/a03/T3-closure/',
        'examples/a03/P2-R12-R1-unknown-projection/legacy-recovery/',
        'tests/fixtures/a03/R1/final/','docs/evidence/A03/R1/final-correction/')
    paths=[p for p in git('ls-tree','-r','--name-only',FINAL).decode().splitlines()
        if p.startswith(prefixes) or p in ('examples/a03/T1-capture/capture.py',
        'docs/tasks/A03-R1-final-correction-report.md')]
    packed=git('cat-file','--batch',data=''.join(FINAL+':'+p+'\n'for p in paths).encode())
    position=0;identities=[]
    for path in paths:
        end=packed.index(b'\n',position);oid,kind,size=packed[position:end].decode().split();assert kind=='blob'
        position=end+1;raw=packed[position:position+int(size)];position+=int(size)+1
        f=ROOT/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(raw)
        identities.append(dict(path=path,git_blob=oid,bytes=len(raw),sha256=sha(raw)))
    assert position==len(packed)
    execution=ROOT/'docs/evidence/A03/R1/final-correction'
    manifest=json.loads((execution/'manifest.json').read_bytes())
    for row in manifest['members']:
        raw=(ROOT/row['path']).read_bytes();assert len(raw)==row['bytes']and sha(raw)==row['sha256']
    assert sha((ROOT/'docs/tasks/A03-R1-final-correction-report.md').read_bytes())=='40f030a5c4a1f538c35dcd196b7375f8b8f86d5029a59be41b8bb19d1dc0659e'
    assert sha((execution/'manifest.json').read_bytes())=='22614eaeeaeb6ae6a14e9846e4ab552d3b9eed0ce5602c9dcbb044044e4ee405'
    assert not git('diff','--name-only',PRODUCT,FINAL,'--','src').strip()
    assert not git('diff','--name-only',FROZEN,FINAL,'--','src','examples/a03/R1/final.py',
        'examples/a03/R1/final_controls.py','examples/a03/R1/deltas.py','tests/fixtures/a03/R1/final').strip()
    changed=git('diff','--name-only','54e86adfaf144093a688b62fe0dad5190ceb2fa6',FINAL).decode().splitlines()
    assert all(p.startswith(('examples/a03/R1/','tests/fixtures/a03/R1/final/',
        'docs/evidence/A03/R1/final-correction/'))or p=='docs/tasks/A03-R1-final-correction-report.md'for p in changed)
    own=PREVIOUS/'docs/evidence/A03/R1/review'
    case=own/'business/cases/M2-sufficient';capture=own/'L1/captures/after-release'
    continuation=[]
    for kind,path in [('runtime',case/'runtime/runtime.sqlite3'),('target',case/'target/target.sqlite3')]:
        raw=path.read_bytes();assert raw==(capture/(kind+'.sqlite3')).read_bytes(),kind
        continuation.append(dict(path=str(path),bytes=len(raw),sha256=sha(raw),fixed_capture=str(capture/(kind+'.sqlite3'))))
    sql=json.loads((capture/'SQL.json').read_bytes())
    books=sql['runtime']['tables']['books']
    assert len(books)==1 and books[0]['owner']is None and books[0]['pid']is None and books[0]['lease']==0 and books[0]['phase']=='RELEASED'
    assert len(sql['runtime']['tables']['legacy'])==2
    anchor=json.loads((case/'anchor.json').read_bytes())
    assert Path(anchor['anchor_path']).resolve()==(case/'anchor.json').resolve()
    assert Path(anchor['state_dir']).resolve()==(case/'runtime').resolve()
    route=ROOT/'route-project'
    old=route/'docs/evidence/A03/R1/execution'
    mappings=[(old/'candidate-1/business/cases/M1',own/'business/cases/M1'),
        (old/'candidate-1/business/cases/M2-sufficient',case),(old/'deltas-correction/L1',own/'L1')]
    for link,target in mappings:
        link.parent.mkdir(parents=True,exist_ok=True)
        assert target.is_relative_to(PREVIOUS) and target.exists()
        # Junctions route to the original owned identities; no database is copied
        # or relabelled to become a positive continuation.
        script="New-Item -ItemType Junction -Path '"+str(link)+"' -Target '"+str(target)+"' | Out-Null"
        run(['powershell','-NoProfile','-Command',script])
        assert link.resolve()==target.resolve(),(link,target,link.resolve())
    ev=route/'docs/evidence/A03/R1/final-correction'
    write(ev/'preparation/checks.json',dict(continuation=continuation,
        routing_only=True,unchanged_original_preparation=str(execution/'preparation/checks.json')))
    profile=json.loads((ROOT/'src/annotation/contracts/a03_native/data/profile.json').read_bytes())
    pins=[]
    for path,expected in profile['implementation_pins']:
        f=ROOT/('src/'+path[1:])if path.startswith('@')else ROOT/'src/annotation/contracts/a03_native'/path
        assert sha(f.read_bytes())==expected;pins.append(dict(path=path,sha256=expected))
    for path,expected in profile['schema_pins']:
        assert sha((ROOT/'src/annotation/contracts/a03_native/data'/path).read_bytes())==expected
    old_manifest=SOURCE/'docs/evidence/A03/R1/review/manifest.json'
    write(OUT/'preparation.json',dict(final=FINAL,frozen=FROZEN,product=PRODUCT,root=str(ROOT),
        routing_project=str(route),exported=identities,manifest_members=len(manifest['members']),
        manifest_bytes=sum(r['bytes']for r in manifest['members']),changed_paths=changed,
        continuation=continuation,anchor=anchor,junctions=[dict(logical=str(l),actual=str(t))for l,t in mappings],
        product_pins=pins,old_review_manifest_sha256=sha(old_manifest.read_bytes()),
        original_author_live_opened=False,old_capture_SQL_opened=False,calls=CALLS))
    print(json.dumps(dict(status='FIXED_RAW_AND_OWN_CONTINUATION_READY',files=len(paths),members=len(manifest['members']),changed=len(changed))))

if __name__=='__main__':main()
