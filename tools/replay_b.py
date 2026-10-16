"""Replay committed development OCR evidence without original images or OCR."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from annotation.recognition.offline import assemble, quality_check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=ROOT / "tests/fixtures/book46007447")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new directory")
    evidence = json.loads((args.fixture/"ocr-evidence.json").read_text(encoding="utf-8"))
    review = json.loads((args.fixture/"review.json").read_text(encoding="utf-8"))
    graph = assemble(evidence)
    report = quality_check(evidence, graph, review)
    args.out.mkdir(parents=True)
    for name, value in (("question-graph.json",graph),("check-report.json",report)):
        (args.out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"decision":report["payload"]["decision"], **report["payload"]["summary"]}))


if __name__ == "__main__":
    main()
