"""Reproduce C01 independent review through public APIs on a frozen source tree."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

from review_mutations import artifact, payload, first_box, cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.tree.resolve() / 'src'))
    from annotation.contracts import (
        ContractError, ExchangeBundle, OriginalBox, artifact_ref, content_digest,
        assert_plan_ready, assert_patch_base, load_bundle, schema, validate_bundle,
        write_bundle,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    fixture_root = args.tree / 'tests' / 'fixtures' / 'contracts'
    inputs = {name: json.loads((fixture_root / name / 'input.json').read_text(encoding='utf-8'))
              for name in ('normal', 'exception', 'unknown', 'choice-assumption')}
    observations = []

    def observe(name, ok, **details):
        observations.append(dict(case=name, passed=bool(ok), **details))

    def reseal(data):
        """Update hashes without silently repairing deliberately broken references."""
        history = {}
        for a in data['artifacts']:
            key = (a['artifact_id'], a['revision'], a['kind'])
            history.setdefault(key, set()).add(a['content_hash'])
        for iteration in range(len(data['artifacts']) + 3):
            current = {}
            for a in data['artifacts']:
                key = (a['artifact_id'], a['revision'], a['kind'])
                a['content_hash'] = content_digest(a)
                current.setdefault(key, a['content_hash'])

            def rebind(value):
                if isinstance(value, dict):
                    if set(value) == {'artifact_id', 'revision', 'kind', 'content_hash'}:
                        key = (value['artifact_id'], value['revision'], value['kind'])
                        if key in history and value['content_hash'] in history[key]:
                            value['content_hash'] = current[key]
                    else:
                        for child in value.values():
                            rebind(child)
                elif isinstance(value, list):
                    for child in value:
                        rebind(child)
            rebind(data)
            for key, digest in current.items():
                history[key].add(digest)
            if all(a['content_hash'] == content_digest(a) for a in data['artifacts']):
                return data
        raise AssertionError('digest dependency propagation did not converge')

    for name, data in inputs.items():
        try:
            bundle = load_bundle(fixture_root / name / 'input.json')
            kinds = sorted({a.kind for a in bundle.artifacts})
            observe('fixture_' + name, len(kinds) == 9, artifacts=len(bundle.artifacts), kinds=kinds)
        except Exception as error:
            observe('fixture_' + name, False, error=str(error))

    for case_id, fixture, mutate, expected_layer in cases():
        data = copy.deepcopy(inputs[fixture])
        try:
            mutate(data)
            if case_id not in ('bbox_nan', 'bbox_infinity'):
                reseal(data)
            input_path = args.output / 'inputs' / (case_id + '.json')
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=True) + '\n', encoding='utf-8')
            try:
                validate_bundle(data)
            except ContractError as error:
                stale_hash = any(i['code'] == 'HASH_MISMATCH' for i in error.issues)
                observe(case_id, not stale_hash, expected='REJECT', result='REJECTED',
                        expected_layer=expected_layer, issues=error.issues, input=str(input_path))
            else:
                observe(case_id, False, expected='REJECT', result='ACCEPTED_INVALID', input=str(input_path))
        except Exception as error:
            observe(case_id, False, result='RUNNER_ERROR', error=repr(error))

    # Public hash rule: root content_hash excluded; every other field is included.
    graph = artifact(inputs['normal'], 'QuestionGraph')
    independently_hashed = dict(graph)
    independently_hashed.pop('content_hash')
    encoded = json.dumps(independently_hashed, sort_keys=True, ensure_ascii=False,
                         separators=(',', ':'), allow_nan=False).encode('utf-8')
    expected_hash = hashlib.sha256(encoded).hexdigest()
    observe('independent_canonical_hash', content_digest(graph) == expected_hash == graph['content_hash'], digest=expected_hash)
    reversed_keys = dict(reversed(list(graph.items())))
    observe('hash_key_order_invariant', content_digest(graph) == content_digest(reversed_keys))
    changed_self_hash = dict(graph, content_hash='0' * 64)
    observe('hash_not_self_referential', content_digest(graph) == content_digest(changed_self_hash))
    tampered = copy.deepcopy(inputs['normal'])
    artifact(tampered, 'QuestionGraph')['payload']['identity_notes'] += ' changed without resealing'
    try:
        validate_bundle(tampered)
        observe('unsealed_tamper_rejected', False)
    except ContractError as error:
        observe('unsealed_tamper_rejected', any(i['code'] == 'HASH_MISMATCH' for i in error.issues), issues=error.issues)

    box = copy.deepcopy(first_box(inputs['normal']))
    box['bbox'] = [0.0, 0.0, float(box['image']['width']), float(box['image']['height'])]
    try:
        OriginalBox.model_validate(box)
        observe('half_open_full_image_boundary_valid', True)
    except Exception as error:
        observe('half_open_full_image_boundary_valid', False, error=str(error))

    for name in ('normal', 'exception', 'unknown', 'choice-assumption'):
        data = inputs[name]
        plan = artifact(data, 'ApplyPlan')
        snapshot = artifact(data, 'PlatformSnapshot')
        expected = name in ('normal', 'choice-assumption')
        try:
            assert_plan_ready(data, artifact_ref(plan), artifact_ref(snapshot))
            observe('eligibility_' + name, expected, eligible=True)
        except ContractError as error:
            observe('eligibility_' + name, not expected, eligible=False, issues=error.issues)

    data = copy.deepcopy(inputs['unknown'])
    fresh_plan = copy.deepcopy(artifact(data, 'ApplyPlan'))
    fresh_plan['artifact_id'] += '-fresh-id'
    fresh_plan['content_hash'] = content_digest(fresh_plan)
    data['artifacts'].append(fresh_plan)
    try:
        assert_plan_ready(data, artifact_ref(fresh_plan), artifact_ref(artifact(data, 'PlatformSnapshot')))
        observe('unknown_cannot_bypass_with_fresh_plan_id', False)
    except ContractError as error:
        observe('unknown_cannot_bypass_with_fresh_plan_id', any(i['code'] == 'BOOK_WRITE_PAUSED' for i in error.issues), issues=error.issues)

    data = copy.deepcopy(inputs['normal'])
    old_snapshot = artifact(data, 'PlatformSnapshot')
    fresh_snapshot = copy.deepcopy(old_snapshot)
    fresh_snapshot['revision'] += 1
    fresh_snapshot['payload']['observed_version'] += '-changed'
    fresh_snapshot['payload']['observed_hash'] = 'a' * 64
    fresh_snapshot['content_hash'] = content_digest(fresh_snapshot)
    data['artifacts'].append(fresh_snapshot)
    try:
        assert_plan_ready(data, artifact_ref(artifact(data, 'ApplyPlan')), artifact_ref(fresh_snapshot))
        observe('fresh_target_rejects_old_plan', False)
    except ContractError as error:
        observe('fresh_target_rejects_old_plan', any(i['code'] == 'TARGET_CHANGED' for i in error.issues), issues=error.issues)

    data = inputs['normal']
    patch = artifact(data, 'ReviewPatch')
    graph = artifact(data, 'QuestionGraph')
    try:
        assert_patch_base(data, artifact_ref(patch), artifact_ref(graph))
        observe('patch_exact_baseline_valid', True)
    except Exception as error:
        observe('patch_exact_baseline_valid', False, error=str(error))

    data = copy.deepcopy(inputs['normal'])
    new_graph = max((a for a in data['artifacts'] if a['kind'] == 'QuestionGraph'),
                    key=lambda a: a['revision'])
    try:
        assert_patch_base(data, artifact_ref(artifact(data, 'ReviewPatch')), artifact_ref(new_graph))
        observe('patch_new_baseline_rejected', False)
    except ContractError as error:
        observe('patch_new_baseline_rejected', any(i['code'] == 'PATCH_BASELINE' for i in error.issues), issues=error.issues)

    # Same-session handoff legitimately does not need restart recovery.
    data = copy.deepcopy(inputs['normal'])
    p = payload(data, 'ApplyPlan')
    p['session_mode'] = 'SAME_SESSION_HANDOFF'
    p['required_capabilities'] = ['frame_readback', 'same_session_handoff']
    caps = payload(data, 'PlatformSnapshot')['capabilities']
    if not any(c['name'] == 'same_session_handoff' for c in caps):
        prototype = copy.deepcopy(next(c for c in caps if c['status'] == 'VERIFIED'))
        prototype['name'] = 'same_session_handoff'
        caps.append(prototype)
    for cap in caps:
        if cap['name'] in ('resume_after_restart', 'persistent_draft'):
            cap['status'] = 'UNKNOWN'
            cap['evidence_refs'] = []
    try:
        reseal(data)
        assert_plan_ready(data, artifact_ref(artifact(data, 'ApplyPlan')), artifact_ref(artifact(data, 'PlatformSnapshot')))
        observe('same_session_without_restart_recovery_valid', True)
    except Exception as error:
        observe('same_session_without_restart_recovery_valid', False, error=str(error))

    # Transport includes all bytes. Validation must resolve paths from bundle parent.
    transport_root = args.output / 'transport'
    for name in inputs:
        destination = transport_root / (name + ' copied elsewhere')
        shutil.copytree(fixture_root / name, destination, dirs_exist_ok=True)
        try:
            load_bundle(destination / 'input.json')
            observe('transport_' + name, True, destination=str(destination))
        except Exception as error:
            observe('transport_' + name, False, error=str(error))

    duplicate_json = args.output / 'duplicate-keys.json'
    duplicate_json.write_text('{"format_version":"c01-exchange-1","format_version":"c01-exchange-1"}', encoding='utf-8')
    try:
        load_bundle(duplicate_json)
        observe('duplicate_json_keys_rejected', False)
    except ContractError as error:
        observe('duplicate_json_keys_rejected', any(i['code'] == 'JSON_INPUT' for i in error.issues), issues=error.issues)

    resource_copy = args.output / 'resource-corruption'
    shutil.copytree(fixture_root / 'normal', resource_copy, dirs_exist_ok=True)
    resource = payload(inputs['normal'], 'SourceBundle')['assets'][0]['path']
    with (resource_copy / resource).open('ab') as handle:
        handle.write(b'independent-byte-tamper')
    try:
        load_bundle(resource_copy / 'input.json')
        observe('resource_bytes_tamper_rejected', False)
    except ContractError as error:
        observe('resource_bytes_tamper_rejected', True, issues=error.issues)

    export = args.output / 'public-api-export.json'
    bundle = validate_bundle(inputs['normal'])
    try:
        write_bundle(bundle, export)
        validate_bundle(json.loads(export.read_text(encoding='utf-8')))
        try:
            write_bundle(bundle, export)
            observe('public_api_write_preserves_existing_file', False)
        except FileExistsError:
            observe('public_api_write_preserves_existing_file', True)
    except Exception as error:
        observe('public_api_write_preserves_existing_file', False, error=str(error))

    generated_schema = schema()
    observe('schema_generated_from_types', generated_schema == ExchangeBundle.model_json_schema())
    (args.output / 'generated-schema.json').write_text(json.dumps(generated_schema, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    result = dict(python=sys.version, source_tree=str(args.tree.resolve()),
                  total=len(observations), passed=sum(x['passed'] for x in observations),
                  failed=sum(not x['passed'] for x in observations), cases=observations)
    (args.output / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, ensure_ascii=False))
    for observation in observations:
        if not observation['passed']:
            print(json.dumps(observation, ensure_ascii=False))
    return 1 if result['failed'] else 0


if __name__ == '__main__':
    sys.exit(main())
