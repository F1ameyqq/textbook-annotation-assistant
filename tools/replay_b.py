"""Replay committed development OCR evidence without original images or OCR."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from annotation.recognition.offline import assemble, quality_check
from annotation.recognition.offline import draw_graph
from annotation.recognition.baseline import load_source, write_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=ROOT / "tests/fixtures/book46007447")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source", type=Path, help="optional original-image manifest; validate bytes and render new overlays without re-running OCR")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new directory")
    evidence = json.loads((args.fixture/"ocr-evidence.json").read_text(encoding="utf-8"))
    review = json.loads((args.fixture/"review.json").read_text(encoding="utf-8"))
    if args.source:
        source, _ = load_source(args.source)
        if (source["book_id"], source["scope_id"]) != (evidence["book_id"], evidence["scope_id"]):
            parser.error("source book/scope does not match OCR snapshot")
        descriptors = sorted(source["assets"], key=lambda a: a["reading_order"])
        cached = sorted([p["source"] for p in evidence["payload"]["pages"]], key=lambda a: a["reading_order"])
        if descriptors != cached:
            parser.error("source asset descriptors do not match OCR snapshot")
    graph = assemble(evidence)
    report = quality_check(evidence, graph, review)
    if args.source:
        write_result(evidence, draw_graph(args.source, graph), args.out)
    else:
        args.out.mkdir(parents=True)
    for name, value in (("question-graph.json",graph),("check-report.json",report)):
        (args.out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"decision":report["payload"]["decision"], **report["payload"]["summary"]}))


if __name__ == "__main__":
    main()
