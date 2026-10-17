"""Reproduce the bounded D01 clean installation; never reuse an existing run.

Use --stage under this worktree's ignored .local/ and a new --evidence directory.
All child commands are synchronous. Logs preserve stdout/stderr after URL-userinfo
redaction. No global configuration, browser, platform, or model operations.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile

BASE = "c6bebdf43eb93f7a6ae21e96ec07ed155686777d"
WORKFLOW = "f15f7bc03fac8994ade1642fa7547cbd823c6d43"
SOURCE = "9a7b9d7e374ee7a3ee124c9ff20e0b4003e57464"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sanitize(data):
    # Explicit public indexes are used; this is a defensive logging boundary.
    return re.sub(rb"(https?://)[^\s/@]+:[^\s/@]+@", rb"\1[REDACTED]@", data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--python39", type=Path, required=True)
    parser.add_argument("--source-commit", default=SOURCE)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    # CPython 3.9 on Windows may leave a nonexistent relative path unresolved.
    stage, evidence = args.stage.absolute().resolve(), args.evidence.absolute().resolve()
    assert not stage.exists() and not evidence.exists(), "preserve old attempts; choose new paths"
    assert (repo / ".local").resolve() in stage.parents, "stage must be task-local and ignored"
    assert (repo / "docs/evidence/D01/execution").resolve() in evidence.parents
    stage.mkdir(parents=True)
    evidence.mkdir(parents=True)
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith(("PYTHON", "PIP_"))}
    temp = stage / "temp"
    temp.mkdir()
    env.update(TMP=str(temp), TEMP=str(temp), TMPDIR=str(temp))
    commands = []

    def command(label, argv, cwd, expected=0, timeout=180):
        folder = evidence / "commands" / label
        folder.mkdir(parents=True)
        start = time.time()
        child = subprocess.Popen([str(a) for a in argv], cwd=str(cwd), env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        timed_out = False
        try:
            stdout, stderr = child.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()
            stdout, stderr = child.communicate()
        stdout, stderr = sanitize(stdout), sanitize(stderr)
        (folder / "stdout.txt").write_bytes(stdout)
        (folder / "stderr.txt").write_bytes(stderr)
        record = {"label": label, "argv": [str(a) for a in argv], "cwd": str(cwd),
                  "pid": child.pid, "started_unix": start, "finished_unix": time.time(),
                  "exit_code": child.returncode, "expected_exit_code": expected,
                  "timed_out": timed_out, "synchronous_return": True,
                  "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr),
                  "environment": {k: env[k] for k in ("TMP", "TEMP", "TMPDIR", "SOURCE_DATE_EPOCH") if k in env},
                  "python_and_pip_environment_removed": True}
        save(folder / "command.json", record)
        commands.append(record)
        save(evidence / "commands.json", commands)
        print(label + ": exit " + str(child.returncode), flush=True)
        if child.returncode != expected or timed_out:
            raise RuntimeError(label + " failed; preserve this attempt, see " + str(folder))
        return stdout

    def git(*argv):
        return subprocess.check_output(["git", "-C", str(repo), *argv])

    def export(commit, paths, target):
        names = git("ls-tree", "-r", "--name-only", commit, "--", *paths).decode("utf-8").splitlines()
        assert names
        entries = []
        for name in names:
            raw = git("show", commit + ":" + name)
            oid = git("rev-parse", commit + ":" + name).decode().strip()
            assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == oid
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            assert path.read_bytes() == raw
            entries.append({"path": name, "commit": commit, "git_blob_oid": oid,
                            "bytes": len(raw), "sha256": sha(raw), "export_sha256": sha(path.read_bytes())})
        return entries

    try:
        diff = git("diff", "--name-only", BASE, args.source_commit).decode().splitlines()
        assert diff == ["pyproject.toml"], diff
        epoch = git("show", "-s", "--format=%ct", args.source_commit).decode().strip()
        env["SOURCE_DATE_EPOCH"] = epoch
        source = stage / "fixed source"
        source_index = export(args.source_commit, ["pyproject.toml", "src"], source)
        save(evidence / "source-index.json", {"base_commit": BASE, "workflow_commit": WORKFLOW,
             "source_commit": args.source_commit,
             "source_tree": git("rev-parse", args.source_commit + "^{tree}").decode().strip(),
             "export_scope": ["pyproject.toml", "src/**"], "files": source_index})
        workflow_files = ["AGENTS.md", "docs/coordination.md", "docs/architecture.md", "docs/contracts-v1.md",
                          "docs/tasks/D01-dependency-implementation.md", "docs/tasks/D01-independent-review.md",
                          "docs/tasks/D01-dependency-preparation.md", "docs/tasks/A01-integration-R2-coordinator-acceptance.md"]
        save(evidence / "workflow-index.json", export(WORKFLOW, workflow_files, evidence / "workflow"))
        save(evidence / "receipt.json", {"task": "D01", "state": "RUNNING", "reasoning_effort": "xhigh",
             "worktree": str(repo), "branch": git("branch", "--show-current").decode().strip(),
             "base_commit": BASE, "workflow_commit": WORKFLOW, "implementation_commit": args.source_commit,
             "only_product_change": "pyproject.toml: Pillow==11.3.0", "initial_blockers": []})
        outside = Path(tempfile.gettempdir()).absolute().resolve() / ("1800 D01 outside cwd " + uuid.uuid4().hex)
        assert repo not in outside.parents and not outside.exists()
        outside.mkdir()
        save(evidence / "outside-cwd.json", {"cwd": str(outside), "worktree": str(repo),
             "outside_worktree": repo not in outside.parents,
             "outside_build_source": source not in outside.parents})
        venv = stage / "clean cp39"
        command("01-create-venv", [args.python39, "-I", "-m", "venv", venv], outside)
        py = venv / "Scripts/python.exe"
        (evidence / "pyvenv.cfg").write_bytes((venv / "pyvenv.cfg").read_bytes())
        assert "include-system-site-packages = false" in (venv / "pyvenv.cfg").read_text()
        command("02-new-environment", [py, "-I", "-c",
            "import json,sys,site;print(json.dumps(dict(executable=sys.executable,version=sys.version,prefix=sys.prefix,base_prefix=sys.base_prefix,sys_path=sys.path,user_site=site.ENABLE_USER_SITE)));assert sys.version_info[:2]==(3,9);assert sys.prefix!=sys.base_prefix;assert not site.ENABLE_USER_SITE"], outside)
        pip = [py, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "--no-input"]
        downloads = stage / "bootstrap wheels"
        downloads.mkdir()
        command("03-download-pip", pip + ["download", "--index-url", "https://pypi.org/simple", "--no-deps",
                "--only-binary=:all:", "--dest", downloads, "--retries", "0", "--timeout", "30", "-v", "pip==25.3"], outside)
        pip_wheel, = downloads.glob("pip-25.3-*.whl")
        command("04-bootstrap-pip", pip + ["install", "--no-index", "--no-deps", "--upgrade", pip_wheel], outside)
        command("05-build-tools", pip + ["install", "--index-url", "https://pypi.org/simple", "--report",
                evidence / "build-tools-install-report.json", "--only-binary=:all:", "--retries", "0", "--timeout", "30",
                "setuptools==80.9.0", "wheel==0.45.1"], outside)
        dist = stage / "dist"
        dist.mkdir()
        command("06-build-wheel", pip + ["wheel", "--no-deps", "--no-build-isolation", "--no-index",
                "--wheel-dir", dist, source], outside)
        built, = dist.glob("annotation_contracts-*.whl")
        wheel = evidence / "artifacts" / built.name
        wheel.parent.mkdir()
        shutil.copyfile(built, wheel)
        assert built.read_bytes() == wheel.read_bytes()
        with zipfile.ZipFile(wheel) as archive:
            matches = []
            for entry in source_index:
                if entry["path"].startswith("src/"):
                    member = entry["path"][4:]
                    assert sha(archive.read(member)) == entry["sha256"]
                    matches.append({"git_path": entry["path"], "wheel_path": member,
                                    "sha256": entry["sha256"]})
        save(evidence / "wheel-binding.json", {"implementation_commit": args.source_commit,
             "wheel": str(wheel), "sha256": sha(wheel.read_bytes()), "bytes": wheel.stat().st_size,
             "source_date_epoch": epoch, "source_matches": matches})
        command("07-install-wheel", pip + ["install", "--index-url", "https://pypi.org/simple", "--report",
                evidence / "install-report.json", "--only-binary=:all:", "--retries", "0", "--timeout", "30", wheel], outside)
        command("08-pip-check", pip + ["check"], outside)
        probe = stage / "installed_probe.py"
        probe.write_bytes((Path(__file__).parent / "probe.py").read_bytes())
        command("09-installed-provenance", [py, "-I", probe, "metadata", "--output",
                evidence / "installed-provenance.json", "--wheel", wheel], outside)
        # The bootstrap download is independently tied to public PyPI's release metadata.
        bootstrap_code = (
            "import hashlib,json,pathlib,urllib.request;"
            "p=pathlib.Path(" + repr(str(pip_wheel)) + ");"
            "d=json.load(urllib.request.urlopen('https://pypi.org/pypi/pip/25.3/json',timeout=30));"
            "r=next(x for x in d['urls'] if x['filename']==p.name);"
            "assert hashlib.sha256(p.read_bytes()).hexdigest()==r['digests']['sha256'];"
            "print(json.dumps(dict(name='pip',version='25.3',url=r['url'],sha256=r['digests']['sha256'],bytes=p.stat().st_size)))")
        bootstrap = command("10-pip-public-hash", [py, "-I", "-c", bootstrap_code], outside)
        public = [json.loads(bootstrap)]
        for name in ("build-tools-install-report.json", "install-report.json"):
            report = json.loads((evidence / name).read_text(encoding="utf-8"))
            for entry in report["install"]:
                info = entry["download_info"]
                if not info["url"].startswith("https://"):
                    continue
                assert info["url"].startswith("https://files.pythonhosted.org/")
                public.append({"name": entry["metadata"]["name"], "version": entry["metadata"]["version"],
                               "url": info["url"], "sha256": info["archive_info"]["hashes"]["sha256"], "report": name})
        save(evidence / "public-dependencies.json", public)
        # Freeze the exact accepted R3 packages and public consumer from BASE.
        original = stage / "frozen inputs"
        frozen_paths = ["examples/a01/consume.py", "examples/a01/R3/bundles/46006966", "examples/a01/R3/bundles/46007447"]
        inputs = export(BASE, frozen_paths, original)
        moved = stage / "relocated packages with spaces"
        shutil.copytree(original, moved)
        for entry in inputs:
            entry["relocated_sha256"] = sha((moved / entry["path"]).read_bytes())
            assert entry["relocated_sha256"] == entry["sha256"]
        save(evidence / "sample-index.json", {"base_commit": BASE, "files": inputs})
        consumer = moved / "examples/a01/consume.py"
        positives, negatives = [], []
        for book, count in (("46006966", 6), ("46007447", 2)):
            package = moved / "examples/a01/R3/bundles" / book
            output = evidence / ("consumer-" + book + ".json")
            raw = command("11-consume-" + book, [py, "-I", probe, "consumer", "--output", output,
                          "--consumer", consumer, "--exchange", package / "exchange.json", "--book-id", book], outside)
            result = json.loads(raw)
            assert result["asset_count"] == count and result["coverage_eligible"] is False
            limitations = json.loads((package / "limitations.json").read_text(encoding="utf-8"))
            assert limitations["scope_manifest_status"] == "REFERENCE_ONLY"
            assert limitations["independent_denominator_status"] == "UNKNOWN"
            positives.append(result)
            for mutation, code in (("missing", "RESOURCE_MISSING"), ("corrupt", "RESOURCE_HASH")):
                damaged = stage / "controlled bad copies" / (book + "-" + mutation)
                shutil.copytree(package, damaged)
                value = json.loads((damaged / "exchange.json").read_text(encoding="utf-8"))
                asset = value["artifacts"][0]["payload"]["assets"][0]
                victim = damaged / asset["path"]
                before = sha(victim.read_bytes())
                if mutation == "missing":
                    victim.unlink()  # One explicitly scoped generated file; no recursive deletion.
                else:
                    victim.write_bytes(b"D01 controlled corrupt resource\n")
                label = "12-" + book + "-" + mutation
                command(label, [py, "-I", probe, "consumer", "--output", evidence / (label + ".json"),
                        "--consumer", consumer, "--exchange", damaged / "exchange.json", "--book-id", book], outside, expected=1)
                error = (evidence / "commands" / label / "stderr.txt").read_text(encoding="utf-8")
                assert "[" + code + "]" in error and "$.artifacts[0].payload.assets[0]" in error
                negatives.append({"book": book, "mutation": mutation, "resource_path": asset["path"],
                                  "original_sha256": before, "actual_sha256": sha(victim.read_bytes()) if victim.exists() else None,
                                  "code": code, "exit_code": 1, "command": label})
        save(evidence / "consumption-summary.json", {"positive": positives, "negative": negatives})
        command("13-source-regression", [py, "-I", probe, "source", "--output", evidence / "source-regression.json"], outside)
        regression = stage / "regression fixtures only"
        regression_index = export(BASE, ["tests/test_contracts.py", "tests/test_contracts_platform_refs.py",
             "tests/fixtures/contracts", "examples/contracts/consume.py", "examples/contracts/build_fixtures.py"], regression)
        save(evidence / "regression-input-index.json", regression_index)
        command("14-contract-regression", [py, "-I", probe, "regression", "--tests", regression / "tests",
                "--output", evidence / "contract-regression.json"], outside)
        unchanged = []
        for folder, entries in ((original, inputs), (moved, inputs), (regression, regression_index)):
            for entry in entries:
                actual = sha((folder / entry["path"]).read_bytes())
                assert actual == entry["sha256"]
                unchanged.append({"file": str(folder / entry["path"]), "sha256": actual})
        save(evidence / "post-run-input-integrity.json", unchanged)
        save(evidence / "run-result.json", {"state": "REVIEW", "execution_completed": True,
             "implementation_commit": args.source_commit, "command_count": len(commands),
             "positive_consumers": 2, "expected_resource_rejections": 4,
             "all_synchronous_commands_returned": all(c["synchronous_return"] for c in commands),
             "not_acceptance_or_integration": True, "platform_calls": 0, "model_calls": 0, "browser_downloads": 0})
    except BaseException as error:
        save(evidence / "attempt-failure.json", {"type": type(error).__name__, "message": str(error),
             "completed_command_count": len(commands), "synchronous_commands_returned": True})
        raise
    finally:
        save(evidence / "process-ledger.json", {"collector_pid": os.getpid(),
             "collector_completion": "finally reached; outer command receipt proves collector exit",
             "children": [{k: c[k] for k in ("label", "pid", "exit_code", "synchronous_return", "timed_out")} for c in commands],
             "background_children_started": 0})


if __name__ == "__main__":
    main()
