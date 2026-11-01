"""Focused synthetic regression for unbound current-schema response capture."""
import asyncio
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from annotation.quality.live_pilot import PilotError
from annotation.runtime.live_pilot import owner


SLOTS = ("book", "directory", "frames", "export")


class Authority:
    role = "AUTHOR_SAVE"
    synthetic = True

    def __init__(self, output):
        self.output = output
        self.checks = 0

    def check(self):
        self.checks += 1
        return self


def io_class(responses, calls):
    class FakeCurrentPageIO:
        def __init__(self, page, context, guard, loop, binding, *, synthetic, owner_authority):
            self.owner_authority = owner_authority

        async def fetch_async(self, method, path, *, params, payload, phase):
            calls.append({"method": method, "path": path, "params": params,
                          "payload": payload, "phase": phase})
            return responses[len(calls) - 1]

    return FakeCurrentPageIO


class BookSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="a24-book-snapshot-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.authority = Authority(self.root / "owned-output")
        self.calls = []
        texts = ("BOOK-内容", "DIRECTORY", "FRAMES", "EXPORT")
        self.responses = [{"http_status": 200, "body": text} for text in texts]
        self.expected = dict(zip(SLOTS, (text.encode("utf-8") for text in texts)))

    def acquire(self, responses=None):
        fake = io_class(responses or self.responses, self.calls)
        with patch("annotation.delivery.live_pilot.usense.CurrentPageIO", fake):
            return asyncio.run(owner.acquire_current_schema(
                self.authority, object(), object(), object(), {"synthetic": "binding"}))

    def test_four_gets_save_four_utf8_reencoded_bodies_and_digests(self):
        result = self.acquire()

        self.assertEqual(len(self.calls), 4)
        self.assertEqual([call["method"] for call in self.calls], ["GET"] * 4)
        self.assertTrue(all(call["payload"] is None and call["phase"] == "acquire"
                            for call in self.calls))
        self.assertEqual(result["status"], "CURRENT_SCHEMA_UNBOUND")
        self.assertIs(result["write_allowed"], False)
        self.assertEqual(result["successors"], "NOT_RUN")
        self.assertEqual([read["slot"] for read in result["reads"]], list(SLOTS))

        for read in result["reads"]:
            expected = self.expected[read["slot"]]
            expected_hash = hashlib.sha256(expected).hexdigest()
            private = self.root / "owned-output" / "private" / (read["slot"] + "-snapshot.bin")
            self.assertEqual(private.read_bytes(), expected)
            self.assertEqual(read["sha256"], expected_hash)
            self.assertEqual(read["bytes"], len(expected))
            self.assertEqual(read["capture_representation"], "UTF8_REENCODED_RESPONSE_TEXT")
            self.assertEqual(read["controlled_raw_ref"], {
                "path": str(private), "sha256": expected_hash, "bytes": len(expected),
                "capture_representation": "UTF8_REENCODED_RESPONSE_TEXT"})

        directory = result["reads"][1]
        self.assertEqual(directory["query_keys"], ["file_id"])
        self.assertNotIn("params", directory)
        self.assertNotIn("headers", json.dumps(result))

    def test_existing_output_rejects_without_overwrite(self):
        self.acquire()
        before = {slot: (self.root / "owned-output" / "private" / (slot + "-snapshot.bin")).read_bytes()
                  for slot in SLOTS}
        self.calls.clear()
        changed = [{"http_status": 200, "body": "CHANGED-" + slot} for slot in SLOTS]

        with self.assertRaises(FileExistsError):
            self.acquire(changed)

        self.assertEqual(len(self.calls), 1)
        after = {slot: (self.root / "owned-output" / "private" / (slot + "-snapshot.bin")).read_bytes()
                 for slot in SLOTS}
        self.assertEqual(after, before)

    def test_http_failure_stops_before_any_snapshot_or_later_request(self):
        failed = [{"http_status": 503, "body": "PRIVATE_FAILURE_BODY"}] + self.responses[1:]

        with self.assertRaises(PilotError):
            self.acquire(failed)

        self.assertEqual(len(self.calls), 1)
        self.assertFalse((self.root / "owned-output" / "private").exists())

    def test_third_get_failure_retains_prior_private_evidence_and_never_unlocks_write(self):
        failed = self.responses[:2] + [{"http_status": 503, "body": "PRIVATE_FAILURE_BODY"}] + self.responses[3:]

        with self.assertRaises(PilotError) as caught:
            self.acquire(failed)

        self.assertEqual(caught.exception.code, "OWNER_FIRST_SAVE_BLOCKED")
        self.assertEqual(len(self.calls), 3)
        self.assertEqual([call["method"] for call in self.calls], ["GET"] * 3)
        self.assertTrue(all(call["payload"] is None and call["phase"] == "acquire"
                            for call in self.calls))
        private = self.root / "owned-output" / "private"
        self.assertEqual((private / "book-snapshot.bin").read_bytes(), self.expected["book"])
        self.assertEqual((private / "directory-snapshot.bin").read_bytes(), self.expected["directory"])
        self.assertFalse((private / "frames-snapshot.bin").exists())
        self.assertFalse((private / "export-snapshot.bin").exists())
        # acquire_current_schema raises before returning any result that could
        # carry write_allowed=True; the caller therefore cannot reach adapter.
        self.assertFalse(any(call["method"] != "GET" for call in self.calls))


if __name__ == "__main__":
    unittest.main()
