"""Batch integrity faults using tiny sources and an explicit synthetic worker.

These tests exercise bookkeeping and source ownership, never OCR accuracy or
whole-book acceptance. Expected source order is fixed independently of SQL.
"""
from __future__ import annotations

import copy
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from annotation.recognition.baseline import digest, file_digest
from annotation.recognition.batch import run_batch
from annotation.recognition.batch_quality import audit_batch


def synthetic_worker(source_path, *, use_ocr=False):
    """An explicitly invented worker; regions encode source identity, not OCR."""
    source = json.loads(Path(source_path).read_text(encoding="utf-8"))
    asset = source["assets"][0]
    aid = asset["asset_id"]
    crop_id = aid+"/synthetic-crop"
    page = {"asset_id": aid, "source": copy.deepcopy(asset),
            "regions": [{"region_id":aid+"/synthetic-region", "asset_id":aid, "bbox":[10,10,90,30],
                         "crop_id":crop_id, "content_type":"unknown", "role_candidate":None,
                         "confidence":None, "text_hint":"", "text_hint_is_final_transcription":False,
                         "verification_status":"UNVERIFIED"}],
            "crop_transforms":[{"crop_id":crop_id, "asset_id":aid, "original_bbox":[0,0,100,60],
                                "crop_to_original":[[1,0,0],[0,1,0],[0,0,1]]}],
            "ocr_lines":[], "split_info":{"synthetic":True}, "issues":[],
            "coverage_evidence":{"method":"SYNTHETIC_TEST", "independent_of_recognizer":False,
                                 "can_authorize_quality_pass":False,"lines":[]}}
    payload = {"pages":[page], "quality_decision":"NOT_EVALUATED", "limitations":["SYNTHETIC_TEST"]}
    return {"schema_version":"b-evidence-trial/0.1", "kind":"EvidenceBundleTrial",
            "artifact_id":"synthetic-result-"+digest(source)[:24], "revision":1,
            "book_id":source["book_id"], "scope_id":source["scope_id"],
            "input_refs":[{"artifact_id":source["artifact_id"],"content_hash":digest(source)}],
            "producer":{"module":__name__,"version":"synthetic-test-only","ocr_enabled":use_ocr},
            "content_hash":digest(payload),"payload":payload}


synthetic_worker.cache_identity = {"purpose":"SYNTHETIC_TEST", "fixture_version":1}


class BatchQualityRegression(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root/"run"
        assets = []
        # Deliberately unsorted declaration: expected processing order is b,c,a.
        for aid, order in (("page-a",20),("page-b",5),("page-c",11)):
            image = Image.new("RGB",(100,60),"white")
            ImageDraw.Draw(image).rectangle([10,10,70+order,30], fill="black")
            path = self.root/(aid+".png")
            image.save(path)
            assets.append({"asset_id":aid,"path":path.name,"sha256":file_digest(path),
                           "width":100,"height":60,"reading_order":order})
        self.source = {"schema_version":"b-source-trial/0.1","artifact_id":"synthetic-source",
                       "book_id":"synthetic-book","scope_id":"synthetic-declared-scope","assets":assets}
        self.source_path = self.root/"source.json"
        self.save_source()

    def save_source(self):
        self.source_path.write_text(json.dumps(self.source),encoding="utf-8")

    def batch(self, **kwargs):
        return run_batch(self.source_path,self.work,worker=synthetic_worker,**kwargs)

    def check(self, report):
        return audit_batch(self.source_path,self.work,report)["payload"]

    def assertCode(self, report, code):
        checked = self.check(report)
        self.assertFalse(checked["accepted"],checked)
        self.assertIn(code,{i["code"] for i in checked["issues"]},checked)
        self.assertEqual(checked["decision"],"HOLD")

    def sql(self, statement, values=()):
        with closing(sqlite3.connect(self.work/"batch.sqlite3")) as db:
            with db:
                db.execute(statement,values)

    def put_object(self, value):
        """Fault helper creates a NEW address; it does not overwrite old bytes."""
        value["content_hash"] = digest(value["payload"])
        prefixes = {"BatchItemTrial":"batch-item-", "EvidenceBundleTrial":"batch-evidence-"}
        if value["kind"] in prefixes:
            value["artifact_id"] = prefixes[value["kind"]]+digest(value["payload"])[:24]
        data = json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
        sha = hashlib.sha256(data).hexdigest()
        relative = "objects/"+sha+".json"
        (self.work/relative).write_bytes(data)
        return {"path":relative,"sha256":sha,"artifact_ref":{k:value[k]for k in ("artifact_id","revision","content_hash")}}

    def read_object(self, descriptor):
        return json.loads((self.work/descriptor["path"]).read_text(encoding="utf-8"))

    def replace_descriptor(self, previous, current):
        """Coordinated fault updates journal copies, not just the report hash."""
        def replace(value):
            if isinstance(value,dict):
                if all(value.get(k) == v for k,v in previous.items()):
                    return {**value,**copy.deepcopy(current)}
                return {k:replace(v)for k,v in value.items()}
            if isinstance(value,list): return [replace(v)for v in value]
            return value
        with closing(sqlite3.connect(self.work/"batch.sqlite3")) as db:
            with db:
                for table,column,pk in (("items","artifact_json","rowid"),("attempts","artifact_json","attempt_id"),
                                        ("cache_entries","artifact_json","item_key"),("jobs","bundle_json","job_id"),
                                        ("events","details_json","event_id")):
                    for key,text in db.execute(f"SELECT {pk},{column} FROM {table}").fetchall():
                        if text:
                            changed = replace(json.loads(text))
                            db.execute(f"UPDATE {table} SET {column}=? WHERE {pk}=?",(json.dumps(changed),key))

    def publish_report_fault(self, report):
        report["content_hash"] = digest(report["payload"])
        report["artifact_id"] = "batch-report-"+digest([report["input_refs"],report["producer"],report["payload"],report["run_id"]])[:24]
        descriptor = self.put_object(report)
        with closing(sqlite3.connect(self.work/"batch.sqlite3")) as db:
            with db:
                for eid,text in db.execute("SELECT event_id,details_json FROM events WHERE event_type='RUN_FINISHED'").fetchall():
                    details = json.loads(text)
                    if details.get("run_id") == report["run_id"]:
                        details.update(report_ref=descriptor["artifact_ref"],report_artifact=descriptor)
                        db.execute("UPDATE events SET details_json=? WHERE event_id=?",(json.dumps(details),eid))

    def coherent_item_fault(self, report, index, mutate):
        old_item = report["payload"]["items"][index]["artifact"]
        retained = self.read_object(old_item)
        mutate(retained)
        new_item = self.put_object(retained)
        self.replace_descriptor(old_item,new_item)
        report["payload"]["items"][index]["artifact"] = new_item
        old_bundle = report["payload"]["bundle"]
        bundle = self.read_object(old_bundle)
        bundle["payload"]["pages"][index] = copy.deepcopy(retained["payload"]["result"]["payload"]["pages"][0])
        bundle["payload"]["batch_binding"]["per_page_refs"][index].update(new_item)
        new_bundle = self.put_object(bundle)
        self.replace_descriptor(old_bundle,new_bundle)
        report["payload"]["bundle"] = new_bundle
        self.publish_report_fault(report)

    def test_declared_three_page_scope_order_and_synthetic_mode_stay_hold(self):
        report = self.batch()
        checked = self.check(report)
        self.assertTrue(checked["accepted"],checked)
        self.assertEqual(report["payload"]["declared_asset_ids"],["page-b","page-c","page-a"])
        self.assertEqual(checked["summary"]["completed_asset_count"],3)
        self.assertEqual(checked["summary"]["execution_kind"],"SYNTHETIC_TEST")
        self.assertEqual(checked["decision"],"HOLD")
        self.assertFalse(checked["business_acceptance"])
        self.assertEqual(checked["platform_actions"],[])

    def test_max_items_limits_work_without_shrinking_scope_then_resumes(self):
        partial = self.batch(max_items=1)
        checked = self.check(partial)
        self.assertTrue(checked["accepted"],checked)
        self.assertEqual(partial["payload"]["counts"],{"declared":3,"done":1,"pending":2,"failed":0,"invalidated":0,"cache_hits":0})
        self.assertFalse(partial["payload"]["batch_complete"])
        self.assertIsNone(partial["payload"]["bundle"])
        complete = self.batch()
        self.assertTrue(self.check(complete)["accepted"],self.check(complete))
        self.assertEqual(len(complete["payload"]["items"]),3)

    def test_repeat_run_uses_traceable_cache_not_duplicate_attempts(self):
        self.batch()
        report = self.batch()
        checked = self.check(report)
        self.assertTrue(checked["accepted"],checked)
        self.assertEqual(report["payload"]["counts"]["cache_hits"],3)
        self.assertEqual(checked["summary"]["attempt_count"],3)

    def test_quality_does_not_run_or_import_the_batch_worker(self):
        report = self.batch()
        snapshot = copy.deepcopy(report)
        with mock.patch("annotation.recognition.batch.run_batch",side_effect=AssertionError("producer rerun")):
            self.assertTrue(self.check(report)["accepted"])
        self.assertEqual(report,snapshot)
        module = sys.modules["annotation.recognition.batch_quality"]
        self.assertNotIn("from .batch import",Path(module.__file__).read_text(encoding="utf-8"))

    def test_source_byte_changes_are_not_hidden_by_sql_done(self):
        report = self.batch()
        (self.root/"page-c.png").write_bytes(b"changed-source")
        self.assertCode(report,"BATCH_SOURCE_INVALID")

    def test_report_cannot_omit_a_declared_page_even_with_rehashed_counts(self):
        report = self.batch()
        report["payload"]["items"].pop()
        report["payload"]["declared_asset_ids"].pop()
        report["payload"]["counts"]["declared"] = 2
        report["payload"]["counts"]["done"] = 2
        report["content_hash"] = digest(report["payload"])
        self.assertCode(report,"BATCH_DECLARED_SCOPE_INCOMPLETE")

    def test_missing_sql_item_cannot_still_claim_full_batch(self):
        report = self.batch()
        self.sql("DELETE FROM items WHERE asset_id=?",("page-c",))
        self.assertCode(report,"BATCH_JOURNAL_ITEM_SCOPE_MISMATCH")

    def test_exchanged_perpage_artifacts_do_not_match_source_owners(self):
        report = self.batch()
        first, second = report["payload"]["items"][:2]
        first["artifact"], second["artifact"] = second["artifact"], first["artifact"]
        report["content_hash"] = digest(report["payload"])
        self.assertCode(report,"BATCH_REPORT_ITEM_JOURNAL_MISMATCH")

    def test_damaged_immutable_object_is_rejected_then_invalidated_and_recovered(self):
        report = self.batch()
        path = self.work/report["payload"]["items"][0]["artifact"]["path"]
        path.write_text("{}",encoding="utf-8")
        self.assertCode(report,"BATCH_ITEM_ARTIFACT_INVALID")
        recovered = self.batch()
        self.assertTrue(self.check(recovered)["accepted"],self.check(recovered))
        self.assertGreater(recovered["payload"]["counts"]["invalidated"],0)

    def test_deleted_attempt_history_cannot_be_replaced_by_done_flag(self):
        report = self.batch()
        self.sql("DELETE FROM attempts WHERE asset_id=?",("page-c",))
        self.assertCode(report,"BATCH_SUCCESS_PROVENANCE_MISSING")

    def test_missing_terminal_event_is_not_reconstructed_from_attempt_state(self):
        report = self.batch()
        self.sql("DELETE FROM events WHERE asset_id=? AND event_type='ATTEMPT_SUCCEEDED'",("page-c",))
        self.assertCode(report,"BATCH_ATTEMPT_EVENT_MISMATCH")

    def test_forged_cache_hit_needs_a_current_run_event(self):
        report = self.batch()
        report["payload"]["items"][0]["cache_hit"] = True
        report["payload"]["counts"]["cache_hits"] = 1
        report["content_hash"] = digest(report["payload"])
        self.assertCode(report,"BATCH_CACHE_EVENT_MISMATCH")

    def test_partial_run_cannot_publish_a_bundle_or_claim_complete(self):
        report = self.batch(max_items=1)
        report["payload"]["batch_complete"] = True
        report["content_hash"] = digest(report["payload"])
        self.assertCode(report,"BATCH_FALSE_COMPLETENESS")

    def test_mixed_execution_and_fabricated_business_acceptance_reject(self):
        report = self.batch()
        report["payload"]["recognizer"]["execution_kind"] = "BASELINE_CPU_OCR"
        report["content_hash"] = digest(report["payload"])
        self.assertCode(report,"BATCH_EXECUTION_KIND_MISMATCH")
        report = self.batch()
        report["payload"]["business_acceptance"] = True
        report["content_hash"] = digest(report["payload"])
        self.assertCode(report,"BATCH_FALSE_VERIFICATION")

    def test_code_version_receipt_must_match_current_source_not_sql_claim(self):
        report = self.batch()
        report["payload"]["recognizer"]["code"]["batch"] = "0"*64
        report["content_hash"] = digest(report["payload"])
        self.assertCode(report,"BATCH_CURRENT_VERSION_MISMATCH")

    def test_mixed_page_owner_rejects_even_when_files_ledger_report_and_merge_agree(self):
        report = self.batch()
        def mutate(retained):
            result = retained["payload"]["result"]
            result["payload"]["pages"][0]["regions"][0]["asset_id"] = "page-c"
            result["content_hash"] = digest(result["payload"])
        self.coherent_item_fault(report,0,mutate)
        self.assertCode(report,"BATCH_PAGE_SOURCE_OWNERSHIP_MISMATCH")

    def test_duplicate_region_identity_across_pages_rejects_coordinated_republication(self):
        report = self.batch()
        def mutate(retained):
            result = retained["payload"]["result"]
            result["payload"]["pages"][0]["regions"][0]["region_id"] = "page-b/synthetic-region"
            result["content_hash"] = digest(result["payload"])
        self.coherent_item_fault(report,1,mutate)
        self.assertCode(report,"BATCH_REGION_ID_REUSED")

    def test_wrong_origin_attempt_cannot_be_made_valid_by_rehashing_all_copies(self):
        report = self.batch()
        self.coherent_item_fault(report,0,lambda value:value["payload"].update(attempt_id="not-a-real-attempt"))
        self.assertCode(report,"BATCH_SUCCESS_PROVENANCE_MISSING")

    def test_merged_pages_must_equal_the_actual_per_page_objects_in_source_order(self):
        report = self.batch()
        original = report["payload"]["bundle"]
        bundle = self.read_object(original)
        bundle["payload"]["pages"].reverse()
        modified = self.put_object(bundle)
        self.replace_descriptor(original,modified)
        report["payload"]["bundle"] = modified
        self.publish_report_fault(report)
        self.assertCode(report,"BATCH_MERGED_PAGE_MISMATCH")

    def test_failed_attempt_is_traceable_and_next_call_retries_without_losing_scope(self):
        remaining = [True]
        def once_failing_worker(source_path,*,use_ocr=False):
            if remaining:
                remaining.pop()
                raise RuntimeError("labelled synthetic one-time failure")
            return synthetic_worker(source_path,use_ocr=use_ocr)
        once_failing_worker.cache_identity = {"purpose":"SYNTHETIC_TEST","case":"failure-retry"}
        failed = run_batch(self.source_path,self.work,worker=once_failing_worker)
        self.assertTrue(self.check(failed)["accepted"],self.check(failed))
        self.assertEqual(failed["payload"]["counts"]["failed"],1)
        self.assertFalse(failed["payload"]["batch_complete"])
        recovered = run_batch(self.source_path,self.work,worker=once_failing_worker)
        self.assertTrue(self.check(recovered)["accepted"],self.check(recovered))
        self.assertEqual(self.check(recovered)["summary"]["attempt_count"],4)

    def test_interrupted_attempt_must_be_closed_before_successful_resume(self):
        remaining = [True]
        def once_interrupted_worker(source_path,*,use_ocr=False):
            if remaining:
                remaining.pop()
                raise KeyboardInterrupt("labelled synthetic process interruption")
            return synthetic_worker(source_path,use_ocr=use_ocr)
        once_interrupted_worker.cache_identity = {"purpose":"SYNTHETIC_TEST","case":"interruption-retry"}
        with self.assertRaises(KeyboardInterrupt):
            run_batch(self.source_path,self.work,worker=once_interrupted_worker)
        recovered = run_batch(self.source_path,self.work,worker=once_interrupted_worker)
        checked = self.check(recovered)
        self.assertTrue(checked["accepted"],checked)
        self.assertEqual(checked["summary"]["attempt_count"],4)
        with closing(sqlite3.connect(self.work/"batch.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM attempts WHERE state='INTERRUPTED'").fetchone()[0],1)

    def test_new_worker_version_cannot_claim_old_cache_as_current_execution(self):
        self.batch()
        original = copy.deepcopy(synthetic_worker.cache_identity)
        self.addCleanup(setattr,synthetic_worker,"cache_identity",original)
        synthetic_worker.cache_identity = {**original,"fixture_version":2}
        report = self.batch()
        checked = self.check(report)
        self.assertTrue(checked["accepted"],checked)
        self.assertEqual(report["payload"]["counts"]["cache_hits"],0)
        self.assertEqual(report["payload"]["counts"]["invalidated"],3)
        self.assertEqual(checked["summary"]["attempt_count"],3)

    def test_run_report_must_be_bound_to_the_actual_finished_event_and_file(self):
        report = self.batch()
        report["run_id"] = "batch-run-forged"
        self.assertCode(report,"BATCH_RUN_EVENT_MISMATCH")

    def test_malformed_journal_json_returns_rejection_without_crashing_or_locking_db(self):
        report = self.batch()
        self.sql("UPDATE items SET asset_json=? WHERE asset_id=?",("{invalid","page-c"))
        self.assertCode(report,"BATCH_PERSISTED_DATA_INVALID")
        self.assertEqual(self.check(report),self.check(report))


if __name__ == "__main__":
    unittest.main()
