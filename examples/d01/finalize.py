"""One-time D01 static closeout and SHA inventory. Does not run product tests."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

BASE = "c6bebdf43eb93f7a6ae21e96ec07ed155686777d"
WORKFLOW = "f15f7bc03fac8994ade1642fa7547cbd823c6d43"
SOURCE = "9a7b9d7e374ee7a3ee124c9ff20e0b4003e57464"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    root = Path(__file__).resolve().parents[2]
    evidence = root / "docs/evidence/D01/execution"
    run = evidence / "run03"
    stage = root / ".local/d01/run03"
    manifest = evidence / "SHA256SUMS.json"
    assert not manifest.exists(), "preserve the frozen manifest"
    git_calls = []

    def git(*args):
        argv = ["git", "-C", str(root), *args]
        result = subprocess.run(argv, capture_output=True)
        git_calls.append({"argv": argv, "cwd": str(root), "exit_code": result.returncode,
                          "stdout_sha256": sha(result.stdout), "stderr_sha256": sha(result.stderr),
                          "synchronous_return": True})
        assert result.returncode == 0, result.stderr
        return result.stdout

    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))

    def save(name, value):
        path = evidence / name
        # Match the exact write_text newline serialization used by the initial
        # Windows attempt, without rewriting or normalizing any archived file.
        raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").replace("\n", os.linesep).encode("utf-8")
        if path.exists():
            assert path.read_bytes() == raw, "preserve previous closeout output: " + name
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    supplement = []
    for name in ("docs/tasks/A01-integration-R2-review-report.md", "docs/tasks/A01-review-R2-handoff.md",
                 "docs/tasks/S01-eligibility-preparation.md"):
        raw = git("show", WORKFLOW + ":" + name)
        path = evidence / "workflow-links" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            assert path.read_bytes() == raw
        else:
            path.write_bytes(raw)
        supplement.append({"path": name, "commit": WORKFLOW, "sha256": sha(raw), "bytes": len(raw),
                           "git_blob_oid": git("rev-parse", WORKFLOW + ":" + name).decode().strip()})
    save("workflow-links-index.json", supplement)
    assert git("diff", "--name-only", BASE, SOURCE).decode().splitlines() == ["pyproject.toml"]
    assert not git("diff", "--name-only", "HEAD").decode().splitlines(), "unexpected existing tracked changes"
    source_index = read(run / "source-index.json")["files"]
    for entry in source_index:
        assert sha((stage / "fixed source" / entry["path"]).read_bytes()) == entry["sha256"]
        assert sha(git("show", SOURCE + ":" + entry["path"])) == entry["sha256"]
    sample_index = read(run / "sample-index.json")["files"]
    for entry in sample_index:
        assert sha(git("show", BASE + ":" + entry["path"])) == entry["sha256"]
        for parent in (stage / "frozen inputs", stage / "relocated packages with spaces"):
            assert sha((parent / entry["path"]).read_bytes()) == entry["sha256"]
    # A complete per-file inventory of the controlled bad copies, including absences.
    negatives = []
    for case in read(run / "consumption-summary.json")["negative"]:
        book, mutation = case["book"], case["mutation"]
        prefix = "examples/a01/R3/bundles/" + book + "/"
        folder = stage / "controlled bad copies" / (book + "-" + mutation)
        entries = []
        for entry in sample_index:
            if entry["path"].startswith(prefix):
                relative = entry["path"][len(prefix):]
                path = folder / relative
                entries.append({"path": relative, "original_git_path": entry["path"],
                    "original_sha256": entry["sha256"], "exists": path.exists(),
                    "bytes": path.stat().st_size if path.exists() else None,
                    "sha256": sha(path.read_bytes()) if path.exists() else None})
        differences = [e for e in entries if e["original_sha256"] != e["sha256"]]
        assert len(differences) == 1 and differences[0]["path"] == case["resource_path"]
        negatives.append({"book": book, "mutation": mutation, "files": entries})
    save("negative-input-index.json", negatives)
    parsed = []
    for path in sorted((root / "examples/d01").glob("*.py")):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=9)
        parsed.append(path.relative_to(root).as_posix())
    for name in ("run.py", "probe.py", "collect.py"):
        assert (root / "examples/d01" / name).read_bytes() == (evidence / "collector-run03" / name).read_bytes()
    links = []
    generated_later = {evidence / "closeout-audit.json", manifest}
    for path in (root / "examples/d01/README.md", root / "docs/tasks/D01-execution-report.md"):
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            assert not target.startswith(("http:", "https:")), "D01 report uses local evidence links only"
            resolved = (path.parent / target.split("#", 1)[0]).resolve()
            assert resolved.exists() or resolved in generated_later, str(resolved)
            links.append({"document": path.relative_to(root).as_posix(), "target": target})
    commands = read(run / "commands.json")
    assert len(commands) == 18 and all(c["synchronous_return"] and not c["timed_out"] for c in commands)
    assert all(c["exit_code"] == c["expected_exit_code"] for c in commands)
    for c in commands:
        folder = run / "commands" / c["label"]
        for stream in ("stdout", "stderr"):
            assert sha((folder / (stream + ".txt")).read_bytes()) == c[stream + "_sha256"]
    for attempt, expected in (("01", 1), ("02", 1), ("03", 0)):
        folder = evidence / ("collector-run" + attempt)
        receipt = read(folder / "command.json")
        assert receipt["exit_code"] == expected and receipt["synchronous_return"]
        for name in ("stdout.txt", "stderr.txt"):
            assert sha((folder / name).read_bytes()) == receipt[name + "_sha256"]
    assert read(run / "contract-regression.json")["tests"] == {
        "ran": 70, "failures": 0, "errors": 0, "skips": []}
    assert read(run / "outside-cwd.json")["outside_worktree"]
    assert read(evidence / "process-observation-final.json")["observed_remaining"] == []
    save("closeout-audit.json", {"state": "REVIEW", "base_commit": BASE, "workflow_commit": WORKFLOW,
        "implementation_commit": SOURCE, "source_tree": read(run / "source-index.json")["source_tree"],
        "source_files_unchanged_after_build": len(source_index), "sample_files_fixed_and_preserved": len(sample_index),
        "controlled_negative_copies": len(negatives), "contract_tests": 70, "functional_commands": len(commands),
        "ast_parsed_on_cpython39": parsed, "checked_links": links,
        "runner_and_probe_bytes_match_executed_snapshot": True,
        "git_queries": git_calls, "scope": "Static closeout; no acceptance, integration, or test replay"})
    paths = {root / "pyproject.toml", root / "docs/tasks/D01-execution-report.md"}
    for prefix in ("examples/d01", "docs/evidence/D01/execution"):
        paths.update(p for p in (root / prefix).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    entries = [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size,
                "sha256": sha(p.read_bytes())} for p in sorted(paths)]
    save("SHA256SUMS.json", {"format": "d01-execution-sha256-1", "base_commit": BASE,
        "implementation_commit": SOURCE, "source_and_external_fixed_inputs": [
            "run03/source-index.json", "run03/sample-index.json", "run03/regression-input-index.json",
            "run03/public-dependencies.json", "negative-input-index.json", "run03/workflow-index.json",
            "workflow-links-index.json"],
        "excluded_self": ["docs/evidence/D01/execution/SHA256SUMS.json"], "files": entries})
    for link in links:
        assert (root / link["document"]).parent.joinpath(link["target"]).resolve().exists()
    print(json.dumps({"files": len(entries), "manifest_sha256": sha(manifest.read_bytes())}, indent=2))


if __name__ == "__main__":
    main()
