"""Freeze B source-confirmed lesson content in the existing C01 exchange format.

Only SourceBundle/EvidenceBundle/QuestionGraph/CheckReport are emitted. No native
identity, platform snapshot, plan, receipt, network or OCR entry is used.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re

from PIL import Image

A_COMMIT = "c5aefbc8e995c410b3babf74a251f05a7724a1c2"
sha = lambda raw: hashlib.sha256(raw).hexdigest()
canonical = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
encode = lambda value: (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n").encode("utf-8")


def need(value, code):
    if not value:
        raise ValueError(code)


def seal(value):
    value = copy.deepcopy(value)
    value["content_hash"] = sha(canonical({k:v for k,v in value.items() if k != "content_hash"}))
    return value


def ref(value):
    return {key:value[key] for key in ("artifact_id", "revision", "kind", "content_hash")}


def runs(text):
    result, end = [], 0
    for match in re.finditer(r"_{2,}", text):
        if match.start() > end:
            result.append({"format":"plain", "text":text[end:match.start()]})
        result.append({"format":"blank", "token":match[0], "value":None})
        end = match.end()
    if end < len(text):
        result.append({"format":"plain", "text":text[end:]})
    return result


def source_runs(block):
    if 'rich_runs' not in block:
        return runs(block['text']) if block['text'] is not None else []
    result=copy.deepcopy(block['rich_runs']);display=[]
    for run in result:
        if run['format']=='plain':
            need(set(run)=={'format','text'} and type(run['text']) is str,'PLAIN_RUN');display.append(run['text'])
        elif run['format']=='blank':
            need({'format','token','value'}<=set(run)<={'format','token','value','blank_id'} and
                 re.fullmatch(r'_{2,}',run['token']) and run['value'] is None,'NULL_SOURCE_BLANK');display.append(run['token'])
        else:
            need(run['format']=='latex' and set(run)=={'format','text','source_text'},'SOURCE_MATH_RUN')
            token=run['source_text'];tex=None
            if m:=re.fullmatch(r'(\d+)/(\d+)',token):tex=r'\frac{'+m[1]+'}{'+m[2]+'}'
            elif m:=re.fullmatch(r'([A-Za-z0-9]+)([²³⁴])',token):tex=m[1]+'^{'+{'²':'2','³':'3','⁴':'4'}[m[2]]+'}'
            elif m:=re.fullmatch(r'([A-Za-z]+)([₁₂₃])',token):tex=m[1]+'_{'+{'₁':'1','₂':'2','₃':'3'}[m[2]]+'}'
            elif m:=re.fullmatch(r'√(\d+)',token):tex=r'\sqrt{'+m[1]+'}'
            need(tex is not None and run['text']==tex,'SOURCE_MATH_SEMANTICS');display.append(token)
    need(''.join(display)==(block['text'] or ''),'EXACT_SOURCE_RUN_TEXT')
    return result


def build_delivery(spec, images, generation=None):
    need(spec["schema"] == "b-private-lesson-source-export-input/0.1" and spec["review_kind"] == "B_MODEL_SOURCE_CONFIRMED", "SOURCE_REVIEW_REQUIRED")
    basis = copy.deepcopy(spec)
    mode = basis.get("evidence_mode", "OBSERVED")
    need(mode in ("OBSERVED", "SYNTHETIC"), "EVIDENCE_MODE")
    basis.setdefault("input_spec_sha256", sha(canonical(spec)))
    for asset in basis["assets"]:
        asset["path"] = "assets/"+asset["asset_id"]+".jpg"
    assets = []
    blobs = {}
    for asset in basis["assets"]:
        raw = images[asset["asset_id"]]
        need(sha(raw) == asset["sha256"], "ORIGINAL_SOURCE_CHANGED")
        with Image.open(io.BytesIO(raw)) as image:
            need(list(image.size) == [asset["width"], asset["height"]], "SOURCE_DIMENSIONS_CHANGED")
        blobs[asset["path"]] = raw
        assets.append({"asset_id":asset["asset_id"], "path":asset["path"], "sha256":asset["sha256"], "media_type":"image/jpeg",
            "width":asset["width"], "height":asset["height"], "source_label":f"Original viewer {asset['viewer_page']} / source index {asset['viewer_page']-1}", "provenance":"ORIGINAL" if mode == "OBSERVED" else "SYNTHETIC"})
    need(len({a["asset_id"] for a in assets}) == len(assets), "DUPLICATE_ASSET")
    items = basis["items"]
    need(len({i["item_key"] for i in items}) == len(items) and all(i["review_kind"] == "B_MODEL_SOURCE_CONFIRMED" and i["human_verified"] is False for i in items), "LOCAL_IDENTITIES_OR_REVIEW_CHANGED")
    review = {"review_kind":"B_MODEL_SOURCE_CONFIRMED", "independent_human_acceptance":False, "a_owner_acceptance":False,
              "original_root_review_sha256":basis["root_review_sha256"], "items":copy.deepcopy(items)}
    blobs.update({"basis.json":encode(basis), "current-review.json":encode(review)})
    expected_context = {"config_version":"lesson-source-c01.1", "a_consumer_commit":A_COMMIT,
                        "basis_sha256":sha(blobs["basis.json"]), "current_review_sha256":sha(blobs["current-review.json"])}
    if generation is None:
        generation = {"created_at":datetime.now(timezone.utc).isoformat(timespec="seconds"), **expected_context}
    need(set(generation) == {"created_at", *expected_context} and all(generation[k] == v for k,v in expected_context.items())
         and datetime.fromisoformat(generation["created_at"].replace("Z", "+00:00")).tzinfo is not None, "GENERATION_CONTEXT_CHANGED")
    blobs["generation.json"] = encode(generation)
    seed = sha(canonical(generation))[:24]
    choice_items = [i for i in items if i["fields"].get("choice") is not None]
    blocks = basis["blocks"]
    combined = []
    for item in choice_items:
        options = [b for b in blocks if b.get("item_key") == item["item_key"] and b["field"] == "choice" and b.get("graph_fragment", True)]
        labels = [re.fullmatch(r"([A-D])[.、]\s*[^\n]+", b["text"].strip()) for b in options]
        if len(options) != 4 or [m[1] if m else None for m in labels] != list("ABCD"):
            combined.append(item["item_key"])
    policy = seal({"policy_id":"b-lesson-source-layout-proposal", "revision":1, "confirmation_status":"UNRESOLVED",
        "option_grouping":"COMBINED" if combined else "SEPARATE", "role_mapping":{"stem":"Q", "option":"W", "answer":"A", "explanation":"E", "shared_material":"Q"},
        "source_notes":["B source layout description only; not a claim of A policy ownership or joint platform adoption.", "Confirmed B text/answer associations are separate from option-level geometry readiness."],
        "frame_save_status":"UNVERIFIED", "ocr_status":"UNVERIFIED", "applicability":"PROPOSAL_ONLY"})
    pref = {key:policy[key] for key in ("policy_id", "revision", "content_hash")}
    def artifact(kind, suffix, payload, dependencies):
        return seal({"schema_version":"1.0.0-a-proposal", "artifact_id":"b-lesson-"+suffix+"-"+seed, "revision":1, "kind":kind,
            "run_id":"b-lesson-"+seed, "book_id":basis["book_id"], "scope_id":basis["scope_id"], "input_refs":[ref(d) for d in dependencies],
            "producer":{"module":"b-lesson-source-projection", "implementation_version":"1", "config_version":generation["config_version"],
                        "policy_versions":[pref], "model_version":None, "prompt_version":None, "evidence_mode":mode},
            "created_at":generation["created_at"], "payload":payload})
    qids = {item["item_key"]:"bq-"+item["item_key"] for item in items}
    source = artifact("SourceBundle", "source", {"assets":assets,
        "directories":[{"directory_id":"lesson-local", "parent_id":None, "label":basis["source_label"]}],
        "pages_expected":list(images), "pages_acquired":list(images), "external_page_mappings":[{"asset_id":a["asset_id"], "directory_id":"lesson-local",
            "external_page":a["source_label"], "mapping_status":"CONFIRMED", "evidence_refs":["ev-current-review"]} for a in assets],
        "history":[], "scope_manifest":list(qids.values()), "scope_manifest_basis":"Exactly the declared B lesson source questions; reading material and next-section boundary are explicit exclusions, not additional questions.", "metadata_page_count":None}, [])
    assets_by_id = {a["asset_id"]:a for a in assets}
    regions, fragments, bindings, proofs, clues = [], [], [], [], []
    for block in blocks + [{**b, "content_type":"image", "text":None, "field":"exclusion", "role":None, "item_key":None, "graph_fragment":False} for b in basis["exclusions"] if b.get("evidence_region", True)]:
        aid = block["asset_id"]; asset = assets_by_id[aid]; bbox = block["bbox"]
        need(len(bbox) == 4 and all(type(x) is int for x in bbox) and 0 <= bbox[0] < bbox[2] <= asset["width"] and 0 <= bbox[1] < bbox[3] <= asset["height"], "SOURCE_WINDOW_BOUNDS")
        if block.get("derived_from_block_id"):
            parents = [b for b in blocks if b["block_id"] == block["derived_from_block_id"]]
            need(len(parents) == 1 and parents[0].get("graph_fragment") is False and parents[0]["asset_id"] == aid, "DERIVED_OPTION_ORIGINAL_REQUIRED")
            pb = parents[0]["bbox"]
            bounds = pb
            if block.get("derived_bounds_review"):
                reviewed = block["derived_bounds_review"]
                need(reviewed["original_bbox"] == pb and reviewed["source_evidence_sha256"] == basis["option_evidence"]["original_raw_sha256"], "DERIVED_BOUNDS_REVIEW_BINDING")
                entry = next((q for q in basis["option_evidence"]["questions"] if q["item_key"] == block["item_key"]), None)
                need(entry is not None and entry["recommended_container_bbox"] == reviewed["allowed_container_bbox"], "DERIVED_BOUNDS_REVIEW_SCOPE")
                bounds = reviewed["allowed_container_bbox"]
            need(bounds[0] <= bbox[0] < bbox[2] <= bounds[2] and bounds[1] <= bbox[1] < bbox[3] <= bounds[3], "DERIVED_OPTION_OUTSIDE_REVIEWED_CONTAINER")
        need(block["content_type"] in ("image", "text", "formula", "table") and (block["text"] is None) == (block["content_type"] == "image"), "SOURCE_BLOCK_TYPE")
        rid, fid = "region-"+block["block_id"], "fragment-"+block["block_id"]
        box = {"image":{key:asset[key] for key in ("asset_id", "width", "height", "sha256")}, "bbox":[float(x) for x in bbox]}
        regions.append({"region_id":rid, "box":box, "crop_transform":{"scale_x":1.0, "scale_y":1.0, "offset_x":float(-bbox[0]), "offset_y":float(-bbox[1]),
            "rotation_degrees":0.0, "padding":[0.0]*4, "processed_width":bbox[2]-bbox[0], "processed_height":bbox[3]-bbox[1], "invertible":True},
            "content_type":block["content_type"], "text":block["text"], "source":"HISTORICAL" if mode == "OBSERVED" else "SYNTHETIC", "evidence_refs":["ev-current-review", "ev-basis"], "printed_number_candidates":[], "certainty":"CONFIRMED"})
        with Image.open(io.BytesIO(images[aid])) as original:
            crop = original.convert("RGB").crop(bbox)
            stream = io.BytesIO(); crop.save(stream, format="PNG"); raw = stream.getvalue()
        path = "crops/"+block["block_id"]+".png"; blobs[path] = raw
        proofs.append({"region_id":rid, "path":path, "sha256":sha(raw), "rgb_sha256":sha(crop.tobytes()),
                       "physical_window_id":sha(canonical([asset["sha256"], bbox]))})
        fragment = block.get("graph_fragment", True)
        bindings.append({"block_id":block["block_id"], "item_key":block["item_key"], "field":block["field"], "role":block["role"],
                         "region_id":rid, "fragment_id":fid if fragment else None, "runs":source_runs(block),
                         "subfigure_count":block.get("subfigure_count", 0)})
        if block.get("derived_from_block_id"):
            bindings[-1]["derived_from_block_id"] = block["derived_from_block_id"]
        if fragment:
            fragments.append({"fragment_id":fid, "region_ids":[rid], "role":block["role"], "content_type":block["content_type"], "reading_order":len(fragments)})
        clues.append({"clue_id":"clue-"+block["block_id"], "box":box, "source":"SHARED_RECOGNITION", "disposition":"EXCLUDED" if block["field"] == "exclusion" else "ASSIGNED",
            "region_ids":[] if block["field"] == "exclusion" else [rid], "reason":block.get("reason", "A declared bounded source window; not an independent whole-page coverage scan."), "evidence_refs":["ev-current-review"]})
    for excluded in (b for b in basis["exclusions"] if not b.get("evidence_region", True)):
        asset = assets_by_id[excluded["asset_id"]]
        bbox = excluded["bbox"]
        need(len(bbox) == 4 and all(type(x) is int for x in bbox) and 0 <= bbox[0] < bbox[2] <= asset["width"] and 0 <= bbox[1] < bbox[3] <= asset["height"], "EXCLUSION_BOUNDS")
        clues.append({"clue_id":"clue-"+excluded["block_id"], "box":{"image":{k:asset[k] for k in ("asset_id", "width", "height", "sha256")}, "bbox":[float(x) for x in bbox]},
            "source":"SHARED_RECOGNITION", "disposition":"EXCLUDED", "region_ids":[], "reason":excluded["reason"], "evidence_refs":["ev-current-review"]})
    need(len({r["region_id"] for r in regions}) == len(regions), "DUPLICATE_REGION")
    questions, relations = [], []
    for item in items:
        owned = [b for b in bindings if b["item_key"] == item["item_key"] and b["fragment_id"] is not None]
        for name, expected in item["fields"].items():
            actual = "".join(next(r["text"] for r in regions if r["region_id"] == b["region_id"]) for b in owned if b["field"] == name)
            need(actual == (expected or ""), "SOURCE_FIELD_LOSS:"+item["item_key"]+":"+name)
        qid = qids[item["item_key"]]
        answers = [b["fragment_id"] for b in owned if b["role"] in ("answer", "explanation")]
        need(bool(answers), "ANSWER_SOURCE_REQUIRED")
        questions.append({"question_id":qid, "directory_id":"lesson-local", "question_type":"ordinary_choice" if item["fields"].get("choice") is not None else "free_response",
            "fragment_ids":[b["fragment_id"] for b in owned if b["role"] not in ("answer", "explanation")],
            "parent_question_id":qids[item["parent_item_key"]] if item.get("parent_item_key") else None, "shared_fragment_ids":[], "cross_page":len({b["asset_id"] for b in blocks if b.get("item_key") == item["item_key"] and b["role"] not in ("answer", "explanation")}) > 1,
            "external_refs":{"printed_number":item["printed_number"], "platform_question_id":None, "platform_order":None}})
        relations.append({"relation_id":"relation-"+item["item_key"], "question_id":qid, "candidate_fragment_ids":answers,
                          "selected_fragment_ids":answers, "status":"SELECTED", "evidence_refs":["ev-current-review"]})
    evidence = artifact("EvidenceBundle", "evidence", {"source":ref(source), "regions":regions, "coverage_clues":clues}, [source])
    graph = artifact("QuestionGraph", "graph", {"source":ref(source), "evidence":ref(evidence), "questions":questions, "fragments":fragments,
        "answer_relations":relations, "identity_notes":"Stable B local semantic IDs only. SELECTED records B model source-confirmed answer ownership, not human signature, A-owner acceptance or platform identity. Frozen model-corrected text uses HISTORICAL because C01 has no MODEL_REVIEW region-source enum."}, [source, evidence])
    issues = [{"issue_id":"option-boundaries-"+key, "code":"OPTION_INCOMPLETE", "scope_type":"question", "scope_id":qids[key],
        "evidence_refs":["ev-current-review"], "severity":"blocking", "blocks":["PLAN", "APPLY", "COMPLETE"],
        "suggested_strategy":{"strategy_id":"RECONCILE", "max_attempts":0, "max_cost":0.0},
        "reason":"All A-D text and answer are source-confirmed, but provided option geometry remains combined; four independently source-bound option windows are not yet supplied."} for key in combined]
    if not issues:
        issues = [{"issue_id":"c01-preapply-policy-scope", "code":"POLICY_UNRESOLVED", "scope_type":"scope", "scope_id":basis["scope_id"], "evidence_refs":["ev-current-review"],
            "severity":"info", "blocks":["PLAN", "APPLY"], "suggested_strategy":{"strategy_id":"RECONCILE", "max_attempts":0, "max_cost":0.0},
            "reason":"B content delivery is complete; this C01 PRE_APPLY envelope does not assert joint platform-policy adoption or full-page target readiness."}]
    checks = [{"check_id":name, "outcome":outcome, "evidence_refs":["ev-current-review", "ev-basis"], "reason":reason} for name,outcome,reason in (
        ("source_integrity", "PASS", "Original hashes and derived source pixels verified."),
        ("structure", "PASS", "Declared lesson identities, fragments, figures, explicit variant parent and null blanks are preserved."),
        ("answer_matching", "PASS", "Every selected answer/explanation is source-confirmed by B model review; no human or A signature is implied."),
        ("coverage", "UNAVAILABLE", "Bounded lesson windows are represented; this package does not claim whole-page/chapter coverage."),
        ("policy", "UNAVAILABLE", "Remaining geometry and C01 PRE_APPLY policy scope are listed precisely; no per-question human-signature requirement is introduced."))]
    check = artifact("CheckReport", "check", {"stage":"PRE_APPLY", "subject":ref(graph), "graph":ref(graph), "policy":pref, "snapshot":None, "receipt":None,
        "coverage":{"scope_id":basis["scope_id"], "pages_expected":list(images), "pages_checked":[], "clue_ids":[c["clue_id"] for c in clues], "unassigned_region_ids":[]},
        "checks":checks, "issues":issues, "decision":"HOLD", "reason":"B content and associations confirmed; remaining source geometry/PRE_APPLY scope is distinct from A-owner acceptance. No execution artifact exists."}, [source, evidence, graph])
    records = [{"evidence_id":"ev-"+name, "resource":{"path":path, "sha256":sha(blobs[path]), "media_type":"application/json"}, "description":description, "mode":mode}
        for name,path,description in (("current-review", "current-review.json", "B model source review and confirmed answer links; not independent human or A-owner acceptance."),
                                      ("basis", "basis.json", "Frozen source layout, raw primary OCR, original hashes and explicit exclusions; no platform state or insertion inputs."))]
    blobs["bundle.json"] = encode({"format_version":"c01-exchange-1", "evidence":records, "policies":[policy], "artifacts":[source, evidence, graph, check]})
    sidecar = {"schema":"b-lesson-source-delivery/0.1", "a_consumer_commit":A_COMMIT, "decision":"HOLD", "b_content_status":"SOURCE_CONTENT_AND_ANSWER_LINKS_CONFIRMED",
        "generation_sha256":sha(blobs["generation.json"]), "basis_sha256":sha(blobs["basis.json"]), "current_review_sha256":sha(blobs["current-review.json"]),
        "c01_graph_ref":ref(graph), "bindings":bindings, "source_proofs":proofs,
        "b_content_ready":not combined, "b_content_issues":[{"item_key":key, "code":"OPTION_INCOMPLETE"} for key in combined],
        "confirmed_item_keys":[i["item_key"] for i in items], "pending_option_geometry":combined,
        "unfilled_question_blanks":sum(len(re.findall(r"_{2,}", i["fields"]["question"])) for i in items),
        "source_windows_are_platform_frames":False, "platform_actions":[], "human_verified":False, "a_owner_acceptance":False,
        "business_acceptance":False, "chapter_denominator":None, "notes":basis["scope_notes"]}
    blobs["delivery.json"] = encode(sidecar)
    return blobs


def write_delivery(root, blobs):
    root = Path(root); root.mkdir(parents=True, exist_ok=False)
    for name, raw in blobs.items():
        path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--spec", type=Path); group.add_argument("--frozen", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    path = args.spec or args.frozen/"basis.json"
    spec = json.loads(path.read_bytes())
    images = {a["asset_id"]:(Path(a["path"]) if args.spec else args.frozen/a["path"]).read_bytes() for a in spec["assets"]}
    generation = json.loads((args.frozen/"generation.json").read_bytes()) if args.frozen else None
    blobs = build_delivery(spec, images, generation); write_delivery(args.out, blobs)
    sidecar = json.loads(blobs["delivery.json"])
    print(json.dumps({"files":len(blobs), "bundle_sha256":sha(blobs["bundle.json"]), "questions":len(sidecar["confirmed_item_keys"]),
                      "confirmed_answer_relations":len(sidecar["confirmed_item_keys"]), "pending_option_geometry":sidecar["pending_option_geometry"], "decision":"HOLD"}))


if __name__ == "__main__":main()
