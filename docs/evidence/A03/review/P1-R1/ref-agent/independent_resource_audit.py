"""Independent stdlib-only A03 P1-R1 static resource-closure review.

Reads the exact exported Git tree. Does not import project/checker code for its
own audit. The separately labelled differential experiment imports only the
author's static audit_closure, never runtime/src code. Future API semantics are
NOT_EXECUTED. Outputs and constructed counterexamples stay in this directory.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import shutil
import sys

FIELDS = {"artifact_id", "revision", "kind", "content_hash"}
RESOURCE = {"path", "sha256", "media_type"}
FORMAL_EVIDENCE = {"evidence_refs", "before_evidence_refs", "after_evidence_refs", "submission_evidence_refs"}


def load(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def seal(value):
    return hashlib.sha256(canonical({k: v for k, v in value.items() if k != "content_hash"}).encode("utf-8")).hexdigest()


def artifact_ref(value):
    return {k: value[k] for k in FIELDS}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Audit:
    """Independent collect-all-error traversal; no author's code is used here."""
    def __init__(self, bundle, root):
        self.bundle, self.root = bundle, root.resolve()
        self.errors, self.edges, self.resources, self.consumers = [], {}, set(), []
        self.by_id = {}
        for index, artifact in enumerate(bundle["artifacts"]):
            self.by_id.setdefault((artifact["artifact_id"], artifact["revision"]), []).append(artifact)
        rows = bundle.get("evidence", [])
        self.evidence = {r["evidence_id"]: r["resource"] for r in rows}
        if len(self.evidence) != len(rows):
            self.error("DUPLICATE_EVIDENCE_ID", "bundle.evidence")

    def error(self, code, where, detail=None):
        entry = {"code": code, "where": where}
        if detail is not None:
            entry["detail"] = detail
        if entry not in self.errors:
            self.errors.append(entry)

    def add_edge(self, parent, child):
        self.edges.setdefault(parent, set()).add(child)

    def resource(self, value, where):
        relative = value["path"]
        if (not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative or
                relative.startswith("/") or any(x in ("", ".", "..") for x in relative.split("/"))):
            self.error("NONPORTABLE_RESOURCE_PATH", where, relative)
            return None
        path = (self.root / PurePosixPath(relative)).resolve()
        if self.root not in path.parents:
            self.error("NONPORTABLE_RESOURCE_PATH", where, relative)
            return None
        if not path.is_file():
            self.error("RESOURCE_NOT_FOUND", where, relative)
            return None
        digest = sha(path)
        self.resources.add((relative, digest))
        if digest != value["sha256"]:
            self.error("RESOURCE_HASH_MISMATCH", where, relative)
            return None
        key = "R:" + relative + ":" + digest
        if value["media_type"] == "application/json":
            try:
                return key, load(path)
            except (ValueError, UnicodeDecodeError) as exc:
                self.error("RESOURCE_JSON_INVALID", where, str(exc))
                return None
        return key, None

    def walk(self, value, consumer, parent, seen, stack, where, found):
        if isinstance(value, dict):
            if FIELDS <= value.keys():
                if set(value) != FIELDS:
                    self.error("EXACT_FOUR_FIELD_REFERENCE_REQUIRED", where)
                    return
                found.add(canonical(value))
                choices = self.by_id.get((value["artifact_id"], value["revision"]), [])
                if not choices:
                    self.error("MISSING_REFERENCE", where, value["artifact_id"])
                    return
                scoped = [a for a in choices if a["book_id"] == consumer["book_id"] and a["scope_id"] == consumer["scope_id"]]
                if not scoped:
                    self.error("REFERENCE_SCOPE_MISMATCH", where, value["artifact_id"])
                    return
                # Identity edges are recorded before exact hash checks so an
                # impossible hash fixed point cannot hide a self/mixed cycle.
                self.add_edge(parent, "A:" + value["artifact_id"] + ":" + str(value["revision"]))
                exact = [a for a in scoped if artifact_ref(a) == value and a["schema_version"] == consumer["schema_version"]]
                if len(exact) != 1:
                    self.error("REFERENCE_HASH_OR_IDENTITY_MISMATCH", where, value["artifact_id"])
                    return
                return
            if RESOURCE <= value.keys():
                resolved = self.resource(value, where)
                if resolved is None:
                    return
                key, payload = resolved
                self.add_edge(parent, key)
                if key in stack:
                    self.error("RESOURCE_REFERENCE_CYCLE", where)
                    return
                if key not in seen:
                    seen.add(key)
                    self.walk(payload, consumer, key, seen, stack + (key,), where + "->" + value["path"], found)
                return
            for field, child in value.items():
                self.walk(child, consumer, parent, seen, stack, where + "." + field, found)
                if field in FORMAL_EVIDENCE and isinstance(child, list):
                    for item in child:
                        if isinstance(item, str):
                            if item not in self.evidence:
                                self.error("MISSING_EVIDENCE_ID", where + "." + field, item)
                            else:
                                self.walk(self.evidence[item], consumer, parent, seen, stack,
                                          where + "." + field + "[" + item + "]", found)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self.walk(child, consumer, parent, seen, stack, where + "[" + str(index) + "]", found)

    def run(self):
        for artifact in self.bundle["artifacts"]:
            found = set()
            declared = {canonical(r) for r in artifact["input_refs"]}
            root = "A:" + artifact["artifact_id"] + ":" + str(artifact["revision"])
            # Envelope is not itself an ArtifactRef. Every field is traversed.
            for field, value in artifact.items():
                if field != "content_hash":
                    self.walk(value, artifact, root, set(), (), artifact["artifact_id"] + "." + field, found)
            missing = sorted(found - declared)
            for reference in missing:
                self.error("UNDECLARED_RESOURCE_REFERENCE", artifact["artifact_id"], json.loads(reference))
            self.consumers.append({"artifact_id": artifact["artifact_id"], "found_count": len(found),
                                   "declared_count": len(declared), "missing_count": len(missing)})
            if artifact["content_hash"] != seal(artifact):
                self.error("CONTENT_HASH_MISMATCH", artifact["artifact_id"])
        # Detect all dependency cycles. A resource back edge to an artifact is
        # represented in the same graph as an ordinary artifact reference.
        active, complete = set(), set()
        def dfs(node):
            if node in active:
                self.error("REFERENCE_CYCLE", node)
                return
            if node in complete:
                return
            active.add(node)
            for child in sorted(self.edges.get(node, ())):
                dfs(child)
            active.remove(node)
            complete.add(node)
        for node in list(self.edges):
            dfs(node)
        return {"error_count": len(self.errors), "errors": self.errors,
                "consumer_count": len(self.consumers), "consumers": self.consumers,
                "distinct_resource_bytes": len(self.resources)}


def rewrite_downstream(bundle):
    """Reseal finite acyclic envelope refs after a mutant, without auto-declaring refs."""
    objects = {(a["artifact_id"], a["revision"]): a for a in bundle["artifacts"]}
    def walk(value):
        if isinstance(value, dict):
            if set(value) == FIELDS:
                target = objects.get((value["artifact_id"], value["revision"]))
                if target is not None:
                    value.update(artifact_ref(target))
            else:
                for child in value.values():
                    walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    # Existing normal order is topological and resources reference only upstream
    # unchanged artifacts. Each mutant changes receipt/progress terminal branches.
    for artifact in bundle["artifacts"]:
        for field, child in artifact.items():
            if field != "content_hash":
                walk(child)
        artifact["content_hash"] = seal(artifact)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-root", required=True, type=Path)
    args = parser.parse_args()
    frozen = args.frozen_root.resolve()
    out = Path(__file__).resolve().parent
    data = frozen / "examples/a03/P1-R1/data"
    old = frozen / "examples/a03/P1"
    manifest, previous, mapping = load(data / "case-manifest.json"), load(old / "case-manifest.json"), load(data / "case-mapping.json")
    old_rows = {c["case_id"]: c for c in previous["cases"]}
    new_rows = {c["case_id"]: c for c in manifest["cases"]}
    mapping_checks = []
    for row in mapping["mappings"]:
        before, after = old_rows[row["old_case_id"]], new_rows[row["r1_case_id"]]
        checks = {
            "old_path_exact": before["path"] == row["old_path"],
            "new_path_exact": after["path"] == row["r1_path"],
            "old_sha_exact": sha(old / row["old_path"]) == row["old_sha256"],
            "new_sha_exact": sha(data / row["r1_path"]) == row["r1_sha256"],
            "same_case_id": row["old_case_id"] == row["r1_case_id"],
            "semantic_layer_unchanged": before["expected_layer"] == after["expected_layer"] == row["expected_layer"],
            "semantic_code_unchanged": before["expected_code"] == after["expected_code"] == row["expected_code"],
            "mapped_source_exact": after["source_P1_case_id"] == before["case_id"],
            "semantic_not_executed": after["semantic_execution"] == "EXPECTED_NOT_EXECUTED",
        }
        mapping_checks.append({"case_id": row["old_case_id"], "checks": checks, "all_pass": all(checks.values())})
    cases = []
    for row in manifest["cases"]:
        result = Audit(load(data / row["path"])["bundle"], data).run()
        cases.append({"case_id": row["case_id"], "author_expected_static": row["expected_static"], **result})
    # A single asset-root copy gives every retained mutant portable paths and
    # frozen bytes. No source file, original case or prior evidence is changed.
    sandbox = out / "counterexamples"
    sandbox.mkdir(exist_ok=True)
    shutil.copytree(data / "assets", sandbox / "assets", dirs_exist_ok=True)
    template = load(data / "cases/normal.json")
    mutants = []
    def find(bundle, kind):
        return next(a for a in bundle["artifacts"] if a["kind"] == kind)
    def add(name, bundle, expected):
        rewrite_downstream(bundle)
        path = sandbox / (name + ".json")
        write(path, {"design_only": True, "counterexample_id": name, "bundle": bundle})
        actual = Audit(bundle, sandbox).run()
        mutants.append({"counterexample_id": name, "path": path.name, "expected_code": expected,
                        "independent": actual})
    # Reproduce prior P1 defect at each of the two independent consumers.
    for kind in ("ExecutionReceipt", "ExecutionProgress"):
        bundle = copy.deepcopy(template["bundle"])
        target = find(bundle, kind)
        target["input_refs"] = [r for r in target["input_refs"] if r["artifact_id"] != "snapshot-action-result-2"]
        add("removed-snapshot-from-" + kind.lower(), bundle, "UNDECLARED_RESOURCE_REFERENCE")
    # Introduce arbitrary-depth JSON resources via an already formal evidence
    # field. This does not depend on fact-specific locations in either audit.
    normal = template["bundle"]
    snapshot = next(a for a in normal["artifacts"] if a["artifact_id"] == "snapshot-normal")
    def make_resource(name, value):
        path = sandbox / "assets" / "independent" / name
        write(path, value)
        return {"path": path.relative_to(sandbox).as_posix(), "sha256": sha(path),
                "media_type": "application/json", "origin": "SYNTHETIC"}
    leaf = make_resource("leaf.json", {"ordinary_at_depth_4": artifact_ref(snapshot)})
    for index in range(3):
        leaf = make_resource("level-" + str(index) + ".json", {"nested": [leaf]})
    for declared in (False, True):
        bundle = copy.deepcopy(normal)
        receipt = find(bundle, "ExecutionReceipt")
        bundle["evidence"].append({"evidence_id": "independent-depth-four", "resource": leaf,
                                  "description": "Independent static depth-four resource fixture", "mode": "SYNTHETIC"})
        receipt["payload"]["results"][0]["before_evidence_refs"].append("independent-depth-four")
        if declared:
            receipt["input_refs"].append(artifact_ref(snapshot))
        add("formal-evidence-depth-four-" + ("declared" if declared else "undeclared"), bundle,
            "PASS" if declared else "UNDECLARED_RESOURCE_REFERENCE")
    # Byte digest and exact tuple wrong-digest neighbours use independent files.
    for flavor in ("wrong-ref-hash", "wrong-resource-hash", "cross-book", "cross-scope", "mixed-self-cycle"):
        bundle = copy.deepcopy(normal)
        receipt = find(bundle, "ExecutionReceipt")
        reference = artifact_ref(snapshot)
        if flavor == "wrong-ref-hash":
            reference["content_hash"] = "1" * 64
        elif flavor in ("cross-book", "cross-scope"):
            other = copy.deepcopy(snapshot)
            other["artifact_id"] = "independent-other-snapshot"
            other["input_refs"] = []
            other["payload"]["evidence_refs"] = []
            other["book_id" if flavor == "cross-book" else "scope_id"] = "independent-other"
            other["content_hash"] = seal(other)
            bundle["artifacts"].append(other)
            reference = artifact_ref(other)
        elif flavor == "mixed-self-cycle":
            reference = artifact_ref(receipt)
        resource = make_resource(flavor + ".json", {"test_ref": reference})
        if flavor == "wrong-resource-hash":
            resource["sha256"] = "2" * 64
        bundle["evidence"].append({"evidence_id": "independent-neighbor", "resource": resource,
                                  "description": "Independent static resource counterexample", "mode": "SYNTHETIC"})
        receipt["payload"]["results"][0]["after_evidence_refs"].append("independent-neighbor")
        receipt["input_refs"].append(reference)
        expected = {"wrong-ref-hash": "REFERENCE_HASH_OR_IDENTITY_MISMATCH", "wrong-resource-hash": "RESOURCE_HASH_MISMATCH",
                    "cross-book": "REFERENCE_SCOPE_MISMATCH", "cross-scope": "REFERENCE_SCOPE_MISMATCH",
                    "mixed-self-cycle": "REFERENCE_CYCLE"}[flavor]
        add("independent-" + flavor, bundle, expected)
    # Compare neighbours with the delivered author static function. Its result
    # cannot define our own expected outcomes or confer runtime qualification.
    spec = importlib.util.spec_from_file_location("author_static_design", data.parent / "check_design.py")
    author = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(author)
    for mutant in mutants:
        value = load(sandbox / mutant["path"])
        try:
            author.audit_closure(value["bundle"], sandbox)
            observation = {"category": "PASS", "detail": None}
        except author.StaticError as exc:
            observation = {"category": exc.category, "detail": exc.detail, "where": exc.path}
        mutant["author_static_differential"] = observation
        codes = {e["code"] for e in mutant["independent"]["errors"]}
        mutant["independent_expectation_matched"] = (not codes if mutant["expected_code"] == "PASS" else mutant["expected_code"] in codes)
    result = {
        "review_target": "ca4fba4f505467228a8164c3999e0cecc54ffc4e", "design_commit": "095ed4aa18a56100ce3aabc4a0d6885ad37ab520",
        "frozen_root": str(frozen), "design_only": True, "runtime_or_recovery_executed": False,
        "input_sha256": {str(path.relative_to(frozen)).replace("\\", "/"): sha(path) for path in (
            frozen / "docs/a03-recovery-contract-v1-r1-proposal.md",
            data.parent / "README.md", data.parent / "check_design.py",
            data / "case-manifest.json", data / "case-mapping.json", old / "case-manifest.json")},
        "semantic_actual": "NOT_EXECUTED", "mapping_count": len(mapping_checks),
        "old_case_count": len(old_rows), "r1_case_count": len(new_rows),
        "old_mapping_bijection": len(mapping_checks) == 42 and len({r["case_id"] for r in mapping_checks}) == 42 and {r["case_id"] for r in mapping_checks} == set(old_rows),
        "mapping_checks": mapping_checks, "cases": cases, "independent_counterexamples": mutants,
        "limitations": ["Independent audit checks recursive bytes/ref declarations and DAG, not general schema semantics.",
                        "Only consumer-reachable formal evidence Resources are audited independently; unrelated bundle evidence diagnostics are left to the primary reviewer.",
                        "Expected_static STRUCTURE_FAIL and DESIGN_FIELD_FAIL need the primary schema/field review.",
                        "Same semantic labels and exact hashes prove case mapping metadata, not executed semantic effects.",
                        "Resource-cycle hash fixed point is not constructed; delivered nested-resource-cycle is rejected at bytes gate.",
                        "Future commits, new observations, locking, owner/generation checks and synthetic admission are NOT_EXECUTED."]}
    write(out / "resource-audit-results.json", result)
    summary = {"mapping_bijection": result["old_mapping_bijection"], "all_mapping_checks_pass": all(r["all_pass"] for r in mapping_checks),
               "cases_audited": len(cases), "counterexamples": len(mutants),
               "counterexample_expectations_match": all(m["independent_expectation_matched"] for m in mutants),
               "author_expected_pass_with_independent_closure_errors": [c["case_id"] for c in cases if c["author_expected_static"] == "PASS" and c["errors"]]}
    write(out / "resource-audit-summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["mapping_bijection"] and summary["all_mapping_checks_pass"] and summary["counterexample_expectations_match"] and not summary["author_expected_pass_with_independent_closure_errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
