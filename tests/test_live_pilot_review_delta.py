"""Exactly six A11 review-delta cases; archive copies and readonly reconciliation only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest

from annotation.contracts import validate_bundle
from annotation.quality.live_pilot import PilotError, check_input, question_facts
from annotation.runtime.live_pilot.journal import Journal
from annotation.runtime.live_pilot.runner import reconcile_readonly
from annotation.runtime.storage.common import digest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "tests/fixtures/live_pilot"
FIXTURES = ASSETS / "review_delta"
ARCHIVE_COMMIT = "c580ca63ada9e452fd5ee71e5272cf0d047d4574"
ARCHIVE_PATH = "docs/evidence/A11/execution/attempt-2/runtime/test_T6_response_frame_and_read_failure/http_only"


def raw_git(*arguments):
    return subprocess.check_output(["git", "-c", "core.longpaths=true", *arguments], cwd=ROOT,
                                   env=dict(os.environ, GIT_NO_LAZY_FETCH="1"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))


class ArchivedReadonlyTransport:
    """Decode the saved fake backend without importing/calling its send implementation."""
    offline = True

    def __init__(self, path, release_mode):
        self.path = path
        self.release_mode = release_mode
        self.reads = 0
        self.sends = 0

    def send_once(self, _):
        self.sends += 1
        raise AssertionError("read-only delta must never send")

    def observe(self, phase):
        if phase != "reconcile" or self.reads:
            raise AssertionError("exactly one readonly reconcile observation")
        self.reads += 1
        data = json.loads(self.path.read_bytes())
        obs = data["initial"]
        obs.update(phase=phase, origin="FAKE_BACKEND_READ", read_sequence=data["sequence"] + 1,
                   source_ref="review-delta-read-" + str(data["sequence"] + 1), session_id="review-delta-readonly-session")
        view = obs["view"]
        for item in data["new"]:
            pid = item["id"]
            view["internal_bindings"][item["internal"]] = pid
            view["target"]["questions"].append({"platform_question_id": pid, "directory_id": item["directory"],
                                                "platform_order": item["order"]})
            view["question_content"][pid] = item["content"]
            for raw in sorted(item["rectangles"], key=lambda value: value["ordinal"]):
                box = {"image": raw["image"], "bbox": raw["coordinates"]}
                view["target"]["frames"].append({"platform_frame_id": raw["rect_id"], "platform_question_id": pid,
                    "box": box, "platform_role": raw["role"], "platform_type": raw["kind"]})
                view["frame_projections"][raw["rect_id"]] = {"fragment_id": raw["fragment"], "region_id": raw["region"],
                    "box": box, "platform_role": raw["role"], "platform_type": raw["kind"]}
        return obs

    def close(self):
        if self.release_mode == "exception":
            raise OSError("synthetic readonly close exception")
        return {"released": self.release_mode == "normal", "session_id": "review-delta-readonly-session",
                "reason": "synthetic returned false" if self.release_mode == "false" else "synthetic readonly released"}


class ReviewDeltaTests(unittest.TestCase):
    def output(self):
        path = Path(os.environ["A11_DELTA_CASE_ROOT"]) / self._testMethodName
        path.mkdir(parents=True, exist_ok=False)
        return path

    def inspect(self, name):
        req = json.loads((FIXTURES / (name + ".json")).read_bytes())
        # Validate C01 plus approval equality separately before reaching the new gate.
        bundle = validate_bundle(req["bundle"], asset_root=ASSETS)
        graph = next(a for a in bundle.artifacts if a.kind == "QuestionGraph")
        facts = [question_facts(bundle, graph, q, bundle.policies[0], req["bindings"]) for q in graph.payload.questions]
        for fact, entry in zip(facts, req["approval"]["questions"]):
            self.assertEqual(entry["input_hash"], digest(fact))
            self.assertEqual(entry["approved_parts"], fact["parts"])
            self.assertEqual(entry["answer_relation"], fact["relations"][0])
            self.assertEqual([frame["platform_role"] for frame in fact["frames"]], ["Q", "W", "W", "W", "W", "A"])
        return req, facts

    def test_D01_bound_single_choice(self):
        out = self.output()
        req, facts = self.inspect("valid")
        original = json.loads((ASSETS / "request.json").read_bytes())
        model = validate_bundle(original["bundle"], asset_root=ASSETS)
        graph = next(a for a in model.artifacts if a.kind == "QuestionGraph")
        for fact, q in zip(facts, graph.payload.questions):
            old = question_facts(model, graph, q, model.policies[0], original["bindings"])
            self.assertEqual(fact["frames"], old["frames"])
            self.assertEqual(fact["parts"], old["parts"])
        admitted = check_input(req, ASSETS, offline=True)
        self.assertEqual(len(admitted.questions), 2)
        write_json(out / "result.json", {"status": "PASS", "scope": "OFFLINE_ONLY", "input_hash": admitted.input_hash,
            "unchanged_frames_and_parts": True, "classification_resources": [e["choice_qualification"] for e in req["approval"]["questions"]],
            "plan_calls": 0, "intent_calls": 0, "send_calls": 0})

    def reject_semantics(self, name, code):
        out = self.output()
        req, facts = self.inspect(name)
        with self.assertRaises(PilotError) as caught:
            check_input(req, ASSETS, offline=True)
        self.assertEqual(caught.exception.code, code)
        write_json(out / "result.json", {"status": "PASS", "c01_valid": True, "approval_exact": True,
            "answer_text": facts[0]["parts"][-1]["text"], "classification": req["approval"]["questions"][0]["choice_qualification"],
            "actual_rejection_layer": "quality.check_single_choice", "actual_code": caught.exception.code,
            "plan_calls": 0, "intent_calls": 0, "send_calls": 0})

    def test_D02_resealed_BC(self):
        self.reject_semantics("multiple-answer", "SINGLE_ANSWER_LABEL_REQUIRED")

    def test_D03_explicit_multiple_with_B(self):
        self.reject_semantics("explicit-multiple", "SINGLE_CHOICE_REQUIRED")

    def readonly_release(self, mode):
        out = self.output()
        members = raw_git("ls-tree", "-r", "-z", ARCHIVE_COMMIT, ARCHIVE_PATH).split(b"\0")
        source_inventory, before = [], {}
        for member in members:
            if not member:
                continue
            meta, name = member.split(b"\t", 1)
            _, kind, blob = meta.decode().split()
            self.assertEqual(kind, "blob")
            name = name.decode("utf-8")
            relative = name[len(ARCHIVE_PATH) + 1:]
            data = raw_git("cat-file", "blob", blob)
            dest = out / "archive-copy" / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as handle:
                handle.write(data)
            self.assertEqual(dest.read_bytes(), data)
            before[relative] = data
            source_inventory.append({"source_commit": ARCHIVE_COMMIT, "source_path": name, "blob": blob,
                                     "copy_path": relative, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        write_json(out / "copy-manifest.json", {"members": source_inventory, "raw_copy_verified": True})
        journal = Journal(out / "archive-copy/journal", offline=True)
        initial = journal.report()
        self.assertEqual(initial["questions"]["a11-new-alpha"]["state"], "UNKNOWN")
        self.assertEqual(initial["questions"]["a11-new-beta"]["state"], "NOT_RUN")
        self.assertTrue(initial["apply_release"]["released"])
        self.assertIsNone(initial["reconcile_release"])
        old_results = [e for e in journal.read() if e["kind"] == "RESULT"]
        self.assertFalse(any(e["kind"] == "RECONCILE_CLAIM" for e in journal.read()))
        backend = out / "archive-copy/backend/fake-backend.json"
        sends_before = json.loads(backend.read_bytes())["sends"]
        transport = ArchivedReadonlyTransport(backend, mode)
        result = reconcile_readonly(journal, transport, "a11-new-alpha")
        report = journal.report()
        self.assertEqual(result["effect_match"], "MATCH")
        self.assertEqual(result["status"], "REVIEW" if mode == "normal" else "HOLD")
        self.assertEqual(report["status"], "REVIEW" if mode == "normal" else "HOLD")
        self.assertEqual(result["reconcile_release"]["released"], mode == "normal")
        self.assertEqual(report["reconcile_release"], result["reconcile_release"])
        self.assertEqual(report["release"]["released"], mode == "normal")
        self.assertTrue(result["apply_release"]["released"])
        self.assertEqual(report["apply_release"], initial["apply_release"])
        self.assertFalse(result["resend_allowed"])
        self.assertFalse(report["resend_allowed"])
        self.assertEqual(result["write_disposition"], "HOLD")
        self.assertEqual(report["questions"], initial["questions"])
        self.assertEqual(old_results, [e for e in journal.read() if e["kind"] == "RESULT"])
        self.assertEqual(transport.reads, 1)
        self.assertEqual(transport.sends, 0)
        self.assertEqual(json.loads(backend.read_bytes())["sends"], sends_before)
        for relative, raw in before.items():
            self.assertEqual((out / "archive-copy" / relative).read_bytes(), raw)
        new_events = journal.read()[initial["event_count"]:]
        self.assertEqual([e["kind"] for e in new_events], ["RECONCILE_CLAIM", "RECONCILE_RELEASE", "RECONCILIATION"])
        write_json(out / "result.json", {"status": "PASS", "mode": mode, "initial_report": initial,
            "reconcile_return": result, "standard_report": report, "new_event_kinds": [e["kind"] for e in new_events],
            "all_archived_member_bytes_preserved": True, "source_send_count": sends_before,
            "new_send_count": 0, "readonly_observations": 1, "apply_calls": 0,
            "book_gate_released": journal._gate is None})
        self.assertIsNone(journal._gate)

    def test_D04_reconcile_close_exception(self):
        self.readonly_release("exception")

    def test_D05_reconcile_close_false(self):
        self.readonly_release("false")

    def test_D06_reconcile_close_normal(self):
        self.readonly_release("normal")
