"""Independent source-pixel audit of recovery-package and review migrations.

Historical envelopes remain historical. A matching page SHA cannot substitute
for identical complete base payloads. No recovery/assembly producer is imported
or called, and no new OCR or business verification is claimed.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path,PurePosixPath,PureWindowsPath
import re

import numpy as np
from PIL import Image,ImageEnhance

from .baseline import code_digest,digest,file_digest,load_source,valid_bbox

SCHEMA = "b-recovery-stage-check-trial/0.1"
POLICY = "EXACT_PAYLOAD_EQUIVALENCE_ONLY/0.1"
IDENTITY_POLICY = "REFERENCE_BOUND_EXECUTION_TIME_IN_JOURNAL/0.1"


def _ref(value):
    return {k:value.get(k)for k in ("artifact_id","revision","content_hash")}


def _docref(value):
    return {"artifact_id":value["artifact_id"],"content_hash":digest(value)}


def _textsha(path):
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def _pixels(image):
    return hashlib.sha256(np.asarray(image,dtype="uint8").tobytes()).hexdigest()


def _path(root,relative):
    if (not isinstance(relative,str)or not relative or "\\"in relative or PurePosixPath(relative).is_absolute()
            or PureWindowsPath(relative).drive or ".."in PurePosixPath(relative).parts):
        raise ValueError("recovery paths must be portable and inside the package")
    result = (root/relative).resolve()
    if not result.is_relative_to(root.resolve())or not result.is_file():
        raise ValueError("recovery file missing or escapes package")
    return result


def _checked(value,schema,kind):
    return (isinstance(value,dict)and value.get("schema_version") == schema and value.get("kind") == kind
            and type(value.get("revision"))is int and value["revision"] >= 1
            and isinstance(value.get("payload"),dict)and value.get("content_hash") == digest(value["payload"]))


def _finish(kind,inputs,source,issues,summary):
    payload = {"accepted":not issues,"decision":"HOLD","issues":issues,"summary":summary,
               "transcription_verified":False,"business_acceptance":False,"new_ocr_calls":0,"platform_actions":[]}
    producer = {"module":__name__,"version":"0.1.0","code_sha256":code_digest(Path(__file__))}
    return {"schema_version":SCHEMA,"kind":kind,"artifact_id":kind.lower()+"-"+digest([inputs,payload,producer])[:24],
            "revision":1,"book_id":source.get("book_id"),"scope_id":source.get("scope_id"),"run_id":source.get("run_id"),
            "input_refs":inputs,"producer":producer,"content_hash":digest(payload),"payload":payload}


def _output_header(value,schema,kind,source,inputs,emit):
    producer = {"module":"annotation.recognition.recovery_stage","version":"0.1.0",
        "code_sha256":code_digest(Path(__file__).with_name("recovery_stage.py")),
        "recovery_apply_code_sha256":code_digest(Path(__file__).with_name("recovery_apply.py")),
        "policy":POLICY,"new_ocr_calls":0,"identity_policy":IDENTITY_POLICY}
    identity_source = {"book_id":source["book_id"],"scope_id":source["scope_id"],"identity_ref":_ref(source)}
    if source.get("run_id"): identity_source["run_id"] = source["run_id"]
    identity = digest({"schema":schema,"source":identity_source,"payload":value["payload"],"inputs":inputs,"producer":producer})
    if (value.get("producer") != producer or value.get("artifact_id") != kind.lower()+"-"+identity[:24]
            or value.get("revision") != 1 or "created_at"in value):
        emit("RECOVERY_OUTPUT_PRODUCER_OR_IDENTITY_MISMATCH")


def _content_receipt(receipt):
    """Semantic lineage excludes platform-dependent JSON newline bytes only."""
    result = copy.deepcopy(receipt)
    result["package"].pop("file_sha256",None)
    for document in result["documents"].values(): document.pop("file_sha256",None)
    result["receipt_policy"] = "NORMALIZED_TEXT_CONTENT/0.1"
    return result


def _load_package(source_path,package_path,emit):
    source,resolved = load_source(Path(source_path))
    path = Path(package_path).resolve()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if (manifest.get("schema_version") != "b-recovery-package-trial/0.1"or not manifest.get("artifact_id")
            or manifest.get("policy") != POLICY
            or set(manifest) != {"schema_version","artifact_id","book_id","scope_id","policy","documents"}
            or any(manifest.get(k) != source[k]for k in ("book_id","scope_id"))
            or set(manifest.get("documents",{})) != {"base_evidence","recovery","source_review"}):
        raise ValueError("invalid recovery package scope/documents")
    documents,document_receipts = {},{}
    for name,descriptor in manifest["documents"].items():
        if set(descriptor) != {"path","text_sha256","artifact_ref"}: raise ValueError("document lacks exact text/source receipt")
        target = _path(path.parent,descriptor.get("path"))
        value = json.loads(target.read_text(encoding="utf-8"))
        if descriptor.get("text_sha256") != _textsha(target)or descriptor.get("artifact_ref") != _ref(value):
            emit("RECOVERY_PACKAGE_DOCUMENT_MISMATCH",name)
        documents[name] = value
        document_receipts[name] = {"path":descriptor["path"],"file_sha256":file_digest(target),
            "text_sha256":_textsha(target),"artifact_ref":_ref(value)}
    original,recovery,review = [documents[k]for k in ("base_evidence","recovery","source_review")]
    for value,schema,kind in ((original,"b-evidence-trial/0.2","EvidenceBundleTrial"),
            (recovery,"b-recovery-trial/0.1","RecoveryEvidenceTrial"),(review,"b-source-review-trial/0.1","SourceRecoveryReviewTrial")):
        if not _checked(value,schema,kind)or any(value.get(k) != source[k]for k in ("book_id","scope_id")):
            raise ValueError("invalid historical recovery envelope or scope")
    if (recovery["payload"].get("base_evidence_ref") != _ref(original)
            or review["payload"].get("base_evidence_ref") != _ref(original)
            or review["payload"].get("recovery_ref") != _ref(recovery)
            or review.get("input_refs") != [_ref(original),_ref(recovery)]):
        emit("RECOVERY_HISTORICAL_REFERENCE_MISMATCH")
    assets = [a for a,p in resolved]
    if ([p.get("source")for p in original["payload"].get("pages",[])] != assets
            or [p.get("asset_id")for p in original["payload"].get("pages",[])] != [a["asset_id"]for a in assets]):
        emit("RECOVERY_PACKAGE_SOURCE_SCOPE_MISMATCH")
    by_asset = {a["asset_id"]:(a,p)for a,p in resolved}
    crops,units,probes_by_line = [],{},{}
    producer = recovery.get("producer",{})
    synthetic = producer.get("execution_kind") == "SYNTHETIC_TEST"
    labelled_synthetic = (original.get("producer",{}).get("execution_kind") == "SYNTHETIC_TEST"
        or original["payload"].get("context",{}).get("reference_quality") == "SYNTHETIC_TEST"
        or any(asset.get("reference_quality") == "SYNTHETIC_TEST"for asset in assets))
    if labelled_synthetic and not synthetic: emit("RECOVERY_BACKEND_PROVENANCE_INVALID")
    if (recovery["payload"].get("verification_status","UNVERIFIED") != "UNVERIFIED"
            or recovery["payload"].get("base_evidence_unchanged")is not True
            or review["payload"].get("business_acceptance")is not False or review["payload"].get("platform_actions") != []):
        emit("RECOVERY_FALSE_VERIFICATION")
    if synthetic:
        if producer.get("device") != "SYNTHETIC_TEST"or producer.get("engine") != "injected_test_backend"or producer.get("model_files") != []:
            emit("RECOVERY_BACKEND_PROVENANCE_INVALID")
    elif (producer.get("device") != "CPU"or producer.get("engine") != "rapidocr_onnxruntime"
            or not producer.get("model_files")or producer.get("dependency_sha256") != digest(producer.get("dependencies"))
            or any(not re.fullmatch(r"[0-9a-f]{64}",str(m.get("sha256","")))for m in producer.get("model_files",[]))):
        emit("RECOVERY_BACKEND_PROVENANCE_INVALID")
    if review["payload"].get("reference_quality")not in {"SYNTHETIC_TEST","MODEL_VISUAL_DEVELOPMENT_REVIEW"}:
        emit("RECOVERY_REVIEW_QUALITY_ESCALATED")
    if recovery.get("input_refs",[])[:1] != [_ref(original)]: emit("RECOVERY_HISTORICAL_REFERENCE_MISMATCH")
    if synthetic and review["payload"].get("reference_quality") != "SYNTHETIC_TEST": emit("RECOVERY_REVIEW_QUALITY_ESCALATED")
    probe_ids = set()
    for probe in recovery["payload"].get("probes",[]):
        if probe.get("probe_id") in probe_ids: emit("RECOVERY_PROBE_ID_REUSED",probe.get("probe_id"))
        probe_ids.add(probe.get("probe_id"))
        if len({v["variant_id"]for v in probe.get("variants",[])}) != len(probe.get("variants",[])):
            emit("RECOVERY_VARIANT_ID_REUSED",probe.get("probe_id"))
        aid = probe["asset_id"]
        if aid not in by_asset: raise ValueError("recovery probe refers to undeclared source asset")
        asset,original_path = by_asset[aid]
        box = probe["crop_bbox"]
        if (probe.get("source_sha256") != asset["sha256"]or probe.get("source_size") != [asset["width"],asset["height"]]
                or not valid_bbox(box,asset["width"],asset["height"])or any(type(v)is not int for v in box)):
            raise ValueError("recovery probe source box/hash mismatch")
        crop_path = _path(path.parent,probe.get("crop_path"))
        with Image.open(crop_path)as opened: tile = opened.convert("RGB")
        with Image.open(original_path)as opened: actual = opened.convert("RGB").crop(box)
        if (file_digest(crop_path) != probe.get("crop_sha256")or tile.size != actual.size or tile.tobytes() != actual.tobytes()):
            emit("RECOVERY_CROP_SOURCE_PIXELS_MISMATCH",probe["probe_id"])
        crops.append({"probe_id":probe["probe_id"],"asset_id":aid,"path":probe["crop_path"],"crop_bbox":box,
            "file_sha256":file_digest(crop_path),"crop_rgb_sha256":_pixels(tile),"source_crop_rgb_sha256":_pixels(actual),
            "source_sha256":asset["sha256"],"crop_size":list(tile.size)})
        if probe.get("verification_status") != "UNVERIFIED": emit("RECOVERY_FALSE_VERIFICATION",probe["probe_id"])
        for variant in probe.get("variants",[]):
            scale,contrast = variant["scale"],variant["contrast"]
            if type(scale)is not int or not 1 <= scale <= 32 or not 0 < contrast <= 8: raise ValueError("invalid recovery preprocessing")
            transformed = ImageEnhance.Contrast(tile.resize((int(tile.width*scale),int(tile.height*scale)),Image.Resampling.LANCZOS)).enhance(contrast)
            bgr = np.asarray(transformed)[:,:,::-1].copy()
            if (variant.get("resampling") != "PIL_LANCZOS"or variant.get("transformed_pixels_sha256") != _pixels(bgr)
                    or variant.get("crop_to_original") != [[1/scale,0,box[0]],[0,1/scale,box[1]],[0,0,1]]
                    or variant.get("use_cls")is not False or variant.get("use_rec")is not True):
                emit("RECOVERY_TRANSFORM_MISMATCH",probe["probe_id"])
            raw,lines = variant.get("raw_ocr_result")or[],variant.get("ocr_lines",[])
            if len(raw) != len(lines): emit("RECOVERY_RAW_LINE_COVERAGE_MISMATCH",probe["probe_id"])
            for index,(row,line)in enumerate(zip(raw,lines)):
                if variant["use_det"]:
                    polygon,text,score = row[:3]
                    mapped = [[round(x/scale+box[0],4),round(y/scale+box[1],4)]for x,y in polygon]
                    bbox = [min(x for x,y in mapped),min(y for x,y in mapped),max(x for x,y in mapped),max(y for x,y in mapped)]
                else:
                    text,score = row[:2]
                    mapped,bbox = None,list(box)
                lid = "recovery/"+probe["probe_id"]+"/"+variant["variant_id"]+"/"+str(index)
                expected = {"line_id":lid,"text":text,"score":float(score),"bbox":bbox,"polygon":mapped,
                    "asset_id":aid,"location":probe.get("location"),"base_line_ids":probe["base_line_ids"],
                    "geometry_precision":"OCR_DETECTION"if variant["use_det"]else"REVIEWED_CROP_REGION","verification_status":"UNVERIFIED"}
                if (not valid_bbox(bbox,asset["width"],asset["height"])or not np.isfinite(float(score))or not 0 <= float(score) <= 1):
                    emit("RECOVERY_RAW_CPU_GEOMETRY_OR_SCORE_INVALID",lid)
                if line != expected: emit("RECOVERY_RAW_CPU_PROJECTION_MISMATCH",lid)
                if lid in units: emit("RECOVERY_HYPOTHESIS_ID_REUSED",lid)
                units[lid],probes_by_line[lid] = expected,(probe,variant)
    receipt = {"package":{"file_sha256":file_digest(path),"text_sha256":_textsha(path),"reference":_docref(manifest)},
        "documents":document_receipts,"crops":crops,"source_ref":_docref(source),"source_assets":assets}
    return source,documents,receipt,units,probes_by_line


def _audit_recovery_stage(source_path,package_path,current_base,derived):
    issues,summary = [],{}
    def emit(code,detail=None):
        item = {"code":code,"severity":"ERROR","detail":detail}
        if item not in issues: issues.append(item)
    source,documents,receipt,units,probe_for = _load_package(source_path,package_path,emit)
    old,recovery,sr = [documents[k]for k in ("base_evidence","recovery","source_review")]
    inputs = [_ref(current_base),_ref(derived),receipt["package"]["reference"]]
    if not _checked(current_base,"b-evidence-trial/0.2","EvidenceBundleTrial"):
        emit("RECOVERY_CURRENT_BASE_VERSION_INVALID")
        return _finish("RecoveryStageCheckTrial",inputs,source,issues,summary)
    if (digest(current_base["payload"]) != digest(old["payload"])or current_base["payload"] != old["payload"]
            or any(current_base.get(k) != old.get(k)for k in ("book_id","scope_id"))):
        emit("RECOVERY_BASE_PAYLOAD_NOT_IDENTICAL")
    if not _checked(derived,"b-evidence-trial/0.3","EvidenceBundleTrial"):
        emit("RECOVERY_DERIVED_VERSION_INVALID")
        return _finish("RecoveryStageCheckTrial",inputs,source,issues,summary)
    p,b = derived["payload"],old["payload"]
    _output_header(derived,"b-evidence-trial/0.3","EvidenceBundleTrial",current_base,
        [_ref(current_base),_ref(old),_ref(recovery),_ref(sr),receipt["package"]["reference"]],emit)
    if (any(derived.get(k) != current_base.get(k)for k in ("book_id","scope_id","run_id"))
            or derived.get("input_refs") != [_ref(current_base),_ref(old),_ref(recovery),_ref(sr),receipt["package"]["reference"]]):
        emit("RECOVERY_MIGRATION_INPUT_REFERENCE_MISMATCH")
    required = {"base_evidence_archive":old,"recovery_evidence_archive":recovery,"recovery_ref":_ref(recovery),
        "recovery_review_ref":_ref(sr),"recovery_source_review":sr["payload"],"source_review":sr["payload"],
        "reviewed_exclusions":sr["payload"]["reviewed_exclusions"]}
    for key,value in required.items():
        if p.get(key) != value: emit("RECOVERY_ORIGINAL_ARCHIVE_OR_REFERENCE_CHANGED",key)
    added_keys = set(required)|{"recovery_application","recovery_migration"}
    if set(p) != set(b)|added_keys or {k:v for k,v in p.items()if k not in added_keys|{"pages"}} != {k:v for k,v in b.items()if k != "pages"}:
        emit("RECOVERY_ORIGINAL_PAYLOAD_CHANGED")
    raw = {line["line_id"]:(page,line)for page in b["pages"]for line in page["ocr_lines"]}
    page_assets = {page["asset_id"]:page["source"]for page in b["pages"]}
    selected,replaced,ordered_ids = {},set(),[]
    for plan in recovery["payload"].get("supersession_plan",[]):
        aid = plan["asset_id"]
        if (aid not in page_assets or plan.get("source_sha256") != page_assets[aid]["sha256"]or plan.get("action") != "REPLACE_FOR_ASSEMBLY"
                or not plan.get("base_line_ids")or not plan.get("replacement_line_ids")or len(set(plan["base_line_ids"])) != len(plan["base_line_ids"])
                or replaced.intersection(plan["base_line_ids"])):
            emit("RECOVERY_PLAN_SOURCE_MISMATCH",plan.get("plan_id"))
        for lid in plan["base_line_ids"]:
            if lid not in raw or raw[lid][0]["asset_id"] != aid: emit("RECOVERY_PLAN_SOURCE_MISMATCH",lid)
        values = []
        for lid in plan["replacement_line_ids"]:
            if lid not in units: raise ValueError("plan selected unknown raw hypothesis")
            probe,variant = probe_for[lid]
            if (probe["probe_id"]not in plan["selected_probe_ids"]or variant["variant_id"] != probe.get("selected_variant_id")
                    or probe["asset_id"] != aid or units[lid].get("location") != plan.get("location")):
                emit("RECOVERY_PLAN_SELECTION_MISMATCH",lid)
            line = copy.deepcopy(units[lid])
            line.update(recovery_plan_id=plan["plan_id"],source_type="LOCAL_CPU_OCR_RECOVERY",
                        verification_status="UNVERIFIED",independent_confirmation=False)
            if probe["status"] == "ANCHOR_RECOVERED_FORMULAS_UNRESOLVED": line["reading_order_status"] = "UNRESOLVED_2D_FORMULA"
            values.append(line)
        top = min(line["bbox"][1]for line in values)
        height = max(line["bbox"][3]for line in values)-top
        for line in values:
            anchor = bool(re.match(r"^\d{1,2}[.．、]\s*解",line["text"]))
            line["assembly_order"] = [top,line["bbox"][0],line["bbox"][1]]if height <= 50 else[top,0 if anchor else 1,line["bbox"][1],line["bbox"][0]]
            if line["line_id"]in selected: emit("RECOVERY_APPLIED_HYPOTHESIS_REUSED",line["line_id"])
            selected[line["line_id"]] = line
            ordered_ids.append(line["line_id"])
        replaced.update(plan["base_line_ids"])
    for choice in sr["payload"].get("reviewed_probe_selections",[]):
        lid = choice["line_id"]
        if lid not in units: raise ValueError("review selected unknown raw hypothesis")
        probe,variant = probe_for[lid]
        if choice.get("source_sha256") != probe["source_sha256"]or not choice.get("reason"):
            emit("RECOVERY_REVIEW_SELECTION_SOURCE_MISMATCH",lid)
        line = copy.deepcopy(units[lid])
        line.update(source_type="LOCAL_CPU_OCR_REVIEWED_SELECTION",verification_status="UNVERIFIED",independent_confirmation=False,
                    reviewed_marker=choice.get("reviewed_marker"),selection_rationale=choice["reason"])
        if lid in selected: emit("RECOVERY_APPLIED_HYPOTHESIS_REUSED",lid)
        selected[lid] = line;ordered_ids.append(lid)
    for anchor in sr["payload"].get("reviewed_primary_anchors",[]):
        lid = anchor["line_id"]
        if lid not in selected: raise ValueError("reviewed primary anchor was not applied")
        line = selected[lid]
        match = re.match(r"^\s*(\d{1,2})[.．、]",line["text"])
        if (not match or match[1] != anchor["printed_number"]or anchor["source_sha256"] != page_assets[line["asset_id"]]["sha256"]or not anchor.get("reason")):
            emit("RECOVERY_REVIEW_ANCHOR_SOURCE_MISMATCH",lid)
        line["reviewed_primary_number"] = anchor["printed_number"]
    actual_pages = p.get("pages",[])
    if [page.get("asset_id")for page in actual_pages] != [page["asset_id"]for page in b["pages"]]:
        emit("RECOVERY_DERIVED_PAGE_SCOPE_MISMATCH")
    for old_page,page in zip(b["pages"],actual_pages):
        if {k:v for k,v in page.items()if k not in {"ocr_lines","answer_detail_lines"}} != {k:v for k,v in old_page.items()if k not in {"ocr_lines","answer_detail_lines"}}:
            emit("RECOVERY_ORIGINAL_PAGE_METADATA_CHANGED",old_page["asset_id"])
        expected_raw = [line for line in old_page["ocr_lines"]if line["line_id"]not in replaced]+[
            selected[lid]for lid in ordered_ids if selected[lid]["asset_id"] == old_page["asset_id"]]
        if page.get("ocr_lines") != expected_raw: emit("RECOVERY_ACTIVE_RAW_PROJECTION_MISMATCH",old_page["asset_id"])
        expected_detail = [line for line in old_page["answer_detail_lines"]if line["parent_line_id"]not in replaced]
        if page.get("answer_detail_lines") != expected_detail: emit("RECOVERY_ACTIVE_DETAIL_PROJECTION_MISMATCH",old_page["asset_id"])
    expected_application = {"supersession_plan":recovery["payload"]["supersession_plan"],"replaced_base_line_ids":sorted(replaced),
        "replacement_line_ids":ordered_ids,"base_unchanged":True,"formula_candidates":sr["payload"].get("formula_candidates",[])}
    if p.get("recovery_application") != expected_application: emit("RECOVERY_APPLICATION_LEDGER_MISMATCH")
    for candidate in sr["payload"].get("formula_candidates",[]):
        if (candidate.get("method") != "MODEL_VISUAL_DEVELOPMENT_TRANSCRIPTION"or candidate.get("verification_status") != "UNVERIFIED"
                or any(candidate.get(key)is not False for key in ("cpu_ocr","human_verified","applied_to_ocr","business_acceptance"))):
            emit("RECOVERY_VISUAL_FORMULA_PROVENANCE_ESCALATED",candidate.get("candidate_id"))
    for exclusion in sr["payload"].get("reviewed_exclusions",[]):
        lid = exclusion["line_id"]
        if lid not in raw: raise ValueError("exclusion not bound to original source")
        page,line = raw[lid]
        text,kind = re.sub(r"\s+","",line["text"]),exclusion.get("kind")
        if (kind not in {"title","footer"}
                or kind == "footer"and (line["bbox"][1] < .94*page["source"]["height"]or not re.fullmatch(r"(?:\d{1,3}|数学·八年级上·BS)",text))
                or kind == "title"and not re.fullmatch(r"(?:小专题[12].+|漫话勾股世界.+|☆问题解决策略：反思)",text)):
            emit("RECOVERY_EXCLUSION_SEMANTICS_INVALID",lid)
        if exclusion.get("source_sha256") != page["source"]["sha256"]or exclusion.get("source_text_sha256") != hashlib.sha256(line["text"].encode()).hexdigest():
            emit("RECOVERY_EXCLUSION_SOURCE_MISMATCH",lid)
    legacy_payload = {k:v for k,v in p.items()if k != "recovery_migration"}
    legacy_inputs = [_ref(old),_ref(recovery),_ref(sr)]
    legacy_producer = {"module":"annotation.recognition.recovery_apply","version":"0.1.0",
        "code_sha256":code_digest(Path(__file__).with_name("recovery_apply.py")),"source_evidence_preserved":True}
    legacy_identity = digest({"schema":"b-evidence-trial/0.3","source":old,"payload":legacy_payload,
        "inputs":legacy_inputs,"producer":legacy_producer})
    migration = {"policy":POLICY,"current_base_ref":_ref(current_base),"original_base_ref":_ref(old),"original_recovery_ref":_ref(recovery),
        "original_source_review_ref":_ref(sr),"legacy_derived_ref":{"artifact_id":"evidencebundletrial-"+legacy_identity[:24],"revision":1,"content_hash":digest(legacy_payload)},
        "package_receipt":_content_receipt(receipt),"current_payload_sha256":digest(current_base["payload"]),"original_payload_sha256":digest(old["payload"]),
        "payloads_equal":True,"current_identity_differs":_ref(current_base) != _ref(old),"original_source_review_archive":sr,
        "decision":"HOLD","transcription_verified":False,"business_acceptance":False,"new_ocr_calls":0,"platform_actions":[]}
    if p.get("recovery_migration") != migration: emit("RECOVERY_MIGRATION_RECEIPT_MISMATCH")
    summary.update(source_asset_count=len(receipt["source_assets"]),probe_count=len(receipt["crops"]),
        raw_hypothesis_count=len(units),replaced_raw_count=len(replaced),applied_hypothesis_count=len(ordered_ids),
        retained_source_group_count=len(sr["payload"].get("remaining_source_groups",[])))
    return _finish("RecoveryStageCheckTrial",inputs,current_base,issues,summary)


def audit_recovery_stage(source_path,package_path,current_base,derived):
    try:
        return _audit_recovery_stage(source_path,package_path,current_base,derived)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,IndexError)as exc:
        return _finish("RecoveryStageCheckTrial",[],current_base,[{"code":"RECOVERY_STAGE_DATA_INVALID","severity":"ERROR",
            "detail":type(exc).__name__+": "+str(exc)}],{})


def _audit_recovery_review(review,derived,artifact):
    issues,summary = [],{}
    def emit(code,detail=None):
        issues.append({"code":code,"severity":"ERROR","detail":detail})
    if not _checked(derived,"b-evidence-trial/0.3","EvidenceBundleTrial")or not _checked(artifact,"b-recovery-review-trial/0.1","RecoveryReviewTrial"):
        emit("RECOVERY_REVIEW_ARTIFACT_INVALID")
        return _finish("RecoveryReviewCheckTrial",[],derived,issues,summary)
    p = artifact["payload"]
    _output_header(artifact,"b-recovery-review-trial/0.1","RecoveryReviewTrial",derived,[_docref(review),_ref(derived)],emit)
    migration = derived["payload"]["recovery_migration"]
    if (artifact.get("input_refs") != [_docref(review),_ref(derived)]
            or any(artifact.get(k) != derived.get(k)for k in ("book_id","scope_id","run_id"))):
        emit("RECOVERY_REVIEW_INPUT_REFERENCE_MISMATCH")
    expected_meta = {"input_review_ref":_docref(review),"recovered_evidence_ref":_ref(derived),"package_receipt":migration["package_receipt"],
        "decision":"HOLD","transcription_verified":False,"business_acceptance":False,"new_ocr_calls":0,"platform_actions":[]}
    if {k:v for k,v in p.items()if k != "review"} != expected_meta:
        emit("RECOVERY_REVIEW_MIGRATION_RECEIPT_MISMATCH")
    actual = p["review"]
    if "recovery_migration_ref"in review:
        emit("RECOVERY_REVIEW_ALREADY_MIGRATED")
    allowed = {"unresolved_source_groups","retired_unresolved_source_groups","recovery_migration_ref","multiline_checks"}
    if (set(actual) != set(review)|{"unresolved_source_groups","retired_unresolved_source_groups","recovery_migration_ref"}
            or {k:v for k,v in actual.items()if k not in allowed} != {k:v for k,v in review.items()if k not in allowed}
            or actual.get("recovery_migration_ref") != _ref(derived)):
        emit("RECOVERY_REVIEW_ORIGINAL_FIELDS_CHANGED")
    replaced = set(derived["payload"]["recovery_application"]["replaced_base_line_ids"])
    old_groups = review.get("unresolved_source_groups",[])
    if actual.get("unresolved_source_groups") != [g for g in old_groups if not set(g["source_line_ids"]) <= replaced]:
        emit("RECOVERY_REVIEW_UNRESOLVED_SOURCE_LOST")
    if actual.get("retired_unresolved_source_groups") != [g for g in old_groups if set(g["source_line_ids"]) <= replaced]:
        emit("RECOVERY_REVIEW_RETIRED_SOURCE_MISMATCH")
    additions = {item["case_id"]:item for item in derived["payload"]["recovery_source_review"].get("regression_additions",[])}
    active = {line["line_id"]:line for page in derived["payload"]["pages"]for line in page["ocr_lines"]}
    old_cases,new_cases = review.get("multiline_checks",[]),actual.get("multiline_checks",[])
    if [c.get("case_id")for c in old_cases] != [c.get("case_id")for c in new_cases]:
        emit("RECOVERY_REVIEW_REGRESSION_SCOPE_MISMATCH")
    for old,new in zip(old_cases,new_cases):
        addition = additions.get(old["case_id"])
        if not addition or addition.get("line_id")not in active:
            if new != old: emit("RECOVERY_REVIEW_ORIGINAL_REGRESSION_CHANGED",old["case_id"])
            continue
        line = active[addition["line_id"]]
        if hashlib.sha256(line["text"].encode()).hexdigest() != addition["source_text_sha256"]:
            emit("RECOVERY_REVIEW_REGRESSION_SOURCE_MISMATCH",old["case_id"])
        changes = {"expected_source_line_ids","expected_source_spans","observed_source_gaps"}
        if {k:v for k,v in new.items()if k not in changes} != {k:v for k,v in old.items()if k not in changes}:
            emit("RECOVERY_REVIEW_ORIGINAL_REGRESSION_CHANGED",old["case_id"])
        if new.get("expected_source_line_ids") != old["expected_source_line_ids"]+[addition["line_id"]]:
            emit("RECOVERY_REVIEW_REGRESSION_SOURCE_MISMATCH",old["case_id"])
        expected_span = {k:addition[k]for k in ("line_id","text_spans","source_text_sha256")}
        if new.get("expected_source_spans") != old["expected_source_spans"]+[expected_span]:
            emit("RECOVERY_REVIEW_REGRESSION_SOURCE_MISMATCH",old["case_id"])
        expected_gaps = copy.deepcopy(old.get("observed_source_gaps",[]))
        for gap in expected_gaps:
            gap.update(recovery_status="PARTIALLY_RECOVERED_UNVERIFIED"if "q1-"in old["case_id"]else"RECOVERED_CANDIDATE_UNVERIFIED",
                       recovered_line_ids=[addition["line_id"]])
        if new.get("observed_source_gaps",[]) != expected_gaps:
            emit("RECOVERY_REVIEW_GAP_STATUS_ESCALATED",old["case_id"])
    summary.update(retained_unresolved_groups=len(actual.get("unresolved_source_groups",[])),
        retired_source_groups=len(actual.get("retired_unresolved_source_groups",[])),regression_case_count=len(new_cases))
    return _finish("RecoveryReviewCheckTrial",[_docref(review),_ref(derived),_ref(artifact)],derived,issues,summary)


def audit_recovery_review(review,derived,artifact):
    try:
        return _audit_recovery_review(review,derived,artifact)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,IndexError)as exc:
        return _finish("RecoveryReviewCheckTrial",[],derived,[{"code":"RECOVERY_REVIEW_DATA_INVALID","severity":"ERROR",
            "detail":type(exc).__name__+": "+str(exc)}],{})
