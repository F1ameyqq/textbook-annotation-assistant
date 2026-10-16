"""Reconstruct fixed invalid inputs using committed bases/deltas; no D: dependency."""
import hashlib
import json
import shutil
from pathlib import Path


def reconstruct(root,name,destination):
    root = Path(root).resolve()
    fixture = root/"tests/fixtures/a01/R3"/name
    data = json.loads((fixture/"manifest.json").read_text(encoding="utf-8"))
    target = Path(destination)
    target.mkdir(parents=True,exist_ok=False)
    result = {}
    for case in data["cases"]:
        folder = target/case["id"]
        shutil.copytree(root/case["base"],folder)
        for item in case["patches"]:
            raw = (fixture/case["id"]/item["path"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != item["sha256"]:
                raise ValueError("fixed fixture digest mismatch: "+case["id"]+"/"+item["path"])
            (folder/item["path"]).write_bytes(raw)
        actual = {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in folder.rglob("*") if p.is_file()}
        expected = {item["path"]:item["sha256"] for item in case["files"]}
        if actual != expected:
            raise ValueError("reconstructed frozen input differs: "+case["id"])
        result[case["id"]] = folder/"exchange.json"
    return result
