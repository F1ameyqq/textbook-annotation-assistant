"""Replay source-bound local OCR recovery; no OCR engine or website is called."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from annotation.recognition.offline import artifact, assemble, quality_check, draw_graph
from annotation.recognition.recovery_apply import derive_evidence, derive_review
from annotation.recognition.baseline import load_source, write_result


def replay(fixture):
    def read(name):
        return json.loads((fixture/name).read_text(encoding="utf-8"))
    base, recovery, source_review = (read(n) for n in ("ocr-evidence.json","recovery-evidence.json","source-recovery-review.json"))
    for probe in recovery["payload"]["probes"]:
        crop = fixture/probe["crop_path"]
        if hashlib.sha256(crop.read_bytes()).hexdigest() != probe["crop_sha256"]:
            raise ValueError("recovery crop hash mismatch")
    evidence = derive_evidence(base, recovery, source_review, artifact)
    review = derive_review(read("review.json"), evidence)
    graph = assemble(evidence)
    report = quality_check(evidence, graph, review)
    return evidence, review, graph, report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=ROOT/"tests/fixtures/book46007447")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source", type=Path, help="optional original-image manifest; validate images and render overlays without OCR")
    args=parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new directory")
    evidence, review, graph, report = replay(args.fixture)
    if args.source:
        source, _ = load_source(args.source)
        expected = sorted((p["source"] for p in evidence["payload"]["pages"]), key=lambda a:a["reading_order"])
        if sorted(source["assets"],key=lambda a:a["reading_order"]) != expected:
            parser.error("original-image manifest differs from recovered source descriptors")
        write_result(evidence, draw_graph(args.source,graph), args.out)
    else:
        args.out.mkdir(parents=True)
    for name,value in (("evidence.json",evidence),("recovery-review.json",review),("question-graph.json",graph),("check-report.json",report)):
        (args.out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"decision":report["payload"]["decision"],**report["payload"]["summary"]}))


if __name__=="__main__":
    main()
