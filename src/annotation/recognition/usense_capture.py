"""Offline capture readers for OCR, including merged independent readbacks.

This module never imports a browser, writer, OCR engine, or network client.
"""
import hashlib
import json
import math
from pathlib import Path
import re


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _finite_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("Finite JSON number required")
    return value


def _reject_constant(text):
    raise ValueError("Finite JSON number required")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      object_pairs_hook=_unique_object, parse_float=_finite_float,
                      parse_constant=_reject_constant)


def file_ref(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def checked_ref(reference):
    actual = file_ref(reference["path"])
    if actual != reference:
        raise ValueError("File reference changed: " + actual["path"])
    return Path(actual["path"])


class CaptureReader:
    """Check HTTP/entity-byte evidence before exposing a saved response.

    A merged readback is accepted only with its original per-request manifest,
    original run summary, and identical original response bytes. A new summary
    generated from the merged files is deliberately insufficient.
    """

    def __init__(self, directory, readback_manifest=None):
        self.directory = Path(directory)
        self.manifest = Path(readback_manifest) if readback_manifest else None
        self.records = {}
        if self.manifest:
            rows = read_json(self.manifest)
            if not isinstance(rows, list) or not rows:
                raise ValueError("Nonempty original readback manifest required")
            for row in rows:
                name, run = row["name"], row["run_id"]
                if (not re.fullmatch(r"[A-Za-z0-9_]+", name)
                        or not re.fullmatch(r"[A-Za-z0-9_-]+", run)):
                    raise ValueError("Unsafe readback identity")
                original_root = self.manifest.parent / run
                declaration = read_json(original_root / "capture-summary.json")["captures"][name]
                if declaration["sha256"] != row["sha256"]:
                    raise ValueError("Original summary and merge manifest disagree")
                self.records.setdefault(name, []).append((declaration, original_root / (name + ".json")))
        else:
            self.records = {name: [(record, None)] for name, record in
                            read_json(self.directory / "capture-summary.json")["captures"].items()}

    def get(self, name):
        file = self.directory / (name + ".json")
        actual = file_ref(file)
        for declaration, original in self.records[name]:
            if (declaration["status"] != 200 or actual["bytes"] != declaration["bytes"]
                    or actual["sha256"] != declaration["sha256"]):
                raise ValueError("Capture does not match original HTTP summary: " + name)
            if original is not None and original.read_bytes() != file.read_bytes():
                raise ValueError("Merged and original response differ: " + name)
        value = read_json(file)
        if type(value.get("code")) is not int or value["code"] != 0:
            raise ValueError("Unsuccessful captured business response: " + name)
        return value["data"]

    def evidence_ref(self):
        return file_ref(self.manifest or self.directory / "capture-summary.json")
