"""Supplement: extract binary cat-file blobs, compare archive, preserve old 355."""
import collections,hashlib,io,json,subprocess,tarfile
from pathlib import Path
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A04/review/coordinate-R3-raw-bytes'
OLD=ROOT/'docs/evidence/A04/review/coordinate-R3';RUN=OUT/'inputs/raw product with spaces'
AUTHOR=Path('C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800')
TARGET='6c8137a4fadddc01a47906d564ab3460277c8958';WF='9317efcdb734b081075c56f6557838d591959e8f'
def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def git(*args):return subprocess.check_output(['git','-c','core.longpaths=true','-C',str(AUTHOR),*args])
def cat(commit,paths):
    command=['git','-C',str(AUTHOR),'cat-file','--batch']
    proc=subprocess.run(command,input=''.join(commit+':'+p+'\n' for p in paths).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    stream=io.BytesIO(proc.stdout);items={}
    for path in paths:
        header=stream.readline().split();assert len(header)==3 and header[1]==b'blob',(path,header)
        size=int(header[2]);data=stream.read(size);assert len(data)==size and stream.read(1)==b'\n'
        oid=header[0].decode();assert hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data).hexdigest()==oid
        items[path]={'data':data,'oid':oid,'sha256':sha(data),'bytes':size}
    return items,{'argv':command,'cwd':str(ROOT),'object_queries':[commit+':'+p for p in paths],
      'returncode':proc.returncode,'stderr':proc.stderr.decode('utf-8','replace'),'objects':len(paths),
      'binary_protocol':'object-oid type size newline; exact size bytes; delimiter newline; git blob SHA1 recomputed'}
assert not RUN.exists(),'Fresh runtime input directory required'
prior_manifest=OLD/'sha256-manifest.json';prior_bytes=prior_manifest.read_bytes()
assert sha(prior_bytes)=='d756ab8d28d49350883fdf47289497451833818bfb76649568dbb8467e9f4002'
prior=json.loads(prior_bytes);assert len(prior['files'])==355
old_records=[]
for e in prior['files']:
    data=(ROOT/e['path']).read_bytes();assert sha(data)==e['sha256'] and len(data)==e['bytes'],e['path'];old_records.append(e)
old_records.append({'path':prior_manifest.relative_to(ROOT).as_posix(),'sha256':sha(prior_bytes),'bytes':len(prior_bytes)})
save(OUT/'old-preservation-before.json',{'old_report_sha256':'ce6bc599c0b1533e58095366c4f8b499248079aa6c571e8569e1b585d4a82e61',
 'old_manifest_sha256':sha(prior_bytes),'records':old_records,'entries_including_manifest':356})
old_inventory=json.loads((OLD/'inputs/frozen-tree-manifest.json').read_text(encoding='utf-8'))
paths=[e['path'] for e in old_inventory['files']];assert len(paths)==212
raw,command=cat(TARGET,paths);save(OUT/'cat-file-export-command.json',command)
archive={}
with tarfile.open(fileobj=io.BytesIO((OLD/'inputs/frozen-inputs.tar.gz').read_bytes()),mode='r:gz') as t:
    for member in t.getmembers():
        if member.isfile():archive[member.name]=t.extractfile(member).read()
assert set(archive)==set(paths)
differences=[];rows=[]
for path in paths:
    item=raw[path];data=item['data'];before=archive[path];e=next(e for e in old_inventory['files'] if e['path']==path)
    assert sha(before)==e['sha256'] and len(before)==e['bytes'],path
    if data!=before:
        only_eol=data.replace(b'\r\n',b'\n')==before.replace(b'\r\n',b'\n')
        assert only_eol,path
        differences.append({'path':path,'git_blob_oid':item['oid'],'git_sha256':item['sha256'],'git_bytes':item['bytes'],
          'old_archive_sha256':sha(before),'old_archive_bytes':len(before),'EOL_only_diagnostic':True,
          'acceptance_uses_exact_bytes_not_normalization':True})
    destination=RUN/path;destination.resolve().relative_to(RUN.resolve());destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
    actual=destination.read_bytes();assert actual==data
    rows.append({'path':path,'git_blob_oid':item['oid'],'git_sha256':item['sha256'],'git_bytes':item['bytes'],
      'runtime_sha256':sha(actual),'runtime_bytes':len(actual),'exact_runtime_match':True})
assert len(differences)==59
counts=collections.Counter(Path(x['path']).suffix or Path(x['path']).name for x in differences)
assert counts['.py']==55 and counts['.pgm']==3 and counts['.gitattributes']==1,counts
save(OUT/'archive-vs-cat-file.json',{'target_commit':TARGET,'files':212,'differences':differences,'different_count':59,
 'difference_types':dict(counts),'old_archive_manifest_was_accurate_for_archive':True,
 'old_raw_git_claim':'INCORRECT','normalization_used_for_acceptance':False})
save(OUT/'runtime-inputs-before.json',{'target_commit':TARGET,'source':'git cat-file --batch; binary stdout; write_bytes',
 'runtime_root':str(RUN),'files':rows,'all_exact':True,'archive_used_for_runtime':False})
wf_paths=['AGENTS.md','docs/coordination.md','docs/tasks/A04-coordinate-R3-raw-byte-supplement.md',
 'docs/evidence/A04/coordinator/coordinate-R3-acceptance/archive-preflight-failure.json',
 'docs/evidence/A04/coordinator/coordinate-R3-acceptance/checks.json']
workflow,wf_cmd=cat(WF,wf_paths)
for path,item in workflow.items():
    dest=OUT/'inputs/workflow'/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(item['data'])
save(OUT/'workflow-inputs.json',{'workflow_commit':WF,'command':wf_cmd,'files':[{'path':p,'oid':e['oid'],'sha256':e['sha256'],'bytes':e['bytes']} for p,e in workflow.items()]})
old_index={e['path']:e for e in prior['files']}
copies=[('inputs/unchanged-R2-repro/repro_incomplete_rows.py','inputs/replay-scripts/exact/repro_incomplete_rows.py'),
 ('inputs/unchanged-R2-repro/offline_guard.py','inputs/replay-scripts/exact/offline_guard.py')]
copies += [('scripts/'+name,'inputs/replay-scripts/'+name) for name in ['independent_checks.py','regression_worker.py','process_identity.py','offline_guard.py']]
scripts=[]
for source_rel,dest_rel in copies:
    source=OLD/source_rel;data=source.read_bytes();original=old_index[source.relative_to(ROOT).as_posix()]
    assert sha(data)==original['sha256'] and len(data)==original['bytes']
    dest=OUT/dest_rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    scripts.append({'source':source.relative_to(ROOT).as_posix(),'copy':dest_rel,'sha256':sha(data),'bytes':len(data),'unchanged':True})
save(OUT/'replayed-scripts.json',{'basis':'Old 355-item manifest and actual old bytes, untouched checks/expected values',
 'scripts':scripts,'new_controller_required':'Old run_jobs.py hardcodes old stage/output; new controller changes paths/logging only'})
assert git('rev-parse','HEAD').decode().strip()==TARGET and git('status','--porcelain').decode()==''
pgms=[r for r in rows if r['path'].endswith('.pgm') and r['path'].startswith('tests/fixtures/a04/source/')]
assert len(pgms)==3
save(OUT/'raw-pgm-inputs.json',{'files':pgms,'old_archive_differences':[d for d in differences if d['path'].endswith('.pgm')]})
print(json.dumps({'files':212,'exact_matches':212,'archive_differences':59,'types':dict(counts),'old_records_preserved':356,
 'unchanged_check_scripts':len(scripts),'runtime_root':str(RUN)}))
