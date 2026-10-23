import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
P=Path('D:/1800/.local/stages/a28-independent-20261023/code-r1-review')
O=Path('D:/1800/docs/evidence/A28-independent/code-r1-review')
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,v):
 raw=(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
 with p.open('xb') as f:f.write(raw)
 return sha(raw)
def ref(p):
 raw=p.read_bytes();return {'path':str(p),'bytes':len(raw),'sha256':sha(raw)}
verification=json.loads((O/'final-verification.json').read_bytes());assert verification['status']=='PASS'
raws=[ref(p) for p in sorted(P.rglob('*')) if p.is_file()]
private_manifest=O/'private-artifact-manifest.json'
put(private_manifest,{'schema':'A28IndependentR1PrivateArtifactManifest/v1','count':len(raws),'members':raws})
result={'schema':'A28IndependentR1Result/v1','status':'ACCEPTED_OFFLINE_ONLY','completed_at':datetime.now(timezone.utc).isoformat(),
 'reviewer_thread_id':'01a16910-8c4e-7803-9347-87ab6798b358','commit':verification['commit'],
 'root_index_sha256':verification['root_index_sha256'],'fixed_delivery_sha256':verification['fixed_delivery_sha256'],
 'raw_manifest_sha256':verification['raw_manifest_sha256'],'launcher_sha256':'62088f27c5c2dfc432ecd60497f64d4ca696cb390ac372a7593814c11208f527',
 'launch_eligibility':'ELIGIBLE_FOR_ROOT_ACCEPTANCE_AND_EXACT_OWN_ONCE_AUTHORITY_BINDING',
 'finding_R1':'CLOSED_BY_ORIGINAL_FROZEN_COUNTEREXAMPLE_REJECTION',
 'known_old_info_coverage':{'observed':8,'native_raw':6,'accepted_public_proof':1,'accepted_code_binding':1,'unobserved_old_info':15,'all23_observed':False},
 'verification':{'root_raw_pairs':244,'git_raw_blobs':31,'known_identity_origin_pairs':8,'author_new_R1_checks_independently_run':8,
  'independent_control_groups':9,'launcher_dynamic_cases':10,'prior_40_checks_rerun':0,'content_reassessment':0,'OCR':0},
 'original_failures_preserved':{'v1_REWORK':True,'author_R1_initial_fixture_failures':6,'author_R1_initial_fixture_errors':1,
  'author_first_failed_run_failfast':False,'reviewer_raw_vs_checkout_precheck_assertion':1,'reviewer_first_launcher_cases':'NOT_RUN'},
 'limits':{'writers':4,'readers':4,'contexts':8,'posts':4,'business_gets':174,'login':0,'retries':0,'whole_process_seconds':900},
 'live':{'new_saves':'NOT_RUN','independent_readbacks':'NOT_RUN','native_export':'NOT_RUN','platform_requests':0,
  'actual_profile_identity_or_OS_release_proven':False},
 'no_active_author_workspace_or_profile_read':True,'authority_created':False,'root_state_or_product_modified':False,
 'private_artifact_manifest':ref(private_manifest),'reports':{n:ref(O/n) for n in ['report.md','intake.json','final-verification.json',
  'new-r1-suite-process.json','independent-controls.json','launcher-controls.json','checkout-representation.json','launcher-helper-correction.json']}}
result_sha=put(O/'result.json',result)
files=[ref(p) for p in sorted(O.iterdir()) if p.is_file() and p.name!='report-manifest.json']
manifest_sha=put(O/'report-manifest.json',{'schema':'A28IndependentR1ReportManifest/v1','count':len(files),'members':files,
 'self_hash_excluded':True,'private_artifact_count':len(raws)})
for member in files+raws:
 raw=Path(member['path']).read_bytes();assert len(raw)==member['bytes'] and sha(raw)==member['sha256']
print(json.dumps({'status':result['status'],'result_sha256':result_sha,'report_manifest_sha256':manifest_sha,'public_members':len(files),
 'private_artifacts':len(raws)},ensure_ascii=True))
