"""Closeout metadata verification only; Git filenames decoded explicitly as UTF-8."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

root = Path.cwd()
r2 = root / "docs/evidence/A02/execution/portability-R2"
report = root / "docs/tasks/A02-portability-R2-execution-report.md"
base = "38aca9dcc8d027409b95193e9cc142c2336b76d3"
patch_commit = "ad71284f3b6ffc8454ee1d1e30933c8e39d7c1d8"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git"] + list(args), cwd=root).decode("utf-8")


entries = git("ls-tree", "-r", base, "docs/evidence/A02/execution", "docs/tasks/A02-execution-report.md",
              "docs/tasks/A02-rework-R1-report.md").splitlines()
pairs = [(line.split("\t", 1)[0].split()[2], line.split("\t", 1)[1]) for line in entries]
blobs = subprocess.run(["git", "cat-file", "--batch"], cwd=root, input="".join(d + "\n" for d, p in pairs).encode(),
                       capture_output=True, check=True).stdout
position = 0
for oid, relative in pairs:
    end = blobs.index(b"\n", position)
    size = int(blobs[position:end].split()[2])
    assert (root / relative).read_bytes() == blobs[end + 1:end + 1 + size], relative
    position = end + 1 + size + 1
source_counts = {}
for phase in ("before", "before-frozen-runner", "after"):
    binding = json.loads((r2 / phase / "source-binding.json").read_text(encoding="utf-8"))
    source = Path(binding["source_root"])
    for relative, digest in binding["source_sha256"].items():
        assert sha(source / relative) == digest, relative
    source_counts[phase] = len(binding["source_sha256"])
    assert not (source / ".git").exists()
    if phase == "after":
        source.relative_to(root)
    results = json.loads((r2 / phase / "results.json").read_text(encoding="utf-8"))
    assert all(c["exit_code"] == c["expected_exit_code"] for c in results["commands"])
    if phase in ("after", "before-frozen-runner"):
        for name, digest in binding["runner_sha256"].items():
            assert sha(root / "examples/a02/portability-R2" / name) == digest, name
for mode in ("noGit", "withGit"):
    log = r2 / "after" / ("a02-discovery-" + mode + ".stdout.txt")
    events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.startswith("{")]
    state = events[-1]
    assert state["tests_run"] == 62 and state["successful"] and state["skipped"] == state["errors"] == state["failures"] == 0
    for name, item in state["actual_imports"].items():
        path = Path(item["file"])
        path.relative_to(source)
        assert sha(path) == item["sha256"], name
    assert (events[0]["git_executable"] is None) == (mode == "noGit")
links = re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", report.read_text(encoding="utf-8"))
for link in links:
    if not link.endswith("/sha256-manifest.json"):
        assert (report.parent / link).exists(), link
changed = git("diff", base, "--name-only").splitlines()
allowed = lambda p: (p == "examples/a02/R1/identity.py" or p == "tests/test_a02_portability_r2.py"
                     or p.startswith("examples/a02/portability-R2/"))
assert all(allowed(p) for p in changed), changed
old = set(git("ls-tree", "-r", "--name-only", base).splitlines())
assert [p for p in changed if p in old] == ["examples/a02/R1/identity.py"]
assert not git("diff", base, patch_commit, "--name-only", "--", "src", "tests/test_a02.py", "tests/test_a02_r1.py", "pyproject.toml", ".gitattributes")
check = subprocess.run(["git", "diff", "--check", base, patch_commit], cwd=root, capture_output=True)
assert check.returncode == 0, check.stdout
assert not git("diff", patch_commit, "--name-only", "--", "src", "examples", "tests")
import pydantic

result = {"state": "REVIEW", "base_commit": base, "workflow_commit": "6b77c436742cf2826083b109d8ed86b85539cba6",
          "patch_commit": patch_commit, "only_existing_changed_file": "examples/a02/R1/identity.py",
          "old_archived_files_raw_bytes_preserved": len(pairs), "formal_runner_matches_patch": True,
          "formal_a02_noGit_withGit_tests_each": 62, "test_skips_each": 0, "raw_sources_intact": source_counts,
          "actual_import_hashes_verified": True, "report_links_checked": len(links), "patch_diff_check_exit_code": check.returncode,
          "python": sys.version, "pydantic": pydantic.__version__, "report_sha256": sha(report), "platform_browser_model_calls": 0,
          "not_rerun": ["C01", "login", "630 geometry matrix", "A01 full integrated entry"]}
with (r2 / "delivery-checks.json").open("x", encoding="utf-8", newline="\n") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
print(json.dumps(result, ensure_ascii=False))
