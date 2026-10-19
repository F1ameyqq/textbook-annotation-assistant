"""Read only the already-produced R0 evidence; no receiver imports or calls."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
report = json.loads((HERE / "R0-original.json").read_bytes())
assets = {asset["asset_id"]: asset for asset in report["assets"]}
rows = []


def walk(value, path, inherited=None):
    if isinstance(value, list):
        for index, item in enumerate(value):
            walk(item, path + "/" + str(index), inherited)
    elif isinstance(value, dict):
        asset_id = value.get("asset_id", inherited)
        for field in ("bbox", "original_bbox", "revised_bbox", "trimmed_bbox"):
            if field in value and asset_id in assets:
                box, asset = value[field], assets[asset_id]
                assert len(box) == 4 and 0 <= box[0] < box[2] <= asset["width"]
                assert 0 <= box[1] < box[3] <= asset["height"]
                if "source_sha256" in value:
                    assert value["source_sha256"] == asset["sha256"]
                if "source_size" in value:
                    assert value["source_size"] == [asset["width"], asset["height"]]
                rows.append({"path": path + "/" + field, "asset_id": asset_id, "bbox": box,
                             "asset_sha256": asset["sha256"], "dimensions": [asset["width"], asset["height"]]})
        for key, item in value.items():
            walk(item, path + "/" + key, asset_id)


for case in report["cases"]:
    walk(case["source_snapshot"], case["case_id"])

out = {"status": "PASS_SAVED_OUTPUT_GEOMETRY", "receiver_calls": 0,
       "scope": "preserved coordinate occurrences bound to their own original assets; not approved drawing extents",
       "coordinate_occurrences": len(rows), "by_asset": {key: sum(r["asset_id"] == key for r in rows) for key in assets},
       "assets": report["assets"], "coordinates": rows,
       "all_original_snapshots_equal_checked_by": "independent_review.py check_original",
       "unknown_resource_173_viewer_page": assets["resource-173"]["external_refs"]["viewer_page"]}
with (HERE / "coordinate-ledger.json").open("xb") as handle:
    handle.write((json.dumps(out, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
print(json.dumps({"status": out["status"], "coordinate_occurrences": len(rows), "by_asset": out["by_asset"]}))
