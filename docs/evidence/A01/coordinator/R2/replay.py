"""Read-only coordinator replay of the four frozen A01 R1 contradictions."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
REVIEW = ROOT / "docs/evidence/A01/review-R1"
BOOT = json.loads((REVIEW / "bootstrap.json").read_text(encoding="utf-8"))
SNAPSHOT = Path(BOOT["snapshot"])
COMMIT = "03c1af41a134945c406a52a48e3d4f6f0da33eb2"
assert BOOT["target_commit"] == COMMIT


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    source_checks = []
    for path in sorted((SNAPSHOT / "src").rglob("*.py")):
        relative = path.relative_to(SNAPSHOT).as_posix()
        expected = subprocess.check_output(["git", "show", COMMIT + ":" + relative], cwd=ROOT)
        assert path.read_bytes() == expected, relative
        source_checks.append({"path": relative, "sha256": digest(expected)})
    manifest = json.loads((REVIEW / "sha256-manifest.json").read_text(encoding="utf-8"))
    entries = {row["path"].replace("\\", "/"): row for row in manifest["records"]}
    original = json.loads((REVIEW / "primary-source-confirmation/results.json").read_text(encoding="utf-8"))
    inputs = []
    for case in original["records"]:
        folder = REVIEW / "primary-source-confirmation" / case["id"]
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                relative = path.relative_to(ROOT).as_posix()
                row = entries[relative]
                assert digest(path.read_bytes()) == row["sha256"], relative
                inputs.append({"path": relative, "sha256": row["sha256"]})
    sys.path.insert(0, str(SNAPSHOT / "src"))
    import annotation.contracts as contracts
    import annotation.source.static.importer as importer
    results = []
    for case in original["records"]:
        path = REVIEW / "primary-source-confirmation" / case["id"] / "exchange.json"
        public = contracts.load_bundle(path, verify_assets=True)
        try:
            loaded = importer.load_static_bundle(path, expected_book_id=case["book"])
            actual = {"result": "ACCEPT", "book_id": loaded.artifacts[0].book_id}
        except Exception as error:
            actual = {"result": "REJECT", "code": getattr(error, "code", None), "message": str(error)}
        results.append({"id": case["id"], "expected": "REJECT", "actual": actual,
                        "public_validation": "ACCEPT", "source_content_hash": public.artifacts[0].content_hash})
    output = {"target_commit": COMMIT, "source_checks": source_checks, "input_checks": inputs,
              "module_paths": {"contracts": contracts.__file__, "importer": importer.__file__},
              "results": results, "failures_reproduced": sum(row["actual"]["result"] == "ACCEPT" for row in results),
              "scope": "Frozen invalid inputs replay only; no full suite, mutation of inputs, platform or model calls."}
    with (OUT / "coordinator-check.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"source_blobs_verified": len(source_checks), "input_files_verified": len(inputs),
                      "failures_reproduced": output["failures_reproduced"]}))
    return 0 if output["failures_reproduced"] == 4 else 1


if __name__ == "__main__":
    raise SystemExit(main())
