"""Fixed real Q1 -> A C01 HOLD diagnostic -> BLOCKED plan -> NOT_EXECUTED.

This B integration probe never grants A approval or calls a platform. The only
synthetic input is an explicitly empty local diagnostic target with no permitted
operations. A's unchanged TARGET/planner/mock produce the final artifacts.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import shutil
import sys
from datetime import datetime, timezone

A_COMMIT = '37089f9e0229da76ae1c45461b7e63929590be56'
PIN_SHA = '3174f9981ffc336b3d576d78afe3e6932e042521011555272dc94d9b564e1fe0'
QID = 'q-e92a499995ca1bbd570a2a09'
MAPPING_SHA = '09f9937a411a5ed5a7003019306a456937a422fc874a9baaae52817f02ccf06a'
MAPPING_MANIFEST_SHA = 'a831da5d89f2620220cff19565c5aff1825e47c5b0d900f7e269c61dbd590e2f'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def pin_a(root, pins):
    raw = pins.read_bytes()
    if sha(raw) != PIN_SHA:
        raise ValueError('A source pin list differs from fixed B review')
    manifest = json.loads(raw)
    if manifest['a_commit'] != A_COMMIT:
        raise ValueError('wrong A commit')
    expected = {row['path'] for row in manifest['files']}
    actual = {p.relative_to(root).as_posix() for p in (root / 'src').rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    if expected != actual:
        raise ValueError('A source inventory differs from pinned commit')
    for row in manifest['files']:
        if sha((root / row['path']).read_bytes()) != row['sha256']:
            raise ValueError('A source bytes differ: ' + row['path'])
    return manifest


def run(a_root, mapping, output, pins, created_at=None):
    a_root, mapping, output = a_root.resolve(), mapping.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError('use a new output directory; history is immutable')
    pinned = pin_a(a_root, pins)
    if sha(mapping.read_bytes()) != MAPPING_SHA:
        raise ValueError('mapping bytes differ from fixed Q1 candidate mapping')
    manifest_path = mapping.parent / 'manifest.json'
    if sha(manifest_path.read_bytes()) != MAPPING_MANIFEST_SHA:
        raise ValueError('mapping manifest differs from fixed Q1 mapping')
    mapping_manifest = json.loads(manifest_path.read_bytes())
    for row in mapping_manifest['files']:
        member = (mapping.parent / row['path']).resolve()
        if not member.is_relative_to(mapping.parent):
            raise ValueError('mapping member escapes root')
        raw = member.read_bytes()
        if sha(raw) != row['sha256'] or len(raw) != row['bytes']:
            raise ValueError('fixed mapping dependency differs: ' + row['path'])
    created_at = created_at or datetime.now(timezone.utc).isoformat(timespec='seconds')
    if datetime.fromisoformat(created_at.replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('created_at needs an explicit timezone')
    if any(name == 'annotation' or name.startswith('annotation.') for name in sys.modules):
        raise RuntimeError('run this CLI in a fresh process to avoid mixed A/B imports')
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(a_root / 'src'))
    from annotation.contracts import (artifact_ref, content_digest, load_bundle,
        policy_ref, seal_artifact, validate_bundle, write_bundle)
    from annotation.delivery.mock import MockSession
    from annotation.delivery.planner import create_plan
    from annotation.quality.targetcheck import (SimulationConfig, append_artifacts,
        check_target, coverage_for)

    # The mapper owns exact candidate/native/pixel verification. Revalidate every
    # resource through A's independent public consumer after copying to a new root.
    original = load_bundle(mapping, verify_assets=True)
    shutil.copytree(mapping.parent, output)
    bundle = load_bundle(output / mapping.name, verify_assets=True)
    if bundle.model_dump(mode='json') != original.model_dump(mode='json'):
        raise ValueError('copied mapping differs')
    source, evidence, graph = [next(a for a in bundle.artifacts if a.kind == k)
                              for k in ('SourceBundle', 'EvidenceBundle', 'QuestionGraph')]
    if len(bundle.artifacts) != 3 or len(bundle.policies) != 1:
        raise ValueError('only one new mapped Q1 source/evidence/graph and policy allowed')
    if [q.question_id for q in graph.payload.questions] != [QID]:
        raise ValueError('probe is restricted to real question one')
    if any(a.book_id != '46007447' or a.scope_id != graph.scope_id for a in bundle.artifacts):
        raise ValueError('fixed book or scope differs')
    geometry = [(r.box.image.asset_id, tuple(r.box.bbox)) for r in evidence.payload.regions]
    if len(geometry) != 6 or len(set(geometry)) != 6:
        raise ValueError('fixed Q1 mapping requires six unique semantic regions')
    if any(a.producer.evidence_mode != 'OBSERVED' for a in bundle.artifacts):
        raise ValueError('real B input must remain OBSERVED')
    if any(a.provenance != 'ORIGINAL' for a in source.payload.assets):
        raise ValueError('original image provenance cannot be relabelled')
    if any(r.status != 'UNRESOLVED' or r.selected_fragment_ids for r in graph.payload.answer_relations):
        raise ValueError('unapproved Q1 relation must remain unselected')
    policy = bundle.policies[0]
    if policy.confirmation_status != 'UNRESOLVED' or policy.applicability != 'PROPOSAL_ONLY':
        raise ValueError('no A confirmation has been provided')
    refs = {a.kind: artifact_ref(a) for a in bundle.artifacts}
    pref = policy_ref(policy)
    token = content_digest({'inputs': refs, 'policy': pref, 'probe': 'b-q1-hold-1',
                            'created_at': created_at})[:20]
    run_id = 'b-q1-a-hold-' + token

    def envelope(kind, suffix, payload, inputs, mode, module, config):
        return seal_artifact({'schema_version': graph.schema_version,
            'artifact_id': 'b-q1-' + suffix + '-' + token, 'revision': 1,
            'kind': kind, 'run_id': run_id, 'book_id': graph.book_id,
            'scope_id': graph.scope_id, 'input_refs': inputs,
            'producer': {'module': module, 'implementation_version': 'b-q1-hold-1',
                         'config_version': config, 'policy_versions': [pref],
                         'model_version': None, 'prompt_version': None, 'evidence_mode': mode},
            'created_at': created_at, 'payload': payload})

    outcomes = [
        ('source_integrity', 'PASS', 'A load_bundle verified all original image/resource bytes and dimensions; source provenance only.'),
        ('structure', 'UNAVAILABLE', 'C01 structure is valid, but six candidate regions and text normalization lack A acceptance.'),
        ('answer_matching', 'UNAVAILABLE', 'Candidate Q1 to 1.D correspondence remains UNRESOLVED; no human or A approval.'),
        ('coverage', 'UNAVAILABLE', 'Thirty scope exclusions are proposals; whole chapter coverage and single-question scope policy are not accepted.'),
        ('policy', 'FAIL', 'Policy confirmation is UNRESOLVED; A real-observed PRE_APPLY producer and OBSERVED/SIMULATED consumer support are absent.'),
    ]
    proof = {'format': 'b-q1-current-pre-diagnostic/0.1', 'run_id': run_id,
             'a_commit': A_COMMIT, 'input_refs': refs, 'policy_ref': pref,
             'checks': [{'check_id': key, 'outcome': result, 'reason': why} for key, result, why in outcomes],
             'decision': 'HOLD', 'a_formal_pre_apply': False,
             'business_acceptance': False, 'scope_exclusions_accepted': False}
    write(output / 'probe/pre-diagnostic-evidence.json', proof)
    proof_id = 'b-q1-pre-proof-' + token
    data = bundle.model_dump(mode='json')
    data['evidence'].append({'evidence_id': proof_id, 'mode': 'OBSERVED',
        'description': 'New B factual diagnostic, not A PRE_APPLY acceptance or human review.',
        'resource': {'path': 'probe/pre-diagnostic-evidence.json', 'media_type': 'application/json',
                     'sha256': sha((output / 'probe/pre-diagnostic-evidence.json').read_bytes())}})
    bundle = validate_bundle(data, asset_root=output)
    coverage, _ = coverage_for(bundle, graph)
    issue_codes = {'structure': 'CONTENT_MISMATCH', 'answer_matching': 'ANSWER_AMBIGUOUS',
                   'coverage': 'UNASSIGNED_CONTENT', 'policy': 'POLICY_UNRESOLVED'}
    issues = [{'issue_id': 'b-q1-pre-' + key + '-' + token, 'code': issue_codes[key],
               'scope_type': 'question', 'scope_id': QID, 'evidence_refs': [proof_id],
               'severity': 'blocking', 'blocks': ['PLAN', 'APPLY', 'COMPLETE'],
               'suggested_strategy': {'strategy_id': 'HUMAN_REVIEW', 'max_attempts': 0, 'max_cost': 0.0},
               'reason': why} for key, result, why in outcomes if result != 'PASS']
    pre = envelope('CheckReport', 'pre-diagnostic', {
        'stage': 'PRE_APPLY', 'subject': refs['QuestionGraph'], 'graph': refs['QuestionGraph'],
        'policy': pref, 'snapshot': None, 'receipt': None, 'coverage': coverage,
        'checks': [dict(check_id=k, outcome=o, reason=r, evidence_refs=[proof_id]) for k, o, r in outcomes],
        'issues': issues, 'decision': 'HOLD',
        'reason': 'B current diagnostic only; A real-source five-check acceptance is unavailable.'},
        list(refs.values()), 'OBSERVED', 'b-q1-current-diagnostic', 'b-q1-hold-1')
    bundle = append_artifacts(bundle, pre, asset_root=output)
    write_bundle(bundle, output / 'prechecked.json')

    target_id = 'b-local-q1-diagnostic-only'
    config = SimulationConfig(book_id=graph.book_id, target_id=target_id,
        scope_id=graph.scope_id, directory_map={q.directory_id: 'local-diagnostic-directory'
        for q in graph.payload.questions}, allowed_operations=())
    local_state = {'kind': 'EMPTY_LOCAL_DIAGNOSTIC_FIXTURE', 'target_id': target_id,
                   'not_a_platform_observation': True, 'a_authorization': False,
                   'allowed_operations': [], 'questions': [], 'frames': []}
    write(output / 'probe/local-target-fixture.json', local_state)
    target_proof_id = 'b-q1-local-target-proof-' + token
    data = bundle.model_dump(mode='json')
    data['evidence'].append({'evidence_id': target_proof_id, 'mode': 'SYNTHETIC',
        'description': 'Empty local diagnostic fixture only, not a platform snapshot or execution permission.',
        'resource': {'path': 'probe/local-target-fixture.json', 'media_type': 'application/json',
                     'sha256': sha((output / 'probe/local-target-fixture.json').read_bytes())}})
    bundle = validate_bundle(data, asset_root=output)
    snapshot = envelope('PlatformSnapshot', 'local-target', {
        'target_id': target_id, 'platform_version': 'LOCAL_DIAGNOSTIC_ONLY',
        'observed_at': created_at, 'observed_version': 'empty-fixture-1',
        'observed_hash': content_digest(local_state), 'authorized_scope_id': graph.scope_id,
        'directories': ['local-diagnostic-directory'], 'questions': [], 'frames': [],
        'capabilities': [], 'evidence_refs': [target_proof_id]},
        [refs['SourceBundle']], 'SYNTHETIC', 'b-local-diagnostic-fixture', config.version)
    bundle = append_artifacts(bundle, snapshot, asset_root=output)
    session = MockSession()
    session.register_target(bundle, artifact_ref(snapshot), asset_root=output,
                            source_ref=refs['SourceBundle'])
    before = session.read_target(graph.book_id)
    snapshot_ref = artifact_ref(snapshot)
    bundle = check_target(bundle, refs['QuestionGraph'], snapshot_ref, snapshot_ref, pref, config,
                          artifact_id='b-q1-a-target-' + token, created_at=created_at, run_id=run_id)
    target = bundle.artifacts[-1]
    write_bundle(bundle, output / 'targetchecked.json')
    bundle = create_plan(bundle, refs['QuestionGraph'], artifact_ref(pre), artifact_ref(target),
        snapshot_ref, snapshot_ref, pref, config, artifact_id='b-q1-a-plan-' + token,
        created_at=created_at, run_id=run_id)
    plan = bundle.artifacts[-1]
    if plan.payload.readiness != 'BLOCKED' or plan.payload.actions:
        raise RuntimeError('fail closed: this Q1 probe must never become executable')
    write_bundle(bundle, output / 'planned.json')
    bundle = session.execute(bundle, artifact_ref(plan), config, asset_root=output,
        receipt_id='b-q1-a-receipt-' + token, created_at=created_at)
    receipt = bundle.artifacts[-1]
    after = session.read_target(graph.book_id)
    if (before != after or session.action_log or receipt.payload.results or
            receipt.payload.execution_mode != 'NOT_EXECUTED' or receipt.payload.write_disposition != 'NOT_EXECUTED'):
        raise RuntimeError('unexpected effect in HOLD diagnostic')
    write_bundle(bundle, output / 'executed.json')
    load_bundle(output / 'executed.json', verify_assets=True)
    from dataclasses import asdict
    write(output / 'simulation-config.json', asdict(config))
    write(output / 'target-before.json', before)
    write(output / 'target-after.json', after)
    write(output / 'action-log.json', list(session.action_log))
    summary = {'format': 'b-q1-a-hold-probe/0.1', 'a_commit': A_COMMIT,
        'a_source_members_verified': len(pinned['files']), 'a_source_pin_sha256': PIN_SHA,
        'input_mapping_sha256': sha(mapping.read_bytes()),
        'input_mapping_manifest_sha256': MAPPING_MANIFEST_SHA, 'question_id': QID,
        'input_refs': refs, 'policy_ref': pref, 'pre_ref': artifact_ref(pre),
        'target_ref': artifact_ref(target), 'plan_ref': artifact_ref(plan),
        'receipt_ref': artifact_ref(receipt), 'decision': 'HOLD', 'business_acceptance': False,
        'a_mapping_accepted': False, 'a_formal_pre_apply': False, 'positive_simulation_complete': False,
        'pre_decision': 'HOLD', 'target_decision': target.payload.decision,
        'plan_readiness': plan.payload.readiness, 'receipt_execution_mode': receipt.payload.execution_mode,
        'write_disposition': receipt.payload.write_disposition, 'action_count': 0, 'dispatch_count': 0,
        'target_unchanged': before == after, 'platform_requests': 0, 'model_calls': 0,
        'target_issues': [i.model_dump(mode='json') for i in target.payload.issues],
        'environment': {'python': sys.version.split()[0], 'pydantic': importlib.metadata.version('pydantic'),
                        'Pillow': importlib.metadata.version('Pillow'), 'clean_install': False}}
    write(output / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--a-root', type=Path, required=True)
    parser.add_argument('--mapping', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--created-at', help='Timezone-aware time; omit for current UTC. Reuse only for deterministic replay.')
    parser.add_argument('--pins', type=Path, default=Path(__file__).resolve().parents[1] /
                        'tests/fixtures/book46007447/q1-a-stage2-source-pins.json')
    args = parser.parse_args()
    result = run(args.a_root, args.mapping, args.output, args.pins, args.created_at)
    print(json.dumps({k: result[k] for k in ('decision', 'target_decision', 'plan_readiness',
        'write_disposition', 'action_count', 'dispatch_count', 'target_unchanged')}, ensure_ascii=False))
