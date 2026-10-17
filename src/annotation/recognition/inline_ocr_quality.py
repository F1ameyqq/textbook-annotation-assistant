"""Independent source/observation audit of approximate inline OCR boxes.

No collector or OCR runtime is imported. CTC boxes estimate positions from
recognizer time steps and a detected line height; they are not glyph masks and
cannot prove a superscript, root sign, transcription or business correctness.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import re

import numpy as np
from PIL import Image

from .baseline import code_digest,digest,file_digest,valid_bbox

SCHEMA = "b-inline-ocr-check-trial/0.1"
_HASH = re.compile(r"^[a-f0-9]{64}$")
_VARIANTS = (("scale3",3),("scale4",4))
_FLAGS = {"localization_kind":"CTC_TIMESTEP_ESTIMATE","precise_glyph_localization":False,
          "spatial_role_verified":False,"verification_status":"UNVERIFIED"}
_CONFIG = {"padding":2,"bbox_rounding":"FLOOR_MIN_CEIL_MAX_CLAMP_ORIGINAL_PAGE",
    "variants":[{"variant_id":"scale3","scale":3},{"variant_id":"scale4","scale":4}],
    "resampling":"PIL_LANCZOS","channel_order":"BGR","dtype":"uint8",
    "engine_flags":{"use_det":True,"use_cls":False,"use_rec":True,"return_word_box":True,"text_score":0},
    "localization_kind":"CTC_TIMESTEP_ESTIMATE","precise_glyph_localization":False,"spatial_role_verified":False,
    "rapidocr_version":"1.4.4","candidate_policy":"PRESERVE_ALL_RAW_ROWS_AND_WORD_ARRAY_INDICES"}


def _ref(value): return {k:value.get(k)if isinstance(value,dict)else None for k in ("artifact_id","revision","content_hash")}
def _rgb(image): return hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()
def _finite(value): return type(value)in (int,float)and math.isfinite(value)
def _score(value): return _finite(value)and 0 <= value <= 1


def _polygon(value,size,matrix):
    if (not isinstance(value,list)or len(value) != 4 or any(not isinstance(p,list)or len(p) != 2 or any(not _finite(n)for n in p)for p in value)):
        return "INVALID",None
    scale = round(1/matrix[0][0])
    projected = [[p[0]/scale+matrix[0][2],p[1]/scale+matrix[1][2]]for p in value]
    area = abs(sum(value[i][0]*value[(i+1)%4][1]-value[(i+1)%4][0]*value[i][1]for i in range(4)))/2
    if area == 0: return "DEGENERATE",projected
    if any(not 0 <= p[0] <= size[0]or not 0 <= p[1] <= size[1]for p in value): return "OUTSIDE_INPUT",projected
    return "USABLE",projected


def audit_inline_ocr(evidence,observations,source_path,*,line_ids=None):
    """Audit exact requested rows and retained raw results without recognition.

    Passing external ``line_ids`` binds the requested scope. Omitting it only
    checks the collector's declared scope; the summary states that limitation.
    Honest malformed/empty engine observations remain risks, not hidden data.
    """
    issues,risks = [],[]
    summary = {"declared_scope_only":line_ids is None,"requested_rows":0,"observed_rows":0,
        "variants":0,"raw_candidates":0,"word_estimates":0,"unusable_word_estimates":0,
        "observation_risks":0,"transcription_verified":False,"pixel_verified_assets":0}
    def issue(code,detail=None,row_id=None,variant_id=None):
        item = {"code":code,"severity":"ERROR","detail":detail}
        if row_id is not None: item["row_id"] = row_id
        if variant_id is not None: item["variant_id"] = variant_id
        if item not in issues: issues.append(item)
    def finish():
        summary["observation_risks"] = len(risks)
        payload = {"accepted":not issues,"issues":issues,"observation_risks":risks,"summary":summary,
            "decision":"HOLD","transcription_verified":False,"business_acceptance":False,"complete":False,
            "graph_modified":False,"platform_actions":[],**_FLAGS,
            "limitations":["Integrity checks cannot authenticate a CPU execution receipt as a signature.",
                "CTC timestep estimates are not precise source glyph boxes or proof of mathematical roles.",
                "Repeated OCR agreement and source pixel binding do not establish complete transcription."]}
        inputs = [_ref(evidence),_ref(observations)]
        producer = {"module":__name__,"version":"0.1.0","code_sha256":code_digest(Path(__file__))}
        return {"schema_version":SCHEMA,"kind":"InlineOCRCheckTrial","artifact_id":"inline-ocr-check-"+digest([inputs,producer,payload])[:24],
            "revision":1,**{k:evidence.get(k)if isinstance(evidence,dict)else None for k in ("book_id","scope_id","run_id")},"input_refs":inputs,"producer":producer,
            "content_hash":digest(payload),"payload":payload}
    try:
        _audit(evidence,observations,Path(source_path),line_ids,issue,risks,summary)
    except (OSError,ValueError,TypeError,KeyError,IndexError,AttributeError,OverflowError,RecursionError,StopIteration)as exc:
        issue("INLINE_OCR_DATA_INVALID",type(exc).__name__+": "+str(exc))
    return finish()


def _audit(evidence,observations,source_path,line_ids,issue,risks,summary):
    for value,schemas,kind in ((evidence,{"b-evidence-trial/0.2","b-evidence-trial/0.3"},"EvidenceBundleTrial"),
            (observations,{"b-inline-ocr-observation-trial/0.1"},"InlineOCRObservationTrial")):
        if (value.get("schema_version")not in schemas or value.get("kind") != kind or not isinstance(value.get("artifact_id"),str)
                or type(value.get("revision"))is not int or value["revision"] < 1 or not isinstance(value.get("payload"),dict)
                or value.get("content_hash") != digest(value["payload"])):
            issue("INLINE_OCR_ARTIFACT_INVALID",kind);return
    p = observations["payload"];source = p["source"];producer = observations["producer"]
    header_keys = {"schema_version","kind","artifact_id","revision","book_id","scope_id","input_refs","producer","content_hash","payload"}
    if set(observations) != header_keys or observations["revision"] != 1: issue("INLINE_OCR_HEADER_VERSION_OR_FIELDS_INVALID")
    if (observations.get("input_refs") != [_ref(evidence)]or p.get("evidence_ref") != _ref(evidence)
            or any(observations.get(k) != evidence.get(k)for k in ("book_id","scope_id"))or "created_at"in observations):
        issue("INLINE_OCR_EVIDENCE_BINDING_MISMATCH")
    if observations.get("artifact_id") != "inline-ocr-observation-"+digest({"source":_ref(evidence),"inputs":[_ref(evidence)],"producer":producer,"payload":p})[:24]:
        issue("INLINE_OCR_IDENTITY_MISMATCH")
    _backend(producer,issue)
    expected_flags = {"decision":"HOLD","complete":False,"transcription_verified":False,"business_acceptance":False,
        "graph_modified":False,"platform_actions":[],**_FLAGS}
    if any(p.get(k) != value for k,value in expected_flags.items()): issue("INLINE_OCR_FALSE_VERIFICATION")
    allowed = set(expected_flags)|{"evidence_ref","source","requested_line_ids","rows","limitations"}
    if set(p) != allowed: issue("INLINE_OCR_UNKNOWN_PAYLOAD_FIELDS",sorted(set(p)^allowed))
    declared = p["requested_line_ids"]
    if (not isinstance(declared,list)or not declared or any(not isinstance(n,str)or not n for n in declared)
            or len(declared) != len(set(declared))or line_ids is not None and declared != list(line_ids)):
        issue("INLINE_OCR_REQUESTED_SCOPE_MISMATCH")
    summary["requested_rows"] = len(declared)
    page_ids,all_line_ids = [],[]
    for declared_page in evidence["payload"]["pages"]:
        declared_asset = declared_page["source"];aid = declared_page["asset_id"]
        page_ids.append(aid)
        if (declared_asset.get("asset_id") != aid or any(type(declared_asset.get(k))is not int or declared_asset[k] <= 0 for k in ("width","height"))
                or not _HASH.fullmatch(declared_asset.get("sha256",""))): issue("INLINE_OCR_EVIDENCE_SCOPE_INVALID")
        for declared_line in declared_page["ocr_lines"]:
            all_line_ids.append(declared_line["line_id"])
            if declared_line.get("asset_id",aid) != aid: issue("INLINE_OCR_EVIDENCE_SCOPE_INVALID")
    if (len(page_ids) != len(set(page_ids))or len(all_line_ids) != len(set(all_line_ids))
            or any(not isinstance(l,str)or not l for l in page_ids+all_line_ids)): issue("INLINE_OCR_EVIDENCE_SCOPE_INVALID")
    pages = [page for page in evidence["payload"]["pages"]if page["asset_id"] == source["asset_id"]]
    if len(pages) != 1: issue("INLINE_OCR_ASSET_SOURCE_MISMATCH");return
    page = pages[0];asset = page["source"]
    with Image.open(source_path)as opened: original = opened.convert("RGB")
    expected_source = {"asset_id":page["asset_id"],"asset":asset,"original_sha256":asset["sha256"],
        "width":asset["width"],"height":asset["height"],"original_rgb_sha256":_rgb(original)}
    if (source != expected_source or file_digest(source_path) != asset["sha256"]or list(original.size) != [asset["width"],asset["height"]]):
        issue("INLINE_OCR_ORIGINAL_SOURCE_MISMATCH")
    else: summary["pixel_verified_assets"] = 1
    rows = p["rows"];summary["observed_rows"] = len(rows)
    lookup = {line["line_id"]:line for line in page["ocr_lines"]}
    if [r.get("line_id")for r in rows] != declared: issue("INLINE_OCR_ROW_SCOPE_MISMATCH")
    for row in rows:
        lid = row["line_id"];raw_line = lookup.get(lid)
        if raw_line is None: issue("INLINE_OCR_LINE_SOURCE_MISSING",lid);continue
        row_id = "inline-row-"+digest([_ref(evidence),page["asset_id"],lid])[:24]
        box = raw_line["bbox"]
        if not valid_bbox(box,*original.size): issue("INLINE_OCR_LINE_GEOMETRY_INVALID",lid);continue
        crop_box = [max(0,math.floor(box[0])-2),max(0,math.floor(box[1])-2),min(original.width,math.ceil(box[2])+2),min(original.height,math.ceil(box[3])+2)]
        crop = original.crop(crop_box)
        expected = {"row_id":row_id,"line_id":lid,"asset_id":page["asset_id"],"source_line":raw_line,"bbox":box,
            "crop_bbox":crop_box,"crop_size":list(crop.size),"crop_rgb_sha256":_rgb(crop)}
        if any(row.get(k) != value for k,value in expected.items())or set(row) != set(expected)|{"variants"}:
            issue("INLINE_OCR_COMPLETE_LINE_SNAPSHOT_OR_PIXELS_MISMATCH",lid,row_id)
        variants = row["variants"]
        if [(v.get("variant_id"),v.get("scale"))for v in variants] != list(_VARIANTS): issue("INLINE_OCR_VARIANT_SCOPE_MISMATCH",lid,row_id)
        for variant in variants:
            vid,scale = variant["variant_id"],variant["scale"]
            if (vid,scale)not in _VARIANTS: continue
            summary["variants"] += 1
            transformed = crop.resize((crop.width*scale,crop.height*scale),Image.Resampling.LANCZOS)
            bgr = np.ascontiguousarray(np.asarray(transformed,dtype=np.uint8)[:,:,::-1])
            matrix = [[1/scale,0,crop_box[0]],[0,1/scale,crop_box[1]],[0,0,1]]
            expected_variant = {"variant_id":vid,"scale":scale,"size":list(transformed.size),"rgb_sha256":_rgb(transformed),
                "bgr_sha256":hashlib.sha256(bgr.tobytes()).hexdigest(),"dtype":"uint8","channel_order":"BGR","variant_to_original":matrix}
            if any(variant.get(k) != value for k,value in expected_variant.items()): issue("INLINE_OCR_TRANSFORM_OR_TENSOR_MISMATCH",lid,row_id,vid)
            _raw(variant,row_id,matrix,list(transformed.size),issue,risks,summary)


def _backend(producer,issue):
    names = {"module","version","code_sha256","dependency_code_sha256","configuration","configuration_sha256",
        "execution_kind","engine","device","dependencies","dependency_sha256","package_files","package_code_sha256",
        "config_file","model_files","models_sha256","session_providers","session_providers_sha256"}
    if (set(producer) != names or producer.get("module") != "annotation.recognition.inline_ocr"or producer.get("version") != "0.1.0"
            or producer.get("code_sha256") != code_digest(Path(__file__).with_name("inline_ocr.py"))
            or producer.get("dependency_code_sha256") != {"baseline":code_digest(Path(__file__).with_name("baseline.py"))}):
        issue("INLINE_OCR_PRODUCER_IDENTITY_INVALID")
    if producer.get("configuration") != _CONFIG or producer.get("configuration_sha256") != digest(_CONFIG): issue("INLINE_OCR_CONFIGURATION_INVALID")
    deps,files,models,providers = [producer.get(k)for k in ("dependencies","package_files","model_files","session_providers")]
    if (not isinstance(deps,dict)or not isinstance(files,list)or not isinstance(models,list)or not isinstance(providers,dict)
            or producer.get("dependency_sha256") != digest(deps)or producer.get("package_code_sha256") != digest(files)
            or producer.get("models_sha256") != digest(models)or producer.get("session_providers_sha256") != digest(providers)):
        issue("INLINE_OCR_BACKEND_RECEIPT_INVALID");return
    if producer.get("execution_kind") == "SYNTHETIC_TEST":
        if (producer.get("device") != "SYNTHETIC_TEST"or producer.get("engine") != "injected_test_backend"
                or deps != {}or files != []or models != []or providers != {}or producer.get("config_file")is not None):
            issue("INLINE_OCR_BACKEND_RECEIPT_INVALID")
        return
    if (producer.get("execution_kind") != "CPU_RAPIDOCR_INLINE"or producer.get("device") != "CPU"
            or producer.get("engine") != "rapidocr_onnxruntime"): issue("INLINE_OCR_BACKEND_RECEIPT_INVALID");return
    expected_dist = {"rapidocr_onnxruntime":"rapidocr-onnxruntime","onnxruntime":"onnxruntime","numpy":"numpy","PIL":"Pillow","yaml":"PyYAML"}
    if set(deps) != set(expected_dist)|{"cv2"}: issue("INLINE_OCR_BACKEND_RECEIPT_INVALID")
    for name,receipt in deps.items():
        if (set(receipt) != {"distribution","version","package_entry_sha256","distribution_record_sha256"}
                or not isinstance(receipt.get("version"),str)or not receipt["version"]
                or not _HASH.fullmatch(receipt.get("package_entry_sha256",""))or not _HASH.fullmatch(receipt.get("distribution_record_sha256","")or"")
                or name in expected_dist and receipt.get("distribution") != expected_dist[name]
                or name == "cv2"and receipt.get("distribution")not in {"opencv-python","opencv-python-headless","opencv-contrib-python","opencv-contrib-python-headless"}):
            issue("INLINE_OCR_BACKEND_RECEIPT_INVALID",name)
    if deps.get("rapidocr_onnxruntime",{}).get("version") != "1.4.4": issue("INLINE_OCR_BACKEND_VERSION_INVALID")
    paths = [f.get("path")for f in files]
    if (not files or len(paths) != len(set(paths))or not {"__init__.py","main.py","cal_rec_boxes/main.py","ch_ppocr_rec/utils.py"} <= set(paths)
            or any(set(f) != {"path","sha256"}or not isinstance(f["path"],str)or not f["path"].endswith(".py")
                   or f["path"].startswith("/")or ":"in f["path"]or "\\"in f["path"]or ".."in f["path"].split("/")
                   or not _HASH.fullmatch(f.get("sha256",""))for f in files)):
        issue("INLINE_OCR_PACKAGE_SOURCE_RECEIPT_INVALID")
    config = producer.get("config_file")
    if (not isinstance(config,dict)or set(config) != {"path","sha256","text_sha256"}or config.get("path") != "config.yaml"
            or any(not _HASH.fullmatch(config.get(k,""))for k in ("sha256","text_sha256"))): issue("INLINE_OCR_BACKEND_RECEIPT_INVALID","config")
    if ([m.get("role")for m in models] != ["Det","Cls","Rec"]or any(set(m) != {"role","name","sha256","active_in_call"}
            or not _HASH.fullmatch(m.get("sha256",""))or not isinstance(m.get("name"),str)or not m["name"].endswith(".onnx")
            or m["name"].startswith("/")or ":"in m["name"]or "\\"in m["name"]or ".."in m["name"].split("/")
            or m["active_in_call"]is not (m["role"] != "Cls")for m in models)
            or providers != {role:["CPUExecutionProvider"]for role in ("Det","Cls","Rec")}):
        issue("INLINE_OCR_MODEL_OR_CPU_PROVIDER_RECEIPT_INVALID")


def _raw(variant,row_id,matrix,size,issue,risks,summary):
    vid = variant["variant_id"]
    expected_keys = {"variant_id","scale","size","rgb_sha256","bgr_sha256","dtype","channel_order","variant_to_original",
        "raw_call_result","raw_ocr_result","engine_elapsed_seconds","wall_elapsed_seconds","recognition_error","candidates","issues"}
    if set(variant) != expected_keys: issue("INLINE_OCR_UNKNOWN_VARIANT_FIELDS",sorted(set(variant)^expected_keys),row_id,vid)
    if not _finite(variant.get("wall_elapsed_seconds"))or variant["wall_elapsed_seconds"] < 0: issue("INLINE_OCR_ELAPSED_INVALID",None,row_id,vid)
    call,raw,elapsed,error = [variant[k]for k in ("raw_call_result","raw_ocr_result","engine_elapsed_seconds","recognition_error")]
    valid_call = isinstance(call,list)and len(call) == 2
    valid_elapsed = elapsed is None or isinstance(elapsed,list)and all(_finite(t)and t >= 0 for t in elapsed)
    if valid_call:
        if raw != call[0]or elapsed != call[1]: issue("INLINE_OCR_RAW_CALL_PROJECTION_MISMATCH",None,row_id,vid)
    elif raw is not None or elapsed is not None: issue("INLINE_OCR_RAW_CALL_PROJECTION_MISMATCH",None,row_id,vid)
    if error is not None:
        if (not isinstance(error,dict)or set(error) != {"type","message"}or not isinstance(error.get("type"),str)
                or not error["type"]or not isinstance(error.get("message"),str)
                or variant["candidates"] != []or variant["issues"] != []): issue("INLINE_OCR_FAILURE_RECORD_INVALID",None,row_id,vid)
        risks.append({"code":"OCR_CALL_FAILED","row_id":row_id,"variant_id":vid,"detail":error,"severity":"REVIEW"})
        return
    if not valid_call or not valid_elapsed: issue("INLINE_OCR_RAW_CALL_INVALID",None,row_id,vid)
    expected,codes = [],[]
    if raw is None: codes.append({"code":"OCR_EMPTY"})
    elif not isinstance(raw,list): codes.append({"code":"RAW_RESULT_INVALID"})
    else:
        for index,entry in enumerate(raw):
            candidate = {"candidate_id":"inline-candidate-"+digest([row_id,vid,index])[:24],"raw_result_index":index,"raw_observation":entry,
                "text":None,"score":None,"polygon":None,"source_polygon":None,"polygon_status":"INVALID","word_estimates":[],"word_alignment_status":"INVALID",**_FLAGS}
            expected.append(candidate)
            def risk(code,word=None):
                item = {"code":code,"raw_result_index":index}
                if word is not None: item["raw_word_index"] = word
                codes.append(item)
            if not isinstance(entry,list)or len(entry) != 6:
                risk("RAW_ROW_INVALID");continue
            polygon,text,score,boxes,words,scores = entry
            status,mapped = _polygon(polygon,size,matrix)
            candidate.update(text=text if isinstance(text,str)else None,score=score if _finite(score)else None,
                polygon=polygon,source_polygon=mapped,polygon_status=status)
            if status != "USABLE": risk("POLYGON_"+status)
            if not isinstance(text,str): risk("RAW_ROW_INVALID")
            if not _score(score): risk("SCORE_INVALID")
            if not all(isinstance(array,list)for array in (boxes,words,scores)):
                risk("WORD_ARRAYS_INVALID");continue
            lengths_match = len(boxes) == len(words) == len(scores)
            typed = all(isinstance(word,str)for word in words)
            text_matches = typed and isinstance(text,str)and "".join(words) == text
            candidate["word_alignment_status"] = "ALIGNED"if lengths_match and text_matches else"LENGTH_MISMATCH"if typed else"INVALID"
            if not lengths_match: risk("WORD_ARRAY_LENGTH_MISMATCH")
            if not text_matches: risk("WORD_SEQUENCE_MISMATCH")
            for j in range(max(len(boxes),len(words),len(scores))):
                polygon = boxes[j]if j < len(boxes)else None
                status,mapped = _polygon(polygon,size,matrix)
                score = scores[j]if j < len(scores)else None
                candidate["word_estimates"].append({"raw_word_index":j,"polygon":polygon,"source_polygon":mapped,
                    "text":words[j]if j < len(words)else None,"score":score,"polygon_status":status,**_FLAGS})
                if status != "USABLE": risk("POLYGON_"+status,j)
                if not _score(score): risk("SCORE_INVALID",j)
        if not raw: codes.append({"code":"OCR_EMPTY"})
    if variant["candidates"] != expected: issue("INLINE_OCR_RAW_CANDIDATE_OR_WORD_PROJECTION_MISMATCH",None,row_id,vid)
    if variant["issues"] != codes: issue("INLINE_OCR_RAW_RISKS_NOT_PRESERVED",None,row_id,vid)
    for risk in codes: risks.append({**risk,"row_id":row_id,"variant_id":vid,"severity":"REVIEW"})
    summary["raw_candidates"] += len(expected)
    for candidate in expected:
        for word in candidate["word_estimates"]:
            summary["word_estimates"] += 1
            if word["polygon_status"] != "USABLE": summary["unusable_word_estimates"] += 1
            if _score(word["score"])and word["score"] < .5:
                risks.append({"code":"LOW_CONFIDENCE_WORD_ESTIMATE","row_id":row_id,"variant_id":vid,
                    "raw_result_index":candidate["raw_result_index"],"raw_word_index":word["raw_word_index"],"score":word["score"],"severity":"REVIEW"})
