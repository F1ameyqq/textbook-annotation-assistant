"""Assemble bounded observation-only independent acceptance from frozen actual evidence."""
import hashlib
import json
from pathlib import Path

ROOT=Path('D:/1800-worktrees/a16-observation-review');OUT=ROOT/'docs/evidence/A16/independent-observation-review'
E=ROOT/'docs/evidence/A16/current-readonly/revisions/observation-only'
CANDIDATE='e66e9f96197871f7123ebe2ed981a587262c50fb3f6e62cdc300f8e96be5a63f'
def load(p):return json.loads(p.read_bytes())
def save(name,data):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as stream:json.dump(data,stream,ensure_ascii=False,indent=2);stream.write('\n')

controls=load(OUT/'independent-controls-result.json');suite=load(E/'test-runs/independent-observation-01/result.json')
assert len(controls['cases'])==9 and all(c['status']=='PASS' for c in controls['cases'])
assert controls['first_failure'] is None and controls['resource_attempts']==[] and controls['parser_qualification_calls']==[]
assert suite['tests']==18 and suite['success'] and suite['old_suites_run']==0
assert [c['exit_code'] for c in load(OUT/'fixed-command-results.json')['commands']]==[0,0]

obligations=[
    {'id':'OBS01','result':'PASS_OFFLINE_LIMITED','requirement':'sample_limit0 and all sample reads unconditionally disabled',
     'actual':'register_sample rejects alleged bool/proof/scope flags without state change. All5 paths hard-block even with forged business/original/cache maps, q3/q22 parameters. get_once never evaluates page fetch.',
     'evidence':['NO_SAMPLE_REGISTRATION_OR_CACHE_BYPASS','BOTH_GUARDS_HARD_DENY','new18 PolicyTests'],
     'limit':'No live request was attempted; only policy/native/context handlers with synthetic routes.'},
    {'id':'OBS02','result':'PASS_OFFLINE_LIMITED','requirement':'collect no parser/qualification or sample selection; six reads/two originals and UNKNOWN content',
     'actual':'Three different static-data inputs and forged confirmation fields do not call parser/selection/register. Actual collect/observer produces sample NOT_RUN, schema/body UNKNOWN, FULL synthetic inventory with q22 retained, no write baseline/ready/eligible.',
     'evidence':['COLLECT_NO_PARSER_NO_SAMPLES','new18 observation collect cases'],
     'limit':'Transport/UI/image boundaries synthetic; FULL refers only complete synthetic inventory and proves no current platform fact.'},
    {'id':'OBS03','result':'PASS_OFFLINE_LIMITED','requirement':'same bounded book/viewers/GET and auxiliary network whitelist',
     'actual':'Six actual captured fixed GET responses consumed by get_once from exact bytes without evaluate/resend. Unknown book/page/API/write denied. New path restrictions only reduce sample permissions.',
     'evidence':['SIX_FIXED_CACHE_SCOPE','new18 six fixed/two-original policy controls','unchanged-source-evidence.json'],
     'limit':'Same-origin session/static helpers remain allowed under prior rules; six business+two originals is not an eight-total-HTTP claim. Real CORS/UI/API applicability remains unverified.'},
    {'id':'OBS04','result':'PASS_OFFLINE_LIMITED','requirement':'allowed static Script exact bytes/hash/source retained only, no collector execution or public leakage',
     'actual':'Two distinct same-origin response URLs with CRLF/nonUTF8/NUL/synthetic secret data produce exact .bin bytes and private source sidecars, hash/length/URL hash match. Re-capture does not duplicate artifacts. Public assets/events exclude bytes/full URL/secret/set-cookie; parser/evaluate not invoked.',
     'evidence':['STATIC_EXACT_PRIVATE_PUBLIC_SANITIZED','UNAPPROVED_STATIC_NOT_READ','new18 static output controls'],
     'limit':'All .bin in this review are synthetic data. Actual future raw scripts restricted to fixed .local live output; no real private directory visited. This is not complete frontend/version inventory or code/schema correctness.'},
    {'id':'OBS05','result':'PASS_OFFLINE_LIMITED','requirement':'unexpected fixed read/login/guard failure still stops and preserves unknown statuses',
     'actual':'Source read failure stops pages/originals/mappings/sample successors; previously observed inventory remains evidence. Late final guard error overrides observation success with sample NOT_RUN and write/schema flags nonqualifying. Script401 rejects before body read.',
     'evidence':['FIRST_READ_FAILURE_AND_LATE_GUARD','UNAPPROVED_STATIC_NOT_READ','new18 failure controls'],
     'limit':'Real login/session/child-process/OS behavior not tested.'},
    {'id':'OBS06','result':'PASS_OFFLINE_LIMITED','requirement':'new workflow/scope/candidate, typed sample0, count6+2, no auto schema, templates and gate binding',
     'actual':'Pure in-memory strict positive and21 document mutations reject old scope/workflow/wrong candidate/sample1/schema true/enlarged counts. Missing fields, boolFalse as count0, unapproved live/TLS and expiry reject. Three templates match actual candidate scope and are nonexecuting.',
     'evidence':['SCOPE_GATE_TYPED_BINDINGS','TEMPLATE_AND_NO_ENABLE_SWITCH','new18 GateTests','default static launcher'],
     'limit':'No executable activation/decision/once marker created. Approval fixture2031 is synthetic memory only; formal acceptance below is offline preflight, not TLS/live approval.'},
    {'id':'OBS07','result':'PASS_RAW_PRESERVATION','requirement':'59 input raw, original31259 and old136 evidence; original R02 remains REWORK',
     'actual':'Exact Git/raw input and candidate16/delivery50 hashes verified; original baseline/evidence modes/types/blobs unchanged. Original report/manifest hashes unchanged; no old suite or parser counterexample replayed.',
     'evidence':['preflight-result.json','final-preservation.json','retained-boundaries.json'],
     'limit':'Source preservation supports exact reuse of prior finite evidence only; no whole-project or platform acceptance.'}]
save('scope-checks.json',{'task':'A16','candidate_manifest_sha256':CANDIDATE,'scope':'CURRENT_BOOK_SOURCE_INVENTORY_STATIC_OBSERVATION_ONLY',
    'result':'ACCEPTED_OFFLINE_ONLY','limited_result':'ACCEPTED_OFFLINE_OBSERVATION_ONLY','checks':obligations})

# Per coordinator clarification, result uses the fixed gate's exact enum and
# all scope-binding fields; the separate limited label prevents scope inflation.
result=load(E/'independent-report-template-NONEXECUTABLE.json')
result.update({'result':'ACCEPTED_OFFLINE_ONLY','limited_result':'ACCEPTED_OFFLINE_OBSERVATION_ONLY',
    'review_thread_id':'01a15841-0d44-7272-9740-40d013839869',
    'dispatch_workflow':'988a72998b4b6d8f293f21a96056db1343ceecb8',
    'product_commit':'dd22193a30e969aaf90043365f31f84a5a50df59','final_commit':'2453c71c070c153a22a49b772bb2696b3858f5d4',
    'delivery_manifest_sha256':'ae37099d56f8462db27145ce755ec5305fceafd9ebc14ead1a1c3cd966ba8622',
    'book_id':'46007447','viewers':[14,173],
    'new_suite':{'tests':18,'failures':0,'errors':0,'duration_ms':suite['duration_ms'],'shell_exit':0},
    'independent_controls':{'groups':9,'pass':9,'fail':0,'duration_ms':controls['duration_ms'],'shell_exit':0},
    'static_launcher':'PASS_DEFAULT_STATIC_ONLY','findings':[],
    'old_R02_result':'REWORK_UNCHANGED_NOT_A_PARSER_REPAIR','automatic_schema_capability':'DISABLED',
    'current_book_source_target_frontend_applicability':'NOT_RUN_UNKNOWN',
    'body_status':'UNKNOWN','schema_status':'UNKNOWN','sample_status':'NOT_RUN',
    'production_ready':False,'write_eligible':False,'live_authorized':False,'live_activated':False,
    'TLS_approved':False,'platform_save_refresh_reopen':'NOT_RUN','old_suites_run':0,'B_messages':0,
    'acceptance_limits':'Offline observation-only product scope. Not current platform evidence, script/schema correctness, real OS release, TLS exception or executable activation.',
    'next_dependency':'Coordinator verifies fixed report/release and obtains this-run TLS decision before separately binding/activating any live observation.'})
assert result['candidate_manifest_sha256']==CANDIDATE
save('review-result.json',result)
save('findings.json',{'task':'A16','candidate_manifest_sha256':CANDIDATE,'result':'ACCEPTED_OFFLINE_ONLY',
    'scope':result['scope'],'new_findings':[],'old_R02':'REWORK_NOT_RELABELED','not_a_general_parser_pass':True})
save('retained-boundaries.json',{'task':'A16','original_R02':'REWORK; capability disabled, not repaired',
    'old_independent_manifest_sha256':'4f7d35c301412ea8877bb4ca1db94a74ea201003856b34417e47000a91735795',
    'old_independent_report_sha256':'0779d6030752e01824a6b129c1fc805c4822ce004aef0369eca0c47b05d59d92',
    'previous_failures':'Original encoding/packaging/Windows glob/import/test failures and early pending records remain frozen; no old run relabeled PASS',
    'old_C14_C15_C16':'Original NOT_RUN unchanged; no old test or parser replay',
    'result_enum_clarification':'Direct coordinator instruction: result=ACCEPTED_OFFLINE_ONLY with exact observation scope and sample0; task limited display label retained separately',
    'no_real_resource_scope':'All protected resources0; synchronous local review tools/children only, no full-system process scan',
    'TLS_or_live_approval':False,'first_save_content_refresh_reopen':'NOT_RUN'})

copies=[];dest=OUT/'suite-raw';dest.mkdir(exist_ok=False)
source=E/'test-runs/independent-observation-01'
for path in sorted(source.rglob('*')):
    if path.is_file():
        relative=path.relative_to(source);target=dest/relative;target.parent.mkdir(parents=True,exist_ok=True)
        raw=path.read_bytes()
        with target.open('xb') as stream:stream.write(raw)
        copies.append({'path':target.relative_to(OUT).as_posix(),'source_relative':relative.as_posix(),
            'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
save('suite-copy-manifest.json',{'source':str(source),'members':copies,'all_static_bin_files_synthetic_only':True})
print(json.dumps({'result':result['result'],'limited_scope':result['scope'],'new_suite':18,
    'suite_ms':suite['duration_ms'],'independent_groups':9,'independent_ms':controls['duration_ms'],'old_R02':'REWORK_UNCHANGED'}))
