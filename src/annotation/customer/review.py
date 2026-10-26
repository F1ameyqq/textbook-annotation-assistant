"""Customer job adapter for the existing source-visible B review server/UI."""
from __future__ import annotations

import copy
import io
import json
import re
from pathlib import Path

from .prepare import candidate_hash, preparation_status, utcnow
from .source import verify_sources
from .store import Hold, digest, byte_hash
from .orphan_groups import group_unassigned_sources
from .review_features import figure_requirements, candidate_support
from .figure_proposals import BLOCKER
from .source_occupancy import occupancy, plan_transfers, apply_transfers

CONFIRMABLE = {"IMAGE_TRANSCRIPTION_AND_FIGURES_REVIEW", "FIGURE_OR_FORMULA_REVIEW", "ANSWER_BOUNDARY_UNRESOLVED",
               "LOW_OR_MISSING_OCR_CONFIDENCE", "FORMULA_LAYOUT_REVIEW", "UNEXPLAINED_SOURCE_INK"}


def recheck_structure(candidate, *, pages=(), graph=None, evidence=None):
    """Re-evaluate correctable facts; retain provenance and boundary blockers."""
    from annotation.recognition.policy import option_set_valid, choice_answer_valid
    issues=set(candidate['issues'])-{'CHOICE_OR_ANSWER_STRUCTURE','QUESTION_EMPTY',BLOCKER}
    zones=candidate['zones']
    if not zones['question'].strip():issues.add('QUESTION_EMPTY')
    if 'choice' in zones:
        labels=re.findall(r'^\s*([A-G])[.．、]',zones['choice'],re.M)
        if not option_set_valid(labels) or not choice_answer_valid(zones['answer'],labels):issues.add('CHOICE_OR_ANSWER_STRUCTURE')
    if not zones['answer'].strip() or not any(f['zone']=='answer' for f in candidate['frames']):
        issues.add('ANSWER_MISSING_OR_AMBIGUOUS')
    elif candidate.get('manual_answer_binding') or candidate.get('source_candidate_answer_binding'):
        issues.discard('ANSWER_MISSING_OR_AMBIGUOUS')
    requirements=figure_requirements(candidate,pages,graph,evidence)
    candidate['figure_requirements']=requirements
    issues.update(row['code'] for row in requirements)
    if candidate.get('source_reassignment_pending_zones'):
        issues.add('SOURCE_REGION_REASSIGNED_TEXT_CHECK')
    candidate['issues']=sorted(issues)
    from .graphic_options import recheck
    recheck(candidate)
    from .question_figures import recheck as recheck_referenced_figures
    recheck_referenced_figures(candidate)
    if requirements:candidate['content_status']='NEEDS_REVIEW'


class CustomerReviewWorkspace:
    def __init__(self, store, identity, *, settings_provider=None):
        self.store, self.identity = store, identity
        self._figure_cache = {}
        self._settings_provider = settings_provider

    def _load(self):
        job, head = self.store.job(self.identity)
        verify_sources(job["pages"])
        return job, head

    def _review_recheck(self, job, candidate):
        graph=self.store.get(job["graph_ref"]) if job.get("graph_ref") else None
        evidence=self.store.get(job["evidence_ref"]) if job.get("evidence_ref") else None
        recheck_structure(candidate,pages=job["pages"],graph=graph,evidence=evidence)

    def _support(self, job, candidate, head):
        try:
            graph=self.store.get(job["graph_ref"])
            evidence=self.store.get(job["evidence_ref"])
            layouts=self.store.get(job["section_scope_ref"]) if job.get("section_scope_ref") else ()
            return candidate_support(candidate,job["pages"],graph,evidence,layouts,cache=self._figure_cache)
        except (KeyError,ValueError,TypeError,OSError) as exc:
            return {"source_projection":{"status":"SOURCE_MAPPING_UNAVAILABLE","zones":[],"issues":[{"code":"SOURCE_MAPPING_UNAVAILABLE","detail":str(exc)}],"content_approved":False},
                    "figure_requirements":figure_requirements(candidate,job["pages"]),
                    "figure_discovery":{"status":"NEEDS_REVIEW","proposals":[],"issues":["FIGURE_SOURCE_MAPPING_UNAVAILABLE"],"approved":False}}

    def state(self):
        job, head = self._load()
        answers, issues = [], []
        from .formula_regions import propose_job,mark_consumed_regions
        try:
            formula_proposals=propose_job(job,self.store.get(job['graph_ref']),self.store.get(job['evidence_ref']))
            for proposed in formula_proposals.values():
                proposed['regions']=mark_consumed_regions(self.store,job['book_id'],proposed['regions'])
        except (KeyError,TypeError,ValueError) as exc:
            formula_proposals={candidate['key']:{'regions':[],'status':'SOURCE_MAPPING_UNAVAILABLE','message':str(exc)} for candidate in job['candidates']}
        for index, issue in enumerate(job["issues"]):
            issues.append({**issue, "issue_id": "global-" + str(index), "severity": "ERROR"})
        for original in job["candidates"]:
            candidate=copy.deepcopy(original)
            self._review_recheck(job,candidate)
            features=self._support(job,candidate,head)
            features['formula_regions']=formula_proposals[candidate['key']]
            features['formula_observations']=self._formula_observations(candidate)
            linked = []
            for code in candidate["issues"]:
                iid = candidate["key"] + "-" + code
                issues.append({"code": code, "issue_id": iid, "severity": "REVIEW", "scope_id": candidate["key"]})
                linked.append(iid)
            blocks = []
            for zone, text in candidate["zones"].items():
                frames = [f for f in candidate["frames"] if f["zone"] == zone]
                frame = frames[0] if frames else candidate["frames"][0]
                blocks.append({"key": candidate["key"] + ":" + zone, "kind": "FRAGMENT", "role": zone,
                    "asset_id": frame["asset_id"], "bbox": frame["bbox"], "text": text,
                    "source_text": candidate.get("original_zones", candidate["zones"]).get(zone, ""),
                    "runs": [{"format": "plain", "text": text}], "candidates": [], "source_fragment_ids": []})
            answers.append({"answer_id": candidate["key"], "printed_number": candidate["printed_number"],
                "section_path": candidate["section_path"], "text": candidate["zones"]["answer"],
                "explanation_text": candidate["zones"].get("analysis", ""), "blocks": blocks,
                "figures": [{"region_id": "source-" + str(i), "asset_id": f["asset_id"], "bbox": f["bbox"], "role": f["zone"], "content_type": f.get("content_type","text"),
                             'graphic_option_label':f.get('graphic_option_label'),'referenced_figure_id':f.get('referenced_figure_id'),
                             'source_checked':f.get('binding',{}).get('source_checked') is True}
                            for i, f in enumerate(candidate["frames"])],
                "issue_ids": linked, "question_candidates": [{"question_id": candidate["question_id"],
                    "printed_number": candidate["printed_number"], "section_path": candidate["section_path"],
                    "text": candidate["zones"]["question"]}], "content_status": candidate["content_status"],
                "platform_status":candidate['platform_status'],
                "source_reassignment_pending_zones":candidate.get("source_reassignment_pending_zones",[]), **features})
        # These are the existing UI's immutable draft/recognition boundary,
        # not the separate customer review receipt or platform acceptance.
        source_occupancy=occupancy(job,self.store.get(job["graph_ref"]),self.store.get(job["evidence_ref"])) if job.get("graph_ref") and job.get("evidence_ref") else []
        unassigned = self._unassigned(job)
        groups = self._unassigned_groups(job, head, unassigned)
        return {"schema_version": "b-content-review-state-trial/0.1", "head": head,
            "book_id": job["book_id"], "scope_id": job["lesson"], "plan_revision": job["revision"],
            "author": {"kind": "HUMAN_DRAFT", "id": "local-customer", "note": "对照原始材料核对"},
            "counts": {"questions": len(answers), "answers": len(answers), "issues": len(issues), "unassigned": len(job["issues"])},
            "assets": [{"asset_id": p["asset_id"], "width": p.get("width", 1), "height": p.get("height", 1), "sha256": p["raw_sha256"]}
                       for p in job["pages"]], "answers": answers, "issues": issues, "history": [],
            "decision": "HOLD", "complete": False, "transcription_verified": False,
            "business_acceptance": False, "platform_actions": [],
            "customer": {"job_status": job["status"], "can_confirm": True,
                         "unassigned_sources": unassigned,
                         "unassigned_groups": groups,
                         "region_binding": True, "source_occupancy": source_occupancy,
                         "message": job.get("last_message", "核对题干、选项、答案及来源框后确认；缺材料或结构错误仍会阻断。"),
                         "metrics": job["metrics"], "platform_status": job["platform_status"]}}

    def _formula_observations(self,candidate):
        with self.store.connect() as db:
            rows=db.execute('SELECT output FROM operations WHERE kind=? AND state=?',
                            ('formula-review:'+self.identity,'COMPLETE')).fetchall()
        result=[]
        for (reference,) in rows:
            value=self.store.get(reference)
            if value['candidate_key']==candidate['key']:
                result.append({**value,'review_record_ref':reference})
        return result

    def formula(self,request):
        from .formula_regions import recognize_proposal
        settings=(self._settings_provider() if self._settings_provider else
                  json.loads((self.store.root/'settings.json').read_bytes()))
        result=recognize_proposal(self.store,self.identity,request.get('expected_head'),request.get('answer_id'),
            request.get('proposal_id'),settings,source_checked=request.get('source_checked') is True,
            adjusted_bbox=request.get('adjusted_bbox'))
        self._retain_formula(result,request.get('author'),region_review='EXPLICIT_SOURCE_REGION_CHECK')
        return self.state()

    def _retain_formula(self,result,author,*,region_review):
        record={'candidate_key':result['candidate_key'],'proposal_id':result['proposal_id'],
                'requested_head':result['head'],'candidate':result['candidate'],'operation_ref':result['operation_ref'],
                'reused':result['reused'],'new_worker_invocations':result['new_worker_invocations'],
                'observed_at':utcnow(),'operator':copy.deepcopy(author or {'kind':'UNSPECIFIED_LOCAL_OPERATOR'}),
                'region_review':region_review,
                'content_applied':False,'content_approved':False}
        key=digest([result['candidate_key'],result['proposal_id'],result['operation_ref']])
        old=self.store.operation('formula-review:'+self.identity,key)
        if old is None:return self.store.record_read('formula-review:'+self.identity,key,record)
        if old['state']!='COMPLETE':raise Hold('公式审校记录未完成，保留原记录。')
        return old['output']

    def formula_batch(self,request):
        from .formula_batch import run
        settings=(self._settings_provider() if self._settings_provider else
                  json.loads((self.store.root/'settings.json').read_bytes()))
        result=run(self.store,self.identity,request.get('expected_head'),settings,
                   lambda item:self._retain_formula(item,request.get('author'),region_review='PROGRAM_CLEAR_ROW_PENDING_CUSTOMER_REVIEW'))
        state=self.state();state['customer']['formula_batch_result']=result
        return state

    def _unassigned(self, job):
        refs={ref for issue in job['issues'] if issue.get('code')=='UNASSIGNED_ANSWER_OCR_LINE'
              for ref in issue.get('evidence_refs',[])}
        if not refs or not job.get('evidence_ref'):return []
        evidence=self.store.get(job['evidence_ref']);result=[]
        for page in evidence['payload']['pages']:
            if page['page_role']!='answer':continue
            for line in page['ocr_lines']:
                if line['line_id'] in refs:
                    result.append({'line_id':line['line_id'],'asset_id':page['asset_id'],'bbox':line['bbox'],
                        'text':line['text'],'location':line.get('location')})
        return result

    def _unassigned_groups(self, job, head, sources=None):
        sources = self._unassigned(job) if sources is None else sources
        if not sources or not job.get("evidence_ref"): return []
        evidence = self.store.get(job["evidence_ref"])
        return group_unassigned_sources(sources, evidence["payload"]["pages"], head)

    def assign(self, request):
        job,head=self._load()
        with self.store.book_lock(job['book_id']):
            job,head=self._load();candidate=self._target(job,request,head)
            if candidate['zones']['answer'].strip():raise Hold('本题已有答案；不能用未归属行覆盖现有绑定。')
            if request.get('source_checked') is not True:raise Hold('先对照原页核对所选行确属本题。')
            available={r['line_id']:r for r in self._unassigned(job)}
            paragraph_group=None
            if request.get('group_id') is not None:
                paragraph_group=next((group for group in self._unassigned_groups(job,head,list(available.values()))
                    if group['group_id']==request['group_id']),None)
                if paragraph_group is None:raise Hold('未归属段落组已变化，请刷新后重新核对。')
                ids=list(paragraph_group['line_ids'])
                if request.get('line_ids') is not None and request['line_ids']!=ids:
                    raise Hold('段落组来源行不一致，不能扩展或缩减组内来源。')
            else:
                ids=request.get('line_ids')
            if type(ids) is not list or not ids or len(ids)>100 or any(type(i) is not str for i in ids) or len(set(ids))!=len(ids):raise Hold('请选择未归属的答案来源行。')
            if any(i not in available for i in ids):raise Hold('来源行已经变化或不属于当前未归属队列。')
            lines=[available[i] for i in ids]
            if len({l['asset_id'] for l in lines})!=1:raise Hold('一次配答选择同一页的连续来源行。')
            for line in lines:
                if not line['location'] or line['location']['section_path']!=candidate['section_path']:
                    raise Hold('来源行没有绑定本题所属课时。')
            if len({l['location']['column'] for l in lines})!=1:raise Hold('一次配答不能跨栏。')
            lines.sort(key=lambda l:(l['bbox'][1],l['bbox'][0]))
            for line in lines[1:]:
                if re.match(r'^\s*\d+[.．、]',line['text']):raise Hold('所选行包含另一个题号，不能并入同一答案。')
            for line in available.values():
                if (line['asset_id']==lines[0]['asset_id'] and line.get('location')
                    and line['location']['column']==lines[0]['location']['column']
                    and lines[0]['bbox'][1]<=line['bbox'][1]<=lines[-1]['bbox'][1] and line['line_id'] not in ids):
                    raise Hold('所选答案行不连续，先核对中间未归属内容。')
            text='\n'.join(l['text'] for l in lines)
            marker=re.match(r'^\s*(\d+)[.．、]\s*(.*)',lines[0]['text'])
            if marker:
                if marker[1]!=str(candidate['printed_number']):raise Hold('来源题号与当前题目不同。')
                text='\n'.join([marker[2],*[l['text'] for l in lines[1:]]])
            if not text.strip():raise Hold('所选来源没有答案内容。')
            page=next(p for p in job['pages'] if p['asset_id']==lines[0]['asset_id'])
            from .prepare import _union
            candidate['frames'].append({'zone':'answer','content_type':'text','asset_id':page['asset_id'],
                'bbox':_union([l['bbox'] for l in lines]),'source_sha256':page['raw_sha256'],
                'source_dimensions':[page['width'],page['height']],
                'coordinate_space':page.get('coordinate_space','ORIGINAL_PIXELS'),
                'source_fragment_ids':['customer-assigned:'+l['line_id'] for l in lines],'column':lines[0]['location']['column']})
            candidate['zones']['answer']=text
            candidate['manual_answer_binding']={'at':utcnow(),'previous_head':head,'evidence_ref':job['evidence_ref'],
                'line_ids':[l['line_id'] for l in lines],'raw_texts':[l['text'] for l in lines],'source_checked':True}
            if paragraph_group is not None:
                candidate['manual_answer_binding']['paragraph_group']={key:copy.deepcopy(paragraph_group[key]) for key in
                    ('group_id','line_ids','bbox','basis','reading_order_status','inferred_question_number')}
                if paragraph_group['formula_review_required']:
                    candidate['issues']=sorted(set(candidate['issues'])|{'FORMULA_LAYOUT_REVIEW'})
            unresolved=[]
            for issue in job['issues']:
                if issue.get('code')!='UNASSIGNED_ANSWER_OCR_LINE':unresolved.append(issue);continue
                remaining=[r for r in issue.get('evidence_refs',[]) if r not in ids]
                if remaining:unresolved.append({**issue,'evidence_refs':remaining})
            job['issues']=unresolved
            candidate['review']=None;candidate['content_status']='NEEDS_REVIEW'
            candidate['issues'].append('EDITED_CONTENT_REVIEW');self._review_recheck(job,candidate)
            candidate['content_hash']=candidate_hash(candidate)
            job['revision']+=1;job['metrics']['review_actions']+=1;job['status']=preparation_status(job)
            self.store.save_job(job,head,'CUSTOMER_ASSIGN_SOURCE')
        return self.state()

    def assign_source_candidate(self, request):
        """Bind one reviewed source observation to one local question only."""
        job, head = self._load()
        with self.store.book_lock(job['book_id']):
            job, head = self._load()
            candidate = self._target(job, request, head)
            if candidate['platform_status'] != 'NOT_RUN' or candidate.get('acceptance_ref'):
                raise Hold('已有平台状态，不能改写本题配答。')
            if candidate['zones']['answer'].strip() or any(f['zone'] == 'answer' for f in candidate['frames']):
                raise Hold('本题已有答案来源，不能直接覆盖。')
            if request.get('source_checked') is not True or request.get('content_checked') is not True:
                raise Hold('请先逐字核对原图答案及来源框。')
            answer_text = request.get('answer_text')
            if not isinstance(answer_text, str) or not answer_text.strip() or len(answer_text) > 100000:
                raise Hold('请输入核对后的完整答案文字。')
            from .rich_content import zone_html
            zone_html(answer_text)
            source_id = request.get('source_candidate_id')
            sources = [s for s in candidate.get('answer_source_candidates', [])
                       if s['candidate_id'] == source_id]
            if len(sources) != 1:
                raise Hold('答案来源候选已变化，请刷新后重新核对。')
            source = sources[0]
            if (source['question_item_id'] != candidate.get('source_instance_id') or
                    source['source_binding_status'] != 'ORIGINAL_PAGE_BOUND' or
                    source.get('direct_binding_allowed') is not True or
                    not source['requires_review'] or source['selected'] or
                    not source['asset_id'] or not source['bbox']):
                raise Hold('此来源未绑定本题原始答页与原图框。')
            page = next((p for p in job['pages'] if p['asset_id'] == source['asset_id']), None)
            from annotation.recognition.baseline import valid_bbox
            if (page is None or page['role'] != 'answer' or page['kind'] != 'image' or
                    page['raw_sha256'] != source['source_sha256'] or
                    not valid_bbox(source['bbox'], page['width'], page['height'])):
                raise Hold('来源原图身份或坐标已经变化。')
            pairings = [p for p in job.get('source_plan', {}).get('pairing_status', [])
                        if p['question_item_id'] == candidate.get('source_instance_id')]
            if len(pairings) != 1:
                raise Hold('本题来源配答身份不唯一。')
            pairing = pairings[0]
            details = json.loads(pairing.get('details_json') or '{}')
            supplemental = {r['candidate_id'] for r in details.get('supplemental_answer_candidates', [])}
            if source_id != pairing.get('answer_item_id') and source_id not in supplemental:
                raise Hold('此来源没有列入本题原始配答候选。')
            frame = {'zone': 'answer', 'content_type': 'text',
                     'asset_id': page['asset_id'], 'bbox': list(source['bbox']),
                     'source_sha256': page['raw_sha256'],
                     'source_dimensions': [page['width'], page['height']],
                     'coordinate_space': 'ORIGINAL_PIXELS',
                     'source_fragment_ids': ['customer-source-candidate:' + source_id]}
            candidate['frames'].append(frame)
            candidate['zones']['answer'] = answer_text
            candidate['source_candidate_answer_binding'] = {
                'source_candidate_id': source_id,
                'source_kind': source['source_kind'],
                'source_item_id': pairing.get('answer_item_id'),
                'question_item_id': candidate['source_instance_id'],
                'asset_id': page['asset_id'], 'source_sha256': page['raw_sha256'],
                'bbox': list(source['bbox']), 'original_observation': source['text'],
                'suggested_answer_text': source['suggested_answer_text'],
                'human_entered_answer_text': answer_text,
                'source_checked': True, 'content_checked': True,
                'at': utcnow(), 'previous_head': head,
                'content_approved': False}
            candidate['review'] = None
            candidate['content_status'] = 'NEEDS_REVIEW'
            candidate['issues'] = sorted(set(candidate['issues']) | {'EDITED_CONTENT_REVIEW'})
            self._review_recheck(job, candidate)
            candidate['content_hash'] = candidate_hash(candidate)
            job['revision'] += 1
            job['metrics']['review_actions'] += 1
            job['status'] = preparation_status(job)
            self.store.save_job(job, head, 'CUSTOMER_ASSIGN_SOURCE_CANDIDATE')
        return self.state()

    def source_png(self, aid, bbox=None):
        from PIL import Image, ImageDraw, ImageFont
        job, _ = self._load()
        page = next((p for p in job["pages"] if p["asset_id"] == aid), None)
        if page is None:
            raise Hold("来源页不属于本任务。")
        if page["kind"] == "image":
            with Image.open(page["raw_path"]) as original:
                image = original.convert("RGB")
        else:
            image = Image.new("RGB", (page["width"], page["height"]), "white")
            font_path = Path("C:/Windows/Fonts/msyh.ttc")
            font = ImageFont.truetype(str(font_path), 20) if font_path.exists() else ImageFont.load_default()
            draw = ImageDraw.Draw(image)
            for index, line in enumerate(page["text"].splitlines()):
                draw.text((20, 20 + index * 30), line, font=font, fill="black")
        if bbox is not None:
            from annotation.recognition.baseline import valid_bbox
            if not valid_bbox(bbox, *image.size) or any(type(x) is not int for x in bbox):
                raise Hold("来源裁片范围无效。")
            image = image.crop(tuple(bbox))
        output = io.BytesIO(); image.save(output, format="PNG")
        return output.getvalue()

    def bind_region(self,request):
        if request.get('replace_text_region_id') is not None:
            return self.adjust_text_region(request)
        job,head=self._load()
        with self.store.book_lock(job['book_id']):
            job,head=self._load();candidate=self._target(job,request,head)
            if candidate.get('acceptance_ref') or candidate['platform_status']!='NOT_RUN':raise Hold('已有平台状态，不能改写来源框。')
            if request.get('source_checked') is not True:raise Hold('请先在原页框选并核对题图范围。')
            page=next((p for p in job['pages'] if p['asset_id']==request.get('asset_id')),None)
            zone=request.get('zone');box=request.get('bbox')
            from annotation.recognition.baseline import valid_bbox
            if page is None or page['kind']!='image' or zone not in candidate['zones'] or type(box) is not list or any(type(v) is not int for v in box) or not valid_bbox(box,page['width'],page['height']):
                raise Hold('所选题图页或范围无效。')
            if page['role']!=('question' if zone in {'question','choice'} else 'answer') or not any(f['asset_id']==page['asset_id'] for f in candidate['frames']):
                raise Hold('题图没有绑定本题对应的题页或答页。')
            replacement=None
            if request.get('replace_region_id') is not None:
                region_id=request['replace_region_id']
                if not isinstance(region_id,str) or not re.fullmatch(r'source-\d+',region_id):raise Hold('待调整题图标识无效。')
                replacement=int(region_id[7:])
                if replacement>=len(candidate['frames']):raise Hold('待调整题图已变化。')
                previous=candidate['frames'][replacement]
                if (previous.get('content_type')!='image' or previous.get('binding',{}).get('kind') not in {'CUSTOMER_SOURCE_REGION','GRAPHIC_OPTION_PROPOSAL','REFERENCED_FIGURE_PROPOSAL','REVIEWED_SOURCE_GEOMETRY'}
                    or previous['asset_id']!=page['asset_id'] or previous['zone']!=zone):
                    raise Hold('只能调整当前题已绑定的同页、同分区题图。')
            graph=self.store.get(job['graph_ref']) if job.get('graph_ref') else None
            evidence=self.store.get(job['evidence_ref']) if job.get('evidence_ref') else None
            try:
                transfers=plan_transfers(job,candidate,page,box,request.get('source_transfers',[]),graph,evidence)
            except ValueError as exc:
                raise Hold('所选区域仍与受保护来源相交；请逐项核对图内误归文字，不能占用其他题真实文字、题号或已保存来源。 '+str(exc)) from exc
            frame={'zone':zone,'content_type':'image','asset_id':page['asset_id'],'bbox':box,
                'source_sha256':page['raw_sha256'],'source_dimensions':[page['width'],page['height']],
                'coordinate_space':'ORIGINAL_PIXELS','source_fragment_ids':['customer-region:'+digest([head,box,zone])],
                'binding':{'kind':'CUSTOMER_SOURCE_REGION','source_checked':True,'previous_head':head,'at':utcnow()}}
            if request.get('proposal_id') is not None:
                proposed=next((p for p in self._support(job,candidate,head)['figure_discovery']['proposals'] if p['proposal_id']==request['proposal_id']),None)
                if (proposed is None or not proposed['can_confirm_extent_without_adjustment'] or proposed['bbox']!=box
                    or proposed['asset_id']!=page['asset_id'] or proposed['zone']!=zone or proposed['source_sha256']!=page['raw_sha256']):
                    raise Hold('题图候选已变化或范围仍需调整，请在当前原页重新核对。')
                frame['binding']['proposal_id']=proposed['proposal_id']
            if any(i!=replacement and f.get('content_type')=='image' and f['asset_id']==page['asset_id'] and f['bbox']==box for i,f in enumerate(candidate['frames'])):
                raise Hold('此题图已经绑定。')
            if replacement is not None:
                from .graphic_options import confirm_frame
                confirm_frame(candidate,candidate['frames'][replacement],frame)
                from .question_figures import confirm_frame as confirm_referenced_frame
                confirm_referenced_frame(candidate,candidate['frames'][replacement],frame)
            for donor in apply_transfers(job,candidate,frame,transfers,head,graph,evidence):
                self._review_recheck(job,donor)
                donor['content_hash']=candidate_hash(donor)
            if replacement is None:candidate['frames'].append(frame)
            else:
                frame['binding']['replaces_region_id']=request['replace_region_id']
                frame['previous_bound_image']=copy.deepcopy(candidate['frames'][replacement])
                candidate['frames'][replacement]=frame
            if zone=='question':candidate['issues']=[i for i in candidate['issues'] if i!='FIGURE_EXTENT_UNVERIFIED']
            candidate['issues']=sorted(set(candidate['issues'])|{'EDITED_CONTENT_REVIEW'})
            candidate['review']=None;candidate['content_status']='NEEDS_REVIEW'
            self._review_recheck(job,candidate)
            candidate['content_hash']=candidate_hash(candidate)
            job['revision']+=1;job['metrics']['review_actions']+=1;job['status']=preparation_status(job)
            self.store.save_job(job,head,'CUSTOMER_BIND_IMAGE')
        return self.state()

    def adjust_text_region(self,request):
        """Adjust original text bounds; checked expansion retains every original pixel."""
        from .source_occupancy import contains,intersects
        from annotation.recognition.baseline import valid_bbox
        job,head=self._load()
        with self.store.book_lock(job['book_id']):
            job,head=self._load();candidate=self._target(job,request,head)
            if candidate.get('acceptance_ref') or candidate['platform_status']!='NOT_RUN':
                raise Hold('已有平台状态，不能改写文字来源框。')
            if (request.get('source_checked') is not True or request.get('text_complete_checked') is not True
                or any(request.get(k) is not None for k in ('replace_region_id','proposal_id','source_transfers'))):
                raise Hold('请在原页核对文字完整；文字范围调整不能同时移交来源或改题图。')
            region_id=request.get('replace_text_region_id')
            if not isinstance(region_id,str) or not re.fullmatch(r'source-\d+',region_id):
                raise Hold('待调整文字来源标识无效。')
            index=int(region_id[7:])
            if index>=len(candidate['frames']):raise Hold('待调整文字来源已变化。')
            previous=candidate['frames'][index]
            history=previous.get('text_source_adjustment_history',[])
            original=history[0].get('previous_source_frame') if history else previous
            if (not isinstance(original,dict) or original.get('content_type','text')!='text'
                or any(original.get(k)!=previous.get(k) for k in ('asset_id','zone','source_sha256','source_dimensions','coordinate_space','source_fragment_ids'))):
                raise Hold('文字原始范围的来源链不完整，请保留记录并核对。')
            page=next((p for p in job['pages'] if p['asset_id']==request.get('asset_id')),None)
            box=request.get('bbox');zone=request.get('zone')
            if (previous.get('content_type','text')!='text' or page is None or page['kind']!='image'
                or previous['asset_id']!=page['asset_id'] or previous['zone']!=zone
                or previous['source_sha256']!=page['raw_sha256']
                or previous['source_dimensions']!=[page['width'],page['height']]
                or type(box) is not list or any(type(v) is not int for v in box)
                or not valid_bbox(box,page['width'],page['height'])
                or box==previous['bbox']):
                raise Hold('文字范围须为同原图、同分区的有效新边界，不能替换来源。')
            expansion=not contains(original['bbox'],box)
            if expansion and (request.get('expand_complete_source') is not True or not contains(box,original['bbox'])):
                raise Hold('补齐遗漏符号时必须明确核对外扩，且新框须完整包含最初文字框。')
            review_sha=request.get('review_input_sha256')
            if review_sha is not None and (not isinstance(review_sha,str) or not re.fullmatch(r'[0-9a-f]{64}',review_sha)):
                raise Hold('文字范围审校输入摘要无效。')
            if expansion:
                raw_review=request.get('field_review_json')
                if (not isinstance(raw_review,str) or len(raw_review)>1_000_000
                    or byte_hash(raw_review.encode('utf-8'))!=review_sha):
                    raise Hold('文字外扩需使用已固定的字段审校清单。')
                try:
                    document=json.loads(raw_review)
                    entries=[r for r in document['items'] if r['source_instance_id']==candidate.get('source_instance_id')
                             and r['candidate_key']==candidate['key']]
                    record=entries[0]['additional_layout_mark_evidence'] if len(entries)==1 else {}
                    source_rows=[r for r in document['source_images'] if r['page']==page.get('viewer_page')]
                    checked=(document['schema']=='FieldLevelSourceCheckedPreparation/v1' and document['book_id']==job['book_id']
                        and document['scope_id']==job.get('source_plan',{}).get('scope_id')
                        and record.get('source_page')==page.get('viewer_page') and record.get('source_sha256')==page['raw_sha256']
                        and record.get('current_text_frame_bbox')==original['bbox']
                        and record.get('full_printed_stem_region_if_new_source_window_supported')==box
                        and len(source_rows)==1 and source_rows[0]['source_sha256']==page['raw_sha256']
                        and [source_rows[0]['width'],source_rows[0]['height']]==previous['source_dimensions'])
                except (ValueError,KeyError,TypeError,IndexError):checked=False
                if not checked:raise Hold('文字外扩不符合本题已核对的原页及完整题区。')
            for other in job['candidates']:
                for frame_index,f in enumerate(other['frames']):
                    if other['key']==candidate['key'] and frame_index==index:continue
                    if f['asset_id']!=page['asset_id'] or not intersects(f['bbox'],box):continue
                    if expansion:
                        overlap=[max(f['bbox'][0],box[0]),max(f['bbox'][1],box[1]),min(f['bbox'][2],box[2]),min(f['bbox'][3],box[3])]
                        if not contains(previous['bbox'],overlap):raise Hold('新增文字范围与受保护题目、选项或题图相交。')
                    elif other['key']!=candidate['key'] and f['zone']==zone:
                        raise Hold('调整后仍与其他题同区来源框相交，请继续核对边界。')
            revised=copy.deepcopy(previous);revised['bbox']=list(box)
            revised.setdefault('text_source_adjustment_history',[]).append({
                'kind':'CUSTOMER_CHECKED_TEXT_FRAME_EXPANSION' if expansion else 'CUSTOMER_CHECKED_TEXT_FRAME_TIGHTENING',
                'previous_head':head,'at':utcnow(),'review_input_sha256':review_sha,
                'previous_source_frame':copy.deepcopy(previous),'source_checked':True,'text_complete_checked':True,
                'content_rewritten':False,'original_ocr_rewritten':False})
            candidate['frames'][index]=revised
            candidate['issues']=sorted(set(candidate['issues'])|{'EDITED_CONTENT_REVIEW'})
            candidate['review']=None;candidate['content_status']='NEEDS_REVIEW'
            self._review_recheck(job,candidate);candidate['content_hash']=candidate_hash(candidate)
            job['revision']+=1;job['metrics']['review_actions']+=1;job['status']=preparation_status(job)
            self.store.save_job(job,head,'CUSTOMER_ADJUST_TEXT_SOURCE')
        return self.state()

    def _target(self, job, request, head):
        from annotation.recognition.content_review import ReviewConflict
        if request.get("expected_head") != head:
            raise ReviewConflict("任务已更新，请刷新后再操作。")
        candidate = next((q for q in job["candidates"] if q["key"] == request.get("answer_id")), None)
        if candidate is None:
            raise Hold("没有找到所选题目。")
        return candidate

    def save(self, request):
        job, head = self._load()
        with self.store.book_lock(job["book_id"]):
            job, head = self._load()
            candidate = self._target(job, request, head)
            changes = request.get("changes")
            if not isinstance(changes, list) or not changes:
                raise Hold("没有可保存的修改。")
            candidate.setdefault("original_zones", copy.deepcopy(candidate["zones"]))
            seen = set()
            for change in changes:
                if set(change) != {"key", "text", "format"} or change["format"] != "plain":
                    raise Hold("本入口保存完整文字；公式候选的结构编辑需保留原有区域审校流程。")
                prefix = candidate["key"] + ":"
                if not isinstance(change["key"], str) or not change["key"].startswith(prefix):
                    raise Hold("编辑块不属于当前题目。")
                zone = change["key"][len(prefix):]
                text = change["text"]
                if zone not in candidate["zones"] or zone in seen or not isinstance(text, str) or not text.strip() or len(text) > 100000:
                    raise Hold("编辑块为空、重复或超出范围。")
                candidate["zones"][zone] = text; seen.add(zone)
            pending=set(candidate.get('source_reassignment_pending_zones',[]))-seen
            candidate['source_reassignment_pending_zones']=sorted(pending)
            if not pending:candidate['issues']=[i for i in candidate['issues'] if i!='SOURCE_REGION_REASSIGNED_TEXT_CHECK']
            candidate["review"] = None
            candidate["content_status"] = "NEEDS_REVIEW"
            if "EDITED_CONTENT_REVIEW" not in candidate["issues"]:
                candidate["issues"].append("EDITED_CONTENT_REVIEW")
            self._review_recheck(job,candidate)
            candidate["content_hash"] = candidate_hash(candidate)
            job["revision"] += 1; job["metrics"]["review_actions"] += 1
            job["status"] = preparation_status(job)
            self.store.save_job(job, head, "CUSTOMER_EDIT")
        return self.state()

    def confirm(self, request):
        job, head = self._load()
        with self.store.book_lock(job["book_id"]):
            job, head = self._load()
            candidate = self._target(job, request, head)
            if request.get("source_checked") is not True or request.get("content_checked") is not True:
                raise Hold("请对照原图核对完整内容及来源框。")
            self._review_recheck(job,candidate)
            if request.get('structure_checked') is True:
                candidate['issues']=[i for i in candidate['issues'] if i not in {'SHARED_MATERIAL_STRUCTURE_REVIEW','CROSS_COLUMN_CONTINUATION'}]
            from .rich_content import zone_html
            for text in candidate['zones'].values():zone_html(text)
            blocking = set(candidate["issues"]) - CONFIRMABLE - {"EDITED_CONTENT_REVIEW"}
            from .selection import blockers
            evidence=self.store.get(job['evidence_ref']) if job.get('evidence_ref') else None
            if blocking or blockers(job,[candidate],evidence):
                raise Hold("仍有缺材料、配答或结构问题；内容确认不能消除这些问题。请补充正确范围后重新准备，已有识别缓存会复用。")
            if any(not text.strip() for text in candidate["zones"].values()):
                raise Hold("题干或答案为空。")
            # Re-run semantic structural checks after an edit, not only before.
            from annotation.recognition.policy import option_set_valid, choice_answer_valid
            import re
            if "choice" in candidate["zones"]:
                labels = re.findall(r"^\s*([A-G])[.．、]", candidate["zones"]["choice"], re.M)
                if not option_set_valid(labels) or not choice_answer_valid(candidate["zones"]["answer"], labels):
                    raise Hold("选项或答案结构仍不完整。")
            candidate["review"] = {"kind": "CUSTOMER_SOURCE_REVIEW", "at": utcnow(),
                "content_hash": candidate_hash(candidate), "previous_head": head,
                "source_checked": True, "content_checked": True,'structure_checked':request.get('structure_checked') is True,
                'operator':copy.deepcopy(request.get('author',{'kind':'UNSPECIFIED_LOCAL_OPERATOR'}))}
            candidate["issues"] = []
            candidate["content_status"] = "READY_CUSTOMER_REVIEWED"
            job["revision"] += 1; job["metrics"]["review_actions"] += 1
            job["status"] = preparation_status(job)
            self.store.save_job(job, head, "CUSTOMER_CONFIRM")
        return self.state()

    def documents(self):
        job, _ = self._load()
        return {"plan": job}

    def restore(self, request):
        raise Hold("原版本保存在本地历史中；本入口不自动恢复已确认或已执行内容。")

    def region_catalog(self):
        raise Hold("本任务没有公式区域候选目录。")
