"""Run source-bound B CPU recovery probes without any website access."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from annotation.recognition.recovery import recover


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, default=ROOT/"tests/fixtures/book46007447/ocr-evidence.json")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--probe", action="append", help="optional explicit probe ID; repeat to select several")
    args = parser.parse_args()
    try:
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
        artifact = recover(args.source,evidence,args.out,probe_ids=args.probe)
    except (ValueError,OSError,KeyError,ImportError) as exc:
        parser.exit(1, f"Offline recovery failed: {exc}\n")
    print(json.dumps({"artifact_id": artifact["artifact_id"], "probes": len(artifact["payload"]["probes"]),
                      "plans": len(artifact["payload"]["supersession_plan"]), "verification_status": "UNVERIFIED"}))


if __name__ == "__main__":
    main()
