"""Explicit offline crop preparation from the two retained, hash-bound originals."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / ".local/a24-first-save-wire-r1/crops"
PUBLIC = ROOT / "docs/evidence/A24/first-save-wire-r1"
DRAFT = Path("D:/1800/docs/evidence/coordinator/a24-first-save-source-plan/candidate-source-draft.json")
DRAFT_SHA = "602ba152c760fa67cec50cadf9ff792281270c9274df1c536521a8970c4a6ee8"
SOURCES = {
    14: (Path("D:/1800/.local/stages/a24-current-context-r1-live/original-viewer-14.jpg"),
         "4186d57ffad14f576fe7c967c96697d25c83ffe3512217c79b8371134181c1d9", 13, (1218, 1694)),
    173: (Path("D:/1800/.local/stages/a24-current-context-r1-live/original-viewer-173.jpg"),
          "a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be", 172, (1148, 1621)),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare():
    raw = DRAFT.read_bytes()
    assert sha(raw) == DRAFT_SHA
    draft = json.loads(raw)
    PRIVATE.mkdir(parents=True, exist_ok=False)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    originals = {}
    for viewer, (path, expected, resource, dimensions) in SOURCES.items():
        data = path.read_bytes()
        assert sha(data) == expected
        with Image.open(path) as image:
            image.load()
            assert image.format == "JPEG" and image.size == dimensions
            originals[viewer] = image.convert("RGB")
    crops, display = [], []
    for index, region in enumerate(draft["proposed_regions"]):
        viewer, box = region["viewer_page"], region["bbox"]
        assert all(type(v) is int for v in box)
        image = originals[viewer]
        assert 0 <= box[0] < box[2] <= image.width and 0 <= box[1] < box[3] <= image.height
        cut = image.crop(tuple(box))
        zone = ["question", "choice", "choice", "choice", "choice", "answer"][index]
        zone_index = [0, 0, 1, 2, 3, 0][index]
        path = PRIVATE / ("rect-" + str(index) + ".jpg")
        cut.save(path, "JPEG", quality=95, subsampling=0, optimize=False, progressive=False)
        data = path.read_bytes()
        with Image.open(path) as decoded:
            decoded.load()
            assert decoded.format == "JPEG" and decoded.size == cut.size
            pixel_hash = sha(decoded.convert("RGB").tobytes())
            display.append(decoded.convert("RGB").copy())
        name = "46007447_23_" + zone + "_" + str(zone_index) + "@page_" + str(viewer) + "_" + sha(data)[:12] + ".jpg"
        crops.append({"rect_id": "a24-r1-printed1-" + str(index), "role": region["role"], "zone": zone,
            "zone_index": zone_index, "option_label": region.get("option_label"), "viewer_page": viewer,
            "resource_index": SOURCES[viewer][2], "save_page_proposal": viewer,
            "actual_save_mapping": "UNKNOWN_UNTIL_CURRENT_BINDING_AND_READBACK", "original_bbox_xyxy": box,
            "original_sha256": SOURCES[viewer][1], "original_dimensions": list(image.size),
            "source_crop_RGB_sha256": sha(cut.tobytes()), "width": cut.width, "height": cut.height,
            "jpeg_bytes": len(data), "jpeg_sha256": sha(data), "jpeg_decoded_RGB_sha256": pixel_hash,
            "private_path": str(path), "object_basename": name, "object_key_template": "{QUALIFIED_SIGNATURE_DIR}" + name,
            "encoding": {"library": "Pillow", "format": "JPEG", "quality": 95, "subsampling": 0,
                         "optimize": False, "progressive": False}, "visual_review": "PENDING_EXACT_JPEG_REVIEW"})
    sheet = Image.new("RGB", (1100, 1000), "white")
    draw = ImageDraw.Draw(sheet)
    y = 10
    for index, image in enumerate(display):
        scale = 2 if index == 0 else 4
        enlarged = image.resize((image.width*scale, image.height*scale), Image.Resampling.NEAREST)
        draw.text((10, y), "JPEG " + str(index) + "  " + crops[index]["zone"] + "  " + str(crops[index]["width"]) + "x" + str(crops[index]["height"]), fill="black")
        y += 18
        sheet.paste(enlarged, (10, y))
        y += enlarged.height + 12
    sheet_path = PRIVATE / "jpeg-review-sheet.png"
    sheet.save(sheet_path)
    record = {"schema": "A24R1ExactCropBindings/v1", "status": "OFFLINE_JPEG_BYTES_READY_PENDING_VISUAL_REVIEW",
              "candidate_identity": "section2-basic-printed1-viewer14", "draft_sha256": DRAFT_SHA,
              "source_actual_final": "dceda09db31487d64654e23dd36ccd3705c740fc", "book_id": "46007447",
              "regions": crops, "private_review_sheet": str(sheet_path), "actual_uploads": 0,
              "save_authority": False, "whole_originals_copied": False}
    with (PUBLIC / "crop-bindings.json").open("xb") as handle:
        handle.write((json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"crops": len(crops), "private_review_sheet": str(sheet_path), "actual_uploads": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-fixed-crops", action="store_true", required=True)
    parser.parse_args()
    prepare()
