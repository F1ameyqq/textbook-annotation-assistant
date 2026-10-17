"""R8 native closure derived from frozen R7 R2/R3/R5 rules; old bytes stay frozen.

No session, conversion, oracle, code loader, planner, or writer is imported.
"""
from ..a03_bridge._errors import StaticCodecError, need
from ..a03_bridge._json import digest
from ..a03_bridge._schema import validate

VERSION = "1.4.0-a03-native-proposal"
HISTORY_VERSION = "1.1.0-a-recovery-proposal"
PREFIX = "a03-runtime-event-prefix-2"
FORMAL_NAMES = {"evidence_refs", "before_evidence_refs", "after_evidence_refs", "submission_evidence_refs"}


def artifact_ref(artifact):
    return {key: artifact[key] for key in ("artifact_id", "revision", "kind", "content_hash")}


def is_ref(value):
    return isinstance(value, dict) and set(value) == {"artifact_id", "revision", "kind", "content_hash"}


def is_resource(value):
    return isinstance(value, dict) and {"path", "sha256", "media_type"} <= set(value)


class StaticPackage:
    def __init__(self, bundle, reader, documents, registry):
        self.bundle = bundle
        self.reader = reader
        self.documents = documents
        self.registry = registry
        self.index = {}
        self.evidence_index = {}
        self.edges = {}
        self.consumers = []
        self.contexts = []
        self.active_consumers = set()
        self.typed_lists = {}
        self.fields = {}
        self.prefix_visits = []
        self.registration_checks = []
        self.stages = []
        self.id_pattern = documents["exchange"]["$defs"]["EvidenceRecord"]["properties"]["evidence_id"]["pattern"]
        for name in ("exchange", "fact", "prefix"):
            self.catalog(name, documents[name])

    def catalog(self, docname, node, pointer=""):
        for key, child in node.get("properties", {}).items():
            location = pointer + "/properties/" + key
            if key in FORMAL_NAMES and child.get("type") == "array" and child.get("items", {}).get("type") == "string" and child["items"].get("pattern") == self.id_pattern:
                self.fields[(docname, location)] = {"document": docname, "schema_pointer": "#" + location, "field": key}
            self.catalog(docname, child, location)
        for key, child in node.get("$defs", {}).items():
            self.catalog(docname, child, pointer + "/$defs/" + key)
        if isinstance(node.get("items"), dict):
            self.catalog(docname, node["items"], pointer + "/items")
        for key in ("oneOf", "anyOf"):
            for i, child in enumerate(node.get(key, [])):
                self.catalog(docname, child, pointer + "/" + key + "/" + str(i))

    def slots(self, value, node, docname, pointer):
        doc = self.documents[docname]
        if "$ref" in node:
            target_pointer = node["$ref"]
            need(target_pointer.startswith("#/"), "EVIDENCE_SCHEMA_REF", target_pointer)
            target = doc
            for token in target_pointer[2:].split("/"):
                target = target[token.replace("~1", "/").replace("~0", "~")]
            self.slots(value, target, docname, target_pointer[1:])
        for key in ("oneOf", "anyOf"):
            for i, child in enumerate(node.get(key, [])):
                try:
                    validate(value, child, doc)
                except StaticCodecError:
                    continue
                self.slots(value, child, docname, pointer + "/" + key + "/" + str(i))
        if isinstance(value, list) and (docname, pointer) in self.fields:
            # Keep the list itself: object IDs cannot be recycled into authority.
            self.typed_lists[id(value)] = (value, self.fields[(docname, pointer)])
        if isinstance(value, dict):
            for key, child in node.get("properties", {}).items():
                if key in value:
                    self.slots(value[key], child, docname, pointer + "/properties/" + key)
        if isinstance(value, list) and isinstance(node.get("items"), dict):
            for member in value:
                self.slots(member, node["items"], docname, pointer + "/items")

    def artifact_schema(self, artifact):
        version = artifact.get("schema_version")
        if version == VERSION:
            name = "Amended" + artifact.get("kind", "")
        elif version == HISTORY_VERSION:
            name = artifact.get("kind", "")
        else:
            return None
        return name if name in self.documents["exchange"]["$defs"] else None

    def known_resource_type(self, value):
        if not isinstance(value, dict):
            return
        required = {"schema_version", "artifact_id", "revision", "kind", "run_id", "book_id", "scope_id", "created_at", "producer", "input_refs", "content_hash", "payload"}
        if required <= set(value):
            name = self.artifact_schema(value)
            if name:
                node = self.documents["exchange"]["$defs"][name]
                validate(value, node, self.documents["exchange"])
                self.slots(value, node, "exchange", "/$defs/" + name)
        if value.get("format_version") == "a03-action-fact-3":
            validate(value, self.documents["fact"])
            self.slots(value, self.documents["fact"], "fact", "")

    def artifact(self, reference, path):
        key = digest(reference)
        need(key in self.index and artifact_ref(self.index[key]) == reference, "EXACT_REF", path)
        return self.index[key]

    def edge(self, parent, child):
        self.edges.setdefault(parent, set()).add(child)
        self.edges.setdefault(child, set())

    def consumer(self, node, value, book, scope, declared, path):
        key = (node, book, scope)
        if key in self.active_consumers:
            return  # All edges remain; the whole mixed DAG rejects recursion.
        artifact = self.index.get(node[2:]) if node.startswith("A:") else None
        if artifact:
            name = self.artifact_schema(artifact)
            payload = self.documents["exchange"]["$defs"][name]["properties"]["payload"]
            self.slots(value, payload, "exchange", "/$defs/" + name + "/properties/payload")
        else:
            event = self.documents["prefix"]["properties"]["frames"]["items"]["properties"]["event"]
            self.slots(value, event, "prefix", "/properties/frames/items/properties/event")
        self.active_consumers.add(key)
        self.contexts.append((node, book, scope, path))
        try:
            found = {}
            self.scan(value, node, book, scope, found, path, set(), False)
            declarations = {digest(r): r for r in declared}
            self.consumers.append((found, declarations, book, scope, path))
            for reference in declarations.values():
                target = self.artifact(reference, path + "/input_refs")
                self.edge(node, "A:" + digest(artifact_ref(target)))
        finally:
            self.contexts.pop()
            self.active_consumers.remove(key)

    def registration_binding(self, prefix, event, book, path):
        payload = event["payload"]
        source = self.artifact(payload["source_ref"], path + "/registration/source")
        snapshot = self.artifact(payload["snapshot_ref"], path + "/registration/snapshot")
        checks = {"kinds": source["kind"] == "SourceBundle" and snapshot["kind"] == "PlatformSnapshot", "book": source["book_id"] == snapshot["book_id"] == book, "scope": source["scope_id"] == snapshot["scope_id"] == payload["scope_id"]}
        row = {"path": path, "binding_checks": checks, "book_id": book}
        self.registration_checks.append(row)
        need(all(checks.values()), "FRAME_REGISTRATION_BINDING", path)
        key = prefix["target_key"]
        observed = self.reader.read(payload["observation"])
        need(isinstance(observed, dict), "FRAME_REGISTRATION_OBSERVATION", path + "/registration/observation")
        targets = {"event_target_key": event["target_key"] == key, "canonical_book": key["book_id"] == book, "snapshot_target_id": snapshot["payload"]["target_id"] == key["target_id"], "snapshot_authorized_scope": snapshot["payload"]["authorized_scope_id"] == payload["scope_id"], "observation_target_key": observed.get("target_key") == key, "observation_source": observed.get("source_ref") == payload["source_ref"], "observation_snapshot": observed.get("snapshot_ref") == payload["snapshot_ref"], "observation_scope": observed.get("scope_id") == payload["scope_id"]}
        for field in ("registration_id", "target_store_id", "target_session_id"):
            targets["observation_" + field] = observed.get(field) == payload[field]
        business = observed.get("business_value")
        if isinstance(business, dict):
            if "target_key" in business:
                targets["business_target_key"] = business["target_key"] == key
            view = business.get("target_view")
            if isinstance(view, dict) and "target_id" in view:
                targets["business_target_id"] = view["target_id"] == key["target_id"]
        baseline = self.reader.read(payload["baseline"]["binding"])
        if isinstance(baseline, dict) and "target_key" in baseline:
            targets["baseline_target_key"] = baseline["target_key"] == key
        row["target_checks"] = targets
        need(all(targets.values()), "FRAME_REGISTRATION_TARGET", path + "/registration/target")
        return source["scope_id"]

    def scan_prefix(self, value, parent, book, scope, found, path, active, resource_root):
        need(resource_root, "PREFIX_LOCATION", path)
        validate(value, self.documents["prefix"])
        bound = bool(self.contexts)
        need(book is not None if bound else book is None and scope is None, "CONSUMER_BOOK_REQUIRED" if bound else "UNBOUND_CONTEXT_REQUIRED", path)
        self.prefix_visits.append({"mode": "REAL_CONSUMER" if bound else "GLOBAL_GRAPH", "book_id": book, "scope_id": scope, "path": path})
        if bound:
            need(value["target_key"]["book_id"] == book, "PREFIX_TARGET_BOOK", path)
        for key, item in value.items():
            if key != "frames":
                self.scan(item, parent, book, scope, found, path + "/" + key, active, False)
        for i, frame in enumerate(value["frames"]):
            event = frame["event"]
            frame_path = path + "/frames/" + str(i)
            expected_scope = None
            if bound:
                need(event["target_key"] == value["target_key"], "FRAME_TARGET_KEY", frame_path)
            if event["plan_ref"] is not None:
                plan = self.artifact(event["plan_ref"], frame_path)
                need(plan["kind"] == "ApplyPlan", "FRAME_PLAN_KIND", path)
                expected_scope = plan["scope_id"]
            elif event["event"] == "TARGET_DRIFT_HOLD" and event["payload"].get("registration_id") and event["payload"].get("source_ref"):
                if bound:
                    expected_scope = self.registration_binding(value, event, book, path)
                else:
                    source = self.artifact(event["payload"]["source_ref"], path + "/registration/source")
                    snapshot = self.artifact(event["payload"]["snapshot_ref"], path + "/registration/snapshot")
                    need(source["kind"] == "SourceBundle" and snapshot["kind"] == "PlatformSnapshot", "FRAME_REGISTRATION_KIND", path)
                    expected_scope = source["scope_id"]
            node = parent + "/F:" + str(i)
            self.edge(parent, node)
            need(frame["consumer_scope_id"] == expected_scope, "FRAME_SCOPE", frame_path)
            if bound:
                self.consumer(node, event, book, expected_scope, frame["input_refs"], frame_path)
            else:
                event_schema = self.documents["prefix"]["properties"]["frames"]["items"]["properties"]["event"]
                self.slots(event, event_schema, "prefix", "/properties/frames/items/properties/event")
                global_found = {}
                self.scan(event, node, None, None, global_found, frame_path, active, False)
                declared = {digest(r): r for r in frame["input_refs"]}
                need(set(global_found) <= set(declared), "UNDECLARED_REFERENCE", frame_path)
                for reference in declared.values():
                    self.edge(node, "A:" + digest(artifact_ref(self.artifact(reference, frame_path + "/input_refs"))))

    def scan(self, value, parent, book, scope, found, path, active, resource_root):
        self.known_resource_type(value)
        if isinstance(value, dict) and value.get("format_version") == PREFIX:
            return self.scan_prefix(value, parent, book, scope, found, path, active, resource_root)
        slot = self.typed_lists.get(id(value)) if isinstance(value, list) else None
        if slot is not None and slot[0] is value:
            for evidence_id in value:
                need(evidence_id in self.evidence_index, "EVIDENCE_ID_MISSING", path + "[" + str(evidence_id) + "]")
                node = "E:" + evidence_id
                self.edge(parent, node)
                self.scan(self.evidence_index[evidence_id]["resource"], node, book, scope, found, path + "[" + evidence_id + "]/EvidenceRecord.resource", active, False)
            return
        if is_ref(value):
            artifact = self.artifact(value, path)
            self.edge(parent, "A:" + digest(artifact_ref(artifact)))
            found[digest(value)] = value
            return
        if is_resource(value):
            node = "R:" + value["path"] + ":" + value["sha256"]
            self.edge(parent, node)
            body = self.reader.read(value)
            token = (value["path"], value["sha256"])
            if body is not None and token not in active:
                self.scan(body, node, book, scope, found, value["path"], active | {token}, True)
            return
        if isinstance(value, dict):
            need("frame_version" not in value, "FRAME_OUTSIDE_TYPED_PREFIX", path)
            for key, item in value.items():
                self.scan(item, parent, book, scope, found, path + "/" + key, active, False)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                self.scan(item, parent, book, scope, found, path + "/" + str(i), active, False)

    def validate(self):
        validate(self.bundle, self.documents["exchange"])
        self.index = {digest(artifact_ref(a)): a for a in self.bundle["artifacts"]}
        need(len(self.index) == len(self.bundle["artifacts"]), "DUPLICATE_REF", "$")
        need(len({(a["artifact_id"], a["revision"]) for a in self.bundle["artifacts"]}) == len(self.bundle["artifacts"]), "DUPLICATE_ID", "$")
        for i, record in enumerate(self.bundle["evidence"]):
            key = record["evidence_id"]
            need(key not in self.evidence_index, "EVIDENCE_ID_DUPLICATE", "evidence/" + str(i) + "/" + key)
            self.evidence_index[key] = record
        for artifact in self.bundle["artifacts"]:
            need(artifact["kind"] in self.registry, "UNREGISTERED_KIND", artifact["artifact_id"])
            need(artifact["schema_version"] in (VERSION,), "VERSION_SELECTOR", artifact["artifact_id"])
            self.consumer("A:" + digest(artifact_ref(artifact)), artifact["payload"], artifact["book_id"], artifact["scope_id"], artifact["input_refs"], artifact["artifact_id"])
        for record in self.bundle["evidence"]:
            self.scan(record["resource"], "E:" + record["evidence_id"], None, None, {}, "evidence/" + record["evidence_id"], set(), False)
        self.stages.append("MIXED_DAG")
        active, done = set(), set()

        def visit(node):
            need(node not in active, "MIXED_CYCLE", node)
            if node in done:
                return
            active.add(node)
            for child in self.edges.get(node, ()):
                visit(child)
            active.remove(node)
            done.add(node)

        for node in list(self.edges):
            visit(node)
        self.stages.append("CONSUMER_DECLARATIONS_BOOK_SCOPE")
        for found, declared, book, scope, path in self.consumers:
            need(set(found) <= set(declared), "UNDECLARED_REFERENCE", path)
            for reference in declared.values():
                target = self.artifact(reference, path)
                need(target["book_id"] == book, "FOREIGN_BOOK", path)
                need(target["scope_id"] == scope, "ORDINARY_SCOPE", path)
        self.stages.append("ARTIFACT_HASH_AND_PRE_STATIC_TAIL")
        for artifact in self.bundle["artifacts"]:
            need(digest({key: value for key, value in artifact.items() if key != "content_hash"}) == artifact["content_hash"], "ARTIFACT_HASH", artifact["artifact_id"])
            if artifact["schema_version"] == VERSION and artifact["kind"] == "CheckReport" and artifact["payload"]["stage"] == "PRE_APPLY":
                run = self.reader.read(artifact["payload"]["synthetic_run_ref"])
                validate(run, self.documents["pre_run"])
                need(run["context"] == artifact["payload"]["verification_context"], "PRE_CONTEXT", artifact["artifact_id"])
                need(run["graph_ref"] == artifact["payload"]["graph"] and run["admission"] == "RUNTIME_RECHECK_REQUIRED" and run["snapshot_ref"] == artifact["payload"]["snapshot"], "PRE_BINDING", artifact["artifact_id"])
        self.stages.append("COMPLETE_STATIC_RETURN")
        return self
