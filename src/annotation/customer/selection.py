"""Explicit bounded production selections without dismissing global issues."""
from .store import Hold

READY = {'READY_EXACT_TEXT', 'READY_CUSTOMER_REVIEWED', 'READY_SOURCE_CHECKED'}


def blockers(job, selected, evidence=None):
    if not job['issues']:
        return []
    lines = {line['line_id']: (page, line) for page in (evidence or {}).get('payload', {}).get('pages', [])
             for line in page.get('ocr_lines', [])}
    result = []
    for issue in job['issues']:
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
