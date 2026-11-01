"""Read-only inline observation stages; attach alternatives, never rewrite text."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath

from PIL import Image

from .baseline import code_digest, digest, file_digest
from .inline_ocr import plan_inline_rows
from .inline_ocr_quality import audit_inline_ocr
from .inline_formula_quality import audit_inline_formula
from .inline_candidates import build_inline_candidates

PACKAGE_SCHEMA = "b-inline-package-trial/0.1"
PREPARE_SCHEMA = "b-inline-preparation-trial/0.1"
APPLY_SCHEMA = "b-inline-apply-stage-trial/0.1"
POLICY = "EXACT_SELECTED_PAGE_EQUIVALENCE_ONLY/0.1"
IDENTITY_POLICY = "CURRENT_REFS_WITH_EXECUTION_TIME_IN_JOURNAL/0.1"
CONTENT_POLICY = "NORMALIZED_PACKAGE_JSON_CONTENT/0.1"
DOCUMENTS = {"evidence": ("b-evidence-trial/0.2", "b-evidence-trial/0.3"), "rows": None,
             "ocr_observations": ("b-inline-ocr-observation-trial/0.1",),
             "formula_observations": ("b-inline-formula-observation-trial/0.1",),
             "formula_report": ("b-inline-formula-run-trial/0.1",)}


def reference(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def _flags():
    return {"decision": "HOLD", "complete": False, "transcription_verified": False,
            "business_acceptance": False, "platform_actions": [], "new_model_calls": 0}


def _checked(value, schemas):
    if (not isinstance(value, dict) or value.get("schema_version") not in schemas
            or not isinstance(value.get("payload"), dict) or value.get("content_hash") != digest(value["payload"])
            or type(value.get("revision")) is not int or value["revision"] < 1
            or any(not isinstance(value.get(key), str) or not value[key] for key in ("artifact_id", "book_id", "scope_id"))):
        raise ValueError("invalid inline stage artifact identity, schema or payload")


def _path(root, relative, *, directory=False):
    if (not isinstance(relative, str) or not relative or "\\" in relative or PurePosixPath(relative).is_absolute()
            or PureWindowsPath(relative).drive or any(part in {"", ".", ".."} for part in relative.split("/"))):
        raise ValueError("inline package paths must be portable and relative")
    candidate = root/relative
    for part in (candidate, *candidate.parents):
        if part == root.parent: break
        if part.is_symlink(): raise ValueError("inline package members cannot use symlinks")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()) or not (resolved.is_dir() if directory else resolved.is_file()):
        raise ValueError("inline package member missing or escaping its root")
    return resolved


def _read(path):
    def invalid(value): raise ValueError("nonfinite inline JSON: "+value)
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=invalid)


def content_receipt(receipt):
    result = copy.deepcopy(receipt)
    result["package"].pop("file_sha256")
    result["receipt_policy"] = CONTENT_POLICY
    return result


def load_inline_package(package_path, original_path):
    """Validate exact declared files and original pixels without model imports."""
    package_path, original_path = Path(package_path), Path(original_path)
    manifest, root = _read(package_path), package_path.parent
    keys = {"schema_version", "artifact_id", "book_id", "scope_id", "asset_id", "line_ids", "policy", "documents", "journal_dir", "members"}
    if (not isinstance(manifest, dict) or set(manifest) != keys or manifest.get("schema_version") != PACKAGE_SCHEMA
            or manifest.get("policy") != POLICY or any(not isinstance(manifest.get(k), str) or not manifest[k] for k in ("artifact_id", "book_id", "scope_id", "asset_id"))
            or not isinstance(manifest.get("documents"), dict) or set(manifest["documents"]) != set(DOCUMENTS)
            or not isinstance(manifest.get("members"), dict)):
        raise ValueError("invalid inline package manifest")
    journal = _path(root, manifest["journal_dir"], directory=True)
    if not (journal/"inline-formula.sqlite3").is_file():
        raise ValueError("inline package requires its actual formula journal")
    documents, paths = {}, set()
    for name, schemas in DOCUMENTS.items():
        descriptor = manifest["documents"][name]
        if not isinstance(descriptor, dict) or set(descriptor) != {"path", "sha256", "artifact_ref"}:
            raise ValueError("invalid inline document descriptor")
        path = _path(root, descriptor["path"])
        if descriptor["path"] in paths or path.is_relative_to(journal) or file_digest(path) != descriptor["sha256"]:
            raise ValueError("duplicate, changed or journal-overlapping inline document")
        paths.add(descriptor["path"])
        value = _read(path)
        if schemas:
            _checked(value, schemas)
            kinds = {"evidence": "EvidenceBundleTrial", "ocr_observations": "InlineOCRObservationTrial",
                     "formula_observations": "InlineFormulaObservationTrial", "formula_report": "InlineFormulaRunTrial"}
            if value.get("kind") != kinds[name]:
                raise ValueError("inline document kind differs from its declared role")
            if reference(value) != descriptor["artifact_ref"] or (value["book_id"], value["scope_id"]) != (manifest["book_id"], manifest["scope_id"]):
                raise ValueError("inline document ref or scope differs from package")
        elif descriptor["artifact_ref"] is not None or value != manifest["line_ids"]:
            raise ValueError("inline rows require the exact external line scope")
        documents[name] = value
    journal_files = {p.relative_to(root.resolve()).as_posix() for p in journal.rglob("*") if p.is_file()}
    expected = paths | journal_files
    if set(manifest["members"]) != expected:
        raise ValueError("inline package member set does not cover all documents and journal files")
    for relative, entry in manifest["members"].items():
        path = _path(root, relative)
        if (not isinstance(entry, dict) or set(entry) != {"sha256", "bytes"} or type(entry["bytes"]) is not int
                or entry["bytes"] != path.stat().st_size or entry["sha256"] != file_digest(path)):
            raise ValueError("inline member bytes or SHA-256 changed: "+relative)
    evidence = documents["evidence"]
    image, source, _ = plan_inline_rows(evidence, original_path, asset_id=manifest["asset_id"], line_ids=manifest["line_ids"])
    receipt = {"book_id": manifest["book_id"], "scope_id": manifest["scope_id"], "asset_id": manifest["asset_id"],
               "package": {"reference": {"artifact_id": manifest["artifact_id"], "content_hash": digest(manifest)}, "file_sha256": file_digest(package_path)},
               "documents": copy.deepcopy(manifest["documents"]), "journal_dir": manifest["journal_dir"], "members": copy.deepcopy(manifest["members"]),
               "source": {"asset_id": manifest["asset_id"], "sha256": source["original_sha256"], "width": image.width,
                          "height": image.height, "rgb_sha256": hashlib.sha256(image.tobytes()).hexdigest()}}
    return {"manifest": manifest, "receipt": receipt, "documents": documents, "journal_dir": journal, "source_path": original_path}


def _producer(operation):
    names = ("baseline", "inline_ocr", "inline_ocr_quality", "inline_math", "inline_formula", "inline_candidates",
             "inline_formula_quality", "inline_continuity", "formula_canvas", "formula_canvas_quality", "formula_syntax", "formula_quality")
    return {"module": __name__, "version": "0.1.0", "operation": operation, "code_sha256": code_digest(Path(__file__)),
            "dependency_code_sha256": {name: code_digest(Path(__file__).with_name(name+".py")) for name in names},
            "identity_policy": IDENTITY_POLICY, "policy": POLICY, "new_model_calls": 0}


def _envelope(schema, kind, prefix, source, inputs, payload, operation):
    body = {"schema_version": schema, "kind": kind, "revision": 1, "book_id": source["book_id"], "scope_id": source["scope_id"],
            "input_refs": inputs, "producer": _producer(operation), "payload": payload}
    return {**body, "artifact_id": prefix+"-"+digest(body)[:24], "content_hash": digest(payload)}


def _bindings(evidence, graph, asset_id, line_ids):
    _checked(evidence, {"b-evidence-trial/0.2", "b-evidence-trial/0.3"})
    _checked(graph, {"b-graph-trial/0.2", "b-graph-trial/0.3", "b-graph-trial/0.4"})
    if ((evidence["book_id"], evidence["scope_id"]) != (graph["book_id"], graph["scope_id"])
            or reference(evidence) not in graph.get("input_refs", []) or "inline_content" in graph["payload"]):
        raise ValueError("inline graph must be the current evidence-bound base graph")
    pages = [p for p in evidence["payload"]["pages"] if p["asset_id"] == asset_id]
    if len(pages) != 1:
        raise ValueError("inline source asset must occur exactly once")
    raw = {line["line_id"]: line for line in pages[0]["ocr_lines"]}
    all_elements = {l["line_id"]: l for l in pages[0]["ocr_lines"]+pages[0].get("answer_detail_lines", [])}
    result = []
    for lid in line_ids:
        if lid not in raw:
            raise ValueError("inline source row absent from current page")
        owners = []
        for kind, collection, idfield in (("question", "questions", "question_id"), ("answer", "answers", "answer_id")):
            for entity in graph["payload"][collection]:
                for fragment in entity["fragments"]:
                    refs = fragment.get("evidence_refs", [])
                    parent = fragment.get("parent_line_id")
                    belongs = parent == lid or lid in refs or any(all_elements.get(r, {}).get("parent_line_id") == lid for r in refs)
                    if not belongs:
                        continue
                    if fragment.get("asset_id") != asset_id or len(refs) != 1 or refs[0] not in all_elements:
                        raise ValueError("inline fragment source belongs to another page or unknown OCR element")
                    source = all_elements[refs[0]]
                    canonical_parent = source["line_id"] if source["line_id"] in raw else source.get("parent_line_id")
                    if canonical_parent != lid or (parent is not None and parent != canonical_parent):
                        raise ValueError("inline declared fragment parent is not proved by its actual OCR source")
                    span = fragment.get("text_span", [0, len(source["text"])])
                    if (not isinstance(span, list) or len(span) != 2 or any(type(n) is not int for n in span)
                            or not 0 <= span[0] < span[1] <= len(source["text"])
                            or fragment.get("raw_text", source["text"]) != source["text"]
                            or fragment["text"] != source["text"][span[0]:span[1]]
                            or fragment["bbox"] != source["bbox"]):
                        raise ValueError("inline current fragment differs from its exact OCR source/span")
                    regions = entity.get("render_regions", entity.get("regions", []))
                    region_ids = [r.get("region_id", r.get("fragment_id")) for r in regions if fragment["fragment_id"] in r.get("source_fragment_ids", [r.get("fragment_id")])]
                    owners.append({"entity_kind": kind, "entity_id": entity[idfield], "answer_id": entity[idfield] if kind == "answer" else None,
                        "fragment_id": fragment["fragment_id"], "text_span": copy.deepcopy(span), "role": fragment["role"], "render_region_ids": region_ids})
        result.append({"line_id": lid, "source_line_sha256": digest(raw[lid]), "fragments": owners, "unassigned": not owners})
    return result


def prepare_inline_stage(evidence, graph, package_path, original_path):
    package = load_inline_package(package_path, original_path)
    manifest, docs = package["manifest"], package["documents"]
    old = docs["evidence"]
    asset_id, line_ids = manifest["asset_id"], manifest["line_ids"]
    _checked(evidence, DOCUMENTS["evidence"])
    current_page = [p for p in evidence["payload"]["pages"] if p["asset_id"] == asset_id]
    old_page = [p for p in old["payload"]["pages"] if p["asset_id"] == asset_id]
    if ((evidence["book_id"], evidence["scope_id"]) != (old["book_id"], old["scope_id"])
            or digest(evidence["payload"]["context"]) != digest(old["payload"]["context"])
            or len(current_page) != 1 or digest(current_page) != digest(old_page)):
        raise ValueError("inline reuse requires exact full context and selected page equivalence")
    bindings = _bindings(evidence, graph, asset_id, line_ids)
    ordinary, formulas, report = [docs[n] for n in ("ocr_observations", "formula_observations", "formula_report")]
    layout = formulas["payload"]["layout_archive"]
    candidates = build_inline_candidates(formulas)
    ordinary_check = audit_inline_ocr(old, ordinary, original_path, line_ids=line_ids)
    formula_check = audit_inline_formula(old, layout, formulas, candidates, original_path,
        line_ids=line_ids, workdir=package["journal_dir"], report=report)
    from .inline_continuity import build_inline_continuity
    continuity = build_inline_continuity(evidence, graph, layout, candidates, asset_id=asset_id, line_ids=line_ids)
    state = report["payload"]["state"]
    if state not in {"READY", "PARTIAL", "FAILED"}:
        raise ValueError("inline saved report has unknown execution state")
    if (not ordinary_check["payload"]["accepted"] or not formula_check["payload"]["accepted"]
            or any(v["recognition_error"] is not None for row in ordinary["payload"]["rows"] for v in row["variants"])):
        state = "FAILED"
    counts = {"rows": len(line_ids), "units": len(layout["payload"]["units"]), **{k: report["payload"]["counts"][k] for k in ("declared_calls", "done", "pending", "failed")}}
    payload = {"base_evidence_ref": reference(evidence), "base_graph_ref": reference(graph),
        "base_evidence_archive": copy.deepcopy(evidence), "base_graph_archive": copy.deepcopy(graph),
        "package_receipt": content_receipt(package["receipt"]), "original_evidence_archive": copy.deepcopy(old),
        "ocr_observations_archive": copy.deepcopy(ordinary), "layout_archive": copy.deepcopy(layout),
        "formula_observations_archive": copy.deepcopy(formulas), "formula_report_archive": copy.deepcopy(report),
        "candidates": candidates, "ocr_check": ordinary_check, "formula_check": formula_check, "continuity": continuity,
        "bindings": bindings, "execution_state": state, "counts": counts, **_flags()}
    if load_inline_package(package_path, original_path)["receipt"] != package["receipt"]:
        raise ValueError("inline package changed during preparation")
    return _envelope(PREPARE_SCHEMA, "InlinePreparationTrial", "inline-preparation", evidence,
                     [reference(evidence), reference(graph), package["receipt"]["package"]["reference"]], payload, "prepare")


def _validate_prepared(prepared):
    _checked(prepared, {PREPARE_SCHEMA})
    p = prepared["payload"]
    expected = _envelope(PREPARE_SCHEMA, "InlinePreparationTrial", "inline-preparation", p["base_evidence_archive"],
        [p["base_evidence_ref"], p["base_graph_ref"], p["package_receipt"]["package"]["reference"]], p, "prepare")
    if digest(prepared) != digest(expected) or digest({k: p.get(k) for k in _flags()}) != digest(_flags()):
        raise ValueError("inline preparation identity, producer or flags changed")
    if (p["base_evidence_ref"] != reference(p["base_evidence_archive"]) or p["base_graph_ref"] != reference(p["base_graph_archive"])
            or p["bindings"] != _bindings(p["base_evidence_archive"], p["base_graph_archive"], p["package_receipt"]["asset_id"], p["layout_archive"]["payload"]["requested_line_ids"])):
        raise ValueError("inline preparation current source bindings changed")
    formulas = p["formula_observations_archive"]
    _checked(formulas, {"b-inline-formula-observation-trial/0.1"})
    report = p["formula_report_archive"]
    _checked(report, {"b-inline-formula-run-trial/0.1"})
    if (p["execution_state"] != "READY" or report["payload"]["state"] != "READY"
            or formulas["payload"]["run_complete"] is not True
            or any(c["state"] != "DONE" for c in formulas["payload"]["calls"])
            or not all(p[k]["payload"]["accepted"] is True for k in ("ocr_check", "formula_check"))):
        raise ValueError("inline preparation must be READY with accepted source/execution audits")
    if digest(p["candidates"]) != digest(build_inline_candidates(formulas)):
        raise ValueError("inline prepared candidates changed from original raw observations")
    from .inline_continuity import build_inline_continuity
    expected_continuity = build_inline_continuity(p["base_evidence_archive"], p["base_graph_archive"], p["layout_archive"], p["candidates"],
        asset_id=p["package_receipt"]["asset_id"], line_ids=p["layout_archive"]["payload"]["requested_line_ids"])
    if digest(p["continuity"]) != digest(expected_continuity):
        raise ValueError("inline prepared continuation proposals changed from current source")
    return p


def apply_inline_stage(prepared):
    p = _validate_prepared(prepared)
    evidence, base = p["base_evidence_archive"], p["base_graph_archive"]
    payload = copy.deepcopy(base["payload"])
    payload["inline_content"] = {"prepared_ref": reference(prepared), "base_evidence_ref": p["base_evidence_ref"],
        "base_graph_ref": p["base_graph_ref"], "base_graph_archive": copy.deepcopy(base), "package_receipt": copy.deepcopy(p["package_receipt"]),
        "units": copy.deepcopy(p["layout_archive"]["payload"]["units"]), "calls": copy.deepcopy(p["formula_observations_archive"]["payload"]["calls"]),
        "not_inference_units": copy.deepcopy(p["formula_observations_archive"]["payload"]["not_inference_units"]),
        "candidates": copy.deepcopy(p["candidates"]["payload"]["candidates"]), "bindings": copy.deepcopy(p["bindings"]),
        "continuity": copy.deepcopy(p["continuity"]), "selected_unit_ids": [], "selected_candidate_refs": [], **_flags()}
    graph = _envelope("b-graph-trial/0.5", "QuestionGraphTrial", "inline-graph", evidence,
        [reference(evidence), reference(base), reference(prepared)], payload, "attach")
    return _envelope(APPLY_SCHEMA, "InlineApplyStageTrial", "inline-apply-stage", evidence, [reference(prepared)],
        {"prepared_ref": reference(prepared), "base_evidence_ref": reference(evidence), "base_graph_ref": reference(base),
         "package_receipt": copy.deepcopy(p["package_receipt"]), "graph": graph, **_flags()}, "apply")


def build_inline_quality(prepared, application, base_check):
    p = _validate_prepared(prepared)
    if digest(application) != digest(apply_inline_stage(prepared)):
        raise ValueError("inline graph application is not the exact attachment projection")
    _checked(base_check, {"b-check-trial/0.2", "b-check-trial/0.3", "b-check-trial/0.4"})
    e, base, graph = p["base_evidence_archive"], p["base_graph_archive"], application["payload"]["graph"]
    if ((base_check["book_id"], base_check["scope_id"]) != (e["book_id"], e["scope_id"])
            or reference(e) not in base_check["input_refs"] or reference(base) not in base_check["input_refs"]
            or base_check["payload"].get("decision") != "HOLD"
            or any(base_check["payload"].get(k, False) is not False for k in ("business_acceptance", "transcription_verified"))):
        raise ValueError("inline quality requires the current base-core check")
    if base_check["schema_version"] == "b-check-trial/0.4" and (base_check["payload"].get("evidence_ref") != reference(e) or base_check["payload"].get("graph_ref") != reference(base)):
        raise ValueError("inline base Check04 graph/evidence references changed")
    if base_check["schema_version"] in {"b-check-trial/0.2", "b-check-trial/0.3"} and base_check["input_refs"][:2] != [reference(e), reference(base)]:
        raise ValueError("inline base Check02/03 requires exact ordered evidence and graph references")
    risks = copy.deepcopy(p["ocr_check"]["payload"]["observation_risks"]+p["formula_check"]["payload"]["observation_risks"]+p["continuity"]["payload"]["diagnostics"])
    payload = copy.deepcopy(base_check["payload"])
    payload.update(stage="inline_quality", base_check_archive=copy.deepcopy(base_check), package_receipt=copy.deepcopy(p["package_receipt"]),
        evidence_ref=reference(e), graph_ref=reference(graph), inline_counts=copy.deepcopy(p["counts"]), inline_risks=risks,
        inline_basis={"base_evidence_ref": reference(e), "base_graph_ref": reference(base), "base_check_ref": reference(base_check),
            "prepared_ref": reference(prepared), "application_ref": reference(application), "core_payload_sha256": digest(base["payload"]), "core_unchanged": True}, **_flags())
    finding = {"code": "INLINE_CONTENT_TRANSCRIPTION_UNVERIFIED", "scope_type": "scope", "scope_id": e["scope_id"],
        "evidence_refs": p["layout_archive"]["payload"]["requested_line_ids"], "severity": "REVIEW", "blocks": ["PRE_APPLY"],
        "suggested_strategy": "REVIEW_OFFLINE", "detail": {"inline_counts": p["counts"], "risk_count": len(risks),
            "base_core_check_reused_only_for_exact_unchanged_payload": True, "text_selected": False}}
    finding["issue_id"] = "issue-"+digest(finding)[:24]
    payload["issues"].append(finding)
    unsupported = [c for c in p["candidates"]["payload"]["candidates"] if not c["parse_result"]["supported"]]
    groups = []
    if unsupported:
        groups.append(("INLINE_FORMULA_SYNTAX_UNSUPPORTED", {"call_ids": [c["call_id"] for c in unsupported],
            "candidate_ids": [c["candidate_id"] for c in unsupported]}))
    diagnostics = p["continuity"]["payload"]["diagnostics"]
    if diagnostics:
        groups.append(("INLINE_FORMULA_SOURCE_WRAP_CLOSURE_CONFLICT", {"diagnostics": copy.deepcopy(diagnostics),
                                                                    "source_bindings": copy.deepcopy(p["bindings"])}))
    for code, detail in groups:
        group = {key: copy.deepcopy(value) for key, value in finding.items() if key not in {"issue_id", "code", "detail"}}
        group.update(code=code, detail=detail)
        group["issue_id"] = "issue-"+digest(group)[:24]
        payload["issues"].append(group)
    payload["summary"]["issues"] = len(payload["issues"])
    return _envelope("b-check-trial/0.5", "CheckReportTrial", "inline-check", e,
        [reference(e), reference(graph), reference(base_check), reference(prepared), reference(application)], payload, "quality")
