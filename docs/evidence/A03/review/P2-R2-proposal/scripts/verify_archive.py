# -*- coding: utf-8 -*-
"""Read-only static archive verification. Never import checker/product or DB.

--finalize writes initial final-verification and manifest once.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,hashlib,json,os,re,subprocess
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R2-proposal'
REPORT=ROOT/'docs/tasks/A03-P2-R2-proposal-review-report.md';MANIFEST=OUT/'sha256-manifest.json'
C='526d264284f36f856c306db88c1d7e71c04152e1'
def load(p):return json.loads(p.read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def rel(p):return p.relative_to(ROOT).as_posix()
def write(p,v):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def check():
 idx=load(OUT/'input-index.json');assert idx['commit']==C and len(idx['files'])==122 and idx['old_git_unchanged']==27670
 assert idx['manifest_entries']==205 and idx['new_paths']==206
 paths=set()
 for x in idx['files']:
  p=ROOT/x['copy'];b=p.read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['copy']
  assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==x['git_blob']
  paths.add(rel(p))
 assert paths=={rel(p) for p in (OUT/'input').rglob('*') if p.is_file()}
 old=load(OUT/'protected-old-review-files.json')['files']
 for x in old:
  b=(ROOT/x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
 stage=Path(idx['stage']);home=stage/'examples/a03/P2-R2-proposal';data=stage/idx['candidate'];profile=load(data/'profile.json')
 assert sha((data/'profile.json').read_bytes())=='f7385ba20090b5df8aa062c417e3d5c66a889a30f464facff994d9929b94f9ea'
 actual={p.relative_to(data).as_posix():sha(p.read_bytes()) for p in (data/'schemas').glob('*.json')}
 assert len(actual)==6 and actual=={x['path']:x['sha256'] for x in profile['schema_pins']}
 for file,key in [('api.json','api_sha256')]:assert sha((data/file).read_bytes())==profile[key]
 assert sha((home/'oracle.json').read_bytes())==profile['oracle_sha256']
 assert sha((home/'oracle_verifier.py').read_bytes())==profile['oracle_verifier_sha256']
 for x in profile['source_pins']:assert sha((stage/x['path']).read_bytes())==x['sha256']
 author=load(OUT/'author-reproduction/static-results.json');assert len(author['records'])==36
 counts={k:sum(x['result']==k for x in author['records']) for k in ('STATIC_ACCEPTED','EXPECTED_STATIC_REJECTION','STATIC_MATCH','EXPECTED_STATIC_MISMATCH')}
 assert counts=={'STATIC_ACCEPTED':7,'EXPECTED_STATIC_REJECTION':23,'STATIC_MATCH':1,'EXPECTED_STATIC_MISMATCH':5}
 diagnostic_codes={x['id']:x.get('code') for x in author['records']}
 assert diagnostic_codes['archived-readonly-session-does-not-match-gate-binding']=='SESSION_BINDING'
 assert diagnostic_codes['archived-initial-head-not-in-canonical-prefix']=='H0_CHAIN'
 result=load(OUT/'independent-static-results.json');assert result['whole_scope_package']['scopes']==['original-a','original-b']
 assert result['session']['independent_chain_events']==14 and result['session']['checker']['H0']['sequence']==7 and result['session']['checker']['Hfinal']['sequence']==14
 assert result['conversion']['old_mapped']==4 and result['conversion']['old_archive_only']==3 and result['conversion']['new_derived']==1
 assert result['conversion']['INITIAL']=='INITIAL' and result['conversion']['POST_HOLD']=='POST_HOLD'
 case=load(OUT/'counterexample/evidence-id-consumer/result.json');assert case['actual']=='STATIC_ACCEPTED' and case['ordinary_ref_declared_by_consumer'] is False
 bundle=load(OUT/case['bundle_file']);assert len(bundle['artifacts'])==16
 for a in bundle['artifacts']:assert a['content_hash']==sha(canonical({k:v for k,v in a.items() if k!='content_hash'}))
 for x in case['resource_overrides']:assert sha((OUT/x['file']).read_bytes())==x['sha256']
 current=load(OUT/'counterexample/evidence-id-consumer/current-consumer-confirmation.json')
 assert current['consumer_schema']=='1.3.0-a03-static-proposal' and current['ordinary_ref_declared_by_current_consumer'] is False
 assert current['raw_bundle_sha256']==sha((OUT/case['bundle_file']).read_bytes())
 commands=[load(OUT/p) for p in ('static-command/completion.json','counterexample-command/completion.json')]
 assert [x['exit_code'] for x in commands]==[0,1] and all(not x['alive'] and not x['timed_out'] for x in commands)
 release=load(OUT/'process-release.json');assert release['static_runner_pid']==commands[0]['pid'] and release['started_child_processes']==0 and release['background_processes']==0
 scope=load(OUT/'scope-declaration.json');assert scope['conclusion']=='REWORK' and scope['remaining_owned_background_processes']==0
 assert scope['field_reset']=='NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION' and not scope['I01_released']
 assert scope['product_imports_runs_planner_DB_native_network_browser_credentials_profile_model_install']==0
 rows=load(OUT/'local-conclusions.json');assert rows['overall']=='REWORK' and len(rows['rows'])==5
 local={r['item']:r['conclusion'] for r in rows['rows']}
 assert local['SCOPE-01']=='REWORK' and local['SESSION-02']==local['CONVERSION-07']=='STATIC_ACCEPTED_LIMITED'
 residual=load(OUT/'residual-assessment.json');assert residual['R17_VERSION_BRIDGE']['status']=='BLOCKED' and residual['REGISTRATION_SCOPE_BRANCH']['status']=='BLOCKED_NOT_POSITIVELY_VERIFIED'
 failure=load(OUT/'report-generation-attempt-01-failure.json');assert failure['exit_code']==1 and failure['candidate_or_static_results_changed'] is False
 assert load(OUT/'report-metadata-completion.json')['static_checks_rerun'] is False
 text=REPORT.read_text(encoding='utf-8');assert '整体结论：**REWORK**' in text and all(not line.endswith((' ','\t')) for line in text.splitlines())
 pending={MANIFEST,OUT/'final-verification.json'};links=[]
 for label,target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',text):
  p=(REPORT.parent/target.split('#',1)[0]).resolve();assert p.is_relative_to(ROOT) and (p.is_file() or p in pending),target
  links.append({'label':label,'target':target})
 return {'result':'A03_P2_R2_STATIC_REVIEW_ARCHIVE_VERIFIED','overall_conclusion':'REWORK','delivery_commit':C,
  'workflow':'0a668650f3dfdc00898032fb9c89e96694260d23','candidate':'candidate-final','manifest_raw_entries_verified_at_freeze':205,
  'added_paths_verified':206,'old_git_paths_blobs_unchanged':27670,'selected_raw_inputs_unchanged':122,'old_review_files_unchanged':len(old),
  'schema_pins':6,'author_static_counts':counts,'local_conclusions':local,'counterexample':'R2-SCOPE-EVIDENCE-ID-01',
  'counterexample_actual':'STATIC_ACCEPTED','counterexample_process_exit':1,'new_static_counterexamples':1,
  'R17_version_bridge':'BLOCKED','registration_derived_scope_positive':'BLOCKED_NOT_POSITIVELY_VERIFIED',
  'native_functions':'ALL_NOT_EXECUTED','oracle_adopted':False,'I01_released':False,'product_planner_DB_native_network_model_calls':0,
  'owned_static_commands_exited':[0,1],'remaining_owned_background_processes':0,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
  'preserved_document_formatter_error':'duplicate exclusive metadata write exit1; original script/report retained, missing declaration only completed',
  'report_links':links}
def files():return sorted([REPORT,*[p for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST]],key=rel)
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--finalize',action='store_true');args=parser.parse_args();r=check()
if args.finalize:
 assert not MANIFEST.exists() and not (OUT/'final-verification.json').exists()
 write(OUT/'final-verification.json',{**r,'captured_at':datetime.now(timezone(timedelta(hours=8))).isoformat()})
 ff=files();p=subprocess.run(['git','check-ignore','--stdin','-z'],cwd=ROOT,capture_output=True,timeout=30,
  input=('\0'.join(rel(f) for f in ff)+'\0').encode(),env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
 assert p.returncode in (0,1)
 write(MANIFEST,{'format_version':'a03-p2-r2-independent-static-review-1','conclusion':'REWORK','delivery_commit':C,
  'workflow_commit':'0a668650f3dfdc00898032fb9c89e96694260d23','self_excluded':rel(MANIFEST),'excluded_owned_files':[],
  'git_ignored_but_included':[x.decode() for x in p.stdout.split(b'\0') if x],
  'selection':'needed frozen final candidate/deps/text only; full delivery raw-indexed, historical/candidate-failed trees not duplicated; one bounded static counterexample',
  'files':[{'path':rel(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in ff]})
m=load(MANIFEST);assert {rel(p) for p in files()}=={x['path'] for x in m['files']}
for x in m['files']:
 b=(ROOT/x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
r.pop('report_links');r['archive_files']=len(m['files']);print(json.dumps(r))
