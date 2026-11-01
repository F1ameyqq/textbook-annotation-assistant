"""Infer selected section windows from current directory labels and OCR headers.

Coordinates come from observed header boxes. Carry-over follows page/column
reading order. Historical manual windows are not consumed. Ambiguous headings
and number resets are reported instead of assigning the whole answer page.
"""
from __future__ import annotations
import copy
import re
import unicodedata
from .store import Hold


def title_key(text):
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'^\s*(?:第[一二三四五六七八九十0-9]+[章节课时]+|[0-9]+)\s*', '', text)
    return ''.join(c for c in text if c.isalnum())


def heading(text, titles):
    if re.match(r'^\s*\d+[.．、]', text): return None
    key = title_key(text)
    matches = [title for title in titles if len(title_key(title)) >= 5 and
               (key == title_key(title) or key.startswith(title_key(title)) and len(key) <= len(title_key(title)) + 16)]
    # Parent titles can be prefixes of leaf titles, and numbered aliases can
    # normalize to the same visible heading. Prefer the most specific match;
    # aliases of that same text retain the first (selected target is first).
    if not matches: return None
    longest=max(len(title_key(title)) for title in matches)
    matches=[title for title in matches if len(title_key(title))==longest]
    if len({title_key(title) for title in matches})>1: raise Hold('章节标题有歧义，不能自动归属题答。')
    return matches[0]


def select_section(pages_with_lines, target, titles, *, require_roles=('question','answer')):
    from annotation.recognition.offline import detect_columns
    import numpy as np
    from PIL import Image
    titles = list(dict.fromkeys([target, *titles])); results = []
    active_by_role = {'question': None, 'answer': None}
    seen_anchor = {'question': None, 'answer': None}
    for page, raw_lines in pages_with_lines:
        with Image.open(page['raw_path']) as image:
            layout = detect_columns(np.asarray(image.convert('L')) < 160, raw_lines)
        cut = layout['cut_x'] if layout['mode'] == 'two_columns' else None
        columns = 2 if cut is not None else 1
        role = page['role']; active = active_by_role[role]
        assigned = []
        for index, original in enumerate(raw_lines):
            line = copy.deepcopy(original)
            line['original_line_id'] = line.get('line_id')
            line['line_id'] = page['asset_id'] + '/line/' + str(index)
            line['column'] = 0 if cut is None or (line['bbox'][0] + line['bbox'][2]) / 2 < cut else 1
            line['heading'] = heading(line['text'], titles)
            assigned.append(line)
        across = [l for l in assigned if cut is not None and l['bbox'][0] < cut < l['bbox'][2]]
        spanning = [l for l in across if l['heading'] is not None]
        furniture = [l for l in across if role == 'answer' and l['bbox'][3] <= page['height'] * .1
                     and title_key(l['text']) in {'参考答案', '参考答案与解析', '参考答案及解析'}]
        # Only a heading above all ordinary columns can set the initial state.
        top_heading = min(spanning, key=lambda l:l['bbox'][1], default=None)
        if top_heading is not None:
            if any(l['bbox'][1] < top_heading['bbox'][1] and l not in across for l in assigned):
                raise Hold('跨栏标题上方还有正文，章节范围需核对。')
            active = top_heading['heading']; seen_anchor[role] = None
        selected, exclusions, windows, resets = [], [], [], []
        for column in range(columns):
            column_lines = sorted([l for l in assigned if l['column'] == column and l not in across], key=lambda l:(l['bbox'][1], l['bbox'][0]))
            # Use the observed column's first ink/text row, not the physical
            # paper edge. A page header/margin is not an unexplained body gap.
            current_start = top_heading['bbox'][3] if top_heading is not None else min((l['bbox'][1] for l in column_lines),default=0)
            window_start = current_start if active == target else None
            for line in column_lines:
                if line['bbox'][1] >= page['height'] * .95:
                    exclusions.append({'line_id':line['line_id'],'reason':'PAGE_FOOTER_BAND'}); continue
                if line['heading'] is not None:
                    if active == target and window_start is not None:
                        windows.append({'column':column,'y_range':[window_start,line['bbox'][1]],'path':[target]})
                    active = line['heading']; seen_anchor[role] = None
                    window_start = line['bbox'][3] if active == target else None
                    exclusions.append({'line_id':line['line_id'],'reason':'SECTION_HEADING'}); continue
                if active != target:
                    exclusions.append({'line_id':line['line_id'],'reason':'OUTSIDE_SELECTED_SECTION'}); continue
                match = re.match(r'^\s*(\d+)[.．、]',line['text'])
                if match:
                    number = int(match[1]); prior = seen_anchor[role]
                    if number == 1 and prior is not None and prior > 1:
                        resets.append(line['line_id']); active = None
                        if window_start is not None: windows.append({'column':column,'y_range':[window_start,line['bbox'][1]],'path':[target]})
                        window_start = None; continue
                    seen_anchor[role] = max(number, prior or 0)
                line['location'] = {'column':column,'window_index':len(windows),'section_path':[target]}
                selected.append(line)
            if active == target and window_start is not None:
                windows.append({'column':column,'y_range':[window_start,page['height'] * .95],'path':[target]})
        exclusions += [{'line_id':l['line_id'],'reason':'ANSWER_PAGE_HEADER'} for l in furniture]
        if any(l not in spanning and l not in furniture and l['bbox'][1] < page['height']*.95 for l in across):
            raise Hold('章节正文跨栏，当前范围分配有歧义。')
        if resets: raise Hold('选定章节出现无标题题号重置，不能继续串答。')
        active_by_role[role] = active
        details = []
        parent_map = {l['original_line_id']:l for l in selected if l['original_line_id']}
        for old in page.get('historical_detail_lines', []):
            parent = parent_map.get(old.get('parent_line_id'))
            if parent is None: continue
            detail = copy.deepcopy(old)
            detail['line_id'] = parent['line_id'] + '/detail/' + str(len(details))
            detail['parent_line_id'] = parent['line_id']; detail['location'] = copy.deepcopy(parent['location'])
            details.append(detail)
        results.append({'page':page,'lines':selected,'windows':windows,'details':details,'exclusions':exclusions,
                        'section_start_observed': any(l['heading'] == target for l in assigned),
                        'continuation_at_end':active == target,'columns':columns,'cut_x':cut})
    for role in require_roles:
        if not any(r['page']['role']==role and r['section_start_observed'] for r in results):
            raise Hold('所选来源没有识别到完整章节标题：' + role + '。请扩展普通页范围或核对标题。')
    return results
