"""One frozen complete package once, with non-mutating line tracing of its guard."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import types

OUT=Path(__file__).resolve().parents[1];ROOT=OUT/'input/checkout';EX=ROOT/'examples/a03/P2-R4-bridge-registration'
NAMES=['registration-positive','source-binding-negative','snapshot-binding-negative','target-tuple-negative']
name=sys.argv[1];assert name in NAMES and sys.flags.optimize==0
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
def h(v):return sha(canon(v))
def load(p):return json.loads(p.read_bytes())
def ref(a):return {k:a[k]for k in['artifact_id','revision','kind','content_hash']}
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')

# Author loader changes only fixed R3 base.EVID. Redirect the loader's OUT to
# this review directory; input ROOT and all Package/Schema code stay frozen.
os.environ['A03_R4_RUN_ID']=name
loader_path=EX/'fixed_entry.py';loader_raw=loader_path.read_bytes();tree=ast.parse(loader_raw.decode())
changes=[]
for node in tree.body:
    if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='OUT'for t in node.targets):
        changes.append(ast.get_source_segment(loader_raw.decode(),node))
        node.value=ast.copy_location(ast.Name(id='REVIEW_OUT',ctx=ast.Load()),node.value)
assert len(changes)==1
loader=types.ModuleType('_review_r4_fixed_entry');loader.__file__=str(loader_path);loader.__dict__['REVIEW_OUT']=OUT
sys.modules[loader.__name__]=loader
exec(compile(ast.fix_missing_locations(tree),str(loader_path),'exec'),loader.__dict__)
c=loader.c;assert loader.ROUTING['package_class_ast_unchanged']and not loader.ROUTING['old_36_matrix_called']
assert c.Package.entry_calls==0 and c.base.Package is c.Package

case_path=EX/'cases'/name/'case.json';case=load(case_path)
raw=(ROOT/case['bundle']).read_bytes();assert sha(raw)==case['bundle_sha256'];bundle=json.loads(raw)
overrides={};resource_pins=[]
for r in case['resources']:
    body=(ROOT/r['file']).read_bytes();assert sha(body)==r['sha256'];overrides[r['logical']]=body
    resource_pins.append(dict(r,bytes=len(body)))
assert len(overrides)==8 and len(bundle['artifacts'])==10
index={h(ref(a)):a for a in bundle['artifacts']};assert len(index)==10
for a in bundle['artifacts']:assert h({k:v for k,v in a.items()if k!='content_hash'})==a['content_hash']
seen_resources=set();ordinary_refs={}
def walk(v):
    if isinstance(v,dict):
        if set(v)=={'artifact_id','revision','kind','content_hash'}:
            assert h(v)in index and ref(index[h(v)])==v;ordinary_refs[h(v)]=v;return
        if {'path','sha256','media_type'}<=set(v):
            key=(v['path'],v['sha256']);body=overrides[v['path']];assert sha(body)==v['sha256']
            if key not in seen_resources:
                seen_resources.add(key)
                if v['media_type']=='application/json':walk(json.loads(body))
            return
        for x in v.values():walk(x)
    elif isinstance(v,list):
        for x in v:walk(x)
walk(bundle)
prefix=json.loads(overrides[case['prefix_resource']['path']]);assert len(prefix['frames'])==6
previous='0'*64;assert prefix['from_sequence']==1 and prefix['predecessor']=={'sequence':0,'hash':previous}
for number,frame in enumerate(prefix['frames'],1):
    event=frame['event'];assert frame['frame_version']=='a03-journal-consumer-frame-2'
    assert event['sequence']==number and event['previous_hash']==previous
    assert h({k:v for k,v in event.items()if k!='event_hash'})==event['event_hash']
    assert event['journal_id']==prefix['journal_id']and event['target_key']==prefix['target_key'];previous=event['event_hash']
assert prefix['expected_book_head']=={'sequence':6,'hash':previous}
anchor=prefix['accepted_anchor'];anchor_event=prefix['frames'][anchor['sequence']-1]['event']
assert anchor_event['event']=='PLAN_ACCEPTED'and anchor_event['event_hash']==anchor['hash']and anchor_event['plan_ref']==prefix['subject_plan_ref']
plan=index[h(prefix['subject_plan_ref'])]
assert anchor_event['payload']['actions']==[{'action_id':a['action_id'],'action_digest':h(a)}for a in plan['payload']['actions']]
event=prefix['frames'][-1]['event'];payload=event['payload'];frame=prefix['frames'][-1]
assert event['event']=='TARGET_DRIFT_HOLD'and event['plan_ref']is None and payload['plan_ref']is None
source=index[h(payload['source_ref'])];snapshot=index[h(payload['snapshot_ref'])]
owner=next(a for a in bundle['artifacts']if a['artifact_id']=='r4-registration-prefix-consumer')
observation=json.loads(overrides[payload['observation']['path']]);business=observation['business_value']
assert observation['source_ref']==payload['source_ref']and observation['snapshot_ref']==payload['snapshot_ref']
assert observation['target_key']==event['target_key']and observation['scope_id']==payload['scope_id']==frame['consumer_scope_id']
assert observation['registration_id']==payload['registration_id']and observation['target_state_hash']==payload['target_state_hash']==h(business)
semantic={'source_ref':payload['source_ref'],'snapshot_ref':payload['snapshot_ref'],'owner_ref':ref(owner),
 'owner_book':owner['book_id'],'owner_scope':owner['scope_id'],'source_book':source['book_id'],'source_scope':source['scope_id'],
 'snapshot_book':snapshot['book_id'],'snapshot_scope':snapshot['scope_id'],'payload_scope':payload['scope_id'],
 'frame_scope':frame['consumer_scope_id'],'snapshot_target_id':snapshot['payload']['target_id'],'canonical_target_key':event['target_key'],
 'source_snapshot_scope_match':source['scope_id']==snapshot['scope_id']==payload['scope_id'],
 'book_match':source['book_id']==snapshot['book_id']==owner['book_id']==event['target_key']['book_id'],
 'snapshot_target_matches':snapshot['payload']['target_id']==event['target_key']['target_id'],
 'synthetic_observation_only':observation['status']}

r2_path=ROOT/'examples/a03/P2-R2-proposal/check.py'
lines=r2_path.read_text(encoding='utf8').splitlines()
guard_line=next(i+1 for i,x in enumerate(lines)if "source['book_id']==snapshot['book_id']==book"in x)
global_line=next(i+1 for i,x in enumerate(lines)if "self.scan(e['resource'],'E:'+e['evidence_id'],None,None"in x)
guards=[];trace_exceptions=[]
def trace(frame,event,arg):
    if frame.f_code.co_filename!=str(r2_path):return trace
    if event=='line'and frame.f_lineno==guard_line and frame.f_code.co_name=='scan':
        v=frame.f_locals;s=v['source'];sn=v['snapshot'];consumer_book=v['book'];self=v['self']
        guards.append({'source_line':guard_line,'path':v['path'],'consumer_book':consumer_book,'consumer_scope':v['scope'],
          'phase':'GLOBAL_UNBOUND_EVIDENCE'if consumer_book is None else'ACTUAL_ARTIFACT_CONSUMPTION',
          'active_contexts':list(self.contexts),'source_book':s['book_id'],'snapshot_book':sn['book_id'],
          'source_scope':s['scope_id'],'snapshot_scope':sn['scope_id'],'payload_scope':v['e']['payload']['scope_id'],
          'predicate':s['kind']=='SourceBundle'and sn['kind']=='PlatformSnapshot'and s['book_id']==sn['book_id']==consumer_book and s['scope_id']==sn['scope_id']==v['e']['payload']['scope_id']})
    if event=='exception'and frame.f_lineno==guard_line:
        error=arg[1]
        trace_exceptions.append({'line':guard_line,'type':type(error).__name__,'code':getattr(error,'code',None),'path':getattr(error,'path',None)})
    return trace
pkg=c.Package(bundle,overrides);sys.settrace(trace)
try:
    try:pkg.validate();actual='STATIC_ACCEPTED';error=None
    except c.Rejected as e:actual=e.code;error={'code':e.code,'path':e.path}
finally:sys.settrace(None)
assert c.Package.entry_calls==1
assert actual=='FRAME_REGISTRATION_BINDING'and guards and trace_exceptions
if name in ['registration-positive','target-tuple-negative']:
    assert [g['predicate']for g in guards]==[True,False]
    assert [g['phase']for g in guards]==['ACTUAL_ARTIFACT_CONSUMPTION','GLOBAL_UNBOUND_EVIDENCE']
    conclusion='REWORK_FALSE_REJECTION'if name=='registration-positive'else'BLOCKED_TARGET_CONTROL_MASKED'
    exit_code=1
else:
    assert len(guards)==1 and guards[0]['phase']=='ACTUAL_ARTIFACT_CONSUMPTION'and not guards[0]['predicate']
    conclusion='EXPECTED_STATIC_REGISTRATION_REJECTION';exit_code=0
assert not any(n=='annotation'or n.startswith('annotation.')for n in sys.modules)
record={'case':name,'actual':actual,'error':error,'conclusion':conclusion,'whole_package_calls':1,'case_raw_sha256':sha(case_path.read_bytes()),
 'bundle_sha256':sha(raw),'all_10_artifact_hashes_correct':True,'all_6_event_hashes_and_full_chain_correct':True,
 'all_8_resource_hashes_correct':True,'all_ordinary_refs_exact':True,'resource_pins':resource_pins,
 'semantic_tuple':semantic,'actual_guard_visits':guards,'guard_exceptions':trace_exceptions,
 'inherited_guard_line':guard_line,'contextless_global_evidence_line':global_line,
 'loader_source_sha256':sha(loader_raw),'loader_out_assignment_redirected':changes,
 'loader_redirection':'OUT replaced with this independent review root; fixed loader in turn changes only R3 base.EVID',
 'fixed_loader_routing':loader.ROUTING,'loaded_sources':c.loaded_sources(),'trace_method':'sys.settrace observes inherited guard without replacing Package or predicate',
 'old_36_matrix_runs':0,'product_planner_DB_native_network_model_calls':0,'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'cases'/name/'result.json',record)
print(json.dumps({'case':name,'actual':actual,'error':error,'conclusion':conclusion,'guard_phases':[g['phase']for g in guards],'package_calls':1}))
sys.exit(exit_code)
