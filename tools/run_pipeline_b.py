"""Run/resume B's offline stages and persist an independent execution audit.

Without --ocr, live runs stop after geometric recognition. --evidence imports
an existing source-bound refined EvidenceBundle without running an OCR model.
--recovery applies an explicit local recovery package as independently cached
evidence and review stages; it never enables OCR by itself.
--continuation and --adjacent-source explicitly add local source/proof/apply
and independent continuation checks; they never enable a website operation.
--inline and --inline-source attach saved inline observations and their journal
without running an OCR or formula model.
READY means the offline stages ran, while all business results remain HOLD.
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


class PipelineCLIError(RuntimeError):
    def __init__(self, stage, original):
        self.stage = stage
        self.original = original
        super().__init__(str(original))


def local_path(value):
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


def reference(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def _save_check(workdir, report, check):
    name = report.get("run_id", report["artifact_id"])
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
        raise ValueError("pipeline report has no safe local receipt identity")
    relative = Path("checks") / (name + ".json")
    path = Path(workdir) / relative
    encoded = (json.dumps(check, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(encoded)
    except FileExistsError:
        if path.read_bytes() != encoded:
            raise ValueError("immutable pipeline check receipt already exists with different content") from None
    return dict(path=relative.as_posix(), sha256=hashlib.sha256(encoded).hexdigest(), artifact_ref=reference(check))


def execute(source_path, context_path, review_path, workdir, *, use_ocr=False,
            max_items=None, stop_after=None, evidence_path=None, recovery_path=None,
            continuation_path=None, adjacent_source_path=None,
            inline_path=None, inline_source_path=None,
            runner=None, auditor=None):
    try:
        if runner is None:
            from annotation.recognition.pipeline import run_pipeline
            runner = run_pipeline
        if auditor is None:
            from annotation.recognition.pipeline_quality import audit_pipeline
            auditor = audit_pipeline
    except Exception as exc:
        raise PipelineCLIError("SETUP_FAILED", exc) from exc
    source_path, context_path, review_path, workdir = map(Path,
        (source_path, context_path, review_path, workdir))
    evidence_path = Path(evidence_path) if evidence_path is not None else None
    recovery_path = Path(recovery_path) if recovery_path is not None else None
    continuation_path = Path(continuation_path) if continuation_path is not None else None
    adjacent_source_path = Path(adjacent_source_path) if adjacent_source_path is not None else None
    inline_path = Path(inline_path) if inline_path is not None else None
    inline_source_path = Path(inline_source_path) if inline_source_path is not None else None
    try:
        report = runner(source_path, context_path, review_path, workdir, use_ocr=use_ocr,
            max_items=max_items, stop_after=stop_after, evidence_path=evidence_path,
            recovery_path=recovery_path, continuation_path=continuation_path,
            adjacent_source_path=adjacent_source_path, inline_path=inline_path, inline_source_path=inline_source_path)
    except Exception as exc:
        raise PipelineCLIError("RUN_FAILED", exc) from exc
    try:
        check = auditor(source_path, context_path, review_path, report, workdir,
            evidence_path=evidence_path, recovery_path=recovery_path,
            continuation_path=continuation_path, adjacent_source_path=adjacent_source_path,
            inline_path=inline_path, inline_source_path=inline_source_path)
        payload, checked = report["payload"], check["payload"]
        if (check["schema_version"] != "b-pipeline-check-trial/0.1"
                or type(checked["accepted"]) is not bool
                or any(value.get("decision") != "HOLD" or value.get("business_acceptance") is not False
                       or value.get("transcription_verified") is not False or value.get("platform_actions") != []
                       for value in (payload, checked))):
            raise ValueError("pipeline/audit must retain explicit HOLD and unverified business status")
        state, mode, counts = payload["pipeline_state"], payload["mode"], payload["counts"]
        if state not in {"PARTIAL", "READY", "FAILED"} or mode not in {"LIVE_BATCH", "CACHED_INPUT"}:
            raise ValueError("unsupported pipeline state or execution mode")
        report_ref = reference(report)
    except Exception as exc:
        raise PipelineCLIError("AUDIT_FAILED", exc) from exc
    try:
        descriptor = _save_check(workdir, report, check)
    except Exception as exc:
        raise PipelineCLIError("RECEIPT_FAILED", exc) from exc
    return dict(schema_version="b-pipeline-cli-result-trial/0.1", pipeline_state=state, mode=mode,
        decision="HOLD", integrity_accepted=checked["accepted"], business_acceptance=False,
        transcription_verified=False, audit_performed=True, report_ref=report_ref, check=descriptor,
        counts=counts, issues=checked["issues"], exit_code=0 if checked["accepted"] and state != "FAILED" else 1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=local_path, required=True, help="complete declared local source manifest")
    parser.add_argument("--context", type=local_path, required=True, help="source-bound section windows")
    parser.add_argument("--review", type=local_path, required=True, help="source-bound development review/census")
    parser.add_argument("--workdir", type=local_path, required=True, help="persistent offline pipeline directory")
    parser.add_argument("--ocr", action="store_true", help="explicitly enable live baseline and answer-row CPU OCR")
    parser.add_argument("--max-items", type=positive_int, help="bound this live recognition invocation without shrinking scope")
    parser.add_argument("--stop-after", choices=("recognition", "refine", "recover", "assemble", "recovery_review", "quality",
        "continuation_prepare", "continuation_proof", "continuation_apply", "continuation_quality",
        "inline_prepare", "inline_apply", "inline_quality"))
    parser.add_argument("--evidence", type=local_path, help="import an existing refined 0.2/0.3 EvidenceBundle; no new OCR")
    parser.add_argument("--recovery", type=local_path, help="explicit local source-bound recovery package; no new OCR")
    parser.add_argument("--continuation", type=local_path, help="explicit local continuation package; requires --adjacent-source")
    parser.add_argument("--adjacent-source", type=local_path, help="original adjacent image bound to --continuation")
    parser.add_argument("--inline", type=local_path, help="saved inline package; requires --inline-source and runs no models")
    parser.add_argument("--inline-source", type=local_path, help="original source image bound to --inline")
    args = parser.parse_args(argv)
    if args.evidence is not None and (args.ocr or args.max_items is not None):
        parser.error("--evidence cannot be combined with --ocr or --max-items")
    if args.evidence is not None and args.stop_after == "refine":
        parser.error("cached evidence is already refined; --stop-after refine is unsupported")
    if args.recovery is None and args.stop_after in {"recover", "recovery_review"}:
        parser.error("--stop-after recover/recovery_review requires --recovery")
    if (args.continuation is None) != (args.adjacent_source is None):
        parser.error("--continuation and --adjacent-source must be supplied together")
    if args.continuation is None and args.stop_after is not None and args.stop_after.startswith("continuation_"):
        parser.error("continuation stop stages require --continuation and --adjacent-source")
    if (args.inline is None) != (args.inline_source is None):
        parser.error("--inline and --inline-source must be supplied together")
    if args.inline is None and args.stop_after is not None and args.stop_after.startswith("inline_"):
        parser.error("inline stop stages require --inline and --inline-source")
    try:
        result = execute(args.source, args.context, args.review, args.workdir, use_ocr=args.ocr,
            max_items=args.max_items, stop_after=args.stop_after, evidence_path=args.evidence,
            recovery_path=args.recovery, continuation_path=args.continuation,
            adjacent_source_path=args.adjacent_source, inline_path=args.inline, inline_source_path=args.inline_source)
    except PipelineCLIError as exc:
        result = dict(schema_version="b-pipeline-cli-result-trial/0.1", pipeline_state="FAILED",
            mode="CACHED_INPUT" if args.evidence is not None else "LIVE_BATCH", decision="HOLD",
            integrity_accepted=False, business_acceptance=False, transcription_verified=False,
            audit_performed=exc.stage not in {"RUN_FAILED", "SETUP_FAILED"},
            error=dict(stage=exc.stage, type=type(exc.original).__name__, message=str(exc.original)), exit_code=1)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
