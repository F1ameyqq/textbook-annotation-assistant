"""R3 static overlay: formal EvidenceRecord IDs belong to actual consumers.

Loads only SHA-pinned R2 static checker/helpers. No product import or new profile.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HOME=Path(__file__).resolve().parent
ROOT=HOME.parents[2]
OUT=ROOT/'docs/evidence/A03/execution/P2-R3-evidence-closure'
R2=ROOT/'examples/a03/P2-R2-proposal'
PINS=json.loads((OUT/'r2-input-pins.json').read_bytes())
PIN_BY_PATH={p['path']:p for p in PINS['inputs']}

def sha(raw):return hashlib.sha256(raw).hexdigest()
def pinned(path):
    raw=path.read_bytes();name=path.relative_to(ROOT).as_posix();expected=PIN_BY_PATH[name]
    assert len(raw)==expected['bytes'] and sha(raw)==expected['sha256'],name
    return raw
def module(name,path):
    pinned(path);spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec)
    sys.modules[name]=value;spec.loader.exec_module(value);return value

schema_module=module('schema_check',R2/'schema_check.py')
oracle_module=module('oracle_verifier',R2/'oracle_verifier.py')
base=module('_r3_fixed_r2_checker',R2/'check.py')
RUN_ID=os.environ.get('A03_R3_RUN_ID','manual')
assert RUN_ID.replace('-','').isalnum()
base.EVID=OUT/'r2-regression'/RUN_ID
base.EVID.mkdir(parents=True,exist_ok=True)
OriginalPackage=base.Package
Rejected=base.Rejected
need=base.need
canon=base.canon
h=base.h
ref=base.ref

DOC_PATHS={'exchange':R2/'candidate-final/schemas/exchange-v3.schema.json',
           'fact':R2/'candidate-final/schemas/fact-v3.schema.json',
           'prefix':R2/'candidate-final/schemas/prefix-v2.schema.json'}
DOCS={k:json.loads(pinned(p))for k,p in DOC_PATHS.items()}
ID_PATTERN=DOCS['exchange']['$defs']['EvidenceRecord']['properties']['evidence_id']['pattern']
# These are contract field names, classified ONLY inside exact pinned schemas.
# Resource-valued attempt/reconciliation evidence is deliberately not an ID.
FORMAL_NAMES={'evidence_refs','before_evidence_refs','after_evidence_refs','submission_evidence_refs'}
FIELDS={}

def catalog(docname,node,pointer=''):
    for key,child in node.get('properties',{}).items():
        location=pointer+'/properties/'+key
        if key in FORMAL_NAMES and child.get('type')=='array' and child.get('items',{}).get('type')=='string' and child['items'].get('pattern')==ID_PATTERN:
            FIELDS[(docname,location)]={'schema':DOC_PATHS[docname].relative_to(ROOT).as_posix(),'schema_pointer':'#'+location,'field':key,'id_pattern':ID_PATTERN}
        catalog(docname,child,location)
    for key,child in node.get('$defs',{}).items():catalog(docname,child,pointer+'/$defs/'+key)
    if isinstance(node.get('items'),dict):catalog(docname,node['items'],pointer+'/items')
    for key in('oneOf','anyOf'):
        for i,child in enumerate(node.get(key,[])):catalog(docname,child,pointer+'/'+key+'/'+str(i))
for name,doc in DOCS.items():catalog(name,doc)

class Package(OriginalPackage):
    """The single corrected whole-package entry used by controls and R2 matrix."""
    entry_calls=0
    def __init__(self,bundle,overrides=None):
        super().__init__(bundle,overrides)
        self.evidence_index={};self.typed_lists={};self.contexts=[];self.evidence_stack=[]
        self.evidence_uses=[];self.evidence_refs=[];self.active_consumers=set()

    def slots(self,value,node,docname,pointer):
        doc=DOCS[docname]
        if '$ref'in node:
            target_pointer=node['$ref'];need(target_pointer.startswith('#/'),'EVIDENCE_SCHEMA_REF',target_pointer)
            target=doc
            for token in target_pointer[2:].split('/'):target=target[token.replace('~1','/').replace('~0','~')]
            self.slots(value,target,docname,target_pointer[1:])
        for key in('oneOf','anyOf'):
            for i,child in enumerate(node.get(key,[])):
                try:base.validate(value,child,doc)
                except Rejected:continue
                self.slots(value,child,docname,pointer+'/'+key+'/'+str(i))
        if isinstance(value,list)and(docname,pointer)in FIELDS:
            # Strong reference prevents Python object-id reuse. No shared found/scope cache.
            self.typed_lists[id(value)]=(value,FIELDS[(docname,pointer)])
        if isinstance(value,dict):
            for key,child in node.get('properties',{}).items():
                if key in value:self.slots(value[key],child,docname,pointer+'/properties/'+key)
        if isinstance(value,list)and isinstance(node.get('items'),dict):
            for member in value:self.slots(member,node['items'],docname,pointer+'/items')

    def artifact_schema(self,a):
        if a.get('schema_version')==base.VERSION:name='Amended'+a.get('kind','')
        elif a.get('schema_version')=='1.1.0-a-recovery-proposal':name=a.get('kind','')
        else:return None
        return name if name in DOCS['exchange']['$defs'] else None

    def known_resource_type(self,v):
        if not isinstance(v,dict):return
        required={'schema_version','artifact_id','revision','kind','run_id','book_id','scope_id','created_at','producer','input_refs','content_hash','payload'}
        if required<=set(v):
            name=self.artifact_schema(v)
            if name:
                node=DOCS['exchange']['$defs'][name];base.validate(v,node,DOCS['exchange'])
                self.slots(v,node,'exchange','/$defs/'+name)
        if v.get('format_version')=='a03-action-fact-3':
            base.validate(v,DOCS['fact']);self.slots(v,DOCS['fact'],'fact','')

    def consumer(self,node,v,book,scope,declared,path):
        key=(node,book,scope)
        if key in self.active_consumers:return # Edge is already present; global DAG rejects recursion.
        a=self.index.get(node[2:])if node.startswith('A:')else None
        context={'node':node,'consumer':path,'book_id':book,'scope_id':scope,'kind':a['kind']if a else'TYPED_FRAME','schema_version':a['schema_version']if a else None}
        if a:
            name=self.artifact_schema(a);payload=DOCS['exchange']['$defs'][name]['properties']['payload']
            self.slots(v,payload,'exchange','/$defs/'+name+'/properties/payload')
        else:
            event=DOCS['prefix']['properties']['frames']['items']['properties']['event']
            self.slots(v,event,'prefix','/properties/frames/items/properties/event')
        self.active_consumers.add(key);self.contexts.append(context)
        try:return super().consumer(node,v,book,scope,declared,path)
        finally:self.contexts.pop();self.active_consumers.remove(key)

    def scan(self,v,parent,book,scope,found,path,active,resource_root):
        self.known_resource_type(v)
        slot=self.typed_lists.get(id(v))if isinstance(v,list)else None
        if slot is not None and slot[0]is v and self.contexts:
            for evidence_id in v:
                need(evidence_id in self.evidence_index,'EVIDENCE_ID_MISSING',path+'['+str(evidence_id)+']')
                record=self.evidence_index[evidence_id];node='E:'+evidence_id
                self.edge(parent,node)
                use=dict(self.contexts[-1],formal_path=path,evidence_id=evidence_id,field_authority=slot[1])
                self.evidence_uses.append(use);self.evidence_stack.append(use)
                try:self.scan(record['resource'],node,book,scope,found,path+'['+evidence_id+']/EvidenceRecord.resource',active,False)
                finally:self.evidence_stack.pop()
            return
        if base.isref(v)and self.contexts and self.evidence_stack:
            target=self.artifact(v,path)
            self.evidence_refs.append(dict(self.evidence_stack[-1],ordinary_ref=v,reference_path=path,reference_book=target['book_id'],reference_scope=target['scope_id']))
        return super().scan(v,parent,book,scope,found,path,active,resource_root)

    def validate(self):
        Package.entry_calls+=1
        base.shape(self.bundle,'exchange-v3.schema.json')
        for i,record in enumerate(self.bundle['evidence']):
            key=record['evidence_id'];need(key not in self.evidence_index,'EVIDENCE_ID_DUPLICATE','evidence/'+str(i)+'/'+key)
            self.evidence_index[key]=record
        return super().validate()

    def consumer_failures(self):
        result=[]
        for found,declared,book,scope,path in self.consumers:
            missing=set(found)-set(declared)
            wrong_scope=[r for r in found.values()if self.artifact(r,path)['scope_id']!=scope]
            wrong_book=[r for r in found.values()if self.artifact(r,path)['book_id']!=book]
            if missing or wrong_scope or wrong_book:
                result.append({'consumer':path,'book_id':book,'scope_id':scope,'missing_declarations':[found[k]for k in sorted(missing)],'wrong_scope':wrong_scope,'wrong_book':wrong_book})
        return result

# All R2 helper constructors/main()/mutate_case() now dispatch to this same entry.
base.Package=Package

def loaded_sources():
    return [{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p.read_bytes())}for p in(HOME/'closure.py',R2/'check.py',R2/'schema_check.py',R2/'oracle_verifier.py')]
