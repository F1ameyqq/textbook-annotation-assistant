"""A24 pure, evidence-bound unified-commit codec. No client or resource creation.

Field paths describe a captured CURRENT response schema; they are not discovery
instructions. A missing schema/proof is a denial, including for old-body reads.
"""
import copy
from datetime import datetime, timezone
import hashlib
import json
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

from annotation.contracts import policy_ref
from annotation.contracts.integrity import unique_object
from annotation.quality.live_pilot import BOOK, require
from annotation.runtime.storage.common import digest

COMMIT = "/qieti/api/annotate_pic/commit_unified_submit"
FRAMES = "/qieti/api/annotate_pic/get_manual_annotations_unified_by_order_in_level"
INFO = "/qieti/api/annotate_pic/get_question_info"
CONTENT = "/qieti/api/verify_annotation/get-ocr-annotation"
SIGNATURE = "/qieti/api/annotate_pic/oss_signature"
EXPORT = "/qieti/api/annotate_ocr/export-paper-questions/" + BOOK
ZONES = ("question", "choice", "answer", "analysis", "knowledge_point")
PROOFS = ("schema", "receipt", "readback", "old_body", "source_mapping", "crops",
          "insertion", "newness", "joint_policy", "request_manifest", "exclusive_session")
TOP_FIELDS = {"file_id", "target_directory_id", "question_order", "is_new_question_insertion",
              "insert_after_order", "annotations_upsert", "annotations_delete_rect_ids",
              "ocr_submissions", "ocr_delete_zones", "question_info", "created_by"}
ROW_FIELDS = {"rect_id", "type", "belong_to_level", "order_in_level",
              "image_order_in_annotation_zone", "rect_bbox", "page_index", "image_path",
              "parent_rect_id", "directory_id", "content_type", "user_id",
              "is_pre_annotation", "pre_annotations_id"}
SNAPSHOT_FIELDS = ("book_id", "platform_version", "view", "directory_details",
                   "source_bindings", "submission_status", "complete", "read_status")
IDENTITY_OUTPUT_FIELDS = {"platform_question_id", "platform_frame_id", "directory_id", "rect_id"}
IDENTITY_CONTAINER_FIELDS = {"view", "target", "questions", "frames", "directory_details", "directories"}


def canonical_id(value):
    return isinstance(value, str) and bool(value) and value.strip() == value


def direct_from(rule):
    return (isinstance(rule, dict) and set(rule) == {"from"} and
            isinstance(rule["from"], dict) and set(rule["from"]) == {"response", "path"})


def validate_identity_projection(rule, identity_container=False):
    """Identity leaves/containers must remain direct; unrelated lookups stay legal."""
    require(isinstance(rule, dict) and len(rule) == 1, "SNAPSHOT_PROJECTION_RULE")
    kind, spec = next(iter(rule.items()))
    if identity_container and kind == "from":
        require(direct_from(rule), "IDENTITY_FROM_RESPONSE_REQUIRED")
        return True
    if identity_container:
        require(kind in ("object", "array"), "IDENTITY_FROM_RESPONSE_REQUIRED")
    if kind == "object":
        require(isinstance(spec, dict), "SNAPSHOT_PROJECTION_RULE")
        for key, child in spec.items():
            if key in IDENTITY_OUTPUT_FIELDS:
                require(direct_from(child), "IDENTITY_FROM_RESPONSE_REQUIRED")
            validate_identity_projection(child, key in IDENTITY_CONTAINER_FIELDS)
    elif kind == "array":
        require(isinstance(spec, dict) and "item" in spec, "SNAPSHOT_PROJECTION_RULE")
        if identity_container:
            require("source" in spec and direct_from(spec["source"]), "IDENTITY_FROM_RESPONSE_REQUIRED")
        validate_identity_projection(spec["item"], identity_container)
    return True


def public_read_manifest(reads):
    """Exact scope identity without persisting account/query values."""
    result = {}
    for phase, spec in reads.items():
        requests = spec.get("requests", [spec])
        result[phase] = {"requests": [{"slot": r.get("name", "snapshot"), "path_template": r["path"],
            "method": "GET", "count": r["count"], "query_keys": sorted(r["params"]),
            "query_hash": digest(r["params"])} for r in requests], "schema_hash": digest(spec)}
        if "export" in spec:
            e = spec["export"]
            result[phase]["export"] = {"path_template": e["path"], "method": "GET", "count": 1,
                "query_keys": sorted(e["params"]), "query_hash": digest(e["params"]), "codec_hash": digest(e["codec"])}
    return result


def require_window(value):
    now = datetime.now(timezone.utc)
    start = datetime.fromisoformat(value["starts_at"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(value["ends_at"].replace("Z", "+00:00"))
    require(start.tzinfo is not None and end.tzinfo is not None and start <= now <= end, "AUTHORIZATION_WINDOW")


def field(value, path):
    require(isinstance(path, list) and all(isinstance(k, (str, int)) and not isinstance(k, bool)
                                        for k in path), "WIRE_FIELD_PATH")
    for key in path:
        require((isinstance(value, dict) and key in value) or
                (isinstance(value, list) and type(key) is int and 0 <= key < len(value)),
                "WIRE_RESPONSE_SCHEMA")
        value = value[key]
    return value


def project(rule, responses, current=None):
    """Small declarative JSON adapter; no Python/JS evaluation or guessed fields.

    Paths, literal source metadata and lookup tables are part of the approved
    schema proof. Server order can only be read from its captured record.
    """
    require(isinstance(rule, dict) and len(rule) == 1, "SNAPSHOT_PROJECTION_RULE")
    kind, spec = next(iter(rule.items()))
    if kind == "from":
        require(set(spec) == {"response", "path"} and (spec["response"] == "$" or spec["response"] in responses),
                "SNAPSHOT_PROJECTION_SOURCE")
        return copy.deepcopy(field(current if spec["response"] == "$" else responses[spec["response"]], spec["path"]))
    if kind == "object":
        require(isinstance(spec, dict), "SNAPSHOT_PROJECTION_RULE")
        return {key: project(value, responses, current) for key, value in spec.items()}
    if kind == "literal":
        return copy.deepcopy(spec)
    if kind == "array":
        require(set(spec).issubset({"source", "item", "children_path", "where"}) and
                {"source", "item"}.issubset(spec), "SNAPSHOT_PROJECTION_RULE")
        records = project(spec["source"], responses, current)
        require(isinstance(records, list), "SNAPSHOT_PROJECTION_RECORDS")
        flat = []
        def visit(values):
            for item in values:
                flat.append(item)
                if "children_path" in spec:
                    children = field(item, spec["children_path"])
                    require(isinstance(children, list), "SNAPSHOT_PROJECTION_RECORDS")
                    visit(children)
        visit(records)
        if "where" in spec:
            require(set(spec["where"]) == {"path", "equals"}, "SNAPSHOT_PROJECTION_RULE")
            flat = [item for item in flat if field(item, spec["where"]["path"]) == spec["where"]["equals"]]
        return [project(spec["item"], responses, item) for item in flat]
    if kind == "lookup":
        require(set(spec) == {"key", "table"}, "SNAPSHOT_PROJECTION_RULE")
        key = str(project(spec["key"], responses, current))
        require(key in spec["table"], "SNAPSHOT_LOOKUP_UNKNOWN")
        return copy.deepcopy(spec["table"][key])
    if kind == "csv_bbox":
        raw = project(spec, responses, current)
        require(isinstance(raw, str) and len(raw.split(",")) == 4, "WIRE_BBOX")
        values = [float(v) for v in raw.split(",")]
        digest(values)  # Reject NaN/Infinity via canonical serialization.
        return values
    require(False, "SNAPSHOT_PROJECTION_RULE")


def read_evidence(bundle, identity, asset_root, mode):
    matches = [e for e in bundle.evidence if e.evidence_id == identity]
    require(len(matches) == 1 and matches[0].mode == mode, "WIRE_EVIDENCE_MODE")
    resource = matches[0].resource
    root = Path(asset_root).resolve()
    path = (root / resource.path).resolve()
    require(root in path.parents and resource.media_type == "application/json", "WIRE_EVIDENCE_RESOURCE")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == resource.sha256, "WIRE_EVIDENCE_HASH")
    return json.loads(raw, object_pairs_hook=unique_object)


def verify_owner_release(release, asset_root):
    """Independent real reopen also needs the outer owner's frozen release proof.

    Closing this adapter's context does not assert that a runtime, Job or owned
    launcher has exited. The coordinator supplies that separately after exit.
    """
    resource = release.get("owner_release_evidence")
    require(isinstance(resource, dict) and set(resource) == {"path", "sha256", "media_type"} and
            resource["media_type"] == "application/json", "OUTER_OWNER_RELEASE_REQUIRED")
    root = Path(asset_root).resolve()
    path = (root / resource["path"]).resolve()
    require(root in path.parents, "OUTER_RELEASE_RESOURCE")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == resource["sha256"], "OUTER_RELEASE_RESOURCE")
    value = json.loads(raw, object_pairs_hook=unique_object)
    subject = {k: v for k, v in release.items() if k != "owner_release_evidence"}
    require(value.get("schema") == "A24OwnedRelease/v1" and value.get("mode") == "OBSERVED" and
            value.get("issuer") == "01a15dfa-9556-7812-9ed5-1b3bce53555e" and
            value.get("subject_release_hash") == digest(subject) and value.get("status") == "RELEASED" and
            value.get("context_closed") is True and value.get("runtime_stopped") is True and
            value.get("held_identities_released") is True and value.get("jobs_closed") is True and
            value.get("launcher_released") is True and type(value.get("pending_tasks")) is int and
            value["pending_tasks"] == 0 and value.get("raw_evidence_refs"), "OUTER_OWNER_RELEASE_UNPROVEN")
    return digest(value)


def validate_profile(admission, request, asset_root):
    mode = "SYNTHETIC" if admission.offline else "OBSERVED"
    ref = request.get("wire_profile_ref")
    require(isinstance(ref, str), "CURRENT_WIRE_PROFILE_REQUIRED")
    p = read_evidence(admission.bundle, ref, asset_root, mode)
    fact = admission.questions[0]
    scope = {"book_id": BOOK, "question_id": fact["question_id"], "facts_hash": digest(fact),
             "policy": policy_ref(admission.policy), "source_bindings_hash": digest(request["bindings"]),
             "platform_version": p.get("platform_version")}
    require(len(admission.questions) == 1 and p.get("schema") == "A24WireProfile/v1" and
            p.get("mode") == mode and all(p.get(k) == v for k, v in scope.items()), "WIRE_PROFILE_BINDING")
    require(request["approval"].get("wire_profile_hash") == digest(p), "WIRE_PROFILE_APPROVAL")
    uploads = p.get("limits", {}).get("upload")
    required = set(PROOFS) | ({"upload_plan"} if uploads == 6 else set())
    require(set(p.get("proofs", {})) == required, "CURRENT_WIRE_PROOFS_REQUIRED")
    for name in sorted(required):
        proof = read_evidence(admission.bundle, p["proofs"][name], asset_root, mode)
        require(proof.get("schema") == "A24WireProof/v1" and proof.get("claim") == name and
                proof.get("status") == "VERIFIED" and proof.get("mode") == mode and
                proof.get("scope") == scope and proof.get("profile_contract_hash") ==
                digest({k: v for k, v in p.items() if k != "proofs"}) and
                proof.get("basis") == ("SYNTHETIC_TEST" if admission.offline else "CURRENT_OBSERVATION") and
                proof.get("source_refs"), "CURRENT_" + name.upper() + "_PROOF_REQUIRED")
    require(p.get("old_body_coverage") == "ALL_FIELDS_ALL_ZONES_ALL_OLD_QUESTIONS", "OLD_CONTENT_INCOMPLETE")
    require(type(uploads) is int and uploads in (0, 6) and p.get("limits") ==
            {"save": 1, "upload": uploads, "signature": int(uploads == 6), "login": 0, "ocr": 0, "refresh": 1}, "WIRE_LIMITS")
    require(request["approval"]["operations"] == ["CREATE_FRAMES", "CREATE_QUESTION_CONTENT"] +
            (["UPLOAD_CROPS"] if uploads else []), "UPLOAD_AUTHORIZATION_REQUIRED")
    require(p.get("session", {}).get("session_id") and p["session"].get("executor") and
            p["session"].get("reviewer") != p["session"]["executor"] and p["session"].get("reviewer"),
            "EXCLUSIVE_SESSION_EVIDENCE")
    require(set(p.get("reads", {})) == {"baseline", "prewrite", "get", "refresh", "reopen", "reconcile"},
            "EXACT_READ_MANIFEST_REQUIRED")
    for phase, spec in p["reads"].items():
        if "requests" in spec:
            require(set(spec) in ({"requests", "projection"}, {"requests", "projection", "export"}) and
                    isinstance(spec["requests"], list) and spec["requests"] and
                    len({r["name"] for r in spec["requests"]}) == len(spec["requests"]) and
                    set(spec["projection"]) == set(SNAPSHOT_FIELDS) and
                    "literal" not in spec["projection"]["complete"], "EXACT_READ_MANIFEST_REQUIRED")
            book_rule = spec["projection"]["book_id"]
            request_names = {r["name"] for r in spec["requests"]}
            require(isinstance(book_rule, dict) and set(book_rule) == {"from"} and
                    isinstance(book_rule["from"], dict) and set(book_rule["from"]) == {"response", "path"} and
                    book_rule["from"]["response"] in request_names and
                    isinstance(book_rule["from"]["path"], list), "BOOK_IDENTITY_FROM_RESPONSE_REQUIRED")
            validate_identity_projection({"object": spec["projection"]})
            for r in spec["requests"]:
                require(set(r) == {"name", "path", "params", "count"} and r["count"] == 1, "EXACT_READ_MANIFEST_REQUIRED")
                safe_get(r["path"], r["params"])
        else:
            require(set(spec) in ({"path", "params", "response_fields", "count"},
                                 {"path", "params", "response_fields", "count", "export"}) and spec["count"] == 1,
                    "EXACT_READ_MANIFEST_REQUIRED")
            safe_get(spec["path"], spec["params"])
            require(set(spec["response_fields"]) == set(SNAPSHOT_FIELDS), "COMPLETE_SNAPSHOT_CODEC_REQUIRED")
        if "export" in spec:
            require(set(spec["export"]) == {"path", "params", "codec"} and
                    spec["export"]["path"] == EXPORT and spec["export"]["params"] == {}, "EXACT_EXPORT_MANIFEST_REQUIRED")
    aggregate = p.get("aggregate_readback")
    if aggregate is not None:
        require(set(aggregate) == {"mode", "rows_path"} and aggregate["mode"] in ("ALL_ZONES_AND_INFO", "ALL_ZONES_INFO_GET") and
                isinstance(aggregate["rows_path"], list), "AGGREGATE_READBACK_CODEC")
    require(p.get("new_read_count") == (0 if aggregate and aggregate["mode"] == "ALL_ZONES_AND_INFO" else 1 if aggregate else 5),
            "EXACT_READ_MANIFEST_REQUIRED")
    # Five new-question GETs: frames, info, question/choice/answer content. No per-rect POST.
    rb_fields = {"frames_path", "frame_fields", "frame_order_mode", "info_path", "content_text_path",
                 "content_success_path", "content_rect_ids_path", "association"}
    require(set(p.get("readback", {})) in (rb_fields, rb_fields | {"info_fields"}),
            "READBACK_CODEC_REQUIRED")
    require(p["readback"]["frame_order_mode"] in ("SERVER_ALLOCATED", "SUBMITTED_TENTATIVE"), "FRAME_ORDER_CODEC_REQUIRED")
    require(set(p["readback"]["frame_fields"]) == ROW_FIELDS, "READBACK_FRAME_CODEC")
    require(p["readback"]["association"] in ("RETURNED_RECT_IDS", "FRESH_ORDER_ZONE_AND_FRAME_SET"),
            "CONTENT_ASSOCIATION_UNPROVEN")
    if p["readback"]["association"] == "RETURNED_RECT_IDS":
        require(isinstance(p["readback"]["content_rect_ids_path"], list), "CONTENT_ASSOCIATION_UNPROVEN")
    return copy.deepcopy(p)


def upload_manifest(plan, profile):
    if profile["limits"]["upload"] == 0:
        require(not profile.get("uploads") and not profile.get("signature"), "UNAUTHORIZED_UPLOAD")
        return []
    objects, signature = profile.get("uploads"), profile.get("signature", {})
    require(isinstance(objects, list) and len(objects) == 6 and set(signature) ==
            {"host", "dir", "policy_sha256", "minimum_expire", "response_path"}, "EXACT_UPLOAD_MANIFEST_REQUIRED")
    origin = urlsplit(signature["host"])
    require(origin.scheme == "https" and origin.hostname and not origin.username and not origin.password and
            not origin.query and not origin.fragment and origin.path in ("", "/") and
            isinstance(signature["dir"], str) and signature["dir"] and ".." not in signature["dir"] and
            len(signature["policy_sha256"]) == 64 and type(signature["minimum_expire"]) is int,
            "UPLOAD_ORIGIN_POLICY_REQUIRED")
    for entry, frame, row in zip(objects, plan["frames"], plan["payload"]["annotations_upsert"]):
        require(set(entry) == {"fragment_id", "rect_id", "key", "resource", "width", "height"} and
                entry["fragment_id"] == frame["fragment_id"] and entry["rect_id"] == row["rect_id"] and
                isinstance(entry["key"], str) and entry["key"].startswith(signature["dir"]) and
                ".." not in entry["key"] and "?" not in entry["key"] and "#" not in entry["key"] and
                "\\" not in entry["key"] and row["image_path"] == signature["host"].rstrip("/") + "/" + entry["key"] and
                set(entry["resource"]) == {"path", "sha256", "media_type"} and
                entry["resource"]["media_type"] == "image/jpeg" and
                type(entry["width"]) is int and entry["width"] > 0 and
                type(entry["height"]) is int and entry["height"] > 0 and
                (entry["width"], entry["height"]) == (frame["box"]["bbox"][2] - frame["box"]["bbox"][0],
                                                      frame["box"]["bbox"][3] - frame["box"]["bbox"][1]),
                "UPLOAD_OBJECT_BINDING")
    require(len({e["key"] for e in objects}) == 6, "UPLOAD_OBJECT_DUPLICATE")
    return copy.deepcopy(objects)


def load_crops(manifest, asset_root):
    from PIL import Image
    root = Path(asset_root).resolve()
    blobs = []
    for entry in manifest:
        path = (root / entry["resource"]["path"]).resolve()
        require(root in path.parents, "CROP_RESOURCE_PATH")
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == entry["resource"]["sha256"], "CROP_RESOURCE_HASH")
        with Image.open(BytesIO(raw)) as image:
            image.load()
            require(image.format == "JPEG" and image.size == (entry["width"], entry["height"]), "CROP_RESOURCE_DIMENSIONS")
        blobs.append(raw)
    return blobs


def safe_get(path, params):
    parsed = urlsplit(path)
    require(isinstance(params, dict) and parsed.path.startswith("/qieti/api/") and not parsed.scheme and
            not parsed.netloc and not parsed.query and not parsed.fragment and ".." not in path and
            "\\" not in path and all(isinstance(k, str) and isinstance(v, (str, int)) and
                                       not isinstance(v, bool) for k, v in params.items()), "READ_MANIFEST_PATH")


def decode_complete_export(text, codec, inventory):
    """Conditional JSONL codec; row count or filename never establishes coverage.

    The actual export schema is UNKNOWN today. The profile must bind observed
    field paths plus an authoritative completeness record, all five zones and
    stable IDs/rect associations. A plain 22-row dump deliberately fails here.
    """
    if codec.get("schema") == "A24NaturalExportCodec/v1":
        return decode_natural_export(text, codec, inventory)
    require(codec.get("schema") == "A24CompleteExportCodec/v1" and
            set(codec) == {"schema", "kind_path", "metadata_value", "question_value", "metadata_fields", "question_fields"},
            "CURRENT_EXPORT_SCHEMA_REQUIRED")
    require(isinstance(text, str) and text.strip() and not text.lstrip().startswith("<"), "EXPORT_NOT_JSONL")
    records = [json.loads(line, object_pairs_hook=unique_object,
                          parse_constant=lambda value: require(False, "NONFINITE_RESPONSE"))
               for line in text.splitlines() if line.strip()]
    require(records and all(isinstance(r, dict) for r in records), "EXPORT_NOT_JSONL")
    metadata = [r for r in records if field(r, codec["kind_path"]) == codec["metadata_value"]]
    rows = [r for r in records if field(r, codec["kind_path"]) == codec["question_value"]]
    require(len(metadata) == 1 and len(rows) + 1 == len(records), "AUTHORITATIVE_EXPORT_COMPLETENESS_REQUIRED")
    require(set(codec["metadata_fields"]) == {"book_id", "complete", "question_ids", "zones", "state_version"},
            "AUTHORITATIVE_EXPORT_COMPLETENESS_REQUIRED")
    m = {k: field(metadata[0], path) for k, path in codec["metadata_fields"].items()}
    ids = [q["platform_question_id"] for q in inventory]
    require(ids and all(canonical_id(v) for v in ids) and
            str(m["book_id"]) == BOOK and m["complete"] is True and isinstance(m["question_ids"], list) and
            all(canonical_id(v) for v in m["question_ids"]) and
            len(ids) == len(set(ids)) == len(m["question_ids"]) and set(m["question_ids"]) == set(ids) and
            m["zones"] == list(ZONES) and m["state_version"], "EXPORT_COVERAGE_UNPROVEN")
    require(set(codec["question_fields"]) == {"platform_question_id", "question_type", "parts", "wire_zones",
                                              "question_info", "rect_ids"}, "CURRENT_EXPORT_SCHEMA_REQUIRED")
    contents = {}
    for row in rows:
        value = {k: copy.deepcopy(field(row, path)) for k, path in codec["question_fields"].items()}
        pid = value.pop("platform_question_id")
        require(canonical_id(pid) and pid in ids and pid not in contents and value["question_type"] and
                isinstance(value["parts"], list) and value["parts"] and all(isinstance(v, dict) for v in value["parts"]) and
                isinstance(value["wire_zones"], dict) and set(value["wire_zones"]) == set(ZONES) and
                all(v is None or isinstance(v, str) for v in value["wire_zones"].values()) and
                isinstance(value["question_info"], dict) and isinstance(value["rect_ids"], list) and
                all(canonical_id(v) for v in value["rect_ids"]) and
                len(value["rect_ids"]) == len(set(value["rect_ids"])), "EXPORT_QUESTION_COVERAGE")
        # Preserve every observed business field, including unrecognized additions.
        contents[pid] = dict(value, status="AVAILABLE", raw_record=copy.deepcopy(row))
    require(set(contents) == set(ids), "OLD_CONTENT_INCOMPLETE")
    return contents, {"membership_hash": digest(sorted(ids)), "state_version": m["state_version"],
                      "zones": list(ZONES), "complete": True, "raw_export_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def decode_natural_export(text, codec, inventory):
    """Natural question JSONL, with separately evidenced route completeness.

    No metadata row is synthesized or assumed. An observed field map and an
    adopted authoritative route qualification are mandatory. Current real
    qualification remains UNBOUND until actual prewrite evidence establishes it.
    """
    require(set(codec) == {"schema", "question_fields", "qualification"}, "CURRENT_EXPORT_SCHEMA_REQUIRED")
    q = codec["qualification"]
    require(isinstance(q, dict) and q.get("schema") == "A24FullBodyRouteQualification/v1" and
            q.get("status") == "VERIFIED" and q.get("route") == EXPORT and q.get("book_id") == BOOK and
            q.get("authoritative_catalog_complete") is True and q.get("all_business_fields_covered") is True and
            q.get("zones") == list(ZONES) and q.get("state_binding") and q.get("evidence_refs"),
            "NATURAL_EXPORT_AUTHORITY_UNBOUND")
    require(isinstance(text, str) and text.strip() and not text.lstrip().startswith("<"), "EXPORT_NOT_JSONL")
    records = [json.loads(line, object_pairs_hook=unique_object) for line in text.splitlines() if line.strip()]
    ids = [v["platform_question_id"] for v in inventory]
    require(ids and all(canonical_id(v) for v in ids) and
            len(ids) == len(set(ids)) and len(records) == len(ids) and
            set(codec["question_fields"]) == {"platform_question_id", "question_type", "parts", "wire_zones", "question_info", "rect_ids"},
            "EXPORT_QUESTION_COVERAGE")
    contents = {}
    for record in records:
        require(isinstance(record, dict), "EXPORT_NOT_JSONL")
        value = {k: copy.deepcopy(field(record, path)) for k, path in codec["question_fields"].items()}
        pid = value.pop("platform_question_id")
        require(canonical_id(pid) and pid in ids and pid not in contents and value["question_type"] and isinstance(value["parts"], list) and
                value["parts"] and all(isinstance(v, dict) for v in value["parts"]) and
                set(value["wire_zones"]) == set(ZONES) and
                all(v is None or isinstance(v, str) for v in value["wire_zones"].values()) and
                isinstance(value["question_info"], dict) and isinstance(value["rect_ids"], list) and
                all(canonical_id(v) for v in value["rect_ids"]) and
                len(value["rect_ids"]) == len(set(value["rect_ids"])), "EXPORT_QUESTION_COVERAGE")
        contents[pid] = dict(value, status="AVAILABLE", raw_record_hash=digest(record))
    require(set(contents) == set(ids), "OLD_CONTENT_INCOMPLETE")
    return contents, {"membership_hash": digest(sorted(ids)), "state_binding_hash": digest(q["state_binding"]),
                      "complete": True, "zones": list(ZONES), "qualification_hash": digest(q),
                      "raw_export_sha256": sha_text(text)}


def sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def bbox_csv(box):
    require(isinstance(box, list) and len(box) == 4 and all(type(n) in (float, int) for n in box), "WIRE_BBOX")
    return ",".join(str(int(n)) if float(n).is_integer() else str(n) for n in box)


def build_payload(plan, profile):
    fact_frames, parts = plan["frames"], plan["approved_parts"]
    w = profile["wire"]
    require(set(w.get("identity_fields", {})) == {"user_id", "username"} and
            all(isinstance(path, list) and path and all(isinstance(k, str) and k for k in path)
                for path in w["identity_fields"].values()), "CURRENT_IDENTITY_SCHEMA_REQUIRED")
    require(len(fact_frames) == len(parts) == 6 and len(w.get("rows", [])) == 6, "SIX_FRAME_SEMANTICS")
    require(w["directory_id"] == plan["action"]["expected_after"]["directory_id"] and
            w["insert_after_order"] == plan["insert_after_order"] and type(w["insert_after_order"]) is int,
            "LEGAL_INSERTION_REQUIRED")
    rows, ids = [], []
    for i, (frame, supplied) in enumerate(zip(fact_frames, w["rows"])):
        require(set(supplied) == {"fragment_id", "crop", "fields"} and
                supplied["fragment_id"] == frame["fragment_id"], "WIRE_FRAME_BINDING")
        row, crop = copy.deepcopy(supplied["fields"]), supplied["crop"]
        require(set(row) == ROW_FIELDS and isinstance(row["rect_id"], str) and row["rect_id"], "WIRE_FRAME_FIELDS")
        binding = plan["source_bindings"][frame["box"]["image"]["asset_id"]]
        require(crop == {"source_sha256": binding["sha256"], "bbox": frame["box"]["bbox"],
                         "save_page": binding["save_page"], "image_path": row["image_path"]}, "CROP_SOURCE_BINDING")
        require(isinstance(row["image_path"], str) and row["image_path"].strip() == row["image_path"] and
                row["image_path"] and not row["image_path"].lower().startswith(("data:", "blob:", "javascript:", "file:")),
                "EXISTING_CROP_REFERENCE_REQUIRED")
        require(row["image_path"] != binding["resource_id"], "WHOLE_IMAGE_IS_NOT_CROP")
        require(row["rect_bbox"] == bbox_csv(frame["box"]["bbox"]) and
                row["page_index"] == binding["save_page"] and type(row["page_index"]) is int and
                row["directory_id"] == w["directory_id"] and row["content_type"] == "text" and
                row["type"] == (["question"] + ["choice"] * 4 + ["answer"])[i] and
                type(row["image_order_in_annotation_zone"]) is int and
                row["image_order_in_annotation_zone"] == ([0, 0, 1, 2, 3, 0])[i] and
                row["parent_rect_id"] is None and row["is_pre_annotation"] is False and
                row["pre_annotations_id"] is None and row["user_id"] is not None and
                row["belong_to_level"] == "question_level" and isinstance(row["order_in_level"], str) and
                row["order_in_level"].isdigit() and int(row["order_in_level"]) > 0 and
                row["order_in_level"] == w.get("tentative_annotation_order"), "WIRE_FRAME_MAPPING")
        rows.append(row)
        ids.append(row["rect_id"])
    require(len(set(ids)) == 6 and len({r["image_path"] for r in rows}) == 6, "WIRE_FRAME_IDENTITY")
    require(w.get("choice_separator") in ("\n", "\n\n"), "APPROVED_CHOICE_JOIN_REQUIRED")
    bodies = [{"zone": zone, "ocr_result": text, "rect_ids": rects, "question_order": None}
              for zone, text, rects in (("question", parts[0]["text"], ids[:1]),
                   ("choice", w["choice_separator"].join(p["text"] for p in parts[1:5]), ids[1:5]),
                   ("answer", parts[5]["text"], ids[5:]))]
    require(w.get("empty_zones") == [{"zone": "analysis", "operation": "DELETE_NEW_QUESTION_ONLY"},
                                      {"zone": "knowledge_point", "operation": "DELETE_NEW_QUESTION_ONLY"}],
            "EMPTY_ZONE_SCOPE_UNPROVEN")
    info = w.get("question_info")
    require(isinstance(info, dict) and info == {"tishi": "xuanze", "tilei": None, "tihao": None},
            "CURRENT_QUESTION_TYPE_REQUIRED")
    require(w.get("created_by") and w.get("question_info_approved_hash") == digest(info), "QUESTION_INFO_BINDING")
    payload = {"file_id": BOOK, "target_directory_id": w["directory_id"], "question_order": None,
               "is_new_question_insertion": True, "insert_after_order": w["insert_after_order"],
               "annotations_upsert": rows, "annotations_delete_rect_ids": [], "ocr_submissions": bodies,
               "ocr_delete_zones": [z["zone"] for z in w["empty_zones"]], "question_info": copy.deepcopy(info),
               "created_by": w["created_by"]}
    require(set(payload) == TOP_FIELDS, "UNAUTHORIZED_PAYLOAD_FIELD")
    return payload


def write_set(payload, uploads=()):
    return {"operation": "CREATE_QUESTION_CONTENT_AND_SIX_FRAMES", "new_question_count": 1,
            "frame_upserts": payload["annotations_upsert"], "frame_deletes": [],
            "body_submissions": payload["ocr_submissions"], "empty_zone_operations":
            [{"zone": z, "scope": "NEW_QUESTION_ONLY"} for z in payload["ocr_delete_zones"]],
            "question_info": payload["question_info"], "old_record_mutations": 0,
            "uploads": len(uploads), "upload_objects": list(uploads), "final_submission": False}


def decode_receipt(response, profile, payload):
    body = checked_response(response)
    schema = profile["receipt"]
    require(set(schema) == {"code", "file_id", "platform_question_id", "question_order", "inserted", "rect_ids"},
            "CURRENT_RECEIPT_SCHEMA_REQUIRED")
    value = {key: field(body, path) for key, path in schema.items()}
    require(type(value["code"]) is int and value["code"] in (0, 200) and str(value["file_id"]) == BOOK and
            isinstance(value["platform_question_id"], str) and value["platform_question_id"] and
            type(value["question_order"]) is int and value["question_order"] > payload["insert_after_order"] and
            value["inserted"] is True and isinstance(value["rect_ids"], list) and
            sorted(value["rect_ids"]) == sorted(r["rect_id"] for r in payload["annotations_upsert"]),
            "BUSINESS_RECEIPT_UNKNOWN")
    return dict(value, response_hash=digest(response), payload_hash=digest(payload),
                identity_source="SERVER_RESPONSE", evidence_mode=profile["mode"])


def checked_response(response, *, json_body=True):
    require(isinstance(response, dict) and set(response) == {"http_status", "body", "request_id", "session_id",
                                                           "fresh", "cache", "platform_version"} and
            type(response["http_status"]) is int and response["http_status"] == 200 and
            response["fresh"] is True and response["cache"] is False and
            isinstance(response["request_id"], str) and response["request_id"] and
            isinstance(response["body"], str), "FRESH_RESPONSE_REQUIRED")
    # Parse retained response text ourselves; duplicate JSON members cannot be hidden by I/O.
    if not json_body:
        return response["body"]
    body = json.loads(response["body"], object_pairs_hook=unique_object,
                      parse_constant=lambda value: require(False, "NONFINITE_RESPONSE"))
    require(isinstance(body, (dict, list)), "WIRE_RESPONSE_SCHEMA")
    return body
