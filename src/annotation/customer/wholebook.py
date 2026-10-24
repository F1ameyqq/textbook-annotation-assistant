"""Existing full-page OCR database -> ordinary offline preparation and review.

The source database is opened read-only in one transaction. Its page rows and
observed item spans are retained unchanged; no OCR, platform client or writer
is started here. A repeated printed label never establishes instance identity.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import sqlite3

from .store import Hold, byte_hash, digest, encoded


def read_source(path, selected=None):
    path = Path(path).resolve(strict=True)
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute('BEGIN')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'pages', 'scopes', 'scope_summary', 'scope_windows', 'source_items', 'machine_counts'} <= tables:
            raise Hold('全书来源分段尚未完成，请等待原识别进程完成。')
        scopes = [dict(r) for r in db.execute('SELECT * FROM scope_summary ORDER BY rowid')]
        if selected and set(selected) - {r['id'] for r in scopes}:
            raise Hold('所选来源目录不存在。')
        paths = {r['id']: json.loads(r['path']) for r in db.execute('SELECT id,path FROM scopes')}
        result = []
        for scope in scopes:
            if selected and scope['id'] not in selected:
                continue
            windows = [dict(r) for r in db.execute(
                'SELECT * FROM scope_windows WHERE scope_id=? ORDER BY role DESC,page,column,y0', (scope['id'],))]
            items = []
            for row in db.execute('SELECT * FROM source_items WHERE scope_id=? ORDER BY role DESC,start_page,start_row,item_id', (scope['id'],)):
                item = dict(row); item['fragments'] = json.loads(item.pop('fragments_json'))
                items.append(item)
            def order(item):
                first = item['fragments'][0] if item['fragments'] else {
                    'page': item['start_page'], 'column': 0, 'bbox': [0, item['start_row'], 0, 0]}
                return (item['role'] != 'question', first['page'], first['column'], first['bbox'][1], item['start_row'])
            items.sort(key=order)
            plan = {'schema': 'CustomerObservedSourcePlan/v1', 'bridge_version': '2', 'scope_id': scope['id'],
                    'windows': windows, 'items': items, 'path': paths.get(scope['id'], [scope['label']]),
                    'kind': scope['kind'], 'source_database': str(path)}
            count = db.execute('SELECT * FROM machine_counts WHERE scope_id=?', (scope['id'],)).fetchone()
            plan['machine_counts'] = dict(count) if count else None
            result.append(plan)
        numbers = sorted({w['page'] for p in result for w in p['windows']})
        pages = {}
        for n in numbers:
            row = db.execute('SELECT * FROM pages WHERE page=?', (n,)).fetchone()
            if row is None: raise Hold('来源分段引用了尚未识别的页面。')
            pages[n] = dict(row)
        for plan in result:
            plan['page_rows'] = {str(n): digest(json.loads(pages[n]['rows_json']))
                                 for n in sorted({w['page'] for w in plan['windows']})}
            plan['empty_rows'] = {str(n): [i for i, row in enumerate(json.loads(pages[n]['rows_json'])) if not row[1].strip()]
                                  for n in sorted({w['page'] for w in plan['windows']})}
        return pages, result
    finally:
        db.close()


def import_database_pages(store, book, pages):
    from annotation.recognition.offline import artifact
    from .recognition_cache import import_evidence, cached_page
    from .source import validate_lines
    from PIL import Image
    directory = store.root / 'wholebook-cache'; directory.mkdir(exist_ok=True)
    for n, page in pages.items():
        image = Path(page['image'])
        if byte_hash(image.read_bytes()) != page['sha']:
            raise Hold('全书来源原图摘要不一致：' + str(n))
        with Image.open(image) as opened:
            if list(opened.size) != [page['width'], page['height']]:
                raise Hold('全书来源尺寸不一致：' + str(n))
        rows = json.loads(page['rows_json']); lines = []
        if page['method'] not in {'REUSED_FULL_PAGE', 'FULL_PAGE_RAPIDOCR_CPU'}:
            raise Hold('来源不是完整页面 OCR，不能当作全页缓存。')
        for i, (quad, text, score) in enumerate(rows):
            if not text.strip(): continue  # raw empty detections remain in payload below
            lines.append({'line_id': f'wholebook/{n}/row/{i}', 'source_row_index': i, 'source_rows_hash': digest(rows),
                          'text': text, 'score': score,
                          'bbox': [min(v[0] for v in quad), min(v[1] for v in quad),
                                   max(v[0] for v in quad), max(v[1] for v in quad)]})
        validate_lines(lines, page['width'], page['height'])
        retained = cached_page(store, {'raw_sha256': page['sha'], 'width': page['width'], 'height': page['height']}, book)
        if retained is not None:
            if retained['lines'] != lines: raise Hold('同源旧识别行不同，不能覆盖全书识别缓存。')
            continue
        source = {'asset_id': 'wholebook-page-' + str(n), 'sha256': page['sha'],
                  'width': page['width'], 'height': page['height']}
        payload = {'pages': [{'source': source, 'ocr_lines': lines}], 'raw_rows': rows,
                   'retained_rows_hash': digest(rows), 'method': page['method']}
        target = directory / (digest([book, payload]) + '.json')
        if not target.exists():
            evidence = artifact('b-evidence-trial/0.2', 'EvidenceBundleTrial',
                {'book_id': book, 'scope_id': 'wholebook-page-' + str(n)}, payload, [],
                {'module': __name__, 'ocr_enabled': True, 'ocr_execution': 'RETAINED_DATABASE_OBSERVATION',
                 'original_engine': 'rapidocr_onnxruntime.RapidOCR', 'new_model_calls': 0})
            with target.open('xb') as stream: stream.write(encoded(evidence))
        else:
            existing = json.loads(target.read_bytes())
            if existing.get('payload') != payload: raise Hold('既有全书识别桥接原件已变化。')
        import_evidence(store, target)


def prepare_book(store, database, *, book, scope_ids=None):
    """One offline subcommand; existing jobs resume without producing anything."""
    from .prepare import prepare
    pages, plans = read_source(database, scope_ids)
    ordinary = [p for p in plans if p['kind'] != 'EXTRA_PAPER']
    needed = {w['page'] for p in ordinary for w in p['windows']}
    page_errors = {}
    for n in sorted(needed):
        try: import_database_pages(store, book, {n: pages[n]})
        except (Hold, OSError, ValueError) as exc: page_errors[n] = str(exc)
    results = []
    for plan in plans:
        if plan['kind'] == 'EXTRA_PAPER':
            results.append({'scope_id': plan['scope_id'], 'status': 'READ_ONLY_EXTRA_PAPER'}); continue
        if not any(w['role'] == 'question' for w in plan['windows']):
            results.append({'scope_id': plan['scope_id'], 'status': 'SOURCE_WINDOWS_MISSING'}); continue
        if any(pages[w['page']]['width'] > pages[w['page']]['height'] for w in plan['windows']):
            results.append({'scope_id': plan['scope_id'], 'status': 'READ_ONLY_LANDSCAPE_SOURCE'}); continue
        errors = {str(w['page']): page_errors[w['page']] for w in plan['windows'] if w['page'] in page_errors}
        if errors:
            results.append({'scope_id': plan['scope_id'], 'status': 'SOURCE_CACHE_CONFLICT', 'errors': errors}); continue
        question = sorted({w['page'] for w in plan['windows'] if w['role'] == 'question'})
        answer = sorted({w['page'] for w in plan['windows'] if w['role'] == 'answer'})
        bound = {pages[n]['sha']: n for n in question + answer}
        try:
            job = prepare(store, book=book, lesson=plan['path'][-1],
                question_files=[pages[n]['image'] for n in question], answer_files=[pages[n]['image'] for n in answer],
                page_bindings=bound, directory_path=plan['path'], source_plan=plan)
        except Exception as exc:
            results.append({'scope_id': plan['scope_id'], 'status': 'PREPARATION_ERROR',
                            'message': str(exc), 'error_type': type(exc).__name__})
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)
            continue
        results.append({'scope_id': plan['scope_id'], 'job': job['id'], 'status': job['status'],
                        'candidates': len(job['candidates']), 'issues': len(job['issues']),
                        'message': job.get('last_message'), 'new_model_pages': job['metrics']['new_model_pages']})
        print(json.dumps({'scope': plan['scope_id'], 'status': job['status'],
                          'candidates': len(job['candidates'])}, ensure_ascii=False), flush=True)
    return {'schema': 'CustomerWholebookPreparation/v1', 'book_id': book, 'results': results,
            'new_model_calls': 0, 'platform_actions': [], 'workspace': str(store.root)}


def locate_plan(observations, plan, path):
    """Use observed half-page windows, including a mid-page spanning title."""
    if plan.get('schema') != 'CustomerObservedSourcePlan/v1' or plan['path'] != path:
        raise Hold('来源分段与所选目录不一致。')
    results = []
    for page, lines in observations:
        n, role = page['viewer_page'], page['role']
        if not lines or any(line.get('source_rows_hash') != plan.get('page_rows', {}).get(str(n)) for line in lines):
            raise Hold('缓存原始行与来源分段的摘要不一致。')
        windows = [w for w in plan['windows'] if w['page'] == n and w['role'] == role]
        if not windows: raise Hold('所选页面缺少来源分段。')
        item_rows = {i for item in plan['items'] if item['role'] == role
                     for f in item['fragments'] if f['page'] == n for i in f['row_indices']}
        chosen, exclusions, simple = [], [], []
        for w in windows:
            if not (0 <= w['x0'] < w['x1'] <= page['width'] and 0 <= w['y0'] < w['y1'] <= page['height']):
                raise Hold('来源分段坐标超出原图。')
            simple.append({'column': w['column'], 'y_range': [w['y0'], w['y1']], 'path': list(path)})
        for i, original in enumerate(lines):
            row = original.get('source_row_index')
            if type(row) is not int: raise Hold('全书缓存缺少原始行编号。')
            line = copy.deepcopy(original); x0, y0, x1, _ = line['bbox']
            hits = [(j, w) for j, w in enumerate(windows)
                    if w['x0'] <= (x0+x1)/2 < w['x1'] and w['y0'] <= y0 < w['y1']]
            line['original_line_id'] = line['line_id']; line['line_id'] = page['asset_id'] + '/line/' + str(i)
            if len(hits) != 1:
                if row in item_rows: raise Hold('题目片段越过来源分段或落入重叠窗口。')
                exclusions.append({'line_id': line['line_id'], 'reason': 'OUTSIDE_OBSERVED_SOURCE_WINDOW'}); continue
            j, w = hits[0]
            line['location'] = {'column': w['column'], 'window_index': j, 'section_path': list(path)}
            chosen.append(line)
        results.append({'page': page, 'lines': chosen, 'windows': simple, 'details': [],
                        'exclusions': exclusions, 'columns': len({w['column'] for w in windows}),
                        'cut_x': page['width']/2, 'section_start_observed': all(w['start_observed'] for w in windows),
                        'continuation_at_end': False})
    return results


def assemble_plan(evidence, original_graph, plan, path):
    """Carry exact item instances across pages; pair only unique kind+label.

    Inline answer slices retain their complete OCR box and raw character span.
    Shared geometry stays an explicit review issue, never a fabricated box.
    """
    from annotation.recognition.offline import artifact, OPTION, ref
    from annotation.recognition.answer_assembly import _role_pieces
    page_map = {p['asset_id']: p for p in evidence['payload']['pages']}
    raw = {(p['page_role'], line['source_row_index'], p['asset_id']): line
           for p in page_map.values() for line in p['ocr_lines']}
    # viewer numbers are retained in the preparation plan's page bindings.
    by_number = {}
    for p in page_map.values():
        candidates = [w['page'] for w in plan['windows'] if w['role'] == p['page_role']
                      and plan.get('page_assets', {}).get(str(w['page'])) == p['asset_id']]
        if candidates: by_number[p['page_role'], candidates[0]] = p
    if not by_number: raise Hold('全书装配缺少原页到素材的绑定。')
    exclusions = []

    def furniture(page, line):
        compact = re.sub(r'\s+', '', line['text'])
        if re.fullmatch(r'[ABC]?(?:基础题|中档题|综合题|针对训练|巩固训练)[《〈«>]*', compact):
            return 'EXCLUDED_TIER_HEADING'
        x0, y0, x1, _ = line['bbox']; source = page['source']
        if (compact.isdigit() and y0 >= source['height']*.94
                and (x0 <= source['width']*.15 or x1 >= source['width']*.85)):
            return 'EXCLUDED_MARGIN_PAGE_NUMBER'
        return None

    def fragments(item, answer=False):
        output = []; current_role = 'answer'; shared = False
        for part in item['fragments']:
            page = by_number.get((item['role'], part['page']))
            if page is None: raise Hold('来源题目片段的页面不在任务中。')
            spans = {}
            for span in part.get('text_spans', []):
                spans.setdefault(span['row_index'], []).append((span['start'], span['end']))
            for row in dict.fromkeys(part['row_indices']):
                line = raw.get((item['role'], row, page['asset_id']))
                if line is None:
                    if row in plan.get('empty_rows', {}).get(str(part['page']), []): continue
                    raise Hold('来源片段找不到原始 OCR 行。')
                reason = furniture(page, line)
                if reason:
                    exclusions.append({'line_id': line['line_id'], 'reason': reason}); continue
                text = line['text']; ranges = spans.get(row, [(0, len(text))])
                for lo, hi in ranges:
                    if type(lo) is not int or type(hi) is not int or not 0 <= lo < hi <= len(text):
                        raise Hold('来源答案文字区间无效。')
                    shared |= (lo != 0 or hi != len(text))
                    pieces = [(None, lo, hi)]
                    if answer:
                        if not output and item['kind'] in {'QUESTION', 'READING_TASK'}:
                            prefix = re.match(r'\s*(?:' + re.escape(item['label']) + r'\s*[.．、]|[（(]' +
                                              re.escape(item['label']) + r'[）)])\s*', text[lo:hi])
                            if prefix: lo += prefix.end()
                        pieces, current_role = _role_pieces(text, lo, hi, current_role)
                    for role, a, b in pieces:
                        displayed = text[a:b]
                        opt = OPTION.match(displayed) if not answer else None
                        role = role or ('option' if opt else 'stem')
                        output.append({'fragment_id': 'source-fragment-' + digest([item['item_id'], page['asset_id'], row, a, b, role])[:24],
                            'asset_id': page['asset_id'], 'column': part['column'], 'bbox': list(line['bbox']),
                            'text': displayed, 'raw_text': text, 'text_span': [a, b], 'role': role, 'content_type': 'text',
                            'option_label': opt[1] if opt else None, 'option_start': bool(opt),
                            'evidence_refs': [line['line_id']], 'parent_line_id': line['line_id'],
                            'geometry_precision': 'OCR_LINE_SHARED_TEXT_SPAN' if shared else 'OCR_ELEMENT'})
        return output, shared

    questions, answers, issues, materials = [], [], [], {}
    for item in plan['items']:
        if item['role'] == 'question' and item['kind'] == 'MATERIAL':
            body, _ = fragments(item); materials[item['item_id']] = body
    for item in plan['items']:
        if item['kind'] == 'MATERIAL': continue
        body, shared = fragments(item, item['role'] == 'answer')
        if not body:
            issues.append({'code': 'SOURCE_ITEM_EMPTY', 'detail': item['item_id']}); continue
        anchor_line = raw.get((item['role'], item['start_row'], by_number[item['role'], item['start_page']]['asset_id']))
        anchor = anchor_line['line_id'] if anchor_line else body[0]['evidence_refs'][0]
        common = {'book_id': evidence['book_id'], 'section_path': list(path), 'printed_number': item['label'],
                  'asset_id': body[0]['asset_id'], 'source_instance_id': item['item_id'],
                  'source_item_kind': item['kind'], 'verification_status': 'UNVERIFIED'}
        if item['role'] == 'answer':
            flags = ['ANSWER_ROLE_REGIONS_UNSPLIT'] if shared else []
            answers.append({**common, 'answer_id': 'a-' + digest(item['item_id'])[:24], 'fragments': body,
                'text': '\n'.join(f['text'] for f in body if f['role'] == 'answer'),
                'explanation_text': '\n'.join(f['text'] for f in body if f['role'] == 'explanation'),
                'complete': not shared, 'assembly_flags': flags, 'assembly_status': 'AMBIGUOUS' if shared else 'BOUNDED',
                'boundary': {'kind': 'OBSERVED_SOURCE_ITEM_SPANS'}, 'bbox': body[0]['bbox'],
                'evidence_refs': [ref for f in body for ref in f['evidence_refs']]})
        else:
            flags = []
            bare = {f['text'].strip() for f in body if re.fullmatch(r'[A-D]', f['text'].strip())}
            if bare == set('ABCD'): flags.append('FIGURE_EXTENT_UNVERIFIED')
            material = item.get('material_id')
            if material:
                if material in materials: body = copy.deepcopy(materials[material]) + body
                else: flags.append('SHARED_MATERIAL_STRUCTURE_REVIEW')
            questions.append({**common, 'question_id': 'q-' + digest(item['item_id'])[:24], 'anchor_ref': anchor,
                'fragments': body, 'flags': flags, 'candidate_answer_ids': [], 'selected_answer_id': None,
                'parent_question_id': None, 'material_id': material,
                'text': '\n'.join(f['text'] for f in body), 'type_candidate': 'UNVERIFIED'})
    for q in questions:
        matches = [a for a in answers if (a['source_item_kind'], a['printed_number']) ==
                   (q['source_item_kind'], q['printed_number'])]
        same_questions = [o for o in questions if (o['source_item_kind'], o['printed_number']) ==
                          (q['source_item_kind'], q['printed_number'])]
        q['candidate_answer_ids'] = [a['answer_id'] for a in matches]
        if len(matches) == len(same_questions) == 1: q['selected_answer_id'] = matches[0]['answer_id']
    payload = {'questions': questions, 'answers': answers, 'issues': issues, 'answer_coverage': [],
        'matching': 'scope+source_item_kind+printed_label; unique question and answer only',
        'unmatched_answer_ids': [a['answer_id'] for a in answers if not any(q['selected_answer_id'] == a['answer_id'] for q in questions)],
        'selection_status': 'DRAFT_UNVERIFIED', 'platform_actions': [],
        'original_assembly': original_graph, 'source_plan_hash': digest(plan), 'source_exclusions': exclusions}
    return artifact('b-graph-trial/0.2', 'QuestionGraphTrial', evidence, payload, [ref(evidence)],
                    {'module': __name__, 'version': '1', 'new_model_calls': 0})
