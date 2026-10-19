"""Read the fixed B four-case stage without loading external B objects or code."""

import hashlib
import copy
import io
import json
import math
import stat
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image

from ._profile import PROFILE


VERSION = "a08-fixed-stage-readonly/0.1"
PRIORITY_CASE = "q4-first-lesson"
ZERO_ACTIONS = {k: 0 for k in (
    "plans", "targets", "new_c01_execution_objects", "simulation_dispatches",
    "platform_calls", "paid_model_calls", "b_messages", "pushes")}


class BatchReceptionError(ValueError):
    def __init__(self, layer, code, path, detail):
        self.layer, self.code, self.path, self.detail = layer, code, path, detail
        super().__init__("%s/%s at %s: %s" % (layer, code, path, detail))

    def as_dict(self):
        return {"report_schema": VERSION, "status": "REJECTED", "decision": "HOLD",
                "business_acceptance": False, "layer": self.layer, "code": self.code,
                "path": self.path, "detail": self.detail, "actions": dict(ZERO_ACTIONS)}


def need(condition, layer, code, path, detail):
    if not condition:
        raise BatchReceptionError(layer, code, path, detail)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def parse(raw, path):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            need(k not in result, "JSON", "DUPLICATE_KEY", path, k)
            result[k] = v
        return result

    def constant(value):
        raise BatchReceptionError("JSON", "NON_FINITE_VALUE", path, value)

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=constant)
        # Also catches a finite-looking exponent that overflows the JSON decoder's float.
        canonical(value)
        return value
    except (UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, BatchReceptionError):
            raise
        raise BatchReceptionError("JSON", "INVALID_JSON", path, str(exc)) from exc


def safe_path(name):
    need(isinstance(name, str) and bool(name) and "\\" not in name and ":" not in name
         and "\x00" not in name and not name.startswith("/"),
         "ZIP", "UNSAFE_PATH", str(name), "only relative POSIX member paths are supported")
    parts = name.split("/")
    need(all(p and p not in (".", "..") and not p.endswith((".", " ")) for p in parts)
         and str(PurePosixPath(name)) == name,
         "ZIP", "UNSAFE_PATH", name, "empty, traversal or ambiguous component")
    return name


def read_zip(path):
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
        need(len(raw) <= 8 * 1024 * 1024, "ZIP", "SIZE_LIMIT", "$", "ZIP exceeds 8 MiB")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            need(0 < len(infos) <= 64, "ZIP", "MEMBER_LIMIT", "$", "1..64 members required")
            members, total = {}, 0
            for entry in infos:
                name = safe_path(entry.filename)
                mode = entry.external_attr >> 16
                need(name not in members and not entry.is_dir() and not stat.S_ISLNK(mode)
                     and not (entry.flag_bits & 1), "ZIP", "UNSUPPORTED_MEMBER", name,
                     "duplicate, directory, symlink or encrypted member")
                total += entry.file_size
                need(0 <= entry.file_size <= 8 * 1024 * 1024 and total <= 16 * 1024 * 1024,
                     "ZIP", "EXPANDED_SIZE_LIMIT", name, "expanded bytes exceed fixed limits")
                members[name] = archive.read(entry)
        return raw, members
    except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise BatchReceptionError("ZIP", "INPUT_READ_FAILED", "$", str(exc)) from exc


def manifest(members, document, prefix):
    need(isinstance(document, dict) and isinstance(document.get("files"), list),
         "MANIFEST", "INVALID_MANIFEST", prefix + "manifest.json", "files array required")
    rows = document["files"]
    declared = set()
    for i, row in enumerate(rows):
        path = prefix + "manifest.json/files/" + str(i)
        need(isinstance(row, dict) and set(row) == {"path", "bytes", "sha256"},
             "MANIFEST", "INVALID_ENTRY", path, "path/bytes/sha256 required")
        name = prefix + safe_path(row["path"])
        need(name not in declared and name in members, "MANIFEST", "MEMBER_COVERAGE", name,
             "duplicate or missing declared member")
        declared.add(name)
        need(type(row["bytes"]) is int and row["bytes"] == len(members[name]),
             "MANIFEST", "MEMBER_SIZE", name, "declared and observed bytes differ")
        need(row["sha256"] == sha(members[name]), "MANIFEST", "MEMBER_DIGEST", name,
             "declared and observed SHA256 differ")
    actual = {n for n in members if n.startswith(prefix)} - {prefix + "manifest.json"}
    need(declared == actual, "MANIFEST", "MEMBER_COVERAGE", prefix + "manifest.json",
         "manifest must cover every member except itself")


def equal_fields(actual, expected, layer, code, path):
    need(isinstance(actual, dict), "SHAPE", "OBJECT_REQUIRED", path, "object required")
    for key, value in expected.items():
        need(key in actual and type(actual[key]) is type(value) and actual[key] == value,
             layer, code, path + "/" + key, "differs from fixed a76e5a9 case/source identity")


def no_escalation(value, path):
    """Observed completion/structural flags never count as business permission."""
    if isinstance(value, dict):
        for key, item in value.items():
            where = path + "/" + key
            normalized = key.lower()
            need(not any(word in normalized for word in ("approval", "approved", "exclusions")),
                 "AUTHORIZATION", "CASE_APPROVAL_ESCALATION", where,
                 "A08 accepts no approval transfer, Q1 exclusions or added approval marker")
            if key in ("business_acceptance", "human_verified", "joint_accepted",
                       "platform_eligible", "transcription_verified"):
                need(item is False, "AUTHORIZATION", "CASE_APPROVAL_ESCALATION", where,
                     "fixed stage remains unapproved")
            if key == "verification_status":
                need(item == "UNVERIFIED", "AUTHORIZATION", "CASE_APPROVAL_ESCALATION", where,
                     "source verification must remain UNVERIFIED")
            no_escalation(item, where)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            no_escalation(item, path + "/" + str(i))


def geometry(value, assets, path, inherited_asset=None):
    if isinstance(value, dict):
        asset_id = value.get("asset_id", inherited_asset)
        if "asset_id" in value:
            need(asset_id in assets, "SOURCE", "UNKNOWN_ASSET", path + "/asset_id", str(asset_id))
        if asset_id in assets:
            asset = assets[asset_id]
            for key in ("bbox", "original_bbox", "revised_bbox", "trimmed_bbox"):
                if key not in value:
                    continue
                box = value[key]
                need(isinstance(box, list) and len(box) == 4 and all(
                    type(x) in (int, float) and math.isfinite(x) for x in box),
                    "SOURCE", "INVALID_BOX", path + "/" + key, "four finite coordinates required")
                need(0 <= box[0] < box[2] <= asset["width"] and
                     0 <= box[1] < box[3] <= asset["height"], "SOURCE", "BOX_OUTSIDE_ASSET",
                     path + "/" + key, "coordinates exceed their own original image")
            for key, expected in (("source_sha256", asset["sha256"]),
                                  ("source_size", [asset["width"], asset["height"]])):
                if key in value:
                    need(value[key] == expected, "SOURCE", "GEOMETRY_SOURCE_BINDING",
                         path + "/" + key, "geometry binds a different original image")
        for key, item in value.items():
            geometry(item, assets, path + "/" + key, asset_id)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            geometry(item, assets, path + "/" + str(i), inherited_asset)


def case_structure(case, fixed, assets, path):
    answer, question = case["answer_snapshot"], case["question_snapshot"]
    need(isinstance(answer.get("fragments"), list) and isinstance(answer.get("regions"), list),
         "STRUCTURE", "MISSING_FRAGMENTS_OR_REGIONS", path + "/answer_snapshot", "arrays required")
    contents = answer.get("content_fragments", [])
    renders = answer.get("render_regions", [])
    need(isinstance(contents, list) and isinstance(renders, list), "STRUCTURE", "ARRAY_REQUIRED",
         path + "/answer_snapshot", "content_fragments/render_regions must be arrays")
    runs = []
    for i, content in enumerate(contents):
        need(isinstance(content, dict) and isinstance(content.get("runs", []), list),
             "STRUCTURE", "INVALID_RUNS", path + "/answer_snapshot/content_fragments/" + str(i),
             "structured runs must be an array")
        for j, run in enumerate(content.get("runs", [])):
            need(isinstance(run, dict) and run.get("format") in ("plain", "latex")
                 and isinstance(run.get("text"), str), "STRUCTURE", "INVALID_RUN",
                 path + "/answer_snapshot/content_fragments/%d/runs/%d" % (i, j),
                 "plain/latex text required")
            if run["format"] == "latex":
                runs.append({"content_fragment_id": content.get("content_fragment_id"),
                             "run_index": j, "source_path": path +
                             "/answer_snapshot/content_fragments/%d/runs/%d" % (i, j),
                             "run": run})
    counts = {"raw_fragments": len(answer["fragments"]), "render_regions": len(renders),
              "latex_runs": len(runs)}
    equal_fields(counts, fixed["envelope"]["counts"], "STRUCTURE", "FIXED_COUNT_MISMATCH",
                 path + "/observed_counts")
    equal_fields(case["counts"], counts, "STRUCTURE", "DECLARED_COUNT_MISMATCH", path + "/counts")
    need(isinstance(answer.get("continuations"), list) and
         len(answer["continuations"]) == fixed["continuations"], "STRUCTURE", "MISSING_CONTINUATION",
         path + "/answer_snapshot/continuations", "fixed continuation inventory changed")
    need(len(answer["regions"]) == fixed["regions"], "STRUCTURE", "FIXED_REGION_COUNT",
         path + "/answer_snapshot/regions", "fixed region inventory changed")
    if question is not None:
        need(isinstance(question.get("fragments"), list) and
             len(question["fragments"]) == fixed["question_fragments"],
             "STRUCTURE", "QUESTION_FRAGMENT_COUNT", path + "/question_snapshot/fragments",
             "fixed question fragment inventory changed")
    raw_ids = [f["fragment_id"] for f in answer["fragments"]]
    need(len(raw_ids) == len(set(raw_ids)), "STRUCTURE", "DUPLICATE_FRAGMENT", path, "unique fragment IDs required")
    order = answer.get("content_projection", {}).get("source_fragment_order", [])
    need(isinstance(order, list) and len(order) == len(set(order)) and set(order) <= set(raw_ids),
         "STRUCTURE", "SOURCE_ORDER_BINDING", path + "/answer_snapshot/content_projection/source_fragment_order",
         "text order must refer to unique original fragments; image coverage is separate")
    coverage = {kind: {fid for r in renders if r.get("content_type") == kind
                       for fid in r.get("source_fragment_ids", [])} for kind in ("text", "image")}
    if renders:
        need(coverage["text"] | coverage["image"] == set(raw_ids), "STRUCTURE", "SOURCE_COVERAGE",
             path + "/answer_snapshot/render_regions", "raw text/image source coverage changed")
    geometry(case, assets, path)
    for name, value in (("question", question), ("answer", answer)):
        need(sha(canonical(value)) == fixed[name + "_sha256"], "SNAPSHOT_BINDING",
             "FROZEN_SNAPSHOT_CHANGED", path + "/" + name + "_snapshot",
             "snapshot differs from fixed B stage; no content approval is inferred")
    return {"observed_counts": counts, "structured_latex_runs": runs,
            "text_source_fragment_order": order,
            "render_text_source_count": len(coverage["text"]),
            "render_image_source_count": len(coverage["image"]),
            "latex_metric_scope": "content_fragments[].runs only; zero does not imply no mathematics"}


def support_matrix():
    return {
        "N01": {"status": "PARTIAL", "implemented": "fixed stage explicit case routing and version gates",
                "pending": ["complete G0.8/Check0.8/plan0.3 objects", "new C01"]},
        "N02": {"status": "SUPPORTED_FIXED_STAGE_READONLY", "pending": ["three missing question identities/relations"]},
        "N03": {"status": "PARTIAL", "implemented": "preserve source order, per-asset geometry and unknown viewer mapping",
                "pending": ["content/continuation business qualification", "non-prefix coverage"]},
        "N04": {"status": "PARTIAL", "implemented": "preserve plain/latex runs, original fragments and figure records",
                "pending": ["formula parsing", "formula/figure/role policy approval"]},
        "N05": {"status": "PARTIAL", "implemented": "preserve original/revised geometry and B pixel claims as data",
                "pending": ["new cropping", "pixel-claim recomputation", "transform policy approval"]},
        "N06": {"status": "PENDING", "pending": ["current complete Check", "per-case policy/issue applicability/content approval"]},
        "N07": {"status": "PENDING", "pending": ["PRE_APPLY", "TARGET", "plan", "simulation authorization and implementation"]},
        "N08": {"status": "PARTIAL", "implemented": "fixed receiver refusal fields and separate HOLD diagnostics",
                "pending": ["execution readback", "per-frame business comparison"]},
    }


def _receive(path, priority_case):
    need(priority_case == PRIORITY_CASE, "SCOPE", "UNSUPPORTED_PRIORITY_CASE", "priority_case",
         "A08 priority is q4-first-lesson only")
    raw, members = read_zip(path)
    need("manifest.json" in members and "staging/manifest.json" in members,
         "MANIFEST", "MISSING_MANIFEST", "$", "outer and stage manifests required")
    outer = parse(members["manifest.json"], "manifest.json")
    equal_fields(outer, {"schema": "b-complex-batch-evidence-package/0.1"},
                 "VERSION", "UNSUPPORTED_OUTER_SCHEMA", "manifest.json")
    manifest(members, outer, "")
    inner = parse(members["staging/manifest.json"], "staging/manifest.json")
    manifest(members, inner, "staging/")
    need("staging/batch.json" in members, "SHAPE", "MISSING_BATCH", "$", "stage batch required")
    batch = parse(members["staging/batch.json"], "staging/batch.json")
    equal_fields(batch, {"schema_version": "b-complex-batch-proposal/0.1",
                         "kind": "ComplexCaseBatchProposal"}, "VERSION", "UNSUPPORTED_BATCH_VERSION",
                 "staging/batch.json")
    no_escalation(batch, "staging/batch.json")
    equal_fields(outer, {"decision": "HOLD", "a_support": "PENDING_EXTENSION"},
                 "AUTHORIZATION", "CASE_APPROVAL_ESCALATION", "manifest.json")
    equal_fields(batch, {"decision": "HOLD", "business_acceptance": False,
                         "human_verified": False, "platform_actions": []},
                 "AUTHORIZATION", "CASE_APPROVAL_ESCALATION", "staging/batch.json")
    assets_list = batch.get("assets")
    need(isinstance(assets_list, list) and len(assets_list) == 3, "SOURCE", "ASSET_INVENTORY",
         "staging/batch.json/assets", "three separate original assets required")
    assets = {}
    for i, asset in enumerate(assets_list):
        where = "staging/batch.json/assets/" + str(i)
        need(isinstance(asset, dict) and asset.get("asset_id") not in assets, "SOURCE",
             "ASSET_IDENTITY_CONFLICT", where, "unique original asset identity required")
        fixed = next((a for a in PROFILE["assets"] if a["asset_id"] == asset.get("asset_id")), None)
        need(fixed is not None, "SOURCE", "ASSET_IDENTITY_CONFLICT", where, "unregistered asset identity")
        equal_fields(asset, fixed, "SOURCE", "ASSET_IDENTITY_CONFLICT", where)
        assets[asset["asset_id"]] = asset
        name = "staging/" + safe_path(asset["path"])
        need(name in members and sha(members[name]) == asset["sha256"], "SOURCE", "ASSET_DIGEST", name,
             "original asset SHA256 differs")
        try:
            with Image.open(io.BytesIO(members[name])) as im:
                im.verify()
            with Image.open(io.BytesIO(members[name])) as im:
                im.load()
                need(im.format == "JPEG" and list(im.size) == [asset["width"], asset["height"]],
                     "SOURCE", "ASSET_DIMENSIONS", name, "JPEG original dimensions differ")
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            if isinstance(exc, BatchReceptionError):
                raise
            raise BatchReceptionError("SOURCE", "IMAGE_DECODE", name, str(exc)) from exc
    cases = batch.get("cases")
    need(isinstance(cases, list) and len(cases) == 4, "IDENTITY", "CASE_INVENTORY",
         "staging/batch.json/cases", "exactly four fixed cases required")
    diagnostics, seen = [], set()
    for i, case in enumerate(cases):
        where = "staging/batch.json/cases/" + str(i)
        need(isinstance(case, dict), "SHAPE", "OBJECT_REQUIRED", where, "case object required")
        cid = case.get("case_id")
        need(cid in PROFILE["cases"] and cid not in seen, "IDENTITY", "CASE_INVENTORY", where,
             "unregistered or duplicate case")
        seen.add(cid)
        fixed = PROFILE["cases"][cid]
        for key in ("decision", "human_verified", "joint_accepted", "platform_eligible"):
            equal_fields(case, {key: fixed["envelope"][key]}, "AUTHORIZATION", "CASE_APPROVAL_ESCALATION", where)
        if fixed["question_identity"] is None:
            need("question_id" in case and "question_snapshot" in case and case["question_id"] is None
                 and case["question_snapshot"] is None and case.get("mode") == "ANSWER_EVIDENCE_ONLY",
                 "IDENTITY", "FABRICATED_QUESTION_OR_RELATION", where,
                 "answer evidence cannot acquire a question, candidate or selected relation")
        identity = {k: v for k, v in fixed["envelope"].items() if k not in (
            "blockers", "counts", "decision", "human_verified", "joint_accepted", "platform_eligible")}
        equal_fields(case, identity, "IDENTITY", "CROSS_SCOPE_OR_CASE_IDENTITY", where)
        equal_fields(case.get("answer_snapshot"), fixed["answer_identity"],
                     "IDENTITY", "CROSS_SCOPE_OR_CASE_IDENTITY", where + "/answer_snapshot")
        if fixed["question_identity"] is not None:
            equal_fields(case.get("question_snapshot"), fixed["question_identity"],
                         "IDENTITY", "CROSS_SCOPE_OR_CASE_IDENTITY", where + "/question_snapshot")
        need(set(case) == set(fixed["envelope"]) | {"question_snapshot", "answer_snapshot"},
             "SHAPE", "UNREGISTERED_CASE_FIELDS", where, "fixed stage case fields required")
        equal_fields(case, {"blockers": fixed["envelope"]["blockers"]},
                     "AUTHORIZATION", "CASE_APPROVAL_ESCALATION", where)
        standalone = "staging/cases/" + cid + ".json"
        need(standalone in members and parse(members[standalone], standalone) == case,
             "BINDING", "CASE_BATCH_MISMATCH", standalone, "batch and separate case must match")
        structure = case_structure(case, fixed, assets, where)
        diagnostics.append({"case_id": cid, "mode": case["mode"], "decision": "HOLD",
            "business_acceptance": False, "platform_eligible": False,
            "content_approval": "PENDING", "region_approval": "PENDING", "case_policy_approval": "PENDING",
            "question_id": case["question_id"], "answer_id": case["answer_id"],
            "section_path": case["section_path"], "printed_number": case["printed_number"],
            "source_asset_ids": case["source_asset_ids"], "blockers": case["blockers"],
            "candidate_relation": ({"status": "B_DECLARED_CANDIDATE_ONLY",
                "question_id": case["question_id"], "answer_id": case["answer_id"],
                "source_selected_answer_id": case["question_snapshot"]["selected_answer_id"],
                "a_selected_relation_created": False} if case["question_id"] else None),
            "source_case_member": standalone, "source_case_sha256": sha(members[standalone]),
            "structure": structure, "source_snapshot": case})
    equal_fields(batch, PROFILE["batch_metadata"], "BINDING", "BATCH_SOURCE_BINDING", "staging/batch.json")
    need(set(batch) == set(PROFILE["batch_metadata"]) | {"assets", "cases"},
         "SHAPE", "UNREGISTERED_BATCH_FIELDS", "staging/batch.json", "fixed batch fields required")
    receipt = parse(members["staging/receipt.json"], "staging/receipt.json")
    equal_fields(receipt, {"batch_file_sha256": sha(members["staging/batch.json"]), "cases": 4,
                           "question_answer_candidates": 1, "answer_evidence_only": 3,
                           "business_acceptance": False, "source_graph_ref": batch["source_graph_ref"],
                           "source_package_sha256": batch["source_package_sha256"]},
                 "BINDING", "STAGE_RECEIPT_BINDING", "staging/receipt.json")
    # These pins run after the explicit version/identity/HOLD/structure gates. Repacked
    # negative inputs can therefore reach those gates, but can never be accepted.
    need(set(members) == {r["path"] for r in PROFILE["members"]}, "FIXED_INPUT", "MEMBER_INVENTORY",
         "$", "only the registered stage package is consumable")
    for row in PROFILE["members"]:
        need(len(members[row["path"]]) == row["bytes"] and sha(members[row["path"]]) == row["sha256"],
             "FIXED_INPUT", "RAW_MEMBER_BINDING", row["path"], "raw bytes differ from fixed a76e5a9 member")
    need(len(raw) == PROFILE["package_bytes"] and sha(raw) == PROFILE["package_sha256"],
         "FIXED_INPUT", "PACKAGE_BINDING", "$", "only the exact registered original ZIP may succeed")
    diagnostics.sort(key=lambda d: d["case_id"] != priority_case)
    return {"report_schema": VERSION, "status": "RECEIVED_READONLY_HOLD", "decision": "HOLD",
        "business_acceptance": False, "priority_case": priority_case,
        "input": {"b_commit": PROFILE["b_commit"], "zip_sha256": sha(raw), "zip_bytes": len(raw),
                  "source_git_blob": PROFILE["source_git_blob"], "raw_members": PROFILE["members"],
                  "zip_member_count": len(members), "outer_manifest_entries": len(outer["files"]),
                  "inner_manifest_entries": len(inner["files"])},
        "observed_versions": {"outer_schema": outer["schema"], "batch_kind": batch["kind"],
                              "batch_schema": batch["schema_version"],
                              "content_projection": "b-content-projection-trial/0.3 (embedded snapshots only)"},
        "external_objects": {"status": "DECLARED_ONLY_EXTERNAL_NOT_LOADED",
            "complete_G_Check_plan_objects_loaded": False, "source_graph_ref": batch["source_graph_ref"],
            "source_graph_file_sha256": batch["source_graph_file_sha256"],
            "source_package_sha256": batch["source_package_sha256"],
            "g08_check08_plan03_claim": "B_DECLARATION_ONLY; not complete-object schema validation",
            "embedded_projection_and_continuation_refs": "PRESERVED_DECLARATIONS_NOT_LOADED"},
        "assets": assets_list, "cases": diagnostics,
        "summary": {"cases": 4, "assets": 3, "question_answer_candidates": 1,
                    "answer_evidence_only": 3, "hold_cases": 4},
        "support_matrix": support_matrix(), "q1_authorization_transfer_allowed": False,
        "embedded_code_or_historical_test_results_used_as_acceptance": False,
        "scope": "A08 fixed-stage reception structure only; no business qualification",
        "coordinate_convention": "original image [x1,y1,x2,y2), per-asset SHA and dimensions",
        "actions": dict(ZERO_ACTIONS)}


def receive_package(package, *, priority_case=PRIORITY_CASE):
    """Return a new JSON-compatible diagnostic dict; read only the given fixed ZIP.

    Failure raises BatchReceptionError with the actual reached layer/code/path.
    There is no approval, external-object-loading, planning or execution option.
    """
    try:
        return copy.deepcopy(_receive(package, priority_case))
    except (KeyError, TypeError, IndexError, AttributeError, RecursionError, ValueError) as exc:
        if isinstance(exc, BatchReceptionError):
            raise
        raise BatchReceptionError("SHAPE", "UNSUPPORTED_INPUT_SHAPE", "$", str(exc)) from exc
