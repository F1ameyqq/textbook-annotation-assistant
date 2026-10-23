"""Pure Q7 copy-first insert contract for the observed 22-question test book.

No HTTP, browser, files, credentials, ledger mutation or server-ID prediction.
The native values are never normalized. Only the explicit global +1 reindex of
old questions 8..22 is allowed; even old updated_at changes cause HOLD.
Successful pure comparison is necessary but not sufficient for live acceptance:
the caller must prove raw hashes, process/context separation, one send and release.
"""
from __future__ import annotations

import copy
from datetime import datetime
import re
import uuid

from . import update as u

BOOK = u.BOOK
DIRECTORY = "dir-1792063578574-2a6vq8zom"
OLD_Q7_NODE = "1792066417325"
OLD_Q7_INFO = "2110705653289365506"
GLOBAL_KEYS = ("directory", "frames", "source", "page_10", "page_11", "page_12", "page_173")
SUFFIXES = ("annotations", "info") + u.ZONES
SCHEMA = "UsenseQ7CopyFirstInsertPlan/v1"
ROW_KEYS = ("type", "verified", "rect_id", "file_id", "belong_to_level", "order_in_level",
            "image_order_in_annotation_zone", "rect_bbox", "page_index", "image_path",
            "created_at", "updated_at", "parent_rect_id", "directory_id", "content_type",
            "user_id", "is_pre_annotation", "pre_annotations_id")
INFO_KEYS = ("id", "tishi", "tilei", "tixu", "tihao", "file_id", "order_in_level", "created_at", "updated_at")
NODE_KEYS = ("id", "label", "isQuestion", "order_in_level")
# The first real middle-insertion receipt (raw SHA 470b0109c1cc90784d7794ad3f118b2c1cc6389d954c39873e412e435c7eacf3)
# returned this exact second layout. Preserve it verbatim through directory
# comparison; do not sort keys or allow arbitrary permutations/unknown fields.
OBSERVED_INSERTED_NODE_KEYS = ("isQuestion", "order_in_level", "id", "label")
FRAME_KEYS = ("variant-stem", "variant-figures", "variant-choice-A", "variant-choice-B",
              "variant-choice-C", "variant-choice-D", "variant-answer")


def require(ok, code, detail=""):
    u.require(ok, code, detail)


def flat_digest(flat):
    """Flat internal map insertion order is irrelevant; native key order is not."""
    return u.digest({key: flat[key] for key in sorted(flat)})


def _questions(directory):
    data = u._response(directory, code=(0,))
    require(type(data) is dict and type(data.get("directory_data")) is list, "DIRECTORY_SCHEMA")
    result, ids = [], set()

    def walk(nodes, parent=None):
        require(type(nodes) is list, "DIRECTORY_CHILDREN_SCHEMA")
        for node in nodes:
            require(type(node) is dict and u._id(node.get("id")) and node["id"] not in ids,
                    "DIRECTORY_NODE_ID_OR_DUPLICATE")
            ids.add(node["id"])
            flag = node.get("isQuestion", False)
            require(type(flag) is bool, "IS_QUESTION_TYPE")
            children = node.get("children", [])
            require(type(children) is list, "DIRECTORY_CHILDREN_SCHEMA")
            if flag:
                require(not children and parent is not None, "QUESTION_DIRECTORY_SHAPE")
                number = len(result) + 1
                require(u._order(node.get("order_in_level")) == number and
                        u._order(node.get("label")) == number, "GLOBAL_DIRECTORY_ORDER")
                result.append((node, parent))
            else:
                walk(children, node["id"])
    walk(data["directory_data"])
    return result


def _validate_full(flat, count):
    u._json(flat)
    keys = set(GLOBAL_KEYS) | {f"q{i}_{suffix}" for i in range(1, count + 1) for suffix in SUFFIXES}
    require(type(flat) is dict and set(flat) == keys, "FULL_CAPTURE_KEYS", f"expected {len(keys)} raw responses")
    for key in GLOBAL_KEYS:
        u._response(flat[key])
    nodes = _questions(flat["directory"])
    require(len(nodes) == count, "GLOBAL_QUESTION_COUNT")
    identities, info_ids = [], set()
    for i, (node, parent) in enumerate(nodes, 1):
        info = u._response(flat[f"q{i}_info"])
        require(type(info) is dict and u._id(info.get("id")) and info["id"] not in info_ids,
                "INFO_ID_MISSING_OR_DUPLICATE")
        info_ids.add(info["id"])
        target = {"book_id": BOOK, "lesson_directory_id": parent, "node_id": node["id"],
                  "info_id": info["id"], "question_order": i}
        u.validate_snapshot(u.from_captured_map(flat, f"q{i}_"), target)
        identities.append(target)
    all_frames = flat["frames"]["data"]
    # Every frame in this observed book belongs to exactly one captured question.
    require(all(row.get("belong_to_level") == "question_level" and
                1 <= u._order(row["order_in_level"]) <= count for row in all_frames), "UNBOUND_GLOBAL_FRAME")
    return identities


def load_full_capture(captured_map, count=22):
    require(type(count) is int and count in (22, 23), "FULL_BOOK_COUNT_SCOPE")
    _validate_full(captured_map, count)
    return copy.deepcopy(captured_map)


def _hash(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _source_page_bindings(frames, source_map):
    """Membership alone cannot bind a source image to its declared viewer page."""
    pages = {}
    for frame in frames:
        page = frame["viewer_page"]
        source = frame["source"]
        identity = (source["path"], source["sha256"])
        require(page not in pages or pages[page] == identity,
                "ONE_SOURCE_PER_VIEWER_PAGE_REQUIRED")
        pages[page] = identity
    require(set(pages) == {10, 173} and len({ref[0] for ref in pages.values()}) == 2
            and len({ref[1] for ref in pages.values()}) == 2
            and {path: digest for path, digest in pages.values()} == source_map,
            "DISTINCT_SOURCE_PAGE_BINDINGS_REQUIRED")


def _approved_payload(approved, before):
    require(type(approved) is dict, "APPROVED_NEW_CONTENT_REQUIRED")
    for field in ("candidate", "review", "crop_evidence"):
        require(u._id(approved.get(field + "_ref")) and _hash(approved.get(field + "_sha256")),
                "APPROVAL_FILE_REFERENCE_REQUIRED", field)
    sources = approved.get("source_evidence")
    require(type(sources) is list and len(sources) == 2 and
            all(type(row) is dict and set(row) == {"path", "sha256"} and u._id(row["path"]) and
                _hash(row["sha256"]) for row in sources) and len({row["path"] for row in sources}) == 2,
            "TWO_SOURCE_EVIDENCE_REFERENCES_REQUIRED")
    source_map = {row["path"]: row["sha256"] for row in sources}
    candidate = approved.get("candidate")
    require(type(candidate) is dict and candidate.get("schema") == "Q7FinalSevenFrameContentCandidate/v1" and
            candidate.get("logical_owner") == "variant" and candidate.get("book_id") == BOOK and
            candidate.get("target_directory_id") == DIRECTORY, "EXACT_VARIANT_CANDIDATE_REQUIRED")
    target = candidate.get("target", {})
    require(all(key in target and target[key] is None for key in ("node_id", "info_id", "question_order")) and
            target.get("proposed_insert_after_existing_node_id") == OLD_Q7_NODE and
            type(target.get("proposed_insert_after_existing_order")) is int and
            target["proposed_insert_after_existing_order"] == 7, "NO_PRESUMED_NEW_SERVER_IDENTITY")
    frames = candidate.get("frames")
    require(type(frames) is list and [row.get("key") for row in frames] == list(FRAME_KEYS), "EXACT_SEVEN_FRAME_LAYOUT")
    old_ids = {row["rect_id"] for row in before["frames"]["data"]}
    new_ids, rows = set(), []
    zone_layout = [("question", 0, "text"), ("question", 1, "image"), ("choice", 0, "text"),
                   ("choice", 1, "text"), ("choice", 2, "text"), ("choice", 3, "text"), ("answer", 0, "text")]
    for frame, layout in zip(frames, zone_layout):
        rect = frame.get("planned_rect_id")
        require(type(rect) is str, "FRESH_RECT_UUID_REQUIRED")
        try:
            valid_uuid = str(uuid.UUID(rect)) == rect
        except ValueError:
            valid_uuid = False
        require(valid_uuid and rect not in old_ids and rect not in new_ids, "FRESH_RECT_UUID_REQUIRED")
        new_ids.add(rect)
        require(u.json_same([frame.get("zone"), frame.get("image_order_in_annotation_zone"), frame.get("content_type")], list(layout)),
                "FRAME_ZONE_LAYOUT")
        bbox, dimensions = frame.get("bbox"), frame.get("source_dimensions")
        require(type(bbox) is list and len(bbox) == 4 and all(type(v) is int for v in bbox) and
                type(dimensions) is list and len(dimensions) == 2 and all(type(v) is int for v in dimensions) and
                0 <= bbox[0] < bbox[2] <= dimensions[0] and 0 <= bbox[1] < bbox[3] <= dimensions[1], "SOURCE_BOUNDS")
        require(frame.get("rect_bbox") == ",".join(map(str, bbox)), "BBOX_SERIALIZATION")
        page = frame.get("viewer_page")
        require(type(page) is int and page == (173 if layout[0] == "answer" else 10) and
                type(frame.get("page_index")) is int and frame["page_index"] == page, "FRAME_SOURCE_PAGE")
        x1, y1, x2, y2 = bbox
        url = (f"https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com/upload_images/{BOOK}/"
               f"{BOOK}_page_{page-1}.jpg?x-oss-process=image/crop,x_{x1},y_{y1},w_{x2-x1},h_{y2-y1}")
        require(frame.get("image_path") == frame.get("hosted_image_url") == url, "EXACT_SOURCE_CROP_URL")
        source, crop, fetch = frame.get("source", {}), frame.get("crop", {}), frame.get("fetch_evidence", {})
        require(source_map.get(source.get("path")) == source.get("sha256") == frame.get("source_sha256") and
                _hash(source.get("sha256")), "SOURCE_EVIDENCE_BINDING")
        require(fetch.get("status") == "FETCHED_CROP" and type(fetch.get("http_status")) is int and
                fetch["http_status"] == 200 and fetch.get("url") == url and
                u.json_same(fetch.get("bbox"), bbox) and u.json_same(fetch.get("dimensions"), [x2-x1, y2-y1]) and
                fetch.get("source_sha256") == source["sha256"] and
                fetch.get("sha256") == crop.get("sha256") == frame.get("crop_sha256") and
                _hash(crop.get("sha256")), "VERIFIED_CROP_EVIDENCE_REQUIRED")
        rows.append({"rect_id": rect, "type": layout[0], "belong_to_level": "question_level", "order_in_level": "23",
                     "image_order_in_annotation_zone": layout[1], "rect_bbox": frame["rect_bbox"], "page_index": page,
                     "image_path": url, "parent_rect_id": None, "directory_id": DIRECTORY, "content_type": layout[2],
                     "user_id": None, "is_pre_annotation": False, "pre_annotations_id": None})
    _source_page_bindings(frames, source_map)
    zones = candidate.get("zone_values")
    require(type(zones) is dict and set(zones) == {"question", "choice", "answer"}, "THREE_APPROVED_ZONES_REQUIRED")
    require(all(type(text) is str and bool(text.strip()) and candidate.get("zone_text_sha256", {}).get(zone) ==
                u.text_digest(text) for zone, text in zones.items()), "APPROVED_TEXT_HASH")
    require(zones["answer"] == "B" and [line[:2] for line in zones["choice"].splitlines()] == ["A.", "B.", "C.", "D."],
            "VARIANT_SINGLE_CHOICE_CONTENT")
    require(u.image_references(zones["question"]) == {frames[1]["image_path"]: 1}, "EXACT_ONE_VARIANT_FIGURE_IN_BODY")
    info = {"tishi": "xuanze", "tilei": None, "tihao": None}
    require(u.json_same(candidate.get("question_info"), info), "NEW_SINGLE_CHOICE_METADATA")
    submissions = [{"zone": zone, "ocr_result": zones[zone],
                    "rect_ids": [row["rect_id"] for row in rows if row["type"] == zone], "question_order": None}
                   for zone in ("question", "choice", "answer")]
    return {"file_id": BOOK, "target_directory_id": DIRECTORY, "question_order": None,
            "is_new_question_insertion": True, "insert_after_order": 7, "annotations_upsert": rows,
            "annotations_delete_rect_ids": [], "ocr_submissions": submissions, "ocr_delete_zones": [],
            "question_info": info, "created_by": None}


def make_insert_plan(before, insert_after=7, parent_directory_id=DIRECTORY, payload_candidate=None, approved_new_content=None):
    require(type(insert_after) is int and insert_after == 7 and parent_directory_id == DIRECTORY, "FIXED_COPY_FIRST_SCOPE")
    identities = _validate_full(before, 22)
    require(identities[6] == {"book_id": BOOK, "lesson_directory_id": DIRECTORY, "node_id": OLD_Q7_NODE,
                              "info_id": OLD_Q7_INFO, "question_order": 7}, "OLD_Q7_STABLE_BINDING")
    require(len(before["frames"]["data"]) == 68, "OBSERVED_68_FRAME_BASELINE_REQUIRED")
    require(all(tuple(row) == ROW_KEYS for row in before["frames"]["data"]), "OBSERVED_FRAME_SCHEMA_CHANGED")
    require(all(tuple(before[f"q{i}_info"]["data"]) == INFO_KEYS for i in range(1, 23)), "OBSERVED_INFO_SCHEMA_CHANGED")
    expected = _approved_payload(approved_new_content, before)
    require(u.json_same(payload_candidate, expected), "PAYLOAD_NOT_EXACT_APPROVED_SEVEN_FRAME_INSERT")
    ledger_key = "book-46007447-node-1792066417325-info-2110705653289365506-split-variant-copy-first"
    plan = {"schema": SCHEMA, "operation": "Q7_COPY_FIRST_VARIANT_INSERT", "book_id": BOOK,
            "before_count": 22, "after_count": 23, "insert_after_order": 7, "new_order": 8,
            "old_q7_target": copy.deepcopy(identities[6]), "old_identities": identities,
            "before_full": copy.deepcopy(before), "before_sha256": flat_digest(before),
            "payload_candidate": copy.deepcopy(payload_candidate), "approved_new_content": copy.deepcopy(approved_new_content),
            "ledger_key": ledger_key, "automatic_retry_allowed": False, "phase2_permitted": False,
            "old_metadata_changes_allowed": []}
    plan["plan_sha256"] = u.digest(plan)
    return plan


def validate_insert_plan(plan):
    require(type(plan) is dict and plan.get("schema") == SCHEMA, "INSERT_PLAN_SCHEMA")
    rebuilt = make_insert_plan(plan.get("before_full"), plan.get("insert_after_order"),
                               plan.get("old_q7_target", {}).get("lesson_directory_id"),
                               plan.get("payload_candidate"), plan.get("approved_new_content"))
    require(u.json_same(plan, rebuilt), "INSERT_PLAN_TAMPERED")
    return {"ok": True, "status": "VALID_COPY_FIRST_INSERT_PLAN", "plan_sha256": plan["plan_sha256"]}


def check_prewrite(plan, fresh):
    validate_insert_plan(plan)
    _validate_full(fresh, 22)
    require(set(fresh) == set(plan["before_full"]) and
            all(u.json_same(fresh[key], plan["before_full"][key]) for key in fresh), "STALE_FULL_BOOK_BEFORE_STATE")
    return {"ok": True, "status": "ALL161_FRESH_RESPONSES_EXACT", "response_count": len(fresh),
            "before_sha256": flat_digest(fresh)}


def decode_receipt(plan, raw_receipt):
    validate_insert_plan(plan)
    require(type(raw_receipt) is dict and set(raw_receipt) == {"code", "message", "data"}, "INSERT_RECEIPT_ENVELOPE_UNKNOWN")
    data = u._response(raw_receipt, code=(0,))
    require(type(data) is dict and set(data) == {"inserted", "question_order", "inserted_question_node", "success", "append_at_global_end"},
            "INSERT_RECEIPT_DATA_UNKNOWN")
    require(data["inserted"] is True and data["success"] is True and data["append_at_global_end"] is False and
            type(data["question_order"]) is int and data["question_order"] == 8, "INSERT_RECEIPT_FLAGS_OR_ORDER")
    node = data["inserted_question_node"]
    old_nodes = {target["node_id"] for target in plan["old_identities"]}
    require(type(node) is dict and tuple(node) in (NODE_KEYS, OBSERVED_INSERTED_NODE_KEYS) and u._id(node.get("id")) and node["id"] not in old_nodes and
            node["isQuestion"] is True and type(node["order_in_level"]) is str and node["order_in_level"] == "8" and
            type(node["label"]) is str and node["label"] == "8", "EXACT_NEW_SERVER_NODE_REQUIRED")
    return {"ok": True, "status": "VALID_INSERT_RECEIPT", "question_order": 8,
            "inserted_question_node": copy.deepcopy(node), "receipt_sha256": u.digest(raw_receipt)}


def _shift_value(value):
    number = u._order(value) + 1
    return str(number) if type(value) is str else number


def _shift_frame(row):
    expected = copy.deepcopy(row)
    if u._order(row["order_in_level"]) > 7:
        expected["order_in_level"] = _shift_value(row["order_in_level"])
    return expected


def _expected_directory(before, new_node):
    expected = copy.deepcopy(before)
    inserted = 0

    def walk(nodes):
        nonlocal inserted
        for node in list(nodes):
            if node.get("isQuestion") is True:
                if u._order(node["order_in_level"]) > 7:
                    node["order_in_level"] = _shift_value(node["order_in_level"])
                    node["label"] = _shift_value(node["label"])
                if node["id"] == OLD_Q7_NODE:
                    nodes.insert(nodes.index(node) + 1, copy.deepcopy(new_node))
                    inserted += 1
            else:
                walk(node.get("children", []))
    walk(expected["data"]["directory_data"])
    require(inserted == 1, "Q7_INSERT_LOCATION_AMBIGUOUS")
    return expected


def _new_timestamp_pair(data):
    first, second = data.get("created_at"), data.get("updated_at")
    if type(first) is not str or type(second) is not str or first != second:
        return False
    try:
        value = datetime.fromisoformat(first)
        return "T" in first and value.year >= 2026
    except ValueError:
        return False


def compare_insert_readback(plan, after, receipt, *, runtime_actor_hashes=None):
    """Pure acceptance; returns ok False on any unsupported native delta.

    Old metadata is immutable, including timestamps. New timestamps must be valid
    equal creation/update values in the observed native schema; actual clock and
    process evidence is deliberately the caller's responsibility. No retries.
    """
    validate_insert_plan(plan)
    decoded = decode_receipt(plan, receipt)
    differences, checks = [], []

    def check(ok, path, reason="VALUE_MISMATCH"):
        checks.append({"path": path, "ok": bool(ok)})
        if not ok:
            differences.append({"path": path, "reason": reason})

    def same(expected, actual, path):
        check(u.json_same(expected, actual), path)
        if type(expected) is dict and type(actual) is dict:
            if "updated_at" in expected and expected.get("updated_at") != actual.get("updated_at"):
                differences.append({"path": path + ".updated_at", "reason": "UNAPPROVED_OLD_METADATA_CHANGE"})
            if "data" in expected and type(expected["data"]) is dict and type(actual.get("data")) is dict:
                if "updated_at" in expected["data"] and expected["data"]["updated_at"] != actual["data"].get("updated_at"):
                    differences.append({"path": path + ".data.updated_at", "reason": "UNAPPROVED_OLD_METADATA_CHANGE"})

    before = plan["before_full"]
    try:
        identities = _validate_full(after, 23)
    except (ValueError, KeyError, TypeError) as error:
        return {"schema": "UsenseCopyFirstInsertReadback/v1", "ok": False, "status": "HOLD",
                "plan_sha256": plan["plan_sha256"], "differences": [{"path": "after", "reason": str(error)}],
                "phase2_permitted": False, "automatic_retry_allowed": False}
    require(type(runtime_actor_hashes) is dict and set(runtime_actor_hashes) ==
            {"runtime_actor_sha256", "runtime_user_id_sha256"} and all(_hash(v) for v in runtime_actor_hashes.values()),
            "RUNTIME_ACTOR_HASH_PROOF_REQUIRED")
    new_node = decoded["inserted_question_node"]
    same(_expected_directory(before["directory"], new_node), after["directory"], "directory")
    for key in GLOBAL_KEYS[2:]:
        same(before[key], after[key], key)
    old_frames = before["frames"]["data"]
    old_ids = {row["rect_id"] for row in old_frames}
    payload = plan["payload_candidate"]
    new_rows = payload["annotations_upsert"]
    new_ids = {row["rect_id"] for row in new_rows}
    actual_frames = after["frames"]["data"]
    check(len(actual_frames) == 75 and {row["rect_id"] for row in actual_frames} == old_ids | new_ids,
          "frames.identities", "EXACT_68_OLD_PLUS_7_NEW_REQUIRED")
    expected_old_global = copy.deepcopy(before["frames"])
    expected_old_global["data"] = [_shift_frame(row) for row in old_frames]
    filtered_after = copy.deepcopy(after["frames"])
    filtered_after["data"] = [row for row in actual_frames if row["rect_id"] in old_ids]
    same(expected_old_global, filtered_after, "frames.old_subsequence")
    actual_by_id = {row["rect_id"]: row for row in actual_frames}
    # Report every old timestamp delta separately, never hide it in a global diff.
    for old in old_frames:
        actual = actual_by_id.get(old["rect_id"])
        if actual is not None and actual.get("updated_at") != old.get("updated_at"):
            check(False, "frames." + old["rect_id"] + ".updated_at", "UNAPPROVED_OLD_METADATA_CHANGE")
    for i, target in enumerate(plan["old_identities"], 1):
        new_i = i + (i > 7)
        expected_target = copy.deepcopy(target)
        expected_target["question_order"] = new_i
        same(expected_target, identities[new_i - 1], f"q{i}.stable_identity_at_{new_i}")
        for suffix in SUFFIXES:
            expected = copy.deepcopy(before[f"q{i}_{suffix}"])
            if suffix == "annotations":
                expected["data"] = [_shift_frame(row) for row in expected["data"]]
            elif suffix == "info" and i > 7:
                expected["data"]["order_in_level"] = _shift_value(expected["data"]["order_in_level"])
            same(expected, after[f"q{new_i}_{suffix}"], f"q{i}->{new_i}.{suffix}")
    new_identity = identities[7]
    check(new_identity["node_id"] == new_node["id"] and new_identity["lesson_directory_id"] == DIRECTORY and
          new_identity["info_id"] not in {target["info_id"] for target in plan["old_identities"]},
          "q8.new_server_identity", "NEW_IDS_MUST_BE_UNIQUE_AND_RECEIPT_BOUND")
    new_annotations = copy.deepcopy(before["q7_annotations"])
    new_annotations["data"] = [row for row in actual_frames if row["rect_id"] in new_ids]
    same(new_annotations, after["q8_annotations"], "q8.annotations_envelope_and_global_binding")
    for row in new_rows:
        actual = actual_by_id.get(row["rect_id"], {})
        check(tuple(actual) == ROW_KEYS, "new_frame." + row["rect_id"] + ".schema", "UNKNOWN_NEW_FRAME_SCHEMA")
        expected = {}
        for key in ROW_KEYS:
            if key in row:
                expected[key] = copy.deepcopy(row[key])
            elif key == "file_id":
                expected[key] = BOOK
            elif key == "verified":
                expected[key] = 0
            else:
                expected[key] = actual.get(key)
        expected["order_in_level"] = "8"
        expected["user_id"] = actual.get("user_id")
        same(expected, actual, "new_frame." + row["rect_id"])
        check(type(actual.get("user_id")) is str and
              u.text_digest(actual["user_id"]) == runtime_actor_hashes["runtime_user_id_sha256"],
              "new_frame." + row["rect_id"] + ".user_id", "RUNTIME_USER_ID_HASH_MISMATCH")
        check(_new_timestamp_pair(actual), "new_frame." + row["rect_id"] + ".timestamps", "NEW_CREATION_METADATA_UNKNOWN")
    info = after["q8_info"]["data"]
    expected_info = {"id": new_identity["info_id"], "tishi": "xuanze", "tilei": None, "tixu": None,
                     "tihao": None, "file_id": BOOK, "order_in_level": "8", "created_at": info.get("created_at"),
                     "updated_at": info.get("updated_at")}
    info_response = copy.deepcopy(before["q7_info"])
    info_response["data"] = expected_info
    same(info_response, after["q8_info"], "q8.info")
    check(_new_timestamp_pair(info), "q8.info.timestamps", "NEW_CREATION_METADATA_UNKNOWN")
    submissions = {row["zone"]: row for row in payload["ocr_submissions"]}
    for zone in u.ZONES:
        # The exact native success/absence shape was captured before this write.
        template = copy.deepcopy(before["q7_" + zone])
        if zone in submissions:
            submission = submissions[zone]
            template["data"] = {"rect_ids": submission["rect_ids"], "ocr_result": submission["ocr_result"], "success": True}
        else:
            template["data"] = copy.deepcopy(u.ABSENT)
        same(template, after["q8_" + zone], "q8." + zone)
    return {"schema": "UsenseCopyFirstInsertReadback/v1", "ok": not differences,
            "status": "ACCEPTED_COPY_FIRST_INSERT_PRESERVATION" if not differences else "HOLD",
            "plan_sha256": plan["plan_sha256"], "before_sha256": plan["before_sha256"], "after_sha256": flat_digest(after),
            "receipt_sha256": decoded["receipt_sha256"], "new_identity": copy.deepcopy(new_identity),
            "checks": checks, "differences": differences, "old_q7_preserved": all(
                u.json_same(before["q7_" + suffix], after["q7_" + suffix]) for suffix in SUFFIXES),
            "old_question_count": 22, "new_question_count": 1, "expected_frame_count": 75,
            "old_metadata_changes_allowed": [], "phase2_permitted": False, "automatic_retry_allowed": False,
            "receipt_verified": True, "independent_context_verified": False, "live_save_verified": False,
            "new_metadata_policy": "Observed schema only; created_at equals updated_at; runtime user id hash bound. Caller verifies actual clock/process evidence."}
