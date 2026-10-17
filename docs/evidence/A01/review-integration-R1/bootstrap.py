import hashlib,json,os,platform,subprocess,sys,tempfile,time
from pathlib import Path

ROOT=Path('D:/1800')
OUT=ROOT/'docs/evidence/A01/review-integration-R1'
STAGE=ROOT/'.local/stages/A01-review-integration-R1'
FINAL='5f872150a237b195f73c78e02e13a91d2f4f46a7'
PATCH='f8f2981a815f96147144d3747d26752b564cc9f7'
MAIN='4946b8ab307f88bdc25c14ace5ead774e3119fc5'
BASE='180bb1e86fb2a7eb1546be85af70f466f069daf5'
EXPECTED_TREE='2078731114ad3a07368ca46a2f34c3544af64e2b'
OUT.mkdir(parents=True,exist_ok=True)
STAGE.mkdir(parents=True,exist_ok=True)
records=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',encoding='utf-8',newline='\n') as handle:handle.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def run(args,cwd=ROOT,data=None,env=None):
 p=subprocess.run(list(map(str,args)),cwd=cwd,input=data,capture_output=True,env=env)
 row=dict(argv=p.args,cwd=str(cwd),exit_code=p.returncode,stdout=p.stdout.decode('utf-8','replace'),stderr=p.stderr.decode('utf-8','replace'))
 records.append(row)
 if p.returncode:dump(OUT/'bootstrap-commands.json',records);raise RuntimeError(row)
 return p.stdout
def files(ref,repo):
 raw=run(['git','ls-tree','-rz','--full-tree',ref],repo)
 rows=[]
 for part in raw.split(b'\0'):
  if part:
   meta,path=part.split(b'\t',1);mode,kind,oid=meta.decode().split();assert kind=='blob' and mode in ('100644','100755')
   rows.append(dict(path=path.decode('utf-8'),oid=oid,mode=mode))
 return rows
def export(ref,dest,repo):
 assert not dest.exists(),dest
 dest.mkdir(parents=True)
 rows=files(ref,repo)
 proc=subprocess.Popen(['git','cat-file','--batch'],cwd=repo,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 for row in rows:
  proc.stdin.write((row['oid']+'\n').encode());proc.stdin.flush()
  head=proc.stdout.readline().decode().split();assert head[:2]==[row['oid'],'blob']
  data=proc.stdout.read(int(head[2]));assert proc.stdout.read(1)==b'\n'
  assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['oid']
  path=dest/row['path'];path.resolve().relative_to(dest.resolve());path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
  row.update(bytes=len(data),sha256=sha(data))
 proc.stdin.close();assert proc.wait()==0;assert not proc.stderr.read()
 assert not (dest/'.git').exists()
 return rows

initial_status=run(['git','status','--short','--branch']).decode('utf-8')
tracked=run(['git','ls-files','-z']).split(b'\0')
before=[]
for raw in tracked:
 if raw:
  rel=raw.decode('utf-8');path=ROOT/rel
  if path.is_file():before.append(dict(path=rel,sha256=sha(path.read_bytes()),bytes=path.stat().st_size))
if (ROOT/'mermaid-diagram.png').is_file():before.append(dict(path='mermaid-diagram.png',sha256=sha((ROOT/'mermaid-diagram.png').read_bytes()),bytes=(ROOT/'mermaid-diagram.png').stat().st_size))
dump(OUT/'primary-before.json',dict(status=initial_status,files=before))
temp=Path(tempfile.mkdtemp(prefix='A01-review-integration-R1-'))
clone=STAGE/'local object repository'
run(['git','clone','--shared','--no-checkout',str(ROOT),str(clone)])
tree=run(['git','merge-tree','--write-tree',MAIN,PATCH],clone).decode().strip();assert tree==EXPECTED_TREE
env=dict(os.environ,GIT_AUTHOR_NAME='Offline Reviewer',GIT_AUTHOR_EMAIL='offline-review@example.invalid',GIT_COMMITTER_NAME='Offline Reviewer',GIT_COMMITTER_EMAIL='offline-review@example.invalid',GIT_AUTHOR_DATE='2026-10-17T00:00:00+00:00',GIT_COMMITTER_DATE='2026-10-17T00:00:00+00:00')
commit=run(['git','commit-tree',tree,'-p',MAIN,'-p',PATCH],clone,b'Independent temporary integration reproduction; no product branch update.\n',env).decode().strip()
run(['git','checkout','--detach',commit],clone)
raw=STAGE/'raw integrated no Git'
raw_rows=export(tree,raw,clone)
checkout=[]
for row in raw_rows:
 data=(clone/row['path']).read_bytes();original=(raw/row['path']).read_bytes()
 representation='GIT_RAW' if data==original else 'EXACT_LF_TO_CRLF' if b'\r' not in original and data==original.replace(b'\n',b'\r\n') else 'OTHER'
 assert representation!='OTHER',row['path']
 checkout.append(dict(path=row['path'],oid=row['oid'],git_sha256=row['sha256'],git_bytes=row['bytes'],disk_sha256=sha(data),disk_bytes=len(data),representation=representation))
frozen=STAGE/'original R3 raw frozen'
frozen_rows=export(BASE,frozen,clone)
delivery=STAGE/'final delivery raw frozen'
delivery_rows=export(FINAL,delivery,clone)
for path in ('tests/test_a01_rework_r3.py','tests/test_a01_integration_r1.py','examples/a01/integration-R1/verify.py','examples/a01/integration-R1/fixed_inputs.py','tests/fixtures/a01/integration-R1/reference.json'):
 assert run(['git','rev-parse',PATCH+':'+path],clone)==run(['git','rev-parse',FINAL+':'+path],clone)
import PIL,pydantic
summary=dict(final=FINAL,patch=PATCH,main_parent=MAIN,base=BASE,integration_tree=tree,temporary_commit=commit,temporary_parents=run(['git','rev-list','--parents','-n','1',commit],clone).decode().strip(),stage=str(STAGE),temporary=str(temp),checkout=str(clone),raw=str(raw),frozen=str(frozen),delivery=str(delivery),counts=dict(raw=len(raw_rows),checkout=len(checkout),checkout_raw=sum(x['representation']=='GIT_RAW' for x in checkout),checkout_crlf=sum(x['representation']=='EXACT_LF_TO_CRLF' for x in checkout),frozen=len(frozen_rows),delivery=len(delivery_rows)),environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),pydantic=pydantic.__version__,Pillow=PIL.__version__),network_calls=0)
dump(OUT/'raw-input-index.json',raw_rows);dump(OUT/'checkout-input-index.json',checkout);dump(OUT/'frozen-input-index.json',frozen_rows);dump(OUT/'delivery-input-index.json',delivery_rows)
dump(OUT/'bootstrap-commands.json',records);dump(OUT/'bootstrap.json',summary)
print(json.dumps(summary,ensure_ascii=False))
