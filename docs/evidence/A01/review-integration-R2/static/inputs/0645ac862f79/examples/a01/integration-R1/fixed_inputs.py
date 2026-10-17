"""Materialize encoded fixed Git originals, without changing checkout attributes."""
import base64
import hashlib
import json
from pathlib import Path


def materialize(fixture,destination):
    data=json.loads((Path(fixture)/"reference.json").read_text(encoding="utf-8"))
    target=Path(destination).resolve(); target.mkdir(parents=True,exist_ok=False)
    records=[]
    for source in data["files"]:
        entry={k:v for k,v in source.items() if k!="git_original_base64"}
        raw=base64.b64decode(source["git_original_base64"],validate=True)
        if hashlib.sha256(raw).hexdigest()!=entry["git_sha256"]:
            raise ValueError("fixed Git original digest mismatch: "+entry["path"])
        path=target/entry["path"]; path.resolve().relative_to(target)
        path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw)
        records.append(entry)
    return dict(reference_commit=data["reference_commit"],source_manifest_sha256=data["source_manifest_sha256"],files=records)
