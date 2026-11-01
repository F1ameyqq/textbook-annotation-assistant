"""Portable B offline experiment. Never connects to a website."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from annotation.recognition.baseline import recognize, write_result, digest, file_digest
from annotation.recognition.offline import refine, assemble, quality_check, draw_graph, scalar_issues


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def compare_reference(path, review):
    """Only explicitly reviewed record bindings; tixu is never a platform ID."""
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    comparisons = []
    for case in review.get("answer_checks", []):
        binding = case.get("reference_export")
        if not binding:
            continue
        if file_digest(path) != binding["file_sha256"]:
            raise ValueError("reference export hash mismatch")
        matched = [r for r in records if digest(r) == binding["record_content_hash"]]
        if len(matched) != 1:
            raise ValueError("reviewed export record binding is missing or ambiguous")
        value = matched[0]["answer"]
        comparisons.append({"case_id": case["case_id"], "source_binding": case["asset_sha256"],
                            "record_content_hash": binding["record_content_hash"],
                            "expected_scalar": case["expected_scalar"], "observed_answer": value,
                            "issues": scalar_issues(value, case["expected_scalar"]),
                            "reference_quality": "UNVERIFIED_HISTORY"})
    return {"decision": "HOLD", "records": len(records), "reviewed_bindings": len(comparisons),
            "unmapped_records": len(records)-len(comparisons), "comparisons": comparisons,
            "note": "Unmapped records are not missing questions; no global tixu/platform-order mapping."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, help="optional baseline OCR cache; validated against source bytes")
    parser.add_argument("--reference-export", type=Path, help="optional historical JSONL, diagnostics only")
    parser.add_argument("--out", type=Path, required=True, help="new run directory")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new directory")
    try:
        context, review = read(args.context), read(args.review)
        baseline = read(args.evidence) if args.evidence else recognize(args.source, use_ocr=True)[0]
        evidence = refine(args.source, baseline, context)
        graph = assemble(evidence)
        report = quality_check(evidence, graph, review)
        comparison = compare_reference(args.reference_export, review) if args.reference_export else None
        previews = draw_graph(args.source, graph)
        write_result(evidence, previews, args.out)
        for name, value in (("question-graph.json", graph), ("check-report.json", report),
                            ("baseline-evidence.json", baseline), ("reference-comparison.json", comparison)):
            if value is not None:
                (args.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    except (ValueError, OSError, ImportError, KeyError) as exc:
        parser.exit(1, f"Offline run failed: {exc}\n")
    print(json.dumps({"decision": report["payload"]["decision"], **report["payload"]["summary"],
                      "page_census_matches": sum(p["census_matches"] for p in report["payload"]["page_coverage"]),
                      "reference_export": comparison}, ensure_ascii=False))


if __name__ == "__main__":
    main()
