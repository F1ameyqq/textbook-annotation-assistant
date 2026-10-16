"""R1 offline reproduction, explicit source commit + raw source hashes, new output only.

Works in a real checkout or a raw Git export. An enclosing repository's HEAD is
never used as the export identity. Does not invoke the old verify.py.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

from identity import source_binding


def verify(source, declared_commit, repo, output, matrix_only=False):
    source, repo, output = Path(source).resolve(), Path(repo).resolve(), Path(output).resolve()
    binding = source_binding(source, declared_commit, repo)
    # Bind regression and consumer/runner code too, not just the production modules.
    auxiliary = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", declared_commit,
                                        "examples/a02", "tests/test_a02.py", "tests/test_a02_r1.py"], cwd=repo, text=True).splitlines()
    for relative in auxiliary:
        if relative.endswith(".py"):
            blob = subprocess.check_output(["git", "show", declared_commit + ":" + relative], cwd=repo)
            actual = (source / relative).read_bytes()
            assert actual == blob, "auxiliary code differs from declared raw blob: " + relative
            binding["source_sha256"][relative] = hashlib.sha256(actual).hexdigest()
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(source / "src"))
    import pydantic
    from annotation.contracts import load_bundle
    from scenarios import run_matrix, write_json
    imports = {}
    for name in ("annotation.contracts", "annotation.delivery.mock", "annotation.delivery.planner", "annotation.quality.targetcheck"):
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve()
        path.relative_to((source / "src").resolve())
        imports[name] = str(path)
    write_json(output / "source-binding.json", dict(binding, imports=imports, python=sys.version,
                                                   executable=sys.executable, pydantic=pydantic.__version__))
    env = dict(os.environ, PYTHONPATH=str(source / "src"), PYTHONDONTWRITEBYTECODE="1")
    commands = []

    def command(name, args):
        argv = [sys.executable, "-B"] + args
        result = subprocess.run(argv, cwd=source, env=env, capture_output=True)
        (output / (name + ".stdout.txt")).write_bytes(result.stdout)
        (output / (name + ".stderr.txt")).write_bytes(result.stderr)
        commands.append({"name": name, "argv": argv, "cwd": str(source), "exit_code": result.returncode})
        write_json(output / (name + "-command.json"), commands[-1])
        print(name + ": exit " + str(result.returncode), flush=True)
        assert result.returncode == 0, name + " failed; inspect archived stdout/stderr"

    if not matrix_only:
        command("a02-tests", ["-m", "unittest", "discover", "-s", "tests", "-p", "test_a02*.py", "-v"])
        command("c01-tests", ["-m", "unittest", "discover", "-s", "tests", "-p", "test_contracts*.py", "-v"])
    matrix = run_matrix(source, output / "matrix")
    write_json(output / "matrix-command.json", {"argv": sys.argv, "cwd": str(Path.cwd()), "source_root": str(source),
                                                "declared_commit": declared_commit, "exit_code": 0, "case_count": len(matrix)})
    print("R1 matrix: " + str(len(matrix)) + " passed", flush=True)
    if not matrix_only:
        cases = [("normal", "normal", "applied", 0), ("choice", "choice", "applied", 0),
                 ("exceptions", "exceptions", "applied", 0), ("not-applied", "normal", "not_applied", 0),
                 ("lost-response", "normal", "lost_response", 0), ("response-lost-readable", "normal", "response_lost_readable", 0),
                 ("contradictory", "normal", "contradictory", 0), ("partial", "normal", "partial", 0),
                 ("readback-failure", "normal", "readback_failure", 0), ("lost-second", "normal", "lost_response", 1)]
        for name, fixture, fault, index in cases:
            destination = output / "demos" / name
            command("demo-" + name, [str(source / "examples/a02/run.py"), "--input", str(source / "tests/fixtures/a02" / fixture / "input.json"),
                                     "--output", str(destination), "--fault", fault, "--fault-index", str(index)])
            load_bundle(destination / "final.json")
    # Recheck every bound byte after test/demo execution.
    for relative, digest in binding["source_sha256"].items():
        assert hashlib.sha256((source / relative).read_bytes()).hexdigest() == digest, relative
    files = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(output.rglob("*")) if p.is_file()}
    write_json(output / "manifest.json", {"provenance": "SYNTHETIC", "execution_mode": "SIMULATED", "state": "REVIEW",
                                          "r1_base_commit": "5c9285720c8628c5198bedeadfc9f6bc7826a914",
                                          "source_binding": binding, "commands": commands, "matrix_cases": len(matrix),
                                          "evidence_sha256": files, "platform_browser_model_calls": 0,
                                          "limitations": ["N1 excluded-region association unchanged", "N2 evidence-label admission unchanged",
                                                          "no persistence/restart/reconciliation", "content PENDING", "NOT_SUBMITTED"]})
    print(output / "manifest.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--identity-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--matrix-only", action="store_true")
    args = parser.parse_args()
    verify(args.source_root, args.source_commit, args.identity_repo, args.output, args.matrix_only)
