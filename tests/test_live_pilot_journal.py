"""Fixed once-only A11 crash/restart and contention probes in owned child processes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent / "fixtures" / "live_pilot"))
from helper import HERE, FakeTransport, case_root, process_event, request
from annotation.quality.live_pilot import PilotError
from annotation.runtime.live_pilot.journal import Journal, exclusive
from annotation.runtime.live_pilot.runner import apply, reconcile_readonly


class JournalTests(unittest.TestCase):
    def spawn(self, root, point):
        process = subprocess.Popen([sys.executable, str(HERE/"helper.py"), "worker", str(root), point],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        process_event({"event": "created", "pid": process.pid, "case": self._testMethodName, "root": str(root), "point": point})
        return process

    def join_owned(self, process, root, tag):
        try:
            out, err = process.communicate(timeout=40)
        except subprocess.TimeoutExpired:
            process.terminate()
            out, err = process.communicate(timeout=10)
            process_event({"event": "terminated_owned", "pid": process.pid, "exit_code": process.returncode})
            self.fail("owned child exceeded bound")
        process_event({"event": "exited", "pid": process.pid, "exit_code": process.returncode})
        (root/(tag+".json")).write_text(json.dumps({"pid":process.pid,"exit_code":process.returncode,"stdout":out,"stderr":err}), encoding="utf-8")
        return process.returncode, out, err

    def test_T5_crash_points_and_new_process_restart(self):
        base = case_root(self._testMethodName)
        for point, expected in (("before_intent",0),("after_intent",0),("after_claim",0),("after_effect",1),("before_receipt",1)):
            root = base/point
            root.mkdir()
            first = self.spawn(root, point)
            self.assertEqual(self.join_owned(first, root, "first")[0], 73)
            second = self.spawn(root, "none")
            code, out, err = self.join_owned(second, root, "restart")
            self.assertEqual(code, 2, err)
            self.assertIn("BOOK_ALREADY_STARTED", out)
            self.assertEqual(json.loads((root/"backend"/"fake-backend.json").read_text(encoding="utf-8"))["sends"], expected)
            report = Journal(root/"journal", offline=True).report()
            self.assertEqual(report["questions"]["a11-new-beta"]["state"], "NOT_RUN")

    def test_T5_two_process_one_claim(self):
        root = case_root(self._testMethodName)
        FakeTransport(root/"backend", request()["observation"])
        # Child 1 exits after its durable claim; child 2 must never send, regardless of interleaving.
        first, second = self.spawn(root, "after_claim"), self.spawn(root, "after_claim")
        results = [self.join_owned(first,root,"one"), self.join_owned(second,root,"two")]
        self.assertEqual(sorted(r[0] for r in results), [2,73])
        journal = Journal(root/"journal",offline=True)
        self.assertEqual(sum(e["kind"] == "SEND_CLAIMED" for e in journal.read()), 1)
        self.assertEqual(json.loads((root/"backend"/"fake-backend.json").read_text(encoding="utf-8"))["sends"], 0)

    def test_T5_same_content_and_corrupt_ledger(self):
        root = case_root(self._testMethodName)
        value = {"same":"content"}
        exclusive(root/"same.json", value)
        with self.assertRaises(PilotError): exclusive(root/"same.json", value)
        req = request()
        journal = Journal(root/"journal",offline=True)
        with journal:
            journal.begin("input", ["test-question"])
            intent = journal.intent("test-question", {"value":1})
            journal.claim("test-question", intent)
            with self.assertRaises(PilotError): journal.claim("test-question", intent)
        path = root/"journal"/"event-000001.json"
        saved = path.read_bytes()
        path.write_bytes(saved+b" ")  # whitespace preserves parsed data, then semantic damage
        changed = json.loads(saved)
        changed["data"]["input_hash"] = "tampered"
        path.write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaises(PilotError): journal.read()

    def test_T6_unknown_readonly_match_absent_conflict(self):
        base = case_root(self._testMethodName)
        for variant in ("MATCH", "ABSENT", "CONFLICT"):
            req = request()
            root = base/variant
            journal = Journal(root/"journal",offline=True)
            transport = FakeTransport(root/"backend",req["observation"],"response_loss")
            report = apply(req,HERE,journal,transport)
            self.assertEqual(report["questions"]["a11-new-alpha"]["state"],"UNKNOWN")
            self.assertEqual(report["questions"]["a11-new-beta"]["state"],"NOT_RUN")
            before_results = [e for e in journal.read() if e["kind"] == "RESULT"]
            data = transport._load()
            if variant == "ABSENT": data["new"] = []
            if variant == "CONFLICT": data["new"][0]["content"]["parts"][-1]["text"] = "A"
            transport._save(data)
            transport.behavior = "normal"
            result = reconcile_readonly(journal,transport,"a11-new-alpha")
            self.assertEqual(result["effect_match"],variant)
            self.assertEqual(transport._load()["sends"],1)
            self.assertEqual(before_results,[e for e in journal.read() if e["kind"] == "RESULT"])
            with self.assertRaises(PilotError): reconcile_readonly(journal,transport,"a11-new-alpha")
            with self.assertRaises(PilotError): apply(req,HERE,journal,transport)


if __name__ == "__main__": unittest.main()
