"""Explicit A-internal STATIC_INSPECTION codec. No execution authority.

The existing C01/1.1 dispatch is unchanged. These APIs do not create PRE proofs,
sessions, plans, writer handles, CURRENT selections, or native capabilities.
"""
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from types import MappingProxyType
from typing import Tuple

from ._builtin import PINS, document, raw_data, rule_documents
from ._errors import StaticCodecError, need
from ._json import canonical, copy_json, sha
from ._resources import ResourceReader
from ._rules import StaticPackage


@dataclass(frozen=True)
class BridgeSelection:
    __slots__ = ("codec_id", "role", "exchange_version", "artifact_versions", "profile_id", "profile_sha256", "schema_pins", "api_sha256", "validation_rules_id", "adoption_scope")
    codec_id: str
    role: str
    exchange_version: str
    artifact_versions: Tuple[str, ...]
    profile_id: str
    profile_sha256: str
    schema_pins: Tuple[Tuple[str, str], ...]
    api_sha256: str
    validation_rules_id: str
    adoption_scope: str


@dataclass(frozen=True)
class BridgeContext:
    __slots__ = ("selection", "asset_root")
    selection: BridgeSelection
    asset_root: Path


@dataclass(frozen=True)
class ConsumedResource:
    __slots__ = ("path", "raw_sha256")
    path: str
    raw_sha256: str


def _immutable(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _immutable(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_immutable(item) for item in value)
    return value


@dataclass(frozen=True, repr=False)
class ValidatedA03Bundle:
    __slots__ = ("selection", "canonical_sha256", "resources", "_canonical_json")
    selection: BridgeSelection
    canonical_sha256: str
    resources: Tuple[ConsumedResource, ...]
    _canonical_json: bytes

    @property
    def data(self):
        return _immutable(self.model_dump())

    def model_dump(self):
        """A fresh JSON-native copy of the complete bundle, never a write view."""
        return json.loads(self._canonical_json)

    def __repr__(self):
        return "ValidatedA03Bundle(canonical_sha256={!r}, resources={})".format(self.canonical_sha256, len(self.resources))


@lru_cache(maxsize=1)
def select_static_codec() -> BridgeSelection:
    """Return the sole fixed immutable description, which is not authority."""
    adoption = document("readonly-adoption.json")
    profile = document("profile.json")
    pins = dict(PINS)
    need(adoption["role"] == "STATIC_INSPECTION" and adoption["adoption_scope"] == "A_INTERNAL_READONLY", "BUILTIN_ROLE", "builtin/readonly-adoption.json")
    need(profile["status"] == "STATIC_UNIMPLEMENTED" and profile["implementation_authorized"] is False, "BUILTIN_PROFILE", "builtin/profile.json")
    schemas = tuple((row["path"], row["sha256"]) for row in profile["schema_pins"])
    need(all(pins[name] == expected for name, expected in schemas), "BUILTIN_PIN", "builtin/profile.json/schema_pins")
    need(adoption["schema_pins"] == [list(row) for row in schemas] and adoption["profile_sha256"] == pins["profile.json"] and adoption["api_sha256"] == profile["api_sha256"] == pins["api.json"], "BUILTIN_ADOPTION", "builtin/readonly-adoption.json")
    need(adoption["profile_id"] == profile["profile_id"] and adoption["exchange_version"] == profile["exchange_version"], "BUILTIN_ADOPTION", "builtin/readonly-adoption.json")
    return BridgeSelection(adoption["codec_id"], adoption["role"], adoption["exchange_version"], tuple(adoption["artifact_versions"]), adoption["profile_id"], adoption["profile_sha256"], schemas, adoption["api_sha256"], adoption["validation_rules_id"], adoption["adoption_scope"])


def _selection(selection):
    need(type(selection) is BridgeSelection, "SELECTION_TYPE", "$context.selection")
    need(type(selection.role) is str and selection.role == "STATIC_INSPECTION", "ROLE_NOT_ALLOWED", "$context.selection.role")
    expected = select_static_codec()
    for field in BridgeSelection.__slots__:
        actual, fixed = getattr(selection, field), getattr(expected, field)
        need(type(actual) is type(fixed), "SELECTION_PINS", "$context.selection." + field)
        if field == "schema_pins":
            need(all(type(row) is tuple and len(row) == 2 and all(type(item) is str for item in row) for row in actual), "SELECTION_PINS", "$context.selection.schema_pins")
        elif field == "artifact_versions":
            need(all(type(item) is str for item in actual), "SELECTION_PINS", "$context.selection.artifact_versions")
        need(actual == fixed, "SELECTION_PINS", "$context.selection." + field)
    return expected


def _root(asset_root):
    try:
        result = Path(asset_root).resolve(strict=True)
    except (TypeError, OSError, ValueError, RuntimeError) as error:
        raise StaticCodecError("ASSET_ROOT", "$context.asset_root", str(error)) from error
    need(result.is_dir(), "ASSET_ROOT", "$context.asset_root")
    return result


def open_static_context(*, asset_root, selection=None) -> BridgeContext:
    """Bind only the fixed read-only descriptor and an explicit resolved root."""
    chosen = select_static_codec() if selection is None else _selection(selection)
    return BridgeContext(chosen, _root(asset_root))


def validate_static_bundle(bundle, *, context) -> ValidatedA03Bundle:
    """Validate all fixed static rules and return a detached immutable snapshot."""
    need(type(context) is BridgeContext, "CONTEXT_TYPE", "$context")
    chosen = _selection(context.selection)
    need(isinstance(context.asset_root, Path) and context.asset_root.is_absolute(), "CONTEXT_ROOT", "$context.asset_root")
    root = _root(context.asset_root)
    need(root == context.asset_root, "CONTEXT_ROOT_CHANGED", "$context.asset_root")
    try:
        isolated = copy_json(bundle)
        need(type(isolated) is dict, "BUNDLE_TYPE", "$")
        need(isolated.get("format_version") == chosen.exchange_version, "EXCHANGE_VERSION", "$/format_version")
        reader = ResourceReader(root)
        package = StaticPackage(isolated, reader, rule_documents(), set(document("api.json")["registry"]))
        package.validate()
        encoded = canonical(isolated)
    except RecursionError as error:
        raise StaticCodecError("STRUCTURE_DEPTH", "$", "JSON or reference nesting exceeds interpreter depth") from error
    consumed = tuple(ConsumedResource(path, raw_sha) for path, raw_sha in sorted(reader.consumed.items()))
    return ValidatedA03Bundle(chosen, sha(encoded), consumed, encoded)


__all__ = ["BridgeSelection", "BridgeContext", "ConsumedResource", "ValidatedA03Bundle", "StaticCodecError", "select_static_codec", "open_static_context", "validate_static_bundle"]
