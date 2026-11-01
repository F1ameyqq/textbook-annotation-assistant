"""Offline recognition using existing projection/CC and optional CPU OCR.

This consumes B's explicitly provisional manifest, not A's SourceBundle contract.
No history annotations, browser state, assembly, or quality PASS are consumed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import importlib.metadata
import json
import math
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from uuid import NAMESPACE_URL, uuid5

import numpy as np
from PIL import Image, ImageDraw

SOURCE_SCHEMA = "b-source-trial/0.1"
EVIDENCE_SCHEMA = "b-evidence-trial/0.1"
REPO = Path(__file__).resolve().parents[3]
LEGACY_PATH = REPO / "tools" / "route_a_layout.py"
ROLES = {"question": "stem", "option": "option", "answer": "answer",
         "analysis": "explanation", "text_block": None}


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_digest(path: Path) -> str:
    """Git checkouts can differ in line endings without changing implementation."""
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def load_source(path: Path) -> tuple[dict, list[tuple[dict, Path]]]:
    """Validate identity and local asset bytes before any recognition starts."""
    source = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(source, dict):
        raise ValueError("source must be a JSON object")
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise ValueError(f"expected provisional schema {SOURCE_SCHEMA}; adapt A's contract explicitly")
    for key in ("artifact_id", "book_id", "scope_id"):
        if not isinstance(source.get(key), str) or not source[key].strip():
            raise ValueError(f"missing identity: {key}")
    assets = source.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("assets must be nonempty")
    root, seen, orders, resolved = path.parent.resolve(), set(), set(), []
    for asset in assets:
        if not isinstance(asset, dict):
            raise ValueError("each asset must be a JSON object")
        aid, rel = asset.get("asset_id"), asset.get("path")
        if not isinstance(aid, str) or not aid.strip() or aid in seen:
            raise ValueError("missing or duplicate asset_id")
        seen.add(aid)
        if (not isinstance(rel, str) or not rel or "\\" in rel
                or PurePosixPath(rel).is_absolute() or PureWindowsPath(rel).drive
                or ".." in PurePosixPath(rel).parts):
            raise ValueError("asset path must be portable and relative to the manifest")
        image_path = (root / rel).resolve()
        if not image_path.is_relative_to(root) or not image_path.is_file():
            raise ValueError(f"asset missing or outside source root: {aid}")
        order = asset.get("reading_order")
        if type(order) is not int or order < 0 or order in orders:
            raise ValueError("reading_order must be unique nonnegative integers")
        orders.add(order)
        for key in ("width", "height"):
            if type(asset.get(key)) is not int or asset[key] <= 0:
                raise ValueError(f"invalid {key}: {aid}")
        if file_digest(image_path) != asset.get("sha256"):
            raise ValueError(f"asset SHA-256 mismatch: {aid}")
        with Image.open(image_path) as image:
            if image.size != (asset["width"], asset["height"]):
                raise ValueError(f"asset dimensions mismatch: {aid}")
        resolved.append((asset, image_path))
    return source, sorted(resolved, key=lambda item: item[0]["reading_order"])


def legacy_backend():
    spec = importlib.util.spec_from_file_location("b_legacy_layout", LEGACY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_bbox(box: list, width: int, height: int) -> bool:
    return (len(box) == 4 and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                and math.isfinite(v) for v in box)
            and 0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height)


def recognize(source_path: Path, *, use_ocr: bool = False) -> tuple[dict, dict[str, Image.Image]]:
    source, inputs = load_source(source_path)
    backend = legacy_backend()
    cfg = dict(backend.CFG)
    backend_hash = code_digest(LEGACY_PATH)
    packages = ["numpy", "Pillow"] + (["rapidocr-onnxruntime", "onnxruntime"] if use_ocr else [])
    dependencies = {name: importlib.metadata.version(name) for name in packages}
    dependencies["opencv"] = backend.cv2.__version__
    # IDs are reproducible only for this exact source, implementation and config.
    identity = digest({"source": source, "backend": backend_hash, "config": cfg,
                       "ocr": use_ocr, "wrapper": code_digest(Path(__file__)),
                       "dependencies": dependencies})
    pages, previews = [], {}
    for asset, image_path in inputs:
        with Image.open(image_path) as image:
            rgb = np.asarray(image.convert("RGB"))
        gray = backend.imread_gray(image_path)
        mask, height, width = gray < cfg["thresh"], gray.shape[0], gray.shape[1]
        subpages, split_info = backend.split_subpages(mask, cfg)
        candidates, coverage_lines, crop_transforms, ocr_lines = [], [], [], []
        for subpage in subpages:
            index = subpage["subpage_index"]
            x1, x2 = int(subpage["x1"]), int(subpage["x2"])
            tx1, tx2 = backend.trim_low_ink_columns(mask, x1, x2, cfg["seam_ink_frac"])
            if tx2 - tx1 >= 20:
                x1, x2 = tx1, tx2
            # Legacy CC refinement includes one pixel of context. Preserve it in
            # the actual OCR crop and its inverse transform as well.
            x1, x2 = max(0, x1 - 1), min(width, x2 + 1)
            lines = backend.detect_lines(mask, x1, x2, 0, height, cfg)
            crop_id = f"{asset['asset_id']}-crop-{index}"
            crop_transforms.append({"crop_id": crop_id, "asset_id": asset["asset_id"],
                                    "original_bbox": [x1, 0, x2, height],
                                    "crop_to_original": [[1, 0, x1], [0, 1, 0], [0, 0, 1]]})
            coverage_lines.extend({"bbox": line["bbox"], "crop_id": crop_id} for line in lines)
            if use_ocr:
                atoms = backend.ocr_atoms(rgb[:, x1:x2, ::-1].copy(), ox=x1, oy=0,
                                          score_floor=cfg["ocr_score_floor"])
                backend.attach_atoms(lines, atoms)
                ocr_lines.extend({**atom, "crop_id": crop_id} for atom in atoms)
                local, _ = backend.group_candidates(lines, mask, cfg, asset["reading_order"], index)
            else:
                groups, _ = backend.group_by_gaps(lines, cfg)
                local = [{"bbox": backend.union_bbox([line["bbox"] for line in group]),
                          "role": "text_block", "confidence": None, "text": ""} for group in groups]
            candidates.extend((candidate, crop_id) for candidate in local)
        regions, issues = [], []
        for ordinal, (candidate, crop_id) in enumerate(candidates):
            box = [float(v) for v in candidate["bbox"]]
            if not valid_bbox(box, width, height):
                issues.append({"code": "INVALID_CANDIDATE_BBOX", "candidate_ordinal": ordinal,
                               "bbox": box})
                continue
            region_id = "r-" + str(uuid5(NAMESPACE_URL, f"{identity}/{asset['asset_id']}/{ordinal}"))
            regions.append({"region_id": region_id, "asset_id": asset["asset_id"],
                            "bbox": box, "crop_id": crop_id, "content_type": "unknown",
                            "role_candidate": ROLES[candidate["role"]],
                            "confidence": candidate["confidence"], "text_hint": candidate["text"],
                            "text_hint_is_final_transcription": False,
                            "verification_status": "UNVERIFIED"})
        if not regions:
            issues.append({"code": "NO_CANDIDATES"})
        preview = Image.fromarray(rgb)
        draw = ImageDraw.Draw(preview)
        for index, region in enumerate(regions):
            draw.rectangle(region["bbox"], outline="red", width=3)
            draw.text((region["bbox"][0], region["bbox"][1]), str(index), fill="blue")
        previews[asset["asset_id"]] = preview
        pages.append({"asset_id": asset["asset_id"], "source": asset, "regions": regions,
                      "crop_transforms": crop_transforms, "ocr_lines": ocr_lines,
                      "split_info": split_info, "issues": issues,
                      "coverage_evidence": {"method": "projection+connected_components",
                                            "independent_of_recognizer": False,
                                            "can_authorize_quality_pass": False,
                                            "lines": coverage_lines}})
    payload = {"pages": pages, "quality_decision": "NOT_EVALUATED",
               "limitations": ["Provisional B-side format; not the frozen public contract.",
                               "Candidates are not QuestionGraph or verified question/answer pairs.",
                               "No formula reconstruction or independent coverage check.",
                               "Region identities do not migrate human patches across changed inputs/models."]}
    return {"schema_version": EVIDENCE_SCHEMA, "kind": "EvidenceBundleTrial",
            "artifact_id": "b-evidence-" + identity[:24], "revision": 1,
            "book_id": source["book_id"], "scope_id": source["scope_id"],
            "input_refs": [{"artifact_id": source["artifact_id"], "content_hash": digest(source)}],
            "producer": {"module": "annotation.recognition.baseline", "version": "0.1.0",
                         "legacy_code_sha256": backend_hash, "ocr_enabled": use_ocr,
                         "dependencies": dependencies,
                         "configuration": cfg},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": digest(payload), "payload": payload}, previews


def write_result(result: dict, previews: dict[str, Image.Image], output: Path) -> None:
    # A new run directory prevents accidental replacement of a previous handoff.
    output.mkdir(parents=True, exist_ok=False)
    (output / "evidence.json").write_text(json.dumps(result, ensure_ascii=False, indent=2,
                                                   allow_nan=False), encoding="utf-8")
    overlay_manifest = []
    for index, (asset_id, preview) in enumerate(previews.items()):
        name = f"overlay-{index:03d}.png"
        preview.save(output / name)
        overlay_manifest.append({"asset_id": asset_id, "path": name,
                                 "sha256": file_digest(output / name)})
    (output / "previews.json").write_text(json.dumps(overlay_manifest, indent=2), encoding="utf-8")
