"""Exact current-body dispatch: frozen owner supervisor plus private raw capture."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

PACKAGE = Path("D:/1800/.local/stages/a24-controlled-capture-frozen-launch")
AUTHORITY = Path("D:/1800/docs/evidence/coordinator/a24-controlled-capture-current-body-dispatch/authority.json")
AUTH_SHA = "411ec3757822ed374ed7f4c13e6a0becc571609d2d2b4117991c8acc20c4e244"
OUTER = Path(__file__).resolve().parent

def sha(raw): return hashlib.sha256(raw).hexdigest()
def put(path, raw):
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
def record(path, value): put(path, (json.dumps(value, indent=2)+"\n").encode())

# Verify fixed source bytes before importing any annotation/native definitions.
raw = AUTHORITY.read_bytes()
assert sha(raw) == AUTH_SHA
data = json.loads(raw)
assert data["run_id"] == "A24-first-save-r1-controlled-capture-body-20261021t143424z"
assert data["role"] == "AUTHOR_SAVE" and data["refs"]["schema_profile"] is None
candidate_raw = Path(data["refs"]["candidate"]["path"]).read_bytes()
assert sha(candidate_raw) == data["refs"]["candidate"]["sha256"]
candidate = json.loads(candidate_raw)
for item in candidate["dependencies"]:
    path = (PACKAGE/item["path"]).resolve()
    assert PACKAGE in path.parents
    raw = path.read_bytes()
    assert len(raw) == item["bytes"] and sha(raw) == item["sha256"]
library_provenance = json.loads((PACKAGE/"docs/evidence/A24/route-callback-minimum/library-provenance.json").read_bytes())
for item in library_provenance["sources"]:
    source_raw = Path(item["path"]).read_bytes()
    assert len(source_raw) == item["bytes"] and sha(source_raw) == item["sha256"]
assert len(library_provenance["sources"]) == 4
from importlib.metadata import version
assert sys.version_info[:3] == (3, 9, 13) and version("playwright") == "1.58.0"
assert not list(PACKAGE.rglob("__pycache__"))
sys.path.insert(0, str(PACKAGE/"src"))
from annotation.runtime.live_pilot.authority import verify_authority
authority = verify_authority(AUTHORITY, AUTH_SHA, PACKAGE)
assert authority.plan["body_admission"] == "CURRENT_SCHEMA_UNBOUND" and authority.schema_profile is None
assert not authority.output.exists()
record(OUTER/"outer-claimed.json", {"schema": "A24CurrentBodyOuterClaim/v1", "authority_sha256": AUTH_SHA,
    "run_id": data["run_id"], "at": datetime.now(timezone.utc).isoformat(), "dependencies_verified": len(candidate["dependencies"]),
    "wrapper_sha256": sha(Path(__file__).read_bytes()), "resources_before_verification": 0, "attempt_limit": 1})
from annotation.runtime.live_pilot import owner
framework = owner.load_framework(authority)  # definitions only, not old main/activation
real_popen = owner.subprocess.Popen
class RawCapturedChild:
    def __init__(self, *args, **kwargs): self.child = real_popen(*args, **kwargs)
    def __getattr__(self, name): return getattr(self.child, name)
    def communicate(self, *args, **kwargs):
        try:
            stdout, stderr = self.child.communicate(*args, **kwargs)
            put(OUTER/"launcher-stdout.bin", stdout)
            put(OUTER/"launcher-stderr.bin", stderr)
            record(OUTER/"raw-capture.json", {"complete": True, "stdout": {"bytes": len(stdout), "sha256": sha(stdout)},
                "stderr": {"bytes": len(stderr), "sha256": sha(stderr)}})
            return stdout, stderr
        except BaseException as error:
            for name, attr in (("stdout", "output"), ("stderr", "stderr")):
                partial = getattr(error, attr, None)
                if isinstance(partial, bytes): put(OUTER/("launcher-"+name+"-partial.bin"), partial)
            record(OUTER/"raw-capture.json", {"complete": False, "error": owner.safe_error(error)})
            raise
owner.subprocess.Popen = RawCapturedChild
command = [sys.executable, "-B", str(PACKAGE/"tools/a24_first_save_launcher.py"), "run",
    "--authority", str(AUTHORITY), "--authority-sha256", AUTH_SHA]
try:
    release = owner.supervise(authority, framework, command, "launcher", b"", limit=880)
finally:
    owner.subprocess.Popen = real_popen
record(OUTER/"outer-result.json", {"schema": "A24CurrentBodyOuterResult/v1", "authority_sha256": AUTH_SHA,
    "run_id": data["run_id"], "at": datetime.now(timezone.utc).isoformat(), "held_launcher": release,
    "helper_own_exit_identity": "NOT_SELF_CERTIFIED", "retry_allowed": False})
print(json.dumps({"schema": "A24CurrentBodyDispatchResult/v1", "launcher_stage_success": release["stage_success"],
    "launcher_released": release["released"], "launcher_status": release.get("child_projection", {}).get("status", "UNKNOWN"),
    "retry_allowed": False}))
raise SystemExit(0 if release["stage_success"] else 2)
