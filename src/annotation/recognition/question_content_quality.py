"""Independent question-content provenance audit; does not call the producer."""
import hashlib
import json
from pathlib import Path
import re
from PIL import Image
from .baseline import digest, load_source, file_digest, code_digest


def audit_question_content(source_path, evidence, graph, plan_path, application, *, expected_plan_sha256, crop_dir):
    def reference(v): return {k:v[k] for k in ('artifact_id','revision','content_hash')}
    def require(test, message):
        if not test: raise ValueError(message)
    def box(v): return isinstance(v,list) and len(v)==4 and all(type(n)is int for n in v) and 0<=v[0]<v[2]<=asset['width'] and 0<=v[1]<v[3]<=asset['height']
    def contains(a,b): return a[0]<=b[0]<b[2]<=a[2] and a[1]<=b[1]<b[3]<=a[3]
    def overlap(a,b): return max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])
    errors=[]
    try:
        raw=Path(plan_path).read_bytes()
        require(hashlib.sha256(raw).hexdigest()==expected_plan_sha256,'fixed plan file SHA mismatch')
        def unique(pairs):
            d={}
            for k,v in pairs:
                require(k not in d,'duplicate JSON key');d[k]=v
            return d
        plan=json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
        require(set(plan)=={'schema_version','content_hash','payload'} and plan['schema_version']=='b-question-source-draft-trial/0.1','unsupported plan')
        p=plan['payload'];a=application['payload']
        require(set(p)=={'book_id','asset_id','source_sha256','source_size','evidence_ref','graph_ref','baseline_ref','context_ref','evidence_artifact_sha256','graph_artifact_sha256','page_ocr_snapshot','source_ledger','author','questions','decision','human_verification','transcription_verified','business_acceptance','platform_actions'},'unknown plan fields')
        require(set(application)=={'schema_version','kind','book_id','scope_id','revision','content_hash','payload','artifact_id','producer'},'unknown application envelope')
        require(application['producer']=={'module':'annotation.recognition.question_content','code_sha256':code_digest(Path(__file__).with_name('question_content.py')),'baseline_code_sha256':code_digest(Path(__file__).with_name('baseline.py'))},'producer source version differs')
        require(set(a)=={'plan_file_sha256','plan_archive','evidence_ref','source_graph_archive','questions','source_ledger','crop_receipts','risks','decision','complete','human_verification','transcription_verified','business_acceptance','platform_actions','new_model_calls','answer_matching_performed','graph_projection_performed'},'unknown application fields')
        require(plan['content_hash']==digest(p),'plan payload mismatch')
        require(evidence['schema_version']=='b-evidence-trial/0.2' and graph['schema_version']=='b-graph-trial/0.2'and evidence['kind']=='EvidenceBundleTrial'and graph['kind']=='QuestionGraphTrial','base schema pair unsupported')
        for v in (evidence,graph,application):
            require(type(v['revision'])is int and v['revision']>0 and v['content_hash']==digest(v['payload']),'artifact corrupt')
        expected_keys={'artifact_id','book_id','content_hash','created_at','input_refs','kind','payload','producer','revision','run_id','schema_version','scope_id'}
        require(set(evidence)==set(graph)==expected_keys,'base envelope fields changed')
        context=evidence['payload']['context'];context_ref={'artifact_id':context['artifact_id'],'content_hash':digest(context)}
        require(digest(evidence)==p['evidence_artifact_sha256']and digest(graph)==p['graph_artifact_sha256'],'complete base envelope receipt differs')
        require(evidence['run_id']==graph['run_id']and graph['input_refs']==[reference(evidence)]and p['context_ref']==context_ref and evidence['input_refs']==[p['baseline_ref'],context_ref],'exact run/input references differ')
        require(application['schema_version']=='b-question-content-application-trial/0.1' and application['kind']=='QuestionContentApplicationTrial','application schema unsupported')
        require(application['artifact_id']=='question-content-application-'+digest({k:v for k,v in application.items()if k!='artifact_id'})[:24],'application identity mismatch')
        source,assets=load_source(Path(source_path));require(len(assets)==1,'single-page scope required')
        asset,path=assets[0];pages=evidence['payload']['pages'];require(len(pages)==1,'one evidence page required');page=pages[0]
        require(source['book_id']==p['book_id']==evidence['book_id']==graph['book_id']==application['book_id'],'book differs')
        require(source['scope_id']==evidence['scope_id']==graph['scope_id']==application['scope_id'],'scope differs')
        require(page['source']==asset and p['source_sha256']==asset['sha256'] and p['source_size']==[asset['width'],asset['height']] and p['asset_id']==asset['asset_id'],'source identity differs')
        require(p['evidence_ref']==reference(evidence) and p['graph_ref']==reference(graph) and p['baseline_ref']==evidence['input_refs'][0] and graph['input_refs'][0]==reference(evidence),'base references differ')
        require(p['page_ocr_snapshot']==page['ocr_lines'],'full OCR snapshot differs')
        require(a['plan_archive']==plan and a['plan_file_sha256']==expected_plan_sha256 and a['source_graph_archive']==graph and a['evidence_ref']==reference(evidence),'archive or fixed reference changed')
        require(a['questions']==p['questions'] and a['source_ledger']==p['source_ledger'],'draft projection changed')
        require(set(p['author'])=={'kind','id','note'}and p['author']['kind']=='MODEL_DRAFT','author is not model draft')
        for v in (p,a):
            require(v['decision']=='HOLD' and v['human_verification'] is False and v['transcription_verified'] is False and v['business_acceptance'] is False and v['platform_actions']==[],'approval flags promoted')
        require(a['complete'] is False and a['answer_matching_performed'] is False and a['graph_projection_performed'] is False and type(a['new_model_calls'])is int and a['new_model_calls']==0,'unsupported execution or completion claim')
        require(a['risks']==['MODEL_TRANSCRIPTION_UNVERIFIED','SOURCE_REGION_EXTENT_UNVERIFIED','FIGURE_EXTENT_UNVERIFIED','FORMULA_TRANSCRIPTION_UNVERIFIED','SECTION_IDENTITY_UNVERIFIED','ANSWER_MATCHING_NOT_PERFORMED','BUSINESS_REVIEW_REQUIRED'],'unresolved risks suppressed')
        originals=graph['payload']['questions']
        require(not graph['payload']['answers'] and all(not q['candidate_answer_ids'] and q['selected_answer_id']is None for q in originals),'unexpected answer matching')
        require([q['question_id']for q in p['questions']]==[q['question_id']for q in originals],'question identity/order changed')
        image=Image.open(path).convert('RGB');regions=[q['question_bbox']for q in p['questions']]
        require(all(box(b) and not any(overlap(b,c)for c in regions[i+1:]) for i,b in enumerate(regions)),'invalid question partition')
        claimed={};seen_blocks=set();seen_blanks=set();expected_receipts=[]
        for q,old in zip(p['questions'],originals):
            require(set(q)=={'question_id','printed_number','asset_id','source_question_sha256','question_bbox','blocks','counting_status','section_status','answer_link_status','source_ocr_snapshot','source_question_archive'},'unknown question fields')
            require(q['source_question_archive']==old and q['source_question_sha256']==digest(old) and q['printed_number']==old['printed_number'] and q['asset_id']==old['asset_id']==asset['asset_id'],'source question archive changed')
            require(q['counting_status']=='UNKNOWN' and q['section_status']=='INFERRED_UNVERIFIED' and q['answer_link_status']=='UNMATCHED','question status promoted')
            require(all(contains(q['question_bbox'],f['bbox'])for f in old['fragments']),'original fragment clipped')
            rows=[r for r in page['ocr_lines']if contains(q['question_bbox'],r['bbox'])]
            require(q['source_ocr_snapshot']==rows,'question OCR partition changed')
            for row in rows:
                require(row['line_id']not in claimed,'duplicate source ownership');claimed[row['line_id']]=q['question_id']
            blocks=q['blocks'];require(blocks and blocks[0]['role']=='stem','stem missing')
            labels=[b.get('label')for b in blocks if b['role']=='option']
            require(labels==[f['option_label']for f in old['fragments']if f.get('option_start')] and (not labels or labels==list('ABCD')),'option set/order differs')
            task_labels=[m.group(1)for r in rows if(m:=re.match(r'^[（(](\d+)[）)]',r['text']))]
            require([b.get('label')for b in blocks if b['role']=='task']==task_labels,'task anchors differ')
            require('如图'not in old['text']or any(b['role']=='figure'for b in blocks),'figure lost')
            for i,b in enumerate(blocks):
                allowed={'block_id','role','bbox','source_sha256','crop_rgb_sha256','verification_status','crop_png_sha256','crop_size','source_ocr_refs','content_origin'}
                if b['role']!='figure':allowed.add('runs')
                if b['role']in{'option','task'}:allowed.add('label')
                if b['role']=='task':allowed.add('parent_question_id')
                if 'fraction_components'in b:allowed.add('fraction_components')
                if 'editorial_badges'in b:allowed.add('editorial_badges')
                require(set(b)==allowed,'unknown block fields')
                bid=b['block_id'];region=b['bbox']
                require(isinstance(bid,str) and re.fullmatch(r'[A-Za-z0-9_-]+',bid) and bid not in seen_blocks,'block ID invalid');seen_blocks.add(bid)
                require(box(region) and contains(q['question_bbox'],region) and not any(overlap(region,c['bbox'])for c in blocks[i+1:]),'block geometry invalid')
                require(b['role']in{'stem','option','figure','task'} and b['source_sha256']==asset['sha256'] and b['verification_status']=='UNVERIFIED','block source/type/flags invalid')
                require(b['source_ocr_refs']==[r['line_id']for r in rows if contains(region,r['bbox'])],'block OCR binding differs')
                contained=[r for r in rows if r['line_id']in b['source_ocr_refs']]
                require(b['role']!='stem'or old['anchor_ref']in b['source_ocr_refs'],'stem original anchor missing')
                if b['role']=='option':require([m.group(1)for r in contained if(m:=re.match(r'^([A-D])[.．、]',r['text']))]==[b['label']],'option marker differs')
                if b['role']=='task':require([m.group(1)for r in contained if(m:=re.match(r'^[（(](\d+)[）)]',r['text']))]==[b['label']],'task marker differs')
                require(b['content_origin']==('SOURCE_PIXELS'if b['role']=='figure'else'MODEL_VISUAL_TRANSCRIPTION'),'origin changed')
                require(b['role']!='task'or b['parent_question_id']==q['question_id'],'task parent changed')
                for badge in b.get('editorial_badges',[]):
                    require(set(badge)=={'text','bbox','crop_rgb_sha256','disposition','verification_status'}and b['role']=='stem'and isinstance(badge['text'],str)and badge['text']and box(badge['bbox'])and contains(region,badge['bbox'])and badge['disposition']=='SOURCE_DECORATION_RETAINED'and badge['verification_status']=='UNVERIFIED'and hashlib.sha256(image.crop(badge['bbox']).tobytes()).hexdigest()==badge['crop_rgb_sha256'],'editorial badge invalid')
                crop=image.crop(region);rgb=hashlib.sha256(crop.tobytes()).hexdigest()
                require(rgb==b['crop_rgb_sha256'] and list(crop.size)==b['crop_size'],'actual source pixels differ')
                exported=Path(crop_dir)/(bid+'.png');require(exported.is_file(),'exported crop missing')
                with Image.open(exported)as saved:
                    require(saved.mode=='RGB'and saved.size==crop.size and saved.tobytes()==crop.tobytes(),'crop rescaled, altered or incomplete')
                require(file_digest(exported)==b['crop_png_sha256'],'exported bytes differ')
                require((b['role']=='figure'and not b.get('runs'))or(b['role']!='figure'and b.get('runs')),'figure/text representation mismatch')
                for run in b.get('runs',[]):
                    if run['format']=='blank':
                        require(set(run)=={'format','blank_id','bbox','response_kind','value'} and run['value']is None and run['blank_id']not in seen_blanks and box(run['bbox'])and contains(region,run['bbox'])and run['response_kind']in{'expression','single_choice'},'blank filled or invalid');seen_blanks.add(run['blank_id'])
                    else:require(set(run)=={'format','text'} and run['format']in{'plain','latex'}and isinstance(run['text'],str)and run['text'].strip(),'text run invalid')
                fractions=b.get('fraction_components',[])
                require(len(fractions)==sum(r.get('text','').count(r'\frac{')for r in b.get('runs',[])),'fraction component missing')
                ids=set();numerators=set()
                positions=[i for i,r in enumerate(b.get('runs',[]))if r.get('format')=='latex'and r'\frac{'in r.get('text','')]
                require([c.get('run_index')for c in fractions]==positions and all(type(c.get('run_index'))is int for c in fractions),'fraction run mapping differs')
                for fraction in fractions:
                    parts=fraction['parts']
                    require(set(fraction)=={'component_id','parts','verification_status','run_index'},'unknown fraction fields')
                    require(isinstance(fraction['component_id'],str)and fraction['component_id']and fraction['component_id']not in ids and isinstance(parts,list)and len(parts)==3,'duplicate or malformed fraction');ids.add(fraction['component_id'])
                    require(fraction['verification_status']=='UNVERIFIED'and[p['role']for p in parts]==['numerator','bar','denominator'],'fraction role mismatch')
                    require(parts[0]['bbox'][3]<=parts[1]['bbox'][1]and parts[1]['bbox'][3]<=parts[2]['bbox'][1],'fraction vertical order changed')
                    for part in parts:require(set(part)=={'role','bbox','crop_rgb_sha256','verification_status'}and box(part['bbox'])and contains(region,part['bbox'])and part['verification_status']=='UNVERIFIED'and hashlib.sha256(image.crop(part['bbox']).tobytes()).hexdigest()==part['crop_rgb_sha256'],'fraction pixel proof invalid')
                    require(tuple(parts[0]['bbox'])not in numerators,'source fraction duplicated');numerators.add(tuple(parts[0]['bbox']))
                groups=[]
                for component in sorted(fractions,key=lambda c:min(part['bbox'][1]for part in c['parts'])):
                    left=min(part['bbox'][0]for part in component['parts']);top=min(part['bbox'][1]for part in component['parts']);bottom=max(part['bbox'][3]for part in component['parts'])
                    if groups and max(top,groups[-1][0])<min(bottom,groups[-1][1]):
                        row=groups[-1];row[0]=max(row[0],top);row[1]=min(row[1],bottom);row[2].append((left,component['component_id']))
                    else:groups.append([top,bottom,[(left,component['component_id'])]])
                order=[id for row in groups for _,id in sorted(row[2])]
                require(order==[c['component_id']for c in fractions],'fraction source reading order differs')
                expected_receipts.append(dict(block_id=bid,relative_path=bid+'.png',source_bbox=region,rgb_sha256=rgb,file_sha256=file_digest(exported),size=list(crop.size),transform_to_source=[[1,0,region[0]],[0,1,region[1]],[0,0,1]]))
        ledger=[dict(line_id=r['line_id'],owner_question_id=claimed.get(r['line_id']),status='QUESTION_SOURCE'if r['line_id']in claimed else'COLUMN_HEADER_DECORATION'if r['bbox'][3]<=min(b[1]for b in regions)else'PAGE_FOOTER'if r['bbox'][1]>=max(b[3]for b in regions)else'UNASSIGNED')for r in page['ocr_lines']]
        require(not any(r['status']=='UNASSIGNED'for r in ledger),'unassigned body OCR')
        require(ledger==a['source_ledger']and expected_receipts==a['crop_receipts'],'ledger or receipts changed')
        require(file_digest(path)==asset['sha256']and file_digest(Path(plan_path))==expected_plan_sha256,'input changed while checking')
    except (ValueError,KeyError,TypeError,IndexError,OSError)as exc:errors.append(str(exc))
    result=dict(schema_version='b-question-content-check-trial/0.1',accepted=not errors,meaning='SOURCE_AND_PROJECTION_INTEGRITY_ONLY',issues=errors,decision='HOLD',complete=False,human_verification=False,transcription_verified=False,business_acceptance=False,platform_actions=[],plan_file_sha256=expected_plan_sha256,application_ref={k:application.get(k)for k in('artifact_id','revision','content_hash')},evidence_ref={k:evidence.get(k)for k in('artifact_id','revision','content_hash')},graph_ref={k:graph.get(k)for k in('artifact_id','revision','content_hash')})
    result['content_hash']=digest({k:v for k,v in result.items()if k!='content_hash'})
    return result
