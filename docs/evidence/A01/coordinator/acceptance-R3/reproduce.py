"""Coordinator replay of frozen A01 R3 public consumers; offline, no writes to inputs."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[5]
TARGET = "180bb1e86fb2a7eb1546be85af70f466f069daf5"
SNAPSHOT = ROOT / ".local/stages/A01-review-R3" / TARGET / "snapshot"
OUT = Path(__file__).resolve().parent / "coordinator-check.json"
assert not OUT.exists(), "Use a new output directory; do not overwrite evidence"


def sha(data):
    return hashlib.sha256(data).hexdigest()


paths = subprocess.check_output(
    ["git", "ls-tree", "-r", "--name-only", TARGET, "--", "src"], cwd=ROOT
).decode().splitlines()
bindings = []
for name in paths:
    expected = subprocess.check_output(["git", "show", TARGET + ":" + name], cwd=ROOT)
    actual = (SNAPSHOT / name).read_bytes()
    assert actual == expected, name
    bindings.append({"path": name, "sha256": sha(actual), "bytes": len(actual)})
sys.path.insert(0, str(SNAPSHOT / "src"))
from annotation.contracts import load_bundle
from annotation.source.static import StaticSourceError, load_static_bundle
from annotation.source.static import importer
assert Path(importer.__file__).resolve().is_relative_to(SNAPSHOT / "src")

review = ROOT / "docs/evidence/A01/review-R3"
manifest = json.loads((review / "sha256-manifest.json").read_text(encoding="utf-8"))
replays = review / "source/replay-inputs"
inputs = []
for entry in manifest["records"]:
    if "/source/replay-inputs/" not in entry["path"]:
        continue
    raw = (ROOT / entry["path"]).read_bytes()
    assert sha(raw) == entry["sha256"] and len(raw) == entry["bytes"]
    inputs.append(entry)

results = []
for folder in sorted(replays.iterdir()):
    if not folder.is_dir():
        continue
    path = folder / "exchange.json"
    load_bundle(path, verify_assets=True)
    try:
        load_static_bundle(path, expected_book_id="46007447")
        raise AssertionError("Historical counterexample was accepted: " + folder.name)
    except StaticSourceError as error:
        assert error.code == "SOURCE_URL_COMPONENT", (folder.name, error.code)
        results.append({"case": folder.name, "public_assets": "PASS", "actual": "REJECT", "code": error.code, "location": error.location})
assert len(results) == 5
for book in ("46006966", "46007447"):
    path = SNAPSHOT / "examples/a01/R3/bundles" / book / "exchange.json"
    public = load_bundle(path, verify_assets=True)
    source = load_static_bundle(path, expected_book_id=book)
    assert public == source
    results.append({"case": "valid-bundle-" + book, "actual": "ACCEPT", "exchange_sha256": sha(path.read_bytes())})
    url = "https://example.invalid/upload_images/" + book + "/" + book + "_page_13.jpg"
    assert importer.url_index(url, book, "coordinator-positive") == 13
    for suffix in ("?", "#", "?masked=wrong", "#masked=wrong"):
        try:
            importer.url_index(url + suffix, book, "coordinator-components")
            raise AssertionError("URL component accepted")
        except StaticSourceError as error:
            assert error.code == "SOURCE_URL_COMPONENT"
            results.append({"case": "helper-" + book + suffix, "actual": "REJECT", "code": error.code, "layer": "string helper only"})
for entry in bindings:
    assert sha((SNAPSHOT / entry["path"]).read_bytes()) == entry["sha256"]
for entry in inputs:
    assert sha((ROOT / entry["path"]).read_bytes()) == entry["sha256"]
result = {"target_commit": TARGET, "python": sys.version, "executable": sys.executable,
          "source_bindings": bindings, "replay_inputs": inputs, "results": results,
          "passed": True, "frozen_inputs_unchanged": True,
          "module": importer.__file__, "scope": "Five historical full bundles, two positive bundles and eight component helper negatives. No full-suite rerun or geometry matrix.",
          "network_calls": 0, "platform_calls": 0, "model_calls": 0}
with OUT.open("x", encoding="utf-8", newline="\n") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
print(json.dumps({"passed": True, "source_bindings": len(bindings), "replay_files": len(inputs), "checks": len(results)}))
