"""Reconcile fixed local chapter sources and propose the previously disconnected Q16 link.

No website, OCR, model, graph mutation, C01 approval or platform execution.
The outputs are B-side source inventories and an unselected HOLD proposal.
"""
from pathlib import Path, PurePosixPath
import argparse
import copy
import hashlib
import io
import json
import sys
import zipfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    'observed': ('handoffs/b/46007447/B-46007447-observed-eight-sources-v2-PARTIAL-2026-10-17.zip',
                 'ec77d52ebcf25b3fec64579f63400c010cc08a623d71e20506e6ed46125ea695'),
    'question': ('tests/fixtures/book46007447/viewer15-question-draft-v4.zip',
                 '6c8850dc9fdb9dc220175e6ca48a9de704eed29d5965be1010c0aabacc906019'),
    'answers': ('handoffs/b/46007447/B-46007447-Q4-Q9-Q16-next-batch-HOLD-2026-10-19.zip',
                'b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673'),
}
PLAN_SHA = 'a7a5c43eb33d2e1378d0f82dc7375603a462dba64a60adbdb06f09a3a2f4ac99'
QID = 'q-457f1973a1426d29587d5752'
AID = 'a-7302d4870826c53aea0bcd16'
SECTION = ['第一章 勾股定理', '2 一定是直角三角形吗']
sha = lambda raw: hashlib.sha256(raw).hexdigest()
canonical = lambda obj: json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
encode = lambda obj: (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')

def need(condition, code):
    if not condition:
        raise ValueError(code)

def unpack_fixed(path, expected):
    raw = Path(path).read_bytes()
    need(sha(raw) == expected, 'FIXED_PACKAGE_SHA')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        need(len(names) == len(set(names)), 'DUPLICATE_PACKAGE_MEMBER')
        for name in names:
            p = PurePosixPath(name)
            need(not p.is_absolute() and '..' not in p.parts and '\\' not in name, 'UNSAFE_MEMBER')
        return {name: archive.read(name) for name in names if not name.endswith('/')}

def validate_q16_inputs(question, answer, source_images):
    need(question['source_question_archive']['book_id'] == answer['book_id'] == '46007447', 'BOOK_IDENTITY')
    need(question['question_id'] == QID and answer['answer_id'] == AID, 'STABLE_IDENTITY')
    need(question['printed_number'] == answer['printed_number'] == '16', 'PRINTED_NUMBER')
    need(question['source_question_archive']['section_path'] == answer['section_path'] == SECTION,
         'SECTION_IDENTITY')
    need(question['asset_id'] == 'viewer-15' and answer['asset_id'] == 'viewer-173', 'SOURCE_ASSET_IDENTITY')
    need(question['source_question_archive']['question_id'] == QID and
         sha(canonical(question['source_question_archive'])) == question['source_question_sha256'], 'BASE_QUESTION_BINDING')
    blocks = question['blocks']
    need([b['block_id'] for b in blocks] == ['q16-stem','q16-task1','q16-task2','q16-task3'], 'QUESTION_TASK_ORDER')
    need([b.get('label') for b in blocks[1:]] == ['1','2','3'], 'QUESTION_TASK_LABELS')
    need(all(b.get('parent_question_id') == QID for b in blocks[1:]), 'TASK_PARENT_IDENTITY')
    need(sum(r['format'] == 'blank' for b in blocks for r in b['runs']) == 3 and
         all(r.get('value') is None for b in blocks for r in b['runs'] if r['format']=='blank'), 'NO_FILLED_QUESTION_BLANKS')
    for block in blocks:
        source = source_images['viewer-15']
        need(block['source_sha256'] == sha(source), 'QUESTION_SOURCE_SHA')
        box = block['bbox']
        with Image.open(io.BytesIO(source)) as image:
            crop = image.convert('RGB').crop(box)
            need(0 <= box[0] < box[2] <= image.width and 0 <= box[1] < box[3] <= image.height,
                 'QUESTION_REGION_BOUNDS')
            need(sha(crop.tobytes()) == block['crop_rgb_sha256'], 'QUESTION_CROP_PIXELS')
        need(block['verification_status'] == 'UNVERIFIED', 'NO_QUESTION_APPROVAL')
    lines = answer['content_fragments']
    need(len(answer['fragments']) == 17 and len(lines) == 3, 'ANSWER_FRAGMENT_COVERAGE')
    need(sum(r['format']=='latex' for line in lines for r in line['runs']) == 11, 'ANSWER_FORMULA_COVERAGE')
    need(answer['text'] == '\n'.join(line['text'] for line in lines), 'ANSWER_CURRENT_ASSEMBLY')
    for line in lines:
        region = line['source_region']
        need(region['asset_id']=='viewer-173' and region['source_sha256']==sha(source_images['viewer-173']), 'ANSWER_SOURCE_SHA')
        need(not line['transcription_verified'] and not line['business_acceptance'] and not line['complete'], 'NO_ANSWER_APPROVAL')
    need(lines[0]['text'].startswith('16.解：（1）60 61（2）') and '（3）∵' in lines[0]['text'], 'ANSWER_SUBPART_ANCHORS')

def build(observed, question_package, answers):
    scope = json.loads(observed['chapter-scope.json'])
    observation = json.loads(observed['observation.json'])
    need(scope['book_id']=='46007447' and not scope['inventory_frozen'], 'PARTIAL_SCOPE_REQUIRED')
    evidence_assets = {a['asset_id']: a for a in observation['observed_assets']}
    images = {}
    inventory = []
    for item in scope['assets']:
        raw = observed[item['path']]
        with Image.open(io.BytesIO(raw)) as image:
            need(sha(raw)==item['sha256'] and image.size==(item['width'],item['height']), 'OBSERVED_ASSET_BYTES')
        aid = item['asset_id']
        need(aid not in images, 'DUPLICATE_ASSET')
        images[aid] = raw
        record = evidence_assets[aid]
        need(record['sha256']==item['sha256'], 'OBSERVATION_ASSET_BINDING')
        inventory.append(dict(asset_id=aid, source_package_member=item['path'], sha256=sha(raw),
                              width=item['width'],height=item['height'],
                              printed_page_model_visual=record['printed_page_model_visual'], role=record['role'],
                              physical_page_identity_status='MODEL_VISUAL_UNVERIFIED',
                              chapter_region_limit=record['chapter_region_limit'],
                              content_lane='SEPARATE_QUESTION_G09' if aid=='viewer-13' else
                              'SEPARATE_QUESTION_CONTENT_V4' if aid=='viewer-15' else 'EXISTING_SIX_ASSET_CONTENT_CHAIN'))
    need(len(images)==8 and len({sha(raw) for raw in images.values()})==8, 'EIGHT_DISTINCT_ASSETS')
    need(images['viewer-15']==question_package['46007447_page_14.jpg'], 'QUESTION_CROSS_PACKAGE_BYTES')
    for aid in ('viewer-173','resource-173'):
        need(images[aid]==answers[f'staging/assets/{aid}.jpg'], 'ANSWER_CROSS_PACKAGE_BYTES')
    need(sha(question_package['plan.json'])==PLAN_SHA, 'FIXED_QUESTION_PLAN')
    plan = json.loads(question_package['plan.json'])
    p = plan['payload']
    need(p['book_id']=='46007447' and not p['human_verification'] and not p['business_acceptance'] and
         not p['transcription_verified'] and p['decision']=='HOLD', 'NO_PLAN_PROMOTION')
    need(plan['content_hash']==sha(canonical(p)), 'QUESTION_PLAN_PAYLOAD_HASH')
    question = next(q for q in p['questions'] if q['question_id']==QID)
    old_case = json.loads(answers['staging/cases/q16-unit2-formulas.json'])
    need(old_case['question_id'] is None and old_case['mode']=='ANSWER_EVIDENCE_ONLY', 'HISTORICAL_STAGE_UNCHANGED')
    answer = old_case['answer_snapshot']
    validate_q16_inputs(question, answer, images)
    first = answer['content_fragments'][0]
    markers = [first['text'].index('（1）'),first['text'].index('（2）'),first['text'].index('（3）')]
    task_map = [
        dict(task_block_id='q16-task1',answer_regions=[dict(content_fragment_id=first['content_fragment_id'],text_span=markers[:2])],
             semantic_anchor='next triple begins at 11; printed answer has separate 60 61',status='MODEL_SOURCE_CANDIDATE'),
        dict(task_block_id='q16-task2',answer_regions=[dict(content_fragment_id=first['content_fragment_id'],text_span=markers[1:])],
             semantic_anchor='third expression after the supplied second expression',status='MODEL_SOURCE_CANDIDATE'),
        dict(task_block_id='q16-task3',answer_regions=[dict(content_fragment_id=line['content_fragment_id'],
             text_span=[markers[2] if index==0 else 0,len(line['text'])]) for index,line in enumerate(answer['content_fragments'])],
             semantic_anchor='three-line proof plus odd positive integer conditions',status='MODEL_SOURCE_CANDIDATE'),
    ]
    graph = json.loads(question_package['graph.json'])
    matching = json.loads(answers['staging/batch.json'])
    candidate = dict(schema_version='b-q16-source-link-proposal/0.1',book_id='46007447',question_id=QID,answer_id=AID,
                     section_path=SECTION,relationship_status='CANDIDATE_NOT_SELECTED',decision='HOLD',
                     question_snapshot=copy.deepcopy(question),answer_snapshot=copy.deepcopy(answer),task_map=task_map,
                     provenance=dict(question_plan_file_sha256=PLAN_SHA,question_source_graph_ref={k:graph[k] for k in ('artifact_id','revision','content_hash')},
                         answer_source_graph_ref=matching['source_graph_ref'],
                         input_package_sha256={k:v[1] for k,v in PINS.items()},
                         source_assets=[x for x in inventory if x['asset_id'] in ('viewer-15','viewer-173')]),
                     content_review_basis='MODEL_VISUAL_SOURCE_COMPARISON_AND_STRUCTURAL_BINDING; NOT_INDEPENDENT_HUMAN',
                     blockers=['CONTENT_AND_FORMULA_INDEPENDENT_REVIEW','SECTION_MEMBERSHIP_REVIEW',
                               'COMPOSITE_QUESTION_AND_ANSWER_ROLE_POLICY','A_CURRENT_CONSUMER_CHECKS_PENDING'],
                     graph_mutation_performed=False,selected_relation_created=False,human_verified=False,
                     business_acceptance=False,platform_eligible=False,platform_actions=[])
    candidate['content_hash'] = sha(canonical(candidate))
    q9 = json.loads(answers['staging/cases/q9-reflection-continuation.json'])
    directory = json.loads(observed['directory-observed-history.json'])
    chapter = next(x for x in directory['data']['directory_data'] if x['id']==scope['chapter_id'])
    requests = [
        dict(id='S01',owner='A_SOURCE_ACCESS_OR_USER_EXPORT',priority=1,
             material='Q9 in 问题解决策略 反思: full question page(s), figure(s), two subparts and chapter header; adjacent pages only if needed to establish continuation',
             answer_id=q9['answer_id'],answer_section_path=q9['section_path'],
             search_clues=['ant surface path','first subpart answer20cm, source8/8/12','second subpart answer25cm, dimensions10/20/5'],
             status='NOT_LOCATED_IN_FIXED_LOCAL_SOURCE_SET',question_id=None),
        dict(id='S02',owner='A_SOURCE_ACCESS_OR_USER_EXPORT',priority=2,
             material='chapter table of contents plus page navigation/source list proving first/last question and answer boundaries, including 周测 inclusion',
             status='WHOLE_CHAPTER_RANGE_UNKNOWN',expected_page_count=None),
        dict(id='S03',owner='A_SOURCE_ACCESS_OR_USER_EXPORT',priority=3,
             material='remaining chapter sources after reconciliation against these eight hashes; no duplicate delivery required',
             status='WAIT_FOR_RANGE_NOT_BLIND_NUMBER_RANGE'),
    ]
    report = dict(schema_version='b-chapter-source-reconciliation/0.1',date='2026-10-19',timezone='Asia/Shanghai',
                  book_id='46007447',chapter_id=scope['chapter_id'],decision='HOLD',
                  input_package_sha256={k:v[1] for k,v in PINS.items()},verified_local_assets=inventory,
                  local_original_count=8,newly_acquired_web_assets=0,
                  chapter_expected_pages=None,chapter_expected_questions=None,chapter_expected_answers=None,
                  inventory_frozen=False,human_verified=False,
                  directory_snapshot_sha256=sha(observed['directory-observed-history.json']),
                  directory_groups=[dict(directory_id=x['id'],label=x['label']) for x in chapter['children']],
                  directory_question_nodes_are_denominator=False,
                  q16=dict(question_source_available_locally=True,question_id=QID,answer_id=AID,
                           relationship_status='CANDIDATE_NOT_SELECTED',requires_A_to_resend_question_page=False,
                           old_stage_question_id=None,old_stage_rewritten=False,task_count=3,answer_raw_fragments=17,answer_latex_runs=11),
                  q9=dict(question_source_status='NOT_LOCATED_IN_FIXED_LOCAL_SOURCE_SET',
                          answer_id=q9['answer_id'],section_path=q9['section_path'],question_id=None,
                          no_same_number_substitution=True,answer_source_assets=q9['source_asset_ids']),
                  a_source_requests=requests,
                  b_owned_work=['join separate viewer13 G09 and viewer15 content lane with current chapter view without dropping history',
                                'independently check Q16 symbols/formulas and candidate task-answer mapping',
                                'verify Q9 full continuation content and figures while question page is unavailable',
                                'reconcile 19 legacy rows against newly available reading-material source before asking A for all 19 again',
                                'produce chapter census from source pages and retain unknown denominator',
                                'current-content recheck, package recovery and clean environment replay'],
                  execution=dict(network_calls=0,ocr_calls=0,model_calls=0,graph_mutations=0,platform_calls=0),
                  limits=['eight received image files do not establish chapter completeness',
                          'same question number, mathematical plausibility and structural checks are not identity or human approval',
                          'the old three answer-only cases remain historical; the new Q16 relation is an unselected sidecar only'])
    return report, candidate

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key,(relative,_) in PINS.items(): parser.add_argument('--'+key,type=Path,default=ROOT/relative)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    report,candidate = build(*(unpack_fixed(getattr(args,key),pin[1]) for key,pin in PINS.items()))
    args.out.mkdir(parents=True,exist_ok=True)
    for name,value in [('source-reconciliation.json',report),('q16-source-link-candidate.json',candidate)]:
        (args.out/name).write_bytes(encode(value))
    print(json.dumps(dict(verified_local_assets=8,q16_question_source_available=True,
                         q16_relationship='CANDIDATE_NOT_SELECTED',q9_question_source='NOT_LOCATED',decision='HOLD'),ensure_ascii=False))

if __name__=='__main__': main()
