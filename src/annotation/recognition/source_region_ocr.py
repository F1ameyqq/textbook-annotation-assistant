"""Source-region OCR for items without native question IDs or frames.

Page bindings, proposed regions, raw model observations and source review are
separate. No browser/runtime writer is imported. Model imports are collect-only.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import time

from .usense_capture import checked_ref, file_ref, read_json


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def validate_sources(spec):
    """Bind image bytes to saved download evidence, page inventory and native JSON."""
    from PIL import Image
    require(spec["schema"] == "SourceRegionOCRSpec/v1", "Unsupported source-region specification")
    book, sources = spec["book_id"], {}
    for source in spec["sources"]:
        viewer = source["viewer_page"]
        require(type(viewer) is int and viewer > 0 and viewer not in sources, "Invalid/duplicate viewer page")
        image_path = checked_ref(source["image"])
        inventory = read_json(checked_ref(source["page_inventory"]))
        require(inventory["book_id"] == book, "Page inventory belongs to another book")
        matches = [row for row in inventory["pages"] if row["viewer_page"] == viewer]
        require(len(matches) == 1, "Page inventory identity is not unique")
        page = matches[0]
        require(page["source_image_index"] == viewer-1, "Viewer/native page index mismatch")
        native_path = checked_ref(source["native_metadata"])
        require(source["native_metadata"]["sha256"] == page["native_response_sha256"],
                "Native metadata and inventory disagree")
        native = read_json(native_path)
        require(type(native.get("code")) is int and native["code"] == 0, "Native response is unsuccessful")
        require(str(native["data"]["file_id"]) == book, "Native page belongs to another book")
        native_pages = native["data"]["pages"]
        require(len(native_pages) == 1 and native_pages[0]["page_index"] == viewer-1,
                "Wrong native page bound to source image")
        require(native_pages[0]["image"] == page["image_url"], "Native source URL mismatch")
        manifest = read_json(checked_ref(source["download_manifest"]))
        require(manifest["book_id"] == book, "Download manifest belongs to another book")
        rows = [row for row in manifest["pages"] if row["viewer_page"] == viewer]
        require(len(rows) == 1, "Download page identity is not unique")
        download = rows[0]
        require(download.get("source_url", download.get("url")) == page["image_url"],
                "Downloaded image URL does not match native page")
        require(download["sha256"] == source["image"]["sha256"]
                and download["bytes"] == source["image"]["bytes"], "Wrong image bytes bound to page")
        if "metadata_sha256" in download:
            require(download["metadata_sha256"] == source["native_metadata"]["sha256"],
                    "Download metadata binding changed")
        with Image.open(image_path) as image:
            require(list(image.size) == source["dimensions"], "Source dimensions changed")
            if "width" in download:
                require([download["width"], download["height"]] == list(image.size), "Download dimensions mismatch")
        require(isinstance(source["allowed_roles"], list) and len(set(source["allowed_roles"])) == len(source["allowed_roles"]),
                "Explicit unique allowed source roles required")
        sources[viewer] = source
    return sources


def region_image(region, sources):
    from PIL import Image
    require(re.fullmatch(r"[A-Za-z0-9_.-]+", region["region_id"] or ""), "Unsafe region ID")
    source = sources[region["viewer_page"]]
    require(region["role"] in source["allowed_roles"], "Source page is forbidden for this region role")
    box = region["bbox"]
    require(isinstance(box, list) and len(box) == 4
            and all(type(v) in (int, float) and math.isfinite(v) for v in box), "Finite XYXY source bbox required")
    width, height = source["dimensions"]
    require(0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height, "Source bbox is outside page")
    rounded = [math.floor(box[0]), math.floor(box[1]), math.ceil(box[2]), math.ceil(box[3])]
    with Image.open(checked_ref(source["image"])) as image:
        crop = image.convert("RGB").crop(rounded)
    return source, rounded, crop


def row_boxes(image):
    import cv2
    import numpy as np
    threshold, mask = cv2.threshold(np.asarray(image.convert("L")), 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    groups = []
    for y in np.flatnonzero((mask > 0).sum(axis=1) >= 2).tolist():
        if not groups or y-groups[-1][-1] > 3:
            groups.append([y])
        else:
            groups[-1].append(y)
    result = []
    for group in groups:
        if group[-1]-group[0] < 3:
            continue
        xs = np.flatnonzero((mask[group[0]:group[-1]+1] > 0).sum(axis=0) >= 1)
        if len(xs):
            result.append([max(0, int(xs[0])-2), max(0, group[0]-2),
                           min(image.width, int(xs[-1])+3), min(image.height, group[-1]+3)])
    return result, float(threshold)


def collect(spec_path, out):
    """Run explicitly requested installed local OCR; never accepts transcripts."""
    spec_path, out = Path(spec_path), Path(out)
    spec = read_json(spec_path)
    sources = validate_sources(spec)
    out.mkdir(parents=True, exist_ok=False)
    (out/"crops").mkdir()
    (out/"observations").mkdir()
    run = {"schema": "SourceRegionOCRRun/v1", "status": "STARTED", "spec": file_ref(spec_path),
           "collector_source": file_ref(Path(__file__)), "inference_calls": 0,
           "platform_requests": 0, "downloads": 0, "paid_api_calls": 0,
           "status_is_not_content_approval": True, "regions": []}
    start, engine = time.perf_counter(), None
    seen = set()
    try:
        for region in spec["regions"]:
            rid = region["region_id"]
            require(rid not in seen, "Duplicate source-region ID")
            seen.add(rid)
            require(type(region["ocr"]) is bool, "Explicit OCR boolean required")
            source, box, crop = region_image(region, sources)
            crop_path = out/"crops"/(rid+".png")
            crop.save(crop_path)
            item = {"schema": "SourceRegionOCRObservation/v1", "region": region,
                    "source": source, "rounded_bbox": box, "crop": file_ref(crop_path),
                    "variants": [], "write_allowed": False, "human_confirmation": None}
            if region["ocr"]:
                import numpy as np
                from PIL import Image
                from .inline_ocr import _cpu_backend, _json_value
                if engine is None:
                    engine, backend = _cpu_backend()
                    write(out/"backend.json", backend)
                    run["backend"] = file_ref(out/"backend.json")
                boxes, threshold = row_boxes(crop)
                item.update(row_boxes=boxes, row_threshold=threshold)
                for scale in (3, 4):
                    variant = {"scale": scale, "rows": []}
                    for subbox in boxes:
                        image = crop.crop(subbox)
                        image = image.resize((image.width*scale, image.height*scale), Image.Resampling.LANCZOS)
                        bgr = np.ascontiguousarray(np.asarray(image)[:, :, ::-1])
                        raw, elapsed = engine(bgr, use_det=False, use_cls=False, use_rec=True, text_score=0)
                        run["inference_calls"] += 1
                        raw = _json_value(raw)
                        variant["rows"].append({"bbox_in_crop": subbox, "raw_result": raw,
                            "backend_elapsed": _json_value(elapsed),
                            "input_bgr_sha256": hashlib.sha256(bgr.tobytes()).hexdigest(),
                            "text": "".join(row[0] for row in raw or [])})
                    variant["joined_raw_text"] = "\n".join(row["text"] for row in variant["rows"])
                    item["variants"].append(variant)
            observation = out/"observations"/(rid+".json")
            write(observation, item)
            run["regions"].append({"region_id": rid, "observation": file_ref(observation)})
            write(out/"run.json", run)
        run["status"] = "LOCAL_SOURCE_REGION_OCR_DONE_REVIEW_REQUIRED"
    except Exception as exc:
        run.update(status="FAILED", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        run["wall_seconds"] = time.perf_counter()-start
        write(out/"run.json", run)
    return run


def check_inventory(run_path):
    """Reopen saved sources and check source-role/geometry/raw projections, no OCR."""
    from PIL import Image
    run = read_json(run_path)
    require(run["status"] == "LOCAL_SOURCE_REGION_OCR_DONE_REVIEW_REQUIRED", "Source-region run is incomplete")
    spec = read_json(checked_ref(run["spec"]))
    checked_ref(run["collector_source"])
    sources = validate_sources(spec)
    definitions = {row["region_id"]: row for row in spec["regions"]}
    require(len(definitions) == len(spec["regions"]) == len(run["regions"]), "Region scope changed")
    seen, calls = set(), 0
    for record in run["regions"]:
        rid = record["region_id"]
        require(rid not in seen and rid in definitions, "Unexpected/duplicate observation region")
        seen.add(rid)
        observation = read_json(checked_ref(record["observation"]))
        require(observation["region"] == definitions[rid], "Observation definition changed")
        source, box, crop = region_image(definitions[rid], sources)
        require(source == observation["source"] and box == observation["rounded_bbox"], "Observation source changed")
        with Image.open(checked_ref(observation["crop"])) as saved:
            require(saved.convert("RGB").size == crop.size and saved.convert("RGB").tobytes() == crop.tobytes(),
                    "Source crop pixels changed")
        require(observation["write_allowed"] is False and observation["human_confirmation"] is None,
                "Observation cannot be elevated to approval")
        variants = observation["variants"]
        require([v["scale"] for v in variants] == ([3, 4] if definitions[rid]["ocr"] else []), "OCR variants missing")
        for variant in variants:
            require(variant["joined_raw_text"] == "\n".join(row["text"] for row in variant["rows"]),
                    "Raw OCR projection changed")
            for row in variant["rows"]:
                require(row["text"] == "".join(value[0] for value in row["raw_result"] or []), "Raw result text changed")
                calls += 1
    require(calls == run["inference_calls"], "Inference count changed")
    return {"status": "SOURCE_REGION_BINDINGS_VALID_REVIEW_REQUIRED", "regions": len(seen),
            "inference_calls": calls, "write_allowed": False, "human_confirmation": None}
