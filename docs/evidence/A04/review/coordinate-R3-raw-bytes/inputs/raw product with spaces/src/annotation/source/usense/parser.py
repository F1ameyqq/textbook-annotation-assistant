"""Parse bounded captures into the C01 source view, without network or geometry.

Only an allowlist of response fields survives parsing. Original source URLs,
request bodies, headers, cookies and unknown response fields are never emitted.
The original-image API index and annotation viewer page are separate identities.
"""
import hashlib
import io
import json
import math
import re
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Dict, List

from annotation.contracts import SCHEMA_VERSION, SourceBundle, content_digest, seal_artifact
from .png_pixels import MAX_PNG_BYTES, PNG_SIGNATURE, PNGPixelError, verify_png_pixels


class SourceParseError(ValueError):
    """Fixed, safe diagnostics. The failing response value is deliberately absent."""

    def __init__(self, code, path, message):
        self.code, self.path, self.message = code, path, message
        super().__init__("{}: [{}] {}".format(path, code, message))


def _fail(code, path, message):
    raise SourceParseError(code, path, message)


def _mapping(value, path):
    if not isinstance(value, dict):
        _fail("INCOMPLETE_RESPONSE", path, "expected an object")
    return value


def _list(value, path):
    if not isinstance(value, list):
        _fail("INCOMPLETE_RESPONSE", path, "expected a list")
    return value


def _text(value, path):
    if not isinstance(value, str) or not value or len(value) > 4096 or any(ord(c) < 32 for c in value):
        _fail("INVALID_FIELD", path, "expected a nonempty bounded text field")
    return value


def _external(value, path):
    value = _text(value, path)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value):
        _fail("INVALID_IDENTIFIER", path, "unsupported platform identifier")
    return value


def _integer(value, path, minimum=0):
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail("INVALID_FIELD", path, "expected a bounded integer")
    return value


def _timestamp(value, path):
    if not isinstance(value, str):
        _fail("INVALID_TIME", path, "timestamp must include a timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail("INVALID_TIME", path, "timestamp must be ISO 8601")
    if parsed.tzinfo is None:
        _fail("INVALID_TIME", path, "timestamp must include a timezone")
    return parsed


def _data(raw, path):
    raw = _mapping(raw, path)
    code = raw.get("code")
    if code in (401, 403, "401", "403"):
        _fail("LOGIN_REQUIRED", path, "protected response requires authentication")
    if isinstance(code, bool) or code != 0:
        _fail("RESPONSE_FAILURE", path, "platform response did not report success")
    if "data" not in raw:
        _fail("INCOMPLETE_RESPONSE", path, "successful response has no data")
    return raw["data"]


def _identity(kind, book_id, external):
    return "{}-{}".format(kind, hashlib.sha256((book_id + "\0" + external).encode("utf-8")).hexdigest()[:24])


def parse_directory(raw, book_id="46007447"):
    """Return (directories, questions), with platform and internal IDs separated.

    Platform question order is resolved within its directory, never globally.
    Internal IDs derive from the platform node identity, never the printed label,
    platform order or a box. No chapter membership of a page is inferred here.
    """
    book_id = _external(book_id, "$.book_id")
    data = _mapping(_data(raw, "$.directory"), "$.directory.data")
    nodes = _list(data.get("directory_data"), "$.directory.data.directory_data")
    directories, questions, seen, question_keys = [], [], set(), set()

    def visit(node, parent_platform, parent_internal, path, depth):
        if depth > 64:
            _fail("DIRECTORY_DEPTH", path, "directory depth exceeds parser limit")
        node = _mapping(node, path)
        external = _external(node.get("id"), path + ".id")
        if external in seen:
            _fail("DUPLICATE_REFERENCE", path + ".id", "directory/question node identifier repeats")
        seen.add(external)
        label = _text(node.get("label"), path + ".label")
        marker = node.get("isQuestion", False)
        if not isinstance(marker, bool):
            _fail("INVALID_FIELD", path + ".isQuestion", "question marker must be boolean")
        children = _list(node.get("children", []), path + ".children")
        if marker:
            if parent_platform is None or children:
                _fail("MISSING_REFERENCE", path, "question requires a directory parent and no child nodes")
            order = _integer(node.get("order_in_level"), path + ".order_in_level", 1)
            key = (parent_platform, order)
            if key in question_keys:
                _fail("AMBIGUOUS_QUESTION", path, "question order repeats within the same directory")
            question_keys.add(key)
            questions.append({"question_id": _identity("question", book_id, external),
                              "platform_question_id": external, "directory_id": parent_platform,
                              "source_directory_id": parent_internal,
                              "platform_order": order, "printed_label": label})
            return
        internal = _identity("directory", book_id, external)
        directories.append({"directory_id": internal, "parent_id": parent_internal,
                            "label": label, "platform_directory_id": external})
        for i, child in enumerate(children):
            visit(child, external, internal, path + ".children[{}]".format(i), depth + 1)

    for i, node in enumerate(nodes):
        visit(node, None, None, "$.directory.data.directory_data[{}]".format(i), 0)
    if not directories:
        _fail("SOURCE_EMPTY_DIRECTORY", "$.directory", "no directory nodes were observed")
    return directories, questions


def _asset_path(root, value, path):
    value = _text(value, path)
    parts = value.split("/")
    if ("\\" in value or ":" in value or PurePosixPath(value).is_absolute()
            or PureWindowsPath(value).drive or any(p in ("", ".", "..") for p in parts)
            or any(p.endswith((".", " ")) or re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", p, re.I)
                   or any(c in p for c in '<>"|?*') for p in parts)):
        _fail("PATH_ESCAPE", path, "asset path must be a portable relative path")
    resolved = (root / value).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        _fail("PATH_ESCAPE", path, "resolved asset leaves the bundle root")
    return value, resolved


def _image_inventory(path, location):
    """Bind metadata after PNG scanline completeness AND strict pixel decode.

    C01's resource loader checks hashes/headers. This source boundary additionally
    requires the actual original bytes to decode; an intact header is not proof
    of usable pixels. Both parse_capture and the publication recheck call here.
    """
    try:
        with path.open("rb") as source:
            prefix = source.read(8)
            # Bound allocation before reading a PNG body. Other supported image
            # formats retain their existing decoder path and behaviour.
            blob = prefix + source.read(MAX_PNG_BYTES - 7 if prefix == PNG_SIGNATURE else -1)
    except OSError:
        _fail("RESOURCE_MISSING", location, "downloaded original file is unavailable")
    if blob.startswith(PNG_SIGNATURE):
        try:
            verify_png_pixels(blob)
        except PNGPixelError:
            _fail("RESOURCE_INVALID", location, "PNG original pixel completeness check failed")
    width = height = 0
    media_type = None
    try:
        if blob.startswith(b"\x89PNG\r\n\x1a\n") and blob[12:16] == b"IHDR":
            width, height = struct.unpack(">II", blob[16:24])
            media_type = "image/png"
        elif blob.startswith((b"P2", b"P5")):
            tokens = []
            for line in blob.splitlines():
                tokens.extend(line.split(b"#", 1)[0].split())
                if len(tokens) >= 4:
                    break
            width, height = int(tokens[1]), int(tokens[2])
            media_type = "image/x-portable-graymap"
        elif blob.startswith(b"\xff\xd8"):
            offset = 2
            while offset < len(blob):
                if blob[offset] != 255:
                    offset += 1
                    continue
                while offset < len(blob) and blob[offset] == 255:
                    offset += 1
                marker = blob[offset]
                offset += 1
                if marker in (0xD9, 0xDA):
                    break
                if marker in (0x00, 0x01, *range(0xD0, 0xD9)):
                    continue
                length = struct.unpack(">H", blob[offset:offset + 2])[0]
                if length < 2:
                    break
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                              0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    height, width = struct.unpack(">HH", blob[offset + 3:offset + 7])
                    media_type = "image/jpeg"
                    break
                offset += length
    except (ValueError, IndexError, struct.error):
        _fail("RESOURCE_INVALID", location, "original image header is invalid")
    if not media_type or width <= 0 or height <= 0:
        _fail("RESOURCE_INVALID", location, "original image dimensions are unavailable")
    try:
        from PIL import Image, ImageFile
        # Never enable Pillow's permissive truncation flag or modify global
        # decoder settings. A permissive ambient decoder cannot prove this gate.
        if ImageFile.LOAD_TRUNCATED_IMAGES:
            _fail("RESOURCE_INVALID", location, "strict original image decoding is required")
        expected_format = {"image/png": "PNG", "image/jpeg": "JPEG",
                           "image/x-portable-graymap": "PPM"}[media_type]
        with Image.open(io.BytesIO(blob)) as image:
            if image.format != expected_format or image.size != (width, height):
                _fail("RESOURCE_INVALID", location, "decoded original format or dimensions differ")
            image.verify()
        # verify() checks structure/CRCs but need not decompress pixel data.
        # Reopen the same immutable bytes and decode every available frame.
        with Image.open(io.BytesIO(blob)) as image:
            for frame in range(getattr(image, "n_frames", 1)):
                image.seek(frame)
                image.load()
    except SourceParseError:
        raise
    except Exception:
        _fail("RESOURCE_INVALID", location, "complete original image decoding failed")
    return {"sha256": hashlib.sha256(blob).hexdigest(), "width": width,
            "height": height, "media_type": media_type}


def _annotations(raw, questions, book_id):
    records = _list(_data(raw, "$.annotations"), "$.annotations.data")
    index = {(q["directory_id"], q["platform_order"]): q for q in questions}
    by_id = {q["platform_question_id"]: q for q in questions}
    roles = {"question": "Q", "choice": "W", "option": "W", "answer": "A",
             "analysis": "E", "explanation": "E", "Q": "Q", "W": "W", "A": "A", "E": "E"}
    output, seen = [], set()
    for i, record in enumerate(records):
        loc = "$.annotations.data[{}]".format(i)
        record = _mapping(record, loc)
        if "file_id" in record and str(record["file_id"]) != book_id:
            _fail("TARGET_MISMATCH", loc + ".file_id", "annotation belongs to a different book")
        frame_id = _external(record.get("platform_frame_id", record.get("rect_id")), loc + ".rect_id")
        if frame_id in seen:
            _fail("DUPLICATE_REFERENCE", loc, "platform frame identifier repeats")
        seen.add(frame_id)
        directory = _external(record.get("directory_id"), loc + ".directory_id")
        order = _integer(record.get("platform_order", record.get("order_in_level")), loc + ".order_in_level", 1)
        question = index.get((directory, order))
        if question is None:
            _fail("MISSING_REFERENCE", loc, "frame directory/order has no question node")
        if "platform_question_id" in record and by_id.get(record["platform_question_id"]) != question:
            _fail("REFERENCE_CONFLICT", loc, "frame question identity conflicts with its directory/order")
        bbox = record.get("bbox", record.get("rect_bbox"))
        if isinstance(bbox, str):
            bbox = bbox.split(",")
        if not isinstance(bbox, list) or len(bbox) != 4 or any(isinstance(v, bool) for v in bbox):
            _fail("INVALID_BBOX", loc + ".rect_bbox", "box must contain four finite numbers")
        try:
            bbox = [float(v) for v in bbox]
        except (ValueError, TypeError, OverflowError):
            _fail("INVALID_BBOX", loc + ".rect_bbox", "box must contain four finite numbers")
        if not all(math.isfinite(v) for v in bbox):
            _fail("INVALID_BBOX", loc + ".rect_bbox", "box must contain four finite numbers")
        role = roles.get(_text(record.get("platform_role", record.get("type")), loc + ".type"))
        if role is None:
            _fail("UNSUPPORTED_FRAME_ROLE", loc + ".type", "frame type has no known platform role")
        parent = record.get("parent_frame_id", record.get("parent_rect_id"))
        if parent is not None:
            parent = _external(parent, loc + ".parent_rect_id")
        output.append({"platform_frame_id": frame_id, "platform_question_id": question["platform_question_id"],
                       "directory_id": directory, "platform_order": order,
                       "viewer_page": _integer(record.get("viewer_page", record.get("page_index")), loc + ".page_index", 1),
                       "bbox": bbox, "platform_role": role, "parent_frame_id": parent})
    for i, frame in enumerate(output):
        if frame["parent_frame_id"] is not None and frame["parent_frame_id"] not in seen:
            _fail("MISSING_REFERENCE", "$.annotations.data[{}].parent_rect_id".format(i), "frame parent is absent")
    parents = {frame["platform_frame_id"]: frame["parent_frame_id"] for frame in output}
    for frame_id in parents:
        visited, current = set(), frame_id
        while current is not None:
            if current in visited:
                _fail("REFERENCE_CYCLE", "$.annotations.data", "frame parent references contain a cycle")
            visited.add(current)
            current = parents[current]
    return output


@dataclass(frozen=True)
class ParsedCapture:
    book_id: str
    observed_at: str
    evidence_mode: str
    provenance: str
    book: Dict[str, Any]
    metadata_page_count: int
    directories: List[dict]
    questions: List[dict]
    pages: List[dict]
    annotations: List[dict]
    observed_hash: str

    def safe_data(self):
        return {key: getattr(self, key) for key in self.__dataclass_fields__}

    def assert_integrity(self):
        data = self.safe_data()
        data.pop("observed_hash")
        if content_digest(data) != self.observed_hash:
            _fail("CAPTURE_MUTATED", "$", "parsed capture differs from its observation hash")


def parse_capture(capture, root, expected_book="46007447", expected_pages=(14, 15, 173),
                  now=None, max_age_seconds=300):
    """Parse a complete bounded capture; defaults reject stale/future observations.

    Offline replay must supply an explicit ``now`` and retain provenance. Such a
    replay checks parsing only; it cannot establish that an old capture is live.
    Source resources must already exist beneath root; no download is performed.
    """
    capture = _mapping(capture, "$")
    if capture.get("capture_version") != "a04.readonly.v1":
        _fail("CAPTURE_VERSION", "$.capture_version", "unsupported capture version")
    if capture.get("complete", True) is not True:
        _fail("INCOMPLETE_RESPONSE", "$.complete", "capture explicitly reports incompleteness")
    mode = capture.get("evidence_mode")
    provenance = capture.get("provenance", "SYNTHETIC" if mode == "SYNTHETIC" else "LIVE")
    if mode not in ("SYNTHETIC", "OBSERVED") or provenance not in ("SYNTHETIC", "LIVE", "HISTORICAL"):
        _fail("PROVENANCE", "$.evidence_mode", "capture mode/provenance is unsupported")
    if (mode == "SYNTHETIC") != (provenance == "SYNTHETIC"):
        _fail("PROVENANCE", "$.provenance", "synthetic and observed provenance must remain separate")
    observed_at = capture.get("observed_at")
    observed_time = _timestamp(observed_at, "$.observed_at")
    if now is None:
        current_time = datetime.now(timezone.utc)
    elif isinstance(now, datetime):
        current_time = now
        if now.tzinfo is None:
            _fail("INVALID_TIME", "$.now", "comparison time must include a timezone")
    else:
        current_time = _timestamp(now, "$.now")
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, (int, float)) or not math.isfinite(max_age_seconds) or max_age_seconds < 0:
        _fail("INVALID_TIME", "$.max_age_seconds", "maximum age must be finite and nonnegative")
    age = (current_time - observed_time).total_seconds()
    if age > max_age_seconds or age < -5:
        _fail("STALE_CAPTURE", "$.observed_at", "capture is stale or from the future")
    expected_book = _external(expected_book, "$.expected_book")
    book_raw = _mapping(capture.get("book"), "$.book")
    if "code" in book_raw:
        book_raw = _mapping(_data(book_raw, "$.book"), "$.book.data")
    if str(book_raw.get("id")) != expected_book:
        _fail("TARGET_MISMATCH", "$.book.id", "book response does not match the authorized target")
    metadata = _mapping(_data(capture.get("source_metadata"), "$.source_metadata"), "$.source_metadata.data")
    if str(metadata.get("file_id")) != expected_book:
        _fail("TARGET_MISMATCH", "$.source_metadata.data.file_id", "source metadata belongs to a different book")
    count = _integer(metadata.get("total_pages"), "$.source_metadata.data.total_pages", 1)
    if "page_count" in book_raw and _integer(book_raw["page_count"], "$.book.page_count", 1) != count:
        _fail("INCOMPLETE_RESPONSE", "$.book.page_count", "book and source metadata page counts disagree")
    book = {"id": expected_book, "page_count": count}
    for key in ("title", "status", "updated_at", "processing_status", "reviewed_at", "delivered_at", "delivery_submitted_at"):
        if key in book_raw:
            book[key] = None if book_raw[key] is None else _text(book_raw[key], "$.book." + key)
    if "question_count" in book_raw:
        book["question_count"] = _integer(book_raw["question_count"], "$.book.question_count")
    directories, questions = parse_directory(capture.get("directory"), expected_book)
    if not questions:
        _fail("SOURCE_EMPTY_SCOPE", "$.directory", "source scope has no observed question identities")
    annotations = _annotations(capture.get("annotations"), questions, expected_book)
    if not isinstance(expected_pages, (tuple, list)):
        _fail("INVALID_SCOPE", "$.expected_pages", "requested pages must be a list or tuple")
    wanted = [_integer(v, "$.expected_pages", 1) for v in expected_pages]
    if not wanted or len(wanted) != len(set(wanted)):
        _fail("INVALID_SCOPE", "$.expected_pages", "requested page scope must be nonempty and unique")
    root = Path(root).resolve()
    pages, seen = [], set()
    for i, item in enumerate(_list(capture.get("pages"), "$.pages")):
        loc = "$.pages[{}]".format(i)
        item = _mapping(item, loc)
        viewer_page = _integer(item.get("viewer_page"), loc + ".viewer_page", 1)
        if viewer_page not in wanted or viewer_page in seen:
            _fail("INVALID_SCOPE", loc + ".viewer_page", "page lies outside the exact requested scope or repeats")
        seen.add(viewer_page)
        data = _mapping(_data(item.get("source_response"), loc + ".source_response"), loc + ".source_response.data")
        if str(data.get("file_id")) != expected_book:
            _fail("TARGET_MISMATCH", loc, "page resource response belongs to a different book")
        response_pages = _list(data.get("pages"), loc + ".source_response.data.pages")
        if len(response_pages) != 1:
            _fail("PAGE_MAPPING_UNCERTAIN", loc, "bounded page response must identify exactly one original")
        page = _mapping(response_pages[0], loc + ".source_response.data.pages[0]")
        source_index = _integer(page.get("page_index"), loc + ".source_index")
        if source_index >= count or viewer_page > count:
            _fail("PAGE_MAPPING_UNCERTAIN", loc, "page identity exceeds metadata page count")
        # The collector strips the URL and binds this safe identifier to its UI observation.
        if page.get("image") != "original:viewer-{}".format(viewer_page):
            _fail("PAGE_MAPPING_UNCERTAIN", loc, "source resource lacks its sanitized viewer identity")
        mapping = _mapping(item.get("mapping_evidence"), loc + ".mapping_evidence")
        if (mapping.get("original_loaded") is not True
                or _integer(mapping.get("viewer_page"), loc + ".mapping_evidence.viewer_page", 1) != viewer_page
                or _integer(mapping.get("source_index"), loc + ".mapping_evidence.source_index") != source_index):
            _fail("PAGE_MAPPING_UNCERTAIN", loc + ".mapping_evidence", "loaded original and viewer/source evidence disagree")
        if isinstance(item.get("download_status"), bool) or item.get("download_status") != 200:
            _fail("RESOURCE_FAILURE", loc + ".download_status", "original download was not successful")
        relative, resolved = _asset_path(root, item.get("asset_path"), loc + ".asset_path")
        inventory = _image_inventory(resolved, loc + ".asset_path")
        for key in ("width", "height", "sha256"):
            if key in item and item[key] != inventory[key]:
                _fail("RESOURCE_MISMATCH", loc + "." + key, "declared asset identity differs from original bytes")
        pages.append({"viewer_page": viewer_page, "source_index": source_index,
                      "asset_id": "asset-a04-book-{}-viewer-{}".format(expected_book, viewer_page),
                      "path": relative, **inventory,
                      "mapping_evidence": {"viewer_page": viewer_page, "source_index": source_index,
                                           "original_loaded": True}})
    if set(wanted) != seen:
        _fail("SOURCE_MISSING", "$.pages", "one or more requested original pages are absent")
    if len({p["path"] for p in pages}) != len(pages):
        _fail("RESOURCE_MISMATCH", "$.pages", "different page identities share the same local asset path")
    pages.sort(key=lambda p: p["viewer_page"])
    fields = dict(book_id=expected_book, observed_at=observed_at, evidence_mode=mode, provenance=provenance,
                  book=book, metadata_page_count=count, directories=directories, questions=questions,
                  pages=pages, annotations=annotations)
    return ParsedCapture(**fields, observed_hash=content_digest(fields))


def _history(parsed):
    return {"capture_version": "a04.readonly.v1", **parsed.safe_data(),
            "scope_statement": "Only listed originals acquired; directory/annotation metadata does not prove page content coverage.",
            "page_directory_statement": "Page mappings use an adapter source-scope container; no chapter membership was inferred.",
            "geometry_status": "NOT_PERFORMED_BY_SOURCE"}


def build_source(parsed, root, run_id="run-a04", scope_id="scope-a04-readonly",
                 artifact_id="source-a04", revision=1, history_path="evidence/source-capture.json"):
    """Create an immutable history resource and a sealed public SourceBundle.

    Build does not create a policy or assert content completeness. A caller must
    include source_evidence() when validating its complete C01 exchange bundle.
    Reusing an existing identical history is harmless; changed bytes fail closed.
    """
    if not isinstance(parsed, ParsedCapture):
        _fail("INVALID_INPUT", "$", "build_source requires a parsed capture")
    parsed.assert_integrity()
    root = Path(root).resolve()
    # Recheck at publication: the time between parse and build must not bind a
    # changed original to an old byte digest, even before whole-bundle validation.
    for i, page in enumerate(parsed.pages):
        _, asset = _asset_path(root, page["path"], "$.pages[{}].path".format(i))
        inventory = _image_inventory(asset, "$.pages[{}].path".format(i))
        if any(inventory[key] != page[key] for key in ("sha256", "width", "height", "media_type")):
            _fail("RESOURCE_MISMATCH", "$.pages[{}]".format(i), "original bytes changed after capture parsing")
    relative, destination = _asset_path(root, history_path, "$.history_path")
    encoded = (json.dumps(_history(parsed), ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("xb") as handle:
            handle.write(encoded)
    except FileExistsError:
        if destination.read_bytes() != encoded:
            _fail("IMMUTABLE_RESOURCE", "$.history_path", "existing history has different bytes")
    except OSError:
        _fail("RESOURCE_FAILURE", "$.history_path", "source history could not be persisted")
    container_id = _identity("directory", parsed.book_id, "a04-source-scope-container")
    directories = [{"directory_id": container_id, "parent_id": None,
                    "label": "Usense bounded original-resource scope (adapter container)"}]
    directories.extend({"directory_id": d["directory_id"], "parent_id": d["parent_id"] or container_id,
                        "label": d["label"]} for d in parsed.directories)
    resource = {"path": relative, "sha256": hashlib.sha256(encoded).hexdigest(), "media_type": "application/json"}
    payload = {"assets": [{k: p[k] for k in ("asset_id", "path", "sha256", "media_type", "width", "height")}
                          | {"source_label": "viewer page {} / source index {}".format(p["viewer_page"], p["source_index"]),
                             "provenance": "SYNTHETIC" if parsed.evidence_mode == "SYNTHETIC" else "ORIGINAL"}
                          for p in parsed.pages],
               "directories": directories,
               "pages_expected": [p["asset_id"] for p in parsed.pages],
               "pages_acquired": [p["asset_id"] for p in parsed.pages],
               "external_page_mappings": [{"asset_id": p["asset_id"], "directory_id": container_id,
                                            "external_page": "viewer:{};source_index:{}".format(p["viewer_page"], p["source_index"]),
                                            "mapping_status": "CONFIRMED", "evidence_refs": ["proof-a04-source"]}
                                           for p in parsed.pages],
               "history": [{"resource": resource, "quality": "UNVERIFIED",
                            "reason": "Bounded source capture and raw platform box evidence; no content or geometry acceptance."}],
               "scope_manifest": [q["question_id"] for q in parsed.questions],
               "scope_manifest_basis": "Observed directory question-node identities; full metadata tree only, not content coverage of unacquired pages.",
               "metadata_page_count": parsed.metadata_page_count}
    envelope = {"schema_version": SCHEMA_VERSION, "artifact_id": artifact_id, "revision": revision,
                "kind": "SourceBundle", "run_id": run_id, "book_id": parsed.book_id, "scope_id": scope_id,
                "input_refs": [], "producer": {"module": "source.usense", "implementation_version": "a04.1",
                  "config_version": "a04.readonly.v1", "policy_versions": [], "model_version": None,
                  "prompt_version": None, "evidence_mode": parsed.evidence_mode},
                "created_at": parsed.observed_at, "payload": payload}
    return SourceBundle.model_validate(seal_artifact(envelope))


def source_evidence(parsed, root, history_path="evidence/source-capture.json"):
    """EvidenceRecord dictionary for the immutable history produced by build_source."""
    parsed.assert_integrity()
    relative, destination = _asset_path(Path(root).resolve(), history_path, "$.history_path")
    try:
        blob = destination.read_bytes()
    except OSError:
        _fail("RESOURCE_MISSING", "$.history_path", "build_source history is unavailable")
    expected = (json.dumps(_history(parsed), ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if blob != expected:
        _fail("RESOURCE_MISMATCH", "$.history_path", "source evidence differs from parsed capture")
    return {"evidence_id": "proof-a04-source",
            "resource": {"path": relative, "sha256": hashlib.sha256(blob).hexdigest(), "media_type": "application/json"},
            "description": "Bounded original-image inventory and separate viewer/source identities; {} capture.".format(parsed.provenance),
            "mode": parsed.evidence_mode}
