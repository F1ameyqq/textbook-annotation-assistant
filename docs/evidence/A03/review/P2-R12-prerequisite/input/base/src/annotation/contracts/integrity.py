"""Deterministic exchange serialization and local-resource integrity."""
import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter

from .models import Artifact, PlatformPolicy

ARTIFACT_ADAPTER = TypeAdapter(Artifact)


def as_data(value: Any):
    return value.model_dump(mode="json") if isinstance(value, BaseModel) else value


def content_digest(value) -> str:
    data = dict(as_data(value))
    data.pop("content_hash", None)
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def seal_artifact(data):
    candidate = dict(as_data(data))
    candidate["content_hash"] = "0" * 64
    candidate = ARTIFACT_ADAPTER.validate_python(candidate).model_dump(mode="json")
    candidate["content_hash"] = content_digest(candidate)
    return candidate


def seal_policy(data):
    candidate = dict(as_data(data))
    candidate["content_hash"] = "0" * 64
    candidate = PlatformPolicy.model_validate(candidate).model_dump(mode="json")
    candidate["content_hash"] = content_digest(candidate)
    return candidate


def artifact_ref(artifact):
    data = as_data(artifact)
    return {key: data[key] for key in ("artifact_id", "revision", "kind", "content_hash")}


def policy_ref(policy):
    data = as_data(policy)
    return {key: data[key] for key in ("policy_id", "revision", "content_hash")}


def file_digest(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path):
    def reject_constant(value):
        raise ValueError("non-finite JSON number: " + value)
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                      parse_constant=reject_constant)
