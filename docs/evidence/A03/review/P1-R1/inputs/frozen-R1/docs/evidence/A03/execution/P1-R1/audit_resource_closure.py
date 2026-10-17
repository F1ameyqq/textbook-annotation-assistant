"""Independent stdlib, read-only P1-R1 Resource/ArtifactRef closure audit.

This is deliberately not a JSON Schema implementation, admission checker,
recovery implementation, or evidence of runtime behavior.  It imports no author
checker or business code. Each consumer gets its own Resource expansion cache;
only JSON Resources whose portable path and byte hash pass are parsed. Known
EvidenceRecord IDs are followed ONLY in the four formal string-ID fields below.
All ordinary refs found in payload or consumed resources require this consumer's
own input_refs declaration, exact target kind/hash, and same book/scope. Artifact
refs discovered through Resources also enter the artifact DAG.

Usage (case paths are relative to --root, or absolute):
 python -B docs/evidence/A03/execution/P1-R1/audit_resource_closure.py \
   --root examples/a03/P1 --case cases/normal.json
Repeat --case for more cases. JSON is written to stdout; no files are written.
Exit 0 means no violations in THIS static audit; exit 1 means violations. It does
not mean qualification, functional acceptance, or that any future API ran.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

REF_FIELDS = frozenset(("artifact_id", "revision", "kind", "content_hash"))
RESOURCE_FIELDS = frozenset(("path", "sha256", "media_type"))
KINDS = frozenset(("SourceBundle", "EvidenceBundle", "QuestionGraph",
                   "PlatformSnapshot", "CheckReport", "ApplyPlan",
                   "ExecutionReceipt", "ReviewPatch", "BatchReport",
                   "WriteIntent", "ExecutionProgress", "ReconciliationResult"))
# Exact formal fields whose ARRAY STRING items denote EvidenceRecord IDs.
# Resource-valued evidence_refs / attempt_evidence_refs are visited as dicts.
EVIDENCE_ID_FIELDS = frozenset(("evidence_refs", "before_evidence_refs",
                                "after_evidence_refs", "submission_evidence_refs"))
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def reject_constant(value):
    raise ValueError("non-finite JSON number: " + value)


def unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate JSON key: " + name)
        result[name] = value
    return result


def read_json(data):
    return json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_object,
                      parse_constant=reject_constant)


def digest_artifact(artifact):
    core = {k: v for k, v in artifact.items() if k != "content_hash"}
    raw = json.dumps(core, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def identity(value):
    return (value.get("artifact_id"), value.get("revision"), value.get("kind"))


def exact_ref(value):
    return (value.get("artifact_id"), value.get("revision"), value.get("kind"),
            value.get("content_hash"))


def display_identity(key):
    return {"artifact_id": key[0], "revision": key[1], "kind": key[2]}


def child_location(location, name):
    return location + "/" + str(name).replace("~", "~0").replace("/", "~1")


class ClosureAudit:
    def __init__(self, root, case_path):
        self.root = root.resolve()
        self.case_path = case_path
        self.violations = []
        self.stats = []
        self.artifacts = {}
        self.by_id_revision = {}
        self.evidence = {}
        self.graph = {}
        self.edge_locations = {}
        self.case_id = None
        self.case_sha256 = None

    def violation(self, consumer, location, code, expected, actual, resource=None):
        self.violations.append({"case_id": self.case_id,
            "consumer": display_identity(identity(consumer)) if consumer else None,
            "location": location, "resource": resource, "code": code,
            "expected": expected, "actual": actual})

    def read_bundle(self):
        try:
            raw = self.case_path.read_bytes()
            self.case_sha256 = hashlib.sha256(raw).hexdigest()
            case = read_json(raw)
        except (OSError, ValueError, UnicodeError) as exc:
            self.violation(None, "case", "CASE_READ_OR_JSON", "readable strict JSON", str(exc))
            return None
        if not isinstance(case, dict):
            self.violation(None, "case", "CASE_SHAPE", "object", type(case).__name__)
            return None
        self.case_id = case.get("case_id")
        bundle = case.get("bundle", case)
        if not isinstance(bundle, dict) or not isinstance(bundle.get("artifacts"), list):
            self.violation(None, "case/bundle", "BUNDLE_SHAPE", "bundle.artifacts array", bundle)
            return None
        for number, item in enumerate(bundle["artifacts"]):
            location = "bundle/artifacts/" + str(number)
            if not isinstance(item, dict):
                self.violation(None, location, "ARTIFACT_SHAPE", "artifact object", item)
                continue
            key = identity(item)
            if (not isinstance(key[0], str) or not isinstance(key[1], int) or
                isinstance(key[1], bool) or key[1] < 1 or not isinstance(key[2], str) or
                key[2] not in KINDS):
                self.violation(item, location, "ARTIFACT_IDENTITY_SHAPE", "known scalar identity", list(key))
                continue
            if key in self.artifacts:
                self.violation(item, location, "DUPLICATE_ARTIFACT", "unique artifact identity", list(key))
                continue
            self.artifacts[key] = item
            self.graph[key] = set()
            self.by_id_revision.setdefault(key[:2], []).append(key)
            try:
                calculated = digest_artifact(item)
                if item.get("content_hash") != calculated:
                    self.violation(item, location + "/content_hash", "ARTIFACT_CONTENT_HASH",
                                   calculated, item.get("content_hash"))
            except (TypeError, ValueError) as exc:
                self.violation(item, location, "ARTIFACT_CANONICAL_JSON", "canonical JSON", str(exc))
        records = bundle.get("evidence", [])
        if not isinstance(records, list):
            self.violation(None, "bundle/evidence", "EVIDENCE_INDEX_SHAPE", "array", records)
            records = []
        for number, record in enumerate(records):
            if not isinstance(record, dict) or not isinstance(record.get("evidence_id"), str):
                self.violation(None, "bundle/evidence/" + str(number), "EVIDENCE_RECORD_SHAPE",
                               "record with string evidence_id", record)
                continue
            eid = record["evidence_id"]
            if eid in self.evidence:
                self.violation(None, "bundle/evidence/" + str(number), "DUPLICATE_EVIDENCE_ID",
                               "unique evidence_id", eid)
                continue
            self.evidence[eid] = record
        return bundle

    def add_edge(self, consumer, target, location):
        source = identity(consumer)
        self.graph[source].add(target)
        self.edge_locations.setdefault((source, target), []).append(location)

    def check_ref(self, value, consumer, location, state, require_declaration=True, resource=None):
        state["ordinary_ref_occurrences"] += 1
        if not isinstance(value, dict) or set(value) != REF_FIELDS:
            self.violation(consumer, location, "REFERENCE_SHAPE", sorted(REF_FIELDS), value, resource)
            return
        if (not isinstance(value["artifact_id"], str) or
            not isinstance(value["revision"], int) or isinstance(value["revision"], bool) or
            value["revision"] < 1 or not isinstance(value["kind"], str) or value["kind"] not in KINDS or
            not isinstance(value["content_hash"], str) or not HASH_RE.fullmatch(value["content_hash"])):
            self.violation(consumer, location, "REFERENCE_SHAPE", "valid ordinary four-tuple", value, resource)
            return
        key = identity(value)
        state["referenced_artifacts"].add(key)
        target = self.artifacts.get(key)
        if target is None:
            alternatives = self.by_id_revision.get(key[:2], [])
            code = "REFERENCE_KIND_MISMATCH" if alternatives else "REFERENCE_TARGET_MISSING"
            self.violation(consumer, location, code,
                           [display_identity(k) for k in alternatives] if alternatives else "known exact artifact",
                           value, resource)
        else:
            self.add_edge(consumer, key, location)
            if key == identity(consumer):
                self.violation(consumer, location, "SELF_REFERENCE", "different artifact identity", value, resource)
            if value["content_hash"] != target.get("content_hash"):
                self.violation(consumer, location, "REFERENCE_HASH_MISMATCH", target.get("content_hash"),
                               value["content_hash"], resource)
            for field, code in (("book_id", "REFERENCE_BOOK_MISMATCH"),
                                ("scope_id", "REFERENCE_SCOPE_MISMATCH")):
                if target.get(field) != consumer.get(field):
                    self.violation(consumer, location, code, consumer.get(field), target.get(field), resource)
        if require_declaration and exact_ref(value) not in state["declared_refs"]:
            self.violation(consumer, location, "UNDECLARED_REFERENCE",
                           "exact four-tuple in this consumer.input_refs", value, resource)

    def expand_resource(self, value, consumer, location, state):
        state["resource_occurrences"] += 1
        raw_path = value.get("path")
        expected_hash = value.get("sha256")
        if (not isinstance(raw_path, str) or not raw_path or "\\" in raw_path or
            ":" in raw_path or "\x00" in raw_path or raw_path.startswith("/") or
            any(part in ("", ".", "..") for part in raw_path.split("/")) or
            PurePosixPath(raw_path).is_absolute()):
            self.violation(consumer, location, "RESOURCE_PATH_NOT_PORTABLE",
                           "root-contained portable relative path", raw_path, raw_path)
            return
        path = (self.root / raw_path).resolve()
        try:
            path.relative_to(self.root)
        except ValueError:
            self.violation(consumer, location, "RESOURCE_PATH_ESCAPE", "path beneath asset root", raw_path, raw_path)
            return
        if not isinstance(expected_hash, str) or not HASH_RE.fullmatch(expected_hash):
            self.violation(consumer, location, "RESOURCE_HASH_SHAPE", "lowercase SHA256", expected_hash, raw_path)
            return
        try:
            raw = path.read_bytes()
        except OSError as exc:
            self.violation(consumer, location, "RESOURCE_READ", "readable local bytes", str(exc), raw_path)
            return
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected_hash:
            self.violation(consumer, location, "RESOURCE_HASH_MISMATCH", expected_hash, actual, raw_path)
            return
        resource_key = (str(path), expected_hash)
        if resource_key in state["active_resources"]:
            self.violation(consumer, location, "RESOURCE_CYCLE", "acyclic Resource expansion", raw_path, raw_path)
            return
        if resource_key in state["expanded_resources"]:
            state["resource_reuses"] += 1
            return
        state["resource_bytes_verified"] += len(raw)
        state["expanded_resources"].add(resource_key)
        state["resource_paths"].add(raw_path)
        if value.get("media_type") != "application/json":
            state["non_json_resources"] += 1
            return
        try:
            parsed = read_json(raw)
        except (ValueError, UnicodeError) as exc:
            self.violation(consumer, location, "RESOURCE_JSON", "strict UTF-8 JSON after hash check", str(exc), raw_path)
            return
        state["json_resources"] += 1
        state["active_resources"].add(resource_key)
        self.visit(parsed, consumer, location + " -> " + raw_path + "#", state, raw_path)
        state["active_resources"].remove(resource_key)

    def follow_evidence(self, eid, consumer, location, state, resource):
        state["evidence_id_occurrences"] += 1
        record = self.evidence.get(eid)
        if record is None:
            self.violation(consumer, location, "EVIDENCE_ID_MISSING", "known EvidenceRecord.evidence_id", eid, resource)
            return
        state["evidence_ids"].add(eid)
        value = record.get("resource")
        if not isinstance(value, dict) or not RESOURCE_FIELDS <= set(value):
            self.violation(consumer, location, "EVIDENCE_RESOURCE_SHAPE", "EvidenceRecord.resource Resource", value, resource)
            return
        self.expand_resource(value, consumer, location + " -> evidence:" + eid, state)

    def visit(self, value, consumer, location, state, resource=None):
        if isinstance(value, dict):
            # Full artifact envelopes in arbitrary JSON are not ordinary refs.
            if "artifact_id" in value and "payload" not in value:
                self.check_ref(value, consumer, location, state, resource=resource)
                return
            if RESOURCE_FIELDS <= set(value):
                self.expand_resource(value, consumer, location, state)
                return
            for name, child in value.items():
                place = child_location(location, name)
                if name in EVIDENCE_ID_FIELDS and isinstance(child, list):
                    for number, item in enumerate(child):
                        point = child_location(place, number)
                        if isinstance(item, str):
                            self.follow_evidence(item, consumer, point, state, resource)
                        else:
                            self.visit(item, consumer, point, state, resource)
                else:
                    self.visit(child, consumer, place, state, resource)
        elif isinstance(value, list):
            for number, child in enumerate(value):
                self.visit(child, consumer, child_location(location, number), state, resource)

    def check_consumer(self, consumer):
        declarations = consumer.get("input_refs")
        state = {"declared_refs": set(), "referenced_artifacts": set(),
            "active_resources": set(), "expanded_resources": set(), "resource_paths": set(),
            "evidence_ids": set(), "ordinary_ref_occurrences": 0,
            "resource_occurrences": 0, "resource_reuses": 0, "resource_bytes_verified": 0,
            "json_resources": 0, "non_json_resources": 0, "evidence_id_occurrences": 0}
        if not isinstance(declarations, list):
            self.violation(consumer, "input_refs", "INPUT_REFS_SHAPE", "array", declarations)
            declarations = []
        for value in declarations:
            if isinstance(value, dict) and set(value) == REF_FIELDS:
                try:
                    state["declared_refs"].add(exact_ref(value))
                except TypeError:
                    pass
        before = len(self.violations)
        for number, value in enumerate(declarations):
            self.check_ref(value, consumer, "input_refs/" + str(number), state, require_declaration=False)
        try:
            self.visit(consumer.get("payload"), consumer, "payload", state)
        except RecursionError:
            self.violation(consumer, "payload", "AUDIT_RECURSION_LIMIT",
                           "closure audit completes; no success on truncated traversal", "Python recursion limit")
        summary = {"consumer": display_identity(identity(consumer)),
            "book_id": consumer.get("book_id"), "scope_id": consumer.get("scope_id"),
            "declared_ref_count": len(state["declared_refs"]),
            "ordinary_ref_occurrences": state["ordinary_ref_occurrences"],
            "referenced_artifacts": [display_identity(k) for k in sorted(state["referenced_artifacts"])],
            "resource_occurrences": state["resource_occurrences"],
            "resources_expanded": len(state["expanded_resources"]),
            "resource_paths": sorted(state["resource_paths"]),
            "resource_reuses": state["resource_reuses"],
            "resource_bytes_verified": state["resource_bytes_verified"],
            "json_resources": state["json_resources"], "non_json_resources": state["non_json_resources"],
            "evidence_id_occurrences": state["evidence_id_occurrences"],
            "evidence_ids": sorted(state["evidence_ids"]),
            "violation_count": len(self.violations) - before}
        self.stats.append(summary)

    def check_dag(self):
        # Iterative DFS avoids hiding an artifact cycle behind recursion depth.
        colors = {}
        for start in self.graph:
            if colors.get(start):
                continue
            colors[start] = 1
            path = [start]
            stack = [(start, iter(sorted(self.graph[start])))]
            while stack:
                source, targets = stack[-1]
                target = next(targets, None)
                if target is None:
                    colors[source] = 2
                    stack.pop()
                    path.pop()
                elif colors.get(target) == 1:
                    cycle = path[path.index(target):] + [target]
                    self.violation(self.artifacts[source], self.edge_locations[(source, target)][0],
                                   "ARTIFACT_CYCLE", "acyclic input/payload/resource dependency DAG",
                                   [display_identity(k) for k in cycle])
                elif not colors.get(target):
                    colors[target] = 1
                    path.append(target)
                    stack.append((target, iter(sorted(self.graph[target]))))

    def run(self):
        bundle = self.read_bundle()
        if bundle is not None:
            for consumer in self.artifacts.values():
                self.check_consumer(consumer)
            self.check_dag()
        return {"case_id": self.case_id, "case_path": str(self.case_path),
                "case_sha256": self.case_sha256, "artifact_count": len(self.artifacts),
                "artifact_dependency_edges": sum(len(v) for v in self.graph.values()),
                "consumer_stats": self.stats, "violations": self.violations,
                "static_result": "VIOLATIONS" if self.violations else "NO_VIOLATIONS",
                "future_behavior": "EXPECTED_NOT_EXECUTED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="root for portable Resource paths")
    parser.add_argument("--case", required=True, action="append", help="root-relative or absolute case JSON; repeatable")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    results = []
    for name in args.case:
        path = Path(name)
        if not path.is_absolute():
            path = root / path
        results.append(ClosureAudit(root, path.resolve()).run())
    report = {"audit": "a03-p1-r1-independent-resource-closure-1",
        "scope": "STATIC_ONLY_NO_RECOVERY_OR_BUSINESS_IMPORTS",
        "root": str(root), "case_count": len(results),
        "consumer_rule": "Each consumer independently declares all ordinary refs in its payload and Resource/evidence-ID closure.",
        "dedup_rule": "Per consumer after byte verification; active resource expansion and combined artifact DAG cycles reject.",
        "evidence_id_fields": sorted(EVIDENCE_ID_FIELDS),
        "limitations": ["Not a full JSON Schema validator, admission/authorization proof, or runtime/API implementation.",
                        "Only exact formal EvidenceRecord-ID fields are followed; arbitrary strings are not references.",
                        "No target reads, intent commits, fact commits, functional tests, network, or database actions.",
                        "Evidence records not consumed by any artifact are outside this consumer-closure audit."],
        "results": results,
        "violation_count": sum(len(r["violations"]) for r in results)}
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if report["violation_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
