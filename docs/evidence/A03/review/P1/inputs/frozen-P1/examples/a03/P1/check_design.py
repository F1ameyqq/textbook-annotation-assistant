"""DESIGN_ONLY P1 JSON/schema/resource/reference audit, without recovery logic.

No runtime qualification, synthetic admission, owner/generation, SQLite, target
read, observation freshness, intent commit or effect comparison is implemented.
Semantic expected outcomes in case-manifest.json are always NOT_EXECUTED.
"""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


class StaticError(Exception):
    def __init__(self, category, path, detail):
        super().__init__(detail)
        self.category, self.path, self.detail = category, path, detail


def load(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key " + key)
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError("nonfinite " + s)))


def walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_hash(value):
    return hashlib.sha256(encoded({k: v for k, v in value.items() if k != "content_hash"}).encode("utf-8")).hexdigest()


def ref(value):
    return {k: value[k] for k in ("artifact_id", "revision", "kind", "content_hash")}


def is_ref(value):
    return isinstance(value, dict) and set(value) == {"artifact_id", "revision", "kind", "content_hash"}


class SchemaChecker:
    """Small structural evaluator for the exact schema keywords used here.

    It is deliberately not exported into src and not a replacement for a full
    standards validator or candidate semantic validation. Unknown assertion
    keywords fail closed so the delivered schema cannot silently outrun it.
    """
    annotations = {"title", "description", "default", "$comment", "$schema", "$id", "$defs", "discriminator"}
    assertions = {"$ref", "type", "const", "enum", "required", "properties", "additionalProperties", "items",
                  "minItems", "maxItems", "minProperties", "maxProperties", "minLength", "maxLength", "pattern", "minimum", "maximum",
                  "exclusiveMinimum", "exclusiveMaximum", "anyOf", "oneOf", "format", "propertyNames"}

    def __init__(self, base):
        self.base = base
        self.documents = {}

    def document(self, name):
        if name not in self.documents:
            if Path(name).name != name:
                raise ValueError("schema document must be a local basename")
            self.documents[name] = load(self.base / name)
        return self.documents[name]

    def check_schema(self, name):
        document = self.document(name)
        for node in walk(document):
            if isinstance(node, dict) and "$ref" in node:
                self.resolve(node["$ref"], document)
        def node(schema):
            unknown = set(schema) - self.annotations - self.assertions
            if unknown:
                raise ValueError("unsupported structural schema keywords: " + str(sorted(unknown)))
            for key in ("properties", "$defs"):
                for child in schema.get(key, {}).values():
                    node(child)
            for key in ("items", "additionalProperties", "propertyNames"):
                if isinstance(schema.get(key), dict):
                    node(schema[key])
            for key in ("anyOf", "oneOf"):
                for child in schema.get(key, []):
                    node(child)
        node(document)

    def resolve(self, pointer, root):
        file, _, fragment = pointer.partition("#")
        document = self.document(file) if file else root
        result = document
        if fragment:
            for segment in fragment.lstrip("/").split("/"):
                result = result[segment.replace("~1", "/").replace("~0", "~")]
        return result, document

    def validate(self, value, schema, root, path="$"):
        def fail(message):
            raise StaticError("STRUCTURE_FAIL", path, message)
        if "$ref" in schema:
            target, target_root = self.resolve(schema["$ref"], root)
            self.validate(value, target, target_root, path)
            return
        for union in ("anyOf", "oneOf"):
            if union in schema:
                successes = 0
                for variant in schema[union]:
                    try:
                        self.validate(value, variant, root, path)
                        successes += 1
                    except StaticError:
                        pass
                if successes < 1 or (union == "oneOf" and successes != 1):
                    fail(union + " branches accepted=" + str(successes))
                return
        if "const" in schema and (value != schema["const"] or type(value) != type(schema["const"])):
            fail("const mismatch")
        if "enum" in schema and value not in schema["enum"]:
            fail("enum mismatch")
        expected = schema.get("type")
        valid = {"object": isinstance(value, dict), "array": isinstance(value, list), "string": isinstance(value, str),
                 "integer": isinstance(value, int) and not isinstance(value, bool),
                 "number": isinstance(value, (int, float)) and not isinstance(value, bool), "boolean": isinstance(value, bool), "null": value is None}
        if expected and not valid.get(expected, False):
            fail("type mismatch: " + expected)
        if isinstance(value, dict):
            if len(value) < schema.get("minProperties", 0) or len(value) > schema.get("maxProperties", float("inf")):
                fail("object property count")
            missing = set(schema.get("required", [])) - set(value)
            if missing:
                fail("missing " + str(sorted(missing)))
            properties = schema.get("properties", {})
            for key, child in value.items():
                if "propertyNames" in schema:
                    self.validate(key, schema["propertyNames"], root, path + ".<key>")
                if key in properties:
                    self.validate(child, properties[key], root, path + "." + key)
                elif schema.get("additionalProperties") is False:
                    fail("unexpected field " + key)
                elif isinstance(schema.get("additionalProperties"), dict):
                    self.validate(child, schema["additionalProperties"], root, path + "." + key)
        if isinstance(value, list):
            if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", float("inf")):
                fail("array length")
            for n, child in enumerate(value):
                if "items" in schema:
                    self.validate(child, schema["items"], root, path + "[" + str(n) + "]")
        if isinstance(value, str):
            if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", float("inf")):
                fail("string length")
            if "pattern" in schema and re.search(schema["pattern"], value) is None:
                fail("string pattern")
            if schema.get("format") == "date-time":
                try:
                    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        fail("timestamp lacks timezone")
                except ValueError:
                    fail("invalid timestamp")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if not math.isfinite(value):
                fail("nonfinite number")
            if value < schema.get("minimum", -float("inf")) or value > schema.get("maximum", float("inf")):
                fail("number range")
            if value <= schema.get("exclusiveMinimum", -float("inf")) or value >= schema.get("exclusiveMaximum", float("inf")):
                fail("exclusive number range")


def references(bundle):
    artifacts = bundle["artifacts"]
    known = {(a["artifact_id"], a["revision"]): a for a in artifacts}
    if len(known) != len(artifacts):
        raise StaticError("REFERENCE_FAIL", "$.bundle.artifacts", "duplicate artifact identity")
    edges = {}
    for a in artifacts:
        key = (a["artifact_id"], a["revision"])
        edges[key] = [(r["artifact_id"], r["revision"]) for r in walk(a) if is_ref(r)]
    done, busy = set(), set()
    def visit(key):
        if key in busy:
            raise StaticError("REFERENCE_FAIL", str(key), "DEPENDENCY_CYCLE")
        if key in done:
            return
        busy.add(key)
        for child in edges.get(key, []):
            visit(child)
        busy.remove(key)
        done.add(key)
    for key in known:
        visit(key)
    for a in artifacts:
        for r in (node for node in walk(a) if is_ref(node)):
            other = known.get((r["artifact_id"], r["revision"]))
            if other is None:
                raise StaticError("REFERENCE_FAIL", a["artifact_id"], "MISSING_REFERENCE " + r["artifact_id"])
            if (a["book_id"], a["scope_id"]) != (other["book_id"], other["scope_id"]):
                raise StaticError("REFERENCE_FAIL", a["artifact_id"], "ordinary ref must keep same book/scope")
            if r != ref(other):
                raise StaticError("REFERENCE_FAIL", a["artifact_id"], "reference digest/kind mismatch")
        declared = {encoded(r) for r in a["input_refs"]}
        for r in (node for node in walk(a["payload"]) if is_ref(node)):
            if encoded(r) not in declared:
                raise StaticError("REFERENCE_FAIL", a["artifact_id"], "UNDECLARED_INPUT")


def resources_and_hashes(bundle, base):
    for node in walk(bundle):
        if isinstance(node, dict) and {"path", "sha256", "media_type"} <= node.keys():
            relative = node["path"]
            target = (base / relative).resolve()
            if "\\" in relative or ":" in relative or Path(relative).is_absolute() or base not in target.parents:
                raise StaticError("RESOURCE_FAIL", relative, "nonportable/escaping resource path")
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != node["sha256"]:
                raise StaticError("RESOURCE_FAIL", relative, "RESOURCE_HASH_MISMATCH")
    for node in bundle["artifacts"] + bundle["policies"]:
        if node["content_hash"] != content_hash(node):
            raise StaticError("HASH_FAIL", node.get("artifact_id", node.get("policy_id")), "CONTENT_HASH_MISMATCH")


def design_source_fields(bundle, base):
    """Only compare hand-authored fixture declarations, never establish S01 eligibility."""
    for source in (a for a in bundle["artifacts"] if a["kind"] == "SourceBundle"):
        p = source["payload"]
        proof_ref = p["scope_integrity"]["proof"]
        if proof_ref is None:
            continue
        proof = load(base / proof_ref["path"])
        fields = {"book_id": source["book_id"], "scope_id": source["scope_id"], "pages_expected": p["pages_expected"],
                  "pages_acquired": p["pages_acquired"], "scope_manifest": p["scope_manifest"],
                  "assets": [{k: a[k] for k in ("asset_id", "path", "sha256", "width", "height")} for a in p["assets"]]}
        if any(proof.get(k) != v for k, v in fields.items()):
            raise StaticError("DESIGN_FIELD_FAIL", source["artifact_id"], "fixture source/proof declarations differ")
        pages = proof.get("per_page_questions", [])
        if {row["asset_id"] for row in pages} != set(p["pages_expected"]):
            raise StaticError("DESIGN_FIELD_FAIL", source["artifact_id"], "fixture per-page declaration differs")
        if {q for row in pages for q in row["question_ids"]} != set(p["scope_manifest"] or []):
            raise StaticError("DESIGN_FIELD_FAIL", source["artifact_id"], "fixture manifest/per-page question IDs differ")


def design_action_facts(bundle, base, checker):
    """Only structural/byte/exact-reference equality for design event resources."""
    known = {(a["artifact_id"], a["revision"]): a for a in bundle["artifacts"]}
    fact_schema = checker.document("action-fact.schema.json")
    def read_fact(resource):
        file = base / resource["path"]
        value = load(file)
        checker.validate(value, fact_schema, fact_schema)
        for node in walk(value):
            if isinstance(node, dict) and {"path", "sha256", "media_type"} <= node.keys():
                file = (base / node["path"]).resolve()
                if base not in file.parents or not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != node["sha256"]:
                    raise StaticError("RESOURCE_FAIL", resource["path"], "action-fact nested resource mismatch")
            if is_ref(node):
                actual = known.get((node["artifact_id"], node["revision"]))
                if actual is None or ref(actual) != node:
                    raise StaticError("REFERENCE_FAIL", resource["path"], "action-fact exact reference mismatch")
        return value
    for artifact in bundle["artifacts"]:
        p = artifact["payload"]
        if artifact["kind"] == "ExecutionProgress":
            for row in p["actions"]:
                if row["result_fact"] is not None:
                    fact = read_fact(row["result_fact"])
                    if fact["action_id"] != row["action_id"]:
                        raise StaticError("DESIGN_FIELD_FAIL", artifact["artifact_id"], "action/fact identity differs")
        if artifact["kind"] == "ExecutionReceipt":
            facts = [read_fact(r) for r in p["action_fact_refs"]]
            if len(facts) != len(p["results"]) or [f["result"] for f in facts] != p["results"]:
                raise StaticError("DESIGN_FIELD_FAIL", artifact["artifact_id"], "ACTION_FACT_RESULT_MISMATCH")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=HERE)
    args = parser.parse_args()
    base = args.root.resolve()
    checker = SchemaChecker(base)
    for name in ("recovery-exchange.schema.json", "ledger-export.schema.json", "case-file.schema.json", "action-fact.schema.json", "archive-v1.schema.json"):
        checker.check_schema(name)
    manifest = load(base / "case-manifest.json")
    result = {"design_only": True, "static_checks_only": True, "runtime_intent_commits": 0, "runtime_or_recovery_executed": False,
              "synthetic_admission_executed": False, "semantic_cases_executed": 0, "cases": []}
    case_schema = checker.document("case-file.schema.json")
    for case in manifest["cases"]:
        value = load(base / case["path"])
        actual, detail = "PASS", None
        try:
            checker.validate(value, case_schema, case_schema)
            references(value["bundle"])
            resources_and_hashes(value["bundle"], base)
            design_source_fields(value["bundle"], base)
            design_action_facts(value["bundle"], base, checker)
        except StaticError as exc:
            actual, detail = exc.category, {"path": exc.path, "detail": exc.detail}
        result["cases"].append({"case_id": case["case_id"], "expected_static": case["expected_static"], "actual_static": actual,
            "static_expectation_matches": actual == case["expected_static"], "detail": detail,
            "expected_layer": case["expected_layer"], "expected_code": case["expected_code"], "semantic_actual": "NOT_EXECUTED"})
    migration = load(base / "migration-map.json")
    archive = base / migration["archive"]
    result["archive_original_bytes_match"] = len(archive.read_bytes()) == migration["original_size"] and hashlib.sha256(archive.read_bytes()).hexdigest() == migration["original_sha256"]
    archived_schema = checker.document("archive-v1.schema.json")
    result["old_archives_structure_resources_hashes"] = True
    for file in (archive, base / "archive/legacy/input.json"):
        archived = load(file)
        checker.validate(archived, archived_schema, archived_schema)
        references(archived)
        resources_and_hashes(archived, file.parent)
    result["static_expectations_match"] = all(c["static_expectation_matches"] for c in result["cases"])
    result["case_count"] = len(result["cases"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["archive_original_bytes_match"] and result["static_expectations_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
