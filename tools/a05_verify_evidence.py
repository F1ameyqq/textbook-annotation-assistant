"""Offline verification of A05 evidence. Never opens a browser or writes Usense."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / 'docs/evidence/A05/execution'

def verify(folder: Path) -> dict:
    def read(name):
        return json.loads((folder/name).read_text(encoding='utf-8-sig'))
    checks = {}
    def check(name, value):
        checks[name] = bool(value)
    plan = read('write-plan.json')
    pre = read('prewrite-annotations.json')['data']
    refresh = read('refresh-annotations.json')['data']
    reopen = read('reopen-annotations.json')['data']
    by_id = lambda records: {a['rect_id']: a for a in records}
    old, mid, final = map(by_id, (pre, refresh, reopen))
    check('unique_rect_ids', all(len(by_id(a)) == len(a) for a in (pre, refresh, reopen)))
    check('counts_66_68_68', [len(pre),len(refresh),len(reopen)] == [66,68,68])
    check('historical_records_exact_after_refresh', all(mid.get(k)==v for k,v in old.items()))
    check('historical_records_exact_after_reopen', all(final.get(k)==v for k,v in old.items()))
    check('refresh_equals_reopen', mid == final)
    new_ids = set(final)-set(old)
    new = [final[k] for k in sorted(new_ids)]
    check('exactly_one_question_two_new_frames', len(new)==2 and {a['order_in_level'] for a in new}=={'22'} and {a['type'] for a in new}=={'question','answer'})
    check('question_orders_1_to_22', {a['order_in_level'] for a in reopen}=={str(n) for n in range(1,23)})
    check('new_frames_book_directory_and_type', all(str(a['file_id'])=='46007447' and a['directory_id']==plan['directory_id'] and a['content_type']=='text' for a in new))
    for frame in plan['frames']:
        actual = next(a for a in new if a['type']==frame['role'])
        bbox = list(map(float,actual['rect_bbox'].split(',')))
        check(frame['role']+'_bbox_matches_plan', all(abs(a-b)<.001 for a,b in zip(bbox,frame['bbox_original'])))
        check(frame['role']+'_page_mapping', actual['page_index']==frame['viewer_page']==frame['platform_annotation_page_index'] and frame['source_index']==frame['viewer_page']-1)
        check(frame['role']+'_source_digest', hashlib.sha256((folder/frame['source_file']).read_bytes()).hexdigest()==frame['sha256'])
    receipt = read('commit-receipt.json')
    node = receipt['data']['inserted_question_node']
    check('business_receipt', receipt.get('code')==0 and receipt['data'].get('success') is True and receipt['data'].get('inserted') is True and receipt['data'].get('question_order')==22 and receipt['data'].get('append_at_global_end') is True)
    original_tree=read('prewrite-directory.json')['data']['directory_data']
    for phase in ('refresh','reopen'):
        tree=read(phase+'-directory.json')['data']['directory_data']
        found=[]
        def remove_new(nodes,parent=None):
            result=[]
            for item in nodes:
                if item.get('id')==node['id']:
                    found.append((parent,item));continue
                item=copy.deepcopy(item)
                if 'children' in item:item['children']=remove_new(item['children'],item['id'])
                result.append(item)
            return result
        remaining=remove_new(tree)
        check(phase+'_old_directory_exact', remaining==original_tree)
        check(phase+'_only_expected_new_question_node', found==[(plan['directory_id'],node)])
    payload=read('commit-preflight.json')['payload']
    check('preflight_all_true', all(read('commit-preflight.json')['checks'].values()))
    check('append_only_payload', payload['question_order'] is None and payload['is_new_question_insertion'] is True and payload['insert_after_order']==21 and payload['target_directory_id']==plan['directory_id'] and payload['annotations_delete_rect_ids']==[] and payload['ocr_submissions']==[] and len(payload['annotations_upsert'])==2 and {a['rect_id'] for a in payload['annotations_upsert']}==new_ids)
    check('payload_fields_equal_reopen', all(all(final[a['rect_id']].get(k)==v for k,v in a.items()) for a in payload['annotations_upsert']))
    check('single_question_readback_equals_full', by_id(read('reopen-question22.json')['data'])=={k:final[k] for k in new_ids})
    check('saved_question_type_fill_blank', read('reopen-question-info22.json')['data']['tishi']=='tiankong')
    check('ocr_empty_content_pending', all(read('reopen-ocr-'+zone+'22.json')['data'].get('success') is False for zone in ('question','answer')) and plan['content_check_status']=='PENDING')
    check('book_before_21_marking', read('prewrite-book.json')['data']['status']=='标注中' and read('prewrite-book.json')['data']['question_count']==21)
    for phase in ('after-save','refresh','reopen'):
        book=read(phase+'-book.json')['data']
        check(phase+'_book22_still_marking', book['id']=='46007447' and book['status']=='标注中' and book['question_count']==22 and all(book.get(k) is None for k in ('review_submitted_at','reviewed_at','delivery_submitted_at','delivered_at')))
    network=read('network.json')
    writes=[e for e in network if e['method'] not in ('GET','HEAD','OPTIONS')]
    check('only_one_captured_api_write', len(writes)==1 and writes[0]['url'].endswith('/annotate_pic/commit_unified_submit'))
    check('no_ocr_or_book_submission_api_write', not any(any(p in e['url'] for p in ('batch-ocr-task','submit-review','submit-delivery','start-ocr')) for e in writes))
    actions=read('actions.json')
    check('save_clicked_once', len([a for a in actions if a['op']=='click' and a['target']=='提交修改'])==1)
    release=read('session-release.json')
    check('session_released_no_pending_action', release['released'] is True and release['matching_active_process_count']==0 and release['pending_write'] is False)
    check('paid_model_calls_zero', plan['paid_model_calls']==0)
    failed=[k for k,v in checks.items() if not v]
    return {'result':'PASS' if not failed else 'FAIL','checks':checks,'failed':failed,'new_rect_ids':sorted(new_ids),'content_check_status':'PENDING','scope':'offline execution evidence self-check; independent platform acceptance remains with coordinator'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,default=DEFAULT)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=verify(args.evidence)
    rendered=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:args.output.write_text(rendered,encoding='utf8')
    print(rendered)
    raise SystemExit(0 if result['result']=='PASS' else 1)
