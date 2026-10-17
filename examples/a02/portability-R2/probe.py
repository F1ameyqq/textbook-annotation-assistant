"""Direct child process probe; binding errors intentionally propagate nonzero."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--identity-file", type=Path, required=True)
parser.add_argument("--source-root", type=Path, required=True)
parser.add_argument("--operation", choices=("identity", "binding"), default="identity")
parser.add_argument("--declared-commit")
parser.add_argument("--identity-repo", type=Path)
args = parser.parse_args()
spec = importlib.util.spec_from_file_location("r2_identity_probe", args.identity_file.resolve())
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)
print(json.dumps({"event": "environment", "argv": sys.argv, "cwd": str(Path.cwd()),
                  "PATH": os.environ.get("PATH"), "git_executable": shutil.which("git"),
                  "source_root": str(args.source_root.resolve()), "has_dot_git": (args.source_root / ".git").exists(),
                  "identity_import": identity.__file__, "identity_sha256": hashlib.sha256(Path(identity.__file__).read_bytes()).hexdigest(),
                  "python": sys.version, "executable": sys.executable}), flush=True)
if args.operation == "identity":
    result = identity.git_identity(args.source_root)
else:
    result = identity.source_binding(args.source_root, args.declared_commit, args.identity_repo)
print(json.dumps({"event": "result", "operation": args.operation, "result": result}), flush=True)
