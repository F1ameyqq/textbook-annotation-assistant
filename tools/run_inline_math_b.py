"""Prepare explicit whole-row OCR, collect formulas, or replay local evidence.

Only --collect-ocr and --collect-formula enable their respective local models.
Default replay requires saved observations and the actual formula journal.
Integrity acceptance always leaves transcription and business results HOLD.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))


def local_path(value):
    value = str(value)
    if (value.startswith(("\\\\", "//")) or "://" in value
            or ".." in PurePosixPath(value).parts or ".." in PureWindowsPath(value).parts
            or (re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value) and not re.match(r"^[A-Za-z]:[\\/]", value))):
        raise argparse.ArgumentTypeError("an explicit local path without network URLs or parent traversal is required")
    return Path(value)


def positive_int(value):
    try: result = int(value)
    except (ValueError, TypeError): raise argparse.ArgumentTypeError("--max-items must be a positive integer") from None
    if result < 1: raise argparse.ArgumentTypeError("--max-items must be a positive integer")
    return result


def reference(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def _load(path):
    def invalid(value): raise ValueError("nonfinite JSON constant: "+value)
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=invalid)


def _checked_artifact(value):
    from annotation.recognition.baseline import digest
    if (not isinstance(value, dict) or not isinstance(value.get("payload"), dict)
            or not isinstance(value.get("artifact_id"), str) or not value["artifact_id"]
            or type(value.get("revision")) is not int or value["revision"] < 1
            or not re.fullmatch(r"[0-9a-f]{64}", str(value.get("content_hash", "")))
            or value["content_hash"] != digest(value["payload"])):
        raise ValueError("artifact identity or payload hash mismatch")
    return value


def load_evidence(path):
    """Unwrap only documented evidence containers, checking every layer.

    Hash verification does not replace the original pipeline SQL/package audit.
    The complete input container is persisted alongside the extracted evidence.
    """
    container = value = _load(path)
    layers = []
    for _ in range(5):
        _checked_artifact(value)
        schema, kind = value.get("schema_version"), value.get("kind")
        layers.append({"schema_version": schema, "kind": kind, "artifact_ref": reference(value)})
        if schema in {"b-evidence-trial/0.2", "b-evidence-trial/0.3"} and kind == "EvidenceBundleTrial":
            return value, container, layers
        if schema == "b-pipeline-stage-trial/0.1" and kind == "PipelineStageTrial":
            stage = value["payload"].get("stage_id")
            if stage not in {"evidence", "refine", "recover", "continuation_prepare"}:
                raise ValueError("pipeline wrapper is not an evidence-producing stage")
            child = value["payload"]["result"]
            expected = "ContinuationScopeTrial" if stage == "continuation_prepare" else "EvidenceBundleTrial"
            if not isinstance(child, dict) or child.get("book_id") != value.get("book_id") or child.get("kind") != expected:
                raise ValueError("pipeline evidence wrapper child identity or kind mismatch")
            value = child
        elif schema == "b-continuation-scope-trial/0.1" and kind == "ContinuationScopeTrial":
            child = value["payload"]["evidence"]
            if (child.get("book_id"), child.get("scope_id")) != (value.get("book_id"), value.get("scope_id")):
                raise ValueError("continuation evidence scope differs from its container")
            value = child
        else:
            raise ValueError("unsupported evidence container")
    raise ValueError("evidence container nesting exceeds the supported depth")


def _options(*, collect_ocr, ocr_path, prepare_only, collect_formula, models, max_items,
             formula_workdir, formula_path, report_path, ocr_collector=None, formula_collector=None):
    if collect_ocr == (ocr_path is not None):
        raise ValueError("choose exactly one of --collect-ocr and --ocr-observations")
    if ocr_collector is not None and not collect_ocr:
        raise ValueError("an OCR collector requires explicit --collect-ocr")
    formula_options = collect_formula or any(x is not None for x in (models, max_items, formula_workdir, formula_path, report_path, formula_collector))
    if prepare_only:
        if formula_options: raise ValueError("--prepare-only cannot consume formula arguments")
        return
    if collect_formula:
        if models is None: raise ValueError("--collect-formula requires explicit --models")
        if formula_path is not None or report_path is not None:
            raise ValueError("formula collection cannot consume cached formula observations or reports")
    else:
        if models is not None or max_items is not None or formula_collector is not None:
            raise ValueError("model, budget and collector inputs require --collect-formula")
        if formula_path is None or report_path is None or formula_workdir is None:
            raise ValueError("cached replay requires --formula-observations, --formula-report and --formula-workdir")
        if collect_ocr:
            raise ValueError("cached formula replay requires the bound cached --ocr-observations")
    if max_items is not None and (type(max_items) is not int or max_items < 1):
        raise ValueError("--max-items must be a positive integer")


def _output_root(path):
    path = Path(path)
    if path.exists() and not path.is_dir(): raise ValueError("output workdir is not a directory")
    if not (path/"objects").resolve().is_relative_to(path.resolve()):
        raise ValueError("immutable objects directory escapes its explicit workdir")
    return path


def _audit(check, schema, inputs):
    _checked_artifact(check)
    p = check["payload"]
    if (check.get("schema_version") != schema or check.get("input_refs") != inputs or type(p.get("accepted")) is not bool
            or p.get("decision") != "HOLD" or p.get("business_acceptance") is not False
            or p.get("transcription_verified") is not False or p.get("complete") is not False
            or p.get("graph_modified") is not False or p.get("platform_actions") != []):
        raise ValueError("independent audit binding or HOLD status is invalid")
    return p["accepted"]


def execute(evidence_path, source_path, asset_id, rows_path, workdir, *, collect_ocr=False,
            ocr_observations_path=None, prepare_only=False, collect_formula=False, model_dir=None,
            max_items=None, formula_workdir=None, formula_observations_path=None, formula_report_path=None,
            ocr_collector=None, formula_collector=None, ocr_auditor=None, formula_auditor=None):
    """Return a persisted HOLD summary; injected collection must be synthetic."""
    _options(collect_ocr=collect_ocr, ocr_path=ocr_observations_path, prepare_only=prepare_only,
        collect_formula=collect_formula, models=model_dir, max_items=max_items, formula_workdir=formula_workdir,
        formula_path=formula_observations_path, report_path=formula_report_path,
        ocr_collector=ocr_collector, formula_collector=formula_collector)
    from annotation.recognition import batch
    from annotation.recognition.baseline import code_digest, digest, file_digest
    from annotation.recognition.inline_ocr import plan_inline_rows
    from annotation.recognition.inline_math import build_inline_math_layout

    paths = {"evidence": Path(local_path(evidence_path)), "source": Path(local_path(source_path)), "rows": Path(local_path(rows_path))}
    for name, path in (("ocr_observations", ocr_observations_path), ("formula_observations", formula_observations_path), ("formula_report", formula_report_path)):
        if path is not None: paths[name] = Path(local_path(path))
    workdir = _output_root(local_path(workdir))
    journal = _output_root(local_path(formula_workdir)) if formula_workdir is not None else _output_root(workdir/"formula")
    if model_dir is not None:
        model_dir = Path(local_path(model_dir))
        if not model_dir.is_dir(): raise ValueError("--models must name an existing local model directory")
    for path in paths.values():
        if not path.is_file(): raise ValueError("required local input file is missing: "+str(path))
    if not prepare_only and not collect_formula and not (journal/"inline-formula.sqlite3").is_file():
        raise ValueError("cached replay requires the actual existing formula journal")
    if not prepare_only and not collect_formula and workdir.resolve().is_relative_to(journal.resolve()):
        raise ValueError("replay output must stay outside the read-only formula journal")
    evidence, container, layers = load_evidence(paths["evidence"])
    line_ids = _load(paths["rows"])
    # This pure source planner checks explicit row identity and pixels before
    # either a default model backend or a test seam can be invoked.
    plan_inline_rows(evidence, paths["source"], asset_id=asset_id, line_ids=line_ids)
    receipts = {name: {"file_sha256": file_digest(path), "filename": path.name} for name, path in paths.items()}
    receipts["evidence"]["unwrapped_layers"] = layers
    artifacts = {name: None for name in ("evidence_container", "evidence", "ocr_observations", "ocr_check", "math_layout",
                                          "formula_observations", "formula_report", "formula_candidates", "formula_check")}
    workdir.mkdir(parents=True, exist_ok=True)
    def save(name, value):
        _output_root(workdir)
        artifacts[name] = batch._put_object(workdir, value)
    save("evidence_container", container)
    save("evidence", evidence)
    if collect_ocr:
        injected = ocr_collector is not None
        if ocr_collector is None:
            from annotation.recognition.inline_ocr import collect_inline_observations
            ocr_collector = collect_inline_observations
        ordinary = ocr_collector(evidence, paths["source"], asset_id=asset_id, line_ids=line_ids)
        if injected and ordinary.get("producer", {}).get("execution_kind") != "SYNTHETIC_TEST":
            raise ValueError("an injected OCR collector must remain SYNTHETIC_TEST")
    else: ordinary = _load(paths["ocr_observations"])
    if ocr_auditor is not None and ordinary.get("producer", {}).get("execution_kind") != "SYNTHETIC_TEST":
        raise ValueError("an injected auditor is only supported for synthetic test evidence")
    if ocr_auditor is None:
        from annotation.recognition.inline_ocr_quality import audit_inline_ocr
        ocr_auditor = audit_inline_ocr
    ordinary_check = ocr_auditor(evidence, ordinary, paths["source"], line_ids=line_ids)
    accepted = _audit(ordinary_check, "b-inline-ocr-check-trial/0.1", [reference(evidence), reference(ordinary)])
    save("ocr_observations", ordinary)
    save("ocr_check", ordinary_check)
    issues = [{"stage": "OCR", **issue} for issue in ordinary_check["payload"]["issues"]]
    layout = formulas = report = formula_check = None
    state = "FAILED"
    failures = sum(v.get("recognition_error") is not None for row in ordinary.get("payload", {}).get("rows", []) for v in row.get("variants", []))
    if accepted:
        layout = build_inline_math_layout(evidence, ordinary, paths["source"], line_ids=line_ids)
        save("math_layout", layout)
        state = "PREPARED" if not failures else "FAILED"
    if accepted and not failures and not prepare_only:
        if collect_formula:
            injected = formula_collector is not None
            if formula_collector is None:
                from annotation.recognition.inline_formula import collect_inline_formula
                formula_collector = collect_inline_formula
            formulas, report = formula_collector(evidence, layout, paths["source"], journal,
                line_ids=line_ids, model_dir=model_dir, max_items=max_items)
            if injected and any(v.get("producer", {}).get("execution_kind") != "SYNTHETIC_TEST" for v in (formulas, report)):
                raise ValueError("an injected formula collector must remain SYNTHETIC_TEST")
        else:
            formulas, report = _load(paths["formula_observations"]), _load(paths["formula_report"])
        if formula_auditor is not None and formulas.get("producer", {}).get("execution_kind") != "SYNTHETIC_TEST":
            raise ValueError("an injected auditor is only supported for synthetic test evidence")
        from annotation.recognition.inline_candidates import build_inline_candidates
        candidates = build_inline_candidates(formulas)
        if formula_auditor is None:
            from annotation.recognition.inline_formula_quality import audit_inline_formula
            formula_auditor = audit_inline_formula
        formula_check = formula_auditor(evidence, layout, formulas, candidates, paths["source"],
            line_ids=line_ids, workdir=journal, report=report)
        accepted = _audit(formula_check, "b-inline-formula-check-trial/0.1",
            [reference(v) for v in (evidence, layout, formulas, candidates, report)]) and accepted
        for name, value in (("formula_observations", formulas), ("formula_report", report),
                            ("formula_candidates", candidates), ("formula_check", formula_check)): save(name, value)
        issues.extend({"stage": "FORMULA", **issue} for issue in formula_check["payload"]["issues"])
        state = report["payload"]["state"]
        if state not in {"READY", "PARTIAL", "FAILED"}: raise ValueError("unsupported formula execution state")
    changed = []
    for name, path in paths.items():
        if not path.is_file() or file_digest(path) != receipts[name]["file_sha256"]: changed.append(name)
    if changed:
        accepted = False
        issues.append({"stage": "INPUT", "code": "INPUT_CHANGED_DURING_EXECUTION", "inputs": changed})
    if not accepted: state = "FAILED"
    payload = {"schema_version": "b-inline-math-cli-result-trial/0.1", "execution_state": state,
        "mode": "PREPARE_ONLY" if prepare_only else "EXPLICIT_FORMULA_COLLECTION" if collect_formula else "CACHED_FORMULA_REPLAY",
        "ocr_mode": "EXPLICIT_COLLECTION" if collect_ocr else "CACHED_INPUT", "asset_id": asset_id, "line_ids": line_ids,
        "execution_kind": {"ocr": ordinary.get("producer", {}).get("execution_kind"),
                           "formula": formulas.get("producer", {}).get("execution_kind") if formulas else None},
        "integrity_accepted": accepted, "audit_performed": True, "decision": "HOLD", "complete": False,
        "transcription_verified": False, "business_acceptance": False, "graph_modified": False,
        "entire_answer_reconstructed": False, "expected_text_consumed": False, "paid_model_calls": 0,
        "website_requests": 0, "platform_actions": [], "input_receipts": receipts, "artifacts": artifacts,
        "counts": {"rows": len(line_ids), "ordinary_recognition_failures": failures,
                   "layout": layout["payload"]["counts"] if layout else None,
                   "formula": report["payload"]["counts"] if report else None}, "issues": issues,
        "limitations": ["Evidence-container hashes do not replace the original pipeline execution/package audit.",
                        "Character boxes and formula ROIs are estimates; content accuracy and completeness remain unverified."],
        "exit_code": 0 if accepted and state != "FAILED" else 1}
    producer = {"module": "run_inline_math_b", "code_sha256": code_digest(Path(__file__))}
    result = {"schema_version": "b-inline-math-cli-receipt-trial/0.1", "kind": "InlineMathCLIReceiptTrial", "revision": 1,
              "book_id": evidence["book_id"], "scope_id": evidence["scope_id"], "input_refs": [reference(evidence)],
              "producer": producer, "payload": payload, "content_hash": digest(payload)}
    result["artifact_id"] = "inline-cli-result-"+digest(result)[:24]
    return {**payload, "result": batch._put_object(workdir, result)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("evidence", "source", "rows", "workdir"):
        parser.add_argument("--"+name, type=local_path, required=True)
    parser.add_argument("--asset-id", required=True)
    ordinary = parser.add_mutually_exclusive_group(required=True)
    ordinary.add_argument("--collect-ocr", action="store_true")
    ordinary.add_argument("--ocr-observations", type=local_path)
    parser.add_argument("--prepare-only", action="store_true")
    formula = parser.add_mutually_exclusive_group()
    formula.add_argument("--collect-formula", action="store_true")
    formula.add_argument("--formula-observations", type=local_path)
    parser.add_argument("--formula-report", type=local_path)
    parser.add_argument("--formula-workdir", type=local_path)
    parser.add_argument("--models", type=local_path)
    parser.add_argument("--max-items", type=positive_int)
    args = parser.parse_args(argv)
    try:
        _options(collect_ocr=args.collect_ocr, ocr_path=args.ocr_observations, prepare_only=args.prepare_only,
            collect_formula=args.collect_formula, models=args.models, max_items=args.max_items,
            formula_workdir=args.formula_workdir, formula_path=args.formula_observations, report_path=args.formula_report)
    except ValueError as exc: parser.error(str(exc))
    try:
        result = execute(args.evidence, args.source, args.asset_id, args.rows, args.workdir,
            collect_ocr=args.collect_ocr, ocr_observations_path=args.ocr_observations, prepare_only=args.prepare_only,
            collect_formula=args.collect_formula, model_dir=args.models, max_items=args.max_items,
            formula_workdir=args.formula_workdir, formula_observations_path=args.formula_observations,
            formula_report_path=args.formula_report)
    except (OSError, ValueError, KeyError, TypeError, ImportError, AttributeError, IndexError, StopIteration, RuntimeError, OverflowError) as exc:
        result = {"schema_version": "b-inline-math-cli-result-trial/0.1", "execution_state": "FAILED", "integrity_accepted": False,
            "audit_performed": False, "decision": "HOLD", "complete": False, "transcription_verified": False,
            "business_acceptance": False, "graph_modified": False, "platform_actions": [],
            "error": {"type": type(exc).__name__, "message": str(exc)}, "exit_code": 1}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
