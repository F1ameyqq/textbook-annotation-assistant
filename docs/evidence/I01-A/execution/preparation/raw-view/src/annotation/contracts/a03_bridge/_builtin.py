"""Exact packaged data; source profile/oracle hashes confer no native role."""
from functools import lru_cache
from importlib import resources
from types import MappingProxyType

from ._errors import StaticCodecError, need
from ._json import parse_json, sha
from ._schema import audit

PINS = (
    ("profile.json", "f7385ba20090b5df8aa062c417e3d5c66a889a30f464facff994d9929b94f9ea"),
    ("api.json", "b5210ab175ccfd3f1f8f6baf0da07a3757dac732decf3bfa3de0b65354b0eba8"),
    ("schemas/basis-v3.schema.json", "40db0538a512f65e2f8668c528f98643d372cdc195b9b868c446cce2b0743202"),
    ("schemas/conversion-v3.schema.json", "ac28365f16d028af83e385108cb06cdb3a6f81e2a2e792051692952640c116e4"),
    ("schemas/exchange-v3.schema.json", "02f8dd3fc22c1775622e8a7807037911214a3d400bbdf83afc9839b783589394"),
    ("schemas/fact-v3.schema.json", "97eda5084ec698235559977cb29782fa77888cae9f5efbe57bea6a106bb3fb23"),
    ("schemas/pre-run-v2.schema.json", "2f03ff9eca620747fb273d92150b67312778ba63f9bccd5f32425d3948bcfd08"),
    ("schemas/prefix-v2.schema.json", "3d1bec1e23fb666816e74916f25066e5a057c63a14cafa9e6b9130b6d2f706fb"),
    ("readonly-adoption.json", "41f50606ad8b2283acad08ae5d63e0c40681ec424c83c026fe654d3c3734880c"),
)


@lru_cache(maxsize=1)
def raw_data():
    root = resources.files(__package__).joinpath("data")
    result = {}
    for logical, expected in PINS:
        path = root
        for part in logical.split("/"):
            path = path.joinpath(part)
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise StaticCodecError("BUILTIN_DATA", logical, str(error)) from error
        need(sha(raw) == expected, "BUILTIN_PIN", logical)
        result[logical] = raw
    return MappingProxyType(result)


def document(name):
    return parse_json(raw_data()[name], "builtin/" + name)


def rule_documents():
    names = {"exchange": "exchange-v3.schema.json", "fact": "fact-v3.schema.json", "prefix": "prefix-v2.schema.json", "pre_run": "pre-run-v2.schema.json", "basis": "basis-v3.schema.json", "conversion": "conversion-v3.schema.json"}
    docs = {key: document("schemas/" + value) for key, value in names.items()}
    for doc in docs.values():
        audit(doc)
    return docs
