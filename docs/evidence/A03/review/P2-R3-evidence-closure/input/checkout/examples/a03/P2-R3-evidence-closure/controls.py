"""Only EvidenceRecord closure controls plus ONE affected R2 static matrix."""
import collections
import copy
import json
from pathlib import Path
import closure as c

ROOT=c.ROOT;OUT=c.OUT;EX=c.HOME;RUN=c.RUN_ID;RESULTS=[]
CASE_ROOT=EX/'cases'/RUN
def load(p):return json.loads(p.read_bytes())
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,ensure_ascii=False,indent=2).encode('utf8')+b'\n'
    if path.exists():assert path.read_bytes()==raw
    else:
        with path.open('xb')as f:f.write(raw)
def reseal(a):a['content_hash']=c.h({k:v for k,v in a.items()if k!='content_hash'});return a
def physical_case(name,bundle,overrides):
    directory=CASE_ROOT/name;write(directory/'bundle.json',bundle);resources=[]
    for i,(logical,raw)in enumerate(sorted(overrides.items())):
        p=directory/'resources'/('%02d.json'%i);p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():assert p.read_bytes()==raw
        else:p.write_bytes(raw)
        resources.append({'logical':logical,'file':p.relative_to(ROOT).as_posix(),'sha256':c.sha(raw)})
    info={'bundle':(directory/'bundle.json').relative_to(ROOT).as_posix(),'bundle_sha256':c.sha((directory/'bundle.json').read_bytes()),'resources':resources,'baseline':'526d264284f36f856c306db88c1d7e71c04152e1','data_root':c.base.DATA.relative_to(ROOT).as_posix()}
    write(directory/'case.json',info);return info
def run_case(name,bundle,overrides,expected=None,metadata=None):
    case=physical_case(name,bundle,overrides);pkg=c.Package(bundle,overrides)
    try:pkg.validate();actual='STATIC_ACCEPTED';error=None
    except c.Rejected as e:actual=e.code;error={'code':e.code,'path':e.path}
    assert actual==(expected or'STATIC_ACCEPTED'),(name,actual,error)
    result={'id':name,'actual':actual,'expected':expected or'STATIC_ACCEPTED','error':error,'case':case,'entry':'closure.Package.validate','metadata':metadata}
    RESULTS.append(result);return pkg,result
def virtual(overrides,path,value):
    raw=c.canon(value)+b'\n';overrides[path]=raw;return {'path':path,'sha256':c.sha(raw),'media_type':'application/json','origin':'SYNTHETIC'}

def primary():
    directory=OUT/'inputs/counterexample';raw=(directory/'bundle.json').read_bytes()
    assert c.sha(raw)=='b816535f29e8da7e5c85739c6e1b3e6937190c039b7228b518617025125ac653'
    bundle=json.loads(raw);spec=load(directory/'result.json');overrides={}
    for v in spec['resource_overrides']:
        resource=(directory/Path(v['file']).name).read_bytes();assert c.sha(resource)==v['sha256'];overrides[v['logical']]=resource
    assert all(c.h({k:v for k,v in a.items()if k!='content_hash'})==a['content_hash']for a in bundle['artifacts'])
    pkg=c.Package(bundle,overrides)
    try:pkg.validate();raise AssertionError('original counterexample accepted')
    except c.Rejected as e:
        assert e.code in('UNDECLARED_REFERENCE','ORDINARY_SCOPE'),str(e)
        error={'code':e.code,'path':e.path}
    receipt=next(a for a in bundle['artifacts']if a['kind']=='ExecutionReceipt'and a['schema_version']==c.base.VERSION)
    required=receipt['artifact_id']+'/results/0/before_evidence_refs'
    traces=[v for v in pkg.evidence_refs if v['consumer']==receipt['artifact_id'] and v['formal_path']==required and v['ordinary_ref']==spec['referenced_artifact']]
    assert traces,'new 1.3 receipt must actually consume the original EvidenceRecord path'
    failures=pkg.consumer_failures();assert any(v['consumer']==receipt['artifact_id']for v in failures)
    result={'id':'R2-SCOPE-EVIDENCE-ID-01','actual':'EXPECTED_STATIC_REJECTION','error':error,'bundle_raw_sha256':c.sha(raw),
            'all_artifact_hashes_correct':True,'original_version_and_resources_unchanged':True,'consumer_failures':failures,
            'new_receipt_before_evidence_path':required,'new_receipt_trace':traces,'evidence_uses':pkg.evidence_uses,
            'native_qualification':False,'entry':'closure.Package.validate'}
    write(OUT/'controls'/RUN/'original-counterexample.json',result)
    RESULTS.append({'id':result['id'],'actual':'EXPECTED_STATIC_REJECTION','code':error['code'],'new_1_3_receipt_confirmed':True,'consumers_with_closure_faults':len(failures)})

def ordinary_controls():
    target=load(c.base.DATA/'converted-initial.json');source=copy.deepcopy(next(a for a in target['artifacts']if a['kind']=='SourceBundle'))
    leaf=copy.deepcopy(source);leaf['artifact_id']='r3-neutral-leaf'
    for mapping in leaf['payload']['external_page_mappings']:mapping['evidence_refs']=['proof-neutral']
    leaf['input_refs']=[];reseal(leaf)
    consumer=copy.deepcopy(source);consumer['artifact_id']='r3-json-consumer'
    for mapping in consumer['payload']['external_page_mappings']:mapping['evidence_refs']=['proof-json']
    consumer['input_refs']=[c.ref(leaf)];reseal(consumer)
    overrides={};inner=virtual(overrides,'r3-static/legal-inner.json',{'ordinary_source_ref':c.ref(leaf)})
    outer=virtual(overrides,'r3-static/legal-outer.json',{'nested_resource':inner})
    neutral=copy.deepcopy(load(c.base.DATA/'scope-session.json')['evidence'][0]);neutral['evidence_id']='proof-neutral'
    record=dict(neutral,evidence_id='proof-json',resource=outer)
    bundle={'format_version':'a03-exchange-3-proposal','evidence':[record,neutral],'policies':target['policies'],'artifacts':[consumer,leaf]}
    run_case('legal-json-evidence-declared-same-scope',bundle,overrides)
    missing=copy.deepcopy(bundle);missing['artifacts'][0]['input_refs']=[];reseal(missing['artifacts'][0])
    run_case('json-evidence-missing-consumer-declaration',missing,overrides,'UNDECLARED_REFERENCE')
    shared=copy.deepcopy(bundle);other=copy.deepcopy(consumer);other.update(artifact_id='r3-shared-resource-other-scope',scope_id='other-scope');reseal(other);shared['artifacts'].append(other)
    pkg,_=run_case('shared-resource-each-consumer-context',shared,overrides,'ORDINARY_SCOPE')
    seen={v['consumer']for v in pkg.evidence_refs if v['evidence_id']=='proof-json'}
    assert consumer['artifact_id']in seen and other['artifact_id']in seen,seen
    absent=copy.deepcopy(bundle);absent['evidence']=[neutral]
    run_case('formal-evidence-id-missing',absent,overrides,'EVIDENCE_ID_MISSING')
    duplicate=copy.deepcopy(bundle);duplicate['evidence'].append(copy.deepcopy(record))
    run_case('formal-evidence-id-duplicate',duplicate,overrides,'EVIDENCE_ID_DUPLICATE')
    cycle=copy.deepcopy(bundle);cycle['artifacts'][1]['payload']['external_page_mappings'][0]['evidence_refs']=['proof-json']
    run_case('formal-evidence-mixed-cycle',cycle,overrides,'MIXED_CYCLE',{'intentional_stale_leaf_hash':'structural mixed DAG is checked before final Artifact hash; not a replacement for the original hash-correct counterexample'})
    lookalike=copy.deepcopy(overrides)
    extra=virtual(lookalike,'r3-static/opaque-lookalike.json',{'note':{'evidence_refs':['not-a-formal-evidence-id'],'before_evidence_refs':['also-not-an-id']},'ordinary_source_ref':c.ref(leaf)})
    opaque=copy.deepcopy(bundle);opaque['evidence'][0]['resource']=extra
    run_case('opaque-json-same-name-strings-are-not-ids',opaque,lookalike)

def frame_controls():
    original=load(c.base.DATA/'scope-session.json')
    def change(bundle,prefix,basis,fact,v):
        source=copy.deepcopy(next(a for a in bundle['artifacts']if a['kind']=='SourceBundle'and a['scope_id']=='original-b'))
        embedded=copy.deepcopy(source);embedded['artifact_id']='r3-embedded-source-b'
        for mapping in embedded['payload']['external_page_mappings']:mapping['evidence_refs']=['proof-frame']
        reseal(embedded)
        evidence=v('r3-static/frame-proof.json',{'ordinary_source_ref':c.ref(source)})
        record=copy.deepcopy(bundle['evidence'][0]);record.update(evidence_id='proof-frame',resource=evidence);bundle['evidence'].append(record)
        frame=next(f for f in prefix['frames']if f['event']['event']=='PLAN_ACCEPTED'and f['consumer_scope_id']=='original-b')
        frame['event']['payload']['evidence']=v('r3-static/frame-embedded-artifact.json',{'artifact_value':embedded})
    mutated,basis,_=c.base.mutate_case(original,change,False,True)
    bundle=mutated.bundle;overrides=dict(mutated.overrides);receipt=bundle['artifacts'][-1]
    fr=receipt['payload']['action_fact_refs'][0];fact=mutated.read(fr);br=fact['unattempted_basis'];basis=mutated.read(br);pr=basis['complete_uncalled_prefix'];prefix=mutated.read(pr)
    previous=c.base.ZERO
    for number,frame in enumerate(prefix['frames'],1):
        e=frame['event']
        if e['event']=='READONLY_ABSENCE_STARTED':
            basis['initial_event_head']={'sequence':number-1,'hash':previous};e['payload']['initial_event_head']=basis['initial_event_head']
        e.update(sequence=number,previous_hash=previous);e['event_hash']=c.h({k:v for k,v in e.items()if k!='event_hash'});previous=e['event_hash']
        if e['event']=='PLAN_ACCEPTED'and e['plan_ref']==prefix['subject_plan_ref']:prefix['accepted_anchor']={'sequence':number,'hash':previous}
    prefix['expected_book_head']={'sequence':len(prefix['frames']),'hash':previous};basis['expected_event_head']=prefix['expected_book_head']
    basis['complete_uncalled_prefix']=virtual(overrides,pr['path'],prefix);fact['unattempted_basis']=virtual(overrides,br['path'],basis)
    fact.update(predecessor_hash=previous,journal_sequence=len(prefix['frames'])+1);receipt['payload']['action_fact_refs']=[virtual(overrides,fr['path'],fact)];reseal(receipt)
    pkg,_=run_case('typed-frame-formal-evidence-uses-frame-scope',bundle,overrides)
    c.base.session(pkg,basis)
    assert any(v['kind']=='TYPED_FRAME'and v['scope_id']=='original-b'and v['evidence_id']=='proof-frame'for v in pkg.evidence_refs)
    bad=copy.deepcopy(bundle);changed=copy.deepcopy(prefix)
    frame=next(f for f in changed['frames']if f['event']['event']=='PLAN_ACCEPTED'and f['consumer_scope_id']=='original-b')
    source=next(a for a in bad['artifacts']if a['kind']=='SourceBundle'and a['scope_id']=='original-b')
    frame['input_refs']=[r for r in frame['input_refs']if r!=c.ref(source)]
    altered=dict(overrides);bs=copy.deepcopy(basis);ff=copy.deepcopy(fact)
    bs['complete_uncalled_prefix']=virtual(altered,pr['path'],changed);ff['unattempted_basis']=virtual(altered,br['path'],bs)
    bad['artifacts'][-1]['payload']['action_fact_refs']=[virtual(altered,fr['path'],ff)];reseal(bad['artifacts'][-1])
    run_case('typed-frame-evidence-missing-own-declaration',bad,altered,'UNDECLARED_REFERENCE')

def regression():
    before=c.Package.entry_calls
    inputs=c.base.EVID/'inputs';inputs.mkdir(parents=True,exist_ok=True)
    for name in('readonly-session-does-not-match-gate-binding.json','initial-head-not-in-canonical-prefix.json','amended-source-kind-coverage.json'):
        raw=c.pinned(ROOT/'docs/evidence/A03/execution/P2-R2-proposal/inputs'/name);p=inputs/name
        with p.open('xb')as f:f.write(raw)
    c.base.RESULTS.clear();c.base.main()
    result=load(c.base.EVID/'static-results.json');assert len(result['records'])==36
    counts=dict(collections.Counter(row['result']for row in result['records']))
    assert counts=={'STATIC_ACCEPTED':7,'EXPECTED_STATIC_REJECTION':23,'STATIC_MATCH':1,'EXPECTED_STATIC_MISMATCH':5},counts
    assert c.base.Package is c.Package and c.Package.entry_calls>before
    return {'records':36,'classification':counts,'corrected_whole_entry_calls':c.Package.entry_calls-before,
            'session_and_conversion':'LIMITED_STATIC_RESULTS_PRESERVED','oracle':'one existing group only; no additional comparison run or adoption'}

if __name__=='__main__':
    primary();ordinary_controls();frame_controls();matrix=regression()
    write(OUT/'controls'/RUN/'formal-field-registry.json',{'authority':'exact R2 pinned schema fields, not arbitrary same-name strings','fields':list(c.FIELDS.values())})
    result={'status':'REVIEW_STATIC_REPAIR_ONLY','entry':'closure.Package.validate','loaded_sources':c.loaded_sources(),
      'controls':RESULTS,'r2_static_regression_once':matrix,'total_corrected_package_entry_calls':c.Package.entry_calls,
      'profile_api_schemas':'UNCHANGED_FIXED_R2','product_runs':0,'database_queries':0,'native_sessions':0,'network_or_model_calls':0,
      'blocked':['R17 version bridge','registration-derived scope positive fixture','oracle/public/native adoption','I01'],
      'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
    write(OUT/'controls'/RUN/'results.json',result)
    print(json.dumps({'status':result['status'],'closure_controls':len(RESULTS),'r2_records_once':36,'r2_classification':matrix['classification'],'entry_calls':c.Package.entry_calls,'product_runs':0}))
