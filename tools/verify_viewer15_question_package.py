"""Independent byte, reference, and pixel verification for the fixed v4 package."""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
from pathlib import PurePosixPath
import zipfile

from PIL import Image

EXPECTED_COMMIT = "7d5c3b738a3e28b528e510d16d7cfe2640936964"
EXPECTED_PLAN_SHA = "a7a5c43eb33d2e1378d0f82dc7375603a462dba64a60adbdb06f09a3a2f4ac99"
EXPECTED_SOURCE_SHA = "7c1a4afec69a94371fa31b6111969ca3d6ec39d7d7c6b1c73764f90316a610dd"
EXPECTED_APP_HASH = "dbe20a6ce34f1cbf050a1d09a9f497f5405d53780fb298e3e72fc2b7058f02db"
EXPECTED_CHECK_HASH = "432cd7bca0582e87ed62723f90d2d01997a7dadacbaecafb1d681cb69cff6fce"
CODE_HASHES = {
    "code/src/annotation/recognition/baseline.py": "f6c84e8f997e08c7bcef2aaf685b57f472410081485f784c01717311cc1a3675",
    "code/src/annotation/recognition/question_content.py": "694963744bbb9e697f0c9b8fffe63361cddf87b708c2d74f769da9efc0c48437",
    "code/src/annotation/recognition/question_content_quality.py": "bb22eead945be2747dd1c4428ac4eb881092c9da4840ca44c0694458d44c9822",
    "code/tools/rebuild_question_content_b.py": "2fbfb28edd56a3878d265374729a28d367ebe2bee3a2143c5faf47ef587b11a6",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf8")


def digest(value) -> str:
    return sha(canonical(value))


def reference(value: dict) -> dict:
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def require_bytes(data: bytes, expected: str, description: str) -> None:
    if sha(data) != expected:
        raise ValueError(description + " SHA-256 mismatch")


def require_ref(value: dict, expected: dict, description: str) -> None:
    if value != expected:
        raise ValueError(description + " reference mismatch")


def require_fixed_plan(data: bytes) -> dict:
    require_bytes(data, EXPECTED_PLAN_SHA, "externally pinned plan")
    plan = json.loads(data)
    if plan["schema_version"] != "b-question-source-draft-trial/0.1" or plan["content_hash"] != digest(plan["payload"]):
        raise ValueError("plan payload or schema mismatch")
    return plan


def verify_nested_archive(data: bytes) -> tuple[dict, zipfile.ZipFile]:
    nested = zipfile.ZipFile(io.BytesIO(data))
    names = nested.namelist()
    if nested.testzip() is not None or len(names) != len(set(names)):
        raise ValueError("history fixture ZIP corrupt")
    manifest = json.loads(nested.read("MANIFEST.json"))
    listed = manifest.get("files", manifest)
    if set(listed) != set(names) - {"MANIFEST.json"}:
        raise ValueError("history fixture members differ")
    for name, receipt in listed.items():
        member = nested.read(name)
        if len(member) != receipt["bytes"]:
            raise ValueError("history fixture member size differs")
        require_bytes(member, receipt["sha256"], name)
    return manifest, nested


def verify(archive_path: str, self_test: bool = False) -> dict:
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if archive.testzip() is not None or len(names) != len(set(names)):
            raise ValueError("package ZIP corrupt or duplicate")
        if any(PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
               or "\\" in name for name in names):
            raise ValueError("unsafe package path")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest["code_commit"] != EXPECTED_COMMIT or manifest["plan_file_sha256"] != EXPECTED_PLAN_SHA:
            raise ValueError("fixed code or external plan anchor differs")
        entries = {entry["path"]: entry for entry in manifest["files"]}
        if len(entries) != len(manifest["files"]) or set(entries) != set(names) - {"manifest.json"}:
            raise ValueError("file manifest incomplete")
        for name, entry in entries.items():
            data = archive.read(name)
            if len(data) != entry["bytes"]:
                raise ValueError("file size differs: " + name)
            require_bytes(data, entry["sha256"], name)
        for name, expected in CODE_HASHES.items():
            require_bytes(archive.read(name), expected, name)

        source_bytes = archive.read("inputs/46007447_page_14.jpg")
        require_bytes(source_bytes, EXPECTED_SOURCE_SHA, "source image")
        source_image = Image.open(io.BytesIO(source_bytes)).convert("RGB")
        if source_image.size != (1219, 1703):
            raise ValueError("source dimensions differ")
        source = json.loads(archive.read("inputs/source.json"))
        if len(source["assets"]) != 1 or source["assets"][0]["sha256"] != EXPECTED_SOURCE_SHA:
            raise ValueError("source identity differs")
        asset = source["assets"][0]
        if (source["book_id"] != "46007447" or asset["asset_id"] != "viewer-15"
                or asset["width"] != 1219 or asset["height"] != 1703
                or asset["external_refs"]["viewer_page"] != 15
                or asset["external_refs"]["printed_page"] != 7
                or asset["external_refs"]["observed_browser_asset_id"] != "5e95d184d28da244"):
            raise ValueError("source page mapping differs")
        evidence = json.loads(archive.read("inputs/evidence.json"))
        graph = json.loads(archive.read("inputs/graph.json"))
        plan = require_fixed_plan(archive.read("inputs/plan.json"))
        for label, artifact in (("evidence", evidence), ("graph", graph)):
            if artifact["content_hash"] != digest(artifact["payload"]):
                raise ValueError(label + " payload changed")
        if (plan["payload"]["source_sha256"] != EXPECTED_SOURCE_SHA
                or plan["payload"]["evidence_artifact_sha256"] != digest(evidence)
                or plan["payload"]["graph_artifact_sha256"] != digest(graph)):
            raise ValueError("base artifact or source binding differs")
        require_ref(plan["payload"]["evidence_ref"], reference(evidence), "plan evidence")
        require_ref(plan["payload"]["graph_ref"], reference(graph), "plan graph")

        application = json.loads(archive.read("outputs/application.json"))
        check = json.loads(archive.read("outputs/check.json"))
        if (application["schema_version"] != "b-question-content-application-trial/0.1"
                or application["content_hash"] != EXPECTED_APP_HASH
                or application["content_hash"] != digest(application["payload"])
                or application["producer"]["code_sha256"] != CODE_HASHES["code/src/annotation/recognition/question_content.py"]
                or application["producer"]["baseline_code_sha256"] != CODE_HASHES["code/src/annotation/recognition/baseline.py"]):
            raise ValueError("application identity or producer differs")
        if (application["payload"]["plan_archive"] != plan
                or application["payload"]["source_graph_archive"] != graph
                or application["payload"]["plan_file_sha256"] != EXPECTED_PLAN_SHA):
            raise ValueError("application input archive differs")
        require_ref(application["payload"]["evidence_ref"], reference(evidence), "application evidence")
        if (check["schema_version"] != "b-question-content-check-trial/0.1"
                or check["content_hash"] != EXPECTED_CHECK_HASH
                or check["content_hash"] != digest({k: v for k, v in check.items() if k != "content_hash"})
                or check["accepted"] is not True or check["meaning"] != "SOURCE_AND_PROJECTION_INTEGRITY_ONLY"
                or check["issues"] or check["decision"] != "HOLD"
                or check["plan_file_sha256"] != EXPECTED_PLAN_SHA):
            raise ValueError("source/projection check differs")
        require_ref(check["application_ref"], reference(application), "check application")
        require_ref(check["evidence_ref"], reference(evidence), "check evidence")
        require_ref(check["graph_ref"], reference(graph), "check graph")
        if (application["payload"]["decision"] != "HOLD"
                or application["payload"]["complete"] is not False
                or application["payload"]["human_verification"] is not False
                or application["payload"]["transcription_verified"] is not False
                or application["payload"]["business_acceptance"] is not False
                or application["payload"]["platform_actions"]
                or application["payload"]["new_model_calls"] != 0
                or application["payload"]["answer_matching_performed"] is not False
                or application["payload"]["graph_projection_performed"] is not False
                or "MODEL_TRANSCRIPTION_UNVERIFIED" not in application["payload"]["risks"]):
            raise ValueError("draft content promoted")

        receipts = application["payload"]["crop_receipts"]
        if len(receipts) != 23 or len({r["relative_path"] for r in receipts}) != 23:
            raise ValueError("source crop count or identity differs")
        for receipt in receipts:
            name = "outputs/source-crops/" + receipt["relative_path"]
            data = archive.read(name)
            require_bytes(data, receipt["file_sha256"], name)
            saved = Image.open(io.BytesIO(data)).convert("RGB")
            bbox = receipt["source_bbox"]
            expected = source_image.crop(tuple(bbox))
            if (saved.size != tuple(receipt["size"]) or saved.tobytes() != expected.tobytes()
                    or sha(saved.tobytes()) != receipt["rgb_sha256"]
                    or receipt["transform_to_source"] != [[1, 0, bbox[0]], [0, 1, bbox[1]], [0, 0, 1]]):
                raise ValueError("source crop pixels or geometry differ: " + name)

        fixtures = manifest["fixture_files"]
        for label, receipt in fixtures.items():
            data = archive.read(receipt["path"])
            require_bytes(data, receipt["sha256"], label)
            inner_manifest, nested = verify_nested_archive(data)
            if label == "v4":
                for member in ("source.json", "evidence.json", "graph.json", "plan.json", "46007447_page_14.jpg"):
                    if nested.read(member) != archive.read("inputs/" + member):
                        raise ValueError("v4 input bytes differ from original fixture")
            if label == "ocr":
                if (inner_manifest["engine_entry_calls"] != 8 or inner_manifest["selected_call_ids"]
                        or inner_manifest["selection_status"] != "UNSELECTED"):
                    raise ValueError("OCR observations were promoted")
                observation_names = [n for n in nested.namelist()
                                     if "-scale" in n and n.endswith(".json") and "-intent" not in n]
                if len(observation_names) != 8:
                    raise ValueError("not eight raw OCR observations")
        for name in manifest["independent_reports"]:
            archive.read(name)
        if len(manifest["independent_reports"]) < 2:
            raise ValueError("independent audit reports missing")
        if self_test:
            changed = copy.deepcopy(plan)
            changed["payload"]["decision"] = "PASS"
            changed["content_hash"] = digest(changed["payload"])
            try:
                require_fixed_plan(canonical(changed))
            except ValueError:
                pass
            else:
                raise AssertionError("internally re-signed plan was accepted")
            try:
                require_bytes(archive.read("outputs/source-crops/" + receipts[0]["relative_path"]) + b"tamper",
                              receipts[0]["file_sha256"], "tampered crop")
            except ValueError:
                pass
            else:
                raise AssertionError("tampered crop was accepted")
            try:
                require_bytes(archive.read("code/src/annotation/recognition/question_content.py") + b"tamper",
                              CODE_HASHES["code/src/annotation/recognition/question_content.py"], "tampered code")
            except ValueError:
                pass
            else:
                raise AssertionError("tampered code was accepted")
        return {"code_commit": EXPECTED_COMMIT, "decision": "HOLD",
                "files": len(entries), "crops": len(receipts), "ocr_calls": 8,
                "plan_sha256": EXPECTED_PLAN_SHA, "self_test": self_test}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("package")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.package, args.self_test), ensure_ascii=False, sort_keys=True))
