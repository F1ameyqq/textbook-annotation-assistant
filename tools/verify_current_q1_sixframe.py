#!/usr/bin/env python3
"""Independently verify the frozen Q1 six-frame delivery."""

import hashlib
import json
from pathlib import Path
import sys


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_q1_sixframe.py OUTPUT_DIR")
    root = Path(sys.argv[1]).resolve()
    manifest = load(root / "manifest.json")
    assert manifest["status"] == "OFFLINE_SIMULATION_ONLY"
    assert manifest["file_count_excluding_manifest"] == len(manifest["files"])
    for item in manifest["files"]:
        path = root / item["path"]
        assert path.is_file(), item["path"]
        assert path.stat().st_size == item["bytes"], item["path"]
        assert sha(path) == item["sha256"], item["path"]

    obj = load(root / "q1-sixframe-object.json")
    plan = load(root / "q1-offline-plan.json")
    receipt = load(root / "q1-simulated-receipt.json")
    invocation = load(root / "native-consumer-invocation.json")
    assert obj["status"] == plan["status"] == receipt["status"] == "OFFLINE_SIMULATION_ONLY"
    assert [f["platform_role"] for f in obj["frames"]] == ["Q", "W", "W", "W", "W", "A"]
    assert obj["binding"]["printed_parentheses"]["contained_by_Q"] is True
    assert obj["binding"]["printed_parentheses"]["intersects_any_W"] is False
    assert obj["current_content"]["sha256"] == "2384a8386e8946b5842dfa5d9ce099857e7795f9397335bd6434da1f2f4aab1f"
    assert obj["platform_gate"]["platform_use_allowed"] is False
    assert plan["consumer"] == invocation["existing_consumer_called"] == "annotation.delivery.q1_offline"
    assert invocation["exit_code"] == receipt["consumer_exit_code"] == 0
    assert receipt["native_simulated_result"] == "APPLIED"
    assert receipt["native_effect_match"] == "MATCH"
    assert receipt["platform_calls"] == 0 and receipt["platform_write"] is False
    native = root / "native-c01-run"
    before = load(native / "assets/before.json")
    after = load(native / "assets/readback.json")
    # Compare actual separately read target values, rather than trusting the
    # receipt's PASS/MATCH labels or the wrapper's declarative booleans.
    assert before["view"]["target"]["questions"] == []
    assert before["view"]["target"]["frames"] == []
    assert after["read_sequence"] > before["read_sequence"]
    assert before["instance_id"] == after["instance_id"]
    assert before["view"]["target"]["directories"] == after["view"]["target"]["directories"]
    assert len(after["view"]["target"]["questions"]) == 1
    assert len(after["view"]["target"]["frames"]) == 6
    actual = [after["view"]["frame_projections"][f["platform_frame_id"]]
              for f in after["view"]["target"]["frames"]]
    expected = [{
        "box": {"image": f["asset"], "bbox": f["bbox_xyxy_original_pixels"]},
        "fragment_id": f["fragment_id"], "region_id": f["region_id"],
        "platform_role": f["platform_role"], "platform_type": f["platform_type"],
    } for f in obj["frames"]]
    assert actual == expected
    exchange = load(native / "exchange.json")
    native_plan = next(a for a in exchange["artifacts"] if a["kind"] == "ApplyPlan")
    assert json.loads(native_plan["payload"]["actions"][0]["expected_after"]["frames"]) == actual
    native_receipt = load(native / "receipt.json")
    readback = native_receipt["payload"]["results"][0]["readback"]
    assert sha(native / readback["path"]) == readback["sha256"]
    assert native_receipt["content_hash"] == receipt["native_receipt_ref"]["content_hash"]
    p = obj["binding"]["printed_parentheses"]["bbox_xyxy_original_pixels"]
    q = obj["frames"][0]["bbox_xyxy_original_pixels"]
    assert q[0] <= p[0] < p[2] <= q[2] and q[1] <= p[1] < p[3] <= q[3]
    for f in obj["frames"][1:5]:
        w = f["bbox_xyxy_original_pixels"]
        assert not (max(w[0], p[0]) < min(w[2], p[2]) and max(w[1], p[1]) < min(w[3], p[3]))
    assert load(root / "native-c01-run" / "replay-rejection.json")["code"] == "PLAN_REPLAY"
    assert load(root / "native-c01-run" / "replay-rejection.json")["zero_target_change"] is True
    print(json.dumps({
        "result": "PASS",
        "manifest_sha256": sha(root / "manifest.json"),
        "verified_files": len(manifest["files"]),
        "roles": [f["platform_role"] for f in obj["frames"]],
        "platform_use_allowed": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
