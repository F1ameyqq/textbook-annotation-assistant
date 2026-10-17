"""Replay the 7 geometry / 9 source formal defects into NEW R1 evidence only."""
import argparse
import hashlib
import json
import os
import platform
import sys
import tempfile
from pathlib import Path

from cases import SOURCE_IDS, capture, geometry_cases, mutated_source

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src"))
import annotation.contracts as contracts
import annotation.geometry as geometry
import annotation.source.static as source
import annotation.source.static.importer as importer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination",type=Path)
    args = parser.parse_args()
    out = args.destination.resolve()
    out.mkdir(parents=True,exist_ok=False)
    rows = geometry_cases(geometry)
    with tempfile.TemporaryDirectory(prefix="a01 R1 probes ") as folder:
        folder = Path(folder)
        base = ROOT/"examples/a01/bundles/46006966"
        for case in SOURCE_IDS:
            path = mutated_source(base,folder/case,case,contracts.seal_artifact)
            contracts.load_bundle(path,verify_assets=True)  # Each is a publicly valid, newly sealed envelope.
            actual = capture(lambda:source.load_static_bundle(path,expected_book_id="46006966"))
            changed = {}
            for item in path.parent.rglob("*"):
                if item.is_file():
                    relative = item.relative_to(path.parent)
                    if item.read_bytes() != (base/relative).read_bytes():
                        target = out/case/relative
                        target.parent.mkdir(parents=True,exist_ok=True)
                        target.write_bytes(item.read_bytes())
                        changed[relative.as_posix()] = hashlib.sha256(item.read_bytes()).hexdigest()
            rows.append(dict(id=case,input=dict(base="examples/a01/bundles/46006966",changed_files=changed),
                             expected="StaticSourceError with code and location",actual=actual,
                             matches_expectation=actual.get("exception") == "StaticSourceError" and bool(actual.get("code")) and bool(actual.get("location"))))
    result = dict(task="A01-R1",cwd=str(Path.cwd()),python=platform.python_version(),command=sys.argv,
                  imported_modules={m.__name__:dict(path=m.__file__,sha256=hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest())
                                    for m in (geometry,importer,contracts)},
                  rows=rows,passed=sum(r["matches_expectation"] for r in rows),failed=sum(not r["matches_expectation"] for r in rows),
                  network_browser_platform_model_calls=0)
    (out/"results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(passed=result["passed"],failed=result["failed"],status="REVIEW")))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
