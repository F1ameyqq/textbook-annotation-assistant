"""Independent content/provenance readback; does not import or call the exporter."""
from pathlib import Path
import argparse,hashlib,io,json
from datetime import datetime
from PIL import Image

REVIEW_SHA='4dd4425140620ef37a289df29206c2f04734c082badd2c73b238851d8031cada'
BASIS_SHA='ad8795629c41b67908ba21d0d8039f7a3b5bdbd1eb0155cf75dc375922744a46'
ASSETS={'viewer-13':('997b37d35fca57f73ab71e53f6721be145d10c436deab5fab38bf1ae0d31dc1e',(1219,1691)),
        'viewer-15':('7c1a4afec69a94371fa31b6111969ca3d6ec39d7d7c6b1c73764f90316a610dd',(1219,1703)),
        'viewer-173':('a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be',(1148,1621))}
sha=lambda b:hashlib.sha256(b).hexdigest()
canonical=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

def need(value,code):
    if not value:raise ValueError(code)

def read(path):
    def pairs(items):
        out={}
        for k,v in items:need(k not in out,'DUPLICATE_JSON_KEY');out[k]=v
        return out
    return json.loads(Path(path).read_bytes(),object_pairs_hook=pairs)

def text_of(runs):
    parts=[]
    for run in runs:
        if run['format']=='blank':need(run['value'] is None,'QUESTION_BLANK_FILLED');parts.append('____')
        elif run['format']=='latex':parts.append('\\('+run['text']+'\\)')
        else:need(run['format']=='plain','RUN_KIND');parts.append(run['text'])
    return ''.join(parts)

def verify(folder,bundle=None):
    folder=Path(folder);review=read(folder/'current-review.json');basis=read(folder/'basis.json');d=read(folder/'delivery.json')
    need(sha((folder/'current-review.json').read_bytes())==REVIEW_SHA,'FIXED_SOURCE_REVIEW')
    need(sha((folder/'basis.json').read_bytes())==BASIS_SHA,'FIXED_NATIVE_BASIS')
    need(d['current_review_sha256']==REVIEW_SHA and d['basis_sha256']==sha((folder/'basis.json').read_bytes()),'CURRENT_INPUT_BINDING')
    generation=read(folder/'generation.json')
    need(set(generation)=={'created_at','config_version','b_base_commit','a_consumer_commit','basis_sha256','current_review_sha256'} and
         d['generation_sha256']==sha((folder/'generation.json').read_bytes()) and
         generation['basis_sha256']==BASIS_SHA and generation['current_review_sha256']==REVIEW_SHA and
         generation['config_version']=='q16-reading-20261021.2' and
         generation['a_consumer_commit']==d['a_consumer_commit']=='edf125961be9cdc1642652c038d99872b1c8cdc7' and
         generation['b_base_commit']==d['b_base_commit']=='d48b066ad2620d7f1a2e902b2b28e3139390a721' and
         datetime.fromisoformat(generation['created_at'].replace('Z','+00:00')).tzinfo is not None,'GENERATION_CONTEXT_BINDING')
    q=review['q16'];m=review['reading']
    subjects=[dict(task_map=q['task_map'],question_id=q['question_id'],answer_id=q['answer_id'])]+q['formula_slots']+[
        q['answer_lines'],dict(question=q['question_blocks'],answer=q['answer_lines']),m['material_blocks']]+m['tasks']
    need(d['decision']=='HOLD' and not d['human_verified'] and not d['business_acceptance'] and not d['platform_actions'] and
         not d['source_windows_are_platform_frames'] and not d['native_graphs_or_ledger_modified'] and d['chapter_denominator'] is None,'NO_SCOPE_PROMOTION')
    need(d['model_checks']==review['checks'] and len(d['model_checks'])==d['independent_human_pending']==18 and all(c['human_disposition'] is None and c['independent_human_reviewer'] is None for c in d['model_checks']),'NO_FAKE_ACCEPTANCE')
    pending=read(folder/'pending-review.json')
    need(d['pending_review_sha256']==sha((folder/'pending-review.json').read_bytes()) and pending['current_review_sha256']==REVIEW_SHA and
         pending['c01_graph_ref']==d['c01_graph_ref'] and pending['pending_independent_human_count']==18 and pending['approved_count']==0 and
         len(pending['items'])==18 and [x['issue_id'] for x in pending['items']]==[x['issue_id'] for x in review['checks']] and
         [x['subject'] for x in pending['items']]==subjects and
         all(x['human_reviewer'] is None and x['human_disposition'] is None and x['human_evidence_sha256'] is None and
             x['subject_sha256']==sha(canonical(x['subject'])) for x in pending['items']),'INDEPENDENT_REVIEW_BINDING')
    need(len(basis['original_unassigned'])==19 and all(r['status']=='UNASSIGNED' for r in basis['original_unassigned']),'HISTORICAL_LEDGER')
    bundle=read(folder/'bundle.json') if bundle is None else bundle
    need(bundle['format_version']=='c01-exchange-1','C01_VERSION')
    artifacts={a['kind']:a for a in bundle['artifacts']}
    need(len(bundle['artifacts'])==len(artifacts)==4 and set(artifacts)=={'SourceBundle','EvidenceBundle','QuestionGraph','CheckReport'} and
         len(bundle['policies'])==1 and len(bundle['evidence'])==2 and
         {x['evidence_id'] for x in bundle['evidence']}=={'ev-current-review','ev-basis'},'READONLY_ARTIFACTS')
    seed=sha(canonical(generation))[:24]
    names=dict(SourceBundle='source',EvidenceBundle='evidence',QuestionGraph='graph',CheckReport='precheck')
    need(all(a['artifact_id']=='b-q16-reading-'+names[a['kind']]+'-'+seed and a['run_id']=='b-q16-reading-'+seed and
             a['revision']==1 and a['created_at']==generation['created_at'] and
             a['producer']['implementation_version']=='2' and a['producer']['config_version']==generation['config_version']
             for a in bundle['artifacts']),'IMMUTABLE_GENERATION_IDENTITIES')
    graph=artifacts['QuestionGraph'];ev=artifacts['EvidenceBundle']['payload'];source=artifacts['SourceBundle']['payload'];check=artifacts['CheckReport']['payload']
    need(d['c01_graph_ref']=={k:graph[k] for k in ('artifact_id','revision','kind','content_hash')},'SIDECAR_GRAPH_REF')
    for a in bundle['artifacts']+bundle['policies']:
        need(a['content_hash']==sha(canonical({k:v for k,v in a.items() if k!='content_hash'})),'ARTIFACT_DIGEST')
    need(all(a['producer']['evidence_mode']=='OBSERVED' for a in bundle['artifacts']),'ORIGINAL_MODE')
    need(len(source['assets'])==3 and {a['asset_id'] for a in source['assets']}==set(ASSETS),'SOURCE_INVENTORY')
    images={}
    for asset in source['assets']:
        raw=(folder/asset['path']).read_bytes();pin,size=ASSETS[asset['asset_id']];im=Image.open(io.BytesIO(raw)).convert('RGB')
        need(sha(raw)==asset['sha256']==pin and im.size==size==(asset['width'],asset['height']) and asset['provenance']=='ORIGINAL','SOURCE_BYTES_AND_SIZE')
        images[asset['asset_id']]=im
    expected=[]
    for b in q['question_blocks']:expected.append((b['block_id'],dict(b,asset_id='viewer-15'),'stem',q['question_id'],True))
    for b in q['answer_lines']:expected.append((b['block_id'],b,'answer',q['question_id'],True))
    for b in m['material_blocks']:expected.append((b['block_id'],b,'shared_material',m['material_id'],True))
    for task in m['tasks']:
        for b in task['question_blocks']:expected.append((b['block_id'],b,'stem',task['task_id'],True))
        for b in task['answer_regions']:expected.append((b['segment_id'],b,'answer',task['task_id'],True))
    for s in q['formula_slots']:
        expected.append(('q16-'+s['slot'],dict(asset_id='viewer-173',bbox=s['source_bbox'],runs=[dict(format='latex',text=s['expected_latex'])],content_type='formula'),'answer',q['question_id'],False))
    regions={r['region_id']:r for r in ev['regions']};fragments={f['fragment_id']:f for f in graph['payload']['fragments']}
    need(len(regions)==len(d['bindings'])==len(d['source_proofs'])==len(expected)==37,'NO_OMITTED_OR_DUPLICATE_REGIONS')
    need(len(fragments)==26,'NO_DIAGNOSTIC_FORMULA_DUPLICATION')
    fragment_order=0
    for (identity,want,role,owner,has_fragment),binding,proof in zip(expected,d['bindings'],d['source_proofs']):
        rid='region-'+identity;fid='fragment-'+identity;got=regions[rid];box=list(map(int,want.get('bbox',want.get('bbox_xyxy',[]))))
        is_image=want.get('content_type')=='image' or identity in ('reading-figure1','reading-figure2')
        content_type='image' if is_image else 'formula' if want.get('content_type')=='formula' else 'text'
        need(got['box']['bbox']==box and got['box']['image']['asset_id']==want['asset_id'] and got['content_type']==content_type,'REGION_IDENTITY_GEOMETRY')
        need(got['text']==(None if is_image else text_of(want['runs'])),'SOURCE_TRANSCRIPTION_READBACK')
        need(binding==dict(block_id=identity,owner_id=owner,region_id=rid,fragment_id=fid if has_fragment else None,runs=want.get('runs',[]),role=role),'RUN_AND_OWNER_BINDING')
        need(got['source']=='HISTORICAL' and got['certainty']=='UNCERTAIN','NO_HUMAN_SOURCE_CLAIM')
        crop=images[want['asset_id']].crop(box);raw=(folder/proof['path']).read_bytes();decoded=Image.open(io.BytesIO(raw)).convert('RGB')
        need(proof['region_id']==rid and sha(raw)==proof['sha256'] and sha(crop.tobytes())==proof['rgb_sha256'] and crop.size==decoded.size and crop.tobytes()==decoded.tobytes(),'CROP_PIXEL_READBACK')
        if has_fragment:
            need(fragments[fid]['region_ids']==[rid] and fragments[fid]['role']==role and fragments[fid]['content_type']==content_type and
                 fragments[fid]['reading_order']==fragment_order,'GRAPH_FRAGMENT_READBACK')
            fragment_order+=1
        else:need(fid not in fragments,'DIAGNOSTIC_NOT_ANSWER_DUPLICATE')
    questions=graph['payload']['questions'];relations=graph['payload']['answer_relations']
    need([x['question_id'] for x in questions]==[q['question_id']]+[t['task_id'] for t in m['tasks']],'FOUR_IDENTITIES')
    need(len(relations)==4 and all(x['status']=='UNRESOLVED' and not x['selected_fragment_ids'] for x in relations),'NO_SELECTED_RELATIONS')
    for question,relation in zip(questions,relations):
        identity=question['question_id'];owned=[b for b in d['bindings'] if b['owner_id']==identity and b['fragment_id'] is not None]
        need(question['fragment_ids']==[b['fragment_id'] for b in owned if b['role']=='stem'],'QUESTION_ORDER')
        need(relation['question_id']==identity and relation['candidate_fragment_ids']==[b['fragment_id'] for b in owned if b['role']=='answer'],'ANSWER_TASK_PAIRING')
        need(not question['cross_page'] and question['external_refs']['platform_question_id'] is None,'NO_PAGE_OR_PLATFORM_INVENTION')
    shared=[b['fragment_id'] for b in d['bindings'] if b['role']=='shared_material']
    need(not questions[0]['shared_fragment_ids'] and all(x['shared_fragment_ids']==shared and x['external_refs']['printed_number'] is None for x in questions[1:]),'SHARED_MATERIAL_WITHOUT_FAKE_NUMBER')
    need(d['q16_task_map']==basis['q16']['task_map']==q['task_map'] and d['q16_formula_slots']==basis['formulas']==q['formula_slots'],'Q16_SOURCE_SPANS')
    need([s['expected_latex'] for s in q['formula_slots']]==[r'\frac{a^{2}+1}{2}',r'\frac{a^{2}-1}{2}',r'\frac{a^{4}+2a^{2}+1}{4}',r'\frac{a^{2}+1}{2}',r'\frac{a^{4}+2a^{2}+1}{4}',r'\frac{a^{2}-1}{2}',r'\frac{a^{2}+1}{2}',r'\frac{a^{2}-1}{2}',r'\frac{a^{2}+1}{2}',r'\frac{a^{2}-1}{2}',r'\frac{a^{2}+1}{2}'],'ELEVEN_FORMULAS')
    blanks=[r for b in d['bindings'] for r in b['runs'] if r['format']=='blank']
    need(len(blanks)==6 and len({r['blank_id'] for r in blanks})==6 and all(r['value'] is None for r in blanks),'SIX_UNFILLED_BLANKS')
    need([x['blank_responses'] for x in d['reading_task_answers']]==[t['blank_responses'] for t in m['tasks']],'BLANK_RESPONSE_ORDER')
    need(check['decision']=='HOLD' and check['stage']=='PRE_APPLY' and check['coverage']['pages_checked']==[] and len(check['checks'])==5 and
         {x['code'] for x in check['issues']}=={'ANSWER_AMBIGUOUS','POLICY_UNRESOLVED','SOURCE_MISSING'},'HOLD_AND_NO_COVERAGE_PROMOTION')
    need({x['check_id']:x['outcome'] for x in check['checks']}==dict(source_integrity='PASS',structure='PASS',answer_matching='UNAVAILABLE',coverage='UNAVAILABLE',policy='UNAVAILABLE'),'NO_DIAGNOSTIC_PROMOTION')
    need(all(p['confirmation_status']=='UNRESOLVED' and p['applicability']=='PROPOSAL_ONLY' for p in bundle['policies']),'NO_POLICY_PROMOTION')
    return dict(status='SOURCE_BOUND_CONTENT_READBACK_OK',questions=4,shared_materials=1,regions=len(regions),fragments=len(fragments),
                q16_formula_slots=11,unfilled_question_blanks=6,model_source_checks=18,independent_human_pending=18,decision='HOLD')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('delivery',type=Path);args=p.parse_args()
    print(json.dumps(verify(args.delivery),ensure_ascii=False))

if __name__=='__main__':main()
