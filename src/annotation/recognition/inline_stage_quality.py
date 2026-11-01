"""Independent audit of saved inline evidence and additive graph attachments.

Old observations/journals are inspected, never re-signed or re-executed. The
business graph core and every prior quality finding remain explicit archives.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path,PurePosixPath,PureWindowsPath
import re

from PIL import Image

from .baseline import code_digest,digest,file_digest
from .inline_ocr_quality import audit_inline_ocr
from .inline_formula_quality import audit_inline_formula

SCHEMA="b-inline-stage-check-trial/0.1"
POLICY="EXACT_SELECTED_PAGE_EQUIVALENCE_ONLY/0.1"
_HASH=re.compile(r"^[0-9a-f]{64}$")
_DOCS={"evidence","rows","ocr_observations","formula_observations","formula_report"}
_FLAGS={"decision":"HOLD","complete":False,"transcription_verified":False,"business_acceptance":False,"platform_actions":[],"new_model_calls":0}


def ref(value):return {k:value.get(k)if isinstance(value,dict)else None for k in ("artifact_id","revision","content_hash")}
def _pixels(image):return hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()
def _document(value):return {"artifact_id":value["artifact_id"],"content_hash":digest(value)}


def _path(root,name):
    if (not isinstance(name,str)or not name or "\\"in name or PurePosixPath(name).is_absolute()
            or PureWindowsPath(name).drive or any(p in {".",".."}for p in name.split("/"))or ""in name.split("/")):
        raise ValueError("inline package paths must be portable relative paths")
    candidate=root/name
    if not candidate.resolve().is_relative_to(root.resolve()):raise ValueError("inline package member escapes package")
    for p in (candidate,*candidate.parents):
        if p==root.parent:break
        if p.is_symlink():raise ValueError("inline package member uses a symlink")
    return candidate


def _checked(value,schema,kind):
    return (isinstance(value,dict)and value.get("schema_version")in schema and value.get("kind")==kind
        and isinstance(value.get("artifact_id"),str)and bool(value["artifact_id"])and type(value.get("revision"))is int and value["revision"]>=1
        and isinstance(value.get("payload"),dict)and value.get("content_hash")==digest(value["payload"]))


def semantic_receipt(receipt):
    result=copy.deepcopy(receipt);result["package"].pop("file_sha256",None)
    result["receipt_policy"]="NORMALIZED_PACKAGE_JSON_CONTENT/0.1"
    return result


def inspect_inline_package(package_path,original_path):
    """Verify all listed saved bytes and the actual selected original image."""
    package_path,original_path=Path(package_path),Path(original_path);root=package_path.parent
    manifest=json.loads(package_path.read_text(encoding="utf8"))
    keys={"schema_version","artifact_id","book_id","scope_id","asset_id","line_ids","policy","documents","journal_dir","members"}
    if (set(manifest)!=keys or manifest.get("schema_version")!="b-inline-package-trial/0.1"or manifest.get("policy")!=POLICY
            or any(not isinstance(manifest.get(k),str)or not manifest[k]for k in ("artifact_id","book_id","scope_id","asset_id"))
            or set(manifest.get("documents",{}))!=_DOCS):raise ValueError("invalid inline package schema or document scope")
    ids=manifest["line_ids"]
    if not isinstance(ids,list)or not ids or any(not isinstance(x,str)or not x for x in ids)or len(ids)!=len(set(ids)):raise ValueError("inline package needs complete unique line scope")
    journal=_path(root,manifest["journal_dir"]).resolve()
    if not journal.is_dir()or not(journal/"inline-formula.sqlite3").is_file():raise ValueError("inline journal is missing")
    docs={};paths=[]
    definitions={"evidence":({"b-evidence-trial/0.2","b-evidence-trial/0.3"},"EvidenceBundleTrial"),
        "ocr_observations":({"b-inline-ocr-observation-trial/0.1"},"InlineOCRObservationTrial"),
        "formula_observations":({"b-inline-formula-observation-trial/0.1"},"InlineFormulaObservationTrial"),
        "formula_report":({"b-inline-formula-run-trial/0.1"},"InlineFormulaRunTrial")}
    for name,descriptor in manifest["documents"].items():
        if set(descriptor)!={"path","sha256","artifact_ref"}or not _HASH.fullmatch(descriptor.get("sha256","")):raise ValueError("invalid inline document descriptor")
        path=_path(root,descriptor["path"]);paths.append(path)
        if path.resolve().is_relative_to(journal)or not path.is_file()or file_digest(path)!=descriptor["sha256"]:raise ValueError("inline document bytes changed or overlap the journal")
        value=json.loads(path.read_text(encoding="utf8"))
        if name=="rows":
            if value!=ids or descriptor["artifact_ref"]is not None:raise ValueError("inline external line scope changed")
        elif (not _checked(value,*definitions[name])or ref(value)!=descriptor["artifact_ref"]
                or any(value.get(k)!=manifest[k]for k in ("book_id","scope_id"))):raise ValueError("inline document artifact binding changed")
        docs[name]=value
    expected={path.relative_to(root).as_posix()for path in paths}
    for path in journal.rglob("*"):
        if path.is_symlink():raise ValueError("inline journal contains a symlink")
        if path.is_file():expected.add(path.relative_to(root.resolve()).as_posix())
    if len(paths)!=len(set(p.resolve()for p in paths))or set(manifest["members"])!=expected:raise ValueError("inline package member scope missing or duplicated")
    resolved=set()
    for name,descriptor in manifest["members"].items():
        path=_path(root,name)
        if (set(descriptor)!={"sha256","bytes"}or not _HASH.fullmatch(descriptor.get("sha256",""))or type(descriptor.get("bytes"))is not int
                or descriptor["bytes"]<0 or not path.is_file()or path.resolve()in resolved
                or path.stat().st_size!=descriptor["bytes"]or file_digest(path)!=descriptor["sha256"]):raise ValueError("inline package member bytes or ownership changed")
        resolved.add(path.resolve())
    pages=[p for p in docs["evidence"]["payload"]["pages"]if p["asset_id"]==manifest["asset_id"]]
    if len(pages)!=1:raise ValueError("inline source page missing or duplicated")
    page=pages[0];asset=page["source"]
    if asset["asset_id"]!=manifest["asset_id"]or file_digest(original_path)!=asset["sha256"]:raise ValueError("inline original source SHA changed")
    with Image.open(original_path)as image:
        if image.size!=(asset["width"],asset["height"]):raise ValueError("inline source dimensions changed")
        rgb=_pixels(image)
    raw={line["line_id"]:line for line in page["ocr_lines"]}
    if len(raw)!=len(page["ocr_lines"])or any(lid not in raw for lid in ids):raise ValueError("inline requested source lines missing or duplicated")
    receipt={"book_id":manifest["book_id"],"scope_id":manifest["scope_id"],"asset_id":manifest["asset_id"],
        "package":{"reference":_document(manifest),"file_sha256":file_digest(package_path)},"documents":copy.deepcopy(manifest["documents"]),
        "journal_dir":manifest["journal_dir"],"members":copy.deepcopy(manifest["members"]),
        "source":{"asset_id":asset["asset_id"],"sha256":asset["sha256"],"width":asset["width"],"height":asset["height"],"rgb_sha256":rgb}}
    return {"manifest":manifest,"receipt":receipt,"documents":docs,"journal_dir":journal,"source_path":original_path}


def _producer(operation):
    names=("baseline","inline_ocr","inline_ocr_quality","inline_math","inline_formula","inline_candidates","inline_formula_quality",
        "inline_continuity","formula_canvas","formula_canvas_quality","formula_syntax","formula_quality")
    return {"module":"annotation.recognition.inline_stage","version":"0.1.0","operation":operation,
        "code_sha256":code_digest(Path(__file__).with_name("inline_stage.py")),
        "dependency_code_sha256":{n:code_digest(Path(__file__).with_name(n+".py"))for n in names},
        "identity_policy":"CURRENT_REFS_WITH_EXECUTION_TIME_IN_JOURNAL/0.1","policy":POLICY,"new_model_calls":0}


def _header(value,schema,kind,prefix,source,inputs,operation,emit):
    keys={"schema_version","kind","revision","book_id","scope_id","input_refs","producer","payload","artifact_id","content_hash"}
    body={k:v for k,v in value.items()if k not in {"artifact_id","content_hash"}}
    if (set(value)!=keys or value.get("schema_version")!=schema or value.get("kind")!=kind or type(value.get("revision"))is not int or value.get("revision")!=1
            or any(value.get(k)!=source[k]for k in ("book_id","scope_id"))or value.get("input_refs")!=inputs
            or digest(value.get("producer"))!=digest(_producer(operation))or value.get("content_hash")!=digest(value.get("payload"))
            or value.get("artifact_id")!=prefix+"-"+digest(body)[:24]):emit("INLINE_STAGE_HEADER_OR_IDENTITY_MISMATCH",kind)


def _finish(kind,values,issues,summary):
    inputs=[ref(v)for v in values];source=values[0]if values and isinstance(values[0],dict)else{}
    payload={"accepted":not issues,"issues":issues,"summary":summary,**_FLAGS}
    producer={"module":__name__,"version":"0.1.0","code_sha256":code_digest(Path(__file__))}
    return {"schema_version":SCHEMA,"kind":kind,"artifact_id":"inline-stage-check-"+digest([inputs,producer,payload])[:24],"revision":1,
        **{k:source.get(k)for k in ("book_id","scope_id")},"input_refs":inputs,"producer":producer,"content_hash":digest(payload),"payload":payload}


def _safe(kind,values,operation):
    issues=[]
    def emit(code,detail=None):
        item={"code":code,"severity":"ERROR","detail":detail}
        if item not in issues:issues.append(item)
    try:summary=operation(emit)
    except (OSError,ValueError,TypeError,KeyError,IndexError,AttributeError,OverflowError,RecursionError,StopIteration)as exc:
        emit("INLINE_STAGE_DATA_INVALID",type(exc).__name__+": "+str(exc));summary={}
    return _finish(kind,values,issues,summary)


def _bindings(evidence,graph,asset_id,line_ids):
    if (not _checked(evidence,{"b-evidence-trial/0.2","b-evidence-trial/0.3"},"EvidenceBundleTrial")
            or not _checked(graph,{"b-graph-trial/0.2","b-graph-trial/0.3","b-graph-trial/0.4"},"QuestionGraphTrial")
            or any(graph[k]!=evidence[k]for k in ("book_id","scope_id"))or ref(evidence)not in graph.get("input_refs",[])or "inline_content"in graph["payload"]):
        raise ValueError("inline current graph is not an unextended evidence-bound graph")
    page=next(p for p in evidence["payload"]["pages"]if p["asset_id"]==asset_id)
    raw={l["line_id"]:l for l in page["ocr_lines"]};units={l["line_id"]:l for l in page["ocr_lines"]+page.get("answer_detail_lines",[])}
    if len(raw)!=len(page["ocr_lines"])or len(units)!=len(page["ocr_lines"])+len(page.get("answer_detail_lines",[])):raise ValueError("duplicate inline source identity")
    rows=[]
    for lid in line_ids:
        owners=[]
        for kind,collection,idfield in (("question","questions","question_id"),("answer","answers","answer_id")):
            for entity in graph["payload"][collection]:
                for fragment in entity["fragments"]:
                    refs=fragment.get("evidence_refs",[])
                    parents={units[r].get("parent_line_id",r)for r in refs if r in units}
                    claimed=fragment.get("parent_line_id")
                    if lid not in parents and claimed!=lid and lid not in refs:continue
                    if len(refs)!=1 or refs[0]not in units or parents!={lid}or claimed is not None and claimed!=lid or fragment.get("asset_id")!=asset_id:
                        raise ValueError("inline fragment canonical source parent differs from its claimed row")
                    source=units[refs[0]];span=fragment.get("text_span",[0,len(source["text"])])
                    if (not isinstance(span,list)or len(span)!=2 or any(type(n)is not int for n in span)or not 0<=span[0]<span[1]<=len(source["text"])
                            or fragment.get("raw_text",source["text"])!=source["text"]or fragment.get("text")!=source["text"][span[0]:span[1]]
                            or fragment.get("bbox")!=source["bbox"]):raise ValueError("inline fragment is not its literal current source span")
                    regions=entity.get("render_regions",entity.get("regions",[]))
                    rids=[r.get("region_id",r.get("fragment_id"))for r in regions if fragment["fragment_id"]in r.get("source_fragment_ids",[r.get("fragment_id")])]
                    owners.append({"entity_kind":kind,"entity_id":entity[idfield],"answer_id":entity[idfield]if kind=="answer"else None,
                        "fragment_id":fragment["fragment_id"],"text_span":span,"role":fragment["role"],"render_region_ids":rids})
        rows.append({"line_id":lid,"source_line_sha256":digest(raw[lid]),"fragments":owners,"unassigned":not owners})
    return rows


_MATH=r'A-Za-z0-9\u0370-\u03ff\u2070-\u209f²³¹=+\-−×÷*/^_<>≤≥≠≈±∓√∛∜().（）\[\]{}:：|∥'
_OPEN='=+−-×÷*/^_(（<≤≥>:：'
_RELATIONS='<>≤≥'
_CONTINUITY_POLICY=dict(version='LITERAL_CURRENT_GRAPH_LINE_WRAP/0.1',math_char_class=_MATH,open_markers=_OPEN,
    relations=_RELATIONS,max_vertical_gap_in_line_heights=2.5,minimum_horizontal_overlap_of_shorter_row=.5,
    ordering='CENTER_Y_THEN_X_THEN_LINE_ID',intermediate_rows='ALL_RAW_ROWS_SAME_LOCATION',
    source_spans='EXACT_OCR_SUBSTRINGS',single_asset_only=True,glyph_localization_verified=False)


def _literal_owner(graph,page,line,span):
    rows=[r for r in graph['payload']['answer_coverage']if r.get('asset_id')==page['asset_id']and r.get('line_id')==line['line_id']]
    if len(rows)!=1 or rows[0].get('status')!='CONSUMED':return None,'SOURCE_NOT_UNIQUELY_CONSUMED'
    matches=[]
    for answer in graph['payload']['answers']:
        for f in answer.get('fragments',[]):
            if f.get('asset_id')!=page['asset_id']or f.get('parent_line_id')!=line['line_id']:continue
            s=f.get('text_span');text=line['text']
            if not isinstance(s,list)or len(s)!=2 or any(type(x)is not int for x in s)or not 0<=s[0]<s[1]<=len(text):return None,'FRAGMENT_SOURCE_SPAN_INVALID'
            if s[1]<=span[0]or s[0]>=span[1]:continue
            if (f.get('content_type')!='text'or f.get('represented_by_image_region')is not None or f.get('render_as_separate_region')is False
                    or f.get('structural_marker')is True or f.get('role')not in {'answer','explanation'}or f.get('text')!=text[s[0]:s[1]]
                    or f.get('source_sha256',page['source']['sha256'])!=page['source']['sha256']):return None,'FRAGMENT_NOT_LITERAL_TEXT'
            allocations=[a for a in rows[0].get('allocations',[])if a.get('answer_id')==answer['answer_id']and a.get('fragment_id')==f['fragment_id']and a.get('text_span')==s]
            if len(allocations)!=1:return None,'FRAGMENT_ALLOCATION_MISMATCH'
            regions=sorted(r['region_id']for r in answer.get('render_regions',[])if r.get('content_type')=='text'and r.get('asset_id')==page['asset_id']and f['fragment_id']in r.get('source_fragment_ids',[]))
            matches.append(dict(answer_id=answer['answer_id'],role=f['role'],fragment_id=f['fragment_id'],text_span=s,
                overlap_span=[max(span[0],s[0]),min(span[1],s[1])],render_region_ids=regions))
    if not matches:return None,'NO_CURRENT_TEXT_OWNER'
    if len({(m['answer_id'],m['role'])for m in matches})!=1:return None,'AMBIGUOUS_OR_MIXED_ROLE_OWNER'
    matches.sort(key=lambda m:(m['overlap_span'],m['fragment_id']));cursor=span[0]
    for m in matches:
        if m['overlap_span'][0]!=cursor:return None,'FRAGMENT_COVERAGE_GAP_OR_OVERLAP'
        cursor=m['overlap_span'][1]
    if cursor!=span[1]:return None,'FRAGMENT_COVERAGE_GAP_OR_OVERLAP'
    return dict(answer_id=matches[0]['answer_id'],role=matches[0]['role'],fragments=matches),None


def _continuity(evidence,graph,layout,candidates,asset_id,line_ids):
    """Independent reading-order, raw-span and literal ledger reconstruction."""
    page=next(p for p in evidence['payload']['pages']if p['asset_id']==asset_id)
    raw=page['ocr_lines'];by_id={r['line_id']:r for r in raw};units={u['unit_id']:u for u in layout['payload']['units']}
    if len(by_id)!=len(raw)or len(units)!=len(layout['payload']['units']):raise ValueError('duplicate continuity source identity')
    def loc(r):
        v=r.get('location',{});return v.get('column'),v.get('window_index'),v.get('section_path')
    def known(v):return type(v[0])is int and v[0]>=0 and type(v[1])is int and v[1]>=0 and isinstance(v[2],list)and bool(v[2])and all(isinstance(s,str)and bool(s)for s in v[2])
    def order(r):return ((r['bbox'][1]+r['bbox'][3])/2,r['bbox'][0],r['line_id'])
    for row in raw:
        box=row.get('bbox')
        if not isinstance(row.get('text'),str)or not isinstance(box,list)or len(box)!=4 or any(type(n)not in (int,float)or not math.isfinite(n)for n in box)or box[2]<=box[0]or box[3]<=box[1]:raise ValueError('invalid continuity raw source')
    proposals=[];rejected=[];diagnostics=[]
    for lid,rid in zip(line_ids,line_ids[1:]):
        left,right=by_id[lid],by_id[rid];a,b=left['bbox'],right['bbox'];reason=None
        if not known(loc(left))or not known(loc(right)):reason='SOURCE_LOCATION_UNKNOWN'
        elif loc(left)!=loc(right):reason='DIFFERENT_COLUMN_WINDOW_OR_SECTION'
        elif order(left)>=order(right):reason='REQUESTED_ROWS_NOT_IN_SOURCE_READING_ORDER'
        elif any(loc(r)==loc(left)and order(left)<order(r)<order(right)for r in raw):reason='INTERVENING_RAW_SOURCE_ROW'
        elif b[1]-a[3]<0 or b[1]-a[3]>2.5*max(a[3]-a[1],b[3]-b[1]):reason='VERTICAL_WRAP_GEOMETRY_UNPROVEN'
        elif max(0,min(a[2],b[2])-max(a[0],b[0]))<.5*min(a[2]-a[0],b[2]-b[0]):reason='HORIZONTAL_COLUMN_GEOMETRY_UNPROVEN'
        if reason is None and re.match(r'^\s*(?:\d+\s*[.、](?!\d)|[A-G]\s*[.、]|[（(]\d+[）)]|[①②③④⑤⑥⑦⑧⑨⑩])',right['text']):reason='NEXT_ROW_LOOKS_LIKE_NEW_QUESTION'
        lm=re.search('['+_MATH+']+$',left['text']);rm=re.match('['+_MATH+']+',right['text']);kind=None
        if reason is None and lm and rm:
            lt,rt=lm.group(),rm.group()
            if lt[-1]in _OPEN and any(c.isalnum()for c in lt)and any(c.isalnum()for c in rt):kind='OPEN_EQUATION_LINE_WRAP'
            elif rt[0]in _RELATIONS and any(c in _RELATIONS for c in lt)and any(c.isalnum()for c in rt):kind='CHAINED_RELATION_LINE_WRAP'
        if reason is None and kind is None:reason='NO_EXPLICIT_MATH_WRAP_MARKER'
        spans=[];bindings=[]
        if reason is None:
            for row,match in ((left,lm),(right,rm)):
                spans.append(dict(asset_id=asset_id,line_id=row['line_id'],text_span=list(match.span()),text=match.group()))
                binding,error=_literal_owner(graph,page,row,match.span())
                if error:reason=error;break
                bindings.append(binding)
            if reason is None and any(bindings[0][k]!=bindings[1][k]for k in ('answer_id','role')):reason='DIFFERENT_CURRENT_ANSWER_OR_ROLE'
        if reason:
            rejected.append(dict(left_line_id=lid,right_line_id=rid,reason=reason));continue
        risks=['UNVERIFIED_RAW_OCR','HEURISTIC_MATH_BOUNDARIES','SINGLE_ASSET_RELATION_ONLY']
        joined=lm.group()+rm.group()
        if '.'in joined:risks.append('DOT_MAY_BE_PUNCTUATION_OR_DECIMAL')
        proposal=dict(kind=kind,left_line_id=lid,right_line_id=rid,source_spans=spans,bindings=bindings,joined_raw_text=joined,
            evidence_quality='LITERAL_UNVERIFIED_OCR_SPANS',risks=risks,selected=False,complete=False,transcription_verified=False,business_acceptance=False)
        proposal['proposal_id']='inline-wrap-'+digest([ref(evidence),ref(graph),proposal])[:24];proposals.append(proposal)
        if kind=='OPEN_EQUATION_LINE_WRAP'and lm.group().endswith('='):
            for candidate in candidates['payload']['candidates']:
                for binding in candidate['unit_bindings']:
                    u=units.get(binding['unit_id']);raw_latex=candidate.get('raw_latex')
                    if (u is not None and u.get('line_id')==lid and u.get('raw_text','').endswith('=')and isinstance(raw_latex,str)
                            and re.search(r'=[^=]*[A-Za-z0-9}]\s*$',raw_latex)):
                        diagnostics.append(dict(code='MODEL_CLOSURE_AFTER_RAW_OPEN_EQUATION',proposal_id=proposal['proposal_id'],unit_id=u['unit_id'],
                            call_id=candidate['call_id'],candidate_id=candidate['candidate_id'],raw_latex=raw_latex))
    payload=dict(asset_id=asset_id,requested_line_ids=line_ids,source_sha256=page['source']['sha256'],proposals=proposals,diagnostics=diagnostics,
        rejected_adjacent_pairs=rejected,selected_proposal_ids=[],decision='HOLD',complete=False,transcription_verified=False,
        business_acceptance=False,graph_modified=False,platform_actions=[],new_model_calls=0,expected_text_consumed=False)
    body=dict(schema_version='b-inline-continuity-trial/0.1',kind='InlineContinuityTrial',revision=1,book_id=evidence['book_id'],scope_id=evidence['scope_id'],
        input_refs=[ref(v)for v in (evidence,graph,layout,candidates)],producer=dict(module='annotation.recognition.inline_continuity',version='0.1.0',
            code_sha256=code_digest(Path(__file__).with_name('inline_continuity.py')),policy=_CONTINUITY_POLICY),payload=payload)
    return {**body,'artifact_id':'inline-continuity-'+digest(body)[:24],'content_hash':digest(payload)}


def _prepare(evidence,graph,prepared,package_path,original_path,emit):
    package=inspect_inline_package(package_path,original_path);m,docs=package['manifest'],package['documents'];p=prepared['payload'];old=docs['evidence']
    _header(prepared,'b-inline-preparation-trial/0.1','InlinePreparationTrial','inline-preparation',evidence,
        [ref(evidence),ref(graph),package['receipt']['package']['reference']],'prepare',emit)
    current=[page for page in evidence['payload']['pages']if page['asset_id']==m['asset_id']]
    original=[page for page in old['payload']['pages']if page['asset_id']==m['asset_id']]
    if (any(evidence[k]!=old[k]for k in ('book_id','scope_id'))or digest(evidence['payload']['context'])!=digest(old['payload']['context'])
            or len(current)!=1 or digest(current)!=digest(original)):emit('INLINE_SELECTED_PAGE_EQUIVALENCE_MISMATCH')
    layout=docs['formula_observations']['payload']['layout_archive'];candidates=p['candidates']
    ordinary=audit_inline_ocr(old,docs['ocr_observations'],original_path,line_ids=m['line_ids'])
    formulas=audit_inline_formula(old,layout,docs['formula_observations'],candidates,original_path,line_ids=m['line_ids'],workdir=package['journal_dir'],report=docs['formula_report'])
    if not ordinary['payload']['accepted']or not formulas['payload']['accepted']:emit('INLINE_SAVED_OBSERVATIONS_REJECTED',{'ocr':ordinary['payload']['issues'],'formula':formulas['payload']['issues']})
    state=docs['formula_report']['payload']['state']
    if state not in {'READY','PARTIAL','FAILED'}:raise ValueError('unknown saved inline execution state')
    if (not ordinary['payload']['accepted']or not formulas['payload']['accepted']or any(v['recognition_error']is not None for row in docs['ocr_observations']['payload']['rows']for v in row['variants'])):state='FAILED'
    counts=dict(rows=len(m['line_ids']),units=len(layout['payload']['units']),**{k:docs['formula_report']['payload']['counts'][k]for k in ('declared_calls','done','pending','failed')})
    expected=dict(base_evidence_ref=ref(evidence),base_graph_ref=ref(graph),base_evidence_archive=evidence,base_graph_archive=graph,
        package_receipt=semantic_receipt(package['receipt']),original_evidence_archive=old,ocr_observations_archive=docs['ocr_observations'],layout_archive=layout,
        formula_observations_archive=docs['formula_observations'],formula_report_archive=docs['formula_report'],candidates=candidates,
        ocr_check=ordinary,formula_check=formulas,continuity=_continuity(evidence,graph,layout,candidates,m['asset_id'],m['line_ids']),
        bindings=_bindings(evidence,graph,m['asset_id'],m['line_ids']),execution_state=state,counts=counts,**_FLAGS)
    if digest(p)!=digest(expected):emit('INLINE_PREPARATION_PROJECTION_MISMATCH')
    return expected,package


def audit_inline_preparation(evidence,graph,prepared,package_path,original_path):
    def inspect(emit):
        expected,_=_prepare(evidence,graph,prepared,package_path,original_path,emit)
        return {'execution_state':expected['execution_state'],**expected['counts']}
    return _safe('InlinePreparationCheckTrial',[evidence,graph,prepared],inspect)


def _application(prepared,application,package_path,original_path,emit):
    p=prepared['payload'];e,g=p['base_evidence_archive'],p['base_graph_archive']
    expected,_=_prepare(e,g,prepared,package_path,original_path,emit)
    if expected['execution_state']!='READY':emit('INLINE_APPLICATION_REQUIRES_READY')
    _header(application,'b-inline-apply-stage-trial/0.1','InlineApplyStageTrial','inline-apply-stage',e,[ref(prepared)],'apply',emit)
    derived=application['payload']['graph']
    _header(derived,'b-graph-trial/0.5','QuestionGraphTrial','inline-graph',e,[ref(e),ref(g),ref(prepared)],'attach',emit)
    attachment=dict(prepared_ref=ref(prepared),base_evidence_ref=ref(e),base_graph_ref=ref(g),base_graph_archive=g,package_receipt=p['package_receipt'],
        units=p['layout_archive']['payload']['units'],calls=p['formula_observations_archive']['payload']['calls'],
        not_inference_units=p['formula_observations_archive']['payload']['not_inference_units'],candidates=p['candidates']['payload']['candidates'],
        bindings=expected['bindings'],continuity=expected['continuity'],selected_unit_ids=[],selected_candidate_refs=[],**_FLAGS)
    core={k:v for k,v in derived['payload'].items()if k!='inline_content'}
    if digest(core)!=digest(g['payload']):emit('INLINE_GRAPH_CORE_CHANGED')
    if digest(derived['payload'].get('inline_content'))!=digest(attachment):emit('INLINE_ATTACHMENT_SCOPE_OR_BINDING_MISMATCH')
    expected_payload=dict(prepared_ref=ref(prepared),base_evidence_ref=ref(e),base_graph_ref=ref(g),package_receipt=p['package_receipt'],graph=derived,**_FLAGS)
    if digest(application['payload'])!=digest(expected_payload):emit('INLINE_APPLICATION_PROJECTION_MISMATCH')
    return expected


def audit_inline_application(prepared,application,package_path,original_path):
    def inspect(emit):
        p=_application(prepared,application,package_path,original_path,emit)
        graph=application['payload']['graph']['payload']
        return {'core_unchanged':digest({k:v for k,v in graph.items()if k!='inline_content'})==digest(p['base_graph_archive']['payload']),**p['counts']}
    return _safe('InlineApplicationCheckTrial',[prepared,application],inspect)


def audit_inline_quality(prepared,application,base_check,check,package_path,original_path):
    def inspect(emit):
        p=_application(prepared,application,package_path,original_path,emit);e,g=p['base_evidence_archive'],p['base_graph_archive'];derived=application['payload']['graph']
        if (not _checked(base_check,{'b-check-trial/0.2','b-check-trial/0.3','b-check-trial/0.4'},'CheckReportTrial')
                or any(base_check[k]!=e[k]for k in ('book_id','scope_id'))or base_check['payload'].get('decision')!='HOLD'
                or any(base_check['payload'].get(k,False)is not False for k in ('business_acceptance','transcription_verified'))
                or base_check['payload'].get('platform_actions',[])!=[]):emit('INLINE_BASE_CHECK_INVALID')
        if base_check['schema_version']=='b-check-trial/0.4':
            if (base_check['payload'].get('evidence_ref')!=ref(e)or base_check['payload'].get('graph_ref')!=ref(g)
                    or ref(e)not in base_check['input_refs']or ref(g)not in base_check['input_refs']):emit('INLINE_BASE_CHECK_SOURCE_MISMATCH')
        elif base_check['input_refs'][:2]!=[ref(e),ref(g)]:emit('INLINE_BASE_CHECK_SOURCE_MISMATCH')
        _header(check,'b-check-trial/0.5','CheckReportTrial','inline-check',e,[ref(e),ref(derived),ref(base_check),ref(prepared),ref(application)],'quality',emit)
        risks=copy.deepcopy(p['ocr_check']['payload']['observation_risks']+p['formula_check']['payload']['observation_risks']+p['continuity']['payload']['diagnostics'])
        expected=copy.deepcopy(base_check['payload'])
        expected.update(stage='inline_quality',base_check_archive=base_check,package_receipt=p['package_receipt'],evidence_ref=ref(e),graph_ref=ref(derived),inline_counts=p['counts'],inline_risks=risks,
            inline_basis=dict(base_evidence_ref=ref(e),base_graph_ref=ref(g),base_check_ref=ref(base_check),prepared_ref=ref(prepared),application_ref=ref(application),core_payload_sha256=digest(g['payload']),core_unchanged=True),**_FLAGS)
        finding=dict(code='INLINE_CONTENT_TRANSCRIPTION_UNVERIFIED',scope_type='scope',scope_id=e['scope_id'],evidence_refs=p['layout_archive']['payload']['requested_line_ids'],
            severity='REVIEW',blocks=['PRE_APPLY'],suggested_strategy='REVIEW_OFFLINE',detail=dict(inline_counts=p['counts'],risk_count=len(risks),base_core_check_reused_only_for_exact_unchanged_payload=True,text_selected=False))
        finding['issue_id']='issue-'+digest(finding)[:24];expected['issues'].append(finding)
        unsupported=[c for c in p['candidates']['payload']['candidates']if not c['parse_result']['supported']]
        grouped=[]
        if unsupported:grouped.append(('INLINE_FORMULA_SYNTAX_UNSUPPORTED',dict(call_ids=[c['call_id']for c in unsupported],candidate_ids=[c['candidate_id']for c in unsupported])))
        if p['continuity']['payload']['diagnostics']:grouped.append(('INLINE_FORMULA_SOURCE_WRAP_CLOSURE_CONFLICT',dict(diagnostics=p['continuity']['payload']['diagnostics'],source_bindings=p['bindings'])))
        for code,detail in grouped:
            item=dict(code=code,scope_type='scope',scope_id=e['scope_id'],evidence_refs=p['layout_archive']['payload']['requested_line_ids'],severity='REVIEW',blocks=['PRE_APPLY'],suggested_strategy='REVIEW_OFFLINE',detail=detail)
            item['issue_id']='issue-'+digest(item)[:24];expected['issues'].append(item)
        expected['summary']['issues']=len(expected['issues'])
        if digest(check['payload'])!=digest(expected):emit('INLINE_CHECK_PRESERVATION_OR_RISK_MISMATCH')
        return {'base_findings':len(base_check['payload']['issues']),'current_findings':len(expected['issues']),'risk_count':len(risks)}
    return _safe('InlineQualityCheckTrial',[prepared,application,base_check,check],inspect)
