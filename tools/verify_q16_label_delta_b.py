"""Strict adjacent-revision audit: restore only Q16's three printed sublabels.

This audits already consumed snapshots. It neither edits nor seals a C01 bundle.
"""
import copy
import json

LABELS={'q16-task1':'（1）','q16-task2':'（2）','q16-task3':'（3）'}
PUBLICATION_FIELDS=('artifact_id','revision','content_hash','created_at','run_id')
FILE_DIGESTS={'basis_sha256':'basis.json','current_review_sha256':'current-review.json',
              'generation_sha256':'generation.json','pending_review_sha256':'pending-review.json'}


def normalize_labels(value,path='',events=None):
    events=[] if events is None else events
    if isinstance(value,list):
        return [normalize_labels(v,path+'/'+str(i),events) for i,v in enumerate(value)]
    if not isinstance(value,dict):return value
    result={k:normalize_labels(v,path+'/'+k,events) for k,v in value.items()}
    identity=result.get('region_id','').removeprefix('region-')
    if identity in LABELS and 'text' in result:
        text=result['text'];label=LABELS[identity]
        if isinstance(text,str) and text.startswith(label):
            result['text']=text[len(label):]
            events.append(dict(path=path+'/text',block_id=identity,label=label,representation='region_text'))
    identity=result.get('block_id')
    if identity in LABELS and isinstance(result.get('runs'),list) and result['runs']:
        runs=result['runs'];label=LABELS[identity]
        if runs[0].get('format')=='plain' and runs[0].get('text','').startswith(label):
            runs[0]['text']=runs[0]['text'][len(label):]
            if not runs[0]['text'] and set(runs[0])=={'format','text'}:runs.pop(0)
            events.append(dict(path=path+'/runs',block_id=identity,label=label,representation='runs'))
    return result


def normalize_envelopes(value,path='',events=None):
    """Normalize only publication envelopes and bound file digests, never content."""
    events=[] if events is None else events
    if isinstance(value,list):return [normalize_envelopes(v,path+'/'+str(i),events) for i,v in enumerate(value)]
    if not isinstance(value,dict):return value
    result={k:normalize_envelopes(v,path+'/'+k,events) for k,v in value.items()}
    c01_reference=(path.startswith('/bundle/artifacts/') and ('/input_refs/' in path or path.rsplit('/',1)[-1] in ['source','evidence','graph','subject']))
    sidecar_reference=path in ['/sidecars/delivery.json/c01_graph_ref','/sidecars/pending-review.json/c01_graph_ref']
    if (c01_reference or sidecar_reference) and set(value)=={'artifact_id','revision','kind','content_hash'}:
        events.append(path)
        return dict(artifact_id='BOUND-'+value['kind'],revision='BOUND',kind=value['kind'],content_hash='BOUND')
    # Only the four top-level C01 artifacts have this envelope shape.
    if path.startswith('/bundle/artifacts/') and path.count('/')==3:
        for key in PUBLICATION_FIELDS:
            if key in result:result[key]='PUBLICATION-'+key
        if 'producer' in result:
            for key in ['implementation_version','config_version']:
                if key in result['producer']:result['producer'][key]='PUBLICATION-'+key
    if path=='/sidecars/generation.json':
        for key in ['created_at','config_version','b_base_commit']:
            if key in result:result[key]='PUBLICATION-'+key
    # Hash values are separately checked against actual file bytes by the caller.
    if path in ['/sidecars/delivery.json','/sidecars/generation.json','/sidecars/pending-review.json']:
        for key in FILE_DIGESTS:
            if key in result:result[key]='BOUND-FILE-'+FILE_DIGESTS[key]
    if path.startswith('/bundle/evidence/') and path.endswith('/resource'):
        if result.get('path') in ['basis.json','current-review.json']:
            result['sha256']='BOUND-FILE-'+result['path']
    return result


def bound_digest_checks(folder,snapshot,read_bytes,sha):
    """Check dependent hashes before granting them a reseal-only exemption."""
    checks=[]
    for name in ['delivery.json','generation.json','pending-review.json']:
        value=snapshot['sidecars'].get(name,{})
        for key,file in FILE_DIGESTS.items():
            if key in value:
                try:passed=value[key]==sha(read_bytes(folder/file))
                except FileNotFoundError:passed=False
                checks.append(dict(check='label_bound_file_digest_'+name+'/'+key,passed=passed,detail=file))
    return checks


def audit_labels_only(old,new,diff):
    """Reject every remaining field delta after exact labels and reseals are removed."""
    before_events=[];after_events=[]
    before=normalize_labels(copy.deepcopy(old),events=before_events)
    after=normalize_labels(copy.deepcopy(new),events=after_events)
    checks=[]
    checks.append(dict(check='label_adjacent_baseline_is_unlabelled',passed=not before_events,detail=before_events))
    for block,label in LABELS.items():
        core=[e for e in after_events if e['block_id']==block and e['path'].startswith('/bundle/') and e['representation']=='region_text']
        bindings=[e for e in after_events if e['block_id']==block and e['path'].startswith('/sidecars/delivery.json/bindings/') and e['representation']=='runs']
        reviewed=[e for e in after_events if e['block_id']==block and e['path'].startswith('/sidecars/current-review.json/q16/question_blocks/') and e['representation']=='runs']
        checks.append(dict(check='label_in_C01_text_'+block,passed=len(core)==1,detail=core))
        checks.append(dict(check='label_in_bound_runs_'+block,passed=len(bindings)==1,detail=bindings))
        checks.append(dict(check='label_in_current_source_review_'+block,passed=len(reviewed)==1,detail=reviewed))
    before=normalize_envelopes(before);after=normalize_envelopes(after)
    unauthorized=diff(before,after)
    checks.append(dict(check='only_three_labels_and_dependent_reseals_changed',passed=not unauthorized,detail=unauthorized))
    old_parts={a['kind']:a['payload'] for a in old['bundle']['artifacts']}
    new_parts={a['kind']:a['payload'] for a in new['bundle']['artifacts']}
    old_regions={r['region_id']:r for r in old_parts['EvidenceBundle']['regions']}
    new_regions={r['region_id']:r for r in new_parts['EvidenceBundle']['regions']}
    source_bindings=[]
    for block,label in LABELS.items():
        rid='region-'+block
        old_region=old_regions.get(rid);new_region=new_regions.get(rid)
        if old_region and new_region:
            exact=new_region['text']==label+old_region['text']
            geometry=old_region['box']==new_region['box'] and old_region['crop_transform']==new_region['crop_transform']
            checks.append(dict(check='label_exact_prefix_and_fixed_geometry_'+block,passed=exact and geometry,detail=None))
            source_bindings.append(dict(block_id=block,label=label,region_id=rid,original_box=old_region['box'],
                before_text=old_region['text'],after_text=new_region['text'],evidence_refs=new_region['evidence_refs'],
                exact_label_prefix=exact,geometry_unchanged=geometry))
    return dict(status='Q16_THREE_LABELS_ONLY' if all(c['passed'] for c in checks) else 'Q16_LABEL_DELTA_REJECTED',
        checks=checks,events=after_events,unauthorized_delta=unauthorized,source_bindings=source_bindings,
        local_rule='Exactly the three Chinese fullwidth prefixes; no other source text, formula, answer, blank, geometry or field delta is exempted.',
        publication_normalization='Known C01 artifact envelopes/ArtifactRefs and existing bound file digests only; digest values must be verified from real files separately.',
        actual_new_package_consumed=False,platform_requests=0,dispatch=False)


def audit_historical_source_manifest(old,new,diff):
    """Historical v2 -> confirmed revision: distinguish lifecycle from source text.

The abandoned intermediate draft is not needed. The three source-bound records
must exactly describe the only text/runs changes against immutable historical v2.
"""
    before={a['kind']:a['payload'] for a in old['bundle']['artifacts']}
    after={a['kind']:a['payload'] for a in new['bundle']['artifacts']}
    old_d=old['sidecars']['delivery.json'];new_d=new['sidecars']['delivery.json']
    review=new['sidecars']['current-review.json'];checks=[]
    def check(name,passed,detail=None):checks.append(dict(check=name,passed=bool(passed),detail=detail))
    old_regions={r['region_id']:r for r in before['EvidenceBundle']['regions']}
    old_bindings={b['block_id']:b for b in old_d['bindings']}
    old_proofs={p['region_id']:p for p in old_d['source_proofs']}
    changes=new_d.get('source_text_changes',[])
    check('source_label_manifest_bound_to_current_review',changes==review.get('source_text_changes'))
    check('exact_three_source_label_records',len(changes)==3 and {r.get('block_id') for r in changes}==set(LABELS))
    expected_regions=copy.deepcopy(before['EvidenceBundle']['regions'])
    expected_bindings=copy.deepcopy(old_d['bindings'])
    expected_manifest=[]
    for block,label in LABELS.items():
        binding=old_bindings[block];region=old_regions[binding['region_id']];proof=old_proofs[binding['region_id']]
        runs=copy.deepcopy(binding['runs']);runs[0]['text']=label+runs[0]['text']
        expected_manifest.append(dict(operation='RESTORE_PRINTED_SUBQUESTION_LABEL',block_id=block,region_id=binding['region_id'],
            prefix=label,before_text=region['text'],after_text=label+region['text'],before_runs=binding['runs'],after_runs=runs,
            asset_id=region['box']['image']['asset_id'],source_sha256=region['box']['image']['sha256'],bbox=region['box']['bbox'],
            crop_path=proof['path'],crop_png_sha256=proof['sha256'],crop_rgb_sha256=proof['rgb_sha256']))
        next(r for r in expected_regions if r['region_id']==binding['region_id'])['text']=label+region['text']
        next(b for b in expected_bindings if b['block_id']==block)['runs']=runs
    check('three_label_records_exact_before_after_and_source_proof',changes==expected_manifest,diff(expected_manifest,changes))
    # The separately authorized source-confirmation phase changes certainty,
    # never the region's content, geometry, type, order or original-image binding.
    for region in expected_regions:region['certainty']='CONFIRMED'
    check('all_regions_equal_except_three_labels_and_source_certainty',after['EvidenceBundle']['regions']==expected_regions,diff(expected_regions,after['EvidenceBundle']['regions']))
    check('source_confirmation_covers_exact_original_region_ids',review.get('confirmed_region_ids')==list(old_regions))
    check('only_three_bound_run_prefixes_changed',new_d['bindings']==expected_bindings,diff(expected_bindings,new_d['bindings']))
    for name in ['source_proofs','q16_task_map','q16_formula_slots','reading_task_answers']:
        check('unchanged_'+name,old_d[name]==new_d[name],diff(old_d[name],new_d[name]))
    check('historical_basis_complete_object_unchanged',old['sidecars']['basis.json']==new['sidecars']['basis.json'])
    check('shared_and_active_fragments_complete_object_unchanged',before['QuestionGraph']['fragments']==after['QuestionGraph']['fragments'])
    q16=next(q['question_id'] for q in before['QuestionGraph']['questions'] if q['external_refs']['printed_number']=='16')
    routing={q['question_id']:('b-section2-local' if q['question_id']==q16 else 'b-reading-local') for q in before['QuestionGraph']['questions']}
    expected_questions=copy.deepcopy(before['QuestionGraph']['questions'])
    for q in expected_questions:q['directory_id']=routing[q['question_id']]
    check('questions_identical_except_explicit_independent_local_directories',after['QuestionGraph']['questions']==expected_questions,diff(expected_questions,after['QuestionGraph']['questions']))
    check('current_review_routes_q16_separately_from_three_reading_tasks',review.get('question_directories')==routing)
    expected_relations=copy.deepcopy(before['QuestionGraph']['answer_relations'])
    for relation in expected_relations:
        relation['status']='SELECTED';relation['selected_fragment_ids']=list(relation['candidate_fragment_ids'])
    check('four_relations_only_authorized_selected_transition',after['QuestionGraph']['answer_relations']==expected_relations,diff(expected_relations,after['QuestionGraph']['answer_relations']))
    confirmations=review.get('answer_confirmations',[])
    check('four_explicit_B_source_confirmations',len(confirmations)==4 and len({c['question_id'] for c in confirmations})==4)
    for relation in expected_relations:
        row=next((c for c in confirmations if c['question_id']==relation['question_id']),{})
        check('source_confirmed_own_selected_answers_'+relation['question_id'],row.get('selected_fragment_ids')==relation['selected_fragment_ids'] and row.get('disposition')=='B_MODEL_SOURCE_CONFIRMED' and bool(row.get('source_reason')))
    check('original_source_payload_unchanged_except_routing_and_history',
        {k:v for k,v in before['SourceBundle'].items() if k not in ['directories','external_page_mappings','history']}==
        {k:v for k,v in after['SourceBundle'].items() if k not in ['directories','external_page_mappings','history']})
    expected_dirs=[dict(directory_id='chapter1-local',parent_id=None,label='第一章 勾股定理'),
        dict(directory_id='b-reading-local',parent_id='chapter1-local',label='漫话勾股世界——教材P6阅读·思考变式'),
        dict(directory_id='b-section2-local',parent_id='chapter1-local',label='2 一定是直角三角形吗')]
    check('independent_local_directories_source_bound',after['SourceBundle']['directories']==review.get('local_directories')==expected_dirs)
    asset_routes={'viewer-13':'b-reading-local','viewer-15':'b-section2-local','viewer-173':'chapter1-local'}
    expected_mappings=copy.deepcopy(before['SourceBundle']['external_page_mappings'])
    for row in expected_mappings:row['directory_id']=asset_routes[row['asset_id']];row['mapping_status']='CONFIRMED'
    check('page_mappings_only_source_confirmed_local_routing',after['SourceBundle']['external_page_mappings']==expected_mappings and review.get('asset_directories')==asset_routes)
    check('original_image_hashes_bound_to_current_review',review.get('source_asset_sha256')=={a['asset_id']:a['sha256'] for a in before['SourceBundle']['assets']})
    check('coverage_clues_unchanged',before['EvidenceBundle']['coverage_clues']==after['EvidenceBundle']['coverage_clues'])
    check('no_human_or_platform_acceptance',review.get('review_kind')=='B_MODEL_SOURCE_CONFIRMED' and review.get('human_verified') is False and review.get('a_owner_acceptance') is False and review.get('independent_human_acceptance') is False and review.get('platform_requests')==0 and review.get('planning_or_dispatch') is False)
    return dict(status='SOURCE_CONFIRMED_WITH_EXACT_THREE_LABEL_TEXT_DELTA' if all(c['passed'] for c in checks) else 'Q16_LABEL_SOURCE_DELTA_REJECTED',
        checks=checks,source_bindings=expected_manifest,
        unauthorized_delta=[c for c in checks if not c['passed']],
        comparison_basis='Immutable historical v2; discarded intermediate draft was not consumed. Only labels change source text/runs; authorized B confirmation/routing are audited separately.',
        actual_new_package_consumed=False,platform_requests=0,dispatch=False)
