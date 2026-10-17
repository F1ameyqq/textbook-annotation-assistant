"""Finite JSON values and isolated canonical representations."""
import hashlib
import json
import math

from ._errors import StaticCodecError, need


def copy_json(value, path="$", active=None):
    active = set() if active is None else active
    kind = type(value)
    if kind in (dict, list):
        need(id(value) not in active, "JSON_CYCLE", path)
        active.add(id(value))
        try:
            if kind is dict:
                need(all(type(key) is str for key in value), "JSON_KEY", path)
                return {key: copy_json(item, path + "/" + key, active) for key, item in value.items()}
            return [copy_json(item, path + "/" + str(i), active) for i, item in enumerate(value)]
        finally:
            active.remove(id(value))
    need(kind in (str, int, float, bool, type(None)), "JSON_TYPE", path)
    if kind is float:
        need(math.isfinite(value), "JSON_NONFINITE", path)
    return value


def canonical(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError) as error:
        raise StaticCodecError("JSON_ENCODING", "$", str(error)) from error


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(canonical(value))


def parse_json(raw, path):
    try:
        value = json.loads(raw)
        return copy_json(value, path)
    except (ValueError, UnicodeError) as error:
        if isinstance(error, StaticCodecError):
            raise
        raise StaticCodecError("RESOURCE_JSON", path, str(error)) from error
