"""Independent source and lossless-parse audit of unverified formula candidates.

The collector and candidate producer are never imported or executed here.
Acceptance certifies traceability to retained observations, not formula accuracy.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import re

import numpy as np
from PIL import Image, ImageEnhance

from .baseline import code_digest, digest, file_digest, valid_bbox

SCHEMA = "b-formula-check-trial/0.1"
_VARIANTS = (("scale3",3,1.0),("scale4-contrast15",4,1.5))
_HASH = re.compile(r"^[0-9a-f]{64}$")
_CONFIG = {"padding_pixels":2,"variants":[{"variant_id":"scale3","scale":3,"contrast":1.0},
            {"variant_id":"scale4-contrast15","scale":4,"contrast":1.5}],
           "resize":"PIL_LANCZOS","color":"RGB","seed":0,"maximum_decode_tokens":128,"temperature":.00001}
_PRESENTATION = {r"\left",r"\right",r"\displaystyle",r"\textstyle",r"\scriptstyle",r"\scriptscriptstyle",
                 "\\,", "\\;", "\\!", "\\ "}
_FRACTIONS = {r"\frac",r"\dfrac",r"\tfrac"}
_OPERATORS = set("+-=,.<>|") | {r"\cdot",r"\times",r"\div",r"\leq",r"\geq"}


def _lex(raw):
    """Scan source characters independently, retaining exact lexical spans."""
    if not isinstance(raw,str) or len(raw) > 8192:
        return [],False
    tokens,index = [],0
    while index < len(raw):
        start = index
        char = raw[index]
        if char.isspace():
            index += 1
            continue
        if char == "\\":
            index += 1
            while index < len(raw) and raw[index] in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ": index += 1
            if index == start+1:
                if index < len(raw) and raw[index] in ",;! ": index += 1
                else: return tokens,False
            text = raw[start:index]
            kind = "presentation" if text in _PRESENTATION else "command"
        elif char in "0123456789":
            index += 1
            while index < len(raw) and raw[index] in "0123456789": index += 1
            if index+1 < len(raw) and raw[index] == "." and raw[index+1] in "0123456789":
                index += 2
                while index < len(raw) and raw[index] in "0123456789": index += 1
            text,kind = raw[start:index],"number"
        elif char in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
            index += 1
            text,kind = char,"symbol"
        elif char in "{}()[]^_+-=.,|<>":
            index += 1
            text,kind = char,"punctuation"
        else:
            return tokens,False
        tokens.append({"kind":kind,"text":text,"start":start,"end":index})
        if len(tokens) > 2048: return tokens,False
    return tokens,True


def _normalized(value):
    if isinstance(value,list): return [_normalized(v)for v in value]
    if not isinstance(value,dict): return value
    result = {k:_normalized(v)for k,v in value.items()if k != "raw_source_span"}
    if result.get("type") == "group" and result.get("delimiters") == "{}": return result["body"]
    if result.get("type") == "sequence" and len(result["items"]) == 1: return result["items"][0]
    return result


def _walk_raw_ast(ast,tokens):
    """Consume the actual AST against raw tokens, including fraction arguments.

    This never creates an expected AST with the production parser. Every token
    of a supported observation must be owned by exactly one syntactic operation.
    """
    semantic = [t for t in tokens if t["kind"] != "presentation"]
    cursor,fractions = 0,0

    def take(text=None):
        nonlocal cursor
        if cursor >= len(semantic): raise ValueError("AST reads beyond raw tokens")
        token = semantic[cursor]
        cursor += 1
        if text is not None and token["text"] != text: raise ValueError("AST operation differs from raw token")
        return token

    def walk(node,depth=0):
        nonlocal fractions
        if depth > 128 or not isinstance(node,dict): raise ValueError("invalid AST node/depth")
        kind = node.get("type")
        fields = {"type","raw_source_span"}
        if kind in {"number","symbol","operator"}:
            fields.add("value")
            token = take()
            if (node.get("value") != token["text"] or kind == "operator" and token["text"] not in _OPERATORS
                    or kind != "operator" and token["kind"] != kind):
                raise ValueError("AST leaf changed raw symbol")
            span = [token["start"],token["end"]]
        elif kind == "sequence":
            fields.add("items")
            if not isinstance(node.get("items"),list) or not node["items"]: raise ValueError("empty AST sequence")
            spans = [walk(v,depth+1)for v in node["items"]]
            span = [spans[0][0],spans[-1][1]]
        elif kind == "group":
            fields.update(("delimiters","body"))
            pair = node.get("delimiters")
            if pair not in ("{}","()","[]"): raise ValueError("invented delimiters")
            first = take(pair[0]);walk(node.get("body"),depth+1);last = take(pair[1])
            span = [first["start"],last["end"]]
        elif kind == "fraction":
            fractions += 1
            fields.update(("numerator","denominator"))
            first = take()
            if first["text"] not in _FRACTIONS: raise ValueError("fraction not present in raw observation")
            for role in ("numerator","denominator"):
                take("{")
                if node.get(role,{}).get("type") != "sequence": raise ValueError("fraction role scope changed")
                walk(node[role],depth+1)
                last = take("}")
            span = [first["start"],last["end"]]
        elif kind in {"power","subscript"}:
            fields.update(("base","exponent","index"))
            span = walk(node.get("base"),depth+1)
            base = node.get("base")
            while isinstance(base,dict) and base.get("type") in {"power","subscript"}:
                if base["type"] == kind: raise ValueError("repeated script requires explicit grouping")
                base = base.get("base")
            take("^" if kind == "power" else "_")
            arg = node.get("exponent" if kind == "power" else "index")
            if node.get("index" if kind == "power" else "exponent") is not None:
                raise ValueError("unused script role is not null")
            if not isinstance(arg,dict) or arg.get("type") not in {"group","number","symbol","fraction"}:
                raise ValueError("invalid script scope")
            if arg.get("type") == "group" and arg.get("delimiters") != "{}":
                raise ValueError("unbraced script group")
            if arg.get("type") == "number" and len(arg.get("value","")) != 1:
                raise ValueError("unbraced multi-digit script")
            end = walk(arg,depth+1)
            span = [span[0],end[1]]
        else:
            raise ValueError("unknown AST node")
        if (set(node) != fields or node.get("raw_source_span") != span
                or any(type(v) is not int for v in node.get("raw_source_span",[]))):
            raise ValueError("AST span/fields changed raw ownership")
        return span

    if not isinstance(ast,dict) or ast.get("type") != "sequence": raise ValueError("root sequence required")
    walk(ast)
    if cursor != len(semantic): raise ValueError("raw tokens were dropped")
    return fractions


def _ref(value):
    return {k:value.get(k) for k in ("artifact_id","revision","content_hash")}


def _pixels(image):
    return hashlib.sha256(np.asarray(image,dtype="uint8").tobytes()).hexdigest()


def _planned(layout,image):
    payload = layout["payload"]
    crop = payload["crop_bbox"]
    planned = []
    for fraction in payload["fraction_candidates"]:
        boxes = [fraction["bar_bbox"],fraction["numerator"]["pixel_bbox"],fraction["denominator"]["pixel_bbox"]]
        if any(not valid_bbox(b,*payload["source_size"]) or any(type(x) is not int for x in b)
               or not (crop[0] <= b[0] < b[2] <= crop[2] and crop[1] <= b[1] < b[3] <= crop[3]) for b in boxes):
            raise ValueError("invalid source fraction geometry")
        bar,numerator,denominator = boxes
        if (numerator[3] > bar[1]+1 or denominator[1] < bar[3]-1
                or any(min(role[2],bar[2])-max(role[0],bar[0]) <= 0 for role in (numerator,denominator))):
            raise ValueError("fraction numerator/denominator source side changed")
        box = [max(crop[0],min(b[0]for b in boxes)-2),max(crop[1],min(b[1]for b in boxes)-2),
               min(crop[2],max(b[2]for b in boxes)+2),min(crop[3],max(b[3]for b in boxes)+2)]
        local = [box[i]-crop[i % 2] for i in range(4)]
        tile = image.crop(local)
        planned.append({"unit_id":"formula-unit-"+digest([_ref(layout),fraction["fraction_id"],box])[:24],
            "fraction_id":fraction["fraction_id"],"source_bbox":box,"crop_local_bbox":local,
            "bar_bbox":fraction["bar_bbox"],"role_bboxes":{r:fraction[r]["pixel_bbox"]for r in ("numerator","denominator")},
            "source_ocr_refs":{r:fraction[r]["ocr_refs"]for r in ("numerator","denominator")},
            "crop_rgb_sha256":_pixels(tile),"crop_size":list(tile.size)})
    return planned


def _audit_formula_candidates(layout, observations, candidates, crop_path):
    """Verify source pixels and every retained raw result and parse projection."""
    issues = []
    summary = {"unit_count":0,"variant_count":0,"parsed_candidate_count":0,
               "unparsed_variant_count":0,"disagreement_unit_count":0}

    def issue(code,unit_id=None,detail=None):
        item = {"code":code,"severity":"ERROR","detail":detail}
        if unit_id is not None: item["unit_id"] = unit_id
        if item not in issues: issues.append(item)

    def finish():
        payload = {"accepted":not issues,"decision":"HOLD","issues":issues,"summary":summary,
                   "business_acceptance":False,"transcription_verified":False,"platform_actions":[]}
        inputs = [_ref(v) for v in (layout,observations,candidates)]
        producer = {"module":__name__,"version":"0.1.0","code_sha256":code_digest(Path(__file__))}
        return {"schema_version":SCHEMA,"kind":"FormulaCheckTrial",
                "artifact_id":"formula-check-"+digest([inputs,payload,producer])[:24],"revision":1,
                "book_id":layout.get("book_id"),"scope_id":layout.get("scope_id"),"run_id":layout.get("run_id"),
                "input_refs":inputs,"producer":producer,"content_hash":digest(payload),"payload":payload}

    for value,schema,kind in ((layout,"b-math-layout-trial/0.1","MathLayoutTrial"),
            (observations,"b-formula-observation-trial/0.1","FormulaObservationTrial"),
            (candidates,"b-formula-candidate-trial/0.1","FormulaCandidateTrial")):
        if (not isinstance(value,dict) or value.get("schema_version") != schema or value.get("kind") != kind
                or type(value.get("revision")) is not int or value.get("revision") != 1 or not isinstance(value.get("payload"),dict)
                or value.get("content_hash") != digest(value.get("payload"))):
            issue("FORMULA_ARTIFACT_INVALID")
    if issues: return finish()
    lp,op,cp = layout["payload"],observations["payload"],candidates["payload"]
    layout_inputs = layout.get("input_refs",[])
    if (len(layout_inputs) != 3 or layout_inputs[1] != {"asset_id":lp.get("asset_id"),"sha256":lp.get("source_sha256")}
            or layout_inputs[2] != {"crop_sha256":lp.get("crop_sha256")}):
        issue("FORMULA_LAYOUT_SOURCE_REFERENCE_MISMATCH")
    if (observations.get("input_refs") != [_ref(layout)] or op.get("layout_ref") != _ref(layout)
            or cp.get("layout_ref") != _ref(layout) or cp.get("observation_ref") != _ref(observations)
            or candidates.get("input_refs") != [_ref(layout),_ref(observations)]):
        issue("FORMULA_STALE_REFERENCE")
    for other in (observations,candidates):
        if any(other.get(k) != layout.get(k)for k in ("book_id","scope_id","run_id")):
            issue("FORMULA_IDENTITY_MISMATCH")
    for payload in (op,cp):
        if (payload.get("decision") != "HOLD" or payload.get("complete") is not False
                or payload.get("transcription_verified") is not False or payload.get("business_acceptance") is not False
                or payload.get("platform_actions") != [] or payload.get("expected_text_consumed") is not False
                or payload.get("graph_modified") is not False):
            issue("FORMULA_FALSE_VERIFICATION")
    producer = observations.get("producer",{})
    kind = producer.get("execution_kind")
    if producer.get("configuration") != _CONFIG or producer.get("configuration_sha256") != digest(_CONFIG):
        issue("FORMULA_CONFIGURATION_MISMATCH")
    if kind == "SYNTHETIC_TEST":
        if producer.get("backend") != "injected-test-only" or any(k in producer for k in ("model_files","providers","backend_version","dependencies","backend_code")):
            issue("FORMULA_BACKEND_RECEIPT_INVALID")
    elif kind == "CPU_RAPID_LATEX_OCR":
        files = producer.get("model_files",[])
        if (producer.get("backend") != "rapid-latex-ocr" or producer.get("backend_version") != "0.0.9"
                or producer.get("providers") != [["CPUExecutionProvider"]]*3
                or [f.get("name")for f in files] != ["image_resizer.onnx","encoder.onnx","decoder.onnx","tokenizer.json"]
                or any(type(f.get("bytes")) is not int or f["bytes"] <= 0 or not _HASH.fullmatch(f.get("sha256",""))for f in files)
                or producer.get("decode_tokens_capped") != 128
                or set(producer.get("dependencies",{})) != {"rapid-latex-ocr","onnxruntime","numpy","Pillow","tokenizers","opencv-python","PyYAML","chardet"}
                or any(not isinstance(v,str) or not v for v in producer.get("dependencies",{}).values())
                or producer.get("dependencies",{}).get("rapid-latex-ocr") != "0.0.9"
                or set(producer.get("backend_code",{})) != {"main.py","models.py","utils.py","utils_load.py"}
                or any(not _HASH.fullmatch(v)for v in producer.get("backend_code",{}).values())
                or not _HASH.fullmatch(producer.get("backend_configuration_sha256",""))):
            issue("FORMULA_BACKEND_RECEIPT_INVALID")
    else:
        issue("FORMULA_BACKEND_RECEIPT_INVALID")
    if producer.get("version") != "0.1.0" or not _HASH.fullmatch(producer.get("code_sha256","")):
        issue("FORMULA_BACKEND_RECEIPT_INVALID")
    if (producer.get("module") != "annotation.recognition.formula_backend"
            or observations.get("artifact_id") != "formula-observations-"+digest([observations["input_refs"],producer,op])[:24]):
        issue("FORMULA_OBSERVATION_IDENTITY_MISMATCH")
    candidate_producer = candidates.get("producer",{})
    if (candidate_producer.get("execution_kind") != kind or candidate_producer.get("version") != "0.1.0"
            or not _HASH.fullmatch(candidate_producer.get("code_sha256",""))
            or not _HASH.fullmatch(candidate_producer.get("syntax_code_sha256",""))):
        issue("FORMULA_BACKEND_RECEIPT_INVALID")
    if (candidate_producer.get("module") != "annotation.recognition.formula_candidates"
            or candidates.get("artifact_id") != "formula-candidates-"+digest([candidates["input_refs"],candidate_producer,cp])[:24]):
        issue("FORMULA_CANDIDATE_IDENTITY_MISMATCH")
    if (cp.get("reading_groups") != lp.get("reading_groups") or cp.get("source_layout_issues") != lp.get("issues")):
        issue("FORMULA_LAYOUT_ORDER_CHANGED")
    if cp.get("entire_answer_reconstructed") is not False:
        issue("FORMULA_FALSE_VERIFICATION")
    allowed_observation = {"layout_ref","source","units","decision","complete","transcription_verified",
        "business_acceptance","platform_actions","expected_text_consumed","graph_modified","limitations"}
    allowed_candidate = {"layout_ref","observation_ref","source","units","reading_groups","source_layout_issues","issues",
        "decision","complete","transcription_verified","business_acceptance","graph_modified","platform_actions",
        "expected_text_consumed","entire_answer_reconstructed"}
    if set(op) != allowed_observation or set(cp) != allowed_candidate:
        issue("FORMULA_UNKNOWN_FIELD")
    try:
        image = Image.open(crop_path).convert("RGB")
        crop = lp["crop_bbox"]
        if file_digest(Path(crop_path)) != lp["crop_sha256"] or list(image.size) != [crop[2]-crop[0],crop[3]-crop[1]]:
            issue("FORMULA_SOURCE_PIXELS_MISMATCH")
        source = {k:lp[k]for k in ("asset_id","source_sha256","source_size","crop_bbox","crop_sha256")}
        source["base_crop_rgb_sha256"] = _pixels(image)
        if op.get("source") != source or cp.get("source") != source:
            issue("FORMULA_SOURCE_BINDING_MISMATCH")
        planned = _planned(layout,image)
    except (OSError,ValueError,TypeError,KeyError) as exc:
        issue("FORMULA_SOURCE_PIXELS_MISMATCH",detail=str(exc))
        return finish()
    summary["unit_count"] = len(planned)
    if len({u["fraction_id"]for u in planned}) != len(planned):
        issue("FORMULA_SOURCE_UNIT_ID_REUSED")
    units = op.get("units",[])
    if [u.get("unit_id")for u in units] != [u["unit_id"]for u in planned]:
        issue("FORMULA_UNIT_COVERAGE_MISMATCH")
    projected_units = cp.get("units",[])
    if [u.get("unit_id")for u in projected_units] != [u["unit_id"]for u in planned]:
        issue("FORMULA_CANDIDATE_UNIT_COVERAGE_MISMATCH")
    projected_map = {u.get("unit_id"):u for u in projected_units}
    candidate_ids,expected_issues = [],[]
    for wanted,unit in zip(planned,units):
        uid = wanted["unit_id"]
        if any(unit.get(k) != v for k,v in wanted.items()):
            issue("FORMULA_UNIT_SOURCE_MISMATCH",uid)
        if set(unit) != set(wanted) | {"variants"}:
            issue("FORMULA_UNIT_SOURCE_MISMATCH",uid)
        projected = projected_map.get(uid,{})
        if any(projected.get(k) != v for k,v in wanted.items()):
            issue("FORMULA_CANDIDATE_SOURCE_MISMATCH",uid)
        if set(projected) != set(wanted) | {"variants","exact_ast_agreement","selected_candidate_refs","complete","transcription_verified","status"}:
            issue("FORMULA_UNKNOWN_FIELD",uid)
        if (projected.get("selected_candidate_refs") != [] or projected.get("complete") is not False
                or projected.get("transcription_verified") is not False
                or projected.get("status") != "FORMULA_CANDIDATES_UNVERIFIED"):
            issue("FORMULA_FALSE_VERIFICATION",uid)
        variants = unit.get("variants",[])
        summary["variant_count"] += len(variants)
        if [(v.get("variant_id"),v.get("scale"),v.get("contrast"))for v in variants] != list(_VARIANTS):
            issue("FORMULA_VARIANT_COVERAGE_MISMATCH",uid)
        tile = image.crop(wanted["crop_local_bbox"])
        projected_variants = projected.get("variants",[])
        if len(projected_variants) != len(variants):
            issue("FORMULA_CANDIDATE_VARIANT_COVERAGE_MISMATCH",uid)
        normalized = []
        for index,variant in enumerate(variants):
            if set(variant) != {"variant_id","scale","contrast","resize","color","transformed_size","transformed_rgb_sha256",
                    "transformed_to_source","raw_latex","engine_elapsed_seconds","wall_elapsed_seconds","recognition_error","seed","verification_status"}:
                issue("FORMULA_UNKNOWN_FIELD",uid)
            scale,contrast = variant.get("scale"),variant.get("contrast")
            if not isinstance(scale,(int,float)) or scale <= 0:
                issue("FORMULA_TRANSFORM_MISMATCH",uid)
                continue
            transformed = ImageEnhance.Contrast(tile.resize((int(tile.width*scale),int(tile.height*scale)),Image.Resampling.LANCZOS)).enhance(contrast)
            if (variant.get("resize") != "PIL_LANCZOS" or variant.get("color") != "RGB"
                    or variant.get("transformed_size") != list(transformed.size)
                    or variant.get("transformed_rgb_sha256") != _pixels(transformed)
                    or variant.get("transformed_to_source") != [[1/scale,0,wanted["source_bbox"][0]],[0,1/scale,wanted["source_bbox"][1]],[0,0,1]]
                    or variant.get("seed") != 0 or variant.get("verification_status") != "UNVERIFIED"):
                issue("FORMULA_TRANSFORM_MISMATCH",uid)
            error,raw = variant.get("recognition_error"),variant.get("raw_latex")
            if (error is None and (not isinstance(raw,str) or isinstance(variant.get("engine_elapsed_seconds"),bool)
                    or not isinstance(variant.get("engine_elapsed_seconds"),(int,float))
                    or not math.isfinite(variant["engine_elapsed_seconds"]) or variant["engine_elapsed_seconds"] < 0)
                    or error is not None and (raw is not None or variant.get("engine_elapsed_seconds") is not None)):
                issue("FORMULA_RAW_RECEIPT_INVALID",uid)
            pv = projected_variants[index] if index < len(projected_variants) else {}
            candidate_fields = {"candidate_id","parse_result","fraction_node_count","source_fraction_shape_matches","complete","transcription_verified"}
            if set(pv) != set(variant) | candidate_fields or any(pv.get(k) != v for k,v in variant.items()):
                issue("FORMULA_RAW_OBSERVATION_CHANGED",uid)
            cid = "formula-candidate-"+digest([_ref(observations),uid,variant.get("variant_id"),raw])[:24]
            if pv.get("candidate_id") != cid:
                issue("FORMULA_CANDIDATE_REFERENCE_MISMATCH",uid)
            candidate_ids.append(pv.get("candidate_id"))
            if pv.get("complete") is not False or pv.get("transcription_verified") is not False:
                issue("FORMULA_FALSE_VERIFICATION",uid)
            parsed = pv.get("parse_result",{})
            tokenized,lexically_complete = _lex(raw)
            if (set(parsed) != {"raw_latex","supported","ast","normalized_ast","tokens","errors","unparsed_tail"}
                    or parsed.get("raw_latex") != raw or parsed.get("tokens") != tokenized):
                issue("FORMULA_RAW_TOKEN_PROJECTION_MISMATCH",uid)
            supported = parsed.get("supported")
            count,normal = 0,None
            if supported is True:
                summary["parsed_candidate_count"] += 1
                try:
                    if not lexically_complete: raise ValueError("supported parse omitted source characters")
                    count = _walk_raw_ast(parsed.get("ast"),tokenized)
                    normal = _normalized(parsed["ast"])
                    if parsed.get("normalized_ast") != normal or parsed.get("errors") != [] or parsed.get("unparsed_tail") is not None:
                        raise ValueError("normalization/error status changed AST")
                except (ValueError,TypeError,KeyError) as exc:
                    issue("FORMULA_AST_RAW_MISMATCH",uid,str(exc))
            elif supported is False:
                summary["unparsed_variant_count"] += 1
                errors = parsed.get("errors",[])
                if parsed.get("ast") is not None or parsed.get("normalized_ast") is not None or not errors:
                    issue("FORMULA_UNPARSED_RAW_DROPPED",uid)
                elif not isinstance(raw,str):
                    if errors != [{"code":"FORMULA_NOT_TEXT","position":0}] or parsed.get("unparsed_tail") is not None:
                        issue("FORMULA_UNPARSED_RAW_DROPPED",uid)
                else:
                    position = errors[0].get("position")
                    if type(position) is not int or not 0 <= position <= len(raw) or parsed.get("unparsed_tail") != raw[position:]:
                        issue("FORMULA_UNPARSED_RAW_DROPPED",uid)
                    else:
                        unknown_positions = [t["start"]for t in tokenized if t["kind"] == "command"
                                             and t["text"] not in _FRACTIONS | _OPERATORS]
                        if not lexically_complete and len(raw) <= 8192:
                            first_unread = tokenized[-1]["end"] if tokenized else 0
                            while first_unread < len(raw) and raw[first_unread].isspace(): first_unread += 1
                            unknown_positions.append(first_unread)
                        if any(position > unknown for unknown in unknown_positions):
                            issue("FORMULA_UNPARSED_RAW_DROPPED",uid)
                expected_issues.append({"code":"FORMULA_SYNTAX_UNSUPPORTED","unit_id":uid,"variant_id":variant.get("variant_id")})
            else:
                issue("FORMULA_PARSE_STATUS_INVALID",uid)
            shape = bool(supported is True and isinstance(normal,dict) and normal.get("type") == "fraction" and count == 1)
            if type(pv.get("fraction_node_count")) is not int or pv.get("fraction_node_count") != count or pv.get("source_fraction_shape_matches") is not shape:
                issue("FORMULA_FRACTION_STRUCTURE_MISMATCH",uid)
            if supported is True and not shape:
                expected_issues.append({"code":"FORMULA_SOURCE_FRACTION_SHAPE_MISMATCH","unit_id":uid,"variant_id":variant.get("variant_id")})
            normalized.append(normal if supported is True else None)
        agreement = len(normalized) == 2 and all(v is not None for v in normalized) and normalized[0] == normalized[1]
        if projected.get("exact_ast_agreement") is not agreement:
            issue("FORMULA_FALSE_AGREEMENT",uid)
        if not agreement:
            summary["disagreement_unit_count"] += 1
            expected_issues.append({"code":"FORMULA_VARIANT_DISAGREEMENT_OR_UNPARSED","unit_id":uid})
    if len(candidate_ids) != len(set(candidate_ids)) or any(not v for v in candidate_ids):
        issue("FORMULA_CANDIDATE_ID_REUSED")
    if cp.get("issues") != expected_issues:
        issue("FORMULA_RISK_LEDGER_MISMATCH")
    return finish()


def audit_formula_candidates(layout, observations, candidates, crop_path):
    """Return HOLD/rejection rather than crash on malformed retained data."""
    try:
        return _audit_formula_candidates(layout,observations,candidates,crop_path)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,IndexError,RecursionError) as exc:
        payload = {"accepted":False,"decision":"HOLD","issues":[{"code":"FORMULA_PERSISTED_DATA_INVALID",
            "severity":"ERROR","detail":type(exc).__name__+": "+str(exc)}],"summary":{},
            "business_acceptance":False,"transcription_verified":False,"platform_actions":[]}
        inputs = [_ref(v)for v in (layout,observations,candidates)if isinstance(v,dict)]
        producer = {"module":__name__,"version":"0.1.0","code_sha256":code_digest(Path(__file__))}
        return {"schema_version":SCHEMA,"kind":"FormulaCheckTrial",
            "artifact_id":"formula-check-"+digest([inputs,payload,producer])[:24],"revision":1,
            "book_id":layout.get("book_id")if isinstance(layout,dict)else None,
            "scope_id":layout.get("scope_id")if isinstance(layout,dict)else None,
            "run_id":layout.get("run_id")if isinstance(layout,dict)else None,
            "input_refs":inputs,"producer":producer,"content_hash":digest(payload),"payload":payload}
