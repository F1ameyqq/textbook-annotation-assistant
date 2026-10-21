"""Attach existing accepted content refs to a new immutable request draft."""
import hashlib
import json
from pathlib import Path

BASE = Path("D:/1800/.local/stages/a24-first-save-r1-inputs/author-content-v1")
CLOSURE = Path("D:/1800/docs/evidence/coordinator/a24-model-one-question-independent-closure")
OUT = Path(__file__).resolve().parents[2]/"docs/evidence/A24/first-save-wire-r1"

def reference(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

draft = json.loads((BASE/"request-draft.json").read_bytes())
draft["content_acceptance"] = {"independent": reference(CLOSURE/"independent-result.json"),
                               "root": reference(CLOSURE/"root-disposition.json")}
draft["preceding_draft_ref"] = reference(BASE/"request-draft.json")
dest = BASE/"request-accepted-content-v2.json"
with dest.open("xb") as handle:
    handle.write((json.dumps(draft, ensure_ascii=False, indent=2)+"\n").encode("utf-8"))
record = {"schema": "A24R1FixedAcceptedNativeContent/v1", "request_ref": reference(dest),
    "conversion_ref": draft["native_conversion_ref"], "fixed_model_refs": draft["model_binding"],
    "content_acceptance": draft["content_acceptance"], "model_failure_preserved": True,
    "human_user_content_approval_claimed": False, "model_calls": 0, "platform_calls": 0,
    "body_schema": "CURRENT_SCHEMA_UNBOUND", "write_eligible": False}
with (OUT/"fixed-accepted-content-binding.json").open("xb") as handle:
    handle.write((json.dumps(record, indent=2)+"\n").encode())
print(json.dumps({"request_sha256": record["request_ref"]["sha256"], "model_calls": 0, "platform_calls": 0}))
