"""Independent pixels, tensors and lossless syntax audit for canvas observations.

No collector, candidate builder, backend adapter or production parser is run.
Acceptance concerns retained provenance/projection, never transcription accuracy.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
from PIL import Image

from .baseline import code_digest,digest,file_digest
from .formula_quality import (_lex,_normalized,_walk_raw_ast,_planned,_ref,_pixels,_HASH,
    _FRACTIONS,_OPERATORS,audit_formula_candidates)

SCHEMA = "b-formula-canvas-check-trial/0.1"
_DEFINITIONS = [{"variant_id":"gray-native","scale":1},{"variant_id":"gray-scale3","scale":3}]
_CONFIG = {"padding_pixels":2,"variants":_DEFINITIONS,"grayscale":"PIL_L","resize":"PIL_LANCZOS","color":"RGB",
    "canvas_multiple":32,"canvas_alignment":"TOP_LEFT","canvas_background":255,"maximum_canvas_size":[672,192],
    "minimum_canvas_size":[32,32],"full_pad_normalization":"MINMAX_UINT8","resizer_maximum_iterations":10,
    "tensor_layout":"NCHW","tensor_dtype":"float32","tensor_channels":1,"normalization_mean":.7931,
    "normalization_std":.1738,"normalization_max_pixel_value":255,"seed":0,"maximum_decode_tokens":128,
    "temperature":.00001,"learned_resizer":True,"trim":False}


def _checked(value,schema,kind):
    return (isinstance(value,dict)and value.get("schema_version") == schema and value.get("kind") == kind
        and type(value.get("revision"))is int and value["revision"] == 1 and isinstance(value.get("payload"),dict)
        and value.get("content_hash") == digest(value["payload"]))


def _finish(layout,observations,candidates,legacy,issues,summary):
    inputs = [_ref(v)for v in (layout,observations,candidates,legacy)if isinstance(v,dict)]
    payload = {"accepted":not issues,"decision":"HOLD","issues":issues,"summary":summary,
        "transcription_verified":False,"business_acceptance":False,"platform_actions":[]}
    producer = {"module":__name__,"version":"0.1.0","code_sha256":code_digest(Path(__file__))}
    return {"schema_version":SCHEMA,"kind":"FormulaCanvasCheckTrial",
        "artifact_id":"formula-canvas-check-"+digest([inputs,payload,producer])[:24],"revision":1,
        **{k:layout.get(k)if isinstance(layout,dict)else None for k in ("book_id","scope_id","run_id")},
        "input_refs":inputs,"producer":producer,"content_hash":digest(payload),"payload":payload}


def _pad(image):
    values = np.asarray(image.convert("L"),dtype="float32")
    low,high = float(values.min()),float(values.max())
    if high != low: values = (values-low)/(high-low)*255
    tile = Image.fromarray(values.astype("uint8"))
    size = (((tile.width+31)//32)*32,((tile.height+31)//32)*32)
    canvas = Image.new("L",size,255)
    canvas.paste(tile,(0,0))
    return canvas,{"input_size":list(image.size),"input_rgb_sha256":_pixels(image.convert("RGB")),
        "output_size":list(size),"output_gray_sha256":_pixels(canvas),"min":low,"max":high,"threshold_crop":False}


def _limit(image):
    before = image
    factor = max(image.width/672,image.height/192)
    if factor > 1:
        dimensions = np.maximum(np.asarray(image.size)//factor,1).astype(int)
        image = image.resize(tuple(dimensions),Image.Resampling.BILINEAR)
    downscaled = list(image.size)
    size = (max(image.width,32),max(image.height,32))
    if size != image.size:
        canvas = Image.new("L",size,255);canvas.paste(image,(0,0));image = canvas
    return image,{"input_size":list(before.size),"input_rgb_sha256":_pixels(before.convert("RGB")),
        "downscaled_size":downscaled,"output_size":list(image.size),"output_rgb_sha256":_pixels(image.convert("RGB"))}


def _tensor(canvas):
    gray = np.asarray(canvas.convert("L"),dtype="<f4")
    mean = np.float32(.7931)*np.float32(255)
    denominator = np.reciprocal(np.float32(.1738)*np.float32(255))
    tensor = np.ascontiguousarray(((gray-mean)*denominator)[None,None,:,:],dtype="<f4")
    return {"tensor_shape":list(tensor.shape),"tensor_dtype":"float32","tensor_sha256":hashlib.sha256(tensor.tobytes()).hexdigest()}


def _metadata_equal(actual,expected):
    if isinstance(expected,dict):
        if not isinstance(actual,dict)or set(actual) != set(expected): return False
        for key,value in expected.items():
            if key in {"source_to_canvas","canvas_to_source"}:
                try:
                    a,b = np.asarray(actual[key],dtype="float64"),np.asarray(value,dtype="float64")
                    if a.shape != (3,3)or not np.isfinite(a).all()or not np.allclose(a,b,rtol=0,atol=1e-9): return False
                except (ValueError,TypeError): return False
            elif not _metadata_equal(actual[key],value): return False
        return True
    if isinstance(expected,list):
        return isinstance(actual,list)and len(actual) == len(expected)and all(_metadata_equal(a,b)for a,b in zip(actual,expected))
    if isinstance(expected,bool): return type(actual)is bool and actual is expected
    return actual == expected


def _canvas_metadata(image,unit,definition,recorded):
    """Replay supplied raw resizer observations; no model predicts new values."""
    scale = definition["scale"]
    tile = image.crop(unit["crop_local_bbox"]).convert("L")
    transformed = tile.resize((tile.width*scale,tile.height*scale),Image.Resampling.LANCZOS).convert("RGB")
    padded,initial_pad = _pad(transformed)
    fixed,initial_minmax = _limit(padded)
    fixed = fixed.convert("RGB")
    steps = recorded.get("steps",[])
    if not 1 <= len(steps) <= 10: raise ValueError("resizer trace must contain 1..10 steps")
    trace = {"initial_pad":initial_pad,"initial_minmax":initial_minmax,"input_image_size":list(fixed.size),
        "input_image_rgb_sha256":_pixels(fixed),"steps":[],"stop_reason":None}
    initial_x = scale*initial_minmax["downscaled_size"][0]/initial_minmax["input_size"][0]
    initial_y = scale*initial_minmax["downscaled_size"][1]/initial_minmax["input_size"][1]
    width,height,ratio = fixed.width,fixed.height,1
    for index,saved in enumerate(steps):
        height = int(height*ratio)
        if width < 1 or height < 1 or width*height > 16_777_216: raise ValueError("unsupported zero-size or oversized resizer canvas")
        interpolation = Image.Resampling.BILINEAR if ratio > 1 else Image.Resampling.LANCZOS
        resized = fixed.resize((width,height),interpolation)
        limited,minmax = _limit(resized)
        padded,pad = _pad(limited)
        canvas = padded.convert("RGB")
        sx = initial_x*width/fixed.width*minmax["downscaled_size"][0]/width
        sy = initial_y*height/fixed.height*minmax["downscaled_size"][1]/height
        x,y = unit["source_bbox"][:2]
        step = {"step_index":index,"requested_ratio":ratio,"requested_size":[width,height],
            "resize_method":"PIL_BILINEAR"if ratio > 1 else"PIL_LANCZOS","resized_rgb_sha256":_pixels(resized),
            "minmax":minmax,"pad":pad,"canvas_size":list(canvas.size),"canvas_rgb_sha256":_pixels(canvas),
            **_tensor(canvas),"source_to_canvas":[[sx,0,-sx*x],[0,sy,-sy*y],[0,0,1]],
            "canvas_to_source":[[1/sx,0,x],[0,1/sy,y],[0,0,1]],"resizer_logits":None,
            "resizer_logits_shape":None,"resizer_logits_dtype":None,"argmax_index":None,
            "next_width":None,"terminated":False,"resizer_error":saved.get("resizer_error")}
        error = saved.get("resizer_error")
        if error is not None:
            if (set(error) != {"type","status"}or not isinstance(error["type"],str)or not error["type"]
                    or error["status"] != "RESIZER_FAILED"): raise ValueError("invalid resizer failure receipt")
            trace["stop_reason"] = "RESIZER_FAILED"
        else:
            dtype = np.dtype(saved.get("resizer_logits_dtype"))
            if dtype.kind not in "fiu"or dtype.itemsize > 8: raise ValueError("invalid resizer numeric dtype")
            logits = np.asarray(saved.get("resizer_logits"),dtype=dtype)
            if (logits.ndim != 2 or logits.shape[0] != 1 or not logits.shape[1]or not np.isfinite(logits).all()
                    or saved.get("resizer_logits_dtype") != str(logits.dtype)
                    or saved.get("resizer_logits_shape") != list(logits.shape)):
                raise ValueError("invalid resizer logits shape/dtype")
            # The serialized values must be actual finite float32 observations.
            if logits.tolist() != saved["resizer_logits"]: raise ValueError("resizer logits changed float32 values")
            argmax = int(logits.argmax(axis=-1).item());next_width = (argmax+1)*32
            step.update(resizer_logits=saved["resizer_logits"],resizer_logits_shape=list(logits.shape),resizer_logits_dtype=str(logits.dtype),
                argmax_index=argmax,next_width=next_width,terminated=next_width == canvas.width)
            if step["terminated"]: trace["stop_reason"] = "WIDTH_STABLE"
        trace["steps"].append(step)
        if trace["stop_reason"]is not None:
            if index != len(steps)-1: raise ValueError("steps present after terminated/failed resizer")
            break
        width = step["next_width"];ratio = width/canvas.width
    if trace["stop_reason"]is None:
        if len(steps) != 10: raise ValueError("resizer trace stopped before width stability or iteration bound")
        trace["stop_reason"] = "MAX_ITERATIONS"
    final = trace["steps"][-1]
    return {**definition,"grayscale":"PIL_L","resize":"PIL_LANCZOS","color":"RGB",
        "transformed_size":list(transformed.size),"transformed_rgb_sha256":_pixels(transformed),
        "transformed_to_source":[[1/scale,0,unit["source_bbox"][0]],[0,1/scale,unit["source_bbox"][1]],[0,0,1]],
        "preprocessing_trace":trace,"paste_offset":[0,0],
        **{k:final[k]for k in ("canvas_size","canvas_rgb_sha256","tensor_shape","tensor_dtype","tensor_sha256","source_to_canvas","canvas_to_source")}}


def _parse(variant,projected,uid,issue):
    raw = variant.get("raw_latex")
    parsed = projected.get("parse_result",{})
    tokens,complete = _lex(raw)
    if (set(parsed) != {"raw_latex","supported","ast","normalized_ast","tokens","errors","unparsed_tail"}
            or parsed.get("raw_latex") != raw or parsed.get("tokens") != tokens):
        issue("FORMULA_CANVAS_RAW_TOKEN_PROJECTION_MISMATCH",uid)
    supported,count,normal = parsed.get("supported"),0,None
    if supported is True:
        try:
            if not complete: raise ValueError("supported AST omitted original source characters")
            count = _walk_raw_ast(parsed.get("ast"),tokens)
            normal = _normalized(parsed["ast"])
            if parsed.get("normalized_ast") != normal or parsed.get("errors") != []or parsed.get("unparsed_tail")is not None:
                raise ValueError("normalized AST or raw status changed")
        except (ValueError,TypeError,KeyError,OverflowError)as exc:
            issue("FORMULA_CANVAS_AST_RAW_MISMATCH",uid,str(exc))
    elif supported is False:
        errors = parsed.get("errors",[])
        if parsed.get("ast")is not None or parsed.get("normalized_ast")is not None or not errors:
            issue("FORMULA_CANVAS_UNPARSED_RAW_DROPPED",uid)
        elif not isinstance(raw,str):
            if errors != [{"code":"FORMULA_NOT_TEXT","position":0}]or parsed.get("unparsed_tail")is not None:
                issue("FORMULA_CANVAS_UNPARSED_RAW_DROPPED",uid)
        else:
            position = errors[0].get("position")
            if type(position)is not int or not 0 <= position <= len(raw)or parsed.get("unparsed_tail") != raw[position:]:
                issue("FORMULA_CANVAS_UNPARSED_RAW_DROPPED",uid)
            else:
                unknown = [t["start"]for t in tokens if t["kind"] == "command"and t["text"]not in _FRACTIONS|_OPERATORS]
                if not complete and len(raw) <= 8192:
                    unread = tokens[-1]["end"]if tokens else 0
                    while unread < len(raw)and raw[unread].isspace(): unread += 1
                    unknown.append(unread)
                if any(position > start for start in unknown): issue("FORMULA_CANVAS_UNPARSED_RAW_DROPPED",uid)
    else: issue("FORMULA_CANVAS_PARSE_STATUS_INVALID",uid)
    shape = bool(supported is True and isinstance(normal,dict)and normal.get("type") == "fraction"and count == 1)
    if (type(projected.get("fraction_node_count"))is not int or projected.get("fraction_node_count") != count
            or projected.get("source_fraction_shape_matches")is not shape):
        issue("FORMULA_CANVAS_FRACTION_STRUCTURE_MISMATCH",uid)
    return supported,normal,shape


def _receipt(producer,issue):
    base = {"module","version","code_sha256","configuration","configuration_sha256","legacy_backend_adapter_code_sha256","execution_kind","backend"}
    if (producer.get("module") != "annotation.recognition.formula_canvas"or producer.get("version") != "0.1.0"
            or producer.get("code_sha256") != code_digest(Path(__file__).with_name("formula_canvas.py"))
            or producer.get("legacy_backend_adapter_code_sha256") != code_digest(Path(__file__).with_name("formula_backend.py"))
            or producer.get("configuration") != _CONFIG or producer.get("configuration_sha256") != digest(_CONFIG)):
        issue("FORMULA_CANVAS_BACKEND_RECEIPT_INVALID")
    kind = producer.get("execution_kind")
    if kind == "SYNTHETIC_TEST":
        if set(producer) != base or producer.get("backend") != "injected-tensor-test-only": issue("FORMULA_CANVAS_BACKEND_RECEIPT_INVALID")
    elif kind == "CPU_RAPID_LATEX_OCR_PRESERVE_CANVAS":
        extra = {"backend_version","providers","dependencies","model_files","backend_code","backend_configuration_sha256","decode_tokens_capped","backend_adapter"}
        files,deps,code = producer.get("model_files",[]),producer.get("dependencies",{}),producer.get("backend_code",{})
        if (set(producer) != base|extra or producer.get("backend") != "rapid-latex-ocr"
                or producer.get("backend_adapter") != "PRESERVE_CANVAS_LEARNED_RESIZER"or producer.get("backend_version") != "0.0.9"
                or producer.get("providers") != [["CPUExecutionProvider"]]*3
                or [f.get("name")for f in files] != ["image_resizer.onnx","encoder.onnx","decoder.onnx","tokenizer.json"]
                or any(type(f.get("bytes"))is not int or f["bytes"] <= 0 or not _HASH.fullmatch(f.get("sha256",""))for f in files)
                or producer.get("decode_tokens_capped") != 128
                or set(deps) != {"rapid-latex-ocr","onnxruntime","numpy","Pillow","tokenizers","opencv-python","PyYAML","chardet"}
                or any(not isinstance(v,str)or not v for v in deps.values())or deps.get("rapid-latex-ocr") != "0.0.9"
                or set(code) != {"main.py","models.py","utils.py","utils_load.py"}
                or any(not _HASH.fullmatch(h)for h in code.values())or not _HASH.fullmatch(producer.get("backend_configuration_sha256",""))):
            issue("FORMULA_CANVAS_BACKEND_RECEIPT_INVALID")
    else: issue("FORMULA_CANVAS_BACKEND_RECEIPT_INVALID")
    return kind


def _audit_canvas_candidates(layout,observations,candidates,crop_path,legacy):
    issues = []
    summary = {"unit_count":0,"variant_count":0,"parsed_candidate_count":0,"unparsed_variant_count":0,
        "disagreement_unit_count":0,"cross_path_disagreement_unit_count":0}
    def issue(code,unit_id=None,detail=None):
        value = {"code":code,"severity":"ERROR","detail":detail}
        if unit_id is not None: value["unit_id"] = unit_id
        if value not in issues: issues.append(value)
    def finish(): return _finish(layout,observations,candidates,legacy,issues,summary)
    for value,schema,kind in ((layout,"b-math-layout-trial/0.1","MathLayoutTrial"),
            (observations,"b-formula-canvas-observation-trial/0.1","FormulaCanvasObservationTrial"),
            (candidates,"b-formula-canvas-candidate-trial/0.1","FormulaCanvasCandidateTrial"),
            (legacy,"b-formula-observation-trial/0.1","FormulaObservationTrial")):
        if not _checked(value,schema,kind): issue("FORMULA_CANVAS_ARTIFACT_INVALID")
    if issues: return finish()
    lp,op,cp = layout["payload"],observations["payload"],candidates["payload"]
    if (observations.get("input_refs") != [_ref(layout)]or op.get("layout_ref") != _ref(layout)
            or candidates.get("input_refs") != [_ref(layout),_ref(observations),_ref(legacy)]
            or cp.get("layout_ref") != _ref(layout)or cp.get("observation_ref") != _ref(observations)
            or cp.get("legacy_observation_ref") != _ref(legacy)or cp.get("legacy_observations_archive") != legacy):
        issue("FORMULA_CANVAS_STALE_OR_LEGACY_REFERENCE")
    for other in (observations,candidates,legacy):
        if any(other.get(k) != layout.get(k)for k in ("book_id","scope_id","run_id")): issue("FORMULA_CANVAS_IDENTITY_MISMATCH")
    for payload in (op,cp):
        if (payload.get("decision") != "HOLD"or payload.get("complete")is not False
                or payload.get("transcription_verified")is not False or payload.get("business_acceptance")is not False
                or payload.get("platform_actions") != []or payload.get("expected_text_consumed")is not False or payload.get("graph_modified")is not False):
            issue("FORMULA_CANVAS_FALSE_VERIFICATION")
    if cp.get("entire_answer_reconstructed")is not False: issue("FORMULA_CANVAS_FALSE_VERIFICATION")
    allowed_obs = {"layout_ref","source","units","decision","complete","transcription_verified","business_acceptance","platform_actions","expected_text_consumed","graph_modified","limitations"}
    allowed_cp = {"layout_ref","observation_ref","source","units","reading_groups","source_layout_issues","issues","decision","complete","transcription_verified","business_acceptance","graph_modified","platform_actions","expected_text_consumed","entire_answer_reconstructed","legacy_observation_ref","legacy_observations_archive","legacy_candidate_ref","legacy_candidate_producer","legacy_candidates_payload"}
    if set(op) != allowed_obs or set(cp) != allowed_cp: issue("FORMULA_CANVAS_UNKNOWN_FIELD")
    producer = observations.get("producer",{})
    kind = _receipt(producer,issue)
    if observations.get("artifact_id") != "formula-canvas-observations-"+digest([observations["input_refs"],producer,op])[:24]:
        issue("FORMULA_CANVAS_OBSERVATION_IDENTITY_MISMATCH")
    candidate_producer = candidates.get("producer",{})
    expected_producer = {"module":"annotation.recognition.formula_canvas","version":"0.1.0",
        "code_sha256":code_digest(Path(__file__).with_name("formula_canvas.py")),
        "syntax_code_sha256":code_digest(Path(__file__).with_name("formula_syntax.py")),
        "legacy_candidate_code_sha256":code_digest(Path(__file__).with_name("formula_candidates.py")),"execution_kind":kind}
    if candidate_producer != expected_producer: issue("FORMULA_CANVAS_CANDIDATE_PRODUCER_MISMATCH")
    if candidates.get("artifact_id") != "formula-canvas-candidates-"+digest([candidates["input_refs"],candidate_producer,cp])[:24]:
        issue("FORMULA_CANVAS_CANDIDATE_IDENTITY_MISMATCH")
    if cp.get("reading_groups") != lp.get("reading_groups")or cp.get("source_layout_issues") != lp.get("issues"):
        issue("FORMULA_CANVAS_LAYOUT_ORDER_CHANGED")
    legacy_ref,legacy_payload = cp.get("legacy_candidate_ref",{}),cp.get("legacy_candidates_payload",{})
    legacy_candidate = {"schema_version":"b-formula-candidate-trial/0.1","kind":"FormulaCandidateTrial",
        **legacy_ref,**{k:layout.get(k)for k in ("book_id","scope_id","run_id")},
        "input_refs":[_ref(layout),_ref(legacy)],"producer":cp.get("legacy_candidate_producer",{}),"payload":legacy_payload}
    legacy_check = audit_formula_candidates(layout,legacy,legacy_candidate,crop_path)
    if not legacy_check["payload"]["accepted"]: issue("FORMULA_CANVAS_LEGACY_INTEGRITY_REJECTED",detail=legacy_check["payload"]["issues"])
    with Image.open(crop_path)as opened: image = opened.convert("RGB")
    crop = lp["crop_bbox"]
    if file_digest(Path(crop_path)) != lp["crop_sha256"]or list(image.size) != [crop[2]-crop[0],crop[3]-crop[1]]:
        issue("FORMULA_CANVAS_SOURCE_PIXELS_MISMATCH")
    source = {k:lp[k]for k in ("asset_id","source_sha256","source_size","crop_bbox","crop_sha256")}
    source["base_crop_rgb_sha256"] = _pixels(image)
    if op.get("source") != source or cp.get("source") != source: issue("FORMULA_CANVAS_SOURCE_BINDING_MISMATCH")
    planned = _planned(layout,image)
    summary["unit_count"] = len(planned)
    raw_units,projected_units = op.get("units",[]),cp.get("units",[])
    if ([u.get("unit_id")for u in raw_units] != [u["unit_id"]for u in planned]
            or [u.get("unit_id")for u in projected_units] != [u["unit_id"]for u in planned]): issue("FORMULA_CANVAS_UNIT_COVERAGE_MISMATCH")
    if len({u["fraction_id"]for u in planned}) != len(planned): issue("FORMULA_CANVAS_SOURCE_UNIT_ID_REUSED")
    old_map = {u.get("unit_id"):u for u in legacy_payload.get("units",[])}
    candidate_ids,expected_issues = [],[]
    for wanted,raw_unit,unit in zip(planned,raw_units,projected_units):
        uid = wanted["unit_id"]
        if {k:v for k,v in raw_unit.items()if k != "variants"} != wanted: issue("FORMULA_CANVAS_UNIT_SOURCE_MISMATCH",uid)
        extra = {"variants","exact_ast_agreement","cross_path_exact_ast_agreement","selected_candidate_refs","complete","transcription_verified","status"}
        if {k:v for k,v in unit.items()if k not in extra} != wanted or set(unit) != set(wanted)|extra:
            issue("FORMULA_CANVAS_CANDIDATE_SOURCE_MISMATCH",uid)
        if (unit.get("selected_candidate_refs") != []or unit.get("complete")is not False or unit.get("transcription_verified")is not False
                or unit.get("status") != "FORMULA_CANVAS_CANDIDATES_UNVERIFIED"): issue("FORMULA_CANVAS_FALSE_VERIFICATION",uid)
        raw_variants,variants = raw_unit.get("variants",[]),unit.get("variants",[])
        if [{k:v.get(k)for k in ("variant_id","scale")}for v in raw_variants] != _DEFINITIONS or len(variants) != 2:
            issue("FORMULA_CANVAS_VARIANT_COVERAGE_MISMATCH",uid)
        normals = []
        old_variants = old_map.get(uid,{}).get("variants",[])
        for definition,raw_variant,variant in zip(_DEFINITIONS,raw_variants,variants):
            summary["variant_count"] += 1
            try:
                metadata = _canvas_metadata(image,wanted,definition,raw_variant.get("preprocessing_trace",{}))
            except (ValueError,TypeError,KeyError,OverflowError)as exc:
                issue("FORMULA_CANVAS_TRACE_INVALID",uid,str(exc))
                continue
            receipt_fields = {"raw_latex","engine_elapsed_seconds","wall_elapsed_seconds","recognition_error","seed","verification_status"}
            if (set(raw_variant) != set(metadata)|receipt_fields or not _metadata_equal({k:raw_variant.get(k)for k in metadata},metadata)
                    or raw_variant.get("seed") != 0 or raw_variant.get("verification_status") != "UNVERIFIED"):
                issue("FORMULA_CANVAS_PIXEL_OR_TENSOR_MISMATCH",uid)
            error,raw = raw_variant.get("recognition_error"),raw_variant.get("raw_latex")
            wall,engine = raw_variant.get("wall_elapsed_seconds"),raw_variant.get("engine_elapsed_seconds")
            valid_number = lambda v:isinstance(v,(int,float))and not isinstance(v,bool)and math.isfinite(v)and v >= 0
            if (not valid_number(wall)or error is None and (not isinstance(raw,str)or not valid_number(engine))
                    or error is not None and (not isinstance(error,dict)or set(error) != {"type","status"}
                        or not isinstance(error.get("type"),str)or not error.get("type")
                        or error.get("status")not in {"RECOGNITION_FAILED","PREPROCESSING_FAILED"}or raw is not None or engine is not None)):
                issue("FORMULA_CANVAS_RAW_RECEIPT_INVALID",uid)
            resizer_error = metadata["preprocessing_trace"]["steps"][-1]["resizer_error"]
            if (resizer_error is not None and error != {"type":resizer_error["type"],"status":"PREPROCESSING_FAILED"}
                    or resizer_error is None and isinstance(error,dict)and error.get("status") == "PREPROCESSING_FAILED"):
                issue("FORMULA_CANVAS_PREPROCESSING_ERROR_MISMATCH",uid)
            added = {"candidate_id","parse_result","fraction_node_count","source_fraction_shape_matches","complete","transcription_verified","legacy_agreement_candidate_refs"}
            if set(variant) != set(raw_variant)|added or any(variant.get(k) != v for k,v in raw_variant.items()): issue("FORMULA_CANVAS_RAW_OBSERVATION_CHANGED",uid)
            cid = "formula-canvas-candidate-"+digest([_ref(observations),uid,definition["variant_id"],raw])[:24]
            if variant.get("candidate_id") != cid: issue("FORMULA_CANVAS_CANDIDATE_REFERENCE_MISMATCH",uid)
            candidate_ids.append(variant.get("candidate_id"))
            if variant.get("complete")is not False or variant.get("transcription_verified")is not False: issue("FORMULA_CANVAS_FALSE_VERIFICATION",uid)
            supported,normal,shape = _parse(raw_variant,variant,uid,issue)
            summary["parsed_candidate_count"] += supported is True
            summary["unparsed_variant_count"] += supported is False
            if supported is False: expected_issues.append({"code":"FORMULA_CANVAS_SYNTAX_UNSUPPORTED","unit_id":uid,"variant_id":definition["variant_id"]})
            elif supported is True and not shape: expected_issues.append({"code":"FORMULA_CANVAS_SOURCE_FRACTION_SHAPE_MISMATCH","unit_id":uid,"variant_id":definition["variant_id"]})
            agreeing = [v["candidate_id"]for v in old_variants if supported is True and v.get("parse_result",{}).get("supported")is True
                and v["parse_result"].get("normalized_ast") == normal]
            if variant.get("legacy_agreement_candidate_refs") != agreeing: issue("FORMULA_CANVAS_LEGACY_AGREEMENT_MISMATCH",uid)
            normals.append(normal if supported is True else None)
        agreement = len(normals) == 2 and all(n is not None for n in normals)and all(n == normals[0]for n in normals)
        cross = (agreement and len(old_variants) == 2 and all(v.get("parse_result",{}).get("supported")is True
            and v["parse_result"].get("normalized_ast") == normals[0]for v in old_variants))
        if unit.get("exact_ast_agreement")is not agreement or unit.get("cross_path_exact_ast_agreement")is not cross:
            issue("FORMULA_CANVAS_FALSE_AGREEMENT",uid)
        if not agreement:
            summary["disagreement_unit_count"] += 1
            expected_issues.append({"code":"FORMULA_CANVAS_VARIANT_DISAGREEMENT_OR_UNPARSED","unit_id":uid})
        if not cross:
            summary["cross_path_disagreement_unit_count"] += 1
            expected_issues.append({"code":"FORMULA_CANVAS_LEGACY_DISAGREEMENT_OR_UNPARSED","unit_id":uid})
    if len(candidate_ids) != len(set(candidate_ids))or any(not v for v in candidate_ids): issue("FORMULA_CANVAS_CANDIDATE_ID_REUSED")
    if cp.get("issues") != expected_issues: issue("FORMULA_CANVAS_RISK_LEDGER_MISMATCH")
    return finish()


def audit_canvas_candidates(layout,observations,candidates,crop_path,legacy_observations):
    """Fail closed on malformed inputs without running OCR or accepting content."""
    try:
        return _audit_canvas_candidates(layout,observations,candidates,crop_path,legacy_observations)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,IndexError,OverflowError,RecursionError)as exc:
        return _finish(layout,observations,candidates,legacy_observations,[{"code":"FORMULA_CANVAS_PERSISTED_DATA_INVALID",
            "severity":"ERROR","detail":type(exc).__name__+": "+str(exc)}],{})
