"""Verify a read-only B trial handoff ZIP without importing B's runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import PurePosixPath
import zipfile
from io import BytesIO


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def ref(value: dict) -> dict:
    return {k: value[k] for k in ("artifact_id", "revision", "content_hash")}


def check_artifact(value: dict, expected: dict | None = None) -> None:
    if value["content_hash"] != sha(canonical(value["payload"])):
        raise ValueError("artifact payload hash mismatch: " + value["artifact_id"])
    if expected is not None and ref(value) != expected:
        raise ValueError("stale or wrong artifact reference: " + value["artifact_id"])


def check_asset(asset: dict, filenames: set[str]) -> None:
    if asset["asset_id"] not in filenames:
        raise ValueError("unknown source asset: " + asset["asset_id"])


def check_bytes(data: bytes, expected_sha: str) -> None:
    if sha(data) != expected_sha:
        raise ValueError("source or receipt bytes changed")


def verify(path: str, self_test: bool = False) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate archive path")
        if any(PurePosixPath(n).is_absolute() or ".." in PurePosixPath(n).parts
               or "\\" in n for n in names):
            raise ValueError("unsafe archive path")
        manifest = json.loads(archive.read("manifest.json"))
        declared = {entry["path"]: entry for entry in manifest["files"]}
        if set(declared) != set(names) - {"manifest.json"}:
            raise ValueError("manifest does not enumerate every file")
        for name, entry in declared.items():
            data = archive.read(name)
            if len(data) != entry["bytes"] or sha(data) != entry["sha256"]:
                raise ValueError("file bytes changed: " + name)
        report = json.loads(archive.read("artifacts/pipeline-report.json"))
        check_artifact(report, manifest["report_ref"])
        if report["run_id"] != manifest["run_id"] or len(report["payload"]["stages"]) != 14:
            raise ValueError("wrong fixed run or stage count")
        if report["payload"]["pipeline_state"] != "READY" or report["payload"]["decision"] != "HOLD":
            raise ValueError("unexpected run decision")
        if manifest.get("content_status") == "MODEL_DRAFT":
            payload = report["payload"]
            if (payload["business_acceptance"] is not False
                    or payload["transcription_verified"] is not False
                    or payload["content_revision_scope"]["draft_only"] is not True
                    or payload["platform_actions"]):
                raise ValueError("draft content was promoted")
        output_names = {"evidence_ref": "evidence.json", "graph_ref": "graph.json",
                        "quality_ref": "check.json"}
        final = report["payload"]["final_outputs"]
        for key, filename in output_names.items():
            value = json.loads(archive.read("artifacts/" + filename))
            check_artifact(value, final[key])
            if value["book_id"] != manifest["book_id"]:
                raise ValueError("book identity mismatch")
        for stage in report["payload"]["stages"]:
            descriptor = stage["output"]
            name = descriptor["path"]
            if name != "objects/" + descriptor["sha256"] + ".json":
                raise ValueError("bad stage object path")
            data = archive.read(name)
            if sha(data) != descriptor["sha256"]:
                raise ValueError("stage bytes changed")
            wrapper = json.loads(data)
            check_artifact(wrapper, descriptor["artifact_ref"])
            check_artifact(wrapper["payload"]["result"], stage["result_ref"])
            if wrapper["payload"]["stage_id"] != stage["stage_id"]:
                raise ValueError("stage identity mismatch")
            if stage["current_run_receipt"]["run_id"] != manifest["run_id"]:
                raise ValueError("stage receipt belongs to another run")
        source = report["payload"]["source_manifest"]
        known = {asset["asset_id"] for asset in source["assets"]}
        for asset in source["assets"]:
            check_asset(asset, known)
            name = "source/" + asset["path"]
            check_bytes(archive.read(name), asset["sha256"])
        adjacent = manifest["adjacent_source"]
        check_bytes(archive.read(adjacent["path"]), adjacent["sha256"])
        receipt_files = {x["sha256"]: x["path"] for x in manifest["receipt_files"]}
        all_receipts = set()

        def collect_receipts(value):
            if isinstance(value, dict):
                if "file_sha256" in value:
                    all_receipts.add(value["file_sha256"])
                for nested in value.values():
                    collect_receipts(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect_receipts(nested)

        receipts = report["payload"]["input_receipts"]
        collect_receipts(receipts)
        if receipt_files.keys() != all_receipts:
            raise ValueError("input receipt closure mismatch")
        for expected_sha, name in receipt_files.items():
            check_bytes(archive.read(name), expected_sha)
        inline = receipts["inline"]
        inline_package = json.loads(archive.read("inputs/inline-package.json"))
        if (inline_package["artifact_id"] != inline["package"]["reference"]["artifact_id"]
                or sha(canonical(inline_package)) != inline["package"]["reference"]["content_hash"]):
            raise ValueError("inline package reference mismatch")
        with zipfile.ZipFile(BytesIO(archive.read("inputs/inline-observed.zip"))) as inner:
            if not set(inline["members"]).issubset(inner.namelist()):
                raise ValueError("inline member list changed")
            for name, receipt in inline["members"].items():
                data = inner.read(name)
                if len(data) != receipt["bytes"]:
                    raise ValueError("inline member size changed")
                check_bytes(data, receipt["sha256"])
        if self_test:
            bad = dict(final["graph_ref"], content_hash="0" * 64)
            graph = json.loads(archive.read("artifacts/graph.json"))
            try:
                check_artifact(graph, bad)
            except ValueError:
                pass
            else:
                raise AssertionError("stale reference was accepted")
            try:
                check_asset({"asset_id": "unknown-asset"}, known)
            except ValueError:
                pass
            else:
                raise AssertionError("unknown asset was accepted")
            try:
                check_bytes(archive.read(adjacent["path"]) + b"corrupt", adjacent["sha256"])
            except ValueError:
                pass
            else:
                raise AssertionError("corrupted resource was accepted")
        return {"run_id": manifest["run_id"], "decision": "HOLD",
                "stages": 14, "files": len(declared), "self_test": self_test}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.self_test), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
