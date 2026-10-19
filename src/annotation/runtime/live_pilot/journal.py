"""Append-only A11 ledger. An existing intent/claim never grants new sending rights."""
import hashlib
import json
import os
from pathlib import Path

from annotation.delivery.mock.persistent import BookEffectGate
from annotation.quality.live_pilot import BOOK, PilotError, require
from annotation.runtime.storage.common import canonical, digest


def exclusive(path, value):
    """Unlike common.exclusive_bytes, same-content existing files are a hard denial."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(canonical(value))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise PilotError("EXISTING_IMMUTABLE_RECORD", path.name) from exc


class Journal:
    def __init__(self, root=None, *, offline=False):
        self.offline = offline
        fixed = Path.home() / ".annotation" / "a11-live-pilot" / "usense" / BOOK
        require(offline or root is None or Path(root).resolve() == fixed.resolve(), "FIXED_BOOK_JOURNAL")
        require(not offline or root is not None, "OFFLINE_ROOT_REQUIRED")
        self.root = Path(root) if offline else fixed
        # Independent of run_id, output_dir, profile and journal location.
        self.lock_path = Path.home() / ".annotation" / "a11-live-pilot-locks" / (
            ("offline-" if offline else "") + "usense-" + BOOK + ".lock")
        self._gate = None
        self.owner = {"pid": os.getpid(), "namespace": "OFFLINE" if offline else "PLATFORM"}

    def __enter__(self):
        self._gate = BookEffectGate(self.lock_path, {"platform": "usense", "book_id": BOOK}, timeout=5)
        self._gate.__enter__()
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            self.read()
        except BaseException:
            self._gate.__exit__(None, None, None)
            self._gate = None
            raise
        return self

    def __exit__(self, *args):
        if self._gate:
            self._gate.__exit__(*args)
            self._gate = None

    def read(self):
        events, previous = [], None
        paths = sorted(self.root.glob("event-*.json")) if self.root.exists() else []
        anchors = sorted(self.root.glob("anchor-*.json")) if self.root.exists() else []
        require(len(paths) == len(anchors), "JOURNAL_CORRUPT")
        try:
            for number, path in enumerate(paths, 1):
                record = json.loads(path.read_bytes())
                require(path.name == "event-{:06d}.json".format(number) and record["sequence"] == number and
                        record["previous_hash"] == previous, "JOURNAL_CORRUPT")
                anchor = json.loads((self.root / "anchor-{:06d}.json".format(number)).read_bytes())
                require(anchor == {"sequence": number, "hash": digest(record)}, "JOURNAL_CORRUPT")
                previous = digest(record)
                events.append(record)
            for event in events:
                if event["kind"] in ("INTENT", "SEND_CLAIMED"):
                    prefix = "intent-" if event["kind"] == "INTENT" else "claim-"
                    path = self.root / (prefix + self.key(event["data"]["question_id"]) + ".json")
                    require(json.loads(path.read_bytes()) == event["data"], "JOURNAL_CORRUPT")
            for path in self.root.glob("intent-*.json"):
                item = json.loads(path.read_bytes())
                require(any(e["kind"] == "INTENT" and e["data"] == item for e in events), "JOURNAL_CORRUPT")
            for path in self.root.glob("claim-*.json"):
                item = json.loads(path.read_bytes())
                require(any(e["kind"] == "SEND_CLAIMED" and e["data"] == item for e in events), "JOURNAL_CORRUPT")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise PilotError("JOURNAL_CORRUPT") from exc
        return events

    def append(self, kind, data):
        require(self._gate is not None, "BOOK_LOCK_REQUIRED")
        events = self.read()
        number = len(events) + 1
        record = {"sequence": number, "previous_hash": digest(events[-1]) if events else None,
                  "owner": self.owner, "kind": kind, "data": data}
        exclusive(self.root / "event-{:06d}.json".format(number), record)
        exclusive(self.root / "anchor-{:06d}.json".format(number), {"sequence": number, "hash": digest(record)})
        return record

    def begin(self, request_hash, question_ids):
        require(not self.read() and not list(self.root.glob("intent-*")) and not list(self.root.glob("claim-*")),
                "BOOK_ALREADY_STARTED")
        self.append("BATCH", {"input_hash": request_hash,
                              "questions": {qid: "NOT_RUN" for qid in question_ids}})

    @staticmethod
    def key(question_id):
        return hashlib.sha256(question_id.encode("utf-8")).hexdigest()

    def intent(self, question_id, value):
        require(not any(e["kind"] == "INTENT" and e["data"]["question_id"] == question_id for e in self.read()),
                "INTENT_ALREADY_EXISTS")
        value = dict(value, question_id=question_id)
        self.append("INTENT", value)
        exclusive(self.root / ("intent-" + self.key(question_id) + ".json"), value)
        return value

    def claim(self, question_id, intent):
        events = self.read()
        require(any(e["kind"] == "INTENT" and e["data"] == intent for e in events), "DURABLE_INTENT_REQUIRED")
        require(not any(e["kind"] == "SEND_CLAIMED" and e["data"]["question_id"] == question_id for e in events),
                "SEND_ALREADY_CLAIMED")
        value = {"question_id": question_id, "intent_hash": digest(intent)}
        # Create the capability first. A crash before its event causes corruption, never replay.
        exclusive(self.root / ("claim-" + self.key(question_id) + ".json"), value)
        # append cannot read this pending claim; finish its event without normal read verification.
        paths = sorted(self.root.glob("event-*.json"))
        last = json.loads(paths[-1].read_bytes())
        number = len(paths) + 1
        record = {"sequence": number, "previous_hash": digest(last), "owner": self.owner,
                  "kind": "SEND_CLAIMED", "data": value}
        exclusive(self.root / "event-{:06d}.json".format(number), record)
        exclusive(self.root / "anchor-{:06d}.json".format(number), {"sequence": number, "hash": digest(record)})
        self.read()
        return value

    def report(self):
        events = self.read()
        batch = next((e["data"] for e in events if e["kind"] == "BATCH"), {"questions": {}})
        questions = {qid: {"state": "NOT_RUN", "frames": "UNAVAILABLE", "content": "PENDING"}
                     for qid in batch["questions"]}
        for event in events:
            data = event["data"]
            if event["kind"] == "INTENT":
                questions[data["question_id"]].update(state="UNKNOWN")
            if event["kind"] == "RESULT":
                questions[data["question_id"]].update(data)
        releases = [e["data"] for e in events if e["kind"] == "RELEASE"]
        return {"status": "REVIEW", "mode": "OFFLINE" if self.offline else "PLATFORM", "questions": questions,
                "independent_acceptance": "PENDING", "release": releases[-1] if releases else {"released": False},
                "submission_status": "NOT_SUBMITTED", "platform_fact": "NOT_PROVED", "event_count": len(events)}
