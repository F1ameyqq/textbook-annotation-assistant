"""Independent source freeze and C01 audit for section 2 Q1-Q15.

Raw/native source records remain in the caller's private work directory. Public
summaries contain counts, local logical identities and hashes, never raw inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
import zipfile

sha=lambda raw:hashlib.sha256(raw).hexdigest()
canonical=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
EXPECTED_COUNTS=dict(items=15,question=16,choice=28,diagram=5,answer=16,regions=65,blanks=5)
ITEM_FIELDS=['item_key','printed_number','question_type','question_text','choices','answer_text','analysis_text',
    'question_region_ids_in_reading_order','diagram_region_ids','answer_region_ids_in_reading_order',
    'blank_slots','intentional_wrong_solution_in_question','source_flow_note']
REGION_FIELDS=['region_id','item_key','viewer_page','role','bbox','source_image_sha256','source_dimensions','crop','model_reviewed_text']


def read(path):
    def unique(pairs):
        out={}
        for key,value in pairs:
            if key in out:raise ValueError('DUPLICATE_JSON_KEY')
            out[key]=value
        return out
    return json.loads(Path(path).read_bytes(),object_pairs_hook=unique)


def write(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)


def safe_name(name):
    if not isinstance(name,str) or not name or any(c in name for c in ['\\',':','\0']) or name.startswith('/') or any(p in ['','.','..'] for p in name.split('/')):
        raise ValueError('UNSAFE_PACKAGE_MEMBER')
    return name


def extract_source(archive,digest,target):
    if sha(archive.read_bytes())!=digest:raise ValueError('SOURCE_ARCHIVE_SHA256_MISMATCH')
    target.mkdir(parents=True,exist_ok=False);names=set()
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            name=safe_name(member.filename)
            if name.casefold() in names or stat.S_ISLNK(member.external_attr>>16):raise ValueError('DUPLICATE_OR_SYMLINK_MEMBER')
            names.add(name.casefold());file=(target/name).resolve()
            if not file.is_relative_to(target.resolve()):raise ValueError('SOURCE_PATH_ESCAPE')
            file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(z.read(member))
    manifest=read(target/'file-manifest.json');members=manifest['files']
    listed=[safe_name(m['relative_path']) for m in members]
    if len(listed)!=len(set(listed)):raise ValueError('DUPLICATE_SOURCE_MANIFEST_MEMBER')
    actual={p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}
    if actual!=set(listed)|{'file-manifest.json'}:raise ValueError('SOURCE_MANIFEST_INVENTORY_DIFFERS')
    for member in members:
        raw=(target/member['relative_path']).read_bytes()
        if len(raw)!=member['bytes'] or sha(raw)!=member['sha256']:raise ValueError('SOURCE_MEMBER_BYTES_CHANGED')
    return len(actual),len(members)


def freeze_expectations(source):
    if source['book_id']!='46007447' or source['section_title']!='2 一定是直角三角形吗':raise ValueError('WRONG_SOURCE_SCOPE')
    items=[{k:item[k] for k in ITEM_FIELDS} for item in source['items']]
    regions=[{k:region[k] for k in REGION_FIELDS} for region in source['regions']]
    assets=[dict(asset_id='viewer-'+str(s['viewer_page']),viewer_page=s['viewer_page'],dimensions=s['dimensions'],
        relative_path=s['image']['relative_path'],sha256=s['image']['sha256']) for s in source['sources']]
    counts={role:sum(r['role']==role for r in regions) for role in ['question','choice','diagram','answer']}
    counts.update(items=len(items),regions=len(regions),blanks=sum(len(i['blank_slots']) for i in items))
    if counts!=EXPECTED_COUNTS:raise ValueError('NEW_SECTION_SOURCE_COUNTS_DIFFER')
    types={kind:sum(i['question_type']==kind for i in items) for kind in ['single_choice','fill_blank','free_response']}
    if types!=dict(single_choice=7,fill_blank=5,free_response=3):raise ValueError('NEW_SECTION_SOURCE_QUESTION_TYPES_DIFFER')
    if [i['item_key'] for i in items]!=['section2-q'+str(i) for i in range(1,16)] or [i['printed_number'] for i in items]!=list(range(1,16)):
        raise ValueError('FIFTEEN_UNIQUE_ORDERED_IDENTITIES_REQUIRED')
    if len({r['region_id'] for r in regions})!=65:raise ValueError('DUPLICATE_REGION_IDENTITY')
    inventory={r['region_id']:r for r in regions};used=[]
    for item in items:
        groups=[('question',item['question_region_ids_in_reading_order']),('choice',[c['region_id'] for c in item['choices']]),
            ('diagram',item['diagram_region_ids']),('answer',item['answer_region_ids_in_reading_order'])]
        for role,ids in groups:
            for rid in ids:
                if rid not in inventory or inventory[rid]['item_key']!=item['item_key'] or inventory[rid]['role']!=role:raise ValueError('SOURCE_ROLE_OR_OWNER_CONFLICT')
                used.append(rid)
        if item['choices'] and [c['label'] for c in item['choices']]!=list('ABCD'):raise ValueError('FOUR_INDEPENDENT_OPTIONS_REQUIRED')
        if any(b['value'] is not None for b in item['blank_slots']):raise ValueError('SOURCE_QUESTION_BLANK_ALREADY_FILLED')
        if item['analysis_text'] is not None:raise ValueError('UNEXPECTED_INVENTED_SEPARATE_ANALYSIS')
    if len(used)!=65 or set(used)!=set(inventory):raise ValueError('SOURCE_OMITTED_OR_DUPLICATE_PRIMARY_REGION')
    q7=items[6];q15=items[14]
    if q7['intentional_wrong_solution_in_question'] is not True or q7['question_region_ids_in_reading_order']!=['section2-q7.question.1','section2-q7.question.2']:
        raise ValueError('Q7_ERROR_AND_CROSS_COLUMN_FLOW_MUST_BE_FROZEN')
    if q15['answer_region_ids_in_reading_order']!=['section2-q15.answer.1','section2-q15.answer.2']:raise ValueError('Q15_CROSS_COLUMN_ANSWER_ORDER_MUST_BE_FROZEN')
    return dict(schema='BSection2PrivateExpectedContent/1',scope='section2-q1-q15',counts=counts,assets=assets,items=items,regions=regions,
        excluded=['section2-q16','adjacent-three-reading-tasks'],source_fields_retained=ITEM_FIELDS+REGION_FIELDS)


def audit_source_pixels(folder,expected):
    from PIL import Image
    assets={a['viewer_page']:a for a in expected['assets']};images={}
    for page,asset in assets.items():
        raw=(folder/asset['relative_path']).read_bytes()
        if sha(raw)!=asset['sha256']:raise ValueError('ORIGINAL_IMAGE_CHANGED')
        with Image.open(folder/asset['relative_path']) as im:
            if list(im.size)!=asset['dimensions']:raise ValueError('SOURCE_IMAGE_DIMENSIONS')
            images[page]=im.convert('RGB')
    checks=[]
    for region in expected['regions']:
        image=images[region['viewer_page']];box=region['bbox'];proof=region['crop']
        path=folder/safe_name(proof['relative_path']);raw=path.read_bytes()
        crop=image.crop(box)
        with Image.open(path) as im:actual=im.convert('RGB')
        passed=(region['source_image_sha256']==assets[region['viewer_page']]['sha256'] and
            0<=box[0]<box[2]<=image.width and 0<=box[1]<box[3]<=image.height and
            sha(raw)==proof['sha256'] and list(crop.size)==proof['dimensions']==list(actual.size) and
            crop.tobytes()==actual.tobytes() and sha(crop.tobytes())==proof['rgb_sha256'])
        checks.append(dict(region_id=region['region_id'],passed=passed))
    if any(not c['passed'] for c in checks):raise ValueError('SOURCE_CROP_PIXELS_DIFFER')
    return checks


def freeze(args):
    args.out.mkdir(parents=True,exist_ok=False)
    source=args.out/'private-source';members,listed=extract_source(args.source_zip,args.source_sha256,source)
    expected=freeze_expectations(read(source/'source-spec.json'))
    checks=audit_source_pixels(source,expected)
    expected['source_archive_sha256']=args.source_sha256
    expected['source_spec_sha256']=sha((source/'source-spec.json').read_bytes())
    write(args.out/'private-expectations.json',expected)
    q7=expected['items'][6];q15=expected['items'][14]
    public=dict(schema='BSection2FrozenConsumerExpectations/1',status='SOURCE_EXPECTATIONS_FROZEN_C01_NOT_YET_CONSUMED',scope=expected['scope'],
        source_archive_sha256=args.source_sha256,source_spec_sha256=expected['source_spec_sha256'],
        private_expectations_sha256=sha((args.out/'private-expectations.json').read_bytes()),members=members,manifest_members=listed,
        counts=expected['counts'],source_pixel_checks=checks,
        item_text_fingerprints=[dict(item_key=i['item_key'],question_sha256=sha(i['question_text'].encode()),answer_sha256=sha(i['answer_text'].encode()),
            option_count=len(i['choices']),diagram_count=len(i['diagram_region_ids']),answer_segment_count=len(i['answer_region_ids_in_reading_order'])) for i in expected['items']],
        special_preservation=dict(q7_original_wrong_solution_must_remain_in_question=True,q7_question_region_order=q7['question_region_ids_in_reading_order'],
            q7_question_sha256=sha(q7['question_text'].encode()),q7_answer_kept_separate=True,q15_answer_region_order=q15['answer_region_ids_in_reading_order'],
            q15_answer_sha256=sha(q15['answer_text'].encode())),
        excluded=expected['excluded'],raw_native_records_or_personal_paths_exported=False,
        actual_C01_consumed=False,platform_requests=0,new_OCR_calls=0,dispatch=False,human_acceptance=False,a_owner_acceptance=False)
    write(args.out/'public-source-freeze.json',public)
    print(json.dumps({k:public[k] for k in ['status','scope','source_archive_sha256','counts','raw_native_records_or_personal_paths_exported']}))


def expected_latex(token):
    match=re.fullmatch(r'([0-9]+)/([0-9]+)',token)
    if match:return '\\frac{'+match[1]+'}{'+match[2]+'}'
    match=re.fullmatch(r'√([0-9]+)',token)
    if match:return '\\sqrt{'+match[1]+'}'
    match=re.fullmatch(r'([A-Za-z0-9]+)²',token)
    if match:return match[1]+'^{2}'
    match=re.fullmatch(r'([A-Za-z]+)([₀₁₂₃₄₅₆₇₈₉]+)',token)
    if match:return match[1]+'_{'+match[2].translate(str.maketrans('₀₁₂₃₄₅₆₇₈₉','0123456789'))+'}'
    raise ValueError('UNSUPPORTED_SOURCE_MATH_TOKEN')


def audit_loaded(expected,bundle,basis,sidecar):
    """Audit source ownership, exact plain text, rich math, blanks and flow.

    Details expose hashes instead of source text, raw records or local paths.
    """
    checks=[]
    def check(name,passed,want=None,got=None):
        detail=None if want is None and got is None else dict(expected_sha256=sha(canonical(want)),actual_sha256=sha(canonical(got)))
        checks.append(dict(check=name,passed=bool(passed),detail=detail))
    artifacts={a['kind']:a for a in bundle['artifacts']};parts={k:a['payload'] for k,a in artifacts.items()}
    check('this_batch_four_content_artifacts_only',len(bundle['artifacts'])==4 and set(parts)=={'SourceBundle','EvidenceBundle','QuestionGraph','CheckReport'})
    source=parts['SourceBundle'];ev=parts['EvidenceBundle'];graph=parts['QuestionGraph']
    regions={r['region_id']:r for r in ev['regions']};fragments={f['fragment_id']:f for f in graph['fragments']}
    wanted={r['region_id']:r for r in expected['regions']};items={i['item_key']:i for i in expected['items']}
    geometry=lambda r:(r['source_image_sha256'],tuple(r['source_dimensions']),tuple(r['bbox']))
    source_geo={geometry(r):r['region_id'] for r in expected['regions']}
    mapping={};seen=[]
    check('exact_65_source_regions',len(ev['regions'])==65 and len(regions)==65)
    for rid,region in regions.items():
        image=region['box']['image'];key=(image['sha256'],(image['width'],image['height']),tuple(region['box']['bbox']))
        original=source_geo.get(key);check('original_geometry_binding_'+rid,original is not None)
        if original is not None:mapping[rid]=original;seen.append(original)
    check('every_frozen_region_bound_once',len(seen)==65 and len(set(seen))==65 and set(seen)==set(wanted))
    if len(mapping)!=len(regions) or len(seen)!=65 or len(set(seen))!=65 or set(seen)!=set(wanted):
        return dict(status='SOURCE_GEOMETRY_MAPPING_REJECTED',checks=checks,failures=[c for c in checks if not c['passed']],
            counts=dict(questions=len(graph['questions']),regions=len(regions),fragments=len(fragments),options=None,diagrams=None,
                answer_segments=None,math_runs=None,null_blanks=None))
    source_to_c01={sid:rid for rid,sid in mapping.items()}
    blocks={b['original_region_id']:b for b in basis['blocks']}
    bindings={b['block_id']:b for b in sidecar['bindings']}
    check('exact65_original_blocks',len(basis['blocks'])==65 and set(blocks)==set(wanted))
    projection=basis['source_projection']
    check('independent_frozen_source_archive_sha',projection['original_archive_sha256']==expected['source_archive_sha256'])
    check('independent_frozen_source_spec_sha',projection['original_source_spec_sha256']==expected['source_spec_sha256'])
    projected_items=[{k:i[k] for k in ITEM_FIELDS} for i in projection['source_items']]
    projected_regions=[{k:r[k] for k in REGION_FIELDS} for r in projection['regions']]
    check('all_frozen_item_fields_retained',projected_items==expected['items'],expected['items'],projected_items)
    check('all_frozen_region_fields_retained',projected_regions==expected['regions'],expected['regions'],projected_regions)
    assets={a['asset_id']:a for a in source['assets']}
    check('three_original_assets',len(assets)==3 and {a['sha256'] for a in assets.values()}=={a['sha256'] for a in expected['assets']})
    math_count=0;blank_runs=[]
    role_map={'question':'stem','choice':'option','diagram':'stem','answer':'answer'}
    for sid,want in wanted.items():
        rid=source_to_c01[sid];region=regions[rid];block=blocks[sid];binding=bindings[block['block_id']]
        check('block_original_geometry_'+sid,block['item_key']==want['item_key'] and block['bbox']==want['bbox'] and block['original_crop_sha256']==want['crop']['sha256'] and block['original_crop_rgb_sha256']==want['crop']['rgb_sha256'])
        check('block_source_role_'+sid,block['role']==role_map[want['role']] and binding['role']==role_map[want['role']] and binding['item_key']==want['item_key'])
        check('bound_C01_region_'+sid,binding['region_id']==rid and region['content_type']==('image' if want['role']=='diagram' else 'text') and region['text']==block['text'])
        check('rich_runs_identical_in_binding_'+sid,binding['runs']==block['rich_runs'])
        reconstructed=[]
        for index,run in enumerate(binding['runs']):
            if run['format']=='plain':reconstructed.append(run['text'])
            elif run['format']=='latex':
                token=run.get('source_text');valid=False
                if isinstance(token,str):
                    try:valid=run['text']==expected_latex(token)
                    except ValueError:valid=False
                check('independent_latex_source_equivalence_'+sid+'_'+str(index),valid)
                reconstructed.append(token or '');math_count+=1
            elif run['format']=='blank':
                check('blank_still_null_'+sid,run.get('value','MISSING') is None)
                reconstructed.append(run['token']);blank_runs.append(run)
            else:check('supported_rich_run_'+sid,False)
        check('rich_runs_reconstruct_frozen_plain_text_'+sid,''.join(reconstructed)==(block['text'] or ''))
        if want['model_reviewed_text'] is not None:
            exact=block['text']==want['model_reviewed_text']
            # The first three independent options may carry one display-only
            # newline so their concatenation preserves the original choice list.
            separator=(want['role']=='choice' and any(c['region_id']==sid for c in items[want['item_key']]['choices'][:-1]) and block['text']==want['model_reviewed_text']+'\n')
            check('regional_reviewed_text_'+sid,exact or separator,want['model_reviewed_text'],block['text'])
        check('fragment_region_and_role_'+sid,binding['fragment_id'] in fragments and fragments[binding['fragment_id']]['region_ids']==[rid] and fragments[binding['fragment_id']]['role']==role_map[want['role']])
    check('exact_five_blank_ids',[r.get('blank_id') for r in blank_runs]==[b['blank_id'] for i in expected['items'] for b in i['blank_slots']] and len(blank_runs)==5)
    graph_owners={};used=[]
    by_item={i['item_key']:i for i in basis['items']}
    check('exact15_graph_questions',len(graph['questions'])==15 and len({q['question_id'] for q in graph['questions']})==15)
    check('no_reading_shared_material_in_this_batch',all(not q['shared_fragment_ids'] for q in graph['questions']))
    def unroll(ids):return [mapping[rid] for fid in ids for rid in fragments[fid]['region_ids']]
    for q in graph['questions']:
        identities=unroll(q['fragment_ids']);owners={wanted[sid]['item_key'] for sid in identities}
        check('one_frozen_owner_'+q['question_id'],len(owners)==1)
        if len(owners)!=1:continue
        owner=next(iter(owners));item=items[owner];graph_owners[q['question_id']]=owner;used.extend(q['fragment_ids'])
        check('printed_number_scope_'+owner,q['external_refs']['printed_number']==str(item['printed_number']) and q['external_refs']['platform_question_id'] is None and q['external_refs']['platform_order'] is None)
        check('question_type_'+owner,q['question_type']==('ordinary_choice' if item['question_type']=='single_choice' else 'free_response'))
        for role,desired in [('question',item['question_region_ids_in_reading_order']),('choice',[c['region_id'] for c in item['choices']]),('diagram',item['diagram_region_ids'])]:
            actual=[sid for sid in identities if wanted[sid]['role']==role]
            check('ordered_'+role+'_regions_'+owner,actual==desired,desired,actual)
        actual_question=''.join(regions[source_to_c01[sid]]['text'] for sid in identities if wanted[sid]['role']=='question')
        check('complete_original_question_text_'+owner,actual_question==item['question_text'],item['question_text'],actual_question)
        original=by_item[owner]
        expected_fields=dict(question=item['question_text'],choice='\n'.join(c['text'] for c in item['choices']) if item['choices'] else None,answer=item['answer_text'],analysis=None)
        check('all_item_fields_'+owner,original['fields']==expected_fields,expected_fields,original['fields'])
        check('source_blank_and_wrong_solution_flags_'+owner,original['blank_slots']==item['blank_slots'] and original['intentional_wrong_solution_in_question']==item['intentional_wrong_solution_in_question'])
        q_pages={wanted[sid]['viewer_page'] for sid in identities}
        check('cross_column_is_not_cross_page_'+owner,q['cross_page']==(len(q_pages)>1))
    check('all15_source_items_owned_once',len(graph_owners)==15 and len(set(graph_owners.values()))==15 and set(graph_owners.values())==set(items))
    check('exact15_answer_relations',len(graph['answer_relations'])==15 and {r['question_id'] for r in graph['answer_relations']}==set(graph_owners))
    answer_segments=0
    for relation in graph['answer_relations']:
        owner=graph_owners.get(relation['question_id'])
        if owner is None:continue
        item=items[owner];actual=unroll(relation['selected_fragment_ids']);used.extend(relation['selected_fragment_ids']);answer_segments+=len(actual)
        check('selected_own_answer_segments_'+owner,relation['status']=='SELECTED' and relation['candidate_fragment_ids']==relation['selected_fragment_ids'] and actual==item['answer_region_ids_in_reading_order'],item['answer_region_ids_in_reading_order'],actual)
        check('answer_roles_'+owner,all(fragments[f]['role']=='answer' for f in relation['selected_fragment_ids']))
        answer=''.join(regions[source_to_c01[sid]]['text'] for sid in actual)
        check('complete_original_answer_text_'+owner,answer==item['answer_text'],item['answer_text'],answer)
    check('exact16_answer_segments',answer_segments==16)
    check('no_orphan_or_reused_fragment',len(used)==len(set(used))==len(fragments) and set(used)==set(fragments))
    check('exact28_option_fragments',sum(f['role']=='option' for f in fragments.values())==28)
    check('exact5_image_regions',sum(r['content_type']=='image' for r in regions.values())==5)
    check('B_ready_separate_from_policy_coverage',sidecar['b_content_ready'] is True and sidecar['b_content_issues']==[] and parts['CheckReport']['decision']=='HOLD')
    return dict(status='SECTION2_FROZEN_SOURCE_C01_MAPPING_PASS' if all(c['passed'] for c in checks) else 'SECTION2_FROZEN_SOURCE_C01_MAPPING_REVIEW_REQUIRED',
        checks=checks,failures=[c for c in checks if not c['passed']],counts=dict(questions=len(graph['questions']),regions=len(regions),fragments=len(fragments),
            options=sum(f['role']=='option' for f in fragments.values()),diagrams=sum(r['content_type']=='image' for r in regions.values()),answer_segments=answer_segments,
            math_runs=math_count,null_blanks=len(blank_runs)),
        source_archive_sha256=expected['source_archive_sha256'],raw_native_records_or_personal_paths_exported=False,
        platform_requests=0,new_OCR_calls=0,dispatch=False,a_owner_acceptance=False,human_acceptance=False)


def consume(args):
    expected_file=args.frozen/'private-expectations.json';public=read(args.frozen/'public-source-freeze.json')
    if sha(expected_file.read_bytes())!=public['private_expectations_sha256']:raise ValueError('INDEPENDENT_SOURCE_EXPECTATIONS_CHANGED')
    expected=read(expected_file)
    if sha(args.bundle.read_bytes())!=args.bundle_sha256:raise ValueError('FIXED_NEW_BUNDLE_SHA256_MISMATCH')
    if args.out.resolve().is_relative_to(args.frozen.resolve()) or args.out.resolve().is_relative_to(args.bundle.parent.resolve()):raise ValueError('OUTPUT_MUST_NOT_MODIFY_SOURCE_OR_DELIVERY')
    args.out.mkdir(parents=True,exist_ok=False)
    receipt=args.out/'private-full-readback.json'
    command=[sys.executable,'-B','-X','utf8',str(args.consumer.resolve()),'--a-source',str(args.a_source.resolve()),'--pins',str(args.pins.resolve()),
        '--pins-sha256',args.pins_sha256,'--bundle',str(args.bundle.resolve()),'--expected-questions','15','--out',str(receipt.resolve())]
    result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
    (args.out/'private-fixed-a24-read.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:
        report=dict(status='FIXED_A24_NEW_SECTION2_REJECTED',exit_code=result.returncode,actual_C01_consumed=False,success_receipt_created=receipt.exists(),raw_error_exposed=False)
        write(args.out/'public-consumption.json',report);return 1
    got=read(receipt)
    if got['bundle_sha256']!=args.bundle_sha256 or sha(args.bundle.read_bytes())!=args.bundle_sha256:raise ValueError('BUNDLE_CHANGED_DURING_READ')
    folder=args.bundle.parent;basis=read(folder/'basis.json');sidecar=read(folder/'delivery.json')
    report=audit_loaded(expected,got['full_object'],basis,sidecar)
    resource_checks=audit_delivery_resources(folder,expected,got['full_object'],sidecar)
    report['checks'].extend(resource_checks)
    report['failures']=[c for c in report['checks'] if not c['passed']]
    report['status']='SECTION2_FROZEN_SOURCE_C01_MAPPING_PASS' if not report['failures'] else 'SECTION2_FROZEN_SOURCE_C01_MAPPING_REVIEW_REQUIRED'
    report.update(bundle_sha256=got['bundle_sha256'],complete_object_sha256=got['complete_object_sha256'],complete_object_equal=got['complete_object_equal'],
        a_commit=got['a_commit'],actual_C01_consumed=True,final_container_bound=False)
    write(args.out/'public-consumption.json',report)
    print(json.dumps({k:report[k] for k in ['status','bundle_sha256','counts','failures']}))
    return 0 if not report['failures'] else 2


def audit_delivery_resources(folder,expected,bundle,sidecar):
    from PIL import Image
    folder=Path(folder).resolve();parts={a['kind']:a['payload'] for a in bundle['artifacts']}
    regions={r['region_id']:r for r in parts['EvidenceBundle']['regions']}
    assets={a['asset_id']:a for a in parts['SourceBundle']['assets']}
    geom=lambda r:(r['source_image_sha256'],tuple(r['bbox']))
    original={geom(r):r for r in expected['regions']};checks=[]
    def local(name):
        path=(folder/safe_name(name)).resolve()
        if not path.is_relative_to(folder):raise ValueError('DELIVERY_RESOURCE_PATH_ESCAPE')
        return path
    for a in assets.values():
        checks.append(dict(check='original_JPEG_bytes_'+a['asset_id'],passed=sha(local(a['path']).read_bytes())==a['sha256'],detail=None))
    for proof in sidecar['source_proofs']:
        region=regions[proof['region_id']];box=region['box'];asset=assets[box['image']['asset_id']]
        want=original.get((box['image']['sha256'],tuple(box['bbox'])))
        path=local(proof['path']);raw=path.read_bytes()
        with Image.open(local(asset['path'])) as im:source=im.convert('RGB')
        with Image.open(path) as im:actual=im.convert('RGB')
        crop=source.crop(tuple(int(v) for v in box['bbox']))
        passed=(want is not None and sha(raw)==proof['sha256']==want['crop']['sha256'] and
            sha(crop.tobytes())==proof['rgb_sha256']==want['crop']['rgb_sha256'] and crop.size==actual.size and crop.tobytes()==actual.tobytes())
        checks.append(dict(check='frozen_original_PNG_and_pixels_'+proof['region_id'],passed=passed,detail=None))
    checks.append(dict(check='exact65_unique_crop_proofs',passed=len(sidecar['source_proofs'])==len({p['region_id'] for p in sidecar['source_proofs']})==65 and {p['region_id'] for p in sidecar['source_proofs']}==set(regions),detail=None))
    forbidden_keys={'user_id','userId','access_token','cookie','cookies','profile_path','raw_native_response','native_response'}
    private_paths=[]
    def privacy(value,path=''):
        if isinstance(value,dict):
            for k,v in value.items():
                here=path+'/'+k
                if k in forbidden_keys and v not in (None,False,'NOT_RUN'):private_paths.append(here)
                privacy(v,here)
        elif isinstance(value,list):
            for i,v in enumerate(value):privacy(v,path+'/'+str(i))
        elif isinstance(value,str) and re.search(r'(?:[A-Za-z]:[\\/]|/(?:Users|home)/)',value):private_paths.append(path)
    for file in folder.rglob('*.json'):privacy(read(file),file.relative_to(folder).as_posix())
    checks.append(dict(check='no_personal_paths_or_native_account_payload_in_JSON',passed=not private_paths,detail=dict(unsafe_field_count=len(private_paths))))
    return checks


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    f=sub.add_parser('freeze-source')
    f.add_argument('--source-zip',required=True,type=Path);f.add_argument('--source-sha256',required=True);f.add_argument('--out',required=True,type=Path)
    c=sub.add_parser('consume')
    for key in ['frozen','bundle','consumer','a-source','pins','out']:c.add_argument('--'+key,required=True,type=Path)
    c.add_argument('--bundle-sha256',required=True);c.add_argument('--pins-sha256',required=True)
    args=p.parse_args()
    return freeze(args) if args.mode=='freeze-source' else consume(args)


if __name__=='__main__':raise SystemExit(main())
