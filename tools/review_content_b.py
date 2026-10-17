"""Open a loopback-only source/content review workspace; no website or model calls."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from prepare_content_revision_b import _read, local_path


def port_number(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("port must be 0..65535") from None
    if not 0 <= number <= 65535:
        raise argparse.ArgumentTypeError("port must be 0..65535")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("evidence", "graph", "base-check", "review", "plan", "workdir"):
        parser.add_argument("--" + name, required=True, type=local_path)
    parser.add_argument("--source", required=True, action="append", type=local_path, help="original source manifests; repeat to cover current E scope")
    parser.add_argument("--port", type=port_number, default=0, help="local port, 0 chooses an available port")
    parser.add_argument("--check-only", action="store_true", help="prepare/check persistent workspace without starting HTTP")
    parser.add_argument("--region-catalog", type=local_path, help="optional source-bound region draft/crop manifest for formula choices")
    args = parser.parse_args(argv)
    try:
        from annotation.recognition.content_review import ReviewWorkspace
        from annotation.recognition.content_review_server import make_server
        values = [_read(getattr(args, key))[0] for key in ("evidence", "graph", "base_check", "review", "plan")]
        catalog = None
        if args.region_catalog is not None:
            from annotation.recognition.region_review import load_region_catalog
            catalog = load_region_catalog(args.region_catalog)
        workspace = ReviewWorkspace(*values, args.workdir, args.source, region_catalog=catalog)
        state = workspace.state()
        result = {"schema_version": "b-content-review-cli-trial/0.1", "ready": True,
            "head": state["head"], "plan_revision": state["plan_revision"], "counts": state["counts"],
            "decision": "HOLD", "complete": False, "transcription_verified": False,
            "business_acceptance": False, "platform_actions": [], "new_model_calls": 0}
        if args.check_only:
            print(json.dumps(result, ensure_ascii=False), flush=True)
            return 0
        server = make_server(workspace, port=args.port)
        result.update(url="http://127.0.0.1:" + str(server.server_address[1]), pid=os.getpid())
        print(json.dumps(result, ensure_ascii=False), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    except Exception as exc:
        print(json.dumps({"schema_version": "b-content-review-cli-trial/0.1", "ready": False,
            "error": {"type": type(exc).__name__, "message": str(exc)[:800]}, "decision": "HOLD",
            "complete": False, "transcription_verified": False, "business_acceptance": False,
            "platform_actions": [], "new_model_calls": 0}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
