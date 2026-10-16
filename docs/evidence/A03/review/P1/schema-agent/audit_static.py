"""Independent offline P1 declaration audit. No runtime/recovery execution.

Uses only stdlib and a local, explicitly bounded JSON Schema assertion subset;
it does not claim full standards-validator coverage. Input files are read-only.
"""
import argparse
import copy
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True


def load(path):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate JSON key: " + key)
            out[key] = value
        return out
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def is_ref(value):
    return isinstance(value, dict) and set(value) == {"artifact_id", "revision", "kind", "content_hash"}


def exact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class LocalAssertions:
    """Independent evaluator of only the assertions actually present in P1."""
    annotations = {"$id", "$schema", "$defs", "$comment", "title", "description", "default", "discriminator"}
    assertions = {"$ref", "type", "const", "enum", "required", "properties", "additionalProperties", "items",
                  "minItems", "maxItems", "minProperties", "maxProperties", "minLength", "maxLength", "pattern",
                  "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "anyOf", "oneOf", "format", "propertyNames"}

    def __init__(self, base):
        self.documents = {p.name: load(p) for p in base.glob("*.schema.json")}

    def resolve(self, value, root):
        file, _, fragment = value.partition("#")
        if file:
            if Path(file).name != file or file not in self.documents:
                raise ValueError("nonlocal schema reference: " + value)
            root = self.documents[file]
        target = root
        if fragment:
            if not fragment.startswith("/"):
                raise ValueError("unsupported fragment: " + fragment)
            for part in fragment[1:].split("/"):
                target = target[part.replace("~1", "/").replace("~0", "~")]
        return target, root

    def check(self, value, schema, root, path="$"):
        errors = []
        def add(why):
            errors.append({"path": path, "reason": why})
        if schema is True:
            return errors
        if schema is False:
            return [{"path": path, "reason": "false schema"}]
        unknown = set(schema) - self.annotations - self.assertions
        if unknown:
            raise ValueError("unreviewed schema assertions: " + str(sorted(unknown)))
        if "$ref" in schema:
            target, target_root = self.resolve(schema["$ref"], root)
            errors.extend(self.check(value, target, target_root, path))
        if "anyOf" in schema and not any(not self.check(value, branch, root, path) for branch in schema["anyOf"]):
            add("anyOf no accepted branch")
        if "oneOf" in schema:
            accepted = sum(not self.check(value, branch, root, path) for branch in schema["oneOf"])
            if accepted != 1:
                add("oneOf accepted branches=" + str(accepted))
        if "const" in schema and exact(value) != exact(schema["const"]):
            add("const mismatch")
        if "enum" in schema and exact(value) not in [exact(v) for v in schema["enum"]]:
            add("enum mismatch")
        expected = schema.get("type")
        matches = {"null": value is None, "boolean": isinstance(value, bool), "string": isinstance(value, str),
                   "array": isinstance(value, list), "object": isinstance(value, dict),
                   "integer": isinstance(value, int) and not isinstance(value, bool),
                   "number": isinstance(value, (int, float)) and not isinstance(value, bool)}
        if expected and not any(matches.get(t, False) for t in (expected if isinstance(expected, list) else [expected])):
            add("type mismatch")
        if isinstance(value, dict):
            for key in schema.get("required", []):
                if key not in value:
                    add("missing required field " + key)
            if len(value) < schema.get("minProperties", 0) or len(value) > schema.get("maxProperties", float("inf")):
                add("property count")
            properties = schema.get("properties", {})
            for key, child in value.items():
                if "propertyNames" in schema:
                    errors.extend(self.check(key, schema["propertyNames"], root, path + ".<key>"))
                child_schema = properties.get(key, schema.get("additionalProperties", True))
                errors.extend(self.check(child, child_schema, root, path + "." + key))
        if isinstance(value, list):
            if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", float("inf")):
                add("array count")
            if "items" in schema:
                for n, child in enumerate(value):
                    errors.extend(self.check(child, schema["items"], root, path + "[" + str(n) + "]"))
        if isinstance(value, str):
            if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", float("inf")):
                add("string length")
            if "pattern" in schema and re.search(schema["pattern"], value) is None:
                add("pattern mismatch")
            if schema.get("format") == "date-time":
                try:
                    if datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is None:
                        add("date-time has no timezone")
                except ValueError:
                    add("invalid date-time")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if value < schema.get("minimum", -float("inf")) or value > schema.get("maximum", float("inf")):
                add("numeric range")
            if value <= schema.get("exclusiveMinimum", -float("inf")) or value >= schema.get("exclusiveMaximum", float("inf")):
                add("exclusive numeric range")
        return errors


def nested_resource_refs(base, resource, seen=None):
    seen = set() if seen is None else seen
    path = (base / resource["path"]).resolve()
    if base not in path.parents:
        raise ValueError("resource escaped fixture directory")
    if path in seen:
        return []
    seen.add(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != resource["sha256"]:
        raise ValueError("resource hash mismatch: " + resource["path"])
    if resource["media_type"] != "application/json":
        return []
    value = load(path)
    refs = [node for node in walk(value) if is_ref(node)]
    for node in walk(value):
        if isinstance(node, dict) and {"path", "sha256", "media_type"} <= set(node):
            refs.extend(nested_resource_refs(base, node, seen))
    return refs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    stage = args.stage.resolve()
    base = stage / "examples/a03/P1"
    out = args.out.resolve()
    allowed = Path(r"D:/1800/docs/evidence/A03/review/P1/schema-agent").resolve()
    if out != allowed:
        raise SystemExit("output must be the assigned evidence directory")
    out.mkdir(exist_ok=True, parents=True)
    checker = LocalAssertions(base)
    manifest = load(base / "case-manifest.json")
    summary = {"input_commit": "2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9", "design_only": True,
               "recovery_execution": "NOT_RUN", "full_standards_jsonschema": "NOT_RUN: unavailable in Python39/311/312",
               "local_assertion_subset": "Only exact assertions present in frozen P1, independent of author checker",
               "cases": [], "positive_resource_closure_violations": [], "migration_identity_pairs": []}
    case_schema = checker.documents["case-file.schema.json"]
    fact_schema = checker.documents["action-fact.schema.json"]
    positives = {"normal", "intent-no-receipt-match", "intent-no-receipt-absent", "partial-without-absent",
                 "partial-with-complete-absent", "conflict", "indeterminate", "original-unknown-preserved",
                 "recovered-report-binding", "new-read-unchanged-state-version", "cross-scope-only-one-resolved",
                 "source-only-zero-actions"}
    for entry in manifest["cases"]:
        value = load(base / entry["path"])
        errors = checker.check(value, case_schema, case_schema)
        case_result = {"case_id": entry["case_id"], "shape_accepted": not errors,
                       "expected_structure_failure": entry["expected_static"] == "STRUCTURE_FAIL",
                       "shape_matches_expected": bool(errors) == (entry["expected_static"] == "STRUCTURE_FAIL"),
                       "first_shape_error": errors[0] if errors else None,
                       "fact_shape_errors": []}
        for artifact in value["bundle"]["artifacts"]:
            if artifact["kind"] not in {"ExecutionReceipt", "ExecutionProgress"}:
                continue
            declared = {exact(ref) for ref in artifact["input_refs"]}
            resources = (artifact["payload"]["action_fact_refs"] if artifact["kind"] == "ExecutionReceipt" else
                         [row["result_fact"] for row in artifact["payload"]["actions"] if row["result_fact"] is not None])
            for resource in resources:
                fact = load(base / resource["path"])
                fact_errors = checker.check(fact, fact_schema, fact_schema)
                case_result["fact_shape_errors"].extend(fact_errors)
                if entry["case_id"] not in positives:
                    continue
                for nested_ref in nested_resource_refs(base, resource):
                    if exact(nested_ref) not in declared:
                        issue = {"case_id": entry["case_id"], "consumer": artifact["artifact_id"],
                                 "consumer_kind": artifact["kind"], "resource": resource["path"],
                                 "missing_input_ref": nested_ref, "expected_rule": "UNDECLARED_INPUT (proposal:106/API:984)"}
                        if issue not in summary["positive_resource_closure_violations"]:
                            summary["positive_resource_closure_violations"].append(issue)
        summary["cases"].append(case_result)
    migration = load(base / "migration-map.json")
    for pair in migration["mappings"]:
        summary["migration_identity_pairs"].append({"old": pair["old"], "new": pair["new"],
            "same_id_revision_kind": all(pair["old"][k] == pair["new"][k] for k in ["artifact_id", "revision", "kind"]),
            "different_content_hash": pair["old"]["content_hash"] != pair["new"]["content_hash"]})
    summary["case_count"] = len(summary["cases"])
    summary["all_shape_expectations_match"] = all(row["shape_matches_expected"] for row in summary["cases"])
    summary["all_referenced_fact_shapes_accepted"] = all(not row["fact_shape_errors"] for row in summary["cases"])
    summary["closure_affected_positive_cases"] = sorted({row["case_id"] for row in summary["positive_resource_closure_violations"]})
    # Deliberately call only the inspected author's local static functions; no main,
    # generator, business modules, target, runtime, SQLite, network or recovery.
    spec = importlib.util.spec_from_file_location("frozen_design_checker", base / "check_design.py")
    author = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(author)
    normal = load(base / "cases/normal.json")
    local = author.SchemaChecker(base)
    author.references(normal["bundle"])
    author.design_action_facts(normal["bundle"], base, local)
    summary["author_static_normal_resource_reference_check"] = "PASS despite missing consumer input declarations"
    receipt = next(a for a in normal["bundle"]["artifacts"] if a["kind"] == "ExecutionReceipt")
    fact_resource = receipt["payload"]["action_fact_refs"][0]
    fact = load(base / fact_resource["path"])
    minimal = {"design_only": True, "input_commit": summary["input_commit"], "source_case": "cases/normal.json",
               "consumer": {k: copy.deepcopy(receipt[k]) for k in ["artifact_id", "kind", "input_refs"]},
               "fact_resource": fact_resource, "fact": fact,
               "undeclared_ref": fact["observed_snapshot_ref"],
               "authority": ["docs/a03-recovery-contract-v1-proposal.md:106", "examples/a03/P1/api-proposal.json:984"],
               "author_static_actual": "PASS", "independent_declaration_actual": "UNDECLARED_INPUT",
               "functional_recovery_result": "NOT_RUN"}
    (out / "minimal-normal-resource-ref.json").write_text(json.dumps(minimal, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (out / "audit-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ["case_count", "all_shape_expectations_match", "all_referenced_fact_shapes_accepted",
        "closure_affected_positive_cases", "author_static_normal_resource_reference_check", "recovery_execution"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
