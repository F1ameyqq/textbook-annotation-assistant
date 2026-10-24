"""Synthetic fixtures only; no network, native IDs, writes or actual-save claims."""
import copy
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "src/annotation/runtime/usense_live/update.py"
spec = importlib.util.spec_from_file_location("usense_update_under_test", MODULE)
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


def response(data):
    return {"code": 0, "message": "success", "data": data}


def review(text):
    return {"text": text, "source_ref": "synthetic-source-image", "source_sha256": "a" * 64,
            "review_ref": "synthetic-reviewed-content", "reviewed_text_sha256": update.text_digest(text)}


def fixture(order=2):
    directory = [{"id": "synthetic-chapter", "label": "Synthetic chapter", "children": [
        {"id": "synthetic-lesson", "label": "Synthetic lesson", "children": [
            {"id": f"synthetic-node-{i}", "label": str(i), "isQuestion": True, "order_in_level": str(i),
             "unknown_node": {"keep": False}} for i in (1, 2, 3)]},
        {"id": "synthetic-other-lesson", "label": "Synthetic other lesson", "children": [
            {"id": "synthetic-node-4", "label": "4", "isQuestion": True, "order_in_level": "4"}]}]}]
    all_frames = []
    for i in (1, 2, 3, 4):
        zones = ("question", "answer", "analysis", "knowledge_point") if i == 3 else ("question", "choice", "answer")
        for zone in zones:
            all_frames.append({"type": zone, "rect_id": f"synthetic-{i}-{zone}", "file_id": "46007447",
                               "directory_id": "synthetic-other-lesson" if i == 4 else "synthetic-lesson",
                               "belong_to_level": "question_level", "order_in_level": str(i),
                               "image_order_in_annotation_zone": 0, "rect_bbox": "1,2,3,4", "page_index": i,
                               "image_path": f"synthetic-image-{i}", "unknown": {"bool": False, "float": 1.0},
                               "updated_at": "2026-10-15T00:00:00"})
    frames = [row for row in all_frames if row["order_in_level"] == str(order)]
    target = {"book_id": "46007447", "lesson_directory_id": "synthetic-other-lesson" if order == 4 else "synthetic-lesson",
              "node_id": f"synthetic-node-{order}", "info_id": f"synthetic-info-{order}", "question_order": order}
    zones = {zone: response(copy.deepcopy(update.ABSENT)) for zone in update.ZONES}
    for zone in ("question", "answer") + (("analysis", "knowledge_point") if order == 3 else ()):
        text = "" if zone == "knowledge_point" else f"synthetic existing {zone} {order} $x^2$"
        zones[zone] = response({"rect_ids": [f"synthetic-{order}-{zone}"], "ocr_result": text,
                                "success": True, "unknown": {"retained": None}})
    before = {"directory": response({"directory_data": directory, "unknown": {"a": 1, "b": False}}),
              "frames": response(all_frames), "annotations": response(frames),
              "info": response({"id": target["info_id"], "file_id": "46007447", "order_in_level": str(order),
                                "tishi": "synthetic-choice" if order != 3 else "synthetic-answer",
                                "tilei": None, "tihao": "", "tixu": None, "updated_at": "2026-10-15T00:00:00",
                                "unknown_info": {"type_sensitive": [1, 1.0, True]}}),
              "zones": zones}
    return before, target


class UsenseExistingQuestionTests(unittest.TestCase):
    def blocked(self, code, fn):
        with self.assertRaises(update.UpdateError) as result:
            fn()
        self.assertEqual(result.exception.code, code)

    def test_parameterized_q2_formula_two_zone_update(self):
        before, target = fixture(2)
        changes = {"question": review("题干 $a^2+b^2=c^2$（ ）"),
                   "choice": review("A. $\\sqrt{2}$\nB. 2\nC. 3\nD. 4")}
        plan = update.make_plan(before, target, changes)
        payload = plan["payload_candidate"]
        self.assertEqual(payload["question_order"], 2)
        self.assertIs(payload["is_new_question_insertion"], False)
        self.assertIsNone(payload["insert_after_order"])
        self.assertEqual(payload["annotations_upsert"], [])
        self.assertEqual(payload["annotations_delete_rect_ids"], [])
        self.assertEqual(payload["ocr_delete_zones"], [])
        self.assertEqual(payload["ocr_submissions"][1]["ocr_result"], changes["choice"]["text"])
        self.assertEqual(payload["ocr_submissions"][1]["rect_ids"], ["synthetic-2-choice"])
        self.assertTrue(update.compare_readback(plan, copy.deepcopy(plan["expected"]))["match"])

    def test_nonempty_html_and_markdown_image_references_cannot_be_removed(self):
        for image in ('<img src="https://synthetic.invalid/diagram?a=1&amp;b=2">',
                      '![图形](https://synthetic.invalid/signed(a).png?sig=keep)',
                      '![图形][diagram]\n[diagram]: https://synthetic.invalid/diagram.png'):
            with self.subTest(image=image):
                before, target = fixture()
                before["zones"]["question"]["data"]["ocr_result"] += "\n" + image
                self.blocked("EXISTING_IMAGE_REFERENCE_REMOVAL_FORBIDDEN",
                             lambda: update.make_plan(before, target, {"question": review("updated text without figure")}))
                plan = update.make_plan(before, target, {"question": review("updated text\n" + image)})
                self.assertTrue(plan["mutation_required"])

    def test_changed_image_url_or_missing_duplicate_is_rejected(self):
        before, target = fixture()
        image = '![diagram](https://synthetic.invalid/keep.png)'
        before["zones"]["question"]["data"]["ocr_result"] = image + "\n" + image
        for text in (image, image.replace("keep", "different") + "\n" + image):
            self.blocked("EXISTING_IMAGE_REFERENCE_REMOVAL_FORBIDDEN",
                         lambda: update.make_plan(before, target, {"question": review(text)}))

    def test_empty_broken_img_can_be_removed(self):
        before, target = fixture()
        before["zones"]["question"]["data"]["ocr_result"] = 'old <img src=""> text ![empty]()'
        self.assertTrue(update.make_plan(before, target, {"question": review("cleaned text")})["mutation_required"])

    def test_legacy_lossy_plan_is_history_only_never_new_writer_input(self):
        before, target = fixture()
        before["zones"]["question"]["data"]["ocr_result"] += ' ![figure](https://synthetic.invalid/figure)'
        legacy = update._make_plan(before, target, {"question": review("old defective approved text")}, protect_images=False)
        self.assertIs(update.validate_recorded_plan(legacy), legacy)
        self.assertTrue(update.compare_recorded_readback(legacy, legacy["expected"])["match"])
        self.blocked("EXISTING_IMAGE_REFERENCE_REMOVAL_FORBIDDEN", lambda: update.validate_plan(legacy))
        self.blocked("EXISTING_IMAGE_REFERENCE_REMOVAL_FORBIDDEN", lambda: update.compare_readback(legacy, legacy["expected"]))

    def test_existing_question_modes_allow_non_choice_text_zones(self):
        before, target = fixture(3)
        changes = {"question": review("解答：$x^2=4$"), "answer": review("$x=\\pm2$"),
                   "analysis": review("根据原图核对的解析"), "knowledge_point": review("平方根")}
        plan = update.make_plan(before, target, changes)
        self.assertEqual([row["zone"] for row in plan["payload_candidate"]["ocr_submissions"]], list(changes))
        self.assertTrue(update.json_same(plan["before"]["zones"]["choice"], plan["expected"]["zones"]["choice"]))

    def test_same_present_text_and_empty_string_are_noop(self):
        before, target = fixture(3)
        plan = update.make_plan(before, target, {"question": review(before["zones"]["question"]["data"]["ocr_result"]),
                                                 "knowledge_point": review("")})
        self.assertEqual(plan["mode"], "no-op")
        self.assertFalse(plan["mutation_required"])
        self.assertIsNone(plan["payload_candidate"])
        self.assertEqual(update.compare_readback(plan, copy.deepcopy(before))["status"], "NO_OP_CONFIRMED")

    def test_absent_and_empty_are_not_interchangeable(self):
        before, target = fixture(2)
        self.blocked("EMPTY_UPDATE_REQUIRES_EXPLICIT_CLEAR_PROTOCOL",
                     lambda: update.make_plan(before, target, {"choice": review("")}))
        self.blocked("EMPTY_UPDATE_REQUIRES_EXPLICIT_CLEAR_PROTOCOL",
                     lambda: update.make_plan(before, target, {"question": review("")}))

    def test_missing_zone_and_unknown_absence_never_filled(self):
        before, target = fixture()
        del before["zones"]["analysis"]
        self.blocked("FIVE_NATIVE_ZONES_REQUIRED", lambda: update.make_plan(before, target, {}))
        before, target = fixture()
        before["zones"]["analysis"]["data"] = {"success": False, "message": "server error"}
        self.blocked("OCR_ABSENCE_NOT_PROVEN", lambda: update.make_plan(before, target, {}))

    def test_no_new_zone_without_real_frame(self):
        before, target = fixture()
        self.blocked("ZONE_HAS_NO_SOURCE_FRAME", lambda: update.make_plan(before, target, {"analysis": review("new")}))

    def test_review_and_source_are_required_and_text_bound(self):
        before, target = fixture()
        for field, value, code in [("review_ref", "", "REVIEW_SOURCE_REQUIRED"),
                                    ("source_sha256", "bad", "SOURCE_HASH_REQUIRED"),
                                    ("reviewed_text_sha256", "0" * 64, "REVIEW_TEXT_HASH_MISMATCH")]:
            with self.subTest(field=field):
                item = review("new")
                item[field] = value
                self.blocked(code, lambda: update.make_plan(before, target, {"question": item}))

    def test_inputs_and_unknown_fields_remain_untouched(self):
        before, target = fixture()
        original = copy.deepcopy(before)
        plan = update.make_plan(before, target, {"question": review("new")})
        self.assertTrue(update.json_same(before, original))
        self.assertTrue(update.json_same(plan["expected"]["frames"], before["frames"]))
        self.assertTrue(update.json_same(plan["expected"]["zones"]["question"]["data"]["unknown"],
                                         before["zones"]["question"]["data"]["unknown"]))
        self.assertEqual(plan["payload_candidate"]["question_info"], {"tishi": "synthetic-choice", "tilei": None, "tihao": ""})

    def test_wrong_book_node_info_order_and_lesson_rejected(self):
        cases = [("book_id", "other", "TARGET_SCOPE"), ("node_id", "2", "TARGET_NODE_NOT_FOUND"),
                 ("info_id", "other", "INFO_IDENTITY_MISMATCH"), ("question_order", 3, "FRONTEND_ORDER_MISMATCH"),
                 ("lesson_directory_id", "other", "WRONG_LESSON_DIRECTORY")]
        for field, value, code in cases:
            with self.subTest(field=field):
                before, target = fixture()
                target[field] = value
                self.blocked(code, lambda: update.make_plan(before, target, {}))

    def test_other_lesson_target_requires_its_current_identity(self):
        before, target = fixture(4)
        plan = update.make_plan(before, target, {"question": review("new")})
        self.assertEqual(plan["payload_candidate"]["target_directory_id"], "synthetic-other-lesson")
        self.assertEqual(plan["payload_candidate"]["question_order"], 4)

    def test_stale_before_full_frames_or_other_directory_field_rejected(self):
        before, target = fixture()
        plan = update.make_plan(before, target, {"question": review("new")})
        fresh = copy.deepcopy(before)
        fresh["frames"]["data"][-1]["unknown"]["bool"] = True
        self.assertFalse(update.check_prewrite(plan, fresh)["match"])
        fresh = copy.deepcopy(before)
        fresh["directory"]["data"]["unknown"]["a"] = 2
        self.assertFalse(update.check_prewrite(plan, fresh)["match"])

    def test_new_question_extra_frames_and_old_field_changes_rejected(self):
        before, target = fixture()
        plan = update.make_plan(before, target, {"question": review("new")})
        for category in ("extra_frame", "extra_node", "extra_zone", "info_unknown", "frame_timestamp"):
            with self.subTest(category=category):
                after = copy.deepcopy(plan["expected"])
                if category == "extra_frame":
                    after["frames"]["data"].append({"rect_id": "synthetic-added"})
                elif category == "extra_node":
                    after["directory"]["data"]["directory_data"].append({"id": "synthetic-added"})
                elif category == "extra_zone":
                    after["zones"]["answer"]["data"]["ocr_result"] = "different"
                elif category == "info_unknown":
                    after["info"]["data"]["tixu"] = ""
                else:
                    after["annotations"]["data"][0]["updated_at"] = "2026-10-23T00:00:00"
                self.assertFalse(update.compare_readback(plan, after)["match"])

    def test_only_info_timestamp_can_advance_after_update(self):
        before, target = fixture()
        plan = update.make_plan(before, target, {"question": review("new")})
        after = copy.deepcopy(plan["expected"])
        after["info"]["data"]["updated_at"] = "2026-10-23T00:00:00"
        self.assertTrue(update.compare_readback(plan, after)["match"])
        for value in ("2025-10-15T00:00:00", "2026-10-23T00:00:00+08:00", None):
            after["info"]["data"]["updated_at"] = value
            self.assertFalse(update.compare_readback(plan, after)["match"])

    def test_noop_does_not_allow_even_timestamp_changes(self):
        before, target = fixture()
        plan = update.make_plan(before, target, {})
        after = copy.deepcopy(before)
        after["info"]["data"]["updated_at"] = "2026-10-23T00:00:00"
        self.assertFalse(update.compare_readback(plan, after)["match"])

    def test_type_and_key_order_remain_strict(self):
        before, target = fixture()
        plan = update.make_plan(before, target, {"question": review("new")})
        after = copy.deepcopy(plan["expected"])
        after["frames"]["data"][-1]["unknown"]["float"] = 1
        self.assertFalse(update.compare_readback(plan, after)["match"])
        after = copy.deepcopy(plan["expected"])
        values = after["zones"]["question"]["data"]
        after["zones"]["question"]["data"] = {key: values[key] for key in reversed(values)}
        self.assertFalse(update.compare_readback(plan, after)["match"])

    def test_ledger_identity_does_not_change_with_new_plan(self):
        before, target = fixture()
        first = update.make_plan(before, target, {"question": review("first")})
        second = update.make_plan(before, target, {"question": review("second")})
        self.assertNotEqual(first["plan_sha256"], second["plan_sha256"])
        self.assertEqual(first["ledger_key"], second["ledger_key"])

    def test_plan_tampering_and_geometry_updates_rejected(self):
        before, target = fixture()
        self.blocked("ZONE_CHANGE_FORBIDDEN", lambda: update.make_plan(before, target, {"frames": review("new")}))
        plan = update.make_plan(before, target, {"question": review("new")})
        plan["payload_candidate"]["annotations_upsert"] = [{"rect_id": "x"}]
        self.blocked("PLAN_TAMPERED", lambda: update.check_prewrite(plan, before))

    def test_duplicate_native_ids_and_ambiguous_frame_order_rejected(self):
        before, target = fixture()
        before["frames"]["data"].append(copy.deepcopy(before["frames"]["data"][0]))
        self.blocked("DUPLICATE_FRAME_ID", lambda: update.make_plan(before, target, {}))
        before, target = fixture()
        rows = before["directory"]["data"]["directory_data"][0]["children"][0]["children"]
        rows.append(copy.deepcopy(rows[0]))
        self.blocked("DUPLICATE_DIRECTORY_ID", lambda: update.make_plan(before, target, {}))

    def test_legacy_flat_map_is_lossless(self):
        before, _ = fixture()
        flat = {"directory": before["directory"], "frames": before["frames"],
                "q1_annotations": before["annotations"], "q1_info": before["info"]}
        flat.update({"q1_" + zone: value for zone, value in before["zones"].items()})
        self.assertTrue(update.json_same(update.from_captured_map(flat), before))

    def test_json_duplicates_nonfinite_and_boolean_order_rejected(self):
        self.blocked("DUPLICATE_JSON_KEY", lambda: update.loads('{"x":1,"x":2}'))
        self.blocked("NONFINITE_JSON", lambda: update.loads('{"x":NaN}'))
        before, target = fixture()
        target["question_order"] = True
        self.blocked("TARGET_IDENTITY", lambda: update.make_plan(before, target, {}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
