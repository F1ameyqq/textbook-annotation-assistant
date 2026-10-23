import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
P=Path('D:/1800/.local/stages/a28-independent-20261023/native-v1-review')
O=Path('D:/1800/docs/evidence/A28-independent/native-v1-review')
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def put(p,v):
 b=(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
 with p.open('xb') as f:f.write(b)
 return sha(b)
v=json.loads((O/'verification.json').read_bytes());assert v['status']=='PASS_FINITE_NINE_UNIT_NATIVE_DISPLAY_AND_PORTABLE_DELIVERY'
private=[ref(p) for p in sorted(P.rglob('*')) if p.is_file()]
put(O/'private-artifact-manifest.json',{'schema':'A28IndependentNativePrivateManifest/v1','count':len(private),'members':private})
dependencies=[ref(Path(p)) for p in ['D:/1800/docs/evidence/A28-independent/actual-v1-review/result.json',
 'D:/1800/docs/evidence/A28-independent/content-v1-review/result.json',
 'D:/1800/docs/evidence/coordinator/a26-final-native-delivery-closure/receipt.json',
 'D:/1800/.local/stages/a26-independent-20261023/native-delivery-review-20261023/106-A26-lesson2-five-native-delivery-20261023.zip']]
put(O/'accepted-dependency-manifest.json',{'schema':'A28IndependentNativeAcceptedDependencies/v1','members':dependencies,'old_screenshots_reopened':0})
result={'schema':'A28IndependentNativeResult/v1','status':'ACCEPTED_NINE_UNIT_NATIVE_CONTENT_DISPLAY_PORTABLE_DELIVERY_AND_OWN_RELEASE_ONLY',
 'completed_at':datetime.now(timezone.utc).isoformat(),'reviewer_thread_id':'01a16910-8c4e-7803-9347-87ab6798b358',
 'root_index_sha256':'4d7f11206df99ed81444ab78ad1e491b4945e77f2bfbe947cb6c9526debb1625',
 'fixed_native_delivery_sha256':'8ac91a0445ffbc6385786eace0a48ffb88e0ffcc47dc3ea4f1b37b93ad5802f9',
 'raw_manifest_sha256':'48e215a734016d7d01bcf7f632b388af13da563ea974175c8b960dc9cf4951bf',
 'actual_acceptance':dependencies[0],'root_raw_pairs':276,'declared_raw_members':274,'native_export_gets':1,'strict_records':26,
 'unique_full_content_type_tihao_matches':9,'new_four_stable_identity_matches':4,'old_five_A26_current_content_matches':5,
 'old_A26_files_byte_identical':59,'new_formula_occurrences':35,'new_question_images':4,'source_gallery_images':8,
 'screenshots_directly_viewed':55,'screenshot_groups':{'articles':8,'formulas':35,'images':12},
 'zip':{'sha256':v['zip_sha256'],'bytes':v['zip_bytes'],'files':140,'manifest_members':139,'crc':'PASS','raw_member_equality':'PASS','offline_links_and_anchors':'PASS'},
 'holders_accepted':5,'nonzero_owned_child_exits':v['nonzero_owned_child_exits'],'nonzero_child_cause':'UNKNOWN',
 'nonzero_child_effect':'NO_CONCRETE_ARTIFACT_DEFECT_FOUND_WITHIN_FROZEN_VISUAL_AND_BYTE_SCOPE',
 'production_wall_clock_seconds':42.639465,'author_declared_preparation_to_final_fixed_seconds':4582.093802,'postproduction_model_commands':5,'whole_task_unattended':False,
 'save_or_login_or_retry_in_export':0,'reviewer_platform_calls':0,'reviewer_browser_runs':0,'old_screenshots_reopened':0,'old_tests_rerun':0,
 'reviewer_helper_failures_preserved':2,'additional_read_path_error_preserved':True,'product_defects_found':0,'old15_info_raw_limitation_preserved':True,
 'limits':v['limitations'],'review_complete_and_released':True,'reports':{n:ref(O/n) for n in ['report.md','intake.json','verification.json','visual-review.json',
 'verification-failure.json','verification-failure-corrected1.json','private-artifact-manifest.json','accepted-dependency-manifest.json']}}
result_sha=put(O/'result.json',result)
public=[ref(p) for p in sorted(O.iterdir()) if p.is_file() and p.name!='report-manifest.json']
manifest_sha=put(O/'report-manifest.json',{'schema':'A28IndependentNativeReportManifest/v1','count':len(public),'members':public,'self_hash_excluded':True})
for r in private+public+dependencies:
 b=Path(r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
print(json.dumps({'status':result['status'],'result_sha256':result_sha,'report_manifest_sha256':manifest_sha,'public_members':len(public),'private_artifacts':len(private)}))
