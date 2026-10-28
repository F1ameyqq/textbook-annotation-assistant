"""Batch real CPU OCR from captured platform frames and verified local pages.

Reads only captured JSON and image bytes; blocks sockets. No transcript inputs
are accepted. Every model result is retained and all candidates require review.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import socket
import sys
import time
import unicodedata


def blocked(*args, **kwargs):
    raise RuntimeError("BATCH_OCR_NETWORK_DISABLED")


socket.create_connection = blocked
socket.getaddrinfo = blocked
socket.socket.connect = blocked
socket.socket.connect_ex = blocked
sys.dont_write_bytecode = True


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p):
    return {"path": str(p.resolve()), "bytes": p.stat().st_size, "sha256": sha(p)}


def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def write(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def normal(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text or ""))


def parse_choices(text):
    """Parse observed A-D prefixes only; preserve all preamble and value text."""
    text = unicodedata.normalize("NFKC", text)
    matches = list(re.finditer(r"(?<![A-Za-z])([A-D])\s*[.、:：]\s*", text))
    values, issues = {}, []
    prefix = text[:matches[0].start()].strip() if matches else text.strip()
    for i, match in enumerate(matches):
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        value = text[match.end():end].strip()
        if match[1] in values:
            issues.append("DUPLICATE_OPTION_LABEL:"+match[1])
        else:
            values[match[1]] = value
        if not value:
            issues.append("EMPTY_OPTION:"+match[1])
    if set(values) != set("ABCD"):
        issues.append("FOUR_OPTION_LABELS_NOT_PARSED")
    if prefix:
        issues.append("CHOICE_PREAMBLE_NOT_ASSIGNED_TO_STEM")
    return values, prefix, issues


def line_boxes(image):
    """Otsu projection only; preserve faint single letters without text hints."""
    import cv2
    import numpy as np
    threshold, mask = cv2.threshold(np.asarray(image.convert("L")), 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    ys = np.flatnonzero((mask > 0).sum(axis=1) >= 2).tolist()
    groups = []
    for y in ys:
        if not groups or y-groups[-1][-1] > 3: groups.append([y])
        else: groups[-1].append(y)
    boxes = []
    for group in groups:
        if group[-1]-group[0] < 3: continue
        xs = np.flatnonzero((mask[group[0]:group[-1]+1] > 0).sum(axis=0) >= 1)
        if len(xs):
            boxes.append([max(0, int(xs[0])-2), max(0, group[0]-2), min(image.width, int(xs[-1])+3), min(image.height, group[-1]+3)])
    return boxes, float(threshold)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--capture", type=Path, required=True)
    p.add_argument("--sources", type=Path, required=True)
    p.add_argument("--source-manifest", type=Path, required=True)
    p.add_argument("--orders", type=int, nargs="+", required=True)
    p.add_argument("--lesson-id", default="dir-1792063578574-2a6vq8zom")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if len(set(args.orders)) != len(args.orders) or not args.orders: raise ValueError("Explicit unique question orders required")
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "script-source.py").write_bytes(Path(__file__).read_bytes())
    start = time.perf_counter()
    run = {"schema": "LessonBatchOCRRun/v1", "status": "STARTED", "orders": args.orders,
           "started_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
           "python_executable": sys.executable, "script": ref(Path(__file__)),
           "network_disabled": True, "platform_requests": 0, "downloads": 0, "paid_api_calls": 0,
           "inference_calls": 0, "variants": [3, 4], "algorithm": "OTSU_ROW_PROJECTION_THEN_EXISTING_CPU_RECOGNIZER",
           "no_reference_transcript_input": True, "candidates": []}
    try:
        import numpy as np
        from PIL import Image
        sys.path.insert(0, str(args.repo / "src"))
        from annotation.recognition.inline_ocr import _cpu_backend, _json_value
        summary = read(args.capture / "capture-summary.json")
        captures = summary["captures"]
        def get(name):
            declared, file = captures[name], args.capture / (name+".json")
            assert declared["status"] == 200 and file.stat().st_size == declared["bytes"] and sha(file) == declared["sha256"]
            value = read(file)
            assert value["code"] == 0
            return value["data"]
        directory = get("directory")["directory_data"]
        all_frames = get("frames")
        lesson = []
        def walk(nodes):
            for node in nodes:
                if node["id"] == args.lesson_id: lesson.append(node)
                walk(node.get("children", []))
        walk(directory)
        assert len(lesson) == 1
        nodes = {int(n["order_in_level"]): n for n in lesson[0]["children"] if n.get("isQuestion")}
        manifest = read(args.source_manifest)
        image_by_page, page_provenance = {}, {}
        for source in manifest["pages"]:
            viewer = int(source["viewer_page"])
            path = args.sources / ("viewer-"+str(viewer)+".jpg")
            assert path.is_file() and sha(path) == source["sha256"] and path.stat().st_size == source["bytes"]
            native = get("page_"+str(viewer))
            assert native["file_id"] == "46007447"
            assert native["pages"][0]["image"] == source["url"]
            assert native["pages"][0]["page_index"] == source["source_page_index"]
            with Image.open(path) as original: image_by_page[viewer] = original.convert("RGB")
            page_provenance[viewer] = {**source, "file": ref(path), "dimensions": list(image_by_page[viewer].size)}
        engine, backend = _cpu_backend()
        write(args.out / "backend.json", backend)
        run["adapter"] = ref(args.repo / "src/annotation/recognition/inline_ocr.py")
        write(args.out / "sources.json", {"source_manifest": ref(args.source_manifest), "pages": page_provenance,
                                          "capture_summary": ref(args.capture / "capture-summary.json")})
        for order in args.orders:
            qout = args.out / ("q"+str(order))
            qout.mkdir()
            crops = qout / "crops"
            crops.mkdir()
            node, info = nodes[order], get("q"+str(order)+"_info")
            assert str(info["file_id"]) == "46007447" and int(info["order_in_level"]) == order
            frames = get("q"+str(order)+"_annotations")
            expected = [f for f in all_frames if f.get("directory_id") == args.lesson_id and int(f["order_in_level"]) == order]
            assert sorted(frames, key=lambda f:f["rect_id"]) == sorted(expected, key=lambda f:f["rect_id"])
            zone_records, issues = defaultdict(list), []
            for frame in sorted(frames, key=lambda f:(f["type"], f["image_order_in_annotation_zone"], f["rect_id"])):
                if frame["type"] not in {"question", "choice", "answer"}: continue
                if frame.get("content_type") != "text":
                    issues.append({"code": "NON_TEXT_FRAME_PRESERVED_NOT_RECOGNIZED", "rect_id": frame["rect_id"]})
                    continue
                image = image_by_page[int(frame["page_index"])]
                boxf = [float(n) for n in frame["rect_bbox"].split(",")]
                if not (0 <= boxf[0] < boxf[2] <= image.width and 0 <= boxf[1] < boxf[3] <= image.height): raise ValueError("Frame outside current source")
                box = [math.floor(boxf[0]), math.floor(boxf[1]), math.ceil(boxf[2]), math.ceil(boxf[3])]
                padded = [max(0, box[0]-2), max(0, box[1]-2), min(image.width, box[2]+2), min(image.height, box[3]+2)]
                crop = image.crop(padded)
                crop_file = crops / (frame["type"]+"-"+frame["rect_id"]+".png")
                crop.save(crop_file)
                boxes, threshold = line_boxes(crop)
                item = {"rect_id": frame["rect_id"], "zone": frame["type"], "platform_frame": frame,
                        "source": page_provenance[int(frame["page_index"])] , "crop": ref(crop_file),
                        "original_bbox": boxf, "rounded_bbox": box, "padded_bbox": padded,
                        "row_threshold": threshold, "row_boxes": boxes, "variants": []}
                for scale in (3, 4):
                    v = {"scale": scale, "rows": [], "joined_raw_text": ""}
                    for row_index, subbox in enumerate(boxes):
                        row = crop.crop(subbox)
                        row = row.resize((row.width*scale, row.height*scale), Image.Resampling.LANCZOS)
                        bgr = np.ascontiguousarray(np.asarray(row)[:, :, ::-1])
                        tick = time.perf_counter()
                        result, elapsed = engine(bgr, use_det=False, use_cls=False, use_rec=True, text_score=0)
                        run["inference_calls"] += 1
                        result, elapsed = _json_value(result), _json_value(elapsed)
                        texts = [r[0] for r in result or []]
                        v["rows"].append({"row_index": row_index, "bbox_in_crop": subbox,
                                          "input_bgr_sha256": hashlib.sha256(bgr.tobytes()).hexdigest(),
                                          "raw_result": result, "backend_elapsed": elapsed,
                                          "wall_seconds": time.perf_counter()-tick, "text": "".join(texts)})
                    v["joined_raw_text"] = "\n".join(r["text"] for r in v["rows"])
                    item["variants"].append(v)
                if normal(item["variants"][0]["joined_raw_text"]) != normal(item["variants"][1]["joined_raw_text"]):
                    issues.append({"code": "VARIANT_DISAGREEMENT", "rect_id": frame["rect_id"]})
                zone_records[frame["type"]].append(item)
                write(qout / "raw-results.json", dict(zone_records))
            # Deterministic primary proposal, not acceptance. All raw variants
            # and disagreements remain available to the reviewer.
            fields = {zone: "\n".join(item["variants"][0]["joined_raw_text"] for item in zone_records[zone])
                      for zone in ("question", "choice", "answer")}
            options, unassigned, option_issues = parse_choices(fields["choice"])
            issues += [{"code": s} for s in option_issues]
            answer_match = re.fullmatch(r"(?:\d+[.、])?([A-D])", normal(fields["answer"]))
            answer = answer_match[1] if answer_match else None
            if answer is None: issues.append({"code": "SINGLE_CHOICE_ANSWER_NOT_PARSED"})
            if not fields["question"].strip(): issues.append({"code": "EMPTY_STEM"})
            qcandidate = {"schema": "LessonQuestionOCRCandidate/v1", "status": "REVIEW_REQUIRED",
                          "book_id": "46007447", "question_order": order, "node_id": node["id"], "question_info_id": info["id"],
                          "lesson_id": args.lesson_id, "question_info": info, "raw_zone_text": fields,
                          "parsed_options": options, "choice_unassigned_preamble": unassigned,
                          "parsed_answer": answer, "issues": issues, "write_allowed": False,
                          "selection_rule": "SCALE3_PRIMARY_OBSERVATION_WITH_ALL_VARIANTS_RETAINED_NOT_CORRECTNESS_CLAIM",
                          "raw_results": ref(qout / "raw-results.json"), "platform_frames": frames,
                          "existing_zone_bodies": {z: get("q"+str(order)+"_"+z) for z in ("question", "choice", "answer", "analysis", "knowledge_point")},
                          "human_confirmation": None, "auto_correction": False}
            write(qout / "candidate.json", qcandidate)
            run["candidates"].append({"order": order, "candidate": ref(qout / "candidate.json"),
                                      "issues": issues, "status": "REVIEW_REQUIRED"})
            write(args.out / "run.json", run)
            print(json.dumps({"order": order, "issues": [x["code"] for x in issues], "parsed_option_labels": list(options), "answer": answer}, ensure_ascii=True), flush=True)
        run["status"] = "REAL_LOCAL_BATCH_OCR_DONE_REVIEW_REQUIRED"
    except Exception as exc:
        run.update(status="FAILED", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        run["wall_seconds"] = time.perf_counter()-start
        run["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write(args.out / "run.json", run)
        write(args.out / "output-manifest.json", {"files": [ref(f) for f in sorted(args.out.rglob("*")) if f.is_file() and f.name != "output-manifest.json"]})


if __name__ == "__main__": main()
