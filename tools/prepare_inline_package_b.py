"""Verify a saved inline-observation ZIP and prepare a fresh local package.

This tool copies saved execution evidence byte for byte. It never initializes
models, edits a journal, or manufactures a CPU execution receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import sys
import unicodedata
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"tools")]
from run_inline_math_b import local_path

_HASH = re.compile(r"^[0-9a-f]{64}$")


def _json(raw):
    def invalid(value): raise ValueError("nonfinite JSON constant: "+value)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError("duplicate JSON key: "+str(key))
            result[key] = value
        return result
    return json.loads(raw.decode("utf-8"), parse_constant=invalid, object_pairs_hook=unique)


def _sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _portable(name):
    if (not isinstance(name, str) or not name or "\\" in name or any(ord(c) < 32 or c in ':*?<>|"' for c in name)
            or PurePosixPath(name).is_absolute() or PureWindowsPath(name).drive
            or PurePosixPath(name).as_posix() != name or unicodedata.normalize("NFC", name) != name):
        raise ValueError("nonportable or absolute bundle member: "+repr(name))
    for part in name.split("/"):
        if part in {"", ".", ".."} or part.endswith((" ", ".")):
            raise ValueError("bundle member contains parent traversal or ambiguous components")
        if part.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *("COM"+str(i) for i in range(1, 10)), *("LPT"+str(i) for i in range(1, 10))}:
            raise ValueError("bundle member contains a reserved device name")
    return name


def _member_sha(archive, info):
    total, digest = 0, hashlib.sha256()
    with archive.open(info) as stream:
        while True:
            chunk = stream.read(1024*1024)
            if not chunk: break
            total += len(chunk)
            digest.update(chunk)
    return total, digest.hexdigest()


def verify_inline_bundle(bundle_path, manifest_path):
    """Verify the complete external/internal manifests and every ZIP member."""
    bundle_path, manifest_path = Path(local_path(bundle_path)), Path(local_path(manifest_path))
    external_bytes = manifest_path.read_bytes()
    external = _json(external_bytes)
    if (not isinstance(external, dict) or external.get("schema_version") != "b-inline-observed-bundle-trial/0.1"
            or not isinstance(external.get("members"), dict) or not external["members"]
            or not isinstance(external.get("archive"), dict) or set(external["archive"]) != {"path", "sha256", "bytes"}
            or not _HASH.fullmatch(str(external.get("internal_manifest_sha256", "")))):
        raise ValueError("invalid external inline bundle manifest")
    if (external.get("decision") != "HOLD" or external.get("business_acceptance") is not False
            or external.get("human_gold") is not False):
        raise ValueError("bundle must retain HOLD and unverified development evidence status")
    descriptor = external["archive"]
    _portable(descriptor["path"])
    if (type(descriptor["bytes"]) is not int or descriptor["bytes"] < 0 or not _HASH.fullmatch(str(descriptor["sha256"]))
            or bundle_path.stat().st_size != descriptor["bytes"] or _sha(bundle_path) != descriptor["sha256"]):
        raise ValueError("inline bundle archive SHA or byte count mismatch")
    members = external["members"]
    for name, item in members.items():
        _portable(name)
        if name == "MANIFEST.json" or not isinstance(item, dict) or set(item) != {"sha256", "bytes"}:
            raise ValueError("invalid member descriptor or reserved internal manifest name")
        if type(item["bytes"]) is not int or item["bytes"] < 0 or not _HASH.fullmatch(str(item["sha256"])):
            raise ValueError("invalid member SHA or byte count")
    with zipfile.ZipFile(bundle_path) as archive:
        names, normalized = [], set()
        for info in archive.infolist():
            name = _portable(info.filename)
            if info.orig_filename != name or name.casefold() in normalized:
                raise ValueError("duplicate or ambiguous ZIP member name")
            normalized.add(name.casefold())
            mode = info.external_attr >> 16
            if info.is_dir() or info.flag_bits & 1 or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) and not stat.S_ISREG(mode)):
                raise ValueError("only unencrypted regular ZIP files are supported")
            names.append(name)
        if set(names) != set(members)|{"MANIFEST.json"}:
            raise ValueError("ZIP has missing or extra members")
        internal_raw = archive.read("MANIFEST.json")
        if hashlib.sha256(internal_raw).hexdigest() != external["internal_manifest_sha256"]:
            raise ValueError("internal manifest SHA mismatch")
        internal = _json(internal_raw)
        if internal != {k: v for k, v in external.items() if k not in {"archive", "internal_manifest_sha256"}}:
            raise ValueError("internal and external manifests disagree")
        for name, item in members.items():
            info = archive.getinfo(name)
            if info.file_size != item["bytes"] or _member_sha(archive, info) != (item["bytes"], item["sha256"]):
                raise ValueError("bundle member SHA or byte count mismatch: "+name)
    return {"manifest": external, "manifest_sha256": hashlib.sha256(external_bytes).hexdigest(),
            "archive_sha256": descriptor["sha256"], "member_count": len(members)}


def _extract_verified(bundle_path, out, verified):
    """Publish only into a fresh directory, never use ZipFile.extractall."""
    out = Path(out)
    if out.exists() or out.is_symlink(): raise ValueError("--out must be a fresh directory")
    out.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(bundle_path) as archive:
        for info in archive.infolist():
            target = out/info.filename
            if not target.resolve().is_relative_to(out.resolve()): raise ValueError("bundle extraction escapes output root")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("xb") as destination:
                while True:
                    chunk = source.read(1024*1024)
                    if not chunk: break
                    destination.write(chunk)
            expected = ({"sha256": verified["manifest"]["internal_manifest_sha256"], "bytes": info.file_size}
                        if info.filename == "MANIFEST.json" else verified["manifest"]["members"][info.filename])
            if target.stat().st_size != expected["bytes"] or _sha(target) != expected["sha256"]:
                raise ValueError("extracted bundle member changed")


def _artifact(value, schemas, kind):
    from annotation.recognition.baseline import digest
    if (not isinstance(value, dict) or value.get("schema_version") not in schemas or value.get("kind") != kind
            or not isinstance(value.get("payload"), dict) or value.get("content_hash") != digest(value["payload"])
            or type(value.get("revision")) is not int or value["revision"] < 1
            or not isinstance(value.get("artifact_id"), str) or not value["artifact_id"]):
        raise ValueError("saved document artifact schema, reference or payload hash is invalid")
    if value["payload"].get("business_acceptance", False) is not False or value["payload"].get("transcription_verified", False) is not False:
        raise ValueError("saved evidence cannot claim transcription or business acceptance")
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def _package_documents(bundle_path, verified, formula_run):
    roles = {"evidence": "evidence.json", "rows": "rows.json", "ocr_observations": "observations.json",
             "formula_observations": "formula-observed-trials/"+formula_run+"-observations.json",
             "formula_report": "formula-observed-trials/"+formula_run+"-report.json"}
    members = verified["manifest"]["members"]
    if any(path not in members for path in roles.values()): raise ValueError("selected saved formula run or required document is missing")
    if "formula/inline-formula.sqlite3" not in members: raise ValueError("saved formula journal is missing")
    with zipfile.ZipFile(bundle_path) as archive:
        docs = {role: _json(archive.read(path)) for role, path in roles.items()}
    e, rows, ordinary, formulas, report = (docs[name] for name in roles)
    refs = {"evidence": _artifact(e, {"b-evidence-trial/0.2", "b-evidence-trial/0.3"}, "EvidenceBundleTrial"), "rows": None,
        "ocr_observations": _artifact(ordinary, {"b-inline-ocr-observation-trial/0.1"}, "InlineOCRObservationTrial"),
        "formula_observations": _artifact(formulas, {"b-inline-formula-observation-trial/0.1"}, "InlineFormulaObservationTrial"),
        "formula_report": _artifact(report, {"b-inline-formula-run-trial/0.1"}, "InlineFormulaRunTrial")}
    if (not isinstance(rows, list) or not rows or any(not isinstance(x, str) or not x for x in rows) or len(set(rows)) != len(rows)
            or rows != verified["manifest"].get("requested_line_ids") or rows != ordinary["payload"].get("requested_line_ids")
            or rows != formulas["payload"].get("requested_line_ids")):
        raise ValueError("saved ordered row scopes disagree")
    source = ordinary["payload"]["source"]
    pages = [p for p in e["payload"]["pages"] if p["asset_id"] == source["asset_id"]]
    if (len(pages) != 1 or pages[0]["source"] != source["asset"]
            or source["original_sha256"] != source["asset"]["sha256"]
            or source["original_sha256"] != verified["manifest"].get("source_sha256")
            or (source["width"], source["height"]) != (source["asset"]["width"], source["asset"]["height"])):
        raise ValueError("saved source asset descriptors disagree")
    known = {line["line_id"] for line in pages[0]["ocr_lines"]}
    if not set(rows).issubset(known): raise ValueError("saved selected rows are missing from original evidence")
    if any((d["book_id"], d["scope_id"]) != (e["book_id"], e["scope_id"]) for d in (ordinary, formulas, report)):
        raise ValueError("saved document book or scope mismatch")
    layout = formulas["payload"]["layout_archive"]
    layout_ref = _artifact(layout, {"b-inline-math-layout-trial/0.1"}, "InlineMathLayoutTrial")
    if (ordinary["payload"].get("evidence_ref") != refs["evidence"]
            or layout["payload"].get("evidence_ref") != refs["evidence"]
            or layout["payload"].get("observations_archive") != ordinary
            or formulas["payload"].get("source") != source
            or formulas["payload"].get("layout_ref") != layout_ref
            or report["payload"].get("layout_ref") != layout_ref
            or report["payload"].get("result_ref") != refs["formula_observations"]):
        raise ValueError("saved formula/ordinary/evidence reference chain disagrees")
    documents = {role: {"path": path, "sha256": members[path]["sha256"], "artifact_ref": refs[role]} for role, path in roles.items()}
    included = set(roles.values()) | {path for path in members if path.startswith("formula/")}
    package = {"schema_version": "b-inline-package-trial/0.1", "book_id": e["book_id"], "scope_id": e["scope_id"],
        "asset_id": source["asset_id"], "line_ids": rows, "policy": "EXACT_SELECTED_PAGE_EQUIVALENCE_ONLY/0.1",
        "documents": documents, "journal_dir": "formula", "members": {path: members[path] for path in sorted(included)}}
    from annotation.recognition.baseline import digest
    package["artifact_id"] = "inline-package-"+digest(package)[:24]
    return package, source, report["payload"]["state"]


def prepare_inline_package(bundle_path, manifest_path, out, *, formula_run="formal-warm"):
    """Verify and extract all saved outcomes; point the package at one run."""
    choices = {"formal-warm": "formal-warm", "partial8": "formal-partial8", "formal-partial8": "formal-partial8",
               "resumed": "formal-resumed", "formal-resumed": "formal-resumed"}
    if formula_run not in choices: raise ValueError("unknown saved formula run")
    formula_run = choices[formula_run]
    bundle_path, manifest_path, out = map(lambda p: Path(local_path(p)), (bundle_path, manifest_path, out))
    if out.exists() or out.is_symlink(): raise ValueError("--out must be a fresh directory")
    verified = verify_inline_bundle(bundle_path, manifest_path)
    reserved = {"inline-package.json", "inline-package-preparation.json", "EXTERNAL-MANIFEST.json"}
    if any(name.casefold() in {x.casefold() for x in reserved} for name in verified["manifest"]["members"]):
        raise ValueError("bundle member conflicts with generated package output")
    package, source, state = _package_documents(bundle_path, verified, formula_run)
    _extract_verified(bundle_path, out, verified)
    if _sha(bundle_path) != verified["archive_sha256"] or _sha(manifest_path) != verified["manifest_sha256"]:
        raise ValueError("bundle inputs changed during extraction")
    external_raw = manifest_path.read_bytes()
    with (out/"EXTERNAL-MANIFEST.json").open("xb") as stream: stream.write(external_raw)
    encoded = (json.dumps(package, ensure_ascii=False, indent=2, allow_nan=False)+"\n").encode("utf-8")
    with (out/"inline-package.json").open("xb") as stream: stream.write(encoded)
    from annotation.recognition.baseline import digest
    summary = {"schema_version": "b-inline-package-preparation-trial/0.1", "formula_run": formula_run,
        "saved_execution_state": state, "bundle_sha256": verified["archive_sha256"], "external_manifest_sha256": verified["manifest_sha256"],
        "internal_manifest_sha256": verified["manifest"]["internal_manifest_sha256"], "extracted_files": verified["member_count"]+1,
        "package_members": len(package["members"]), "journal_files": sum(path.startswith("formula/") for path in package["members"]),
        "package": {"path": "inline-package.json", "sha256": hashlib.sha256(encoded).hexdigest(),
                    "reference": {"artifact_id": package["artifact_id"], "content_hash": digest(package)}},
        "source": {key: source[key] for key in ("asset_id", "original_sha256", "width", "height")},
        "source_image_required_for_stage_validation": True, "decision": "HOLD", "business_acceptance": False,
        "transcription_verified": False, "human_gold": False, "new_model_calls": 0, "platform_actions": [], "exit_code": 0}
    with (out/"inline-package-preparation.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "manifest", "out"): parser.add_argument("--"+name, type=local_path, required=True)
    parser.add_argument("--formula-run", default="formal-warm", choices=("formal-warm", "partial8", "formal-partial8", "resumed", "formal-resumed"))
    args = parser.parse_args(argv)
    if args.out.exists() or args.out.is_symlink(): parser.error("--out must be a fresh directory")
    try: result = prepare_inline_package(args.bundle, args.manifest, args.out, formula_run=args.formula_run)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, RuntimeError) as exc:
        result = {"schema_version": "b-inline-package-preparation-trial/0.1", "decision": "HOLD", "business_acceptance": False,
                  "new_model_calls": 0, "platform_actions": [], "error": {"type": type(exc).__name__, "message": str(exc)}, "exit_code": 1}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
