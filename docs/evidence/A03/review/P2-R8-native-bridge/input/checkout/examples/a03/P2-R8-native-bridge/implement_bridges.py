"""Apply the nineteen explicit R4 keyword-only bridges without changing defaults."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def edit(path, names, transform):
    file = ROOT / path
    text = file.read_text(encoding='utf-8')
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    spans = [(node.lineno - 1, node.end_lineno, node) for node in ast.walk(tree)
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    for start, end, node in sorted(spans, reverse=True):
        original = ''.join(lines[start:end])
        close = original.index('):')
        prefix = original[:close]
        prefix += ', bridge_context=None' if node.args.kwonlyargs else ', *, bridge_context=None'
        value = prefix + original[close:]
        lines[start:end] = [transform(node.name, value)]
    file.write_bytes(''.join(lines).encode('utf-8'))


def dispatch(name, value):
    if name == 'validate_bundle':
        value = value.replace('    version =', '    version =', 1)
        needle = '    if version == RECOVERY_EXCHANGE_VERSION:'
        if needle in value:
            value = value.replace(needle, "    if version == 'a03-exchange-4-proposal':\n        from .a03_native import validate_native_bundle\n        return validate_native_bundle(bundle, bridge_context=bridge_context, asset_root=asset_root)\n" + needle)
        else:
            pos = value.index('    try:')
            value = value[:pos] + "    version = bundle.get('format_version') if isinstance(bundle, dict) else getattr(bundle, 'format_version', None)\n    if version == 'a03-exchange-4-proposal':\n        from .a03_native import validate_native_bundle\n        return validate_native_bundle(bundle, bridge_context=bridge_context, asset_root=asset_root)\n" + value[pos:]
    if name == 'seal_artifact':
        value = value.replace('    if version == RECOVERY_SCHEMA_VERSION:', "    if version == '1.4.0-a03-native-proposal':\n        from .a03_native import seal_native_artifact\n        return seal_native_artifact(data, bridge_context=bridge_context)\n    if version == RECOVERY_SCHEMA_VERSION:")
    if name in ('assert_plan_ready', 'assert_recovery_plan_ready'):
        pos = value.index('\n') + 1
        value = value[:pos] + "    version = bundle.get('format_version') if isinstance(bundle, dict) else getattr(bundle, 'format_version', None)\n    if version == 'a03-exchange-4-proposal':\n        from .a03_native import assert_native_plan_ready\n        return assert_native_plan_ready(bundle, plan_ref, current_snapshot_ref, bridge_context=bridge_context)\n" + value[pos:]
    if name == 'validate_recovery_bundle':
        pos = value.index('\n') + 1
        value = value[:pos] + "    version = bundle.get('format_version') if isinstance(bundle, dict) else getattr(bundle, 'format_version', None)\n    if version == 'a03-exchange-4-proposal':\n        from .a03_native import validate_native_bundle\n        return validate_native_bundle(bundle, bridge_context=bridge_context, asset_root=asset_root)\n" + value[pos:]
    return value


def target(name, value):
    value = value.replace('validate_bundle(bundle)', 'validate_bundle(bundle, bridge_context=bridge_context)')
    value = value.replace('validate_bundle(data, asset_root=asset_root)', 'validate_bundle(data, asset_root=asset_root, bridge_context=bridge_context)')
    value = value.replace('current_snapshot_ref, policy_reference, config)', 'current_snapshot_ref, policy_reference, config, bridge_context=bridge_context)')
    if name == 'make_artifact':
        value = value.replace('if anchor.schema_version == "1.1.0-a-recovery-proposal"', 'if anchor.schema_version in ("1.1.0-a-recovery-proposal", "1.4.0-a03-native-proposal")')
        value = value.replace('    refs = list({', "    if anchor.schema_version == '1.4.0-a03-native-proposal':\n        exact = {}\n        for ref in refs:\n            key = (ref['artifact_id'], ref['revision'])\n            if key in exact and exact[key] != ref:\n                reject('NATIVE_DEPENDENCY_CONFLICT', 'same identity with different exact reference')\n            exact[key] = ref\n    refs = list({")
        value = value.replace('    })', '    }, bridge_context=bridge_context)')
    if name == 'append_artifacts':
        value = value.replace('    return validate_bundle', "    if data.get('format_version') == 'a03-exchange-4-proposal':\n        from annotation.contracts.a03_native import derive_context\n        bridge_context = derive_context(bridge_context, data, asset_root=asset_root)\n    return validate_bundle")
    if name == 'analyze_target':
        value = value.replace('if graph.schema_version == "1.1.0-a-recovery-proposal":', 'if graph.schema_version in ("1.1.0-a-recovery-proposal", "1.4.0-a03-native-proposal"):')
        value = value.replace('scope_id=graph.scope_id).paused', 'scope_id=graph.scope_id, bridge_context=bridge_context).paused')
    if name == 'check_target':
        value = value.replace('created_at, run_id)', 'created_at, run_id, bridge_context=bridge_context)')
        value = value.replace('append_artifacts(bundle, report)', 'append_artifacts(bundle, report, bridge_context=bridge_context)')
    return value


def planner(name, value):
    value = value.replace('validate_bundle(bundle)', 'validate_bundle(bundle, bridge_context=bridge_context)')
    value = value.replace('!= "1.1.0-a-recovery-proposal"', 'not in ("1.1.0-a-recovery-proposal", "1.4.0-a03-native-proposal")')
    value = value.replace('verify_generated_plan(bundle, plan, plan.payload.snapshot, config)', 'verify_generated_plan(bundle, plan, plan.payload.snapshot, config, bridge_context=bridge_context)')
    if name == 'create_plan':
        value = value.replace('current_snapshot_ref, policy_reference, config)', 'current_snapshot_ref, policy_reference, config, bridge_context=bridge_context)')
        value = value.replace('    plan = make_artifact', "    if graph.schema_version == '1.4.0-a03-native-proposal':\n        from annotation.contracts.a03_native import require_context\n        require_context(bridge_context, bundle)('creation_anchor', bridge_context, bundle=bundle, config=config,\n            artifact_id=artifact_id, created_at=created_at, run_id=run_id or graph.run_id)\n    plan = make_artifact")
        value = value.replace('created_at, run_id)', 'created_at, run_id, bridge_context=bridge_context)')
        value = value.replace('append_artifacts(bundle, plan)', 'append_artifacts(bundle, plan, bridge_context=bridge_context)')
        value = value.replace('assert_plan_ready(output, artifact_ref(plan), artifact_ref(current))', 'assert_plan_ready(output, artifact_ref(plan), artifact_ref(current), bridge_context=getattr(output, "bridge_context", bridge_context))')
    if name == 'verify_generated_plan':
        value = value.replace('    payload = plan.payload', "    if plan.schema_version == '1.4.0-a03-native-proposal':\n        from annotation.contracts.a03_native import require_context\n        return require_context(bridge_context, bundle)('verify_creation_anchor', bridge_context, bundle=bundle,\n            plan=plan, current_ref=current_ref, config=config, observation_binding=observation_binding)\n    payload = plan.payload")
    if name == 'snapshot_state_equivalent':
        value = value.replace('    for name in (', "    if planned['schema_version'] == '1.4.0-a03-native-proposal':\n        from annotation.contracts.a03_native import require_context\n        require_context(bridge_context)\n    for name in (", 1)
    return value


def persistent(name, value):
    value = value.replace('validate_bundle(bundle, asset_root=asset_root)', 'validate_bundle(bundle, asset_root=asset_root, bridge_context=bridge_context)')
    value = value.replace('assert_plan_ready(bundle, plan_ref, current_snapshot_ref)', 'assert_plan_ready(bundle, plan_ref, current_snapshot_ref, bridge_context=bridge_context)')
    value = value.replace('self._verify_observation(observation)', 'self._verify_observation(observation, bridge_context=bridge_context)')
    value = value.replace('self.snapshot_from_observation(observation)', 'self.snapshot_from_observation(observation, bridge_context=bridge_context)')
    value = value.replace('return seal_artifact(snapshot)', 'return seal_artifact(snapshot, bridge_context=bridge_context)')
    value = value.replace('asset_root=prepared["asset_root"])', 'asset_root=prepared["asset_root"], bridge_context=bridge_context)')
    value = value.replace('progress_refs=prefix)', 'progress_refs=prefix, bridge_context=bridge_context)')
    value = value.replace('progress_refs=prepared["observation_binding"]["applied_prefix"])', 'progress_refs=prepared["observation_binding"]["applied_prefix"], bridge_context=bridge_context)')
    if name in ('create', 'open'):
        # Native format selection is a separate runtime-owned implementation.
        marker = '        bundle = validate_bundle' if name == 'create' else '        directory = Path(target_dir).resolve()'
        argument = 'bundle, snapshot_ref, platform_namespace=platform_namespace, source_ref=source_ref, asset_root=asset_root, expected_store_id=expected_store_id, target_session_id=target_session_id' if name == 'create' else 'expected_store_id=expected_store_id, expected_target_session_id=expected_target_session_id, expected_target_key=expected_target_key, expected_scope_id=expected_scope_id, expected_source_ref=expected_source_ref'
        value = value.replace(marker, "        if bridge_context is not None and cls is PersistentMockSession:\n            from annotation.runtime.storage.native_target import NativeTargetSession\n            return NativeTargetSession." + name + '(target_dir, ' + argument + ', bridge_context=bridge_context)\n' + marker, 1)
    if name == 'prepare_action':
        value = value.replace('        binding = bind_plan_observation', "        if plan.schema_version == '1.4.0-a03-native-proposal':\n            from annotation.quality.targetcheck import append_artifacts\n            bundle = append_artifacts(bundle, snapshot, asset_root=asset_root, bridge_context=bridge_context)\n            bridge_context = bundle.bridge_context\n        binding = bind_plan_observation", 1)
    return value


if __name__ == '__main__':
    edit('src/annotation/contracts/__init__.py', {'validate_bundle', 'seal_artifact', 'assert_plan_ready'}, dispatch)
    edit('src/annotation/contracts/validation.py', {'validate_bundle'}, dispatch)
    edit('src/annotation/contracts/recovery.py', {'validate_recovery_bundle', 'assert_recovery_plan_ready'}, dispatch)
    edit('src/annotation/quality/targetcheck/__init__.py', {'make_artifact', 'append_artifacts', 'analyze_target', 'check_target'}, target)
    edit('src/annotation/delivery/planner/__init__.py', {'create_plan', 'verify_generated_plan', 'bind_plan_observation', 'snapshot_state_equivalent'}, planner)
    edit('src/annotation/delivery/mock/persistent.py', {'create', 'open', '_verify_observation', 'snapshot_from_observation', 'prepare_action', 'verify_prepared_action'}, persistent)
