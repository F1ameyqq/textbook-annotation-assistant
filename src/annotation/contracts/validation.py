"""Referential and safety invariants; no planner, executor or recognition code."""
import copy
import struct
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .integrity import artifact_ref, as_data, content_digest, file_digest, policy_ref, read_json
from .models import (ArtifactRef, ExchangeBundle, ImageBinding, PolicyRef, Resource)


class ContractError(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__("\n".join("{path}: [{code}] {message}".format(**item) for item in issues))


def fail(path, code, message):
    raise ContractError([{"path": path, "code": code, "message": message}])


def walk(value, path):
    yield path, value
    if isinstance(value, BaseModel):
        for name in type(value).model_fields:
            yield from walk(getattr(value, name), path + "." + name)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from walk(item, path + "[" + str(i) + "]")
    elif isinstance(value, dict):
        for name, item in value.items():
            yield from walk(item, path + "." + name)


def distinct(items, path):
    if len(items) != len(set(items)):
        fail(path, "DUPLICATE_ID", "identifiers must be unique in this collection")


def subset(items, allowed, path):
    for i, item in enumerate(items):
        if item not in allowed:
            fail(path + "[" + str(i) + "]", "MISSING_REFERENCE", "unknown reference " + str(item))


def image_size(path, media_type):
    """Read only image headers; support PNG, JPEG and portable graymap fixtures."""
    with path.open("rb") as handle:
        if media_type == "image/png":
            head = handle.read(24)
            if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR" or len(head) < 24:
                raise ValueError("invalid PNG header")
            return struct.unpack(">II", head[16:24])
        if media_type == "image/x-portable-graymap":
            tokens = []
            while len(tokens) < 4:
                line = handle.readline(4096)
                if not line:
                    raise ValueError("incomplete PGM header")
                tokens.extend(line.split(b"#", 1)[0].split())
            if tokens[0] not in (b"P2", b"P5"):
                raise ValueError("invalid PGM header")
            return int(tokens[1]), int(tokens[2])
        if media_type == "image/jpeg":
            if handle.read(2) != b"\xff\xd8":
                raise ValueError("invalid JPEG header")
            while True:
                prefix = handle.read(1)
                if not prefix:
                    raise ValueError("JPEG size not found")
                if prefix != b"\xff":
                    continue
                marker = handle.read(1)
                while marker == b"\xff":
                    marker = handle.read(1)
                if not marker or marker[0] in (0xD9, 0xDA):
                    raise ValueError("JPEG size not found")
                if marker[0] in (0x00, 0x01, *range(0xD0, 0xD9)):
                    continue
                raw_length = handle.read(2)
                if len(raw_length) != 2:
                    raise ValueError("truncated JPEG")
                length = struct.unpack(">H", raw_length)[0]
                if length < 2:
                    raise ValueError("invalid JPEG segment")
                if marker[0] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    size = handle.read(5)
                    if len(size) != 5:
                        raise ValueError("truncated JPEG size")
                    height, width = struct.unpack(">HH", size[1:5])
                    return width, height
                handle.seek(length - 2, 1)
    raise ValueError("asset media_type must be an image")


class _Context:
    def __init__(self, bundle):
        self.bundle = bundle
        self.artifacts = {}
        self.paths = {}
        self.policies = {}
        self.evidence = {e.evidence_id: e for e in bundle.evidence}
        distinct([e.evidence_id for e in bundle.evidence], "$.evidence")
        for i, policy in enumerate(bundle.policies):
            key = (policy.policy_id, policy.revision)
            if key in self.policies:
                fail("$.policies[{}]".format(i), "DUPLICATE_ID", "duplicate policy revision")
            if policy.content_hash != content_digest(policy):
                fail("$.policies[{}].content_hash".format(i), "HASH_MISMATCH", "policy digest differs")
            if set(policy.role_mapping) != {"stem", "option", "answer", "explanation", "shared_material"}:
                fail("$.policies[{}].role_mapping".format(i), "POLICY_MAPPING", "all generic roles require mapping")
            if policy.applicability == "SYNTHETIC_ONLY" and policy.confirmation_status != "SYNTHETIC_ASSUMPTION":
                fail("$.policies[{}]".format(i), "POLICY_STATUS", "synthetic policy must be an explicit assumption")
            if policy.applicability == "JOINT_CONFIRMED" and policy.confirmation_status != "JOINT_CONFIRMED":
                fail("$.policies[{}]".format(i), "POLICY_STATUS", "joint applicability requires joint confirmation")
            self.policies[key] = policy
        identities = {}
        for i, artifact in enumerate(bundle.artifacts):
            path = "$.artifacts[{}]".format(i)
            key = (artifact.artifact_id, artifact.revision)
            if key in self.artifacts:
                fail(path, "DUPLICATE_ID", "duplicate immutable artifact revision")
            identity = (artifact.kind, artifact.book_id, artifact.scope_id)
            if artifact.artifact_id in identities and identities[artifact.artifact_id] != identity:
                fail(path, "IDENTITY_CONFLICT", "artifact identity changed kind/book/scope")
            identities[artifact.artifact_id] = identity
            if artifact.content_hash != content_digest(artifact):
                fail(path + ".content_hash", "HASH_MISMATCH", "artifact digest differs from normalized content")
            self.artifacts[key], self.paths[key] = artifact, path

    def resolve(self, ref, path, kind=None):
        artifact = self.artifacts.get((ref.artifact_id, ref.revision))
        if artifact is None:
            fail(path, "MISSING_REFERENCE", "missing artifact revision")
        if artifact_ref(artifact) != as_data(ref):
            fail(path, "REFERENCE_CONFLICT", "kind/revision/hash does not match referenced artifact")
        if kind and artifact.kind != kind:
            fail(path, "KIND_CONFLICT", "expected " + kind)
        return artifact

    def policy(self, ref, path):
        policy = self.policies.get((ref.policy_id, ref.revision))
        if policy is None or policy_ref(policy) != as_data(ref):
            fail(path, "POLICY_CONFLICT", "missing policy or revision/hash mismatch")
        return policy

    def source(self, artifact, path):
        if artifact.kind == "SourceBundle":
            return artifact
        if hasattr(artifact.payload, "source"):
            return self.resolve(artifact.payload.source, path + ".source", "SourceBundle")
        if hasattr(artifact.payload, "graph"):
            graph = self.resolve(artifact.payload.graph, path + ".graph", "QuestionGraph")
            return self.source(graph, path)
        if artifact.kind == "ExecutionReceipt":
            return self.source(self.resolve(artifact.payload.plan, path + ".plan", "ApplyPlan"), path)
        if artifact.kind == "ReviewPatch":
            return self.source(self.resolve(artifact.payload.baseline, path + ".baseline", "QuestionGraph"), path)
        # Snapshots may list frames; their exact image source must be an explicit input.
        sources = [self.resolve(r, path + ".input_refs") for r in artifact.input_refs if r.kind == "SourceBundle"]
        if len(sources) != 1:
            fail(path, "SOURCE_BINDING", "exactly one source dependency required for image bindings")
        return sources[0]

    def evrefs(self, refs, path, extra=()):
        subset(refs, set(self.evidence) | set(extra), path)


def _relationships(ctx):
    for key, artifact in ctx.artifacts.items():
        path = ctx.paths[key]
        declared = [tuple(as_data(r).values()) for r in artifact.input_refs]
        distinct(declared, path + ".input_refs")
        for location, value in walk(artifact, path):
            if isinstance(value, ArtifactRef):
                dependency = ctx.resolve(value, location)
                if (dependency.book_id, dependency.scope_id) != (artifact.book_id, artifact.scope_id):
                    fail(location, "SCOPE_CONFLICT", "dependency belongs to a different book or scope")
                if artifact.producer.evidence_mode == "OBSERVED" and dependency.producer.evidence_mode == "SYNTHETIC":
                    fail(location, "SYNTHETIC_EVIDENCE", "observed artifact cannot depend on a synthetic artifact")
                if ".input_refs[" not in location and tuple(as_data(value).values()) not in declared:
                    fail(location, "UNDECLARED_INPUT", "payload dependency must also appear in input_refs")
            elif isinstance(value, PolicyRef):
                ctx.policy(value, location)
                if ".producer.policy_versions[" not in location and value not in artifact.producer.policy_versions:
                    fail(location, "UNDECLARED_POLICY", "policy must also appear in producer.policy_versions")
        if artifact.kind == "SourceBundle" and artifact.input_refs:
            fail(path + ".input_refs", "SOURCE_MUTATION", "source imports are immutable roots in C01")
    visited, active = set(), set()

    def visit(key):
        if key in active:
            fail(ctx.paths[key] + ".input_refs", "DEPENDENCY_CYCLE", "artifact dependency cycle")
        if key not in visited:
            active.add(key)
            for ref in ctx.artifacts[key].input_refs:
                visit((ref.artifact_id, ref.revision))
            active.remove(key)
            visited.add(key)
    for key in ctx.artifacts:
        visit(key)


def _resources(ctx, asset_root):
    for path, value in walk(ctx.bundle, "$"):
        if isinstance(value, Resource) and asset_root is not None:
            root = Path(asset_root).resolve()
            resolved = (root / value.path).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                fail(path + ".path", "PATH_ESCAPE", "resolved resource leaves bundle directory")
            if not resolved.is_file():
                fail(path + ".path", "RESOURCE_MISSING", "resource does not exist")
            if file_digest(resolved) != value.sha256:
                fail(path + ".sha256", "RESOURCE_HASH", "resource bytes differ")
            if hasattr(value, "asset_id"):
                try:
                    size = image_size(resolved, value.media_type)
                except (ValueError, OSError) as error:
                    fail(path, "IMAGE_HEADER", str(error))
                if size != (value.width, value.height):
                    fail(path, "IMAGE_DIMENSIONS", "image header differs from declared width/height")
    for key, artifact in ctx.artifacts.items():
        for path, value in walk(artifact.payload, ctx.paths[key] + ".payload"):
            if isinstance(value, ImageBinding):
                source = ctx.source(artifact, path)
                assets = {asset.asset_id: asset for asset in source.payload.assets}
                asset = assets.get(value.asset_id)
                if asset is None:
                    fail(path + ".asset_id", "MISSING_ASSET", "asset absent from bound SourceBundle")
                if (value.width, value.height, value.sha256) != (asset.width, asset.height, asset.sha256):
                    fail(path, "IMAGE_BINDING", "original dimensions/digest conflict with asset")


def _source(ctx, a, path):
    p = a.payload
    assets = {x.asset_id for x in p.assets}
    dirs = {x.directory_id for x in p.directories}
    distinct([x.asset_id for x in p.assets], path + ".assets")
    distinct([x.directory_id for x in p.directories], path + ".directories")
    for name in ("pages_expected", "pages_acquired", "scope_manifest"):
        distinct(getattr(p, name), path + "." + name)
    if set(p.pages_acquired) != assets:
        fail(path + ".pages_acquired", "SOURCE_PAGES", "acquired pages must equal actual asset inventory")
    subset(p.pages_acquired, p.pages_expected, path + ".pages_acquired")
    parents = {d.directory_id: d.parent_id for d in p.directories}
    for i, directory in enumerate(p.directories):
        if directory.parent_id is not None:
            subset([directory.parent_id], dirs, path + ".directories[{}].parent_id".format(i))
        seen, current = set(), directory.directory_id
        while current is not None:
            if current in seen:
                fail(path + ".directories", "DIRECTORY_CYCLE", "directory tree contains a cycle")
            seen.add(current)
            current = parents[current]
    mappings = []
    for i, mapping in enumerate(p.external_page_mappings):
        loc = path + ".external_page_mappings[{}]".format(i)
        subset([mapping.asset_id], assets, loc + ".asset_id")
        subset([mapping.directory_id], dirs, loc + ".directory_id")
        ctx.evrefs(mapping.evidence_refs, loc + ".evidence_refs")
        mappings.append(mapping.asset_id)
    distinct(mappings, path + ".external_page_mappings")
    if set(mappings) != assets:
        fail(path + ".external_page_mappings", "PAGE_MAPPING", "every acquired original needs an external-page mapping")


def _evidence(ctx, a, path):
    p = a.payload
    regions = {r.region_id for r in p.regions}
    distinct([r.region_id for r in p.regions], path + ".regions")
    distinct([c.clue_id for c in p.coverage_clues], path + ".coverage_clues")
    for i, region in enumerate(p.regions):
        ctx.evrefs(region.evidence_refs, path + ".regions[{}].evidence_refs".format(i))
    for i, clue in enumerate(p.coverage_clues):
        loc = path + ".coverage_clues[{}]".format(i)
        subset(clue.region_ids, regions, loc + ".region_ids")
        ctx.evrefs(clue.evidence_refs, loc + ".evidence_refs")
        if clue.disposition == "ASSIGNED" and not clue.region_ids:
            fail(loc, "COVERAGE_ASSIGNMENT", "assigned clue must identify regions")
        if clue.disposition in ("EXCLUDED", "UNASSIGNED") and clue.region_ids:
            fail(loc, "COVERAGE_ASSIGNMENT", "excluded/unassigned clue cannot claim assigned regions")


def _graph(ctx, a, path):
    p = a.payload
    source = ctx.resolve(p.source, path + ".source", "SourceBundle")
    evidence = ctx.resolve(p.evidence, path + ".evidence", "EvidenceBundle")
    if evidence.payload.source != p.source:
        fail(path + ".source", "VERSION_CONFLICT", "graph/evidence source versions differ")
    regions = {r.region_id: r for r in evidence.payload.regions}
    fragments = {f.fragment_id: f for f in p.fragments}
    questions = {q.question_id: q for q in p.questions}
    for name, ids in (("questions", [q.question_id for q in p.questions]),
                      ("fragments", [f.fragment_id for f in p.fragments]),
                      ("answer_relations", [r.relation_id for r in p.answer_relations])):
        distinct(ids, path + "." + name)
    # IDs identify distinct entity namespaces; numbers can repeat in external_refs.
    all_ids = list(regions) + list(fragments) + list(questions)
    distinct(all_ids, path)
    subset(list(questions), source.payload.scope_manifest, path + ".questions")
    dirs = {d.directory_id for d in source.payload.directories}
    for i, fragment in enumerate(p.fragments):
        loc = path + ".fragments[{}]".format(i)
        subset(fragment.region_ids, regions, loc + ".region_ids")
        distinct(fragment.region_ids, loc + ".region_ids")
        if any(regions[r].content_type != fragment.content_type for r in fragment.region_ids):
            fail(loc + ".content_type", "CONTENT_TYPE", "fragment and region content types differ")
    for i, question in enumerate(p.questions):
        loc = path + ".questions[{}]".format(i)
        subset([question.directory_id], dirs, loc + ".directory_id")
        subset(question.fragment_ids + question.shared_fragment_ids, fragments, loc + ".fragment_ids")
        distinct(question.fragment_ids, loc + ".fragment_ids")
        if question.parent_question_id is not None:
            subset([question.parent_question_id], questions, loc + ".parent_question_id")
        seen, current = set(), question.question_id
        while current is not None:
            if current in seen:
                fail(loc, "QUESTION_CYCLE", "question parent cycle")
            seen.add(current)
            current = questions[current].parent_question_id
        if any(fragments[f].role != "shared_material" for f in question.shared_fragment_ids):
            fail(loc + ".shared_fragment_ids", "SHARED_ROLE", "shared material requires generic shared_material role")
        pages = {regions[r].box.image.asset_id for f in question.fragment_ids + question.shared_fragment_ids
                 for r in fragments[f].region_ids if fragments[f].role not in ("answer", "explanation")}
        if question.cross_page != (len(pages) > 1):
            fail(loc + ".cross_page", "CROSS_PAGE", "cross_page must match question content original pages")
        orders = [fragments[f].reading_order for f in question.fragment_ids]
        distinct(orders, loc + ".fragment_ids")
    for i, relation in enumerate(p.answer_relations):
        loc = path + ".answer_relations[{}]".format(i)
        subset([relation.question_id], questions, loc + ".question_id")
        subset(relation.candidate_fragment_ids, fragments, loc + ".candidate_fragment_ids")
        subset(relation.selected_fragment_ids, relation.candidate_fragment_ids, loc + ".selected_fragment_ids")
        if any(fragments[f].role not in ("answer", "explanation") for f in relation.candidate_fragment_ids):
            fail(loc, "ANSWER_ROLE", "answer candidates must have answer/explanation roles")
        if (relation.status == "SELECTED") != bool(relation.selected_fragment_ids):
            fail(loc, "ANSWER_SELECTION", "selected status must have selected candidates; unresolved cannot select")
        ctx.evrefs(relation.evidence_refs, loc + ".evidence_refs", regions)
    # A graph that claims a patch derivation must actually be that patch result.
    patches = [ctx.resolve(ref, path + ".input_refs", "ReviewPatch")
               for ref in a.input_refs if ref.kind == "ReviewPatch"]
    if patches:
        if len(patches) != 1:
            fail(path, "PATCH_DERIVATION", "one explicit patch per derived graph revision is required")
        patch = patches[0].payload
        baseline = ctx.resolve(patch.baseline, path + ".patch.baseline", "QuestionGraph")
        if baseline.artifact_id != a.artifact_id or patch.result_revision != a.revision:
            fail(path, "PATCH_DERIVATION", "patch result identity/revision differs from derived graph")
        if patch.baseline not in a.input_refs:
            fail(path, "PATCH_DERIVATION", "derived graph must declare the immutable baseline input")
        expected = copy.deepcopy(baseline.payload.model_dump(mode="json"))
        for change in patch.changes:
            if change.field == "role":
                collection, id_field = expected["fragments"], "fragment_id"
            elif change.field == "printed_number":
                collection, id_field = expected["questions"], "question_id"
            else:
                collection, id_field = expected["answer_relations"], "relation_id"
            entity = next((e for e in collection if e[id_field] == change.entity_id), None)
            if entity is None:
                fail(path, "PATCH_DERIVATION", "patch entity missing from baseline")
            if change.field == "printed_number":
                entity["external_refs"]["printed_number"] = change.after
            else:
                entity[change.field] = change.after
        if expected != p.model_dump(mode="json"):
            fail(path, "PATCH_DERIVATION", "derived graph differs from exact baseline plus declared patch; re-recognition needs explicit conflict handling")


def _coverage(ctx, coverage, graph, path, passing=False):
    source = ctx.source(graph, path)
    evidence = ctx.resolve(graph.payload.evidence, path + ".evidence", "EvidenceBundle")
    if coverage.scope_id != graph.scope_id or set(coverage.pages_expected) != set(source.payload.pages_expected):
        fail(path, "COVERAGE_SCOPE", "coverage must bind complete original source scope")
    for name in ("pages_expected", "pages_checked", "clue_ids", "unassigned_region_ids"):
        distinct(getattr(coverage, name), path + "." + name)
    subset(coverage.pages_checked, source.payload.pages_acquired, path + ".pages_checked")
    clues = {c.clue_id: c for c in evidence.payload.coverage_clues}
    subset(coverage.clue_ids, clues, path + ".clue_ids")
    subset(coverage.unassigned_region_ids, {r.region_id for r in evidence.payload.regions}, path + ".unassigned_region_ids")
    # Every independently observed clue on a checked page must be accounted for.
    required = {c.clue_id for c in clues.values() if c.box.image.asset_id in coverage.pages_checked}
    if not required.issubset(coverage.clue_ids):
        fail(path + ".clue_ids", "COVERAGE_OMISSION", "checked page omitted whole-page coverage clues")
    if passing:
        if {q.question_id for q in graph.payload.questions} != set(source.payload.scope_manifest):
            fail(path, "SCOPE_QUESTION_MISSING", "PASS cannot omit an independently scoped question")
        owned = {f for q in graph.payload.questions for f in q.fragment_ids + q.shared_fragment_ids}
        owned.update(f for relation in graph.payload.answer_relations for f in relation.selected_fragment_ids)
        assigned = {r for f in graph.payload.fragments if f.fragment_id in owned for r in f.region_ids}
        if set(coverage.pages_checked) != set(coverage.pages_expected) or coverage.unassigned_region_ids:
            fail(path, "COVERAGE_INCOMPLETE", "PASS requires complete pages and no unassigned regions")
        for clue_id in coverage.clue_ids:
            clue = clues[clue_id]
            if clue.disposition == "UNASSIGNED" or (clue.disposition == "ASSIGNED" and not set(clue.region_ids).issubset(assigned)):
                fail(path + ".clue_ids", "UNASSIGNED_CONTENT", "whole-page clue lacks graph ownership")


def _check(ctx, a, path):
    p = a.payload
    graph = ctx.resolve(p.graph, path + ".graph", "QuestionGraph")
    policy = ctx.policy(p.policy, path + ".policy")
    if p.snapshot is not None:
        ctx.resolve(p.snapshot, path + ".snapshot", "PlatformSnapshot")
    if p.stage != "POST_APPLY" and p.receipt is not None:
        fail(path + ".receipt", "CHECK_STAGE", "receipt binding is reserved for POST_APPLY")
    expected_subject = {"PRE_APPLY": p.graph, "TARGET": p.snapshot, "POST_APPLY": p.receipt}[p.stage]
    if p.subject != expected_subject:
        fail(path + ".subject", "CHECK_SUBJECT", "stage subject must match graph/snapshot/receipt respectively")
    if p.decision == "PASS" and p.stage in ("PRE_APPLY", "TARGET"):
        if any(q.question_type in ("ordinary_choice", "seven_choice") for q in graph.payload.questions):
            if policy.option_grouping == "UNRESOLVED" or policy.confirmation_status == "UNRESOLVED":
                fail(path + ".policy", "POLICY_UNRESOLVED", "affected option rule must be resolved before PASS")
    _coverage(ctx, p.coverage, graph, path + ".coverage", p.decision == "PASS")
    source = ctx.source(graph, path)
    evidence = ctx.resolve(graph.payload.evidence, path + ".evidence", "EvidenceBundle")
    entities = {q.question_id for q in graph.payload.questions} | set(source.payload.scope_manifest)
    fragments = {f.fragment_id for f in graph.payload.fragments}
    regions = {r.region_id for r in evidence.payload.regions}
    extra = entities | fragments | regions | {c.clue_id for c in evidence.payload.coverage_clues}
    distinct([i.issue_id for i in p.issues], path + ".issues")
    for i, check in enumerate(p.checks):
        ctx.evrefs(check.evidence_refs, path + ".checks[{}].evidence_refs".format(i), extra)
    for i, issue in enumerate(p.issues):
        loc = path + ".issues[{}]".format(i)
        ctx.evrefs(issue.evidence_refs, loc + ".evidence_refs", extra)
        allowed = {"book": {a.book_id}, "scope": {a.scope_id}, "page": set(source.payload.pages_expected),
                   "question": entities, "fragment": fragments, "region": regions,
                   "action": {x.action_id for item in ctx.bundle.artifacts if item.kind == "ApplyPlan"
                              for x in item.payload.actions}}[issue.scope_type]
        subset([issue.scope_id], allowed, loc + ".scope_id")
    if p.stage == "POST_APPLY":
        receipt = ctx.resolve(p.receipt, path + ".receipt", "ExecutionReceipt")
        plan = ctx.resolve(receipt.payload.plan, path + ".receipt.plan", "ApplyPlan")
        if plan.payload.graph != p.graph or plan.payload.policy != p.policy:
            fail(path, "POSTCHECK_BINDING", "postcheck graph/policy must match executed plan")
        if p.decision == "PASS" and (not receipt.payload.results or any(r.outcome != "APPLIED" for r in receipt.payload.results)):
            fail(path + ".decision", "UNPROVEN_APPLY", "POST_APPLY PASS requires all actions APPLIED")


def _plan(ctx, a, path, current_snapshot=None):
    p = a.payload
    graph = ctx.resolve(p.graph, path + ".graph", "QuestionGraph")
    pre = ctx.resolve(p.precheck, path + ".precheck", "CheckReport").payload
    target = ctx.resolve(p.targetcheck, path + ".targetcheck", "CheckReport").payload
    snapshot = ctx.resolve(p.snapshot, path + ".snapshot", "PlatformSnapshot")
    policy = ctx.policy(p.policy, path + ".policy")
    previous = None
    if p.previous_receipt is not None:
        previous = ctx.resolve(p.previous_receipt, path + ".previous_receipt", "ExecutionReceipt")
        previous_plan = ctx.resolve(previous.payload.plan, path + ".previous_receipt.plan", "ApplyPlan")
        if (previous_plan.payload.graph.artifact_id != p.graph.artifact_id
                or previous_plan.payload.graph.revision >= p.graph.revision):
            fail(path + ".previous_receipt", "DELTA_BASELINE", "old receipt must belong to a prior revision of this graph")
    if pre.stage != "PRE_APPLY" or target.stage != "TARGET":
        fail(path, "TWO_CHECK_STAGES", "plan needs distinct PRE_APPLY and TARGET reports")
    for name, report in (("precheck", pre), ("targetcheck", target)):
        if report.graph != p.graph or report.policy != p.policy:
            fail(path + "." + name, "VERSION_CONFLICT", "check graph/policy version differs from plan")
        if report.snapshot is not None and report.snapshot != p.snapshot:
            fail(path + "." + name + ".snapshot", "TARGET_CHANGED", "check snapshot version differs from plan")
    if current_snapshot is not None and artifact_ref(snapshot) != as_data(current_snapshot):
        fail(path + ".snapshot", "TARGET_CHANGED", "current snapshot differs; recheck and replan")
    if snapshot.payload.authorized_scope_id != a.scope_id:
        fail(path + ".snapshot", "AUTHORIZED_SCOPE", "snapshot authorization scope differs")
    if p.readiness == "BLOCKED":
        issue_ids = {i.issue_id for report in (pre, target) for i in report.issues}
        subset(p.blocked_issue_ids, issue_ids, path + ".blocked_issue_ids")
        if pre.decision == target.decision == "PASS":
            fail(path, "BLOCKED_BASIS", "blocked plan needs a failed/held check")
        return
    if pre.decision != "PASS" or target.decision != "PASS":
        fail(path, "TWO_PASS_REQUIRED", "READY plan requires both content and target PASS")
    if any(q.question_type in ("ordinary_choice", "seven_choice") for q in graph.payload.questions):
        if policy.option_grouping == "UNRESOLVED" or policy.confirmation_status == "UNRESOLVED":
            fail(path + ".policy", "POLICY_UNRESOLVED", "affected option grouping cannot silently pass")
    if policy.applicability == "SYNTHETIC_ONLY" and (p.execution_mode != "SIMULATED" or a.producer.evidence_mode != "SYNTHETIC"):
        fail(path + ".policy", "SYNTHETIC_ONLY", "demo assumption cannot authorize platform execution")
    if p.execution_mode == "PLATFORM" and (policy.applicability != "JOINT_CONFIRMED" or a.producer.evidence_mode != "OBSERVED"):
        fail(path, "POLICY_UNCONFIRMED", "platform eligibility requires confirmed policy and observed evidence")
    caps = {c.name: c for c in snapshot.payload.capabilities}
    required = set(p.required_capabilities) | {"frame_readback"}
    required.add("persistent_draft" if p.session_mode == "PERSISTENT" else "same_session_handoff")
    if any(action.operation == "UPDATE_FRAMES" for action in p.actions):
        required.add("frame_update")
    for cap in required:
        if cap not in caps or caps[cap].status != "VERIFIED":
            fail(path + ".required_capabilities", "CAPABILITY_UNVERIFIED", "required capability not verified: " + cap)
        if caps[cap].platform_version != snapshot.payload.platform_version:
            fail(path + ".required_capabilities", "CAPABILITY_VERSION", "capability was tested against a different platform version: " + cap)
    distinct([x.action_id for x in p.actions], path + ".actions")
    questions = {q.question_id: q for q in graph.payload.questions}
    platform_questions = {q.platform_question_id: q for q in snapshot.payload.questions}
    graph_path = ctx.paths[(graph.artifact_id, graph.revision)] + ".payload"
    for i, question in enumerate(graph.payload.questions):
        external = question.external_refs
        if external.platform_question_id is None:
            continue
        loc = graph_path + ".questions[{}].external_refs".format(i)
        if external.platform_question_id not in platform_questions:
            fail(loc + ".platform_question_id", "MISSING_REFERENCE", "existing question mapping is absent from the plan snapshot")
        existing = platform_questions[external.platform_question_id]
        if external.platform_order is not None and external.platform_order != existing.platform_order:
            fail(loc + ".platform_order", "PLATFORM_MAPPING_CONFLICT", "mapped question order differs from the plan snapshot")
    entities = set(questions) | {f.fragment_id for f in graph.payload.fragments}
    seen = set()
    for i, action in enumerate(p.actions):
        loc = path + ".actions[{}]".format(i)
        subset(action.depends_on, seen, loc + ".depends_on")
        subset([action.target.question_id], questions, loc + ".target.question_id")
        subset(action.source_entity_ids, entities, loc + ".source_entity_ids")
        question = questions[action.target.question_id]
        owned = {question.question_id} | set(question.fragment_ids) | set(question.shared_fragment_ids)
        owned.update(f for relation in graph.payload.answer_relations if relation.question_id == question.question_id
                     for f in relation.selected_fragment_ids)
        if not set(action.source_entity_ids).issubset(owned):
            fail(loc + ".source_entity_ids", "ACTION_OWNERSHIP", "action sources must belong to its target question")
        if action.target.target_id != snapshot.payload.target_id:
            fail(loc + ".target.target_id", "TARGET_CONFLICT", "action target differs from snapshot")
        platform_id = action.target.platform_question_id
        mapped_id = question.external_refs.platform_question_id
        target_path = loc + ".target.platform_question_id"
        if platform_id is not None:
            if platform_id not in platform_questions:
                fail(target_path, "MISSING_REFERENCE", "action platform question is absent from the plan snapshot")
            if mapped_id is None:
                fail(target_path, "PLATFORM_MAPPING_REQUIRED", "existing action target requires an explicit mapping on its internal question")
            if platform_id != mapped_id:
                fail(target_path, "PLATFORM_MAPPING_CONFLICT", "action target differs from its internal question's existing platform mapping")
        elif mapped_id is not None:
            fail(target_path, "PLATFORM_MAPPING_CONFLICT", "null target cannot replace an existing platform question mapping")
        if action.operation == "UPDATE_FRAMES" and p.previous_receipt is None:
            fail(loc, "DELTA_BASELINE", "updates must reference old receipt; actual delta support is out of C01")
        if action.operation == "UPDATE_FRAMES":
            previous_targets = {old.action_id: old.target.question_id for old in previous_plan.payload.actions}
            applied_questions = {previous_targets[r.action_id] for r in previous.payload.results if r.outcome == "APPLIED"}
            if action.target.question_id not in applied_questions:
                fail(loc, "DELTA_BASELINE", "update target has no APPLIED baseline action")
        seen.add(action.action_id)


def _receipt(ctx, a, path):
    p = a.payload
    plan = ctx.resolve(p.plan, path + ".plan", "ApplyPlan").payload
    distinct([r.action_id for r in p.results], path + ".results")
    if plan.readiness == "BLOCKED":
        if p.results or p.execution_mode != "NOT_EXECUTED" or p.write_disposition != "NOT_EXECUTED":
            fail(path, "BLOCKED_EXECUTION", "blocked plan must not have executed actions")
    else:
        if {r.action_id for r in p.results} != {a.action_id for a in plan.actions}:
            fail(path + ".results", "ACTION_COVERAGE", "every planned action requires exactly one result")
        if p.execution_mode != {"SIMULATED": "SIMULATED", "PLATFORM": "PLATFORM_OBSERVED"}[plan.execution_mode]:
            fail(path + ".execution_mode", "EVIDENCE_MODE", "receipt execution mode differs from plan")
        outcomes = {r.outcome for r in p.results}
        expected = "PAUSE_RECONCILE" if "UNKNOWN" in outcomes else "RECHECK_TARGET" if "NOT_APPLIED" in outcomes else "POSTCHECK"
        if p.write_disposition != expected:
            fail(path + ".write_disposition", "UNKNOWN_GUARD", "receipt disposition must follow worst unresolved action")
        if "UNKNOWN" in outcomes and not p.unresolved_issue_ids:
            fail(path + ".unresolved_issue_ids", "UNKNOWN_GUARD", "UNKNOWN requires unresolved issue")
    for i, result in enumerate(p.results):
        ctx.evrefs(result.before_evidence_refs, path + ".results[{}].before_evidence_refs".format(i))
        ctx.evrefs(result.after_evidence_refs, path + ".results[{}].after_evidence_refs".format(i))


def _patch(ctx, a, path):
    p = a.payload
    graph = ctx.resolve(p.baseline, path + ".baseline", "QuestionGraph")
    if p.result_revision != graph.revision + 1:
        fail(path + ".result_revision", "PATCH_REVISION", "patch must propose next immutable revision")
    fragments = {f.fragment_id: f for f in graph.payload.fragments}
    questions = {q.question_id: q for q in graph.payload.questions}
    relations = {r.relation_id: r for r in graph.payload.answer_relations}
    distinct([(c.entity_id, c.field) for c in p.changes], path + ".changes")
    for i, change in enumerate(p.changes):
        loc = path + ".changes[{}]".format(i)
        if change.field == "role":
            entity = fragments.get(change.entity_id)
            if change.after not in ("stem", "option", "answer", "explanation", "shared_material"):
                fail(loc + ".after", "PATCH_VALUE", "invalid generic role")
            before = entity.role if entity else None
        elif change.field == "printed_number":
            entity = questions.get(change.entity_id)
            if change.after is not None and not isinstance(change.after, str):
                fail(loc + ".after", "PATCH_VALUE", "printed number must be string or null")
            before = entity.external_refs.printed_number if entity else None
        else:
            entity = relations.get(change.entity_id)
            if not isinstance(change.after, list):
                fail(loc + ".after", "PATCH_VALUE", "answer selection must be a list")
            subset(change.after, entity.candidate_fragment_ids if entity else (), loc + ".after")
            before = entity.selected_fragment_ids if entity else None
        if entity is None:
            fail(loc + ".entity_id", "MISSING_ENTITY", "patch entity absent from exact baseline")
        if change.before != before:
            fail(loc + ".before", "PATCH_BASELINE", "expected old field does not match baseline")


def _batch(ctx, a, path):
    p = a.payload
    source = ctx.resolve(p.source, path + ".source", "SourceBundle")
    graph = ctx.resolve(p.graph, path + ".graph", "QuestionGraph")
    receipt = ctx.resolve(p.receipt, path + ".receipt", "ExecutionReceipt")
    post = ctx.resolve(p.postcheck, path + ".postcheck", "CheckReport").payload
    if p.scope_manifest != source.payload.scope_manifest:
        fail(path + ".scope_manifest", "DENOMINATOR_CHANGED", "batch must retain independent source scope manifest")
    if graph.payload.source != p.source or post.graph != p.graph or post.receipt != p.receipt or post.stage != "POST_APPLY":
        fail(path, "BATCH_BINDING", "batch source/graph/postcheck/receipt versions differ")
    _coverage(ctx, p.coverage, graph, path + ".coverage", p.state in ("COMPLETED", "READY_FOR_SUBMISSION"))
    checks = {c.check_id: c.outcome for c in post.checks}
    expected_frames = {"PASS": "PASS", "FAIL": "FAIL", "UNAVAILABLE": "UNAVAILABLE"}[checks["frame_structure"]]
    if p.frame_check_status != expected_frames:
        fail(path + ".frame_check_status", "FRAME_EVIDENCE", "frame result differs from postcheck")
    if p.content_check_status == "VERIFIED" and checks["final_content"] != "PASS":
        fail(path + ".content_check_status", "CONTENT_EVIDENCE", "verified content requires final-content PASS")
    if p.content_check_status == "MISMATCH" and checks["final_content"] != "FAIL":
        fail(path + ".content_check_status", "CONTENT_EVIDENCE", "mismatch requires final-content failure")
    if p.state in ("COMPLETED", "READY_FOR_SUBMISSION") and post.decision != "PASS":
        fail(path + ".state", "COMPLETION_GUARD", "completion/readiness requires POST_APPLY PASS")
    if any(r.outcome == "UNKNOWN" for r in receipt.payload.results):
        if p.state != "NEEDS_RECONCILIATION" or not p.unresolved_issue_ids or not any(q.state == "UNKNOWN" for q in p.questions):
            fail(path + ".state", "UNKNOWN_GUARD", "unknown write must pause batch for reconciliation")
        if p.content_check_status == "VERIFIED":
            fail(path + ".content_check_status", "UNKNOWN_GUARD", "unresolved write cannot have verified final content")
    plan = ctx.resolve(receipt.payload.plan, path + ".receipt.plan", "ApplyPlan")
    targets = {action.action_id: action.target.question_id for action in plan.payload.actions}
    statuses = {q.question_id: q.state for q in p.questions}
    for result in receipt.payload.results:
        if result.outcome == "UNKNOWN" and statuses.get(targets[result.action_id]) != "UNKNOWN":
            fail(path + ".questions", "UNKNOWN_QUESTION", "each unresolved action target must remain UNKNOWN")
        if result.outcome == "NOT_APPLIED" and statuses.get(targets[result.action_id]) == "VERIFIED":
            fail(path + ".questions", "UNAPPLIED_QUESTION", "unapplied action target cannot be VERIFIED")
    for i, question in enumerate(p.questions):
        if question.question_id not in {q.question_id for q in graph.payload.questions} and question.state == "VERIFIED":
            fail(path + ".questions[{}]".format(i), "UNRECOGNIZED_QUESTION", "missing graph question cannot be verified")
    ctx.evrefs(p.submission_evidence_refs, path + ".submission_evidence_refs")


def validate_bundle(bundle, asset_root=None, *, bridge_context=None):
    """Validate schema, exact dependencies, geometry, policy and state invariants.

    asset_root=None deliberately skips file-byte validation; load_bundle defaults to it on.
    Re-parse even model instances to catch mutations of nested Python lists/dicts.
    """
    version = bundle.get('format_version') if isinstance(bundle, dict) else getattr(bundle, 'format_version', None)
    if version == 'a03-exchange-4-proposal':
        from .a03_native import validate_native_bundle
        return validate_native_bundle(bundle, bridge_context=bridge_context, asset_root=asset_root)
    return _validate_c01_context(_Context(_parse_c01(bundle)), asset_root)


def _parse_c01(bundle):
    try:
        bundle = ExchangeBundle.model_validate(as_data(bundle))
    except ValidationError as error:
        raise ContractError([{"path": "$" + "".join("[{}]".format(x) if isinstance(x, int) else "." + x for x in e["loc"]),
                              "code": "SCHEMA", "message": e["msg"]} for e in error.errors(include_url=False)]) from error
    return bundle


class _NativeProjectionContext(_Context):
    """Private full-fact proof consumer, with no caller-provided allowed IDs."""

    def __init__(self, bundle, native):
        from .recovery import _native_receipt_issue_ownership, _identity, _legacy_projection_value
        proofs = _native_receipt_issue_ownership(native)
        expected, _ = _legacy_projection_value(native)
        if as_data(bundle) != as_data(_parse_c01(expected)):
            fail('$.receipt', 'NATIVE_ISSUE_OWNERSHIP', 'proof binds only the exact native semantic projection')
        super().__init__(bundle)
        self._receipt_proofs = {}
        for artifact in bundle.artifacts:
            if artifact.kind != 'ExecutionReceipt':
                continue
            proof = proofs.get(_identity(artifact.model_dump(mode='json')))
            if proof is None or list(artifact.payload.unresolved_issue_ids) != [i['issue_id'] for i in proof['issues']]:
                fail('$.receipt', 'NATIVE_ISSUE_OWNERSHIP', 'projection must preserve its own proven issue binding')
            self._receipt_proofs[(artifact.artifact_id, artifact.revision)] = (artifact_ref(artifact), proof)

    def receipt_issues(self, artifact):
        bound, proof = self._receipt_proofs[(artifact.artifact_id, artifact.revision)]
        if bound != artifact_ref(artifact):
            fail('$.receipt', 'NATIVE_ISSUE_OWNERSHIP', 'proof cannot be transferred to another projected consumer')
        return {issue['issue_id'] for issue in proof['issues']}


def _validate_native_projection(bundle, native):
    """Internal native-to-C01 adapter; original closure is checked, not IDs."""
    return _validate_c01_context(_NativeProjectionContext(_parse_c01(bundle), native), None)


def _validate_c01_context(ctx, asset_root):
    bundle = ctx.bundle
    _relationships(ctx)
    _resources(ctx, asset_root)
    handlers = {"SourceBundle": _source, "EvidenceBundle": _evidence, "QuestionGraph": _graph,
                "CheckReport": _check, "ApplyPlan": _plan, "ExecutionReceipt": _receipt,
                "ReviewPatch": _patch, "BatchReport": _batch}
    all_issues = {issue.issue_id for a in bundle.artifacts if a.kind == "CheckReport" for issue in a.payload.issues}
    for key, artifact in ctx.artifacts.items():
        path = ctx.paths[key] + ".payload"
        if artifact.kind in handlers:
            handlers[artifact.kind](ctx, artifact, path)
        if artifact.kind == "PlatformSnapshot":
            p = artifact.payload
            distinct(p.directories, path + ".directories")
            distinct([c.name for c in p.capabilities], path + ".capabilities")
            distinct([q.platform_question_id for q in p.questions], path + ".questions")
            distinct([f.platform_frame_id for f in p.frames], path + ".frames")
            for i, question in enumerate(p.questions):
                if question.directory_id not in p.directories:
                    fail(path + ".questions[{}].directory_id".format(i), "MISSING_REFERENCE", "platform question directory is absent from this snapshot")
            for i, cap in enumerate(p.capabilities):
                ctx.evrefs(cap.evidence_refs, path + ".capabilities[{}].evidence_refs".format(i))
            ctx.evrefs(p.evidence_refs, path + ".evidence_refs")
            for i, frame in enumerate(p.frames):
                subset([frame.platform_question_id], {q.platform_question_id for q in p.questions}, path + ".frames[{}]".format(i))
        for name in ("unresolved_issue_ids", "related_issue_ids"):
            if hasattr(artifact.payload, name):
                allowed = all_issues
                if type(ctx) is _NativeProjectionContext and artifact.kind == 'ExecutionReceipt' and name == 'unresolved_issue_ids':
                    allowed = all_issues | ctx.receipt_issues(artifact)
                subset(getattr(artifact.payload, name), allowed, path + "." + name)
        if artifact.producer.evidence_mode == "OBSERVED":
            # A synthetic evidence file cannot be relabeled into an observation chain.
            for location, value in walk(artifact, ctx.paths[key]):
                if isinstance(value, list) and location.endswith("evidence_refs"):
                    for evidence_id in value:
                        if evidence_id in ctx.evidence and ctx.evidence[evidence_id].mode == "SYNTHETIC":
                            fail(location, "SYNTHETIC_EVIDENCE", "observed artifact references synthetic evidence")
    return bundle


def load_bundle(path, verify_assets=True):
    path = Path(path)
    try:
        data = read_json(path)
    except (OSError, ValueError) as error:
        fail("$", "JSON_INPUT", str(error))
    return validate_bundle(data, path.parent if verify_assets else None)


def assert_plan_ready(bundle, plan_ref, current_snapshot_ref):
    """Check eligibility against an explicit current snapshot; performs no I/O or action."""
    bundle = validate_bundle(bundle)
    ctx = _Context(bundle)
    try:
        plan_ref = ArtifactRef.model_validate(as_data(plan_ref))
        current_snapshot_ref = ArtifactRef.model_validate(as_data(current_snapshot_ref))
    except ValidationError as error:
        fail("$.eligibility", "SCHEMA", str(error))
    plan = ctx.resolve(plan_ref, "$.plan", "ApplyPlan")
    ctx.resolve(current_snapshot_ref, "$.current_snapshot", "PlatformSnapshot")
    if plan.payload.readiness != "READY":
        fail("$.plan.readiness", "PLAN_BLOCKED", "diagnostic plan is not eligible")
    _plan(ctx, plan, "$.plan.payload", current_snapshot_ref)
    # A fresh plan ID cannot bypass an unresolved write elsewhere in this book.
    for artifact in bundle.artifacts:
        if artifact.kind == "ExecutionReceipt" and artifact.book_id == plan.book_id:
            if any(r.outcome == "UNKNOWN" for r in artifact.payload.results):
                fail("$.plan", "BOOK_WRITE_PAUSED", "UNKNOWN receipt requires reconciliation before any book write")
    return plan


def assert_patch_base(bundle, patch_ref, baseline_ref):
    bundle = validate_bundle(bundle)
    ctx = _Context(bundle)
    try:
        patch_ref = ArtifactRef.model_validate(as_data(patch_ref))
        baseline_ref = ArtifactRef.model_validate(as_data(baseline_ref))
    except ValidationError as error:
        fail("$.patch", "SCHEMA", str(error))
    patch = ctx.resolve(patch_ref, "$.patch", "ReviewPatch")
    ctx.resolve(baseline_ref, "$.baseline", "QuestionGraph")
    if patch.payload.baseline != baseline_ref:
        fail("$.patch.payload.baseline", "PATCH_BASELINE", "patch may only apply to its exact baseline version")
    return patch
