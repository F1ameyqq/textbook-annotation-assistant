#!/usr/bin/env python3
"""Run the fixed A07 C01 consumer, bind current Q1 content, and freeze overlays.

This tool never contacts or writes the platform.  The native A07 consumer is
executed against its in-memory target, then the current visual transcription is
semantically compared with the six generated C01 frame projections.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

from PIL import Image, ImageDraw, ImageFont


EXPECTED = {
    "a07_archive": "41ebfa94ea9d880d375f8428d054f8da857e7a5587b52d2734ef8a47d6287dbe",
    "current_q1": "2384a8386e8946b5842dfa5d9ce099857e7795f9397335bd6434da1f2f4aab1f",
    "base_zip": "b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d",
    "candidate_zip": "3039645ca69c2604f542c479cb180049604788a3ca28ffac1b5063dee533afac",
    "history": "a763af50c0515f863eeb6dbaf533f4215535591096dd06b81632cec4acbb4493",
    "viewer-10": "eb7cc17e6b58a55a005ce1cdef5bd5058ad258c3dd44dc891b3d830ed3db3626",
    "viewer-173": "a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be",
}

A07_COMMIT = "e37606d74d7e538052c563d02df11c6c961b742f"
B_BASELINE = "fa3a48e872ae6dfe0819b223b484ee5331288a51"
A07_RUN_INPUT = "a07-fixed/docs/evidence/A07/F01/review/normal/run/assets/input/"
MISSING_PLATFORM_FIELDS = [
    "canonical_question_id",
    "current_source_asset_byte_binding",
    "current_canvas_to_original_transform",
    "savepage_mapping",
    "current_platform_frame_readback_target",
]


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def precheck_current(path_value: str) -> dict:
    """Reject a wrong/unwritable current record before creating output or running C01."""
    path = Path(path_value)
    require(path.is_file(), f"missing current Q1 input: {path}")
    require(sha256_file(path) == EXPECTED["current_q1"], "current Q1 input hash mismatch")
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    require(len(lines) == 1, "current Q1 JSONL must contain exactly one record")
    current = json.loads(lines[0])
    require(current["evidence_type"] == "CURRENT_VISUAL_DRAFT", "current input is not visual draft evidence")
    require(current["source_type_meaning"].endswith("NOT_SERVER_RAW"), "current source boundary missing")
    require(current["canonical_question_id"] is None and current["write_allowed"] is False,
            "current input unexpectedly authorizes a platform write")
    require("（" in current["question"] and "）" in current["question"],
            "printed parentheses must remain inside current stem")
    return current


def normalize_stem(text: str) -> str:
    text = re.sub(r"^\s*1\s*[\.．、]\s*", "", text)
    text = re.sub(r"（\s*）", "（）", text)
    return re.sub(r"\s+", "", text)


def intersects(a, b) -> bool:
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def locate_artifact(exchange: dict, kind: str) -> dict:
    hits = [item for item in exchange["artifacts"] if item["kind"] == kind]
    require(len(hits) == 1, f"expected one {kind}, got {len(hits)}")
    return hits[0]


def label_box(draw: ImageDraw.ImageDraw, box, label: str, color, width: int = 4) -> None:
    x1, y1, x2, y2 = [int(v) for v in box]
    draw.rectangle((x1, y1, x2, y2), outline=color, width=width)
    font = ImageFont.load_default()
    lbox = draw.textbbox((0, 0), label, font=font)
    tw, th = lbox[2] - lbox[0], lbox[3] - lbox[1]
    top = max(0, y1 - th - 8)
    draw.rectangle((x1, top, x1 + tw + 8, top + th + 8), fill=color)
    draw.text((x1 + 4, top + 4), label, fill="white", font=font)


def make_overlays(native_run: Path, frames: list[dict], placeholder_box: list[int], out: Path) -> list[Path]:
    overlays = out / "overlays"
    overlays.mkdir(parents=True, exist_ok=False)
    source_dir = native_run / "assets" / "assets"
    outputs: list[Path] = []
    colors = {"Q": (220, 20, 60), "W": (0, 115, 220), "A": (20, 150, 70)}
    for asset_id in ("viewer-10", "viewer-173"):
        src = source_dir / f"{asset_id}.jpg"
        require(sha256_file(src) == EXPECTED[asset_id], f"source asset hash mismatch: {asset_id}")
        image = Image.open(src).convert("RGB")
        draw = ImageDraw.Draw(image)
        page_frames = [f for f in frames if f["box"]["image"]["asset_id"] == asset_id]
        role_counts = {"Q": 0, "W": 0, "A": 0}
        for frame in page_frames:
            role = frame["platform_role"]
            role_counts[role] += 1
            suffix = str(role_counts[role]) if role == "W" else ""
            label_box(draw, frame["box"]["bbox"], role + suffix, colors[role])
        if asset_id == "viewer-10":
            # This is a diagnostic subregion, not a seventh frame.
            label_box(draw, placeholder_box, "P inside Q", (225, 140, 0), width=2)
        target = overlays / f"{asset_id}-sixframe-overlay.png"
        image.save(target)
        outputs.append(target)

        if asset_id == "viewer-10":
            zoom_box = (45, 285, 625, 525)
        else:
            zoom_box = (35, 190, 450, 300)
        zoom = image.crop(zoom_box)
        zoom = zoom.resize((zoom.width * 2, zoom.height * 2), Image.Resampling.LANCZOS)
        zoom_target = overlays / f"{asset_id}-sixframe-zoom.png"
        zoom.save(zoom_target)
        outputs.append(zoom_target)
    return outputs


def stage_native_inputs(args, output: Path) -> Path:
    stage = output / "native-input"
    stage.mkdir(parents=True, exist_ok=False)
    copies = {
        "base.zip": Path(args.base_zip),
        "candidate.zip": Path(args.candidate_zip),
        "history.json": Path(args.history),
    }
    for name, source in copies.items():
        require(source.is_file(), f"missing input: {source}")
        expected_key = {"base.zip": "base_zip", "candidate.zip": "candidate_zip", "history.json": "history"}[name]
        require(sha256_file(source) == EXPECTED[expected_key], f"unexpected {name} hash")
        shutil.copyfile(source, stage / name)
    with zipfile.ZipFile(args.a07_archive) as archive:
        for name in ("approval.json", "policy.json"):
            raw = archive.read(A07_RUN_INPUT + name)
            (stage / name).write_bytes(raw)
    return stage


def run_native_chain(args, stage: Path, output: Path) -> tuple[Path, dict]:
    runtime = Path(args.runtime_root).resolve()
    require((runtime / "src" / "annotation" / "delivery" / "q1_offline" / "__main__.py").is_file(),
            "runtime root does not contain the fixed A07 q1_offline consumer")
    native_run = output / "native-c01-run"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(runtime / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [
        str(Path(args.python).resolve()), "-m", "annotation.delivery.q1_offline",
        "--input-dir", str(stage.resolve()),
        "--policy", str((stage / "policy.json").resolve()),
        "--output", str(native_run.resolve()),
        "--run-id", "a24-current-q1-sixframe-20261022",
    ]
    completed = subprocess.run(command, cwd=runtime, env=env, text=True, capture_output=True)
    invocation = {
        "command": command,
        "cwd": str(runtime),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "existing_consumer_called": "annotation.delivery.q1_offline",
    }
    write_json(output / "native-consumer-invocation.json", invocation)
    require(completed.returncode == 0, "existing C01 consumer failed; see native-consumer-invocation.json")
    summary = read_json(native_run / "summary.json")
    require(summary["result"] == "READY_FOR_REVIEW", "native C01 chain did not close")
    require(summary["frame_count"] == 6 and summary["outcome"] == "APPLIED", "native chain frame result mismatch")
    return native_run, invocation


def build_delivery(args, output: Path, native_run: Path, invocation: dict, current: dict) -> None:
    current_path = Path(args.current_q1)

    exchange = read_json(native_run / "exchange.json")
    require(exchange["format_version"] == "c01-exchange-1", "unexpected C01 exchange format")
    graph = locate_artifact(exchange, "QuestionGraph")
    evidence = locate_artifact(exchange, "EvidenceBundle")
    plan = locate_artifact(exchange, "ApplyPlan")
    native_receipt = locate_artifact(exchange, "ExecutionReceipt")
    plan_action = plan["payload"]["actions"][0]
    frames = json.loads(plan_action["expected_after"]["frames"])
    require([f["platform_role"] for f in frames] == ["Q", "W", "W", "W", "W", "A"],
            "fixed A07 role sequence is not Q/W/W/W/W/A")
    require(plan["payload"]["execution_mode"] == "SIMULATED", "native plan is not simulated")
    require(native_receipt["payload"]["results"][0]["effect_match"] == "MATCH", "native readback mismatch")

    regions = {r["region_id"]: r for r in evidence["payload"]["regions"]}
    q_region = regions[frames[0]["region_id"]]
    historical_stem = q_region["text"]
    expected_options = {
        chr(65 + index): regions[frame["region_id"]]["text"].split(".", 1)[1]
        for index, frame in enumerate(frames[1:5])
    }
    require(normalize_stem(current["question"]) == normalize_stem(historical_stem),
            "current stem does not semantically match the fixed A07 stem")
    require(current["option"] == expected_options, "current options do not match fixed A07 options")
    require(current["answer"] == regions[frames[5]["region_id"]]["text"] == "D",
            "current answer does not match fixed A07 answer")
    side_candidate = read_json(native_run / "assets" / "input" / "side-candidate.json")
    placeholder = next(r for r in side_candidate["payload"]["regions"] if r["key"] == "response-parentheses")
    q_box = frames[0]["box"]["bbox"]
    p_box = placeholder["bbox"]
    require(q_box[0] <= p_box[0] < p_box[2] <= q_box[2] and q_box[1] <= p_box[1] < p_box[3] <= q_box[3],
            "A07 Q frame does not contain the printed parentheses")
    require(not any(intersects(p_box, f["box"]["bbox"]) for f in frames[1:5]),
            "a W frame incorrectly contains the printed parentheses")

    overlay_paths = make_overlays(native_run, frames, p_box, output)
    frame_objects = []
    for index, frame in enumerate(frames, start=1):
        region = regions[frame["region_id"]]
        frame_objects.append({
            "frame_index": index,
            "platform_role": frame["platform_role"],
            "platform_type": frame["platform_type"],
            "fragment_id": frame["fragment_id"],
            "region_id": frame["region_id"],
            "asset": frame["box"]["image"],
            "bbox_xyxy_original_pixels": frame["box"]["bbox"],
            "historical_region_text": region["text"],
            "content_binding": "CURRENT_V3_SEMANTIC_MATCH_ONLY",
        })

    frozen = {
        "schema": "A24Q1SixFrameOfflineObject/v1",
        "status": "OFFLINE_SIMULATION_ONLY",
        "book_id": current["book_id"],
        "B_baseline": B_BASELINE,
        "fixed_A07_commit": A07_COMMIT,
        "current_content": {
            "input_path": str(current_path.resolve()),
            "sha256": EXPECTED["current_q1"],
            "evidence_type": current["evidence_type"],
            "source_type_meaning": current["source_type_meaning"],
            "question": current["question"],
            "option": current["option"],
            "answer": current["answer"],
            "canonical_question_id": None,
        },
        "geometry_provenance": {
            "source": "FIXED_A07_LOCAL_ORIGINAL_JPEGS",
            "a07_archive_path": str(Path(args.a07_archive).resolve()),
            "a07_archive_sha256": EXPECTED["a07_archive"],
            "c01_exchange_path": "native-c01-run/exchange.json",
            "c01_exchange_sha256": sha256_file(native_run / "exchange.json"),
            "source_v6_canvas_equivalence": "NOT_PROVEN",
            "current_screenshot_coordinate_source": "REJECTED",
        },
        "binding": {
            "content_to_geometry": "SEMANTIC_MATCH_ONLY_NOT_BYTE_OR_COORDINATE_EQUIVALENCE",
            "roles": [f["platform_role"] for f in frames],
            "frame_count": len(frames),
            "printed_parentheses": {
                "classification": "STEM_SUBREGION_NOT_SEPARATE_FRAME",
                "bbox_xyxy_original_pixels": p_box,
                "contained_by_Q": True,
                "intersects_any_W": False,
            },
        },
        "frames": frame_objects,
        "platform_gate": {
            "platform_use_allowed": False,
            "rejected_exact_missing_fields": MISSING_PLATFORM_FIELDS,
            "display_pages": {"question": current["question_page"], "answer": current["answer_page"]},
            "display_to_asset_or_savepage_mapping": "NOT_PROVEN",
        },
    }
    write_json(output / "q1-sixframe-object.json", frozen)

    offline_plan = {
        "schema": "A24Q1C01OfflinePlanBinding/v1",
        "status": "OFFLINE_SIMULATION_ONLY",
        "consumer": "annotation.delivery.q1_offline",
        "consumer_invocation_path": "native-consumer-invocation.json",
        "native_c01_plan_ref": {
            "artifact_id": plan["artifact_id"],
            "revision": plan["revision"],
            "content_hash": plan["content_hash"],
        },
        "native_operation": plan_action["operation"],
        "execution_mode": plan["payload"]["execution_mode"],
        "expected_after": {
            "question_exists": True,
            "frame_count": 6,
            "roles": [f["platform_role"] for f in frames],
        },
        "current_content_binding": "PASS_SEMANTIC_MATCH_ONLY",
        "platform_execution": "REJECTED",
        "platform_rejection_missing_fields": MISSING_PLATFORM_FIELDS,
    }
    write_json(output / "q1-offline-plan.json", offline_plan)

    receipt = {
        "schema": "A24Q1C01OfflineReceipt/v1",
        "status": "OFFLINE_SIMULATION_ONLY",
        "existing_consumer_called": invocation["existing_consumer_called"],
        "consumer_exit_code": invocation["exit_code"],
        "native_receipt_ref": {
            "artifact_id": native_receipt["artifact_id"],
            "revision": native_receipt["revision"],
            "content_hash": native_receipt["content_hash"],
            "path": "native-c01-run/receipt.json",
        },
        "native_simulated_result": native_receipt["payload"]["results"][0]["outcome"],
        "native_effect_match": native_receipt["payload"]["results"][0]["effect_match"],
        "native_replay_rejection_path": "native-c01-run/replay-rejection.json",
        "current_binding_checks": {
            "current_input_sha256": "PASS",
            "stem_semantics": "PASS",
            "options": "PASS",
            "answer": "PASS",
            "roles_Q_W_W_W_W_A": "PASS",
            "parentheses_inside_Q": "PASS",
            "parentheses_outside_all_W": "PASS",
            "local_original_asset_hashes": "PASS",
        },
        "platform_calls": 0,
        "platform_write": False,
        "platform_use_allowed": False,
        "platform_rejection_missing_fields": MISSING_PLATFORM_FIELDS,
    }
    write_json(output / "q1-simulated-receipt.json", receipt)

    manifest_files = []
    for path in sorted(p for p in output.rglob("*") if p.is_file() and p.name != "manifest.json"):
        manifest_files.append({
            "path": path.relative_to(output).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    manifest = {
        "schema": "A24Q1SixFrameDeliveryManifest/v1",
        "status": "OFFLINE_SIMULATION_ONLY",
        "file_count_excluding_manifest": len(manifest_files),
        "files": manifest_files,
        "overlay_paths": [p.relative_to(output).as_posix() for p in overlay_paths],
    }
    write_json(output / "manifest.json", manifest)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True, help="Python with pydantic 2 and Pillow")
    parser.add_argument("--runtime-root", required=True, help="Extracted fixed a07-fixed source root")
    parser.add_argument("--a07-archive", required=True)
    parser.add_argument("--base-zip", required=True)
    parser.add_argument("--candidate-zip", required=True)
    parser.add_argument("--history", required=True)
    parser.add_argument("--current-q1", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    current = precheck_current(args.current_q1)
    output = Path(args.output).resolve()
    require(not output.exists(), "output directory already exists; refusing overwrite")
    require(sha256_file(Path(args.a07_archive)) == EXPECTED["a07_archive"], "unexpected A07 archive hash")
    output.mkdir(parents=True)
    try:
        stage = stage_native_inputs(args, output)
        native_run, invocation = run_native_chain(args, stage, output)
        build_delivery(args, output, native_run, invocation, current)
    except BaseException as exc:
        write_json(output / "failed.json", {
            "status": "FAILED_STOPPED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "platform_calls": 0,
            "platform_write": False,
            "adapter_point": "CURRENT_V3_TO_FIXED_A07_C01_SEMANTIC_BINDING",
        })
        raise
    print(json.dumps({
        "status": "OFFLINE_SIMULATION_ONLY",
        "output": str(output),
        "object": str(output / "q1-sixframe-object.json"),
        "plan": str(output / "q1-offline-plan.json"),
        "receipt": str(output / "q1-simulated-receipt.json"),
        "manifest_sha256": sha256_file(output / "manifest.json"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
