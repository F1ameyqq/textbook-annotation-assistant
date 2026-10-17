"""New R2 isolation only. Fixed main parent is not the workflow/live HEAD."""
import hashlib,json,os,platform,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parent
STAGE=ROOT/'.local/stages/A01-review-integration-R2'
WORKFLOW='fe91c27939d13f9be290f8274a0d46d90f4de2f0'
MAIN='2d1dc8b97713ee06ec5bf35febe0b894ece584b2'
A01='5f872150a237b195f73c78e02e13a91d2f4f46a7'
PATCH='f8f2981a815f96147144d3747d26752b564cc9f7'
EXPECTED='0645ac862f79fb4e232e4cfbd5f6bb5055a68d62'
OUT.mkdir(parents=True,exist_ok=True);STAGE.mkdir(parents=True,exist_ok=True)
commands=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def run(args,cwd=ROOT,data=None,env=None):
 p=subprocess.run(list(map(str,args)),cwd=cwd,input=data,capture_output=True,env=env)
 commands.append(dict(argv=p.args,cwd=str(cwd),exit_code=p.returncode,stdout=p.stdout.decode('utf-8','replace'),stderr=p.stderr.decode('utf-8','replace')))
 if p.returncode:
  dump(OUT/'bootstrap-failure-commands.json',commands);raise RuntimeError(commands[-1])
 return p.stdout
def listing(ref,repo):
 rows=[]
 for part in run(['git','ls-tree','-rz','--full-tree',ref],repo).split(b'\0'):
  if part:
   meta,path=part.split(b'\t',1);mode,kind,oid=meta.decode().split();assert kind=='blob' and mode in ('100644','100755')
   rows.append(dict(path=path.decode('utf-8'),oid=oid,mode=mode))
 return rows
live_head=run(['git','rev-parse','HEAD']).decode().strip()
status=run(['git','status','--short','--branch']).decode('utf-8')
tracked={p.decode('utf-8') for p in run(['git','ls-files','-z']).split(b'\0') if p}
extra=set()
for directory in ('docs/evidence/A01','docs/evidence/A02'):
 for path in (ROOT/directory).rglob('*'):
  if path.is_file() and OUT not in path.parents:extra.add(path.relative_to(ROOT).as_posix())
if (ROOT/'mermaid-diagram.png').is_file():extra.add('mermaid-diagram.png')
rows=[]
for rel in sorted(tracked|extra):
 path=ROOT/rel
 if path.is_file():rows.append(dict(path=rel,sha256=sha(path.read_bytes()),bytes=path.stat().st_size,tracked=rel in tracked))
dump(OUT/'primary-before.json',dict(live_HEAD=live_head,workflow=WORKFLOW,fixed_integration_main_parent=MAIN,status=status,files=rows))
handoff=run(['git','show',WORKFLOW+':docs/tasks/A01-integration-R2-review-handoff.md'])
(OUT/'frozen-handoff.md').write_bytes(handoff)
for rel,expected in (
 ('docs/tasks/A01-integration-R1-review-report.md','2aaed84505799509319cab8e99a94eba818b69fd301caf4d3be89fe48c6a3caf'),
 ('docs/evidence/A01/review-integration-R1/sha256-manifest.json','a331ad8a039408f2225f9e9842cc0a4d0860af7a0ece67f3fafa527f0c6600ad')):
 assert sha((ROOT/rel).read_bytes())==expected
clone=STAGE/'checkout'
run(['git','clone','--shared','--no-checkout',str(ROOT),str(clone)])
tree=run(['git','merge-tree','--write-tree',MAIN,A01],clone).decode().strip();assert tree==EXPECTED
env=dict(os.environ,GIT_AUTHOR_NAME='Offline Reviewer',GIT_AUTHOR_EMAIL='offline-review@example.invalid',GIT_COMMITTER_NAME='Offline Reviewer',GIT_COMMITTER_EMAIL='offline-review@example.invalid',GIT_AUTHOR_DATE='2026-10-17T05:00:00+00:00',GIT_COMMITTER_DATE='2026-10-17T05:00:00+00:00')
commit=run(['git','commit-tree',tree,'-p',MAIN,'-p',A01],clone,b'Independent A01 integration R2 temporary combination; no branch integration.\n',env).decode().strip()
run(['git','checkout','--detach',commit],clone)
raw=STAGE/'raw no Git';raw.mkdir(exist_ok=False)
index=listing(tree,clone);checkout=[]
batch=subprocess.Popen(['git','cat-file','--batch'],cwd=clone,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
for row in index:
 batch.stdin.write((row['oid']+'\n').encode());batch.stdin.flush()
 header=batch.stdout.readline().decode().split();assert header[:2]==[row['oid'],'blob']
 data=batch.stdout.read(int(header[2]));assert batch.stdout.read(1)==b'\n'
 assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['oid']
 dest=raw/row['path'];dest.resolve().relative_to(raw.resolve());dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 row.update(bytes=len(data),sha256=sha(data))
 disk=(clone/row['path']).read_bytes()
 kind='GIT_RAW' if disk==data else 'EXACT_LF_TO_CRLF' if b'\r' not in data and disk==data.replace(b'\n',b'\r\n') else 'OTHER'
 assert kind!='OTHER',row['path']
 checkout.append(dict(path=row['path'],oid=row['oid'],git_sha256=row['sha256'],git_bytes=len(data),disk_sha256=sha(disk),disk_bytes=len(disk),representation=kind))
batch.stdin.close();assert batch.wait()==0;assert not batch.stderr.read();assert not (raw/'.git').exists()
temp=Path(tempfile.mkdtemp(prefix='A01-review-integration-R2-'))
import PIL,pydantic
summary=dict(workflow=WORKFLOW,main_parent=MAIN,A01_delivery=A01,A01_patch=PATCH,integration_tree=tree,temporary_commit=commit,temporary_parents=run(['git','rev-list','--parents','-n','1',commit],clone).decode().strip(),stage=str(STAGE),temporary=str(temp),checkout=str(clone),raw=str(raw),live_primary_HEAD_at_start=live_head,handoff_sha256=sha(handoff),counts=dict(files=len(index),checkout_raw=sum(r['representation']=='GIT_RAW' for r in checkout),checkout_crlf=sum(r['representation']=='EXACT_LF_TO_CRLF' for r in checkout)),environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),pydantic=pydantic.__version__,Pillow=PIL.__version__),network_calls=0,main_A01_integration=False)
dump(OUT/'raw-input-index.json',index);dump(OUT/'checkout-input-index.json',checkout)
dump(OUT/'bootstrap-commands.json',commands);dump(OUT/'bootstrap.json',summary)
print(json.dumps(summary,ensure_ascii=False))
