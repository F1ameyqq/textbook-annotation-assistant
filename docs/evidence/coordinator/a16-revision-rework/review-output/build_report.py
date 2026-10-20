"""Build fixed independent revision dispositions from completed raw results."""
import json
from pathlib import Path
import hashlib

ROOT=Path('D:/1800-worktrees/a16-r1-review')
OUT=ROOT/'docs/evidence/A16/independent-r1-review'
E=ROOT/'docs/evidence/A16/current-readonly/revisions/frame-binding-r1'
CANDIDATE='071340237c76a7159bd90485e17a774c2f870114baef0199172a2fc5f9547efc'
def load(path):return json.loads(path.read_bytes())
def save(name,data):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2);stream.write('\n')

controls=load(OUT/'independent-controls-result.json')
suite=load(E/'test-runs/independent-r1-01/result.json')
assert len(controls['cases'])==13
assert sum(c['status']=='PASS' for c in controls['cases'])==12
assert controls['first_failure']['case']=='R2_RESERVED_GETTER_SYNTAX'
assert controls['resource_attempts']==[]
assert suite['tests']==75 and suite['success']
commands=load(OUT/'independent-command-results.json')['commands']
assert [x['exit_code'] for x in commands]==[0,1,1]
actual=load(OUT/'reserved-getter-counterexample.actual.json')
assert actual['wire']['status']=='CURRENT_CODE_CONFIRMED' and len(actual['calls'])==11
assert actual['sample_registered']==3 and all(v['status']=='AVAILABLE' for v in actual['sample_content'].values())

finding={'id':'A16-R1-R02-01','priority':2,'result':'CONFIRMED_NEW_REVISION_COUNTEREXAMPLE',
    'title':'Reject reserved keywords in declaration/call binding positions',
    'file':'src/annotation/source/usense/current_readonly/js_wire.py','start_line':112,'end_line':119,
    'related':['src/annotation/source/usense/current_readonly/js_wire.py:235',
        'src/annotation/source/usense/current_readonly/decode.py:327',
        'src/annotation/source/usense/current_readonly/policy.py:67'],
    'requirement':'Unsupported source must remain UNKNOWN and must not register/request sample APIs or yield available/known-empty content.',
    'input':'reserved-getter-invalid.js: otherwise matching narrow native fetch module, with function frameRead renamed to reserved keyword if and caller await if(b,n).',
    'independent_syntax_evidence':'Node --check exits1: SyntaxError Unexpected token if. Valid paired source exits0. Neither file executed as JS.',
    'actual':'Actual new collect accepts binding_proof.complete=true, CURRENT_CODE_CONFIRMED; registers sample3; makes11 synthetic business GETs and yields question/choice/answer AVAILABLE; outcome READONLY_REVIEW.',
    'cause':'lex classifies any identifier-shaped word as id; functions and call_chain accept kind=id for function/parameter/local/call names, without binding-position reserved-word validation.',
    'expected':'Invalid/out-of-supported-grammar source stays UNKNOWN; only six fixed GETs, zero sample registration/GET, no AVAILABLE/KNOWN_EMPTY sample.',
    'correction_scope':'Validate legal supported JS binding identifiers/grammar; reject invalid reserved words. This does not require supporting more JS forms or executing script code.',
    'evidence':['independent-controls-result.json#R2_RESERVED_GETTER_SYNTAX',
        'reserved-getter-counterexample.actual.json','invalid-js-syntax.stderr.raw.txt',
        'independent-command-results.json','independent-input-freeze.json'],
    'limits':'Synthetic transport/UI/original/file boundaries; actual new parser/current_code/register_sample/collect/frame/content binding used. Current frontend applicability and real platform behavior remain unproved.'}
save('findings.json',{'task':'A16','candidate_manifest_sha256':CANDIDATE,'result':'REWORK','findings':[finding]})

dispositions=[
    {'finding':'R01','status':'VERIFIED_CORRECTION_OFFLINE_LIMITED','new_evidence':
        ['new revision suite62 collect cases','R1_CURRENT_FRAME_DATAFLOW','R1_OPTIONAL_ZONE_MISSING',
         'R1_IMAGE_DIGEST_CONFLICT','R1_LATE_ANSWER_INVALIDATION'],
     'verified':'Complete semantic projection before info/body; list order can change; decoder receives exact new binding frames, not initial inventory object; failed/late read invalidates old acceptable text and publishes rejection.',
     'prepared48_affected':['D02','F03','N08','I05','C02'],
     'limit':'No real platform frame state, crop geometry approval, current candidate newness or live browser callbacks.'},
    {'finding':'R02','status':'REWORK','new_evidence':['new75 schema controls','R2_SUPPORTED_RELATION',
        'R2_WRONG_RESPONSE_FIELD','R2_SHADOWED_CALLER','R2_CROSS_ASSET','R2_TOP_ALIAS',
        'R2_RESERVED_GETTER_SYNTAX'],
     'verified':'Specific supported concatenative GET/JSON getters and straight caller give asset/field ranges/digests; several unbound forms stay unknown without sample calls.',
     'remaining':'Reserved-word function declaration accepted despite real syntax rejection, then sample reads become enabled.',
     'prepared48_affected':['N10','D01','D02','D04','Q02'],
     'limit':'Narrow native-fetch form only. No current platform/frontend application proof; no axios/interceptor/alias/arrow/cross-asset bundle qualification.'},
    {'finding':'R03','status':'VERIFIED_CORRECTION_OFFLINE_LIMITED','new_evidence':
        ['new revision JPEG/PNG full decode controls','R3_FULL_DECODE_SAME_SAVE','R3_TRUNCATED_BEFORE_SAVE'],
     'verified':'Exact immutable31x43 independent JPEG bytes fully decoded/hash matched/saved once; PNG decoded; header-readable truncated JPEG rejected before writer call, no retry or global tolerance change.',
     'prepared48_affected':['S03'], 'limit':'Synthetic single-frame images; no current source image read or real source/UI mapping.'},
    {'finding':'R04','status':'VERIFIED_CORRECTION_OFFLINE_LIMITED','new_evidence':
        ['new revision held identity cases','R4_HELD_IDENTITY_AND_PARENT'],
     'verified':'Eight independent fake API/Job/handle/clock cases. Positive same pid/time can release; bool/zero/missing/mismatch/check failure remain UNKNOWN; independent worker error remains failure even after valid release.',
     'prepared48_affected':['L02','L01'], 'limit':'Pure fakes, no native/API/real Job/OS process identity or self-exit proof.'},
    {'finding':'REVISION_GATE_AND_PACKAGE','status':'VERIFIED_OFFLINE_LIMITED','new_evidence':
        ['new75 RevisionGateTests','default static launcher own wait/exit','111 raw preflight'],
     'verified':'New product workflow f04c1579, old workflow rejects, strict TLS default; 73-byte parent initializer present and in candidate19; raw111 and delivery104 verified.',
     'prepared48_affected':['A01','A03','A05','L03'],
     'limit':'No activation or user TLS decision. Existing profile/target/output run authorities not invoked.'}]
save('revision-dispositions.json',{'task':'A16','candidate_manifest_sha256':CANDIDATE,
    'result':'REWORK','dispositions':dispositions,
    'old48_matrix':'Fixed previous requirement-matrix-48.json remains finite prior evidence; no blanket48-pass claim or old-suite rerun.',
    'old_C14_C15_C16':'NOT_RUN_UNCHANGED; new candidate controls are separately identified.'})

rawcopy=OUT/'revision-suite-raw';rawcopy.mkdir(exist_ok=False)
copies=[]
for name in ['result.json','unittest.txt','collect-cases.json','formal-cases.json']:
    data=(E/'test-runs/independent-r1-01'/name).read_bytes()
    with (rawcopy/name).open('xb') as stream:stream.write(data)
    copies.append({'path':'revision-suite-raw/'+name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
save('revision-suite-copy-manifest.json',{'source':str(E/'test-runs/independent-r1-01'),'members':copies})
packaging=load(E/'packaging-failure-01.json')
save('retained-limitations.json',{'task':'A16','author_packaging_failure':packaging,
    'original_A16_evidence39':'Preserved in exact Git blobs; no old failure relabeled PASS',
    'early_author_pending_documents':'Remain original bytes/timing; report is not rewritten to imply independent acceptance',
    'old_run01_run05_tracebacks':'Original fixed summaries stay summaries; no original chat read or reconstructed traceback invented',
    'tooling_error':{'command':'git diff <old> <final> -- ... from raw no-.git directory',
        'observed':'Git treated arguments as no-index; usage returned; no product ran or files changed',
        'correction':'Read-only git -C D:/1800 -c core.longpaths=true diff of exact commits'},
    'own_child_evidence':'Only pid, wait/exit; OS creation identity not held or claimed',
    'actual_current_book_source_target_interfaces':'NOT_RUN_UNKNOWN',
    'A16_TLS_approval':False,'live_activation':False,'first_save_content_refresh_reopen':'NOT_RUN'})

save('review-result.json',{'task':'A16','revision':'R01-R04-same-stage',
    'candidate_manifest_sha256':CANDIDATE,'result':'REWORK',
    'review_thread_id':'01a15841-0d44-7272-9740-40d013839869',
    'dispatch_workflow':'ed182f685db56be8b98d3d97782ee44ee71c0981',
    'product_workflow':'f04c1579353de3fd2006b533d5c792c80190f5b8',
    'product_commit':'cb26282a2340d2136c4db103a07391e593730cf9',
    'final_commit':'8ab0944116b5230b8e69c2f129b635435c243d55',
    'delivery_manifest_sha256':'91d126dcd7204f71bedc3e9b3ca64a84421c536da177376b5a92c36a35ed5c59',
    'revision_suite':{'tests':75,'failures':0,'errors':0,'duration_ms':suite['duration_ms'],'shell_exit':0},
    'static_launcher':{'exit':0,'default_strict':True},
    'independent_controls':{'pass':12,'fail':1,'duration_ms':controls['duration_ms'],'shell_exit':1},
    'R01':'VERIFIED_CORRECTION_OFFLINE_LIMITED','R02':'REWORK_RESERVED_IDENTIFIER_PROOF_GAP',
    'R03':'VERIFIED_CORRECTION_OFFLINE_LIMITED','R04':'VERIFIED_CORRECTION_OFFLINE_LIMITED',
    'first_failure':'R2_RESERVED_GETTER_SYNTAX','product_modified':False,'old_suites_run':False,
    'live_activated':False,'TLS_approved':False,'first_save_content_refresh_reopen':'NOT_RUN',
    'next_dependency':'Coordinator handles same-stage R02 correction and a new frozen delivery; no reviewer repair or rerun.'})
print(json.dumps({'result':'REWORK','new_suite':75,'new_suite_ms':suite['duration_ms'],
    'controls_pass':12,'controls_fail':1,'R01_R03_R04':'VERIFIED_OFFLINE_LIMITED','R02':'REWORK'}))
