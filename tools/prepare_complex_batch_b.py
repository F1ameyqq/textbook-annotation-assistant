"""Freeze four explicitly identified B cases; no C01 plans, OCR or platform calls."""
from pathlib import Path, PurePosixPath
import argparse
import copy
import hashlib
import io
import json
import zipfile
from PIL import Image

PACKAGE_SHA = '8c812330b93cc60b920f6ccd1cd7784f0afe8d293336166a586e1aeaab8231ad'
CASES = [
    ('q4-first-lesson', 'a-92c4d2164ab878c8e6d4c88d', 'q-260d10c51f2b7c16fb6fefb5', '13', 1, 0, 0),
    ('q4-topic-fraction', 'a-35b5bc7421c65d9fcaa47e33', None, r'2或\frac{25}{8}', 3, 1, 1),
    ('q9-reflection-continuation', 'a-9a6c21dd0fe88b1059b7919e', None, None, 33, 15, None),
    ('q16-unit2-formulas', 'a-7302d4870826c53aea0bcd16', None, None, 17, 3, 11),
]
ASSETS = {
    'viewer-10': 'base/source/assets/46007447_viewer_10.jpg',
    'viewer-173': 'base/source/assets/46007447_viewer_173.jpg',
    'resource-173': 'base/source/adjacent/46007447_resource_173.jpg',
}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode('utf-8')

def need(ok, code):
    if not ok:
        raise ValueError(code)

def ref(value):
    return {k: value[k] for k in ('artifact_id', 'revision', 'content_hash')}

def load_package(path):
    raw = Path(path).read_bytes()
    need(sha(raw) == PACKAGE_SHA, 'FIXED_PACKAGE_HASH')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        need(len(names) == len(set(names)), 'DUPLICATE_ZIP_MEMBER')
        for name in names:
            p = PurePosixPath(name)
            need(not p.is_absolute() and '..' not in p.parts and '\\' not in name, 'UNSAFE_ZIP_MEMBER')
        manifest = json.loads(z.read('manifest.json'))
        for row in manifest['files']:
            b = z.read(row['path'])
            need(sha(b) == row['sha256'] and len(b) == row['bytes'], 'PACKAGE_MEMBER_HASH')
        return {n: z.read(n) for n in names if not n.endswith('/')}

def build(members):
    graph_raw = members['reference/final/graph.json']
    graph = json.loads(graph_raw)
    payload = graph['payload']
    need(graph['schema_version'] == 'b-graph-trial/0.8' and payload['decision'] == 'HOLD'
         and not payload['business_acceptance'], 'FIXED_GRAPH_SCOPE')
    answers = {a['answer_id']: a for a in payload['answers']}
    images = {}
    output = {}
    evidence = json.loads(members['inline/evidence.json'])
    descriptors = {p['asset_id']: p['source'] for p in evidence['payload']['pages']}
    for aid, source_path in ASSETS.items():
        raw = members[source_path]
        d = descriptors[aid]
        im = Image.open(io.BytesIO(raw))
        need(sha(raw) == d['sha256'] and im.size == (d['width'], d['height']), 'ASSET_BYTES_OR_SIZE')
        images[aid] = {'asset_id': aid, 'sha256': sha(raw), 'width': im.width, 'height': im.height,
                       'path': f'assets/{aid}.jpg', 'external_refs': d['external_refs'],
                       'content_coverage': 'QUESTION_REGIONS_ONLY' if aid == 'viewer-10' else 'SELECTED_ANSWER_REGIONS_ONLY'}
        if aid == 'resource-173':
            images[aid]['external_refs'] = dict(d['external_refs'], viewer_page=None)
        output[images[aid]['path']] = raw
    cases = []
    for key, answer_id, question_id, expected_text, fragments, render_count, formulas in CASES:
        answer = answers[answer_id]
        questions = [q for q in payload['questions'] if q.get('selected_answer_id') == answer_id]
        need(len(questions) == (1 if question_id else 0), 'QUESTION_SOURCE_NOT_ESTABLISHED')
        question = questions[0] if question_id else None
        need(question is None or question['question_id'] == question_id, 'WRONG_QUESTION_ID')
        if expected_text is not None:
            need(answer['text'] == expected_text, 'CONTENT_REGRESSION')
        need(len(answer['fragments']) == fragments and len(answer.get('render_regions', [])) == render_count,
             'FRAGMENT_OR_RENDER_COVERAGE')
        runs = [run for f in answer.get('content_fragments', []) for run in f.get('runs', [])]
        actual_formulas = sum(run['format'] == 'latex' for run in runs)
        if formulas is not None:
            need(actual_formulas == formulas, 'FORMULA_SLOT_COVERAGE')
        if key == 'q9-reflection-continuation':
            need(sum(r['content_type'] == 'image' for r in answer['render_regions']) == 5, 'FIGURE_COVERAGE')
            order = list(dict.fromkeys(r['asset_id'] for r in answer['render_regions']))
            need(order == ['viewer-173', 'resource-173'], 'CROSS_PAGE_READING_ORDER')
        if key == 'q16-unit2-formulas':
            need('60 61' in answer['text'] and '60，61' not in answer['text'], 'UNSUPPORTED_PUNCTUATION')
        case = {'case_id': key, 'book_id': graph['book_id'], 'question_id': question_id,
                'answer_id': answer_id, 'section_path': answer['section_path'],
                'printed_number': answer['printed_number'], 'decision': 'HOLD',
                'mode': 'QUESTION_ANSWER_CANDIDATE' if question_id else 'ANSWER_EVIDENCE_ONLY',
                'human_verified': False, 'joint_accepted': False, 'platform_eligible': False,
                'question_snapshot': question, 'answer_snapshot': answer,
                'source_asset_ids': sorted({f['asset_id'] for f in answer['fragments']}
                                           | ({question['asset_id']} if question else set())
                                           | {r['asset_id'] for r in answer.get('render_regions', [])}),
                'counts': {'raw_fragments': fragments, 'render_regions': render_count,
                           'latex_runs': actual_formulas},
                'blockers': ['A_CASE_INTERFACE_AND_POLICY_PENDING', 'CONTENT_AND_REGION_APPROVAL_PENDING']
                            + ([] if question_id else ['QUESTION_SOURCE_AND_ID_NOT_ESTABLISHED'])}
        cases.append(case)
        output[f'cases/{key}.json'] = encode(case)
    batch = {'schema_version': 'b-complex-batch-proposal/0.1', 'kind': 'ComplexCaseBatchProposal',
             'book_id': graph['book_id'], 'source_package_sha256': PACKAGE_SHA,
             'source_graph_ref': ref(graph), 'source_graph_file_sha256': sha(graph_raw),
             'a_reference_commit': 'e37606d74d7e538052c563d02df11c6c961b742f',
             'a_consumer_support': 'PENDING_A_EXTENSION', 'decision': 'HOLD',
             'business_acceptance': False, 'human_verified': False, 'platform_actions': [],
             'chapter_denominator': None, 'cases': cases, 'assets': list(images.values())}
    output['batch.json'] = encode(batch)
    return batch, output

def validate_batch(batch, original):
    """Fixed staging consumer; not a general C01 or business approval gate."""
    need(batch['decision'] == 'HOLD' and not batch['business_acceptance'] and not batch['human_verified']
         and batch['platform_actions'] == [] and batch['chapter_denominator'] is None, 'SCOPE_OR_APPROVAL_ESCALATION')
    need(batch['assets'] == original['assets'], 'ASSET_ALIAS_OR_IDENTITY_CHANGED')
    need(len(batch['cases']) == len(CASES), 'CASE_COVERAGE')
    for got, expected in zip(batch['cases'], original['cases']):
        need(got['case_id'] == expected['case_id'] and got['answer_id'] == expected['answer_id']
             and got['section_path'] == expected['section_path'], 'CROSS_SCOPE_OR_CASE_IDENTITY')
        need(got['question_id'] == expected['question_id'], 'FABRICATED_QUESTION_OR_RELATION')
        need(got['decision'] == 'HOLD' and not got['joint_accepted'] and not got['platform_eligible'], 'CASE_APPROVAL_ESCALATION')
        need(got['answer_snapshot'] == expected['answer_snapshot']
             and got['question_snapshot'] == expected['question_snapshot'], 'FROZEN_SNAPSHOT_CHANGED')

def rejection_checks(batch):
    mutations = []
    bad = copy.deepcopy(batch); bad['cases'][1]['answer_id'] = bad['cases'][0]['answer_id']
    mutations.append(('same-number-cross-scope-answer', bad, 'CROSS_SCOPE_OR_CASE_IDENTITY'))
    bad = copy.deepcopy(batch); bad['cases'][2]['question_id'] = batch['cases'][0]['question_id']
    mutations.append(('invented-q9-question-relation', bad, 'FABRICATED_QUESTION_OR_RELATION'))
    bad = copy.deepcopy(batch); bad['assets'][2]['asset_id'] = 'viewer-173'
    mutations.append(('resource-viewer-173-alias', bad, 'ASSET_ALIAS_OR_IDENTITY_CHANGED'))
    bad = copy.deepcopy(batch); bad['cases'][3]['joint_accepted'] = True
    mutations.append(('q1-approval-reused-on-q16', bad, 'CASE_APPROVAL_ESCALATION'))
    bad = copy.deepcopy(batch); bad['cases'][2]['answer_snapshot']['render_regions'].pop()
    mutations.append(('missing-q9-continuation-region', bad, 'FROZEN_SNAPSHOT_CHANGED'))
    bad = copy.deepcopy(batch)
    formula_runs = bad['cases'][3]['answer_snapshot']['content_fragments'][0]['runs']
    formula_runs.pop(next(i for i, run in enumerate(formula_runs) if run['format'] == 'latex'))
    mutations.append(('missing-q16-formula-run', bad, 'FROZEN_SNAPSHOT_CHANGED'))
    results = []
    for name, bad, expected in mutations:
        try:
            validate_batch(bad, batch)
        except ValueError as e:
            need(str(e) == expected, 'UNEXPECTED_REJECTION_LAYER')
            results.append({'case': name, 'rejected': True, 'code': str(e), 'layer': 'B_FIXED_BATCH_STAGING_ONLY'})
        else:
            raise ValueError('MUTATION_ACCEPTED:' + name)
    return results

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    members = load_package(args.package)
    batch, output = build(members)
    validate_batch(batch, batch)
    rejected = rejection_checks(batch)
    args.output.mkdir(parents=True, exist_ok=False)
    for name, raw in output.items():
        dest = args.output / name; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(raw)
    receipt = {'result': 'READY_FOR_A_EXTENSION_REVIEW_HOLD', 'business_acceptance': False,
               'cases': len(batch['cases']), 'question_answer_candidates': 1, 'answer_evidence_only': 3,
               'rejection_checks': rejected, 'new_ocr_calls': 0, 'platform_calls': 0,
               'new_simulation_dispatches': 0, 'source_package_sha256': PACKAGE_SHA,
               'source_graph_ref': batch['source_graph_ref'], 'batch_file_sha256': sha(output['batch.json']),
               'code_sha256': sha(Path(__file__).read_bytes())}
    (args.output / 'receipt.json').write_bytes(encode(receipt))
    manifest = [{'path': f.relative_to(args.output).as_posix(), 'bytes': f.stat().st_size,
                 'sha256': sha(f.read_bytes())} for f in sorted(args.output.rglob('*')) if f.is_file()]
    (args.output / 'manifest.json').write_bytes(encode({'files': manifest}))
    print(json.dumps({k:v for k,v in receipt.items() if k != 'rejection_checks'}, ensure_ascii=False))

if __name__ == '__main__':
    main()
