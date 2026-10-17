"""Independent, offline P1-R1 mapping/profile/schema audit; no runtime imports.

LocalAssertions below is retained from the independent P1 review evaluator,
not from the author checker. Only its finite assertion subset is evaluated.
"""
import argparse
from datetime import datetime
import hashlib
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


def exact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LocalAssertions:
    """Explicit subset; unknown assertions fail closed rather than get ignored."""
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


def projection(value, base, seen=()):
    """Review aid only: strip resealed hash/input declarations; inline resources.

    Does not assert retention of hash-based attacks. Those get separate checks.
    """
    if isinstance(value, dict):
        if {"path", "sha256", "media_type"} <= set(value):
            path = (base / value["path"]).resolve()
            safe = base.resolve() in path.parents
            resource = {k: v for k, v in value.items() if k not in {"path", "sha256"}}
            if safe and path.is_file() and value["media_type"] == "application/json" and path not in seen:
                resource["RESOURCE_BODY"] = projection(load(path), base, seen + (path,))
            elif safe and path.is_file():
                resource["BINARY_SHA"] = digest(path)
            else:
                resource["UNRESOLVED_PATH"] = value["path"]
            return resource
        return {k: projection(v, base, seen) for k, v in value.items() if k not in {"content_hash", "input_refs", "unattempted_basis"}}
    if isinstance(value, list):
        if value and all(isinstance(v, dict) and {"artifact_id", "revision", "kind", "payload"} <= set(v) for v in value):
            return {v["artifact_id"] + "@" + str(v["revision"]): projection(v, base, seen) for v in value}
        return [projection(v, base, seen) for v in value]
    return value


def diffs(a, b, path="$"):
    if type(a) is not type(b):
        return [{"path": path, "old": a, "new": b}]
    if isinstance(a, dict):
        out = []
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                out.append({"path": path + "." + key, "old": a.get(key, "<MISSING>"), "new": b.get(key, "<MISSING>")})
            else:
                out.extend(diffs(a[key], b[key], path + "." + key))
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [{"path": path, "old_count": len(a), "new_count": len(b)}]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in diffs(x, y, path + "[" + str(i) + "]")]
    return [] if a == b else [{"path": path, "old": a, "new": b}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    stage, out = args.stage.resolve(), args.out.resolve()
    allowed = Path("D:/1800/docs/evidence/A03/review/P1-R1/mapping-agent").resolve()
    if out != allowed:
        raise SystemExit("output outside assignment")
    out.mkdir(parents=True, exist_ok=True)
    old, package = stage / "examples/a03/P1", stage / "examples/a03/P1-R1"
    base = package / "data"
    oldm, newm, mapping = [load(p) for p in [old / "case-manifest.json", base / "case-manifest.json", base / "case-mapping.json"]]
    oldidx = {x["case_id"]: x for x in oldm["cases"]}
    newidx = {x["case_id"]: x for x in newm["cases"]}
    results = {"input_commit": "ca4fba4f505467228a8164c3999e0cecc54ffc4e", "design_commit": "095ed4aa18a56100ce3aabc4a0d6885ad37ab520",
               "design_only": True, "recovery_execution": "NOT_RUN", "runtime_or_business_imports": 0,
               "author_checker_imports_or_calls": 0, "network_platform_browser_credentials_ocr_model_api_operations": 0,
               "validator_scope": "Finite LocalAssertions from previous independent P1 review; not full JSON Schema certification",
               "mapping": [], "profile": [], "json_syntax": [], "local_schema_cases": [], "projection_diffs": []}
    for p in sorted(base.rglob("*.json")):
        load(p)
        results["json_syntax"].append({"path": p.relative_to(base).as_posix(), "sha256": digest(p)})
    api = load(package / "api-proposal.json")
    results["json_syntax"].append({"path": "../api-proposal.json", "sha256": digest(package / "api-proposal.json")})
    profile = api["candidate_profile"]
    for name, entry in profile["schema_files"].items():
        p = package / entry["path"]
        results["profile"].append({"schema": name, "declared_sha256": entry["sha256"], "actual_sha256": digest(p), "matches": digest(p) == entry["sha256"]})
    results["profile_selection"] = profile["selection"]
    results["unchanged_version_strings"] = {k: api[k] == load(old / "api-proposal.json")[k] for k in ["schema_version", "exchange_version"]}
    results["all_schema_files_pinned"] = set(profile["schema_files"]) == {p.name for p in base.glob("*.schema.json")}
    local = LocalAssertions(base)
    for entry in newm["cases"]:
        value = load(base / entry["path"])
        errors = local.check(value, local.documents["case-file.schema.json"], local.documents["case-file.schema.json"])
        seen = set()
        resource_errors = []
        def resources(obj):
            for node in walk(obj):
                if not (isinstance(node, dict) and {"path", "sha256", "media_type"} <= set(node)):
                    continue
                p = (base / node["path"]).resolve()
                if p in seen or base.resolve() not in p.parents or not p.is_file() or node["media_type"] != "application/json":
                    continue
                seen.add(p)
                child = load(p)
                if child.get("format_version") in {"a03-action-fact-1", "a03-unattempted-basis-1"}:
                    schema_name = "action-fact.schema.json" if child["format_version"] == "a03-action-fact-1" else "unattempted-basis.schema.json"
                    errs = local.check(child, local.documents[schema_name], local.documents[schema_name])
                    resource_errors.extend([{"resource": p.relative_to(base).as_posix(), **e} for e in errs])
                resources(child)
        resources(value)
        structural_failed = bool(errors or resource_errors)
        results["local_schema_cases"].append({"case_id": entry["case_id"], "case_errors": errors, "resource_errors": resource_errors,
                  "expected_structure_failure": entry["expected_static"] == "STRUCTURE_FAIL", "matches_expected": structural_failed == (entry["expected_static"] == "STRUCTURE_FAIL")})
    for row in mapping["mappings"]:
        o, n = oldidx[row["old_case_id"]], newidx[row["r1_case_id"]]
        oldpath, newpath = old / row["old_path"], base / row["r1_path"]
        results["mapping"].append({"case_id": row["old_case_id"], "old_actual_sha256": digest(oldpath), "new_actual_sha256": digest(newpath),
                    "byte_hashes_match": digest(oldpath) == row["old_sha256"] and digest(newpath) == row["r1_sha256"],
                    "expected_layer_preserved": o["expected_layer"] == row["expected_layer"] == n["expected_layer"],
                    "expected_code_preserved": o["expected_code"] == row["expected_code"] == n["expected_code"],
                    "expected_static_preserved": o["expected_static"] == n["expected_static"],
                    "source_id_match": n["source_P1_case_id"] == o["case_id"],
                    "old_semantic_execution": o.get("semantic_execution"), "new_semantic_execution": n.get("semantic_execution")})
        changes = diffs(projection(load(oldpath), old), projection(load(newpath), base))
        results["projection_diffs"].append({"case_id": row["old_case_id"], "differences": changes})
    migration = load(base / "migration-map.json")
    oldarchive, normal = load(base / migration["archive"]), load(base / "cases/normal.json")["bundle"]
    archiveidx = {a["artifact_id"]: a for a in oldarchive["artifacts"]}
    normalidx = {a["artifact_id"]: a for a in normal["artifacts"]}
    results["migration"] = {"namespace_fields": migration["namespace_fields"], "future_index_key": migration["future_index_key"], "rows": []}
    for row in migration["mappings"]:
        oa, na = archiveidx[row["old"]["artifact_id"]], normalidx[row["new"]["artifact_id"]]
        oldns = "schema:" + oa["schema_version"] + "/exchange:" + oldarchive["format_version"]
        newns = "schema:" + na["schema_version"] + "/exchange:" + normal["format_version"]
        results["migration"]["rows"].append({"artifact_id": oa["artifact_id"],
                    "old_ref_matches": all(oa[k] == v for k, v in row["old"].items()),
                    "new_ref_matches": all(na[k] == v for k, v in row["new"].items()),
                    "namespace_matches": row["old_namespace"] == oldns and row["new_namespace"] == newns,
                    "namespace_differs": oldns != newns, "same_local_id_revision_kind": all(row["old"][k] == row["new"][k] for k in ["artifact_id", "revision", "kind"])})
    results["case_counts"] = {"old": len(oldm["cases"]), "new": len(newm["cases"]), "mapping": len(mapping["mappings"]),
                     "old_ids_mapped_once": sorted(oldidx) == sorted(r["old_case_id"] for r in mapping["mappings"]),
                     "new_mapping_injective": len({r["r1_case_id"] for r in mapping["mappings"]}) == len(mapping["mappings"])}
    results["summary"] = {"json_syntax_count": len(results["json_syntax"]), "all_mapping_bytes_layers_codes_sources_match": all(all(r[k] for k in ["byte_hashes_match", "expected_layer_preserved", "expected_code_preserved", "expected_static_preserved", "source_id_match"]) for r in results["mapping"]),
                     "all_case_and_referenced_fact_basis_shape_expectations_match": all(r["matches_expected"] for r in results["local_schema_cases"]),
                     "profile_hashes_match": all(r["matches"] for r in results["profile"]),
                     "case_projection_diffs_require_human_review": sum(bool(r["differences"]) for r in results["projection_diffs"])}
    (out / "audit-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"case_counts": results["case_counts"], **results["summary"]}, ensure_ascii=False, indent=2))
    return 0 if all(results["summary"][k] for k in ["all_mapping_bytes_layers_codes_sources_match", "all_case_and_referenced_fact_basis_shape_expectations_match", "profile_hashes_match"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
