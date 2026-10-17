"""Pure-stdlib, design-only validation of the R2 synthetic event-prefix Resource.

This module checks serialized facts, never a runtime store, platform, lock or API.
No ``complete`` flag establishes completeness.  The caller supplies the exact
ApplyPlan artifact and the basis CAS head; errors are static design findings.
"""

import datetime
import hashlib
import json
import re
from pathlib import PurePosixPath


ZERO_HASH = "0" * 64
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
REF_KEYS = {"artifact_id", "revision", "kind", "content_hash"}
TARGET_KEYS = {"platform_namespace", "target_id", "book_id"}
RESOURCE_KEYS = {"path", "sha256", "media_type", "origin"}
EVENT_KEYS = {
    "sequence", "event", "journal_id", "target_key", "plan_ref", "owner_id",
    "generation", "recorded_at", "payload", "previous_hash", "event_hash",
}
HEADER_KEYS = {
    "format_version", "journal_id", "target_key", "plan_ref", "scope_id",
    "owner_id", "generation", "from_sequence", "through_sequence", "head_hash",
    "genesis_hash", "events", "design_only",
}
HEADER_OPTIONAL = {"complete", "description", "subject_action_id"}
ACTION_KEYS = {"action_id", "action_digest"}
PAYLOAD_KEYS = {
    "PLAN_ACCEPTED": {"plan_ref", "actions"},
    "PLAN_ACTIONS_RESERVED": {"reservations"},
    "PLAN_STARTED": {"plan_state"},
    "WRITE_INTENT_COMMITTED": ACTION_KEYS | {"intent_ref", "obligation_id"},
    "DISPATCH_PERMIT_ISSUED": ACTION_KEYS | {"intent_ref", "permit_id"},
    "DISPATCH_PERMIT_CONSUMED": ACTION_KEYS | {"intent_ref", "permit_id"},
    "DISPATCH_STARTED": ACTION_KEYS | {"intent_ref", "permit_id"},
    "ACTION_RESULT_COMMITTED": ACTION_KEYS | {
        "intent_ref", "obligation_id", "fact", "outcome", "plan_state",
    },
    "UNATTEMPTED_ABSENCE_COMMITTED": ACTION_KEYS | {
        "fact", "outcome", "plan_state",
    },
}


def canonical_hash(value):
    """H(value): UTF-8 JSON, sorted keys, compact, Unicode, no nonfinite numbers."""
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def hash_event(event):
    """Hash every event member except its top-level event_hash member."""
    return canonical_hash({key: value for key, value in event.items() if key != "event_hash"})


def _positive_int(value):
    return type(value) is int and value > 0


def _string(value):
    return isinstance(value, str) and bool(value)


def _sha(value):
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _ref(value, kind=None):
    return (
        isinstance(value, dict) and set(value) == REF_KEYS
        and _string(value.get("artifact_id")) and _positive_int(value.get("revision"))
        and _string(value.get("kind")) and _sha(value.get("content_hash"))
        and (kind is None or value.get("kind") == kind)
    )


def _resource(value):
    if not isinstance(value, dict) or set(value) != RESOURCE_KEYS:
        return False
    path = value.get("path")
    if not _string(path) or "\\" in path or ":" in path:
        return False
    segments = path.split("/")
    return (
        not PurePosixPath(path).is_absolute()
        and all(segment not in ("", ".", "..") for segment in segments)
        and _sha(value.get("sha256"))
        and value.get("media_type") == "application/json"
        and value.get("origin") == "SYNTHETIC"
    )


def _timestamp(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value[:-1] + "+00:00")
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else None


def _action_bindings(value):
    return (
        isinstance(value, list) and bool(value)
        and all(
            isinstance(item, dict) and set(item) == ACTION_KEYS
            and _string(item.get("action_id")) and _sha(item.get("action_digest"))
            for item in value
        )
    )


def validate_prefix(prefix, plan, expected_head=None, subject_action_id=None):
    """Return distinct static error-code strings; [] means serialized checks pass.

    ``plan`` is the full ApplyPlan artifact, not a reference. ``expected_head``
    is the unattempted basis's {sequence, hash}; callers validating that basis
    must pass it.  ``subject_action_id`` names the unattempted action for which
    this is the *precommit* prefix.  The optional header subject must agree.
    Resource bytes, consumer declarations and fact bodies are independently
    checked by the containing R2 checker; this function checks their event
    Resource envelopes and the exact action/intent/permit identities.
    """
    errors = []

    def add(code):
        if code not in errors:
            errors.append(code)

    if not isinstance(prefix, dict):
        return ["PREFIX_SHAPE_INVALID"]
    if not HEADER_KEYS <= set(prefix) or set(prefix) - HEADER_KEYS - HEADER_OPTIONAL:
        add("PREFIX_SHAPE_INVALID")
    if (
        prefix.get("format_version") != "a03-event-prefix-1"
        or prefix.get("design_only") is not True
        or not _string(prefix.get("journal_id"))
        or not _string(prefix.get("scope_id"))
        or not _string(prefix.get("owner_id"))
        or not _positive_int(prefix.get("generation"))
        or type(prefix.get("from_sequence")) is not int
        or prefix.get("from_sequence") != 1
        or not _positive_int(prefix.get("through_sequence"))
        or prefix.get("genesis_hash") != ZERO_HASH
        or not _sha(prefix.get("head_hash"))
        or not _ref(prefix.get("plan_ref"), "ApplyPlan")
        or ("complete" in prefix and type(prefix["complete"]) is not bool)
        or ("description" in prefix and not _string(prefix["description"]))
        or ("subject_action_id" in prefix and not _string(prefix["subject_action_id"]))
    ):
        add("PREFIX_SHAPE_INVALID")
    target = prefix.get("target_key")
    if (
        not isinstance(target, dict) or set(target) != TARGET_KEYS
        or not all(_string(value) for value in target.values())
    ):
        add("PREFIX_BINDING_MISMATCH")
    if not isinstance(plan, dict) or plan.get("kind") != "ApplyPlan":
        add("PREFIX_PLAN_INVALID")
        return errors
    plan_ref = {key: plan.get(key) for key in REF_KEYS}
    actions = plan.get("payload", {}).get("actions") if isinstance(plan.get("payload"), dict) else None
    if not isinstance(actions, list) or not actions:
        add("PREFIX_PLAN_INVALID")
        return errors
    try:
        bindings = [{"action_id": action["action_id"], "action_digest": canonical_hash(action)} for action in actions]
    except (KeyError, TypeError, ValueError):
        add("PREFIX_PLAN_INVALID")
        return errors
    if not _action_bindings(bindings) or len({a["action_id"] for a in bindings}) != len(bindings):
        add("PREFIX_PLAN_INVALID")
        return errors
    action_map = {action["action_id"]: action for action in actions}
    digests = {item["action_id"]: item["action_digest"] for item in bindings}
    if (
        not _ref(plan_ref, "ApplyPlan") or prefix.get("plan_ref") != plan_ref
        or prefix.get("scope_id") != plan.get("scope_id")
        or not isinstance(target, dict) or target.get("book_id") != plan.get("book_id")
        or any(not isinstance(a.get("target"), dict) or a["target"].get("target_id") != target.get("target_id") for a in actions)
    ):
        add("PREFIX_BINDING_MISMATCH")
    header_subject = prefix.get("subject_action_id")
    if subject_action_id is not None and header_subject is not None and subject_action_id != header_subject:
        add("PREFIX_SUBJECT_MISMATCH")
    subject = subject_action_id if subject_action_id is not None else header_subject
    if subject is not None and (not _string(subject) or subject not in action_map):
        add("PREFIX_SUBJECT_MISMATCH")
    events = prefix.get("events")
    if not isinstance(events, list) or not events:
        add("PREFIX_ACCEPTANCE_MISSING")
        return errors
    if prefix.get("through_sequence") != len(events):
        add("PREFIX_SEQUENCE_BROKEN")
    if not isinstance(events[0], dict) or events[0].get("event") != "PLAN_ACCEPTED":
        add("PREFIX_ACCEPTANCE_MISSING")
    if expected_head is not None:
        if (
            not isinstance(expected_head, dict) or set(expected_head) != {"sequence", "hash"}
            or not _positive_int(expected_head.get("sequence")) or not _sha(expected_head.get("hash"))
            or expected_head.get("sequence") != prefix.get("through_sequence")
            or expected_head.get("hash") != prefix.get("head_hash")
        ):
            add("PREFIX_CAS_MISMATCH")

    previous_hash = ZERO_HASH
    previous_time = None
    state = "UNACCEPTED"
    accepted = reserved = started = False
    action_state = {action_id: {} for action_id in action_map}
    permits = set()
    intent_identities = set()
    obligations = set()
    for sequence, event in enumerate(events, 1):
        if not isinstance(event, dict):
            add("PREFIX_EVENT_INVALID")
            continue
        if set(event) != EVENT_KEYS:
            add("PREFIX_EVENT_INVALID")
        if type(event.get("sequence")) is not int or event.get("sequence") != sequence:
            add("PREFIX_SEQUENCE_BROKEN")
        try:
            actual_hash = hash_event(event)
        except (TypeError, ValueError):
            actual_hash = None
        if (
            not _sha(event.get("event_hash")) or not _sha(event.get("previous_hash"))
            or event.get("event_hash") != actual_hash
            or event.get("previous_hash") != previous_hash
        ):
            add("PREFIX_HASH_BROKEN")
        previous_hash = event.get("event_hash")
        if any(event.get(key) != prefix.get(key) for key in ("journal_id", "target_key", "plan_ref", "owner_id", "generation")):
            add("PREFIX_BINDING_MISMATCH")
        if not _positive_int(event.get("generation")):
            add("PREFIX_BINDING_MISMATCH")
        recorded = _timestamp(event.get("recorded_at"))
        if recorded is None or (previous_time is not None and recorded < previous_time):
            add("PREFIX_EVENT_TIME_INVALID")
        if recorded is not None:
            previous_time = recorded
        name = event.get("event")
        payload = event.get("payload")
        if not _string(name) or name not in PAYLOAD_KEYS or not isinstance(payload, dict) or set(payload) != PAYLOAD_KEYS[name]:
            add("PREFIX_EVENT_INVALID")
            continue
        if state == "INTERRUPTED" and name != "UNATTEMPTED_ABSENCE_COMMITTED":
            add("PREFIX_INTERRUPTED_DISPATCH")
        if name == "PLAN_ACCEPTED":
            if sequence != 1 or accepted or payload.get("plan_ref") != plan_ref or payload.get("actions") != bindings:
                add("PREFIX_ACCEPTANCE_INVALID")
            if not _action_bindings(payload.get("actions")):
                add("PREFIX_ACCEPTANCE_INVALID")
            accepted = True
            state = "ACCEPTED"
            continue
        if name == "PLAN_ACTIONS_RESERVED":
            if not accepted or reserved or started or payload.get("reservations") != bindings:
                add("PREFIX_RESERVATION_INVALID")
            if not _action_bindings(payload.get("reservations")):
                add("PREFIX_RESERVATION_INVALID")
            reserved = True
            continue
        if name == "PLAN_STARTED":
            if not accepted or not reserved or started or payload.get("plan_state") != "RUNNING":
                add("PREFIX_STATE_INVALID")
            started = True
            state = "RUNNING"
            continue
        if not accepted or not reserved or not started:
            add("PREFIX_RESERVATION_INVALID")
        action_id = payload.get("action_id")
        if not _string(action_id) or action_id not in action_map or payload.get("action_digest") != digests.get(action_id):
            add("PREFIX_ACTION_MISMATCH")
            continue
        if subject is not None and action_id == subject:
            add("PREFIX_SUBJECT_ALREADY_ATTEMPTED")
        current = action_state[action_id]
        if "fact" in payload and not _resource(payload["fact"]):
            add("PREFIX_FACT_INVALID")
        if name == "UNATTEMPTED_ABSENCE_COMMITTED":
            if state != "INTERRUPTED" or current or payload.get("outcome") != "NOT_APPLIED" or payload.get("plan_state") != "INTERRUPTED":
                add("PREFIX_UNATTEMPTED_INVALID")
            current["outcome"] = "NOT_APPLIED"
            continue
        intent = payload.get("intent_ref")
        if not _ref(intent, "WriteIntent"):
            add("PREFIX_INTENT_INVALID")
        if name == "WRITE_INTENT_COMMITTED":
            dependency_ids = action_map[action_id].get("depends_on", [])
            if (
                state != "RUNNING" or current or not isinstance(dependency_ids, list)
                or not all(_string(dep) for dep in dependency_ids)
                or any(action_state.get(dep, {}).get("outcome") != "APPLIED" for dep in dependency_ids)
            ):
                add("PREFIX_INTENT_INVALID")
            obligation = payload.get("obligation_id")
            try:
                identity = canonical_hash(intent)
            except (TypeError, ValueError):
                identity = None
                add("PREFIX_INTENT_INVALID")
            if not _string(obligation) or obligation in obligations or identity in intent_identities:
                add("PREFIX_INTENT_INVALID")
            obligations.add(obligation) if isinstance(obligation, str) else None
            intent_identities.add(identity)
            current.update(intent_ref=intent, obligation_id=obligation, stage="INTENT")
            continue
        if current.get("intent_ref") != intent:
            add("PREFIX_INTENT_INVALID")
        if name == "DISPATCH_PERMIT_ISSUED":
            permit = payload.get("permit_id")
            if state != "RUNNING" or current.get("stage") != "INTENT" or not _string(permit) or permit in permits:
                add("PREFIX_PERMIT_INVALID")
            if isinstance(permit, str):
                permits.add(permit)
            current.update(permit_id=permit, stage="ISSUED")
        elif name == "DISPATCH_PERMIT_CONSUMED":
            if state != "RUNNING" or current.get("stage") != "ISSUED" or current.get("permit_id") != payload.get("permit_id"):
                add("PREFIX_PERMIT_INVALID")
            current["stage"] = "CONSUMED"
        elif name == "DISPATCH_STARTED":
            if state != "RUNNING" or current.get("stage") != "CONSUMED" or current.get("permit_id") != payload.get("permit_id"):
                add("PREFIX_PERMIT_INVALID")
            current["stage"] = "DISPATCHED"
        elif name == "ACTION_RESULT_COMMITTED":
            if current.get("stage") != "DISPATCHED":
                add("PREFIX_DISPATCH_MISSING")
            if state != "RUNNING" or current.get("obligation_id") != payload.get("obligation_id") or "outcome" in current:
                add("PREFIX_RESULT_INVALID")
            outcome = payload.get("outcome")
            if outcome not in ("APPLIED", "UNKNOWN", "NOT_APPLIED"):
                add("PREFIX_RESULT_INVALID")
            required_state = "INTERRUPTED" if outcome == "UNKNOWN" else "RUNNING"
            if payload.get("plan_state") != required_state:
                add("PREFIX_STATE_INVALID")
            current.update(outcome=outcome, stage="RESULT")
            if outcome == "UNKNOWN":
                state = "INTERRUPTED"
    if not accepted:
        add("PREFIX_ACCEPTANCE_MISSING")
    if not reserved:
        add("PREFIX_RESERVATION_INVALID")
    if not started:
        add("PREFIX_STATE_INVALID")
    if previous_hash != prefix.get("head_hash"):
        add("PREFIX_HASH_BROKEN")
    if subject is not None and state != "INTERRUPTED":
        add("PREFIX_STATE_INVALID")
    return errors
