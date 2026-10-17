"""Public C01 contracts API. Structure, offline validation and exchange only."""
import json
from pathlib import Path

from .integrity import artifact_ref, content_digest, policy_ref, seal_artifact as _legacy_seal_artifact, seal_policy
from .models import (
    SCHEMA_VERSION, Action, ActionResult, ApplyPlan, ArtifactRef, BatchReport,
    CheckReport, EvidenceBundle, ExchangeBundle, ExecutionReceipt, Issue,
    OriginalBox, PlatformPolicy, PlatformSnapshot, PolicyRef, QuestionGraph,
    ReviewPatch, SourceBundle,
)
from .validation import (ContractError, assert_patch_base, assert_plan_ready as _legacy_assert_plan_ready,
                         load_bundle, validate_bundle as _legacy_validate_bundle)
from .recovery import (
    RECOVERY_SCHEMA_VERSION, RECOVERY_EXCHANGE_VERSION, RECOVERY_PROFILE, Node,
    RecoveryExchangeBundle, load_archive_bundle, load_recovery_bundle,
    validate_recovery_bundle, convert_synthetic_fixture, assert_recovery_plan_ready,
    effective_recovery_outcomes, seal_recovery_artifact, recovery_artifact_ref,
    recovery_schema, target_state_digest, canonical_hash, obligation_id,
    plan_dependency_digest,
)


def validate_bundle(bundle, asset_root=None):
    """Select the explicit namespace; C01 validation and defaults stay unchanged."""
    version = bundle.get('format_version') if isinstance(bundle, dict) else getattr(bundle, 'format_version', None)
    if version == RECOVERY_EXCHANGE_VERSION:
        return validate_recovery_bundle(bundle, asset_root=asset_root)
    return _legacy_validate_bundle(bundle, asset_root=asset_root)


def seal_artifact(data):
    version = data.get('schema_version') if isinstance(data, dict) else getattr(data, 'schema_version', None)
    if version == RECOVERY_SCHEMA_VERSION:
        return seal_recovery_artifact(data)
    return _legacy_seal_artifact(data)


def assert_plan_ready(bundle, plan_ref, current_snapshot_ref):
    version = bundle.get('format_version') if isinstance(bundle, dict) else getattr(bundle, 'format_version', None)
    if version == RECOVERY_EXCHANGE_VERSION:
        return assert_recovery_plan_ready(bundle, plan_ref, current_snapshot_ref)
    return _legacy_assert_plan_ready(bundle, plan_ref, current_snapshot_ref)


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
           "assert_patch_base", "assert_plan_ready", "load_bundle", "validate_bundle",
           "RECOVERY_SCHEMA_VERSION", "RECOVERY_EXCHANGE_VERSION", "RECOVERY_PROFILE", "Node",
           "RecoveryExchangeBundle", "load_archive_bundle", "load_recovery_bundle", "validate_recovery_bundle",
           "convert_synthetic_fixture", "assert_recovery_plan_ready", "effective_recovery_outcomes",
           "seal_recovery_artifact", "recovery_artifact_ref", "recovery_schema", "target_state_digest",
           "canonical_hash", "obligation_id", "plan_dependency_digest"]
