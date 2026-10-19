"""Immutable B stage bytes and separate A authority -> new C01 source objects."""
import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from annotation.contracts import artifact_ref, policy_ref, seal_artifact, seal_policy, validate_bundle
from annotation.contracts.integrity import unique_object

BOOK = "46007447"
QUESTION = "q-260d10c51f2b7c16fb6fefb5"
ANSWER = "a-92c4d2164ab878c8e6d4c88d"
CASE = "q4-first-lesson"
SCOPE = "a09-fixed-q4-offline"
DIRECTORY = "a09-lesson1"
TARGET = "a09-q4-memory-target"
VERSION = "a09-q4-offline-v1"
APPROVAL_SHA = "5c73af50262f6bd7e48e2b0d46148026c1c3a953d1ee93c8262e356733d99010"
PROPOSAL_SHA = "e8146fc7a4fe2e16c1fc1194d49de1caa1fe029dd6907848bbaa6c9082dc0bbe"
REGISTRY_SHA = "aa4f2f7119ef71f70367e3bf7b3c3ed61e05e8a1643572aca92969d05cc1f9bf"
ZIP_SHA = "b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673"
POLICY_SHA = "0764136893bc44dae37b884cf52ceffe9756224fb6ddcb417ea9255cc9233f6c"


class Q4Error(ValueError):
    def __init__(self, layer, code, message):
        self.layer, self.code = layer, code
        super().__init__(message)


def need(ok, layer, code, message):
    if not ok:
        raise Q4Error(layer, code, message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def parse(raw):
    def invalid(value):
        raise ValueError("nonfinite JSON: " + value)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=invalid)


@dataclass(frozen=True)
class Inputs:
    stage_raw: bytes
    proposal_raw: bytes
    approval_raw: bytes
    registry_raw: bytes
    policy_raw: bytes


def load_inputs(stage, proposal, approval, registry, policy):
    try:
        return Inputs(*(Path(p).read_bytes() for p in (stage, proposal, approval, registry, policy)))
    except (OSError, TypeError) as exc:
        raise Q4Error("INPUT", "INPUT_MISSING", str(exc)) from exc


def authorize(inputs):
    """Only the frozen task's raw authority can admit this exact question."""
    need(bool(inputs.approval_raw), "AUTHORIZATION", "APPROVAL_MISSING", "Q4 approval required")
    need(sha(inputs.approval_raw) == APPROVAL_SHA, "AUTHORIZATION", "APPROVAL_BINDING", "wrong or changed approval; Q1 authority cannot transfer")
    need(sha(inputs.registry_raw) == REGISTRY_SHA and sha(inputs.policy_raw) == POLICY_SHA,
         "AUTHORIZATION", "TASK_BINDING", "fixed input registry/policy changed")
    need(sha(inputs.stage_raw) == ZIP_SHA and sha(inputs.proposal_raw) == PROPOSAL_SHA,
         "AUTHORIZATION", "INPUT_BINDING", "stage or proposal replaced")
    registry, approval, proposal, policy = map(parse, (inputs.registry_raw, inputs.approval_raw, inputs.proposal_raw, inputs.policy_raw))
    need(all(approval[k] == v for k, v in (("book_id", BOOK), ("case_id", CASE), ("question_id", QUESTION), ("answer_id", ANSWER))) and
         approval["business_approval_granted"] is True and approval["allowed_use"] == "A_SIDE_OFFLINE_POSITIVE_SIMULATION_ONLY" and
         approval["approved_proposal"]["sha256"] == registry["proposal_sha256"] == PROPOSAL_SHA and
         approval["input_zip_sha256"] == registry["zip_sha256"] == ZIP_SHA and
         approval["case_member_sha256"] == registry["case_member_sha256"] and
         approval["b_commit"] == proposal["source_b_commit"] == registry["b_commit"],
         "AUTHORIZATION", "SCOPE_BINDING", "fixed book, question, stage, or offline scope differs")
    need(policy["approval_sha256"] == APPROVAL_SHA and policy["proposal_sha256"] == PROPOSAL_SHA and
         policy["registry_sha256"] == REGISTRY_SHA and policy["scope_id"] == SCOPE and
         policy["target_id"] == TARGET and policy["directory_id"] == DIRECTORY and
         policy["execution_mode"] == "SIMULATED" and policy["allowed_operations"] == ["CREATE_FRAMES"],
         "AUTHORIZATION", "POLICY_SCOPE", "fixed A09 policy differs")
    return registry, approval, proposal, policy


def read_stage(inputs, registry):
    """Read only the required original members; never execute B producers or A08."""
    required = ["manifest.json", "staging/manifest.json", "staging/receipt.json", registry["case_member"]]
    required += ["staging/" + s["path"] for s in registry["sources"]]
    pins = {x["path"]: x for x in registry["raw_package_members"]}
    with zipfile.ZipFile(io.BytesIO(inputs.stage_raw)) as archive:
        names = archive.namelist()
        need(len(names) == len(set(names)) and set(names) == set(pins), "ENVELOPE", "INVENTORY", "stage member inventory differs")
        files = {n: archive.read(n) for n in required}
    for n, raw in files.items():
        need(len(raw) == pins[n]["bytes"] and sha(raw) == pins[n]["sha256"], "ENVELOPE", "MEMBER_BINDING", n)
    outer = parse(files["manifest.json"])
    need(outer["schema"] == registry["outer_schema"] and outer["decision"] == "HOLD" and
         {x["path"]: x for x in outer["files"]} == {k: v for k, v in pins.items() if k != "manifest.json"},
         "ENVELOPE", "MANIFEST_BINDING", "original outer manifest differs")
    inner = parse(files["staging/manifest.json"])
    need(all(dict(x, path="staging/" + x["path"]) == pins["staging/" + x["path"]] for x in inner["files"]),
         "ENVELOPE", "STAGE_MANIFEST", "original stage manifest differs")
    return files


def inspect_source(inputs):
    registry, approval, proposal, policy = authorize(inputs)
    files = read_stage(inputs, registry)
    case = parse(files[registry["case_member"]])
    q, a = case["question_snapshot"], case["answer_snapshot"]
    need(case == proposal["source_case_snapshot"] and case["book_id"] == BOOK and case["case_id"] == CASE and
         case["question_id"] == q["question_id"] == QUESTION and case["answer_id"] == a["answer_id"] == ANSWER and
         q["selected_answer_id"] == ANSWER and q["candidate_answer_ids"] == [ANSWER] and
         q["section_path"] == a["section_path"] == approval["section_path"] == proposal["section_path"],
         "SOURCE", "RELATION_BINDING", "original case and unique scoped relation differ")
    need(case["decision"] == "HOLD" and not any(case[k] for k in ("human_verified", "joint_accepted", "platform_eligible")) and
         q["verification_status"] == a["verification_status"] == "UNVERIFIED" and
         q["flags"] == ["FIGURE_EXTENT_UNVERIFIED"] and all(v is False for v in proposal["approvals"].values()),
         "SOURCE", "HISTORY_BINDING", "B HOLD and historical proposal flags must remain")
    selected = approval["approved_regions_in_physical_order"]
    need(selected == proposal["proposed_regions_in_physical_order"] and approval["approved_content"] == proposal["content_proposal"] and
         [r["proposed_role"] for r in selected] == ["Q", "Q", "Q", "A"] and
         [r["content_type"] for r in selected] == ["image", "text", "text", "text"] and
         [r["role"] for r in selected] == ["stem", "stem", "stem", "answer"] and
         selected[0]["text"] is None and selected[1]["text"] + selected[2]["text"] == approval["approved_content"]["stem_normalized"] and
         selected[3]["text"] == approval["approved_content"]["answer"] == a["text"] == "13",
         "SOURCE", "APPROVED_TABLE", "four approved groups/content differ")
    af = a["fragments"][0]
    qf = q["fragments"]
    start, end = af["text_span"]
    normalized = (qf[0]["text"][2:] + qf[1]["text"]).replace("5cm", "5 cm").replace("6cm", "6 cm")
    need(len(qf) == 4 and [f["role"] for f in qf] == ["stem", "stem", "stem", "figure_caption"] and
         qf[0]["text"].startswith("4.") and normalized == selected[1]["text"] and qf[2]["text"] == "cm." and
         qf[3]["text"] == "第4题图" and q["asset_id"] == "viewer-10" and
         all(f["asset_id"] == "viewer-10" for f in qf) and a["asset_id"] == "viewer-173" and
         af["raw_text"] == "4.13" and [start, end] == [2, 4] and af["raw_text"][start:end] == "13" and
         a["explanation_present"] is False and not a["explanation_text"],
         "SOURCE", "CONTENT_MAPPING", "original fragments/answer span differ")
    need(proposal["sources"] == registry["sources"] and
         approval["approved_scope_policy"]["frame_count"] == 4 and approval["approved_scope_policy"]["other_three_cases"] == "HOLD" and
         approval["approved_scope_policy"]["q1_authorization_transferred"] is False,
         "SOURCE", "SCOPE_POLICY", "fixed single-question policy differs")
    for s in registry["sources"]:
        raw = files["staging/" + s["path"]]
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            need(sha(raw) == s["sha256"] and image.size == (s["width"], s["height"]), "SOURCE", "IMAGE_BINDING", s["asset_id"])
        for r in selected:
            if r["asset_id"] == s["asset_id"]:
                x1, y1, x2, y2 = r["bbox"]
                need(0 <= x1 < x2 <= s["width"] and 0 <= y1 < y2 <= s["height"], "SOURCE", "ORIGINAL_BOX", r["proposal_region_id"])
    mapping = [
        {"region_id": selected[0]["proposal_region_id"], "original_fragments": [], "basis": "A approved original-image geometry; caption is identity evidence only"},
        {"region_id": selected[1]["proposal_region_id"], "original_fragments": qf[:2], "basis": "remove printed 4.; join layout newline; preserve 5 cm and 6 cm"},
        {"region_id": selected[2]["proposal_region_id"], "original_fragments": [qf[2]], "basis": "A approved visible blank plus cm.; ____ is display representation"},
        {"region_id": selected[3]["proposal_region_id"], "original_fragments": [af], "basis": "original 4.13 Unicode code point span [2,4); A approved tighter region"}]
    provenance = {"input_sha256": {"zip": ZIP_SHA, "proposal": PROPOSAL_SHA, "approval": APPROVAL_SHA, "registry": REGISTRY_SHA, "policy": POLICY_SHA},
        "source_case_snapshot": case, "historical_proposal_approvals": proposal["approvals"], "original_ocr_to_A_regions": mapping,
        "approved_regions": selected, "approved_content": approval["approved_content"], "caption_identity_only": qf[3],
        "question_type_mapping": {"proposal": "fill_blank", "C01": "free_response", "original_B_candidate": q["type_candidate"]},
        "cross_page": False, "original_B_blockers": case["blockers"] + q["flags"],
        "A_disposition": {"status": "USER_APPROVED_THIS_Q4_OFFLINE_ONLY", "approval_sha256": APPROVAL_SHA,
                          "original_facts_unchanged": True, "independent_human_visual_review": False},
        "external_B_refs_declared_only": parse(files["staging/receipt.json"]),
        "full_external_G_Check_plan": "DECLARED_ONLY_EXTERNAL_NOT_LOADED",
        "other_cases": [{"case_id": n, "status": "HOLD", "question_relation_created": False} for n in
                        ("q4-topic-fraction", "q9-reflection-continuation", "q16-unit2-formulas")],
        "whole_page_coverage_claim": False, "B_joint_adoption": False, "platform_eligible": False}
    return {"registry": registry, "approval": approval, "proposal": proposal, "policy": policy,
            "files": files, "selected": selected, "case": case, "provenance": provenance}


def artifact(kind, identity, payload, dependencies, policy, run_id, created_at, mode="OBSERVED"):
    return seal_artifact({"schema_version": "1.0.0-a-proposal", "artifact_id": identity, "revision": 1, "kind": kind,
        "run_id": run_id, "book_id": BOOK, "scope_id": SCOPE, "input_refs": [artifact_ref(a) for a in dependencies], "created_at": created_at,
        "producer": {"module": "annotation.a09.q4", "implementation_version": VERSION, "config_version": "a09-policy-" + POLICY_SHA,
            "policy_versions": [policy_ref(policy)], "model_version": None, "prompt_version": None, "evidence_mode": mode}, "payload": payload})


def write_once(root, path, raw):
    dest = Path(root) / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        need(dest.read_bytes() == raw, "RESOURCE", "OUTPUT_EXISTS", "immutable resource differs: " + path)
    else:
        with dest.open("xb") as handle:
            handle.write(raw)
    return {"path": path, "sha256": sha(raw), "media_type": "image/jpeg" if path.endswith(".jpg") else "application/json"}


def build_source(inputs, root, run_id, created_at):
    facts = inspect_source(inputs)
    policy = seal_policy({"policy_id": VERSION, "revision": 1, "confirmation_status": "A_INTERNAL_PROPOSAL", "option_grouping": "SEPARATE",
        "role_mapping": {"stem": "Q", "option": "W", "answer": "A", "explanation": "E", "shared_material": "W"},
        "source_notes": ["Fixed Q4 A user approval SHA256 " + APPROVAL_SHA, "Four-region policy SHA256 " + POLICY_SHA,
                         "fill_blank maps to C01 free_response; original B HOLD/UNVERIFIED preserved; no joint adoption"],
        "frame_save_status": "SYNTHETIC", "ocr_status": "UNVERIFIED", "applicability": "PROPOSAL_ONLY"})
    files, registry = facts["files"], facts["registry"]
    resources = [("approval", inputs.approval_raw), ("proposal", inputs.proposal_raw), ("input-registry", inputs.registry_raw),
                 ("policy", inputs.policy_raw), ("provenance", encode(facts["provenance"])),
                 ("original-case", files[registry["case_member"]]), ("outer-manifest", files["manifest.json"]),
                 ("stage-manifest", files["staging/manifest.json"]), ("original-receipt", files["staging/receipt.json"])]
    evidence = [{"evidence_id": "ev-" + name, "resource": write_once(root, "assets/input/" + name + ".json", raw),
                 "description": "Unmodified input or explicit A mapping; original B facts retained: " + name, "mode": "OBSERVED"} for name, raw in resources]
    assets = []
    for s in registry["sources"]:
        resource = write_once(root, "assets/original/" + s["asset_id"] + ".jpg", files["staging/" + s["path"]])
        assets.append(dict(resource, asset_id=s["asset_id"], width=s["width"], height=s["height"],
                           source_label="staging/" + s["path"], provenance="ORIGINAL"))
        evidence.append({"evidence_id": "ev-image-" + s["asset_id"], "resource": resource,
                         "description": "Raw original JPEG; not reencoded; asset/viewer identity is explicit", "mode": "OBSERVED"})
    proof = ["ev-approval", "ev-proposal", "ev-provenance", "ev-original-case"]
    source = artifact("SourceBundle", "a09-source-" + run_id, {"assets": assets,
        "directories": [{"directory_id": DIRECTORY, "parent_id": None, "label": "/".join(facts["approval"]["section_path"])}],
        "pages_expected": [s["asset_id"] for s in assets], "pages_acquired": [s["asset_id"] for s in assets],
        "external_page_mappings": [{"asset_id": s["asset_id"], "directory_id": DIRECTORY, "external_page": s["asset_id"],
                                    "mapping_status": "CONFIRMED", "evidence_refs": proof} for s in assets],
        "history": [{"resource": e["resource"], "quality": "UNVERIFIED", "reason": "Historical B HOLD / proposal false flags remain; A user authority is separate"}
                    for e in evidence if e["evidence_id"] in {"ev-original-case", "ev-original-receipt", "ev-proposal"}],
        "scope_manifest": [QUESTION], "scope_manifest_basis": "Fixed single Q4, four approved regions only, A approval " + APPROVAL_SHA,
        "metadata_page_count": None}, [], policy, run_id, created_at)
    regions, fragments, clues = [], [], []
    for i, r in enumerate(facts["selected"]):
        s = next(a for a in assets if a["asset_id"] == r["asset_id"])
        box = {"image": {k: s[k] for k in ("asset_id", "width", "height", "sha256")}, "bbox": r["bbox"]}
        rid, fid = r["proposal_region_id"], "a09-fragment-" + str(i)
        refs = proof + ["ev-image-" + s["asset_id"]]
        regions.append({"region_id": rid, "box": box, "crop_transform": {"scale_x": 1.0, "scale_y": 1.0,
            "offset_x": -float(r["bbox"][0]), "offset_y": -float(r["bbox"][1]), "rotation_degrees": 0.0, "padding": [0.0]*4,
            "processed_width": r["bbox"][2]-r["bbox"][0], "processed_height": r["bbox"][3]-r["bbox"][1], "invertible": True},
            "content_type": r["content_type"], "text": r["text"], "source": "HISTORICAL", "evidence_refs": refs,
            "printed_number_candidates": ["4"], "certainty": "CONFIRMED"})
        fragments.append({"fragment_id": fid, "region_ids": [rid], "role": r["role"], "content_type": r["content_type"], "reading_order": i})
        clues.append({"clue_id": "a09-clue-" + str(i), "box": box, "source": "SHARED_RECOGNITION", "disposition": "ASSIGNED",
                      "region_ids": [rid], "reason": "Fixed user-approved Q4 inventory only; not whole-page coverage", "evidence_refs": refs})
    observed = artifact("EvidenceBundle", "a09-evidence-" + run_id, {"source": artifact_ref(source), "regions": regions, "coverage_clues": clues}, [source], policy, run_id, created_at)
    graph = artifact("QuestionGraph", "a09-graph-" + run_id, {"source": artifact_ref(source), "evidence": artifact_ref(observed),
        "questions": [{"question_id": QUESTION, "directory_id": DIRECTORY, "question_type": "free_response",
            "fragment_ids": [f["fragment_id"] for f in fragments[:3]], "parent_question_id": None, "shared_fragment_ids": [],
            "cross_page": False, "external_refs": {"printed_number": "4", "platform_question_id": None, "platform_order": None}}],
        "fragments": fragments, "answer_relations": [{"relation_id": "a09-answer-relation", "question_id": QUESTION,
            "candidate_fragment_ids": [fragments[3]["fragment_id"]], "selected_fragment_ids": [fragments[3]["fragment_id"]], "status": "SELECTED", "evidence_refs": proof}],
        "identity_notes": "fill_blank -> free_response; original Q4/answer IDs and old OCR geometry in ev-provenance. Three stem parts on viewer-10; answer viewer-173. B HOLD unchanged."},
        [source, observed], policy, run_id, created_at)
    return validate_bundle({"format_version": "c01-exchange-1", "evidence": evidence, "policies": [policy], "artifacts": [source, observed, graph]}, asset_root=root), facts
