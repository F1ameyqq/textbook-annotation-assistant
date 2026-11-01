"""Evidence-bound non-contiguous text occupancy and explicit figure-label repair.

No OCR, content inference, source writes, platform or filesystem access.
Unknown mappings retain the whole frame. Only the ordinary review operator can
transfer a fully contained, non-anchor fragment from an unsaved question.
"""
from __future__ import annotations

import copy
import math

from .source_review_projection import project_candidate


def intersects(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def contains(a, b):
    return a[0] <= b[0] and a[1] <= b[1] and a[2] >= b[2] and a[3] >= b[3]


def _union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def _box(value, size):
    return (isinstance(value, (list, tuple)) and len(value) == 4
            and all(type(v) in (int, float) and math.isfinite(v) for v in value)
            and 0 <= value[0] < value[2] <= size[0] and 0 <= value[1] < value[3] <= size[1])


def occupancy(job, graph, evidence):
    """Refine a text frame only when EVERY declared fragment has raw evidence."""
    entries = []
    try:
        line_pairs = [(line['line_id'], (page, line)) for page in evidence['payload']['pages']
                      for line in page['ocr_lines']]
        raw_lines = dict(line_pairs)
        if len(raw_lines) != len(line_pairs): raw_lines = {}
        questions = {q['question_id']: q for q in graph['payload']['questions']}
    except (KeyError, TypeError):
        raw_lines, questions = {}, {}
    for candidate in job['candidates']:
        try:
            projection = project_candidate(candidate, graph, evidence)
            fragments = {s['frame_index']: [] for z in projection['zones'] for s in z['segments']}
            for zone in projection['zones']:
                for segment in zone['segments']:
                    fragments[segment['frame_index']].extend(segment['fragments'])
        except (KeyError, TypeError, ValueError):
            fragments = {}
        anchor = questions.get(candidate.get('question_id'), {}).get('anchor_ref')
        for index, frame in enumerate(candidate['frames']):
            common = {'owner_key': candidate['key'], 'printed_number': candidate['printed_number'],
                      'frame_index': index, 'zone': frame['zone'], 'asset_id': frame['asset_id'],
                      'source_sha256': frame.get('source_sha256'),
                      'source_dimensions': copy.deepcopy(frame.get('source_dimensions')),
                      'frame_bbox': copy.deepcopy(frame['bbox'])}
            selected = fragments.get(index, [])
            ids = frame.get('source_fragment_ids', [])
            refined = frame.get('content_type') == 'text' and ids and len(set(ids)) == len(ids)
            refined = refined and len(selected) == len(ids) and {f['fragment_id'] for f in selected} == set(ids)
            raw_boxes = {}
            if refined:
                for fragment in selected:
                    refs = fragment.get('evidence_refs', [])
                    if not refs or len(set(refs)) != len(refs):
                        refined = False; break
                    boxes = []
                    for ref in refs:
                        raw_page, line = raw_lines.get(ref, ({}, {}))
                        source = raw_page.get('source', {})
                        if (raw_page.get('asset_id') != frame['asset_id']
                                or source.get('sha256') != frame.get('source_sha256')
                                or [source.get('width'), source.get('height')] != frame.get('source_dimensions')
                                or not _box(line.get('bbox'), frame.get('source_dimensions', []))
                                or not contains(frame['bbox'], line['bbox'])):
                            refined = False; break
                        boxes.append(line['bbox'])
                    if not refined: break
                    raw_boxes[fragment['fragment_id']] = _union(boxes + [fragment['bbox']])
            if not refined:
                entries.append({**common, 'kind': 'WHOLE_FRAME_PROTECTED',
                                'bbox': copy.deepcopy(frame['bbox']), 'can_transfer': False})
                continue
            for fragment in selected:
                entries.append({**common, 'kind': 'VERIFIED_TEXT_FRAGMENT',
                    'fragment_id': fragment['fragment_id'], 'bbox': copy.deepcopy(raw_boxes[fragment['fragment_id']]),
                    'fragment_bbox': copy.deepcopy(fragment['bbox']), 'text': fragment.get('text', ''),
                    'evidence_refs': copy.deepcopy(fragment['evidence_refs']),
                    'can_transfer': (candidate.get('platform_status') == 'NOT_RUN'
                        and not candidate.get('acceptance_ref') and frame['zone'] in {'question', 'choice'}
                        and anchor not in fragment['evidence_refs'] and fragment.get('role') in {'stem', 'option'})})
    return entries


def plan_transfers(job, candidate, page, box, selections, graph, evidence):
    """Check exact UI selections; leave the job unchanged until all checks pass."""
    if type(selections) is not list:
        raise ValueError('SOURCE_TRANSFER_SELECTION_INVALID')
    if candidate.get('acceptance_ref') or candidate.get('platform_status') != 'NOT_RUN':
        raise ValueError('SAVED_SOURCE_TRANSFER_REFUSED')
    requested = []
    for item in selections:
        if type(item) is not dict or set(item) != {'owner_key', 'frame_index', 'fragment_id'}:
            raise ValueError('SOURCE_TRANSFER_SELECTION_INVALID')
        if not isinstance(item['owner_key'], str) or type(item['frame_index']) is not int or not isinstance(item['fragment_id'], str):
            raise ValueError('SOURCE_TRANSFER_SELECTION_INVALID')
        requested.append((item['owner_key'], item['frame_index'], item['fragment_id']))
    if len(set(requested)) != len(requested):
        raise ValueError('SOURCE_TRANSFER_SELECTION_DUPLICATE')
    hits = [entry for entry in occupancy(job, graph, evidence)
            if entry['owner_key'] != candidate['key'] and entry['asset_id'] == page['asset_id']
            and intersects(entry['bbox'], box)]
    result = []
    for entry in hits:
        key = (entry['owner_key'], entry['frame_index'], entry.get('fragment_id'))
        if (key not in requested or not entry['can_transfer'] or not contains(box, entry['bbox'])
                or not contains(box, entry.get('fragment_bbox', entry['bbox']))
                or entry['source_sha256'] != page['raw_sha256']
                or entry['source_dimensions'] != [page['width'], page['height']]):
            raise ValueError('SOURCE_OVERLAP_PROTECTED_OR_NOT_EXPLICITLY_REASSIGNED')
        result.append(copy.deepcopy(entry))
    if set(requested) != {(e['owner_key'], e['frame_index'], e['fragment_id']) for e in result}:
        raise ValueError('SOURCE_TRANSFER_SELECTION_STALE_OR_OUTSIDE_REGION')
    # A raw line still claimed elsewhere cannot be made free by one fragment selection.
    all_entries = occupancy(job, graph, evidence)
    for moved in result:
        for other in all_entries:
            if (other['owner_key'], other['frame_index'], other.get('fragment_id')) in requested:
                continue
            if set(moved['evidence_refs']) & set(other.get('evidence_refs', [])):
                raise ValueError('SOURCE_TRANSFER_SHARED_RAW_LINE_REFUSED')
    return result


def apply_transfers(job, candidate, image_frame, transfers, head, graph, evidence):
    """Move references only; never delete/rewrite current or original text."""
    changed = []
    before_occupancy = occupancy(job, graph, evidence)
    grouped = {}
    for entry in transfers:
        grouped.setdefault(entry['owner_key'], {}).setdefault(entry['frame_index'], []).append(entry)
    for owner, groups in grouped.items():
        donor = next(q for q in job['candidates'] if q['key'] == owner)
        if donor.get('acceptance_ref') or donor['platform_status'] != 'NOT_RUN':
            raise ValueError('SAVED_SOURCE_TRANSFER_REFUSED')
        log, revised = [], []
        for index, frame in enumerate(donor['frames']):
            if index not in groups:
                revised.append(frame); continue
            entries = groups[index]
            removed = {e['fragment_id'] for e in entries}
            before = copy.deepcopy(frame)
            revision = {
                'kind': 'CUSTOMER_EXPLICIT_FIGURE_LABEL_REASSIGNMENT', 'previous_head': head,
                'target_candidate_key': candidate['key'], 'target_image_bbox': copy.deepcopy(image_frame['bbox']),
                'previous_source_frame': before, 'moved_fragments': copy.deepcopy(entries),
                'content_rewritten': False, 'content_approved': False}
            remaining = [e for e in before_occupancy if e['owner_key'] == owner and e['frame_index'] == index
                         and e.get('fragment_id') not in removed]
            for entry in remaining:
                piece = copy.deepcopy(frame)
                piece['source_fragment_ids'] = [entry['fragment_id']]
                bounds = _union([entry['bbox'], entry['fragment_bbox']])
                piece['bbox'] = [math.floor(bounds[0]), math.floor(bounds[1]), math.ceil(bounds[2]), math.ceil(bounds[3])]
                piece.setdefault('source_region_reassignments', []).append(copy.deepcopy(revision))
                revised.append(piece)
            log.extend(entries)
        # Non-contiguous text gets separate frames; provenance is retained in both candidates.
        donor['frames'] = revised
        donor.setdefault('source_region_reassignment_history', []).append({
            'previous_head': head, 'target_candidate_key': candidate['key'], 'fragments': copy.deepcopy(log)})
        donor['source_reassignment_pending_zones'] = sorted(set(donor.get('source_reassignment_pending_zones', []))
                                                          | {e['zone'] for e in log})
        donor['issues'] = sorted(set(donor['issues']) | {'SOURCE_REGION_REASSIGNED_TEXT_CHECK', 'EDITED_CONTENT_REVIEW'})
        donor['review'] = None; donor['content_status'] = 'NEEDS_REVIEW'
        changed.append(donor)
    if transfers:
        image_frame['reassigned_source_fragments'] = copy.deepcopy(transfers)
        image_frame['binding']['source_assignment_checked'] = True
        image_frame['binding']['content_rewritten'] = False
    return changed
