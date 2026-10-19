"""Local CLI; there is deliberately no production sending switch or force bypass."""
import argparse
import json
from pathlib import Path

from annotation.contracts.integrity import read_json
from annotation.delivery.live_pilot.plan import create_live_plan
from annotation.delivery.live_pilot.usense import UsenseTransport
from annotation.quality.live_pilot import check_input
from annotation.runtime.live_pilot.journal import Journal


def main(argv=None):
    parser = argparse.ArgumentParser(description="A11 limited core; real wire/readback are BLOCKED")
    parser.add_argument("command", choices=("inspect-input", "prepare", "apply", "reconcile-readonly", "report"))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--asset-root", type=Path)
    parser.add_argument("--offline-fixture", action="store_true", help="local validation/plan only; cannot send")
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command in ("apply", "reconcile-readonly"):
            result = {"status": "BLOCKED", "reason": "LIVE_TRANSPORT_NOT_IMPLEMENTED",
                      "missing": UsenseTransport.missing, "platform_calls": 0, "submission_status": "NOT_SUBMITTED"}
        elif args.command == "report":
            result = Journal(args.journal, offline=args.offline_fixture).report()
        else:
            if args.input is None:
                parser.error("--input is required")
            request = read_json(args.input)
            admission = check_input(request, args.asset_root or args.input.parent, offline=args.offline_fixture)
            result = {"status": "OFFLINE_VALID" if args.offline_fixture else "BLOCKED",
                      "input_hash": admission.input_hash, "production_ready": False,
                      "submission_status": "NOT_SUBMITTED"}
            if args.command == "prepare":
                result["plans"] = [create_live_plan(admission, request, q["question_id"], request["observation"])
                                   for q in admission.questions[:1]]
                result["note"] = "first question preview only; successors require fresh post-save baseline"
    except Exception as exc:
        result = {"status": "BLOCKED", "reason": getattr(exc, "code", type(exc).__name__),
                  "detail": str(exc), "production_ready": False, "submission_status": "NOT_SUBMITTED"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result.get("status") == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
