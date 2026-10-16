"""S01 proof using the exact committed SourceBundle, preserving its identity."""
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

target=STAGE / "primary S01 exact fixed delivery"
shutil.copytree(SNAPSHOT / "examples/a01/bundles/46007447",target)
case=FORMAL / "source-independent/cases/S23-S01-public-preapply-gate-gap/changed-inputs"
shutil.copy2(case/"synthetic-proof.txt",target/"synthetic-proof.txt")
baseline=json.loads((SNAPSHOT / "examples/a01/bundles/46007447/exchange.json").read_text(encoding="utf-8"))
expanded=json.loads((case/"exchange.json").read_text(encoding="utf-8"))
exact_source=baseline["artifacts"][0]
old_source=expanded["artifacts"][0]
replacements={old_source["content_hash"]:contracts.artifact_ref(exact_source)}

def replace_refs(value):
    if isinstance(value,list):
        return [replace_refs(v) for v in value]
    if isinstance(value,dict):
        if set(value) == {"artifact_id","revision","content_hash","kind"} and value["content_hash"] in replacements:
            return replacements[value["content_hash"]]
        return {k:replace_refs(v) for k,v in value.items()}
    return value

artifacts=[exact_source]
for artifact in expanded["artifacts"][1:]:
    sealed=contracts.seal_artifact(replace_refs(artifact))
    replacements[artifact["content_hash"]]=contracts.artifact_ref(sealed)
    artifacts.append(sealed)
expanded["artifacts"]=artifacts
(target/"exchange.json").write_text(json.dumps(expanded,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
loaded=contracts.load_bundle(target/"exchange.json",verify_assets=True)
original=contracts.load_bundle(SNAPSHOT / "examples/a01/bundles/46007447/exchange.json")
source=next(a for a in loaded.artifacts if a.kind == "SourceBundle")
check=next(a for a in loaded.artifacts if a.kind == "CheckReport")
limits=json.loads((target/"limitations.json").read_text(encoding="utf-8"))
assert source == original.artifacts[0]
result={"target_commit":"a8d5e96d128e10d341de935d4856682e50df79d9","contract_module":contracts.__file__,
        "source_artifact_unchanged":True,"source_content_hash":source.content_hash,
        "coverage_eligible":limits["coverage_eligible"],"independent_denominator_status":limits["independent_denominator_status"],
        "public_load":"ACCEPT","check_stage":check.payload.stage,"check_decision":check.payload.decision,
        "mode":"SYNTHETIC_OFFLINE_ONLY","platform_actions":0,
        "prior_probe_correction":"S23 used an unchanged reimported baseline, not the exact committed sample. This probe uses the exact committed artifact.",
        "interpretation":"Known S01 public-contract integration gap; no real quality or platform acceptance"}
(FORMAL/"primary-confirmation/S01-fixed-delivery-gate.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
shutil.copytree(target,FORMAL/"primary-confirmation/S01-fixed-delivery-input")
print(json.dumps(result,ensure_ascii=False))
