"""Build a local coverage ledger from captured metadata and source-bound reviews.

No browser, HTTP client, OCR engine or platform writer is imported. Output may
contain private source references and must stay outside the published repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit


def require(condition, code):
    if not condition:
        raise ValueError(code)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def checked_pages(inventory, book_id):
    require(inventory.get("book_id") == book_id, "PAGE_BOOK_MISMATCH")
    pages = inventory.get("pages", [])
    total = inventory.get("source_total_pages")
    require(type(total) is int and total > 0 and len(pages) == total, "PAGE_SCOPE_INCOMPLETE")
    require({p["viewer_page"] for p in pages} == set(range(1, total + 1)), "VIEWER_SCOPE_MISMATCH")
    result = {}
    for page in pages:
        viewer, index = page["viewer_page"], page["source_image_index"]
        require(type(viewer) is int and type(index) is int and index >= 0, "PAGE_INDEX_INVALID")
        raw = Path(page["native_response"])
        require(sha(raw) == page["native_response_sha256"], "NATIVE_RESPONSE_CHANGED")
        payload = read(raw)
        require(payload.get("code") == 0 and str(payload["data"]["file_id"]) == book_id, "NATIVE_BOOK_MISMATCH")
        entries = payload["data"]["pages"]
        require(len(entries) == 1, "NATIVE_PAGE_SCOPE_AMBIGUOUS")
        native = entries[0]
        require(native["image"] == page["image_url"] and native["page_index"] == index, "NATIVE_PAGE_BINDING_MISMATCH")
        url = urlsplit(page["image_url"])
        require(url.scheme == "https" and not url.username and not url.query and not url.fragment,
                "SOURCE_URL_INVALID")
        require(url.path.endswith(f"/{book_id}/{book_id}_page_{index}.jpg"), "SOURCE_BOOK_OR_INDEX_MISMATCH")
        result[viewer] = page
    require(len({p["source_image_index"] for p in pages}) == total, "SOURCE_INDEX_DUPLICATE")
    return result


def checked_images(manifest, pages, book_id):
    require(manifest.get("book_id") == book_id, "IMAGE_BOOK_MISMATCH")
    images = {}
    for image in manifest.get("pages", []):
        viewer = image["viewer_page"]
        require(viewer in pages and viewer not in images, "IMAGE_PAGE_DUPLICATE_OR_UNKNOWN")
        require(image.get("status") == "IMAGE_VERIFIED", "IMAGE_NOT_VERIFIED")
        require(image["source_image_index"] == pages[viewer]["source_image_index"] and
                image["source_url"] == pages[viewer]["image_url"], "IMAGE_PAGE_BINDING_MISMATCH")
        require(sha(image["path"]) == image["sha256"] and Path(image["path"]).stat().st_size == image["bytes"],
                "IMAGE_BYTES_CHANGED")
        images[viewer] = image
    return images


def checked_evidence(evidence, images, book_id):
    require(evidence and isinstance(evidence, list), "SOURCE_EVIDENCE_REQUIRED")
    viewers = set()
    for ref in evidence:
        viewer = ref["viewer_page"]
        require(viewer in images and ref["source_sha256"] == images[viewer]["sha256"], "REVIEW_SOURCE_MISMATCH")
        viewers.add(viewer)
        if ref.get("ocr_path"):
            require(sha(ref["ocr_path"]) == ref["ocr_sha256"], "OCR_BYTES_CHANGED")
            ocr = read(ref["ocr_path"])
            require(ocr.get("book_id") == book_id and ocr["viewer_page"] == viewer and
                    ocr["source_sha256"] == images[viewer]["sha256"], "OCR_SOURCE_MISMATCH")
            indices = ref.get("ocr_row_indices", [])
            require(all(type(i) is int and 0 <= i < len(ocr["rows"]) for i in indices), "OCR_ROW_REFERENCE_INVALID")
    return viewers


def build_ledger(*, book_id, page_inventory, directory_inventory, image_manifest, mappings):
    pages = checked_pages(page_inventory, book_id)
    images = checked_images(image_manifest, pages, book_id)
    require(mappings.get("book_id") == book_id, "MAPPING_BOOK_MISMATCH")
    directories = directory_inventory["directories"]
    ids = {d["id"] for d in directories}
    require(len(ids) == len(directories), "DIRECTORY_ID_DUPLICATE")
    require(all(isinstance(d.get("path"), list) and d["path"] for d in directories), "DIRECTORY_PATH_REQUIRED")
    raw_questions = directory_inventory.get("questions", [])
    nodes = {q["id"]: q for q in raw_questions}
    require(len(nodes) == len(raw_questions), "NATIVE_NODE_DUPLICATE")
    reviews, bound_nodes = {}, set()
    for mapping in mappings.get("directories", []):
        did = mapping["directory_id"]
        require(did in ids and did not in reviews, "MAPPING_DIRECTORY_UNKNOWN_OR_DUPLICATE")
        question_pages, answer_pages = mapping.get("question_pages", []), mapping.get("answer_pages", [])
        require(len(question_pages) == len(set(question_pages)) and len(answer_pages) == len(set(answer_pages)),
                "MAPPING_PAGE_DUPLICATE")
        require(set(question_pages + answer_pages) <= set(images), "MAPPING_SOURCE_IMAGE_MISSING")
        refs = checked_evidence(mapping.get("source_evidence"), images, book_id)
        require(set(question_pages + answer_pages) <= refs, "MAPPING_PAGE_EVIDENCE_MISSING")
        items = mapping.get("recognized_items", [])
        require(isinstance(items, list), "ITEM_ENUMERATION_INVALID")
        require(len({i["item_key"] for i in items}) == len(items), "ITEM_KEY_DUPLICATE")
        for item in items:
            require(item.get("kind") in {"QUESTION", "VARIANT", "READING_TASK", "WORKED_EXAMPLE"}, "ITEM_KIND_INVALID")
            require(item["viewer_page"] in question_pages and item["source_sha256"] == images[item["viewer_page"]]["sha256"],
                    "ITEM_SOURCE_MISMATCH")
            require(item.get("evidence_kind") in {"OCR_ROW_OBSERVATION", "MODEL_SOURCE_INSPECTION"}, "ITEM_EVIDENCE_REQUIRED")
        complete = mapping.get("complete_enumeration", False)
        require(type(complete) is bool, "ENUMERATION_FLAG_INVALID")
        require(not complete or bool(items), "COMPLETE_ENUMERATION_NEEDS_ITEMS")
        bindings = []
        for binding in mapping.get("native_bindings", []):
            require(binding["node_id"] in nodes, "NATIVE_BINDING_NODE_UNKNOWN")
            require(binding["node_id"] not in bound_nodes, "NATIVE_NODE_BOUND_TWICE")
            bound_nodes.add(binding["node_id"])
            actual = nodes[binding["node_id"]]
            require(str(actual["native_order"]) == str(binding["native_order"]), "NATIVE_ORDER_MISMATCH")
            require(actual["parent_id"] == binding["current_directory_id"], "NATIVE_PARENT_MISMATCH")
            require(binding["item_key"] in {i["item_key"] for i in items}, "NATIVE_ITEM_UNRECOGNIZED")
            bindings.append({**binding, "desired_directory_id": did, "migration_needed": actual["parent_id"] != did})
        reviews[did] = {**mapping, "native_bindings": bindings,
            "recognized_items_observed": len(items),
            "question_count": sum(i["kind"] != "WORKED_EXAMPLE" for i in items) if complete else None,
            "worked_example_count": sum(i["kind"] == "WORKED_EXAMPLE" for i in items) if complete else None,
            "human_confirmation": None, "platform_acceptance": "NOT_RUN"}
    rows = []
    for directory in directories:
        mapping = reviews.get(directory["id"])
        rows.append({"directory_id": directory["id"], "path": directory["path"],
                     "is_leaf": directory["subdirectories"] == 0,
                     "existing_native_nodes": directory["direct_questions"],
                     "question_count": mapping["question_count"] if mapping else None,
                     "coverage_status": mapping.get("status", "SOURCE_MAPPING_MISSING") if mapping else "SOURCE_MAPPING_MISSING",
                     "mapping": mapping})
    chapters = []
    for directory in directories:
        if len(directory["path"]) != 1:
            continue
        children = [r for r in rows if r["path"][0] == directory["path"][0] and r["is_leaf"]]
        chapters.append({"directory_id": directory["id"], "label": directory["path"][0],
                         "leaf_directories": len(children),
                         "mapped_leaf_directories": sum(r["mapping"] is not None for r in children),
                         "question_pages": sorted({p for r in children if r["mapping"] for p in r["mapping"]["question_pages"]}),
                         "answer_pages": sorted({p for r in children if r["mapping"] for p in r["mapping"]["answer_pages"]}),
                         "source_enumerated_leaf_directories": sum(r["question_count"] is not None for r in children),
                         "question_count": None, "human_confirmation": None})
    roles = mappings.get("page_roles", [])
    require(len(roles) == len({r["viewer_page"] for r in roles}), "PAGE_ROLE_DUPLICATE")
    require(all(r["viewer_page"] in pages for r in roles), "PAGE_ROLE_UNKNOWN")
    role_map = {r["viewer_page"]: r for r in roles}
    unbound = mappings.get("unbound_scopes", [])
    require(len({s["scope_id"] for s in unbound}) == len(unbound), "UNBOUND_SCOPE_DUPLICATE")
    for scope in unbound:
        require(scope.get("directory_id") is None and scope.get("question_count") is None,
                "UNBOUND_SCOPE_MUST_NOT_FABRICATE_DIRECTORY_OR_COUNT")
        referenced = set(scope.get("question_pages", []) + scope.get("answer_pages", []))
        require(referenced <= checked_evidence(scope.get("source_evidence"), images, book_id),
                "UNBOUND_SCOPE_EVIDENCE_MISSING")
    page_rows = [{**page, "local_image": images.get(viewer), "classification": role_map.get(viewer),
                  "question_count": None} for viewer, page in sorted(pages.items())]
    return {"schema": "SourceBoundBookCoverageLedger/v1", "book_id": book_id,
            "summary": {"source_pages": len(pages), "verified_images": len(images),
                        "directory_nodes": len(rows), "leaf_directories": sum(r["is_leaf"] for r in rows),
                        "mapped_directories": len(reviews),
                        "mapped_leaf_directories": sum(r["is_leaf"] and r["mapping"] is not None for r in rows),
                        "complete_item_enumerations": sum(r["question_count"] is not None for r in rows),
                        "native_question_nodes": len(nodes), "whole_book_question_count": None,
                        "unbound_source_scopes": len(unbound),
                        "pre_annotation_blocks": sum(p["pre_annotation_blocks"] for p in pages.values())},
            "pages": page_rows, "chapters": chapters, "directories": rows, "unbound_scopes": unbound,
            "hierarchy_notes": mappings.get("hierarchy_notes", []),
            "counting_policy": "Unknown counts remain null; native nodes, pages, directories and zero pre-annotation blocks are not question denominators.",
            "human_confirmation": None, "platform_acceptance": "NOT_RUN", "platform_calls": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("book-id", "page-inventory", "directory-inventory", "image-manifest", "mappings", "out"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    output = Path(args.out)
    require(not output.exists(), "OUTPUT_ALREADY_EXISTS")
    inputs = {name: Path(getattr(args, name)) for name in ("page_inventory", "directory_inventory", "image_manifest", "mappings")}
    result = build_ledger(book_id=args.book_id, **{name: read(path) for name, path in inputs.items()})
    result["input_refs"] = {name: {"path": str(path.resolve()), "sha256": sha(path)} for name, path in inputs.items()}
    result["implementation"] = {"file": Path(__file__).name, "sha256": sha(__file__)}
    # Validate everything before creating the private output.
    output.mkdir(parents=True)
    (output / "coverage-ledger.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
