"""Source-bound CPU OCR recovery probes; never rewrites base OCR evidence.

Crop geometry is reviewed development configuration. Recognition text is always
the actual engine output, including mistakes. Consensus is a reproducibility
signal, not formula correctness or business verification. Public contracts are
still a draft; this is B's provisional supplemental artifact.
"""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image, ImageEnhance

from .baseline import code_digest, digest, file_digest, load_source, valid_bbox

SCHEMA = "b-recovery-trial/0.1"
ASSET = "viewer-173"


def _probe(name, box, parents=(), *, window=None, mode="REC_ONLY", group=None, purpose="source crop recovery"):
    return {"probe_id": name, "asset_id": ASSET, "crop_bbox": box,
            "base_line_ids": [f"{ASSET}/ocr/{n}" for n in parents],
            "window_index": window, "engine_mode": mode,
            "supersession_group": group, "purpose": purpose}


# Boundaries select visible source regions, not expected recognized text.
DEFAULT_PROBES = [
    _probe("unit2-q16", [579,263,1084,367], [13,15,16,17,20,21,23,25], window=4,
           mode="DET_REC", group="unit2-q16", purpose="Recover a missing primary anchor and available formula OCR"),
    _probe("lesson1-q16", [55,508,551,696], [48,51,52,53,57,58,60,63,64,65,66,68],
           window=0, mode="DET_REC", purpose="Re-probe whole answer; formula fidelity remains unverified"),
    _probe("lesson1-q16-formula-row1", [65,555,545,580], window=0, purpose="Missing formula row; no value inferred"),
    _probe("lesson1-q16-formula-row2", [65,578,545,601], window=0, purpose="Missing formula row; no value inferred"),
    _probe("lesson2-row79-tail", [68,774,150,797], [79], window=1, group="lesson2-row79"),
    _probe("lesson2-row79-q2", [153,774,188,797], [79], window=1, group="lesson2-row79"),
    _probe("lesson2-row79-q3", [194,774,227,797], [79], window=1, group="lesson2-row79"),
    _probe("lesson2-row79-q4", [232,774,283,797], [79], window=1, group="lesson2-row79"),
    _probe("lesson2-variant", [65,945,545,970], window=1, group="lesson2-variant",
           purpose="Previously missing printed variant line; preserve OCR spelling of marker"),
    _probe("lesson2-q6", [54,869,92,893], [88], window=1, group="lesson2-q6-q7"),
    _probe("lesson2-q7", [94,869,134,893], [88], window=1, group="lesson2-q6-q7"),
    _probe("unit2-q9", [54,1458,93,1482], [149], window=3, group="unit2-q9-q10"),
    _probe("unit2-q10", [96,1458,145,1482], [149], window=3, group="unit2-q9-q10"),
    _probe("topic1-training-q3", [578,1055,619,1088], [106], window=6, group="topic1-training-q3-q4"),
    _probe("topic1-training-q4", [620,1055,665,1087], [106], window=6, group="topic1-training-q3-q4"),
    _probe("topic1-training-q4-numerator", [663,1051,690,1071], [105], window=6, group="topic1-training-q3-q4"),
    _probe("topic1-training-q4-denominator", [663,1071,690,1089], [107], window=6, group="topic1-training-q3-q4"),
    _probe("topic2-training", [577,1224,805,1261], [119,120,121,122,123,125], window=7,
           mode="DET_REC", purpose="Dense training row; preserve unresolved fractions and identity"),
    _probe("topic1-examples", [577,837,1079,892], [86,87], window=6, mode="DET_REC",
           purpose="Examples have their own namespace; do not invent training question IDs"),
    _probe("topic2-example", [576,1111,1079,1209], [111,113,114,115,116,117], window=7,
           mode="DET_REC", purpose="Unnumbered example; no invented primary number"),
    _probe("math-world", [54,1012,548,1240], [102,104,108,110,112], window=2,
           mode="DET_REC", purpose="Unnumbered reading answer including diagram labels; retain unresolved identity"),
    _probe("title-topic1", [599,803,1062,835], [82], purpose="Known heading evidence"),
    _probe("title-math-world", [83,983,516,1011], [98], purpose="Known heading evidence"),
    _probe("title-topic2", [597,1086,1058,1115], [109], purpose="Known heading evidence"),
    _probe("title-reflection", [699,1259,951,1288], [126], purpose="Known heading evidence"),
    _probe("footer-page", [1037,1548,1080,1579], [157], purpose="Page-number evidence, no answer identity"),
    _probe("footer-book", [910,1556,1041,1587], [158], purpose="Footer evidence, no answer identity"),
]
VARIANTS = [{"variant_id": "scale3", "scale": 3, "contrast": 1.0},
            {"variant_id": "scale4-contrast", "scale": 4, "contrast": 1.5}]


def _ref(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def _compact(text):
    return re.sub(r"\s+", "", text)


def _select(probe):
    variants = probe["variants"]
    usable = [v for v in variants if v["ocr_lines"]]
    if len(usable) == 2:
        signatures = [[_compact(line["text"]) for line in v["ocr_lines"]] for v in usable]
        if signatures[0] == signatures[1] and all(line["score"] >= .75 for v in usable for line in v["ocr_lines"]):
            return usable[0]["variant_id"], "OCR_CONSENSUS_UNVERIFIED", "Two declared preprocessing passes agree; source crop geometry is explicit."
        # Formula probes can recover an anchor even when formula text disagrees.
        anchors = []
        for variant in usable:
            anchors.append([re.match(r"^\s*(\d{1,2})[.．、]\s*解", line["text"])[1]
                            for line in variant["ocr_lines"] if re.match(r"^\s*(\d{1,2})[.．、]\s*解", line["text"])
                            and line["score"] >= .8])
        if anchors[0] and anchors[0] == anchors[1]:
            return usable[0]["variant_id"], "ANCHOR_RECOVERED_FORMULAS_UNRESOLVED", "Primary anchor agrees in two passes; differing formula hypotheses remain unresolved."
    return None, "UNRESOLVED", "Predeclared OCR consensus/anchor rules were not met; no expected answer was used."


def _model_receipts(package_root):
    return [{"name": str(path.relative_to(package_root)).replace("\\", "/"), "sha256": file_digest(path)}
            for path in sorted(package_root.rglob("*.onnx"))]


def recover(source_path, evidence, out, *, probe_ids=None):
    """Run explicit local crops, persist all hypotheses and optional apply plans.

    ``out`` must be new. Crop PNGs are unscaled source pixels, not edited OCR
    predictions. No caller-provided text or expected numeric answer is consumed.
    Plans are provisional assembly views; consumers must archive base evidence.
    """
    source_path, out = Path(source_path), Path(out)
    if out.exists():
        raise ValueError("recovery output must be a new directory")
    if evidence.get("content_hash") != digest(evidence.get("payload")):
        raise ValueError("base evidence payload hash mismatch")
    source, inputs = load_source(source_path)
    if (source["book_id"], source["scope_id"]) != (evidence["book_id"], evidence["scope_id"]):
        raise ValueError("source/base evidence scope mismatch")
    pages = {page["asset_id"]: page for page in evidence["payload"]["pages"]}
    paths = {asset["asset_id"]: path for asset, path in inputs}
    for asset, _ in inputs:
        if pages.get(asset["asset_id"], {}).get("source") != asset:
            raise ValueError("source/base asset descriptor mismatch")
    if source["book_id"] != "46007447" or ASSET not in pages:
        raise ValueError("this reviewed development crop plan is only for book 46007447")
    selected = [p for p in DEFAULT_PROBES if probe_ids is None or p["probe_id"] in probe_ids]
    if probe_ids is not None and set(probe_ids) != {p["probe_id"] for p in selected}:
        raise ValueError("unknown recovery probe")
    from rapidocr_onnxruntime import RapidOCR
    import rapidocr_onnxruntime
    dependencies = {name: importlib.metadata.version(name) for name in
                    ("rapidocr-onnxruntime", "onnxruntime", "numpy", "Pillow", "opencv-python")}
    engine = RapidOCR()
    models = _model_receipts(Path(rapidocr_onnxruntime.__file__).parent)
    producer = {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__)),
                "engine": "rapidocr_onnxruntime", "device": "CPU", "dependencies": dependencies,
                "dependency_sha256": digest(dependencies), "model_files": models,
                "configuration_sha256": digest({"probes": selected, "variants": VARIANTS}),
                "selection_policy": "two-pass exact text agreement with scores>=.75; or primary worked-answer anchor agreement>=.8; never expected answer values"}
    out.mkdir(parents=True)
    crop_dir = out / "recovery-assets"
    crop_dir.mkdir()
    payload = {"base_evidence_ref": _ref(evidence), "source_ref": {"artifact_id": source["artifact_id"], "content_hash": digest(source)},
               "base_raw_line_count": sum(len(p["ocr_lines"]) for p in pages.values()),
               "base_detail_line_count": sum(len(p.get("answer_detail_lines", [])) for p in pages.values()),
               "base_evidence_unchanged": True, "probes": [], "supersession_plan": [],
               "visual_transcription_slots": [], "verification_status": "UNVERIFIED", "run_status": "RUNNING",
               "limitations": ["OCR agreement does not certify formulas or missing content.",
                               "Reviewed crop/section geometry is development input.",
                               "Raw base OCR and all alternate hypotheses must remain immutable.",
                               "Unnumbered examples and reading material need explicit semantic namespaces."]}

    def write_checkpoint():
        identity = digest({"payload": payload, "producer": producer})
        value = {"schema_version": SCHEMA, "kind": "RecoveryEvidenceTrial", "artifact_id": "b-recovery-"+identity[:24],
                 "revision": 1, "run_id": evidence.get("run_id"), "book_id": evidence["book_id"], "scope_id": evidence["scope_id"],
                 "input_refs": [_ref(evidence), payload["source_ref"]], "producer": producer,
                 "created_at": datetime.now(timezone.utc).isoformat(), "content_hash": digest(payload), "payload": payload}
        (out/"recovery-evidence.json").write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        return value

    images = {}
    for specification in selected:
        page, asset = pages[specification["asset_id"]], pages[specification["asset_id"]]["source"]
        box = specification["crop_bbox"]
        if not valid_bbox(box, asset["width"], asset["height"]):
            raise ValueError("recovery crop outside source")
        if specification["asset_id"] not in images:
            images[specification["asset_id"]] = Image.open(paths[specification["asset_id"]]).convert("RGB")
        crop = images[specification["asset_id"]].crop(box)
        crop_path = crop_dir/(specification["probe_id"]+".png")
        crop.save(crop_path)
        window = specification["window_index"]
        location = None
        if window is not None:
            context = evidence["payload"]["context"]["pages"][specification["asset_id"]]["windows"][window]
            location = {"column": context["column"], "window_index": window, "section_path": list(context["path"])}
        probe = {**specification, "source_sha256": asset["sha256"], "source_size": [asset["width"],asset["height"]],
                 "crop_path": "recovery-assets/"+crop_path.name, "crop_sha256": file_digest(crop_path),
                 "location": location, "variants": [], "verification_status": "UNVERIFIED"}
        for config in VARIANTS:
            scale = config["scale"]
            transformed = crop.resize((crop.width*scale, crop.height*scale), Image.Resampling.LANCZOS)
            if config["contrast"] != 1:
                transformed = ImageEnhance.Contrast(transformed).enhance(config["contrast"])
            bgr = np.array(transformed)[:, :, ::-1].copy()
            use_det = specification["engine_mode"] == "DET_REC"
            raw, elapsed = engine(bgr, use_det=use_det, use_cls=False)
            variant = {**config, "use_det": use_det, "use_cls": False, "use_rec": True,
                       "resampling": "PIL_LANCZOS", "transformed_pixels_sha256": hashlib.sha256(bgr.tobytes()).hexdigest(),
                       "crop_to_original": [[1/scale,0,box[0]],[0,1/scale,box[1]],[0,0,1]],
                       "raw_ocr_result": raw, "elapsed_seconds": elapsed, "ocr_lines": []}
            for ordinal, result in enumerate(raw or []):
                if use_det:
                    polygon, text, score = result[:3]
                    mapped = [[round(x/scale+box[0],4),round(y/scale+box[1],4)] for x,y in polygon]
                    bbox = [min(x for x,y in mapped),min(y for x,y in mapped),max(x for x,y in mapped),max(y for x,y in mapped)]
                else:
                    text, score = result[:2]
                    mapped, bbox = None, list(box)
                variant["ocr_lines"].append({"line_id": "recovery/"+probe["probe_id"]+"/"+config["variant_id"]+"/"+str(ordinal),
                                              "text": text, "score": float(score), "bbox": bbox, "polygon": mapped,
                                              "asset_id": specification["asset_id"], "location": location,
                                              "base_line_ids": list(specification["base_line_ids"]),
                                              "geometry_precision": "OCR_DETECTION" if use_det else "REVIEWED_CROP_REGION",
                                              "verification_status": "UNVERIFIED"})
            probe["variants"].append(variant)
        probe["selected_variant_id"], probe["status"], probe["selection_rationale"] = _select(probe)
        payload["probes"].append(probe)
        if probe["probe_id"].startswith("lesson1-q16-formula") or probe["probe_id"] == "unit2-q16":
            payload["visual_transcription_slots"].append({"probe_id": probe["probe_id"], "asset_id": probe["asset_id"],
                                                          "source_sha256": probe["source_sha256"], "crop_bbox": probe["crop_bbox"],
                                                          "crop_sha256": probe["crop_sha256"], "method": "MODEL_VISUAL_DEVELOPMENT_TRANSCRIPTION",
                                                          "status": "NOT_POPULATED", "text": None, "verification_status": "UNVERIFIED"})
        write_checkpoint()
        print(json.dumps({"probe_id": probe["probe_id"], "status": probe["status"],
                          "selected_variant_id": probe["selected_variant_id"]}), flush=True)
    groups = {}
    for probe in payload["probes"]:
        if probe["supersession_group"]:
            groups.setdefault(probe["supersession_group"], []).append(probe)
    for group, probes in groups.items():
        expected = [p["probe_id"] for p in DEFAULT_PROBES if p["supersession_group"] == group]
        if {p["probe_id"] for p in probes} != set(expected) or any(p["selected_variant_id"] is None for p in probes):
            continue
        replacements = [line["line_id"] for probe in probes for variant in probe["variants"]
                        if variant["variant_id"] == probe["selected_variant_id"] for line in variant["ocr_lines"]]
        base_ids = list(dict.fromkeys(ref for p in probes for ref in p["base_line_ids"]))
        payload["supersession_plan"].append({"plan_id": group, "action": "REPLACE_FOR_ASSEMBLY" if base_ids else "ADD_MISSING",
                                             "base_line_ids": base_ids, "replacement_line_ids": replacements,
                                             "selected_probe_ids": [p["probe_id"] for p in probes], "asset_id": probes[0]["asset_id"],
                                             "source_sha256": probes[0]["source_sha256"], "location": probes[0]["location"],
                                             "partition_basis": "Explicit reviewed source crop regions; exact whole base OCR objects remain archived. New text is actual local OCR.",
                                             "verification_status": "UNVERIFIED"})
    payload["run_status"] = "COMPLETE"
    return write_checkpoint()
