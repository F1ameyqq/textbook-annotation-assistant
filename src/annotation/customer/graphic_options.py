"""Source-bound A–D image proposals. Display never implies confirmation.

Original label rows, proposed geometry and review-file provenance stay separate.
No recognizer, browser, platform client or bulk confirmation is used here.
"""
from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path

from .store import Hold, byte_hash, digest

BLOCKER = 'GRAPHIC_OPTIONS_REQUIRE_SOURCE_REVIEW'


def contains(a, b):
    return a[0] <= b[0] and a[1] <= b[1] and a[2] >= b[2] and a[3] >= b[3]


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def pixel_box(box, size):
    if (type(box) is not list or len(box) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in box)):
        raise Hold('图形选项来源范围无效。')
    # Identical shared cuts use the same rounding, avoiding a one-pixel overlap.
    result = [math.floor(v + .5) for v in box]
    if not (0 <= result[0] < result[2] <= size[0] and 0 <= result[1] < result[3] <= size[1]):
        raise Hold('图形选项来源范围越界。')
    return result


def load_review(path, expected_sha256):
    if path is None:
        if expected_sha256 is not None: raise Hold('缺少图形选项复核文件。')
        return None
    raw = Path(path).read_bytes()
    if not expected_sha256 or byte_hash(raw) != expected_sha256:
        raise Hold('图形选项复核文件摘要不一致。')
    data = json.loads(raw)
    if data.get('schema') != 'GraphicOptionVisualReview/v1':
        raise Hold('图形选项复核格式不支持。')
    groups = {}
    for key, status in (('automatic_display_allowlist', 'VISUAL_DISPLAY_ALLOWLIST'),
                        ('proposed_recuts', 'RECUT_PROPOSAL_REQUIRES_REVIEW')):
        for group in data.get(key, []):
            identity = group['question_item_id']
            if identity in groups: raise Hold('图形复核题目实例重复。')
            groups[identity] = {**copy.deepcopy(group), 'display_status': status,
                                'review_sha256': expected_sha256}
    return {'sha256': expected_sha256, 'groups': groups}


def annotate_question(question, plan, evidence, questions):
    rows = [r for r in plan.get('graphic_option_candidates', [])
            if r['question_item_id'] == question['source_instance_id']]
    if not rows: return
    if len(rows) != 4 or {r['label'] for r in rows} != set('ABCD'):
        raise Hold('图形选项必须有四个独立的原始标签。')
    rows.sort(key=lambda r: r['label'])
    group = plan.get('graphic_review', {}).get('groups', {}).get(question['source_instance_id'])
    if group and (group['scope_id'] != plan['scope_id'] or len(group['options']) != 4
                  or {o['label'] for o in group['options']} != set('ABCD')):
        raise Hold('图形复核与来源实例不一致。')
    ep = {p['asset_id']: p for p in evidence['payload']['pages']}
    proposals, label_fragments = [], {}
    for row in rows:
        aid = plan['page_assets'].get(str(row['page']))
        page = ep.get(aid)
        if page is None or page['page_role'] != 'question': raise Hold('图形选项没有绑定题页。')
        source = page['source']; size = [source['width'], source['height']]
        line = next((l for l in page['ocr_lines'] if l['source_row_index'] == row['row_index']), None)
        label_box = json.loads(row['label_bbox_json'])
        original_box = json.loads(row['candidate_bbox_json'])
        if (line is None or line['text'].strip() != row['label'] or line['bbox'] != label_box
                or row['scope_id'] != plan['scope_id']):
            raise Hold('图形选项标签与原始识别行不一致。')
        selected_box, status = original_box, 'SOURCE_GRID_PROPOSAL'
        if group:
            option = next(o for o in group['options'] if o['label'] == row['label'])
            if (group['page'] != row['page'] or group['source_sha256'] != source['sha256']
                    or option['row_index'] != row['row_index']
                    or option.get('label_bbox', option.get('original_label_bbox')) != label_box
                    or option.get('candidate_bbox', option.get('original_candidate_bbox')) != original_box):
                raise Hold('图形选项复核不能映射当前来源。')
            selected_box = option.get('proposed_bbox', option.get('candidate_bbox'))
            status = group['display_status']
        box = pixel_box(selected_box, size)
        if not contains(box, label_box): raise Hold('图形选项框没有完整包含自己的标签。')
        fragments = [f for f in question['fragments'] if f['asset_id'] == aid and line['line_id'] in f['evidence_refs']]
        if len(fragments) != 1 or fragments[0]['text'].strip() != row['label']:
            raise Hold('图形标签没有唯一绑定本题实例。')
        fragment = fragments[0]; label_fragments[fragment['fragment_id']] = row['label']
        edge_proofs = []
        for other in questions:
            if other['question_id'] == question['question_id']: continue
            anchor = next((l for l in page['ocr_lines'] if l['line_id'] == other.get('anchor_ref')), None)
            if anchor and overlaps(box, anchor['bbox']):
                from PIL import Image
                raw = Path(plan['source_images'][str(row['page'])]).read_bytes()
                if byte_hash(raw) != source['sha256']: raise Hold('图形边界原图摘要不一致。')
                intersection = [max(box[0], math.floor(anchor['bbox'][0])), max(box[1], math.floor(anchor['bbox'][1])),
                                min(box[2], math.ceil(anchor['bbox'][2])), min(box[3], math.ceil(anchor['bbox'][3]))]
                with Image.open(plan['source_images'][str(row['page'])]) as image:
                    ink = sum(v < 160 for v in image.convert('L').crop(tuple(intersection)).getdata())
                if ink: raise Hold('图形选项范围包含另一题来源文字：' + question['source_instance_id'] + '/' + row['label'])
                edge_proofs.append({'other_question_instance': other['source_instance_id'], 'intersection_bbox': intersection,
                                    'ink_threshold': 160, 'ink_pixels': 0, 'source_sha256': source['sha256']})
        proposals.append({'kind': 'GRAPHIC_OPTION_REGION_PROPOSAL', 'asset_id': aid, 'viewer_page': row['page'],
            'option_label': row['label'], 'bbox': box, 'source_sha256': source['sha256'],
            'source_dimensions': size, 'coordinate_space': 'ORIGINAL_PIXELS', 'column': fragment.get('column', 0),
            'original_candidate_bbox': original_box, 'review_candidate_bbox': copy.deepcopy(selected_box),
            'label_bbox': label_box, 'label_row_index': row['row_index'], 'source_fragment_ids': [fragment['fragment_id']],
            'blank_ocr_edge_overlap_proofs': edge_proofs,
            'evidence_refs': [line['line_id']], 'display_status': status,
            'review_sha256': group.get('review_sha256') if group else None,
            'approved': False, 'source_checked': False})
    if len({p['asset_id'] for p in proposals}) != 1:
        raise Hold('同组图形选项跨页，需人工核对。')
    if any(overlaps(a['bbox'], b['bbox']) for i, a in enumerate(proposals) for b in proposals[i+1:]):
        raise Hold('图形选项范围重叠。')
    kept, observations = [], []
    for fragment in question['fragments']:
        label = label_fragments.get(fragment['fragment_id'])
        if label:
            fragment = copy.deepcopy(fragment)
            fragment.update(raw_text=fragment['text'], text=label + '.', role='option',
                            option_label=label, option_start=True, text_derivation='OBSERVED_LABEL_WITH_OPTION_DELIMITER')
            kept.append(fragment)
        elif any(p['asset_id'] == fragment['asset_id'] and contains(p['bbox'], fragment['bbox']) for p in proposals):
            observations.append(copy.deepcopy(fragment))
        else: kept.append(fragment)
    kept = ([f for f in kept if f['fragment_id'] not in label_fragments]
            + sorted([f for f in kept if f['fragment_id'] in label_fragments], key=lambda f: f['option_label']))
    question['fragments'] = kept
    question['text'] = '\n'.join(f['text'] for f in kept)
    question['graphic_observation_fragments'] = observations
    question['graphic_option_proposals'] = proposals
    question['graphic_extent_only'] = not any(f['role'] == 'figure_caption' or
        (f['role'] == 'stem' and re.search(r'如图|图示|下图', f['text'])) for f in kept)
    question['flags'] = sorted(set(question['flags']) | {BLOCKER})


def attach_frames(candidates, graph):
    questions = {q['question_id']: q for q in graph['payload']['questions']}
    for candidate in candidates:
        question = questions[candidate['question_id']]
        proposals = copy.deepcopy(question.get('graphic_option_proposals', []))
        if not proposals: continue
        frames = []
        for proposed in proposals:
            proposed['proposal_id'] = 'graphic-' + digest([candidate['key'], proposed])[:24]
            frames.append({k: copy.deepcopy(proposed[k]) for k in ('asset_id', 'bbox', 'source_sha256',
                'source_dimensions', 'coordinate_space', 'source_fragment_ids', 'column')})
            frames[-1].update(zone='choice', content_type='image', graphic_option_label=proposed['option_label'],
                graphic_proposal_id=proposed['proposal_id'],
                binding={'kind': 'GRAPHIC_OPTION_PROPOSAL', 'source_checked': False, 'approved': False})
        candidate['frames'] = [f for f in candidate['frames'] if f['zone'] != 'choice'] + frames
        candidate['graphic_option_proposals'] = proposals
        candidate['graphic_extent_only'] = question['graphic_extent_only']
        candidate['content_status'] = 'NEEDS_REVIEW'


def review_proposals(candidate):
    result = []
    for proposal in candidate.get('graphic_option_proposals', []):
        matching = [(i, f) for i, f in enumerate(candidate['frames'])
                    if f.get('graphic_proposal_id') == proposal['proposal_id']]
        if len(matching) != 1: continue
        index, frame = matching[0]
        if frame.get('binding', {}).get('source_checked') is True: continue
        result.append({**copy.deepcopy(proposal), 'zone': 'choice', 'question_key': candidate['key'],
            'replace_region_id': 'source-' + str(index), 'status': 'PROPOSED_UNREVIEWED',
            'content_status': 'NEEDS_REVIEW', 'confidence': 'LOW' if proposal['display_status'] != 'VISUAL_DISPLAY_ALLOWLIST' else 'REVIEW_REQUIRED',
            'can_confirm_extent_without_adjustment': proposal['display_status'] == 'VISUAL_DISPLAY_ALLOWLIST',
            'content_inference': 'NONE'})
    return result


def confirm_frame(candidate, previous, frame):
    label = previous.get('graphic_option_label')
    if label is None: return
    proposal = next((p for p in candidate.get('graphic_option_proposals', [])
                     if p['proposal_id'] == previous.get('graphic_proposal_id')), None)
    if (proposal is None or frame['zone'] != 'choice' or frame['asset_id'] != proposal['asset_id']
            or frame['source_sha256'] != proposal['source_sha256']
            or not contains(frame['bbox'], proposal['label_bbox'])):
        raise Hold('调整后的选项图必须包含本题对应标签。')
    if any(f is not previous and f.get('graphic_option_label') and f['asset_id'] == frame['asset_id']
           and overlaps(f['bbox'], frame['bbox']) for f in candidate['frames']):
        raise Hold('调整后的选项图与其他选项相交。')
    frame.update(graphic_option_label=label, graphic_proposal_id=proposal['proposal_id'],
                 source_fragment_ids=copy.deepcopy(previous['source_fragment_ids']), column=previous.get('column', 0))
    frame['binding'].update(graphic_option_label=label, approved=True)


def all_confirmed(candidate):
    if not candidate.get('graphic_option_proposals'): return True
    frames = [f for f in candidate['frames'] if f.get('graphic_option_label')]
    return (len(frames) == 4 and {f['graphic_option_label'] for f in frames} == set('ABCD')
            and all(f.get('binding', {}).get('source_checked') is True
                    and f.get('binding', {}).get('kind') == 'CUSTOMER_SOURCE_REGION' for f in frames))


def recheck(candidate):
    if not candidate.get('graphic_option_proposals'): return
    complete = all_confirmed(candidate)
    issues = set(candidate['issues'])
    if complete:
        issues.discard(BLOCKER)
        if candidate.get('graphic_extent_only'): issues.discard('FIGURE_EXTENT_UNVERIFIED')
    else: issues.add(BLOCKER)
    candidate['issues'] = sorted(issues)


def choice_html(text, source_frames, native_frames):
    """Use temporary label metadata; never add private keys to platform frames."""
    from .rich_content import zone_html
    images = [(s, n) for s, n in zip(source_frames, native_frames)
              if s['zone'] == 'choice' and s.get('content_type') == 'image']
    if not any(s.get('graphic_option_label') for s, _ in images):
        return zone_html(text, [n for _, n in images])
    labels = [s.get('graphic_option_label') for s, _ in images]
    blocks = re.split(r'(?m)(?=^[ \t]*[A-D][.．、])', text)
    blocks = [b for b in blocks if b.strip()]
    observed = [re.match(r'\s*([A-D])[.．、]', b) for b in blocks]
    if (len(images) != 4 or set(labels) != set('ABCD') or len(blocks) != 4
            or any(m is None for m in observed) or [m[1] for m in observed] != list('ABCD')):
        raise Hold('图形选项文字与四张来源图没有一一对应。')
    by_label = {s['graphic_option_label']: n for s, n in images}
    return '<br>'.join(zone_html(block.rstrip(), [by_label[m[1]]]) for block, m in zip(blocks, observed))
