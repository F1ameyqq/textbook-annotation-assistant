"""Run or resume a local B batch, then independently audit its persisted result.

Default recognition is geometric. --ocr explicitly opts into the local CPU OCR
backend. Successful execution or cache reuse never authorizes business PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class BatchCLIError(RuntimeError):
    def __init__(self, stage, error):
        self.stage = stage
        self.original = error
        super().__init__(str(error))


def local_path(value):
    """Accept filesystem paths, rejecting URLs and network-share locations."""
    if (value.startswith(("\\\\", "//")) or "://" in value
            or (re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value)
                and not re.match(r"^[A-Za-z]:[\\/]", value))):
        raise argparse.ArgumentTypeError("a local filesystem path is required; URLs and network shares are unsupported")
    return Path(value)


def positive_int(value):
    try:
        count = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("--max-items must be a positive integer") from None
    if count < 1:
        raise argparse.ArgumentTypeError("--max-items must be a positive integer")
    return count


def reference(artifact):
    return {key: artifact[key] for key in ("artifact_id", "revision", "content_hash")}


def _save_check(workdir, report, check):
    name = report.get("run_id", report["artifact_id"])
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
        raise ValueError("batch report has no safe local receipt identity")
    relative = Path("checks") / (name + ".json")
    path = Path(workdir) / relative
    encoded = (json.dumps(check, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(encoded)
    except FileExistsError:
        if path.read_bytes() != encoded:
            raise ValueError("immutable batch check receipt already exists with different content") from None
    return dict(path=relative.as_posix(), sha256=hashlib.sha256(encoded).hexdigest(), artifact_ref=reference(check))


def execute(source_path, workdir, *, use_ocr=False, max_items=None, runner=None, auditor=None):
    """Run one invocation and persist its independent check without overwriting."""
    # These imports stay inside the call so --help and invalid network paths
    # never initialize a recognizer, a cache or an OCR dependency.
    try:
        if runner is None:
            from annotation.recognition.batch import run_batch
            runner = run_batch
        if auditor is None:
            from annotation.recognition.batch_quality import audit_batch
            auditor = audit_batch
    except Exception as exc:
        raise BatchCLIError("SETUP_FAILED", exc) from exc
    try:
        report = runner(Path(source_path), Path(workdir), use_ocr=use_ocr, max_items=max_items)
    except Exception as exc:
        raise BatchCLIError("RUN_FAILED", exc) from exc
    try:
        check = auditor(Path(source_path), Path(workdir), report)
        checked = check["payload"]
        payload = report["payload"]
        if (check["schema_version"] != "b-batch-check-trial/0.1"
                or type(checked["accepted"]) is not bool
                or checked["decision"] != "HOLD" or checked["business_acceptance"] is not False
                or checked["transcription_verified"] is not False
                or checked["platform_actions"] != []
                or payload["decision"] != "HOLD" or payload["business_acceptance"] is not False
                or payload["transcription_verified"] is not False or payload["platform_actions"] != []):
            raise ValueError("batch/audit must retain explicit HOLD and unverified business status")
        counts = payload["counts"]
        state = "FAILED" if counts["failed"] else "READY" if payload["batch_complete"] else "PARTIAL"
        execution_kind = payload["recognizer"]["execution_kind"]
        report_ref = reference(report)
    except Exception as exc:
        raise BatchCLIError("AUDIT_FAILED", exc) from exc
    try:
        check_descriptor = _save_check(workdir, report, check)
    except Exception as exc:
        raise BatchCLIError("RECEIPT_FAILED", exc) from exc
    successful_execution = checked["accepted"] and state != "FAILED"
    return dict(schema_version="b-batch-cli-result-trial/0.1", batch_state=state,
        recognition_mode="CPU_OCR" if use_ocr else "GEOMETRIC",
        execution_kind=execution_kind, decision="HOLD",
        integrity_accepted=checked["accepted"], business_acceptance=False, transcription_verified=False,
        audit_performed=True, report_ref=report_ref, check=check_descriptor,
        counts=counts, batch_complete=payload["batch_complete"], issues=checked["issues"],
        exit_code=0 if successful_execution else 1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=local_path, required=True, help="local provisional source manifest")
    parser.add_argument("--workdir", type=local_path, required=True, help="persistent batch directory; existing directory resumes")
    parser.add_argument("--ocr", action="store_true", help="explicitly enable the local CPU OCR backend")
    parser.add_argument("--max-items", type=positive_int, help="limit worker calls this invocation; declared source scope stays unchanged")
    args = parser.parse_args(argv)
    try:
        result = execute(args.source, args.workdir, use_ocr=args.ocr, max_items=args.max_items)
    except BatchCLIError as exc:
        result = dict(schema_version="b-batch-cli-result-trial/0.1", batch_state="FAILED",
            recognition_mode="CPU_OCR" if args.ocr else "GEOMETRIC", decision="HOLD",
            integrity_accepted=False, business_acceptance=False, transcription_verified=False,
            audit_performed=exc.stage not in ("RUN_FAILED", "SETUP_FAILED"), error=dict(stage=exc.stage,
                type=type(exc.original).__name__, message=str(exc.original)), exit_code=1)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
