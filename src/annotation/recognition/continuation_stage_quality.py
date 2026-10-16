"""Independent current-reference source and continuation-stage integrity checks.

No prepare/proof/apply producer or assembler is used to manufacture gold.
Original image bytes/capture pixels and actual current graph facts are checked.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import re

from PIL import Image

from .baseline import code_digest,digest,file_digest,load_source,valid_bbox
from .boundary import validate_boundary
from .continuation import validate_continuation
from .continuation_quality import audit_continuation_application
from .image_regions import validate_image_regions
from .recovery_stage_quality import _path,_textsha

SCHEMA = "b-continuation-stage-check-trial/0.1"
POLICY = "CURRENT_REFERENCE_REBUILD_ONLY/0.1"
IDENTITY_POLICY = "CURRENT_REFS_WITH_EXECUTION_TIME_IN_JOURNAL/0.1"
PREFIX = "SOURCE_PREFIX_CROP_ONLY_WITH_BOUNDARY_AND_FIGURES"
_NAMES = ("continuation_fixture","image_review","boundary_review","content_review")
_SCHEMAS = ("b-continuation-fixture-trial/0.1","b-image-review-trial/0.1","b-boundary-review-trial/0.1","b-continuation-content-review-trial/0.1")


def ref(value): return {k:value.get(k)for k in ("artifact_id","revision","content_hash")}
def docref(value): return {"artifact_id":value["artifact_id"],"content_hash":digest(value)}
def _rgb(image): return hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()
def _checked(value,schema=None):
    return (isinstance(value,dict)and isinstance(value.get("artifact_id"),str)and bool(value["artifact_id"])
        and type(value.get("revision"))is int and value["revision"] >= 1 and isinstance(value.get("payload"),dict)
        and value.get("content_hash") == digest(value["payload"])and (schema is None or value.get("schema_version") == schema))
def _common(): return {"decision":"HOLD","transcription_verified":False,"business_acceptance":False,"new_ocr_calls":0,"website_requests":0,"platform_actions":[]}


def semantic_receipt(receipt):
    result = copy.deepcopy(receipt)
    for key in ("package","source"): result[key].pop("file_sha256",None)
    for value in result["documents"].values(): value.pop("file_sha256",None)
    result["receipt_policy"] = "NORMALIZED_TEXT_CONTENT/0.1"
    return result


def inspect_continuation_package(package_path,source_path,adjacent_source_path):
    """Read current originals and all captures, independently of the loader."""
    if adjacent_source_path is None: raise ValueError("adjacent original is required")
    package_path,source_path = Path(package_path),Path(source_path)
    manifest = json.loads(package_path.read_text(encoding="utf-8"))
    source,source_paths = load_source(source_path)
    expected_keys = {"schema_version","artifact_id","book_id","scope_id","extended_scope_id","policy","printed_number","documents","captures","adjacent_source","reviewed_source_answer"}
    if (set(manifest) != expected_keys or manifest.get("schema_version") != "b-continuation-package-trial/0.1"
            or manifest.get("policy") != POLICY or not manifest.get("artifact_id")
            or any(manifest.get(k) != source[k]for k in ("book_id","scope_id"))
            or not manifest.get("extended_scope_id")or manifest["extended_scope_id"] == source["scope_id"]
            or not re.fullmatch(r"[1-9]\d?",str(manifest.get("printed_number","")))or set(manifest.get("documents",{})) != set(_NAMES)):
        raise ValueError("invalid continuation package schema, scope or documents")
    documents,receipts = {},{}
    for name,schema in zip(_NAMES,_SCHEMAS):
        descriptor = manifest["documents"][name]
        if set(descriptor) != {"path","text_sha256","artifact_ref"}: raise ValueError("unbound continuation document")
        path = _path(package_path.parent,descriptor["path"])
        value = json.loads(path.read_text(encoding="utf-8"))
        if (not _checked(value,schema)or ref(value) != descriptor["artifact_ref"]or _textsha(path) != descriptor["text_sha256"]
                or value.get("book_id") != source["book_id"]): raise ValueError("continuation document identity changed")
        documents[name] = value
        receipts[name] = {**descriptor,"file_sha256":file_digest(path)}
    fixture,images,boundary,content = [documents[n]for n in _NAMES]
    data,observed = fixture["payload"],fixture["payload"]["reviewed_scope"]
    adjacent = data["source"]
    assets = [a for a,p in source_paths]
    previous = next((a for a in assets if a["asset_id"] == observed["from_asset_id"]),None)
    if (fixture.get("scope_id") != source["scope_id"]or images.get("scope_id") != manifest["extended_scope_id"]
            or manifest["adjacent_source"] != adjacent or manifest["captures"] != images["payload"]["captures"]
            or adjacent["asset_id"]in {a["asset_id"]for a in assets}or "viewer_page"in adjacent.get("external_refs",{})
            or adjacent["reading_order"] != max(a["reading_order"]for a in assets)+1
            or not previous or previous["sha256"] != observed["from_asset_sha256"]
            or type(observed["from_resource_index"])is not int
            or previous.get("external_refs",{}).get("resource_index") != observed["from_resource_index"]
            or adjacent.get("external_refs",{}).get("resource_index") != observed["from_resource_index"]+1):
        raise ValueError("continuation source scope/resource adjacency changed")
    acquisition = data["acquisition_receipt"]
    if (acquisition.get("method") != "GET"or acquisition.get("status") != 200
            or any(acquisition.get(k) != adjacent[k]for k in ("sha256","width","height"))): raise ValueError("unbound historical acquisition")
    originals = {}
    for asset,path in source_paths:
        with Image.open(path)as image: originals[asset["asset_id"]] = (asset,image.convert("RGB"))
    adjacent_path = Path(adjacent_source_path)
    if file_digest(adjacent_path) != adjacent["sha256"]: raise ValueError("adjacent original bytes changed")
    with Image.open(adjacent_path)as opened:
        if list(opened.size) != [adjacent["width"],adjacent["height"]]: raise ValueError("adjacent dimensions changed")
        originals[adjacent["asset_id"]] = (adjacent,opened.convert("RGB"))
    captures,capture_images,seen_paths = [],{},set()
    for descriptor in manifest["captures"]:
        aid,box = descriptor["asset_id"],descriptor["source_bbox"]
        if aid in capture_images or descriptor["path"]in seen_paths or aid not in originals: raise ValueError("capture identity duplicated/unknown")
        asset,original = originals[aid]
        path = _path(package_path.parent,descriptor["path"])
        if (descriptor["source_sha256"] != asset["sha256"]or descriptor["source_size"] != list(original.size)
                or not valid_bbox(box,*original.size)or any(type(v)is not int for v in box)
                or file_digest(path) != descriptor["sha256"]): raise ValueError("capture descriptor/hash changed")
        with Image.open(path)as opened: crop = opened.convert("RGB")
        expected = original.crop(box)
        if crop.size != expected.size or crop.tobytes() != expected.tobytes()or _rgb(crop) != descriptor["rgb_sha256"]:
            raise ValueError("capture differs from actual original source pixels")
        captures.append({"asset_id":aid,"path":descriptor["path"],"file_sha256":file_digest(path),"source_sha256":asset["sha256"],
            "source_bbox":list(box),"source_size":list(original.size),"rgb_sha256":_rgb(crop),"source_crop_rgb_sha256":_rgb(expected),"crop_size":list(crop.size)})
        capture_images[aid] = (descriptor,crop);seen_paths.add(descriptor["path"])
    crop = data["crop"];box,scale = crop["source_bbox"],crop["ocr_scale"]
    if (not isinstance(scale,(int,float))or isinstance(scale,bool)or not math.isfinite(scale)or scale <= 0
            or crop["crop_to_original"] != [[1/scale,0,box[0]],[0,1/scale,box[1]],[0,0,1]]
            or [crop["width"],crop["height"]] != [box[2]-box[0],box[3]-box[1]]
            or not any(c["asset_id"] == adjacent["asset_id"]and c["path"] == crop["path"]and c["file_sha256"] == crop["sha256"]and c["source_bbox"] == box for c in captures)):
        raise ValueError("prefix crop/transform changed")
    seen,lines = set(),{}
    windows = [observed["window"],observed["hard_boundary_window"]]
    for line in data["ocr_lines"]:
        lid,location = line["line_id"],line.get("location",{})
        index = location.get("window_index")
        if (not isinstance(lid,str)or not lid or lid in seen or not isinstance(line.get("text"),str)or not line["text"]
                or not valid_bbox(line["bbox"],adjacent["width"],adjacent["height"])
                or line["bbox"] != [round(line["engine_bbox"][i]/scale+box[i%2],3)for i in range(4)]
                or type(index)is not int or not 0 <= index < len(windows)
                or location.get("column") != windows[index]["column"]or location.get("section_path") != windows[index]["path"]):
            raise ValueError("prefix OCR source/geometry/window changed")
        seen.add(lid);lines[lid] = line
    snapshot = manifest["reviewed_source_answer"]
    if (snapshot.get("asset_id") != observed["from_asset_id"]or snapshot.get("section_path") != observed["section_path"]
            or snapshot.get("printed_number") != manifest["printed_number"]or snapshot.get("assembly_status") != "OPEN"
            or snapshot.get("boundary",{}).get("kind") != "ANSWER_PAGE_EDGE"):
        raise ValueError("source snapshot is not the reviewed open tail")
    cp = content["payload"]
    if (content.get("scope_id") != manifest["extended_scope_id"]
            or cp.get("asset") != {k:adjacent[k]for k in ("asset_id","sha256","width","height")}
            or cp.get("capture") != {k:crop[k]for k in ("path","sha256","source_bbox","width","height")}
            or cp.get("reference_quality")not in {"MODEL_VISUAL_DEVELOPMENT_REVIEW","SYNTHETIC_TEST"}
            or any(cp.get(k)is not False for k in ("human_verified","transcription_verified","business_acceptance"))or cp.get("platform_actions") != []):
        raise ValueError("content review source or provenance changed")
    cases = set()
    for case in cp.get("line_checks",[]):
        line = lines.get(case["line_id"]);region = case["review_region_bbox"]
        if (case["case_id"]in cases or not line or case["asset_id"] != adjacent["asset_id"]or case["source_sha256"] != adjacent["sha256"]
                or case["raw_text"] != line["text"]or case["line_bbox"] != line["bbox"]
                or case["raw_text_sha256"] != hashlib.sha256(line["text"].encode()).hexdigest()
                or not valid_bbox(region,adjacent["width"],adjacent["height"])or any(type(v)is not int for v in region)
                or any(not box[i%2] <= region[i] <= box[2+i%2]for i in range(4))
                or not (region[0] <= line["bbox"][0] <= line["bbox"][2] <= region[2]and region[1] <= line["bbox"][1] <= line["bbox"][3] <= region[3])
                or case.get("reference_quality") != cp["reference_quality"]or case.get("human_verified")is not False or case.get("business_acceptance")is not False):
            raise ValueError("content review line/region is not bound to source")
        actual_region = originals[adjacent["asset_id"]][1].crop(region)
        if _rgb(actual_region) != case["review_region_rgb_sha256"]: raise ValueError("content review source pixels changed")
        for difference in case["differences"]:
            lo,hi = difference["raw_text_span"]
            if (type(lo)is not int or type(hi)is not int or not 0 <= lo < hi <= len(line["text"])
                    or line["text"][lo:hi] != difference["raw_fragment"]or not difference.get("observed_source_fragment")):
                raise ValueError("content review does not retain exact original raw text span")
        cases.add(case["case_id"])
    receipt = {"book_id":manifest["book_id"],"scope_id":manifest["scope_id"],"extended_scope_id":manifest["extended_scope_id"],
        "package":{"file_sha256":file_digest(package_path),"text_sha256":_textsha(package_path),"reference":docref(manifest)},
        "documents":receipts,"source":{"file_sha256":file_digest(source_path),"text_sha256":_textsha(source_path),"reference":docref(source)},
        "source_assets":assets,"adjacent_source":{"file_sha256":file_digest(adjacent_path),"asset":adjacent},"captures":captures}
    return {"manifest":manifest,"documents":documents,"receipt":receipt}


def _producer(operation):
    names = ("baseline","offline","answer_assembly","policy","continuation","continuation_apply","continuation_quality","image_regions","boundary")
    return {"module":"annotation.recognition.continuation_stage","version":"0.1.0", "code_sha256":code_digest(Path(__file__).with_name("continuation_stage.py")),
        "dependency_code_sha256":{name:code_digest(Path(__file__).with_name(name+".py"))for name in names},
        "operation":operation,"policy":POLICY,"identity_policy":IDENTITY_POLICY,"new_ocr_calls":0,"website_requests":0}


def _header(value,schema,kind,operation,book,scope,run,inputs,emit,revision=1,extra=None):
    if (not _checked(value,schema)or value.get("kind") != kind or value.get("producer") != _producer(operation)
            or any(value.get(k) != v for k,v in (("book_id",book),("scope_id",scope),("run_id",run),("revision",revision),("input_refs",inputs)))
            or "created_at"in value): emit("CONTINUATION_STAGE_HEADER_MISMATCH",kind)
    body = {k:v for k,v in value.items()if k not in {"artifact_id","content_hash","created_at"}}
    keys = {"schema_version","kind","revision","book_id","scope_id","run_id","input_refs","producer","payload"}|set(extra or {})
    if (set(body) != keys or value.get("artifact_id") != kind.lower()+"-"+digest(body)[:24]
            or any(value.get(k) != v for k,v in (extra or {}).items())): emit("CONTINUATION_STAGE_IDENTITY_MISMATCH",kind)


def _report(kind,values,issues,summary):
    source = values[0]if values else{}
    payload = {"accepted":not issues,"issues":issues,"summary":summary,**_common()}
    inputs = [ref(value)for value in values if isinstance(value,dict)]
    producer = {"module":__name__,"version":"0.1.0","code_sha256":code_digest(Path(__file__))}
    return {"schema_version":SCHEMA,"kind":kind,"artifact_id":kind.lower()+"-"+digest([inputs,payload,producer])[:24],"revision":1,
        **{k:source.get(k)for k in ("book_id","scope_id","run_id")},"input_refs":inputs,"producer":producer,"content_hash":digest(payload),"payload":payload}


def _collector():
    issues = []
    def emit(code,detail=None):
        item = {"code":code,"severity":"ERROR","detail":detail}
        if item not in issues: issues.append(item)
    return issues,emit


def _scope(base_evidence,base_graph,scope,package):
    issues,emit = _collector()
    m,docs,r = package["manifest"],package["documents"],package["receipt"]
    f = docs["continuation_fixture"];data,observed = f["payload"],f["payload"]["reviewed_scope"]
    p = scope["payload"];e,g = p["evidence"],p["graph"]
    run = "b-continuation-run-"+digest([ref(base_evidence),ref(base_graph),r["package"]["reference"]])[:24]
    _header(scope,"b-continuation-scope-trial/0.1","ContinuationScopeTrial","PREPARE_SCOPE",m["book_id"],m["extended_scope_id"],run,
        [ref(base_evidence),ref(base_graph),r["package"]["reference"]],emit)
    # These independent source/fragment checks never run the assembler.
    from .pipeline_quality import _source_evidence,_graph_sources
    source = {"book_id":m["book_id"],"scope_id":m["scope_id"],"assets":r["source_assets"]}
    units = _source_evidence(base_evidence,source,base_evidence["payload"]["context"],lambda code,**kw:emit(code,kw.get("detail")))
    _graph_sources(base_evidence,base_graph,units,lambda code,**kw:emit(code,kw.get("detail")))
    if base_evidence["scope_id"] != m["scope_id"]or "continuation_scope_extension"in base_evidence["payload"]:
        emit("CONTINUATION_CURRENT_BASE_SCOPE_MISMATCH")
    selector = m["reviewed_source_answer"]
    selected = [a for a in base_graph["payload"]["answers"]if all(a.get(k) == selector[k]for k in ("asset_id","section_path","printed_number"))]
    if len(selected) != 1: raise ValueError("source answer missing or ambiguous")
    answer = selected[0]
    source_lines = {l["line_id"]:l for page in base_evidence["payload"]["pages"]for l in page["ocr_lines"]}
    actual_snapshot = {k:copy.deepcopy(answer[k])for k in ("asset_id","section_path","printed_number","source_line_ids","assembly_status","boundary")}
    actual_snapshot.update(anchor_ref=answer["source_line_ids"][0],source_tail_line_id=answer["source_line_ids"][-1],
        raw_lines=[source_lines[lid]for lid in answer["source_line_ids"]],
        fragments=[{k:v for k,v in fragment.items()if k != "fragment_id"}for fragment in answer["fragments"]])
    if actual_snapshot != selector: emit("CONTINUATION_SOURCE_SNAPSHOT_MISMATCH")
    ep,bp = e["payload"],base_evidence["payload"]
    expected_new_page = {"asset_id":data["source"]["asset_id"],"source":data["source"],"page_role":"answer",
        "layout":{"mode":"two_columns","cut_x":data["source"]["width"]/2,"method":"REVIEWED_PREFIX_CROP_ONLY","verified":False},
        "ocr_lines":data["ocr_lines"],"answer_detail_lines":[],"unscoped_line_ids":[],"coverage_scope":PREFIX,"crop_provenance":data["crop"]}
    if ep["pages"] != bp["pages"]+[expected_new_page]: emit("CONTINUATION_EXTENDED_SOURCE_PROJECTION_MISMATCH")
    context = copy.deepcopy(bp["context"])
    context["artifact_id"] = "continuation-context-"+digest([docref(context),ref(f),m["extended_scope_id"]])[:24]
    context["scope_id"] = m["extended_scope_id"]
    context["pages"][data["source"]["asset_id"]] = {"sha256":data["source"]["sha256"],"role":"answer","windows":[observed["window"],observed["hard_boundary_window"]]}
    extension = {"fixture_ref":ref(f),"package_ref":r["package"]["reference"],"original_page_count":len(bp["pages"]),"new_asset_id":data["source"]["asset_id"],
        "base_evidence_ref":ref(base_evidence),"base_graph_ref":ref(base_graph),"coverage_scope":PREFIX,
        "scope":"Actual adjacent resource prefix only; full-page OCR and viewer mapping are not asserted."}
    if (ep.get("context") != context or ep.get("continuation_scope_extension") != extension
            or {k:v for k,v in ep.items()if k not in {"pages","context","continuation_scope_extension"}} != {k:v for k,v in bp.items()if k not in {"pages","context"}}):
        emit("CONTINUATION_ORIGINAL_EVIDENCE_CHANGED")
    _header(e,"b-evidence-trial/0.3","EvidenceBundleTrial","PREPARE_EVIDENCE_SCOPE",m["book_id"],m["extended_scope_id"],run,
        [ref(base_evidence),ref(base_graph),ref(f),r["package"]["reference"]],emit,base_evidence["revision"]+1)
    extra_rows = [{"asset_id":data["source"]["asset_id"],"line_id":line["line_id"],"status":"UNASSIGNED"if line["location"]["window_index"] == 0 else"EXCLUDED",
        "answer_ids":[],"fragment_ids":[],"allocations":[],"reason":"REVIEWED_CROSS_PAGE_PREFIX_PENDING_PROOF"if line["location"]["window_index"] == 0 else"OBSERVED_NEXT_SECTION_HEADING"}for line in data["ocr_lines"]]
    expected_g_extension = {"fixture_ref":ref(f),"package_ref":r["package"]["reference"],"original_entities_preserved":True,"graph_merge_performed":False}
    gp,bg = g["payload"],base_graph["payload"]
    if (gp.get("answer_coverage") != bg["answer_coverage"]+extra_rows or gp.get("continuation_scope_extension") != expected_g_extension
            or {k:v for k,v in gp.items()if k not in {"answer_coverage","continuation_scope_extension"}} != {k:v for k,v in bg.items()if k != "answer_coverage"}):
        emit("CONTINUATION_ORIGINAL_GRAPH_CHANGED")
    _header(g,"b-graph-trial/0.3","QuestionGraphTrial","PREPARE_GRAPH_SCOPE",m["book_id"],m["extended_scope_id"],run,[ref(e)],emit,base_graph["revision"]+1,
        {"derivation_refs":[ref(base_graph),ref(f),r["package"]["reference"]]})
    source_scope = {"base_scope_id":base_evidence["scope_id"],"extended_scope_id":m["extended_scope_id"],"base_source_ref":r["source"]["reference"],
        "base_assets":r["source_assets"],"adjacent_asset":data["source"],"base_page_count":len(bp["pages"]),"observed_asset_count":len(ep["pages"]),
        "adjacent_ocr_coverage":PREFIX,"adjacent_crop_bbox":data["crop"]["source_bbox"],"full_page_ocr_claimed":False}
    expected = {"evidence":e,"graph":g,"base_evidence_ref":ref(base_evidence),"base_graph_ref":ref(base_graph),"base_evidence_archive":base_evidence,
        "base_graph_archive":base_graph,"package_receipt":semantic_receipt(r),"source_scope":source_scope,**_common()}
    if p != expected: emit("CONTINUATION_SCOPE_ARCHIVE_OR_RECEIPT_MISMATCH")
    return _report("ContinuationScopeCheckTrial",[scope],issues,{"source_assets":len(ep["pages"]),"added_raw_lines":len(data["ocr_lines"]),"original_entities_preserved":gp.get("questions") == bg.get("questions")and gp.get("answers") == bg.get("answers")})


def _safe(kind,values,operation):
    try: return operation()
    except (OSError,ValueError,TypeError,KeyError,AttributeError,IndexError,OverflowError,RecursionError,StopIteration,ZeroDivisionError)as exc:
        return _report(kind,values,[{"code":"CONTINUATION_STAGE_DATA_INVALID","severity":"ERROR","detail":type(exc).__name__+": "+str(exc)}],{})


def audit_continuation_scope(base_evidence,base_graph,scope,package_path,source_path,adjacent_source_path):
    return _safe("ContinuationScopeCheckTrial",[scope],lambda:_scope(base_evidence,base_graph,scope,inspect_continuation_package(package_path,source_path,adjacent_source_path)))


def _proof(scope,stage,package):
    issues,emit = _collector()
    p = scope["payload"];e,g = p["evidence"],p["graph"]
    docs,r = package["documents"],package["receipt"]
    m = package["manifest"];data = docs["continuation_fixture"]["payload"];snapshot = m["reviewed_source_answer"]
    expected_scope = _scope(p["base_evidence_archive"],p["base_graph_archive"],scope,package)
    if not expected_scope["payload"]["accepted"]: emit("CONTINUATION_PROOF_SCOPE_REJECTED",expected_scope["payload"]["issues"])
    _header(stage,"b-continuation-proof-stage-trial/0.1","ContinuationProofStageTrial","REBUILD_PROOF",e["book_id"],e["scope_id"],e["run_id"],
        [ref(scope),ref(e),ref(g),r["package"]["reference"]],emit)
    sp = stage["payload"];proof = sp["proof"]
    root = Path(package["package_path"]).parent
    image_check = validate_image_regions(e,sp["image_regions"],docs["image_review"],root)
    boundary_check = validate_boundary(e,sp["boundary_candidate"])
    check = validate_continuation(e,g,proof,image_review=docs["image_review"],capture_root=root)
    for label,value in (("images",image_check),("boundary",boundary_check),("proof",check)):
        if not value["payload"].get("accepted"): emit("CONTINUATION_PROOF_EVIDENCE_REJECTED",{label:value["payload"]["issues"]})
    if (sp.get("image_check") != image_check or sp.get("boundary_check") != boundary_check or sp.get("continuation_check") != check):
        emit("CONTINUATION_PROOF_VALIDATION_RECEIPT_MISMATCH")
    h = docs["boundary_review"]["payload"];bc = sp["boundary_candidate"]["payload"]
    if (bc.get("source_bbox") != h["source_bbox"]or bc.get("asset",{}).get("asset_id") != h["asset"]["asset_id"]
            or [dict(line_id=x["line_id"],text_span=x["text_span"])for x in bc.get("members",[])] != h["line_spans"]):
        emit("CONTINUATION_FROZEN_HEADING_MISMATCH")
    selected = next(a for a in g["payload"]["answers"]if all(a.get(k) == snapshot[k]for k in ("asset_id","section_path","printed_number")))
    prefix = sorted((line for line in data["ocr_lines"]if line["location"]["window_index"] == 0),key=lambda line:(line["bbox"][1],line["bbox"][0],line["line_id"]))
    pp = proof["payload"]
    if (pp.get("from_answer_id") != selected["answer_id"]or pp.get("source_tail_line_id") != snapshot["source_tail_line_id"]
            or pp.get("to_line_ids") != [l["line_id"]for l in prefix]or pp.get("to_asset",{}).get("asset_id") != data["source"]["asset_id"]
            or pp.get("image_regions") != sp["image_regions"]or pp.get("boundary_candidate") != sp["boundary_candidate"]
            or pp.get("adjacency_receipt") != sp["adjacency_receipt"]): emit("CONTINUATION_PROOF_CURRENT_SELECTION_MISMATCH")
    expected = {"scope_ref":ref(scope),"evidence_ref":ref(e),"graph_ref":ref(g),"package_receipt":semantic_receipt(r),"source_scope":p["source_scope"],
        "adjacency_receipt":sp["adjacency_receipt"],"image_regions":sp["image_regions"],"image_check":image_check,"boundary_candidate":sp["boundary_candidate"],
        "boundary_check":boundary_check,"proof":proof,"continuation_check":check,**_common()}
    if sp != expected: emit("CONTINUATION_PROOF_STAGE_BINDING_MISMATCH")
    return _report("ContinuationProofStageCheckTrial",[stage],issues,{"target_lines":len(prefix),"validated_images":len(image_check["payload"].get("validated_regions",[]))})


def audit_continuation_proof_stage(scope,proof_stage,package_path,source_path,adjacent_source_path):
    def run():
        package = inspect_continuation_package(package_path,source_path,adjacent_source_path);package["package_path"] = str(package_path)
        return _proof(scope,proof_stage,package)
    return _safe("ContinuationProofStageCheckTrial",[proof_stage],run)


def _apply(scope,proof_stage,stage,package):
    issues,emit = _collector();p = scope["payload"];e,g = p["evidence"],p["graph"];docs,r = package["documents"],package["receipt"]
    proof_check = _proof(scope,proof_stage,package)
    if not proof_check["payload"]["accepted"]: emit("CONTINUATION_APPLY_PROOF_STAGE_REJECTED",proof_check["payload"]["issues"])
    _header(stage,"b-continuation-apply-stage-trial/0.1","ContinuationApplyStageTrial","APPLY_LOCAL",e["book_id"],e["scope_id"],e["run_id"],
        [ref(scope),ref(proof_stage),r["package"]["reference"]],emit)
    sp = stage["payload"];graph = sp["graph"];proof = proof_stage["payload"]["proof"]
    check = audit_continuation_application(e,g,graph,proof,image_review=docs["image_review"],capture_root=Path(package["package_path"]).parent)
    if not check["payload"]["accepted"]: emit("CONTINUATION_APPLICATION_REJECTED",check["payload"]["issues"])
    rp = {"evidence_ref":ref(e),"base_graph_ref":ref(g),"derived_graph_ref":ref(graph),"proof_ref":ref(proof),"decision":"HOLD","platform_actions":[]}
    receipt = {"schema_version":"b-continuation-application-receipt-trial/0.1","kind":"LocalContinuationApplicationReceiptTrial",
        "artifact_id":"local-application-receipt-"+digest(rp)[:24],"revision":1,"book_id":e["book_id"],"scope_id":e["scope_id"],"content_hash":digest(rp),"payload":rp}
    expected = {"scope_ref":ref(scope),"proof_stage_ref":ref(proof_stage),"evidence_ref":ref(e),"base_graph_ref":ref(g),"graph":graph,
        "application_receipt":receipt,"application_check":check,"rollback_verification":{"restored_equals_original":True,"restored_graph_ref":ref(g),"restored_complete_object_sha256":digest(g)},
        "package_receipt":semantic_receipt(r),"source_scope":p["source_scope"],**_common()}
    if sp != expected or "created_at"in graph: emit("CONTINUATION_APPLICATION_STAGE_BINDING_MISMATCH")
    return _report("ContinuationApplyStageCheckTrial",[stage],issues,{"application_accepted":check["payload"]["accepted"],**check["payload"].get("summary",{})})


def audit_continuation_apply_stage(scope,proof_stage,apply_stage,package_path,source_path,adjacent_source_path):
    def run():
        package = inspect_continuation_package(package_path,source_path,adjacent_source_path);package["package_path"] = str(package_path)
        return _apply(scope,proof_stage,apply_stage,package)
    return _safe("ContinuationApplyStageCheckTrial",[apply_stage],run)


def _continued_review(review,scope,proof_stage,package):
    """Independent review projection from the frozen raw source snapshots."""
    manifest,fixture = package["manifest"],package["documents"]["continuation_fixture"]
    snapshot = manifest["reviewed_source_answer"]
    source_lines = {x["line_id"]:x for x in snapshot["raw_lines"]}
    target_lines = {x["line_id"]:x for x in fixture["payload"]["ocr_lines"]}
    targets = proof_stage["payload"]["proof"]["payload"]["to_line_ids"]
    spans = {}
    for fragment in snapshot["fragments"]:
        for line in fragment["evidence_refs"]: spans.setdefault(line,[]).append(fragment["text_span"])
    expectations = []
    for line,values in spans.items():
        expectations.append({"line_id":line,"source_text_sha256":hashlib.sha256(source_lines[line]["text"].encode()).hexdigest(),"text_spans":sorted(values)})
    for line in targets:
        text = target_lines[line]["text"]
        expectations.append({"line_id":line,"source_text_sha256":hashlib.sha256(text.encode()).hexdigest(),"text_spans":[[0,len(text)]]})
    assets = {asset["asset_id"]:asset["sha256"]for asset in package["receipt"]["source_assets"]+[fixture["payload"]["source"]]
              if asset["asset_id"]in {snapshot["asset_id"],fixture["payload"]["source"]["asset_id"]}}
    case = {"case_id":"continued-answer-"+digest([docref(manifest),ref(fixture)])[:24],"asset_sha256":assets,
        "section_path":snapshot["section_path"],"printed_number":snapshot["printed_number"],
        "expected_source_line_ids":snapshot["source_line_ids"]+targets,"expected_source_spans":expectations,
        "reference_quality":fixture["payload"]["reviewed_scope"]["reference_quality"],"human_verified":False,"business_acceptance":False}
    expected = copy.deepcopy(review);expected["scope_id"] = scope["scope_id"]
    expected["multiline_checks"] = expected.get("multiline_checks",[])+[case]
    expected["artifact_id"] = "continued-review-"+digest([docref(review),ref(scope),ref(proof_stage),case])[:24]
    basis = {"input_review_ref":docref(review),"scope_ref":ref(scope),"fixture_ref":ref(fixture),"frozen_source_snapshot_sha256":digest(snapshot),
        "proof_ref":ref(proof_stage["payload"]["proof"]),"source_line_ids":snapshot["source_line_ids"],"target_line_ids":targets,
        "expected_text_from_current_graph":False,"business_acceptance":False}
    return expected,basis


def _continued(scope,proof_stage,apply_stage,review,checked,package):
    from .answer_quality import audit_answers
    from .question_quality import audit_questions
    from .recovery_quality import audit_recovery
    from .offline import scope_key,scalar_issues
    issues,emit = _collector()
    sp = scope["payload"];e,g = sp["evidence"],apply_stage["payload"]["graph"]
    checks = [_scope(sp["base_evidence_archive"],sp["base_graph_archive"],scope,package),
              _proof(scope,proof_stage,package),_apply(scope,proof_stage,apply_stage,package)]
    if not all(c["payload"]["accepted"]for c in checks): emit("CONTINUED_STAGE_INTEGRITY_REJECTED",[c["payload"]["issues"]for c in checks])
    if (review.get("schema_version") != "b-review-trial/0.1"or review.get("book_id") != e["book_id"]
            or review.get("scope_id") != sp["base_evidence_archive"]["scope_id"]): emit("CONTINUED_INPUT_REVIEW_INVALID")
    p = checked["payload"]
    names = ("question_quality","answer_quality","recovery_quality","continuation_stage_quality","continuation_quality","offline")
    producer = {"module":"annotation.recognition.continued_quality","version":"0.1.0","code_sha256":code_digest(Path(__file__).with_name("continued_quality.py")),
        "dependency_code_sha256":{n:code_digest(Path(__file__).with_name(n+".py"))for n in names},
        "identity_policy":IDENTITY_POLICY,"new_ocr_calls":0,"website_requests":0}
    inputs = [ref(scope),ref(proof_stage),ref(apply_stage),docref(review),package["receipt"]["package"]["reference"],ref(e),ref(g)]
    body = {k:v for k,v in checked.items()if k not in {"artifact_id","content_hash"}}
    if (not _checked(checked,"b-check-trial/0.4")or checked.get("kind") != "CheckReportTrial"
            or set(body) != {"schema_version","kind","revision","book_id","scope_id","run_id","input_refs","producer","payload"}
            or checked.get("artifact_id") != "checkreporttrial-"+digest(body)[:24]or checked.get("producer") != producer
            or checked.get("input_refs") != inputs or checked.get("revision") != 1
            or any(checked.get(k) != e[k]for k in ("book_id","scope_id","run_id"))): emit("CONTINUED_CHECK_HEADER_OR_IDENTITY_MISMATCH")
    derived,basis = _continued_review(review,scope,proof_stage,package)
    if (p.get("input_review_archive") != review or p.get("derived_review") != derived
            or p.get("input_review_ref") != docref(review)or p.get("derived_review_ref") != docref(derived)
            or p.get("review_migration_basis") != basis): emit("CONTINUED_REVIEW_SOURCE_PROJECTION_MISMATCH")
    question_findings,coverage = audit_questions(e,g,derived,scope_key=scope_key,scalar_issues=scalar_issues)
    answer_findings,metrics = audit_answers(e,g,derived)
    recovery_findings,recovery_metrics = audit_recovery(sp["base_evidence_archive"],g)
    metrics.update(recovery_metrics)
    aid = proof_stage["payload"]["proof"]["payload"]["from_answer_id"]
    headings = set(proof_stage["payload"]["boundary_check"]["payload"]["boundary"]["line_ids"])
    expected_findings,dispositions = list(question_findings),[]
    for item in answer_findings:
        is_typed_legacy = item["scope_id"] == aid and item["code"]in {"ANSWER_AGGREGATE_TEXT_MISMATCH","ANSWER_REGIONS_MISMATCH","ANSWER_REGION_PROJECTION_MISMATCH"}
        is_proven_heading = item["code"] == "ANSWER_EXCLUSION_WITHOUT_EVIDENCE"and bool(item["evidence_refs"])and set(item["evidence_refs"]) <= headings
        if is_typed_legacy or is_proven_heading:
            dispositions.append({"finding":item,"status":"SUPERSEDED_PRESENTATION_RULE","replacement_check_ref":ref(checks[2]),"boundary_check_ref":ref(proof_stage["payload"]["boundary_check"])})
        else: expected_findings.append(item)
    expected_findings.extend(recovery_findings)
    def add(code,scope_id,refs=(),detail=None):
        expected_findings.append(dict(code=code,scope_id=scope_id,evidence_refs=list(refs),severity="REVIEW",detail=detail))
    for item in g["payload"]["issues"]:
        if item["code"] == "UNASSIGNED_ANSWER_OCR_LINE": continue
        if item.get("answer_id") == aid and item["code"] == "ANSWER_BOUNDARY_UNRESOLVED"and item.get("status") == "RESOLVED_STRUCTURAL_BOUNDARY":
            dispositions.append({"finding":item,"status":"RESOLVED_STRUCTURAL_BOUNDARY","replacement_check_ref":ref(checks[2]),"boundary_check_ref":ref(proof_stage["payload"]["boundary_check"])})
        else: add(item["code"],item.get("answer_id",e["scope_id"]),item["evidence_refs"],item.get("detail"))
    content = package["documents"]["content_review"]
    for case in content["payload"]["line_checks"]:
        add("CONTINUATION_DEVELOPMENT_TRANSCRIPTION_DISAGREEMENT",aid,[case["line_id"]],
            {"case_id":case["case_id"],"content_review_ref":ref(content),"raw_text":case["raw_text"],"observed_text":case["observed_text"],
             "differences":case["differences"],"reference_quality":"MODEL_VISUAL_DEVELOPMENT_REVIEW","human_verified":False,"ocr_corrected":False})
    target = proof_stage["payload"]["proof"]["payload"]["to_line_ids"]
    add("CONTINUATION_PARTIAL_ADJACENT_PAGE_OCR",e["scope_id"],target,sp["source_scope"])
    add("CONTINUATION_TYPED_CONTENT_UNVERIFIED",aid,target,{"body_transcription_verified":False,"image_semantics_verified":False,"source_pixels_verified_only":True})
    add("BUSINESS_REVIEW_REQUIRED",e["scope_id"],detail="Development source reviews and shared OCR are not independent business acceptance.")
    pages = {page["asset_id"]for page in e["payload"]["pages"]}
    expected_issues = []
    for f in expected_findings:
        expected_issues.append({"issue_id":"issue-"+digest([f["code"],f["scope_id"],f["evidence_refs"],f["detail"]])[:24],**f,
            "scope_type":"question"if f["scope_id"].startswith("q-")else"answer"if f["scope_id"].startswith("a-")else"asset"if f["scope_id"]in pages else"scope",
            "blocks":["PRE_APPLY"],"suggested_strategy":"REVIEW_OFFLINE"})
    if p.get("issues") != expected_issues: emit("CONTINUED_CURRENT_FINDINGS_MISMATCH")
    if p.get("rule_dispositions") != dispositions: emit("CONTINUED_RULE_SUPERSESSION_MISMATCH")
    expected_summary = {"questions":len(g["payload"]["questions"]),"answers":len(g["payload"]["answers"]),
        "unique_candidate_links":sum(q["selected_answer_id"]is not None for q in g["payload"]["questions"]),"issues":len(expected_issues),
        "source_assets":len(pages),"continuation_target_lines":len(target),"development_content_disagreements":len(content["payload"]["line_checks"]),**metrics}
    if p.get("summary") != expected_summary or p.get("page_coverage") != coverage: emit("CONTINUED_CURRENT_CENSUS_MISMATCH")
    expected_basis = {"current_question_census_matching_scalar_rules":True,"current_answer_source_span_owner_ledger_rules":True,
        "recovery_source_evidence_ref":ref(sp["base_evidence_archive"]),"recovery_graph_ref":ref(g),"typed_application_check_ref":ref(checks[2]),
        "adjacent_full_page_ocr":False,"business_acceptance":False}
    bindings = {"stage":"PRE_APPLY","scope_ref":ref(scope),"proof_stage_ref":ref(proof_stage),"apply_stage_ref":ref(apply_stage),"evidence_ref":ref(e),"graph_ref":ref(g),
        "package_receipt":semantic_receipt(package["receipt"]),"stage_integrity_checks":checks,"basis":expected_basis,**_common()}
    if any(p.get(k) != value for k,value in bindings.items()): emit("CONTINUED_CHECK_BINDING_OR_ACCEPTANCE_MISMATCH")
    allowed = set(bindings)|{"input_review_ref","input_review_archive","derived_review","derived_review_ref","review_migration_basis","rule_dispositions","issues","page_coverage","summary"}
    if set(p) != allowed: emit("CONTINUED_CHECK_UNKNOWN_FIELDS")
    return _report("ContinuedQualityCheckTrial",[checked],issues,{"current_issues":len(expected_issues),"business_acceptance":False,"source_assets":len(pages)})


def audit_continued_quality(scope,proof_stage,apply_stage,review,checked,*,package_path,source_path,adjacent_source_path):
    def run():
        package = inspect_continuation_package(package_path,source_path,adjacent_source_path);package["package_path"] = str(package_path)
        return _continued(scope,proof_stage,apply_stage,review,checked,package)
    return _safe("ContinuedQualityCheckTrial",[checked],run)
