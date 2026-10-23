"""Pure, finite A28 lesson-two insertion and preservation contract.

Only Q6, Q7, Q8 and Q8 variant may be added, in that order. The complete
directory and frame inventory, current three source pages, and seven responses
for the unique old suffix are bound before every send. Other old OCR is outside
this minimal capture; its accepted predecessor evidence is a caller obligation.
No filesystem, browser, network, ledger mutation, retry or server-ID prediction.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import re
import uuid

from . import insertion as ins, update as u
from .config import endpoints

BOOK = u.BOOK
DIRECTORY = "dir-1792063578574-lvqkxdluj"
LESSON = "第2课时 勾股定理的验证及简单应用"
OLD_PARENT = "dir-1792063578574-2a6vq8zom"
TAIL_PARENT = "dir-1792063578574-g0n3ulsni"
TAIL_NODE = "1792148510557"
TAIL_INFO = "2111049977118109698"
OLD_NODES = ("1792064001811", "1792064044446", "1792065598862", "1792065892243",
             "1792066005626", "1792066259991", "1792066417325", "1792695084803",
             "1792066451314", "1792066484290", "1792066542156", "1792066591590",
             "1792066621924", "1792066675186", "1792066698921", "1792066733957",
             "1792066770075", "1792066823781", "1792066869052", "1792067036007",
             "1792067074506", "1792067091596")
LOGICAL_KEYS = ("q6", "q7", "q8", "q8-variant")
FRAME_TOTALS = (76, 80, 84, 87, 90)
GLOBAL_KEYS = ("directory", "frames", "source", "page_12", "page_13", "page_173")
SUFFIXES = ins.SUFFIXES
SCHEMA = "A28LessonInsertPlan/v1"
NATIVE_TZ = timezone(timedelta(hours=8))
SOURCE_DIMENSIONS = {12: [1220, 1692], 13: [1219, 1691], 173: [1148, 1621]}
SOURCE_SHA256 = {12: "774c8a29bbdcaa35fcb88479129d2b523ec077edfa4e0ac3db6f11e9bcae9b87",
                 13: "997b37d35fca57f73ab71e53f6721be145d10c436deab5fab38bf1ae0d31dc1e",
                 173: "a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be"}
ZONE_ORDERS = (("rect_ids", "ocr_result", "success"), ("success", "ocr_result", "rect_ids"))
require = u.require
flat_digest = ins.flat_digest


def full_endpoints(plan=None, tail_order=23):
    """Thirteen before responses; callers add new_order's seven for readback."""
    if plan is not None:
        require(type(plan) is dict and plan.get("schema") == SCHEMA, "LESSON_INSERT_PLAN_SCHEMA")
        tail_order = plan.get("new_order")
    require(type(tail_order) is int and 23 <= tail_order <= 27, "TAIL_ORDER_SCOPE")
    return endpoints((tail_order,), (12, 13, 173), source=True)


def _directory_nodes(response):
    nodes = {}

    def walk(items):
        for node in items:
            nodes[node["id"]] = node
            walk(node.get("children", []))
    walk(response["data"]["directory_data"])
    return nodes


def _source_url(page):
    return (f"https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com/upload_images/"
            f"{BOOK}/{BOOK}_page_{page - 1}.jpg")


def _layout(index):
    rows = [("question", "text", 0), ("question", "image", 1)]
    if index < 2:
        rows.append(("choice", "text", 0))
    return rows + [("answer", "text", 0)]


def _validate_full(flat, count, read_orders):
    u._json(flat)
    require(type(count) is int and 23 <= count <= 27, "LESSON_COUNT_SCOPE")
    expected_keys = set(GLOBAL_KEYS) | {f"q{i}_{s}" for i in read_orders for s in SUFFIXES}
    require(type(flat) is dict and set(flat) == expected_keys, "FULL_CAPTURE_KEYS")
    for key in GLOBAL_KEYS:
        u._response(flat[key], code=(0,))
    questions = ins._questions(flat["directory"])
    require(len(questions) == count, "GLOBAL_QUESTION_COUNT")
    require([(n["id"], p) for n, p in questions[:22]] == [(n, OLD_PARENT) for n in OLD_NODES],
            "ACCEPTED_22_NODE_BINDING_CHANGED")
    require(questions[-1][0]["id"] == TAIL_NODE and questions[-1][1] == TAIL_PARENT,
            "UNIQUE_OLD_SUFFIX_REQUIRED")
    all_nodes = _directory_nodes(flat["directory"])
    lesson = all_nodes.get(DIRECTORY, {})
    children = lesson.get("children")
    require(lesson.get("label") == LESSON and type(children) is list and len(children) == count - 23 and
            u.json_same(children, [n for n, _ in questions[22:-1]]) and
            all(p == DIRECTORY for _, p in questions[22:-1]), "EXACT_LESSON_PRIOR_CHILDREN_REQUIRED")
    frames = u._response(flat["frames"])
    require(type(frames) is list and len(frames) == FRAME_TOTALS[count - 23], "EXACT_FRAME_COUNT_REQUIRED")
    ids = set()
    for frame in frames:
        require(type(frame) is dict and tuple(frame) == ins.ROW_KEYS and u._id(frame.get("rect_id")) and
                frame["rect_id"] not in ids and frame["file_id"] == BOOK and
                frame["belong_to_level"] == "question_level", "GLOBAL_FRAME_SCHEMA_OR_ID")
        ids.add(frame["rect_id"])
        order = u._order(frame["order_in_level"])
        require(1 <= order <= count and frame["directory_id"] == questions[order - 1][1], "GLOBAL_FRAME_SCOPE")
    require(len([f for f in frames if u._order(f["order_in_level"]) == count]) == 2,
            "EXACT_TWO_OLD_TAIL_FRAMES")
    for index in range(count - 23):
        selected = [f for f in frames if u._order(f["order_in_level"]) == 23 + index]
        require(all(type(f["image_order_in_annotation_zone"]) is int for f in selected), "PRIOR_FRAME_ORDER_TYPE")
        actual = sorted((f["type"], f["content_type"], f["image_order_in_annotation_zone"]) for f in selected)
        require(actual == sorted(_layout(index)), "PRIOR_INSERT_FRAME_LAYOUT")
    source = u._response(flat["source"])
    require(type(source) is dict and source.get("file_id") == BOOK and source.get("source") == "legacy_db" and
            type(source.get("total_pages")) is int and source["total_pages"] == 214, "CURRENT_SOURCE_BINDING")
    for page in (12, 13, 173):
        data = u._response(flat[f"page_{page}"])
        require(type(data) is dict and data.get("file_id") == BOOK and data.get("source") == "legacy_db" and
                type(data.get("pages")) is list and len(data["pages"]) == 1, "CURRENT_PAGE_SCHEMA")
        native = data["pages"][0]
        require(type(native) is dict and native.get("image") == _source_url(page) and
                type(native.get("page_index")) is int and native["page_index"] == page - 1,
                "CURRENT_PAGE_SOURCE_URL")
    identities = []
    for order in read_orders:
        node, parent = questions[order - 1]
        info = u._response(flat[f"q{order}_info"])
        require(type(info) is dict and tuple(info) == ins.INFO_KEYS and u._id(info.get("id")), "INFO_SCHEMA")
        target = {"book_id": BOOK, "lesson_directory_id": parent, "node_id": node["id"],
                  "info_id": info["id"], "question_order": order}
        u.validate_snapshot(u.from_captured_map(flat, f"q{order}_"), target)
        if order == count:
            require(info["id"] == TAIL_INFO, "OLD_TAIL_INFO_BINDING")
        identities.append(target)
    return questions, identities


def _approved_payload(candidate, approved, before, index):
    require(type(approved) is dict and set(approved) == {
        "candidate_ref", "candidate_sha256", "review_ref", "review_sha256", "crop_evidence_ref",
        "crop_evidence_sha256", "source_evidence", "candidate"}, "APPROVAL_SHAPE")
    for field in ("candidate", "review", "crop_evidence"):
        require(u._id(approved.get(field + "_ref")) and ins._hash(approved.get(field + "_sha256")),
                "APPROVAL_FILE_REFERENCE_REQUIRED")
    require(type(candidate) is dict and u.json_same(candidate, approved["candidate"]), "CANDIDATE_APPROVAL_MISMATCH")
    require(candidate.get("schema") == "A28LessonQuestionCandidate/v1" and candidate.get("book_id") == BOOK and
            candidate.get("logical_key") == LOGICAL_KEYS[index] and candidate.get("semantic_lesson") == LESSON and
            candidate.get("target_directory_id") == DIRECTORY and type(candidate.get("printed_question")) is int and
            candidate["printed_question"] == (6, 7, 8, 8)[index] and type(candidate.get("variant")) is bool and
            candidate["variant"] is (index == 3), "EXACT_A28_CANDIDATE_SCOPE")
    require(u.json_same(candidate.get("review"), {"path": approved["review_ref"], "sha256": approved["review_sha256"]}),
            "CANDIDATE_REVIEW_BINDING")
    info = {"tishi": "xuanze" if index < 2 else "wenda", "tilei": None, "tihao": None}
    require(u.json_same(candidate.get("question_info"), info), "EXACT_NATIVE_QUESTION_TYPE")
    zones = candidate.get("zone_values")
    zone_names = ("question", "choice", "answer") if index < 2 else ("question", "answer")
    require(type(zones) is dict and tuple(zones) == zone_names and
            all(type(text) is str and bool(text.strip()) for text in zones.values()), "EXACT_NONEMPTY_ZONE_VALUES")
    hashes = candidate.get("zone_text_sha256")
    require(type(hashes) is dict and set(hashes) == set(zone_names) and
            all(hashes[zone] == u.text_digest(zones[zone]) for zone in zone_names), "APPROVED_TEXT_HASH")
    frames = candidate.get("frames")
    require(type(frames) is list and len(frames) == len(_layout(index)) and
            all(type(frame) is dict and u._id(frame.get("key")) for frame in frames) and
            len({frame["key"] for frame in frames}) == len(frames), "EXACT_A28_FRAME_LAYOUT")
    sources = approved["source_evidence"]
    require(type(sources) is list and 2 <= len(sources) <= 3 and all(type(source) is dict and
            set(source) == {"path", "sha256"} and u._id(source["path"]) and ins._hash(source["sha256"])
            for source in sources) and len({source["path"] for source in sources}) == len(sources),
            "SOURCE_EVIDENCE_REFERENCES")
    source_map = {source["path"]: source["sha256"] for source in sources}
    old_ids = {frame["rect_id"] for frame in before["frames"]["data"]}
    new_ids, used_sources, rows = set(), set(), []
    for frame, (zone, content, image_order) in zip(frames, _layout(index)):
        rect = frame.get("planned_rect_id")
        try:
            valid_uuid = type(rect) is str and str(uuid.UUID(rect)) == rect
        except (ValueError, AttributeError):
            valid_uuid = False
        require(valid_uuid and rect not in old_ids and rect not in new_ids, "FRESH_RECT_UUID_REQUIRED")
        new_ids.add(rect)
        require(u.json_same([frame.get("zone"), frame.get("content_type"), frame.get("image_order_in_annotation_zone")],
                            [zone, content, image_order]), "EXACT_FRAME_ZONE_LAYOUT")
        page = frame.get("viewer_page")
        require(type(page) is int and page == (173 if zone == "answer" else 12 if index < 2 else 13), "FRAME_SOURCE_PAGE")
        dimensions, bbox = frame.get("source_dimensions"), frame.get("bbox")
        require(u.json_same(dimensions, SOURCE_DIMENSIONS[page]) and type(bbox) is list and len(bbox) == 4 and
                all(type(v) is int for v in bbox) and 0 <= bbox[0] < bbox[2] <= dimensions[0] and
                0 <= bbox[1] < bbox[3] <= dimensions[1], "SOURCE_BOUNDS")
        source = frame.get("source")
        require(type(source) is dict and set(source) == {"path", "sha256"} and
                source_map.get(source.get("path")) == source.get("sha256") == SOURCE_SHA256[page],
                "SOURCE_EVIDENCE_BINDING")
        used_sources.add(source["path"])
        x1, y1, x2, y2 = bbox
        url = _source_url(page) + f"?x-oss-process=image/crop,x_{x1},y_{y1},w_{x2-x1},h_{y2-y1}"
        require(frame.get("image_path") == url, "EXACT_SOURCE_CROP_URL")
        rows.append({"rect_id": rect, "type": zone, "belong_to_level": "question_level",
                     "order_in_level": str(24 + index), "image_order_in_annotation_zone": image_order,
                     "rect_bbox": ",".join(map(str, bbox)), "page_index": page, "image_path": url,
                     "parent_rect_id": None, "directory_id": DIRECTORY, "content_type": content,
                     "user_id": None, "is_pre_annotation": False, "pre_annotations_id": None})
    require(used_sources == set(source_map), "UNUSED_SOURCE_EVIDENCE")
    require(u.image_references(zones["question"]) == {frames[1]["image_path"]: 1} and
            all(not u.image_references(zones[zone]) for zone in zone_names if zone != "question"),
            "EXACT_CANDIDATE_FIGURE_REFERENCE")
    return {"file_id": BOOK, "target_directory_id": DIRECTORY, "question_order": None,
            "is_new_question_insertion": True, "insert_after_order": 22 + index,
            "annotations_upsert": rows, "annotations_delete_rect_ids": [],
            "ocr_submissions": [{"zone": zone, "ocr_result": zones[zone],
                "rect_ids": [row["rect_id"] for row in rows if row["type"] == zone], "question_order": None}
                for zone in zone_names], "ocr_delete_zones": [], "question_info": info, "created_by": None}


def validate_candidate(candidate, before, approved):
    """Preflight any of the four frozen candidates without pretending predecessors exist.

    The caller validates source/review/crop files and all-four UUID disjointness;
    this pure check binds the candidate's exact payload and current frame IDs.
    It neither validates a sequential before state nor authorizes a send.
    """
    u._json(candidate)
    u._json(approved)
    require(type(candidate) is dict and candidate.get("logical_key") in LOGICAL_KEYS, "A28_LOGICAL_KEY")
    require(type(before) is dict and type(before.get("frames")) is dict and
            type(u._response(before["frames"])) is list, "CURRENT_FRAME_INVENTORY_REQUIRED")
    index = LOGICAL_KEYS.index(candidate["logical_key"])
    payload = _approved_payload(candidate, approved, before, index)
    return {"ok": True, "status": "VALID_A28_CANDIDATE_ONLY", "logical_key": candidate["logical_key"],
            "payload_candidate": payload, "payload_sha256": u.digest(payload), "write_authorized": False}


def make_insert_plan(before, candidate, approved_new_content):
    require(type(candidate) is dict and candidate.get("logical_key") in LOGICAL_KEYS, "A28_LOGICAL_KEY")
    index = LOGICAL_KEYS.index(candidate["logical_key"])
    count = 23 + index
    questions, identities = _validate_full(before, count, (count,))
    payload = _approved_payload(candidate, approved_new_content, before, index)
    plan = {"schema": SCHEMA, "operation": "A28_LESSON_QUESTION_INSERT", "book_id": BOOK,
            "logical_key": candidate["logical_key"], "before_count": count, "after_count": count + 1,
            "insert_after_order": count - 1, "new_order": count, "old_tail_target": identities[0],
            "old_identities": [{"node_id": node["id"], "lesson_directory_id": parent,
                                "question_order": i} for i, (node, parent) in enumerate(questions, 1)],
            "candidate": copy.deepcopy(candidate), "before_full": copy.deepcopy(before),
            "before_sha256": flat_digest(before), "payload_candidate": payload,
            "approved_new_content": copy.deepcopy(approved_new_content),
            "ledger_key": "book46007447-lesson2-" + candidate["logical_key"],
            "automatic_retry_allowed": False, "write_authorized_by_this_module": False,
            "old_metadata_changes_allowed": ["only shifted old-tail frame/info updated_at, monotonic, within actual send window"],
            "native_timestamp_timezone": "+08:00", "timestamp_quantization_tolerance_seconds": 1,
            "predecessor_acceptance_verified_by_this_module": False}
    plan["plan_sha256"] = u.digest(plan)
    return plan


def validate_insert_plan(plan):
    require(type(plan) is dict and plan.get("schema") == SCHEMA, "LESSON_INSERT_PLAN_SCHEMA")
    rebuilt = make_insert_plan(plan.get("before_full"), plan.get("candidate"), plan.get("approved_new_content"))
    require(u.json_same(plan, rebuilt), "INSERT_PLAN_TAMPERED")
    return {"ok": True, "status": "VALID_A28_INSERT_PLAN", "plan_sha256": plan["plan_sha256"]}


def check_prewrite(plan, fresh):
    validate_insert_plan(plan)
    _validate_full(fresh, plan["before_count"], (plan["new_order"],))
    require(all(u.json_same(fresh[key], plan["before_full"][key]) for key in fresh), "STALE_FULL_BOOK_BEFORE_STATE")
    return {"ok": True, "status": "ALL13_FRESH_RESPONSES_EXACT", "response_count": len(fresh),
            "before_sha256": flat_digest(fresh)}


def decode_receipt(plan, raw):
    validate_insert_plan(plan)
    require(type(raw) is dict and tuple(raw) == ("code", "message", "data"), "INSERT_RECEIPT_ENVELOPE_UNKNOWN")
    data = u._response(raw, code=(0,))
    require(type(data) is dict and set(data) == {"inserted", "question_order", "inserted_question_node", "success",
                                              "append_at_global_end"}, "INSERT_RECEIPT_DATA_UNKNOWN")
    order = plan["new_order"]
    require(data["inserted"] is True and data["success"] is True and data["append_at_global_end"] is False and
            type(data["question_order"]) is int and data["question_order"] == order, "INSERT_RECEIPT_FLAGS_OR_ORDER")
    node = data["inserted_question_node"]
    require(type(node) is dict and tuple(node) in (ins.NODE_KEYS, ins.OBSERVED_INSERTED_NODE_KEYS) and
            u._id(node.get("id")) and node["id"] not in _directory_nodes(plan["before_full"]["directory"]) and
            node["isQuestion"] is True and type(node["order_in_level"]) is str and
            node["order_in_level"] == str(order) and type(node["label"]) is str and node["label"] == str(order),
            "EXACT_NEW_SERVER_NODE_REQUIRED")
    return {"ok": True, "status": "VALID_INSERT_RECEIPT", "question_order": order,
            "inserted_question_node": copy.deepcopy(node), "receipt_sha256": u.digest(raw)}


def _native_time(value):
    require(type(value) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value) is not None,
            "NATIVE_TIMESTAMP_FORMAT")
    return datetime.fromisoformat(value).replace(tzinfo=NATIVE_TZ)


def _window(send_window):
    require(type(send_window) is dict and set(send_window) == {"start", "end"}, "ACTUAL_SEND_WINDOW_REQUIRED")
    require(all(type(value) is str for value in send_window.values()), "SEND_WINDOW_FORMAT")
    start, end = (datetime.fromisoformat(send_window[key].replace("Z", "+00:00")) for key in ("start", "end"))
    require(start.utcoffset() is not None and end.utcoffset() is not None and
            timedelta(0) <= end - start <= timedelta(seconds=120), "BOUNDED_AWARE_SEND_WINDOW_REQUIRED")
    return start - timedelta(seconds=1), end + timedelta(seconds=1)


def compare_insert_readback(plan, after, receipt, runtime_actor_hashes=None, send_window=None):
    """Require twenty response readback; accepted comparison never implies a save."""
    validate_insert_plan(plan)
    decoded = decode_receipt(plan, receipt)
    checks, differences, metadata_changes = [], [], []

    def check(ok, path, reason="VALUE_MISMATCH"):
        checks.append({"path": path, "ok": bool(ok)})
        if not ok:
            differences.append({"path": path, "reason": reason})

    def same(left, right, path):
        check(u.json_same(left, right), path)

    before, order = plan["before_full"], plan["new_order"]
    try:
        _, identities = _validate_full(after, plan["after_count"], (order, order + 1))
        require(type(runtime_actor_hashes) is dict and set(runtime_actor_hashes) ==
                {"runtime_actor_sha256", "runtime_user_id_sha256"} and
                all(ins._hash(value) for value in runtime_actor_hashes.values()), "RUNTIME_ACTOR_HASH_PROOF_REQUIRED")
        start, end = _window(send_window)
    except (ValueError, KeyError, TypeError, IndexError) as error:
        return {"schema": "A28LessonInsertReadback/v1", "ok": False, "status": "HOLD",
                "plan_sha256": plan["plan_sha256"], "differences": [{"path": "after", "reason": str(error)}],
                "automatic_retry_allowed": False, "live_save_verified": False}

    def new_time(row, path):
        try:
            timestamp = _native_time(row.get("created_at"))
            valid = row.get("created_at") == row.get("updated_at") and start <= timestamp <= end
        except (ValueError, TypeError):
            valid = False
        check(valid, path, "NEW_TIMESTAMP_NOT_IN_ACTUAL_SEND_WINDOW")

    def shifted(old, actual, path):
        expected = copy.deepcopy(old)
        expected["order_in_level"] = ins._shift_value(old["order_in_level"])
        if not u.json_same(old.get("updated_at"), actual.get("updated_at")):
            try:
                prior, current = _native_time(old.get("updated_at")), _native_time(actual.get("updated_at"))
                valid = prior < current and start <= current <= end
            except (ValueError, TypeError):
                valid = False
            check(valid, path + ".updated_at", "SHIFTED_TAIL_TIMESTAMP_NOT_MONOTONIC_OR_OUTSIDE_SEND_WINDOW")
            if valid:
                expected["updated_at"] = actual["updated_at"]
                metadata_changes.append({"path": path + ".updated_at", "before": old["updated_at"],
                                         "after": actual["updated_at"]})
        return expected

    expected_directory = copy.deepcopy(before["directory"])
    nodes = _directory_nodes(expected_directory)
    receipt_node = decoded["inserted_question_node"]
    native_node = _directory_nodes(after["directory"]).get(receipt_node["id"], {})
    node_layout_ok = tuple(native_node) in (ins.NODE_KEYS, ins.OBSERVED_INSERTED_NODE_KEYS)
    check(node_layout_ok and all(key in native_node and u.json_same(native_node[key], receipt_node[key])
                                for key in receipt_node), "new.directory_node", "RECEIPT_NODE_VALUES_OR_LAYOUT")
    expected_node = {key: copy.deepcopy(receipt_node[key]) for key in native_node} if node_layout_ok else receipt_node
    nodes[DIRECTORY]["children"].append(expected_node)
    nodes[TAIL_NODE]["order_in_level"] = ins._shift_value(nodes[TAIL_NODE]["order_in_level"])
    nodes[TAIL_NODE]["label"] = ins._shift_value(nodes[TAIL_NODE]["label"])
    same(expected_directory, after["directory"], "directory")
    for key in GLOBAL_KEYS[2:]:
        same(before[key], after[key], key)
    old_frames = before["frames"]["data"]
    old_ids = {row["rect_id"] for row in old_frames}
    new_rows = plan["payload_candidate"]["annotations_upsert"]
    new_ids = {row["rect_id"] for row in new_rows}
    actual_frames = after["frames"]["data"]
    by_id = {row["rect_id"]: row for row in actual_frames}
    check(set(by_id) == old_ids | new_ids, "frames.identities", "EXACT_OLD_PLUS_NEW_IDENTITIES_REQUIRED")
    expected_old = copy.deepcopy(before["frames"])
    expected_old["data"] = [shifted(row, by_id.get(row["rect_id"], {}), "frames." + row["rect_id"])
        if u._order(row["order_in_level"]) == order else copy.deepcopy(row) for row in old_frames]
    actual_old = copy.deepcopy(after["frames"])
    actual_old["data"] = [row for row in actual_frames if row["rect_id"] in old_ids]
    same(expected_old, actual_old, "frames.old_subsequence")
    for suffix in SUFFIXES:
        expected = copy.deepcopy(before[f"q{order}_{suffix}"])
        actual = after[f"q{order+1}_{suffix}"]
        if suffix == "annotations":
            expected["data"] = [row for row in expected_old["data"] if u._order(row["order_in_level"]) == order + 1]
        elif suffix == "info":
            expected["data"] = shifted(expected["data"], actual["data"], "old_tail.info")
        same(expected, actual, "old_tail." + suffix)
    new_identity = identities[0]
    check(new_identity["node_id"] == decoded["inserted_question_node"]["id"] and
          new_identity["lesson_directory_id"] == DIRECTORY and new_identity["info_id"] != TAIL_INFO,
          "new_identity", "RECEIPT_BOUND_NEW_IDENTITY_REQUIRED")
    for row in new_rows:
        actual = by_id.get(row["rect_id"], {})
        expected = {key: copy.deepcopy(row[key]) if key in row else actual.get(key) for key in ins.ROW_KEYS}
        expected.update(verified=0, file_id=BOOK, order_in_level=str(order), user_id=actual.get("user_id"))
        same(expected, actual, "new_frame." + row["rect_id"])
        check(type(actual.get("user_id")) is str and u.text_digest(actual["user_id"]) ==
              runtime_actor_hashes["runtime_user_id_sha256"], "new_frame." + row["rect_id"] + ".user_id")
        new_time(actual, "new_frame." + row["rect_id"] + ".timestamps")
    annotations = copy.deepcopy(before[f"q{order}_annotations"])
    annotations["data"] = [row for row in actual_frames if row["rect_id"] in new_ids]
    same(annotations, after[f"q{order}_annotations"], "new.annotations")
    info = after[f"q{order}_info"]["data"]
    expected_info = {"id": new_identity["info_id"], "tishi": plan["payload_candidate"]["question_info"]["tishi"],
                     "tilei": None, "tixu": None, "tihao": None, "file_id": BOOK, "order_in_level": str(order),
                     "created_at": info.get("created_at"), "updated_at": info.get("updated_at")}
    info_response = copy.deepcopy(before[f"q{order}_info"])
    info_response["data"] = expected_info
    same(info_response, after[f"q{order}_info"], "new.info")
    new_time(info, "new.info.timestamps")
    submissions = {row["zone"]: row for row in plan["payload_candidate"]["ocr_submissions"]}
    for zone in u.ZONES:
        expected = copy.deepcopy(before[f"q{order}_{zone}"])
        actual = after[f"q{order}_{zone}"]
        if zone in submissions:
            sub = submissions[zone]
            values = {"rect_ids": sub["rect_ids"], "ocr_result": sub["ocr_result"], "success": True}
            actual_order = tuple(actual["data"])
            check(actual_order in ZONE_ORDERS, "new." + zone + ".data_order", "UNKNOWN_CREATED_ZONE_KEY_ORDER")
            expected["data"] = {key: values[key] for key in actual_order} if actual_order in ZONE_ORDERS else values
        else:
            expected["data"] = copy.deepcopy(u.ABSENT)
        same(expected, actual, "new." + zone)
    return {"schema": "A28LessonInsertReadback/v1", "ok": not differences,
            "status": "ACCEPTED_A28_INSERT_PRESERVATION" if not differences else "HOLD",
            "plan_sha256": plan["plan_sha256"], "before_sha256": plan["before_sha256"],
            "after_sha256": flat_digest(after), "receipt_sha256": decoded["receipt_sha256"],
            "new_identity": new_identity, "checks": checks, "differences": differences,
            "metadata_changes": metadata_changes, "send_window": copy.deepcopy(send_window),
            "native_timestamp_timezone": "+08:00", "timestamp_quantization_tolerance_seconds": 1,
            "old_tail_ocr_preserved": all(u.json_same(before[f"q{order}_{zone}"], after[f"q{order+1}_{zone}"])
                                           for zone in u.ZONES),
            "old_question_count": plan["before_count"], "new_question_count": 1,
            "expected_frame_count": FRAME_TOTALS[plan["after_count"] - 23],
            "automatic_retry_allowed": False, "receipt_verified": True,
            "independent_context_verified": False, "live_save_verified": False,
            "predecessor_acceptance_verified_by_this_module": False}
