"""Repository CLI for the provisional B-side recognizer."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from annotation.recognition.baseline import recognize, write_result


def main():
    parser = argparse.ArgumentParser(description="Offline B-side recognition; no platform writes")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="new output directory")
    parser.add_argument("--ocr", action="store_true", help="use installed RapidOCR CPU backend")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new directory")
    try:
        result, previews = recognize(args.source, use_ocr=args.ocr)
        write_result(result, previews, args.out)
    except (ValueError, OSError, ImportError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Recognition failed: {exc}\n")
    print(json.dumps({"artifact_id": result["artifact_id"], "content_hash": result["content_hash"],
                      "pages": len(result["payload"]["pages"]),
                      "regions": sum(len(p["regions"]) for p in result["payload"]["pages"]),
                      "quality_decision": result["payload"]["quality_decision"]}))


if __name__ == "__main__":
    main()
