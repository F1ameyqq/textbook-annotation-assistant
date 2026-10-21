"""Immutable controlled .local evidence references; generic journal holds hashes."""
import hashlib
import json
import os
from pathlib import Path

from annotation.contracts.integrity import unique_object
from annotation.quality.live_pilot import require
from annotation.runtime.live_pilot.authority import Authority
from annotation.runtime.storage.common import canonical, digest


class ControlledVault:
    def __init__(self, authority):
        require(type(authority) is Authority, "VALIDATED_OWNER_AUTHORITY_REQUIRED")
        authority.check()
        self.authority = authority
        self.root = authority.output / "private" / "immutable"
        self.author_evidence_ref = None

    def freeze(self, kind, question_id, value):
        require(kind in ("intent", "get", "refresh", "reopen", "author-evidence", "reconcile"), "PRIVATE_EVIDENCE_KIND")
        path = self.root / (kind + "-" + hashlib.sha256(question_id.encode()).hexdigest() + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = canonical(value)
        with path.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                "media_type": "application/json", "scope": "CONTROLLED_PRIVATE_BUSINESS_EVIDENCE"}

    def load(self, reference):
        require(isinstance(reference, dict) and set(reference) == {"path", "bytes", "sha256", "media_type", "scope"} and
                reference["media_type"] == "application/json" and reference["scope"] == "CONTROLLED_PRIVATE_BUSINESS_EVIDENCE",
                "PRIVATE_EVIDENCE_REF")
        path = Path(reference["path"]).resolve()
        allowed = self.root.resolve() in path.parents
        if self.authority.author_release is not None:
            allowed = allowed or reference in self.authority.author_release.get("private_refs", [])
        require(allowed and not path.is_symlink(), "PRIVATE_EVIDENCE_SCOPE")
        raw = path.read_bytes()
        require(len(raw) == reference["bytes"] and hashlib.sha256(raw).hexdigest() == reference["sha256"], "PRIVATE_EVIDENCE_HASH")
        return json.loads(raw, object_pairs_hook=unique_object)


def resolve_intent(record, vault):
    if "private_intent_ref" not in record:
        return record  # Historical immutable layout is read only, never rewritten.
    require(vault is not None, "PRIVATE_INTENT_VAULT_REQUIRED")
    value = vault.load(record["private_intent_ref"])
    require(all(value.get(k) == record.get(k) for k in ("code_version", "input_hash", "approval_hash", "policy",
                                                       "plan_hash", "baseline_hash", "payload_hash")) and
            digest(value["plan"]) == record["plan_hash"] and digest(value["baseline"]) == record["baseline_hash"] and
            digest(value["payload"]) == record["payload_hash"], "PRIVATE_INTENT_BINDING")
    return dict(value, question_id=record["question_id"])
