"""Frozen actual derived inputs; no original image, model, or human gold.

This fixture is a new UTF-8 export of unchanged artifact objects from the
baseline's model-free, source-audited pipeline. It does not rerun image audits
and cannot establish transcription accuracy or human acceptance.
"""
import hashlib
import json
from pathlib import Path
import zipfile

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "book46007447"
ARCHIVE_SHA256 = "b992264f7daefa3313f462056d2059f55e33baa2a580aef93cf5245c38b886fb"


def observed_inputs():
    outer = json.loads((FIXTURE / "content-revision-inputs-manifest.json").read_text(encoding="utf-8"))
    raw = (FIXTURE / "content-revision-inputs.zip").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ARCHIVE_SHA256 == outer["archive"]["sha256"]
    assert len(raw) == outer["archive"]["bytes"]
    with zipfile.ZipFile(FIXTURE / "content-revision-inputs.zip") as stream:
        assert len(stream.namelist()) == len(set(stream.namelist())) == 5
        assert set(stream.namelist()) == {*outer["members"], "MANIFEST.json"}
        manifest_raw = stream.read("MANIFEST.json")
        assert hashlib.sha256(manifest_raw).hexdigest() == outer["internal_manifest_sha256"]
        inner = json.loads(manifest_raw)
        assert inner == {k: v for k, v in outer.items() if k not in {"archive", "internal_manifest_sha256"}}
        docs = {}
        for role, description in outer["documents"].items():
            name = description["path"]
            data = stream.read(name)
            assert len(data) == outer["members"][name]["bytes"]
            assert hashlib.sha256(data).hexdigest() == outer["members"][name]["sha256"]
            docs[role] = json.loads(data)
    return docs, outer


def observed_plan(version):
    return json.loads((FIXTURE / ("content-revision-plan-v" + str(version) + ".json")).read_text(encoding="utf-8"))
