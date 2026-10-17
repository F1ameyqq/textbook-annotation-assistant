# -*- coding: utf-8 -*-
"""Independent frozen JSON/source inspection. No checker import or execution."""
import ast
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parents[1];ROOT=OUT/'input/checkout';EX=ROOT/'examples/a03/P2-R6-mixed-control';EV=ROOT/'docs/evidence/A03/execution/P2-R6-mixed-control';DATA=ROOT/'examples/a03/P2-R2-proposal/candidate-final'
def load(p):return json.loads(p.read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def h(v):return sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def ref(a):return {k:a[k]for k in ['artifact_id','revision','kind','content_hash']}
def isref(v):return isinstance(v,dict)and set(v)=={'artifact_id','revision','kind','content_hash'}
def isres(v):return isinstance(v,dict)and {'path','sha256','media_type'}<=set(v)
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def diff(a,b,path=''):
    assert type(a)is type(b),(path,'type changed')
    if isinstance(a,dict):
        assert a.keys()==b.keys(),(path,'keys changed')
        return [r for k in a for r in diff(a[k],b[k],path+'/'+k)]
    if isinstance(a,list):
        assert len(a)==len(b),(path,'length changed')
        return [r for i,(x,y)in enumerate(zip(a,b))for r in diff(x,y,path+'/'+str(i))]
    return []if a==b else[{'path':path,'old':a,'new':b}]

case=load(EX/'case.json');old_case=load(ROOT/case['source_case'])
old=load(ROOT/old_case['bundle']);raw=(ROOT/case['bundle']).read_bytes();bundle=json.loads(raw)
assert sha(raw)==case['bundle_sha256']=='6a39c873de02dab04d3efd831cb1032b87ba8323c35bfd2a7a31f0b2e48dabd2'
assert sha((EX/'case.json').read_bytes())=='2763198f4b68b9e636b00780cf5a28b8a89ac0dc117269c43fc6efc731bccab2'
over={r['logical']:(ROOT/r['file']).read_bytes()for r in case['resources']}
old_over={r['logical']:(ROOT/r['file']).read_bytes()for r in old_case['resources']}
for r in case['resources']:assert sha(over[r['logical']])==r['raw_sha256']and len(over[r['logical']])==r['bytes']
new_prefix=json.loads(over['r5-static/cycle-prefix.json']);old_prefix=json.loads(old_over['r5-static/cycle-prefix.json'])
prefix_diff=diff(old_prefix,new_prefix);bundle_diff=diff(old,bundle)
allowed={'/frames/7/event/payload/initial_event_head/hash','/expected_book_head/hash'}
allowed.update('/frames/'+str(i)+'/event/event_hash'for i in range(7,14))
allowed.update('/frames/'+str(i)+'/event/previous_hash'for i in range(8,14))
assert len(prefix_diff)==15 and {x['path']for x in prefix_diff}==allowed
assert len(bundle_diff)==1 and bundle_diff[0]['path']=='/evidence/1/resource/sha256'
assert bundle['artifacts']==old['artifacts']and len(bundle['artifacts'])==16
assert new_prefix['accepted_anchor']==old_prefix['accepted_anchor']and new_prefix['accepted_anchor']['sequence']==5
assert over['r5-static/cycle-return.json']==old_over['r5-static/cycle-return.json']
artifacts={h(ref(a)):a for a in bundle['artifacts']};assert len(artifacts)==16
for a in bundle['artifacts']:assert h({k:v for k,v in a.items()if k!='content_hash'})==a['content_hash']
evidence={x['evidence_id']:x for x in bundle['evidence']};assert len(evidence)==len(bundle['evidence'])
resources={};prefixes=[];bases=[];all_refs={}
def read_resource(r):
    key=(r['path'],r['sha256']);p=(DATA/r['path']).resolve();assert p.is_relative_to(DATA)
    if key not in resources:
        b=over[r['path']]if r['path']in over else p.read_bytes();assert sha(b)==r['sha256'],r
        resources[key]={'path':r['path'],'sha256':sha(b),'bytes':len(b),'body':json.loads(b)if r['media_type']=='application/json'else None}
    return resources[key]['body']
passive_seen=set()
def passive(v,path='$'):
    if isref(v):assert h(v)in artifacts and ref(artifacts[h(v)])==v;all_refs[h(v)]=v;return
    if isres(v):
        key=(v['path'],v['sha256']);body=read_resource(v)
        if key not in passive_seen:
            passive_seen.add(key)
            if body is not None:passive(body,v['path'])
        return
    if isinstance(v,dict):
        if v.get('format_version')=='a03-runtime-event-prefix-2':
            assert v['predecessor']=={'sequence':0,'hash':'0'*64}and v['from_sequence']==1
            prev='0'*64;heads=[]
            for number,f in enumerate(v['frames'],1):
                e=f['event'];assert e['sequence']==number and e['previous_hash']==prev
                assert h({k:x for k,x in e.items()if k!='event_hash'})==e['event_hash']
                assert e['journal_id']==v['journal_id']and e['target_key']==v['target_key']
                if 'initial_event_head'in e['payload']:
                    expected={'sequence':number-1,'hash':prev};assert e['payload']['initial_event_head']==expected,(path,number)
                    heads.append({'sequence':number,'initial_event_head':expected})
                prev=e['event_hash']
            assert v['expected_book_head']=={'sequence':len(v['frames']),'hash':prev}
            a=v['accepted_anchor'];event=v['frames'][a['sequence']-1]['event']
            assert event['event']=='PLAN_ACCEPTED'and event['event_hash']==a['hash']and event['plan_ref']==v['subject_plan_ref']
            prefixes.append({'resource':path,'events':len(v['frames']),'internal_heads':heads,'accepted_anchor':a,'expected_head':v['expected_book_head']})
        if {'initial_event_head','expected_event_head','complete_uncalled_prefix'}<=set(v):
            p=read_resource(v['complete_uncalled_prefix']);start=next(f['event']for f in p['frames']if f['event']['event']=='READONLY_ABSENCE_STARTED')
            assert v['initial_event_head']==start['payload']['initial_event_head']and v['expected_event_head']==p['expected_book_head']
            bases.append({'resource':path,'initial_head':v['initial_event_head'],'expected_head':v['expected_event_head']})
        for k,x in v.items():passive(x,path+'/'+k)
    elif isinstance(v,list):
        for i,x in enumerate(v):passive(x,path+'/'+str(i))
passive(bundle);assert len(resources)==18 and len(prefixes)==2 and bases

# Locate formal ID arrays from pinned schema/type structure, then inspect each
# actual consumer independently. This is data inspection, not a Package route.
exchange=load(DATA/'schemas/exchange-v3.schema.json');prefix_schema=load(DATA/'schemas/prefix-v2.schema.json');fact_schema=load(DATA/'schemas/fact-v3.schema.json')
formal_names={'evidence_refs','before_evidence_refs','after_evidence_refs','submission_evidence_refs'}
id_pattern=exchange['$defs']['EvidenceRecord']['properties']['evidence_id']['pattern'];slots={}
def resolve(n,doc):
    if '$ref'not in n:return n
    p=doc
    for t in n['$ref'][2:].split('/'):p=p[t.replace('~1','/').replace('~0','~')]
    return p
def plausible(v,n,doc):
    n=resolve(n,doc)
    if 'const'in n and v!=n['const']:return False
    if 'enum'in n and v not in n['enum']:return False
    if isinstance(v,dict):
        if not set(n.get('required',[]))<=set(v):return False
        props=n.get('properties',{})
        if n.get('additionalProperties')is False and set(v)-set(props):return False
        for k,child in props.items():
            if k in v and ('const'in child or'enum'in child)and not plausible(v[k],child,doc):return False
    return True
def mark(v,n,doc,path=''):
    n=resolve(n,doc)
    for tag in ['oneOf','anyOf']:
        for i,branch in enumerate(n.get(tag,[])):
            if plausible(v,branch,doc):mark(v,branch,doc,path+'/'+tag+'/'+str(i))
    if isinstance(v,dict):
        for k,child in n.get('properties',{}).items():
            if k in v:
                item=child.get('items',{})
                if k in formal_names and child.get('type')=='array'and item.get('type')=='string'and item.get('pattern')==id_pattern:
                    slots[id(v[k])]=v[k]
                mark(v[k],child,doc,path+'/'+k)
    elif isinstance(v,list)and isinstance(n.get('items'),dict):
        for x in v:mark(x,n['items'],doc,path+'/[]')
def artifact_definition(a):return exchange['$defs'][('Amended'if a['schema_version']=='1.3.0-a03-static-proposal'else'')+a['kind']]
consumer_audits=[];covered_frames=set()
def consumer(v,book,scope,declared,path,schema,doc):
    assert book is not None;mark(v,schema,doc);found={}
    scan(v,book,scope,found,path,set())
    declared_map={h(x):x for x in declared};assert set(found)<=set(declared_map),(path,'undeclared',set(found)-set(declared_map))
    for r in declared_map.values():
        a=artifacts[h(r)];assert a['book_id']==book and a['scope_id']==scope,(path,'book/scope')
    consumer_audits.append({'path':path,'book':book,'scope':scope,'found_count':len(found),'declared_count':len(declared_map),'faults':[]})
def scan(v,book,scope,found,path,active):
    if isref(v):assert h(v)in artifacts;found[h(v)]=v;return
    if isres(v):
        key=(v['path'],v['sha256']);body=read_resource(v)
        if body is not None and key not in active:scan(body,book,scope,found,v['path'],active|{key})
        return
    if isinstance(v,dict):
        if v.get('format_version')=='a03-runtime-event-prefix-2':
            assert v['target_key']['book_id']==book
            for k,x in v.items():
                if k!='frames':scan(x,book,scope,found,path+'/'+k,active)
            for i,f in enumerate(v['frames']):
                e=f['event'];assert e['target_key']==v['target_key']
                expected=artifacts[h(e['plan_ref'])]['scope_id']if e['plan_ref']is not None else None
                assert f['consumer_scope_id']==expected;covered_frames.add((path,i))
                consumer(e,book,expected,f['input_refs'],path+'/frames/'+str(i),prefix_schema['properties']['frames']['items']['properties']['event'],prefix_schema)
            return
        if v.get('format_version')=='a03-action-fact-3':mark(v,fact_schema,fact_schema)
        if {'schema_version','artifact_id','revision','kind','payload','content_hash','input_refs'}<=set(v):mark(v,artifact_definition(v),exchange)
        for k,x in v.items():scan(x,book,scope,found,path+'/'+k,active)
    elif isinstance(v,list):
        if slots.get(id(v))is v:
            for eid in v:
                assert eid in evidence,(path,'missing evidence ID');scan(evidence[eid]['resource'],book,scope,found,path+'['+eid+']',active)
        else:
            for i,x in enumerate(v):scan(x,book,scope,found,path+'/'+str(i),active)
for a in bundle['artifacts']:consumer(a['payload'],a['book_id'],a['scope_id'],a['input_refs'],a['artifact_id'],artifact_definition(a)['properties']['payload'],exchange)
for p in prefixes:assert all((p['resource'],i)in covered_frames for i in range(p['events']))

source=next(a for a in bundle['artifacts']if a['artifact_id']=='r5-mixed-cycle-source-consumer');record=evidence['proof-r5-mixed-cycle'];pr=record['resource']
i=next(i for i,f in enumerate(new_prefix['frames'])if f['event']['event']=='PLAN_ACCEPTED'and f['consumer_scope_id']==source['scope_id'])
frame=new_prefix['frames'][i];rr=frame['event']['payload']['evidence'];returned=read_resource(rr)
assert returned['ordinary_source_ref']==ref(source)and ref(source)in frame['input_refs']and source['input_refs']==[new_prefix['subject_plan_ref']]
assert any('proof-r5-mixed-cycle'in m['evidence_refs']for m in source['payload']['external_page_mappings'])
nodes=['A:'+h(ref(source)),'E:proof-r5-mixed-cycle','R:'+pr['path']+':'+pr['sha256']]
nodes+=[nodes[-1]+'/F:'+str(i),'R:'+rr['path']+':'+rr['sha256'],nodes[0]]
ring=[{'from':a,'to':b}for a,b in zip(nodes,nodes[1:])]
assert ring==load(EV/'precheck.json')['ring_edges']

# Parse, never execute, the original failed driver. Python parses the full
# module before imports/statements, so this SyntaxError precludes any Package.
failed=(EV/'runs/entry-01/registered-script.py').read_bytes();current=(EX/'entry.py').read_bytes()
assert sha(failed)==load(EV/'runs/entry-01/registration.json')['script_sha256']
try:ast.parse(failed.decode('utf8'));raise AssertionError('failed driver unexpectedly parses')
except SyntaxError as e:failure={'line':e.lineno,'offset':e.offset,'message':e.msg,'text':e.text}
assert failure['line']==25 and b'__code__and'in failed and failed.replace(b'__code__and',b'__code__ and')==current
ast.parse(current.decode('utf8'));assert load(EV/'runs/entry-01/exit.json')['exit_code']==1
assert not(EV/'runs/entry-01/stdout.txt').read_bytes()and b'SyntaxError'in(EV/'runs/entry-01/stderr.txt').read_bytes()
write(OUT/'independent-data-audit.json',{'status':'INDEPENDENT_DATA_READY_FOR_SINGLE_ENTRY','Package_calls':0,'bundle_sha256':sha(raw),
 'prefix_sha256':sha(over['r5-static/cycle-prefix.json']),'prefix_leaf_changes':prefix_diff,'bundle_leaf_changes':bundle_diff,
 'artifact_count':16,'all_artifact_hashes_correct':True,'all_artifacts_and_refs_unchanged':True,'return_resource_bytes_unchanged':True,
 'resources':[{k:v for k,v in x.items()if k!='body'}for x in resources.values()],'prefixes':prefixes,'basis_heads':bases,
 'consumer_audits':consumer_audits,'ring_edges':ring,'schema_typed_ID_arrays':'pinned schema paths; no checker imports; each actual data consumer has its own found/declared context',
 'new_residuals':[],'author_precheck_true_fields_used_as_proof':False})
write(OUT/'failed-driver-static-audit.json',{'failure_source_sha256':sha(failed),'current_source_sha256':sha(current),'static_SyntaxError':failure,
 'only_source_difference':'one separating space: __code__and -> __code__ and','failed_driver_executed_by_reviewer':False,
 'failed_Package_calls':0,'basis':'entire-file parsing fails before module imports and top-level execution; frozen stdout empty, stderr SyntaxError, exit1 retained'})
print(json.dumps({'result':'INDEPENDENT_DATA_READY_FOR_SINGLE_ENTRY','prefix_changes':len(prefix_diff),'bundle_changes':len(bundle_diff),
 'artifacts':16,'resources':len(resources),'prefixes':len(prefixes),'consumer_data_checks':len(consumer_audits),'ring_edges':5,'Package_calls':0}))
