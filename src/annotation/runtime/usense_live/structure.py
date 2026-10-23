"""Offline structural drafts and whole-object comparison; no live transport.

The frontend proves request construction, not the backend preview/apply schema.
Every draft remains non-executable. A coordinator must collect and audit real
preview/apply responses before adding any directory writer.
"""
import copy
from datetime import datetime, timezone
from pathlib import Path
import re

from . import update as u
from .batch import file_ref, ref_bytes
from .core import sha, utc
from .insertion import _questions, flat_digest, SUFFIXES

FRONTEND_SHA = "d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41"
PREVIEW = "/qieti/api/annotate_pic/directory/change-set/preview"
APPLY = "/qieti/api/annotate_pic/directory/change-set/apply"
COMMIT = "/qieti/api/annotate_pic/commit_unified_submit"
MOVE_SCHEMA = "b-usense-directory-move-draft/0.1"


def protocol_evidence(path):
    """Bind exact local frontend bytes and the literal observed request builders."""
    ref = file_ref(path)
    u.require(ref["sha256"] == FRONTEND_SHA, "STRUCTURE_FRONTEND_HASH_UNKNOWN")
    source = Path(path).read_text(encoding="utf-8")
    tokens = {"base": 'Hr="/qieti/api/annotate_pic"',
              "preview": 'gn.post(`${Hr}/directory/change-set/preview`,{file_id:e,original_directory_data:t,draft_directory_data:n})',
              "apply": 'gn.post(`${Hr}/directory/change-set/apply`,{file_id:e,original_directory_data:t,draft_directory_data:n})',
              "commit": 'gn.post(`${Hr}/commit_unified_submit`,e)',
              "normalize": 'function Eg(N){const O=xc(N);return C0(O),O}',
              "new_question": 'question_order:we?null:fn,is_new_question_insertion:we,insert_after_order:we?na.insertAfterOrder:null'}
    offsets = {}
    for key, token in tokens.items():
        u.require(source.count(token) == 1, "STRUCTURE_FRONTEND_REQUEST_BUILDER_AMBIGUOUS")
        offsets[key] = source.index(token)
    return {"schema": "b-usense-frontend-structural-evidence/0.1", "file": ref,
            "offset_unit": "unicode-codepoints", "offsets": offsets,
            "request_protocol_observed": True, "directory_response_schema_observed": False}


def check_protocol(proof):
    u.require(type(proof) is dict and proof.get("schema") == "b-usense-frontend-structural-evidence/0.1", "STRUCTURE_PROTOCOL_REQUIRED")
    ref_bytes(proof["file"])
    u.require(u.json_same(proof, protocol_evidence(proof["file"]["path"])), "STRUCTURE_PROTOCOL_PROOF_CHANGED")


def full_snapshot(flat):
    """Validate every native question, frame, directory identity and global page."""
    u.require(type(flat) is dict and {"directory", "frames", "source"} <= set(flat), "STRUCTURE_FULL_BOOK_REQUIRED")
    identities, info_ids = [], set()
    nodes = _questions(flat["directory"])
    u.require(bool(nodes), "STRUCTURE_EMPTY_BOOK_UNSUPPORTED")
    expected = {"directory", "frames", "source"} | {f"q{q}_{suffix}" for q in range(1, len(nodes)+1) for suffix in SUFFIXES}
    pages = {name for name in flat if re.fullmatch(r"page_[0-9]+", name)}
    u.require(set(flat) == expected | pages, "STRUCTURE_COMPLETE_NATIVE_MAP_REQUIRED")
    for name in ("source", *pages):
        u._response(flat[name])
    for q, (node, parent) in enumerate(nodes, 1):
        info = u._response(flat[f"q{q}_info"])
        u.require(type(info) is dict and u._id(info.get("id")) and info["id"] not in info_ids, "STRUCTURE_INFO_AMBIGUOUS")
        info_ids.add(info["id"])
        target = {"book_id": u.BOOK, "lesson_directory_id": parent, "node_id": node["id"], "info_id": info["id"], "question_order": q}
        u.validate_snapshot(u.from_captured_map(flat, f"q{q}_"), target)
        identities.append(target)
    frames = u._response(flat["frames"])
    u.require(all(row.get("belong_to_level") == "question_level" and 1 <= u._order(row.get("order_in_level")) <= len(nodes)
                  for row in frames), "STRUCTURE_UNBOUND_FRAME")
    return identities


def directories(directory):
    result = {}
    def walk(nodes):
        for node in nodes:
            if not node.get("isQuestion", False):
                u.require(node["id"] not in result, "STRUCTURE_DIRECTORY_AMBIGUOUS")
                result[node["id"]] = node
                walk(node.get("children", []))
    walk(u._response(directory)["directory_data"])
    return result


def fingerprint(plan):
    value = copy.deepcopy(plan)
    value.pop("plan_sha256", None)
    return u.digest(value)


def check_fresh(plan, fresh, *, now=None):
    """A draft never grants writes, including after an exact fresh precheck."""
    u.require(fingerprint(plan) == plan["plan_sha256"], "STRUCTURE_DRAFT_CHANGED")
    check_protocol(plan["protocol"])
    if plan.get("schema") == MOVE_SCHEMA:
        rebuilt = make_move_draft(plan["before_full"],plan["targets"],plan["destination_directory_id"],
                                  plan["scope_review"],plan["protocol"],plan["baseline_observed_at"])
    else:
        from .new_question import SCHEMA, make_new_draft
        u.require(plan.get("schema") == SCHEMA,"STRUCTURE_DRAFT_SCHEMA")
        rebuilt = make_new_draft(plan["before_full"],plan["candidate"],plan["scope_review"],plan["content_review"],
                                 plan["protocol"],plan["baseline_observed_at"])
    u.require(u.json_same(rebuilt,plan),"STRUCTURE_DRAFT_NOT_RECONSTRUCTIBLE")
    age = ((now or datetime.now(timezone.utc)) - utc(plan["baseline_observed_at"])).total_seconds()
    u.require(0 <= age <= 900, "STRUCTURE_BASELINE_EXPIRED")
    full_snapshot(fresh)
    u.require(flat_digest(fresh) == plan["before_sha256"] and
              all(u.json_same(value, fresh[key]) for key, value in plan["before_full"].items()), "STRUCTURE_STALE_FULL_BOOK")
    return {"baseline_match": True, "write_authorized": False, "automatic_retry_allowed": False}


def check_ledger(ledger_root, identity_key):
    root = Path(ledger_root)
    u.require(root.is_dir(), "STRUCTURE_REAL_LEDGER_REQUIRED")
    u.require(not list(root.glob(identity_key + "*.json")), "STRUCTURE_EXISTING_INTENT_NO_RETRY")


def preflight(plan, fresh, ledger_root, *, now=None):
    result = check_fresh(plan, fresh, now=now)
    check_ledger(ledger_root, plan["ledger_key"])
    targets = plan.get("targets", [plan.get("candidate", {}).get("anchor")])
    for target in targets:
        stable = "usense-existing-" + u.digest({key:target[key] for key in ("book_id","node_id","info_id")})
        # No structural predecessor schema is guessed here. Even an accepted
        # history requires a separate reviewed structural admission adapter.
        check_ledger(ledger_root, stable)
    result.update(status="EXACT_FRESH_BASELINE_ONLY_STRUCTURAL_WRITER_UNAVAILABLE", ledger_clear=True,
                  platform_acceptance=False, platform_requests=0)
    return result


def make_move_draft(before, targets, destination, scope_review, protocol, observed_at):
    """Only move existing questions while preserving global order and every ID."""
    check_protocol(protocol)
    utc(observed_at)
    identities = full_snapshot(before)
    u.require(type(targets) is list and bool(targets) and len({t["node_id"] for t in targets}) == len(targets), "STRUCTURE_UNIQUE_MOVE_TARGETS")
    u.require(all(any(u.json_same(t, identity) for identity in identities) for t in targets), "STRUCTURE_MOVE_STABLE_BINDING")
    u.require(len({t["lesson_directory_id"] for t in targets}) == 1, "STRUCTURE_SINGLE_SOURCE_REQUIRED")
    source = targets[0]["lesson_directory_id"]
    u.require(source != destination and all(t["book_id"] == u.BOOK for t in targets), "STRUCTURE_MOVE_DESTINATION")
    expected_scope = {"schema": "b-usense-move-scope-review/0.1", "book_id": u.BOOK, "targets": targets,
                      "source_directory_id": source, "destination_directory_id": destination,
                      "decision": "SOURCE_LESSON_MEMBERSHIP_REVIEWED"}
    u.require(u.json_same(scope_review, expected_scope), "STRUCTURE_MOVE_SCOPE_REVIEW_REQUIRED")
    expected = copy.deepcopy(before)
    lookup = directories(expected["directory"])
    u.require(source in lookup and destination in lookup, "STRUCTURE_DIRECTORY_NOT_FOUND")
    dest = lookup[destination]
    u.require("children" in dest and not dest["children"], "STRUCTURE_EMPTY_LEAF_DESTINATION_REQUIRED")
    selected = {t["node_id"] for t in targets}
    old = lookup[source]["children"]
    moved = [node for node in old if node["id"] in selected]
    u.require(len(moved) == len(targets) and [node["id"] for node in moved] == [t["node_id"] for t in targets], "STRUCTURE_MOVE_NATIVE_ORDER_REQUIRED")
    lookup[source]["children"] = [node for node in old if node["id"] not in selected]
    dest["children"] = moved
    # Frontend Eg/C0 reindexes by tree traversal. This limited migration only
    # admits moves with NO global order change; no unobserved rewrite is guessed.
    after_nodes = _questions(expected["directory"])
    u.require([node["id"] for node, _ in after_nodes] == [t["node_id"] for t in identities], "STRUCTURE_ORDER_CHANGING_MOVE_UNSUPPORTED")
    orders = {t["question_order"] for t in targets}
    for row in expected["frames"]["data"]:
        if u._order(row["order_in_level"]) in orders:
            row["directory_id"] = destination
    for q in orders:
        for row in expected[f"q{q}_annotations"]["data"]:
            row["directory_id"] = destination
    after_ids = full_snapshot(expected)
    u.require(all(before_id["node_id"] == after_id["node_id"] and before_id["info_id"] == after_id["info_id"]
                  for before_id, after_id in zip(identities, after_ids)), "STRUCTURE_IDENTITY_CHANGED")
    payload = {"file_id": u.BOOK,
               "original_directory_data": copy.deepcopy(before["directory"]["data"]["directory_data"]),
               "draft_directory_data": copy.deepcopy(expected["directory"]["data"]["directory_data"])}
    key = "usense-move-" + u.digest({"book_id": u.BOOK, "node_ids": sorted(selected)})
    plan = {"schema": MOVE_SCHEMA, "status": "OFFLINE_PREVIEW_DRAFT_NOT_EXECUTABLE", "book_id": u.BOOK,
            "protocol": copy.deepcopy(protocol), "baseline_observed_at": observed_at,
            "before_full": copy.deepcopy(before), "before_sha256": flat_digest(before), "expected_full": expected,
            "targets": copy.deepcopy(targets), "destination_directory_id": destination, "scope_review": copy.deepcopy(scope_review),
            "preview_request": {"method": "POST", "path": PREVIEW, "body": payload},
            "apply_endpoint_observed": APPLY, "apply_request": None,
            "blockers": ["DIRECTORY_PREVIEW_RAW_RESPONSE_SCHEMA_NOT_OBSERVED", "DIRECTORY_APPLY_RECEIPT_SCHEMA_NOT_OBSERVED"],
            "ledger_key": key, "write_authorized": False, "automatic_retry_allowed": False,
            "protected_other_questions": len(identities)-len(targets), "old_identities": identities}
    plan["plan_sha256"] = fingerprint(plan)
    return plan


def verify_move(plan, after):
    u.require(fingerprint(plan) == plan["plan_sha256"], "STRUCTURE_DRAFT_CHANGED")
    rebuilt = make_move_draft(plan["before_full"], plan["targets"], plan["destination_directory_id"],
                              plan["scope_review"], plan["protocol"], plan["baseline_observed_at"])
    u.require(u.json_same(rebuilt, plan), "STRUCTURE_MOVE_PLAN_TAMPERED")
    full_snapshot(after)
    delta = u.differences(plan["expected_full"], after)
    return {"schema": "b-usense-move-native-comparison/0.1", "match": not delta,
            "status": "NATIVE_OBJECTS_MATCH_REQUIRES_PROCESS_RECEIPT_AND_EXPORT" if not delta else "HOLD",
            "differences": delta, "protected_other_questions": plan["protected_other_questions"],
            "stable_identities_preserved": not delta, "platform_acceptance": False, "automatic_retry_allowed": False}
