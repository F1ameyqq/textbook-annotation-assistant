"""Finish explicit runtime propagation; product code never imports this file."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def edit(name, transform):
    path = ROOT / name
    path.write_bytes(transform(path.read_text(encoding='utf-8')).encode('utf-8'))


def runtime(value):
    value = value.replace('expected_scope_id=reg["scope"], expected_source_ref=json.loads(reg["source"]))', 'expected_scope_id=reg["scope"], expected_source_ref=json.loads(reg["source"]),\n        bridge_context=store.bridge_for(store.bundle(reg["id"]), reg["package_root"]))')
    value = value.replace('validate_recovery_bundle(store.bundle(reg["id"]), asset_root=reg["package_root"])', 'store._validate(store.bundle(reg["id"]), asset_root=reg["package_root"])')
    value = value.replace('current_snapshot_ref=plan["payload"]["snapshot"], asset_root=reg["package_root"])', 'current_snapshot_ref=plan["payload"]["snapshot"], asset_root=reg["package_root"],\n                bridge_context=getattr(bundle, "bridge_context", None))')
    value = value.replace('observed_snapshot_ref=reference(snapshot) if snapshot else None)', 'observed_snapshot_ref=reference(snapshot) if snapshot else None, bridge_context=getattr(bundle, "bridge_context", None))')
    value = value.replace('    from .quality import build_quality_report', "    if getattr(store, '_user_version', 1) == 4:\n        from .native_quality import publish_native_quality\n        return publish_native_quality(store, registration_id, projection)\n    from .quality import build_quality_report")
    return value


def holds(value):
    value = value.replace('bundle = validate_recovery_bundle(self.bundle(reg[\'id\']), asset_root=reg[\'package_root\'])', 'bundle = self._validate(self.bundle(reg[\'id\']), asset_root=reg[\'package_root\'])')
    value = value.replace('selected = assert_recovery_plan_ready(bundle, candidate_plan_ref, snapshot_ref)', 'selected = assert_recovery_plan_ready(bundle, candidate_plan_ref, snapshot_ref, bridge_context=getattr(bundle, "bridge_context", None))')
    value = value.replace('verify_generated_plan(bundle, selected, snapshot_ref, configuration(json.loads(reg[\'config\'])))', 'verify_generated_plan(bundle, selected, snapshot_ref, configuration(json.loads(reg[\'config\'])), bridge_context=getattr(bundle, "bridge_context", None))')
    return value


def reconciler(value):
    value = value.replace('observed_snapshot_ref=None):', 'observed_snapshot_ref=None, bridge_context=None):')
    value = value.replace('bundle = validate_bundle(bundle)', 'bundle = validate_bundle(bundle, bridge_context=bridge_context)')
    value = value.replace('"created_at": observation["observed_at"], "payload": payload})', '"created_at": observation["observed_at"], "payload": payload}, bridge_context=bridge_context)')
    return value


if __name__ == '__main__':
    edit('src/annotation/runtime/recovery/__init__.py', runtime)
    edit('src/annotation/runtime/storage/holds.py', holds)
    edit('src/annotation/delivery/reconciler/__init__.py', reconciler)
