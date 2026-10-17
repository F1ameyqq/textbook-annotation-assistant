"""Run actual A02 tests, record loaded files, and propagate the unittest result."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import unittest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source-root", type=Path, required=True)
parser.add_argument("--identity-only", action="store_true")
args = parser.parse_args()
root = args.source_root.resolve()
sys.path[:0] = [str(root / "src"), str(root / "tests")]
print(json.dumps({"event": "environment", "argv": sys.argv, "cwd": str(Path.cwd()),
                  "PATH": os.environ.get("PATH"), "git_executable": shutil.which("git"),
                  "source_root": str(root), "has_dot_git": (root / ".git").exists(),
                  "python": sys.version, "executable": sys.executable}), flush=True)
if args.identity_only:
    suite = unittest.defaultTestLoader.loadTestsFromName(
        "test_a02_r1.A02R1Tests.test_export_subdirectory_cannot_borrow_enclosing_git_head")
else:
    suite = unittest.defaultTestLoader.discover(str(root / "tests"), pattern="test_a02*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
imports = {}
for name, module in list(sys.modules.items()):
    path = getattr(module, "__file__", None)
    if path and (name.startswith("annotation") or name.startswith("test_a02")):
        imports[name] = {"file": str(Path(path).resolve()), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
# test_a02_r1 loads identity through importlib without adding it to sys.modules.
old_test = sys.modules.get("test_a02_r1")
if old_test is not None:
    path = Path(old_test.identity.__file__).resolve()
    imports["test_a02_r1.identity"] = {"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
print(json.dumps({"event": "result", "tests_run": result.testsRun, "failures": len(result.failures),
                  "errors": len(result.errors), "skipped": len(result.skipped), "successful": result.wasSuccessful(),
                  "actual_imports": imports}), flush=True)
raise SystemExit(0 if result.wasSuccessful() else 1)
