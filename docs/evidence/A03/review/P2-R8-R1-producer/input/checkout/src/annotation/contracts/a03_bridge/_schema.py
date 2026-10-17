"""The frozen finite schema dialect, not general JSON Schema conformance."""
from datetime import datetime
import json
import re

from ._errors import StaticCodecError, need

KEYS = {"$schema", "$id", "$comment", "$defs", "$ref", "title", "description", "discriminator", "type", "properties", "propertyNames", "required", "additionalProperties", "anyOf", "oneOf", "const", "enum", "pattern", "format", "minLength", "minItems", "maxItems", "minimum", "maximum", "exclusiveMinimum", "items", "uniqueItems", "minProperties"}


def audit(schema):
    need(not set(schema) - KEYS, "SCHEMA_KEYWORDS", "$schema", str(sorted(set(schema) - KEYS)))
    for key in ("properties", "$defs"):
        for child in schema.get(key, {}).values():
            audit(child)
    for key in ("oneOf", "anyOf"):
        for child in schema.get(key, []):
            audit(child)
    for key in ("items", "propertyNames", "additionalProperties"):
        if isinstance(schema.get(key), dict):
            audit(schema[key])


def validate(value, schema, doc=None, path="$"):
    if doc is None:
        audit(schema)
        doc = schema
    if "$ref" in schema:
        need(schema["$ref"].startswith("#/"), "SCHEMA_EXTERNAL_REF", path)
        target = doc
        for key in schema["$ref"][2:].split("/"):
            target = target[key.replace("~1", "/").replace("~0", "~")]
        validate(value, target, doc, path)
    for key in ("oneOf", "anyOf"):
        if key in schema:
            matches = 0
            for child in schema[key]:
                try:
                    validate(value, child, doc, path)
                    matches += 1
                except StaticCodecError:
                    pass
            need(matches == 1 if key == "oneOf" else matches > 0, "SHAPE_" + key, path)
    if "const" in schema:
        need(value == schema["const"] and ((type(value) is bool) == (type(schema["const"]) is bool)), "SHAPE_CONST", path)
    if "enum" in schema:
        need(value in schema["enum"], "SHAPE_ENUM", path)
    if "type" in schema:
        types = {"object": type(value) is dict, "array": type(value) is list, "string": type(value) is str, "integer": type(value) is int, "number": type(value) in (int, float), "boolean": type(value) is bool, "null": value is None}
        need(schema["type"] in types and types[schema["type"]], "SHAPE_TYPE", path)
    if isinstance(value, dict):
        need(set(schema.get("required", [])) <= set(value), "SHAPE_REQUIRED", path)
        need(len(value) >= schema.get("minProperties", 0), "SHAPE_MIN_PROPERTIES", path)
        properties = schema.get("properties", {})
        for key, item in value.items():
            if "propertyNames" in schema:
                validate(key, schema["propertyNames"], doc, path)
            if key in properties:
                validate(item, properties[key], doc, path + "/" + key)
            elif schema.get("additionalProperties") is False:
                raise StaticCodecError("SHAPE_EXTRA", path + "/" + key)
            elif isinstance(schema.get("additionalProperties"), dict):
                validate(item, schema["additionalProperties"], doc, path + "/" + key)
    if isinstance(value, list):
        need(schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", len(value)), "SHAPE_ITEMS", path)
        if schema.get("uniqueItems"):
            need(len({json.dumps(item, sort_keys=True) for item in value}) == len(value), "SHAPE_UNIQUE", path)
        if "items" in schema:
            for i, item in enumerate(value):
                validate(item, schema["items"], doc, path + "/" + str(i))
    if isinstance(value, str):
        need(len(value) >= schema.get("minLength", 0), "SHAPE_LENGTH", path)
        if "pattern" in schema:
            need(re.search(schema["pattern"], value) is not None, "SHAPE_PATTERN", path)
        if "format" in schema:
            need(schema["format"] == "date-time", "SCHEMA_FORMAT", path)
            try:
                need(datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None, "SHAPE_TIME", path)
            except ValueError as error:
                if isinstance(error, StaticCodecError):
                    raise
                raise StaticCodecError("SHAPE_TIME", path) from error
    if type(value) in (int, float):
        for key, predicate in (("minimum", lambda x: value >= x), ("maximum", lambda x: value <= x), ("exclusiveMinimum", lambda x: value > x)):
            if key in schema:
                need(predicate(schema[key]), "SHAPE_" + key, path)
