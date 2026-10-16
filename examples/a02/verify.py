"""Archive reproducible offline author evidence at a NEW output path.

Runs only local Python. Explicit PYTHONPATH prevents importing another editable checkout.
Creates no browser/session/login/network/model activity. Not independent acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def verify(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    records = []

    def command(name, arguments):
        result = subprocess.run([sys.executable] + arguments, cwd=ROOT, env=env, capture_output=True)
        (output / (name + ".stdout.txt")).write_bytes(result.stdout)
        (output / (name + ".stderr.txt")).write_bytes(result.stderr)
        records.append({"name": name, "argv": ["python"] + [str(a).replace(str(ROOT), "<checkout>").replace(str(output), "<output>") for a in arguments],
                        "exit_code": result.returncode})
        print(name + ": exit " + str(result.returncode), flush=True)
        if result.returncode:
            raise RuntimeError(name + " failed; preserved stdout/stderr in " + str(output))

    command("environment", ["-c", "import sys,pydantic,annotation.contracts,annotation.delivery.planner; "
             "print(sys.version); print('pydantic',pydantic.__version__); print(annotation.contracts.__file__); print(annotation.delivery.planner.__file__)"])
    command("a02-tests", ["-m", "unittest", "discover", "-s", "tests", "-p", "test_a02*.py", "-v"])
    command("c01-tests", ["-m", "unittest", "discover", "-s", "tests", "-p", "test_contracts*.py", "-v"])
    cases = [("normal", "normal", "applied", 0), ("choice", "choice", "applied", 0),
             ("exceptions", "exceptions", "applied", 0), ("not-applied", "normal", "not_applied", 0),
             ("lost-response", "normal", "lost_response", 0),
             ("response-lost-readable", "normal", "response_lost_readable", 0),
             ("contradictory", "normal", "contradictory", 0), ("partial", "normal", "partial", 0),
             ("readback-failure", "normal", "readback_failure", 0), ("lost-second", "normal", "lost_response", 1)]
    summaries = {}
    for name, fixture, fault, index in cases:
        case_root = output / "cases" / name
        command("demo-" + name, [str(ROOT / "examples/a02/run.py"), "--input", str(ROOT / "tests/fixtures/a02" / fixture / "input.json"),
                                "--output", str(case_root), "--fault", fault, "--fault-index", str(index)])
        summaries[name] = json.loads((case_root / "summary.json").read_text(encoding="utf-8"))
    source_files = [p for folder in ("src/annotation/delivery/planner", "src/annotation/delivery/mock", "src/annotation/quality/targetcheck", "examples/a02")
                    for p in (ROOT / folder).rglob("*.py")] + [ROOT / "tests/test_a02.py"]
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"provenance": "SYNTHETIC", "execution_mode": "SIMULATED", "acceptance_state": "REVIEW",
                "base_commit": "39341c98d73c354d639f3beeb55429f55d0e9be5",
                "workflow_commit": "39341c98d73c354d639f3beeb55429f55d0e9be5",
                "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "commands": records, "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(source_files)},
                "evidence_sha256": {p.relative_to(output).as_posix(): sha(p) for p in sorted(output.rglob("*")) if p.is_file()},
                "case_results": {name: {key: value[key] for key in ("readiness", "outcomes", "write_disposition", "book_paused", "target_question_count", "target_frame_count")}
                                 for name, value in summaries.items()},
                "platform_actions": 0, "model_calls": 0, "model_cost": 0,
                "unproven": ["real platform", "algorithm accuracy", "cross-process recovery", "final content", "submission", "B contract confirmation"]}
    with (output / "manifest.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print(output / "manifest.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args().output)
