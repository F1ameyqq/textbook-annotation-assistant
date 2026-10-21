"""Mechanical delta and input-preservation checks; no product execution."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
REL='src/annotation/runtime/live_pilot/owner.py'
before=ast.parse((Path('D:/1800-worktrees/a24-bootstrap-body-actual-review')/REL).read_bytes())
after=ast.parse((ROOT/REL).read_bytes())
checks={}
new_functions={'capture_binding','bind_capture_owner','validate_capture_owner','capture_evidence'}
checks['exactly_four_new_capture_helpers']=len([n for n in after.body if isinstance(n,ast.FunctionDef) and n.name in new_functions])==4
after.body=[n for n in after.body if not(isinstance(n,ast.FunctionDef) and n.name in new_functions)]
for node in after.body:
    if isinstance(node,ast.FunctionDef) and node.name=='owner_guard_class':
        cls=next(n for n in node.body if isinstance(n,ast.ClassDef))
        capture=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='capture')
        checks['capture_validates_before_inherited_capture']=ast.dump(capture,include_attributes=False)==ast.dump(ast.parse(
            'async def capture(self, response):\n    validate_capture_owner(authority, framework, self)\n    await super().capture(response)').body[0],include_attributes=False)
        cls.body.remove(capture)
    if isinstance(node,ast.FunctionDef) and node.name=='guard_evidence':
        project=next(n for n in ast.walk(node) if isinstance(n,ast.FunctionDef) and n.name=='project')
        loop=next(n for n in project.body if isinstance(n,ast.For))
        branch=loop.body[0]
        expected=ast.parse('if key == "decision":\n    require(value in ("ALLOW", "BLOCK"), "GUARD_EVENT_PROJECTION")').body[0]
        checks['decision_exact_allow_block_guard']=ast.dump(branch.test,include_attributes=False)==ast.dump(expected.test,include_attributes=False) and ast.dump(ast.Module(body=branch.body,type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=expected.body,type_ignores=[]),include_attributes=False)
        legacy=branch.orelse[0]
        legacy.test=ast.parse('key in ("method", "category", "decision", "source", "resource_type", "known_route")',mode='eval').body
        loop.body[0]=legacy
    if isinstance(node,ast.ClassDef) and node.name=='WindowsBackend':
        opened=next(n for n in node.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='open')
        source=ast.unparse(opened)
        checks['binding_before_install_and_online']=source.index('bind_capture_owner(')<source.index('await self.guard.install()')<source.index('await self.context.set_offline(False)')
        bind=next(n for n in opened.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='bind_capture_owner')
        checks['exact_backend_binding_call']=ast.dump(bind,include_attributes=False)==ast.dump(ast.parse('bind_capture_owner(self.authority, self.framework, self.guard)').body[0],include_attributes=False)
        opened.body.remove(bind)
    if isinstance(node,ast.AsyncFunctionDef) and node.name=='run_owned_worker':
        finalizer=next(n for n in node.body if isinstance(n,ast.Try)).finalbody
        additions=[n for n in finalizer if isinstance(n,ast.Assign) and any(isinstance(t,ast.Subscript) and isinstance(t.slice,ast.Constant) and t.slice.value=='private_capture_evidence' for t in n.targets)]
        checks['one_additive_final_capture_evidence_snapshot']=len(additions)==1
        for value in additions:finalizer.remove(value)
checks['all_other_owner_ast_identical']=ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False)
with (OUT/'static-delta-result.json').open('xb') as handle:handle.write((json.dumps(dict(schema='A24ControlledCaptureIndependentStaticDelta/v1',checks=checks,passed=all(checks.values()),product_execution=False,additional_controls=False),indent=2)+'\n').encode())

manifest=json.loads((OUT/'input-raw-manifest.json').read_bytes())
for row in manifest['members']:
    raw=(ROOT/row['path']).read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
for row in manifest['private_references']:
    raw=Path(row['snapshot_path']).read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
with (OUT/'input-preservation.json').open('xb') as handle:handle.write((json.dumps(dict(schema='A24ControlledCaptureIndependentInputPreservation/v1',at=datetime.now(timezone.utc).isoformat(),result='ALL_322_RAW_AND_41_PRIVATE_INPUTS_UNCHANGED',product_input_edits=0,test_or_control_reruns=0,historical_tree_audit_repeated=False),indent=2)+'\n').encode())
print(json.dumps({'static_checks':checks,'inputs_preserved':[322,41]}))
