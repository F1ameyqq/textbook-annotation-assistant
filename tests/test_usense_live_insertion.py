"""Synthetic 22->23 fixtures. No real server response or write is simulated as proof."""
import copy
import importlib.util
from pathlib import Path
import sys
import types
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from annotation.runtime.usense_live import update as u, insertion as ins


def response(data):
    return {"code": 0, "message": "success", "data": data}


def uid(text):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, "SYNTHETIC_ONLY." + text))


def synthetic_fixture():
    """Independent fixed native layout, with old22 under a different lesson."""
    nodes, frames, flat = [], [], {}
    for order in range(1, 23):
        node_id = ins.OLD_Q7_NODE if order == 7 else str(8000000 + order)
        nodes.append({"id": node_id, "label": str(order), "isQuestion": True, "order_in_level": str(order)})
        info_id = ins.OLD_Q7_INFO if order == 7 else str(9000000 + order)
        flat[f"q{order}_info"] = response({"id": info_id, "tishi": "duoxuan" if order == 7 else "xuanze",
            "tilei": None, "tixu": None, "tihao": None, "file_id": ins.BOOK, "order_in_level": str(order),
            "created_at": "2026-10-15T20:13:37", "updated_at": "2026-10-15T20:13:37"})
        layout = [("question", 0), ("choice", 0), ("answer", 0)]
        if order == 1:
            layout = [("question", 0), ("question", 1), ("question", 2), ("choice", 0), ("answer", 0)]
        if order == 7:
            layout = [("question", 0), ("question", 1), ("question", 2), ("choice", 0), ("choice", 1), ("answer", 0)]
        if order in (8, 9, 22):
            layout = [("question", 0), ("answer", 0)]
        for zone, index in layout:
            frames.append({"type": zone, "verified": 0, "rect_id": uid(f"old-{order}-{zone}-{index}"),
                "file_id": ins.BOOK, "belong_to_level": "question_level", "order_in_level": str(order),
                "image_order_in_annotation_zone": index, "rect_bbox": "1,2,30,40", "page_index": 10,
                "image_path": "https://synthetic.invalid/preserved-image.jpg", "created_at": "2026-10-15T20:13:37",
                "updated_at": "2026-10-15T20:13:37", "parent_rect_id": None,
                "directory_id": ins.DIRECTORY if order < 22 else "synthetic-other-lesson",
                "content_type": "text", "user_id": "111", "is_pre_annotation": False, "pre_annotations_id": None})
    frames.sort(key=lambda row: row["rect_id"])
    flat["directory"] = response({"directory_data": [{"id": "synthetic-root", "label": "SYNTHETIC_ONLY",
        "children": [{"id": ins.DIRECTORY, "label": "first lesson", "children": nodes[:21]},
                     {"id": "synthetic-other-lesson", "label": "other lesson", "children": nodes[21:]}]}],
                     "opaque_native_field": {"must": "survive", "typed": 1}})
    flat["frames"] = response(frames)
    for key in ins.GLOBAL_KEYS[2:]:
        flat[key] = response({"SYNTHETIC_ONLY": key, "opaque": [None, False, 0, "0"]})
    for order in range(1, 23):
        rows = [row for row in frames if row["order_in_level"] == str(order)]
        flat[f"q{order}_annotations"] = response(copy.deepcopy(rows))
        for zone in u.ZONES:
            ids = [row["rect_id"] for row in sorted(rows, key=lambda row: row["image_order_in_annotation_zone"]) if row["type"] == zone]
            flat[f"q{order}_{zone}"] = response({"rect_ids": ids, "ocr_result": f"SYNTHETIC old {order} {zone}", "success": True}
                if ids else copy.deepcopy(u.ABSENT))
    candidate_frames = []
    layouts = [("question", 0, "text"), ("question", 1, "image"), ("choice", 0, "text"),
               ("choice", 1, "text"), ("choice", 2, "text"), ("choice", 3, "text"), ("answer", 0, "text")]
    for number, (key, (zone, index, content)) in enumerate(zip(ins.FRAME_KEYS, layouts)):
        page = 173 if zone == "answer" else 10
        bbox = [number * 10, 20, number * 10 + 10, 40]
        url = (f"https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com/upload_images/{ins.BOOK}/"
               f"{ins.BOOK}_page_{page-1}.jpg?x-oss-process=image/crop,x_{bbox[0]},y_20,w_10,h_20")
        candidate_frames.append({"key": key, "zone": zone, "image_order_in_annotation_zone": index, "content_type": content,
            "planned_rect_id": uid("new-" + key), "bbox": bbox, "source_dimensions": [1000, 1000],
            "rect_bbox": ",".join(map(str, bbox)), "viewer_page": page, "page_index": page, "image_path": url,
            "hosted_image_url": url, "source": {"path": f"SYNTHETIC-page-{page}.jpg", "sha256": str(page % 10) * 64},
            "source_sha256": str(page % 10) * 64, "crop": {"sha256": "a" * 64}, "crop_sha256": "a" * 64,
            "fetch_evidence": {"status": "FETCHED_CROP", "http_status": 200, "url": url, "bbox": bbox,
                "dimensions": [10, 20], "source_sha256": str(page % 10) * 64, "sha256": "a" * 64}})
    zones = {"question": 'SYNTHETIC VARIANT ONLY <img src="' + candidate_frames[1]["image_path"] + '" />',
             "choice": "A. 1\nB. 2\nC. 3\nD. 4", "answer": "B"}
    candidate = {"schema": "Q7FinalSevenFrameContentCandidate/v1", "logical_owner": "variant", "book_id": ins.BOOK,
        "target_directory_id": ins.DIRECTORY, "target": {"node_id": None, "info_id": None, "question_order": None,
            "proposed_insert_after_existing_node_id": ins.OLD_Q7_NODE, "proposed_insert_after_existing_order": 7},
        "frames": candidate_frames, "zone_values": zones, "zone_text_sha256": {zone: u.text_digest(text) for zone, text in zones.items()},
        "question_info": {"tishi": "xuanze", "tilei": None, "tihao": None}}
    approved = {"candidate_ref": "SYNTHETIC-candidate.json", "candidate_sha256": "a" * 64,
        "review_ref": "SYNTHETIC-review.json", "review_sha256": "b" * 64,
        "crop_evidence_ref": "SYNTHETIC-proof.json", "crop_evidence_sha256": "c" * 64,
        "source_evidence": [{"path": f"SYNTHETIC-page-{page}.jpg", "sha256": str(page % 10) * 64} for page in (10, 173)],
        "candidate": candidate}
    rows = [{"rect_id": f["planned_rect_id"], "type": f["zone"], "belong_to_level": "question_level", "order_in_level": "23",
            "image_order_in_annotation_zone": f["image_order_in_annotation_zone"], "rect_bbox": f["rect_bbox"],
            "page_index": f["viewer_page"], "image_path": f["image_path"], "parent_rect_id": None,
            "directory_id": ins.DIRECTORY, "content_type": f["content_type"], "user_id": None,
            "is_pre_annotation": False, "pre_annotations_id": None} for f in candidate_frames]
    payload = {"file_id": ins.BOOK, "target_directory_id": ins.DIRECTORY, "question_order": None,
        "is_new_question_insertion": True, "insert_after_order": 7, "annotations_upsert": rows,
        "annotations_delete_rect_ids": [], "ocr_submissions": [{"zone": zone, "ocr_result": zones[zone],
            "rect_ids": [r["rect_id"] for r in rows if r["type"] == zone], "question_order": None} for zone in zones],
        "ocr_delete_zones": [], "question_info": copy.deepcopy(candidate["question_info"]), "created_by": None}
    return flat, payload, approved


def synthetic_readback(before, payload):
    new_node = {"id": "999888777666", "label": "8", "isQuestion": True, "order_in_level": "8"}
    after = {key: copy.deepcopy(before[key]) for key in ins.GLOBAL_KEYS}
    lessons = after["directory"]["data"]["directory_data"][0]["children"]
    for lesson in lessons:
        for node in lesson["children"]:
            if int(node["order_in_level"]) >= 8:
                node["order_in_level"] = node["label"] = str(int(node["order_in_level"]) + 1)
    lessons[0]["children"].insert(7, copy.deepcopy(new_node))
    for row in after["frames"]["data"]:
        if int(row["order_in_level"]) >= 8:
            row["order_in_level"] = str(int(row["order_in_level"]) + 1)
    for row in payload["annotations_upsert"]:
        generated = dict(row, order_in_level="8", verified=0, file_id=ins.BOOK, user_id="222",
                         created_at="2026-10-22T19:00:00", updated_at="2026-10-22T19:00:00")
        after["frames"]["data"].append({key: generated[key] for key in ins.ROW_KEYS})
    after["frames"]["data"].sort(key=lambda row: row["rect_id"])
    for i in range(1, 23):
        dest = i if i < 8 else i + 1
        for suffix in ins.SUFFIXES:
            after[f"q{dest}_{suffix}"] = copy.deepcopy(before[f"q{i}_{suffix}"])
        after[f"q{dest}_info"]["data"]["order_in_level"] = str(dest)
        after[f"q{dest}_annotations"]["data"] = [row for row in after["frames"]["data"] if row["order_in_level"] == str(dest)]
    after["q8_info"] = response({"id": "999555444333", "tishi": "xuanze", "tilei": None, "tixu": None, "tihao": None,
        "file_id": ins.BOOK, "order_in_level": "8", "created_at": "2026-10-22T19:00:00", "updated_at": "2026-10-22T19:00:00"})
    after["q8_annotations"] = response([row for row in after["frames"]["data"] if row["order_in_level"] == "8"])
    subs = {row["zone"]: row for row in payload["ocr_submissions"]}
    for zone in u.ZONES:
        after["q8_" + zone] = response({"rect_ids": subs[zone]["rect_ids"], "ocr_result": subs[zone]["ocr_result"], "success": True}
            if zone in subs else copy.deepcopy(u.ABSENT))
    receipt = response({"inserted": True, "question_order": 8, "inserted_question_node": new_node,
                        "success": True, "append_at_global_end": False})
    return after, receipt


class InsertionTests(unittest.TestCase):
    def setUp(self):
        self.before, self.payload, self.approved = synthetic_fixture()
        self.plan = ins.make_insert_plan(self.before, payload_candidate=self.payload, approved_new_content=self.approved)
        self.after, self.receipt = synthetic_readback(self.before, self.payload)
        self.actors = {"runtime_actor_sha256": u.text_digest("SYNTHETIC-username"), "runtime_user_id_sha256": u.text_digest("222")}

    def compare(self):
        return ins.compare_insert_readback(self.plan, self.after, self.receipt, runtime_actor_hashes=self.actors)

    def reject(self):
        self.assertFalse(self.compare()["ok"])

    def test_success_preserves_old_q7_and_other_directory22(self):
        result = self.compare()
        self.assertTrue(result["ok"], result["differences"])
        self.assertTrue(result["old_q7_preserved"])
        self.assertFalse(result["phase2_permitted"])
        self.assertFalse(result["live_save_verified"])
        self.assertEqual(result["new_identity"]["info_id"], "999555444333")
        self.assertEqual(self.after["q23_info"]["data"]["id"], self.before["q22_info"]["data"]["id"])

    def test_prewrite_all161_and_outer_map_order(self):
        self.assertTrue(ins.check_prewrite(self.plan, dict(reversed(list(self.before.items()))))["ok"])

    def test_prewrite_hidden_old_zone_change(self):
        self.before["q22_answer"]["data"]["ocr_result"] += "wrong"
        with self.assertRaisesRegex(ValueError, "STALE"):
            ins.check_prewrite(self.plan, self.before)

    def test_prewrite_source_page_change(self):
        self.before["page_173"]["data"]["opaque"][2] = False
        with self.assertRaises(ValueError):
            ins.check_prewrite(self.plan, self.before)

    def test_plan_hash_tamper(self):
        self.plan["old_metadata_changes_allowed"] = ["updated_at"]
        with self.assertRaisesRegex(ValueError, "TAMPERED"):
            ins.validate_insert_plan(self.plan)

    def test_delete_cannot_enter_insert_plan(self):
        self.payload["annotations_delete_rect_ids"] = [self.before["q7_annotations"]["data"][0]["rect_id"]]
        with self.assertRaises(ValueError):
            ins.make_insert_plan(self.before, payload_candidate=self.payload, approved_new_content=self.approved)

    def test_reusing_old_frame_id_rejected(self):
        self.approved["candidate"]["frames"][0]["planned_rect_id"] = self.before["frames"]["data"][0]["rect_id"]
        with self.assertRaises(ValueError):
            ins.make_insert_plan(self.before, payload_candidate=self.payload, approved_new_content=self.approved)

    def test_changed_review_text_hash_rejected(self):
        self.approved["candidate"]["zone_values"]["answer"] = "A"
        with self.assertRaises(ValueError):
            ins.make_insert_plan(self.before, payload_candidate=self.payload, approved_new_content=self.approved)

    def test_cropped_figure_reference_cannot_disappear(self):
        self.payload["ocr_submissions"][0]["ocr_result"] = "SYNTHETIC no figure"
        with self.assertRaises(ValueError):
            ins.make_insert_plan(self.before, payload_candidate=self.payload, approved_new_content=self.approved)

    def test_receipt_unknown_keys_rejected(self):
        self.receipt["data"]["extra"] = True
        with self.assertRaisesRegex(ValueError, "UNKNOWN"):
            ins.decode_receipt(self.plan, self.receipt)

    def test_receipt_missing_exact_new_node_rejected(self):
        self.receipt["data"]["inserted_question_node"] = None
        with self.assertRaises(ValueError):
            ins.decode_receipt(self.plan, self.receipt)

    def test_receipt_bool_not_integer_order(self):
        self.receipt["data"]["question_order"] = True
        with self.assertRaises(ValueError):
            ins.decode_receipt(self.plan, self.receipt)

    def test_receipt_old_node_rejected(self):
        self.receipt["data"]["inserted_question_node"]["id"] = ins.OLD_Q7_NODE
        with self.assertRaises(ValueError):
            ins.decode_receipt(self.plan, self.receipt)

    def test_observed_inserted_node_layout_preserved_exactly(self):
        node = self.receipt["data"]["inserted_question_node"]
        observed = {key: node[key] for key in ins.OBSERVED_INSERTED_NODE_KEYS}
        self.receipt["data"]["inserted_question_node"] = observed
        self.after["directory"]["data"]["directory_data"][0]["children"][0]["children"][7] = copy.deepcopy(observed)
        self.assertEqual(tuple(ins.decode_receipt(self.plan, self.receipt)["inserted_question_node"]), ins.OBSERVED_INSERTED_NODE_KEYS)
        self.assertTrue(self.compare()["ok"])

    def test_unobserved_receipt_node_permutation_rejected(self):
        node = self.receipt["data"]["inserted_question_node"]
        self.receipt["data"]["inserted_question_node"] = {key: node[key] for key in reversed(ins.NODE_KEYS)}
        with self.assertRaises(ValueError):
            ins.decode_receipt(self.plan, self.receipt)

    def test_observed_receipt_unknown_node_field_rejected(self):
        node = self.receipt["data"]["inserted_question_node"]
        self.receipt["data"]["inserted_question_node"] = {key: node[key] for key in ins.OBSERVED_INSERTED_NODE_KEYS}
        self.receipt["data"]["inserted_question_node"]["unknown"] = None
        with self.assertRaises(ValueError):
            ins.decode_receipt(self.plan, self.receipt)

    def test_new_receipt_layout_does_not_normalize_directory(self):
        node = self.receipt["data"]["inserted_question_node"]
        self.receipt["data"]["inserted_question_node"] = {key: node[key] for key in ins.OBSERVED_INSERTED_NODE_KEYS}
        self.reject()

    def test_no_actor_proof_rejected(self):
        with self.assertRaisesRegex(ValueError, "ACTOR"):
            ins.compare_insert_readback(self.plan, self.after, self.receipt)

    def test_wrong_runtime_user_hash(self):
        self.actors["runtime_user_id_sha256"] = u.text_digest("333")
        self.reject()

    def test_old_q7_content_is_immutable(self):
        self.after["q7_question"]["data"]["ocr_result"] = "SYNTHETIC illicit phase2"
        self.reject()

    def test_old22_content_bound_after_global_reindex(self):
        self.after["q23_question"]["data"]["ocr_result"] = "wrong old22"
        self.reject()

    def test_missing_old22_global_reindex_rejected(self):
        self.after["q23_info"]["data"]["order_in_level"] = "22"
        self.reject()

    def test_old_info_timestamp_unknown_change_held(self):
        self.after["q23_info"]["data"]["updated_at"] = "2026-10-22T19:00:00"
        result = self.compare()
        self.assertFalse(result["ok"])
        self.assertTrue(any(row["reason"] == "UNAPPROVED_OLD_METADATA_CHANGE" for row in result["differences"]))

    def test_old_frame_timestamp_unknown_change_held(self):
        self.after["q7_annotations"]["data"][0]["updated_at"] = "2026-10-22T19:00:00"
        self.reject()

    def test_geometry_cannot_change(self):
        self.after["q7_annotations"]["data"][0]["rect_bbox"] = "0,0,1,1"
        self.reject()

    def test_new_frame_metadata_bool_not_zero(self):
        self.after["q8_annotations"]["data"][0]["verified"] = False
        self.reject()

    def test_new_frame_unknown_field_held(self):
        self.after["q8_annotations"]["data"][0]["surprise"] = "server side effect"
        self.reject()

    def test_new_info_unknown_field_held(self):
        self.after["q8_info"]["data"]["surprise"] = None
        self.reject()

    def test_new_info_metadata_unexplained_second_update_held(self):
        self.after["q8_info"]["data"]["updated_at"] = "2026-10-22T19:01:00"
        self.reject()

    def test_new_annotations_unknown_envelope_field_held(self):
        self.after["q8_annotations"]["extra"] = 123
        self.reject()

    def test_old_unknown_directory_field_preserved(self):
        self.after["directory"]["data"]["opaque_native_field"]["typed"] = True
        self.reject()

    def test_old_native_key_order_preserved(self):
        row = self.after["q23_question"]["data"]
        self.after["q23_question"]["data"] = dict(reversed(list(row.items())))
        self.reject()

    def test_absent_zone_cannot_be_filled_or_empty_substituted(self):
        self.after["q8_analysis"]["data"] = {"rect_ids": [], "ocr_result": "", "success": True}
        self.reject()

    def test_crossed_choice_rect_order_rejected(self):
        self.after["q8_choice"]["data"]["rect_ids"].reverse()
        self.reject()

    def test_server_new_node_different_from_receipt_rejected(self):
        self.receipt["data"]["inserted_question_node"]["id"] = "999888777555"
        self.reject()

    def test_duplicate_info_id_rejected(self):
        self.after["q8_info"]["data"]["id"] = self.after["q7_info"]["data"]["id"]
        self.reject()

    def test_added_twentyfourth_question_not_accepted(self):
        self.after["q24_info"] = copy.deepcopy(self.after["q23_info"])
        self.reject()

    def test_missing_old_frame_not_accepted(self):
        old_id = self.after["q23_annotations"]["data"][0]["rect_id"]
        self.after["frames"]["data"] = [row for row in self.after["frames"]["data"] if row["rect_id"] != old_id]
        self.reject()

    def test_ledger_key_does_not_depend_on_plan_content(self):
        altered = copy.deepcopy(self.approved)
        altered["review_sha256"] = "f" * 64
        second = ins.make_insert_plan(self.before, payload_candidate=self.payload, approved_new_content=altered)
        self.assertEqual(second["ledger_key"], self.plan["ledger_key"])
        self.assertNotEqual(second["plan_sha256"], self.plan["plan_sha256"])


if __name__ == "__main__":
    unittest.main()
