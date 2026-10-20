"""Finalize static evidence dispositions; no product execution or additional system checks."""
import json
from pathlib import Path

ROOT=Path('D:/1800-worktrees/a16-live-review');OUT=ROOT/'docs/evidence/A16/independent-live-review'
E=ROOT/'docs/evidence/A16/current-readonly/revisions/observation-only/live-delivery';R=E/'runtime-raw'
def load(p):return json.loads(p.read_bytes())
def save(name,value):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
state=load(R/'current-state.json');author=load(E/'author-report.json');wait=load(E/'author-tool-wait.json')
network=load(OUT/'network-and-counts.json');release=load(OUT/'owned-release-ledger.json')
assert author['steps']==state['steps'] and author['first_block']==network['first_block_original']
assert author['author_wait']==wait and author['release']['worker']==load(R/'worker-release.json')
assert author['release']['launcher']==load(R/'launcher-release.json') and author['release']['occupancy']==load(R/'occupancy.json')
for field in ['fixed_business_gets','original_gets','sample_gets','login_submissions','business_writes','uploads','ocr','retries','static_assets_saved']:
    assert author['counts'][field]==0
assert author['counts']['audit_events']==8 and author['counts']['native_fetch_stage_events']==5 and author['counts']['context_route_events']==3
checks=[
    {'id':'L01_FIXED_INPUT_BINDINGS','result':'ACCEPTED_ARCHIVE_ONLY',
     'evidence':['raw-preservation.json','authorization-and-single-call.json'],
     'proved':'42 raw final blobs;24 delivery+manifest,16 candidate dependencies+candidate manifest. Decision/activation/preflight/markers/cwd/argv agree; actual1 call and wait/exit2.',
     'limits':'Dispatch READY_TO_SEND and pre-call0 retain earlier timepoint. No author active directory or .local read; fingerprint is not authentication.'},
    {'id':'L02_WINDOW_TIMELINE','result':'ACCEPTED_RECORDED_WINDOW_ONLY','evidence':['timeline.json'],
     'proved':'All retained start/audit/release/wait timestamps and held FILETIMEs inside900-second approval window; exact fractional parsing, source strings unchanged.',
     'limits':'10469ms is author reported duration, clock source not specified there. Wall timestamps differ10472.598ms;3.598ms discrepancy cause UNKNOWN, no forced normalization/cross-process monotonic comparison.'},
    {'id':'L03_FIRST_FAILURE','result':'ACCEPTED_FIXED_FAILURE_ONLY','evidence':['network-and-counts.json','runtime-raw/current-state.json'],
     'proved':'First BLOCK is event5, https cdn.bootcdn.net443 Script GET, FETCH_REQUEST_STAGE ORIGIN_BLOCKED, not passive/redirect. First guard failure stays ORIGIN_BLOCKED; final NETWORK_GUARD_STOPPED.',
     'limits':'Current candidate origin policy refusal, not evidence of DNS/TLS/site outage or whole-platform root cause; no CDN permission or success-after-removal inference.'},
    {'id':'L04_COUNTS_AND_SUCCESSORS','result':'ACCEPTED_LIMITED_COUNTS_WITH_UNKNOWNS','evidence':['network-and-counts.json'],
     'proved':'Recorded one launcher/context/navigation attempt. Navigation FAILED; all15 later steps NOT_RUN. No allowed business/original/sample event; counts0 match source/asset absence and author records.',
     'limits':'8 audit events5 native+3 context are not8 requests. HTTP status and auxiliary real send total UNKNOWN. NOT_RUN alone is not a claim of no earlier automatic UI request.'},
    {'id':'L05_OWN_RELEASE','result':'ACCEPTED_PROVEN_OWN_RELEASE_ONLY','evidence':['owned-release-ledger.json'],
     'proved':'Context/runtime closed without errors;3 held children pid+creation time equal and exit observed(occupancy0,worker2,product2), handles closed;2 assigned ownJobs active1→0/closed.',
     'limits':'Streams closure inferred from exact cleanup path and later closed-handle flags, not separate runtime bools. Outer launcher69228 wait/exit2 only; OS creation identity UNKNOWN. No global/post-run scan.'},
    {'id':'L06_CONTENT_AND_COVERAGE','result':'NOT_RUN_NOT_ACCEPTED','evidence':['runtime-raw/current-state.json','review-result.json'],
     'proved':'Authentication not proven; book/directory/frames/source/two pages/originals/mapping not run; no static original saved. Body/schema UNKNOWN, sample NOT_RUN, ready/eligible false.',
     'limits':'No current book/source/target/schema or first-save qualification; original R02 remains REWORK and disabled.'},
    {'id':'L07_PRESERVATION_SCOPE','result':'ACCEPTED_RAW_PRESERVATION_ONLY','evidence':['raw-preservation.json'],
     'proved':'31454 previous Git members mode/type/blob preserved,25 additions only in live-delivery. Runtime12 bytes verified; no actual JS/bin/image/video/source sidecar among additions.',
     'limits':'Only fixed inspected output fields/data; no scan of .local or protected files; no new product/suite/launcher/import/native/network action.'}]
save('evidence-index.json',{'task':'A16','result':'ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY',
    'candidate_manifest_sha256':author['candidate_manifest_sha256'],'checks':checks,
    'raw_refs_base':'../current-readonly/revisions/observation-only/live-delivery/',
    'author_summary_matches_fixed_raw_fields':True})
save('unknowns-and-boundaries.json',{'task':'A16','unknowns':{
    'outer_launcher_OS_creation_identity':'UNKNOWN_NOT_CAPTURED','auxiliary_actual_send_total':'UNKNOWN',
    'navigation_HTTP_status':'UNKNOWN','authentication':'NOT_PROVEN','current_book_source_target':'NOT_RUN',
    'static_original_script_bytes':'0_RETAINED','current_script_full_path_or_version':'NOT_RETAINED',
    'author_duration_clock_kind':'NOT_SPECIFIED_IN_FIXED_WAIT_RECORD','3_598ms_duration_difference_cause':'UNKNOWN',
    'product90byte_stdout':'Only parent byte count/hash, not separately retained raw stream',
    'post_run_machine_or_profile_occupancy':'NOT_CHECKED_NOT_PROVEN'},
    'not_accepted':['Platform access success','authenticated viewer/book','current inventory/source/image/schema',
        'first-question content/frame/save/readback','global process absence','retry or unused live budget'],
    'live_used':1,'live_remaining':0,'retry_authorized':False,'new_window_authorized':False,
    'new_CDN_or_TLS_authority':False,'original_R02':'REWORK_CAPABILITY_DISABLED',
    'other_cases':'HOLD','Q22_replay':False,'B_messages':0,
    'prior_evidence':'All previous offline conclusions and failures remain exactly scoped; no new product regression or platform acceptance inferred.'})
print(json.dumps({'result':'ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY','checks':7,'live_outcome':'FAILED',
    'proven_held_children':len(release['held_processes']),'jobs':len(release['jobs']),
    'outer_launcher_identity':'UNKNOWN','new_product_or_network_actions':0}))
