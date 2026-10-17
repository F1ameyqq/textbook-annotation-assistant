"""Independent raw-source, ROI, canvas, syntax and durable-run audit.

No inline proposer, collector, candidate builder, parser or model is invoked.
Integrity acceptance is distinct from mathematical/transcription acceptance.
"""
from __future__ import annotations

from collections import Counter
from contextlib import closing
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3

from PIL import Image

from .baseline import code_digest,digest,file_digest
from .inline_ocr_quality import audit_inline_ocr
from .formula_canvas_quality import _canvas_metadata,_metadata_equal,_CONFIG as _CANVAS
from .formula_quality import _lex,_normalized,_PRESENTATION

SCHEMA = "b-inline-formula-check-trial/0.1"
_HASH = re.compile(r"^[0-9a-f]{64}$")
_FLAGS = dict(decision="HOLD",complete=False,transcription_verified=False,business_acceptance=False,
              platform_actions=[],graph_modified=False,expected_text_consumed=False)
_OPERATORS = set("=+-−×÷*/<>≤≥≠≈±∓√∛∜^_%∞∑∏∫∂∇∈∉∪∩∠⊥∥°:＝＋－＜＞")
_SCRIPTS = set("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")
_MATH_CONFIG = {"policy":"ALL_RAW_MATHLIKE_RUNS_WITH_FULL_LINE_FALLBACK/0.1","source_row_padding":2,
    "variants":[{"variant_id":"scale3","scale":3},{"variant_id":"scale4","scale":4}],"resampling":"PIL_LANCZOS",
    "horizontal_halo":{"minimum_source_pixels":4,"full_crop_height_multiplier":1},"vertical_policy":"ENTIRE_ORIGINAL_ROW_CROP_HEIGHT_NO_TRIM",
    "rounding":"FLOOR_MIN_CEIL_MAX_CLAMP_ORIGINAL_PAGE","ambiguous_bridge":"DECIMAL_DIGIT_TEN_CHARACTER_DECIMAL_DIGIT_ONLY",
    "text_policy":"VERBATIM_NO_OPERATOR_OR_EXPONENT_CORRECTION","overlap_policy":"RETAIN_ALL_NO_NMS_NO_SELECTION"}
_CONFIG = {"eligibility":"MATHLIKE_RUN_WITH_OPERAND_AND_ARITHMETIC_MARKER_OR_AMBIGUOUS_TEN_BRIDGE/0.1",
    "arithmetic_markers":"=+-−×÷*/<>≤≥≠≈±∓√∛∜^_:²³⁴⁵⁶⁷⁸⁹⁰∑∏∫∂∇∈∉∪∩∠⊥∥","regions":["CORE_CONTEXT_PAD2","HALO"],"core_padding_pixels":2,
    "vertical_policy":"FULL_SOURCE_ROW_CROP_HEIGHT","deduplication":"EXACT_SOURCE_BBOX_AND_CANVAS_VARIANT_ONLY",
    "elapsed_policy":"CALL_WALL_INCLUDING_PREPROCESSING_OR_SYNTHETIC_DECLARATION","canvas":_CANVAS,"selection":"NONE"}
_BASE_RISKS = ["CTC_ESTIMATED_POSITION","MISSING_GLYPH_NOT_LOCALIZED","COMPLETE_MATH_COVERAGE_UNPROVEN"]


def _ref(v): return {k:v.get(k)if isinstance(v,dict)else None for k in ("artifact_id","revision","content_hash")}
def _pixels(image): return hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()
def _finite(v): return type(v)in (int,float)and math.isfinite(v)
def _json(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
def _core(c): return c.isdecimal()or "A" <= c <= "Z"or "a" <= c <= "z"or "\u0370" <= c <= "\u03ff"or c in _OPERATORS|_SCRIPTS


def _spans(text):
    """Independent maximal-source-run membership, retaining ambiguous bridges."""
    ranges=[];start=None
    for i,c in enumerate(text+"\0"):
        allowed = i < len(text)and (_core(c)or c in "()[]{}（）［］｛｝.．, "or c.isspace()
            or c == "十"and 0 < i < len(text)-1 and text[i-1].isdecimal()and text[i+1].isdecimal())
        if allowed and start is None: start=i
        if not allowed and start is not None:
            lo,hi=start,i
            while lo < hi and text[lo].isspace():lo+=1
            while hi > lo and text[hi-1].isspace():hi-=1
            if any(_core(x)for x in text[lo:hi]): ranges.append([lo,hi])
            start=None
    return ranges


def _word(box,variant):
    if (not isinstance(box,list)or len(box)!=4 or any(not isinstance(p,list)or len(p)!=2 or not all(_finite(n)for n in p)for p in box)):
        return None,["CTC_WORD_GEOMETRY_INVALID"]
    scale=variant["scale"];x,y=variant["variant_to_original"][0][2],variant["variant_to_original"][1][2]
    points=[[p[0]/scale+x,p[1]/scale+y]for p in box];risks=[]
    if any(not 0<=p[0]<=variant["size"][0]or not 0<=p[1]<=variant["size"][1]for p in box):risks.append("CTC_WORD_OUTSIDE_INPUT")
    if sum(box[i][0]*box[(i+1)%4][1]-box[(i+1)%4][0]*box[i][1]for i in range(4))==0:risks.append("CTC_DEGENERATE_WORD_ESTIMATE")
    return points,risks


def _unit(obs,row,variant,image,raw_index=None,span=None,text=None,indices=None,polygons=None,risks=()):
    box=list(row["crop_bbox"]);halo=max(4,box[3]-box[1]);core=None;warnings=list(_BASE_RISKS)+list(risks)
    if polygons is not None:
        if polygons and all(p is not None for p in polygons):
            p=[point for polygon in polygons for point in polygon]
            core=[min(x[0]for x in p),min(x[1]for x in p),max(x[0]for x in p),max(x[1]for x in p)]
            requested=[math.floor(core[0])-halo,box[1],math.ceil(core[2])+halo,box[3]]
            clipped=[max(0,requested[0]),requested[1],min(image.width,requested[2]),requested[3]]
            if clipped[0]<clipped[2]:
                box=clipped
                if box!=requested:warnings.append("SOURCE_EDGE_CONTEXT_CLAMPED")
                if box[0]<row["crop_bbox"][0]or box[2]>row["crop_bbox"][2]:warnings.append("CONTEXT_OUTSIDE_RECOGNITION_CROP")
            else:warnings.append("CTC_ROI_OUTSIDE_SOURCE_FULL_LINE_FALLBACK")
        else:warnings.append("UNLOCATED_MATH_RUN_FULL_LINE_FALLBACK")
    p={"kind":"FULL_LINE_FALLBACK"if span is None else"MATHLIKE_RUN","line_id":row["line_id"],"row_id":row["row_id"],"asset_id":row["asset_id"],
        "variant_id":variant["variant_id"],"raw_result_index":raw_index,"char_span":span,"raw_text":text,"raw_word_indices":indices or[],
        "core_source_bbox":core,"source_bbox":box,"crop_size":[box[2]-box[0],box[3]-box[1]],"crop_rgb_sha256":_pixels(image.crop(box)),
        "horizontal_halo_source_pixels":halo,"variant_to_original":variant["variant_to_original"],"risks":sorted(set(warnings)),
        "verification_status":"UNVERIFIED","complete":False,"localization_kind":"CTC_TIMESTEP_ESTIMATE",
        "precise_glyph_localization":False,"spatial_role_verified":False,"selected":False}
    return {"unit_id":"inline-math-unit-"+digest([_ref(obs),p])[:24],**p}


def _layout(evidence,layout,image,original,line_ids,issue):
    p=layout["payload"];obs=p["observations_archive"]
    check=audit_inline_ocr(evidence,obs,original,line_ids=line_ids)
    if not check["payload"]["accepted"]:issue("INLINE_FORMULA_OCR_BINDING_REJECTED",check["payload"]["issues"])
    producer={"module":"annotation.recognition.inline_math","version":"0.1.0","code_sha256":code_digest(Path(__file__).with_name("inline_math.py")),
        "dependency_code_sha256":{"baseline":code_digest(Path(__file__).with_name("baseline.py"))},"execution_kind":"GEOMETRIC_INLINE_PROPOSAL_NO_OCR",
        "configuration_sha256":digest(_MATH_CONFIG)}
    inputs=[_ref(evidence),_ref(obs)]
    header_fields={"schema_version","kind","artifact_id","revision","book_id","scope_id","input_refs","producer","content_hash","payload"}
    if (set(layout)!=header_fields or layout.get("schema_version")!="b-inline-math-layout-trial/0.1"or layout.get("kind")!="InlineMathLayoutTrial"or layout.get("producer")!=producer
            or layout.get("input_refs")!=inputs or layout.get("artifact_id")!="inline-math-layout-"+digest([inputs,producer,p])[:24]
            or layout.get("content_hash")!=digest(p)or layout.get("revision")!=1 or any(layout.get(k)!=evidence[k]for k in ("book_id","scope_id"))):
        issue("INLINE_FORMULA_LAYOUT_HEADER_INVALID")
    units,rows=[],[];raw_count=0
    for row in obs["payload"]["rows"]:
        summary={k:row[k]for k in ("line_id","row_id","asset_id","source_line","bbox","crop_bbox","crop_size","crop_rgb_sha256")};summary["variants"]=[]
        for variant in row["variants"]:
            fallback=_unit(obs,row,variant,image,risks=["ROW_RECOGNITION_FAILED"]if variant["recognition_error"]is not None else[]);units.append(fallback)
            raw=variant["raw_ocr_result"]
            vs={"variant_id":variant["variant_id"],"full_line_fallback_unit_id":fallback["unit_id"],"mathlike_unit_ids":[],"raw_row_count":len(raw)if isinstance(raw,list)else 0,"issues":[]}
            summary["variants"].append(vs)
            if not isinstance(raw,list):vs["issues"].append({"code":"RAW_ROWS_UNAVAILABLE_FULL_LINE_RETAINED"});continue
            raw_count+=len(raw)
            for i,entry in enumerate(raw):
                if not isinstance(entry,list)or len(entry)!=6:vs["issues"].append({"code":"RAW_ROW_INVALID_FULL_LINE_RETAINED","raw_result_index":i});continue
                _,text,_,boxes,words,scores=entry
                if (not isinstance(text,str)or not all(isinstance(a,list)for a in (boxes,words,scores))or not all(isinstance(w,str)for w in words)
                        or not len(boxes)==len(words)==len(scores)or "".join(words)!=text):
                    vs["issues"].append({"code":"RAW_CHARACTER_ALIGNMENT_UNRESOLVED_FULL_LINE_RETAINED","raw_result_index":i});continue
                word_owners=[j for j,w in enumerate(words)for _ in w]
                for span in _spans(text):
                    indices=list(dict.fromkeys(word_owners[span[0]:span[1]]));polygons=[];risks=[]
                    for j in indices:
                        points,r=_word(boxes[j],variant);polygons.append(points);risks.extend(r)
                        if not _finite(scores[j])or not 0<=scores[j]<=1:risks.append("CHARACTER_SCORE_INVALID")
                        elif scores[j]<.8:risks.append("LOW_CHARACTER_SCORE")
                    value=text[span[0]:span[1]]
                    if "十"in value:risks.append("CHINESE_TEN_OPERATOR_LOOKALIKE_UNRESOLVED")
                    if len(indices)==1:risks.append("SINGLE_ESTIMATED_TOKEN_MAY_BE_PROSE_OR_REFERENCE")
                    unit=_unit(obs,row,variant,image,i,span,value,indices,polygons,risks);units.append(unit);vs["mathlike_unit_ids"].append(unit["unit_id"])
        rows.append(summary)
    runs=sum(u["kind"]=="MATHLIKE_RUN"for u in units)
    fields={"evidence_ref":_ref(evidence),"observation_ref":_ref(obs),"source":obs["payload"]["source"],"requested_line_ids":list(line_ids),"configuration":_MATH_CONFIG,
        "rows":rows,"units":units,"counts":{"declared_rows":len(rows),"variants":sum(len(r["variants"])for r in rows),"raw_rows":raw_count,
        "mathlike_runs":runs,"full_line_fallbacks":len(units)-runs,"units":len(units)},"selected_unit_ids":[],"verification_status":"UNVERIFIED","model_calls":0,**_FLAGS}
    if any(p.get(k)!=v for k,v in fields.items())or set(p)!=set(fields)|{"observations_archive","limitations"}:issue("INLINE_FORMULA_MATH_SOURCE_PROJECTION_MISMATCH")
    return units,rows


def _plans(layout,units,rows,image):
    calls,skipped,indices=[],[],{};by_row={r["line_id"]:r for r in rows}
    for unit in units:
        text=unit["raw_text"]or""
        operand=any(c.isdigit()or "A"<=c<="Z"or "a"<=c<="z"or "\u0370"<=c<="\u03ff"for c in text)
        eligible=(unit["kind"]=="MATHLIKE_RUN"and operand
            and(any(c in _CONFIG["arithmetic_markers"]for c in text)or"CHINESE_TEN_OPERATOR_LOOKALIKE_UNRESOLVED"in unit["risks"]))
        if not eligible:
            skipped.append({"unit_id":unit["unit_id"],"reason":"FULL_ROW_CONTEXT_ONLY"if unit["kind"]=="FULL_LINE_FALLBACK"else"NO_OPERAND_AND_ARITHMETIC_OR_AMBIGUOUS_BRIDGE",
                "raw_text":unit["raw_text"],"inference_performed":False});continue
        row=by_row[unit["line_id"]];core=unit["core_source_bbox"]
        box=list(row["crop_bbox"])if core is None else[max(0,math.floor(core[0])-2),row["crop_bbox"][1],min(image.width,math.ceil(core[2])+2),row["crop_bbox"][3]]
        if box[2]<=box[0]:box=list(row["crop_bbox"])
        for region,bbox in (("CORE_CONTEXT_PAD2",box),("HALO",unit["source_bbox"])):
            for definition in _CANVAS["variants"]:
                key=digest([_ref(layout),bbox,definition]);binding={"unit_id":unit["unit_id"],"line_id":unit["line_id"],"region_variant":region}
                if key in indices:calls[indices[key]]["unit_bindings"].append(binding);continue
                indices[key]=len(calls)
                calls.append({"call_id":"inline-formula-call-"+key[:24],"source_bbox":bbox,"crop_local_bbox":bbox,"crop_size":[bbox[2]-bbox[0],bbox[3]-bbox[1]],
                    "crop_rgb_sha256":_pixels(image.crop(bbox)),"canvas_variant":definition,"unit_bindings":[binding],"localization_kind":"CTC_TIMESTEP_ESTIMATE","source_glyph_complete":False})
    return calls,skipped


_PARSE_OPS=set("+-=,.<>|:")|{r"\cdot",r"\times",r"\div",r"\leq",r"\geq",r"\because",r"\therefore",r"\approx",r"\neq"}
_STYLES={r"\mathrm",r"\mathbf",r"\mathit",r"\text"}
_SYMBOLS={r"\pi",r"\alpha",r"\beta",r"\gamma",r"\theta",r"\ell"}
_FRACS={r"\frac",r"\dfrac",r"\tfrac"}


def _inline_tokens(raw):
    # Colon has the same lexical width as '+'. Restore exact raw token text;
    # no production lexer/parser is imported or used to manufacture an AST.
    tokens,complete=_lex(raw.replace(":","+")if isinstance(raw,str)else raw)
    if isinstance(raw,str):
        for token in tokens:token["text"]=raw[token["start"]:token["end"]]
    return tokens,complete


def _walk_inline(ast,tokens):
    source=[t for t in tokens if t["kind"]!="presentation"];cursor=0
    def take(text=None):
        nonlocal cursor
        if cursor>=len(source):raise ValueError("AST exceeds retained raw tokens")
        token=source[cursor];cursor+=1
        if text is not None and token["text"]!=text:raise ValueError("AST changes raw operation")
        return token
    def argument(node):
        if not isinstance(node,dict):raise ValueError("missing raw argument")
        if node.get("type")=="group":
            if node.get("delimiters")!="{}":raise ValueError("argument needs braces")
        elif node.get("type")=="number"and len(node.get("value",""))!=1:raise ValueError("unbraced multidigit argument")
        elif node.get("type")not in {"number","symbol","fraction","radical","styled"}:raise ValueError("unsupported argument scope")
        return walk(node)
    def walk(node,depth=0):
        if depth>128 or not isinstance(node,dict):raise ValueError("invalid AST depth/node")
        kind=node.get("type");keys={"type","raw_source_span"}
        if kind in {"number","symbol","operator"}:
            keys.add("value");t=take();value=node.get("value")
            if value!=t["text"]or(kind=="operator"and value not in _PARSE_OPS)or(kind=="number"and t["kind"]!="number")or(kind=="symbol"and not(t["kind"]=="symbol"or value in _SYMBOLS)):
                raise ValueError("AST invents a raw leaf")
            span=[t["start"],t["end"]]
        elif kind=="sequence":
            keys.add("items")
            if not isinstance(node.get("items"),list)or not node["items"]:raise ValueError("empty sequence")
            spans=[walk(n,depth+1)for n in node["items"]];span=[spans[0][0],spans[-1][1]]
        elif kind=="group":
            keys|={"delimiters","body"};pair=node.get("delimiters")
            if pair not in {"{}","()","[]"}:raise ValueError("invented delimiter")
            first=take(pair[0]);walk(node.get("body"),depth+1);last=take(pair[1]);span=[first["start"],last["end"]]
        elif kind=="fraction":
            keys|={"numerator","denominator"};first=take()
            if first["text"]not in _FRACS:raise ValueError("fraction absent from raw")
            for role in ("numerator","denominator"):
                take("{")
                if node.get(role,{}).get("type")!="sequence":raise ValueError("fraction role must own its full sequence")
                walk(node[role],depth+1);last=take("}")
            span=[first["start"],last["end"]]
        elif kind=="radical":
            keys|={"index","radicand"};first=take(r"\sqrt")
            index=node.get("index")
            if index is not None:
                if not isinstance(index,dict)or index.get("type")!="group"or index.get("delimiters")!="[]":raise ValueError("radical index scope changed")
                walk(index,depth+1)
            end=argument(node.get("radicand"));span=[first["start"],end[1]]
        elif kind=="styled":
            keys|={"style","body"};first=take(node.get("style"))
            if first["text"]not in _STYLES or node.get("body",{}).get("type")!="group"or node["body"].get("delimiters")!="{}":raise ValueError("styled raw scope changed")
            end=walk(node["body"],depth+1);span=[first["start"],end[1]]
        elif kind in {"power","subscript"}:
            keys|={"base","exponent","index"};begin=walk(node.get("base"),depth+1)
            base=node.get("base")
            while isinstance(base,dict)and base.get("type")in {"power","subscript"}:
                if base["type"]==kind:raise ValueError("repeated ungrouped script")
                base=base.get("base")
            take("^"if kind=="power"else"_")
            if node.get("index"if kind=="power"else"exponent")is not None:raise ValueError("extra script role")
            end=argument(node.get("exponent"if kind=="power"else"index"));span=[begin[0],end[1]]
        else:raise ValueError("unsupported AST node")
        if set(node)!=keys or node.get("raw_source_span")!=span or any(type(n)is not int for n in node.get("raw_source_span",[])):raise ValueError("AST fields/span changed raw token ownership")
        return span
    if not isinstance(ast,dict)or ast.get("type")!="sequence":raise ValueError("AST root is not a sequence")
    walk(ast)
    if cursor!=len(source):raise ValueError("AST silently dropped raw tokens")


def _parse(raw,parsed,issue,call_id,risks):
    tokens,complete=_inline_tokens(raw)
    keys={"raw_latex","supported","ast","normalized_ast","tokens","errors","unparsed_tail","syntax_profile"}
    if (not isinstance(parsed,dict)or set(parsed)!=keys or parsed.get("raw_latex")!=raw or parsed.get("tokens")!=tokens
            or type(parsed.get("supported"))is not bool or parsed.get("syntax_profile")!="INLINE_ARITHMETIC_RADICAL/0.1"):
        issue("INLINE_FORMULA_PARSE_RAW_OR_TOKEN_MISMATCH",call_id);return
    if parsed["supported"]:
        try:
            if not complete or parsed["errors"]!=[]or parsed["unparsed_tail"]is not None:raise ValueError("supported parse drops lexical tail")
            _walk_inline(parsed["ast"],tokens)
            if parsed["normalized_ast"]!=_normalized(parsed["ast"]):raise ValueError("normalized tree changes raw AST")
        except (ValueError,TypeError,KeyError,IndexError,RecursionError)as exc:issue("INLINE_FORMULA_AST_RAW_PROJECTION_MISMATCH",{"call_id":call_id,"reason":str(exc)})
    else:
        errors=parsed.get("errors")
        if parsed.get("ast")is not None or parsed.get("normalized_ast")is not None or not isinstance(errors,list)or not errors:
            issue("INLINE_FORMULA_UNSUPPORTED_RAW_LOST",call_id)
        elif isinstance(raw,str):
            position=errors[0].get("position")
            if type(position)is not int or not 0<=position<=len(raw)or parsed.get("unparsed_tail")!=raw[position:]:issue("INLINE_FORMULA_UNSUPPORTED_RAW_LOST",call_id)
            known=_PARSE_OPS|_STYLES|_SYMBOLS|_FRACS|_PRESENTATION|{r"\sqrt"}
            unknown=[t["start"]for t in tokens if t["kind"]=="command"and t["text"]not in known]
            if not complete and len(raw)<=8192:
                stopped=tokens[-1]["end"]if tokens else 0
                while stopped<len(raw)and raw[stopped].isspace():stopped+=1
                unknown.append(stopped)
            if unknown and(type(position)is not int or position>min(unknown)):issue("INLINE_FORMULA_UNKNOWN_SYNTAX_TAIL_DROPPED",call_id)
        elif parsed.get("unparsed_tail")is not None:issue("INLINE_FORMULA_UNSUPPORTED_RAW_LOST",call_id)
        risks.append({"code":"INLINE_FORMULA_SYNTAX_UNSUPPORTED","call_id":call_id,"severity":"REVIEW"})


def _envelope(value,schema,kind,prefix,layout,producer,inputs,issue):
    keys={"schema_version","kind","revision","book_id","scope_id","input_refs","producer","payload","artifact_id","content_hash"}
    body={k:v for k,v in value.items()if k not in {"artifact_id","content_hash"}}
    if (set(value)!=keys or value.get("schema_version")!=schema or value.get("kind")!=kind or value.get("revision")!=1
            or any(value.get(k)!=layout[k]for k in ("book_id","scope_id"))or value.get("producer")!=producer
            or value.get("input_refs")!=inputs or value.get("content_hash")!=digest(value.get("payload"))or value.get("artifact_id")!=prefix+"-"+digest(body)[:24]):
        issue("INLINE_FORMULA_ARTIFACT_HEADER_INVALID",kind)


def _backend(producer,has_calls,issue):
    base={"module","version","code_sha256","dependency_code_sha256","configuration","configuration_sha256","execution_kind","backend"}
    names=("inline_math","formula_backend","formula_canvas","batch","baseline")
    if (producer.get("module")!="annotation.recognition.inline_formula"or producer.get("version")!="0.1.0"
            or producer.get("code_sha256")!=code_digest(Path(__file__).with_name("inline_formula.py"))
            or producer.get("dependency_code_sha256")!={n:code_digest(Path(__file__).with_name(n+".py"))for n in names}
            or producer.get("configuration")!=_CONFIG or producer.get("configuration_sha256")!=digest(_CONFIG)):
        issue("INLINE_FORMULA_IMPLEMENTATION_OR_CONFIGURATION_MISMATCH")
    kind=producer.get("execution_kind")
    if kind=="SYNTHETIC_TEST":
        if set(producer)!=base|{"worker_identity"}or producer.get("backend")!="injected-tensor-test-only"or not isinstance(producer.get("worker_identity"),dict):issue("INLINE_FORMULA_BACKEND_RECEIPT_INVALID")
    elif kind=="NO_ELIGIBLE_INLINE_FORMULA_CALLS":
        if has_calls or set(producer)!=base or producer.get("backend")!="source-geometry-only":issue("INLINE_FORMULA_BACKEND_RECEIPT_INVALID")
    elif kind=="CPU_RAPID_LATEX_OCR_INLINE":
        extra={"backend_version","providers","dependencies","model_files","backend_code","backend_configuration_sha256","decode_tokens_capped","backend_adapter"}
        models=producer.get("model_files",[]);deps=producer.get("dependencies",{});code=producer.get("backend_code",{})
        if (set(producer)!=base|extra or producer.get("backend")!="rapid-latex-ocr"or producer.get("backend_version")!="0.0.9"
                or producer.get("providers")!=[["CPUExecutionProvider"]]*3 or producer.get("backend_adapter")!="PRESERVE_CANVAS_LEARNED_RESIZER"
                or producer.get("decode_tokens_capped")!=128 or [f.get("name")for f in models]!=["image_resizer.onnx","encoder.onnx","decoder.onnx","tokenizer.json"]
                or any(set(f)!={"name","sha256","bytes"}or type(f.get("bytes"))is not int or f["bytes"]<=0 or not _HASH.fullmatch(f.get("sha256",""))for f in models)
                or set(deps)!={"rapid-latex-ocr","onnxruntime","numpy","Pillow","tokenizers","opencv-python","PyYAML","chardet"}
                or deps.get("rapid-latex-ocr")!="0.0.9"or any(not isinstance(v,str)or not v for v in deps.values())
                or set(code)!={"main.py","models.py","utils.py","utils_load.py"}or any(not _HASH.fullmatch(v)for v in code.values())
                or not _HASH.fullmatch(producer.get("backend_configuration_sha256",""))):issue("INLINE_FORMULA_BACKEND_RECEIPT_INVALID")
    else:issue("INLINE_FORMULA_BACKEND_RECEIPT_INVALID")
    return kind


def _call(call,plan,layout,producer,image,kind,issue,risks):
    state=call.get("state");value=call.get("observation")
    if call.get("plan")!=plan or set(call)!={"plan","state","observation"}or state not in {"DONE","FAILED","PENDING"}:issue("INLINE_FORMULA_CALL_PLAN_OR_STATE_MISMATCH",plan["call_id"])
    if state=="PENDING":
        if value is not None:issue("INLINE_FORMULA_PENDING_HAS_RESULT",plan["call_id"])
        return
    if not isinstance(value,dict):issue("INLINE_FORMULA_OBSERVATION_MISSING",plan["call_id"]);return
    _envelope(value,"b-inline-formula-call-trial/0.1","InlineFormulaCallTrial","inline-formula-observed-call",layout,producer,[_ref(layout)],issue)
    p=value["payload"]
    expected=set(_FLAGS)|{"plan","preprocessing","raw_latex","decoded_text","raw_token_ids","recognition_error","encoder_decoder_called",
        "raw_backend_elapsed_seconds","engine_elapsed_seconds","wall_elapsed_seconds"}
    if set(p)!=expected or p.get("plan")!=plan or any(p.get(k)!=v for k,v in _FLAGS.items()):issue("INLINE_FORMULA_CALL_FALSE_VERIFICATION_OR_SOURCE",plan["call_id"])
    if not _finite(p.get("wall_elapsed_seconds"))or p["wall_elapsed_seconds"]<0:issue("INLINE_FORMULA_CALL_TIME_INVALID",plan["call_id"])
    metadata=p.get("preprocessing")
    if metadata is not None:
        try:
            expected_metadata=_canvas_metadata(image,plan,plan["canvas_variant"],metadata["preprocessing_trace"])
            if not _metadata_equal(metadata,expected_metadata):issue("INLINE_FORMULA_CANVAS_OR_TENSOR_MISMATCH",plan["call_id"])
        except (ValueError,TypeError,KeyError,IndexError,OverflowError)as exc:issue("INLINE_FORMULA_CANVAS_TRACE_INVALID",{"call_id":plan["call_id"],"reason":str(exc)})
    if state=="DONE":
        if (p.get("recognition_error")is not None or metadata is None or metadata.get("preprocessing_trace",{}).get("stop_reason")=="RESIZER_FAILED"
                or p.get("encoder_decoder_called")is not True or not isinstance(p.get("raw_latex"),str)or not isinstance(p.get("decoded_text"),str)
                or not _finite(p.get("engine_elapsed_seconds"))or p["engine_elapsed_seconds"]<0):issue("INLINE_FORMULA_DONE_CALL_INVALID",plan["call_id"])
    else:
        error=p.get("recognition_error")
        if (not isinstance(error,dict)or set(error)!={"type","status"}or not isinstance(error.get("type"),str)or not error["type"]
                or error.get("status")!="RECOGNITION_FAILED"or p.get("engine_elapsed_seconds")is not None):issue("INLINE_FORMULA_FAILED_CALL_INVALID",plan["call_id"])
        risks.append({"code":"INLINE_FORMULA_CALL_FAILED","call_id":plan["call_id"],"severity":"REVIEW","raw_text_retained":isinstance(p.get("raw_latex"),str)})
    if type(p.get("encoder_decoder_called"))is not bool:issue("INLINE_FORMULA_ENCODER_CALL_STATUS_INVALID",plan["call_id"])
    raw_elapsed=p.get("raw_backend_elapsed_seconds")
    if raw_elapsed is not None and not _finite(raw_elapsed):issue("INLINE_FORMULA_CALL_TIME_INVALID",plan["call_id"])
    if kind=="SYNTHETIC_TEST":
        if p.get("raw_token_ids")is not None or p.get("decoded_text")!=p.get("raw_latex"):issue("INLINE_FORMULA_SYNTHETIC_DECODE_MISMATCH",plan["call_id"])
        if state=="DONE"and p.get("engine_elapsed_seconds")!=raw_elapsed:issue("INLINE_FORMULA_CALL_TIME_INVALID",plan["call_id"])
    elif kind=="CPU_RAPID_LATEX_OCR_INLINE"and p.get("encoder_decoder_called"):
        tokens=p.get("raw_token_ids")
        if (p.get("decoded_text")is not None and(not isinstance(tokens,list)or len(tokens)!=1 or not isinstance(tokens[0],list)
            or not tokens[0]or any(type(t)is not int or t<0 for t in tokens[0]))):issue("INLINE_FORMULA_CPU_RAW_TOKEN_RECEIPT_INVALID",plan["call_id"])
        if raw_elapsed is not None:issue("INLINE_FORMULA_CPU_TIME_RECEIPT_INVALID",plan["call_id"])
        if isinstance(p.get("raw_latex"),str)and isinstance(p.get("decoded_text"),str)and p["raw_latex"]!=p["decoded_text"]:
            risks.append({"code":"INLINE_FORMULA_DECODE_POSTPROCESS_DIFFERENCE","call_id":plan["call_id"],"severity":"REVIEW",
                "decoded_text":p["decoded_text"],"postprocessed_raw_latex":p["raw_latex"],"content_verified":False})


def _candidates(observations,candidates,issue,risks):
    producer={"module":"annotation.recognition.inline_candidates","version":"0.1.0","code_sha256":code_digest(Path(__file__).with_name("inline_candidates.py")),
        "syntax_code_sha256":code_digest(Path(__file__).with_name("formula_syntax.py"))}
    _envelope(candidates,"b-inline-formula-candidate-trial/0.1","InlineFormulaCandidateTrial","inline-formula-candidates",observations,producer,[_ref(observations)],issue)
    p=candidates["payload"];entries=p["candidates"];calls=observations["payload"]["calls"]
    if len(entries)!=len(calls):issue("INLINE_FORMULA_CANDIDATE_SCOPE_MISMATCH")
    by_unit={};expected_issues=[]
    for index,call in enumerate(calls):
        if index>=len(entries):break
        candidate=entries[index];value=call["observation"];raw=value["payload"]["raw_latex"]if value else None;cid=call["plan"]["call_id"]
        expected={"call_id":cid,"state":call["state"],"raw_latex":raw,"observation_ref":_ref(value)if value else None,
            "unit_bindings":call["plan"]["unit_bindings"],"complete":False,"transcription_verified":False,"business_acceptance":False,"selected":False}
        if any(candidate.get(k)!=v for k,v in expected.items())or set(candidate)!=set(expected)|{"candidate_id","parse_result"}:issue("INLINE_FORMULA_CANDIDATE_RAW_BINDING_MISMATCH",cid)
        body={k:v for k,v in candidate.items()if k!="candidate_id"}
        if candidate.get("candidate_id")!="inline-formula-candidate-"+digest([_ref(observations),body])[:24]:issue("INLINE_FORMULA_CANDIDATE_IDENTITY_MISMATCH",cid)
        _parse(raw,candidate["parse_result"],issue,cid,risks)
        for binding in call["plan"]["unit_bindings"]:
            values=by_unit.setdefault(binding["unit_id"],[])
            if not any(v["candidate_id"]==candidate.get("candidate_id")for v in values):values.append(candidate)
        if call["state"]!="DONE":expected_issues.append({"code":"INLINE_FORMULA_CALL_NOT_DONE","call_id":cid})
        elif not candidate["parse_result"]["supported"]:expected_issues.append({"code":"INLINE_FORMULA_SYNTAX_UNSUPPORTED","call_id":cid})
    units=[]
    for uid,values in by_unit.items():
        normalized=[v["parse_result"]["normalized_ast"]for v in values]
        agreement=bool(values)and all(v["state"]=="DONE"and v["parse_result"]["supported"]for v in values)and all(n==normalized[0]for n in normalized)
        units.append({"unit_id":uid,"candidate_refs":[v["candidate_id"]for v in values],"exact_ast_agreement":agreement,"selected_candidate_refs":[],"complete":False,"transcription_verified":False})
        if not agreement:expected_issues.append({"code":"INLINE_FORMULA_VARIANT_DISAGREEMENT_OR_UNPARSED","unit_id":uid})
    expected={"observation_ref":_ref(observations),"observations_archive":observations,"units":units,"not_inference_units":observations["payload"]["not_inference_units"],
        "issues":expected_issues,"entire_answer_reconstructed":False,"selected_candidate_refs":[],**_FLAGS}
    if any(p.get(k)!=v for k,v in expected.items())or set(p)!=set(expected)|{"candidates"}:issue("INLINE_FORMULA_CANDIDATE_AGREEMENT_OR_FLAGS_MISMATCH")


def _descriptor(root,descriptor):
    if (not isinstance(descriptor,dict)or set(descriptor)!={"path","sha256","artifact_ref"}or not _HASH.fullmatch(descriptor.get("sha256",""))
            or descriptor.get("path")!="objects/"+descriptor["sha256"]+".json"):raise ValueError("invalid immutable inline object descriptor")
    path=(root/descriptor["path"]).resolve()
    if not path.is_relative_to(root.resolve())or file_digest(path)!=descriptor["sha256"]:raise ValueError("missing or corrupted immutable inline object")
    value=json.loads(path.read_text(encoding="utf8"))
    if _ref(value)!=descriptor["artifact_ref"]or value.get("content_hash")!=digest(value.get("payload")):raise ValueError("immutable inline object reference changed")
    return value


def _journal(root,report,observations,layout,producer,plans,kind,issue):
    _envelope(report,"b-inline-formula-run-trial/0.1","InlineFormulaRunTrial","inline-formula-run",layout,producer,[_ref(layout),_ref(observations)],issue)
    p=report["payload"];op=observations["payload"];run_id=p["run_id"]
    if _descriptor(root,p["observation_output"])!=observations:issue("INLINE_FORMULA_RUN_OBSERVATION_OBJECT_MISMATCH")
    encoded=_json(report).encode("utf8");sha=hashlib.sha256(encoded).hexdigest()
    if (root/"objects"/(sha+".json")).read_bytes()!=encoded:issue("INLINE_FORMULA_REPORT_NOT_IMMUTABLY_PERSISTED")
    path=root/"inline-formula.sqlite3"
    with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True))as db:
        db.row_factory=sqlite3.Row
        rows=[dict(r)for r in db.execute("SELECT * FROM events WHERE run_id=? ORDER BY event_id",(run_id,))]
        events={r["event_id"]:{**r,"details":json.loads(r["details_json"])}for r in rows}
        starts=[r for r in events.values()if r["kind"]=="RUN_STARTED"];ends=[r for r in events.values()if r["kind"]=="RUN_FINISHED"]
        if len(starts)!=1 or len(ends)!=1:issue("INLINE_FORMULA_RUN_EVENT_MISMATCH");return
        if starts[0]["details"]!={"declared_calls":len(plans),"layout_ref":_ref(layout),"producer":producer}:issue("INLINE_FORMULA_RUN_SOURCE_SCOPE_MISMATCH")
        if len(p["calls"])!=len(plans):issue("INLINE_FORMULA_RUN_CALL_SCOPE_MISMATCH")
        declared_events=[]
        for receipt in p["calls"]:
            if receipt["state"]=="PENDING":continue
            if receipt["cached"]:declared_events.append(("CACHE_HIT",receipt["call_id"],receipt["origin_attempt_id"]))
            else:
                declared_events.extend((kind,receipt["call_id"],receipt["origin_attempt_id"])for kind in ("STARTED","SUCCEEDED"if receipt["state"]=="DONE"else"FAILED"))
        actual_events=[(r["kind"],r["call_id"],r["attempt_id"])for r in rows if r["kind"]in {"STARTED","SUCCEEDED","FAILED","CACHE_HIT"}]
        if Counter(actual_events)!=Counter(declared_events)or any(not starts[0]["event_id"]<r["event_id"]<ends[0]["event_id"]for r in rows if r["kind"]in {"STARTED","SUCCEEDED","FAILED","CACHE_HIT","INVALIDATED"}):
            issue("INLINE_FORMULA_RUN_ATTEMPT_SCOPE_MISMATCH")
        for index,plan in enumerate(plans):
            if index>=len(p["calls"]):break
            receipt=p["calls"][index];observed=op["calls"][index];key=digest([plan,producer]);cid=plan["call_id"]
            keys={"call_id","state","cached","cache_key","origin_attempt_id","output","event_id"}
            if (set(receipt)!=keys or receipt.get("call_id")!=cid or receipt.get("cache_key")!=key or receipt.get("state")!=observed["state"]or type(receipt.get("cached"))is not bool):
                issue("INLINE_FORMULA_RUN_CALL_RECEIPT_MISMATCH",cid)
            if receipt["state"]=="PENDING":
                if receipt["cached"]or any(receipt[k]is not None for k in ("origin_attempt_id","output","event_id")):issue("INLINE_FORMULA_PENDING_RECEIPT_INVALID",cid)
                continue
            value=_descriptor(root,receipt["output"])
            if value!=observed["observation"]:issue("INLINE_FORMULA_CALL_OBJECT_MISMATCH",cid)
            attempt=db.execute("SELECT * FROM attempts WHERE attempt_id=?",(receipt["origin_attempt_id"],)).fetchone()
            event=events.get(receipt["event_id"])
            desired="SUCCEEDED"if receipt["state"]=="DONE"else"FAILED"
            if (attempt is None or attempt["call_id"]!=cid or attempt["cache_key"]!=key or attempt["state"]!=desired
                    or not attempt["started_at"]or not attempt["finished_at"]or json.loads(attempt["output_json"])!=receipt["output"]):
                issue("INLINE_FORMULA_ORIGIN_ATTEMPT_MISMATCH",cid);continue
            history=[dict(r)for r in db.execute("SELECT * FROM events WHERE attempt_id=? ORDER BY event_id",(attempt["attempt_id"],))]
            origin_start=[r for r in history if r["kind"]=="STARTED"];origin_end=[r for r in history if r["kind"]==desired]
            if (len(origin_start)!=1 or len(origin_end)!=1 or origin_start[0]["event_id"]>=origin_end[0]["event_id"]
                    or any(r["run_id"]!=attempt["run_id"]or r["call_id"]!=cid for r in origin_start+origin_end)
                    or json.loads(origin_start[0]["details_json"])!={"cache_key":key}
                    or json.loads(origin_end[0]["details_json"])!={"cache_key":key,"output":receipt["output"]}):
                issue("INLINE_FORMULA_ORIGIN_EVENTS_MISMATCH",cid)
            if (event is None or event["call_id"]!=cid or event["attempt_id"]!=attempt["attempt_id"]or event["kind"]!=("CACHE_HIT"if receipt["cached"]else desired)
                    or event["details"]!={"cache_key":key,"output":receipt["output"]}or(not receipt["cached"]and attempt["run_id"]!=run_id)):
                issue("INLINE_FORMULA_CURRENT_RUN_RECEIPT_MISMATCH",cid)
            if receipt["cached"]and origin_end and event is not None and origin_end[0]["event_id"]>=event["event_id"]:issue("INLINE_FORMULA_CACHE_EVENT_ORDER_INVALID",cid)
            if receipt["state"]=="DONE":
                cached=db.execute("SELECT * FROM cache WHERE cache_key=?",(key,)).fetchone()
                if cached is None or cached["call_id"]!=cid or cached["attempt_id"]!=attempt["attempt_id"]or json.loads(cached["output_json"])!=receipt["output"]:
                    issue("INLINE_FORMULA_CACHE_ORIGIN_MISMATCH",cid)
        counts={"declared_calls":len(plans),"done":sum(c["state"]=="DONE"for c in op["calls"]),"pending":sum(c["state"]=="PENDING"for c in op["calls"]),
            "failed":sum(c["state"]=="FAILED"for c in op["calls"]),"cache_hits":sum(r["kind"]=="CACHE_HIT"for r in rows),
            "invalidated":sum(r["kind"]=="INVALIDATED"for r in rows),"new_attempts":sum(r["kind"]=="STARTED"for r in rows),
            "new_encoder_decoder_calls":sum(c["observation"]["payload"]["encoder_decoder_called"]for c,r in zip(op["calls"],p["calls"])if not r["cached"]and c["state"]!="PENDING")}
        state="FAILED"if op["input_changed_during_execution"]or counts["failed"]else"PARTIAL"if counts["pending"]else"READY"
        if (p.get("counts")!=counts or p.get("state")!=state or ends[0]["event_id"]!=p.get("terminal_event_id")
                or ends[0]["details"]!={"state":state,"counts":counts,"observation_output":p["observation_output"]}
                or not starts[0]["event_id"]<ends[0]["event_id"]):issue("INLINE_FORMULA_RUN_COUNTS_OR_TERMINAL_EVENT_MISMATCH")
    expected_keys=set(_FLAGS)|{"run_id","state","counts","calls","observation_output","result_ref","layout_ref","original_sha256_before","original_sha256_after","terminal_event_id","model_initializations"}
    if (set(p)!=expected_keys or any(p.get(k)!=v for k,v in _FLAGS.items())or p.get("result_ref")!=_ref(observations)or p.get("layout_ref")!=_ref(layout)
            or p.get("original_sha256_before")!=layout["payload"]["source"]["original_sha256"]or p.get("original_sha256_after")!=p.get("original_sha256_before")
            or p.get("model_initializations")!=(1 if kind=="CPU_RAPID_LATEX_OCR_INLINE"else 0)):
        issue("INLINE_FORMULA_RUN_SOURCE_OR_FLAGS_MISMATCH")


def audit_inline_formula(evidence,layout,observations,candidates,original_path,*,line_ids,workdir,report):
    """Audit durable execution consistency; every business result stays HOLD."""
    issues,risks=[],[]
    summary={"requested_rows":len(line_ids)if isinstance(line_ids,(list,tuple))else 0,"mathlike_units":0,"full_line_fallbacks":0,
        "declared_calls":0,"done":0,"pending":0,"failed":0,"parsed_candidates":0,"unparsed_candidates":0,"model_calls_during_audit":0}
    def issue(code,detail=None):
        item={"code":code,"severity":"ERROR","detail":detail}
        if item not in issues:issues.append(item)
    try:
        _audit(evidence,layout,observations,candidates,Path(original_path),line_ids,Path(workdir),report,issue,risks,summary)
    except (OSError,ValueError,TypeError,KeyError,IndexError,AttributeError,OverflowError,RecursionError,sqlite3.Error,StopIteration)as exc:
        issue("INLINE_FORMULA_DATA_INVALID",type(exc).__name__+": "+str(exc))
    inputs=[_ref(v)for v in (evidence,layout,observations,candidates,report)]
    producer={"module":__name__,"version":"0.1.0","code_sha256":code_digest(Path(__file__)),
        "independent_canvas_checker_code_sha256":code_digest(Path(__file__).with_name("formula_canvas_quality.py")),
        "independent_ocr_checker_code_sha256":code_digest(Path(__file__).with_name("inline_ocr_quality.py"))}
    payload={"accepted":not issues,"issues":issues,"observation_risks":risks,"summary":summary,"verification_status":"UNVERIFIED",**_FLAGS,
        "entire_answer_reconstructed":False,"limitations":["Integrity acceptance is not mathematical, glyph-localization or business accuracy.",
            "CPU receipts and journal records are checksums and execution bookkeeping, not external signatures.",
            "Raw token IDs and decoded text are retained; without a supplied tokenizer vocabulary this audit does not certify token-to-string decoding.",
            "Repeated normalized-AST agreement remains an unselected observation; unknown syntax and failed calls remain visible."]}
    source=evidence if isinstance(evidence,dict)else{}
    return {"schema_version":SCHEMA,"kind":"InlineFormulaCheckTrial","artifact_id":"inline-formula-check-"+digest([inputs,producer,payload])[:24],"revision":1,
        **{k:source.get(k)for k in ("book_id","scope_id","run_id")},"input_refs":inputs,"producer":producer,"content_hash":digest(payload),"payload":payload}


def _audit(evidence,layout,observations,candidates,original,line_ids,workdir,report,issue,risks,summary):
    if not isinstance(line_ids,(list,tuple))or not line_ids or len(line_ids)!=len(set(line_ids)):raise ValueError("explicit complete line scope is required")
    if file_digest(original)!=layout["payload"]["source"]["original_sha256"]:raise ValueError("inline original bytes changed")
    with Image.open(original)as opened:image=opened.convert("RGB")
    units,rows=_layout(evidence,layout,image,original,line_ids,issue)
    plans,skipped=_plans(layout,units,rows,image)
    p=observations["payload"];producer=observations["producer"]
    kind=_backend(producer,bool(plans),issue)
    _envelope(observations,"b-inline-formula-observation-trial/0.1","InlineFormulaObservationTrial","inline-formula-observations",layout,producer,[_ref(layout)],issue)
    summary.update(mathlike_units=sum(u["kind"]=="MATHLIKE_RUN"for u in units),full_line_fallbacks=sum(u["kind"]=="FULL_LINE_FALLBACK"for u in units),declared_calls=len(plans))
    expected={"source":layout["payload"]["source"],"requested_line_ids":list(line_ids),"layout_ref":_ref(layout),"not_inference_units":skipped,"layout_archive":layout,**_FLAGS}
    if any(p.get(k)!=v for k,v in expected.items())or set(p)!=set(expected)|{"calls","run_complete","input_changed_during_execution"}:issue("INLINE_FORMULA_SOURCE_OR_SKIPPED_SCOPE_MISMATCH")
    if p.get("input_changed_during_execution")is not False:issue("INLINE_FORMULA_INPUT_CHANGED_DURING_RUN")
    if len(p["calls"])!=len(plans):issue("INLINE_FORMULA_CALL_SCOPE_MISMATCH")
    for index,plan in enumerate(plans):
        if index<len(p["calls"]):_call(p["calls"][index],plan,layout,producer,image,kind,issue,risks)
    for state in ("DONE","PENDING","FAILED"):summary[state.lower()]=sum(c["state"]==state for c in p["calls"])
    if p.get("run_complete")!=(not summary["pending"]and not summary["failed"]and not p["input_changed_during_execution"]):issue("INLINE_FORMULA_FALSE_RUN_COMPLETE")
    _candidates(observations,candidates,issue,risks)
    summary["parsed_candidates"]=sum(c["parse_result"]["supported"]for c in candidates["payload"]["candidates"])
    summary["unparsed_candidates"]=len(candidates["payload"]["candidates"])-summary["parsed_candidates"]
    _journal(workdir,report,observations,layout,producer,plans,kind,issue)
