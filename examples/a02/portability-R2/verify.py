"""Bounded R2 reproduction: exact source export, real noGit children, no error masking."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE = "38aca9dcc8d027409b95193e9cc142c2336b76d3"


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def verify(repo, commit, output, before=False):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    top = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=repo, text=True).strip()
    assert Path(top).resolve() == repo, "explicit repository must be its own Git top-level"
    resolved = subprocess.check_output(["git", "rev-parse", "--verify", commit + "^{commit}"], cwd=repo, text=True).strip()
    paths = ["src/annotation", "examples/a02/R1/identity.py", "examples/a02/R1/scenarios.py", "tests/test_a02_r1.py"]
    if not before:
        paths += ["examples/a02/run.py", "examples/a02/portability-R2", "tests/test_a02.py", "tests/test_a02_portability_r2.py",
                  "tests/fixtures/a02", "tests/fixtures/contracts/unknown"]
    files = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", resolved] + paths, cwd=repo, text=True).splitlines()
    output.mkdir(parents=True, exist_ok=False)
    source = output / "raw source no Git"
    source.mkdir()
    hashes = {}
    for relative in files:
        blob = subprocess.check_output(["git", "show", resolved + ":" + relative], cwd=repo)
        destination = source / relative
        destination.resolve().relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as handle:
            handle.write(blob)
        hashes[relative] = hashlib.sha256(blob).hexdigest()
    tools = Path(__file__).resolve().parent
    save(output / "source-binding.json", {"declared_commit": resolved, "checkout_commit": None,
                                         "method": "explicit commit plus raw Git blob export; parent HEAD not adopted",
                                         "source_root": str(source), "identity_repo": str(repo), "source_sha256": hashes,
                                         "runner_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                                            for p in sorted(tools.glob("*.py"))}})
    no_git = output / "empty executable search path"
    no_git.mkdir()
    no_git_path = str(no_git)
    assert shutil.which("git", path=no_git_path) is None
    commands = []

    def command(label, args, without_git=False, expected=0, cwd=None):
        env = dict(os.environ, PYTHONPATH=str(source / "src"), PYTHONDONTWRITEBYTECODE="1")
        if without_git:
            env["PATH"] = no_git_path
        argv = [sys.executable, "-B"] + args
        run = subprocess.run(argv, cwd=cwd or source, env=env, capture_output=True)
        (output / (label + ".stdout.txt")).write_bytes(run.stdout)
        (output / (label + ".stderr.txt")).write_bytes(run.stderr)
        record = {"label": label, "argv": argv, "cwd": str(cwd or source), "PATH": env.get("PATH"),
                  "git_executable": shutil.which("git", path=env.get("PATH")), "exit_code": run.returncode,
                  "expected_exit_code": expected, "stdout": label + ".stdout.txt", "stderr": label + ".stderr.txt"}
        commands.append(record)
        save(output / (label + "-command.json"), record)
        print(label + ": exit " + str(run.returncode), flush=True)
        assert run.returncode == expected, label + " unexpected exit; original stdout/stderr retained"
        events = [json.loads(line) for line in run.stdout.decode("utf-8").splitlines() if line.startswith("{")]
        return run, events

    identity_file = str(source / "examples/a02/R1/identity.py")
    probe = [str(tools / "probe.py"), "--identity-file", identity_file, "--source-root", str(source)]
    old_expected = 1 if before else 0
    direct, events = command("raw-noGit-identity", probe, True, old_expected)
    assert events[0]["git_executable"] is None and events[0]["has_dot_git"] is False
    if before:
        assert b"FileNotFoundError" in direct.stderr
    else:
        assert events[-1]["result"]["checkout_commit"] is None and "unknown" in events[-1]["result"]["status"]
    command("original-identity-test-noGit", [str(tools / "run_tests.py"), "--source-root", str(source), "--identity-only"], True, old_expected)
    _, events = command("raw-withGit-identity", probe)
    assert events[-1]["result"]["checkout_commit"] is None  # Nested under repo, never its own checkout.
    command("original-identity-test-withGit", [str(tools / "run_tests.py"), "--source-root", str(source), "--identity-only"])
    if not before:
        _, events = command("actual-checkout-withGit", [str(tools / "probe.py"), "--identity-file", identity_file,
                                                        "--source-root", str(repo)], cwd=repo)
        observed_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        assert events[-1]["result"]["checkout_commit"] == observed_head
        binding_args = probe + ["--operation", "binding", "--declared-commit", resolved, "--identity-repo", str(repo)]
        failed, events = command("source-binding-noGit", binding_args, True, 1)
        assert b"identity repository must be an actual Git top-level" in failed.stderr
        assert not any(e.get("event") == "result" for e in events), "failed binding must not return verified result"
        _, events = command("source-binding-withGit", binding_args)
        assert events[-1]["result"]["declared_commit"] == resolved and events[-1]["result"]["checkout_commit"] is None
        _, events = command("a02-discovery-noGit", [str(tools / "run_tests.py"), "--source-root", str(source)], True)
        assert events[-1]["successful"] and events[-1]["skipped"] == 0
        command("a02-discovery-withGit", [str(tools / "run_tests.py"), "--source-root", str(source)])
    for relative, digest in hashes.items():
        assert hashlib.sha256((source / relative).read_bytes()).hexdigest() == digest
    save(output / "results.json", {"state": "REVIEW", "phase": "before" if before else "after", "declared_commit": resolved,
                                   "commands": commands, "source_files_unchanged": len(hashes), "platform_browser_model_calls": 0,
                                   "scope": "A02 affected tests only; no A01 full integration/C01/login/geometry rerun"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--before", action="store_true")
    args = parser.parse_args()
    verify(args.repo, args.commit, args.output, args.before)
