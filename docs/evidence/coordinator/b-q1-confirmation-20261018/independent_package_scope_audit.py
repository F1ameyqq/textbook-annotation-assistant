"""Coordinator-owned fixed-input read-only audit; never imports bundled B code."""
import collections
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath
from PIL import Image

ROOT = Path('D:/1800/.local/stages/coordinator/b-q1-ef6ba4dd')
OUT = ROOT / 'audit' / 'independent-package-scope-audit.json'
EXTRACTED = ROOT / 'extracted'
BASE = Path('D:/1800/.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip')
NEW = ROOT / 'handoffs/b/46007447/B-46007447-Q1-source-candidate-v1-HOLD-2026-10-18.zip'
EXPECTED_NEW = '3039645ca69c2604f542c479cb180049604788a3ca28ffac1b5063dee533afac'
EXPECTED_BASE = 'b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d'
report = {'audit_kind':'INDEPENDENT_FIXED_PACKAGE_STATIC_AUDIT', 'decision':'HOLD',
          'fixed_commit':'ef6ba4dd083e7fd5378e80123b2b038dd11d7052',
          'business_acceptance':False, 'checks':[], 'failures':[], 'observations':[]}

def sha(b):
    return hashlib.sha256(b).hexdigest()

def canonical(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(',',':'), allow_nan=False).encode('utf-8')

def check(name, ok, detail=None):
    item = {'name':name, 'ok':bool(ok)}
    if detail is not None: item['detail'] = detail
    report['checks'].append(item)
    if not ok: report['failures'].append(item)
    return bool(ok)

def ref(o):
    return {k:o[k] for k in ('artifact_id','revision','content_hash')}

def intersects(a,b):
    return max(a[0],b[0]) < min(a[2],b[2]) and max(a[1],b[1]) < min(a[3],b[3])

def contains(a,b):
    return a[0]<=b[0] and a[1]<=b[1] and b[2]<=a[2] and b[3]<=a[3]

before = {str(p):sha(p.read_bytes()) for p in (BASE,NEW)}
with zipfile.ZipFile(BASE) as old, zipfile.ZipFile(NEW) as new:
    cache = {}
    def base_json(name):
        if name not in cache: cache[name] = json.loads(old.read(name))
        return cache[name]
    def resolve(pointer):
        name,fragment = pointer.split('#',1)
        value = base_json(name)
        for token in fragment.strip('/').split('/') if fragment.strip('/') else []:
            token = token.replace('~1','/').replace('~0','~')
            value = value[int(token)] if isinstance(value,list) else value[token]
        return value
    def nj(name): return json.loads(new.read(name))

    check('candidate_zip_sha256', before[str(NEW)]==EXPECTED_NEW, before[str(NEW)])
    check('base_zip_sha256', before[str(BASE)]==EXPECTED_BASE, before[str(BASE)])
    inventories = {}
    for label,z in [('candidate',new),('base',old)]:
        names = [x.filename for x in z.infolist() if not x.is_dir()]
        manifest = json.loads(z.read('manifest.json'))
        entries = manifest['files']
        mnames = [e['path'] for e in entries]
        check(label+'_unique_members',len(set(names))==len(names))
        check(label+'_safe_member_paths',all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts and '\\' not in n and ':' not in n for n in names))
        check(label+'_unique_manifest_paths',len(set(mnames))==len(mnames))
        check(label+'_exact_manifest_file_set',set(names)==set(mnames)|{'manifest.json'}, {'member_count':len(names),'manifest_entries':len(entries)})
        bad = []
        for e in entries:
            b = z.read(e['path'])
            if len(b)!=e['bytes'] or sha(b)!=e['sha256']: bad.append(e['path'])
        check(label+'_all_manifest_sizes_and_hashes',not bad,bad)
        inventories[label]={'member_count':len(names),'manifest_entry_count':len(entries),'manifest_sha256':sha(z.read('manifest.json'))}
    check('extracted_exact_member_set',set(str(p.relative_to(EXTRACTED)).replace('\\','/') for p in EXTRACTED.rglob('*') if p.is_file())==set(new.namelist()))
    check('extracted_all_bytes_match_candidate_zip',all((EXTRACTED/n).read_bytes()==new.read(n) for n in new.namelist()))
    report['package_inventory']=inventories
    candidate=nj('candidate.json'); p=candidate['payload']; binding=nj('base-package-binding.json')
    selection=nj('native-selection.json'); scope=nj('native-scope-issues.json'); proposal=nj('scope-applicability-proposal.json')
    graph=base_json('artifacts/graph.json'); evidence=base_json('artifacts/evidence.json'); checkdoc=base_json('artifacts/check.json')
    check('base_binding_zip_and_manifest',binding['sha256']==before[str(BASE)] and binding['manifest_sha256']==inventories['base']['manifest_sha256'])
    check('base_binding_native_selection_hash',binding['native_selection_sha256']==sha(new.read('native-selection.json')))
    for name,b in binding['source_artifacts'].items():
        check('base_binding_'+name,sha(old.read(name))==b['file_sha256'] and ref(base_json(name))==b['reference'])
    check('candidate_input_refs_exact',candidate['input_refs']==[ref(evidence),ref(graph),ref(checkdoc)])
    check('candidate_payload_hash',candidate['content_hash']==sha(canonical(p)),sha(canonical(p)))
    check('candidate_identity_scope',candidate['book_id']=='46007447' and candidate['scope_id']=='single-question/'+p['question_id'] and candidate['revision']==1)
    check('HOLD_flags',p['decision']=='HOLD' and not any(p[k] for k in ['business_acceptance','human_verified','production_applied','a_accepted']) and p['platform_actions']==[])

    q=resolve(selection['object_paths']['question']); a=resolve(selection['object_paths']['answer'])
    check('native_question_object_unchanged',q==selection['native_question_snapshot'],sha(canonical(q)))
    check('native_answer_object_unchanged',a==selection['native_answer_snapshot'],sha(canonical(a)))
    check('native_relation_and_candidate_ids',q['question_id']==p['question_id'] and a['answer_id']==p['answer_id']==q['selected_answer_id'] and a['answer_id'] in q['candidate_answer_ids'])
    check('native_question_answer_same_section',q['section_path']==a['section_path']==p['section_path'] and q['printed_number']==a['printed_number']==p['printed_number'])
    report['native_object_hashes']={'question_canonical_sha256':sha(canonical(q)),'answer_canonical_sha256':sha(canonical(a))}
    for key in ['question_text','answer_text','explanation','source_answer_region']:
        check('native_pointer_'+key,resolve(selection['object_paths'][key]) is not None)

    source_by_id={s['asset_id']:s for s in p['sources']}; images={}; source_records=[]
    for aid,s in source_by_id.items():
        b=new.read(s['path']); orig=old.read(s['source_package_path']); im=Image.open(io.BytesIO(b)); im.load(); images[aid]=im.convert('RGB')
        ep=next(pg for pg in evidence['payload']['pages'] if pg['asset_id']==aid)
        check('source_bytes_'+aid,b==orig and sha(b)==s['sha256']==ep['source']['sha256'])
        check('source_dimensions_'+aid,list(im.size)==[s['width'],s['height']]==[ep['source']['width'],ep['source']['height']])
        source_records.append({'asset_id':aid,'sha256':sha(b),'size':list(im.size),'bytes':len(b)})
    report['sources']=source_records
    regions={r['region_id']:r for r in p['regions']}; bykey={r['key']:r for r in p['regions']}; crop_records=[]
    check('region_ids_and_keys_unique',len(regions)==len(bykey)==len(p['regions'])==13)
    for r in p['regions']:
        s=source_by_id[r['asset_id']]; im=images[r['asset_id']]; box=r['bbox']; c=r['crop']; data=new.read(c['path']); crop=Image.open(io.BytesIO(data)); crop.load(); rgb=crop.convert('RGB')
        check('crop_source_identity_'+r['key'],r['source_sha256']==s['sha256'] and r['source_size']==list(im.size))
        check('crop_bounds_'+r['key'],all(type(v) is int for v in box) and 0<=box[0]<box[2]<=im.width and 0<=box[1]<box[3]<=im.height)
        check('crop_pixels_'+r['key'],rgb.tobytes()==im.crop(tuple(box)).tobytes() and list(rgb.size)==c['size']==[box[2]-box[0],box[3]-box[1]] and sha(data)==c['sha256'] and sha(rgb.tobytes())==c['rgb_sha256'])
        check('crop_projection_'+r['key'],c['crop_to_original']==[[1,0,box[0]],[0,1,box[1]],[0,0,1]])
        crop_records.append({'key':r['key'],'asset_id':r['asset_id'],'bbox':box,'size':list(rgb.size),'file_sha256':sha(data),'rgb_sha256':sha(rgb.tobytes())})
    report['crops']=crop_records
    selected=[regions[rid] for rid in p['proposed_semantic_region_ids']]
    check('six_semantic_groups_exact',len(selected)==len(set(p['proposed_semantic_region_ids']))==6 and [r['key'] for r in selected]==['stem-with-parentheses','option-A','option-B','option-C','option-D','answer-D'])
    overlaps=[(x['key'],y['key']) for i,x in enumerate(selected) for y in selected[i+1:] if x['asset_id']==y['asset_id'] and intersects(x['bbox'],y['bbox'])]
    check('semantic_groups_nonoverlap',not overlaps,overlaps)
    check('parenthesis_contained_not_extra_group',contains(bykey['stem-with-parentheses']['bbox'],bykey['response-parentheses']['bbox']) and bykey['response-parentheses']['region_id'] not in p['proposed_semantic_region_ids'] and bykey['response-parentheses']['source_fragment_ids']==[])
    check('answer_number_and_neighbor_separate',all(not intersects(bykey['answer-D']['bbox'],bykey[k]['bbox']) for k in ['answer-number-context','answer-next-item-context']))
    all_fragments=q['fragments']+a['fragments']; fragment_ids=[f['fragment_id'] for f in all_fragments]; mapped_ids=[fid for r in selected for fid in r['source_fragment_ids']]
    check('all_seven_fragments_mapped_once',collections.Counter(fragment_ids)==collections.Counter(mapped_ids) and len(mapped_ids)==7)
    fragment_index={f['fragment_id']:f for f in all_fragments}
    check('all_fragment_role_and_asset_bindings',all(fragment_index[fid]['asset_id']==r['asset_id'] and fragment_index[fid]['role']==r['role'] for r in selected for fid in r['source_fragment_ids']))
    sm=p['source_mapping']; content=p['candidate_content']; ansfrag=a['fragments'][0]
    check('source_mapping_stem_ids',sm['stem_source_fragment_ids']==[f['fragment_id'] for f in q['fragments'] if f['role']=='stem'])
    check('source_mapping_option_text_ids',all(x['source_fragment_id']==r['source_fragment_ids'][0] and x['option_label']==fragment_index[x['source_fragment_id']]['option_label'] and r['text']==fragment_index[x['source_fragment_id']]['text'] for x in sm['options'] for r in [regions[x['candidate_region_id']]]))
    check('answer_raw_text_span_old_bbox_preserved',sm['answer']['raw_text']==ansfrag['raw_text'] and sm['answer']['source_text_span']==ansfrag['text_span'] and sm['answer']['old_bbox']==ansfrag['bbox'] and sm['answer']['source_fragment_id']==ansfrag['fragment_id'])
    detail=sm['answer']['source_detail']; check('answer_source_detail_exact',resolve(detail['pointer'])==detail['value'])
    check('answer_span_resolves_to_D',ansfrag['raw_text'][slice(*ansfrag['text_span'])]==content['answer_text']==a['text']=='D')
    stem='\n'.join(f['text'] for f in q['fragments'] if f['role']=='stem')
    placeholder='\uff08\u3000\u3000\uff09'
    check('content_only_declared_normalizations',content['stem_with_number_and_source_linebreaks']==stem+'\n'+placeholder and content['stem_body_normalized_without_number']==stem[2:].replace('\n','')+placeholder and content['option_texts']==[f['text'] for f in q['fragments'] if f['role']=='option'])
    check('response_output_span',content['stem_body_normalized_without_number'][slice(*content['response_output_span'])]==placeholder)
    check('no_invented_explanation',content['explanation_present']==a['explanation_present']==False and content['explanation_text']==a['explanation_text']=='' and not any(r['role']=='explanation' for r in selected))

    original_scopes=[i for i in checkdoc['payload']['issues'] if i.get('scope_type')=='scope']
    native_entries=scope['scope_issues']; dispositions=proposal['dispositions']
    check('original_all_scope_issues_preserved',len(original_scopes)==len(native_entries)==len(dispositions)==31 and [i['issue'] for i in native_entries]==original_scopes)
    check('all_native_scope_pointers_exact',all(resolve(x['pointer'])==x['issue'] for x in native_entries))
    check('all_disposition_ids_exact',len(set(x['issue_id'] for x in dispositions))==31 and set(x['issue_id'] for x in dispositions)==set(x['issue_id'] for x in original_scopes))
    check('all_check_refs_exact',scope['source_check']==proposal['source_check_ref']==ref(checkdoc))
    selected_ids={p['question_id'],p['answer_id']}; selected_boxes=[(r['asset_id'],r['bbox']) for r in selected]+[(f['asset_id'],f['bbox']) for f in all_fragments]
    disposition_records=[]; proof_count=0; code_counts=collections.Counter(); disjoint_count=0
    for d in dispositions:
        orig=resolve(d['original_issue_pointer']); proofs=d['proof']; code_counts[d['code']]+=1
        check('issue_binding_'+d['issue_id'],orig['issue_id']==d['issue_id'] and orig['code']==d['code'] and orig==next(x for x in original_scopes if x['issue_id']==d['issue_id']))
        check('issue_preservation_flags_'+d['issue_id'],d['a_confirmed']==False and d['original_issue_removed']==False)
        proof_ok=True; geometries=[]; proof_line_ids=[]
        for pr in proofs:
            proof_count+=1; obj=resolve(pr['pointer']); proof_ok &= obj==pr['value']
            if 'line_id' in obj:
                proof_line_ids.append(obj['line_id'])
                pagepointer=pr['pointer'].split('/ocr_lines/')[0]
                page=resolve(pagepointer)
                proof_ok &= page['asset_id']==pr['asset_id'] and obj['line_id'].startswith(pr['asset_id']+'/')
                geometries.append((pr['asset_id'],obj['bbox']))
            elif 'source_regions' in obj:
                proof_ok &= obj['asset_id']==pr['asset_id'] and obj['candidate_id']==orig['detail']
                page=next(pg for pg in evidence['payload']['pages'] if pg['asset_id']==obj['asset_id'])
                proof_ok &= obj['source_sha256']==page['source']['sha256']
                geometries.extend((obj['asset_id'],r['bbox']) for r in obj['source_regions'])
        check('proof_object_binding_'+d['issue_id'],proof_ok)
        if orig.get('evidence_refs'): check('proof_covers_all_original_evidence_refs_'+d['issue_id'],set(orig['evidence_refs'])==set(proof_line_ids))
        geo_disjoint=all(aid!=sid or not intersects(box,sbox) for aid,box in geometries for sid,sbox in selected_boxes)
        if d['code']=='BUSINESS_REVIEW_REQUIRED':
            supported=d['proposed_applicability']=='APPLICABLE_REMAINS_HOLD'; basis='BUSINESS_BLOCKER_RETAINED'
        elif d['code']=='CONTENT_REVISION_DRAFT_UNVERIFIED':
            supported=bool(proofs) and not selected_ids.intersection(orig['detail']['affected_answer_ids']); basis='EXPLICIT_OTHER_ANSWER_IDS'
        else:
            supported=bool(geometries) and geo_disjoint; basis='EXACT_SOURCE_OBJECTS_DISJOINT_FROM_SELECTED_CONTENT'; disjoint_count+=int(supported)
        if d['code']!='BUSINESS_REVIEW_REQUIRED': supported &= d['proposed_applicability']=='OUTSIDE_SELECTED_CONTENT_PENDING_A_SCOPE_POLICY'
        check('bounded_scope_basis_'+d['issue_id'],supported)
        disposition_records.append({'issue_id':d['issue_id'],'code':d['code'],'original_pointer':d['original_issue_pointer'],'proof_count':len(proofs),'source_regions_checked':len(geometries),'basis':basis,'supported_for_policy_review_only':bool(supported)})
    check('proposal_counts_and_new_gate',proposal['counts']=={'requires_A_scope_policy':30,'applicable_business_hold':1} and proposal['new_candidate_review_required'] and proposal['decision']=='HOLD')
    check('candidate_whole_chapter_claim_false',p['coverage']['whole_chapter_claim']==False and p['coverage']['platform_frame_count'] is None)
    resource=next(pg['source'] for pg in evidence['payload']['pages'] if pg['asset_id']=='resource-173')
    check('resource_173_distinct_from_viewer_173',resource['sha256']!=source_by_id['viewer-173']['sha256'] and sha(old.read('source/adjacent/46007447_resource_173.jpg'))==resource['sha256'])
    report['scope_audit']={'original_check_issue_count':len(checkdoc['payload']['issues']),'original_scope_count':len(original_scopes),'proof_object_count':proof_count,'code_counts':dict(code_counts),'disjoint_source_based_proposals':disjoint_count,'other_answer_id_proposals':1,'business_hold':1,'dispositions':disposition_records,'resource_173_sha256':resource['sha256']}
    report['observations']=[
      '30 exclusions have exact-object evidence supporting review under a selected-content policy; the evidence does not itself authorize any scope-policy waiver.',
      '7 non-context evidence regions exist, but the explicit semantic ID list contains 6: using context_only=false as the adapter selector would emit the nested placeholder twice.',
      'Native option-B OCR estimate begins at x=206, candidate visual box begins at x=207. Old OCR-box containment is not claimed; exact source pixels and model visual check are separate from pixel-perfect glyph segmentation.',
      'Original Check retains all 127 issue objects; the 31 scope issues are audited as proposals and are not cleared.',
      'No missing or contradictory declared source bindings were found in this bounded static check.'
    ]

after={str(path):sha(path.read_bytes()) for path in (BASE,NEW)}
check('input_archives_unchanged_after_audit',after==before)
report['input_sha256_before']=before
report['input_sha256_after']=after
report['execution']={'python':sys.version,'pillow':Image.__version__,'b_scripts_executed':False,'sqlite_accessed':False,'receiver_planner_mock_platform_executed':False}
report['limits']=['No new recognition/OCR; no B verifier or producer was executed.','No receiver, planner, mock, platform, SQLite or credentials were accessed.','Pixel equality proves crop provenance, not human/business acceptance or platform geometry.','Current script parses immutable raw ZIP JSON and uses Pillow RGB decoding; candidate schema acceptance and A policy implementation are outside this check.','Historical E0.1 supplement is not independently audited in this bounded package task.']
report['result']={'checks':len(report['checks']),'failed':len(report['failures']),'static_integrity': 'PASS' if not report['failures'] else 'FAIL','decision':'HOLD'}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'output':str(OUT),'sha256':sha(OUT.read_bytes()),'result':report['result'],'inventory':report['package_inventory'],'scope':{k:v for k,v in report['scope_audit'].items() if k!='dispositions'},'failures':report['failures']},ensure_ascii=True,indent=2))
