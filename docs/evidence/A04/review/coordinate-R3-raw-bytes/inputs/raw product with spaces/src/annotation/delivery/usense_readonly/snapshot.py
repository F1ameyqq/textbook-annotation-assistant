"""Convert a sanitized A04 capture into the C01 platform business view.

The source parser owns platform response parsing. This view never transforms or
repairs coordinates: only acquired original-image bindings may carry a frame.
The complete capture still determines the observed hash, including omitted
frames. Task wording ``UNVERIFIED`` is represented by C01's ``UNKNOWN`` enum.
"""
import hashlib
import json
import math
from collections import Counter
from pathlib import Path, PurePosixPath, PureWindowsPath

from annotation.contracts import (
    SCHEMA_VERSION, PlatformSnapshot, SourceBundle, artifact_ref, content_digest, seal_artifact,
)
from annotation.source.usense import ParsedCapture


CAPABILITIES = (
    "persistent_draft", "frame_readback", "content_readback", "ocr_before_submit",
    "resume_after_restart", "multi_session", "same_session_handoff", "frame_update",
)


class SnapshotError(ValueError):
    """A fixed, sanitized error with a location into the normalized input."""

    def __init__(self, code, path):
        self.code, self.path = code, path
        super().__init__("{}: {}".format(code, path))


def _fail(code, path):
    raise SnapshotError(code, path)


def _json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def _destination(root, relative):
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or ":" in relative or PurePosixPath(relative).is_absolute()
            or PureWindowsPath(relative).drive
            or any(part in ("", ".", "..") for part in relative.split("/"))):
        _fail("INVALID_EVIDENCE_PATH", "summary_path")
    base = Path(root).resolve()
    destination = (base / relative).resolve()
    try:
        destination.relative_to(base)
    except ValueError:
        _fail("INVALID_EVIDENCE_PATH", "summary_path")
    return destination


def _identity(value, path):
    if not isinstance(value, str) or not value:
        _fail("INVALID_ID", path)
    return value


def _view(parsed, source):
    """Recheck closure before filtering; frozen dataclasses can contain lists."""
    if not isinstance(parsed, ParsedCapture):
        _fail("INVALID_INPUT", "capture")
    source = SourceBundle.model_validate(source.model_dump(mode="json")
                                         if isinstance(source, SourceBundle) else source)
    if source.book_id != parsed.book_id or source.payload is None:
        _fail("WRONG_BOOK", "source.book_id")
    if source.producer.evidence_mode != parsed.evidence_mode:
        _fail("EVIDENCE_MODE_CONFLICT", "source.producer.evidence_mode")
    if (parsed.evidence_mode not in ("SYNTHETIC", "OBSERVED")
            or parsed.provenance not in ("SYNTHETIC", "LIVE", "HISTORICAL")
            or (parsed.evidence_mode == "SYNTHETIC") != (parsed.provenance == "SYNTHETIC")):
        _fail("PROVENANCE_CONFLICT", "capture.provenance")
    if parsed.book.get("id") != parsed.book_id:
        _fail("WRONG_BOOK", "book.id")
    directories, directory_ids = [], set()
    for i, row in enumerate(parsed.directories):
        directory_id = _identity(row.get("platform_directory_id"),
                                 "directories[{}].platform_directory_id".format(i))
        if directory_id in directory_ids:
            _fail("DUPLICATE_ID", "directories[{}]".format(i))
        directories.append(directory_id)
        directory_ids.add(directory_id)
    questions, question_keys, question_ids = [], {}, set()
    for i, row in enumerate(parsed.questions):
        path = "questions[{}]".format(i)
        question_id = _identity(row.get("platform_question_id"), path + ".platform_question_id")
        if question_id in question_ids:
            _fail("DUPLICATE_ID", path + ".platform_question_id")
        if row.get("directory_id") not in directory_ids:
            _fail("MISSING_REFERENCE", path + ".directory_id")
        order = row.get("platform_order")
        if type(order) is not int or order < 0:
            _fail("INVALID_ORDER", path + ".platform_order")
        key = (row["directory_id"], order)
        if key in question_keys:
            _fail("AMBIGUOUS_QUESTION", path + ".platform_order")
        question_ids.add(question_id)
        question_keys[key] = question_id
        questions.append({"platform_question_id": question_id,
                          "directory_id": row["directory_id"], "platform_order": order})
    assets = {asset.asset_id: asset for asset in source.payload.assets}
    acquired = set(source.payload.pages_acquired)
    page_assets = {}
    for i, page in enumerate(parsed.pages):
        path = "pages[{}]".format(i)
        viewer_page = page.get("viewer_page")
        if type(viewer_page) is not int or viewer_page <= 0 or viewer_page in page_assets:
            _fail("INVALID_PAGE_MAPPING", path + ".viewer_page")
        asset = assets.get(page.get("asset_id"))
        if asset is None or asset.asset_id not in acquired:
            _fail("MISSING_IMAGE_BINDING", path + ".asset_id")
        if (asset.sha256, asset.width, asset.height, asset.path) != (
                page.get("sha256"), page.get("width"), page.get("height"), page.get("path")):
            _fail("IMAGE_BINDING_CONFLICT", path)
        page_assets[viewer_page] = asset
    if set(asset.asset_id for asset in page_assets.values()) != acquired:
        _fail("MISSING_IMAGE_BINDING", "pages")
    frames, frame_ids, role_counts, page_counts = [], set(), Counter(), Counter()
    for i, row in enumerate(parsed.annotations):
        path = "annotations[{}]".format(i)
        frame_id = _identity(row.get("platform_frame_id"), path + ".platform_frame_id")
        if frame_id in frame_ids:
            _fail("DUPLICATE_ID", path + ".platform_frame_id")
        frame_ids.add(frame_id)
        question_id = row.get("platform_question_id")
        # Check every row, even frames on pages outside the acquired originals.
        if question_id not in question_ids:
            _fail("MISSING_REFERENCE", path + ".platform_question_id")
        if question_keys.get((row.get("directory_id"), row.get("platform_order"))) != question_id:
            _fail("QUESTION_REFERENCE_CONFLICT", path + ".platform_question_id")
        role = row.get("platform_role")
        if role not in ("Q", "W", "A", "E"):
            _fail("INVALID_FRAME_ROLE", path + ".platform_role")
        bbox = row.get("bbox")
        if (not isinstance(bbox, list) or len(bbox) != 4
                or any(type(value) not in (int, float) or not math.isfinite(value) for value in bbox)
                or not (bbox[0] < bbox[2] and bbox[1] < bbox[3])):
            _fail("INVALID_BBOX", path + ".bbox")
        viewer_page = row.get("viewer_page")
        if type(viewer_page) is not int or viewer_page <= 0:
            _fail("INVALID_PAGE", path + ".viewer_page")
        role_counts[role] += 1
        page_counts[str(viewer_page)] += 1
        asset = page_assets.get(viewer_page)
        if asset is not None:
            # C01 OriginalBox validates acquired-image bounds; no clipping.
            if not (0 <= bbox[0] < bbox[2] <= asset.width
                    and 0 <= bbox[1] < bbox[3] <= asset.height):
                _fail("BBOX_OUT_OF_BOUNDS", path + ".bbox")
            frames.append({
                "platform_frame_id": frame_id, "platform_question_id": question_id,
                "platform_role": role,
                "box": {"image": {"asset_id": asset.asset_id, "width": asset.width,
                                  "height": asset.height, "sha256": asset.sha256},
                        "bbox": [float(value) for value in bbox]},
            })
    for i, row in enumerate(parsed.annotations):
        if row.get("parent_frame_id") is not None and row["parent_frame_id"] not in frame_ids:
            _fail("MISSING_REFERENCE", "annotations[{}].parent_frame_id".format(i))
    state = dict(parsed.safe_data())
    state.pop("observed_hash", None)
    if parsed.observed_hash != content_digest(state):
        _fail("HASH_MISMATCH", "capture.observed_hash")
    summary = {
        "book_id": parsed.book_id, "observed_at": parsed.observed_at,
        "evidence_mode": parsed.evidence_mode, "provenance": parsed.provenance,
        "full_platform_observed_hash": parsed.observed_hash,
        "book_status": parsed.book.get("status"),
        "book_updated_at": parsed.book.get("updated_at"),
        "book_reported_question_count": parsed.book.get("question_count"),
        "metadata_page_count": parsed.metadata_page_count,
        "directory_count": len(directories), "question_node_count": len(questions),
        "full_platform_frame_count": len(parsed.annotations),
        "full_platform_frame_role_counts": dict(sorted(role_counts.items())),
        "full_platform_frame_page_counts": dict(sorted(page_counts.items())),
        "acquired_original_count": len(page_assets),
        "acquired_viewer_pages": sorted(page_assets),
        "snapshot_frame_count": len(frames),
        "omitted_frame_count_without_acquired_original": len(parsed.annotations) - len(frames),
        "frame_scope": "Only frames on acquired original-image pages are in PlatformSnapshot.frames.",
        "complete_platform_frames_in_snapshot": len(frames) == len(parsed.annotations),
        "all_frame_references_checked_before_scope_filter": True,
        "directory_tree_evidence": "proof-a04-source",
        "capabilities": {name: "UNKNOWN" for name in CAPABILITIES},
        "capability_note": "Task UNVERIFIED maps to C01 UNKNOWN; no capability is promoted by a read-only export.",
        "source": artifact_ref(source),
    }
    return source, directories, questions, frames, summary


def build_snapshot(parsed, source, root, *, artifact_id="snapshot-a04-usense", revision=1,
                   summary_path="evidence/platform-summary.json",
                   evidence_id="proof-a04-snapshot", platform_version="usense-annotateUnified-unversioned"):
    """Build a C01 snapshot and exclusively write its scoped/full-state evidence.

    Combine the returned snapshot with the source, ``source_evidence``,
    ``snapshot_evidence`` and an existing policy in ``validate_bundle``. This
    function does no browser/network work and never overwrites an evidence file.
    Historical captures keep their original observed time and provenance.
    """
    source, directories, questions, frames, summary = _view(parsed, source)
    snapshot = PlatformSnapshot.model_validate(seal_artifact({
        "schema_version": SCHEMA_VERSION, "artifact_id": artifact_id, "revision": revision,
        "kind": "PlatformSnapshot", "run_id": source.run_id, "book_id": parsed.book_id,
        "scope_id": source.scope_id, "input_refs": [artifact_ref(source)],
        "producer": {"module": "delivery.usense_readonly", "implementation_version": "a04-v1",
                     "config_version": "a04-readonly-scope-v1", "policy_versions": [],
                     "model_version": None, "prompt_version": None,
                     "evidence_mode": parsed.evidence_mode},
        "created_at": parsed.observed_at,
        "payload": {
            "target_id": parsed.book_id, "platform_version": platform_version,
            "observed_at": parsed.observed_at,
            "observed_version": str(parsed.book.get("updated_at") or "sha256:" + parsed.observed_hash),
            "observed_hash": parsed.observed_hash, "authorized_scope_id": source.scope_id,
            "directories": directories, "questions": questions, "frames": frames,
            "capabilities": [{"name": name, "status": "UNKNOWN", "platform_version": platform_version,
                              "evidence_refs": []} for name in CAPABILITIES],
            "evidence_refs": ["proof-a04-source", evidence_id],
        },
    }))
    destination = _destination(root, summary_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("xb") as handle:
            handle.write(_json_bytes(summary))
    except FileExistsError:
        _fail("EVIDENCE_EXISTS", "summary_path")
    return snapshot


def snapshot_evidence(parsed, source, root, *, summary_path="evidence/platform-summary.json",
                      evidence_id="proof-a04-snapshot"):
    """Reference exactly the bounded/full-state summary emitted by build_snapshot."""
    _, _, _, _, summary = _view(parsed, source)
    expected = _json_bytes(summary)
    try:
        actual = _destination(root, summary_path).read_bytes()
    except OSError:
        _fail("EVIDENCE_MISSING", "summary_path")
    if actual != expected:
        _fail("EVIDENCE_MISMATCH", "summary_path")
    return {
        "evidence_id": evidence_id,
        "resource": {"path": summary_path, "sha256": hashlib.sha256(actual).hexdigest(),
                     "media_type": "application/json"},
        "description": "A04 {} capture: full platform counts and state hash; acquired-original frame scope only.".format(parsed.provenance),
        "mode": parsed.evidence_mode,
    }
