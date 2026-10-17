"""Actual five checks for the adopted, fixed 32x32 synthetic language only.

No SQL, durable registry ownership, dispatch permit, OCR or model calls.
"""
import hashlib
from importlib import resources
import json
from pathlib import Path

from annotation.contracts import artifact_ref, policy_ref, validate_bundle
from annotation.contracts.a03_native import require_context, derive_context
from annotation.quality.targetcheck import (append_artifacts, coverage_for, make_artifact,
    resolve_artifact, resolve_policy, reject)

CHECKS = ('source_integrity', 'structure', 'answer_matching', 'coverage', 'policy')


def _raw_oracle():
    return resources.files('annotation.contracts.a03_native').joinpath('data/oracle.json').read_bytes()


def _write(root, raw, suffix):
    digest = hashlib.sha256(raw).hexdigest()
    path = Path(root) / 'assets/native-pre' / (digest + suffix)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            reject('RESOURCE_HASH_MISMATCH', 'immutable PRE resource differs')
    else:
        with path.open('xb') as stream:
            stream.write(raw)
    return {'path': path.relative_to(root).as_posix(), 'sha256': digest,
            'media_type': 'application/json', 'origin': 'SYNTHETIC'}


def compare_synthetic_inputs(bundle, source_ref, evidence_ref, graph_ref, policy_reference, *, asset_root):
    """Compute five comparisons, using exact unique inputs and every PGM pixel."""
    root = Path(asset_root).resolve(strict=True)
    source = resolve_artifact(bundle, source_ref, 'SourceBundle')
    evidence = resolve_artifact(bundle, evidence_ref, 'EvidenceBundle')
    graph = resolve_artifact(bundle, graph_ref, 'QuestionGraph')
    policy = resolve_policy(bundle, policy_reference)
    for kind, selected in (('SourceBundle', source), ('EvidenceBundle', evidence), ('QuestionGraph', graph)):
        if sum(a.kind == kind for a in bundle.artifacts) != 1:
            reject('SYNTHETIC_INPUT_AMBIGUOUS', 'one explicit unique ' + kind + ' required')
    if len(bundle.policies) != 1 or graph.payload.source != artifact_ref(source) or graph.payload.evidence != artifact_ref(evidence):
        reject('SYNTHETIC_INPUT_BINDING', 'graph/policy exact inputs differ')
    oracle = json.loads(_raw_oracle())
    sp, ep, gp = source.payload, evidence.payload, graph.payload
    asset_ok = len(sp.assets) == 1
    for asset in sp.assets:
        path = (root / asset.path).resolve(strict=True)
        if root not in path.parents or path.is_symlink():
            reject('RESOURCE_PATH', 'PGM escaped explicit root')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != asset.sha256:
            reject('RESOURCE_HASH_MISMATCH', 'PGM raw bytes differ')
        try:
            # P2 permits comments; consume the complete raster, never just header.
            tokens = b' '.join(line.split(b'#', 1)[0] for line in raw.splitlines()).split()
            header = tokens[:4]
            pixels = [int(value) for value in tokens[4:]]
            expected = [0 if (4 <= x < 28 and (4 <= y < 10 or 18 <= y < 24)) else 255
                        for y in range(32) for x in range(32)]
            asset_ok = asset_ok and header == [b'P2', b'32', b'32', b'255'] and pixels == expected
        except ValueError:
            asset_ok = False
        asset_ok = asset_ok and asset.width == 32 and asset.height == 32
    source_ok = asset_ok and len(sp.pages_expected) == len(sp.pages_acquired) == 1 and sp.pages_expected == sp.pages_acquired == [sp.assets[0].asset_id]
    questions, regions, fragments = gp.questions, ep.regions, gp.fragments
    structure_ok = (len(questions) == 1 and len(regions) == 2 and [f.role for f in fragments] == ['stem', 'answer']
        and [r.box.bbox for r in regions] == [[4, 4, 28, 10], [4, 18, 28, 24]]
        and not questions[0].shared_fragment_ids and not questions[0].cross_page
        and questions[0].fragment_ids == [f.fragment_id for f in fragments]
        and len(fragments) == 2 and all(f.region_ids == [r.region_id] for f, r in zip(fragments, regions)))
    answers = [f.fragment_id for f in fragments if f.role == 'answer']
    relations = gp.answer_relations
    answer_ok = len(relations) == 1 and len(answers) == 1 and relations[0].status == 'SELECTED' and relations[0].question_id == questions[0].question_id and relations[0].candidate_fragment_ids == relations[0].selected_fragment_ids == answers
    coverage_ok = (sp.scope_manifest == [q.question_id for q in questions]
        and len(sp.pages_expected) == 1 and len(ep.coverage_clues) == 2
        and [c.disposition for c in ep.coverage_clues] == ['ASSIGNED', 'ASSIGNED']
        and {rid for c in ep.coverage_clues for rid in c.region_ids} == {r.region_id for r in regions})
    policy_ok = (policy.option_grouping == 'SEPARATE' and dict(policy.role_mapping) ==
        {'stem': 'Q', 'option': 'W', 'answer': 'A', 'explanation': 'E', 'shared_material': 'Q'}
        and all(q.question_type == 'free_response' for q in questions))
    return dict(zip(CHECKS, ['PASS' if value else 'FAIL' for value in
        (source_ok, structure_ok, answer_ok, coverage_ok, policy_ok)]))


def produce_a03_pre_run(bundle, source_ref, evidence_ref, graph_ref, policy_reference, *,
                        bridge_context, registered_run_handle, actual_snapshot_ref,
                        actual_observation, asset_root, artifact_id, created_at):
    """Produce immutable PRE/run bytes from new checks; runtime records/adopts them."""
    bundle = validate_bundle(bundle, asset_root=asset_root, bridge_context=bridge_context)
    callback = require_context(bridge_context, bundle)
    binding = callback('producer_binding', bridge_context, handle=registered_run_handle,
        snapshot_ref=actual_snapshot_ref, observation=actual_observation)
    graph = resolve_artifact(bundle, graph_ref, 'QuestionGraph')
    source = resolve_artifact(bundle, source_ref, 'SourceBundle')
    evidence = resolve_artifact(bundle, evidence_ref, 'EvidenceBundle')
    snapshot = resolve_artifact(bundle, actual_snapshot_ref, 'PlatformSnapshot')
    results = compare_synthetic_inputs(bundle, source_ref, evidence_ref, graph_ref, policy_reference, asset_root=asset_root)
    oracle_resource = _write(Path(asset_root), _raw_oracle(), '.json')
    run = {'format_version': 'a03-native-pre-run-1', 'run_id': binding['run_id'],
        'context': binding['context'], 'source_ref': source_ref, 'evidence_ref': evidence_ref,
        'graph_ref': graph_ref, 'policy_ref': policy_reference, 'snapshot_ref': actual_snapshot_ref,
        'oracle': oracle_resource, 'input_raw_sha256': bridge_context.canonical_sha256,
        'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'actual_observation': actual_observation['resource'], 'observed_at': actual_observation['observed_at'],
        'produced_at': created_at, 'checks': results, 'input_manifest': binding['input_manifest'],
        'native_binding': binding['native_binding'], 'runtime_status': 'ACTUAL_CHECKS_COMPUTED',
        'admission': 'RUNTIME_RECHECK_REQUIRED'}
    raw = (json.dumps(run, sort_keys=True, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    run_resource = _write(Path(asset_root), raw, '.json')
    evidence_id = 'native-pre-proof-' + run_resource['sha256'][:40]
    augmented = bundle.model_dump()
    augmented['evidence'].append({'evidence_id': evidence_id, 'resource': run_resource,
        'description': 'Actual fixed synthetic five-check run; no dispatch authority', 'mode': 'SYNTHETIC'})
    bridge_context = derive_context(bridge_context, augmented)
    bundle = validate_bundle(augmented, bridge_context=bridge_context, asset_root=asset_root)
    payload = {'stage': 'PRE_APPLY', 'subject': graph_ref, 'graph': graph_ref, 'policy': policy_reference,
        'snapshot': actual_snapshot_ref, 'receipt': None, 'coverage': coverage_for(bundle, graph),
        'checks': [{'check_id': key, 'outcome': value, 'evidence_refs': [evidence_id], 'reason': 'Actual fixed synthetic comparison: ' + value}
                   for key, value in results.items()], 'issues': [],
        'decision': 'PASS' if all(v == 'PASS' for v in results.values()) else 'HOLD',
        'reason': 'Actual five fixed synthetic comparisons; content remains unverified',
        'recovery_refs': [], 'synthetic_run_ref': run_resource, 'verification_context': binding['context']}
    pre = make_artifact('CheckReport', artifact_id, graph, payload, list(bundle.artifacts),
        'a03-native-pre-1', 'annotation.quality.synthetic_precheck', created_at,
        run_id=binding['run_id'], bridge_context=bridge_context)
    return append_artifacts(bundle, pre, asset_root=asset_root, bridge_context=bridge_context), artifact_ref(pre)


def admit_a03_pre_run(bundle, pre_ref, *, bridge_context, registered_run_handle, actual_snapshot_ref, asset_root):
    """Ask runtime to recheck the actual durable run/currentness; never a permit."""
    bundle = validate_bundle(bundle, asset_root=asset_root, bridge_context=bridge_context)
    return require_context(bridge_context, bundle)('admit_pre', bridge_context, bundle=bundle,
        pre_ref=pre_ref, handle=registered_run_handle, snapshot_ref=actual_snapshot_ref)
