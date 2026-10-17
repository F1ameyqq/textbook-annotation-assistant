"""Validate a declared chapter inventory and prepare B's offline source manifest.

The input is an inventory claim, not proof of business completeness. PARTIAL
reports are useful and may be run locally, but never grant chapter acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any


SCHEMA = "b-chapter-scope-input/0.1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_id(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", value))


def prepare(scope_path: Path, out_dir: Path) -> dict[str, Any]:
    scope_path = Path(scope_path).resolve()
    out_dir = Path(out_dir)
    data = json.loads(scope_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA:
        raise ValueError(f"scope manifest must use {SCHEMA}")

    gaps: list[dict[str, str]] = []
    for key in ("book_id", "scope_id", "chapter_id"):
        if not _safe_id(data.get(key)):
            gaps.append({"code": "INVALID_IDENTITY", "item": key, "detail": "missing or malformed"})
    if data.get("inventory_frozen") is not True:
        gaps.append({"code": "INVENTORY_NOT_FROZEN", "item": "inventory_frozen", "detail": "chapter denominator is not frozen"})

    pages = data.get("pages")
    assets = data.get("assets")
    if not isinstance(pages, list) or not pages:
        pages = []
        gaps.append({"code": "NO_EXPECTED_PAGES", "item": "pages", "detail": "expected page inventory is absent"})
    if not isinstance(assets, list):
        assets = []
        gaps.append({"code": "NO_ASSET_LIST", "item": "assets", "detail": "received asset inventory is absent"})

    expected_pages: dict[str, dict[str, Any]] = {}
    expected_asset_ids: set[str] = set()
    orders: set[int] = set()
    for index, page in enumerate(pages):
        if not isinstance(page, dict) or not _safe_id(page.get("page_id")):
            gaps.append({"code": "INVALID_PAGE_ID", "item": f"pages[{index}]", "detail": "page identity is required"})
            continue
        page_id = page["page_id"]
        if page_id in expected_pages:
            gaps.append({"code": "DUPLICATE_PAGE_ID", "item": page_id, "detail": "page appears more than once in inventory"})
            continue
        order = page.get("page_order")
        if type(order) is not int or order < 0 or order in orders:
            gaps.append({"code": "INVALID_PAGE_ORDER", "item": page_id, "detail": "page_order must be unique nonnegative integer"})
        else:
            orders.add(order)
        required = page.get("required_asset_ids")
        if not isinstance(required, list) or not required or any(not _safe_id(aid) for aid in required):
            gaps.append({"code": "INVALID_REQUIRED_ASSETS", "item": page_id, "detail": "each expected page needs required_asset_ids"})
            required = []
        if len(required) != len(set(required)):
            gaps.append({"code": "DUPLICATE_REQUIRED_ASSET", "item": page_id, "detail": "asset id repeats within page"})
        for aid in required:
            if aid in expected_asset_ids:
                gaps.append({"code": "DUPLICATE_EXPECTED_ASSET_ID", "item": aid, "detail": "asset id is required more than once"})
            expected_asset_ids.add(aid)
        expected_pages[page_id] = page

    received: dict[str, dict[str, Any]] = {}
    resolved_files: dict[str, Path] = {}
    observed_paths: dict[Path, str] = {}
    observed_hashes: dict[str, str] = {}
    for index, asset in enumerate(assets):
        where = f"assets[{index}]"
        if not isinstance(asset, dict) or not _safe_id(asset.get("asset_id")):
            gaps.append({"code": "INVALID_ASSET_ID", "item": where, "detail": "asset identity is required"})
            continue
        aid = asset["asset_id"]
        if aid in received:
            gaps.append({"code": "DUPLICATE_ASSET_ID", "item": aid, "detail": "asset appears more than once"})
            continue
        received[aid] = asset
        page_id = asset.get("page_id")
        if not _safe_id(page_id) or page_id not in expected_pages:
            gaps.append({"code": "UNEXPECTED_PAGE_IDENTITY", "item": aid, "detail": f"page_id {page_id!r} is not in chapter inventory"})
        elif aid not in expected_pages[page_id].get("required_asset_ids", []):
            gaps.append({"code": "ASSET_PAGE_IDENTITY_CONFLICT", "item": aid, "detail": "asset is not declared for its page"})
        if aid not in expected_asset_ids:
            gaps.append({"code": "UNEXPECTED_ASSET", "item": aid, "detail": "asset is not required by inventory"})
        rel = asset.get("path")
        if not isinstance(rel, str) or not rel.strip():
            gaps.append({"code": "ASSET_PATH_MISSING", "item": aid, "detail": "local image path is required"})
            continue
        source = Path(rel)
        if not source.is_absolute():
            source = scope_path.parent / source
        if not source.is_file():
            gaps.append({"code": "ASSET_FILE_MISSING", "item": aid, "detail": "declared source file is not available"})
            continue
        resolved_files[aid] = source.resolve()
        actual_hash = _sha256(source)
        if source.resolve() in observed_paths or actual_hash in observed_hashes:
            gaps.append({"code": "ALIASED_SOURCE_ASSET", "item": aid,
                         "detail": "same source path or byte content is declared under multiple asset identities; independent identity resolution required"})
        observed_paths[source.resolve()] = aid
        observed_hashes[actual_hash] = aid
        if not re.fullmatch(r"[0-9a-f]{64}", str(asset.get("sha256", ""))) or actual_hash != asset.get("sha256"):
            gaps.append({"code": "ASSET_SHA256_MISMATCH", "item": aid, "detail": "file bytes do not match declared SHA-256"})
        for dimension in ("width", "height"):
            if type(asset.get(dimension)) is not int or asset[dimension] <= 0:
                gaps.append({"code": "INVALID_DIMENSIONS", "item": aid, "detail": f"positive integer {dimension} is required"})
        try:
            from PIL import Image
            with Image.open(source) as image:
                if image.size != (asset.get("width"), asset.get("height")):
                    gaps.append({"code": "ASSET_DIMENSIONS_MISMATCH", "item": aid, "detail": "decoded image dimensions differ from declaration"})
        except Exception:
            gaps.append({"code": "ASSET_IMAGE_INVALID", "item": aid, "detail": "source file is not a readable image"})

    for aid in sorted(expected_asset_ids - set(received)):
        gaps.append({"code": "MISSING_ASSET", "item": aid, "detail": "required page asset has not been received"})

    out_dir.mkdir(parents=True, exist_ok=True)
    out_root = out_dir.resolve()
    ordered_assets = []
    page_order = {
        pid: page["page_order"] if type(page.get("page_order")) is int and page["page_order"] >= 0 else 10**9
        for pid, page in expected_pages.items()
    }
    def asset_sort_key(pair: tuple[str, dict[str, Any]]) -> tuple[int, str]:
        page_id = pair[1].get("page_id")
        return (page_order.get(page_id, 10**9) if _safe_id(page_id) else 10**9, pair[0])

    for ordinal, (aid, asset) in enumerate(sorted(received.items(), key=asset_sort_key)):
        source = resolved_files.get(aid)
        if source is not None:
            try:
                rel_path = source.relative_to(out_root).as_posix()
            except ValueError:
                gaps.append({"code": "ASSET_OUTSIDE_OUTPUT_ROOT", "item": aid, "detail": "place --out at a directory containing all declared source files so the source manifest remains portable"})
                rel_path = Path(asset.get("path", "")).name
        else:
            declared_path = asset.get("path")
            rel_path = Path(declared_path).name if isinstance(declared_path, str) else ""
        ordered_assets.append({
            "asset_id": aid,
            "path": rel_path,
            "sha256": asset.get("sha256"),
            "width": asset.get("width"),
            "height": asset.get("height"),
            "reading_order": ordinal,
            "external_refs": {"chapter_page_id": asset.get("page_id")},
            "reference_quality": "DECLARED_SOURCE_UNVERIFIED_CONTENT",
        })
    complete = not gaps and bool(expected_pages) and bool(expected_asset_ids)
    state = "DECLARED_COMPLETE_SOURCE_INVENTORY" if complete else "PARTIAL"
    report = {
        "schema_version": "b-chapter-scope-report/0.1",
        "book_id": data.get("book_id", "UNKNOWN"),
        "scope_id": data.get("scope_id", "UNKNOWN"),
        "chapter_id": data.get("chapter_id", "UNKNOWN"),
        "scope_state": state,
        "decision": "HOLD",
        "business_acceptance": False,
        "transcription_verified": False,
        "independent_denominator_verified": False,
        "inventory_frozen_claim": data.get("inventory_frozen") is True,
        "expected_page_count": len(expected_pages),
        "received_asset_count": len(received),
        "required_asset_count": len(expected_asset_ids),
        "gaps": gaps,
        "limits": [
            "DECLARED_COMPLETE_SOURCE_INVENTORY means only that the frozen input inventory and local bytes reconcile; independent chapter/page/question review is still required.",
            "A PARTIAL scope may be passed to the existing pipeline for offline work, but cannot pass chapter delivery.",
            "No artificial questions, answers, page identities, or human gold are created by this tool.",
        ],
    }
    source_descriptor = {
        "schema_version": "b-source-trial/0.1",
        "artifact_id": f"chapter-{data.get('chapter_id', 'unknown')}-source",
        "book_id": data.get("book_id", "UNKNOWN"),
        "scope_id": data.get("scope_id", "UNKNOWN"),
        "assets": ordered_assets,
        "scope_note": f"{state}; see chapter-scope-report.json. This declaration is not business acceptance.",
    }
    (out_dir / "source-descriptor.json").write_text(json.dumps(source_descriptor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "chapter-scope-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path, required=True, help="chapter inventory JSON")
    parser.add_argument("--out", type=Path, required=True, help="output directory for source descriptor and gap report")
    args = parser.parse_args(argv)
    try:
        report = prepare(args.scope, args.out)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
