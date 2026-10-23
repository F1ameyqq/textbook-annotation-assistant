import hashlib,json,re
from datetime import datetime,timezone,timedelta
from pathlib import Path

PUB=Path('D:/1800/docs/evidence/A28-independent/code-v1-review')
PRI=Path('D:/1800/.local/stages/a28-independent-20261023/code-v1-review')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def put(name,value):
 raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
 with (PUB/name).open('xb') as f:f.write(raw)
 return sha(raw)
intake=json.loads((PUB/'intake.json').read_bytes())
witness=json.loads((PUB/'identity-control.json').read_bytes())
assert witness['status']=='FAIL_NEW_INFO_CAN_ALIAS_KNOWN_OLD_INFO'
first=json.loads((PUB/'new-suite-process.json').read_bytes())
rest=json.loads((PUB/'remaining-suite-process.json').read_bytes())
first_log=Path(first['stderr']).read_bytes()
rest_log=Path(rest['stderr']).read_bytes()
assert first['exit_code']==1 and len(re.findall(rb'\.\.\. ok',first_log))==35
assert rest['exit_code']==0 and len(re.findall(rb'\.\.\. ok',rest_log))==5
for item in intake['members']:
 for field in ('copy','root_frozen'):
  raw=Path(item[field]).read_bytes();assert len(raw)==item['bytes'] and sha(raw)==item['sha256']
 if item.get('isolated_source'):
  assert sha(Path(item['isolated_source']).read_bytes())==item['sha256']
raw_members=[]
for f in sorted(PRI.rglob('*')):
 if f.is_file():
  data=f.read_bytes();raw_members.append({'path':str(f),'bytes':len(data),'sha256':sha(data)})
raw_hash=put('raw-manifest.json',{'schema':'A28IndependentCodeRawEvidence/v1','members':raw_members})
result={
 'schema':'A28IndependentCodeReviewResult/v1','at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
 'status':'REWORK','decision':'REWORK_KNOWN_OLD_INFO_ID_CAN_BE_ACCEPTED_AS_NEW',
 'commit':intake['commit'],'root_index_sha256':intake['root_index_sha256'],
 'fixed_delivery_sha256':'dfc14eb0b86bc4a03f0f21e7c784a444d0137b60cf9c104d9cdffcf5d1cbf27f',
 'author_raw_manifest_sha256':'67db3aee2ede4ee51dfd04bf70dee0cd094b238b33233025b90ea2c4c01ca52c',
 'frozen_members_verified':208,'git_raw_dependencies_verified_against_commit':31,
 'content_acceptance':'UNCHANGED_ACCEPTED_FOUR_QUESTION_CONTENT_AND_FIXED_REMOTE_CROPS_ONLY',
 'new_author_checks':{'distinct_passes':40,'first_passes':35,'first_helper_errors':1,'first_successors_not_run':4,
  'helper_correction_remaining_passes':5,'old_35_replayed':False,'product_failures':0,'old_suites':0},
 'independent_controls':{'normal_fixed_input_control':'PASS','known_old_info_alias_rejection':'FAIL',
  'remaining_independent_controls':'NOT_RUN_AFTER_FIRST_SEMANTIC_FAILURE'},
 'findings':[{'id':'R1','priority':1,'title':'Reject new info IDs that collide with known existing question identities',
  'file':'src/annotation/runtime/usense_live/lesson_insert.py','line':394,
  'batch_file':'src/annotation/runtime/usense_live/lesson_batch.py','batch_lines':[140,202],
  'witness':{'path':str(PUB/'identity-control.json'),'sha256':sha((PUB/'identity-control.json').read_bytes())},
  'actual':'A new q23_info.id replaced with accepted q22_info.id still returns ok=true and ACCEPTED_A28_INSERT_PRESERVATION.',
  'expected':'Reject a new info identity that is already bound to an existing preserved question; stop before promotion/next send.'}],
 'production_eligibility':'NOT_RELEASED_REWORK',
 'launcher_dynamic_controls':'NOT_RUN_AFTER_FIRST_SEMANTIC_FAILURE',
 'actual_candidate_preflight':'FROZEN_AUTHOR_OUTPUT_RECEIVED_NOT_INDEPENDENTLY_REPLAYED',
 'A27_release_module':'BYTE_IDENTICAL_TO_ACCEPTED_BASELINE',
 'A27_writer_entry_checks':'PASS_IN_REMAINING_FIVE',
 'actual_new_writes_readbacks_export':'NOT_RUN_BY_REVIEWER',
 'raw_manifest_sha256':raw_hash,'report_sha256':sha((PUB/'report.md').read_bytes()),
 'preservation':{'root_frozen_members_rechecked':208,'isolated_git_sources_rechecked':31,'product_edits':0,'root_state_edits':0,'old_evidence_edits':0,'automation_changed':False},
 'boundaries':{'business_network':0,'browser':0,'profile_reads':0,'active_author_workspace_reads':0,'OCR':0,'platform_saves':0,'external_messages':0,
  'runtime_internal_IPC':'Standard-library Windows asyncio socketpair only'},
 'helper_errors_preserved':['Relative-path launcher read used wrong cwd; later rg masked shell status; corrected absolute frozen-path read.',
  'Audit denied standard-library asyncio loopback socketpair before test body; original error and loop destructor output preserved.'],
}
rh=put('result.json',result)
files=[]
for f in sorted(PUB.iterdir()):
 if f.is_file():
  data=f.read_bytes();files.append({'path':f.name,'bytes':len(data),'sha256':sha(data)})
mh=put('report-manifest.json',{'schema':'A28IndependentCodeReportManifest/v1','status':'REWORK','members':files})
print(json.dumps({'status':'REWORK','report_members':len(files),'private_artifacts':len(raw_members),'result_sha256':rh,'report_manifest_sha256':mh}))
