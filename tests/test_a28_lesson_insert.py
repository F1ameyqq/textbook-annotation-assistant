"""New A28 synthetic boundary witnesses; no platform success is simulated."""
import copy
from pathlib import Path
import sys
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from annotation.runtime.usense_live import insertion as old, lesson_insert as ins, update as u


def response(data):
    return {"code": 0, "message": "success", "data": data}


def uid(text):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, "A28_SYNTHETIC_ONLY." + text))


def initial_before():
    nodes = [{"id": ident, "label": str(i), "isQuestion": True, "order_in_level": str(i)}
             for i, ident in enumerate(ins.OLD_NODES, 1)]
    tail = {"id": ins.TAIL_NODE, "label": "23", "isQuestion": True, "order_in_level": "23"}
    directory = response({"directory_data": [{"id": "SYNTHETIC-root", "label": "SYNTHETIC ONLY", "children": [
        {"id": ins.OLD_PARENT, "label": "old lesson", "children": nodes},
        {"id": ins.DIRECTORY, "label": ins.LESSON, "children": []},
        {"id": ins.TAIL_PARENT, "label": "old suffix", "children": [tail]}]}],
        "opaque": [None, False, 1, "1"]})
    frames = []
    for order in range(1, 24):
        layout = [("question", 0), ("answer", 0)]
        if order < 23:
            layout.append(("choice", 0))
        if order == 1:
            layout.extend(("question", i) for i in range(1, 9))
        for zone, number in layout:
            values = {"type": zone, "verified": 0, "rect_id": uid(f"old-{order}-{zone}-{number}"),
                "file_id": ins.BOOK, "belong_to_level": "question_level", "order_in_level": str(order),
                "image_order_in_annotation_zone": number, "rect_bbox": "1,2,30,40", "page_index": 12,
                "image_path": "https://synthetic.invalid/preserved.jpg", "created_at": "2026-10-15T20:13:37",
                "updated_at": "2026-10-23T10:00:00", "parent_rect_id": None,
                "directory_id": ins.TAIL_PARENT if order == 23 else ins.OLD_PARENT,
                "content_type": "text", "user_id": "SYNTHETIC-old-actor", "is_pre_annotation": False,
                "pre_annotations_id": None}
            frames.append({key: values[key] for key in old.ROW_KEYS})
    frames.sort(key=lambda row: row["rect_id"])
    flat = {"directory": directory, "frames": response(frames),
            "source": response({"file_id": ins.BOOK, "source": "legacy_db", "total_pages": 214,
                                "opaque": [None, True, 4]})}
    for page in (12, 13, 173):
        flat[f"page_{page}"] = response({"pages": [{"image": ins._source_url(page), "blocks": [], "page_index": page - 1}],
                                         "file_id": ins.BOOK, "source": "legacy_db"})
    flat["q23_annotations"] = response(copy.deepcopy([row for row in frames if row["order_in_level"] == "23"]))
    flat["q23_info"] = response({"id": ins.TAIL_INFO, "tishi": "tiankong", "tilei": None, "tixu": None,
        "tihao": None, "file_id": ins.BOOK, "order_in_level": "23", "created_at": "2026-10-15T20:13:37",
        "updated_at": "2026-10-23T10:00:00"})
    for zone in u.ZONES:
        rows = [row for row in flat["q23_annotations"]["data"] if row["type"] == zone]
        flat[f"q23_{zone}"] = response({"success": True, "ocr_result": "SYNTHETIC old tail " + zone,
            "rect_ids": [row["rect_id"] for row in rows]} if rows else copy.deepcopy(u.ABSENT))
    return flat


def candidate_for(index):
    key = ins.LOGICAL_KEYS[index]
    frames = []
    pages = (12 if index < 2 else 13, 173)
    source_evidence = [{"path": f"SYNTHETIC-source-{page}.jpg", "sha256": ins.SOURCE_SHA256[page]} for page in pages]
    for number, (zone, content, image_order) in enumerate(ins._layout(index)):
        page = pages[1] if zone == "answer" else pages[0]
        bbox = [20 * number, 20, 20 * number + 10, 40]
        url = ins._source_url(page) + f"?x-oss-process=image/crop,x_{bbox[0]},y_20,w_10,h_20"
        frames.append({"key": key + "-" + str(number), "zone": zone, "content_type": content,
            "image_order_in_annotation_zone": image_order, "viewer_page": page,
            "source": next(copy.deepcopy(source) for source in source_evidence if str(page) in source["path"]),
            "source_dimensions": copy.deepcopy(ins.SOURCE_DIMENSIONS[page]), "bbox": bbox,
            "planned_rect_id": uid(key + "-" + str(number)), "image_path": url})
    zones = {"question": 'SYNTHETIC stem <img src="' + frames[1]["image_path"] + '">'}
    if index < 2:
        zones["choice"] = "A. synthetic one\nB. synthetic two\nC. synthetic three\nD. synthetic four"
    zones["answer"] = "B" if index < 2 else "SYNTHETIC explanation"
    candidate = {"schema": "A28LessonQuestionCandidate/v1", "book_id": ins.BOOK, "logical_key": key,
        "printed_question": (6, 7, 8, 8)[index], "variant": index == 3, "semantic_lesson": ins.LESSON,
        "target_directory_id": ins.DIRECTORY, "zone_values": zones,
        "zone_text_sha256": {zone: u.text_digest(text) for zone, text in zones.items()},
        "question_info": {"tishi": "xuanze" if index < 2 else "wenda", "tilei": None, "tihao": None},
        "frames": frames, "review": {"path": "SYNTHETIC-review.json", "sha256": "b" * 64}}
    approved = {"candidate_ref": "SYNTHETIC-candidate.json", "candidate_sha256": "a" * 64,
        "review_ref": candidate["review"]["path"], "review_sha256": candidate["review"]["sha256"],
        "crop_evidence_ref": "SYNTHETIC-crop.json", "crop_evidence_sha256": "c" * 64,
        "source_evidence": source_evidence, "candidate": copy.deepcopy(candidate)}
    return candidate, approved


def readback_for(plan, *, timestamp="2026-10-23T22:00:00"):
    before, order = plan["before_full"], plan["new_order"]
    after = {key: copy.deepcopy(before[key]) for key in ins.GLOBAL_KEYS}
    lessons = after["directory"]["data"]["directory_data"][0]["children"]
    node = {"isQuestion": True, "order_in_level": str(order), "id": "SYNTHETIC-new-node-" + str(order), "label": str(order)}
    lessons[1]["children"].append(copy.deepcopy(node))
    lessons[2]["children"][0].update(order_in_level=str(order + 1), label=str(order + 1))
    for row in after["frames"]["data"]:
        if row["order_in_level"] == str(order):
            row["order_in_level"] = str(order + 1)
            row["updated_at"] = timestamp
    for row in plan["payload_candidate"]["annotations_upsert"]:
        values = dict(row, verified=0, file_id=ins.BOOK, order_in_level=str(order),
                      user_id="SYNTHETIC-new-actor", created_at=timestamp, updated_at=timestamp)
        after["frames"]["data"].append({key: values[key] for key in old.ROW_KEYS})
    after["frames"]["data"].sort(key=lambda row: row["rect_id"])
    for suffix in ins.SUFFIXES:
        after[f"q{order+1}_{suffix}"] = copy.deepcopy(before[f"q{order}_{suffix}"])
    after[f"q{order+1}_info"]["data"].update(order_in_level=str(order + 1), updated_at=timestamp)
    after[f"q{order+1}_annotations"]["data"] = copy.deepcopy([row for row in after["frames"]["data"]
                                                              if row["order_in_level"] == str(order + 1)])
    after[f"q{order}_annotations"] = response(copy.deepcopy([row for row in after["frames"]["data"]
                                                            if row["order_in_level"] == str(order)]))
    after[f"q{order}_info"] = response({"id": "SYNTHETIC-new-info-" + str(order),
        "tishi": plan["payload_candidate"]["question_info"]["tishi"], "tilei": None, "tixu": None, "tihao": None,
        "file_id": ins.BOOK, "order_in_level": str(order), "created_at": timestamp, "updated_at": timestamp})
    subs = {row["zone"]: row for row in plan["payload_candidate"]["ocr_submissions"]}
    for zone in u.ZONES:
        after[f"q{order}_{zone}"] = response({"success": True, "ocr_result": subs[zone]["ocr_result"],
            "rect_ids": copy.deepcopy(subs[zone]["rect_ids"])} if zone in subs else copy.deepcopy(u.ABSENT))
    receipt = response({"inserted": True, "question_order": order, "inserted_question_node": node,
                        "success": True, "append_at_global_end": False})
    return after, receipt


ACTORS = {"runtime_actor_sha256": u.text_digest("SYNTHETIC-username"),
          "runtime_user_id_sha256": u.text_digest("SYNTHETIC-new-actor")}
WINDOW = {"start": "2026-10-23T14:00:00.200+00:00", "end": "2026-10-23T14:00:01.005+00:00"}


class A28LessonInsertTests(unittest.TestCase):
    def setUp(self):
        self.before = initial_before()
        self.candidate, self.approved = candidate_for(0)
        self.plan = ins.make_insert_plan(self.before, self.candidate, self.approved)
        self.after, self.receipt = readback_for(self.plan)

    def compare(self, **changes):
        values = dict(plan=self.plan, after=self.after, receipt=self.receipt,
                      runtime_actor_hashes=ACTORS, send_window=WINDOW)
        values.update(changes)
        return ins.compare_insert_readback(**values)

    def assert_hold(self):
        self.assertFalse(self.compare()["ok"])

    def test_all_four_serial_insertions_use_only_tail_shift(self):
        before = self.before
        for index in range(4):
            candidate, approved = candidate_for(index)
            plan = ins.make_insert_plan(before, candidate, approved)
            stamp = f"2026-10-23T22:0{index}:00"
            after, receipt = readback_for(plan, timestamp=stamp)
            window = {"start": f"2026-10-23T14:0{index}:00.200Z", "end": f"2026-10-23T14:0{index}:01Z"}
            result = ins.compare_insert_readback(plan, after, receipt, ACTORS, window)
            self.assertTrue(result["ok"], result["differences"])
            self.assertTrue(result["old_tail_ocr_preserved"])
            self.assertFalse(result["live_save_verified"])
            self.assertFalse(result["predecessor_acceptance_verified_by_this_module"])
            self.assertEqual(plan["payload_candidate"]["annotations_upsert"][0]["order_in_level"], str(24 + index))
            self.assertEqual(plan["new_order"], 23 + index)
            before = {key: copy.deepcopy(after[key]) for key in ins.full_endpoints(tail_order=24 + index)}

    def test_exact13_before_and20_after(self):
        self.assertEqual(len(ins.full_endpoints(self.plan)), 13)
        self.assertEqual(len(self.after), 20)
        self.assertTrue(ins.check_prewrite(self.plan, dict(reversed(list(self.before.items()))))["ok"])

    def test_all_four_candidates_preflight_without_skipping_plan_predecessors(self):
        for index in range(4):
            candidate, approved = candidate_for(index)
            result = ins.validate_candidate(candidate, self.before, approved)
            self.assertTrue(result["ok"])
            self.assertFalse(result["write_authorized"])

    def test_wrong_page_source_hash_rejected_even_with_matching_approval(self):
        self.candidate["frames"][0]["source"]["sha256"] = "f" * 64
        self.approved["source_evidence"][0]["sha256"] = "f" * 64
        self.approved["candidate"] = copy.deepcopy(self.candidate)
        with self.assertRaisesRegex(ValueError, "SOURCE_EVIDENCE_BINDING"):
            ins.validate_candidate(self.candidate, self.before, self.approved)

    def test_wrong_parent_and_oldfive_directory_migration_rejected(self):
        for native in (1, 18, 22):
            before = copy.deepcopy(self.before)
            row = next(row for row in before["frames"]["data"] if row["order_in_level"] == str(native))
            row["directory_id"] = ins.DIRECTORY
            with self.assertRaises(ValueError):
                ins.make_insert_plan(before, self.candidate, self.approved)

    def test_wrong_candidate_parent_rejected(self):
        self.candidate["target_directory_id"] = ins.OLD_PARENT
        self.approved["candidate"] = copy.deepcopy(self.candidate)
        with self.assertRaisesRegex(ValueError, "SCOPE"):
            ins.make_insert_plan(self.before, self.candidate, self.approved)

    def test_altered_old_body_rejected(self):
        self.after["q24_question"]["data"]["ocr_result"] += " changed"
        self.assert_hold()

    def test_changed_unshifted_old_frame_including_timestamp_rejected(self):
        for key, value in (("image_path", "changed"), ("updated_at", "2026-10-23T22:00:00"), ("verified", False)):
            after = copy.deepcopy(self.after)
            row = next(row for row in after["frames"]["data"] if row["order_in_level"] == "18")
            row[key] = value
            self.assertFalse(self.compare(after=after)["ok"])

    def test_duplicate_and_existing_uuid_rejected(self):
        for ident in (self.candidate["frames"][1]["planned_rect_id"], self.before["frames"]["data"][0]["rect_id"]):
            candidate = copy.deepcopy(self.candidate)
            candidate["frames"][0]["planned_rect_id"] = ident
            approved = dict(self.approved, candidate=candidate)
            with self.assertRaisesRegex(ValueError, "UUID"):
                ins.make_insert_plan(self.before, candidate, approved)

    def test_stale_before_body_or_page_rejected(self):
        for key in ("q23_answer", "page_173"):
            before = copy.deepcopy(self.before)
            before[key]["data"]["unexpected"] = True
            with self.assertRaises(ValueError):
                ins.check_prewrite(self.plan, before)

    def test_receipt_flags_unknown_fields_and_types_rejected(self):
        for key, value in (("success", 1), ("question_order", True), ("append_at_global_end", True), ("extra", False)):
            receipt = copy.deepcopy(self.receipt)
            receipt["data"][key] = value
            with self.assertRaises(ValueError):
                ins.decode_receipt(self.plan, receipt)

    def test_receipt_only_two_exact_node_layouts(self):
        for layout in (old.NODE_KEYS, old.OBSERVED_INSERTED_NODE_KEYS):
            receipt = copy.deepcopy(self.receipt)
            node = receipt["data"]["inserted_question_node"]
            receipt["data"]["inserted_question_node"] = {key: node[key] for key in layout}
            self.assertTrue(ins.decode_receipt(self.plan, receipt)["ok"])
        node = self.receipt["data"]["inserted_question_node"]
        self.receipt["data"]["inserted_question_node"] = dict(reversed(list(node.items())))
        with self.assertRaises(ValueError):
            ins.decode_receipt(self.plan, self.receipt)

    def test_receipt_and_directory_may_use_distinct_known_node_layouts(self):
        lessons = self.after["directory"]["data"]["directory_data"][0]["children"]
        node = lessons[1]["children"][0]
        lessons[1]["children"][0] = {key: node[key] for key in old.NODE_KEYS}
        self.assertTrue(self.compare()["ok"])
        lessons[1]["children"][0] = {key: node[key] for key in reversed(old.NODE_KEYS)}
        self.assert_hold()

    def test_receipt_cannot_reuse_any_directory_id(self):
        self.receipt["data"]["inserted_question_node"]["id"] = ins.DIRECTORY
        with self.assertRaises(ValueError):
            ins.decode_receipt(self.plan, self.receipt)

    def test_missing_window_or_wrong_timezone_or_old_new_timestamp_rejected(self):
        self.assertFalse(self.compare(send_window=None)["ok"])
        self.assertFalse(self.compare(send_window={"start": "2026-10-23T22:00:00Z", "end": "2026-10-23T22:00:01Z"})["ok"])
        self.after["q23_info"]["data"].update(created_at="2026-10-23T21:59:58", updated_at="2026-10-23T21:59:58")
        self.assert_hold()

    def test_tail_timestamp_monotonic_sendwindow_and_other_fields_strict(self):
        for key, value in (("updated_at", "2026-10-23T09:00:00"), ("updated_at", "2026-10-23T21:59:50"),
                           ("created_at", "2026-10-23T22:00:00"), ("tishi", "wenda")):
            after = copy.deepcopy(self.after)
            after["q24_info"]["data"][key] = value
            self.assertFalse(self.compare(after=after)["ok"])

    def test_only_two_created_zone_keyorders_full_types_values(self):
        for layout in ins.ZONE_ORDERS:
            after = copy.deepcopy(self.after)
            data = after["q23_question"]["data"]
            after["q23_question"]["data"] = {key: data[key] for key in layout}
            self.assertTrue(self.compare(after=after)["ok"])
        self.after["q23_question"]["data"]["success"] = 1
        self.assert_hold()

    def test_source_url_bbox_text_review_and_plan_tamper_rejected(self):
        mutations = [lambda c: c["frames"][0].update(image_path="https://wrong.invalid/x"),
                     lambda c: c["frames"][0].update(bbox=[0, 0, 1221, 1692]),
                     lambda c: c["zone_values"].update(answer="A"),
                     lambda c: c["review"].update(sha256="f" * 64)]
        for mutate in mutations:
            candidate = copy.deepcopy(self.candidate)
            mutate(candidate)
            approved = dict(self.approved, candidate=candidate)
            with self.assertRaises(ValueError):
                ins.make_insert_plan(self.before, candidate, approved)
        self.plan["payload_candidate"]["annotations_delete_rect_ids"] = ["old-id"]
        with self.assertRaisesRegex(ValueError, "TAMPERED"):
            ins.validate_insert_plan(self.plan)

    def test_no_skipping_logical_stage(self):
        candidate, approved = candidate_for(2)
        with self.assertRaises(ValueError):
            ins.make_insert_plan(self.before, candidate, approved)


if __name__ == "__main__":
    unittest.main()
