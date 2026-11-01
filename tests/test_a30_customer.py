"""New A30 controls. Fresh ordinary source materials; no old book/OCR replay."""
from pathlib import Path
import copy
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from annotation.customer.store import Store, Hold, digest
from annotation.customer.prepare import prepare, resume, candidate_hash
from annotation.customer.source import page_numbers
from annotation.customer.review import CustomerReviewWorkspace
from annotation.customer.native_plan import make_plan, compare_readback, check_prewrite, source_key, ZONES
from annotation.customer.production import produce, reconcile


def response(data):
    return {"code": 0, "message": "success", "data": data}


def empty_native(book, pages, lesson="Geometry elsewhere"):
    return {"schema": "CustomerNativeSnapshot/v1", "book_id": book,
        "directory": response({"directory_data": [
            {"id": "chapter", "label": "Chapter nine", "children": [
                {"id": "new-lesson", "label": lesson, "children": []},
                {"id": "later-lesson", "label": "Later", "children": []}]}]}),
        "frames": response([]), "questions": {}, "pages": pages}


def apply_native(before, plan, serial):
    """Synthetic server implementation, deliberately independent of comparator."""
    after = copy.deepcopy(before)
    order = plan["new_order"]
    parent = after["directory"]["data"]["directory_data"][0]["children"][0]
    node = {"id": "server-node-" + str(serial), "label": str(order), "isQuestion": True,
            "order_in_level": str(order), "children": []}
    parent["children"].append(node)
    frames = []
    for frame in plan["payload"]["annotations_upsert"]:
        frames.append({**copy.deepcopy(frame), "file_id": before["book_id"], "user_id": "server-actor", "verified": 0,
                       "created_at": "2026-10-24T08:00:00", "updated_at": "2026-10-24T08:00:00"})
    after["frames"]["data"].extend(frames)
    zones = {zone: response({"success": False}) for zone in ZONES}
    for submission in plan["payload"]["ocr_submissions"]:
        zones[submission["zone"]] = response({"success": True, "ocr_result": submission["ocr_result"], "rect_ids": submission["rect_ids"]})
    after["questions"][node["id"]] = {"info": response({"id": "server-info-" + str(serial), "file_id": before["book_id"],
        "order_in_level": str(order), "tixu": None, "created_at": "2026-10-24T08:00:00", "updated_at": "2026-10-24T08:00:00",
        **plan["payload"]["question_info"]}), "annotations": response(frames), "zones": zones}
    receipt = response({"inserted": True, "question_order": order, "inserted_question_node": node,
                        "success": True, "append_at_global_end": True})
    return after, receipt


class OrdinaryInputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "workspace")
        self.q = self.root / "questions.txt"
        self.a = self.root / "answers.txt"
        self.q.write_text("1. Which letter comes first?\nA. Alpha\nB. Bravo\nC. Charlie\nD. Delta\n2. State a colour.\n", encoding="utf-8")
        self.a.write_text("1. A\n2. Blue\n", encoding="utf-8")

    def run_input(self, **extra):
        return prepare(self.store, book="782135", lesson="Unit seventeen", question_files=[self.q],
                       answer_files=[self.a], **extra)

    def test_plain_materials_assemble_without_candidate_or_manifest(self):
        job = self.run_input()
        self.assertEqual(len(job["candidates"]), 2)
        self.assertEqual(job["candidates"][0]["zones"]["answer"], "A")
        self.assertEqual(job["candidates"][1]["zones"]["answer"], "Blue")
        self.assertEqual(job["status"], "PREPARED_OFFLINE")
        self.assertFalse(job["customer_ready"])
        self.assertEqual(job["metrics"]["new_model_pages"], 0)

    def test_exact_selection_resumes_same_job(self):
        first = self.run_input()
        second = self.run_input()
        self.assertEqual(first, second)

    def test_missing_answer_remains_hold(self):
        self.a.write_text("1. A\n", encoding="utf-8")
        job = self.run_input()
        self.assertEqual(job["status"], "NEEDS_REVIEW")
        self.assertIn("ANSWER_MISSING_OR_AMBIGUOUS", job["candidates"][1]["issues"])

    def test_ordinary_page_range_selects_text_page(self):
        self.q.write_text("1. Ignore this page.\f7. State a colour.\n", encoding="utf-8")
        self.a.write_text("7. Green\n", encoding="utf-8")
        job = self.run_input(question_pages="2")
        self.assertEqual([q["printed_number"] for q in job["candidates"]], ["7"])
        self.assertEqual(job["candidates"][0]["zones"]["answer"], "Green")

    def test_duplicate_numbers_are_not_silently_merged(self):
        self.q.write_text("1. First question.\n1. Another question.\n", encoding="utf-8")
        job = self.run_input()
        self.assertTrue(all("DUPLICATE_PRINTED_NUMBER" in q["issues"] for q in job["candidates"]))

    def test_unknown_intent_cannot_be_retried(self):
        self.store.begin("save", "abc")
        with self.assertRaises(Hold):
            self.store.begin("save", "abc")
        self.assertEqual(self.store.operation("save", "abc")["state"], "INTENT")

    def test_book_lock_is_exclusive(self):
        with self.store.book_lock("782135"):
            with self.assertRaises(Hold):
                with self.store.book_lock("782135"):
                    self.fail("book ownership duplicated")

    def test_review_edit_invalidates_previous_content_and_reuses_ui(self):
        job = self.run_input()
        workspace = CustomerReviewWorkspace(self.store, job["id"])
        state = workspace.state()
        key = state["answers"][1]["answer_id"]
        workspace.save({"expected_head": state["head"], "answer_id": key,
            "changes": [{"key": key + ":answer", "text": "Green", "format": "plain"}]})
        updated, _ = self.store.job(job["id"])
        self.assertEqual(updated["candidates"][1]["content_status"], "NEEDS_REVIEW")
        self.assertEqual(workspace.state()["decision"], "HOLD")
        current = workspace.state()
        workspace.confirm({"expected_head": current["head"], "answer_id": key,
                           "source_checked": True, "content_checked": True})
        updated, _ = self.store.job(job["id"])
        self.assertEqual(updated["candidates"][1]["content_status"], "READY_CUSTOMER_REVIEWED")

    def test_source_mutation_blocks_review(self):
        job = self.run_input()
        Path(job["pages"][0]["raw_path"]).write_text("changed", encoding="utf-8")
        from annotation.recognition.content_review import SourceChanged
        with self.assertRaises(SourceChanged):
            CustomerReviewWorkspace(self.store, job["id"]).state()

    def test_page_ranges_reject_duplicate_or_reverse(self):
        for value in ("2,1", "1-2,2", "9", "0", "2-1"):
            with self.subTest(value=value), self.assertRaises(Hold):
                page_numbers(value, 4)


class ImageAndProduction(unittest.TestCase):
    setUp = OrdinaryInputs.setUp

    def image_job(self):
        from PIL import Image, ImageDraw
        q, a = self.root / "unseen-q.png", self.root / "unseen-a.png"
        for path, colour in ((q, "black"), (a, "navy")):
            image = Image.new("RGB", (600, 800), "white")
            ImageDraw.Draw(image).rectangle((30, 40, 300, 55), fill=colour)
            image.save(path)
        def synthetic_ocr(store, page, book, **kwargs):
            strings = ["4. State a colour.", "5. State an animal."] if page["role"] == "question" else ["4. 红色", "5. 猫"]
            return [{"text": value, "bbox": [30, 40 + i * 40, 300, 60 + i * 40], "score": .99}
                    for i, value in enumerate(strings)], "SYNTHETIC_CACHE"
        with patch("annotation.customer.prepare.ocr_page", side_effect=synthetic_ocr):
            job = prepare(self.store, book="981452", lesson="Geometry elsewhere", question_files=[q], answer_files=[a],
                          question_first_page=42, answer_first_page=109)
        self.assertEqual(job["status"], "NEEDS_REVIEW")
        workspace = CustomerReviewWorkspace(self.store, job["id"])
        for candidate in job["candidates"]:
            state = workspace.state()
            workspace.confirm({"expected_head": state["head"], "answer_id": candidate["key"],
                               "source_checked": True, "content_checked": True})
        job, _ = self.store.job(job["id"])
        pages = {p["raw_sha256"]: {"book_id": job["book_id"], "sha256": p["raw_sha256"],
            "dimensions": [p["width"], p["height"]], "viewer_page": p["viewer_page"],
            "image_url": "https://example.oss-cn-guangzhou.aliyuncs.com/upload_images/" + job["book_id"] + "/page-" + str(p["viewer_page"]) + ".jpg"} for p in job["pages"]}
        return job, empty_native(job["book_id"], pages)

    def test_image_candidates_reach_data_driven_insert_plan(self):
        job, before = self.image_job()
        first = make_plan(before, job["candidates"][0], job["lesson"])
        self.assertEqual(first["before_count"], 0)
        self.assertEqual(first["new_order"], 1)
        after, receipt = apply_native(before, first, 1)
        self.assertTrue(compare_readback(first, after, receipt)["match"])
        second = make_plan(after, job["candidates"][1], job["lesson"])
        after2, receipt2 = apply_native(after, second, 2)
        self.assertEqual(compare_readback(second, after2, receipt2)["old_questions_preserved"], 1)
        self.assertEqual(second["new_order"], 2)

    def test_native_old_unknown_field_mutation_is_rejected(self):
        job, before = self.image_job()
        first = make_plan(before, job["candidates"][0], job["lesson"])
        after, receipt = apply_native(before, first, 1)
        after["questions"]["server-node-1"]["info"]["data"]["unknown_metadata"] = {"nested": [True, "1"]}
        second = make_plan(after, job["candidates"][1], job["lesson"])
        after2, receipt2 = apply_native(after, second, 2)
        after2["questions"]["server-node-1"]["info"]["data"]["unknown_metadata"]["nested"][1] = 1
        with self.assertRaises(Hold): compare_readback(second, after2, receipt2)

    def test_source_overlap_and_stale_current_are_rejected(self):
        job, before = self.image_job()
        plan = make_plan(before, job["candidates"][0], job["lesson"])
        after, _ = apply_native(before, plan, 1)
        with self.assertRaises(Hold): make_plan(after, job["candidates"][0], job["lesson"])
        with self.assertRaises(Hold): check_prewrite(plan, after)

    def test_current_cache_is_consumed_without_recognizing_again(self):
        from annotation.customer.source import engine_identity, ocr_page
        job, _ = self.image_job()
        page = job["pages"][0]
        engine = engine_identity()
        key = digest([job["book_id"], page["raw_sha256"], engine])
        lines = [{"text": "9. 新合成缓存", "bbox": [10, 10, 180, 30], "score": .9}]
        self.store.begin("recognition", key)
        self.store.finish("recognition", key, "COMPLETE", {"raw_sha256": page["raw_sha256"], "engine": engine, "lines": lines})
        with patch("annotation.recognition.baseline.recognize", side_effect=AssertionError("must consume cache")):
            actual, mode = ocr_page(self.store, page, job["book_id"], allow_local_ocr=True)
        self.assertEqual((actual, mode), (lines, "CACHE"))

    def test_native_actor_and_actual_time_window_are_checked(self):
        from annotation.runtime.usense_live.update import text_digest
        job, before = self.image_job()
        plan = make_plan(before, job["candidates"][0], job["lesson"])
        after, receipt = apply_native(before, plan, 1)
        actor = {"runtime_user_id_sha256": text_digest("server-actor")}
        window = {"start": "2026-10-24T00:00:00+00:00", "end": "2026-10-24T00:00:02+00:00"}
        self.assertTrue(compare_readback(plan, after, receipt, runtime_actor_hashes=actor, send_window=window)["runtime_actor_and_send_window_checked"])
        with self.assertRaises(Hold):
            compare_readback(plan, after, receipt, runtime_actor_hashes={"runtime_user_id_sha256": "0" * 64}, send_window=window)

    def test_insertion_before_later_lesson_preserves_shifted_tail(self):
        job, before = self.image_job()
        old_plan = make_plan(before, job["candidates"][1], job["lesson"])
        before, _ = apply_native(before, old_plan, 90)
        branches = before["directory"]["data"]["directory_data"][0]["children"]
        branches[1]["children"] = branches[0]["children"]
        branches[0]["children"] = []
        for frame in before["frames"]["data"]: frame["directory_id"] = "later-lesson"
        for frame in before["questions"]["server-node-90"]["annotations"]["data"]: frame["directory_id"] = "later-lesson"
        before["questions"]["server-node-90"]["info"]["data"]["retained_unknown"] = {"exact": [False, "9"]}
        plan = make_plan(before, job["candidates"][0], job["lesson"])
        self.assertEqual(plan["new_order"], 1)
        after, receipt = apply_native(before, plan, 91)
        later = after["directory"]["data"]["directory_data"][0]["children"][1]["children"][0]
        later.update(order_in_level="2", label="2")
        after["questions"]["server-node-90"]["info"]["data"]["order_in_level"] = "2"
        for frame in after["frames"]["data"]:
            if frame["directory_id"] == "later-lesson": frame["order_in_level"] = "2"
        for frame in after["questions"]["server-node-90"]["annotations"]["data"]: frame["order_in_level"] = "2"
        self.assertEqual(compare_readback(plan, after, receipt)["old_questions_preserved"], 1)

    def test_unknown_save_blocks_successors_and_next_launch(self):
        job, before = self.image_job()
        class UnknownTransport:
            def __init__(self, *args): self.processes = []; self.sends = 0
            def capture(self, *args, **kwargs): return before, {}
            def write_once(self, *args): self.sends += 1; raise TimeoutError("synthetic unknown after intent")
        transport = UnknownTransport()
        with self.assertRaises(TimeoutError): produce(self.store, job["id"], {}, transport_factory=lambda *args: transport)
        current, _ = self.store.job(job["id"])
        self.assertEqual(current["platform_status"], "UNKNOWN_NO_RETRY")
        self.assertEqual(current["candidates"][1]["platform_status"], "NOT_RUN")
        with self.assertRaises(Hold): produce(self.store, job["id"], {}, transport_factory=lambda *args: transport)
        self.assertEqual(transport.sends, 1)

    def test_success_then_repeat_has_no_transport_or_save(self):
        job, before = self.image_job()
        class SyntheticTransport:
            def __init__(self): self.current = before; self.processes = []; self.sends = 0
            def capture(self, *args, **kwargs): return self.current, {}
            def write_once(self, plan, flat, job):
                self.sends += 1
                self.current, receipt = apply_native(self.current, plan, self.sends)
                return {"receipt": receipt, "synthetic": True}
        transport = SyntheticTransport()
        output = produce(self.store, job["id"], {}, transport_factory=lambda *args: transport)
        self.assertTrue((output / "index.html").is_file())
        self.assertEqual(transport.sends, 2)
        with patch("annotation.customer.transport.UsenseTransport", side_effect=AssertionError("must not acquire")):
            produce(self.store, job["id"], {}, transport_factory=lambda *args: (_ for _ in ()).throw(AssertionError('must not reacquire synthetic transport')))
        self.assertEqual(transport.sends, 2)

    def test_missing_image_cache_does_not_call_ocr(self):
        from PIL import Image
        source = self.root / "new-image.png"; Image.new("RGB", (600, 800), "white").save(source)
        with patch("annotation.recognition.baseline.recognize", side_effect=AssertionError("no model authorization")):
            job = prepare(self.store, book="834921", lesson="Other lesson", question_files=[source])
        self.assertEqual(job["status"], "WAITING_SOURCE")
        self.assertEqual(job["metrics"]["new_model_pages"], 0)

    def test_generic_book_endpoints_preserve_small_numeric_ids(self):
        from annotation.runtime.usense_live.config import endpoints, configure, capture_endpoints
        from annotation.runtime.usense_live.core import load_binding
        from annotation.customer.store import byte_hash
        profile = self.root / "dedicated"; profile.mkdir()
        out = self.root / "native-output"; out.mkdir()
        path = self.root / "binding.json"
        configure(profile=profile, output_root=out, config_path=path, coordinator="customer-app", executor="child-write",
                  reviewer="child-read", authorization_reference="SYNTHETIC_ONLY", book_id="1", orders=[12], pages=[15], source=True)
        binding = load_binding(path, byte_hash(path.read_bytes()))
        self.assertEqual(capture_endpoints(binding), endpoints([12], [15], source=True, book_id="1"))

    def test_customer_wire_consumed_by_existing_writer_preflight(self):
        from annotation.customer import wire
        from annotation.runtime.usense_live.insertion_writer import validate_inputs, comparator, full_endpoints
        from annotation.customer.store import encoded
        job, current = self.image_job()
        plan = make_plan(current, job["candidates"][0], job["lesson"])
        flat = {"directory": current["directory"], "frames": current["frames"],
                "source": response({"file_id": job["book_id"]})}
        for page in current["pages"].values():
            flat[f"page_{page['viewer_page']}"] = response({"file_id": job["book_id"],
                "pages": [{"image": page["image_url"], "page_index": page["viewer_page"] - 1}]})
        sources = [{"path": p["raw_path"], "sha256": p["raw_sha256"]} for p in job["pages"]]
        wired = wire.make_wire_plan(plan, flat, sources)
        baseline = self.root / "baseline"; baseline.mkdir()
        for name, value in flat.items(): (baseline / (name + ".json")).write_bytes(encoded(value))
        ledger = self.root / "empty-synthetic-ledger"; ledger.mkdir()
        native, paths, claim = validate_inputs(wired, baseline, ledger, "SYNTHETIC_ONLY")
        self.assertEqual(native, flat)
        self.assertEqual(set(paths), set(flat))
        self.assertFalse(claim.exists())
        self.assertIs(comparator(wired), wire)
        self.assertEqual(full_endpoints(wired), paths)

    def test_review_server_serves_sources_and_guards_customer_confirmation(self):
        import json
        import threading
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        from annotation.recognition.content_review_server import make_server
        job, _ = self.image_job()
        server = make_server(CustomerReviewWorkspace(self.store, job["id"]))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            url = "http://127.0.0.1:" + str(server.server_address[1])
            with urlopen(url + "/api/state") as stream: state = json.load(stream)
            with urlopen(url + "/api/source?asset_id=" + job["pages"][0]["asset_id"]) as stream:
                self.assertEqual(stream.read(8), b"\x89PNG\r\n\x1a\n")
            body = json.dumps({"expected_head": state["head"], "answer_id": state["answers"][0]["answer_id"],
                               "source_checked": True, "content_checked": True}).encode()
            with self.assertRaises(HTTPError) as denied:
                urlopen(Request(url + "/api/confirm", data=body, headers={"Content-Type": "application/json", "X-Review-Token": "wrong"}))
            self.assertEqual(denied.exception.code, 403)
            with urlopen(Request(url + "/api/confirm", data=body, headers={"Content-Type": "application/json", "X-Review-Token": state["csrf_token"]})) as stream:
                self.assertTrue(json.load(stream)["ok"])
            with self.assertRaises(HTTPError) as stale:
                urlopen(Request(url + "/api/confirm", data=body, headers={"Content-Type": "application/json", "X-Review-Token": state["csrf_token"]}))
            self.assertEqual(stale.exception.code, 409)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_confirmed_safe_formula_can_be_encoded_after_r1_rich_content_support(self):
        job, before = self.image_job()
        candidate = copy.deepcopy(job["candidates"][0])
        candidate["zones"]["question"] = "求 $x^2$ 的值。"
        candidate["content_hash"] = candidate_hash(candidate)
        candidate["review"]["content_hash"] = candidate["content_hash"]
        plan=make_plan(before,candidate,job['lesson'])
        self.assertIn('$x^2$',plan['payload']['ocr_submissions'][0]['ocr_result'])

    def test_unknown_with_receipt_can_reconcile_without_writer(self):
        job, before = self.image_job()
        class ReadbackFailure:
            def __init__(self): self.current = before; self.processes = []; self.sends = 0; self.reads = 0
            def capture(self, *args, **kwargs):
                self.reads += 1
                if self.reads == 2: raise TimeoutError("synthetic reader failure after recorded receipt")
                return self.current, {}
            def write_once(self, plan, flat, job):
                self.sends += 1
                self.current, receipt = apply_native(self.current, plan, self.sends)
                return {"receipt": receipt, "synthetic": True}
        transport = ReadbackFailure()
        with self.assertRaises(TimeoutError): produce(self.store, job["id"], {}, transport_factory=lambda *args: transport)
        key = source_key(job["book_id"], job["candidates"][0])
        previous = self.store.operation("save:" + job["book_id"], key)
        reconcile(self.store, job["id"], {}, transport_factory=lambda *args: transport)
        self.assertEqual(transport.sends, 1)
        resolved = self.store.operation("save:" + job["book_id"], key)
        self.assertEqual(resolved["state"], "COMPLETE")
        self.assertEqual(self.store.get(resolved["output"])["previous_output"], previous["output"])
        current, _ = self.store.job(job["id"])
        self.assertEqual(current["candidates"][1]["platform_status"], "NOT_RUN")

    def test_unseen_two_column_layout_uses_source_geometry(self):
        from PIL import Image
        question = self.root / "two-column.png"; answer = self.root / "answers-image.png"
        Image.new("RGB", (1000, 1400), "white").save(question)
        Image.new("RGB", (900, 1500), "white").save(answer)
        def synthetic_ocr(store, page, book, **kwargs):
            if page["role"] == "question":
                lines = [{"text": str(i + 1) + ". 请回答。", "bbox": [30 if i < 4 else 550, 300 + i % 4 * 70,
                    450 if i < 4 else 950, 330 + i % 4 * 70], "score": .99} for i in range(8)]
            else:
                lines = [{"text": str(i + 1) + ". 正确", "bbox": [30, 300 + i * 70, 450, 330 + i * 70], "score": .99} for i in range(8)]
            return lines, "SYNTHETIC_CACHE"
        with patch("annotation.customer.prepare.ocr_page", side_effect=synthetic_ocr):
            job = prepare(self.store, book="123819", lesson="另一个课时", question_files=[question], answer_files=[answer])
        self.assertEqual([q["printed_number"] for q in job["candidates"]], [str(i) for i in range(1, 9)])
        self.assertEqual(job["candidates"][4]["frames"][0]["column"], 1)
        self.assertEqual(job["metrics"]["new_model_pages"], 0)


if __name__ == "__main__":
    unittest.main()
