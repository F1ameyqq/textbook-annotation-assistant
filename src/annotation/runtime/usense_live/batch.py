"""Private B-side batch format, not a public contract or a transport.

prepare/status acquire no browser. Explicit identities and existing updater,
writer and predecessor verifier govern each send. UNKNOWN never means retry.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import re

from .core import implementation_digest, sha, utc
from .config import endpoints
from .revision import released, same, verify_previous_acceptance
from .update import BOOK, digest, from_captured_map, json_same, loads, make_plan, require, validate_plan

MANIFEST = "b-usense-reviewed-batch-manifest/0.1"
PLAN = "b-usense-reviewed-batch-plan/0.1"
MAX_AGE = 900
MAPPING = ("item_id", "printed_number", "variant", "native_order", "node_id", "info_id")


def read(path):
    return loads(Path(path).read_bytes())


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def ref_bytes(ref):
    require(type(ref) is dict and set(ref) == {"path", "sha256"}, "BATCH_FILE_REF_REQUIRED")
    require(type(ref["path"]) is str and Path(ref["path"]).is_absolute(), "BATCH_ABSOLUTE_REF_REQUIRED")
    raw = Path(ref["path"]).read_bytes()
    require(sha(raw) == ref["sha256"], "BATCH_EVIDENCE_HASH_CHANGED")
    return raw


def file_ref(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": sha(path.read_bytes())}


def _fresh(observed, now):
    age = (now - utc(observed)).total_seconds()
    require(0 <= age <= MAX_AGE, "BATCH_BASELINE_STALE_OR_FUTURE")


def load_baseline(captures, now):
    """Merge collector summaries; raw overlap must be byte identical."""
    require(type(captures) is list and bool(captures), "BATCH_CAPTURE_EVIDENCE_REQUIRED")
    native, files, observations = {}, {}, []
    for ref in captures:
        summary = loads(ref_bytes(ref))
        require(summary.get("schema") == "UsenseNativeCapture/v1" and summary.get("book_id") == BOOK and
                summary.get("status") == "NATIVE_GETS_CAPTURED" and
                type(summary.get("save_attempts")) is int and summary["save_attempts"] == 0 and
                released(summary.get("release", {})), "BATCH_CAPTURE_NOT_SUCCESSFULLY_RELEASED")
        _fresh(summary["finished_at"], now)
        require(type(summary.get("captures")) is dict and bool(summary["captures"]), "BATCH_EMPTY_CAPTURE")
        parent = Path(ref["path"]).resolve().parent
        for name, row in summary["captures"].items():
            require(re.fullmatch(r"directory|frames|source|page_[0-9]+|q[1-9][0-9]*_(?:annotations|info|question|choice|answer|analysis|knowledge_point)", name)
                    is not None, "BATCH_CAPTURE_NAME")
            require(row.get("filename") == name + ".json" and type(row.get("status")) is int and row["status"] == 200 and
                    type(row.get("request_counts")) is dict and set(row["request_counts"]) == {"context", "native"} and
                    all(type(value) is int and value == 1 for value in row["request_counts"].values()), "BATCH_CAPTURE_ROW_INVALID")
            path = parent / (name + ".json")
            raw = path.read_bytes()
            require(sha(raw) == row.get("sha256") and type(row.get("bytes")) is int and len(raw) == row["bytes"],
                    "BATCH_CAPTURE_RAW_CHANGED")
            _fresh(row["observed_at"], now)
            require(utc(row["observed_at"]) <= utc(summary["finished_at"]), "BATCH_CAPTURE_TIME_ORDER")
            value = loads(raw)
            require(type(value) is dict and type(value.get("code")) is int and value["code"] == 0,
                    "BATCH_CAPTURE_BUSINESS_FAILURE")
            if name in files:
                require(files[name]["sha256"] == sha(raw), "BATCH_CAPTURE_OVERLAP_CHANGED")
            else:
                files[name], native[name] = file_ref(path), value
            observations.append(row["observed_at"])
    return native, files, min(observations, key=utc)


def _predecessor(item, plan, native, ledger):
    previous = item.get("previous_acceptance")
    if previous is not None:
        ref_bytes(previous)
        proof = verify_previous_acceptance(previous["path"], plan, native, ledger)
        return proof["intent_key"], proof["evidence_file_sha256"]
    require(not list(ledger.glob(plan["ledger_key"] + "*.json")), "BATCH_EXISTING_IDENTITY_INTENT_REQUIRES_PREDECESSOR")
    return plan["ledger_key"], {}


def prepare(manifest_path, manifest_sha256, ledger_root, *, now=None):
    now = now or datetime.now(timezone.utc)
    manifest_ref = {"path": str(Path(manifest_path).resolve()), "sha256": manifest_sha256}
    manifest = loads(ref_bytes(manifest_ref))
    require(type(manifest) is dict and set(manifest) == {
        "schema", "book_id", "source_lesson", "lesson_directory_id", "scope_review", "captures", "items"},
        "BATCH_MANIFEST_SHAPE")
    require(manifest["schema"] == MANIFEST and manifest["book_id"] == BOOK, "BATCH_MANIFEST_SCOPE")
    require(all(type(manifest[k]) is str and bool(manifest[k].strip()) for k in ("source_lesson", "lesson_directory_id")),
            "BATCH_LESSON_SCOPE_REQUIRED")
    items = manifest["items"]
    require(type(items) is list and 1 <= len(items) <= 100, "BATCH_EXPLICIT_ITEMS_REQUIRED")
    mapping = []
    seen = {key: set() for key in ("item_id", "node_id", "info_id", "native_order", "printed")}
    for item in items:
        require(type(item) is dict and set(item) == set(MAPPING) | {"candidate", "pages", "previous_acceptance"}, "BATCH_ITEM_SHAPE")
        require(type(item["item_id"]) is str and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", item["item_id"]), "BATCH_ITEM_ID")
        require(all(type(item[k]) is str and bool(item[k].strip()) for k in ("printed_number", "variant", "node_id", "info_id")),
                "BATCH_EXPLICIT_PRINTED_MAPPING_REQUIRED")
        require(type(item["native_order"]) is int and 1 <= item["native_order"] <= 9999, "BATCH_NATIVE_ORDER")
        for key in seen:
            value = (item["printed_number"], item["variant"]) if key == "printed" else item[key]
            require(value not in seen[key], "BATCH_DUPLICATE_IDENTITY_OR_MAPPING")
            seen[key].add(value)
        mapping.append({k: item[k] for k in MAPPING})
    scope = loads(ref_bytes(manifest["scope_review"]))
    require(same(scope, {"schema": "b-usense-batch-scope-review/0.1", "book_id": BOOK,
                             "source_lesson": manifest["source_lesson"], "lesson_directory_id": manifest["lesson_directory_id"],
                             "directory_membership": "CONFIRMED", "mapping": mapping}), "BATCH_SCOPE_REVIEW_CONFLICT_OR_MISMATCH")
    native, baseline_files, oldest = load_baseline(manifest["captures"], now)
    info_ids = [value.get("data", {}).get("id") for name, value in native.items() if re.fullmatch(r"q[1-9][0-9]*_info", name)]
    require(all(type(value) is str and value for value in info_ids) and len(info_ids) == len(set(info_ids)), "BATCH_AMBIGUOUS_CAPTURED_INFO_ID")
    ledger = Path(ledger_root).resolve()
    require(ledger.is_dir(), "BATCH_EXISTING_LEDGER_DIRECTORY_REQUIRED")
    refs = [manifest_ref, manifest["scope_review"], *manifest["captures"]]
    evidence = {ref["path"]: ref["sha256"] for ref in refs}
    prepared = []
    for item in items:
        q = item["native_order"]
        names = endpoints([q], item["pages"], source=True)
        require(bool(item["pages"]) and all(name in native for name in names), "BATCH_NATIVE_EVIDENCE_MISSING")
        target = {"book_id": BOOK, "lesson_directory_id": manifest["lesson_directory_id"],
                  "node_id": item["node_id"], "info_id": item["info_id"], "question_order": q}
        candidate = loads(ref_bytes(item["candidate"]))
        require(type(candidate) is dict and set(candidate) == {"target", "approved_changes"} and
                same(candidate["target"], target), "BATCH_CANDIDATE_IDENTITY_MISMATCH")
        evidence[item["candidate"]["path"]] = item["candidate"]["sha256"]
        plan = make_plan(from_captured_map(native, f"q{q}_"), target, candidate["approved_changes"])
        validate_plan(plan)
        require(bool(plan["approved_changes"]), "BATCH_REVIEWED_CHANGES_REQUIRED")
        for review in plan["approved_changes"].values():
            source = {"path": review["source_ref"], "sha256": review["source_sha256"]}
            ref_bytes(source)
            require(Path(review["review_ref"]).is_absolute(), "BATCH_ABSOLUTE_REF_REQUIRED")
            record = file_ref(review["review_ref"])
            evidence[source["path"]], evidence[record["path"]] = source["sha256"], record["sha256"]
        required_pages = {int(frame["page_index"]) for frame in plan["before"]["annotations"]["data"]}
        require(required_pages <= set(item["pages"]), "BATCH_FRAME_SOURCE_PAGE_MISSING")
        selected = {name: native[name] for name in names}
        intent, prior_evidence = _predecessor(item, plan, selected, ledger)
        evidence.update(prior_evidence)
        prepared.append({"mapping": {k: item[k] for k in MAPPING}, "plan": plan, "pages": item["pages"],
                         "previous_acceptance": item["previous_acceptance"], "intent_key": intent,
                         "baseline_files": {name: baseline_files[name] for name in names}})
    result = {"schema": PLAN, "book_id": BOOK, "source_lesson": manifest["source_lesson"],
              "lesson_directory_id": manifest["lesson_directory_id"], "manifest": manifest_ref,
              "implementation_sha256": implementation_digest(), "created_at": now.isoformat(),
              "oldest_observed_at": oldest, "max_baseline_age_seconds": MAX_AGE, "ledger_root": str(ledger),
              "evidence_file_sha256": evidence, "items": prepared,
              "status": "OFFLINE_PREPARED_NOT_PLATFORM_ACCEPTED", "automatic_retry_allowed": False}
    result["batch_sha256"] = digest(result)
    return result


def validate_batch(plan, *, fresh=False, now=None):
    require(type(plan) is dict and plan.get("schema") == PLAN, "BATCH_PLAN_SCHEMA")
    expected = dict(plan)
    expected.pop("batch_sha256", None)
    require(digest(expected) == plan.get("batch_sha256"), "BATCH_PLAN_CHANGED")
    require(plan["implementation_sha256"] == implementation_digest(), "BATCH_IMPLEMENTATION_CHANGED")
    for path, checksum in plan["evidence_file_sha256"].items():
        ref_bytes({"path": path, "sha256": checksum})
    for item in plan["items"]:
        validate_plan(item["plan"])
        for ref in item["baseline_files"].values():
            ref_bytes(ref)
    if fresh:
        _fresh(plan["oldest_observed_at"], now or datetime.now(timezone.utc))
    return plan


def inspect_state(plan, execution_root, *, now=None, running=False):
    """Read-only resume audit. A partial dispatch always blocks replay."""
    validate_batch(plan)
    root = Path(execution_root).resolve()
    require(running or not (root / "batch-running.lock").exists(), "BATCH_EXECUTION_LOCK_REQUIRES_OPERATOR_REVIEW")
    if (root / "batch-binding.json").exists():
        require(read(root / "batch-binding.json") == {"batch_sha256": plan["batch_sha256"]}, "BATCH_EXECUTION_ROOT_ALREADY_BOUND")
    rows, blocked = [], False
    for item in plan["items"]:
        ident, update = item["mapping"]["item_id"], item["plan"]
        qdir = root / ident
        row = {"item_id": ident, "mapping": item["mapping"], "status": "READY"}
        try:
            if (qdir / "dispatch.json").exists():
                require(read(qdir / "dispatch.json") == {"batch_sha256": plan["batch_sha256"], "intent_key": item["intent_key"]},
                        "BATCH_DISPATCH_BINDING_CHANGED")
                require(update["mutation_required"], "BATCH_NOOP_DISPATCH_UNEXPECTED")
                require(json_same(read(qdir / "plan.json"), update), "BATCH_EXECUTED_PLAN_CHANGED")
                writer = read(qdir / "writer-process-result.json")["result"]
                require(writer.get("intent_key", writer.get("ledger_key")) == item["intent_key"], "BATCH_EXECUTED_INTENT_CHANGED")
                rp = read(qdir / "reader-process-result.json")["result"]
                config = read(qdir / "independent-reader-config.json")
                names = endpoints([update["target"]["question_order"]], item["pages"], source=True)
                from .config import capture_endpoints
                from types import SimpleNamespace
                require(set(capture_endpoints(SimpleNamespace(data=config))) == set(names), "BATCH_READER_ENDPOINTS_CHANGED")
                require(config["run_id"] == rp["run_id"], "BATCH_READER_RUN_CHANGED")
                # Config path/run scope is proved before any result-selected read.
                require(re.fullmatch(r"usense-readonly-[a-z0-9-]{1,64}", rp["run_id"]), "BATCH_READER_RUN_PATH")
                after = {name: read(root / rp["run_id"] / (name + ".json")) for name in names}
                current = make_plan(from_captured_map(after, f'q{update["target"]["question_order"]}_'), update["target"], update["approved_changes"])
                verify_previous_acceptance(qdir / "acceptance.json", current, after, Path(plan["ledger_root"]))
                row["status"] = "ACCEPTED"
            else:
                require(not qdir.exists(), "BATCH_PARTIAL_ITEM_DIRECTORY_NO_RETRY")
                native = {name: loads(ref_bytes(ref)) for name, ref in item["baseline_files"].items()}
                _predecessor(item, update, native, Path(plan["ledger_root"]))
                row["status"] = "READY" if update["mutation_required"] else "NO_CHANGE_OFFLINE"
        except (ValueError, OSError, KeyError, TypeError) as exc:
            row.update(status="BLOCKED_NO_RETRY", reason=getattr(exc, "code", type(exc).__name__))
            blocked = True
        rows.append(row)
    ready = [row for row in rows if row["status"] == "READY"]
    if ready:
        try:
            validate_batch(plan, fresh=True, now=now)
        except ValueError as exc:
            blocked = True
            for row in ready:
                row.update(status="BLOCKED_NO_RETRY", reason=getattr(exc, "code", str(exc)))
    pending_seen = False
    for row in rows:
        if row["status"] in ("READY", "BLOCKED_NO_RETRY"):
            pending_seen = True
        elif row["status"] == "ACCEPTED" and pending_seen:
            row.update(status="BLOCKED_NO_RETRY", reason="BATCH_NONSEQUENTIAL_HISTORY")
            blocked = True
    return {"schema": "b-usense-reviewed-batch-state/0.1", "batch_sha256": plan["batch_sha256"],
            "status": "BLOCKED_NO_RETRY" if blocked else "READY" if ready else "COMPLETE_OFFLINE_AUDIT",
            "next_item_id": None if blocked or not ready else ready[0]["item_id"], "items": rows,
            "automatic_retry_allowed": False, "platform_requests": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare", help="offline dry-run; validate every item before creating output")
    for name in ("manifest", "sha256", "ledger-root", "out"):
        prep.add_argument("--" + name, required=True)
    status = commands.add_parser("status", help="offline per-item evidence audit and resume cursor")
    for name in ("plan", "sha256", "execution-root"):
        status.add_argument("--" + name, required=True)
    run = commands.add_parser("run", help="explicit live execution using existing writer; no automatic retries")
    for name in ("plan", "sha256", "execution-root", "profile", "authorization-reference"):
        run.add_argument("--" + name, required=True)
    run.add_argument("--dependency-dir")
    run.add_argument("--tls-approval-reference")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            value = prepare(args.manifest, args.sha256, args.ledger_root)
            out = Path(args.out).resolve()
            out.mkdir(parents=True, exist_ok=False)
            write_new(out / "batch-plan.json", value)
            print(json.dumps({"status": value["status"], "items": len(value["items"]),
                  "plan": str(out / "batch-plan.json"), "sha256": sha((out / "batch-plan.json").read_bytes()), "platform_requests": 0}))
        else:
            value = loads(ref_bytes({"path": str(Path(args.plan).resolve()), "sha256": args.sha256}))
            if args.command == "run":
                from .batch_runner import run_batch
                result = run_batch(value, args)
            else:
                result = inspect_state(value, args.execution_root)
            print(json.dumps(result, ensure_ascii=True))
            return 2 if result["status"] == "BLOCKED_NO_RETRY" else 0
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED_NO_RETRY", "error": getattr(exc, "code", type(exc).__name__),
                          "automatic_retry_allowed": False}))
        return 2
