"""Independent dependency, journal and source audit of B's offline pipeline.

No runner, refiner, assembler or business-check producer is imported or rerun.
The retained graph is checked directly against its actual evidence, and journal
success is checked against immutable files. Integrity acceptance remains HOLD.
"""
from __future__ import annotations

from collections import Counter,defaultdict
import ast
import importlib.metadata
import importlib.util
import hashlib
import json
from pathlib import Path,PurePosixPath,PureWindowsPath
import re
import sqlite3

import cv2

from .baseline import code_digest,digest,file_digest,load_source,valid_bbox
from .batch_quality import audit_batch
from .recovery_stage_quality import audit_recovery_stage,audit_recovery_review,_load_package,POLICY
from .continuation_stage_quality import (inspect_continuation_package, audit_continuation_scope,
    audit_continuation_proof_stage, audit_continuation_apply_stage, audit_continued_quality)

SCHEMA = "b-pipeline-check-trial/0.1"


def _ref(value):
    return {k:value.get(k)for k in ("artifact_id","revision","content_hash")}


def _document_ref(value):
    return {"artifact_id":value["artifact_id"],"content_hash":digest(value)}


def _checked(value,schemas,kind=None):
    return (isinstance(value,dict) and value.get("schema_version") in schemas
            and (kind is None or value.get("kind") == kind)
            and type(value.get("revision")) is int and value["revision"] >= 1
            and isinstance(value.get("payload"),dict) and value.get("content_hash") == digest(value["payload"]))


def _read_object(root,descriptor):
    if not isinstance(descriptor,dict) or set(descriptor) != {"path","sha256","artifact_ref"}:
        raise ValueError("invalid immutable output descriptor")
    relative = descriptor["path"]
    if (not isinstance(relative,str) or "\\" in relative or PurePosixPath(relative).is_absolute()
            or PureWindowsPath(relative).drive or ".." in PurePosixPath(relative).parts
            or relative != "objects/"+descriptor["sha256"]+".json"):
        raise ValueError("escaping or nonportable immutable output")
    path = (root/relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file() or file_digest(path) != descriptor["sha256"]:
        raise ValueError("immutable output bytes changed or missing")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not _checked(value,{value.get("schema_version")}) or _ref(value) != descriptor["artifact_ref"]:
        raise ValueError("immutable output ref or payload changed")
    return value


def _source_evidence(evidence,source,context,emit):
    """Validate declared-source binding; do not reinterpret recognition text."""
    if not _checked(evidence,{"b-evidence-trial/0.2","b-evidence-trial/0.3"},"EvidenceBundleTrial"):
        emit("PIPELINE_EVIDENCE_INVALID")
        return {}
    p = evidence["payload"]
    assets = sorted(source["assets"],key=lambda a:a["reading_order"])
    if (any(evidence.get(k) != source[k]for k in ("book_id","scope_id"))
            or [page.get("source")for page in p.get("pages",[])] != assets
            or [page.get("asset_id")for page in p.get("pages",[])] != [a["asset_id"]for a in assets]):
        emit("PIPELINE_EVIDENCE_SOURCE_SCOPE_MISMATCH")
    if p.get("context") != context:
        emit("PIPELINE_EVIDENCE_CONTEXT_MISMATCH")
    if p.get("history_annotations_consumed") is not False or p.get("quality_decision") != "NOT_EVALUATED":
        emit("PIPELINE_EVIDENCE_PROVENANCE_MISMATCH")
    units = {}
    for page in p.get("pages",[]):
        aid,asset = page.get("asset_id"),page["source"]
        pc = context.get("pages",{}).get(aid,{})
        if page.get("page_role") != pc.get("role"):
            emit("PIPELINE_EVIDENCE_CONTEXT_MISMATCH",detail=aid)
        coarse = {line.get("line_id"):line for line in page.get("ocr_lines",[])}
        for line in page.get("ocr_lines",[])+page.get("answer_detail_lines",[]):
            lid = line.get("line_id")
            if not isinstance(lid,str) or not lid or lid in units:
                emit("PIPELINE_EVIDENCE_LINE_ID_REUSED",detail=lid)
            units[lid] = (page,line)
            if not valid_bbox(line.get("bbox",[]),asset["width"],asset["height"]):
                emit("PIPELINE_EVIDENCE_LINE_SOURCE_MISMATCH",detail=lid)
            if line.get("asset_id",aid) != aid:
                emit("PIPELINE_EVIDENCE_LINE_SOURCE_MISMATCH",detail=lid)
            if line.get("parent_line_id") is not None and line["parent_line_id"] not in coarse:
                emit("PIPELINE_EVIDENCE_LINE_SOURCE_MISMATCH",detail=lid)
            location = line.get("location")
            if location is not None:
                windows = pc.get("windows",[])
                index = location.get("window_index")
                if type(index) is not int or not 0 <= index < len(windows):
                    emit("PIPELINE_EVIDENCE_CONTEXT_MISMATCH",detail=lid)
                else:
                    window = windows[index]
                    if location.get("column") != window["column"] or location.get("section_path") != window["path"]:
                        emit("PIPELINE_EVIDENCE_CONTEXT_MISMATCH",detail=lid)
    return units


def _graph_sources(evidence,graph,units,emit):
    """Check actual graph content against source units, without assembling gold."""
    schemas = {"b-graph-trial/0.3"}if evidence["schema_version"].endswith("/0.3")else{"b-graph-trial/0.2"}
    if not _checked(graph,schemas,"QuestionGraphTrial"):
        emit("PIPELINE_GRAPH_INVALID")
        return
    if (graph.get("input_refs") != [_ref(evidence)] or any(graph.get(k) != evidence.get(k)for k in ("book_id","scope_id","run_id"))):
        emit("PIPELINE_GRAPH_EVIDENCE_REFERENCE_MISMATCH")
    gp = graph["payload"]
    if gp.get("selection_status") != "DRAFT_UNVERIFIED" or gp.get("platform_actions") != []:
        emit("PIPELINE_GRAPH_FALSE_VERIFICATION")
    entities = gp.get("questions",[])+gp.get("answers",[])
    identities = [e.get("question_id",e.get("answer_id"))for e in entities]
    if len(identities) != len(set(identities)) or any(not isinstance(v,str)or not v for v in identities):
        emit("PIPELINE_GRAPH_ENTITY_ID_REUSED")
    fids,owners,allocations = [],defaultdict(list),defaultdict(list)
    answer_map = {a["answer_id"]:a for a in gp.get("answers",[])}
    for entity in entities:
        is_question = "question_id" in entity
        eid = entity["question_id"] if is_question else entity["answer_id"]
        if entity.get("book_id") != evidence["book_id"] or entity.get("verification_status") != "UNVERIFIED":
            emit("PIPELINE_GRAPH_ENTITY_SOURCE_MISMATCH",detail=eid)
        if not is_question and entity.get("transcription_verified") is not False:
            emit("PIPELINE_GRAPH_FALSE_VERIFICATION",detail=eid)
        if is_question:
            anchor = units.get(entity.get("anchor_ref"))
            if (not anchor or anchor[0]["asset_id"] != entity.get("asset_id")
                    or not anchor[1].get("location") or anchor[1]["location"]["section_path"] != entity.get("section_path")):
                emit("PIPELINE_GRAPH_ANCHOR_SOURCE_MISMATCH",detail=eid)
            expected_id = "q-"+digest({"evidence":_ref(evidence),"role":"q","anchor":entity.get("anchor_ref")})[:24]
            if eid != expected_id:
                emit("PIPELINE_GRAPH_ENTITY_REVISION_MISMATCH",detail=eid)
        actual_refs,parents = [],[]
        for fragment in entity.get("fragments",[]):
            fid = fragment.get("fragment_id")
            fids.append(fid)
            refs = fragment.get("evidence_refs",[])
            actual_refs.extend(refs)
            if len(refs) != 1 or refs[0] not in units:
                emit("PIPELINE_GRAPH_FRAGMENT_SOURCE_MISMATCH",detail=fid)
                continue
            page,line = units[refs[0]]
            parent = line.get("parent_line_id",line["line_id"])
            if (fragment.get("asset_id") != page["asset_id"] or fragment.get("bbox") != line["bbox"]
                    or fragment.get("column") != (line.get("location")or{}).get("column")):
                emit("PIPELINE_GRAPH_FRAGMENT_SOURCE_MISMATCH",detail=fid)
            if not is_question:
                span = fragment.get("text_span",[])
                if (fragment.get("raw_text") != line["text"] or len(span) != 2 or any(type(v)is not int for v in span)
                        or not 0 <= span[0] < span[1] <= len(line["text"])
                        or fragment.get("text") != line["text"][span[0]:span[1]]
                        or fragment.get("parent_line_id") != parent
                        or fragment.get("section_path") != (line.get("location")or{}).get("section_path")):
                    emit("PIPELINE_GRAPH_FRAGMENT_SOURCE_MISMATCH",detail=fid)
                role,seed = "af",[eid,line["line_id"],*span,fragment.get("role")]
                parents.append(parent)
                owners[parent].append((eid,fid))
                allocations[parent].append({"answer_id":eid,"fragment_id":fid,"evidence_refs":refs,"text_span":span})
            else:
                if fragment.get("text") != line["text"]:
                    emit("PIPELINE_GRAPH_FRAGMENT_SOURCE_MISMATCH",detail=fid)
                role = "caption" if fragment.get("role") == "figure_caption" else "f"
                seed = line["line_id"]
            expected_fid = role+"-"+digest({"evidence":_ref(evidence),"role":role,"anchor":seed})[:24]
            if fid != expected_fid:
                emit("PIPELINE_GRAPH_ENTITY_REVISION_MISMATCH",detail=fid)
        if not is_question:
            if entity.get("evidence_refs") != list(dict.fromkeys(actual_refs)) or entity.get("source_line_ids") != list(dict.fromkeys(parents)):
                emit("PIPELINE_GRAPH_ANSWER_REFERENCE_MISMATCH",detail=eid)
            expected_regions = [{k:f[k]for k in ("fragment_id","asset_id","bbox","column","window_index","role","evidence_refs")}
                                for f in entity.get("fragments",[])]
            if entity.get("regions") != expected_regions:
                emit("PIPELINE_GRAPH_REGION_SOURCE_MISMATCH",detail=eid)
            compact = lambda text:re.sub(r"\s+","",text)
            body = "\n".join(f["text"]for f in entity.get("fragments",[])if f.get("role") == "answer"and not f.get("structural_marker"))
            explanation = "\n".join(f["text"]for f in entity.get("fragments",[])if f.get("role") == "explanation"and not f.get("structural_marker"))
            if compact(entity.get("text","")) != compact(body)or compact(entity.get("explanation_text","")) != compact(explanation):
                emit("PIPELINE_GRAPH_TEXT_PROJECTION_MISMATCH",detail=eid)
            fragments = entity.get("fragments",[])
            primary = re.match(r"^\s*(\d{1,2})\s*[.．、]\s*",fragments[0].get("raw_text",""))if fragments else None
            if primary and str(entity.get("printed_number","")).split(":")[0] != primary[1]:
                emit("PIPELINE_GRAPH_PRIMARY_SOURCE_MISMATCH",detail=eid)
        else:
            expected_text = "\n".join(f["text"]for f in entity.get("fragments",[])if f.get("role") != "figure_caption")
            if entity.get("text") != expected_text:
                emit("PIPELINE_GRAPH_TEXT_PROJECTION_MISMATCH",detail=eid)
            source_key = (entity.get("book_id"),tuple(entity.get("section_path",[])),str(entity.get("printed_number")))
            expected_candidates = [a["answer_id"]for a in answer_map.values()
                if (a.get("book_id"),tuple(a.get("section_path",[])),str(a.get("printed_number"))) == source_key]
            expected_selected = expected_candidates[0] if len(expected_candidates) == 1 else None
            if entity.get("candidate_answer_ids") != expected_candidates or entity.get("selected_answer_id") != expected_selected:
                emit("PIPELINE_GRAPH_MATCH_SOURCE_MISMATCH",detail=eid)
    if len(fids) != len(set(fids)) or any(not isinstance(v,str)or not v for v in fids):
        emit("PIPELINE_GRAPH_FRAGMENT_ID_REUSED")
    raw = {line["line_id"]:(page,line)for page in evidence["payload"]["pages"]if page["page_role"] == "answer"for line in page["ocr_lines"]}
    ledger = gp.get("answer_coverage",[])
    if Counter(r.get("line_id")for r in ledger) != Counter(raw.keys()):
        emit("PIPELINE_GRAPH_LEDGER_SCOPE_MISMATCH")
    for row in ledger:
        lid = row.get("line_id")
        if lid not in raw: continue
        expected_owners = owners.get(lid,[])
        if (row.get("asset_id") != raw[lid][0]["asset_id"] or set(row.get("answer_ids",[])) != {a for a,f in expected_owners}
                or set(row.get("fragment_ids",[])) != {f for a,f in expected_owners}
                or Counter(map(digest,row.get("allocations",[]))) != Counter(map(digest,allocations.get(lid,[])))
                or row.get("status") not in ({"CONSUMED"}if expected_owners else{"EXCLUDED","UNASSIGNED"})):
            emit("PIPELINE_GRAPH_LEDGER_SOURCE_MISMATCH",detail=lid)


def _quality_bindings(evidence,graph,check,review,emit):
    schemas = {"b-check-trial/0.3"}if evidence["schema_version"].endswith("/0.3")else{"b-check-trial/0.2"}
    if not _checked(check,schemas,"CheckReportTrial"):
        emit("PIPELINE_QUALITY_INVALID")
        return
    if (check.get("input_refs") != [_ref(evidence),_ref(graph),_document_ref(review)]
            or any(check.get(k) != evidence.get(k)for k in ("book_id","scope_id","run_id"))):
        emit("PIPELINE_QUALITY_INPUT_REFERENCE_MISMATCH")
    cp,gp = check["payload"],graph["payload"]
    if cp.get("decision") != "HOLD" or cp.get("stage") != "PRE_APPLY":
        emit("PIPELINE_QUALITY_FALSE_VERIFICATION")
    if not any(i.get("code") == "BUSINESS_REVIEW_REQUIRED"for i in cp.get("issues",[])):
        emit("PIPELINE_QUALITY_BUSINESS_REVIEW_MISSING")
    summary = cp.get("summary",{})
    if (summary.get("questions") != len(gp.get("questions",[])) or summary.get("answers") != len(gp.get("answers",[]))
            or summary.get("unique_candidate_links") != sum(q.get("selected_answer_id")is not None for q in gp.get("questions",[]))
            or summary.get("issues") != len(cp.get("issues",[]))):
        emit("PIPELINE_QUALITY_SUMMARY_MISMATCH")
    expected_coverage = []
    for page in evidence["payload"]["pages"]:
        if page["page_role"] != "question": continue
        aid = page["asset_id"]
        census = review.get("question_census",{}).get(aid)
        expected = census["printed_numbers"]if census else[]
        actual = [q["printed_number"]for q in gp["questions"]if q["asset_id"] == aid and not q.get("parent_question_id")]
        expected_coverage.append({"asset_id":aid,"expected":expected,"actual":actual,
            "census_matches":bool(census)and actual == expected,"reference_quality":review["reference_quality"],"business_acceptance":False})
    if cp.get("page_coverage") != expected_coverage:
        emit("PIPELINE_QUALITY_SOURCE_COVERAGE_MISMATCH")


def _function_hashes(path):
    """Read Python source without importing or executing the stage producer."""
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines(keepends=True)
    result = {}
    for node in ast.parse(text).body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            start = min([node.lineno]+[d.lineno for d in node.decorator_list])
            result[node.name] = hashlib.sha256("".join(lines[start-1:node.end_lineno]).encode("utf-8")).hexdigest()
    return result


def _offline_global_values(path):
    result = {}
    for node in ast.parse(path.read_text(encoding="utf-8-sig")).body:
        if not isinstance(node,ast.Assign)or len(node.targets) != 1 or not isinstance(node.targets[0],ast.Name): continue
        name,value = node.targets[0].id,node.value
        if name in {"CONTEXT_SCHEMA","EVIDENCE_SCHEMA","GRAPH_SCHEMA","CHECK_SCHEMA"}:
            result[name] = ast.literal_eval(value)
        elif name in {"QSTART","ASTART","OPTION","CAPTION","DECORATION"}:
            if not isinstance(value,ast.Call)or len(value.args) != 1: raise ValueError("unsupported regex source profile")
            pattern = ast.literal_eval(value.args[0])
            result[name] = {"pattern":pattern,"flags":int(re.compile(pattern).flags)}
    return result


def _recognizer_current(receipt,*,use_ocr,synthetic):
    """Recompute a CPU/test receipt from files, without loading an OCR runtime."""
    if not isinstance(receipt,dict): return False
    here = Path(__file__)
    legacy = here.resolve().parents[3]/"tools/route_a_layout.py"
    code = {"batch":code_digest(here.with_name("batch.py")),"baseline":None,"legacy":None,"worker":None}
    cfg = {"baseline":None,"worker_cache_identity":None,"single_asset_manifest_policy":"context+asset+recognizer/0.1"}
    def package(distribution,module):
        return {"version":importlib.metadata.version(distribution),
                "package_entry_sha256":file_digest(Path(importlib.util.find_spec(module).origin))}
    dependencies,models,worker = {"Pillow":package("Pillow","PIL")},[],None
    if synthetic:
        worker = receipt.get("worker_identity")
        if (not isinstance(worker,dict)or not re.fullmatch(r"[0-9a-f]{64}",str(worker.get("code_sha256","")))
                or worker.get("hash_method")not in {"python_source","python_code_object"}
                or not isinstance(worker.get("module"),str)or not isinstance(worker.get("qualname"),str)):
            return False
        code["worker"],cfg["worker_cache_identity"] = worker["code_sha256"],worker.get("cache_identity")
        kind = "SYNTHETIC_TEST"
    else:
        code.update(baseline=code_digest(here.with_name("baseline.py")),legacy=code_digest(legacy))
        tree = ast.parse(legacy.read_text(encoding="utf-8-sig"))
        cfg["baseline"] = next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)
            and any(isinstance(t,ast.Name)and t.id == "CFG"for t in n.targets))
        dependencies.update(numpy=package("numpy","numpy"),
            opencv={"version":cv2.__version__,"package_entry_sha256":file_digest(Path(cv2.__file__))})
        if use_ocr:
            for distribution,module in (("rapidocr-onnxruntime","rapidocr_onnxruntime"),("onnxruntime","onnxruntime")):
                dependencies[module] = package(distribution,module)
            directory = Path(importlib.util.find_spec("rapidocr_onnxruntime").origin).parent
            models = [{"name":str(p.relative_to(directory)).replace("\\","/"),"sha256":file_digest(p)}for p in sorted(directory.rglob("*.onnx"))]
            if not models: return False
        kind = "BASELINE_CPU_OCR"if use_ocr else"BASELINE_GEOMETRY"
    expected = {"execution_kind":kind,"use_ocr":use_ocr,"code":code,"configuration":cfg,
                "dependencies":dependencies,"model_files":models,"worker_identity":worker}
    return receipt == {**expected,"fingerprint":digest(expected)}


def _audit_pipeline(source_path,context_path,review_path,report,workdir,*,evidence_path=None,recovery_path=None,
                    continuation_path=None,adjacent_source_path=None):
    issues,summary = [],{}

    def emit(code,stage=None,detail=None):
        item = {"code":code,"severity":"ERROR","detail":detail}
        if stage is not None: item["stage"] = stage
        if item not in issues: issues.append(item)

    def finish():
        payload = {"accepted":not issues,"decision":"HOLD","issues":issues,"summary":summary,
                   "business_acceptance":False,"transcription_verified":False,"platform_actions":[]}
        inputs = [_ref(report)]if isinstance(report,dict)else[]
        producer = {"module":__name__,"version":"0.1.0","code_sha256":code_digest(Path(__file__))}
        return {"schema_version":SCHEMA,"kind":"PipelineCheckTrial",
            "artifact_id":"pipeline-check-"+digest([inputs,payload,producer])[:24],"revision":1,
            "run_id":report.get("run_id")if isinstance(report,dict)else None,
            "book_id":report.get("book_id")if isinstance(report,dict)else None,
            "scope_id":report.get("scope_id")if isinstance(report,dict)else None,
            "input_refs":inputs,"producer":producer,"content_hash":digest(payload),"payload":payload}

    source,inputs = load_source(Path(source_path))
    context = json.loads(Path(context_path).read_text(encoding="utf-8"))
    review = json.loads(Path(review_path).read_text(encoding="utf-8"))
    assets = [a for a,p in inputs]
    summary["declared_asset_count"] = len(assets)
    receipts = {"source":{"file_sha256":file_digest(Path(source_path)),"reference":_document_ref(source)},
                "context":{"file_sha256":file_digest(Path(context_path)),"reference":_document_ref(context)},
                "review":{"file_sha256":file_digest(Path(review_path)),"reference":_document_ref(review)},"evidence":None}
    imported = None
    if evidence_path is not None:
        imported = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
        receipts["evidence"] = {"file_sha256":file_digest(Path(evidence_path)),"reference":_ref(imported)}
    if recovery_path is not None:
        _,_,receipts["recovery"],_,_ = _load_package(source_path,recovery_path,lambda code,detail=None:emit(code,"recover",detail))
    if (continuation_path is None) != (adjacent_source_path is None):
        raise ValueError("continuation package and adjacent original are required together")
    if continuation_path is not None:
        receipts["continuation"] = inspect_continuation_package(continuation_path,source_path,adjacent_source_path)["receipt"]
    mode = "CACHED_INPUT"if imported is not None else"LIVE_BATCH"
    if (context.get("schema_version") != "b-context-trial/0.1"or review.get("schema_version") != "b-review-trial/0.1"
            or any(document.get(k) != source[k]for document in (context,review)for k in ("book_id","scope_id"))
            or set(context.get("pages",{})) != {a["asset_id"]for a in assets}):
        emit("PIPELINE_INPUT_SCOPE_MISMATCH")
    by_asset = {a["asset_id"]:a for a in assets}
    for aid,page in context.get("pages",{}).items():
        asset = by_asset.get(aid)
        if not asset or page.get("sha256") != asset["sha256"] or page.get("role")not in {"question","answer"}:
            emit("PIPELINE_INPUT_CONTEXT_MISMATCH",detail=aid)
        elif not page.get("windows"):
            emit("PIPELINE_INPUT_CONTEXT_MISMATCH",detail=aid)
        else:
            for window in page["windows"]:
                lo,hi = window["y_range"]
                if (window.get("column") not in (0,1)or not 0 <= lo < hi <= asset["height"]
                        or not window.get("path")or any(not isinstance(s,str)or not s for s in window["path"])):
                    emit("PIPELINE_INPUT_CONTEXT_MISMATCH",detail=aid)
    for aid,census in review.get("question_census",{}).items():
        if aid not in by_asset or census.get("sha256") != by_asset[aid]["sha256"]:
            emit("PIPELINE_INPUT_REVIEW_MISMATCH",detail=aid)
    for case in review.get("answer_checks",[]):
        if any(aid not in by_asset or sha != by_asset[aid]["sha256"]for aid,sha in case.get("asset_sha256",{}).items()):
            emit("PIPELINE_INPUT_REVIEW_MISMATCH",detail=case.get("case_id"))
    if not _checked(report,{"b-pipeline-report-trial/0.1"},"PipelineReportTrial"):
        emit("PIPELINE_REPORT_INVALID")
        return finish()
    p,root = report["payload"],Path(workdir).resolve()
    if (p.get("mode") != mode or p.get("source_manifest") != source or p.get("source_assets") != assets
            or p.get("source_ref") != _document_ref(source)or p.get("input_receipts") != receipts
            or any(report.get(k) != source[k]for k in ("book_id","scope_id"))):
        emit("PIPELINE_INPUT_BINDING_MISMATCH")
    if (p.get("decision") != "HOLD"or p.get("business_acceptance")is not False
            or p.get("transcription_verified")is not False or p.get("platform_actions") != []):
        emit("PIPELINE_FALSE_VERIFICATION")
    stage_order = ["evidence","assemble","quality"]if mode == "CACHED_INPUT"else["recognition","refine","assemble","quality"]
    if recovery_path is not None:
        stage_order.insert(stage_order.index("assemble"),"recover")
        stage_order.insert(stage_order.index("quality"),"recovery_review")
    continuation_stages = ("continuation_prepare","continuation_proof","continuation_apply","continuation_quality")
    if continuation_path is not None: stage_order.extend(continuation_stages)
    stages = p.get("stages",[])
    if [s.get("stage_id")for s in stages] != stage_order:
        emit("PIPELINE_STAGE_SCOPE_MISMATCH")
    summary["stage_count"] = len(stage_order)
    run_id = report.get("run_id")
    if (p.get("run_id") != run_id or report.get("input_refs") != [_document_ref(source)]
            or report.get("producer") != {"module":"annotation.recognition.pipeline","version":"0.1.0",
                "code_sha256":code_digest(Path(__file__).with_name("pipeline.py"))}
            or report.get("artifact_id") != "pipeline-report-"+digest([_document_ref(source),report["producer"],p])[:24]):
        emit("PIPELINE_REPORT_IDENTITY_MISMATCH")
    connection = None
    try:
        database = root/"pipeline.sqlite3"
        if not database.is_file(): raise ValueError("pipeline journal missing")
        connection = sqlite3.connect(database.as_uri()+"?mode=ro",uri=True)
        connection.row_factory = sqlite3.Row
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok": raise ValueError("SQLite integrity failure")
        attempts = [dict(r)for r in connection.execute("SELECT * FROM stage_attempts")]
        events = [dict(r)for r in connection.execute("SELECT * FROM stage_events ORDER BY event_id")]
        cache = {r["expected_key"]:dict(r)for r in connection.execute("SELECT * FROM stage_cache")}
    except (OSError,ValueError,sqlite3.Error)as exc:
        emit("PIPELINE_JOURNAL_INVALID",detail=str(exc))
        return finish()
    finally:
        if connection is not None: connection.close()
    attempt_map = {a["attempt_id"]:a for a in attempts}
    detail_map = {e["event_id"]:json.loads(e["details_json"])for e in events}
    run_events = [e for e in events if e["run_id"] == run_id]
    if any(detail_map[e["event_id"]].get("run_id") != e["run_id"]for e in events):
        emit("PIPELINE_EVENT_RUN_MISMATCH")
    starts,ends = [[e for e in run_events if e["event_type"] == name]for name in ("RUN_STARTED","RUN_FINISHED")]
    if len(starts) != 1 or len(ends) != 1 or starts[0]["event_id"] >= ends[0]["event_id"]:
        emit("PIPELINE_RUN_EVENT_MISMATCH")
        return finish()
    start_detail,end_detail = detail_map[starts[0]["event_id"]],detail_map[ends[0]["event_id"]]
    input_changes = [e for e in run_events if e["event_type"] == "RUN_INPUT_CHANGED"]
    if p.get("run_error")is not None:
        emit("PIPELINE_INPUT_CHANGED_DURING_RUN",detail=p["run_error"])
    if bool(input_changes) != (p.get("run_error")is not None):
        emit("PIPELINE_INPUT_CHANGE_RECEIPT_MISMATCH")
    if (start_detail.get("mode") != mode or start_detail.get("source_ref") != _document_ref(source)
            or start_detail.get("input_receipts") != receipts or start_detail.get("stage_ids") != stage_order
            or end_detail.get("report_ref") != _ref(report)):
        emit("PIPELINE_RUN_EVENT_MISMATCH")
    try:
        if _read_object(root,end_detail.get("report_artifact")) != report:
            emit("PIPELINE_REPORT_RECEIPT_MISMATCH")
    except (OSError,ValueError,TypeError,KeyError)as exc:
        emit("PIPELINE_REPORT_RECEIPT_MISMATCH",detail=str(exc))
    for attempt in attempts:
        associated = [e for e in events if e["attempt_id"] == attempt["attempt_id"]and e["event_type"] != "CACHE_HIT"]
        begin = [e for e in associated if e["event_type"] == "STAGE_STARTED"]
        terminal = [e for e in associated if e["event_type"] in {"STAGE_SUCCEEDED","STAGE_FAILED","STAGE_INTERRUPTED"}]
        expected_terminal = {"SUCCEEDED":"STAGE_SUCCEEDED","FAILED":"STAGE_FAILED","INTERRUPTED":"STAGE_INTERRUPTED"}.get(attempt["state"])
        if (len(begin) != 1 or len(terminal) != 1 or terminal[0]["event_type"] != expected_terminal
                or begin[0]["event_id"] >= terminal[0]["event_id"] or not attempt["finished_at"]
                or any(e["stage_id"] != attempt["stage_id"]for e in associated)):
            emit("PIPELINE_ATTEMPT_EVENT_MISMATCH",attempt["stage_id"],attempt["attempt_id"])
        elif (detail_map[begin[0]["event_id"]].get("expected_key") != attempt["expected_key"]
                or begin[0]["run_id"] != attempt["run_id"]):
            emit("PIPELINE_ATTEMPT_DEPENDENCY_MISMATCH",attempt["stage_id"])
        if attempt["state"] == "SUCCEEDED":
            if not attempt["output_json"]or not attempt["result_ref_json"]or attempt["error"]is not None:
                emit("PIPELINE_ATTEMPT_RESULT_MISMATCH",attempt["stage_id"])
            elif len(terminal) == 1:
                td = detail_map[terminal[0]["event_id"]]
                if td.get("output") != json.loads(attempt["output_json"])or td.get("result_ref") != json.loads(attempt["result_ref_json"]):
                    emit("PIPELINE_ATTEMPT_RESULT_MISMATCH",attempt["stage_id"])
        elif attempt["state"] in {"FAILED","INTERRUPTED"}and not attempt["error"]:
            emit("PIPELINE_ATTEMPT_ERROR_MISSING",attempt["stage_id"])
    if any(e["attempt_id"]is not None and e["attempt_id"]not in attempt_map for e in events):
        emit("PIPELINE_EVENT_ATTEMPT_UNKNOWN")
    offline_path = Path(__file__).with_name("offline.py")
    pipeline_path,batch_path = Path(__file__).with_name("pipeline.py"),Path(__file__).with_name("batch.py")
    source_functions = {"offline":_function_hashes(offline_path),"pipeline":_function_hashes(pipeline_path),"batch":_function_hashes(batch_path),
        "recovery_stage":_function_hashes(Path(__file__).with_name("recovery_stage.py"))}
    if continuation_path is not None:
        source_functions.update(continuation_stage=_function_hashes(Path(__file__).with_name("continuation_stage.py")),
            continued_quality=_function_hashes(Path(__file__).with_name("continued_quality.py")))
    offline_globals = _offline_global_values(offline_path)
    expected_dependencies = {distribution:{"version":importlib.metadata.version(distribution),
        "package_entry_sha256":file_digest(Path(importlib.util.find_spec(module).origin))}for distribution,module in (("numpy","numpy"),("Pillow","PIL"))}
    results,bindings = {},{}
    stopped,blocked = False,False
    kind = p.get("execution_kind")
    use_ocr = start_detail.get("execution_kind") == "LIVE_CPU_OCR"
    if kind == "SYNTHETIC_TEST":
        first_implementation = next((s["implementation"]for s in stages if s.get("implementation")),{})
        use_ocr = first_implementation.get("configuration",{}).get("use_ocr")
    if (kind not in ({"CACHED_INPUT"}if mode == "CACHED_INPUT"else{"SYNTHETIC_TEST","LIVE_GEOMETRY","LIVE_CPU_OCR"})
            or start_detail.get("execution_kind") != kind):
        emit("PIPELINE_EXECUTION_KIND_MISMATCH")
    for entry in stages:
        stage,state = entry.get("stage_id"),entry.get("state")
        expected_reason = "STOP_AFTER"if stopped else"DEPENDENCY_NOT_READY"if blocked else"OCR_REQUIRED"if stage == "refine"and not use_ocr else None
        if expected_reason is not None:
            if (state != "WAITING"or entry.get("reason") != expected_reason or entry.get("output")is not None
                    or entry.get("result_ref")is not None or entry.get("expected_key")is not None
                    or entry.get("dependencies") != {}or entry.get("implementation")is not None
                    or entry.get("cached")is not False or entry.get("origin_attempt_id")is not None or entry.get("current_run_receipt")is not None):
                emit("PIPELINE_WAITING_STAGE_MISMATCH",stage)
            if expected_reason == "OCR_REQUIRED": blocked = True
            continue
        dependencies = {"source":receipts["source"]}
        if stage == "evidence": dependencies.update(context=receipts["context"],evidence=receipts["evidence"])
        elif stage == "refine":
            dependencies.update(context=receipts["context"],recognition=bindings["recognition"],baseline={
                "artifact":results["recognition"]["payload"]["bundle"],"result_ref":_ref(results["baseline"])})
        elif stage == "recover": dependencies.update(evidence=bindings["evidence"],recovery=receipts["recovery"])
        elif stage == "assemble": dependencies["evidence"] = bindings["evidence"]
        elif stage == "recovery_review": dependencies.update(evidence=bindings["evidence"],review=receipts["review"])
        elif stage == "quality":
            review_dependency = {**bindings["recovery_review"],"reference":_document_ref(results["active_review"])}if recovery_path is not None else receipts["review"]
            dependencies.update(evidence=bindings["evidence"],graph=bindings["assemble"],review=review_dependency)
        elif stage == "continuation_prepare":
            dependencies.update(evidence=bindings["evidence"],graph=bindings["assemble"],continuation=receipts["continuation"])
        elif stage == "continuation_proof":
            dependencies.update(scope=bindings["continuation_prepare"],continuation=receipts["continuation"])
        elif stage == "continuation_apply":
            dependencies.update(scope=bindings["continuation_prepare"],proof=bindings["continuation_proof"],continuation=receipts["continuation"])
        elif stage == "continuation_quality":
            review_dependency = {**bindings["recovery_review"],"reference":_document_ref(results["active_review"])}if recovery_path is not None else receipts["review"]
            dependencies.update(scope=bindings["continuation_prepare"],proof=bindings["continuation_proof"],
                application=bindings["continuation_apply"],review=review_dependency,continuation=receipts["continuation"])
        if entry.get("reason") == "STAGE_SETUP_FAILED":
            current = entry.get("current_run_receipt")or{}
            associated = [e for e in run_events if e["event_id"] == current.get("event_id")]
            if (state != "FAILED"or entry.get("expected_key")is not None or entry.get("implementation")is not None
                    or entry.get("output")is not None or entry.get("result_ref")is not None or entry.get("origin_attempt_id")is not None
                    or entry.get("cached")is not False or entry.get("dependencies") != dependencies or not entry.get("last_error")
                    or len(associated) != 1):
                emit("PIPELINE_SETUP_FAILURE_RECEIPT_MISMATCH",stage)
            else:
                event = associated[0]
                detail = detail_map[event["event_id"]]
                if (event["event_type"] != "STAGE_SETUP_FAILED"or event["stage_id"] != stage or event["attempt_id"]is not None
                        or current != {k:event[k]for k in ("run_id","event_id","event_type","attempt_id")}
                        or detail.get("dependencies") != dependencies or detail.get("error") != entry["last_error"]):
                    emit("PIPELINE_SETUP_FAILURE_RECEIPT_MISMATCH",stage)
            blocked = True
            continue
        implementation = entry.get("implementation")or{}
        code = implementation.get("code",{})
        continued_functions = {"continuation_prepare":("continuation_stage","prepare_continuation_scope"),
            "continuation_proof":("continuation_stage","build_continuation_stage_proof"),
            "continuation_apply":("continuation_stage","apply_continuation_stage"),
            "continuation_quality":("continued_quality","build_continued_quality")}
        function_owner,function_name = continued_functions[stage]if stage in continuation_stages else("batch","run_batch")if stage == "recognition"else("pipeline","_validate_evidence")if stage == "evidence"else("recovery_stage","recover_evidence"if stage == "recover"else"build_recovery_review")if stage in {"recover","recovery_review"}else("offline","quality_check"if stage == "quality"else stage)
        helper_names = []if stage == "recognition"else["check_artifact","validate_context"]if stage == "evidence"else["artifact","ref","check_artifact"]+{
            "refine":["validate_context","detect_columns","locate"],"assemble":["entity_id","scope_key"],"quality":["scalar_issues","scope_key"],"recover":["validate_context"],"recovery_review":[],
            "continuation_prepare":["assemble","entity_id","scope_key"],"continuation_proof":[],"continuation_apply":[],"continuation_quality":[]}[stage]
        if stage in {"continuation_proof","continuation_apply"}: helper_names = []
        if stage == "continuation_quality": helper_names = ["scalar_issues","scope_key"]
        expected_helpers = {n:source_functions["offline"][n]for n in helper_names}
        module_names = {"recognition":["batch","baseline"],"evidence":["baseline"],
            "recover":["recovery_stage","recovery_apply","baseline"],"recovery_review":["recovery_stage","recovery_apply","baseline"],
            "refine":["baseline","legacy"],"assemble":["baseline","answer_assembly","policy"],
            "quality":["baseline","question_quality","answer_quality","recovery_quality","recovery_apply","policy"],
            **{name:["continuation_stage","continuation","continuation_apply","continuation_quality","boundary","image_regions","baseline","offline","answer_assembly","policy"]
                for name in continuation_stages}}[stage]
        if stage == "continuation_quality": module_names += ["continued_quality","continuation_stage_quality","question_quality","answer_quality","recovery_quality","recovery_apply","policy"]
        global_names = {"recognition":[],"evidence":["CONTEXT_SCHEMA","EVIDENCE_SCHEMA"],"refine":["CONTEXT_SCHEMA","EVIDENCE_SCHEMA","ASTART"],
            "recover":["EVIDENCE_SCHEMA","CONTEXT_SCHEMA"],"recovery_review":["EVIDENCE_SCHEMA"],
            "assemble":["EVIDENCE_SCHEMA","GRAPH_SCHEMA","QSTART","ASTART","OPTION","CAPTION","DECORATION"],
            "quality":["EVIDENCE_SCHEMA","GRAPH_SCHEMA","CHECK_SCHEMA"],**{name:[]for name in continuation_stages}}[stage]
        if stage == "continuation_prepare": global_names = ["EVIDENCE_SCHEMA","GRAPH_SCHEMA","QSTART","ASTART","OPTION","CAPTION","DECORATION"]
        module_paths = {n:(Path(__file__).resolve().parents[3]/"tools/route_a_layout.py"if n == "legacy"else Path(__file__).with_name(n+".py"))for n in module_names}
        refinement_mode = implementation.get("configuration",{}).get("refinement_mode")
        synthetic_override = stage == "refine"and kind == "SYNTHETIC_TEST"and refinement_mode == "SYNTHETIC_TEST_OVERRIDE"
        expected_entrypoint = source_functions[function_owner][function_name]
        entrypoint_valid = bool(re.fullmatch(r"[0-9a-f]{64}",str(code.get("entrypoint",""))))if synthetic_override else code.get("entrypoint") == expected_entrypoint
        expected_configuration = {"stage_id":stage,"mode":mode,"execution_kind":kind,"use_ocr":use_ocr,
            "offline_globals":{name:offline_globals[name]for name in global_names},
            "refinement_mode":"SYNTHETIC_TEST_OVERRIDE"if synthetic_override else"CPU_OCR"if stage == "refine"else None}
        if stage in {"recover","recovery_review"}: expected_configuration["recovery_policy"] = POLICY
        stage_dependencies = expected_dependencies
        if stage in continuation_stages:
            expected_configuration["continuation_policy"] = "CURRENT_REFERENCE_REBUILD_ONLY/0.1"
            native = Path(getattr(cv2,"_native",cv2).__file__)
            stage_dependencies = {**expected_dependencies,"opencv":{"version":cv2.__version__,
                "package_entry_sha256":file_digest(Path(cv2.__file__)),
                "native_module":{"name":native.name,"sha256":file_digest(native)}}}
        if stage == "assemble" and continuation_path is not None:
            expected_configuration["artifact_time_policy"] = "EXECUTION_TIME_IN_STAGE_JOURNAL/0.1"
        if (code.get("pipeline") != code_digest(pipeline_path)or not entrypoint_valid
                or code.get("helpers") != expected_helpers or code.get("modules") != {n:code_digest(path)for n,path in module_paths.items()}
                or implementation.get("dependencies") != stage_dependencies
                or implementation.get("configuration") != expected_configuration):
            emit("PIPELINE_IMPLEMENTATION_VERSION_MISMATCH",stage)
        if stage in {"recognition","refine"}:
            try:
                if not _recognizer_current(implementation.get("recognizer"),use_ocr=True if stage == "refine"else use_ocr,
                        synthetic=synthetic_override or stage == "recognition"and kind == "SYNTHETIC_TEST"):
                    emit("PIPELINE_RECOGNIZER_VERSION_MISMATCH",stage)
            except (OSError,ImportError,TypeError,ValueError,AttributeError)as exc:
                emit("PIPELINE_RECOGNIZER_VERSION_MISMATCH",stage,str(exc))
        if synthetic_override and implementation.get("recognizer") != results.get("recognition",{}).get("payload",{}).get("recognizer"):
            emit("PIPELINE_RECOGNIZER_VERSION_MISMATCH",stage,"Synthetic refinement belongs to a different worker receipt")
        if stage not in {"recognition","refine"}and implementation.get("recognizer")is not None:
            emit("PIPELINE_EXECUTION_KIND_MISMATCH",stage)
        if entry.get("dependencies") != dependencies:
            emit("PIPELINE_STAGE_DEPENDENCY_MISMATCH",stage)
        key = digest({"mode":mode,"stage_id":stage,"dependencies":dependencies,"implementation":implementation})
        if entry.get("expected_key") != key:
            emit("PIPELINE_STAGE_KEY_MISMATCH",stage)
        current = entry.get("current_run_receipt")or{}
        matching = [e for e in run_events if e["event_id"] == current.get("event_id")]
        if (len(matching) != 1 or current != {k:matching[0][k]for k in ("run_id","event_id","event_type","attempt_id")}
                or matching[0]["stage_id"] != stage or matching[0]["attempt_id"] != entry.get("origin_attempt_id")):
            emit("PIPELINE_CURRENT_RUN_RECEIPT_MISMATCH",stage)
        elif (current["event_type"] != ("CACHE_HIT"if entry.get("cached")else"STAGE_FAILED"if state == "FAILED"and not entry.get("output")else"STAGE_SUCCEEDED")
                or detail_map[current["event_id"]].get("expected_key") != key):
            emit("PIPELINE_CURRENT_RUN_RECEIPT_MISMATCH",stage)
        if entry.get("output")is None:
            if state != "FAILED"or entry.get("result_ref")is not None or not entry.get("last_error"):
                emit("PIPELINE_MISSING_STAGE_OUTPUT",stage)
            origin = attempt_map.get(entry.get("origin_attempt_id"),{})
            if (origin.get("state") != "FAILED"or origin.get("expected_key") != key
                    or json.loads(origin.get("dependencies_json","null")) != dependencies
                    or json.loads(origin.get("implementation_json","null")) != implementation):
                emit("PIPELINE_STAGE_ORIGIN_MISMATCH",stage)
            blocked = True
            continue
        if state not in ({"DONE","PARTIAL","FAILED"}if stage == "recognition"else{"DONE"}):
            emit("PIPELINE_STAGE_STATE_MISMATCH",stage)
        try:
            wrapper = _read_object(root,entry["output"])
            wp = wrapper["payload"]
            expected_wrapper = {"mode":mode,"stage_id":stage,"expected_key":key,"dependencies":dependencies,
                "implementation":implementation,"attempt_id":entry.get("origin_attempt_id"),"decision":"HOLD",
                "transcription_verified":False,"business_acceptance":False,"platform_actions":[]}
            if (not _checked(wrapper,{"b-pipeline-stage-trial/0.1"},"PipelineStageTrial")
                    or {k:v for k,v in wp.items()if k != "result"} != expected_wrapper
                    or wrapper.get("artifact_id") != "pipeline-stage-"+digest(wp)[:24]
                    or wrapper.get("input_refs") != [_document_ref(source)]
                    or any(wrapper.get(k) != source[k]for k in ("book_id","scope_id"))
                    or wrapper.get("producer") != {"module":"annotation.recognition.pipeline","version":"0.1.0","code_sha256":code_digest(pipeline_path)}):
                emit("PIPELINE_STAGE_WRAPPER_MISMATCH",stage)
            result = wp["result"]
            if entry.get("result_ref") != _ref(result): emit("PIPELINE_STAGE_RESULT_REF_MISMATCH",stage)
            origin = attempt_map.get(wp.get("attempt_id"),{})
            if (origin.get("state") != "SUCCEEDED"or origin.get("stage_id") != stage or origin.get("expected_key") != key
                    or json.loads(origin.get("dependencies_json","null")) != dependencies
                    or json.loads(origin.get("implementation_json","null")) != implementation
                    or json.loads(origin.get("output_json","null")) != entry["output"]
                    or json.loads(origin.get("result_ref_json","null")) != _ref(result)):
                emit("PIPELINE_STAGE_ORIGIN_MISMATCH",stage)
            if entry.get("cached"):
                row = cache.get(key,{})
                if (state != "DONE"or row.get("stage_id") != stage or row.get("attempt_id") != wp.get("attempt_id")
                        or json.loads(row.get("output_json","null")) != entry["output"]
                        or json.loads(row.get("result_ref_json","null")) != _ref(result)):
                    emit("PIPELINE_CACHE_ORIGIN_MISMATCH",stage)
            if stage == "recognition":
                checked = audit_batch(source_path,root/"recognition",result)
                if not checked["payload"]["accepted"]:
                    emit("PIPELINE_RECOGNITION_INTEGRITY_REJECTED",stage,checked["payload"]["issues"])
                if implementation.get("recognizer") != result["payload"].get("recognizer"):
                    emit("PIPELINE_EXECUTION_KIND_MISMATCH",stage)
                complete = result["payload"].get("batch_complete")
                expected_state = "DONE"if complete else"FAILED"if result["payload"]["counts"]["failed"]else"PARTIAL"
                if state != expected_state: emit("PIPELINE_RECOGNITION_COMPLETENESS_MISMATCH",stage)
                if complete: results["baseline"] = _read_object(root/"recognition",result["payload"]["bundle"])
            elif stage in {"evidence","refine"}:
                _source_evidence(result,source,context,lambda code,**kwargs:emit(code,stage,kwargs.get("detail")))
                if stage == "evidence"and result != imported: emit("PIPELINE_CACHED_INPUT_CHANGED",stage)
                if stage == "refine"and result.get("input_refs") != [dependencies["baseline"]["result_ref"],receipts["context"]["reference"]]:
                    emit("PIPELINE_REFINED_INPUT_REFERENCE_MISMATCH",stage)
            elif stage == "recover":
                _source_evidence(result,source,context,lambda code,**kwargs:emit(code,stage,kwargs.get("detail")))
                recovery_check = audit_recovery_stage(source_path,recovery_path,results["evidence"],result)
                if not recovery_check["payload"]["accepted"]:
                    emit("PIPELINE_RECOVERY_MIGRATION_REJECTED",stage,recovery_check["payload"]["issues"])
            elif stage == "recovery_review":
                review_check = audit_recovery_review(review,results["evidence"],result)
                if not review_check["payload"]["accepted"]:
                    emit("PIPELINE_RECOVERY_REVIEW_REJECTED",stage,review_check["payload"]["issues"])
            elif stage == "assemble":
                e = results["evidence"]
                if continuation_path is not None and "created_at"in result:
                    emit("PIPELINE_CONTINUATION_VOLATILE_TIME",stage)
                units = _source_evidence(e,source,context,lambda code,**kwargs:emit(code,stage,kwargs.get("detail")))
                _graph_sources(e,result,units,lambda code,**kwargs:emit(code,stage,kwargs.get("detail")))
            elif stage == "quality":
                _quality_bindings(results["evidence"],results["assemble"],result,results.get("active_review",review),
                    lambda code,**kwargs:emit(code,stage,kwargs.get("detail")))
            elif stage in continuation_stages:
                if stage == "continuation_prepare":
                    checked = audit_continuation_scope(results["evidence"],results["assemble"],result,continuation_path,source_path,adjacent_source_path)
                elif stage == "continuation_proof":
                    checked = audit_continuation_proof_stage(results["continuation_prepare"],result,continuation_path,source_path,adjacent_source_path)
                elif stage == "continuation_apply":
                    checked = audit_continuation_apply_stage(results["continuation_prepare"],results["continuation_proof"],result,continuation_path,source_path,adjacent_source_path)
                else:
                    checked = audit_continued_quality(results["continuation_prepare"],results["continuation_proof"],results["continuation_apply"],
                        results.get("active_review",review),result,package_path=continuation_path,source_path=source_path,adjacent_source_path=adjacent_source_path)
                if not checked["payload"]["accepted"]:
                    emit("PIPELINE_CONTINUATION_STAGE_REJECTED",stage,checked["payload"]["issues"])
            if state == "DONE":
                results[stage] = result
                bindings[stage] = {"output":entry["output"],"result_ref":_ref(result)}
                if stage in {"refine","recover"}: results["evidence"],bindings["evidence"] = result,bindings[stage]
                if stage == "recovery_review": results["active_review"] = result["payload"]["review"]
            else: blocked = True
        except (OSError,ValueError,TypeError,KeyError)as exc:
            emit("PIPELINE_STAGE_OUTPUT_INVALID",stage,str(exc))
            blocked = True
        if stage == start_detail.get("stop_after"): stopped = True
    counts = {"declared_stages":len(stage_order),"done":sum(e.get("state") == "DONE"for e in stages),
        "pending":sum(e.get("state")in {"WAITING","PARTIAL"}for e in stages),"failed":sum(e.get("state") == "FAILED"for e in stages),
        "cache_hits":sum(e.get("cached")is True for e in stages),"invalidated":sum(e["event_type"] == "INVALIDATED"for e in run_events)}
    expected_pipeline_state = "FAILED"if counts["failed"]or p.get("run_error")is not None else"READY"if counts["done"] == len(stage_order)else"PARTIAL"
    if p.get("counts") != counts or p.get("pipeline_state") != expected_pipeline_state:
        emit("PIPELINE_FALSE_READINESS")
    if continuation_path is not None:
        expected_scope = {"package_receipt":receipts["continuation"],"base_source_ref":_document_ref(source),
            "adjacent_coverage":"PREFIX_CROP_ONLY_WITH_BOUNDARY_AND_FIGURES","full_adjacent_page_ocr":False,"viewer_page_mapping_verified":False}
        if p.get("continuation_scope") != expected_scope: emit("PIPELINE_CONTINUATION_SCOPE_MISMATCH")
        expected_final = None
        if expected_pipeline_state == "READY" and all(name in results for name in continuation_stages):
            expected_final = {"evidence_ref":_ref(results["continuation_prepare"]["payload"]["evidence"]),
                "graph_ref":_ref(results["continuation_apply"]["payload"]["graph"]),"quality_ref":_ref(results["continuation_quality"])}
        if p.get("final_outputs") != expected_final: emit("PIPELINE_CONTINUATION_FINAL_OUTPUTS_MISMATCH")
    summary.update(stage_count=len(stage_order),completed_stage_count=counts["done"],pipeline_state=expected_pipeline_state,
                   execution_kind=kind,counts=counts,current_run_attempt_count=sum(a["run_id"] == run_id for a in attempts))
    return finish()


def audit_pipeline(source_path,context_path,review_path,report,workdir,*,evidence_path=None,recovery_path=None,
                   continuation_path=None,adjacent_source_path=None):
    """Fail closed on bad inputs; do not certify business or execution signatures."""
    try:
        return _audit_pipeline(source_path,context_path,review_path,report,workdir,evidence_path=evidence_path,recovery_path=recovery_path,
            continuation_path=continuation_path,adjacent_source_path=adjacent_source_path)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,IndexError,sqlite3.Error)as exc:
        payload = {"accepted":False,"decision":"HOLD","issues":[{"code":"PIPELINE_PERSISTED_DATA_INVALID","severity":"ERROR",
            "detail":type(exc).__name__+": "+str(exc)}],"summary":{},"business_acceptance":False,
            "transcription_verified":False,"platform_actions":[]}
        inputs = [_ref(report)]if isinstance(report,dict)else[]
        producer = {"module":__name__,"version":"0.1.0","code_sha256":code_digest(Path(__file__))}
        return {"schema_version":SCHEMA,"kind":"PipelineCheckTrial",
            "artifact_id":"pipeline-check-"+digest([inputs,payload,producer])[:24],"revision":1,
            "run_id":report.get("run_id")if isinstance(report,dict)else None,
            "book_id":report.get("book_id")if isinstance(report,dict)else None,
            "scope_id":report.get("scope_id")if isinstance(report,dict)else None,
            "input_refs":inputs,"producer":producer,"content_hash":digest(payload),"payload":payload}
