"""Report source coverage from fixed B-side 46007447 provenance and ledger files.

This is an evidence summary, not a completeness estimator. Missing or malformed
inputs remain UNKNOWN; no chapter/book denominator is inferred from observed assets.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DESCRIPTOR = ROOT / "tests/fixtures/book46007447/source-descriptor.json"
DEFAULT_EVALUATION = ROOT / "evaluation/book-46007447-pipeline-continuation.json"


def _load(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _display_path(path: Path) -> str:
    """Keep portable repo-relative refs; avoid leaking external absolute paths."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return f"external:{path.name}"


def build_report(descriptor_path: Path, evaluation_path: Path) -> dict[str, Any]:
    descriptor = _load(descriptor_path)
    evaluation = _load(evaluation_path)
    scope = evaluation.get("source_scope") if evaluation else None
    summary = evaluation.get("actual_scope_summary") if evaluation else None
    ledger = evaluation.get("ledger") if evaluation else None

    declared_assets = descriptor.get("assets") if descriptor else None
    base_assets = scope.get("base_assets") if isinstance(scope, dict) else None
    adjacent = scope.get("adjacent_asset") if isinstance(scope, dict) else None
    assets: list[dict[str, Any]] = []
    source_assets = base_assets if isinstance(base_assets, list) else declared_assets
    if isinstance(source_assets, list):
        for item in source_assets:
            if not isinstance(item, dict):
                continue
            refs = item.get("external_refs") or {}
            assets.append({
                "asset_id": item.get("asset_id", "UNKNOWN"),
                "sha256": item.get("sha256", "UNKNOWN"),
                "dimensions": [item.get("width"), item.get("height")],
                "viewer_page": refs.get("viewer_page", "UNKNOWN"),
                "resource_index": refs.get("resource_index", "UNKNOWN"),
                "observed_scope": "FULL_PAGE_DECLARED_OBSERVED" if item.get("sha256") else "UNKNOWN",
                "read_status": "OBSERVED_IN_FIXED_SOURCE_EVIDENCE" if item.get("sha256") else "UNKNOWN",
            })
    if isinstance(adjacent, dict):
        refs = adjacent.get("external_refs") or {}
        assets.append({
            "asset_id": adjacent.get("asset_id", "resource-173"),
            "sha256": adjacent.get("sha256", "UNKNOWN"),
            "dimensions": [adjacent.get("width"), adjacent.get("height")],
            "viewer_page": "UNKNOWN",
            "resource_index": refs.get("resource_index", "UNKNOWN"),
            "observed_scope": "PREFIX_CROP_ONLY",
            "read_status": "PREFIX_OBSERVED_FULL_PAGE_UNREAD",
            "crop_bbox": scope.get("adjacent_crop_bbox", "UNKNOWN"),
        })

    descriptor_by_id = {
        item.get("asset_id"): item for item in declared_assets
        if isinstance(item, dict) and isinstance(item.get("asset_id"), str)
    } if isinstance(declared_assets, list) else {}
    evaluation_by_id = {
        item.get("asset_id"): item for item in base_assets
        if isinstance(item, dict) and isinstance(item.get("asset_id"), str)
    } if isinstance(base_assets, list) else {}
    conflicts: list[str] = []
    if descriptor is None:
        conflicts.append("descriptor unavailable or invalid")
    if evaluation is None or not isinstance(scope, dict):
        conflicts.append("evaluation source_scope unavailable or invalid")
    if descriptor is not None and isinstance(scope, dict):
        if descriptor.get("book_id") != evaluation.get("book_id"):
            conflicts.append("book_id differs between descriptor and evaluation")
        if descriptor.get("scope_id") != scope.get("base_scope_id"):
            conflicts.append("descriptor scope_id differs from evaluation base_scope_id")
        if not isinstance(declared_assets, list) or not isinstance(base_assets, list):
            conflicts.append("base asset inventory missing from one or both sources")
        else:
            if len(declared_assets) != 5 or len(base_assets) != 5:
                conflicts.append("expected five base assets in both source records")
            if set(descriptor_by_id) != set(evaluation_by_id):
                conflicts.append("base asset IDs differ between descriptor and evaluation")
            for asset_id in sorted(set(descriptor_by_id) & set(evaluation_by_id)):
                if descriptor_by_id[asset_id].get("sha256") != evaluation_by_id[asset_id].get("sha256"):
                    conflicts.append(f"SHA-256 differs for base asset {asset_id}")
    base_identity_verified = not conflicts
    if not base_identity_verified:
        for asset in assets:
            asset["observed_scope"] = "UNKNOWN_IDENTITY_CONFLICT"
            asset["read_status"] = "UNKNOWN_IDENTITY_CONFLICT"

    ledger_counts = ledger if base_identity_verified and isinstance(ledger, dict) and all(
        isinstance(ledger.get(key), int) for key in ("CONSUMED", "EXCLUDED", "UNASSIGNED")
    ) else None
    answer_raw_lines = summary.get("answer_raw_lines") if base_identity_verified and isinstance(summary, dict) else None
    ledger_total = sum(ledger_counts.values()) if ledger_counts else None
    return {
        "report_schema": "b-source-coverage-report/1",
        "book_id": descriptor.get("book_id", "UNKNOWN") if base_identity_verified else "UNKNOWN",
        "scope_id": scope.get("extended_scope_id", "UNKNOWN") if base_identity_verified else "UNKNOWN",
        "evidence": {
            "descriptor": _display_path(descriptor_path),
            "evaluation": _display_path(evaluation_path),
            "descriptor_available": descriptor is not None,
            "evaluation_available": evaluation is not None,
            "base_identity_status": "RECORDS_MATCH" if base_identity_verified else "CONFLICT_OR_UNKNOWN",
            "base_identity_conflicts": conflicts,
        },
        "coverage": {
            "expected_chapter_pages": "UNKNOWN",
            "expected_book_pages": "UNKNOWN",
            "chapter_or_book_denominator": "UNKNOWN",
            "declared_observed_full_page_asset_count": len([a for a in assets if a["observed_scope"] == "FULL_PAGE_DECLARED_OBSERVED"]) if assets and base_identity_verified else "UNKNOWN",
            "prefix_only_asset_count": len([a for a in assets if a["observed_scope"] == "PREFIX_CROP_ONLY"]) if assets and base_identity_verified else "UNKNOWN",
            "asset_records": assets if assets else "UNKNOWN",
            "page_mapping_completeness": "UNKNOWN",
        },
        "answer_source_ledger": {
            "status": "KNOWN" if ledger_counts else "UNKNOWN",
            "raw_line_count": answer_raw_lines if isinstance(answer_raw_lines, int) else "UNKNOWN",
            "counts": ledger_counts if ledger_counts else "UNKNOWN",
            "ledger_count_sum": ledger_total if ledger_total is not None else "UNKNOWN",
            "count_reconciles_to_raw_lines": ledger_total == answer_raw_lines if ledger_total is not None and isinstance(answer_raw_lines, int) else "UNKNOWN",
            "unassigned_identity_count": ledger_counts["UNASSIGNED"] if ledger_counts else "UNKNOWN",
            "unassigned_public_identities": "UNKNOWN; rows remain unassigned and lack confirmed question/public IDs",
        },
        "limits": [
            "The six-asset observation set is a development sample, not a chapter or book inventory.",
            "The sixth asset resource-173 is represented by a prefix crop only; its complete page is not observed/read in this evidence set.",
            "No full chapter/book expected-page denominator, table of contents, or complete page-to-question mapping is present.",
            "Ledger CONSUMED means source rows have a graph assignment; it does not establish complete transcription or correctness.",
            "This report compares recorded SHA-256 values across two files; it does not reopen or hash the original image bytes.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--descriptor", type=Path, default=DEFAULT_DESCRIPTOR)
    parser.add_argument("--evaluation", type=Path, default=DEFAULT_EVALUATION)
    parser.add_argument("--out", type=Path, help="write JSON report here; default prints to stdout")
    args = parser.parse_args()
    rendered = json.dumps(build_report(args.descriptor, args.evaluation), ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
