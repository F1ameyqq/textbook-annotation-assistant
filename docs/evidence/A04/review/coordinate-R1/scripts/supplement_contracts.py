import hashlib,io,json,os,subprocess,sys,tarfile,time
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];STAGE=Path('D:/1800/.local/stages/A04-review/coordinate-R1')
ROOT=STAGE/'frozen input with spaces';REPO='C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800'
TARGET='a86eca6ec87ced20dc3a8bcc8f2c87d329e87c39'
archive=subprocess.check_output(['git','-C',REPO,'archive','--format=tar.gz',TARGET,'examples/contracts'])
(OUT/'inputs/contracts-examples-supplement.tar.gz').write_bytes(archive)
inventory=[]
with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as t:
    for m in t.getmembers():
        p=(ROOT/m.name).resolve();p.relative_to(ROOT.resolve())
        if m.isdir():p.mkdir(parents=True,exist_ok=True);continue
        assert m.isfile();assert not p.exists()
        data=t.extractfile(m).read();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        inventory.append({'path':m.name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1',TEMP=str(STAGE),TMP=str(STAGE),PYTHONIOENCODING='utf-8')
args=[sys.executable,'-m','unittest','discover','-s','tests','-p','test_contracts*.py','-v']
t=time.time();p=subprocess.run(args,cwd=str(ROOT),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
(OUT/'reproduction/contracts-after-input-supplement.log').write_bytes(p.stdout)
r={'target_commit':TARGET,'reason':'Reviewer export omitted delivered examples/contracts; original failure log preserved',
 'product_changed':False,'new_input_files':inventory,'archive_sha256':hashlib.sha256(archive).hexdigest(),
 'args':args,'cwd':str(ROOT),'returncode':p.returncode,'elapsed_seconds':time.time()-t,
 'summary':p.stdout.decode('utf-8','replace').splitlines()[-5:]}
(OUT/'reproduction/contracts-after-input-supplement.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps(r));raise SystemExit(p.returncode)
