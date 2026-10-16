"""Offline acceptance checks over A05 independently captured business evidence."""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'AGENTS.md').is_file())
R = ROOT / 'docs/evidence/A05/review'
E = ROOT / 'docs/evidence/A05/execution'
B = ROOT / 'docs/evidence/A05/baseline'

def read(folder, name):
    return json.loads((folder / name).read_text(encoding='utf-8-sig'))

def records(data):
    return {r['rect_id']:{k:v for k,v in r.items() if k != 'user_id'} for r in data['data']}

def main():
    checks = {}
    def check(name, value):
        checks[name] = bool(value)
    before = read(E, 'prewrite-annotations.json')
    live = read(R, 'independent-response-0007.json')
    old = records(before)
    actual = records(live)
    new = {k:v for k,v in actual.items() if k not in old}
    receipt = read(E, 'commit-receipt.json')
    plan = read(E, 'write-plan.json')
    expected_ids = {r['rect_id'] for r in read(E, 'commit-preflight.json')['payload']['annotations_upsert']}
    check('business_all_annotations_code_zero',live['code'] == 0)
    check('unique_68_rect_ids',len(live['data']) == len(actual) == 68)
    check('all_66_old_records_exact',len(old)==66 and all(actual.get(k)==v for k,v in old.items()))
    check('exact_match_to_executor_reopen',actual==records(read(E,'reopen-annotations.json')))
    check('exactly_expected_two_new_rects',set(new)==expected_ids and len(new)==2)
    check('only_book46007447',all(str(r['file_id'])=='46007447' for r in actual.values()))
    check('exactly_22_questions',len({(r['directory_id'],r['order_in_level']) for r in actual.values()})==22)
    check('old_orders_1_to21_new_order22',{r['order_in_level'] for r in old.values()}=={str(n) for n in range(1,22)} and {r['order_in_level'] for r in new.values()}=={'22'})
    check('expected_roles_directory_text', {r['type'] for r in new.values()}=={'question','answer'} and all(r['directory_id']==plan['directory_id'] and r['content_type']=='text' for r in new.values()))
    for frame in plan['frames']:
        row = next(r for r in new.values() if r['type']==frame['role'])
        bbox = list(map(float,row['rect_bbox'].split(',')))
        check(frame['role']+'_saved_bbox_matches_plan',len(bbox)==4 and all(abs(a-b)<0.001 for a,b in zip(bbox,frame['bbox_original'])))
        check(frame['role']+'_saved_page',row['page_index']==frame['platform_annotation_page_index'])
        file = R / ('independent-original-'+frame['role']+'.jpg')
        check(frame['role']+'_fresh_original_hash',hashlib.sha256(file.read_bytes()).hexdigest()==frame['sha256'])
        check(frame['role']+'_fresh_original_dimensions',list(Image.open(file).size)==frame['dimensions'])
        crop = R / ('independent-persisted-'+frame['role']+'.jpg')
        check(frame['role']+'_persisted_crop_equals_executor_crop',crop.read_bytes()==(E/('actual-'+('q' if frame['role']=='question' else 'a')+'-crop.jpg')).read_bytes())
    independent_tree = read(R,'independent-response-0003.json')['data']['directory_data']
    check('live_directory_matches_executor_reopen',independent_tree==read(E,'reopen-directory.json')['data']['directory_data'])
    comparison = read(R,'comparison-independent.json')
    check('all_old_directory_tree_exact',comparison['directory_old_tree_exactly_unchanged_after_pruning_additions'] and not comparison['missing_old_directory_ids'])
    additions = comparison['added_directory_nodes']
    check('exact_expected_new_question_node',additions==[{'node':receipt['data']['inserted_question_node'],'parent_id':plan['directory_id']}])
    check('single_question_response_matches_full',records(read(R,'independent-question22.json'))==new)
    info = read(R,'independent-question-info22.json')
    check('live_question_type_fill_blank',info['code']==0 and info['data']['tishi']=='tiankong' and info['data']['order_in_level']=='22' and info['data']['file_id']=='46007447')
    check('q_a_ocr_absent_content_pending',all(read(R,'independent-ocr-'+role+'22.json')['code']==0 and read(R,'independent-ocr-'+role+'22.json')['data'].get('success') is False for role in ('question','answer')) and plan['content_check_status']=='PENDING')
    books = read(R,'independent-response-0001.json')['target_books']
    check('target_book_state22_marking',bool(books) and all(b['id']=='46007447' and b['question_count']==22 and b['status']=='标注中' for b in books))
    check('book_submission_dates_still_null',all(all(b.get(k) is None for k in ('reviewed_at','delivered_at','delivery_submitted_at')) for b in books))
    save_book = {'code':0,'data':books[0]}
    (R/'independent-book.json').write_text(json.dumps(save_book,ensure_ascii=False,indent=2),encoding='utf-8')
    network = read(R,'independent-network.json')
    check('all_16_captured_api_requests_get',len(network)==16 and all(e['method']=='GET' for e in network))
    check('no_blocked_write_attempt',read(R,'independent-run-result.json')['blocked_requests']==0)
    check('review_session_closed',read(R,'session-release.json')['released'] is True and read(R,'session-release.json')['pending_write_actions'] is False)
    check('profile_exclusivity_before_open',read(R,'independent-preflight.json')['matching_active_process_count']==0)
    check('fresh_source_page_mapping',all(r['source_index']==r['planned_source_index'] and r['matches_plan_sha256'] for r in read(R,'independent-originals.json')))
    check('executor_once_save_no_secret_strings',read(R,'independent-operation-audit.json')['save_command_numbers']==[57] and read(R,'independent-operation-audit.json')['captured_api_write_count']==1 and not read(R,'independent-operation-audit.json')['credential_exact_string_match_files'])
    failed = [k for k,v in checks.items() if not v]
    result = {'result':'PASS' if not failed else 'FAIL','checks':checks,'failed':failed,'scope':'independent acceptance of one saved Q/A frame pair; CONTENT_PENDING; no submission or algorithm acceptance'}
    (R/'independent-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'result':result['result'],'check_count':len(checks),'failed':failed}))
    return 0 if not failed else 1

if __name__ == '__main__':
    raise SystemExit(main())
