"""Recheck S01 without modifying the original A01 source artifact."""
import json
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[5]
FORMAL=Path(__file__).resolve().parent
STAGE=ROOT / ".local/stages/A01-review/a8d5e96d128e10d341de935d4856682e50df79d9"
SNAPSHOT=STAGE / "snapshot-verified"
sys.path.insert(0,str(SNAPSHOT / "src"))
import annotation.contracts as contracts

target=STAGE / "primary S01 expanded source"
shutil.copytree(SNAPSHOT / "examples/a01/bundles/46007447",target)
case=FORMAL / "source-independent/cases/S23-S01-public-preapply-gate-gap/changed-inputs"
shutil.copy2(case/"exchange.json",target/"exchange.json")
shutil.copy2(case/"synthetic-proof.txt",target/"synthetic-proof.txt")
original=contracts.load_bundle(SNAPSHOT / "examples/a01/bundles/46007447/exchange.json")
expanded=contracts.load_bundle(target/"exchange.json",verify_assets=True)
source=next(a for a in expanded.artifacts if a.kind == "SourceBundle")
report=next(a for a in expanded.artifacts if a.kind == "CheckReport")
limits=json.loads((target/"limitations.json").read_text(encoding="utf-8"))
result={"target_commit":"a8d5e96d128e10d341de935d4856682e50df79d9",
        "contract_module":contracts.__file__,"source_artifact_unchanged":source == original.artifacts[0],
        "source_content_hash":source.content_hash,"coverage_eligible":limits["coverage_eligible"],
        "independent_denominator_status":limits["independent_denominator_status"],
        "public_load":"ACCEPT","check_stage":report.payload.stage,"check_decision":report.payload.decision,
        "mode":"SYNTHETIC_OFFLINE_ONLY","platform_actions":0,
        "interpretation":"Known S01 public-contract integration gap, not a real quality PASS and not an implemented gate"}
(FORMAL/"primary-confirmation/S01-public-gate.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
