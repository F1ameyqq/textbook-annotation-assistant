"""Project frozen section-source facts into the existing private C01 exporter input.

Reads only local source-spec/assets/crops. Raw business metadata and absolute
paths are not copied. Cross-column text splits must be explicitly supplied.
"""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import re
from PIL import Image

sha=lambda b:hashlib.sha256(b).hexdigest()
encode=lambda x:(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')


def need(value,code):
    if not value:raise ValueError(code)


def resource(root,path):
    need(isinstance(path,str) and path and not path.startswith('/') and not any(c in path for c in (':','\\','\x00'))
         and all(x not in ('','.','..') for x in path.split('/')),'RELATIVE_SOURCE_RESOURCE')
    return root/path


def rich_runs(text,blank_ids):
    out=[];end=0;blank_index=0
    pattern=r'_{2,}|\d+/\d+|[A-Za-z0-9]+[²³⁴]|[A-Za-z]+[₁₂₃]|√\d+'
    for m in re.finditer(pattern,text):
        if m.start()>end:out.append(dict(format='plain',text=text[end:m.start()]))
        token=m[0]
        if token.startswith('_'):
            need(blank_index<len(blank_ids),'SOURCE_BLANK_ID_REQUIRED')
            out.append(dict(format='blank',token=token,value=None,blank_id=blank_ids[blank_index]));blank_index+=1
        else:
            if '/' in token:
                numerator,denominator=token.split('/');tex='\\frac{'+numerator+'}{'+denominator+'}'
            elif token.startswith('√'):tex='\\sqrt{'+token[1:]+'}'
            elif token[-1] in '²³⁴':tex=token[:-1]+'^{'+str('²³⁴'.index(token[-1])+2)+'}'
            else:tex=token[:-1]+'_{'+str('₁₂₃'.index(token[-1])+1)+'}'
            out.append(dict(format='latex',text=tex,source_text=token))
        end=m.end()
    if end<len(text):out.append(dict(format='plain',text=text[end:]))
    need(blank_index==len(blank_ids),'SOURCE_BLANK_COUNT')
    return out


def project(spec,root,split_evidence,archive_sha256,manifest_sha256):
    root=Path(root)
    need(re.fullmatch(r'[0-9a-f]{64}',archive_sha256) and sha((root/'file-manifest.json').read_bytes())==manifest_sha256,'FROZEN_SOURCE_MANIFEST_HASH')
    need(spec['schema']=='Section2Q1Q15CompleteSourceSpec/v1' and spec['item_count']==len(spec['items']) and
         spec['unresolved_source_uncertainties']==[],'FROZEN_SOURCE_SPEC_REQUIRED')
    assets=[];images={};page_sources={};portable_sources=[]
    for source in spec['sources']:
        image=source['image'];aid='viewer-'+str(source['viewer_page']);raw=resource(root,image['relative_path']).read_bytes()
        need(sha(raw)==image['sha256'] and len(raw)==image['bytes'],'SOURCE_IMAGE_BYTES')
        with Image.open(io.BytesIO(raw)) as im:need(list(im.size)==source['dimensions'],'SOURCE_IMAGE_DIMENSIONS')
        for key in ('existing_OCR','native_metadata'):
            observation=source[key]
            if observation.get('relative_path'):
                need(sha(resource(root,observation['relative_path']).read_bytes())==observation['sha256'],'ORIGINAL_OBSERVATION_HASH')
        assets.append(dict(asset_id=aid,viewer_page=source['viewer_page'],path=str(resource(root,image['relative_path'])),
                           sha256=image['sha256'],width=source['dimensions'][0],height=source['dimensions'][1]))
        images[aid]=raw;page_sources[source['viewer_page']]=source
        portable_sources.append(dict(asset_id=aid,viewer_page=source['viewer_page'],printed_page_label=source['printed_page_label'],
            dimensions=source['dimensions'],image_sha256=image['sha256'],original_ocr_sha256=source['existing_OCR']['sha256'],
            original_native_metadata_sha256=source['native_metadata']['sha256'],original_observation_kind=source['existing_OCR']['observation']))
    regions={r['region_id']:r for r in spec['regions']}
    need(len(regions)==len(spec['regions']),'UNIQUE_SOURCE_REGIONS')
    blocks=[];items=[];portable_regions=[];used=[]
    for r in spec['regions']:
        src=page_sources[r['viewer_page']];aid='viewer-'+str(r['viewer_page']);box=r['bbox'];proof=r['crop']
        need(r['source_image_sha256']==src['image']['sha256'] and r['source_dimensions']==src['dimensions']
             and len(box)==4 and all(type(v) is int for v in box) and 0<=box[0]<box[2]<=src['dimensions'][0]
             and 0<=box[1]<box[3]<=src['dimensions'][1],'SOURCE_REGION_COORDINATES')
        crop_raw=resource(root,proof['relative_path']).read_bytes()
        with Image.open(io.BytesIO(images[aid])) as im:crop=im.convert('RGB').crop(box)
        with Image.open(io.BytesIO(crop_raw)) as saved:
            need(sha(crop_raw)==proof['sha256'] and list(crop.size)==proof['dimensions'] and saved.size==crop.size
                 and saved.convert('RGB').tobytes()==crop.tobytes() and sha(crop.tobytes())==proof['rgb_sha256'],'ORIGINAL_REGION_CROP_PIXELS')
        portable_regions.append(copy.deepcopy(r))
    for item in spec['items']:
        key=item['item_key'];need(item['unresolved_source_uncertainties']==[] and item['native_identity'] is None,'SOURCE_CONTENT_WITHOUT_NATIVE_IDENTITY')
        need(item['analysis_text'] is None,'NO_INVENTED_ANALYSIS')
        need(all(b['value'] is None for b in item['blank_slots']),'SOURCE_DECLARED_BLANKS_MUST_BE_NULL')
        fields=dict(question=item['question_text'],choice='\n'.join(c['text'] for c in item['choices']) if item['choices'] else None,
                    answer=item['answer_text'],analysis=None)
        items.append(dict(item_key=key,printed_number=str(item['printed_number']),parent_item_key=None,review_kind='B_MODEL_SOURCE_CONFIRMED',
            human_verified=False,fields=fields,source_question_type=item['question_type'],blank_slots=copy.deepcopy(item['blank_slots']),
            intentional_wrong_solution_in_question=item['intentional_wrong_solution_in_question'],source_flow_note=item['source_flow_note'],
            source_corrections=copy.deepcopy(item['model_corrections_against_existing_OCR'])))

        def add(rid,field,text,role,blank_ids=None):
            need(rid in regions and rid not in used,'SOURCE_REGION_SINGLE_OWNER')
            r=regions[rid];need(r['item_key']==key and r['role']==('diagram' if field=='figure' else field),'SOURCE_REGION_OWNER_ROLE')
            if r['model_reviewed_text'] is not None:need(r['model_reviewed_text']==(text.strip() if text is not None else None),'EXACT_PROVIDED_REGION_TEXT')
            block=dict(block_id=rid,item_key=key,asset_id='viewer-'+str(r['viewer_page']),bbox=r['bbox'],field=field,role=role,
                       text=text,content_type='image' if text is None else 'text',original_region_id=rid,
                       original_crop_sha256=r['crop']['sha256'],original_crop_rgb_sha256=r['crop']['rgb_sha256'])
            block['rich_runs']=rich_runs(text,blank_ids or []) if text is not None else []
            blocks.append(block);used.append(rid)

        for field,ids,value,role in (
            ('question',item['question_region_ids_in_reading_order'],item['question_text'],'stem'),
            ('answer',item['answer_region_ids_in_reading_order'],item['answer_text'],'answer')):
            if len(ids)==1:pieces=[value]
            else:
                evidence=split_evidence.get(key+'.'+field)
                need(evidence is not None and evidence['region_ids']==ids and evidence['original_full_text']==value,
                     'EXPLICIT_CROSS_COLUMN_SPLIT_REQUIRED:'+key+'.'+field)
                pieces=evidence['texts']
                need(len(pieces)==len(ids) and ''.join(pieces)==value and evidence['source_reason'],'LOSSLESS_SOURCE_BOUND_SPLIT')
            blanks=iter(item['blank_slots'] if field=='question' else [])
            for rid,text in zip(ids,pieces):
                block_blanks=[next(blanks)['blank_id'] for _ in re.finditer(r'_{2,}',text)]
                add(rid,field,text,role,block_blanks)
            need(next(blanks,None) is None,'ALL_SOURCE_BLANKS_BOUND')
        for index,choice in enumerate(item['choices']):
            need(choice['label']=='ABCD'[index] and len(item['choices'])==4,'FOUR_SOURCE_OPTIONS')
            add(choice['region_id'],'choice',choice['text']+('\n' if index<3 else ''),'option')
        for rid in item['diagram_region_ids']:add(rid,'figure',None,'stem')
    need(set(used)==set(regions) and len(used)==len(regions),'ALL_DECLARED_SOURCE_REGIONS_BOUND')
    raw_spec=(root/'source-spec.json').read_bytes()
    result=dict(schema='b-private-lesson-source-export-input/0.1',book_id=spec['book_id'],scope_id='section2-q1-q15',
        source_label=spec['section_title']+' / Q1–Q15',source_input_sha256=archive_sha256,root_review_sha256=sha(raw_spec),
        crop_manifest_sha256=manifest_sha256,review_kind='B_MODEL_SOURCE_CONFIRMED',assets=assets,items=items,blocks=blocks,exclusions=[],
        scope_notes=['Exactly section 2 Q1-Q15. Section 2 Q16 and the adjacent three reading tasks are excluded.',
        'B model source-confirmed answer ownership; joint platform policy and whole-page/full-chapter target readiness are separate PRE_APPLY limits.'],
        source_projection=dict(provenance='DERIVED_PORTABLE_EVIDENCE_NOT_ORIGINAL_HTTP_OR_ORIGINAL_SPEC_BYTES',
            original_archive_sha256=archive_sha256,original_source_spec_sha256=sha(raw_spec),original_file_manifest_sha256=manifest_sha256,
            sources=portable_sources,regions=portable_regions,source_items=[{k:copy.deepcopy(v) for k,v in i.items() if k not in
                ('native_identity','human_confirmation','A_acceptance','platform_acceptance','source_preview','status')} for i in spec['items']],
            source_transcription_convention=spec['source_transcription_convention'],cross_column_splits=copy.deepcopy(split_evidence),
            excluded_items=copy.deepcopy(spec['excluded_items']),new_OCR_calls=0,platform_requests=0))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--splits',type=Path,required=True)
    parser.add_argument('--archive-sha256',required=True);parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();spec=json.loads((args.source/'source-spec.json').read_bytes())
    output=project(spec,args.source,json.loads(args.splits.read_bytes()),args.archive_sha256,args.manifest_sha256)
    with args.out.open('xb') as stream:stream.write(encode(output))
    print(json.dumps(dict(items=len(output['items']),regions=len(output['blocks']),private_input_only=True)))


if __name__=='__main__':main()
