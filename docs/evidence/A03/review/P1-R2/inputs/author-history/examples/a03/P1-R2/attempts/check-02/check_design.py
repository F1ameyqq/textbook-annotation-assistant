"""DESIGN_ONLY P1-R2 recursive reference and event-prefix audit.

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
from prefix_rules import validate_prefix, canonical_hash

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
                  "exclusiveMinimum", "exclusiveMaximum", "anyOf", "oneOf", "format", "propertyNames", "uniqueItems"}

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
            if schema.get("uniqueItems") and len({encoded(child) for child in value}) != len(value):
                fail("array items not unique")
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


def is_resource(value):
    return isinstance(value, dict) and {"path", "sha256", "media_type"} <= set(value)


def reference_shape(value):
    fields = {"artifact_id", "revision", "kind", "content_hash"}
    if not isinstance(value, dict) or not fields <= set(value):
        return
    if set(value) != fields or not isinstance(value["artifact_id"], str) or not value["artifact_id"] or not isinstance(value["kind"], str) or not value["kind"] or type(value["revision"]) is not int or value["revision"] < 1 or not isinstance(value["content_hash"], str) or re.fullmatch("[0-9a-f]{64}", value["content_hash"]) is None:
        raise StaticError("STRUCTURE_FAIL", "ordinary_ref", "EXACT_FOUR_FIELD_REFERENCE_REQUIRED")


def audit_closure(bundle, base):
    """Static bytes/ref DAG only; parsed bytes never replace consumer declarations.

    Resource and Artifact edges share a cycle graph. For every consumer, recurse
    through all Resource JSON values and recheck its own exact input_refs set.
    The cache holds parsed bytes only; expansion deduplication is per consumer.
    """
    base = base.resolve()
    artifacts = bundle["artifacts"]
    known = {(a["artifact_id"], a["revision"]): a for a in artifacts}
    if len(known) != len(artifacts):
        raise StaticError("REFERENCE_FAIL", "$.bundle.artifacts", "DUPLICATE_ARTIFACT_IDENTITY")
    parsed, graph = {}, {}
    records = bundle.get("evidence", [])
    evidence = {row["evidence_id"]: row["resource"] for row in records}
    if len(evidence) != len(records):
        raise StaticError("REFERENCE_FAIL", "evidence", "DUPLICATE_EVIDENCE_ID")
    evidence_fields = {"evidence_refs", "before_evidence_refs", "after_evidence_refs", "submission_evidence_refs"}

    def evidence_resources(field, child):
        if field in evidence_fields and isinstance(child, list):
            for item in child:
                if isinstance(item, str):
                    if item not in evidence:
                        raise StaticError("REFERENCE_FAIL", field, "MISSING_EVIDENCE_ID " + item)
                    yield evidence[item]

    def resource_node(resource):
        relative = resource["path"]
        target = (base / relative).resolve()
        segments = relative.split("/")
        if ("\\" in relative or ":" in relative or Path(relative).is_absolute() or
                not relative or any(x in ("", ".", "..") for x in segments) or base not in target.parents):
            raise StaticError("RESOURCE_FAIL", relative, "NONPORTABLE_RESOURCE_PATH")
        if not target.is_file():
            raise StaticError("RESOURCE_FAIL", relative, "RESOURCE_NOT_FOUND")
        key = ("resource", relative, resource["media_type"])
        if key not in parsed:
            data = target.read_bytes()
            if hashlib.sha256(data).hexdigest() != resource["sha256"]:
                raise StaticError("RESOURCE_FAIL", relative, "RESOURCE_HASH_MISMATCH")
            parsed[key] = (hashlib.sha256(data).hexdigest(),
                load(target) if resource["media_type"] == "application/json" else None)
        actual_hash, value = parsed[key]
        if actual_hash != resource["sha256"]:
            raise StaticError("RESOURCE_FAIL", relative, "RESOURCE_HASH_MISMATCH")
        return key, value

    def artifact_key(r):
        return ("artifact", r["artifact_id"], r["revision"])

    def edges(value, parent, active_resources):
        reference_shape(value)
        if is_ref(value):
            graph.setdefault(parent, set()).add(artifact_key(value))
        elif is_resource(value):
            key, child = resource_node(value)
            graph.setdefault(parent, set()).add(key)
            if key in active_resources:
                raise StaticError("REFERENCE_FAIL", value["path"], "RESOURCE_REFERENCE_CYCLE")
            if key not in graph:
                graph[key] = set()
                edges(child, key, active_resources | {key})
        elif isinstance(value, dict):
            for field, child in value.items():
                edges(child, parent, active_resources)
                for resource in evidence_resources(field, child):
                    edges(resource, parent, active_resources)
        elif isinstance(value, list):
            for child in value:
                edges(child, parent, active_resources)

    for artifact in artifacts:
        key = artifact_key(artifact)
        graph.setdefault(key, set())
        for field, child in artifact.items():
            if field != "content_hash":
                edges(child, key, set())
    edges(bundle.get("evidence", []), ("diagnostic",), set())
    busy, done = set(), set()
    def visit(key):
        if key in busy:
            raise StaticError("REFERENCE_FAIL", str(key), "REFERENCE_CYCLE")
        if key in done:
            return
        busy.add(key)
        for child in graph.get(key, set()):
            visit(child)
        busy.remove(key)
        done.add(key)
    for key in graph:
        visit(key)

    def consume(value, consumer, declared, seen_resources, where):
        reference_shape(value)
        if is_ref(value):
            actual = known.get((value["artifact_id"], value["revision"]))
            if actual is None:
                raise StaticError("REFERENCE_FAIL", where, "MISSING_REFERENCE " + value["artifact_id"])
            if consumer is not None and consumer["book_id"] != actual["book_id"]:
                raise StaticError("REFERENCE_FAIL", where, "REFERENCE_SCOPE_MISMATCH book")
            if consumer is not None and consumer["scope_id"] != actual["scope_id"]:
                raise StaticError("REFERENCE_FAIL", where, "REFERENCE_SCOPE_MISMATCH scope")
            if consumer is not None and consumer["schema_version"] != actual["schema_version"]:
                raise StaticError("REFERENCE_FAIL", where, "REFERENCE_SCOPE_MISMATCH namespace")
            if value != ref(actual):
                raise StaticError("REFERENCE_FAIL", where, "REFERENCE_HASH_MISMATCH exact_four_tuple")
            if consumer is not None and encoded(value) not in declared:
                raise StaticError("REFERENCE_FAIL", where, "UNDECLARED_RESOURCE_REFERENCE")
        elif is_resource(value):
            key, child = resource_node(value)
            if key not in seen_resources:
                seen_resources.add(key)
                consume(child, consumer, declared, seen_resources, where + "->" + value["path"])
        elif isinstance(value, dict):
            for field, child in value.items():
                consume(child, consumer, declared, seen_resources, where + "." + field)
                for resource in evidence_resources(field, child):
                    consume(resource, consumer, declared, seen_resources, where + "." + field + "[EvidenceRecord]")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                consume(child, consumer, declared, seen_resources, where + "[" + str(index) + "]")
    for artifact in artifacts:
        declared = {encoded(r) for r in artifact["input_refs"]}
        seen = set()
        for field, child in artifact.items():
            if field != "content_hash":
                consume(child, artifact, declared, seen, artifact["artifact_id"] + "." + field)
    consume(bundle.get("evidence", []), None, set(), set(), "evidence")
    for artifact in artifacts + bundle["policies"]:
        if artifact["content_hash"] != content_hash(artifact):
            raise StaticError("HASH_FAIL", artifact.get("artifact_id", artifact.get("policy_id")), "CONTENT_HASH_MISMATCH")


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
    basis_schema = checker.document("unattempted-basis.schema.json")
    def read_fact(resource):
        file = base / resource["path"]
        value = load(file)
        checker.validate(value, fact_schema, fact_schema)
        if value["origin_phase"] == "UNATTEMPTED_ABSENCE":
            basis = load(base / value["unattempted_basis"]["path"])
            checker.validate(basis, basis_schema, basis_schema)
            if (basis["plan_ref"] != value["plan_ref"] or basis["action_id"] != value["action_id"] or
                    basis["action_digest"] != value["action_digest"] or basis["expected_event_head"]["sequence"] + 1 != value["journal_sequence"] or
                    basis["expected_event_head"]["hash"] != value["predecessor_hash"] or
                    basis["readonly_prepared_ref"] != value["prepared_before"] or basis["second_observation_ref"] != value["readback"]):
                raise StaticError("DESIGN_FIELD_FAIL", resource["path"], "UNATTEMPTED_BASIS_FIELD_MISMATCH")
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


def design_prefixes(case, base, prefix_schema_checker):
    """Read actual prefix bytes; no expected labels drive any validator branch.

    Candidate neighbors keep the valid basis graph as context. Their separate
    candidate_uncalled_prefix is the tested input, not proof of a committed
    failed fact. Serialized cross-bindings do not qualify a current local DB.
    """
    artifacts = case["bundle"]["artifacts"]
    known = {(a["artifact_id"], a["revision"]): a for a in artifacts}
    plans = {a["artifact_id"]: a for a in artifacts if a["kind"] == "ApplyPlan"}
    checks, seen = [], set()
    schema = prefix_schema_checker.document("event-prefix.schema.json")

    def resource_value(resource):
        relative = resource["path"]
        path = (base / relative).resolve()
        if base not in path.parents or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != resource["sha256"]:
            raise StaticError("RESOURCE_FAIL", relative, "PREFIX_RESOURCE_BYTES_MISMATCH")
        return load(path)

    def event_bodies(prefix):
        for event in prefix["events"]:
            name, payload = event["event"], event["payload"]
            if name == "WRITE_INTENT_COMMITTED":
                intent = known[(payload["intent_ref"]["artifact_id"], payload["intent_ref"]["revision"])]
                p = intent["payload"]
                derived = "obl-" + canonical_hash({"journal_id": p["journal_id"], "target_key": p["target_key"],
                    "intent_ref": ref(intent), "journal_sequence": p["journal_sequence"], "journal_head_hash": p["journal_head_hash"]})
                if (p["journal_sequence"] != event["sequence"] or p["journal_head_hash"] != event["previous_hash"] or
                    p["intent_committed_at"] != event["recorded_at"] or p["plan_ref"] != event["plan_ref"] or
                    p["target_key"] != event["target_key"] or p["owner_id"] != event["owner_id"] or
                    p["generation"] != event["generation"] or p["action_id"] != payload["action_id"] or
                    p["action_digest"] != payload["action_digest"] or payload["obligation_id"] != derived):
                    raise StaticError("PREFIX_FAIL", str(event["sequence"]), "PREFIX_INTENT_BODY_MISMATCH")
            if name in ("ACTION_RESULT_COMMITTED", "UNATTEMPTED_ABSENCE_COMMITTED"):
                fact = resource_value(payload["fact"])
                if (fact["journal_sequence"] != event["sequence"] or fact["predecessor_hash"] != event["previous_hash"] or
                    fact["plan_ref"] != event["plan_ref"] or fact["action_id"] != payload["action_id"] or
                    fact["action_digest"] != payload["action_digest"] or fact["result"]["outcome"] != payload["outcome"]):
                    raise StaticError("PREFIX_FAIL", str(event["sequence"]), "PREFIX_FACT_BODY_MISMATCH")
                if name == "ACTION_RESULT_COMMITTED" and (fact["origin_phase"] != "EXECUTION" or
                    fact["intent_ref"] != payload["intent_ref"] or fact["obligation_id"] != payload["obligation_id"]):
                    raise StaticError("PREFIX_FAIL", str(event["sequence"]), "PREFIX_RESULT_BODY_MISMATCH")
                if name == "UNATTEMPTED_ABSENCE_COMMITTED" and (fact["origin_phase"] != "UNATTEMPTED_ABSENCE" or
                    fact["intent_ref"] is not None or fact["obligation_id"] is not None or fact["resolution_ref"] is not None):
                    raise StaticError("PREFIX_FAIL", str(event["sequence"]), "PREFIX_UNATTEMPTED_BODY_MISMATCH")

    def check_fact(resource):
        if resource["path"] in seen:
            return
        seen.add(resource["path"])
        fact = resource_value(resource)
        if fact["origin_phase"] != "UNATTEMPTED_ABSENCE":
            return
        basis = resource_value(fact["unattempted_basis"])
        prefix_resource = basis["complete_uncalled_prefix"]
        prefix = resource_value(prefix_resource)
        prefix_schema_checker.validate(prefix, schema, schema)
        plan = plans[basis["plan_ref"]["artifact_id"]]
        errors = validate_prefix(prefix, plan, basis["expected_event_head"], basis["action_id"])
        checks.append({"resource": prefix_resource, "subject_action_id": basis["action_id"],
                       "through_sequence": prefix.get("through_sequence"), "errors": errors})
        if errors:
            raise StaticError("PREFIX_FAIL", prefix_resource["path"], ",".join(errors))
        event_bodies(prefix)

    for artifact in artifacts:
        if artifact["kind"] == "ExecutionReceipt":
            for resource in artifact["payload"]["action_fact_refs"]:
                check_fact(resource)
        if artifact["kind"] == "ExecutionProgress":
            for row in artifact["payload"]["actions"]:
                if row["result_fact"] is not None:
                    check_fact(row["result_fact"])
    candidate_checks = []
    candidate_resource = case.get("runtime_claim", {}).get("candidate_uncalled_prefix")
    if candidate_resource is not None:
        prefix = resource_value(candidate_resource)
        prefix_schema_checker.validate(prefix, schema, schema)
        plan = plans[prefix["plan_ref"]["artifact_id"]]
        # Candidate-specific head binds exactly those supplied bytes. For the
        # delete-and-rechain neighbors it deliberately differs from valid basis.
        errors = validate_prefix(prefix, plan, {"sequence": prefix["through_sequence"], "hash": prefix["head_hash"]}, prefix["subject_action_id"])
        candidate_checks.append({"resource": candidate_resource, "through_sequence": prefix["through_sequence"],
                                 "errors": errors, "runtime_actual": "NOT_EXECUTED"})
    return checks, candidate_checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=HERE)
    args = parser.parse_args()
    base = args.root.resolve()
    checker = SchemaChecker(base)
    for name in ("recovery-exchange.schema.json", "ledger-export.schema.json", "case-file.schema.json", "action-fact.schema.json", "archive-v1.schema.json", "unattempted-basis.schema.json"):
        checker.check_schema(name)
    manifest = load(base / "case-manifest.json")
    result = {"design_only": True, "static_checks_only": True, "runtime_intent_commits": 0, "runtime_or_recovery_executed": False,
              "synthetic_admission_executed": False, "semantic_cases_executed": 0, "cases": []}
    case_schema = checker.document("case-file.schema.json")
    prefix_checker = SchemaChecker(HERE)
    prefix_checker.check_schema("event-prefix.schema.json")
    for case in manifest["cases"]:
        value = load(base / case["path"])
        actual, detail = "PASS", None
        prefix_checks, candidate_checks = [], []
        try:
            checker.validate(value, case_schema, case_schema)
            audit_closure(value["bundle"], base)
            design_source_fields(value["bundle"], base)
            design_action_facts(value["bundle"], base, checker)
            prefix_checks, candidate_checks = design_prefixes(value, base, prefix_checker)
            # The new neighbors explicitly supply a candidate resource. Its
            # computed errors, never the manifest's expected label, determine
            # the static finding. The original R1 incomplete-prefix example
            # retains its historical PASS structural classification and has a
            # separately reported actual candidate-prefix finding below.
            if value["case_id"].startswith("prefix-") and candidate_checks and candidate_checks[0]["errors"]:
                raise StaticError("PREFIX_FAIL", candidate_checks[0]["resource"]["path"], ",".join(candidate_checks[0]["errors"]))
        except StaticError as exc:
            actual, detail = exc.category, {"path": exc.path, "detail": exc.detail}
        result["cases"].append({"case_id": case["case_id"], "expected_static": case["expected_static"], "actual_static": actual,
            "static_expectation_matches": actual == case["expected_static"], "detail": detail,
            "expected_layer": case["expected_layer"], "expected_code": case["expected_code"], "semantic_actual": "NOT_EXECUTED"})
        result["cases"][-1]["basis_prefix_checks"] = prefix_checks
        result["cases"][-1]["candidate_prefix_checks"] = candidate_checks
    migration = load(base / "migration-map.json")
    archive = base / migration["archive"]
    result["archive_original_bytes_match"] = len(archive.read_bytes()) == migration["original_size"] and hashlib.sha256(archive.read_bytes()).hexdigest() == migration["original_sha256"]
    archived_schema = checker.document("archive-v1.schema.json")
    result["old_archives_structure_resources_hashes"] = True
    for file in (archive, base / "archive/legacy/input.json"):
        archived = load(file)
        checker.validate(archived, archived_schema, archived_schema)
        audit_closure(archived, file.parent)
    result["static_expectations_match"] = all(c["static_expectation_matches"] for c in result["cases"])
    result["case_count"] = len(result["cases"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["archive_original_bytes_match"] and result["static_expectations_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
