"""Public C01 contracts API. Structure, offline validation and exchange only."""
import json
from pathlib import Path

from .integrity import artifact_ref, content_digest, policy_ref, seal_artifact, seal_policy
from .models import (
    SCHEMA_VERSION, Action, ActionResult, ApplyPlan, ArtifactRef, BatchReport,
    CheckReport, EvidenceBundle, ExchangeBundle, ExecutionReceipt, Issue,
    OriginalBox, PlatformPolicy, PlatformSnapshot, PolicyRef, QuestionGraph,
    ReviewPatch, SourceBundle,
)
from .validation import ContractError, assert_patch_base, assert_plan_ready, load_bundle, validate_bundle


def schema():
    """Generate JSON Schema from the same Python definitions; semantic checks are additional."""
    return ExchangeBundle.model_json_schema()


def write_bundle(bundle, path):
    """Validate and create a new exchange file; never overwrite an old revision/file."""
    bundle = validate_bundle(bundle)
    path = Path(path)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(bundle.model_dump(mode="json"), ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return path


__all__ = ["SCHEMA_VERSION", "Action", "ActionResult", "ApplyPlan", "ArtifactRef", "BatchReport",
           "CheckReport", "EvidenceBundle", "ExchangeBundle", "ExecutionReceipt", "Issue",
           "OriginalBox", "PlatformPolicy", "PlatformSnapshot", "PolicyRef", "QuestionGraph",
           "ReviewPatch", "SourceBundle", "ContractError", "artifact_ref", "policy_ref",
           "content_digest", "seal_artifact", "seal_policy", "schema", "write_bundle",
           "assert_patch_base", "assert_plan_ready", "load_bundle", "validate_bundle"]
