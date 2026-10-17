# -*- coding: utf-8 -*-
"""Read-only byte/provenance archive verification, not functional re-execution.

--finalize creates the first final verification record and manifest exactly once.
No annotation module is imported and no SQLite database is opened.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,hashlib,json,os,re,subprocess
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2';REPORT=ROOT/'docs/tasks/A03-review-report.md'
MANIFEST=OUT/'sha256-manifest.json';FINAL='c30526958e313141bf64152627591b0907b04aa8'
def sha(b):return hashlib.sha256(b).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def load(p):return json.loads(p.read_bytes())
def write(p,v):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def checks():
 idx=load(OUT/'input-index.json');assert idx['final_commit']==FINAL and len(idx['files'])==73
 stage=Path(idx['stage']);staged=set()
 for x in idx['files']:
  p=ROOT/x['copy'];b=p.read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['copy']
  assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==x['git_blob']
  if p.is_relative_to(stage):staged.add(p.relative_to(stage).as_posix())
 assert staged=={p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()}
 old=load(OUT/'protected-old-review-files.json')['files']
 for x in old:
  b=(ROOT/x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
 byte_index=load(OUT/'delivery-byte-index.json');assert len(byte_index['entries'])==17429
 assert len({x['path'] for x in byte_index['entries']})==17429
 for s in idx['schema_pins']:assert s['equals_R2_pin'] and sha((stage/s['path']).read_bytes())==s['sha256']
 result=load(OUT/'independent-results.json');assert result['conclusion']=='REWORK'
 normal=result['cases'][0];failure=result['cases'][1]
 assert normal['effects']==3 and normal['replay_code']=='REPLAY_FORBIDDEN'
 assert failure['actual_exit_code']==2 and failure['actual']['code']=='EVENT_PREFIX_CONTRACT_GAP'
 assert failure['before_effects']==failure['after_effects']==0 and failure['unattempted_fact_events']==0
 assert failure['target_reads_before']==failure['target_reads_after']==2
 assert failure['accepted_plan_event_sequence']==3 and failure['reserved_actions']==3
 rows=load(OUT/'review-matrix.json')['rows'];assert len(rows)==28
 assert {r['id'] for r in rows}=={f'V{i:02}' for i in range(1,11)}|{f'R{i:02}' for i in range(1,19)}
 assert next(x for x in rows if x['id']=='V04')['independent_status']=='FAIL'
 assert next(x for x in rows if x['id']=='R11')['independent_status']=='FAIL'
 env=load(OUT/'environment.json');assert all(Path(p).is_relative_to(stage) for p in env['imports'].values())
 releases=[load(OUT/p) for p in ('process-release.json','process-release-run02.json','process-release-environment.json')]
 assert all(x['remaining_owned_direct_processes']==0 and x['other_processes_signalled']==0 for x in releases)
 commands=[load(p) for p in sorted((OUT/'cases').glob('*/commands/*/completion.json'))]
 assert len(commands)==13 and all(not c['alive'] and not c['timed_out'] for c in commands)
 initial_nonzero=[{'pid':x['pid'],'count':x['job_accounting_before_close']['active_processes']} for x in commands if x['job_accounting_before_close']['active_processes']]
 assert initial_nonzero==[{'pid':66032,'count':1}]
 # That first nonzero count is preserved, not changed to zero. The contained
 # job was closed by the recorded driver finally path (kill-on-close).
 scope=load(OUT/'scope-declaration.json');assert scope['conclusion']=='REWORK' and not scope['i01_released']
 assert scope['author_prohibited_field_reset']=='NOT_EXECUTED'
 text=REPORT.read_text(encoding='utf-8');assert '结论：**REWORK**' in text
 assert all(not line.endswith((' ','\t')) for line in text.splitlines())
 pending={MANIFEST,OUT/'final-verification.json'};links=[]
 for label,target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',text):
  p=(REPORT.parent/target.split('#',1)[0]).resolve();assert p.is_relative_to(ROOT) and (p.is_file() or p in pending),target
  links.append({'label':label,'target':target})
 return {'result':'A03_P2_REVIEW_ARCHIVE_VERIFIED','conclusion':'REWORK','final_commit':FINAL,
  'copied_raw_git_inputs_unchanged':73,'delivery_manifest_raw_blobs_verified_at_freeze':17429,'schema_pins':7,
  'old_review_files_unchanged':len(old),'matrix_rows':28,'actual_independent_cases':2,
  'normal_effects':3,'dedicated_entry_exit':2,'dedicated_entry_code':'EVENT_PREFIX_CONTRACT_GAP','dedicated_case_effects':0,
  'actual_imports':env['imports'],'direct_process_completion_records':13,'all_direct_exited':True,
  'remaining_owned_direct_processes':0,'original_nonzero_job_record_preserved':initial_nonzero,
  'descendant_release':'bounded per-command Job containment and kill-on-close; initial failure not rewritten; no OS-wide audit',
  'prohibited_authorization_field_reset':'NOT_EXECUTED','report_links':links,'full_matrix_rerun':False,
  'product_changes_commit_merge_push':False,'i01_released':False}
def files():return sorted([REPORT,*[p for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST]],key=rel)
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--finalize',action='store_true');args=parser.parse_args()
r=checks()
if args.finalize:
 assert not MANIFEST.exists() and not (OUT/'final-verification.json').exists()
 write(OUT/'final-verification.json',{**r,'captured_at':datetime.now(timezone(timedelta(hours=8))).isoformat()})
 ff=files();p=subprocess.run(['git','check-ignore','--stdin','-z'],cwd=ROOT,capture_output=True,timeout=30,
  input=('\0'.join(rel(f) for f in ff)+'\0').encode(),env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
 assert p.returncode in (0,1)
 write(MANIFEST,{'format_version':'a03-p2-independent-review-1','conclusion':'REWORK','final_commit':FINAL,
  'implementation_commit':'fa645ac8fd70688f3293edc5cfb1077fc7bd9daa','workflow_commit':'2ef3bfda20476dff3bdd23912d5bf2d1e3eb5ce1',
  'self_excluded':rel(MANIFEST),'excluded_owned_files':[],
  'git_ignored_but_included':[s.decode() for s in p.stdout.split(b'\0') if s],
  'not_duplicated':'author 17429 raw blobs verified; only selected necessary inputs and evidence copied',
  'files':[{'path':rel(f),'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())} for f in ff]})
m=load(MANIFEST);assert {rel(p) for p in files()}=={x['path'] for x in m['files']}
for x in m['files']:
 b=(ROOT/x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
r.pop('actual_imports');r.pop('report_links');r['manifest_files']=len(m['files'])
print(json.dumps(r))
