"""Freeze static live-evidence review only; no product import/run or system-resource query."""
import ast
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import re

ROOT=Path('D:/1800-worktrees/a16-live-review').resolve();OUT=ROOT/'docs/evidence/A16/independent-live-review'
CANDIDATE='e66e9f96197871f7123ebe2ed981a587262c50fb3f6e62cdc300f8e96be5a63f'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads(p.read_bytes())
def save(name,value):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
inputs=load(OUT/'input-raw-manifest.independent.json')['members'];assert len(inputs)==42
for item in inputs:
    raw=(ROOT/item['path']).read_bytes();assert len(raw)==item['size'] and sha(raw)==item['sha256'],item['path']
result=load(OUT/'review-result.json')
assert result['task']=='A16' and result['candidate_manifest_sha256']==CANDIDATE
assert result['result']=='ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY' and result['live_remaining']==0
assert result['actual_live_result']=='FAILED_ORIGIN_BLOCKED_NETWORK_GUARD_STOPPED'
assert result['authentication']=='NOT_PROVEN' and result['outer_launcher_OS_creation_identity']=='UNKNOWN'
assert len(load(OUT/'evidence-index.json')['checks'])==7
ledger=load(OUT/'owned-release-ledger.json')
assert len(ledger['held_processes'])==3 and len(ledger['jobs'])==2
assert all(row['creation_identity_match'] and row['exit_observed'] and row['handle_closed'] for row in ledger['held_processes'])
assert all(job['active_final']==0 and job['job_closed'] for job in ledger['jobs'])
timeline=load(OUT/'timeline.json');assert timeline['all_recorded_events_inside_window']
assert timeline['author_duration_clock_source']=='NOT_SPECIFIED_IN_FIXED_WAIT_RECORD'
assert timeline['author_reported_duration_ms']==10469
report=(OUT/'REPORT.md').read_text(encoding='utf-8')
links=re.findall(r'\]\(([^)]+)\)',report);deferred={'raw-manifest.json','final-preservation.json','reviewer-release.json'}
for link in links:
    target=(OUT/link).resolve();assert ROOT in target.parents and '://' not in link,link
    if link not in deferred:assert target.is_file(),link
for path in OUT.glob('*.py'):ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
now=datetime.now(timezone(timedelta(hours=8))).isoformat()
save('final-preservation.json',{'task':'A16','at':now,'result':'PASS_STATIC_PACKAGE_PRESERVATION_ONLY',
    'fixed_raw42_unchanged':True,'previous31454_Git_members':'Independent raw mode/type/blob audit verified; no Git mutations',
    'runtime12_exact_bytes':'Verified against fixed local-output-manifest, no .local access',
    'product_candidate16_and_prior_offline_evidence':'Unchanged','evidence_index_checks':7,
    'report_links_verified':len(links),'reviewer_tools_AST_parse':'PASS',
    'actual_live_result_preserved':'FAILED','unknowns_preserved':True,
    'new_product_suite_launcher_import_or_platform_execution':False})
save('reviewer-release.json',{'task':'A16','role':'FORMAL_INDEPENDENT_FIXED_LIVE_STATIC_REVIEW',
    'review_thread_id':'01a15841-0d44-7272-9740-40d013839869','at':now,
    'state':'STATIC_REVIEW_RELEASED','result':'ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY',
    'candidate_manifest_sha256':CANDIDATE,
    'new_resources':{'product_execution':0,'suite_execution':0,'launcher_execution':0,'product_import':0,
        'browser':0,'network_or_platform':0,'profile_credentials':0,'real_native_API':0,
        'occupancy_or_global_process_scan':0,'login':0,'business_upload_OCR':0,'B_or_other_chat_message':0},
    'local_tooling':'Synchronous standard-library JSON/hash/report tools and awaited read-only local Git commands only; no service/helper/background runtime',
    'Git_child_wait':'check_output calls completed successfully; no creation identity retained or OS identity assertion',
    'file_handles':'Context-managed writes/read_bytes; no actual context/Job/native process handle constructed by reviewer',
    'own_OS_exit_identity':'UNKNOWN_NOT_OBSERVABLE_FROM_OWN_RUNNING_REPORT_TOOL',
    'original_live_launcher_identity':'UNKNOWN_NOT_CAPTURED; author wait/exit2 accepted separately',
    'input42_or_author_report_modified':False,'root_JSON_or_old_evidence_modified':False,'local_private_directory_read':False,
    'output_scope':'D:/1800-worktrees/a16-live-review/docs/evidence/A16/independent-live-review only',
    'live_used':1,'live_remaining':0,'new_TLS_activation_or_retry_authorized':False,
    'platform_auth_book_source_target_first_save_readback':'NOT_ACCEPTED_OR_NOT_RUN',
    'next_dependency':'Coordinator determines a separately authorized next plan; no replay or reopening of this live.'})
members=[]
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        raw=path.read_bytes()
        if path.suffix=='.json':json.loads(raw)
        members.append({'path':path.relative_to(OUT).as_posix(),'bytes':len(raw),'sha256':sha(raw)})
save('raw-manifest.json',{'schema':'A16-independent-fixed-live-review/v1','task':'A16',
    'result':'ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY','candidate_manifest_sha256':CANDIDATE,
    'author_final':'003f862065a2d630e666323c0d158e33bcee91e9','at':now,
    'member_count':len(members),'self_excluded':True,'members':members})
for item in members:
    raw=(OUT/item['path']).read_bytes();assert len(raw)==item['bytes'] and sha(raw)==item['sha256']
print(json.dumps({'result':result['result'],'actual_live':'FAILED','members':len(members),
    'manifest_sha256':sha((OUT/'raw-manifest.json').read_bytes()),
    'report_sha256':sha((OUT/'REPORT.md').read_bytes()),'result_json_sha256':sha((OUT/'review-result.json').read_bytes()),
    'input42_preserved':True,'held_children':3,'jobs':2,'outer_launcher_identity':'UNKNOWN','live_remaining':0}))
