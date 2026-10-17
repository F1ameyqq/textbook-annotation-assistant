"""AST text inventory and a proposal table; NEVER imports product source."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];EX=Path(__file__).resolve().parent
OUT=ROOT/'docs/evidence/A03/execution/P2-R4-bridge-registration'
def sha(v):return hashlib.sha256(v).hexdigest()
def write(path,v):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb')as f:f.write(json.dumps(v,ensure_ascii=False,indent=2).encode('utf8')+b'\n')

def build():
    index=json.loads((OUT/'input-index.json').read_bytes());functions={};classes=[]
    for item in index['product_text']:
        raw=(ROOT/item['copy']).read_bytes();assert sha(raw)==item['sha256'];source=raw.decode('utf8');tree=ast.parse(source);lines=source.splitlines(keepends=True)
        def walk(body,prefix=''):
            for n in body:
                if isinstance(n,ast.ClassDef):
                    classes.append({'path':item['path'],'name':prefix+n.name,'line':n.lineno,'fields':[{'name':x.target.id,'annotation':ast.unparse(x.annotation)}for x in n.body if isinstance(x,ast.AnnAssign)and isinstance(x.target,ast.Name)]})
                    walk(n.body,prefix+n.name+'.')
                elif isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    name=prefix+n.name;header=''.join(lines[n.lineno-1:n.body[0].lineno-1]).strip()
                    if not header:header=lines[n.lineno-1].strip()
                    args=ast.unparse(n.args)
                    functions[(item['path'],name)]={'path':item['path'],'qualified_name':name,'start':n.lineno,'end':n.end_lineno,
                        'signature_source':header,'signature_normalized':n.name+'('+args+')','args':args,'has_kwonly':bool(n.args.kwonlyargs),
                        'source_blob':item['raw_git_blob'],'source_sha256':item['sha256'],'function_source_sha256':sha(ast.get_source_segment(source,n).encode('utf8'))}
        walk(tree.body)
    C='src/annotation/contracts/';T='src/annotation/quality/targetcheck/__init__.py';P='src/annotation/delivery/planner/__init__.py';M='src/annotation/delivery/mock/persistent.py'
    specifications=[
      (C+'__init__.py','validate_bundle','contract_dispatch','Current wrapper selects a03-exchange-1 or falls back to C01. Return is C01 ExchangeBundle or recovery bundle record; no 1.3 handler exists.',
       'Select exact BridgeSelection (version+profile+schema/API/interface pins+role); parse 1.3 with a dedicated typed codec and full business/ref rules, not old 1.1 relabeling. asset_root mandatory for any qualification; structure-only results never authority.'),
      (C+'__init__.py','assert_plan_ready','contract_readiness','Returns the exact plan after version-specific pure readiness/history checks; not a native effect permit.',
       'Separate static plan readiness/quality evidence from runtime CurrentWriteEligibility. Resolve exact plan/snapshot refs, approved PRE admission, TARGET equivalence, current full-book effective pending; preserve UNKNOWN/history. HistoricalDerivationView cannot request current eligibility.'),
      (C+'__init__.py','seal_artifact','artifact_factory','Dispatches sealing by explicit artifact namespace; current supported versions do not include 1.3.',
       'Use selected 1.3 model factory, preserve native 1.3 identity/version and complete refs; reject mixed same-id/revision tuples or 1.1 anchor for current 1.3 output. Never silently set defaults to simulate another version.'),
      (C+'validation.py','validate_bundle','legacy_validator','C01 model/schema, relationships, geometry, policy, formal evidence and state checks.',
       'Keep legacy reader unchanged. New codec must port corresponding business invariants plus R3 typed EvidenceRecord closure; a whitelist or the limited static Package alone is insufficient for native admission.'),
      (C+'recovery.py','validate_recovery_bundle','recovery_validator','Exact 1.1 schema/profile handler, hashes/refs/recovery facts/chains/reports.',
       'Keep 1.1 immutable history reader. New 1.3 codec explicitly defines nullable original receipt, per-action facts/snapshots, report-wide observation and exact effective heads; old equality rules cannot accidentally process 1.3.'),
      (C+'recovery.py','assert_recovery_plan_ready','recovery_readiness','Version-specific plan and effective recovery eligibility, pure data checks.',
       'Use the selected new handler for current 1.3 readiness; runtime still checks actual registration/fence/head/pending and persistent counters. Old 1.1 has read-only status in this bridge, regardless of legacy product capabilities.'),
      (T,'make_artifact','target_factory','Seals anchor.schema_version; only the 1.1 CheckReport branch adds recovery_refs; dependencies currently deduplicate by id/revision.',
       'Bridge factory must select exact 1.3 payload shape for PRE/TARGET/POST; require exact dependency four-tuples, reject conflicting id/revision rather than dropping one. All nested Resource/EvidenceRecord refs must be declared by the produced artifact.'),
      (T,'analyze_target','target_analysis','Computes TARGET checks from graph/current snapshot/config/policy; effective recovery history is special-cased for 1.1.',
       'Keep authorization/capability/coverage/policy and projection support semantics unchanged. Route full history through the new profile effective-head resolver, not generic UNKNOWN deletion or a stale report. Input graph/source/snapshot are current 1.3; old records remain visible read-only.'),
      (T,'check_target','target_producer','Actual TARGET report producer: analyze_target -> make_artifact -> append_artifacts.',
       'Require admitted current INITIAL/POST_HOLD PRE context and exact graph/snapshot/current refs in BridgeContext; recompute TARGET, emit new 1.3 report through its factory. A PASS value is not native PRE or write authority.'),
      (P,'create_plan','planner_create','Validates/recomputes TARGET; generates CREATE_FRAMES per question, preserves directory/order/projection/action-id/dependency rules; seals via make_artifact.',
       'Use the new typed validated bundle/factory and admitted PRE. Preserve graph/snapshot/policy/config exact refs and all algorithm rules, operation=CREATE_FRAMES and previous_receipt=None. Real generation only; no handwritten READY replacement. READY remains a plan property, not runtime authority.'),
      (P,'verify_generated_plan','planner_verify','Validates full bundle, reconstructs upstream historical inputs, regenerates and compares exact plan; 1.1-only observation binding.',
       'First validate the complete original bundle including UNKNOWN/registration/events and all R3 formal evidence. Internal HistoricalDerivationView carries exact creation-input anchor and complete retained Artifact/Resource/EvidenceRecord closure. Compare same derivation core; view is non-exportable/non-sealable and cannot be passed as current eligibility. Never mutate admitted history.'),
      (P,'bind_plan_observation','planner_observation_bridge','1.1-only; checks actual complete observation, action facts, exact effect prefix/progress and current hash/version; returns PublicRecord.',
       'Same comparator/projection rules under exact 1.3 codec. Preserve observation_binding fields, prepared_before, complete progress_refs, genuine source/book/scope/target/session and exact current/before snapshot refs. Runtime proves committed prefix and native read; JSON binding is diagnostic, not permission.'),
      (P,'snapshot_state_equivalent','state_comparison','1.1-only; validates fixed identity and business digest/version of planned/observed snapshots; returns PublicRecord.equivalent and exact refs.',
       'Select state codec/digest by the exact adopted profile. Do not compare arbitrary JSON hashes or timestamps as business equality. Identity/source/scope/session fixed; return comparison data only, never CurrentWriteEligibility.'),
      (M,'PersistentMockSession.create','target_create','Creates known synthetic persistent target, currently requires converted 1.1; descriptor fixes source/book/scope/store/session.',
       'New explicit profile/descriptor binding must be approved and consistent with runtime adoption meta+event/target fence. No implicit unknown DB migration or source replacement; initialize from real approved 1.3 source/snapshot without downgrading.'),
      (M,'PersistentMockSession.open','target_open','Reopens exact known target with expected store/session/key/scope/source.',
       'Additionally bind adopted profile/pins and native target fence. Unknown or interrupted adoption and old held writer uncertainty stay blocked; old handles/rows never regain authority by reopening.'),
      (M,'PersistentMockSession._verify_observation','observation_credential','Reads independent persisted observation row and verifies resource path/raw SHA/deep equality and complete read status.',
       'Preserve exact-row/resource validation and source/book/scope/key/store/session/hash/version binding under the selected codec. Caller dictionaries, completeness flags or resealed resources are not credentials. No new business observe call is hidden here.'),
      (M,'PersistentMockSession.snapshot_from_observation','snapshot_producer','Only from verified persisted read; snapshot payload derives from observation, source ref from fixed descriptor, seals actual anchor version.',
       'Emit exact 1.3 snapshot via approved factory, retaining observation ID/sequence/time/state hash/version provenance and fixed source/target identity. No fabricated merge; output artifact is separately included in full closure before a persisted consumer is committed.'),
      (M,'PersistentMockSession.prepare_action','prepare','Asserts plan readiness, obtains real read/snapshot/prepared_before, binds progress/effect log, registers exact PreparedAction identity+digest/config.',
       'Spend persistent runtime read budget before observe_target; require current 1.3 selection/admitted PRE and native registration. Preserve genuine PreparedAction identity, complete immutable prepared_before, source/book/scope/target/store/session and fresh snapshot. Persisted intent copies cannot recreate this capability.'),
      (M,'PersistentMockSession.verify_prepared_action','prepare_verification','Checks exact issued object/digest/config/plan, independent observation row/snapshot/prepared bytes and recomputed bridge; returns VerifiedPreparedAction.',
       'Preserve exact observer-issued identity and native callback verification, no new observe_target. Verify profile/context plus all original bindings and full package closure. VerifiedPreparedAction is a callback result, never alone a dispatch permit; runtime retains effect gate/intent/permit/fence/head/counter checks.'),
    ]
    rows=[]
    for path,name,role,current,future in specifications:
        item=functions[(path,name)];args=item['args']
        proposed=args+(', bridge_context=None'if item['has_kwonly']else', *, bridge_context=None')
        rows.append({'id':role,'existing':item,'current_input_types':'Exact current signature; ArtifactRef/config/model types from pinned source, no product import',
          'current_output_or_shape':current,'proposal_status':'NOT_IMPLEMENTED_NOT_ADOPTED','proposed_signature':name+'('+proposed+')',
          'proposed_contract':future,'required_selection':'Exact version/profile/pins/interface digest and explicit role; no version-only allowlist',
          'reject':['wrong version/profile/pins','mixed exact refs or scope/source/target','missing approved PRE/native proof for current role','old hold/stale or wrong observation','unresolved current book history','historical view used as current authority'],
          'validation_responsibility':'contracts typed/schema/ref/business checks; quality actual checks/native PRE admission; runtime native registration/fence/head/counters/permits',
          'future_change':{'path':path,'function':name,'algorithm_change':False}})
    proposed_pre={'id':'native_pre_admission','status':'PROPOSED_NOT_EXISTING','future_path':'src/annotation/quality/synthetic_precheck.py',
       'signature':'admit_a03_pre_run(bundle, pre_ref, *, bridge_context, registered_run_handle, actual_snapshot_ref, asset_root)',
       'inputs':['full 1.3 bundle and exact PRE/run/source/graph/policy/snapshot refs','INITIAL without hold or POST_HOLD exact current hold/head/new observation','approved exact oracle/verifier implementation and actual five-check run','private registered run identity, not JSON/signature/PASS'],
       'output':'AdmittedPreRun private proof + immutable check artifacts; never a write permit','reject':['current oracle/profile unadopted','five unavailable checks','old PRE relabeled','missing/replayed/foreign run','hold/snapshot/input hash mismatch']}
    proposal={'proposal_id':'a03-r4-bridge-interface-1-PROPOSAL','status':'INTERFACE_PREPARATION_ONLY_NOT_IMPLEMENTED','base':index['base'],
      'existing_profiles_unchanged':{'new_static_version':'1.3.0-a03-static-proposal','old_read_only':'1.1.0-a-recovery-proposal','profile':'a03-p2-r2-static-2-PROPOSAL','native_adoption':'NOT_APPROVED'},
      'current_source_files':index['product_text'],'interfaces':rows,'proposed_new_pre_boundary':proposed_pre,
      'codec_registration_required':['exact adopted version/profile/schema/API/interface pins','typed model/parser and kind-specific factory','full C01/recovery business rules','R3 EvidenceRecord/typed-frame/reference closure','effective-history/head/report rules','private PRE admission and runtime gate ABI','explicit adoption receipt'],
      'new_types_proposed_not_existing':{'BridgeSelection':'immutable exact codec/pins/role data; no authority','BridgeContext':'controlled context binding selected codec and approved producer/creation inputs; JSON cannot construct native proof','ValidatedA03Bundle':'full typed 1.3 model plus immutable full package and asset root, original refs preserved','AdmittedPreRun':'actual approved producer/run proof for exact inputs, only quality admission','HistoricalDerivationView':'private read-only recomputation projection; never current eligibility or returned admitted bundle','CurrentWriteEligibility':'runtime-private bounded single-use proof after real registry/fence/current head/pending/counters; not assert_plan_ready result'},
      'no_downgrade':'Never change schema_version/content_hash/ref identity to feed 1.3 into 1.1 model or let 1.1 dispatch through new bridge',
      'history_closure':'Full original bundle validated first; retain every UNKNOWN and registration event in admitted history. Historical recomputation uses exact creation-input anchor and complete formal evidence/resource closure; cannot confer current write eligibility.',
      'runtime_split':{'native_only':['actual full registration/source/book/scope/key/store/session equality','owner/generation and persistent target fence','full book current head/pending/holds and CAS','persistent read/parent-entry budgets before target reads','intent/permit uniqueness and effect gate','persist fresh snapshot/resources and all consuming refs before commit'],
                       'pure_bridge':['exact generated projection/action digest and action facts','complete actual-read binding values and applied prefix consistency','state digest/version equivalence result'],
                       'read_budget':'prepare observes a real target read; verification of an already-persisted row/snapshot is local credential checking, not a hidden fourth business read'},
      'progress_and_observation_binding':{'binding_fields':['plan_ref','action_id','action_digest','before_snapshot_ref','observed_snapshot_ref','observation_id','read_sequence','target_key','source_ref','target_session_id','scope_id','baseline_state_hash','current_state_hash','baseline_state_version','current_state_version','prepared_before','applied_prefix','effect_log_delta','comparator_version'],
        'progress':'exact same plan/scope, full action enumeration; predecessors ATTEMPTED+APPLIED with exact intent/result facts; tail NOT_ATTEMPTED; no old attempted tail resume; runtime authenticates committed prefix',
        'fresh_snapshot':'PreparedAction can return a new snapshot separately from initial bundle; runtime must append it/resources and validate full exact closure before creating any persisted intent/fact consumer'},
      'version_qualification_table':[
        {'version':'1.1.0-a-recovery-proposal','role':'READ_ONLY_HISTORY','read':'allowed exact immutable input','dispatch':'REJECT'},
        {'version':'1.3.0-a03-static-proposal','profile':'current R2 static profile','role':'STATIC_INSPECTION','read':'structural/limited static only','dispatch':'REJECT_UNADOPTED'},
        {'version':'exact version in future adoption record','profile':'exact future adopted pins/interface/codec','role':'CURRENT','conditions':['approved codec and source types','actual admitted PRE','fresh verified observation/native preparation','current runtime guards'],'dispatch':'CONDITIONAL_FUTURE_NOT_AUTHORIZED_NOW'},
        {'version':'wrong/unknown/mixed','role':'any current role','dispatch':'REJECT_VERSION_OR_PROFILE'},
        {'version':'otherwise matching','role':'missing run/old hold/wrong observation/history-view','dispatch':'REJECT_PROOF_OR_CURRENTNESS'}],
      'expected_chain_NOT_EXECUTED':[
        {'step':1,'call':'future INITIAL producer + admit_a03_pre_run','artifact':'real new PRE 1.3 bound to singleton Source/Graph/policy/native snapshot; current fixture remains HOLD'},
        {'step':2,'call':'check_target -> analyze_target -> versioned make_artifact','artifact':'new exact 1.3 TARGET, computed from actual current input'},
        {'step':3,'call':'actual create_plan under selected 1.3 codec','artifact':'one generated CREATE_FRAMES action if all original readiness/authorization/coverage/projection checks pass; no handwritten READY'},
        {'step':4,'call':'native prepare_action -> verify_prepared_action -> runtime commit intent/permit/dispatch','artifact':'exact PreparedAction and fresh snapshot/prepare resources; lost/ambiguous result yields UNKNOWN and no original receipt yet'},
        {'step':5,'call':'bounded read-only recovery, no dispatch','artifact':'terminal head for same intent/action, original_receipt_ref=null, immutable fact/readback'},
        {'step':6,'call':'new-version complete receipt materialization','artifact':'late single-action receipt from exact same intent/fact, no head rewrite or tail resume'},
        {'step':7,'call':'independent real report read -> new-version POST/Batch','artifact':'exact effective head/fact and separate report snapshot, all scope items, PENDING/NOT_SUBMITTED; old UNKNOWN preserved'}],
      'singleton_evidence':'Fixed R2 converted-initial.json has one question; frozen planner create_plan loop produces one action only when real prerequisites pass. This preparation does not execute planner or the chain.',
      'not_closed_by_this_document':['product 1.3 codec/model/business handlers','native PRE/oracle adoption','runtime profile/fence/registration/currentness implementation and evidence','actual single-action chain'],
      'B_common_contract_confirmed':False,'native_execution_authorized':False,'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
    write(EX/'bridge-interface-proposal.json',proposal)
    write(OUT/'function-inventory.json',{'source_index':index['product_text'],'functions':list(functions.values()),'type_fields':classes,'mode':'AST_ONLY_NO_PRODUCT_IMPORT'})
    assert len(rows)==19 and all(r['existing']['source_sha256']and r['proposed_signature']for r in rows)
    assert proposal['native_execution_authorized']is False and all(x['step']==i+1 for i,x in enumerate(proposal['expected_chain_NOT_EXECUTED']))
    write(OUT/'interface-static-check.json',{'status':'INTERFACE_TABLE_CONSISTENT_TEXT_ONLY','existing_interface_rows':len(rows),'new_proposed_pre_boundary':1,'source_files':len(index['product_text']),
      'proposal_path':(EX/'bridge-interface-proposal.json').relative_to(ROOT).as_posix(),'proposal_sha256':sha((EX/'bridge-interface-proposal.json').read_bytes()),'product_calls':0,'native_qualification':False})
