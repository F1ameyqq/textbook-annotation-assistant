"""M0 source geometry audit; writes a NEW directory, preserving old evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from math import isfinite
from pathlib import Path

from PIL import Image, ImageDraw
from page_mapping import image_name, is_coord_space_usable

ROOT = Path(__file__).resolve().parents[1]


def check_records(records: list[dict], image_root: Path, book_id: str = "46006966") -> dict:
    """Partial width coverage is not evidence of a different coordinate space."""
    results = []
    for page in sorted({int(record["page_index"]) for record in records}):
        if not is_coord_space_usable(page, book_id):
            results.append({"page_index": page, "verdict": "PAGE_MAPPING_UNCERTAIN"})
            continue
        path = image_root / image_name(book_id, page)
        if not path.is_file():
            results.append({"page_index": page, "verdict": "SOURCE_MISSING"})
            continue
        with Image.open(path) as image:
            width, height = image.size
        subset = [record for record in records if int(record["page_index"]) == page]
        boxes = []
        for record in subset:
            try:
                box = [float(value) for value in record["rect_bbox"].split(",")]
                valid = (len(box) == 4 and all(isfinite(v) for v in box)
                         and 0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height)
            except (ValueError, AttributeError, KeyError):
                box, valid = [], False
            boxes.append({"rect_id": record.get("rect_id", record.get("id")), "bbox": box,
                          "within_image": valid})
        results.append({"page_index": page, "asset_path": path.name,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "image_wh": [width, height], "geometry_alignment": "VERIFIED_SAMPLE",
                        "business_ground_truth": False, "boxes": boxes,
                        "verdict": "IN_BOUNDS" if all(b["within_image"] for b in boxes) else "INVALID_BBOX"})
    return {"book_id": book_id, "pages": results,
            "mapping_evidence": "data/derived/CORRECTION-page-mapping.md",
            "supersedes": ["data/derived/image_layout.json:coordinate_integrity",
                           "data/derived/image_layout.json:scale_hypothesis_probe"],
            "business_quality": "NOT_EVALUATED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new directory")
    records = json.loads((ROOT / "data/raw/annotations/annotations_unified_snapshot.json").read_text(encoding="utf-8"))
    image_root = ROOT / "data/raw/images"
    report = check_records(records, image_root)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# M0 页图映射与边界回归", "", "几何核查不构成业务真值或识别精度验收。", "",
             "| 标注页 | 正确资源 | 框数 | 边界结果 |", "|---|---|---|---|"]
    for page in report["pages"]:
        lines.append(f"| {page['page_index']} | {page.get('asset_path', '-')} | {len(page.get('boxes', []))} | {page['verdict']} |")
        if "asset_path" in page:
            with Image.open(image_root / page["asset_path"]) as original:
                image = original.convert("RGB")
            draw = ImageDraw.Draw(image)
            for box in page["boxes"]:
                if box["within_image"]:
                    draw.rectangle(box["bbox"], outline="red", width=3)
            image.save(args.out / f"page-{page['page_index']}.png")
    (args.out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"pages": len(report["pages"]), "business_quality": "NOT_EVALUATED"}))


if __name__ == "__main__":
    main()
