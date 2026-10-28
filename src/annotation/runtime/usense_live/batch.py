"""Hash-bound batch preparation. No browser, network or ledger mutation."""
from pathlib import Path
import re

from .config import endpoints
from .core import plain_path, require, sha
from .update import loads, make_plan, from_captured_map, json_same
from .writer import validate_inputs
from .transport import validate_transport

SCHEMA = "UsenseReviewedTargetManifest/v1"


def prepare(manifest_path, manifest_sha256, baseline, profile, authorization_reference):
    """Prepare every target before the caller may start the first writer.

    Printed numbers and semantic lessons are descriptive provenance. Native
    order, actual parent, node and info identity must agree with current raw.
    Existing writer/revision validation remains the ledger authority.
    """
    evidence = {}

    def raw(path, expected=None):
        path = plain_path(str(path))
        require(path.is_file(), "BATCH_INPUT_FILE_REQUIRED")
        value = path.read_bytes()
        digest = sha(value)
        if expected is not None:
            require(type(expected) is str and re.fullmatch(r"[0-9a-f]{64}", expected) and
                    digest == expected, "BATCH_INPUT_HASH_MISMATCH")
        evidence[str(path)] = digest
        return value

    def ref(value):
        require(type(value) is dict and set(value) == {"path", "sha256"}, "BATCH_FILE_REFERENCE")
        return raw(value["path"], value["sha256"])

    manifest = loads(raw(manifest_path, manifest_sha256))
    require(type(manifest) is dict and set(manifest) == {"schema", "book_id", "baseline", "targets"} and
            manifest["schema"] == SCHEMA and manifest["book_id"] == "46007447", "BATCH_MANIFEST_SCHEMA")
    baseline, profile = plain_path(str(baseline)), plain_path(str(profile))
    require(baseline.is_dir() and profile.is_dir(), "BATCH_DIRECTORIES_REQUIRED")
    ledger = profile.parent / "usense-existing-ledger"
    # A missing ledger is an empty ledger, created only by the execution caller.
    # Preparation itself never creates it or modifies any existing marker.
    require(ledger.is_dir(), "LEDGER_DIRECTORY_REQUIRED")
    bound = manifest["baseline"]
    require(type(bound) is dict and set(bound) == {"capture_summary_sha256", "files"}, "BATCH_BASELINE_BINDING")
    summary = loads(raw(baseline / "capture-summary.json", bound["capture_summary_sha256"]))
    require(summary.get("status") == "NATIVE_GETS_CAPTURED" and summary.get("book_id") == "46007447" and
            type(summary.get("save_attempts")) is int and summary["save_attempts"] == 0 and
            summary.get("release", {}).get("context_runtime_release_confirmed") is True,
            "BATCH_BASELINE_NOT_COMPLETE_RELEASED_READONLY")
    validate_transport(summary.get("transport"))
    files = bound["files"]
    require(type(files) is dict and set(files) == set(summary["captures"]), "BATCH_BASELINE_FILE_SET")
    native = {}
    for name, digest in files.items():
        require(re.fullmatch(r"directory|frames|source|page_[0-9]+|q[0-9]+_(?:annotations|info|question|choice|answer|analysis|knowledge_point)", name),
                "BATCH_CAPTURE_NAME")
        value = raw(baseline / (name + ".json"), digest)
        cap = summary["captures"][name]
        require(cap.get("filename") == name + ".json" and cap.get("sha256") == digest and
                cap.get("bytes") == len(value) and type(cap.get("status")) is int and cap["status"] == 200 and
                cap.get("request_counts") == {"context": 1, "native": 1}, "BATCH_CAPTURE_RAW_BINDING")
        native[name] = loads(value)
        require(type(native[name]) is dict and type(native[name].get("code")) is int and native[name]["code"] == 0,
                "BATCH_CAPTURE_BUSINESS_FAILURE")
    targets = manifest["targets"]
    require(type(targets) is list and 1 <= len(targets) <= 6, "BATCH_ONE_TO_SIX_TARGETS")
    seen = {key: set() for key in ("node_id", "info_id", "question_order", "printed")}
    prepared, ledger_files = [], {}
    for item in targets:
        require(type(item) is dict and set(item) == {"printed_question", "semantic_lesson", "target", "source_pages",
                "candidate", "review_evidence", "previous_acceptance"}, "BATCH_TARGET_FIELDS")
        target, printed, lesson = item["target"], item["printed_question"], item["semantic_lesson"]
        require(type(printed) is int and printed > 0 and type(lesson) is str and bool(lesson.strip()), "BATCH_PRINTED_LESSON_REQUIRED")
        require(type(target) is dict, "BATCH_TARGET_IDENTITY")
        for key in ("node_id", "info_id", "question_order"):
            value = target.get(key)
            require(type(value) in (str, int) and type(value) is not bool and value not in seen[key], "BATCH_DUPLICATE_TARGET")
            seen[key].add(value)
        require((lesson, printed) not in seen["printed"], "BATCH_DUPLICATE_PRINTED_QUESTION")
        seen["printed"].add((lesson, printed))
        candidate = loads(ref(item["candidate"]))
        require(type(candidate) is dict and set(candidate) == {"target", "approved_changes"} and
                json_same(candidate["target"], target), "BATCH_CANDIDATE_TARGET_MISMATCH")
        order = target["question_order"]
        plan = make_plan(from_captured_map(native, f"q{order}_"), target, candidate["approved_changes"])
        pages = item["source_pages"]
        require(type(pages) is list and bool(pages), "BATCH_SOURCE_PAGES_REQUIRED")
        names = endpoints([order], pages, source=True)
        require(set(names) <= set(native), "BATCH_SOURCE_OR_TARGET_INPUT_MISSING")
        require(all(type(frame.get("page_index")) is int and frame["page_index"] in pages
                    for frame in plan["before"]["annotations"]["data"]), "BATCH_FRAME_PAGE_NOT_BOUND")
        refs = item["review_evidence"]
        require(type(refs) is dict, "BATCH_REVIEW_EVIDENCE_REQUIRED")
        needed = {rv[key] for rv in plan["approved_changes"].values() for key in ("source_ref", "review_ref")}
        require(set(refs) == needed, "BATCH_REVIEW_EVIDENCE_SET")
        for path, digest in refs.items():
            raw(path, digest)
        previous = item["previous_acceptance"]
        if previous is not None:
            ref(previous)
        identity_files = {str(path): sha(raw(path)) for path in sorted(ledger.glob(plan["ledger_key"] + "*.json"))}
        require(previous is not None or not identity_files, "BATCH_EXISTING_IDENTITY_REQUIRES_ACCEPTED_PREDECESSOR")
        revision = {}
        _, claim = validate_inputs(plan, baseline, names, ledger, authorization_reference,
                None if previous is None else previous["path"], revision)
        for path, digest in revision.get("evidence_file_sha256", {}).items():
            raw(path, digest)
        ledger_files[plan["ledger_key"]] = identity_files
        prepared.append({"printed_question": printed, "semantic_lesson": lesson, "target": target,
                "source_pages": pages, "plan": plan, "candidate": item["candidate"],
                "review_evidence": refs, "previous_acceptance": previous, "intent_key": claim.stem,
                "ledger_files": identity_files})
    return {"schema": "UsensePreparedBatch/v1", "manifest_sha256": manifest_sha256,
            "targets": prepared, "evidence_file_sha256": evidence, "ledger_root": str(ledger), "transport": summary["transport"]}


def recheck(prepared, pending):
    """Recheck immutable inputs and pending target ledgers before each process."""
    for path, digest in prepared["evidence_file_sha256"].items():
        require(sha(plain_path(path).read_bytes()) == digest, "BATCH_PREPARED_INPUT_CHANGED")
    ledger = Path(prepared["ledger_root"])
    for item in pending:
        current = {str(p): sha(p.read_bytes()) for p in ledger.glob(item["plan"]["ledger_key"] + "*.json")}
        require(current == item["ledger_files"], "BATCH_PENDING_LEDGER_CHANGED_NO_RETRY")
