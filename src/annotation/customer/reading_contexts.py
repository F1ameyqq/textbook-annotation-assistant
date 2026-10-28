"""Read-only shared answer material, never an independent answer frame."""
from __future__ import annotations

import copy
import json
import math
import re

from .store import Hold


def need(value):
    if not value: raise Hold('阅读答案共享上下文与原始来源不一致。')


def compile_contexts(pages, plan):
    if not plan.get('reading_answer_contexts'): return []
    page_map = {p['asset_id']:p for p in pages}
    result = []
    for context in plan['reading_answer_contexts']:
        need(context['scope_id'] == plan['scope_id'])
        windows = []
        for number, column, x0, y0, x1, y1, title in json.loads(context['windows_json']):
            aid = plan['page_assets'][str(number)]; page = page_map[aid]; source = page['source']
            need(page['page_role'] == 'answer' and 0 <= x0 < x1 <= source['width'] and 0 <= y0 < y1 <= source['height'])
            windows.append({'asset_id':aid,'viewer_page':number,'column':column,'source_bbox':[x0,y0,x1,y1],
                'bbox':[math.floor(x0),math.floor(y0),math.ceil(x1),math.ceil(y1)],
                'source_sha256':source['sha256'],'source_dimensions':[source['width'],source['height']],
                'coordinate_space':'ORIGINAL_PIXELS','title_observation':title,
                'shared_answer_bbox':True,'content_approved':False})
        rows = []
        for ref in json.loads(context['rows_json']):
            aid = plan['page_assets'][str(ref['page'])]; page = page_map[aid]
            line = next((l for l in page['ocr_lines'] if l['source_row_index'] == ref['row_index']), None)
            need(line is not None and line['location'] is not None and line['location']['column'] == ref['column'])
            need(any(w['asset_id'] == aid and w['column'] == ref['column']
                     and w['source_bbox'][0] <= (line['bbox'][0]+line['bbox'][2])/2 < w['source_bbox'][2]
                     and w['source_bbox'][1] <= (line['bbox'][1]+line['bbox'][3])/2 < w['source_bbox'][3] for w in windows))
            rows.append({**copy.deepcopy(ref),'asset_id':aid,'line_id':line['line_id'],
                         'text':line['text'],'bbox':copy.deepcopy(line['bbox'])})
        anchors = []
        for item in plan['items']:
            if item['role'] != 'answer' or item['kind'] != 'READING_TASK': continue
            for part in item['fragments']:
                if part.get('shared_reading_context_id') != context['context_id']: continue
                need(part.get('shared_answer_bbox') is True and part.get('anchor_only') is True)
                for span in part['text_spans']:
                    row = next((r for r in rows if (r['page'],r['column'],r['row_index']) ==
                                (part['page'],part['column'],span['row_index'])), None)
                    need(row is not None and type(span['start']) is int and type(span['end']) is int
                         and 0 <= span['start'] < span['end'] <= len(row['text']))
                    text = row['text'][span['start']:span['end']]
                    match = re.match(r'^\s*[（(]([1-9]\d?)[）)]',text)
                    need(match is not None and match[1] == item['label'])
                    need(any(w['viewer_page'] == part['page'] and w['column'] == part['column']
                             and w['source_bbox'] == part['bbox'] for w in windows))
                    anchors.append({'answer_item_id':item['item_id'],'printed_number':item['label'],
                        'line_id':row['line_id'],'asset_id':row['asset_id'],'text_span':[span['start'],span['end']],
                        'anchor_excerpt':text,'anchor_only':True})
        need(bool(anchors) and len({a['answer_item_id'] for a in anchors}) == len(anchors))
        result.append({'context_id':context['context_id'],'scope_id':plan['scope_id'],'windows':windows,
            'source_rows':rows,'anchors':anchors,'status':'SHARED_READING_SOURCE_REVIEW',
            'independent_answer_frame':False,'source_checked':False,'content_approved':False})
    return result


def candidates(candidate, graph, evidence):
    if candidate.get('source_item_kind') != 'READING_TASK': return []
    question = next(q for q in graph['payload']['questions'] if q['question_id'] == candidate['question_id'])
    if question.get('selected_answer_id') is not None: return []
    answers = {a['source_instance_id']:a for a in graph['payload']['answers'] if a.get('source_item_kind') == 'READING_TASK'}
    result = []
    for context in evidence['payload'].get('reading_answer_contexts', []):
        for anchor in context['anchors']:
            answer = answers.get(anchor['answer_item_id'])
            if (answer is None or anchor['printed_number'] != candidate['printed_number']
                    or answer.get('source_block_key') != candidate.get('source_block_key')): continue
            result.append({**copy.deepcopy(anchor),'context_id':context['context_id'],
                'windows':copy.deepcopy(context['windows']),'source_rows':copy.deepcopy(context['source_rows']),
                'status':'SHARED_READING_SOURCE_REVIEW','independent_answer_frame':False,
                'selected':False,'source_checked':False,'content_approved':False})
    return result
