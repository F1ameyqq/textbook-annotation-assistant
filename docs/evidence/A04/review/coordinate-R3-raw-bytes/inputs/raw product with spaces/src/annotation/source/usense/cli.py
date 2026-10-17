"""Task-local entry point, without modifying parent or installed entry points."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil

from annotation.contracts import load_bundle, validate_bundle, write_bundle
from annotation.delivery.usense_readonly import build_snapshot, snapshot_evidence
from annotation.delivery.usense_readonly.coordinates import DEPENDENCY_COMMIT
from annotation.runtime.browser.guard import BrowserSafetyError
from . import SourceParseError, build_source, parse_capture, source_evidence
from .collector import collect_live, save_json, sanitized_capture


def build_exchange(capture, root, *, as_of=None):
    root = Path(root)
    parsed = parse_capture(capture, root, now=as_of)
    source = build_source(parsed, root)
    snapshot = build_snapshot(parsed, source, root)
    repository = next(p for p in Path(__file__).resolve().parents if (p / "AGENTS.md").is_file())
    policy = json.loads((repository / "config/policies/usense-v1-proposal.json").read_text(encoding="utf-8-sig"))
    bundle = validate_bundle({"format_version":"c01-exchange-1", "policies":[policy],
        "evidence":[source_evidence(parsed, root), snapshot_evidence(parsed, source, root)],
        "artifacts":[source.model_dump(mode="json"),snapshot.model_dump(mode="json")]}, asset_root=root)
    write_bundle(bundle, root / "bundle.json")
    load_bundle(root / "bundle.json")
    return bundle


def main(argv=None):
    parser = argparse.ArgumentParser(description="A04 bounded, headless read-only Usense adapter")
    commands = parser.add_subparsers(dest="command", required=True)
    live = commands.add_parser("live", help="Acquire only authorized book46007447 pages14,15,173")
    live.add_argument("--login-root", type=Path, required=True, help="Existing repository with authorized login helper/profile")
    live.add_argument("--output", type=Path, required=True, help="New evidence package directory")
    live.add_argument("--coordination-state", type=Path, required=True, help="Current coordinator-owned state, read only")
    live.add_argument("--ignore-https-errors", action="store_true", help="Explicit per-run authorized opt-in only")
    replay = commands.add_parser("offline", help="Copy and consume a fixed package without network")
    replay.add_argument("--input", type=Path, required=True, help="Package root containing capture.json and assets")
    replay.add_argument("--output", type=Path, required=True, help="New portable output package")
    replay.add_argument("--as-of", help="Explicit historical replay timestamp; never a current platform check")
    args = parser.parse_args(argv)
    try:
        if args.command == "live":
            state = json.loads(args.coordination_state.read_text(encoding="utf-8-sig"))
            reservation = state.get("platform_session", {})
            if (reservation.get("book_id") != "46007447" or reservation.get("reservation_task") != "A04"
                    or reservation.get("reservation_stage") not in ("execution", "review")):
                raise BrowserSafetyError("PROFILE_IN_USE", "preflight")
            capture = collect_live(args.output, args.login_root, ignore_https_errors=args.ignore_https_errors)
            bundle = build_exchange(capture, args.output)
        else:
            if args.output.exists():
                raise BrowserSafetyError("OUTPUT_EXISTS", "prepare")
            capture = json.loads((args.input / "capture.json").read_text(encoding="utf-8-sig"))
            # Validate before copying, including resource traversal and secrets.
            as_of = datetime.fromisoformat(args.as_of.replace("Z", "+00:00")) if args.as_of else None
            parsed = parse_capture(capture, args.input, now=as_of)
            capture = sanitized_capture(capture)
            args.output.mkdir(parents=True)
            for asset in parsed.pages:
                target = args.output / asset["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(args.input / asset["path"], target)
            if args.as_of and capture.get("evidence_mode") == "OBSERVED":
                capture["provenance"] = "HISTORICAL"
            save_json(args.output / "capture.json", capture)
            bundle = build_exchange(capture, args.output, as_of=as_of)
        save_json(args.output / "evidence/entry-result.json", {"command":args.command,
            "artifact_count":len(bundle.artifacts), "network_used":args.command == "live",
            "geometry_dependency_status":"ACCEPTED", "geometry_dependency_commit":DEPENDENCY_COMMIT,
            "geometry_status":"NOT_PERFORMED_BY_SOURCE", "acceptance":"NOT_ASSERTED"})
        print("A04_PACKAGE_CREATED; GEOMETRY_DEPENDENCY_ACCEPTED; GEOMETRY_NOT_PERFORMED; ACCEPTANCE_NOT_ASSERTED")
        return 0
    except Exception as exc:
        # Never allow raw browser, credential, request or input exception text.
        code = getattr(exc, "code", "A04_FAILED")
        if not isinstance(code, str) or not code.replace("_", "").isalnum() or len(code) > 64:
            code = "A04_FAILED"
        location = "; LOCATION=" + exc.path if isinstance(exc, SourceParseError) and code == "RESOURCE_INVALID" else ""
        print("A04_FAILED:" + code + location)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
