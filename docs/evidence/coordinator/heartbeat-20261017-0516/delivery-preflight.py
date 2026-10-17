import json, subprocess, pathlib, hashlib, datetime

ROOT = pathlib.Path('D:/1800')
OUT = ROOT / 'docs/evidence/coordinator/heartbeat-20261017-0516'
OUT.mkdir(parents=True, exist_ok=True)
SPECS = [
 ('A03','a03-runtime-recovery','c30526958e313141bf64152627591b0907b04aa8','940a5de33a24b1a3a9ded6e69ade1dd0609ed83a','docs/tasks/A03-execution-report.md','docs/evidence/A03/execution/P2/manifest.json',['docs/evidence/A03/execution/P2/process-release-final.json']),
 ('A04','a04-headless-readonly','a86eca6ec87ced20dc3a8bcc8f2c87d329e87c39','3d4d10a0e12faa1af8d47e9f180d086ce401509c','docs/tasks/A04-coordinate-R1-execution-report.md','docs/evidence/A04/execution/coordinate-R1/sha256-manifest.json',['docs/evidence/A04/execution/coordinate-R1/checks/final-profile-release-check.json','docs/evidence/A04/execution/coordinate-R1/transport-diagnostic-02/session-release.json']),
 ('D01','d01-clean-install','48accd7d885fbc7ecdd8b438ada33a0eafd5bc55','c6bebdf43eb93f7a6ae21e96ec07ed155686777d','docs/tasks/D01-execution-report.md','docs/evidence/D01/execution/SHA256SUMS.json',['docs/evidence/D01/execution/process-observation-final.json','docs/evidence/D01/execution/run03/process-ledger.json'])
]
def sha(data): return hashlib.sha256(data).hexdigest()
def git(w,*args): return subprocess.check_output(['git','-c','core.longpaths=true',*args],cwd=str(w))
def disk(w,p): return pathlib.Path('\\\\?\\'+str((w/p).resolve())).read_bytes()
def write(p,data):
 with p.open('w',encoding='utf-8',newline='\n') as f: json.dump(data,f,ensure_ascii=False,indent=2); f.write('\n')
results=[]
for key,name,commit,base,report,manifest,releases in SPECS:
 w=pathlib.Path('C:/Users/ASUS/.codex/worktrees')/name/'1800'
 assert git(w,'rev-parse','HEAD').decode().strip()==commit
 status=git(w,'status','--porcelain=v1','-z')
 assert not status, (key,'dirty with longpaths enabled')
 mbytes=git(w,'show',commit+':'+manifest)
 m=json.loads(mbytes)
 entries=m.get('entries',m.get('files'))
 paths=[e['path'] for e in entries]
 assert len(paths)==len(set(paths))
 for p in paths:
  assert not pathlib.PurePosixPath(p).is_absolute() and '..' not in pathlib.PurePosixPath(p).parts
 tree={}
 for row in git(w,'ls-tree','-r','-z',commit).split(b'\0'):
  if row:
   meta,p=row.split(b'\t',1); tree[p.decode('utf-8')]=meta.split()[2].decode()
 oids=list(dict.fromkeys(tree[p] for p in paths))
 batch=subprocess.run(['git','cat-file','--batch'],cwd=str(w),input=('\n'.join(oids)+'\n').encode(),capture_output=True,check=True).stdout
 blobs={}; offset=0
 for oid in oids:
  end=batch.index(b'\n',offset); fields=batch[offset:end].split(); assert fields[0].decode()==oid and fields[1]==b'blob'
  size=int(fields[2]); start=end+1; data=batch[start:start+size]; assert len(data)==size and batch[start+size:start+size+1]==b'\n'
  blobs[oid]=data; offset=start+size+1
 assert offset==len(batch)
 failures=[]; disk_variants=[]; total=0
 for e in entries:
  p=e['path']; data=blobs[tree[p]]; total+=len(data)
  if sha(data)!=e['sha256'] or len(data)!=e.get('bytes',len(data)): failures.append({'path':p,'kind':'git_bytes'})
  d=disk(w,p)
  if d!=data:
   disk_variants.append({'path':p,'sha256':sha(d),'expected_git_sha256':sha(data),'exact_lf_to_crlf':d==data.replace(b'\n',b'\r\n')})
 assert not failures, (key,failures[:3])
 changes=[x.decode('utf-8') for x in git(w,'diff','--name-only','-z',base,commit).split(b'\0') if x]
 report_bytes=git(w,'show',commit+':'+report)
 release_data=[]
 for p in releases:
  b=git(w,'show',commit+':'+p); assert disk(w,p)==b
  release_data.append({'path':p,'sha256':sha(b),'record':json.loads(b)})
 result={'task':key,'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commit':commit,'base':base,'worktree':str(w),'clean_with_command_longpaths':True,'report':report,'report_sha256':sha(report_bytes),'manifest':manifest,'manifest_sha256':sha(mbytes),'manifest_entries_verified_against_raw_git':len(entries),'manifest_bytes':total,'disk_byte_variants':disk_variants,'release_evidence':release_data,'changed_paths':len(changes),'changed_non_evidence_paths':[p for p in changes if not p.startswith('docs/evidence/')],'functional_tests_run':False,'scope':'Frozen delivery byte/scope preflight only; no functional acceptance or integration.'}
 write(OUT/(key+'-delivery-preflight.json'),result);results.append(result)
 print(json.dumps({k:result[k] for k in ['task','commit','report_sha256','manifest_sha256','manifest_entries_verified_against_raw_git','manifest_bytes','changed_paths','changed_non_evidence_paths']},ensure_ascii=False))
 print('disk_variants',key,len(disk_variants),json.dumps(disk_variants[:3]))
write(OUT/'delivery-index.json',[{k:r[k] for k in ['task','commit','report','report_sha256','manifest','manifest_sha256']} for r in results])
