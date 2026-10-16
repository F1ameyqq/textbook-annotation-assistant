"""Independent offline A02 scenarios; no author test helpers/expected outputs."""
import copy
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import traceback

STAGE = Path('D:/1800/.local/stages/A02-review/frozen-5c928572')
sys.path.insert(0, str(STAGE / 'src'))
sys.dont_write_bytecode = True
from annotation.contracts import (ContractError, artifact_ref, assert_plan_ready, load_bundle,
    policy_ref, seal_artifact, seal_policy, validate_bundle, write_bundle)
from annotation.delivery.mock import MockSession
from annotation.delivery.planner import create_plan, verify_generated_plan
from annotation.quality.targetcheck import SimulationConfig, append_artifacts, check_target

OUT = Path(__file__).resolve().parent / 'independent'
if '--output' in sys.argv:
    OUT = Path(sys.argv[sys.argv.index('--output') + 1]).resolve()
TIME = '2026-10-16T00:00:00Z'
RESULTS = []

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=lambda v: v.model_dump(mode='json')) + '\n', encoding='utf-8')

def get(bundle, kind):
    return next(a for a in bundle.artifacts if a.kind == kind)

def rawget(data, kind):
    return next(a for a in data['artifacts'] if a['kind'] == kind)

def reseal(data):
    """Independent public-API dependency rebuild in original topological order."""
    data = copy.deepcopy(data)
    policies, artifacts = {}, {}
    for i, item in enumerate(data['policies']):
        sealed = seal_policy(item)
        policies[(item['policy_id'], item['revision'])] = policy_ref(sealed)
        data['policies'][i] = sealed
    def refs(value):
        if isinstance(value, list):
            return [refs(x) for x in value]
        if isinstance(value, dict):
            if set(value) == {'artifact_id', 'revision', 'kind', 'content_hash'}:
                return artifacts.get((value['artifact_id'], value['revision']), value)
            if set(value) == {'policy_id', 'revision', 'content_hash'}:
                return policies.get((value['policy_id'], value['revision']), value)
            return {k: refs(v) for k, v in value.items()}
        return value
    for i, item in enumerate(data['artifacts']):
        sealed = seal_artifact(refs(item))
        artifacts[(item['artifact_id'], item['revision'])] = artifact_ref(sealed)
        data['artifacts'][i] = sealed
    return data

class Case:
    def __init__(self, name, fixture='normal'):
        self.name = name
        self.root = OUT / 'cases' / name
        self.root.mkdir(parents=True, exist_ok=False)
        origin = STAGE / 'tests/fixtures/a02' / fixture
        shutil.copytree(origin / 'assets', self.root / 'assets')
        self.bundle = load_bundle(origin / 'input.json')
        raw = json.loads((origin / 'config.json').read_text(encoding='utf-8'))
        raw['allowed_operations'] = tuple(raw['allowed_operations'])
        self.config = SimulationConfig(**raw)
        self.notes = {}
        self.seq = 0
        write_bundle(self.bundle, self.root / 'original-input.json')

    def mutate(self, callback):
        data = self.bundle.model_dump(mode='json')
        callback(data)
        dump(self.root / 'mutation-before-seal.json', data)
        self.bundle = validate_bundle(reseal(data), asset_root=self.root)
        write_bundle(self.bundle, self.root / 'input.json')

    def prepare(self, config=None):
        config = config or self.config
        self.seq += 1
        self.graph, self.pre, self.snapshot = (get(self.bundle, kind) for kind in ('QuestionGraph', 'CheckReport', 'PlatformSnapshot'))
        before = self.bundle.model_dump(mode='json')
        self.planned = check_target(self.bundle, artifact_ref(self.graph), artifact_ref(self.snapshot), artifact_ref(self.snapshot),
            policy_ref(self.bundle.policies[0]), config, artifact_id='review-target-' + self.name + '-' + str(self.seq), created_at=TIME)
        self.target = self.planned.artifacts[-1]
        self.planned = create_plan(self.planned, artifact_ref(self.graph), artifact_ref(self.pre), artifact_ref(self.target),
            artifact_ref(self.snapshot), artifact_ref(self.snapshot), policy_ref(self.bundle.policies[0]), config,
            artifact_id='review-plan-' + self.name + '-' + str(self.seq), created_at=TIME)
        self.plan = self.planned.artifacts[-1]
        assert before == self.bundle.model_dump(mode='json'), 'check/planner mutated input'
        write_bundle(self.planned, self.root / ('planned-' + str(self.seq) + '.json'))
        self.notes['target'] = self.target.payload.model_dump(mode='json')
        self.notes['plan'] = self.plan.payload.model_dump(mode='json')
        return self.planned

    def session(self):
        session = MockSession()
        session.register_target(self.bundle, artifact_ref(get(self.bundle, 'PlatformSnapshot')), asset_root=self.root)
        return session

    def execute(self, fault='applied', index=0, session=None, bundle=None, config=None):
        session = session or self.session()
        self.session_used = session
        before = session.read_target(self.plan.book_id)
        faults = {self.plan.payload.actions[index].action_id: fault} if self.plan.payload.actions else {}
        try:
            result = session.execute(bundle or self.planned, artifact_ref(self.plan), config or self.config, asset_root=self.root,
                receipt_id='review-receipt-' + self.name, created_at=TIME, faults=faults)
            self.receipt = next(a for a in result.artifacts if a.kind == 'ExecutionReceipt' and a.artifact_id == 'review-receipt-' + self.name)
            write_bundle(result, self.root / 'executed.json')
            self.notes['receipt'] = self.receipt.payload.model_dump(mode='json')
            return result, session
        finally:
            after = session.read_target(self.plan.book_id)
            dump(self.root / 'target-before.json', before)
            dump(self.root / 'target-after.json', after)
            dump(self.root / 'action-log.json', session.action_log)
            dump(self.root / 'receipt-history.json', session.receipt_history(self.plan.book_id))
            self.notes['book_paused'] = session.is_paused(self.plan.book_id)

    def reject(self, callback, codes=None):
        try:
            callback()
        except ContractError as error:
            observed = [i['code'] for i in error.issues]
            self.notes.setdefault('rejections', []).append(error.issues)
            if codes:
                assert set(observed) & set(codes), (codes, observed)
            return
        raise AssertionError('Expected rejection but call succeeded')

    def blocked(self, config=None):
        self.prepare(config)
        assert self.plan.payload.readiness == 'BLOCKED' and not self.plan.payload.actions
        out, session = self.execute(config=config)
        assert self.receipt.payload.write_disposition == 'NOT_EXECUTED'
        assert not session.read_target(self.plan.book_id)['target']['frames']
        assert not session.action_log

def run(name, ids, callback, fixture='normal'):
    case = None
    try:
        case = Case(name, fixture)
        callback(case)
        result = {'name': name, 'matrix_ids': ids.split(), 'status': 'PASS', 'observations': case.notes}
    except Exception as error:
        result = {'name': name, 'matrix_ids': ids.split(), 'status': 'FAIL', 'error_type': type(error).__name__, 'error': str(error),
                  'traceback': traceback.format_exc(), 'observations': case.notes if case else {}}
    RESULTS.append(result)
    if case:
        dump(case.root / 'observation.json', result)
    print(name, result['status'], result.get('error', ''), flush=True)

def add_existing(data, mapped=False, same_order=False):
    snapshot = rawget(data, 'PlatformSnapshot')['payload']
    snapshot['questions'].append({'platform_question_id': 'kept-question-north', 'directory_id': 'platform-unit-a', 'platform_order': 23})
    if same_order:
        snapshot['questions'].append({'platform_question_id': 'kept-question-south', 'directory_id': 'platform-unit-a', 'platform_order': 23})
    if mapped:
        rawget(data, 'QuestionGraph')['payload']['questions'][0]['external_refs'].update(platform_question_id='kept-question-north', platform_order=23)

def normal(case):
    def change(data):
        graph = rawget(data, 'QuestionGraph')['payload']
        graph['questions'][0]['external_refs']['printed_number'] = '7'
        graph['questions'][2]['external_refs']['printed_number'] = '7'
        graph['answer_relations'][0]['candidate_fragment_ids'].append('fragment-beta-answer')
        # Change actual geometry so successful output cannot be a copied fixture receipt.
        rawget(data, 'EvidenceBundle')['payload']['regions'][0]['box']['bbox'] = [7, 11, 73, 22]
    case.mutate(change)
    case.prepare()
    assert case.target.payload.decision == 'PASS'
    actions = case.plan.payload.actions
    expected = [(['region-alpha-start', 'region-shared', 'region-alpha-end', 'region-alpha-answer'], ['Q','Q','Q','A']),
                (['region-shared', 'region-child-stem', 'region-child-answer'], ['Q','Q','A']),
                (['region-beta-stem', 'region-beta-answer'], ['Q','A'])]
    for i, (action, (regions, roles)) in enumerate(zip(actions, expected)):
        frames = json.loads(action.expected_after['frames'])
        assert [f['region_id'] for f in frames] == regions
        assert [f['platform_role'] for f in frames] == roles
        assert action.depends_on == ([actions[i-1].action_id] if i else [])
    assert json.loads(actions[0].expected_after['frames'])[0]['box']['bbox'] == [7.,11.,73.,22.]
    assert 'fragment-beta-answer' not in actions[0].source_entity_ids
    result, session = case.execute()
    assert [r.outcome for r in case.receipt.payload.results] == ['APPLIED'] * 3
    target = session.read_target(case.plan.book_id)['target']
    assert len(target['questions']) == 3 and len(target['frames']) == 9
    assert [q['platform_order'] for q in target['questions']] == [1,2,1]
    assert [q['directory_id'] for q in target['questions']] == ['platform-unit-a','platform-unit-a','platform-unit-b']
    assert len({a.action_id for a in actions}) == 3
    assert all(not r.replay_allowed for r in case.receipt.payload.results)
    validate_bundle(result, asset_root=case.root)

def mapping_positive(case, mapped):
    case.mutate(lambda d: add_existing(d, mapped, same_order=True))
    case.prepare()
    assert case.plan.payload.readiness == 'READY'
    first = case.plan.payload.actions[0]
    assert first.target.platform_question_id == ('kept-question-north' if mapped else None)
    assert first.expected_before.get('platform_order' if mapped else 'next_order') == (23 if mapped else 24)
    _, session = case.execute()
    assert len(session.read_target(case.plan.book_id)['target']['questions']) == (4 if mapped else 5)
    assert all(r.outcome == 'APPLIED' for r in case.receipt.payload.results)

def report_gate(case, mode):
    case.prepare()
    pre, target = artifact_ref(case.pre), artifact_ref(case.target)
    if mode == 'pre-missing': pre = dict(pre, artifact_id='absent-pre')
    if mode == 'target-missing': target = dict(target, artifact_id='absent-target')
    if mode == 'same-pre': target = pre
    if mode == 'same-target': pre = target
    case.reject(lambda: create_plan(case.planned, artifact_ref(case.graph), pre, target, artifact_ref(case.snapshot),
        artifact_ref(case.snapshot), policy_ref(case.planned.policies[0]), case.config, artifact_id='review-invalid', created_at=TIME),
        ['MISSING_REFERENCE','TWO_CHECK_STAGES'])

def nonpass(case, decision):
    def mutate(data):
        pre = rawget(data,'CheckReport')['payload']
        pre['decision'] = decision
        pre['checks'][0]['outcome'] = 'FAIL'
        pre['issues'] = [{'issue_id':'review-nonpass','code':'SOURCE_MISSING','scope_type':'scope','scope_id':'synthetic-scope',
            'evidence_refs':['proof-checks'],'severity':'blocking','blocks':['PLAN','APPLY'],
            'suggested_strategy':{'strategy_id':'LOAD_ADJACENT_PAGE' if decision=='RETRY' else 'HUMAN_REVIEW','max_attempts':1 if decision=='RETRY' else 0,'max_cost':0.0},'reason':'Independent negative precheck stub'}]
    case.mutate(mutate)
    case.blocked()

def stale(case, kind):
    case.prepare()
    bundle, graphref, policyref = case.planned, artifact_ref(case.graph), policy_ref(case.bundle.policies[0])
    if kind == 'graph':
        raw = case.graph.model_dump(mode='json'); raw['revision'] += 1; raw['payload']['identity_notes'] += ' reviewer revision'
        new = seal_artifact(raw); bundle = append_artifacts(bundle,new); graphref = artifact_ref(new)
    else:
        data = bundle.model_dump(mode='json'); raw = copy.deepcopy(data['policies'][0]); raw['revision'] += 1; raw['source_notes'].append('Independent changed policy')
        new = seal_policy(raw); data['policies'].append(new); bundle=validate_bundle(data,asset_root=case.root); policyref=policy_ref(new)
    write_bundle(bundle,case.root/'with-new-revision.json')
    case.reject(lambda: create_plan(bundle,graphref,artifact_ref(case.pre),artifact_ref(case.target),artifact_ref(case.snapshot),artifact_ref(case.snapshot),policyref,case.config,artifact_id='review-stale',created_at=TIME),['VERSION_CONFLICT'])

def changed_target(case, platform=False):
    case.prepare(); session=case.session()
    session.inject_external_change(case.plan.book_id, platform_version='new-platform' if platform else None)
    current = session.read_snapshot(case.plan.book_id)
    bundle = append_artifacts(case.planned,current,asset_root=case.root)
    write_bundle(bundle,case.root/'changed-snapshot.json')
    case.reject(lambda: create_plan(bundle,artifact_ref(case.graph),artifact_ref(case.pre),artifact_ref(case.target),artifact_ref(case.snapshot),artifact_ref(current),policy_ref(bundle.policies[0]),case.config,artifact_id='review-stale',created_at=TIME),['TARGET_CHANGED'])
    before=session.read_target(case.plan.book_id)
    case.reject(lambda: case.execute(session=session,bundle=bundle),['TARGET_CHANGED'])
    assert before==session.read_target(case.plan.book_id)
    assert not any(e['event']=='intent' for e in session.action_log)

def config_change(case, **kwargs):
    changed=replace(case.config,**kwargs)
    case.blocked(changed)

def execute_config_change(case, **kwargs):
    case.prepare(); session=case.session(); before=session.read_target(case.plan.book_id)
    case.reject(lambda: case.execute(session=session,config=replace(case.config,**kwargs)),['AUTHORIZATION_CHANGED'])
    assert before==session.read_target(case.plan.book_id) and not session.action_log

def capability(case, mode):
    def mutate(data):
        caps=rawget(data,'PlatformSnapshot')['payload']['capabilities']; cap=next(c for c in caps if c['name']=='frame_readback')
        if mode=='VERSION': cap['platform_version']='wrong-version'
        elif mode=='MISSING': caps.remove(cap)
        else: cap.update(status=mode,evidence_refs=[])
    case.mutate(mutate); case.blocked()

def mapping_negative(case, kind):
    def mutate(data):
        graph=rawget(data,'QuestionGraph')['payload']
        if kind in ('order','directory'):
            add_existing(data,True)
            if kind=='order': graph['questions'][0]['external_refs']['platform_order']=24
        else: graph['questions'][0]['external_refs']['platform_question_id']='' if kind=='empty' else 'missing-platform-question'
    case.mutate(mutate)
    case.blocked(replace(case.config,directory_map={'directory-a':'platform-unit-b','directory-b':'platform-unit-b'}) if kind=='directory' else None)

def missing_directory(case):
    data=case.bundle.model_dump(mode='json'); add_existing(data); rawget(data,'PlatformSnapshot')['payload']['directories']=[]
    dump(case.root/'invalid-input.json',data)
    case.reject(lambda: validate_bundle(reseal(data),asset_root=case.root),['MISSING_REFERENCE'])

def action_tamper(case, kind):
    if kind in ('null','empty','wrong'):
        case.mutate(lambda d: add_existing(d,True))
    elif kind=='nullgraph':
        case.mutate(lambda d: add_existing(d,False))
    case.prepare(); data=case.planned.model_dump(mode='json'); plan=rawget(data,'ApplyPlan')
    action=plan['payload']['actions'][0]
    if kind in ('null','empty','wrong','nullgraph'):
        action['target']['platform_question_id']={'null':None,'empty':'','wrong':'missing','nullgraph':'kept-question-north'}[kind]
    elif kind=='foreign-source': action['source_entity_ids'].append('fragment-beta-answer')
    else: action['expected_after']['frames']='[]'
    dump(case.root/'tampered-plan.json',data)
    sealed=seal_artifact(plan)
    data['artifacts']=[sealed if a['kind']=='ApplyPlan' else a for a in data['artifacts']]
    if kind!='facts':
        case.reject(lambda: validate_bundle(data,asset_root=case.root)); return
    changed=validate_bundle(data,asset_root=case.root); case.plan=next(a for a in changed.artifacts if a.kind=='ApplyPlan')
    case.reject(lambda: case.execute(bundle=changed),['PLAN_CHANGED'])
    assert not case.session_used.action_log

def unsupported(case, kind):
    case.mutate(lambda d: rawget(d,'QuestionGraph')['payload']['questions'][1].update(question_type=kind))
    case.blocked()

def fault(case, mode, index=0):
    case.prepare(); output,session=case.execute(mode,index)
    expected=['APPLIED']*3
    if mode=='not_applied': expected=['NOT_APPLIED']*3
    elif mode in ('lost_response','readback_failure','contradictory','partial'):
        expected=['APPLIED']*index+['UNKNOWN']+['NOT_APPLIED']*(2-index)
    assert [r.outcome for r in case.receipt.payload.results]==expected
    state=session.read_target(case.plan.book_id)
    count=9 if expected==['APPLIED']*3 else 0 if mode=='not_applied' else (7 if index==1 else 3 if mode=='partial' else 4)
    assert len(state['target']['frames'])==count
    assert all(not r.replay_allowed for r in case.receipt.payload.results)
    records={e.evidence_id:e for e in output.evidence}
    reads=[e for e in session.action_log if e['event']=='readback']
    for result,read in zip(case.receipt.payload.results,reads):
        before=json.loads((case.root/records[result.before_evidence_refs[0]].resource.path).read_text(encoding='utf-8'))
        after=json.loads((case.root/result.readback.path).read_text(encoding='utf-8'))
        assert read['outcome']==result.outcome
        if result.outcome=='NOT_APPLIED':
            assert after['read_status']=='OK' and not read['dispatched'] if mode!='not_applied' or result!=case.receipt.payload.results[0] else after['read_status']=='OK'
            qid=next(a.target.question_id for a in case.plan.payload.actions if a.action_id==result.action_id)
            assert qid not in before['internal_bindings'] and qid not in after['view']['internal_bindings']
            assert result.effect_match=='ABSENT' and result.next_step=='RECHECK_TARGET'
        if result.outcome=='UNKNOWN':
            assert result.effect_match=='INDETERMINATE' and result.next_step=='RECONCILE'
            assert session.is_paused(case.plan.book_id)
    case.notes['manual_expected_outcomes']=expected
    case.notes['independent_frame_count']=count
    case.notes['dispatched_flags']=[r['dispatched'] for r in reads]

def replay(case, mode):
    case.prepare(); result,session=case.execute(mode)
    before=session.read_target(case.plan.book_id); oldlog=session.action_log
    case.reject(lambda: session.execute(case.planned,artifact_ref(case.plan),case.config,asset_root=case.root,receipt_id='review-repeat',created_at=TIME),['BOOK_WRITE_PAUSED' if mode=='lost_response' else 'REPLAY_FORBIDDEN'])
    assert before==session.read_target(case.plan.book_id) and oldlog==session.action_log

def unknown_gate(case, mode):
    case.prepare(); result,session=case.execute('lost_response')
    data=case.planned.model_dump(mode='json'); graph=rawget(data,'QuestionGraph')
    if mode=='run':
        for a in data['artifacts']: a['run_id']='different-review-run'
    if mode=='scope':
        def replace_scope(v):
            if isinstance(v,list): return [replace_scope(x) for x in v]
            if isinstance(v,dict): return {k:replace_scope(x) for k,x in v.items()}
            return 'different-review-scope' if v=='synthetic-scope' else v
        data=replace_scope(data)
    if mode=='question':
        def replace_q(v):
            if isinstance(v,list): return [replace_q(x) for x in v]
            if isinstance(v,dict): return {k:replace_q(x) for k,x in v.items()}
            return 'different-review-question' if v=='question-alpha' else v
        data=replace_q(data)
    plan=rawget(data,'ApplyPlan'); plan['artifact_id']='new-review-plan'
    if mode=='action': plan['payload']['actions'][0]['action_id']='new-review-action'; plan['payload']['actions'][1]['depends_on']=['new-review-action']
    new=validate_bundle(reseal(data),asset_root=case.root)
    write_bundle(new,case.root/'history-omitted-new-plan.json')
    candidate=get(new,'ApplyPlan'); before=session.read_target(case.plan.book_id); oldlog=session.action_log; history=session.receipt_history(case.plan.book_id)
    case.reject(lambda: session.execute(new,artifact_ref(candidate),replace(case.config,scope_id='different-review-scope') if mode=='scope' else case.config,asset_root=case.root,receipt_id='new-review-receipt',created_at=TIME),['BOOK_WRITE_PAUSED'])
    assert before==session.read_target(case.plan.book_id) and oldlog==session.action_log and history==session.receipt_history(case.plan.book_id)

def fault_evidence(case):
    case.prepare(); session=case.session(); original=Path.open; writes=[0]
    def injected(path, mode='r', *args, **kwargs):
        if mode=='xb' and path.name.startswith('a02-'):
            writes[0]+=1
            if writes[0]==2: raise OSError('independent injected evidence-write failure after first simulated write')
        return original(path,mode,*args,**kwargs)
    Path.open=injected
    try:
        try: case.execute(session=session)
        except OSError as error: case.notes['injected_failure']=str(error)
        else: raise AssertionError('Evidence failure not triggered')
    finally: Path.open=original
    assert len(session.read_target(case.plan.book_id)['target']['frames'])==4 and session.is_paused(case.plan.book_id)
    before=session.read_target(case.plan.book_id); oldlog=session.action_log
    case.reject(lambda: session.execute(case.planned,artifact_ref(case.plan),case.config,asset_root=case.root,receipt_id='after-failure',created_at=TIME),['BOOK_WRITE_PAUSED'])
    assert before==session.read_target(case.plan.book_id) and oldlog==session.action_log

def summary(case, exception=False):
    case.prepare(); bundle,session=case.execute()
    spec=importlib.util.spec_from_file_location('frozen_demo',STAGE/'examples/a02/run.py'); demo=importlib.util.module_from_spec(spec); spec.loader.exec_module(demo)
    statuses={'question-alpha':'EXCEPTION','question-beta':'SKIPPED','question-missing':'EXCEPTION'} if exception else {}
    out=demo.summarize(bundle,artifact_ref(case.receipt),statuses,case.config)
    write_bundle(out,case.root/'final.json'); batch=get(out,'BatchReport')
    assert batch.payload.total_expected==(4 if exception else 3)
    assert batch.payload.content_check_status=='PENDING' and batch.payload.submission_status=='NOT_SUBMITTED'
    assert batch.payload.state==('NEEDS_REVIEW' if exception else 'CONTENT_PENDING')
    if exception: assert {q.question_id:q.state for q in batch.payload.questions}=={'question-alpha':'EXCEPTION','question-child':'PENDING','question-beta':'SKIPPED','question-missing':'EXCEPTION'}
    case.notes['batch']=batch.payload.model_dump(mode='json')

def update_reject(case):
    case.prepare()
    for op in ('UPDATE_FRAMES','DELETE_FRAMES'):
        case.reject(lambda: create_plan(case.planned,artifact_ref(case.graph),artifact_ref(case.pre),artifact_ref(case.target),artifact_ref(case.snapshot),artifact_ref(case.snapshot),policy_ref(case.bundle.policies[0]),case.config,artifact_id='review-update',created_at=TIME,operation=op),['UPDATE_UNSUPPORTED'])
    case.reject(lambda: create_plan(case.planned,artifact_ref(case.graph),artifact_ref(case.pre),artifact_ref(case.target),artifact_ref(case.snapshot),artifact_ref(case.snapshot),policy_ref(case.bundle.policies[0]),case.config,artifact_id='review-update',created_at=TIME,previous_receipt={'artifact_id':'absent-receipt'}),['UPDATE_UNSUPPORTED'])

def additional_policy(case, mode):
    if mode=='platform':
        case.prepare(); data=case.planned.model_dump(mode='json'); rawget(data,'ApplyPlan')['payload']['execution_mode']='PLATFORM'
        dump(case.root/'invalid-platform-plan.json',data)
        case.reject(lambda:validate_bundle(reseal(data),asset_root=case.root)); return
    if mode=='forged-target':
        case.prepare(); raw=case.target.model_dump(mode='json'); raw['artifact_id']='review-forged-target'; raw['payload']['checks'][0]['reason']='Pretend this is independently verified'
        forged=seal_artifact(raw); data=append_artifacts(case.planned,forged,asset_root=case.root)
        case.reject(lambda:create_plan(data,artifact_ref(case.graph),artifact_ref(case.pre),artifact_ref(forged),artifact_ref(case.snapshot),artifact_ref(case.snapshot),policy_ref(data.policies[0]),case.config,artifact_id='review-forged-plan',created_at=TIME),['TARGET_CHECK_STALE']); return
    def mutate(data):
        data['policies'][0].update(confirmation_status='UNRESOLVED',applicability='PROPOSAL_ONLY')
    case.mutate(mutate); case.blocked()

def defensive_reads(case):
    case.prepare(); result,session=case.execute('lost_response')
    actual=session.read_target(case.plan.book_id); log=session.action_log; history=session.receipt_history(case.plan.book_id)
    view=session.read_target(case.plan.book_id); view['target']['frames'].clear()
    logcopy=session.action_log; logcopy[0].clear()
    hcopy=session.receipt_history(case.plan.book_id); hcopy[0]['artifacts'].clear()
    assert session.read_target(case.plan.book_id)==actual and session.action_log==log and session.receipt_history(case.plan.book_id)==history
    assert session.is_paused(case.plan.book_id)
    # The standalone recomputation helper is not a write gate; the complete mock entry must still reject.
    case.reject(lambda:session.execute(result,artifact_ref(case.plan),case.config,asset_root=case.root,receipt_id='review-complete-unknown',created_at=TIME),['BOOK_WRITE_PAUSED'])
    case.notes['history_defensive_copy']=True

def external_conflict(case):
    def mutate(data):
        add_existing(data,False)
        rawget(data,'QuestionGraph')['payload']['questions'][1]['external_refs'].update(platform_question_id='kept-question-north',platform_order=23)
    case.mutate(mutate); case.prepare(); session=case.session(); real_write=session._write
    def outside_actor(book,action,partial=False):
        result=real_write(book,action,partial)
        if action.action_id==case.plan.payload.actions[0].action_id:
            target=session._targets[book]
            foreign=copy.deepcopy(target['payload']['frames'][0]); foreign.update(platform_frame_id='outside-frame',platform_question_id='kept-question-north')
            target['payload']['frames'].append(foreign)
            session.inject_external_change(book)
        return result
    session._write=outside_actor
    _,session=case.execute(session=session)
    outcomes=[r.outcome for r in case.receipt.payload.results]
    intents=[e['action']['action_id'] for e in session.action_log if e['event']=='intent']
    assert outcomes==['APPLIED','UNKNOWN','NOT_APPLIED'] and intents==[case.plan.payload.actions[0].action_id]
    assert any(f['platform_frame_id']=='outside-frame' for f in session.read_target(case.plan.book_id)['target']['frames'])
    case.notes['synthetic_outside_actor_instrumentation']='After first real mock write, insert a foreign frame into second mapped question and call public inject_external_change; no implementation modified.'

def portable(case):
    case.prepare(); result,_=case.execute()
    destination=case.root/'relocated'; destination.mkdir(); shutil.copytree(case.root/'assets',destination/'assets')
    write_bundle(result,destination/'exchange.json'); assert load_bundle(destination/'exchange.json')==result

def same_bbox(case):
    def mutate(data):
        ev=rawget(data,'EvidenceBundle')['payload']; first=ev['regions'][0]['box']['bbox']
        # Two existing different original image bindings keep separate region/entity identity.
        other=next(r for r in ev['regions'] if r['region_id']=='region-beta-stem')
        other['box']['bbox']=copy.deepcopy(first)
    case.mutate(mutate); case.prepare(); _,session=case.execute()
    state=session.read_target(case.plan.book_id)
    assert len(state['target']['frames'])==9
    first=json.loads(case.plan.payload.actions[0].expected_after['frames'])[0]
    other=json.loads(case.plan.payload.actions[2].expected_after['frames'])[0]
    assert first['box']['bbox']==other['box']['bbox'] and first['box']['image']['asset_id']!=other['box']['image']['asset_id']

def unknown_summary(case):
    case.prepare(); result,_=case.execute('lost_response')
    spec=importlib.util.spec_from_file_location('frozen_demo_unknown',STAGE/'examples/a02/run.py'); demo=importlib.util.module_from_spec(spec); spec.loader.exec_module(demo)
    final=demo.summarize(result,artifact_ref(case.receipt),{},case.config)
    write_bundle(final,case.root/'final.json'); batch=get(final,'BatchReport').payload
    assert batch.state=='NEEDS_RECONCILIATION' and batch.questions[0].state=='UNKNOWN'
    assert batch.content_check_status=='PENDING' and batch.submission_status=='NOT_SUBMITTED'
    case.notes['batch']=batch.model_dump(mode='json')

def main():
    OUT.mkdir(exist_ok=False)
    run('computed-normal','F03 F04 G01 I08 S01 S02 S03 S05 S08 E01 E09',normal)
    run('nonempty-new','G02 I09',lambda c:mapping_positive(c,False))
    run('explicit-mapped','G03 I08 I09',lambda c:mapping_positive(c,True))
    for mode,ids in [('pre-missing','G04'),('target-missing','G05'),('same-pre','G06'),('same-target','G06')]: run(mode,ids,lambda c,m=mode:report_gate(c,m))
    for decision in ('HOLD','EXCEPTION','RETRY'): run('nonpass-'+decision.lower(),'G07',lambda c,d=decision:nonpass(c,d))
    for kind,ids in [('graph','G08'),('policy','G09')]: run('stale-'+kind,ids,lambda c,k=kind:stale(c,k))
    run('target-changed','G10',changed_target)
    run('platform-changed','G10 G15 G20',lambda c:changed_target(c,True))
    for name,kwargs,ids in [('wrong-book',{'book_id':'wrong-book'},'G11 G19'),('wrong-target',{'target_id':'wrong-target'},'G11'),('wrong-scope',{'scope_id':'wrong-scope'},'G12'),('no-operation',{'allowed_operations':()},'G12'),('no-directory',{'directory_map':{}},'G12')]:
        run('plan-'+name,ids,lambda c,k=kwargs:config_change(c,**k))
        run('execute-'+name,'G20',lambda c,k=kwargs:execute_config_change(c,**k))
    for mode,ids in [('UNKNOWN','G13'),('UNSUPPORTED','G14'),('MISSING','G13'),('VERSION','G15')]: run('capability-'+mode.lower(),ids,lambda c,m=mode:capability(c,m))
    run('persistent-capability','G16',lambda c:config_change(c,session_mode='PERSISTENT'))
    for mode,ids in [('empty','I04'),('missing','I02'),('order','I03'),('directory','I08')]: run('mapping-'+mode,ids,lambda c,m=mode:mapping_negative(c,m))
    run('missing-directory','I01',missing_directory)
    for mode,ids in [('null','I06'),('empty','I04'),('wrong','I05'),('nullgraph','I07'),('foreign-source','S04'),('facts','F03 S08')]: run('action-'+mode,ids,lambda c,m=mode:action_tamper(c,m))
    for kind in ('combination','seven_choice','unsupported'): run('unsupported-'+kind,'G17',lambda c,k=kind:unsupported(c,k))
    for mode,ids in [('not_applied','E02 E08'),('response_lost_readable','E03'),('lost_response','E04 E08'),('contradictory','E05'),('readback_failure','E06 E07'),('partial','E05')]: run('effect-'+mode,ids,lambda c,m=mode:fault(c,m))
    run('effect-lost-second','S05 E08',lambda c:fault(c,'lost_response',1))
    for mode in ('applied','not_applied','lost_response'): run('replay-'+mode,'U06',lambda c,m=mode:replay(c,m))
    for mode,ids in [('action','U01'),('run','U02'),('question','U03'),('scope','U04')]: run('unknown-'+mode,ids,lambda c,m=mode:unknown_gate(c,m))
    run('evidence-write-failure','E08 U07',fault_evidence)
    run('update-rejected','U08 U09 U10',update_reject)
    run('content-pending','B02 B03',summary)
    run('independent-denominator','B01',lambda c:summary(c,True),'exceptions')
    dump(OUT/'results.json',{'commit':'5c9285720c8628c5198bedeadfc9f6bc7826a914','source':str(STAGE),'results':RESULTS,
        'pass_count':sum(r['status']=='PASS' for r in RESULTS),'fail_count':sum(r['status']=='FAIL' for r in RESULTS)})
    return int(any(r['status']!='PASS' for r in RESULTS))

if __name__=='__main__':
    if '--supplement' in sys.argv:
        run('stale-policy-rechecked','G09',lambda c:stale(c,'policy'))
        for mode,ids in [('unresolved','G17'),('platform','G18'),('forged-target','G19')]:
            run('additional-'+mode,ids,lambda c,m=mode:additional_policy(c,m),'choice' if mode=='platform' else 'normal')
        run('defensive-history','U07 E09',defensive_reads)
        run('outside-second-conflict','S06',external_conflict)
        run('relocated-package','F05',portable)
        run('same-bbox-different-image','S07',same_bbox)
        run('unknown-batch','B04',unknown_summary)
        dump(OUT/'supplement-results.json',{'commit':'5c9285720c8628c5198bedeadfc9f6bc7826a914','results':RESULTS,'pass_count':sum(r['status']=='PASS' for r in RESULTS),'fail_count':sum(r['status']=='FAIL' for r in RESULTS),
            'review_harness_correction':'Original stale-policy scenario used a shallow source_notes list copy and failed hash validation before the intended gate. Original evidence preserved; this recheck uses deepcopy and does not modify frozen code.'})
        sys.exit(any(r['status']!='PASS' for r in RESULTS))
    sys.exit(main())
