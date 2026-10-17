# -*- coding: utf-8 -*-
"""Verify documentation preparation bytes only; no repository imports or DB access.

Default is read-only archive verification. --finalize creates the initial index
of checks and SHA256 manifest once; it does not run any V/R functional test.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,hashlib,json,re,subprocess,sys
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-preparation'
REPORT=ROOT/'docs/tasks/A03-P2-review-preparation.md';MANIFEST=OUT/'sha256-manifest.json'
WORKFLOW='6b77c436742cf2826083b109d8ed86b85539cba6';FINAL='940a5de33a24b1a3a9ded6e69ade1dd0609ed83a'
def sha(b):return hashlib.sha256(b).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def load(p):return json.loads(p.read_bytes())
def write(p,v):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def source_bytes(c,p):
 r=subprocess.run(['git','cat-file','blob',c+':'+p],cwd=ROOT,capture_output=True,timeout=30)
 assert r.returncode==0,(c,p,r.stderr);return r.stdout
def check_inputs():
 idx=load(OUT/'input-index.json');assert idx['workflow_commit']==WORKFLOW and idx['accepted_final_commit']==FINAL
 assert len(idx['files'])==22
 for x in idx['files']:
  b=source_bytes(x['source_commit'],x['source_path'])
  assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['source_path']
  assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==x['git_blob']
  if x['copied']:assert (ROOT/x['copy']).read_bytes()==b,x['copy']
 copies=[x['copy'] for x in idx['files'] if x['copied']]
 actual={rel(p) for p in (OUT/'inputs').rglob('*') if p.is_file()}
 assert len(copies)==20 and actual==set(copies)
 old=load(OUT/'protected-old-review-files.json')['files']
 for x in old:
  b=(ROOT/x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
 api=load(OUT/'inputs/accepted-design/examples/a03/P1-R2/api-proposal.json')
 extracted=load(OUT/'accepted-api-schema-map.json')
 assert extracted['candidate_profile']==api['candidate_profile']
 assert extracted['contracts_entries']==api['contracts_api'] and len(extracted['contracts_entries'])==5
 assert extracted['runtime_authority']==api['runtime_authority_protocol']
 assert len(extracted['runtime_authority']['methods'])==8
 for i,g in enumerate(extracted['groups']):assert g['entries']==api['groups'][i]['proposed']
 assert [len(x['entries']) for x in extracted['groups']]==[4,5,6,4]
 assert len(extracted['schemas'])==7
 for s in extracted['schemas']:
  assert s['sha256']==api['candidate_profile']['schema_files'][s['name']]['sha256']
  assert sha((ROOT/s['copy']).read_bytes())==s['sha256']
 matrix=load(OUT/'acceptance-matrix.json')['rows'];ids={x['id'] for x in matrix}
 assert len(matrix)==28 and ids=={f'V{i:02}' for i in range(1,11)}|{f'R{i:02}' for i in range(1,19)}
 assert all(x['actual']=='NOT_RUN' and x['related_checks'] and x['evidence_classes'] for x in matrix)
 for x in matrix:
  t=(OUT/'inputs/workflow'/x['source_path']).read_text(encoding='utf-8')
  row=next(line for line in t.splitlines() if line.startswith('| '+x['id']+' |'))
  cols=[s.strip() for s in row.strip('|').split('|')]
  assert cols[1]==x['original_check'] and cols[2]==x['original_acceptance']
  for other in x['related_checks']:
   assert x['id'] in next(y for y in matrix if y['id']==other)['related_checks']
 bounds=load(OUT/'deadline-and-fault-plan.json')
 assert bounds['unattempted_absence']==api['unattempted_absence_protocol']['bounds']
 expected={'maximum_reads_per_intent_per_call':3,'per_read_s':2,'per_intent_s':8,'whole_call_s':60,
  'sqlite_busy_s':1,'effect_gate_s':5,'barrier_s':5,'owner_lease_s':10,'renew_s':2}
 assert all(bounds['intent_reconcile'][k]==v for k,v in expected.items())
 assert bounds['frozen_fault_points']==api['fault_points'] and len(bounds['frozen_fault_points'])==6
 assert set(bounds['exit_codes'])=={'0','2','3','4','5','6','7','90'}
 scope=load(OUT/'scope-declaration.json')
 assert scope['phase']=='P2_REVIEW_PREPARATION_ONLY' and scope['functional_conclusion']=='NOT_ASSESSED'
 assert scope['reviewer_functional_execution_authorized_this_turn'] is False and scope['i01_released'] is False
 for k in ('repository_source_imports_or_execution','floating_implementation_reads','databases_opened','target_effects',
  'browser_network_platform_credentials_profile_ocr_model_api','paid_model_calls',
  'test_or_target_worker_processes_started','remaining_owned_background_os_processes','other_processes_stopped',
  'messages_to_executor_B_other_chats','polling_or_automation_created'):assert scope[k]==0,k
 text=REPORT.read_text(encoding='utf-8');assert 'PREPARED / AWAITING_FROZEN_IMPLEMENTATION' in text
 assert all(not line.endswith((' ','\t')) for line in text.splitlines())
 links=[];pending={OUT/'preparation-check.json',MANIFEST}
 for label,target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',text):
  p=(REPORT.parent/target.split('#',1)[0]).resolve()
  assert p.is_relative_to(ROOT) and (p.is_file() or p in pending),target
  links.append({'label':label,'target':target})
 return {'result':'P2_PREPARATION_ARCHIVE_VERIFIED','workflow_commit':WORKFLOW,'accepted_design_final':FINAL,
  'frozen_inputs_verified':22,'copied_inputs':20,'schema_pins_verified':7,'original_matrix_rows':28,
  'all_functional_actuals':'NOT_RUN','old_review_files_unchanged':len(old),'report_links':links,
  'checks_executed':'raw Git bytes/SHA, mappings, document links and preparation archive only',
  'implementation_imports_or_functional_execution':0,'databases_opened':0,'remaining_owned_test_processes':0}
def manifest_files():return sorted([REPORT,*[p for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST]],key=rel)
def verify_archive():
 m=load(MANIFEST);files=manifest_files();assert {rel(p) for p in files}=={x['path'] for x in m['files']}
 for x in m['files']:
  b=(ROOT/x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
 assert m['phase']=='P2_REVIEW_PREPARATION_ONLY' and m['functional_conclusion']=='NOT_ASSESSED'
 return len(files)
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--finalize',action='store_true');args=parser.parse_args()
result=check_inputs()
if args.finalize:
 assert not MANIFEST.exists() and not (OUT/'preparation-check.json').exists(),'Archive already finalized; use read-only default.'
 write(OUT/'preparation-check.json',{**result,'captured_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
  'argv':sys.argv,'cwd':str(ROOT),'python':sys.executable,'python_version':sys.version,
  'functional_checks_not_run':True,'no_test_target_processes_started':True})
 files=manifest_files()
 p=subprocess.run(['git','check-ignore','--stdin','-z'],cwd=ROOT,capture_output=True,timeout=30,
  input=('\0'.join(rel(f) for f in files)+'\0').encode())
 assert p.returncode in (0,1)
 write(MANIFEST,{'format_version':'a03-p2-review-preparation-sha256-1','phase':'P2_REVIEW_PREPARATION_ONLY',
  'workflow_commit':WORKFLOW,'accepted_design_final':FINAL,'functional_conclusion':'NOT_ASSESSED',
  'self_excluded':rel(MANIFEST),'excluded_owned_files':[],
  'git_ignored_but_included':[s.decode() for s in p.stdout.split(b'\0') if s],
  'historical_evidence_selection':'20 relevant frozen documents/API/schemas; two accepted provenance hashes only; no old evidence tree',
  'files':[{'path':rel(f),'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())} for f in files]})
result['manifest_files']=verify_archive()
result.pop('report_links')
print(json.dumps(result))
