"""Independent data audit, stdlib only; no checker imports or Package calls."""
from files import DATA,EX,OLD_CASE,ROOT,h,isref,isres,load,ref,sha

def differences(a,b,path=''):
    if type(a)is not type(b):return[{'path':path,'before':a,'after':b}]
    if isinstance(a,dict):
        assert set(a)==set(b),('keys changed',path)
        return[d for k in a for d in differences(a[k],b[k],path+'/'+k)]
    if isinstance(a,list):
        assert len(a)==len(b),('length changed',path)
        return[d for i,(x,y)in enumerate(zip(a,b))for d in differences(x,y,path+'/'+str(i))]
    return[]if a==b else[{'path':path,'before':a,'after':b}]

class DataAudit:
    def __init__(self,case):
        self.case=case;self.bundle=load(ROOT/case['bundle']);self.over={r['logical']:(ROOT/r['file']).read_bytes()for r in case['resources']}
        self.artifacts={h(ref(a)):a for a in self.bundle['artifacts']};assert len(self.artifacts)==len(self.bundle['artifacts'])
        assert len({(a['artifact_id'],a['revision'])for a in self.bundle['artifacts']})==len(self.bundle['artifacts'])
        self.evidence={e['evidence_id']:e for e in self.bundle['evidence']};assert len(self.evidence)==len(self.bundle['evidence'])
        self.cache={};self.resource_rows=[];self.prefix_rows=[];self.prefix_ids=set();self.consumers=[];self.ref_count=0;self.formal_uses=[];self.slots={}
        self.docs={name:load(DATA/'schemas'/filename)for name,filename in [('exchange','exchange-v3.schema.json'),('prefix','prefix-v2.schema.json'),('fact','fact-v3.schema.json')]}
        self.id_pattern=self.docs['exchange']['$defs']['EvidenceRecord']['properties']['evidence_id']['pattern']

    def mark_slots(self,value,node,docname,pointer,seen=None):
        # Follow exact schema properties/$refs, without executing its validator.
        # All union branches are inspected for formal string-array authority;
        # opaque JSON and Resource-valued lookalikes never gain that authority.
        seen=set()if seen is None else seen;token=(id(value),id(node))
        if token in seen:return
        seen.add(token);doc=self.docs[docname]
        if '$ref'in node:
            p=node['$ref'];assert p.startswith('#/');target=doc
            for part in p[2:].split('/'):target=target[part.replace('~1','/').replace('~0','~')]
            self.mark_slots(value,target,docname,p[1:],seen)
        if isinstance(value,list)and node.get('type')=='array'and node.get('items',{}).get('type')=='string'and node['items'].get('pattern')==self.id_pattern and pointer.rsplit('/',1)[-1]in{'evidence_refs','before_evidence_refs','after_evidence_refs','submission_evidence_refs'}:
            self.slots[id(value)]=(value,docname+'#'+pointer)
        for union in('oneOf','anyOf'):
            for i,child in enumerate(node.get(union,[])):self.mark_slots(value,child,docname,pointer+'/'+union+'/'+str(i),seen)
        if isinstance(value,dict):
            for k,child in node.get('properties',{}).items():
                if k in value:self.mark_slots(value[k],child,docname,pointer+'/properties/'+k,seen)
        if isinstance(value,list)and isinstance(node.get('items'),dict):
            for member in value:self.mark_slots(member,node['items'],docname,pointer+'/items',seen)

    def typed(self,v):
        if not isinstance(v,dict):return
        if {'schema_version','artifact_id','revision','kind','payload','input_refs','content_hash'}<=set(v):
            name=('Amended'if v['schema_version']=='1.3.0-a03-static-proposal'else'')+v['kind'];assert name in self.docs['exchange']['$defs']
            self.mark_slots(v,self.docs['exchange']['$defs'][name],'exchange','/$defs/'+name)
        if v.get('format_version')=='a03-action-fact-3':self.mark_slots(v,self.docs['fact'],'fact','')

    def artifact(self,r,path):
        assert isref(r)and h(r)in self.artifacts and ref(self.artifacts[h(r)])==r,('exact ref',path,r)
        self.ref_count+=1;return self.artifacts[h(r)]

    def resource(self,r):
        key=(r['path'],r['sha256'])
        if key in self.cache:return self.cache[key]
        if r['path']in self.over:raw=self.over[r['path']];physical=next(x['file']for x in self.case['resources']if x['logical']==r['path'])
        else:
            p=(DATA/r['path']).resolve();assert p.is_relative_to(DATA.resolve());raw=p.read_bytes();physical=p.relative_to(ROOT).as_posix()
        assert sha(raw)==r['sha256'],('Resource SHA',r['path'])
        value=__import__('json').loads(raw)if r['media_type']=='application/json'else None
        self.cache[key]=value;self.resource_rows.append({'logical':r['path'],'sha256':r['sha256'],'bytes':len(raw),'file':physical})
        return value

    def prefix(self,p,path):
        if id(p)in self.prefix_ids:return
        self.prefix_ids.add(id(p));previous=p['predecessor']['hash'];assert p['from_sequence']==1 and p['predecessor']=={'sequence':0,'hash':'0'*64}
        accepted=[];heads=[]
        for i,f in enumerate(p['frames'],1):
            e=f['event'];assert e['sequence']==i and e['previous_hash']==previous and h({k:v for k,v in e.items()if k!='event_hash'})==e['event_hash'],('event digest/chain',path,i)
            assert e['journal_id']==p['journal_id']and e['target_key']==p['target_key'],('event identity',path,i)
            if 'initial_event_head'in e['payload']:
                expected={'sequence':i-1,'hash':previous};assert e['payload']['initial_event_head']==expected,('initial_event_head',path,i,e['payload']['initial_event_head'],expected)
                heads.append({'event_sequence':i,'initial_event_head':expected})
            previous=e['event_hash']
            if e['event']=='PLAN_ACCEPTED'and e['plan_ref']==p['subject_plan_ref']:accepted.append({'sequence':i,'hash':previous})
        assert accepted==[p['accepted_anchor']],('accepted anchor',path)
        assert p['expected_book_head']=={'sequence':len(p['frames']),'hash':previous},('expected head',path)
        self.prefix_rows.append({'logical':path,'events':len(p['frames']),'all_event_hashes_and_predecessors':True,'initial_event_heads':heads,'accepted_anchor':p['accepted_anchor'],'expected_book_head':p['expected_book_head']})

    def consumer(self,v,book,scope,declared,path,kind):
        found={};self.scan(v,book,scope,found,path,set(),False)
        declared={h(r):r for r in declared};missing=set(found)-set(declared);wrong=[]
        for r in declared.values():
            target=self.artifact(r,path+'/input_refs')
            if target['book_id']!=book or target['scope_id']!=scope:wrong.append(r)
        assert not missing and not wrong,('consumer declarations/book/scope',path,[found[k]for k in missing],wrong)
        self.consumers.append({'path':path,'kind':kind,'book_id':book,'scope_id':scope,'found_refs':list(found.values()),'declared_refs':list(declared.values()),'missing':[],'wrong_book_or_scope':[]})

    def scan(self,v,book,scope,found,path,active,resource_root):
        self.typed(v)
        slot=self.slots.get(id(v))if isinstance(v,list)else None
        if slot is not None and slot[0]is v:
            for evidence_id in v:
                assert evidence_id in self.evidence,('formal ID',path,evidence_id);self.formal_uses.append({'path':path,'evidence_id':evidence_id,'authority':slot[1]})
                self.scan(self.evidence[evidence_id]['resource'],book,scope,found,path+'['+evidence_id+']',active,False)
            return
        if isref(v):self.artifact(v,path);found[h(v)]=v;return
        if isres(v):
            value=self.resource(v);key=(v['path'],v['sha256'])
            if value is not None and key not in active:self.scan(value,book,scope,found,v['path'],active|{key},True)
            return
        if isinstance(v,dict):
            if v.get('format_version')=='a03-runtime-event-prefix-2':
                assert resource_root,('prefix location',path);self.prefix(v,path)
                for k,x in v.items():
                    if k!='frames':self.scan(x,book,scope,found,path+'/'+k,active,False)
                for i,f in enumerate(v['frames']):
                    e=f['event'];expected_scope=None
                    if e['plan_ref']is not None:
                        plan=self.artifact(e['plan_ref'],path+'/frames/'+str(i));assert plan['kind']=='ApplyPlan';expected_scope=plan['scope_id']
                    elif e['event']=='TARGET_DRIFT_HOLD'and e['payload'].get('registration_id'):
                        expected_scope=self.artifact(e['payload']['source_ref'],path+'/registration')['scope_id']
                    assert f['consumer_scope_id']==expected_scope,('frame scope',path,i)
                    event_schema=self.docs['prefix']['properties']['frames']['items']['properties']['event'];self.mark_slots(e,event_schema,'prefix','/properties/frames/items/properties/event')
                    # This is intrinsic data consistency, not a native/current
                    # consumer admission. Global headers acquire no outer scope.
                    frame_book=book if book is not None else v['target_key']['book_id']
                    self.consumer(e,frame_book,expected_scope,f['input_refs'],path+'/frames/'+str(i),'FRAME_DATA_BINDING')
                return
            assert'frame_version'not in v,('frame outside prefix',path)
            for k,x in v.items():self.scan(x,book,scope,found,path+'/'+k,active,False)
        elif isinstance(v,list):
            for i,x in enumerate(v):self.scan(x,book,scope,found,path+'/'+str(i),active,False)

    def run(self):
        for a in self.bundle['artifacts']:
            assert h({k:v for k,v in a.items()if k!='content_hash'})==a['content_hash'],('Artifact hash',a['artifact_id'])
            self.typed(a);self.consumer(a['payload'],a['book_id'],a['scope_id'],a['input_refs'],a['artifact_id'],'ARTIFACT_DATA_BINDING')
        for e in self.bundle['evidence']:self.scan(e['resource'],None,None,{},'evidence/'+e['evidence_id'],set(),False)
        basis_heads=[]
        for value in list(self.cache.values()):
            if isinstance(value,dict)and{'complete_uncalled_prefix','initial_event_head','expected_event_head'}<=set(value):
                p=self.resource(value['complete_uncalled_prefix']);matching=[f['event']for f in p['frames']if f['event']['event']=='READONLY_ABSENCE_STARTED'and f['event']['payload']['binding']['readonly_session_id']==value['binding']['readonly_session_id']]
                assert len(matching)==1 and value['initial_event_head']==matching[0]['payload']['initial_event_head']and value['expected_event_head']==p['expected_book_head'],('basis heads',value['readonly_session_id'])
                basis_heads.append({'readonly_session_id':value['readonly_session_id'],'initial_event_head':value['initial_event_head'],'expected_event_head':value['expected_event_head']})
        return{'artifacts':len(self.bundle['artifacts']),'all_artifact_hashes':True,'resources':self.resource_rows,'prefixes':self.prefix_rows,'ordinary_ref_checks':self.ref_count,'formal_evidence_uses':self.formal_uses,'consumers':self.consumers,'basis_heads':basis_heads,'consumer_failures':[],'Package_calls':0,'checker_or_product_imports':0}

def audit():
    case=load(EX/'case.json');old=load(ROOT/OLD_CASE);oldbundle=load(ROOT/old['bundle']);candidate=load(ROOT/case['bundle'])
    assert sha((ROOT/case['bundle']).read_bytes())==case['bundle_sha256']
    for r in case['resources']:assert sha((ROOT/r['file']).read_bytes())==r['raw_sha256']and(ROOT/r['file']).stat().st_size==r['bytes']
    old_item=next(r for r in old['resources']if r['logical']=='r5-static/cycle-prefix.json');new_item=next(r for r in case['resources']if r['logical']==old_item['logical']);before=load(ROOT/old_item['file']);after=load(ROOT/new_item['file'])
    pchanges=differences(before,after);allowed={'/frames/7/event/payload/initial_event_head/hash','/expected_book_head/hash'}
    allowed|={'/frames/'+str(i)+'/event/event_hash'for i in range(7,len(before['frames']))}
    allowed|={'/frames/'+str(i)+'/event/previous_hash'for i in range(8,len(before['frames']))}
    assert{r['path']for r in pchanges}==allowed,('unexpected prefix semantic changes',pchanges)
    bchanges=differences(oldbundle,candidate);position=next(i for i,e in enumerate(oldbundle['evidence'])if e['resource']['path']==old_item['logical'])
    assert[r['path']for r in bchanges]==['/evidence/'+str(position)+'/resource/sha256']
    assert oldbundle['artifacts']==candidate['artifacts']and before['accepted_anchor']==after['accepted_anchor']
    assert before['frames'][:7]==after['frames'][:7]
    data=DataAudit(case).run()
    record=candidate['evidence'][position];prefix=after;return_item=next(r for r in case['resources']if r['logical']=='r5-static/cycle-return.json');returned=load(ROOT/return_item['file'])['ordinary_source_ref']
    source=next(a for a in candidate['artifacts']if ref(a)==returned);evidence_id=record['evidence_id']
    assert any(evidence_id in m['evidence_refs']for m in source['payload']['external_page_mappings'])
    frame_pos=next(i for i,f in enumerate(prefix['frames'])if f['event']['payload'].get('evidence',{}).get('path')==return_item['logical']);frame=prefix['frames'][frame_pos]
    assert returned in frame['input_refs']and frame['consumer_scope_id']==source['scope_id']and prefix['target_key']['book_id']==source['book_id']
    assert source['input_refs']==[prefix['subject_plan_ref']]
    assert returned==load(ROOT/next(r for r in old['resources']if r['logical']==return_item['logical'])['file'])['ordinary_source_ref']
    a='A:'+h(returned);e='E:'+evidence_id;r='R:'+new_item['logical']+':'+new_item['raw_sha256'];f=r+'/F:'+str(frame_pos);back='R:'+return_item['logical']+':'+return_item['raw_sha256'];nodes=[a,e,r,f,back,a]
    return{'status':'DATA_CONSISTENCY_PASSED_BEFORE_PACKAGE','candidate_count':1,'source_case':OLD_CASE,'bundle_sha256':case['bundle_sha256'],'prefix_sha256':new_item['raw_sha256'],'prefix_semantic_changes':pchanges,'bundle_semantic_changes':bchanges,'changed_artifacts':[],'changed_ArtifactRefs':[],'unchanged_accepted_anchor':after['accepted_anchor'],'all_initial_event_heads_match_predecessors':True,'mixed_cycle_preserved':True,'ring_edges':[{'from':x,'to':y}for x,y in zip(nodes,nodes[1:])],'data':data,'Package_calls':0,'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
