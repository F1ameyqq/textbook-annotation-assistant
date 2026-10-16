"""Read a self-contained C01 counterexample using only public contracts APIs."""
import argparse
import json
from pathlib import Path
import sys

p = argparse.ArgumentParser()
p.add_argument('--tree', type=Path, required=True)
p.add_argument('--input', type=Path, required=True)
a = p.parse_args()
sys.dont_write_bytecode = True
sys.path.insert(0, str(a.tree.resolve() / 'src'))
from annotation.contracts import load_bundle, artifact_ref, assert_plan_ready, ContractError

try:
    bundle = load_bundle(a.input)
    plan = next(x for x in bundle.artifacts if x.kind == 'ApplyPlan')
    snapshot = next(x for x in bundle.artifacts if x.kind == 'PlatformSnapshot')
    assert_plan_ready(bundle, artifact_ref(plan), artifact_ref(snapshot))
    print(json.dumps(dict(bundle_valid=True, resources_verified=True, eligible=True,
                         plan_id=plan.artifact_id), sort_keys=True))
except ContractError as error:
    print(json.dumps(dict(bundle_valid=False, eligible=False, issues=error.issues), ensure_ascii=False))
    sys.exit(1)
