"""New isolated A24 fixtures. Reuse frozen DATA only, never old suite/helper code."""
import copy
import hashlib
import json
from pathlib import Path

from annotation.contracts import artifact_ref, policy_ref, seal_artifact
from annotation.contracts.models import ExchangeBundle
from annotation.delivery.live_pilot import wire
from annotation.quality.live_pilot import question_facts
from annotation.runtime.storage.common import digest

REPO = Path(__file__).resolve().parents[2]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"))


def reseal(request):
    pairs = []
    def rewrite(value):
        for old, new in pairs:
            if value == old:
                return copy.deepcopy(new)
        if isinstance(value, dict):
            return {k: rewrite(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rewrite(v) for v in value]
        return value
    for index, value in enumerate(request["bundle"]["artifacts"]):
        old = artifact_ref(value)
        new = seal_artifact(rewrite(value))
        request["bundle"]["artifacts"][index] = new
        pairs.append((old, artifact_ref(new)))
    request.update(rewrite(request))


def fixture(root):
    old = REPO / "tests" / "fixtures" / "live_pilot"
    request = json.loads((old / "review_delta" / "valid.json").read_bytes())
    for name in ("page.pgm", "proof.txt", "review_delta/valid-alpha-classification.json"):
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        raw = (old / name).read_bytes()
        # This frozen PGM is an all-255 synthetic page with an ASCII header.
        # Recreate that page, avoiding Git's text checkout conversion of .pgm.
        dest.write_bytes((b"P5\n100 100\n255\n" + bytes([255])*10000) if name.endswith(".pgm")
                         else raw.replace(b"\r\n", b"\n"))
    qid = "a11-new-alpha"
    source, evidence, graph, snapshot, pre = request["bundle"]["artifacts"]
    source["payload"]["scope_manifest"] = [qid]
    source["payload"]["history"] = source["payload"]["history"][:1]
    request["bundle"]["evidence"][0]["resource"]["sha256"] = hashlib.sha256((root / "proof.txt").read_bytes()).hexdigest()
    qualification = source["payload"]["history"][0]["resource"]
    qualification["sha256"] = hashlib.sha256((root / qualification["path"]).read_bytes()).hexdigest()
    evidence["payload"]["regions"] = [r for r in evidence["payload"]["regions"] if r["region_id"].startswith(qid)]
    evidence["payload"]["coverage_clues"][0]["region_ids"] = [r["region_id"] for r in evidence["payload"]["regions"]]
    for key in ("questions", "fragments", "answer_relations"):
        graph["payload"][key] = [v for v in graph["payload"][key]
            if v.get("question_id", v.get("fragment_id", "")).startswith(qid)]
    request["approval"]["questions"] = request["approval"]["questions"][:1]
    request["approval"]["questions"][0]["choice_qualification"]["resource"] = copy.deepcopy(qualification)
    request["approval"].update(purpose="A24_WIRE_OFFLINE_TEST_ONLY", batch_send_limit=1,
                                operations=["CREATE_FRAMES", "CREATE_QUESTION_CONTENT"])
    reseal(request)
    model = ExchangeBundle.model_validate(request["bundle"])
    mg = next(a for a in model.artifacts if a.kind == "QuestionGraph")
    fact = question_facts(model, mg, mg.payload.questions[0], model.policies[0], request["bindings"])
    request["approval"]["questions"][0].update(input_hash=digest(fact), approved_parts=fact["parts"],
                                               answer_relation=fact["relations"][0])
    initial = copy.deepcopy(request["observation"])
    for content in initial["view"]["question_content"].values():
        content.update(wire_zones={"question": content["parts"][0]["text"], "choice": None, "answer": None,
                                   "analysis": None, "knowledge_point": None}, question_info={"old": True})
    rows = []
    for i, frame in enumerate(fact["frames"]):
        binding = request["bindings"][frame["box"]["image"]["asset_id"]]
        path = "https://synthetic.invalid/crops/rect-" + str(i) + ".jpg"
        fields = {"rect_id": "rect-" + str(i), "type": (["question"] + ["choice"] * 4 + ["answer"])[i],
                  "belong_to_level": "question_level", "order_in_level": "10",
                  "image_order_in_annotation_zone": [0, 0, 1, 2, 3, 0][i],
                  "rect_bbox": wire.bbox_csv(frame["box"]["bbox"]), "page_index": binding["save_page"],
                  "image_path": path, "parent_rect_id": None, "directory_id": "target-a", "content_type": "text",
                  "user_id": "synthetic-user", "is_pre_annotation": False, "pre_annotations_id": None}
        rows.append({"fragment_id": frame["fragment_id"], "fields": fields,
                     "crop": {"source_sha256": binding["sha256"], "bbox": frame["box"]["bbox"],
                              "save_page": binding["save_page"], "image_path": path}})
    info = {"tishi": "xuanze", "tilei": None, "tihao": None}
    profile = {"schema": "A24WireProfile/v1", "mode": "SYNTHETIC", "book_id": "46007447", "question_id": qid,
               "facts_hash": digest(fact), "policy": policy_ref(model.policies[0]),
               "source_bindings_hash": digest(request["bindings"]), "platform_version": "a11-fake-v1",
               "proofs": {name: "a24-proof-" + name for name in wire.PROOFS},
               "old_body_coverage": "ALL_FIELDS_ALL_ZONES_ALL_OLD_QUESTIONS",
               "limits": {"save": 1, "upload": 0, "signature": 0, "login": 0, "ocr": 0, "refresh": 1},
               "session": {"session_id": "a24-author", "executor": "author", "reviewer": "reviewer"},
               "wire": {"directory_id": "target-a", "insert_after_order": 9, "tentative_annotation_order": "10", "rows": rows,
                        "identity_fields": {"user_id": ["id"], "username": ["username"]},
                        "choice_separator": "\n", "empty_zones": [
                            {"zone": "analysis", "operation": "DELETE_NEW_QUESTION_ONLY"},
                            {"zone": "knowledge_point", "operation": "DELETE_NEW_QUESTION_ONLY"}],
                        "question_info": info, "question_info_approved_hash": digest(info), "created_by": "synthetic"},
               "reads": {phase: {"path": "/qieti/api/synthetic/complete-snapshot", "params": {"file_id": "46007447"},
                                  "count": 1, "response_fields": {k: ["snapshot", k] for k in wire.SNAPSHOT_FIELDS}}
                         for phase in ("baseline", "prewrite", "get", "refresh", "reopen", "reconcile")},
               "new_read_count": 5,
               "readback": {"frames_path": ["data", "annotations"], "frame_fields": {k: [k] for k in wire.ROW_FIELDS}, "frame_order_mode": "SERVER_ALLOCATED",
                            "info_path": ["data"], "content_text_path": ["ocr_result"],
                            "content_success_path": ["success"], "content_rect_ids_path": ["rect_ids"],
                            "association": "RETURNED_RECT_IDS"},
               "receipt": {k: [k] for k in ("code", "file_id", "platform_question_id", "question_order", "inserted", "rect_ids")}}
    bind_profile(request, profile, root)
    return request, initial, fact, profile


def bind_profile(request, profile, root, proof_override=None):
    # New synthetic proof resources, all hash-bound; never OBSERVED and no current schema claim.
    request["bundle"]["evidence"] = [e for e in request["bundle"]["evidence"] if not e["evidence_id"].startswith("a24-")]
    scope = {k: profile[k] for k in ("book_id", "question_id", "facts_hash", "policy", "source_bindings_hash", "platform_version")}
    contract_hash = digest({k: v for k, v in profile.items() if k != "proofs"})
    values = {"a24-profile": profile}
    for name, identity in profile["proofs"].items():
        values[identity] = {"schema": "A24WireProof/v1", "mode": "SYNTHETIC", "claim": name,
                            "status": "VERIFIED", "scope": scope, "profile_contract_hash": contract_hash,
                            "basis": "SYNTHETIC_TEST", "source_refs": ["SYNTHETIC_A24_TEST_ONLY"]}
        if proof_override and name == proof_override[0]:
            values[identity].update(proof_override[1])
    for identity, value in values.items():
        path = root / (identity + ".json")
        write_json(path, value)
        request["bundle"]["evidence"].append({"evidence_id": identity,
            "resource": {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "media_type": "application/json"},
            "description": "SYNTHETIC_A24_TEST_ONLY", "mode": "SYNTHETIC"})
    request["wire_profile_ref"] = "a24-profile"
    request["approval"]["wire_profile_hash"] = digest(profile)


class FakeIO:
    offline, evidence_mode = True, "SYNTHETIC"
    def __init__(self, initial, fact, *, behavior="normal", actor="author", session_id="a24-author"):
        self.state, self.fact = copy.deepcopy(initial), fact
        self.behavior, self.actor, self.session_id = behavior, actor, session_id
        self.calls, self.closed, self.refreshed, self.serial = [], False, 0, 0
        self.payload = None

    def response(self, body):
        self.serial += 1
        return {"http_status": 200, "body": json.dumps(body, ensure_ascii=False), "request_id": self.session_id + ":" + str(self.serial),
                "session_id": self.session_id, "fresh": True, "cache": False, "platform_version": "a11-fake-v1"}

    def request_once(self, method, path, *, params, payload, phase):
        self.calls.append({"method": method, "path": path, "params": copy.deepcopy(params), "phase": phase})
        if method == "POST":
            assert path == wire.COMMIT
            self.payload = copy.deepcopy(payload)
            self.effect(payload)
            if self.behavior == "effect_timeout":
                raise TimeoutError("SYNTHETIC effect unknown")
            value = {"code": 0, "file_id": "46007447", "platform_question_id": "server-new", "question_order": 17,
                     "inserted": True, "rect_ids": [r["rect_id"] for r in payload["annotations_upsert"]]}
            if self.behavior == "receipt_fallback":
                value["question_order"] = None
                value["append_at_global_end"] = True
            if self.behavior == "receipt_old_id":
                value["platform_question_id"] = "old-a"
            return self.response(value)
        if path.endswith("complete-snapshot"):
            if phase == "prewrite" and self.behavior == "prewrite_change":
                self.state["view"]["question_content"]["old-a"]["parts"] = [{"text": "changed"}]
            value = self.response({"snapshot": self.state})
            if self.behavior == "cache_refresh" and phase == "refresh":
                value["cache"] = True
            return value
        if path.startswith(wire.FRAMES + "/"):
            rows = [dict(row, order_in_level="17") for row in self.payload["annotations_upsert"]]
            return self.response({"data": {"annotations": rows}})
        if path.startswith(wire.INFO + "/"):
            return self.response({"data": self.payload["question_info"]})
        if path == wire.CONTENT:
            row = next(b for b in self.payload["ocr_submissions"] if b["zone"] == params["zone"])
            text = row["ocr_result"]
            if self.behavior == "partial_body" and params["zone"] == "choice":
                text = "partial"
            return self.response({"success": True, "ocr_result": text, "rect_ids": row["rect_ids"]})
        raise AssertionError("Unexpected fake request")

    def effect(self, payload):
        v, fact = self.state["view"], self.fact
        pid = "server-new"
        v["target"]["questions"].append({"platform_question_id": pid, "directory_id": "target-a", "platform_order": 17})
        v["internal_bindings"][fact["question_id"]] = pid
        for projected, row in zip(fact["frames"], payload["annotations_upsert"]):
            v["target"]["frames"].append({"platform_frame_id": row["rect_id"], "platform_question_id": pid,
                "box": projected["box"], "platform_role": projected["platform_role"], "platform_type": "text"})
            v["frame_projections"][row["rect_id"]] = copy.deepcopy(projected)
        v["question_content"][pid] = {"status": "AVAILABLE", "question_type": "ordinary_choice", "parts": copy.deepcopy(fact["parts"]),
            "wire_zones": {**{b["zone"]: b["ocr_result"] for b in payload["ocr_submissions"]}, "analysis": None, "knowledge_point": None},
            "question_info": copy.deepcopy(payload["question_info"])}
        if self.behavior == "old_body_change":
            v["question_content"]["old-a"]["wire_zones"]["analysis"] = "unapproved change"
        if self.behavior == "partial_frame":
            v["target"]["frames"].pop()

    def refresh_once(self):
        self.refreshed += 1
        return {"refreshed": True, "session_id": self.session_id}

    def close(self):
        self.closed = True
        return {"released": self.behavior != "release_failure", "session_id": self.session_id}
