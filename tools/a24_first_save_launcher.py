"""A24 R1 owner CLI. Inspect is inert; run requires a new exact hashed authority."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def raw_candidate_check(candidate_path, expected_sha):
    """stdlib-only bootstrap: verify raw code before importing annotation code."""
    raw = candidate_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError("CANDIDATE_DIGEST")
    candidate = json.loads(raw)
    required = {"tools/a24_first_save_launcher.py", "src/annotation/runtime/live_pilot/authority.py",
                "src/annotation/quality/live_pilot.py", "src/annotation/runtime/storage/common.py",
                "src/annotation/contracts/integrity.py"}
    if not required.issubset({v["path"] for v in candidate["dependencies"]}):
        raise ValueError("CANDIDATE_BOOTSTRAP_CLOSURE")
    for item in candidate["dependencies"]:
        target = (ROOT / item["path"]).resolve()
        if ROOT not in target.parents:
            raise ValueError("CANDIDATE_PATH")
        data = target.read_bytes()
        if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError("CANDIDATE_DEPENDENCY")
    return candidate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "run"))
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--candidate-sha256")
    parser.add_argument("--authority", type=Path)
    parser.add_argument("--authority-sha256")
    parser.add_argument("--_stage", choices=("product", "worker", "occupancy"), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.command == "inspect":
        if args.candidate is None or args.candidate_sha256 is None:
            parser.error("inspect requires --candidate and --candidate-sha256")
        candidate = raw_candidate_check(args.candidate, args.candidate_sha256)
        print(json.dumps({"mode": "OFFLINE_INSPECT", "dependencies": len(candidate["dependencies"]),
                          "verified": True, "resources_created": False, "activated": False}))
        return 0
    if args.authority is None or args.authority_sha256 is None:
        parser.error("run requires --authority and --authority-sha256")
    authority_raw = args.authority.read_bytes()
    if hashlib.sha256(authority_raw).hexdigest() != args.authority_sha256:
        raise ValueError("AUTHORITY_DIGEST")
    untrusted = json.loads(authority_raw)
    candidate_ref = untrusted["refs"]["candidate"]
    raw_candidate_check(Path(candidate_ref["path"]), candidate_ref["sha256"])
    from annotation.runtime.live_pilot.authority import verify_authority
    authority = verify_authority(args.authority, args.authority_sha256, ROOT)
    from annotation.runtime.live_pilot.owner import run_stage
    return run_stage(authority, args.authority, Path(__file__).resolve(), args._stage or "launcher")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # Detailed controlled failure records are written only by an authorized owner.
        print(json.dumps({"schema": "A24FirstSaveStageResult/v1", "stage": "launcher", "status": "AUTHORITY_OR_OWNER_BLOCKED", "released": False}))
        raise SystemExit(2)
