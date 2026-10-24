"""Independent predecessor/pixel/content verification of a B C01 revision."""
import argparse
import copy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
from PIL import Image
from verify_lesson_c01_b import read, portable, resource

sha = lambda b: hashlib.sha256(b).hexdigest()
canonical = lambda x: json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
ref = lambda a: {k:a[k] for k in ('artifact_id','revision','kind','content_hash')}


def need(value,code):
    if not value:
        raise ValueError(code)


def verify(folder):
    root=Path(folder)
    need(not any(p.is_symlink() for p in root.rglob('*')),'NO_SYMLINKS')
    review=read(root/'current-review.json');d=read(root/'delivery.json');bundle=read(root/'bundle.json');generation=read(root/'generation.json')
    for p in root.rglob('*.json'):
        portable(read(p))
    need(review['review_kind']=='B_MODEL_SOURCE_CONFIRMED' and review['human_verified'] is False and
         review['a_owner_acceptance'] is False and review['content_issues']==[],'B_MODEL_NOT_FAKE_ACCEPTANCE')
    old_files={}
    for member in review['predecessor_members']:
        name=member['path'];p=resource(root,name)
        historical=resource(root,'history/v2/'+name)
        raw=(historical if historical.is_file() else p).read_bytes()
        need(name not in old_files and len(raw)==member['bytes'] and sha(raw)==member['sha256'],'PREDECESSOR_MEMBER_HASH')
        old_files[name]=raw
    need(sha(old_files['bundle.json'])==review['predecessor_bundle_sha256'],'PREDECESSOR_BUNDLE_HASH')
    old_bundle=json.loads(old_files['bundle.json']);old_d=json.loads(old_files['delivery.json'])
    changed={'bundle.json','delivery.json','current-review.json','generation.json','pending-review.json'}
    expected=(set(old_files)-{'pending-review.json'})|{'history/v2/'+n for n in changed if n in old_files}
    need({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}==expected,'EXACT_REVISION_FILE_SET')
    for n,b in old_files.items():
        if n not in changed:
            need(resource(root,n).read_bytes()==b,'IMMUTABLE_ORIGINAL_CONTENT_BYTES')
        else:
            need(resource(root,'history/v2/'+n).read_bytes()==b,'HISTORICAL_STATE_NOT_OVERWRITTEN')
    need(d['current_review_sha256']==generation['current_review_sha256']==sha((root/'current-review.json').read_bytes())
         and d['generation_sha256']==sha((root/'generation.json').read_bytes()) and
         d['basis_sha256']==sha((root/'basis.json').read_bytes()) and
         generation['predecessor_bundle_sha256']==review['predecessor_bundle_sha256'] and
         generation['config_version']=='b-source-confirmation-revision.2' and
         generation['a_consumer_commit']==d['a_consumer_commit']=='c5aefbc8e995c410b3babf74a251f05a7724a1c2' and
         datetime.fromisoformat(generation['created_at'].replace('Z','+00:00')).tzinfo is not None,'FROZEN_REVISION_CONTEXT')
    kinds={'SourceBundle','EvidenceBundle','QuestionGraph','CheckReport'}
    need(bundle['format_version']=='c01-exchange-1','C01_REQUIRED')
    old={a['kind']:a for a in old_bundle['artifacts']};new={a['kind']:a for a in bundle['artifacts']}
    need(set(old)==set(new)==kinds and len(bundle['artifacts'])==4 and len(bundle['policies'])==1 and len(bundle['evidence'])==2,'READONLY_SCOPE')
    for a in old_bundle['artifacts']+old_bundle['policies']+bundle['artifacts']+bundle['policies']:
        need(a['content_hash']==sha(canonical({k:v for k,v in a.items() if k!='content_hash'})),'ARTIFACT_DIGEST')
    policy=bundle['policies'][0];old_policy=old_bundle['policies'][0]
    need(policy['revision']==old_policy['revision']+1 and
         {k:v for k,v in policy.items() if k not in ('revision','content_hash','source_notes')}==
         {k:v for k,v in old_policy.items() if k not in ('revision','content_hash','source_notes')} and
         policy['confirmation_status']=='UNRESOLVED' and policy['applicability']=='PROPOSAL_ONLY','NO_POLICY_ADOPTION_CLAIM')
    for kind,a in new.items():
        previous=old[kind]
        need(a['artifact_id']==previous['artifact_id'] and a['revision']==previous['revision']+1 and
             a['book_id']==previous['book_id'] and a['scope_id']==previous['scope_id'] and
             a['created_at']==generation['created_at'] and a['run_id']=='b-confirmed-'+sha(canonical(generation))[:24] and
             a['producer']['policy_versions']==[{k:policy[k] for k in ('policy_id','revision','content_hash')}], 'ENVELOPE_REVISION')
    source=new['SourceBundle']['payload'];ev=new['EvidenceBundle']['payload'];graph=new['QuestionGraph']['payload'];check=new['CheckReport']['payload']
    old_source=old['SourceBundle']['payload'];old_ev=old['EvidenceBundle']['payload'];old_graph=old['QuestionGraph']['payload']
    need({k:v for k,v in source.items() if k not in ('directories','external_page_mappings','history')}==
         {k:v for k,v in old_source.items() if k not in ('directories','external_page_mappings','history')},'SOURCE_SCOPE_IMMUTABLE')
    need(source['directories']==review['local_directories'],'LOCAL_DIRECTORIES')
    for mapping,previous in zip(source['external_page_mappings'],old_source['external_page_mappings']):
        need({k:v for k,v in mapping.items() if k not in ('directory_id','mapping_status')}==
             {k:v for k,v in previous.items() if k not in ('directory_id','mapping_status')} and
             mapping['directory_id']==review['asset_directories'][mapping['asset_id']] and mapping['mapping_status']=='CONFIRMED','SOURCE_LOCAL_PAGE_MAPPING')
    for history in source['history']:
        r=history['resource'];need(sha(resource(root,r['path']).read_bytes())==r['sha256'],'HISTORICAL_RESOURCE_HASH')
    need(ev['source']==graph['source']==ref(new['SourceBundle']) and graph['evidence']==ref(new['EvidenceBundle']) and
         check['subject']==check['graph']==d['c01_graph_ref']==ref(new['QuestionGraph']),'ARTIFACT_REFERENCES')
    regions={r['region_id']:r for r in ev['regions']}
    need(review['confirmed_region_ids']==list(regions) and len(regions)==len(old_ev['regions']),'REGION_SCOPE')
    label_whitelist={'q16-task1':'（1）','q16-task2':'（2）','q16-task3':'（3）'}
    old_regions={r['region_id']:r for r in old_ev['regions']}
    old_bindings={b['block_id']:b for b in old_d['bindings']}
    old_proofs={p['region_id']:p for p in old_d['source_proofs']}
    changes=review.get('source_text_changes',[]);need(d.get('source_text_changes',[])==changes,'TEXT_DELTA_AUDIT_BINDING')
    required={bid for bid,prefix in label_whitelist.items() if bid in old_bindings and
              not old_regions[old_bindings[bid]['region_id']]['text'].startswith(prefix)}
    need(len(changes)==len({c['block_id'] for c in changes}) and {c['block_id'] for c in changes}==required,'EXACT_PRINTED_LABEL_DELTA_SET')
    by_rid={}
    expected_bindings=copy.deepcopy(old_d['bindings'])
    for c in changes:
        bid=c['block_id'];prefix=label_whitelist.get(bid)
        need(prefix is not None,'TEXT_DELTA_WHITELIST')
        b=old_bindings[bid];reg=old_regions[b['region_id']];proof=old_proofs[b['region_id']]
        runs=copy.deepcopy(b['runs']);need(runs[0]['format']=='plain' and b['role']=='stem','STEM_LABEL_RUN')
        runs[0]['text']=prefix+runs[0]['text']
        need(c['operation']=='RESTORE_PRINTED_SUBQUESTION_LABEL' and c['prefix']==prefix and c['region_id']==b['region_id'] and
             c['before_text']==reg['text'] and c['after_text']==prefix+reg['text'] and c['before_runs']==b['runs'] and
             c['after_runs']==runs and c['asset_id']==reg['box']['image']['asset_id'] and
             c['source_sha256']==reg['box']['image']['sha256'] and c['bbox']==reg['box']['bbox'] and
             c['crop_path']==proof['path'] and c['crop_png_sha256']==proof['sha256']==sha(old_files[proof['path']]) and
             c['crop_rgb_sha256']==proof['rgb_sha256'],'SOURCE_BOUND_LABEL_DELTA')
        by_rid[c['region_id']]=c
        next(x for x in expected_bindings if x['block_id']==bid)['runs']=runs
    for current,previous in zip(ev['regions'],old_ev['regions']):
        expected=copy.deepcopy(previous)
        if current['region_id'] in by_rid:expected['text']=by_rid[current['region_id']]['after_text']
        need({k:v for k,v in current.items() if k!='certainty'}=={k:v for k,v in expected.items() if k!='certainty'}
             and current['certainty']=='CONFIRMED','REGION_TEXT_AND_GEOMETRY_IMMUTABLE')
    need(d['bindings']==expected_bindings and d['source_proofs']==old_d['source_proofs'],'RICH_TEXT_AND_SOURCE_PROOFS_IMMUTABLE')
    images={}
    need(review['source_asset_sha256']=={a['asset_id']:a['sha256'] for a in source['assets']},'REVIEW_ASSET_HASHES')
    for asset in source['assets']:
        raw=resource(root,asset['path']).read_bytes();need(sha(raw)==asset['sha256'],'SOURCE_IMAGE_HASH')
        with Image.open(io.BytesIO(raw)) as image:
            need(image.size==(asset['width'],asset['height']),'SOURCE_IMAGE_SIZE');images[asset['asset_id']]=image.convert('RGB')
    proofs={p['region_id']:p for p in d['source_proofs']}
    need(set(proofs)==set(regions) and len(proofs)==len(d['source_proofs']),'EXACT_CROP_SCOPE')
    for rid,region in regions.items():
        box=region['box'];image=images[box['image']['asset_id']];bbox=box['bbox']
        need(0<=bbox[0]<bbox[2]<=image.width and 0<=bbox[1]<bbox[3]<=image.height,'ORIGINAL_COORDINATE_BOUNDS')
        crop=image.crop(bbox);p=proofs[rid];raw=resource(root,p['path']).read_bytes()
        with Image.open(io.BytesIO(raw)) as saved:
            need(sha(raw)==p['sha256'] and crop.size==saved.size and crop.tobytes()==saved.convert('RGB').tobytes()
                 and sha(crop.tobytes())==p['rgb_sha256'],'ORIGINAL_CROP_PIXELS')
    need(graph['fragments']==old_graph['fragments'],'SHARED_AND_ACTIVE_FRAGMENTS_IMMUTABLE')
    need(len(graph['questions'])==len(old_graph['questions']) and len(graph['answer_relations'])==len(graph['questions']),'QUESTION_AND_RELATION_SCOPE')
    confirmations={c['question_id']:c for c in review['answer_confirmations']}
    for question,previous,relation,old_relation in zip(graph['questions'],old_graph['questions'],graph['answer_relations'],old_graph['answer_relations']):
        qid=question['question_id'];confirmation=confirmations[qid]
        need({k:v for k,v in question.items() if k!='directory_id'}=={k:v for k,v in previous.items() if k!='directory_id'} and
             question['directory_id']==review['question_directories'][qid] and question['external_refs']['platform_question_id'] is None,'LOCAL_QUESTION_AND_SHARED_IDENTITY')
        owned=[b['fragment_id'] for b in d['bindings'] if b.get('owner_id',b.get('item_key'))==qid and
               b['fragment_id'] is not None and b['role'] in ('answer','explanation')]
        need(owned and relation['question_id']==qid and relation['candidate_fragment_ids']==old_relation['candidate_fragment_ids']==owned and
             relation['selected_fragment_ids']==confirmation['selected_fragment_ids']==owned and relation['status']=='SELECTED' and
             confirmation['disposition']=='B_MODEL_SOURCE_CONFIRMED' and confirmation['source_reason'],'EXPLICIT_SOURCE_CONFIRMED_RELATION')
    blanks=[r for b in d['bindings'] for r in b['runs'] if r['format']=='blank']
    need(all(r['value'] is None for r in blanks),'PRINTED_BLANKS_STILL_NULL')
    for name in ('q16_task_map','q16_formula_slots','reading_task_answers'):
        if name in old_d:need(d[name]==old_d[name],'FORMULA_AND_TASK_MAP_PRESERVED')
    outcomes={c['check_id']:c['outcome'] for c in check['checks']}
    need(outcomes==dict(source_integrity='PASS',structure='PASS',answer_matching='PASS',coverage='UNAVAILABLE',policy='UNAVAILABLE') and
         len(check['issues'])==1 and check['issues'][0]['code']=='POLICY_UNRESOLVED' and check['issues'][0]['severity']=='info' and
         check['decision']==d['decision']=='HOLD','CONTENT_READY_PREAPPLY_SCOPE_SEPARATE')
    need(d['b_content_ready'] is True and d['b_content_issues']==[] and d['human_verified'] is False and
         d['a_owner_acceptance'] is False and d['business_acceptance'] is False and d['platform_actions']==[] and
         d['source_windows_are_platform_frames'] is False and d['chapter_denominator'] is None,'NO_FAKE_ACCEPTANCE_OR_EXECUTION')
    for record in bundle['evidence']:
        r=record['resource'];need(sha(resource(root,r['path']).read_bytes())==r['sha256'],'C01_EVIDENCE_RESOURCES')
    shared={f['fragment_id'] for f in graph['fragments'] if f['role']=='shared_material'}
    return dict(status='SOURCE_CONFIRMED_REVISION_AND_IMMUTABLE_CONTENT_VERIFIED',questions=len(graph['questions']),
        selected_answer_relations=len(graph['answer_relations']),shared_fragments=len(shared),
        shared_material_users=sum(bool(q['shared_fragment_ids']) for q in graph['questions']),fragments=len(graph['fragments']),
        regions=len(regions),original_assets=len(source['assets']),source_crops=len(proofs),
        formula_slots=len(d.get('q16_formula_slots',[])),null_blanks=len(blanks),b_content_ready=True,b_content_issues=[],
        source_bound_label_restorations=len(changes),
        decision='HOLD',human_verified=False,a_owner_acceptance=False,platform_requests=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delivery',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=verify(args.delivery)
    with args.out.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps(result))


if __name__=='__main__':main()
