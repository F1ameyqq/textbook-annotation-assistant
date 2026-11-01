"""Validate retained character boxes and source pixels without running OCR."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import re
import statistics
import unicodedata

from .store import Hold, byte_hash


def need(condition, detail):
    if not condition: raise Hold('字符几何来源不一致：' + detail)


def union(boxes):
    points = [p for box in boxes for p in box]
    return [min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points)]


def derive(pages, plan, sources):
    """Create detail observations; the original OCR rows remain unchanged."""
    if not plan.get('answer_geometry_links'): return []
    import numpy as np
    from PIL import Image
    original = {p['asset_id']:p for p in sources}
    evidence = {p['asset_id']:p for p in pages}
    observations = {o['observation_id']:o for o in plan['answer_geometry_observations']}
    groups = {g['group_id']:g for g in plan['answer_geometry_groups']}
    decisions = {d['group_id']:d for d in plan['answer_geometry_merge_decisions']}
    items = {i['item_id']:i for i in plan['items']}
    images, derived = {}, []
    normal = lambda text: unicodedata.normalize('NFKC', text)
    for link in plan['answer_geometry_links']:
        observation = observations[link['observation_id']]; group = groups[link['group_id']]
        item = items[link['answer_item_id']]; parts = item['fragments']
        need(len(parts) == 1, '组对应多个片段')
        part = parts[0]; number = observation['page']; aid = plan['page_assets'][str(number)]
        source = original[aid]; page = evidence[aid]; size = [source['width'], source['height']]
        parent = next((l for l in page['ocr_lines'] if l['source_row_index'] == observation['row_index']), None)
        need(page['page_role'] == item['role'] == 'answer' and parent is not None, '题答页绑定')
        need(observation['scope_id'] == plan['scope_id'] and observation['source_sha'] == source['raw_sha256'], '原图摘要')
        need(parent['text'] == observation['original_text'] == part['original_row_text'], '父行原文')
        decision = decisions[group['group_id']]
        need(group['observation_id'] == observation['observation_id'] == part['geometry_observation_id']
             and group['group_id'] == part['geometry_group_id']
             and decision['status'] == 'MERGED' and decision['existing_answer_id'] == item['item_id'], '合并关系')
        method = json.loads(observation['method_json'])
        need(method.get('observation_format') == 3 and method.get('engine') == 'rapidocr_onnxruntime'
             and method.get('return_word_box') is True and method.get('ink_threshold') == 160
             and method.get('minimum_character_confidence') == .85
             and method.get('maximum_white_column_ink_ratio') == .02
             and len(method.get('models', {})) >= 2
             and all(re.fullmatch(r'[0-9a-f]{64}', h) for h in method['models'].values()), '模型及测量方法')
        chars = json.loads(observation['char_texts_json']); boxes = json.loads(observation['char_boxes_json'])
        scores = json.loads(observation['char_scores_json']); gaps = json.loads(observation['gaps_json'])
        a, b = json.loads(group['char_span_json']); proof = json.loads(group['proof_json'])
        need(len(chars) == len(boxes) == len(scores) and 0 <= a < b <= len(chars)
             and ''.join(chars) == observation['ocr_text']
             and normal(observation['ocr_text']) == normal(observation['original_text'])
             and all(len(normal(c)) == 1 for c in chars), '字符序列')
        need(all(len(box) == 4 and all(len(p) == 2 and all(type(v) in (int,float) and math.isfinite(v) for v in p)
                 and 0 <= p[0] <= size[0] and 0 <= p[1] <= size[1] for p in box) for box in boxes), '字框坐标')
        text = ''.join(chars[a:b]); box = json.loads(group['bbox_json'])
        need(text == group['text'] == part['observation_text'] and box == part['bbox'] == union(boxes[a:b])
             and proof == part['geometry_proof'] and proof['original_char_span'] == [a,b]
             and part['row_indices'] == [observation['row_index']]
             and part['text_spans'] == [{'row_index':observation['row_index'],'start':a,'end':b}], '组文字与范围')
        match = re.match(r'^([1-9]\d?)[.、．]', normal(text))
        need(match is not None and match[1] == item['label'] == group['printed_number']
             and bool(text[match.end():].strip()) and not re.search(r'\d+\.\d+', normal(text[match.end():]))
             and not re.search(r'[A-G][1-9]\d?[.、]', normal(text[match.end():])), '完整题号边界')
        need(group['status'] == 'VERIFIED_PIXEL_GAP' and observation['status'] == 'PIXEL_GROUPS_OBSERVED'
             and min(scores[a:b]) >= .85 and abs(proof['minimum_confidence']-min(scores[a:b])) < 1e-8, '识别置信度')
        windows = [w for w in plan['windows'] if w['role'] == 'answer' and w['page'] == number and w['column'] == part['column']]
        need(any(w['x0'] <= (box[0]+box[2])/2 < w['x1'] and w['y0'] <= (box[1]+box[3])/2 < w['y1'] for w in windows), '答案窗口')
        if aid not in images:
            need(byte_hash(Path(source['raw_path']).read_bytes()) == source['raw_sha256'], '像素文件摘要')
            with Image.open(source['raw_path']) as opened:
                need(list(opened.size) == size, '原图尺寸')
                images[aid] = np.asarray(opened.convert('L'))
        median = statistics.median(max(p[0] for p in q)-min(p[0] for p in q) for q in boxes)
        for edge, offset in (('left_gap', a), ('right_gap', b)):
            gap = proof[edge]; at_edge = offset == (0 if edge == 'left_gap' else len(chars))
            need(proof['at_row_start' if edge == 'left_gap' else 'at_row_end'] == at_edge, '行端边界')
            if at_edge:
                need(gap is None, '行端空隙'); continue
            need(gap in gaps and gap['passed'] is True and gap['before_character'] == offset, '字间空隙归属')
            x0,y0,x1,y1 = gap['white_run_bbox']; need(all(type(v) is int for v in (x0,y0,x1,y1)), '白带整数坐标')
            need(0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]
                 and gap['white_run_width'] == x1-x0 and x1-x0 >= max(4,median), '白带宽度')
            need(gap['bbox'][0] <= x0 < x1 <= gap['bbox'][2] and gap['bbox'][1] == y0 and gap['bbox'][3] == y1, '白带范围')
            previous, following = boxes[offset-1], boxes[offset]
            need(max(p[0] for p in previous) < x0 < x1 <= min(p[0] for p in following)
                 and abs(gap['median_char_width']-median) < 1e-8, '白带与真实字框关系')
            white = (images[aid][y0:y1,x0:x1] < 160).mean(axis=0)
            need(bool((white <= .02).all()), '原图白带像素')
        identity = parent['line_id'] + '/character-geometry/' + group['group_id']
        detail = {'line_id':identity,'parent_line_id':parent['line_id'],'text':text,'bbox':box,
                  'score':min(scores[a:b]),'location':copy.deepcopy(parent['location']),
                  'geometry_group_id':group['group_id'],'geometry_verified':True}
        page['answer_detail_lines'].append(detail)
        derived.append({'item_id':item['item_id'],'page':number,'row':observation['row_index'],
            'asset_id':aid,'line_id':identity,'parent_line_id':parent['line_id'],'source_sha256':source['raw_sha256'],
            'bbox':box,'text':text,'char_span':[a,b],'original_row_text':parent['text'],
            'observation_id':observation['observation_id'],'group_id':group['group_id'],
            'char_boxes':copy.deepcopy(boxes[a:b]),'char_scores':copy.deepcopy(scores[a:b]),
            'proof':copy.deepcopy(proof),'method':copy.deepcopy(method),'new_model_calls':0})
    return derived
