"""New finite boundary only; synthetic fixtures, no old suite or live actions."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("synthetic_update_fixture", Path(__file__).with_name("test_usense_live_update.py"))
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
fixture, response, review, update = fixtures.fixture, fixtures.response, fixtures.review, fixtures.update


class A25CreatedZoneReconciliationTests(unittest.TestCase):
    def example(self):
        before, target = fixture(3)
        second = copy.deepcopy(next(f for f in before["annotations"]["data"] if f["type"] == "question"))
        second["rect_id"] += "-second"
        second["image_order_in_annotation_zone"] = 1
        before["annotations"]["data"].append(copy.deepcopy(second))
        before["frames"]["data"].append(copy.deepcopy(second))
        for zone in ("question", "answer"):
            before["zones"][zone] = response(copy.deepcopy(update.ABSENT))
        plan = update.make_plan(before, target, {"question": review("question with $x^2$ and image"),
                                                 "answer": review("4")})
        after = copy.deepcopy(plan["expected"])
        for zone in ("question", "answer"):
            data = after["zones"][zone]["data"]
            after["zones"][zone]["data"] = {key: data[key] for key in ("success", "ocr_result", "rect_ids")}
        after["info"]["data"]["updated_at"] = "2026-10-15T01:00:00"
        return plan, after

    def test_only_observed_new_zone_order_reconciles_and_original_failure_stays(self):
        plan, after = self.example()
        before_plan, before_after = update.digest(plan), update.digest(after)
        result = update.reconcile_first_created_zone_key_order(plan, after)
        self.assertTrue(result["match"])
        self.assertFalse(result["strict_comparison"]["match"])
        self.assertEqual(len(result["strict_comparison"]["differences"]), 2)
        self.assertEqual(len(result["expected_key_order_adjustments"]), 2)
        self.assertEqual(result["comparison_after_limited_expected_key_order"]["after_sha256"], before_after)
        self.assertFalse(result["new_send_authorized"])
        self.assertFalse(result["ledger_accepted_by_this_function"])
        self.assertEqual(before_plan, update.digest(plan))
        self.assertEqual(before_after, update.digest(after))
        self.assertFalse(update.compare_readback(plan, after)["match"])

    def test_types_values_unknown_fields_arrays_text_and_other_orders_stay_strict(self):
        mutations = [
            lambda a: a["zones"]["question"]["data"].update(ocr_result="changed"),
            lambda a: a["zones"]["question"]["data"].update(ocr_result="question with $x^2$ and image "),
            lambda a: a["zones"]["answer"]["data"].update(ocr_result=4),
            lambda a: a["zones"]["answer"]["data"].update(success=1),
            lambda a: a["zones"]["answer"]["data"].update(unknown="new field"),
            lambda a: a["zones"]["question"]["data"]["rect_ids"].reverse(),
            lambda a: a["zones"]["question"]["data"]["rect_ids"].append("extra"),
            lambda a: a["zones"]["question"]["data"].pop("success"),
            lambda a: a["info"]["data"]["unknown_info"].update(type_sensitive=[1, True, 1.0]),
            lambda a: a["info"]["data"].update(updated_at="2026-10-14T00:00:00"),
            lambda a: a["frames"]["data"].reverse(),
            lambda a: a["directory"]["data"]["unknown"].update(b=0),
            lambda a: a["zones"]["analysis"]["data"].pop("unknown"),
            lambda a: a["zones"]["analysis"].update(code=1),
            lambda a: a["zones"]["analysis"].update(data=dict(reversed(list(a["zones"]["analysis"]["data"].items())))),
            lambda a: a["zones"]["question"].update(data={key: a["zones"]["question"]["data"][key]
                                                       for key in ("ocr_result", "success", "rect_ids")}),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                plan, after = self.example()
                mutate(after)
                self.assertFalse(update.reconcile_first_created_zone_key_order(plan, after)["match"])

    def test_existing_zone_order_is_never_normalized(self):
        before, target = fixture(3)
        before["zones"]["question"]["data"].pop("unknown")
        plan = update.make_plan(before, target, {"question": review("new existing question")})
        after = copy.deepcopy(plan["expected"])
        data = after["zones"]["question"]["data"]
        after["zones"]["question"]["data"] = {key: data[key] for key in ("success", "ocr_result", "rect_ids")}
        result = update.reconcile_first_created_zone_key_order(plan, after)
        self.assertFalse(result["match"])
        self.assertEqual(result["expected_key_order_adjustments"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
