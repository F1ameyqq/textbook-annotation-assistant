"""Coordinator read-only verification of fixed A09 archives. No target/business calls."""
import hashlib, io, json, os, re, subprocess, sys, zipfile
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path('D:/1800')
WORKFLOW='0a9c634d160ac7b39f68a1fb3555f409dd408f49'
PRODUCT='29c82b0997be3080f53dfde2afbb1d7457b04197'
AUTHOR='439423ebf4277e3825aba24fed6f56546ef66a2b'
REVIEW='25fcf2171df87bd7da97528efbe5bc24399d336a'
PREFIX='docs/evidence/A09/review/'
OUT=ROOT/'docs/evidence/coordinator/a09-acceptance-20261019'
EXPORT=ROOT/'.local/stages/a09-coordinator-fixed-review'
ENV=dict(os.environ,GIT_NO_LAZY_FETCH='1',PYTHONDONTWRITEBYTECODE='1')
os.environ.update(ENV)
sys.dont_write_bytecode=True
def git(*args,data=None):
    return subprocess.run(['git','-c','core.longpaths=true','-C',str(ROOT),*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=ENV,check=True).stdout
def tree(ref):
    t={}
    for row in git('ls-tree','-rz',ref).split(b'\0'):
        if row:
            entry,p=row.split(b'\t',1);t[p.decode()]=entry.decode()
    return t
def sha(b): return hashlib.sha256(b).hexdigest()
cache={}
def blob(ref,p):
    if (ref,p) not in cache: cache[ref,p]=git('cat-file','blob',ref+':'+p)
    return cache[ref,p]
def prefetch(keys):
    keys=list(dict.fromkeys(k for k in keys if k not in cache))
    raw=git('cat-file','--batch',data=''.join(r+':'+p+'\n' for r,p in keys).encode());offset=0
    for key in keys:
        end=raw.index(b'\n',offset);parts=raw[offset:end].split();assert parts[1]==b'blob'
        size=int(parts[2]);cache[key]=raw[end+1:end+1+size];offset=end+size+2
    assert offset==len(raw)
def obj(p): return json.loads(blob(REVIEW,PREFIX+p))
def save(p,o): p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(o,ensure_ascii=False,indent=2)+'\n').encode())
def dt(s): return datetime.fromisoformat(re.sub(r'(\.\d{6})\d+',r'\1',s).replace('Z','+00:00'))
trees={r:tree(r) for r in (WORKFLOW,PRODUCT,AUTHOR,REVIEW)}
for p,e in trees[AUTHOR].items(): assert trees[REVIEW].get(p)==e,p
for p,e in trees[WORKFLOW].items(): assert trees[REVIEW].get(p)==e,p
new=sorted(set(trees[REVIEW])-set(trees[AUTHOR]))
assert all(p.startswith(PREFIX) or p=='docs/tasks/A09-Q4-review-report.md' for p in new)
mf=PREFIX+'review-member-manifest.json';manifest=obj('review-member-manifest.json')
assert manifest['product']==PRODUCT and manifest['author_delivery']==AUTHOR
assert {m['path'] for m in manifest['members']}|{mf}==set(new)
prefetch([(REVIEW,p) for p in new])
total=0
for m in manifest['members']:
    raw=blob(REVIEW,m['path']);assert len(raw)==m['bytes'] and sha(raw)==m['sha256'],m['path']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==m['git_blob'];total+=len(raw)
assert total==manifest['total_bytes'] and len(manifest['members'])==manifest['member_count']==92
assert sha(blob(REVIEW,mf))=='68653cd9a562b05daf996ca963c26cb72f1ff1656bda5c43116d47a7d05d685c'
runtime=obj('archive/candidate-1/runtime-members.json')
prefetch([(PRODUCT,m['path']) for m in runtime])
for m in runtime:
    raw=blob(PRODUCT,m['path']);assert sha(raw)==m['sha256'] and len(raw)==m['bytes']
    assert (Path('D:/1800-worktrees/a09-q4-review-run')/m['path']).read_bytes()==raw
assert git('-C','D:/1800-worktrees/a09-q4-review-run','rev-parse','HEAD').decode().strip()==PRODUCT
inputs=obj('preflight/input-raw-manifest.json')
for m in inputs['inputs']:
    if m['source_type']=='RAW_GIT_BLOB': raw=blob(m['source_commit'],m.get('source_path',m['path']))
    else: raw=Path(m['source_path']).read_bytes()
    assert len(raw)==m['bytes'] and sha(raw)==m['sha256']
    if Path(m['path']).is_absolute(): assert Path(m['path']).read_bytes()==raw
approval_raw=blob(WORKFLOW,'docs/approvals/A09-Q4-offline-business-approval.json')
proposal_raw=blob(WORKFLOW,'docs/reviews/q4-first-lesson/proposal.json')
registry_raw=blob(WORKFLOW,'docs/tasks/A09-inputs.json')
approval=json.loads(approval_raw);proposal=json.loads(proposal_raw);registry=json.loads(registry_raw)
assert sha(approval_raw)=='5c73af50262f6bd7e48e2b0d46148026c1c3a953d1ee93c8262e356733d99010'
assert sha(proposal_raw)=='e8146fc7a4fe2e16c1fc1194d49de1caa1fe029dd6907848bbaa6c9082dc0bbe'
assert sha(registry_raw)=='aa4f2f7119ef71f70367e3bf7b3c3ed61e05e8a1643572aca92969d05cc1f9bf'
stage=blob(REVIEW,PREFIX+'archive/inputs/stage.zip')
assert sha(stage)==registry['zip_sha256'] and len(stage)==registry['zip_bytes']
with zipfile.ZipFile(io.BytesIO(stage)) as z:
    assert set(z.namelist())=={m['path'] for m in registry['raw_package_members']}
    for m in registry['raw_package_members']:
        raw=z.read(m['path']);assert len(raw)==m['bytes'] and sha(raw)==m['sha256']
    for s in registry['sources']:
        assert blob(REVIEW,PREFIX+'archive/candidate-1/trial/normal/assets/original/'+s['asset_id']+'.jpg')==z.read('staging/'+s['path'])
# Export only unchanged public validators and fixed archived files, without running a driver.
export_keys=[(PRODUCT,p) for p in trees[PRODUCT] if p.startswith('src/')]
export_keys += [(REVIEW,p) for p in new if p.startswith(PREFIX+'archive/candidate-1/trial/')]
prefetch(export_keys)
for ref,p in export_keys:
    dest=EXPORT/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(blob(ref,p))
sys.path.insert(0,str(EXPORT/'src'))
from annotation.contracts import validate_bundle, assert_plan_ready, artifact_ref, content_digest
def artifact(b,kind,phase=None):
    rows=[a for a in b['artifacts'] if a['kind']==kind and (phase is None or a['payload'].get('stage')==phase)]
    assert len(rows)==1,(kind,phase);return rows[0]
normal=EXPORT/PREFIX/'archive/candidate-1/trial/normal'
semantic=EXPORT/PREFIX/'archive/candidate-1/trial/semantic'
prepared=obj('archive/candidate-1/trial/normal/prepared-bundle.json');final=obj('archive/candidate-1/trial/normal/final-bundle.json')
sem=obj('archive/candidate-1/trial/semantic/legally-resealed-checked-bundle.json')
valid=validate_bundle(prepared,asset_root=normal);validate_bundle(final,asset_root=normal);validate_bundle(sem,asset_root=semantic)
plan=artifact(prepared,'ApplyPlan');snapshot=artifact(prepared,'PlatformSnapshot')
assert_plan_ready(valid,artifact_ref(plan),artifact_ref(snapshot))
pre=artifact(prepared,'CheckReport','PRE_APPLY');target=artifact(prepared,'CheckReport','TARGET')
assert pre['payload']['decision']==target['payload']['decision']=='PASS'
assert {c['check_id'] for c in pre['payload']['checks']}=={'source_integrity','structure','answer_matching','coverage','policy'}
assert all(c['outcome']=='PASS' for c in pre['payload']['checks'])
expected=[]
for i,r in enumerate(approval['approved_regions_in_physical_order']):
    s=next(x for x in registry['sources'] if x['asset_id']==r['asset_id'])
    expected.append({'box':{'image':{k:s[k] for k in ('asset_id','width','height','sha256')},'bbox':r['bbox']},'platform_role':r['proposed_role'],'platform_type':r['content_type'],'text':r['text'],'region_id':r['proposal_region_id'],'fragment_id':'a09-fragment-'+str(i)})
assert [x['platform_role'] for x in expected]==['Q','Q','Q','A'] and [x['platform_type'] for x in expected]==['image','text','text','text']
before=obj('archive/candidate-1/trial/normal/assets/before.json');after=obj('archive/candidate-1/trial/normal/assets/readback.json')
bv=before['view'];av=after['view'];frames=av['target']['frames'];projections=av['frame_projections']
assert before['instance_id']==after['instance_id'] and (before['read_sequence'],after['read_sequence'])==(1,2)
assert bv['epoch']==0 and bv['target']['questions']==bv['target']['frames']==[]
assert av['epoch']==1 and len(av['target']['questions'])==1 and len(frames)==len(projections)==4
actual=[projections[f['platform_frame_id']] for f in frames];assert actual==expected
qid=av['target']['questions'][0]['platform_question_id'];assert av['internal_bindings']=={approval['question_id']:qid}
for f,e in zip(frames,expected): assert f['platform_question_id']==qid and f['box']==e['box'] and f['platform_role']==e['platform_role']
assert content_digest(bv)==before['target_state_hash'] and content_digest(av)==after['target_state_hash'] and before['target_state_hash']!=after['target_state_hash']
assert len(plan['payload']['actions'])==1 and json.loads(plan['payload']['actions'][0]['expected_after']['frames'])==expected
graph=artifact(prepared,'QuestionGraph')['payload'];q=graph['questions'][0]
assert len(graph['questions'])==len(graph['answer_relations'])==1 and len(graph['fragments'])==4
assert q['question_id']==approval['question_id'] and q['question_type']=='free_response' and q['cross_page'] is False
receipt=artifact(final,'ExecutionReceipt');result=receipt['payload']['results'][0]
assert receipt==obj('archive/candidate-1/trial/normal/receipt.json')
assert result['outcome']=='APPLIED' and result['effect_match']=='MATCH' and result['replay_allowed'] is False
assert receipt['payload']['execution_mode']=='SIMULATED' and receipt['producer']['evidence_mode']=='SYNTHETIC'
comparison=obj('archive/candidate-1/trial/normal/comparison.json')
assert comparison['content_check_status']=='PENDING' and comparison['submission_status']=='NOT_SUBMITTED' and comparison['approval_differences']==[]
provenance=obj('archive/candidate-1/trial/normal/assets/input/provenance.json')
assert provenance['source_case_snapshot']==proposal['source_case_snapshot'] and provenance['historical_proposal_approvals']==proposal['approvals']
assert all(v is False for v in proposal['approvals'].values()) and provenance['source_case_snapshot']['decision']=='HOLD'
assert len(provenance['other_cases'])==3 and all(x['status']=='HOLD' and not x['question_relation_created'] for x in provenance['other_cases'])
assert provenance['full_external_G_Check_plan']=='DECLARED_ONLY_EXTERNAL_NOT_LOADED'
for kind in ('SourceBundle','EvidenceBundle','QuestionGraph'): assert artifact(prepared,kind)['producer']['evidence_mode']=='OBSERVED'
assert pre['producer']['evidence_mode']=='OBSERVED'
assert prepared['policies'][0]['confirmation_status']=='A_INTERNAL_PROPOSAL' and prepared['policies'][0]['applicability']=='PROPOSAL_ONLY'
summary=obj('archive/candidate-1/trial/summary.json')
assert summary['identity']['actual_head']==summary['identity']['frozen_head']==PRODUCT
assert summary['normal_attempts']==summary['successful_normal_closures']==summary['business_dispatches']==1
expected_codes={'missing_approval':'APPROVAL_MISSING','altered_approval':'APPROVAL_BINDING','q1_approval':'APPROVAL_BINDING','replaced_input':'INPUT_BINDING','replaced_proposal':'INPUT_BINDING','resealed_image_as_text':'COMPUTED_HOLD','platform_mode':'PLATFORM_MODE_FORBIDDEN','wrong_target':'TARGET_IDENTITY','stale_target':'TARGET_CHANGED','same_plan_replay':'PLAN_REPLAY'}
assert len(summary['refusals'])==10 and {r['case'] for r in summary['refusals']}==set(expected_codes)
for r in summary['refusals']:
    assert r==obj('archive/candidate-1/trial/refusals/'+r['case']+'.json') and r['code']==expected_codes[r['case']]
    assert r['rejected'] and r['new_frames']==r['new_questions']==r['business_dispatches']==0 and r['before_sha256']==r['after_sha256']
semcheck=artifact(sem,'CheckReport','PRE_APPLY')['payload']
assert semcheck['decision']=='HOLD' and {c['check_id']:c['outcome'] for c in semcheck['checks']}=={'source_integrity':'PASS','structure':'FAIL','answer_matching':'PASS','coverage':'PASS','policy':'FAIL'}
launch=obj('archive/launch-1.json');release=obj('archive/candidate-1/release.json')
assert launch['supervisor_exit_code']==release['exit_code']==0 and not release['timed_out']
assert launch['original_process_handle_waited'] and release['waited_original_handle'] and release['child_released'] and release['success']
assert launch['frozen_head']==release['frozen_head']==PRODUCT and release['elapsed_seconds']<180 and launch['within_240_seconds']
pid_ends={launch['supervisor_pid']:launch['supervisor_end_time'],release['child_pid']:release['child_ended_at']}
for start,end in [(launch['supervisor_kernel_creation_time'],launch['supervisor_end_time']),(release['child_kernel_creation_time'],release['child_ended_at'])]: assert 0<(dt(end)-dt(start)).total_seconds()<240
ps="@("+','.join(map(str,pid_ends))+") | ForEach-Object { $wantedPid=$_; $p=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$wantedPid); if ($null -eq $p) { [pscustomobject]@{queried_pid=$wantedPid;found=$false} } else { [pscustomobject]@{queried_pid=$wantedPid;found=$true;creation_time=$p.CreationDate.ToUniversalTime().ToString('o')} } } | ConvertTo-Json -Compress"
query=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',ps]).decode('utf-8-sig'))
for row in query:
    if row['found']: assert dt(row['creation_time'])>dt(pid_ends[row['queried_pid']]),'Original PID ambiguous/live'
result={'status':'PASS_FIXED_REVIEW_COORDINATOR_VERIFICATION','at':datetime.now(timezone.utc).isoformat(),'workflow':WORKFLOW,'product':PRODUCT,'author_delivery':AUTHOR,'review_delivery':REVIEW,'review_manifest':{'members':92,'bytes':total,'sha256':sha(blob(REVIEW,mf))},'review_new_paths':len(new),'author_old_paths_preserved':len(trees[AUTHOR]),'workflow_old_paths_preserved':len(trees[WORKFLOW]),'runtime_members_verified':len(runtime),'inputs_and_original_zip_members_verified':True,'public_contract_checks':['prepared bundle resources/digests/references','final bundle resources/digests/references','archived plan readiness','resealed negative bundle valid C01 with semantic HOLD'],'approved_vs_actual_frames':actual,'frame_differences':[],'receipt_id':receipt['artifact_id'],'receipt_revision':receipt['revision'],'receipt_content_hash':receipt['content_hash'],'receipt_raw_sha256':sha(blob(REVIEW,PREFIX+'archive/candidate-1/trial/normal/receipt.json')),'readback_sha256':sha(blob(REVIEW,PREFIX+'archive/candidate-1/trial/normal/assets/readback.json')),'normal_attempts':1,'successes':1,'dispatches':1,'refusals':summary['refusals'],'release_original_handles_verified':True,'current_pid_query':query,'coordinator_new_business_runs':0,'coordinator_new_targets':0,'coordinator_product_tests':0,'platform_calls':0,'pushes':0,'B_messages':0,'scope':'Fixed approved Q4 A-side offline only; other three HOLD; not B joint adoption or platform acceptance'}
save(OUT/'verification.json',result)
save(OUT/'integration-source-paths.json',{'source':REVIEW,'base':WORKFLOW,'paths':sorted(set(trees[REVIEW])-set(trees[WORKFLOW]))})
print(json.dumps({k:result[k] for k in ('status','review_manifest','review_new_paths','author_old_paths_preserved','runtime_members_verified','receipt_id','receipt_content_hash','current_pid_query','coordinator_new_business_runs')}))
