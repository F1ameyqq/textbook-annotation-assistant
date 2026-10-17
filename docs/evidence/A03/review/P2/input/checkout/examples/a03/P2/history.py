"""Create a portable old-version UNKNOWN archive through the public A02 mock.

This is deliberately legacy history, not a new local durable A03 intent. Its
original output bytes remain immutable and must never become recoverable by
changing its version or by inventing a historical intent.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def generate(root, output, book, scope):
    from annotation.contracts import artifact_ref, write_bundle
    from annotation.delivery.mock import MockSession
    root, output = Path(root).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("a03_p2_legacy_helpers",
                                                root / "examples/a02/R1/scenarios.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    inputs, config = helper.own_input(root, output, book, "p2-history-" + book + "-" + scope,
                                      scope=scope)
    bundle, plan, snapshot = helper.prepare(inputs, config, output, "p2-history-" + scope)
    session = MockSession()
    session.register_target(inputs, artifact_ref(snapshot), asset_root=output)
    executed = session.execute(bundle, artifact_ref(plan), config, asset_root=output,
                               receipt_id="legacy-history-receipt-" + scope,
                               created_at="2026-10-17T00:00:00Z",
                               faults={plan.payload.actions[0].action_id: "lost_response"})
    history = output / "history.json"
    write_bundle(executed, history)
    receipt = next(a for a in executed.artifacts if a.kind == "ExecutionReceipt")
    if not any(item.outcome == "UNKNOWN" for item in receipt.payload.results):
        raise AssertionError("legacy fixture must actually produce UNKNOWN")
    result = {"archive_path": str(history), "archive_sha256": hashlib.sha256(history.read_bytes()).hexdigest(),
              "target_key": {"platform_namespace": "a03-mock", "target_id": config.target_id,
                             "book_id": config.book_id}, "scope_id": config.scope_id,
              "receipt_ref": artifact_ref(receipt), "classification": "LEGACY_UNRECORDED"}
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, sort_keys=True), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--book", required=True)
    parser.add_argument("--scope", required=True)
    args = parser.parse_args()
    generate(args.root, args.output, args.book, args.scope)
