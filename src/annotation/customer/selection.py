"""Explicit bounded production selections without dismissing global issues."""
import copy
import math
from .store import Hold, digest
from .prepare import candidate_hash

READY = {'READY_EXACT_TEXT', 'READY_CUSTOMER_REVIEWED', 'READY_SOURCE_CHECKED'}


def unmatched_scope_issue(job, graph, evidence):
    """Retain unmatched IDs and attach exact, conservative source ownership."""
    ids = graph['payload']['unmatched_answer_ids']
    issue = {'code':'UNMATCHED_ANSWERS','evidence_refs':list(ids)}
    if not job.get('source_plan'): return issue
    rows = []
    for identity in ids:
        answers = [a for a in graph['payload']['answers'] if a['answer_id'] == identity]
        if len(answers) != 1: return issue
        answer = answers[0]
        owners = [q for q in graph['payload']['questions'] if q.get('source_pairing_status', {}).get('answer_item_id') == answer.get('source_instance_id')]
        if len(owners) != 1 or owners[0]['selected_answer_id'] is not None: return issue
        owner = owners[0]; candidates = [c for c in job['candidates'] if c['question_id'] == owner['question_id']]
        if len(candidates) != 1: return issue
        candidate = candidates[0]
        rows.append({'answer_id':identity,'answer_item_id':answer['source_instance_id'],
            'question_item_id':owner['source_instance_id'],'candidate_key':candidate['key'],
            'owner_content_hash':candidate_hash(candidate),
            'question_regions':copy.deepcopy([f for f in candidate['frames'] if f['zone'] in {'question','choice'}]),
            'answer_regions':[{'asset_id':f['asset_id'],'bbox':copy.deepcopy(f['bbox']),
                               'line_ids':list(f['evidence_refs'])} for f in answer['fragments']]})
    issue['scope_proof'] = {'schema':'ExactUnmatchedAnswerScope/v1','book_id':job['book_id'],
        'section_path':list(job['directory_path']),'source_plan_hash':digest(job['source_plan']),
        'evidence_hash':evidence['content_hash'],'unmatched_sources':rows}
    return issue


def _unmatched_disjoint(job, selected, evidence, issue):
    proof = issue.get('scope_proof', {})
    if (not evidence or not job.get('source_plan') or proof.get('schema') != 'ExactUnmatchedAnswerScope/v1'
            or proof.get('book_id') != job['book_id'] or proof.get('section_path') != job.get('directory_path')
            or proof.get('source_plan_hash') != digest(job['source_plan']) or proof.get('evidence_hash') != evidence.get('content_hash')):
        return False
    rows = proof.get('unmatched_sources', []); ids = issue.get('evidence_refs', [])
    if (type(rows) is not list or type(ids) is not list or not rows or not ids
            or any(type(i) is not str for i in ids) or any(type(r) is not dict for r in rows)
            or len(set(ids)) != len(ids) or len(rows) != len(ids)
            or {r.get('answer_id') for r in rows} != set(ids)): return False
    pages = {p['asset_id']:p for p in evidence['payload']['pages']}
    lines = {l['line_id']:(p,l) for p in pages.values() for field in ('ocr_lines','answer_detail_lines') for l in p.get(field, [])}
    items = {i['item_id']:i for i in job['source_plan']['items']}
    pairings = {p['question_item_id']:p for p in job['source_plan'].get('pairing_status', [])}
    selected_ids = {c.get('source_instance_id') for c in selected}
    def valid_region(asset, box):
        p = pages.get(asset); source = p.get('source', {}) if p else {}
        return (type(box) is list and len(box) == 4 and all(type(v) in (int,float) and math.isfinite(v) for v in box)
                and 0 <= box[0] < box[2] <= source.get('width', 0) and 0 <= box[1] < box[3] <= source.get('height', 0))
    def touches(region):
        return any(f['asset_id'] == region['asset_id'] and max(f['bbox'][0],region['bbox'][0]) < min(f['bbox'][2],region['bbox'][2])
                   and max(f['bbox'][1],region['bbox'][1]) < min(f['bbox'][3],region['bbox'][3]) for c in selected for f in c['frames'])
    for row in rows:
        qid, aid = row.get('question_item_id'), row.get('answer_item_id')
        if type(qid) is not str or type(aid) is not str: return False
        question, answer, pairing = items.get(qid, {}), items.get(aid, {}), pairings.get(qid, {})
        if (qid in selected_ids or question.get('role') != 'question' or answer.get('role') != 'answer'
                or question.get('kind') != answer.get('kind') or question.get('label') != answer.get('label')
                or pairing.get('answer_item_id') != aid or pairing.get('status') != 'CUSTOMER_REVIEW'): return False
        owners = [c for c in job['candidates'] if c.get('source_instance_id') == qid and c['key'] == row.get('candidate_key')]
        if len(owners) != 1 or candidate_hash(owners[0]) != row.get('owner_content_hash'): return False
        actual = [f for f in owners[0]['frames'] if f['zone'] in {'question','choice'}]
        if not actual or row.get('question_regions') != actual: return False
        for region in actual:
            source = pages.get(region['asset_id'], {}).get('source', {})
            if (not valid_region(region['asset_id'], region['bbox']) or region.get('source_sha256') != source.get('sha256')
                    or region.get('source_dimensions') != [source.get('width'),source.get('height')] or touches(region)): return False
        if not row.get('answer_regions'): return False
        observed_rows = set()
        for region in row['answer_regions']:
            if not valid_region(region.get('asset_id'), region.get('bbox')) or touches(region): return False
            refs = region.get('line_ids', [])
            if len(refs) != 1 or refs[0] not in lines: return False
            page, line = lines[refs[0]]
            if (page['page_role'] != 'answer' or page['asset_id'] != region['asset_id'] or line['bbox'] != region['bbox']
                    or not line.get('location') or line['location']['section_path'] != proof['section_path']): return False
            raw = line if type(line.get('source_row_index')) is int else lines.get(line.get('parent_line_id'), ({},{}))[1]
            if type(raw.get('source_row_index')) is not int: return False
            observed_rows.add((page['asset_id'],raw['source_row_index']))
        expected_rows = {(job['source_plan']['page_assets'][str(part['page'])],r) for part in answer['fragments'] for r in part['row_indices']
                         if r not in job['source_plan'].get('empty_rows', {}).get(str(part['page']), [])}
        if observed_rows != expected_rows: return False
    return True


def blockers(job, selected, evidence=None):
    if not job['issues']:
        return []
    lines = {line['line_id']: (page, line) for page in (evidence or {}).get('payload', {}).get('pages', [])
             for line in page.get('ocr_lines', [])}
    result = []
    for issue in job['issues']:
        if issue['code'] == 'UNMATCHED_ANSWERS' and _unmatched_disjoint(job, selected, evidence, issue):
            continue
        # Only explicitly located orphan answer lines can be proved disjoint.
        # Unknown geometry, unscoped material and unmatched identities stay held.
        if issue['code'] not in {'UNASSIGNED_ANSWER_OCR_LINE', 'AMBIGUOUS_EMBEDDED_ANSWER_MARKERS'}:
            result.append(issue); continue
        refs = issue.get('evidence_refs', [])
        safe = bool(refs)
        for ref in refs:
            pair = lines.get(ref)
            if pair is None:
                safe = False; break
            page, line = pair
            if page['page_role'] != 'answer' or not line.get('location'):
                safe = False; break
            for candidate in selected:
                if line['location']['section_path'] != candidate['section_path']:
                    safe = False; break
                for frame in candidate['frames']:
                    if frame['asset_id'] != page['asset_id']: continue
                    a, b = line['bbox'], frame['bbox']
                    if max(a[0],b[0]) < min(a[2],b[2]) and max(a[1],b[1]) < min(a[3],b[3]):
                        safe = False; break
                if not safe: break
            if not safe: break
        if not safe: result.append(issue)
    return result


def select(store, job, keys=None):
    if keys is None:
        if job['status'] != 'PREPARED_OFFLINE' or job['issues']:
            raise Hold('请先处理整个任务的异常，或明确选择已经通过检查的题目。')
        selected = job['candidates']
    else:
        if type(keys) is not list or not keys or any(type(k) is not str for k in keys) or len(set(keys)) != len(keys):
            raise Hold('请选择一个或多个具体题目。')
        by_key = {q['key']: q for q in job['candidates']}
        if any(k not in by_key for k in keys): raise Hold('所选题目已经变化。')
        selected = [q for q in job['candidates'] if q['key'] in keys]
    if not selected or any(q['content_status'] not in READY or q['issues'] for q in selected):
        raise Hold('所选题目仍有内容异常。')
    evidence = store.get(job['evidence_ref']) if job.get('evidence_ref') else None
    if blockers(job, selected, evidence): raise Hold('存在涉及所选题目或范围不明的来源异常。')
    return selected
