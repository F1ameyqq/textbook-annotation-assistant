"""Assemble evidence dispositions for all 48 prepared requirements. No product execution."""
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path

ROOT=Path('D:/1800-worktrees/a16-independent-fixed')
OUT=ROOT/'docs/evidence/A16/independent-offline-review'
PREP=Path('D:/1800-worktrees/a16-review-preparation')


def load(path):return json.loads(path.read_bytes())
def save(name,value):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')


controls=load(OUT/'independent-controls-result.json')
assert controls['first_failure']['id']=='C13_CHANGED_SAMPLE_COUNTEREXAMPLE'
assert controls['resource_attempts']==[]
assert Counter(r['status'] for r in controls['probes'])=={'PASS':12,'FAIL':1,'NOT_RUN':3}
sample=load(OUT/'counterexample-changed-sample.actual.json')
assert sample['thrown'] is None and sample['result']['outcome']=='READONLY_REVIEW'
assert sample['result']['sample']['content']['choice']['status']=='AVAILABLE'
supplemented=load(OUT/'supplemented-suite-raw/result.json')
assert supplemented['success'] and supplemented['tests']==33
first=load(ROOT/'docs/evidence/A16/current-readonly/test-runs/independent-01/result.json')
assert first['errors']==1 and not first['success']

findings=[
    {'id':'A16-R01','priority':1,'result':'CONFIRMED_COUNTEREXAMPLE','blocking':True,
     'title':'Reject sample frame semantic changes before using content evidence',
     'file':'tools/a16_current_state_probe.py','line':512,'end_line':514,
     'related':[{'file':'tools/a16_current_state_probe.py','line':497},
        {'file':'src/annotation/source/usense/current_readonly/decode.py','line':70}],
     'requirement':'Fixed sample schema must correspond field by field to current frame ownership, role, zone/order and content; identity mismatch stops successors.',
     'trigger':'Initial full inventory is normal. Single-sample frame response has identical rect_id/file_id/question order, but r-3-1 changes choice→answer and r-3-2 zone index changes 1→3.',
     'actual':'collect completes all 11 business GET steps and returns READONLY_REVIEW; choice text is AVAILABLE and bound using stale initial inventory frames.',
     'cause':'Sample response checks only an ID set and book/question identity. Its role/index/directory/page/bbox/parent/content fields are discarded. expected_frames remains the initial inventory projection.',
     'expected':'Any unapproved semantic mismatch is a terminal sample read failure; do not execute info/content successors. If comparisons succeed, bind content to the actual validated sample rows in a proven order.',
     'evidence':['independent-controls-result.json#C13_CHANGED_SAMPLE_COUNTEREXAMPLE','counterexample-changed-sample.actual.json'],
     'limits':'Synthetic transport/image/UI/file stubs; actual collect/decode/selection/current_code/register_sample/bound_content/check paths used. No platform behavior or real write is asserted.'},
    {'id':'A16-R02','priority':1,'result':'STATIC_GAP','blocking':True,
     'title':'Lexical token co-occurrence does not establish current getter and response schema',
     'file':'src/annotation/source/usense/current_readonly/decode.py','line':189,'end_line':203,
     'related':[{'file':'src/annotation/source/usense/current_readonly/policy.py','line':67},
        {'file':'tools/a16_current_state_probe.py','line':495}],
     'requirement':'Sample API paths/parameters/zones must be derived from current code/response; unknown parameters must not be probed; schema evidence must be field-bound.',
     'actual_static':'has_read searches field words anywhere in a broad block and endpoint names/zone strings anywhere in the asset. has_content only adds global presence of ocr_result and success. register_sample then registers five hardcoded GETs from those booleans.',
     'cause':'No proof links the tokens to the selected getter arguments, its concrete other endpoint paths, or the data.success/data.ocr_result decoder response object.',
     'expected':'Keep lexical hits as CURRENT_CODE observations with applicability UNKNOWN until concrete getter/parameter/zone/response bindings are demonstrated. Only register the evidenced paths/parameters; supply field-level source refs.',
     'evidence':['src/annotation/source/usense/current_readonly/decode.py:174-203',
        'src/annotation/source/usense/current_readonly/policy.py:67-86'],
     'limits':'C15 executable counterexample NOT_RUN after R01 stop. This is a static logic finding; no fabricated runtime output.'},
    {'id':'A16-R03','priority':2,'result':'STATIC_GAP','blocking':True,
     'title':'Full original-image decoding is absent',
     'file':'src/annotation/source/usense/current_readonly/decode.py','line':162,'end_line':170,
     'requirement':'Reject invalid/truncated original image bytes; dimensions/hash and source facts must describe a usable original, rather than a readable header.',
     'actual_static':'original_info reads img.size/img.format and calls img.verify(), but never loads pixel data. There is no later byte decoder in original_once before those bytes are saved and described.',
     'expected':'Perform a full decode/load from the exact bytes and fail closed on decode errors; retain a valid-header/truncated-JPEG negative control.',
     'evidence':['src/annotation/source/usense/current_readonly/decode.py:162-171','tools/a16_current_state_probe.py:379-387'],
     'limits':'C14 truncated-image runtime test NOT_RUN after R01 stop. No claim is made that a particular corrupted file was accepted in this review.'},
    {'id':'A16-R04','priority':2,'result':'STATIC_GAP_LIMITED_FAIL_CLOSED','blocking':False,
     'title':'Worker release state can say RELEASED after creation-identity mismatch',
     'file':'tools/a16_current_state_probe.py','line':670,'end_line':672,
     'requirement':'Exact held creation identity is part of release proof; mismatch must remain UNKNOWN.',
     'actual_static':'The mismatch at 641-642 appends an error, but state at 670-672 checks job/handle closure and exit_observed without identity equality or absence of identity errors.',
     'expected':'Release state explicitly requires creation identity match; otherwise UNKNOWN. Retain error and parent failure.',
     'evidence':['tools/a16_current_state_probe.py:640-672'],
     'limits':'The parent still returns failure because errors is nonempty, so this is not a demonstrated live admission bypass. C16 runtime check NOT_RUN.'}
]
save('findings.json',{'task':'A16','result':'REWORK','findings':findings})

# Dispositions are intentionally narrower than the original case title. A case
# with many variants is not called fully passed on one representative control.
mapping={
'A01':('PARTIAL_OFFLINE_VERIFIED',['C01_DEFAULT_STATIC'],'Default probe verified; author suite covers internal CLI rejection; browser creation path is static only.'),
'A02':('OFFLINE_VERIFIED',['C02_GATE'],'Recomputed-digest A15 task/run and wrong stage bindings rejected; no old grant file read.'),
'A03':('PARTIAL_OFFLINE_VERIFIED',['C02_GATE'],'Fourteen independent binding variants plus author gate tests; not every field independently mutated.'),
'A04':('PARTIAL_OFFLINE_VERIFIED',['C02_GATE'],'Expiry/start, typed context limit, limits and duplicate JSON covered; not all JSON/time variants executed.'),
'A05':('OFFLINE_VERIFIED',['C01_DEFAULT_STATIC','C02_GATE'],'Strict default and synthetic strict/exception separation verified; no real activation exists.'),
'A06':('PARTIAL_STATIC',['AUTHOR:test_marker_replay_retained'],'Mock FileExistsError and exclusive save_new code; full claim bytes/tamper fixture not independently executed.'),
'N01':('PARTIAL_OFFLINE_VERIFIED',['C03_POLICY','C08_REAL_CAPTURE_CACHE'],'Six necessary fixed GET policy positives and real captured-byte cache consumption; fresh browser fetch branch is not live verified.'),
'N02':('PARTIAL_OFFLINE_VERIFIED',['C03_POLICY'],'Wrong page/book/query/path/method and auth-bearing URL negatives; remaining syntactic variants static.'),
'N03':('OFFLINE_VERIFIED',['C03_POLICY','C09_PASSIVE_THEN_FATAL'],'Declared Image/Font/Media rejected without sending; observer remains running for expected passive case.'),
'N04':('PARTIAL_OFFLINE_VERIFIED',['C03_POLICY','C09_PASSIVE_THEN_FATAL'],'Write method dominates Image, redirect active types fatal; full dependency-correlation matrix not executed.'),
'N05':('OFFLINE_VERIFIED',['C09_PASSIVE_THEN_FATAL'],'Optional Font rejection followed by POST becomes fatal and stops next GET; first failure preserved.'),
'N06':('PARTIAL_OFFLINE_VERIFIED',['C03_POLICY','AUTHOR:test_redirect_hop_and_write_stop_successors'],'Redirect denial in policy and paused native handler; actual CDP browser redirects untested.'),
'N07':('PARTIAL_STATIC',['C09_PASSIVE_THEN_FATAL','AUTHOR:test_duplicate_inflight_guard_exception_and_child_stop'],'WS fake never connects; child target fake closes; inherited install/autoattach and blocked service workers static only.'),
'N08':('PARTIAL_OFFLINE_VERIFIED',['C10_TERMINAL','AUTHOR:test_no_business_after_first_fatal_in_collect'],'Late close-await failure overrides success; not every awaited read point independently injected.'),
'N09':('PARTIAL_OFFLINE_VERIFIED',['C08_REAL_CAPTURE_CACHE','AUTHOR:test_query_reordering_cannot_buy_another_get'],'Actual capture→cache→get_once→native local fulfill; context route fulfillment and CORS browser ordering not executed.'),
'N10':('REWORK_STATIC',['A16-R02'],'Runtime sample registration relies on unbound lexical booleans and hardcoded endpoint/zone assumptions.'),
'R01':('PARTIAL_OFFLINE_VERIFIED',['C04_REDACTION'],'URL path/query/userinfo sentinels absent from diagnostic and safe error; not every output channel/shape independently fuzzed.'),
'R02':('PARTIAL_OFFLINE_VERIFIED',['C04_REDACTION'],'Arbitrary exception text redacted; nested response-field credential cases not independently executed.'),
'R03':('STATIC_ONLY',[],'GET_JSON consumes auth internally, exports only status/body; no login fallback and no actual credential file access in reviewed test paths.'),
'I01':('OFFLINE_VERIFIED',['C05_INVENTORY','C12_COLLECTOR_BASELINE'],'Numerical whole-book max22, full inventory versus sample PARTIAL content, Q22 preserved and no write baseline.'),
'I02':('PARTIAL_OFFLINE_VERIFIED',['C05_INVENTORY','AUTHOR:test_mismatched_book_and_duplicate_identity'],'Wrong frame book, count unknown and duplicate identities covered; pagination and bbox/extra-field validity variants not fully checked.'),
'I03':('PARTIAL_STATIC',['C05_INVENTORY','AUTHOR:test_complete_global_inventory_and_q22_preserved'],'Different synthetic counts use actual question_count, no old22/68 expectation; exact21/66 and23/70 prepared pairs not executed.'),
'I04':('OFFLINE_VERIFIED',['C05_INVENTORY','C12_COLLECTOR_BASELINE'],'Q22 inventory retained and not selected; only-Q22 sample returns None; full sequence uses sample3.'),
'I05':('PARTIAL_STATIC',[],'Projection now retains zone index and declared subset; image_path and other noncredential fields omitted; explicitly not a complete write-preservation baseline.'),
'I06':('PARTIAL_STATIC',['AUTHOR:test_business_login_and_http200_not_sufficient'],'Business401/403/nonzero code fail; DOM selected-book proof only statically read, no actual UI identity evidence.'),
'C01':('PARTIAL_OFFLINE_VERIFIED',['C06_CONTENT'],'Explicit nonempty/empty/unconfirmed success/missing result distinct; actual current schema qualification remains R02 gap.'),
'C02':('OFFLINE_VERIFIED',['C05_INVENTORY','C12_COLLECTOR_BASELINE'],'One sample remains PARTIAL content and no production readiness; other questions UNKNOWN.'),
'C03':('OFFLINE_VERIFIED',['C06_CONTENT'],'success=false/missing result stays UNKNOWN and login/business errors raise.'),
'C04':('STATIC_AND_RAW_VERIFIED',[],'All old Git members unchanged; A11 unavailable-content gate untouched; write_preservation_baseline false.'),
'S01':('PARTIAL_OFFLINE_VERIFIED',['C03_POLICY'],'Registration enforces book/viewer/index/domain/path/ref; complete no-registration/fetch order is static.'),
'S02':('OFFLINE_VERIFIED',['C07_SOURCE_DRAFT'],'Viewer14 resource57 kept; source index not inferred as13.'),
'S03':('REWORK_STATIC',['A16-R03'],'Only verify(), no full pixel decode; runtime truncated-JPEG counterexample C14 NOT_RUN.'),
'S04':('STATIC_ONLY',[],'Actual fetched bytes determine SHA; no substitution with archived hash; changed-image visual review remains HOLD.'),
'Q01':('OFFLINE_VERIFIED',['C05_INVENTORY','C12_COLLECTOR_BASELINE'],'Shuffled11/22/3 selects numeric3, one sample, Q22 excluded.'),
'Q02':('PARTIAL_STATIC',[],'No replacement/zone loop; type observation remains UNKNOWN_READONLY_SCHEMA_ONLY. A duoxuan sample is not declared single-choice qualification.'),
'Q03':('STATIC_AND_OFFLINE_VERIFIED',['C12_COLLECTOR_BASELINE'],'Only fixed read sequence used, save fields observed lexically; no commit/upload/signature/OCR method implementation invoked.'),
'D01':('REWORK_STATIC',['A16-R02'],'Current bytes are response-derived, but lexical hits do not prove content schema applicability; C15 NOT_RUN.'),
'D02':('REWORK_CONFIRMED',['C13_CHANGED_SAMPLE_COUNTEREXAMPLE','A16-R01'],'Actual changed sample role/zone order passes; content decoder then uses initial inventory rows.'),
'D03':('PARTIAL_OFFLINE_VERIFIED',['C06_CONTENT','C12_COLLECTOR_BASELINE'],'One choice response binds ordered four rect_ids, reversed IDs reject; no danxuan invention or single-choice qualification from duoxuan.'),
'D04':('PARTIAL_STATIC',[],'Scripts originate same-origin loaded response and bytes/hash; only lexical builder discovery and no actual current script observed.'),
'F01':('HISTORICAL_PREPARATION_ONLY',['C07_SOURCE_DRAFT'],'Historical content/roles and answerC consistent with task; punctuation and boxes remain DRAFT/HOLD, not approval.'),
'F02':('OFFLINE_VERIFIED',['C07_SOURCE_DRAFT'],'Same six content/boxes with four roles Q rejects.'),
'F03':('REWORK_CONFIRMED',['C07_SOURCE_DRAFT','C13_CHANGED_SAMPLE_COUNTEREXAMPLE'],'Draft label/text swaps reject, but actual sample frame role/order drift is accepted (R01).'),
'F04':('STATIC_ONLY',[],'Draft retains current-newness/directory UNKNOWN, old approval not reused, no replacement selection implemented.'),
'F05':('HISTORICAL_PREPARATION_ONLY',[],'Draft numeric bounds checked, no current pixel/crop proof or approved bbox; negative crop examples NOT_RUN.'),
'L01':('PARTIAL_OFFLINE_VERIFIED',['C11_LOCAL_WAIT_CLOCK'],'Injected local wait clock origin7; each process uses own start+UTC remaining by static review; no real process deadline test.'),
'L02':('STATIC_GAP_LIMITED_FAIL_CLOSED',['A16-R04'],'Precise held handles and own Job cleanup implemented; worker release state omits identity predicate, while parent errors still fail.'),
'L03':('RAW_VERIFIED_WITH_LIMITATIONS',[],'49 raw inputs, 31259 old modes/types/blobs and37 prep members verified; same-final50 package supplement. Old failures retained, no product edits.')
}
standards=load(PREP/'acceptance-cases.v002.json')['cases']
assert set(mapping)=={c['id'] for c in standards}
matrix=[]
for case in standards:
    status,evidence,note=mapping[case['id']]
    matrix.append({'id':case['id'],'group':case['group'],'authoritative_rule':case['authoritative_rule'],
        'status':status,'evidence':evidence,'actual_scope_and_limit':note,
        'not_a_blanket_pass_for_all_variants':True})
save('requirement-matrix-48.json',{'task':'A16','candidate_manifest_sha256':controls['candidate_manifest_sha256'],
    'result':'REWORK','prepared_cases':48,'executed_controls':13,'controls_pass':12,'controls_fail':1,
    'controls_not_run_after_first_failure':3,'requirements':matrix,'status_counts':dict(Counter(x['status'] for x in matrix))})

initial_dir=OUT/'initial-suite-raw';initial_dir.mkdir(exist_ok=False)
for name in ['result.json','unittest.txt']:
    with (initial_dir/name).open('xb') as stream:
        stream.write((ROOT/'docs/evidence/A16/current-readonly/test-runs/independent-01'/name).read_bytes())

save('independent-control-command-result.json',{'command':'python -B docs/evidence/A16/independent-offline-review/independent_controls.py',
    'exit_code_observed_by_shell':1,'duration_in_script_ms':controls['duration_ms'],
    'completion':'Finished, first semantic counterexample retained; C14-C16 NOT_RUN',
    'failure_kind':'CONFIRMED_PRODUCT_SEMANTIC_COUNTEREXAMPLE_NOT_HARNESS_FAILURE',
    'process_creation_identity':'NOT_OBSERVED_NO_OS_SELF_EXIT_CLAIM'})
save('tooling-observations.json',{'task':'A16','nonproduct_search_error':{
    'command':'rg -n ... src/annotation/source/usense/current_readonly/*.py',
    'observed':'Windows nonexpanded wildcard OS error123; no file changes or product test',
    'correction':'rg -n -g *.py ... src/annotation/source/usense/current_readonly'},
    'author_run01_run05_full_tracebacks':'NOT_IN_FIXED_PACKAGE; only reconstructed summaries, original chat not read',
    'author_run09_shell_exit0':'Author report supplement; result.json itself lacks shell exit field',
    'author_static_release':'PID/wait/exit only; no creation identity; no broader OS identity assertion'})

save('review-result.json',{'task':'A16','candidate_manifest_sha256':controls['candidate_manifest_sha256'],
    'result':'REWORK','review_thread_id':'01a15841-0d44-7272-9740-40d013839869',
    'workflow_commit':'7409a94d9e94eb1b5a7414a7cbb701b320a9f329',
    'product_commit':'2a604c2d0b0f7781ec0d7ca4b5925ae9ff53b595',
    'final_commit':'4fe417d5246f20fbbbedc577495c7ca400d4ded8',
    'delivery_manifest_sha256':'41d965083d188f7021cb1e64b9d9a98c2b97541aa31f5d39e267b1ff228f7ca1',
    'initial_author_reproduction':'IMPORT_ERROR; product tests NOT_RUN; original retained',
    'supplemented_author_reproduction':{'tests':33,'failures':0,'errors':0,'duration_ms':supplemented['duration_ms'],'shell_exit':0},
    'independent_controls':{'pass':12,'fail':1,'not_run':3,'duration_ms':controls['duration_ms']},
    'primary_blocker':'A16-R01','static_blocking_gaps':['A16-R02','A16-R03'],
    'nonblocking_structured_release_gap':'A16-R04','live_activated':False,
    'TLS_approval_given':False,'save_content_refresh_reopen':'NOT_RUN',
    'author_product_changed':False,'old_suites_run':False,'B_messages':0,
    'next_dependency':'Coordinator arranges same-stage correction and new frozen delivery; reviewer does not modify product or activate live.'})
print(json.dumps({'result':'REWORK','requirements':len(matrix),'findings':len(findings),
    'author_suite':33,'independent_controls_pass':12,'independent_controls_fail':1,'not_run':3}))
