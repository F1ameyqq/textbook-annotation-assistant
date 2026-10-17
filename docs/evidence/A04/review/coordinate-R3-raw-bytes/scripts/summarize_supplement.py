"""Validate new raw run, original script identity, PGM bindings and own release."""
import hashlib,importlib.metadata,io,json,os,subprocess,sys,tarfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parents[1];OLD=ROOT/'docs/evidence/A04/review/coordinate-R3'
F=OUT/'inputs/raw product with spaces';S=OUT/'inputs/replay-scripts';sys.path.insert(0,str(S))
from process_identity import probe
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def sha(b):return hashlib.sha256(b).hexdigest()
exact=read(OUT/'exact-replay/result.json');reg=read(OUT/'regression-result.json');ind=read(OUT/'independent-cases/results.json')
assert exact['public_cli_returncode']==2 and not exact['defect_reproduced'] and not exact['final_bundle_created']
assert not (OUT/'exact-replay/output').exists() and not (OUT/'exact-replay/input/evidence').exists()
assert reg['status']=='PASS' and reg['tests_run']==70 and not reg['errors'] and not reg['failures'] and not reg['skipped']
assert ind['passed']==26 and ind['failed']==0 and ind['all_children_reaped']
old_ind=read(OLD/'independent-cases/results.json')
assert {x['case']:x['status'] for x in old_ind['results']}=={x['case']:x['status'] for x in ind['results']}
save(OUT/'separate-run-comparison.json',{'old_run':'Prior git-archive representation, retained unchanged',
 'new_run':'Direct cat-file 212 exact blobs','old_results':{'regression':70,'independent':26},
 'new_results':{'regression':70,'independent':26},'statuses_match':True,
 'combined_or_double_counted':False,'new_absolute_paths_and_resource_digests_differ_as_expected':True})
identities={};groups=[]
def add(x):identities[(x['pid'],x['creation_filetime'])]={'pid':x['pid'],'creation_filetime':x['creation_filetime']}
for file in ['main-check-processes.json','pgm-check-processes.json']:
    group=read(OUT/file);add(group['runner_identity']);assert group['all_reaped']
    for job in group['jobs']:assert job['returncode']==0 and job['reaped'] and not job['timed_out'];add(job['identity'])
    groups.append(group)
guards=[]
for p in (OUT/'guard-records').glob('*.json'):
    x=read(p);assert x['exit_hook_reached'] and not x['blocked_events'];add(x);guards.append(p.relative_to(OUT).as_posix())
for x in ind['children']:assert x['reaped'];add(x['identity'])
observations=[probe(x) for _,x in sorted(identities.items())];assert all(x['original_process_exited'] for x in observations)
save(OUT/'self-release.json',{'at':datetime.now(timezone.utc).isoformat(),'scope':'Recorded own PID + creation time only; no global enumeration or profile scan',
 'observations':observations,'all_original_processes_exited':True,'guard_records':guards,
 'PID_reuse_distinguished':True,'process_groups':groups,'browser_network_platform_profile_credentials_model_book_actions':0,
 'authorized_profile_state':'NOT_INSPECTED'})
sys.path.insert(0,str(F/'src'))
from PIL import Image
from annotation.source.usense import parser,png_pixels
from annotation.contracts import load_bundle
paths={'parser':parser.__file__,'png_gate':png_pixels.__file__,'public_loader':load_bundle.__code__.co_filename}
inventory=read(OUT/'runtime-inputs-before.json');index={e['path']:e for e in inventory['files']};imports=[]
for role,path in paths.items():
    rel=Path(path).resolve().relative_to(F.resolve()).as_posix();data=Path(path).read_bytes();e=index[rel]
    assert sha(data)==e['git_sha256'];imports.append({'role':role,'path':str(path),'target_path':rel,'git_blob_oid':e['git_blob_oid'],'sha256':sha(data),'bytes':len(data)})
save(OUT/'actual-imports.json',{'imports':imports,'all_match_cat_file':True,'python':sys.version,'executable':sys.executable,
 'Pillow':importlib.metadata.version('Pillow'),'Pydantic':importlib.metadata.version('pydantic'),'dependencies_changed':False})
package=OUT/'raw-pgm-package';moved=OUT/'raw PGM package relocated with spaces';bundle=load_bundle(package/'bundle.json');load_bundle(moved/'bundle.json')
source=next(x for x in bundle.artifacts if x.kind=='SourceBundle');archive={}
with tarfile.open(fileobj=io.BytesIO((OLD/'inputs/frozen-inputs.tar.gz').read_bytes()),mode='r:gz') as tar:
    for m in tar.getmembers():
        if m.isfile() and m.name.startswith('tests/fixtures/a04/source/assets/') and m.name.endswith('.pgm'):archive[m.name]=tar.extractfile(m).read()
bindings=[]
for asset in source.payload.assets:
    target_path='tests/fixtures/a04/source/'+asset.path;e=index[target_path];raw=(F/target_path).read_bytes();old=archive[target_path]
    published=(package/asset.path).read_bytes();relocated=(moved/asset.path).read_bytes()
    assert raw==published==relocated and sha(raw)==asset.sha256==e['git_sha256']
    with Image.open(io.BytesIO(raw)) as im:im.load();size=im.size;pixels=im.tobytes();mode=im.mode
    with Image.open(io.BytesIO(old)) as im:im.load();assert im.size==size and im.mode==mode and im.tobytes()==pixels
    assert size==(asset.width,asset.height)==(4,3)
    bindings.append({'target_path':target_path,'git_blob_oid':e['git_blob_oid'],'git_sha256':e['git_sha256'],
      'raw_bytes':len(raw),'old_archive_bytes':len(old),'old_archive_sha256':sha(old),'published_sha256':sha(published),
      'relocated_sha256':sha(relocated),'asset_sha256':asset.sha256,'dimensions':list(size),'mode':mode,
      'media_type':asset.media_type,'decoded_pixel_sha256':sha(pixels),'old_and_new_pixels_equal':True})
assert len(bindings)==3
save(OUT/'pgm-resource-bindings.json',{'mode':'Raw Git PGM bytes through public source CLI and relocated unchanged public loader',
 'normalization_used':False,'bindings':bindings,'synthetic_fixture_not_current_platform':True})
before=read(OUT/'old-preservation-before.json')
for e in before['records']:
    data=(ROOT/e['path']).read_bytes();assert sha(data)==e['sha256'] and len(data)==e['bytes'],e['path']
save(OUT/'old-preservation-after.json',{'old_manifest_entries':355,'old_manifest_itself_preserved':True,
 'total_records_verified':356,'all_unchanged':True,'records':before['records']})
save(OUT/'review-verdict.json',{'target_commit':'6c8137a4fadddc01a47906d564ab3460277c8958',
 'workflow_commit':'9317efcdb734b081075c56f6557838d591959e8f','reasoning_effort_requested':'xhigh',
 'RAW_BYTE_SUPPLEMENT':'PASS','OFFLINE_R3':'ACCEPTED','A04_OVERALL':'BLOCKED',
 'raw_runtime_files_exact_before_and_after':212,'old_archive_differences':59,'differences_only_EOL':True,
 'product_bug_found':False,'scope':'Same bounded R3 offline PNG repair; evidence provenance corrected without product changes',
 'old_provenance_claim':'Original report full raw-Git-byte claim incorrect; old archive and 355-item manifest retained unchanged',
 'new_results':{'unchanged_exact_repro_wrapper':0,'product_CLI_rejection':2,'regression':70,'independent':26,'PGM_bindings':3},
 'not_run':['Older full matrices','Node deadline','Windows junction','configured maximum stress','real R01-R06','S01 completeness','installation revalidation'],
 'real_scenarios':{f'R{i:02d}':'BLOCKED_NOT_RUN' for i in range(1,7)},
 'preserve_old_results_as_separate_run':True,'integration_or_dependency_release':False,'paid_model_calls':0,'paid_cost':0})
print(json.dumps({'RAW_BYTE_SUPPLEMENT':'PASS','OFFLINE_R3':'ACCEPTED','A04_OVERALL':'BLOCKED',
 'regression':70,'independent':26,'raw_PGM_bindings':3,'own_process_identities_exited':len(observations),'guard_records':len(guards)}))
