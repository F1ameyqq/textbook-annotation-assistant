"""Conservative OCR-caption navigation for original question images.

These broad boxes only help a reviewer find a figure. They are never source
geometry approval and never alter a candidate frame or issue status.
"""
from __future__ import annotations

import math
import re

from .graphic_options import contains, overlaps, pixel_box
from .store import Hold, digest


NUMBERED_CAPTION = re.compile(r'第\s*([1-9]\d?)\s*题图')


def _center(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def _caption_target(text, questions):
    match = NUMBERED_CAPTION.fullmatch(text)
    if match:
        choices = [q for q in questions if q.get('source_item_kind') == 'QUESTION'
                   and q.get('printed_number') == match[1]]
    elif text == '变式题图':
        choices = [q for q in questions if q.get('source_item_kind') == 'VARIANT']
    else:
        return None
    return choices[0] if len(choices) == 1 else None


def _page_anchors(plan, questions, page, viewer_page):
    """Resolve every observed item start row, plus explicit parsed anchors."""
    by_row = {line.get('source_row_index'): line for line in page['ocr_lines']}
    by_id = {line.get('line_id'): line for line in page['ocr_lines']}
    anchors = []
    for item in plan.get('items', []):
        if item.get('role') == 'question' and item.get('start_page') == viewer_page:
            line = by_row.get(item.get('start_row'))
            if line is None:
                return None
            anchors.append(line['bbox'])
    for question in questions:
        line = by_id.get(question.get('anchor_ref'))
        if line is not None:
            anchors.append(line['bbox'])
    return anchors


def navigation_hints(questions, plan, evidence):
    """Return validated, unapproved caption locations for unhinted instances.

    Ambiguous captions, unmatched/duplicate printed labels, weak OCR, missing
    source identity, window conflicts, anchor collisions and competing boxes
    all fail closed. A reviewer must still inspect and redraw the full figure.
    """
    if evidence.get('book_id') != '46007447' or plan.get('schema') != 'CustomerObservedSourcePlan/v1':
        return []
    if not plan.get('windows') or not plan.get('items') or not plan.get('page_assets'):
        return []
    pages = {page['asset_id']: page for page in evidence['payload']['pages']
             if page.get('page_role') == 'question'}
    captions = []
    for viewer_page, asset_id in plan['page_assets'].items():
        page = pages.get(asset_id)
        if page is None:
            continue
        for line in page['ocr_lines']:
            text = line.get('text', '')
            if not (NUMBERED_CAPTION.fullmatch(text) or text == '变式题图'):
                continue
            captions.append({'viewer_page': int(viewer_page), 'asset_id': asset_id,
                             'page': page, 'line': line, 'text': text})
    generated = []
    for entry in captions:
        viewer_page, page, line, text = (entry['viewer_page'], entry['page'],
                                        entry['line'], entry['text'])
        if (not isinstance(line.get('score'), (float, int)) or line['score'] < .60 or
                type(line.get('source_row_index')) is not int):
            continue
        if sum(other['text'] == text for other in captions) != 1:
            continue
        question = _caption_target(text, questions)
        if question is None or question.get('captioned_figure_hints'):
            continue
        source = page['source']
        size = [source.get('width'), source.get('height')]
        if (type(size[0]) is not int or type(size[1]) is not int or
                not isinstance(source.get('sha256'), str) or len(source['sha256']) != 64):
            continue
        caption = line['bbox']
        cx, cy = _center(caption)
        windows = [window for window in plan['windows']
                   if window.get('role') == 'question' and window.get('page') == viewer_page
                   and window['x0'] <= cx < window['x1'] and window['y0'] <= cy < window['y1']]
        if len(windows) != 1:
            continue
        window = windows[0]
        neighbors = [other for other in captions if other is not entry and
                     other['viewer_page'] == viewer_page and
                     abs(_center(other['line']['bbox'])[1] - cy) < 40 and
                     window['x0'] <= _center(other['line']['bbox'])[0] < window['x1']]
        left = [other for other in neighbors if _center(other['line']['bbox'])[0] < cx]
        right = [other for other in neighbors if _center(other['line']['bbox'])[0] > cx]
        x0 = max(math.ceil(window['x0']), int(cx - 180))
        x1 = min(math.floor(window['x1']), int(cx + 180))
        if left:
            x0 = max(x0, int((cx + max(_center(o['line']['bbox'])[0] for o in left)) / 2))
        if right:
            x1 = min(x1, int((cx + min(_center(o['line']['bbox'])[0] for o in right)) / 2))
        box = [x0, max(math.ceil(window['y0']), int(caption[1] - 240)),
               x1, min(math.floor(window['y1']), int(caption[3] + 8))]
        anchors = _page_anchors(plan, questions, page, viewer_page)
        if anchors is None:
            continue
        earlier = [anchor[3] for anchor in anchors
                   if overlaps(box, anchor) and anchor[3] < caption[1] - 60]
        if earlier:
            box[1] = max(box[1], int(max(earlier)) + 5)
        if (box[2] - box[0] < 80 or box[3] - box[1] < 60 or
                any(overlaps(box, anchor) for anchor in anchors) or
                not contains(box, caption)):
            continue
        try:
            if pixel_box(box, size) != box:
                continue
        except (Hold, TypeError, ValueError):
            continue
        generated.append({'question_item_id': question['source_instance_id'],
                          'viewer_page': viewer_page, 'asset_id': entry['asset_id'],
                          'source_sha256': source['sha256'], 'source_dimensions': size,
                          'bbox': box, 'caption_row_index': line['source_row_index'],
                          'caption_line_id': line['line_id'], 'caption_text': text,
                          'caption_bbox': list(caption), 'caption_ocr_score': line['score'],
                          'review_kind': 'AUTO_CAPTION_ORIGINAL_PIXEL_NAVIGATION',
                          'source_checked': False, 'content_approved': False,
                          'approved': False})
    existing = [hint for q in questions for hint in q.get('captioned_figure_hints', [])]
    safe = []
    for hint in generated:
        if any(other['asset_id'] == hint['asset_id'] and overlaps(other['bbox'], hint['bbox'])
               for other in generated if other is not hint):
            continue
        if any(other['asset_id'] == hint['asset_id'] and overlaps(other['bbox'], hint['bbox'])
               for other in existing):
            continue
        hint['review_sha256'] = digest(['AUTO_CAPTION_NAVIGATION/v1', plan['scope_id'],
                                        hint['question_item_id'], hint['source_sha256'],
                                        hint['caption_row_index'], hint['caption_text'], hint['bbox']])
        safe.append(hint)
    return safe
