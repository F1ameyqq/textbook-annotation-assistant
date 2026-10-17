# -*- coding: utf-8 -*-
"""Verify only static review archive bytes and declared results. No DB/imports.

--finalize writes the initial verification and manifest once. Default is read-only.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,hashlib,json,os,re,subprocess
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R1-proposal'
REPORT=ROOT/'docs/tasks/A03-P2-R1-proposal-review-report.md';MANIFEST=OUT/'sha256-manifest.json'
COMMIT='7fdbde8f16569fd3bc399013115e13269d5d33fa'
def load(p):return json.loads(p.read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def write(p,v):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def check():
 idx=load(OUT/'input-index.json');assert idx['commit']==COMMIT and len(idx['files'])==269
 assert idx['old_git_files_unchanged']==27168 and idx['manifest_entries']==501 and idx['added_files']==502
 input_paths=set()
 for x in idx['files']:
  p=ROOT/x['copy'];b=p.read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['copy']
  assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==x['git_blob']
  input_paths.add(rel(p))
 assert input_paths=={rel(p) for p in (OUT/'input').rglob('*') if p.is_file()}
 old=load(OUT/'protected-old-review-files.json')['files']
 for x in old:
  b=(ROOT/x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
 stage=Path(idx['stage']);data=stage/idx['candidate'];profile=load(data/'profile.json')
 actual={p.relative_to(data).as_posix():sha(p.read_bytes()) for p in (data/'schemas').rglob('*.json')}
 assert len(actual)==16 and actual=={p['path']:p['sha256'] for p in profile['schema_pins']}
 assert sha((data/'api-supplement-proposal.json').read_bytes())==profile['api_supplement_sha256']
 for p in (data/'schemas/frozen-r2').glob('*.schema.json'):
  assert p.read_bytes()==(stage/'src/annotation/contracts/schemas'/p.name).read_bytes()
 assert (data/'schemas/frozen-r2/api-proposal.json').read_bytes()==(stage/'examples/a03/P1-R2/api-proposal.json').read_bytes()
 independent=load(OUT/'independent-static-results.json');assert independent['profile_pins']==16
 assert [p['events'] for p in independent['prefixes']]==[16,21] and [p['accepted_sequence'] for p in independent['prefixes']]==[3,8]
 assert all(p['current_event_hashes_recomputed'] and len(p['artifact_scopes'])==1 for p in independent['prefixes'])
 assert all(p['immutable_head_bytes_equal'] and p['post_decision']=='HOLD' and p['frame_structure']=='UNAVAILABLE' for p in independent['reports'])
 assert [p['distinct_action_snapshots'] for p in independent['reports']]==[1,2]
 assert len(independent['diagnostics'])==3
 assert all(x['author_static_actual']=='ACCEPTED' for x in independent['diagnostics'][:2])
 assert independent['diagnostics'][2]['exchange_schema_actual']=='PASS' and independent['diagnostics'][2]['static_semantic_actual']=='unregistered new kind'
 assert independent['pre']['decision']=='HOLD' and set(independent['pre']['checks'].values())=={'UNAVAILABLE'}
 assert independent['conversion']['states']==['CREATED','COPYING','VALIDATING','INCOMPLETE']
 author=load(OUT/'author-reproduction/static-check-result.json');assert len(author['checks'])==32
 counts={s:sum(x['result']==s for x in author['checks']) for s in ('PASS','EXPECTED_REJECTION','OLD_EQUALITIES_UNSATISFIABLE')}
 assert counts=={'PASS':13,'EXPECTED_REJECTION':17,'OLD_EQUALITIES_UNSATISFIABLE':2}
 command=load(OUT/'static-command/completion.json');release=load(OUT/'static-process-release.json')
 assert command['exit_code']==0 and command['alive'] is False and command['timed_out'] is False
 assert command['pid']==release['pid'] and release['child_processes_started']==0 and release['background_processes_or_native_sessions']==0
 scope=load(OUT/'scope-declaration.json');assert scope['conclusion']=='REWORK' and not scope['i01_released']
 assert scope['field_reset']=='NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'
 assert not scope['implementation_contract_approval'] and scope['product_imports_runs_DB_queries_native_sessions_network_browser_profile_credentials_ocr_model_api']==0
 assert len(load(OUT/'decision-table.json')['rows'])==9
 text=REPORT.read_text(encoding='utf-8');assert '结论：**REWORK**' in text and all(not x.endswith((' ','\t')) for x in text.splitlines())
 pending={MANIFEST,OUT/'final-verification.json'};links=[]
 for label,target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',text):
  p=(REPORT.parent/target.split('#',1)[0]).resolve();assert p.is_relative_to(ROOT) and (p.is_file() or p in pending),target
  links.append({'label':label,'target':target})
 return {'result':'A03_P2_R1_STATIC_REVIEW_ARCHIVE_VERIFIED','conclusion':'REWORK','proposal_commit':COMMIT,
  'workflow':'c135542791cb9172dd3163bf593273814a556968','candidate':'candidate-v2','raw_delivery_entries_verified_at_freeze':501,
  'old_git_paths_blobs_unchanged':27168,'selected_raw_inputs_unchanged':269,'old_review_files_unchanged':len(old),
  'schema_api_pin_set':16,'author_static_counts':counts,'independent_event_hashes':37,'independent_diagnostic_values':3,
  'decision_rows':9,'static_runner_exit':0,'remaining_owned_background_processes':0,'product_runs_DB_queries_native_sessions':0,
  'network_browser_model_calls':0,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION','implementation_authorized':False,
  'all_future_functional_checks':'NOT_EXECUTED','i01_released':False,'report_links':links,
  'preserved_review_tool_failure':'input-read-attempt-01.json; initial stage read before freeze completed; exit1, not product/checker run'}
def files():return sorted([REPORT,*[p for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST]],key=rel)
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--finalize',action='store_true');args=parser.parse_args()
r=check()
if args.finalize:
 assert not MANIFEST.exists() and not (OUT/'final-verification.json').exists()
 write(OUT/'final-verification.json',{**r,'captured_at':datetime.now(timezone(timedelta(hours=8))).isoformat()})
 ff=files();p=subprocess.run(['git','check-ignore','--stdin','-z'],cwd=ROOT,capture_output=True,timeout=30,
  input=('\0'.join(rel(f) for f in ff)+'\0').encode(),env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
 assert p.returncode in (0,1)
 write(MANIFEST,{'format_version':'a03-p2-r1-proposal-independent-static-review-1','conclusion':'REWORK','proposal_commit':COMMIT,
  'workflow_commit':'c135542791cb9172dd3163bf593273814a556968','self_excluded':rel(MANIFEST),'excluded_owned_files':[],
  'git_ignored_but_included':[v.decode() for v in p.stdout.split(b'\0') if v],
  'selection':'candidate-v2 and necessary static inputs/diagnostics; old trees and obsolete candidate drafts not duplicated',
  'files':[{'path':rel(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in ff]})
m=load(MANIFEST);assert {rel(p) for p in files()}=={x['path'] for x in m['files']}
for x in m['files']:
 b=(ROOT/x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
r.pop('report_links');r['manifest_files']=len(m['files']);print(json.dumps(r))
