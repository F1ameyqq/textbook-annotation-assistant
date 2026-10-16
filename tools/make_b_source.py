"""Build a portable provisional source fixture from explicitly selected images."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", required=True, nargs="+", type=Path)
    parser.add_argument("--book-id", required=True)
    parser.add_argument("--scope-id", required=True)
    parser.add_argument("--out", required=True, type=Path, help="new portable source directory")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new directory")
    assets, staged = [], []
    # Validate all files before creating the package.
    for index, path in enumerate(args.images):
        with Image.open(path) as image:
            width, height = image.size
        name = f"assets/{index:03d}{path.suffix.lower()}"
        assets.append({"asset_id": f"asset-{index:03d}", "path": name,
                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                       "width": width, "height": height, "reading_order": index,
                       "external_refs": {"source_filename": path.name},
                       "reference_quality": "UNVERIFIED_RESEARCH_SAMPLE"})
        staged.append((path, name))
    package = {"schema_version": "b-source-trial/0.1", "artifact_id": "pending",
               "book_id": args.book_id, "scope_id": args.scope_id, "assets": assets}
    package["artifact_id"] = "b-source-" + hashlib.sha256(
        json.dumps(package, sort_keys=True).encode()).hexdigest()[:24]
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "assets").mkdir()
    for path, name in staged:
        shutil.copyfile(path, args.out / name)
    (args.out / "source.json").write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {len(assets)} assets; provisional schema b-source-trial/0.1")


if __name__ == "__main__":
    main()
