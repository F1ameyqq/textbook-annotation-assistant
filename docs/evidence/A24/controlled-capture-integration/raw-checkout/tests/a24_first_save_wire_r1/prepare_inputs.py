"""Bind the one fixed B/OCR+AI-corrected question; no inference or platform I/O."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"src"))
from annotation.contracts import seal_artifact, seal_policy, artifact_ref, policy_ref, validate_bundle
from annotation.runtime.storage.common import digest
from annotation.quality.live_pilot import question_facts

OUT = ROOT/"docs/evidence/A24/first-save-wire-r1"
PRIVATE = Path("D:/1800/.local/stages/a24-first-save-r1-inputs/author-content-v1")
ASSETS = Path("D:/1800/.local/stages")
MODEL = Path("D:/1800/.local/stages/a24-model-one-question")
MODEL_HASHES = {"reviewed-candidate-v1.json": "cd4ee0c6a379fa5bf8cc87dccdb010c423a9e2f9a2382336efaa00cefe103b5a",
    "raw-regional-candidates-r1.json": "6452f279a70151721115cd1f8bef1d4995a0e296ad10239694fc23bf9acf322d",
    "model-input-manifest.json": "f478e2b47c1338ff303612d3d99967811b7dea5c5b4b7a204faf7f9e789055be",
    "fixed-result-r1-no-body-manifest.json": "ec45a2c44e262a96b210aa5fd8a00a8a360721a4773cbaede4a7d22596ee3108"}


def sha(raw): return hashlib.sha256(raw).hexdigest()
def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw=(json.dumps(value,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    with path.open("xb") as handle: handle.write(raw)
    return {"path": str(path), "sha256": sha(raw), "bytes": len(raw)}
def resource(path):
    return {"path": path.relative_to(ASSETS).as_posix(), "sha256": sha(path.read_bytes()), "media_type": "application/json"}


def prepare():
    reviewed=json.loads((MODEL/"reviewed-candidate-v1.json").read_bytes())
    raw_model=json.loads((MODEL/"raw-regional-candidates-r1.json").read_bytes())
    for name, expected in MODEL_HASHES.items(): assert sha((MODEL/name).read_bytes())==expected
    crops=json.loads((OUT/"crop-bindings.json").read_bytes())
    assert reviewed["human_user_content_review_claimed"] is False
    assert raw_model["status"]=="FAILED_HOLD_ANSWER_REGION_EMPTY" and not raw_model["records"][5]["B_ocr_atoms"]
    for a,b,c in zip(reviewed["fragments"], raw_model["records"], crops["regions"]):
        assert a["original_bbox"]==b["source"]["original_bbox"]==c["original_bbox_xyxy"]
        assert b["source"]["pixel_sha256"]==c["source_crop_RGB_sha256"]
        assert b["source"]["source_original_sha256"]==c["original_sha256"]
    PRIVATE.mkdir(parents=True,exist_ok=False)
    for c in crops["regions"]:
        p=Path(c["private_path"]); assert sha(p.read_bytes())==c["jpeg_sha256"]
        target=PRIVATE/"crops"/c["object_basename"]; target.parent.mkdir(parents=True,exist_ok=True)
        with target.open("xb") as handle: handle.write(p.read_bytes())
    policy=seal_policy({"policy_id":"a24-r1-role-adoption-proposal","revision":1,
        "confirmation_status":"A_INTERNAL_PROPOSAL","option_grouping":"SEPARATE",
        "role_mapping":{"stem":"Q","option":"W","answer":"A","explanation":"E","shared_material":"Q"},
        "source_notes":["Same A24 ordinary single-choice W-role proposal; not joint adoption or first-save authority"],
        "frame_save_status":"UNVERIFIED","ocr_status":"UNVERIFIED","applicability":"PROPOSAL_ONLY"})
    created=datetime.now(timezone.utc).isoformat()
    def artifact(kind,identity,payload,deps=()):
        return seal_artifact({"schema_version":"1.0.0-a-proposal","artifact_id":identity,"revision":1,"kind":kind,
            "run_id":"a24-r1-fixed-content-binding","book_id":"46007447","scope_id":"section2-basic-printed1",
            "input_refs":[artifact_ref(a) for a in deps],"created_at":created,
            "producer":{"module":"a24-r1-native-content-conversion","implementation_version":"1",
                "config_version":MODEL_HASHES["reviewed-candidate-v1.json"],"policy_versions":[policy_ref(policy)],
                "model_version":"B-existing-RapidOCR-1.4.4-local-CPU; partial FAILED_HOLD preserved","prompt_version":None,
                "evidence_mode":"OBSERVED"},"payload":payload})
    qid="a24-b46007447-s2-basic-q1"
    images=[{"asset_id":"a24-original-"+str(v),"path":"a24-current-context-r1-live/original-viewer-"+str(v)+".jpg",
        "media_type":"image/jpeg","width":wh[0],"height":wh[1],"sha256":s,
        "source_label":"Fixed accepted current-source original viewer"+str(v),"provenance":"ORIGINAL"}
        for v,wh,s in ((14,(1218,1694),crops["regions"][0]["original_sha256"]),(173,(1148,1621),crops["regions"][5]["original_sha256"]))]
    source=artifact("SourceBundle","a24-r1-source",{"assets":images,
        "directories":[{"directory_id":"source-s2-basic","parent_id":None,"label":"2 一定是直角三角形吗 / 基础题"}],
        "pages_expected":[a["asset_id"] for a in images],"pages_acquired":[a["asset_id"] for a in images],
        "external_page_mappings":[{"asset_id":a["asset_id"],"directory_id":"source-s2-basic","external_page":str(v),
            "mapping_status":"CONFIRMED","evidence_refs":["a24-r1-fixed-model-source"]} for a,v in zip(images,(14,173))],
        "history":[{"resource":resource(MODEL/name),"quality":"UNVERIFIED" if name.startswith("raw-") else "REVIEWED",
            "reason":"Actual fixed OCR/explicit coordinator AI correction; no human content approval or OCR answer success claimed"}
            for name in ("raw-regional-candidates-r1.json","reviewed-candidate-v1.json","model-input-manifest.json")],
        "scope_manifest":[qid],"scope_manifest_basis":"Exact supplied model/correction hashes; one question only; formal source acceptance referenced separately",
        "metadata_page_count":214})
    regions=[]; fragments=[]; part_texts=[]
    for i,(f,c) in enumerate(zip(reviewed["fragments"],crops["regions"])):
        image=images[0 if i<5 else 1]; binding={k:image[k] for k in ("asset_id","width","height","sha256")}
        text=((f["label"]+". ") if f["role"]=="option" else "")+f["approved_text"]
        part_texts.append(text)
        rid,fid=qid+"-r"+str(i),qid+"-f"+str(i)
        regions.append({"region_id":rid,"box":{"image":binding,"bbox":c["original_bbox_xyxy"]},
            "crop_transform":{"scale_x":1.,"scale_y":1.,"offset_x":float(c["original_bbox_xyxy"][0]),
                "offset_y":float(c["original_bbox_xyxy"][1]),"rotation_degrees":0.,"padding":[0.,0.,0.,0.],
                "processed_width":c["width"],"processed_height":c["height"],"invertible":True},
            "content_type":"text","text":text,"source":"HISTORICAL","evidence_refs":["a24-r1-fixed-model-source"],
            "printed_number_candidates":["1"] if i in (0,5) else [],"certainty":"CONFIRMED"})
        fragments.append({"fragment_id":fid,"region_ids":[rid],"role":f["role"],"content_type":"text","reading_order":i})
    evidence=artifact("EvidenceBundle","a24-r1-evidence",{"source":artifact_ref(source),"regions":regions,
        "coverage_clues":[{"clue_id":qid+"-clue"+str(i),"box":r["box"],"source":"SHARED_RECOGNITION","disposition":"ASSIGNED",
            "region_ids":[r["region_id"]],"reason":"Fixed one-question crop, OCR plus explicit AI correction; not whole-page coverage",
            "evidence_refs":["a24-r1-fixed-model-source"]} for i,r in enumerate(regions)]},[source])
    graph=artifact("QuestionGraph","a24-r1-question-graph",{"source":artifact_ref(source),"evidence":artifact_ref(evidence),
        "questions":[{"question_id":qid,"directory_id":"source-s2-basic","question_type":"ordinary_choice",
            "fragment_ids":[f["fragment_id"] for f in fragments[:5]],"parent_question_id":None,"shared_fragment_ids":[],
            "cross_page":False,"external_refs":{"printed_number":"1","platform_question_id":None,"platform_order":None}}],
        "fragments":fragments,"answer_relations":[{"relation_id":qid+"-answer","question_id":qid,
            "candidate_fragment_ids":[fragments[5]["fragment_id"]],"selected_fragment_ids":[fragments[5]["fragment_id"]],
            "status":"SELECTED","evidence_refs":["a24-r1-fixed-model-source"]}],
        "identity_notes":"Actual OCR partial/answer empty preserved; fixed coordinator AI corrections quoted as HISTORICAL source, not HUMAN; role policy/write authority unresolved"},[source,evidence])
    bundle={"format_version":"c01-exchange-1","evidence":[{"evidence_id":"a24-r1-fixed-model-source",
        "resource":resource(MODEL/"reviewed-candidate-v1.json"),"description":"Fixed coordinator AI visual correction of actual OCR; formal AI review accepted source only; not human user approval","mode":"OBSERVED"}],
        "policies":[policy],"artifacts":[source,evidence,graph]}
    checked=validate_bundle(bundle,asset_root=ASSETS)
    conversion={"schema":"A24R1NativeOneQuestionConversion/v1","book_id":"46007447","question_id":qid,
        "source_reviewed_sha256":MODEL_HASHES["reviewed-candidate-v1.json"],"source_raw_sha256":MODEL_HASHES["raw-regional-candidates-r1.json"],
        "model_status_retained":raw_model["status"],"human_content_approval_claimed":False,
        "option_conversion":"explicit label + '. ' + approved numeric text; no new semantic content",
        "answer_provenance":"COORDINATOR_VISUAL_TRANSCRIPTION_AFTER_EMPTY_OCR; not OCR success",
        "native_bundle_validated":True,"joint_policy":"UNRESOLVED_PROPOSAL_ONLY","platform_authority":False,
        "parts":[{"fragment_id":f["fragment_id"],"role":f["role"],"text":t} for f,t in zip(fragments,part_texts)]}
    bundle_ref=put(PRIVATE/"native-source-graph.json",bundle)
    conversion_ref=put(PRIVATE/"conversion-record.json",conversion)
    request={"schema":"A24R1PrivateSourceRequestDraft/v1","status":"SOURCE_READY_CURRENT_TARGET_SCHEMA_AND_AUTHORITY_UNBOUND",
        "candidate_identity":"section2-basic-printed1-viewer14","bundle":bundle,"refs":{"graph":artifact_ref(graph),"policy":policy_ref(policy)},
        "model_binding":{key:{"path":str(MODEL/name),"bytes":(MODEL/name).stat().st_size,"sha256":MODEL_HASHES[name]}
            for key,name in (("reviewed_candidate","reviewed-candidate-v1.json"),("raw_regional","raw-regional-candidates-r1.json"),
                ("input_manifest","model-input-manifest.json"),("result_manifest","fixed-result-r1-no-body-manifest.json"))},
        "native_conversion_ref":conversion_ref,"body_schema_profile":None,"approval":None,
        "current_write_eligible":False,"no_second_manual_save":True}
    request_ref=put(PRIVATE/"request-draft.json",request)
    current=json.loads((ROOT/"docs/evidence/A24/revisions/current-context-r1/live-delivery/raw/current-state.json").read_bytes())
    statics={}
    for event in current["network_audit"]:
        if event["category"]=="STATIC" and event["decision"]=="ALLOW":
            statics[(event["resource_type"],event["path_sha256"])]=None
    plan={"schema":"A24FirstSaveExecutablePlan/v1","task":"A24","book_id":"46007447",
        "candidate_identity":"section2-basic-printed1-viewer14","target_leaf":"dir-1792063578574-g0n3ulsni",
        "insert_after_order":22,"tentative_annotation_order":"23","question_info":{"tishi":"xuanze","tilei":None,"tihao":None},
        "source_actual_final":"dceda09db31487d64654e23dd36ccd3705c740fc","body_admission":"CURRENT_SCHEMA_UNBOUND",
        "readback_strategy":"AUTHORITATIVE_AGGREGATE","business_get_counts":{"baseline":4,"prewrite":3,"get":3,"refresh":3,"reopen":4},
        "bootstrap":{"target":"https://www.usense.com/qieti/annotateUnified","session_paths":["/qieti/api/user_login/profile",
            "/qieti/api/user_login/config/permissions","/qieti/api/user_login/config/teams"],"session_get_per_path_per_context":2,
            "static_path_hashes":[{"kind":k,"path_sha256":h} for k,h in statics],"static_get_per_path_per_document":1,
            "version_path":"/qieti/version.json","version_get_per_context":1,"version_repeat_denial_events":2,
            "passive_book_denial_events":4,"combined_excluded_denial_events":16},
        "limits":{"author_context":1,"reopen_context":1,"author_navigation":2,"reopen_navigation":1,"signature_get":1,
            "object_post":6,"commit_post":1,"login_post":0,"refresh_token_post":0,"credential_config_reads":0,
            "ocr_model_calls":0,"redirects":0,"retries":0,"old_mutations":0,"book_submit":0,"author_seconds":900,"reopen_seconds":900},
        "save_page_status":"PROPOSED_14_173_CURRENT_SOURCE_AND_POSTSAVE_PROOF_REQUIRED",
        "upload_host":"https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com","oss_success_contract":"NATIVE_OBSERVED_HTTP_2XX_NO_SERVER_HOST_KEY_ECHO",
        "model_requirement":"ACTUAL_B_ENTRY_OUTPUT_WITH_EXPLICIT_CONVERSION_AND_APPROVAL","human_text_use":"EVALUATION_ONLY_NO_SECOND_SAVE",
        "old_budgets_restored":False,"other_cases":"HOLD","Q22":"NATURAL_AGGREGATE_ONLY",
        "effect_gate":"No upload/save while current natural export/schema/authoritative all-five-zone coverage, legal fresh inventory/newness, account/savepage/receipt/signature bindings remain unknown",
        "unbound_prewrite_behavior":"Acquire exact book+directory+full frames+natural export once within this new transaction, retain controlled source refs and safe hashes, then stop successors NOT_RUN if schema/coverage still unknown; no fabricated metadata row",
        "current_activation":False,"actual_platform_calls":0}
    from annotation.runtime.live_pilot.authority import validate_plan
    scope_hash=validate_plan(plan)
    plan_ref=put(OUT/"concrete-plan.json",plan)
    summary={"schema":"A24R1ModelNativeBindingSummary/v1","source_model_status":raw_model["status"],
        "fixed_source_hashes":MODEL_HASHES,"all_six_model_input_pixels_match_original_crop_pixels":True,
        "native_bundle_ref":bundle_ref,"private_request_ref":request_ref,"private_conversion_ref":conversion_ref,
        "native_graph_hash":graph["content_hash"],"part_text_hashes":[digest(p) for p in conversion["parts"]],
        "provenance":"Fixed actual OCR plus disclosed coordinator AI visual correction; answer remains non-OCR; no human user content approval claimed",
        "region_source_enum":"HISTORICAL means quoted fixed corrected artifact; does not mean HUMAN or raw OCR",
        "role_policy":"PROPOSAL_ONLY; not joint first-save adoption","scope_sha256":scope_hash,"plan_ref":plan_ref,
        "real_model_calls_by_author":0,"platform_calls":0,"activation_created":False}
    put(OUT/"model-native-binding-summary.json",summary)
    print(json.dumps({"native_graph_validated":True,"question_count":1,"fragments":6,"private_request_sha256":request_ref["sha256"],"scope_sha256":scope_hash,"platform_calls":0}))


if __name__=="__main__": prepare()
