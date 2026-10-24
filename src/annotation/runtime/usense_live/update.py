"""Pure existing-question update plans for the fixed verification book 46007447.

Native snapshot: directory, frames, annotations, info, zones (five raw responses).
No HTTP, browser, credentials, writes, retries, ledger reset or native-ID guessing.
The caller binds current evidence and approval provenance, then separately enforces
fresh read, once-only intent, one send, real receipt and independent readback.
"""
from __future__ import annotations

import copy
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser
import hashlib
import json
import math
import re

BOOK = "46007447"
ZONES = ("question", "choice", "answer", "analysis", "knowledge_point")
SNAPSHOT_KEYS = ("directory", "frames", "annotations", "info", "zones")
TARGET_KEYS = ("book_id", "lesson_directory_id", "node_id", "info_id", "question_order")
PLAN_SCHEMA = "usense-existing-question-update/v1"
ABSENT = {"success": False, "message": "未找到标注结果"}


class UpdateError(ValueError):
    def __init__(self, code, detail=""):
        self.code, self.detail = code, detail
        super().__init__(detail or code)


def require(ok, code, detail=""):
    if not ok:
        raise UpdateError(code, detail)


def json_same(left, right):
    """V3 json_same semantics: parsed types, object order and array order matter."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return (list(left) == list(right) and
                all(json_same(left[key], right[key]) for key in left))
    if isinstance(left, list):
        return (len(left) == len(right) and
                all(json_same(a, b) for a, b in zip(left, right)))
    return left == right


def _json(value):
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float:
        require(math.isfinite(value), "NONFINITE_JSON")
        return
    if type(value) is list:
        for item in value:
            _json(item)
        return
    if type(value) is dict:
        require(all(type(key) is str for key in value), "NONSTRING_JSON_KEY")
        for item in value.values():
            _json(item)
        return
    raise UpdateError("NON_JSON_VALUE")


def digest(value):
    _json(value)
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                                    allow_nan=False).encode("utf-8")).hexdigest()


def text_digest(text):
    require(type(text) is str, "TEXT_REQUIRED")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY", key)
        result[key] = value
    return result


def loads(raw):
    """Strict JSON ingestion; preserve all types and key order; reject duplicates."""
    value = json.loads(raw, object_pairs_hook=unique_object,
                       parse_constant=lambda x: (_ for _ in ()).throw(UpdateError("NONFINITE_JSON", x)))
    _json(value)
    return value


def from_captured_map(captured, prefix="q1_"):
    """Adapt the initial collector's flat q1_* map without altering native values."""
    needed = ("directory", "frames", prefix + "annotations", prefix + "info") + tuple(prefix + zone for zone in ZONES)
    require(type(captured) is dict and all(key in captured for key in needed), "CAPTURED_MAP_MISSING")
    return {"directory": copy.deepcopy(captured["directory"]), "frames": copy.deepcopy(captured["frames"]),
            "annotations": copy.deepcopy(captured[prefix + "annotations"]), "info": copy.deepcopy(captured[prefix + "info"]),
            "zones": {zone: copy.deepcopy(captured[prefix + zone]) for zone in ZONES}}


def _id(value):
    return type(value) is str and bool(value) and value.strip() == value


def _order(value, *, zero=False):
    if type(value) is int and value >= (0 if zero else 1):
        return value
    if type(value) is str and re.fullmatch(r"0|[1-9][0-9]*" if zero else r"[1-9][0-9]*", value):
        return int(value)
    raise UpdateError("ORDER_TYPE_OR_FORMAT")


def _response(value, code=(0, 200)):
    require(type(value) is dict and type(value.get("code")) is int and value["code"] in code and
            value.get("message") == "success" and "data" in value, "NATIVE_RESPONSE_STATUS")
    return value["data"]


def _directory_binding(directory, target):
    data = _response(directory, code=(0,))
    require(type(data) is dict and type(data.get("directory_data")) is list, "DIRECTORY_SCHEMA")
    seen, matches, next_order = set(), [], 0

    def walk(nodes, parent=None):
        nonlocal next_order
        require(type(nodes) is list, "DIRECTORY_CHILDREN_SCHEMA")
        for node in nodes:
            require(type(node) is dict and _id(node.get("id")), "DIRECTORY_NODE_ID")
            require(node["id"] not in seen, "DUPLICATE_DIRECTORY_ID")
            seen.add(node["id"])
            flag = node.get("isQuestion", False)
            require(type(flag) is bool, "IS_QUESTION_TYPE")
            children = node.get("children", [])
            require(type(children) is list, "DIRECTORY_CHILDREN_SCHEMA")
            if flag:
                next_order += 1
                require(not children, "QUESTION_HAS_CHILDREN")
                if node["id"] == target["node_id"]:
                    require(parent is not None and parent["id"] == target["lesson_directory_id"], "WRONG_LESSON_DIRECTORY")
                    require(next_order == target["question_order"], "FRONTEND_ORDER_MISMATCH")
                    require("order_in_level" in node and _order(node["order_in_level"]) == next_order, "RAW_ORDER_MISMATCH")
                    matches.append(copy.deepcopy(node))
            else:
                walk(children, node)
    walk(data["directory_data"])
    require(len(matches) == 1, "TARGET_NODE_NOT_FOUND")
    return matches[0]


def _zone_state(response):
    data = _response(response)
    require(type(data) is dict and type(data.get("success")) is bool, "OCR_RESPONSE_SCHEMA")
    if data["success"]:
        require(type(data.get("ocr_result")) is str and type(data.get("rect_ids")) is list and
                all(_id(value) for value in data["rect_ids"]) and len(data["rect_ids"]) == len(set(data["rect_ids"])),
                "OCR_PRESENT_SCHEMA")
        return "present", data["ocr_result"]
    # An explicit known absence is distinct from both error and a present empty value.
    require(json_same(data, ABSENT), "OCR_ABSENCE_NOT_PROVEN")
    return "absent", None


def validate_snapshot(snapshot, target):
    """Bind native node/info/order/frame identity; leave original values untouched."""
    _json(snapshot)
    _json(target)
    require(type(target) is dict and set(target) == set(TARGET_KEYS) and target["book_id"] == BOOK,
            "TARGET_SCOPE")
    require(all(_id(target[key]) for key in ("lesson_directory_id", "node_id", "info_id")) and
            type(target["question_order"]) is int and target["question_order"] > 0, "TARGET_IDENTITY")
    require(type(snapshot) is dict and set(snapshot) == set(SNAPSHOT_KEYS), "SNAPSHOT_KEYS")
    require(type(snapshot["zones"]) is dict and set(snapshot["zones"]) == set(ZONES), "FIVE_NATIVE_ZONES_REQUIRED")
    node = _directory_binding(snapshot["directory"], target)
    all_frames = _response(snapshot["frames"])
    frames = _response(snapshot["annotations"])
    require(type(all_frames) is list and type(frames) is list and bool(frames), "CURRENT_FRAMES_REQUIRED")
    all_ids = []
    for frame in all_frames:
        require(type(frame) is dict and _id(frame.get("rect_id")) and frame.get("file_id") == BOOK, "FRAME_ID_OR_BOOK")
        require(frame["rect_id"] not in all_ids, "DUPLICATE_FRAME_ID")
        all_ids.append(frame["rect_id"])
    selected = [frame for frame in all_frames if frame.get("belong_to_level") == "question_level" and
                _order(frame.get("order_in_level")) == target["question_order"]]
    require(json_same(selected, frames), "FULL_AND_TARGET_FRAMES_DISAGREE")
    zone_frames = {zone: [] for zone in ZONES}
    for frame in frames:
        require(frame.get("directory_id") == target["lesson_directory_id"] and
                frame.get("belong_to_level") == "question_level" and
                _order(frame.get("order_in_level")) == target["question_order"], "FRAME_TARGET_SCOPE")
        if frame.get("type") in zone_frames:
            zone_frames[frame["type"]].append(frame)
    rect_ids = {}
    for zone, rows in zone_frames.items():
        orders = [_order(row.get("image_order_in_annotation_zone"), zero=True) for row in rows]
        require(len(orders) == len(set(orders)), "AMBIGUOUS_ZONE_FRAME_ORDER", zone)
        rect_ids[zone] = [row["rect_id"] for _, row in sorted(zip(orders, rows), key=lambda pair: pair[0])]
        state, _ = _zone_state(snapshot["zones"][zone])
        if state == "present":
            require(bool(rect_ids[zone]) and json_same(snapshot["zones"][zone]["data"]["rect_ids"], rect_ids[zone]),
                    "OCR_RECT_BINDING_MISMATCH", zone)
    info = _response(snapshot["info"])
    require(type(info) is dict and info.get("id") == target["info_id"] and info.get("file_id") == BOOK
            and _order(info.get("order_in_level")) == target["question_order"], "INFO_IDENTITY_MISMATCH")
    require(all(field in info for field in ("tishi", "tilei", "tihao", "updated_at")), "INFO_FIELDS_MISSING")
    return {"node": node, "rect_ids": rect_ids, "info": copy.deepcopy(info)}


def _review(review):
    required = {"text", "source_ref", "source_sha256", "review_ref", "reviewed_text_sha256"}
    require(type(review) is dict and set(review) == required, "REVIEW_SHAPE")
    require(type(review["text"]) is str and all(type(review[key]) is str and bool(review[key].strip())
            for key in ("source_ref", "review_ref")), "REVIEW_SOURCE_REQUIRED")
    require(type(review["source_sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", review["source_sha256"]), "SOURCE_HASH_REQUIRED")
    require(review["reviewed_text_sha256"] == text_digest(review["text"]), "REVIEW_TEXT_HASH_MISMATCH")


def image_references(text):
    """Extract nonempty HTML/Markdown image destinations; never dereference URLs.

    Counts matter: retaining one of two repeated diagrams is still data loss.
    HTML entities are decoded by HTMLParser, as the browser decodes img.src.
    Empty img src and empty Markdown destinations contain no usable reference.
    """
    found = []

    class Images(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag.lower() == "img":
                for name, value in attrs:
                    if name.lower() == "src" and isinstance(value, str) and value.strip():
                        found.append(value.strip())
        handle_startendtag = handle_starttag

    Images(convert_charrefs=True).feed(text)
    for match in re.finditer(r"!\[(?:\\.|[^\]\\])*\]\(\s*", text):
        start = match.end()
        if start >= len(text):
            continue
        if text[start] == "<":
            end = start + 1
            while end < len(text) and (text[end] != ">" or text[end - 1] == "\\"):
                end += 1
            destination = text[start + 1:end] if end < len(text) else ""
        else:
            end, depth = start, 0
            while end < len(text):
                char = text[end]
                if char == "\\" and end + 1 < len(text):
                    end += 2
                    continue
                if char == "(":
                    depth += 1
                elif char == ")":
                    if depth == 0:
                        break
                    depth -= 1
                elif char.isspace() and depth == 0:
                    break
                end += 1
            destination = text[start:end]
        if destination.strip():
            found.append(destination.strip())
    definitions = {}
    for match in re.finditer(r"(?m)^ {0,3}\[([^\]]+)\]:\s*(?:<([^>]+)>|(\S+))", text):
        definitions[" ".join(match[1].split()).casefold()] = match[2] or match[3]
    for match in re.finditer(r"!\[((?:\\.|[^\]\\])*)\](?:\[([^\]]*)\])?(?!\()", text):
        # The inline scanner owns immediate '(...)' forms; regex backtracking
        # must not treat one as an unresolved reference-style image.
        if match.end() < len(text) and text[match.end()] == "(":
            continue
        label = match[2] or match[1]
        key = " ".join(label.split()).casefold()
        if key in definitions:
            found.append(definitions[key])
        elif label.strip():
            found.append("unresolved-markdown-image:" + match[0])
    return Counter(found)


def make_plan(before, target, approved_changes):
    return _make_plan(before, target, approved_changes, protect_images=True)


def _make_plan(before, target, approved_changes, *, protect_images):
    binding = validate_snapshot(before, target)
    require(type(approved_changes) is dict and set(approved_changes) <= set(ZONES), "ZONE_CHANGE_FORBIDDEN")
    expected, changes, submissions = copy.deepcopy(before), [], []
    for zone, review in approved_changes.items():
        _review(review)
        state, old_text = _zone_state(before["zones"][zone])
        text = review["text"]
        if state == "present" and text == old_text:
            continue
        # Clearing is a different destructive protocol operation, never inferred.
        require(bool(text.strip()), "EMPTY_UPDATE_REQUIRES_EXPLICIT_CLEAR_PROTOCOL", zone)
        require(bool(binding["rect_ids"][zone]), "ZONE_HAS_NO_SOURCE_FRAME", zone)
        if state == "present" and protect_images:
            require(not (image_references(old_text) - image_references(text)),
                    "EXISTING_IMAGE_REFERENCE_REMOVAL_FORBIDDEN", zone)
        if state == "present":
            expected["zones"][zone]["data"]["ocr_result"] = text
        else:
            expected["zones"][zone]["data"] = {"rect_ids": copy.deepcopy(binding["rect_ids"][zone]),
                                               "ocr_result": text, "success": True}
        submissions.append({"zone": zone, "ocr_result": text, "rect_ids": copy.deepcopy(binding["rect_ids"][zone]),
                            "question_order": target["question_order"]})
        changes.append({"zone": zone, "before_state": state, "before_text": old_text, "after_text": text,
                        "rect_ids": copy.deepcopy(binding["rect_ids"][zone]), "review": copy.deepcopy(review)})
    payload = None
    if changes:
        payload = {"file_id": BOOK, "target_directory_id": target["lesson_directory_id"],
                   "question_order": target["question_order"], "is_new_question_insertion": False,
                   "insert_after_order": None, "annotations_upsert": [], "annotations_delete_rect_ids": [],
                   "ocr_submissions": submissions, "ocr_delete_zones": [],
                   "question_info": {key: copy.deepcopy(binding["info"][key]) for key in ("tishi", "tilei", "tihao")},
                   "created_by": None}
    stable_identity = {key: target[key] for key in ("book_id", "node_id", "info_id")}
    plan = {"schema": PLAN_SCHEMA, "mode": "existing-question-update" if changes else "no-op",
            "target": copy.deepcopy(target), "before": copy.deepcopy(before), "before_sha256": digest(before),
            "approved_changes": copy.deepcopy(approved_changes), "changes": changes, "expected": expected,
            "expected_sha256": digest(expected), "payload_candidate": payload,
            "payload_template_sha256": digest(payload) if payload is not None else None,
            "ledger_key": "usense-existing-" + digest(stable_identity),
            "ledger_rule": "Stable identity key excludes plan hash/order; unresolved previous intent blocks all new plans",
            "runtime_binding": {"field": "created_by", "required_when_mutating": True,
                                "source": "current authenticated username bound inside page; do not export"},
            "metadata_policy": {"path": ["info", "data", "updated_at"],
                                "rule": "unchanged, or same timestamp format/UTC offset and strictly later; update mode only"},
            "mutation_required": bool(changes), "write_authorized_by_this_module": False}
    plan["plan_sha256"] = digest(plan)
    return plan


def validate_plan(plan):
    require(type(plan) is dict and plan.get("schema") == PLAN_SCHEMA, "PLAN_SCHEMA")
    expected = make_plan(plan["before"], plan["target"], plan["approved_changes"])
    require(json_same(expected, plan), "PLAN_TAMPERED")
    return plan


def validate_recorded_plan(plan):
    """Recompute an already-recorded historical plan, never authorize a new send.

    Old accepted runs predate the image-loss guard. Revision verification must
    inspect that historical evidence, including its defect, without rewriting
    history. New writer input always goes through validate_plan instead.
    """
    require(type(plan) is dict and plan.get("schema") == PLAN_SCHEMA, "PLAN_SCHEMA")
    expected = _make_plan(plan["before"], plan["target"], plan["approved_changes"], protect_images=False)
    require(json_same(expected, plan), "PLAN_TAMPERED")
    return plan


def differences(expected, actual, path=()):
    if type(expected) is not type(actual):
        return [{"path": list(path), "kind": "type", "expected_type": type(expected).__name__, "actual_type": type(actual).__name__}]
    if type(expected) is dict:
        result = []
        if list(expected) != list(actual):
            result.append({"path": list(path), "kind": "object_keys_or_order", "expected_keys": list(expected), "actual_keys": list(actual)})
        for key in expected:
            if key in actual:
                result.extend(differences(expected[key], actual[key], path + (key,)))
        return result
    if type(expected) is list:
        result = []
        if len(expected) != len(actual):
            result.append({"path": list(path), "kind": "array_length", "expected": len(expected), "actual": len(actual)})
        for index, (left, right) in enumerate(zip(expected, actual)):
            result.extend(differences(left, right, path + (index,)))
        return result
    return [] if expected == actual else [{"path": list(path), "kind": "value", "expected": expected, "actual": actual}]


def check_prewrite(plan, fresh):
    validate_plan(plan)
    validate_snapshot(fresh, plan["target"])
    diff = differences(plan["before"], fresh)
    return {"status": "BEFORE_MATCH" if not diff else "BEFORE_CHANGED", "match": not diff,
            "differences": diff, "fresh_sha256": digest(fresh), "plan_sha256": plan["plan_sha256"],
            "mutation_required": plan["mutation_required"], "read_freshness_verified": False}


def compare_readback(plan, after):
    """Full native equality except the single predeclared monotonic info timestamp.

    The caller must independently prove current read context/time, native receipt,
    one send and resource release. This pure result never claims a live save.
    """
    validate_plan(plan)
    return _compare_validated_readback(plan, after)


def compare_recorded_readback(plan, after):
    """Historical evidence check only; cannot make a new plan writable."""
    validate_recorded_plan(plan)
    return _compare_validated_readback(plan, after)


def _compare_validated_readback(plan, after):
    _json(after)
    expected = copy.deepcopy(plan["expected"])
    metadata_changes, metadata_error = [], None
    try:
        old, new = expected["info"]["data"]["updated_at"], after["info"]["data"]["updated_at"]
        if not json_same(old, new) and plan["mutation_required"]:
            require(type(old) is str and type(new) is str, "INFO_TIMESTAMP_TYPE")
            require(re.sub(r"\d", "#", old) == re.sub(r"\d", "#", new), "INFO_TIMESTAMP_FORMAT")
            prior, current = datetime.fromisoformat(old), datetime.fromisoformat(new)
            require(prior.utcoffset() == current.utcoffset() and bool(prior.tzinfo) == bool(current.tzinfo)
                    and current > prior, "INFO_TIMESTAMP_NOT_MONOTONIC")
            expected["info"]["data"]["updated_at"] = new
            metadata_changes.append({"path": ["info", "data", "updated_at"], "before": old, "after": new})
    except (KeyError, TypeError, ValueError) as error:
        metadata_error = {"code": getattr(error, "code", type(error).__name__), "detail": str(error)}
    diff = differences(expected, after)
    match = not diff and metadata_error is None
    return {"status": ("NATIVE_STATE_MATCH" if plan["mutation_required"] else "NO_OP_CONFIRMED") if match else "NATIVE_STATE_MISMATCH",
            "match": match, "differences": diff, "metadata_changes": metadata_changes, "metadata_error": metadata_error,
            "after_sha256": digest(after), "plan_sha256": plan["plan_sha256"], "ledger_key": plan["ledger_key"],
            "receipt_verified": False, "independent_context_verified": False, "live_save_verified": False}
