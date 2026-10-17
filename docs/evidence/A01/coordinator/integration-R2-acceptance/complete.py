"""Complete the bounded reproduction after correcting coordinator export scope."""
import datetime,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
root=Path('D:/1800');out=Path(__file__).resolve().parent
tree='0645ac862f79fb4e232e4cfbd5f6bb5055a68d62'
stage=root/'.local/stages/A01-coordinator-integration-R2';raw=stage/'raw source'
selection=['src/annotation','examples/a01','examples/a02/R1','tests/fixtures/a01/integration-R1','tests/fixtures/a01/R3','tests/fixtures/contracts/unknown','tests/test_a01_integration_r1.py','tests/test_a02_r1.py']
specs=[]
for row in subprocess.check_output(['git','ls-tree','-r','-z',tree,*selection],cwd=root).split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob' and mode in (b'100644',b'100755');specs.append((name.decode('utf-8'),oid.decode()))
batch=subprocess.run(['git','cat-file','--batch'],cwd=root,input=('\n'.join(oid for _,oid in specs)+'\n').encode(),capture_output=True,check=True).stdout
pos=0;items=[];added=[]
for path,oid in specs:
 end=batch.index(b'\n',pos);header=batch[pos:end].split();size=int(header[2]);data=batch[end+1:end+size+1];pos=end+size+2
 assert header[0].decode()==oid and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data).hexdigest()==oid
 dest=raw/path;dest.resolve().relative_to(raw.resolve())
 if dest.exists():assert dest.read_bytes()==data,path
 else:
  assert path.startswith('tests/fixtures/a01/R3/'),path
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);added.append(path)
 items.append({'path':path,'oid':oid,'bytes':size,'sha256':hashlib.sha256(data).hexdigest()})
assert pos==len(batch)
env=os.environ.copy()
for key in list(env):
 if key.startswith('GIT_'):env.pop(key)
env.update(PATH=r'C:\Windows\System32;C:\Windows',PYTHONPATH=str(raw/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
commands=[]
def run(name,args):
 argv=[sys.executable,'-B',*map(str,args)];p=subprocess.run(argv,cwd=stage,env=env,capture_output=True,timeout=120)
 for c in ['stdout','stderr']:(out/(name+'-'+c+'.txt')).write_bytes(getattr(p,c))
 receipt={'name':name,'argv':argv,'cwd':str(stage),'exit_code':p.returncode,'PATH':env['PATH'],'PYTHONPATH':env['PYTHONPATH']};commands.append(receipt)
 (out/(name+'-command.json')).write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
 assert p.returncode==0,(name,p.returncode)
run('URL-cases-corrected',[raw/'examples/a01/R3/probe.py',stage/'URL-replay-complete'])
url=json.loads((stage/'URL-replay-complete/results.json').read_bytes());assert url['passed']==5 and url['failed']==0
(out/'URL-cases-corrected-results.json').write_bytes((stage/'URL-replay-complete/results.json').read_bytes())
for book in ['46006966','46007447']:
 copied=stage/('moved book '+book);shutil.copytree(raw/'examples/a01/R3/bundles'/book,copied)
 run('consume-'+book,[raw/'examples/a01/consume.py',copied/'exchange.json','--book-id',book])
for item in items:assert hashlib.sha256((raw/item['path']).read_bytes()).hexdigest()==item['sha256']
single=(out/'original-noGit-stderr.txt').read_bytes();guard=(out/'frozen-input-guards-stderr.txt').read_bytes()
assert b'Ran 1 test' in single and b'OK' in single and b'skipped' not in single
assert b'Ran 3 tests' in guard and b'OK' in guard
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'BOUNDED_REPRODUCTION_PASS','main_parent':'2d1dc8b97713ee06ec5bf35febe0b894ece584b2','A01_delivery':'5f872150a237b195f73c78e02e13a91d2f4f46a7','combination_tree':tree,'raw_files':items,'added_missing_fixture_paths':added,'commands':commands,'first_attempt':'first-attempt.json','first_attempt_successes_reused_without_rerun':['environment','original-noGit','frozen-input-guards'],'original_single_test':{'run':1,'skipped':0},'guard_tests':3,'URL_cases_passed':5,'relocated_consumers':2,'raw_source_unchanged_after_scope_correction':True,'sessions_to_release':0,'synchronous_children_returned':True,'platform_model_calls':0,'full_suite_rerun':False,'remote_push':False}
with (out/'checks.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'result':result['result'],'raw_files':len(items),'supplemental_commands':len(commands)}))
