"""Independent fail-closed extractor for the fixed A24 offline replay ZIP."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath


WINDOWS_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
                    *(f"lpt{i}" for i in range(1, 10))}
MAX_MEMBER = 64 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_RATIO = 1000


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def normalized_member(name: str) -> str:
    if not isinstance(name, str) or not name or "\x00" in name or "\\" in name or ":" in name:
        raise ValueError(f"unsafe ZIP member: {name!r}")
    if name.startswith(("/", "//")) or re.match(r"^[A-Za-z]:", name):
        raise ValueError(f"absolute ZIP member: {name!r}")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"unsafe ZIP member component: {name!r}")
    normalized = []
    for part in parts:
        part = unicodedata.normalize("NFC", part)
        if part.endswith((".", " ")) or part.split(".", 1)[0].casefold() in WINDOWS_RESERVED:
            raise ValueError(f"Windows-unsafe ZIP member: {name!r}")
        if any(ord(character) < 32 for character in part):
            raise ValueError(f"control character in ZIP member: {name!r}")
        normalized.append(part.casefold())
    return "/".join(normalized)


def validate_and_extract(args):
    archive = args.archive.resolve()
    target = args.target.resolve()
    if target.exists():
        raise FileExistsError(f"target already exists: {target}")
    raw_zip = archive.read_bytes()
    if len(raw_zip) != args.expected_bytes or sha256(raw_zip) != args.expected_sha256:
        raise ValueError("archive byte identity mismatch")

    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        if not infos:
            raise ValueError("empty ZIP")
        names = [item.filename for item in infos]
        if len(names) != len(set(names)):
            raise ValueError("duplicate raw ZIP member")
        normalized = [normalized_member(name) for name in names]
        if len(normalized) != len(set(normalized)):
            raise ValueError("normalized/casefold ZIP member collision")
        normalized_set = set(normalized)
        for name in normalized:
            pieces = name.split("/")
            for end in range(1, len(pieces)):
                if "/".join(pieces[:end]) in normalized_set:
                    raise ValueError("file/directory prefix collision")
        if not all(name.startswith("a24-offline-replay/") for name in names):
            raise ValueError("unexpected package root")

        total = 0
        for item in infos:
            if item.flag_bits & 1:
                raise ValueError(f"encrypted ZIP member: {item.filename}")
            if item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise ValueError(f"unsupported compression: {item.filename}")
            mode = item.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if item.is_dir() or kind not in (0, stat.S_IFREG):
                raise ValueError(f"non-regular ZIP member: {item.filename}")
            if item.file_size > MAX_MEMBER:
                raise ValueError(f"oversized ZIP member: {item.filename}")
            if item.compress_size == 0 and item.file_size or (
                    item.compress_size and item.file_size / item.compress_size > MAX_RATIO):
                raise ValueError(f"excessive compression ratio: {item.filename}")
            total += item.file_size
        if total > MAX_TOTAL:
            raise ValueError("expanded ZIP too large")
        if bundle.testzip() is not None:
            raise ValueError("ZIP CRC failure")

        root_name = "a24-offline-replay/root-manifest.json"
        root_raw = bundle.read(root_name)
        if sha256(root_raw) != args.expected_root_sha256:
            raise ValueError("root manifest identity mismatch")
        root = json.loads(root_raw, object_pairs_hook=unique_object)
        members = root.get("members")
        if root.get("schema") != "A24OfflineReplayRootManifest/v1" or not isinstance(members, list):
            raise ValueError("root manifest schema")
        declared = ["a24-offline-replay/" + item["path"] for item in members]
        if root.get("member_count") != len(members) or set(declared) != set(names) - {root_name}:
            raise ValueError("root manifest membership mismatch")
        by_name = {item.filename: item for item in infos}
        for declared_name, item in zip(declared, members):
            data = bundle.read(by_name[declared_name])
            if len(data) != item["bytes"] or sha256(data) != item["sha256"]:
                raise ValueError(f"root manifest binding mismatch: {declared_name}")

        target.mkdir()
        extracted = []
        for item in infos:
            relative = PurePosixPath(item.filename).relative_to("a24-offline-replay")
            destination = target.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            data = bundle.read(item)
            with destination.open("xb") as handle:
                handle.write(data)
            extracted.append(destination.relative_to(target).as_posix())

    return {
        "schema": "A24IndependentSafeExtraction/v1",
        "archive": str(archive),
        "archive_bytes": len(raw_zip),
        "archive_sha256": sha256(raw_zip),
        "zip_members": len(names),
        "expanded_bytes": total,
        "root_manifest_sha256": sha256(root_raw),
        "root_manifest_members": len(members),
        "target": str(target),
        "extracted_files": len(extracted),
        "status": "PASS",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--expected-bytes", type=int, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-root-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(validate_and_extract(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
