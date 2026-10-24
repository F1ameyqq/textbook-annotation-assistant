"""Independent portable source/content readback; never imports the producer."""
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import re
import argparse
from PIL import Image

sha=lambda raw:hashlib.sha256(raw).hexdigest()
canonical=lambda value:json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def need(value,code):
    if not value:raise ValueError(code)


def read(path):
    def pairs(rows):
        out={}
        for key,value in rows:
            need(key not in out,'DUPLICATE_JSON_KEY');out[key]=value
        return out
    def finite(text):
        value=float(text);need(math.isfinite(value),'NONFINITE_JSON');return value
    def constant(text):raise ValueError('NONFINITE_JSON')
    return json.loads(Path(path).read_bytes(),object_pairs_hook=pairs,parse_float=finite,parse_constant=constant)


def portable(value):
    if isinstance(value,dict):
        need(not ({'user_id','profile','cookies','authorization','access_token','native_identity'} & set(value)),'PRIVATE_RUNTIME_DATA')
        for child in value.values():portable(child)
    elif isinstance(value,list):
        for child in value:portable(child)
    elif isinstance(value,str):
        need(not re.search(r'(?i)(?:[A-Z]:[\\/]|(?:https?|file)://|\\\\)',value),'NONPORTABLE_OR_REMOTE_REFERENCE')


def resource(root,path):
    need(type(path) is str and path and not re.search(r'[:\\\x00]',path) and not path.startswith('/')
         and all(p not in ('','.','..') for p in path.split('/')),'RELATIVE_RESOURCE_REQUIRED')
    return root/path


def verify(folder):
    root=Path(folder)
    bundle,basis,review,delivery,generation=[read(root/name) for name in ('bundle.json','basis.json','current-review.json','delivery.json','generation.json')]
    for value in (bundle,basis,review,delivery,generation):portable(value)
    need(bundle['format_version']=='c01-exchange-1','EXISTING_C01_REQUIRED')
    kinds={a['kind']:a for a in bundle['artifacts']}
    need(len(bundle['artifacts'])==len(kinds)==4 and set(kinds)=={'SourceBundle','EvidenceBundle','QuestionGraph','CheckReport'}
         and len(bundle['policies'])==1 and len(bundle['evidence'])==2,'FOUR_ARTIFACT_READONLY_SCOPE')
    need({e['evidence_id'] for e in bundle['evidence']}=={'ev-current-review','ev-basis'},'EXACT_EVIDENCE_SCOPE')
    for entry in bundle['evidence']:
        need(sha(resource(root,entry['resource']['path']).read_bytes())==entry['resource']['sha256'],'EVIDENCE_RESOURCE_HASH')
    need(delivery['basis_sha256']==generation['basis_sha256']==sha((root/'basis.json').read_bytes()) and
         delivery['current_review_sha256']==generation['current_review_sha256']==sha((root/'current-review.json').read_bytes()) and
         delivery['generation_sha256']==sha((root/'generation.json').read_bytes()),'FROZEN_INPUT_HASHES')
    need(generation['a_consumer_commit']==delivery['a_consumer_commit']=='c5aefbc8e995c410b3babf74a251f05a7724a1c2'
         and datetime.fromisoformat(generation['created_at'].replace('Z','+00:00')).tzinfo is not None,'FIXED_CONSUMER_GENERATION')
    seed=sha(canonical(generation))[:24]
    for a in bundle['artifacts']+bundle['policies']:
        need(a['content_hash']==sha(canonical({k:v for k,v in a.items() if k!='content_hash'})),'ARTIFACT_DIGEST')
    need(all(a['run_id']=='b-lesson-'+seed and a['created_at']==generation['created_at'] for a in bundle['artifacts']),'GENERATION_IDENTITY')
    need(review['review_kind']=='B_MODEL_SOURCE_CONFIRMED' and review['items']==basis['items'] and
         not review['independent_human_acceptance'] and not review['a_owner_acceptance'],'MODEL_NOT_HUMAN_OR_A_SIGNATURE')
    need(delivery['human_verified'] is False and delivery['a_owner_acceptance'] is False and delivery['business_acceptance'] is False
         and delivery['platform_actions']==[] and delivery['source_windows_are_platform_frames'] is False and delivery['chapter_denominator'] is None,'NO_PLATFORM_OR_ACCEPTANCE_PROMOTION')
    source=kinds['SourceBundle']['payload'];ev=kinds['EvidenceBundle']['payload'];graph=kinds['QuestionGraph']['payload'];check=kinds['CheckReport']['payload']
    need(all(c['region_ids']==[] for c in ev['coverage_clues'] if c['disposition']=='EXCLUDED'),'EXCLUDED_CLUE_MUST_NOT_OWN_REGIONS')
    artifact_ref=lambda a:{k:a[k] for k in ('artifact_id','revision','kind','content_hash')}
    need(delivery['c01_graph_ref']==artifact_ref(kinds['QuestionGraph']) and check['graph']==check['subject']==artifact_ref(kinds['QuestionGraph'])
         and graph['source']==ev['source']==artifact_ref(kinds['SourceBundle']) and graph['evidence']==artifact_ref(kinds['EvidenceBundle']),'EXACT_ARTIFACT_REFERENCES')
    images={};assets={a['asset_id']:a for a in source['assets']}
    need(set(assets)=={a['asset_id'] for a in basis['assets']},'SOURCE_ASSET_SCOPE')
    for asset in source['assets']:
        raw=resource(root,asset['path']).read_bytes();need(sha(raw)==asset['sha256'],'ORIGINAL_SOURCE_HASH')
        with Image.open(io.BytesIO(raw)) as image:
            need(image.size==(asset['width'],asset['height']),'SOURCE_DIMENSIONS');images[asset['asset_id']]=image.convert('RGB')
    regions={r['region_id']:r for r in ev['regions']};fragments={f['fragment_id']:f for f in graph['fragments']}
    bindings={b['block_id']:b for b in delivery['bindings']};proofs={p['region_id']:p for p in delivery['source_proofs']}
    need(len(regions)==len(ev['regions']) and len(bindings)==len(delivery['bindings']) and len(proofs)==len(delivery['source_proofs']),'DUPLICATE_SOURCE_IDENTITIES')
    expected_blocks=list(basis['blocks'])+[{**e,'content_type':'image','text':None,'field':'exclusion','role':None,'item_key':None,'graph_fragment':False} for e in basis['exclusions'] if e.get('evidence_region',True)]
    need(set(bindings)=={b['block_id'] for b in expected_blocks} and len(proofs)==len(regions)==len(expected_blocks),'EXACT_REGION_BINDING_SET')
    for block in expected_blocks:
        binding=bindings[block['block_id']];rid='region-'+block['block_id'];region=regions[rid];proof=proofs[rid]
        need(binding['region_id']==rid and binding['item_key']==block['item_key'] and binding['field']==block['field'] and binding['role']==block['role'],'SOURCE_OWNER_ROLE_BINDING')
        if block.get('derived_from_block_id'):
            parent=next(b for b in expected_blocks if b['block_id']==block['derived_from_block_id'])
            pb=parent['bbox'];bb=block['bbox'];bounds=pb
            if block.get('derived_bounds_review'):
                review_bounds=block['derived_bounds_review']
                entry=next(q for q in basis['option_evidence']['questions'] if q['item_key']==block['item_key'])
                need(review_bounds['original_bbox']==pb and review_bounds['source_evidence_sha256']==basis['option_evidence']['original_raw_sha256'] and
                     review_bounds['allowed_container_bbox']==entry['recommended_container_bbox'],'OPTION_BOUNDS_REVIEW')
                bounds=review_bounds['allowed_container_bbox']
            need(parent.get('graph_fragment') is False and parent['asset_id']==block['asset_id'] and
                 bounds[0]<=bb[0]<bb[2]<=bounds[2] and bounds[1]<=bb[1]<bb[3]<=bounds[3] and
                 binding.get('derived_from_block_id')==parent['block_id'],'DERIVED_OPTION_PARENT_BINDING')
        need(region['text']==block['text'] and region['content_type']==block['content_type'],'SOURCE_TRANSCRIPTION_READBACK')
        need(all(type(x) is float for x in region['box']['bbox']) and region['box']['bbox']==[float(x) for x in block['bbox']]
             and region['box']['image']=={k:assets[block['asset_id']][k] for k in ('asset_id','width','height','sha256')},'SOURCE_COORDINATE_BINDING')
        raw=resource(root,proof['path']).read_bytes();need(sha(raw)==proof['sha256'],'CROP_BYTE_HASH')
        crop=images[block['asset_id']].crop(block['bbox'])
        with Image.open(io.BytesIO(raw)) as saved:
            need(saved.convert('RGB').size==crop.size and saved.convert('RGB').tobytes()==crop.tobytes()
                 and sha(crop.tobytes())==proof['rgb_sha256'],'ORIGINAL_CROP_PIXELS')
        if binding['fragment_id'] is not None:
            f=fragments[binding['fragment_id']]
            need(f['region_ids']==[rid] and f['role']==block['role'] and f['content_type']==block['content_type'],'GRAPH_FRAGMENT_SOURCE')
        text=''
        for run in binding['runs']:
            if run['format']=='blank':need(run['value'] is None,'QUESTION_BLANK_FILLED');text+=run['token']
            elif run['format']=='latex':
                token=run['source_text'];want=None
                match=re.fullmatch(r'(\d+)/(\d+)',token)
                if match:want='\\frac{'+match.group(1)+'}{'+match.group(2)+'}'
                match=re.fullmatch(r'([A-Za-z0-9]+)([²³⁴])',token)
                if match:want=match.group(1)+'^{'+str('²³⁴'.index(match.group(2))+2)+'}'
                match=re.fullmatch(r'([A-Za-z]+)([₁₂₃])',token)
                if match:want=match.group(1)+'_{'+str('₁₂₃'.index(match.group(2))+1)+'}'
                match=re.fullmatch(r'√(\d+)',token)
                if match:want='\\sqrt{'+match.group(1)+'}'
                need(want is not None and run['text']==want,'SOURCE_FORMULA_SEMANTICS');text+=token
            else:need(run['format']=='plain','RUN_FORMAT');text+=run['text']
        need(text==(block['text'] or ''),'RICH_RUN_TRANSCRIPTION')
        if 'rich_runs' in block:need(binding['runs']==block['rich_runs'],'DECLARED_RICH_RUNS')
    items=basis['items'];qids={'bq-'+i['item_key'] for i in items}
    questions={q['question_id']:q for q in graph['questions']};relations={r['question_id']:r for r in graph['answer_relations']}
    need(set(questions)==set(relations)==set(source['scope_manifest'])==qids and len(questions)==len(items),'QUESTION_SCOPE')
    combined=[];blanks=0
    for item in items:
        qid='bq-'+item['item_key'];q=questions[qid];relation=relations[qid]
        owned=[b for b in delivery['bindings'] if b['item_key']==item['item_key'] and b['fragment_id'] is not None]
        for field,text in item['fields'].items():
            reconstructed=''.join(regions[b['region_id']]['text'] for b in owned if b['field']==field)
            need(reconstructed==(text or ''),'QUESTION_FIELD_READBACK')
        answers=[b['fragment_id'] for b in owned if b['role'] in ('answer','explanation')]
        need(relation['status']=='SELECTED' and relation['candidate_fragment_ids']==answers and relation['selected_fragment_ids']==answers
             and relation['evidence_refs']==['ev-current-review'],'B_SOURCE_CONFIRMED_ANSWER_PAIRING')
        need(q['fragment_ids']==[b['fragment_id'] for b in owned if b['role'] not in ('answer','explanation')]
             and q['external_refs']=={'printed_number':item['printed_number'],'platform_question_id':None,'platform_order':None},'QUESTION_SOURCE_IDENTITY')
        need(q['parent_question_id']==('bq-'+item['parent_item_key'] if item.get('parent_item_key') else None),'VARIANT_PARENT')
        blanks+=len(re.findall(r'_{2,}',item['fields']['question']))
        if item['fields'].get('choice') is not None:
            option_texts=[regions[b['region_id']]['text'] for b in owned if b['field']=='choice']
            labels=[re.fullmatch(r'([A-D])[.、]\s*[^\n]+',text.strip()) for text in option_texts]
            if len(labels)!=4 or [x[1] if x else None for x in labels]!=list('ABCD'):combined.append(item['item_key'])
    need(delivery['pending_option_geometry']==combined and delivery['unfilled_question_blanks']==blanks,'PRECISE_OPTION_AND_BLANK_REPORT')
    if 'b_content_ready' in delivery:need(delivery['b_content_ready']==(not combined),'B_CONTENT_READINESS')
    issue_questions={i['scope_id'] for i in check['issues'] if i['code']=='OPTION_INCOMPLETE'}
    need(issue_questions=={'bq-'+key for key in combined} and all(i['code']!='ANSWER_AMBIGUOUS' for i in check['issues']),'ONLY_ACTUAL_CONTENT_GAPS')
    outcomes={c['check_id']:c['outcome'] for c in check['checks']}
    need(outcomes['answer_matching']=='PASS' and outcomes['source_integrity']=='PASS' and outcomes['structure']=='PASS','CONFIRMED_CONTENT_NOT_HUMAN_GATE')
    if projection:=basis.get('source_projection'):
        need(projection['provenance']=='DERIVED_PORTABLE_EVIDENCE_NOT_ORIGINAL_HTTP_OR_ORIGINAL_SPEC_BYTES' and
             projection['original_source_spec_sha256']==basis['root_review_sha256'] and
             projection['original_archive_sha256']==basis['source_input_sha256'],'DERIVED_SOURCE_PROVENANCE')
        source_items={i['item_key']:i for i in projection['source_items']}
        need(set(source_items)=={i['item_key'] for i in items},'PROJECTED_ITEM_SCOPE')
        projected_regions={r['region_id']:r for r in projection['regions']}
        need(len(projected_regions)==len(projection['regions'])==len(basis['blocks']) and set(projected_regions)==set(bindings),'PROJECTED_REGION_SCOPE')
        for item in items:
            key=item['item_key'];original=source_items[key]
            need(item['fields']=={'question':original['question_text'],'choice':'\n'.join(c['text'] for c in original['choices']) if original['choices'] else None,
                 'answer':original['answer_text'],'analysis':original['analysis_text']} and
                 item['intentional_wrong_solution_in_question']==original['intentional_wrong_solution_in_question'] and
                 item['source_flow_note']==original['source_flow_note'],'EXACT_SOURCE_FACT_FIELDS')
            for field,ids in (('question',original['question_region_ids_in_reading_order']),('answer',original['answer_region_ids_in_reading_order']),
                              ('choice',[c['region_id'] for c in original['choices']]),('figure',original['diagram_region_ids'])):
                need([b['block_id'] for b in delivery['bindings'] if b['item_key']==key and b['field']==field]==ids,'SOURCE_COLUMN_FLOW_AND_OWNER')
            blank_ids=[r['blank_id'] for b in delivery['bindings'] if b['item_key']==key and b['field']=='question' for r in b['runs'] if r['format']=='blank']
            need(blank_ids==[b['blank_id'] for b in original['blank_slots']] and all(b['value'] is None for b in original['blank_slots']),'EXACT_SOURCE_NULL_BLANKS')
        for block in basis['blocks']:
            original=projected_regions[block['block_id']];proof=proofs['region-'+block['block_id']]
            need(block['item_key']==original['item_key'] and block['asset_id']=='viewer-'+str(original['viewer_page']) and block['bbox']==original['bbox'] and
                 proof['rgb_sha256']==original['crop']['rgb_sha256']==block['original_crop_rgb_sha256'] and
                 block['original_crop_sha256']==original['crop']['sha256'],'PROJECTED_ORIGINAL_REGION_PIXELS')
    need(check['decision']==delivery['decision']=='HOLD','PREAPPLY_NOT_EXECUTION')
    need(all(a['kind'] not in ('ApplyPlan','PlatformSnapshot','ExecutionReceipt') for a in bundle['artifacts']),'NO_EXECUTION_ARTIFACT')
    return {'status':'B_SOURCE_CONTENT_AND_C01_BINDINGS_VERIFIED','questions':len(items),'selected_answer_relations':len(relations),
        'fragments':len(fragments),'regions':len(regions),'original_assets':len(assets),'source_crops':len(proofs),
        'unfilled_question_blanks':blanks,'pending_option_geometry':combined,'b_content_confirmed':len(items),
        'a_owner_acceptance':False,'human_verified':False,'platform_requests':0,'decision':'HOLD'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--delivery',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();value=verify(args.delivery)
    with args.out.open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps(value))


if __name__=='__main__':main()
