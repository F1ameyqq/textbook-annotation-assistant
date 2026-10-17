# -*- coding: utf-8 -*-
"""Bounded reviewed static checker, independent bindings and ONE closure probe.

No product import, DB, native session, planner call or rejected field-reset probe.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys
ROOT=Path('D:/1800');OUT=ROOT/'docs/evidence/A03/review/P2-R2-proposal';STAGE=OUT/'input/checkout'
HOME=STAGE/'examples/a03/P2-R2-proposal';DATA=HOME/'candidate-final'
def load(p):return json.loads(p.read_bytes())
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(a):return {k:a[k] for k in ('artifact_id','revision','kind','content_hash')}
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
sys.path.insert(0,str(HOME))
spec=importlib.util.spec_from_file_location('reviewed_R2_static_checker',HOME/'check.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
repro=OUT/'author-reproduction';(repro/'inputs').mkdir(parents=True,exist_ok=False)
copies=[]
for name in ('readonly-session-does-not-match-gate-binding.json','initial-head-not-in-canonical-prefix.json','amended-source-kind-coverage.json'):
 source=STAGE/'docs/evidence/A03/execution/P2-R2-proposal/inputs'/name;b=source.read_bytes()
 with (repro/'inputs'/name).open('xb') as f:f.write(b)
 copies.append({'name':name,'sha256':sha(b),'bytes':len(b)})
m.EVID=repro;m.main()
assert len(m.RESULTS)==36
bundle=load(DATA/'scope-session.json');pkg=m.Package(bundle).validate();basis=pkg.read(load(DATA/'case-index.json')['basis']);session=m.session(pkg,basis)
prefix=pkg.read(basis['complete_uncalled_prefix']);previous='0'*64;heads={0:previous}
for i,frame in enumerate(prefix['frames'],1):
 e=frame['event'];assert e['sequence']==i and e['previous_hash']==previous
 assert e['event_hash']==sha(canon({k:v for k,v in e.items() if k!='event_hash'}));previous=e['event_hash'];heads[i]=previous
start=next(e['event'] for e in prefix['frames'] if e['event']['event']=='READONLY_ABSENCE_STARTED')
assert basis['initial_event_head']=={'sequence':start['sequence']-1,'hash':heads[start['sequence']-1]}
assert basis['expected_event_head']=={'sequence':len(prefix['frames']),'hash':previous}
assert basis['binding']==basis['gate_binding'] and basis['binding']['readonly_session_id']==basis['readonly_session_id']
target=m.check_conversion(pkg);mapping=pkg.read(load(DATA/'conversion/case.json')['mapping'])
independent={'candidate_profile_sha256':sha((DATA/'profile.json').read_bytes()),'author_reproduction_input_copies':copies,
 'whole_scope_package':{'artifacts':len(bundle['artifacts']),'book_ids':sorted({a['book_id'] for a in bundle['artifacts']}),
  'scopes':sorted({a['scope_id'] for a in bundle['artifacts']}),'consumer_count':len(pkg.consumers),'mixed_DAG_nodes':len(pkg.edges),
  'whole_entry_static':'ACCEPTED','scope_plan_branch_only':True},
 'session':{'checker':session,'independent_chain_events':len(prefix['frames']),'initial_head_matches_before_STARTED':True,
  'final_head_matches_prefix':True,'same_binding':True,'actual_target_reads':'NOT_EXECUTED','native_fence_or_CAS':'NOT_EXECUTED'},
 'conversion':{'old_nodes':len(pkg.read(load(DATA/'conversion/case.json')['source'])['artifacts']),'new_nodes':len(target['artifacts']),
  'new_kinds':sorted({a['kind'] for a in target['artifacts']}),'old_mapped':sum(r['new_ref'] is not None for r in mapping['artifacts']),
  'old_archive_only':sum(r['new_ref'] is None for r in mapping['artifacts']),'new_derived':len(mapping['new_derived']),
  'INITIAL':m.pre_context(m.Package(target),load(DATA/'converted/initial-run.json')),
  'POST_HOLD':m.pre_context(m.Package(target),load(DATA/'post-hold/run.json')),'real_conversion':'NOT_EXECUTED'}}
# Only one targeted non-frame closure diagnostic. Keep Artifact refs and hashes
# intact; change the formal EvidenceRecord Resource followed by existing IDs.
bad=copy.deepcopy(bundle);original_proof=copy.deepcopy(bad['evidence'][0]);neutral=copy.deepcopy(original_proof)
neutral['evidence_id']='review-neutral-proof';bad['evidence'].append(neutral)
leaf=copy.deepcopy(next(a for a in bundle['artifacts'] if a['kind']=='SourceBundle' and a['scope_id']=='original-b'))
leaf['schema_version']=m.VERSION;leaf['artifact_id']='review-isolated-source-b'
def neutralize(v):
 if isinstance(v,dict):return {k:neutralize(x) for k,x in v.items()}
 if isinstance(v,list):return [neutralize(x) for x in v]
 return 'review-neutral-proof' if v=='proof' else v
leaf['payload']=neutralize(leaf['payload']);leaf['content_hash']=sha(canon({k:v for k,v in leaf.items() if k!='content_hash'}));bad['artifacts'].append(leaf)
overrides={};resource_files=[];folder=OUT/'counterexample/evidence-id-consumer'
def virtual(logical,value,filename):
 raw=canon(value)+b'\n';overrides[logical]=raw;p=folder/filename;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
 r={'path':logical,'sha256':sha(raw),'media_type':'application/json','origin':'SYNTHETIC'};resource_files.append({'logical':logical,'file':p.relative_to(OUT).as_posix(),'sha256':sha(raw)})
 return r
inner=virtual('review-static/inner.json',{'ordinary_ref':ref(leaf)},'inner.json')
outer=virtual('review-static/outer.json',{'nested':inner},'outer.json')
bad['evidence'][0]['resource']=outer
before_source=next(a for a in bad['artifacts'] if a['artifact_id']=='origin-a-SourceBundle')
assert before_source['payload']['external_page_mappings'][0]['evidence_refs']==['proof']
assert ref(leaf) not in before_source['input_refs'] and before_source['scope_id']!=leaf['scope_id']
for a in bad['artifacts']:assert a['content_hash']==sha(canon({k:v for k,v in a.items() if k!='content_hash'}))
try:
 checked=m.Package(bad,overrides).validate();m.session(checked,basis)
 actual='STATIC_ACCEPTED';error=None
except m.Rejected as e:actual='STATIC_REJECTED';error={'code':e.code,'path':e.path}
write(folder/'bundle.json',bad)
case={'id':'R2-SCOPE-EVIDENCE-ID-01','base_bundle_sha256':sha((DATA/'scope-session.json').read_bytes()),'expected':'REJECT_UNDECLARED_NONFRAME_REFERENCE (and cross-scope if declared)',
 'actual':actual,'error':error,'resource_overrides':resource_files,'bundle_file':'counterexample/evidence-id-consumer/bundle.json',
 'consumer':'origin-a-SourceBundle','consumer_scope':'original-a','formal_evidence_path':'payload.external_page_mappings/0/evidence_refs[proof]',
 'referenced_artifact':ref(leaf),'reference_scope':'original-b','ordinary_ref_declared_by_consumer':False,
 'all_artifact_hashes_recomputed_equal':True,'native_qualification':False,
 'limits':'new static JSON only; no product/native/DB. One extra isolated Source and two Resource values; no candidate source edit.'}
write(folder/'result.json',case);independent['nonframe_evidence_probe']=case
independent['local_conclusion']={'SCOPE-01':'REWORK' if actual=='STATIC_ACCEPTED' else 'STATIC_ACCEPTED_LIMITED',
 'SESSION-02':'STATIC_ACCEPTED_LIMITED','CONVERSION-07':'STATIC_ACCEPTED_LIMITED',
 'R17_VERSION_BRIDGE':'BLOCKED','REGISTRATION_SCOPE_BRANCH':'BLOCKED_NOT_POSITIVELY_VERIFIED','all_native_functions':'NOT_EXECUTED'}
assert all(not x.startswith('annotation') for x in sys.modules)
write(OUT/'independent-static-results.json',independent)
write(OUT/'process-release.json',{'static_runner_pid':os.getpid(),'started_child_processes':0,'native_sessions':0,'background_processes':0,'product_imports':0,
 'release_basis':'parent completion record confirms this synchronous runner exited; no OS-wide scan','field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print(json.dumps({'independent_conclusion':independent['local_conclusion'],'evidence_id_counterexample_actual':actual,'product_runs':0,'DB_queries':0}))
