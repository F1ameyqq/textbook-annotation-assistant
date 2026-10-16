"""Read-only reproduction of frozen R2 URL component counterexamples."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
TARGET = "c3aff9598b6705ab4122062615a13ae3774698b2"
CHECKOUT = Path("C:/Users/ASUS/.codex/worktrees/a01-source-geometry/1800")
SOURCE = ROOT / ".local/stages/A01-coordinator-R3" / TARGET / "source"
REVIEW = ROOT / "docs/evidence/A01/review-R2"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    assert not (OUT / "coordinator-check.json").exists()
    assert subprocess.check_output(["git", "-C", str(CHECKOUT), "rev-parse", "HEAD"], text=True).strip() == TARGET
    SOURCE.mkdir(parents=True, exist_ok=False)
    names = subprocess.check_output(["git", "-C", str(CHECKOUT), "ls-tree", "-r", "--name-only", TARGET, "src/"], text=True).splitlines()
    source_hashes = {}
    for name in names:
        blob = subprocess.check_output(["git", "-C", str(CHECKOUT), "show", TARGET + ":" + name])
        path = SOURCE / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
        assert path.read_bytes() == blob, name
        source_hashes[name] = sha(blob)
    manifest = json.loads((REVIEW / "sha256-manifest.json").read_text(encoding="utf-8"))
    inputs = {}
    for row in manifest["records"]:
        name = row["path"].replace("\\", "/")
        if "/primary-url-path/" in name and not name.endswith("/results.json"):
            raw = (ROOT / name).read_bytes()
            assert sha(raw) == row["sha256"], name
            inputs[name] = sha(raw)
    sys.path.insert(0, str(SOURCE / "src"))
    import annotation.contracts as contracts
    import annotation.source.static.importer as importer
    rows = []
    for case in ["Q01-cross-book-path-query-tail", "Q02-wrong-index-path-fragment-tail"]:
        path = REVIEW / "primary-url-path" / case / "exchange.json"
        assert path.relative_to(ROOT).as_posix() in inputs
        public = contracts.load_bundle(path, verify_assets=True)
        try:
            importer.load_static_bundle(path, expected_book_id="46007447")
            actual = "ACCEPT"
        except Exception as error:
            actual = {"error": type(error).__name__, "code": getattr(error, "code", None)}
        rows.append({"case": case, "input": str(path), "public_assets": "ACCEPT", "source_content_hash": public.artifacts[0].content_hash, "expected": "REJECT actual URL path conflict", "actual": actual})
    assert all(row["actual"] == "ACCEPT" for row in rows), rows
    assert all(sha((SOURCE / n).read_bytes()) == h for n, h in source_hashes.items())
    assert all(sha((ROOT / n).read_bytes()) == h for n, h in inputs.items())
    result = {"target_commit": TARGET, "result": "REWORK_CONFIRMED", "source_hashes": source_hashes, "input_hashes": inputs, "rows": rows, "modules": {"contracts": contracts.__file__, "importer": importer.__file__}, "argv": [sys.executable, "-B", str(Path(__file__).resolve())], "cwd": str(Path.cwd()), "platform_actions": 0, "model_calls": 0, "full_suite_rerun": False}
    (OUT / "coordinator-check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": result["result"], "source_files": len(source_hashes), "input_files": len(inputs), "counterexamples": len(rows)}))

if __name__ == "__main__":
    main()
