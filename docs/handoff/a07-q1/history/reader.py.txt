"""Immutable native B inputs -> fresh C01 objects, only for approved Q1."""
import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from annotation.contracts import artifact_ref, content_digest, policy_ref, seal_artifact, seal_policy, validate_bundle
from annotation.contracts.integrity import unique_object

APPROVAL_SHA = "cf6f675cfd98d438d7d465fc553e0ebbf1bfff71bd62f8453854f8527015cb6c"
# Filled from the new, fixed A07 policy file, never from a caller's bool.
POLICY_SHA = "1954726fa502b0a7c0a8d5705a3ca1ecfe35bd94e67a2131dc9b707115ad745b"
BOOK = "46007447"
QUESTION = "q-e92a499995ca1bbd570a2a09"
ANSWER = "a-b22c88c763b7dfb917d02d18"
SCOPE = "a07-fixed-q1-offline"
DIRECTORY = "a07-lesson1"
TARGET = "a07-q1-memory-target"
VERSION = "a07-q1-offline-v1"


class Q1Error(ValueError):
    def __init__(self, layer, code, message):
        self.layer, self.code = layer, code
        super().__init__(message)


def need(ok, layer, code, message):
    if not ok:
        raise Q1Error(layer, code, message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def parse(raw):
    def invalid(value):
        raise ValueError("nonfinite JSON: " + value)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=invalid)


def archive(raw):
    """Validate the transport before fixed authorization binding, without extraction."""
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        need(len(names) == len(set(names)) and "manifest.json" in names,
             "ENVELOPE", "ZIP_INVENTORY", "duplicate members or no manifest")
        files = {name: z.read(name) for name in names}
    manifest = parse(files["manifest.json"])
    declared = manifest["files"]
    need(len({f["path"] for f in declared}) == len(declared) and
         {f["path"] for f in declared} == set(files) - {"manifest.json"},
         "ENVELOPE", "MANIFEST_INVENTORY", "manifest must account for every member")
    for item in declared:
        value = files[item["path"]]
        need(len(value) == item["bytes"] and sha(value) == item["sha256"],
             "ENVELOPE", "MEMBER_HASH", "member differs: " + item["path"])
    return files


@dataclass(frozen=True)
class Inputs:
    base_raw: bytes
    candidate_raw: bytes
    history_raw: bytes
    approval_raw: bytes
    policy_raw: bytes

    def documents(self):
        return archive(self.base_raw), archive(self.candidate_raw)


def load_inputs(base_zip, candidate_zip, history, approval, policy):
    paths = [base_zip, candidate_zip, history, approval, policy]
    try:
        values = [Path(p).read_bytes() for p in paths]
    except (OSError, TypeError) as exc:
        raise Q1Error("INPUT", "INPUT_MISSING", str(exc)) from exc
    result = Inputs(*values)
    result.documents()
    return result


def authorize(inputs):
    base, side = inputs.documents()
    need(bool(inputs.approval_raw), "AUTHORIZATION", "APPROVAL_MISSING", "fixed user approval required")
    need(sha(inputs.approval_raw) == APPROVAL_SHA, "AUTHORIZATION", "APPROVAL_FORGED", "approval raw Git bytes differ")
    need(sha(inputs.policy_raw) == POLICY_SHA, "AUTHORIZATION", "POLICY_CHANGED", "fixed single-question policy differs")
    approval, policy = parse(inputs.approval_raw), parse(inputs.policy_raw)
    pins = policy["input_sha256"]
    actual = {"base_zip": sha(inputs.base_raw), "candidate_zip": sha(inputs.candidate_raw),
              "candidate_file": sha(side["candidate.json"]), "manifest": sha(side["manifest.json"]),
              "scope_proposal": sha(side["scope-applicability-proposal.json"]), "history": sha(inputs.history_raw)}
    need(actual == pins, "AUTHORIZATION", "INPUT_BINDING", "valid input envelope has changed; this approval cannot transfer")
    candidate = parse(side["candidate.json"])
    ref = {k: candidate[k] for k in ("artifact_id", "revision", "content_hash")}
    need(ref == approval["candidate_ref"] and sha(encode(candidate["payload"])) == candidate["content_hash"],
         "AUTHORIZATION", "CANDIDATE_BINDING", "native candidate ref/payload differs")
    need(candidate["kind"] == "QuestionSourceReviewCandidate" and
         candidate["schema_version"] == "b-question-source-review-trial/0.1" and
         candidate["book_id"] == BOOK and candidate["payload"]["question_id"] == QUESTION and
         candidate["payload"]["answer_id"] == ANSWER and
         approval["allowed_use"] == "A_SIDE_OFFLINE_POSITIVE_SIMULATION_ONLY" and
         approval["business_approval_granted"] is True and
         approval["candidate_zip_sha256"] == pins["candidate_zip"] and
         approval["base_package_sha256"] == pins["base_zip"] and
         approval["scope_proposal_sha256"] == pins["scope_proposal"],
         "AUTHORIZATION", "SCOPE_BINDING", "wrong book/question or offline authority")
    return base, side, approval, policy


def pointer(base, reference):
    name, tail = reference.split("#", 1)
    value = parse(base[name])
    for token in tail.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def intersects(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def inspect_source(inputs):
    base, side, approval, policy = authorize(inputs)
    candidate = parse(side["candidate.json"])
    p = candidate["payload"]
    selection = parse(side["native-selection.json"])
    proposal = parse(side["scope-applicability-proposal.json"])
    native_issues = parse(side["native-scope-issues.json"])
    binding = parse(side["base-package-binding.json"])
    selected = [next(r for r in p["regions"] if r["region_id"] == rid) for rid in p["proposed_semantic_region_ids"]]
    need(p["proposed_semantic_region_ids"] == policy["semantic_region_ids"] and
         [r["role"] for r in selected] == ["stem", "option", "option", "option", "option", "answer"],
         "SOURCE", "REGION_WHITELIST", "exact six groups required")
    content = p["candidate_content"]
    normalized = content["stem_with_number_and_source_linebreaks"][2:].replace("\n", "")
    approved = approval["approved_content"]
    need(content["stem_with_number_and_source_linebreaks"].startswith("1.") and
         normalized == content["stem_body_normalized_without_number"] == approved["stem"] and
         content["option_texts"] == approved["options"] and content["answer_text"] == approved["answer"] and
         content["explanation_present"] is False and content["explanation_text"] == "" and
         ["U+%04X" % ord(x) for x in normalized[-4:]] == approved["placeholder_codepoints"],
         "SOURCE", "CONTENT_BINDING", "content/normalization differs from approved view")
    need(p["decision"] == "HOLD" and all(p[k] is False for k in
         ("business_acceptance", "human_verified", "production_applied", "a_accepted")),
         "SOURCE", "B_HISTORY_CHANGED", "original B HOLD flags must remain")
    source_refs = []
    for name, info in binding["source_artifacts"].items():
        obj = parse(base[name])
        ref = {k: obj[k] for k in ("artifact_id", "revision", "content_hash")}
        need(sha(base[name]) == info["file_sha256"] and ref == info["reference"] and
             sha(encode(obj["payload"])) == obj["content_hash"], "SOURCE", "B_REF", name)
        source_refs.append(ref)
    need(source_refs == candidate["input_refs"] and sha(base["manifest.json"]) == binding["manifest_sha256"],
         "SOURCE", "B_REF", "base artifact references differ")
    history = parse(inputs.history_raw)
    h = selection["historical_evidence"]
    need(all(history[k] == h[k] for k in ("artifact_id", "revision", "content_hash", "schema_version", "kind")) and
         sha(encode(history["payload"])) == history["content_hash"], "SOURCE", "HISTORY_BINDING", "E0.1 identity differs")
    question = pointer(base, selection["object_paths"]["question"])
    answer = pointer(base, selection["object_paths"]["answer"])
    need(question == selection["native_question_snapshot"] and answer == selection["native_answer_snapshot"] and
         question["question_id"] == QUESTION and answer["answer_id"] == ANSWER and
         question["selected_answer_id"] == ANSWER and question["candidate_answer_ids"] == [ANSWER] and
         question["section_path"] == answer["section_path"] == p["section_path"] and
         question["printed_number"] == answer["printed_number"] == "1",
         "SOURCE", "RELATION_BINDING", "native question/answer relation differs")
    amap = p["source_mapping"]["answer"]
    fragment = answer["fragments"][0]
    start, end = amap["source_text_span"]
    need(fragment["fragment_id"] == amap["source_fragment_id"] and fragment["raw_text"] == amap["raw_text"] == "1.D" and
         fragment["text_span"] == [start, end] == [2, 3] and amap["raw_text"][start:end] == content["answer_text"] and
         pointer(base, amap["source_detail"]["pointer"]) == amap["source_detail"]["value"],
         "SOURCE", "ANSWER_SPAN", "answer must preserve original raw span")
    images = {}
    for item in p["sources"]:
        raw = side[item["path"]]
        need(raw == base[item["source_package_path"]] and sha(raw) == item["sha256"], "SOURCE", "IMAGE_HASH", item["asset_id"])
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
            need(im.size == (item["width"], item["height"]), "SOURCE", "IMAGE_SIZE", item["asset_id"])
            images[item["asset_id"]] = im.convert("RGB")
    for r in p["regions"]:
        im = images[r["asset_id"]]
        x1, y1, x2, y2 = r["bbox"]
        need(r["source_size"] == list(im.size) and 0 <= x1 < x2 <= im.width and 0 <= y1 < y2 <= im.height and
             r["source_sha256"] == next(s["sha256"] for s in p["sources"] if s["asset_id"] == r["asset_id"]),
             "SOURCE", "ORIGINAL_BOX", r["region_id"])
        crop = r["crop"]
        with Image.open(io.BytesIO(side[crop["path"]])) as ci:
            rgb = ci.convert("RGB")
            need(sha(side[crop["path"]]) == crop["sha256"] and list(rgb.size) == crop["size"] and
                 rgb.tobytes() == im.crop((x1, y1, x2, y2)).tobytes() and sha(rgb.tobytes()) == crop["rgb_sha256"] and
                 crop["crop_to_original"] == [[1, 0, x1], [0, 1, y1], [0, 0, 1]],
                 "SOURCE", "CROP_BINDING", r["region_id"])
    old_ids = [f["fragment_id"] for f in question["fragments"] + answer["fragments"]]
    mapped = [fid for r in selected for fid in r["source_fragment_ids"]]
    need(len(old_ids) == 7 and sorted(old_ids) == sorted(mapped) and len(mapped) == len(set(mapped)),
         "SOURCE", "SCOPED_COVERAGE", "all seven native fragments must map exactly once")
    placeholder = next(r for r in p["regions"] if r["region_id"] == p["source_mapping"]["response_placeholder"]["source_region_id"])
    stem = selected[0]["bbox"]
    box = placeholder["bbox"]
    need(stem[0] <= box[0] < box[2] <= stem[2] and stem[1] <= box[1] < box[3] <= stem[3] and
         placeholder["region_id"] not in p["proposed_semantic_region_ids"], "SOURCE", "PLACEHOLDER_COVERAGE", "placeholder belongs inside stem")
    dispositions, proof_count = [], 0
    need(len(proposal["dispositions"]) == len(native_issues["scope_issues"]) == 31 and
         {r["issue_id"] for r in proposal["dispositions"]} == {r["issue"]["issue_id"] for r in native_issues["scope_issues"]},
         "SOURCE", "ISSUE_INVENTORY", "31 original scoped issues required")
    for entry in native_issues["scope_issues"]:
        need(pointer(base, entry["pointer"]) == entry["issue"], "SOURCE", "ORIGINAL_ISSUE", entry["pointer"])
    for d in proposal["dispositions"]:
        original = pointer(base, d["original_issue_pointer"])
        need(original["issue_id"] == d["issue_id"] and original["code"] == d["code"], "SOURCE", "ISSUE_BINDING", d["issue_id"])
        if d["code"] == "BUSINESS_REVIEW_REQUIRED":
            need(d["issue_id"] == policy["business_issue_id"] and d["proof"] == [], "SOURCE", "BUSINESS_ISSUE", d["issue_id"])
            dispositions.append({"issue_id": d["issue_id"], "disposition": "A_USER_APPROVED_FOR_FIXED_OFFLINE_SCOPE",
                                 "approval_sha256": APPROVAL_SHA, "original_issue_unchanged": True})
            continue
        expected = next((x for x in policy["exclusions"] if x["issue_id"] == d["issue_id"]), None)
        need(expected and expected["entry_sha256"] == sha(encode(d)) and bool(d["proof"]), "SOURCE", "EXCLUSION_POLICY", d["issue_id"])
        for proof in d["proof"]:
            need(pointer(base, proof["pointer"]) == proof["value"], "SOURCE", "PROOF_POINTER", proof["pointer"])
            value = proof["value"]
            if "affected_answer_ids" in value:
                need(bool(value["affected_answer_ids"]) and ANSWER not in value["affected_answer_ids"], "SOURCE", "EXCLUSION_ENTITY", d["issue_id"])
            else:
                boxes = [value["bbox"]] if "bbox" in value else [x["bbox"] for x in value.get("source_regions", [])]
                need(bool(boxes) and "asset_id" in proof, "SOURCE", "EXCLUSION_GEOMETRY", d["issue_id"])
                need(all(not intersects(b, r["bbox"]) for b in boxes for r in selected if proof["asset_id"] == r["asset_id"]),
                     "SOURCE", "EXCLUSION_OVERLAP", d["issue_id"])
            proof_count += 1
        dispositions.append({"issue_id": d["issue_id"], "disposition": "OUTSIDE_FIXED_SINGLE_QUESTION",
                             "entry_sha256": expected["entry_sha256"], "proof_pointers": [v["pointer"] for v in d["proof"]],
                             "reason": d["reason"], "original_issue_unchanged": True})
    need(proof_count == 78 and len(policy["exclusions"]) == 30, "SOURCE", "PROOF_COUNT", "30 exclusions/78 proofs required")
    graph = parse(base["artifacts/graph.json"])
    ledger = graph["payload"]["answer_coverage"]
    unassigned = [x for x in ledger if x["status"] == "UNASSIGNED"]
    return {"candidate": candidate, "selected": selected, "approval": approval, "policy": policy,
            "base": base, "side": side, "dispositions": dispositions,
            "provenance": {"native_input_refs": source_refs, "candidate_ref": approval["candidate_ref"],
                "input_sha256": policy["input_sha256"], "approval_sha256": APPROVAL_SHA,
                "native_question": question, "native_answer": answer, "original_check_issue_count": len(parse(base["artifacts/check.json"])["payload"]["issues"]),
                "original_scoped_issue_count": 31, "original_unassigned_ledger_count": len(unassigned),
                "original_unassigned_ledger": unassigned, "raw_line_view": content["stem_with_number_and_source_linebreaks"],
                "normalized_body": normalized, "answer_source_span": amap, "region_mapping": selected,
                "content_mapping": {"span_unit": "UNICODE_CODE_POINT_HALF_OPEN",
                    "raw_number_span": [0, 2], "normalized_stem_span": [0, len(normalized)],
                    "normalized_placeholder_span": content["response_output_span"],
                    "normalizations": content["normalizations"],
                    "native_stem_fragments": question["fragments"][:2],
                    "semantic_groups": [{"native_region_id": r["region_id"], "c01_region_id": r["region_id"],
                        "c01_fragment_id": "a07-fragment-" + str(i), "native_fragment_ids": r["source_fragment_ids"],
                        "normalized_text_span": [0, len(normalized if i == 0 else r["text"])]} for i, r in enumerate(selected)]},
                "dispositions": dispositions, "whole_page_coverage_claim": False, "B_joint_adoption": False,
                "independent_human_visual_review": False}}


def artifact(kind, identity, payload, dependencies, policy, run_id, created_at, mode="OBSERVED"):
    return seal_artifact({"schema_version": "1.0.0-a-proposal", "artifact_id": identity, "revision": 1,
        "kind": kind, "run_id": run_id, "book_id": BOOK, "scope_id": SCOPE,
        "input_refs": [artifact_ref(a) for a in dependencies], "created_at": created_at,
        "producer": {"module": "annotation.a07.q1", "implementation_version": VERSION,
            "config_version": "a07-policy-" + POLICY_SHA, "policy_versions": [policy_ref(policy)],
            "model_version": None, "prompt_version": None, "evidence_mode": mode}, "payload": payload})


def write_once(root, path, raw):
    dest = Path(root) / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        need(dest.read_bytes() == raw, "RESOURCE", "OUTPUT_EXISTS", "existing resource differs: " + path)
    else:
        dest.write_bytes(raw)
    return {"path": path, "sha256": sha(raw), "media_type": "image/jpeg" if path.endswith(".jpg") else
            "image/png" if path.endswith(".png") else "application/json"}


def build_source(inputs, root, run_id, created_at):
    facts = inspect_source(inputs)
    base, side = facts["base"], facts["side"]
    p = facts["candidate"]["payload"]
    policy = seal_policy({"policy_id": "a07-q1-offline-v1", "revision": 1, "confirmation_status": "A_INTERNAL_PROPOSAL",
        "option_grouping": "SEPARATE", "role_mapping": {"stem": "Q", "option": "Q", "answer": "A", "explanation": "E", "shared_material": "W"},
        "source_notes": ["A-only fixed Q1 offline user approval SHA256 " + APPROVAL_SHA,
            "30 exclusions and six region whitelist policy SHA256 " + POLICY_SHA, "B HOLD and original issues preserved; joint adoption unproven"],
        "frame_save_status": "SYNTHETIC", "ocr_status": "UNVERIFIED", "applicability": "PROPOSAL_ONLY"})
    evidence = []
    resources = [("approval", inputs.approval_raw), ("policy", inputs.policy_raw), ("history", inputs.history_raw),
                 ("provenance", encode(facts["provenance"]))]
    resources += [("side-" + n.replace(".json", ""), side[n]) for n in
                  ("candidate.json", "native-selection.json", "native-scope-issues.json", "scope-applicability-proposal.json", "manifest.json", "base-package-binding.json")]
    resources += [("base-" + n.split("/")[-1].replace(".json", ""), base[n]) for n in
                  ("artifacts/graph.json", "artifacts/evidence.json", "artifacts/check.json", "manifest.json")]
    for name, raw in resources:
        resource = write_once(root, "assets/input/" + name + ".json", raw)
        evidence.append({"evidence_id": "ev-" + name, "resource": resource, "description": "Unmodified observed input or explicit A provenance: " + name, "mode": "OBSERVED"})
    for r in p["regions"]:
        resource = write_once(root, "assets/" + r["crop"]["path"], side[r["crop"]["path"]])
        evidence.append({"evidence_id": "ev-" + r["region_id"], "resource": resource, "description": "Exact deterministic crop; model visual reviewed, human_verified=false", "mode": "OBSERVED"})
    assets = []
    for s in p["sources"]:
        resource = write_once(root, "assets/" + s["path"], side[s["path"]])
        assets.append(dict(resource, asset_id=s["asset_id"], width=s["width"], height=s["height"], source_label=s["source_package_path"], provenance="ORIGINAL"))
    proof = ["ev-approval", "ev-provenance", "ev-side-candidate"]
    source = artifact("SourceBundle", "a07-source-" + run_id, {"assets": assets,
        "directories": [{"directory_id": DIRECTORY, "parent_id": None, "label": "/".join(p["section_path"])}],
        "pages_expected": [s["asset_id"] for s in p["sources"]], "pages_acquired": [s["asset_id"] for s in p["sources"]],
        "external_page_mappings": [{"asset_id": s["asset_id"], "directory_id": DIRECTORY, "external_page": s["asset_id"],
            "mapping_status": "CONFIRMED", "evidence_refs": proof} for s in p["sources"]],
        "history": [{"resource": e["resource"], "quality": "UNVERIFIED", "reason": "Frozen B/A evidence; does not establish human or joint platform acceptance"} for e in evidence if e["evidence_id"] in
                    {"ev-history", "ev-base-check", "ev-side-native-scope-issues", "ev-side-candidate"}],
        "scope_manifest": [QUESTION], "scope_manifest_basis": "Independent fixed A user scope, six groups and 30 evidence-bound exclusions: " + APPROVAL_SHA,
        "metadata_page_count": None}, [], policy, run_id, created_at)
    regions, fragments, clues = [], [], []
    for i, r in enumerate(facts["selected"]):
        s = next(a for a in assets if a["asset_id"] == r["asset_id"])
        box = {"image": {k: s[k] for k in ("asset_id", "width", "height", "sha256")}, "bbox": r["bbox"]}
        rid, fid = r["region_id"], "a07-fragment-" + str(i)
        text = p["candidate_content"]["stem_body_normalized_without_number"] if i == 0 else r["text"]
        regions.append({"region_id": rid, "box": box, "crop_transform": {"scale_x": 1.0, "scale_y": 1.0,
            "offset_x": -float(r["bbox"][0]), "offset_y": -float(r["bbox"][1]), "rotation_degrees": 0.0,
            "padding": [0.0]*4, "processed_width": r["crop"]["size"][0], "processed_height": r["crop"]["size"][1], "invertible": True},
            "content_type": "text", "text": text, "source": "HISTORICAL", "evidence_refs": proof + ["ev-" + rid],
            "printed_number_candidates": ["1"], "certainty": "CONFIRMED"})
        fragments.append({"fragment_id": fid, "region_ids": [rid], "role": r["role"], "content_type": "text", "reading_order": i})
        clues.append({"clue_id": "a07-clue-" + str(i), "box": box, "source": "SHARED_RECOGNITION", "disposition": "ASSIGNED",
            "region_ids": [rid], "reason": "Approved single-question inventory; no whole-page coverage claim", "evidence_refs": proof + ["ev-" + rid]})
    observed = artifact("EvidenceBundle", "a07-evidence-" + run_id, {"source": artifact_ref(source), "regions": regions, "coverage_clues": clues}, [source], policy, run_id, created_at)
    graph = artifact("QuestionGraph", "a07-graph-" + run_id, {"source": artifact_ref(source), "evidence": artifact_ref(observed),
        "questions": [{"question_id": QUESTION, "directory_id": DIRECTORY, "question_type": "ordinary_choice",
            "fragment_ids": [f["fragment_id"] for f in fragments[:5]], "parent_question_id": None, "shared_fragment_ids": [],
            "cross_page": False, "external_refs": {"printed_number": "1", "platform_question_id": None, "platform_order": None}}],
        "fragments": fragments, "answer_relations": [{"relation_id": "a07-answer-relation", "question_id": QUESTION,
            "candidate_fragment_ids": [fragments[5]["fragment_id"]], "selected_fragment_ids": [fragments[5]["fragment_id"]],
            "status": "SELECTED", "evidence_refs": proof + ["ev-side-native-selection"]}],
        "identity_notes": "Native question/answer IDs and 1.D span preserved in ev-provenance; A approval selects six groups only. B HOLD unchanged."},
        [source, observed], policy, run_id, created_at)
    bundle = validate_bundle({"format_version": "c01-exchange-1", "evidence": evidence, "policies": [policy], "artifacts": [source, observed, graph]}, asset_root=root)
    return bundle, facts
