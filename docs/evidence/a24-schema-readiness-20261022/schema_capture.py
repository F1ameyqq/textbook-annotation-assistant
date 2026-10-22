"""Fail-closed reader for the four unqualified current-schema captures.

This module verifies bytes and provenance boundaries only. It deliberately does
not infer field paths, build a wire profile, create proofs, or authorize writes.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path

from annotation.quality.live_pilot import require
from annotation.runtime.storage.common import digest


CAPTURES = (
    ("book", "/qieti/api/claim_book/books", (), "book-snapshot.bin"),
    ("directory", "/qieti/api/annotate_ocr/directory/get", ("file_id",), "directory-snapshot.bin"),
    ("frames", "/qieti/api/annotate_pic/get_manual_annotations_unified/46007447", (), "frames-snapshot.bin"),
    ("export", "/qieti/api/annotate_ocr/export-paper-questions/46007447", (), "export-snapshot.bin"),
)
REPRESENTATION = "UTF8_REENCODED_RESPONSE_TEXT"
REPARSE_POINT = 0x400


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _regular_non_reparse(path):
    require(path.is_file() and not path.is_symlink(), "CURRENT_SCHEMA_CAPTURE_PATH")
    info = path.lstat()
    require(not (getattr(info, "st_file_attributes", 0) & REPARSE_POINT), "CURRENT_SCHEMA_CAPTURE_PATH")


@dataclass(frozen=True)
class CurrentSchemaCapture:
    root: Path
    manifest: tuple
    texts: tuple

    def text(self, slot):
        matches = [text for name, text in self.texts if name == slot]
        require(len(matches) == 1, "CURRENT_SCHEMA_CAPTURE_SLOT")
        return matches[0]

    def public_summary(self):
        return {
            "schema": "A24CurrentSchemaCaptureSet/v1",
            "status": "CAPTURE_BYTES_VERIFIED_SCHEMA_UNBOUND",
            "write_allowed": False,
            "successors": "NOT_RUN",
            "members": [dict(item) for item in self.manifest],
            "capture_set_sha256": digest(list(self.manifest)),
            "schema_profile": None,
            "qualification": "NOT_RUN",
        }


def load_current_schema_capture(result, output_root):
    """Load exactly four private snapshots without promoting their schema."""
    require(isinstance(result, dict) and set(result) ==
            {"status", "write_allowed", "successors", "reads"} and
            result["status"] == "CURRENT_SCHEMA_UNBOUND" and
            result["write_allowed"] is False and result["successors"] == "NOT_RUN" and
            isinstance(result["reads"], list) and len(result["reads"]) == len(CAPTURES),
            "CURRENT_SCHEMA_CAPTURE_RESULT")
    root = Path(output_root).resolve()
    private = root / "private"
    require(root.is_dir() and private.is_dir() and not root.is_symlink() and not private.is_symlink(),
            "CURRENT_SCHEMA_CAPTURE_PATH")
    for path in (root, private):
        require(not (getattr(path.lstat(), "st_file_attributes", 0) & REPARSE_POINT),
                "CURRENT_SCHEMA_CAPTURE_PATH")

    manifest, texts = [], []
    for read, (slot, route, query_keys, filename) in zip(result["reads"], CAPTURES):
        expected_fields = {"slot", "path_template", "query_keys", "http_status", "bytes", "sha256",
                           "capture_representation", "controlled_raw_ref"}
        require(isinstance(read, dict) and set(read) == expected_fields and
                read["slot"] == slot and read["path_template"] == route and
                read["query_keys"] == list(query_keys) and read["http_status"] == 200 and
                type(read["bytes"]) is int and read["bytes"] > 0 and
                read["capture_representation"] == REPRESENTATION,
                "CURRENT_SCHEMA_CAPTURE_RESULT")
        reference = read["controlled_raw_ref"]
        require(isinstance(reference, dict) and set(reference) ==
                {"path", "sha256", "bytes", "capture_representation"} and
                reference["sha256"] == read["sha256"] and reference["bytes"] == read["bytes"] and
                reference["capture_representation"] == REPRESENTATION,
                "CURRENT_SCHEMA_CAPTURE_REF")
        expected = (private / filename).resolve()
        actual = Path(reference["path"]).resolve()
        require(actual == expected and private in actual.parents, "CURRENT_SCHEMA_CAPTURE_PATH")
        _regular_non_reparse(actual)
        raw = actual.read_bytes()
        require(len(raw) == read["bytes"] and _sha(raw) == read["sha256"],
                "CURRENT_SCHEMA_CAPTURE_BYTES")
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            require(False, "CURRENT_SCHEMA_CAPTURE_ENCODING", str(type(exc).__name__))
        manifest.append({"slot": slot, "path_template": route, "query_keys": list(query_keys),
                         "bytes": len(raw), "sha256": _sha(raw),
                         "capture_representation": REPRESENTATION})
        texts.append((slot, text))
    return CurrentSchemaCapture(root, tuple(manifest), tuple(texts))
