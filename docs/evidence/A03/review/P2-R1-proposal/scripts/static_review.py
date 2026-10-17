# -*- coding: utf-8 -*-
"""Read/reproduce only the reviewed stdlib static checker and new JSON values.

No product imports, native authority, DB, network, old scenarios or field reset.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys
OUT=Path('D:/1800/docs/evidence/A03/review/P2-R1-proposal');STAGE=OUT/'input/checkout'
DATA=STAGE/'examples/a03/P2-R1-proposal/candidate-v2'
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
spec=importlib.util.spec_from_file_location('read_reviewed_static_checker',STAGE/'examples/a03/P2-R1-proposal/check_static.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.EVIDENCE=OUT/'author-reproduction';m.EVIDENCE.mkdir(parents=True,exist_ok=False)
m.main()
assert len(m.CHECKS)==32
pin=load(DATA/'profile.json');actual={p.relative_to(DATA).as_posix():sha(p.read_bytes()) for p in (DATA/'schemas').rglob('*.json')}
assert actual=={x['path']:x['sha256'] for x in pin['schema_pins']}
assert pin['api_supplement_sha256']==sha((DATA/'api-supplement-proposal.json').read_bytes())
independent={'profile_pins':len(actual),'api_supplement_sha256':pin['api_supplement_sha256'],'product_imports':0,'database_queries':0,'prefixes':[],'reports':[],'diagnostics':[]}
for name in ('first-unattempted-prefix','later-plan-prefix'):
 root=DATA/'cases'/name;p=load(root/'package.json');prefix=load(root/p['prefix']['path']);basis=load(root/p['basis']['path'])
 prev='0'*64;accepted=None;events=[]
 for seq,fr in enumerate(prefix['frames'],1):
  e=fr['event'];assert e['sequence']==seq and e['previous_hash']==prev
  assert e['event_hash']==sha(canonical({k:v for k,v in e.items() if k!='event_hash'}));prev=e['event_hash'];events.append(e['event'])
  if e['event']=='PLAN_ACCEPTED' and e['plan_ref']==prefix['subject_plan_ref']:accepted={'sequence':seq,'hash':prev}
 assert accepted==prefix['accepted_anchor'] and prefix['expected_book_head']=={'sequence':len(events),'hash':prev}
 assert basis['expected_event_head']==prefix['expected_book_head']
 independent['prefixes'].append({'case':name,'events':len(events),'accepted_sequence':accepted['sequence'],
  'artifact_scopes':sorted({a['scope_id'] for a in p['bundle']['artifacts']}),'non_null_frame_scopes':sorted({f['consumer_scope_id'] for f in prefix['frames'] if f['consumer_scope_id'] is not None}),
  'current_event_hashes_recomputed':True,'native_completeness':'NOT_EXECUTED'})
for name in ('late-receipt','different-snapshots'):
 root=DATA/'cases'/name;p=load(root/'package.json');nodes=p['bundle']['artifacts'];post=next(a for a in nodes if a['artifact_id']=='static-new-post')
 heads=[next(a for a in nodes if {k:a[k] for k in ('artifact_id','revision','kind','content_hash')}==r) for r in post['payload']['recovery_refs']]
 assert (root/'head-before.json').read_bytes()==(root/'head-after.json').read_bytes()
 for a in nodes:assert a['content_hash']==sha(canonical({k:v for k,v in a.items() if k!='content_hash'}))
 independent['reports'].append({'case':name,'heads':len(heads),'null_original_receipts':sum(h['payload']['original_receipt_ref'] is None for h in heads),
  'distinct_action_snapshots':len({sha(canonical(h['payload']['observed_snapshot_ref'])) for h in heads}),
  'immutable_head_bytes_equal':True,'reachability':p.get('reachability'),'journal_consistency':p.get('global_fact_journal_consistency'),
  'post_decision':post['payload']['decision'],'frame_structure':post['payload']['frame_structure'],
  'runtime_registration':'NOT_EXECUTED; static packet is not native-admissible history'})
root=DATA/'cases/first-unattempted-prefix';package=load(root/'package.json');basis=load(root/package['basis']['path'])
# The oracle is an explicit equality mandated by the proposal, independent of
# the checker result. These are value-only contradictions, never real handles.
for name,mutate,reason in [
 ('readonly-session-does-not-match-gate-binding',lambda v:v.update(readonly_session_id='different-static-session'),'basis.readonly_session_id must equal gate_binding.session_id and STARTED/READ records'),
 ('initial-head-not-in-canonical-prefix',lambda v:v.update(initial_event_head={'sequence':1,'hash':'e'*64}),'initial entry CAS must name the actual prefix head before this readonly session, not an unrelated digest')]:
 v=copy.deepcopy(basis);mutate(v)
 try:m.basis_check(v,package['bundle'],root);accepted=True;diagnostic=None
 except m.Invalid as e:accepted=False;diagnostic=str(e)
 record={'id':name,'kind':'STATIC_DIAGNOSTIC_VALUE_ONLY','required_result':'REJECT_CONTRADICTORY_VALUE','independent_reason':reason,
  'author_static_actual':'ACCEPTED' if accepted else 'REJECTED','diagnostic':diagnostic,'value':v,
  'whole_native_admissible_history':False,'no_product_or_authority_execution':True}
 write(OUT/'diagnostics'/f'{name}.json',record);independent['diagnostics'].append({k:v for k,v in record.items() if k!='value'})
# A version-only new Source node is structurally admitted by exchange-v2 but
# the checker independently rejects all new kinds outside receipt/report/PRE.
source=copy.deepcopy(next(a for a in package['bundle']['artifacts'] if a['kind']=='SourceBundle'))
source['schema_version']=pin['new_artifact_schema_version'];source['content_hash']=sha(canonical({k:v for k,v in source.items() if k!='content_hash'}))
value=copy.deepcopy(package['bundle']);value['artifacts']=[source]
shape_result='PASS';semantic_result=None
try:m.shape(value,'exchange-v2.schema.json')
except m.Invalid as e:shape_result=str(e)
try:m.artifacts(value,root);semantic_result='PASS'
except m.Invalid as e:semantic_result=str(e)
record={'id':'amended-source-kind-coverage','kind':'STATIC_DIAGNOSTIC_VALUE_ONLY','exchange_schema_actual':shape_result,'static_semantic_actual':semantic_result,
 'value':value,'scope':'isolated permitted envelope kind, not complete converted fixture or execution qualification',
 'independent_reason':'conversion target 1.2 Source is admitted by AmendedSourceBundle schema but checker artifacts() has no handling branch for it'}
write(OUT/'diagnostics/amended-source-kind-coverage.json',record);independent['diagnostics'].append({k:v for k,v in record.items() if k!='value'})
pre=DATA/'cases/pre-and-conversion-design';p=load(pre/'package.json');run=load(pre/p['pre_run']['path'])
independent['pre']={'decision':run['decision'],'checks':{k:v['outcome'] for k,v in run['checks'].items()},'native_admission':'NOT_EXECUTED'}
records=[load(q) for q in sorted((pre/'conversion/records').glob('*.json'))]
mapping=load(pre/'conversion/mapping-plan.json')
independent['conversion']={'states':[r['state'] for r in records],'completion_manifest':[r['completion_manifest'] for r in records],
 'mapping_status':mapping.get('status'),'committed_bundle':'NOT_PROVIDED/NOT_EXECUTED'}
assert all(not n.startswith('annotation') for n in sys.modules)
write(OUT/'independent-static-results.json',independent)
write(OUT/'static-process-release.json',{'pid':os.getpid(),'synchronous_static_runner':True,'child_processes_started':0,'background_processes_or_native_sessions':0,
 'product_imports':0,'DB_queries':0,'network_model_calls':0,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
 'release_basis':'parent command exit record to confirm runner completion; no background worker exists'})
print(json.dumps({'independent_prefixes':len(independent['prefixes']),'report_value_packets':len(independent['reports']),'new_diagnostic_values':len(independent['diagnostics']),
 'product_runs':0,'database_queries':0,'field_reset':'NOT_EXECUTED'}))
