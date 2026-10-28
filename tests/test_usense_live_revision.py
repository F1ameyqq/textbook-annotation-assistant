"""Synthetic accepted-predecessor evidence; no actual account or platform calls."""
import copy
import json
from pathlib import Path
import sys
import unittest

import test_usense_live_writer_review as base

writer, update = base.writer, base.update

revision = sys.modules[writer.__package__ + ".revision"]
config = sys.modules[writer.__package__ + ".config"]


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return writer.sha(path.read_bytes())


def accepted_predecessor(files):
    """Build all raw evidence that real accepted-batch admission requires."""
    before = copy.deepcopy(files.plan["before"])
    image = "![synthetic diagram](https://synthetic.invalid/diagram(a).png?sig=preserve)"
    before["zones"]["question"]["data"]["ocr_result"] += "\n" + image
    old_changes = copy.deepcopy(files.plan["approved_changes"])
    prior = update._make_plan(before, files.plan["target"], old_changes, protect_images=False)
    batch = (files.root / "accepted-history").resolve()
    qdir = batch / "q2"
    wrun, rrun = "usense-readonly-synthetic-writer", "usense-readonly-synthetic-reader"
    wd, rd = batch / wrun, batch / rrun
    wd.mkdir(parents=True); rd.mkdir(parents=True); qdir.mkdir()
    planhash = dump(qdir / "plan.json", prior)
    (wd / "plan.json").write_bytes((qdir / "plan.json").read_bytes())
    names = config.endpoints([2], [10])
    files.endpoints = names
    native = {"directory": before["directory"], "frames": before["frames"],
              "q2_annotations": before["annotations"], "q2_info": before["info"],
              **{"q2_" + zone: value for zone, value in before["zones"].items()}, "page_10": files.native["page_10"]}
    after = copy.deepcopy(native)
    for zone in update.ZONES: after["q2_" + zone] = copy.deepcopy(prior["expected"]["zones"][zone])
    after["q2_info"]["data"]["updated_at"] = "2026-10-16T00:00:00"
    captures = {}
    for name in names:
        dump(wd / ("before-" + name + ".json"), native[name])
        digest = dump(rd / (name + ".json"), after[name])
        captures[name] = {"filename": name + ".json", "sha256": digest, "bytes": (rd / (name + ".json")).stat().st_size,
                          "status": 200, "observed_at": "2026-10-23T00:00:06+00:00", "request_counts": {"context": 1, "native": 1}}
    base_config = {"book_id": "46007447", "operation": "READONLY_CAPTURE", "output_root": str(batch),
                   "profile": {"directory": str(files.root.resolve() / "synthetic-profile")},
                   "static_get": {"mode": "DISABLED", "max_requests": 0},
                   "allowed_get": [{"url": writer.TARGET, "resource_types": ["document"], "max_requests": 1}] +
                       [{"url": writer.ORIGIN + path, "resource_types": ["fetch", "xhr"], "max_requests": 1} for path in names.values()]}
    wc = dict(base_config, run_id=wrun); rc = dict(base_config, run_id=rrun)
    wsha = dump(qdir / "writer-config.json", wc); rsha = dump(qdir / "independent-reader-config.json", rc)
    receipt = {"code": 0, "message": "success", "data": {"inserted": False, "question_order": 2,
               "inserted_question_node": None, "success": True, "append_at_global_end": False}}
    rsha_receipt = dump(wd / "native-receipt.json", receipt)
    release = {"context_closed": True, "runtime_stopped": True, "pending_callbacks": 0, "errors": [], "context_runtime_release_confirmed": True}
    w = {"status": "RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK", "release": release, "run_id": wrun,
         "plan_sha256": prior["plan_sha256"], "plan_file_sha256": planhash, "target": prior["target"],
         "ledger_key": prior["ledger_key"], "config_sha256": wsha, "send_intent_at": "2026-10-23T00:00:02+00:00",
         "finished_at": "2026-10-23T00:00:03+00:00", "receipt_sha256": rsha_receipt, "http_status": 200,
         "post_attempts": 1, "post_layers": {"context": 1, "native": 1}, "native_body_sha256": "c" * 64}
    r = {"status": "NATIVE_GETS_CAPTURED", "release": release, "run_id": rrun, "config_sha256": rsha,
         "finished_at": "2026-10-23T00:00:07+00:00", "save_attempts": 0, "captures": captures}
    dump(wd / "execution-result.json", w); dump(rd / "capture-summary.json", r)
    dump(qdir / "writer-process-result.json", {"pid": 1001, "exit_code": 0, "started_at": "2026-10-23T00:00:01+00:00",
         "finished_at": "2026-10-23T00:00:04+00:00", "result": w})
    dump(qdir / "reader-process-result.json", {"pid": 1002, "exit_code": 0, "started_at": "2026-10-23T00:00:05+00:00",
         "finished_at": "2026-10-23T00:00:08+00:00", "result": r})
    comparison = update.compare_recorded_readback(prior, update.from_captured_map(after, "q2_"))
    acceptance = {"status": "ACCEPTED", "checks": {"synthetic_all_checks": True}, "target": prior["target"],
                  "plan_file_sha256": planhash, "writer_run": wrun, "reader_run": rrun, "comparison": comparison}
    apath = qdir / "acceptance.json"; asha = dump(apath, acceptance)
    intent = {"ledger_key": prior["ledger_key"], "plan_sha256": prior["plan_sha256"], "run_id": wrun,
              "automatic_retry_allowed": False, "native_body_sha256": w["native_body_sha256"], "intent_at": w["send_intent_at"]}
    dump(files.ledger / (prior["ledger_key"] + ".json"), intent)
    dump(files.ledger / (prior["ledger_key"] + ".accepted.json"), {"plan_sha256": prior["plan_sha256"],
         "writer_run": wrun, "reader_run": rrun, "acceptance_sha256": asha})
    dump(wd / "send-intent.json", {"native_body_sha256": w["native_body_sha256"], "plan_sha256": prior["plan_sha256"], "send_intent_at": w["send_intent_at"]})
    dump(qdir / "review-evidence-hashes.json", {str(files.source): writer.sha(files.source.read_bytes()),
                                              str(files.review): writer.sha(files.review.read_bytes())})
    events = [{"method": "GET", "layer": layer, "url_sha256": writer.sha((writer.ORIGIN + path).encode()), "allowed": True}
              for path in names.values() for layer in ("context", "native")]
    dump(rd / "network-events.json", events)
    dump(wd / "network-events.json", events + [{"method": "POST", "layer": layer, "url_sha256": writer.sha(writer.POST.encode()), "allowed": True}
                                             for layer in ("context", "native")])
    files.native = after
    current = update.from_captured_map(after, "q2_")
    new_changes = copy.deepcopy(old_changes)
    new_changes["question"]["text"] += "\n" + image
    new_changes["question"]["reviewed_text_sha256"] = update.text_digest(new_changes["question"]["text"])
    files.plan = update.make_plan(current, prior["target"], new_changes)
    files.plan_sha = dump(files.plan_path, files.plan)
    for name in names: dump(files.baseline / (name + ".json"), after[name])
    files.claim = files.ledger / (revision.revision_key(prior["ledger_key"], prior["plan_sha256"]) + ".json")
    return apath, prior


class RevisionAdmissionTests(unittest.TestCase):
    setUp = base.WriterIndependentTests.setUp
    tearDown = base.WriterIndependentTests.tearDown
    run_fake = base.WriterIndependentTests.run_fake
    assertBlocked = base.WriterIndependentTests.assertBlocked

    def prior(self):
        self.acceptance, self.previous_plan = accepted_predecessor(self.files)
        return self.acceptance

    def verify(self):
        return revision.verify_previous_acceptance(self.acceptance, self.files.plan, self.files.native, self.files.ledger)

    def test_complete_predecessor_allows_one_revision_without_touching_old_intent(self):
        self.prior()
        old = self.files.ledger / (self.previous_plan["ledger_key"] + ".json")
        old_bytes = old.read_bytes()
        verified = self.verify()
        self.assertEqual(verified["intent_key"], self.files.claim.stem)
        result, browser = self.run_fake(previous_acceptance=self.acceptance)
        self.assertEqual(result["status"], "RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK")
        self.assertEqual(browser.send_calls, 1)
        self.assertEqual(result["intent_key"], verified["intent_key"])
        self.assertEqual(old.read_bytes(), old_bytes)
        self.assertTrue(self.files.claim.exists())
        self.assertBlocked("EXISTING_REVISION_INTENT_READBACK_REQUIRED_NO_RETRY", self.verify)

    def test_unknown_revision_is_not_retried(self):
        self.prior()
        result, browser = self.run_fake(previous_acceptance=self.acceptance, send_error=TimeoutError("synthetic lost response"))
        self.assertEqual(result["status"], "UNKNOWN_DO_NOT_RETRY")
        self.assertEqual(browser.send_calls, 1)
        self.assertBlocked("EXISTING_REVISION_INTENT_READBACK_REQUIRED_NO_RETRY", self.verify)

    def test_unknown_predecessor_cannot_be_admitted(self):
        self.prior()
        path = self.acceptance.parent / "writer-process-result.json"
        value = json.loads(path.read_bytes()); value["result"]["status"] = "UNKNOWN_DO_NOT_RETRY"; dump(path, value)
        self.assertBlocked("PREVIOUS_RUN_UNKNOWN_OR_FAILED", self.verify)

    def test_forged_acceptance_without_matching_ledger_hash_rejected(self):
        self.prior()
        value = json.loads(self.acceptance.read_bytes()); value["extra"] = "changed"; dump(self.acceptance, value)
        self.assertBlocked("PREVIOUS_ACCEPTED_LEDGER_HASH_MISMATCH", self.verify)

    def test_missing_accepted_marker_never_bypasses_original_intent(self):
        self.prior()
        (self.files.ledger / (self.previous_plan["ledger_key"] + ".accepted.json")).unlink()
        with self.assertRaises(ValueError): self.verify()

    def test_reader_raw_tamper_rejected(self):
        self.prior()
        path = self.acceptance.parent.parent / "usense-readonly-synthetic-reader/q2_question.json"
        value = json.loads(path.read_bytes()); value["data"]["ocr_result"] = "tampered"; dump(path, value)
        self.assertBlocked("PREVIOUS_CAPTURE_RAW_MISMATCH", self.verify)

    def test_even_monotonic_current_timestamp_drift_is_stale_before(self):
        self.prior()
        self.files.native["q2_info"]["data"]["updated_at"] = "2026-10-17T00:00:00"
        self.assertBlocked("CURRENT_BEFORE_NOT_PREVIOUS_READBACK", self.verify)

    def test_unknown_other_revision_branch_blocks_reusing_accepted_ancestor(self):
        self.prior()
        key = revision.revision_key(self.previous_plan["ledger_key"], "d" * 64)
        dump(self.files.ledger / (key + ".json"), {"ledger_key": self.previous_plan["ledger_key"], "state": "UNKNOWN"})
        self.assertBlocked("UNRESOLVED_IDENTITY_INTENT_NO_REVISION", self.verify)

    def test_same_process_or_time_overlap_rejected(self):
        self.prior()
        path = self.acceptance.parent / "reader-process-result.json"
        value = json.loads(path.read_bytes()); value["pid"] = 1001; dump(path, value)
        self.assertBlocked("PREVIOUS_READER_NOT_INDEPENDENT", self.verify)

    def test_revision_stable_identity_is_independent_of_new_text(self):
        self.prior()
        first = self.verify()["intent_key"]
        modified = copy.deepcopy(self.files.plan["approved_changes"])
        modified["question"]["text"] += " another reviewed edit"
        modified["question"]["reviewed_text_sha256"] = update.text_digest(modified["question"]["text"])
        self.files.plan = update.make_plan(self.files.plan["before"], self.files.plan["target"], modified)
        self.assertEqual(first, self.verify()["intent_key"])


if __name__ == "__main__": unittest.main()
