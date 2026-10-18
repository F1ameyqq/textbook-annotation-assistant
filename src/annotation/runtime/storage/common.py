"""Local runtime values. No target business rules or ambient authority."""
from collections.abc import Mapping
import copy
import hashlib
import json
import os
from pathlib import Path
import time
import uuid


class RuntimeFailure(Exception):
    def __init__(self, code, message="", exit_code=None):
        super().__init__(message or code)
        self.code = code
        self.exit_code = exit_code or (4 if any(x in code for x in ("OWNER", "CAS", "GATE")) else
            6 if any(x in code for x in ("TIMEOUT", "DEADLINE")) else
            5 if any(x in code for x in ("CORRUPT", "STORAGE", "LEDGER", "DIRECTORY", "RESOURCE_MISSING")) else
            7 if code in ("SYNTHETIC_ONLY", "SYNTHETIC_COMPLETE_REQUIRED") else 3 if code in
            ("BOOK_WRITE_PAUSED", "LEGACY_UNRECORDED", "PLAN_INTERRUPTED", "TARGET_DRIFT_HOLD") else 2)


def plain(value):
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "model_dump"):
        return plain(value.model_dump(mode="json"))
    if isinstance(value, Mapping):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    return value


def canonical(value):
    return json.dumps(plain(value), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def reference(artifact):
    artifact = plain(artifact)
    return {key: artifact[key] for key in ("artifact_id", "revision", "kind", "content_hash")}


def now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


class Handle(dict):
    """Public diagnostic fields; authority also requires process-local identity."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


def unique(prefix):
    return prefix + "-" + uuid.uuid4().hex


def fail(code, message="", exit_code=None):
    raise RuntimeFailure(code, message, exit_code)


def exclusive_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if path.read_bytes() != data:
            fail("IMMUTABLE_FILE_CONFLICT", str(path), 5)
    if path.read_bytes() != data:
        fail("RESOURCE_HASH_MISMATCH", str(path), 5)
    return path


class FaultController:
    ALIASES = {"before_intent": "BEFORE_INTENT_COMMIT", "after_intent": "AFTER_INTENT_COMMIT",
        "after_dispatch_started": "AFTER_DISPATCH_STARTED", "after_effect": "AFTER_TARGET_EFFECT_COMMIT",
        "after_readback": "AFTER_READBACK_CAPTURE", "after_receipt": "AFTER_RECEIPT_COMMIT"}

    def __init__(self, specification=None):
        self.specification = specification or {}

    def __call__(self, point):
        point = self.ALIASES.get(point, point)
        wanted = self.ALIASES.get(self.specification.get("point"), self.specification.get("point"))
        if point != wanted:
            return
        marker = self.specification.get("marker")
        if marker:
            exclusive_bytes(marker, canonical({"point": point, "pid": os.getpid(), "at": now()}))
        release = self.specification.get("release")
        if release:
            deadline = time.monotonic() + 5
            while not Path(release).exists():
                if time.monotonic() >= deadline:
                    fail("BARRIER_TIMEOUT", point, 6)
                time.sleep(.01)
        if self.specification.get("mode") == "barrier":
            return
        if self.specification.get("exit_code", 90) is not None:
            os._exit(int(self.specification.get("exit_code", 90)))
