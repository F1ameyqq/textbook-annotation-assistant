"""Retained original-image figure assignments; importing is never approval."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re

from .graphic_options import contains, overlaps, pixel_box
from .store import Hold, digest

BLOCKER = 'REFERENCED_FIGURE_REGIONS_REQUIRE_REVIEW'
CAPTION_HINT_FILES = {
    'dir-1792063578574-2a6vq8zom': 'first_lesson_figure_hints.json',
    'dir-1792063578574-lvqkxdluj': 'second_lesson_figure_hints.json',
    'dir-1792063578574-hzrhienmk': 'retrospective_lesson_figure_hints.json',
}


def need(value, detail):
    if not value: raise Hold('题干图来源绑定不一致：' + detail)


def _captioned_source_hints(questions, plan, evidence):
    """Expose exact-caption original-pixel hints without approving a figure.

    This retained small visual review is a navigation aid for the ordinary
    customer crop editor. It never adds a candidate frame or clears an issue.
    The customer must redraw/check the full figure in the source image.
    """
    filename = CAPTION_HINT_FILES.get(plan['scope_id'])
    if filename is None:
        return
    document = json.loads(Path(__file__).with_name(filename).read_text(encoding='utf-8'))
    need(document.get('schema') == 'CaptionedFigureHints/v1' and
         document.get('book_id') == evidence['book_id'] and
         document.get('scope_id') == plan['scope_id'] and
         document.get('status') == 'SOURCE_GEOMETRY_PROPOSALS_REQUIRE_CUSTOMER_CONFIRMATION',
         '图注提议版本或书籍课时')
    pages = {p['asset_id']: p for p in evidence['payload']['pages']}
    questions_by_source = {q['source_instance_id']: q for q in questions}
    need(len(questions_by_source) == len(questions), '图注提议题目实例重复')
    validated = []
    for record in document['records']:
        q = questions_by_source.get(record['question_item_id'])
        aid = plan['page_assets'].get(str(record['viewer_page']))
        page = pages.get(aid)
        need(q is not None and page is not None and page['page_role'] == 'question', '图注提议题目或原页')
        source = page['source']
        size = [source['width'], source['height']]
        need(record['source_sha256'] == source['sha256'] and
             record['source_dimensions'] == size and
             record['source_checked'] is False and record['content_approved'] is False,
             '图注提议原图身份或审校状态')
        box = pixel_box(record['bbox'], size)
        need(box == record['bbox'], '图注提议不是原图整数像素框')
        captions = [line for line in page['ocr_lines']
                    if line.get('source_row_index') == record['caption_row_index']]
        need(len(captions) == 1 and captions[0]['text'] == record['caption_text'] and
             contains(box, captions[0]['bbox']), '图注提议没有绑定原图 OCR 图注')
        numbered = re.fullmatch(r'第\s*([1-9]\d?)\s*题图', record['caption_text'])
        if numbered:
            need(q['source_item_kind'] == 'QUESTION' and q['printed_number'] == numbered[1] and
                 sum(other['source_item_kind'] == 'QUESTION' and other['printed_number'] == numbered[1]
                     for other in questions) == 1, '编号图注未唯一指向本题')
        else:
            need(record['caption_text'] == '变式题图' and q['source_item_kind'] == 'VARIANT' and
                 sum(other['source_item_kind'] == 'VARIANT' for other in questions) == 1,
                 '变式图注未唯一指向本题')
        for other in questions:
            anchor = next((line for line in page['ocr_lines'] if line['line_id'] == other.get('anchor_ref')), None)
            need(anchor is None or not overlaps(box, anchor['bbox']), '图注提议包含题目题号')
        validated.append({**copy.deepcopy(record), 'asset_id': aid,
                          'caption_line_id': captions[0]['line_id'],
                          'review_kind': 'CAPTION_LINKED_ORIGINAL_PIXEL_HINT',
                          'review_sha256': digest(document)})
    need(len({(r['question_item_id'], r['caption_line_id']) for r in validated}) == len(validated),
         '图注提议身份重复')
    need(not any(a['asset_id'] == b['asset_id'] and overlaps(a['bbox'], b['bbox'])
                 for i, a in enumerate(validated) for b in validated[i+1:]),
         '图注提议图框相交')
    for region in validated:
        questions_by_source[region['question_item_id']].setdefault('captioned_figure_hints', []).append(region)


def annotate(questions, plan, evidence):
    _captioned_source_hints(questions, plan, evidence)
    rows = plan.get('question_figure_bindings', [])
    if not rows: return
    reviews = plan.get('question_figure_scope_reviews', [])
    need(len(reviews) == 1, '缺少唯一课时审校输入')
    review = reviews[0]; scope_review = json.loads(review['plan_json'])
    need(scope_review['book_id'] == evidence['book_id'] and scope_review['scope_id'] == plan['scope_id'], '课时身份')
    need(scope_review['summary']['all_regions_visually_checked'] is True
         and scope_review['summary']['positive_area_overlaps'] == 0, '图框审校尚未完成')
    originals = {}
    for item in scope_review['items']:
        for region in item['stem_figure_regions'] + item['option_graphic_regions']:
            fid = region.get('figure_id') or item['question_item_id'] + '/option-graphic/' + region['label']
            need(fid not in originals, '审校输入图框重复')
            originals[fid] = {**region, 'figure_id':fid,'question_item_id':item['question_item_id'],
                'scope_id':item['scope_id'],'assignment_basis':item['assignment_basis'],
                'position_note':item['position_note'],'plan_sha256':review['plan_sha']}
    need(len(originals) == len(rows), '审校图框数量')
    pages = {p['asset_id']: p for p in evidence['payload']['pages']}
    question_map = {q['source_instance_id']: q for q in questions}
    validated = []
    for row in rows:
        q = question_map.get(row['question_item_id'])
        need(q is not None and row['scope_id'] == plan['scope_id'] and row['printed_question'] == q['printed_number'], '题目实例')
        record = json.loads(row['record_json']); aid = plan['page_assets'].get(str(row['page']))
        need(record == originals.get(row['figure_id']), '图框不符合原审校输入')
        page = pages.get(aid); need(page is not None and page['page_role'] == 'question', '题页')
        source = page['source']; size = [source['width'], source['height']]
        box = json.loads(row['bbox_json']); refs = json.loads(row['original_ocr_row_refs_json'])
        need(row['source_sha256'] == source['sha256'] and [row['source_width'], row['source_height']] == size
             and record['source_sha256'] == source['sha256'] and record['source_dimensions'] == size, '原图摘要及尺寸')
        need(record['bbox'] == box and record['question_item_id'] == row['question_item_id']
             and record['figure_id'] == row['figure_id'] and record['page'] == row['page']
             and record['column'] == row['column'] and record['scope_id'] == plan['scope_id']
             and record.get('original_ocr_row_refs', [record['original_label_ocr_row']] if row['zone'] == 'options' else []) == refs
             and record['zone'] == row['zone'] and record['role'] == row['role'] and record['coordinate_space'] == 'ORIGINAL_PIXELS'
             and record['plan_sha256'] == row['plan_sha'] and re.fullmatch(r'[0-9a-f]{64}', row['plan_sha'])
             and row['visual_crop_checked'] == 1 and record['visual_crop_checked'] is True, '审校记录')
        box = pixel_box(box, size)
        need(len(set(refs)) == len(refs), '重复原行')
        observations = [l for l in page['ocr_lines'] if l['source_row_index'] in refs]
        need(len(observations) == len(refs) and all(contains(box, l['bbox']) for l in observations), '原行范围')
        for other in questions:
            anchor = next((l for l in page['ocr_lines'] if l['line_id'] == other.get('anchor_ref')), None)
            need(other['question_id'] == q['question_id'] or anchor is None or not overlaps(box, anchor['bbox']), '包含邻题题号')
        validated.append({**copy.deepcopy(record), 'asset_id': aid, 'bbox': box,
            'original_bbox': json.loads(row['bbox_json']), 'source_ocr_observations': copy.deepcopy(observations),
            'source_fragment_ids': [], 'approved': False, 'source_checked': False})
    need(len({r['figure_id'] for r in validated}) == len(validated), '图框实例重复')
    need(not any(a['asset_id'] == b['asset_id'] and overlaps(a['bbox'], b['bbox'])
                 for i, a in enumerate(validated) for b in validated[i+1:]), '图框重叠')
    stem = [r for r in validated if r['zone'] == 'stem' and r['role'] == 'question_referenced_figure']
    options = [r for r in validated if r['zone'] == 'options' and r['role'] == 'option_graphic']
    need(len(stem) + len(options) == len(validated), '不支持的题图分区')
    for region in stem:
        target = question_map[region['question_item_id']]
        for owner in questions:
            kept = []
            for fragment in owner['fragments']:
                if fragment['asset_id'] != region['asset_id'] or not contains(region['bbox'], fragment['bbox']):
                    kept.append(fragment); continue
                need(owner['anchor_ref'] not in fragment['evidence_refs'] and not fragment.get('option_start'), '不能把题号或选项文字当图内观察')
                observed = {**copy.deepcopy(fragment), 'original_question_id': owner['question_id'],
                            'assigned_figure_id': region['figure_id'], 'assigned_question_id': target['question_id']}
                target.setdefault('referenced_figure_observations', []).append(observed)
                region['source_fragment_ids'].append(fragment['fragment_id'])
            owner['fragments'] = kept
        target.setdefault('referenced_figure_bindings', []).append(region)
        target['flags'] = sorted(set(target['flags']) | {BLOCKER})
    for q in questions:
        for excluded in scope_review.get('excluded_nonfigure_elements', []):
            if excluded.get('old_related_question_item_id') != q['source_instance_id'] or 'bbox' not in excluded: continue
            aid = plan['page_assets'][str(excluded['page'])]
            removed = [f for f in q['fragments'] if f['asset_id'] == aid and contains(excluded['bbox'], f['bbox'])]
            need(all(q['anchor_ref'] not in f['evidence_refs'] for f in removed), '排除元素含题号')
            q['fragments'] = [f for f in q['fragments'] if f not in removed]
            q.setdefault('excluded_source_furniture', []).extend({**copy.deepcopy(f), 'exclusion':copy.deepcopy(excluded),
                'review_sha256':review['plan_sha']} for f in removed)
        q['text'] = '\n'.join(f['text'] for f in q['fragments'])
        option_regions = [r for r in options if r['question_item_id'] == q['source_instance_id']]
        if option_regions: q['reviewed_option_graphic_regions'] = option_regions


def attach(candidates, graph):
    questions = {q['question_id']: q for q in graph['payload']['questions']}
    for candidate in candidates:
        q = questions[candidate['question_id']]
        if q.get('captioned_figure_hints'):
            candidate['captioned_figure_hints'] = copy.deepcopy(q['captioned_figure_hints'])
        regions = copy.deepcopy(q.get('referenced_figure_bindings', []))
        if regions:
            candidate['referenced_figure_bindings'] = regions
            for region in regions:
                region['proposal_id'] = 'referenced-' + digest([candidate['key'], region])[:24]
                candidate['frames'].append({'zone':'question','content_type':'image','asset_id':region['asset_id'],
                    'bbox':region['bbox'],'source_sha256':region['source_sha256'],'source_dimensions':region['source_dimensions'],
                    'coordinate_space':'ORIGINAL_PIXELS','column':region['column'],
                    'source_fragment_ids':region['source_fragment_ids'],'source_ocr_observation_refs':[r['line_id'] for r in region['source_ocr_observations']],
                    'referenced_figure_id':region['figure_id'],'figure_label':region.get('figure_label'),
                    'binding':{'kind':'REVIEWED_SOURCE_GEOMETRY','source_checked':True,'geometry_checked':True,
                               'visual_review_sha256':region['plan_sha256'],'content_approved':False,'approved':False}})
        for region in q.get('reviewed_option_graphic_regions', []):
            matching = [p for p in candidate.get('graphic_option_proposals', []) if p['option_label'] == region['label']]
            need(len(matching) == 1, '图形选项没有唯一标签')
            proposed = matching[0]
            need(proposed['asset_id'] == region['asset_id'] and proposed['source_sha256'] == region['source_sha256']
                 and proposed['bbox'] == region['bbox'] and proposed['label_bbox'] == region['label_bbox'], '选项图与已有来源不一致')
            proposed['referenced_figure_review_sha256'] = region['plan_sha256']
            proposed['referenced_figure_id'] = region['figure_id']
            frame = next(f for f in candidate['frames'] if f.get('graphic_proposal_id') == proposed['proposal_id'])
            frame['binding'] = {'kind':'REVIEWED_SOURCE_GEOMETRY','source_checked':True,'geometry_checked':True,
                                'visual_review_sha256':region['plan_sha256'],'content_approved':False,'approved':False}
        recheck(candidate)
        from .graphic_options import recheck as recheck_options
        recheck_options(candidate)


def all_confirmed(candidate):
    regions = candidate.get('referenced_figure_bindings', [])
    if not regions: return True
    for region in regions:
        frames = [f for f in candidate['frames'] if f.get('referenced_figure_id') == region['figure_id']]
        if len(frames) != 1: return False
        frame = frames[0]; binding = frame.get('binding', {})
        if (binding.get('source_checked') is not True or binding.get('kind') not in {'CUSTOMER_SOURCE_REGION','REVIEWED_SOURCE_GEOMETRY'}
                or frame['source_sha256'] != region['source_sha256'] or frame['asset_id'] != region['asset_id']
                or frame['zone'] != 'question' or not contains(frame['bbox'], region['bbox'])): return False
        if binding.get('kind') == 'REVIEWED_SOURCE_GEOMETRY' and (binding.get('geometry_checked') is not True
                or binding.get('visual_review_sha256') != region['plan_sha256']): return False
    return True


def recheck(candidate):
    if not candidate.get('referenced_figure_bindings'): return
    issues = set(candidate['issues'])
    if all_confirmed(candidate):
        issues.discard(BLOCKER); issues.discard('FIGURE_EXTENT_UNVERIFIED')
    else: issues.add(BLOCKER)
    candidate['issues'] = sorted(issues)


def proposals(candidate):
    result = []
    for region in candidate.get('referenced_figure_bindings', []):
        matching = [(i,f) for i,f in enumerate(candidate['frames']) if f.get('referenced_figure_id') == region['figure_id']]
        if len(matching) != 1: continue
        index, frame = matching[0]
        if frame.get('binding', {}).get('source_checked') is True: continue
        result.append({**copy.deepcopy(region),'zone':'question','question_key':candidate['key'],
            'replace_region_id':'source-'+str(index),'status':'PROPOSED_UNREVIEWED','content_status':'NEEDS_REVIEW',
            'confidence':'REVIEW_REQUIRED','can_confirm_extent_without_adjustment':True,'content_inference':'NONE'})
    for hint in candidate.get('captioned_figure_hints', []):
        if any(f.get('content_type') == 'image' and f['asset_id'] == hint['asset_id']
               and overlaps(f['bbox'], hint['bbox']) for f in candidate['frames']):
            continue
        result.append({**copy.deepcopy(hint), 'proposal_id': 'caption-' + digest([candidate['key'], hint])[:24],
            'question_key': candidate['key'], 'zone': 'question',
            'status': 'PROPOSED_UNREVIEWED', 'content_status': 'NEEDS_REVIEW',
            'confidence': 'LOW', 'can_confirm_extent_without_adjustment': False,
            'suggested_action': 'VIEW_AND_ADJUST',
            'issues': ['CAPTIONED_PIXEL_SCOPE_REQUIRES_CUSTOMER_REVIEW'],
            'content_inference': 'NONE', 'approved': False})
    return result


def confirm_frame(candidate, previous, frame):
    identity = previous.get('referenced_figure_id')
    if identity is None: return
    region = next((r for r in candidate.get('referenced_figure_bindings', []) if r['figure_id'] == identity), None)
    need(region is not None and frame['asset_id'] == region['asset_id'] and frame['zone'] == 'question'
         and frame['source_sha256'] == region['source_sha256'] and contains(frame['bbox'], region['bbox']), '调整不能裁掉已审校完整图')
    need(not any(f is not previous and f.get('referenced_figure_id') and f['asset_id'] == frame['asset_id']
                 and overlaps(f['bbox'],frame['bbox']) for f in candidate['frames']), '调整与同题另一图相交')
    for key in ('referenced_figure_id','figure_label','source_fragment_ids','source_ocr_observation_refs','column'):
        frame[key] = copy.deepcopy(previous[key])
    frame['binding'].update(approved=True, referenced_figure_id=identity, visual_review_sha256=region['plan_sha256'])
