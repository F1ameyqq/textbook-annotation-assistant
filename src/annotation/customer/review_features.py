"""Source-only review adapters: ordered previews and unapproved figure proposals.

No recognizer/worker is invoked. Unknown projections/scopes remain explicit.
Original source bytes are verified by the existing review boundary and again
by the figure module when a closed, program-derived scope can be proposed.
"""
from __future__ import annotations

import copy
from pathlib import Path

from .figure_proposals import required_figure_issues, propose_figures, BLOCKER
from .source_review_projection import project_candidate


def source_bindings(pages):
    return {p["asset_id"]: {"sha256": p["raw_sha256"], "dimensions": [p["width"], p["height"]]}
            for p in pages if p.get("kind") == "image"}


def projection(candidate, graph, evidence):
    try:
        return project_candidate(candidate, graph, evidence)
    except (ValueError, KeyError, TypeError) as exc:
        return {"schema": "CustomerSourceReviewProjection/v1", "candidate_key": candidate["key"],
                "status": "SOURCE_MAPPING_UNAVAILABLE", "issues": [{"code": "SOURCE_MAPPING_UNAVAILABLE", "detail": str(exc)}],
                "zones": [], "content_approved": False, "candidate_modified": False}


def reference_zones(candidate, graph=None, evidence=None):
    """Requirements retain original graph text even after a whole-zone edit."""
    texts = {zone: [text] for zone, text in candidate["zones"].items()}
    for zone, text in candidate.get("original_zones", {}).items():
        texts.setdefault(zone, []).append(text)
    if graph is not None and evidence is not None:
        view = projection(candidate, graph, evidence)
        if view["status"] != "SOURCE_MAPPING_UNAVAILABLE":
            question = next(q for q in graph["payload"]["questions"] if q["question_id"] == candidate["question_id"])
            for fragment in question["fragments"]:
                zone = "choice" if fragment["role"] == "option" else "question"
                texts.setdefault(zone, []).append(fragment["text"])
            answer = next((a for a in graph["payload"]["answers"] if a["answer_id"] == question.get("selected_answer_id")), None)
            for fragment in answer["fragments"] if answer else ():
                zone = "analysis" if fragment["role"] == "explanation" else "answer"
                texts.setdefault(zone, []).append(fragment["text"])
    raw = candidate.get("manual_answer_binding", {}).get("raw_texts", [])
    texts.setdefault("answer", []).extend(raw)
    return {zone: "\n".join(dict.fromkeys(text for text in values if isinstance(text, str))) for zone, values in texts.items()}


def figure_requirements(candidate, pages=(), graph=None, evidence=None):
    return required_figure_issues(reference_zones(candidate, graph, evidence), candidate["frames"],
                                  source_bindings=source_bindings(pages))


def _scopes(candidate, graph, evidence, layouts):
    """Only an observed anchor and next anchor/closed section make a search window."""
    view = projection(candidate, graph, evidence)
    if view["status"] == "SOURCE_MAPPING_UNAVAILABLE":
        return [], ["FIGURE_SOURCE_MAPPING_UNAVAILABLE"]
    question = next(q for q in graph["payload"]["questions"] if q["question_id"] == candidate["question_id"])
    pages = {p["asset_id"]: p for p in evidence["payload"]["pages"] if p["page_role"] == "question"}
    scopes, issues = [], []
    for aid, page in pages.items():
        lines = {line["line_id"]: line for line in page["ocr_lines"]}
        anchor = lines.get(question.get("anchor_ref"))
        own = [f for f in question["fragments"] if f["asset_id"] == aid and f["role"] in {"stem", "option"}]
        if not own:
            continue
        if not anchor or not anchor.get("location"):
            issues.append("FIGURE_CONTINUATION_SCOPE_UNPROVEN")
            continue
        loc = anchor["location"]
        layout = next((entry for entry in layouts if entry.get("page", {}).get("asset_id") == aid), None)
        context = evidence["payload"].get("context", {}).get("pages", {}).get(aid, {})
        windows = layout["windows"] if layout else context.get("windows", [])
        wi, column = loc["window_index"], loc["column"]
        if not 0 <= wi < len(windows) or windows[wi]["path"] != candidate["section_path"]:
            issues.append("FIGURE_SECTION_WINDOW_UNAVAILABLE")
            continue
        source, window = page["source"], windows[wi]
        width, height = source["width"], source["height"]
        columns = layout.get("columns") if layout else len({w["column"] for w in windows})
        cut = layout.get("cut_x") if layout else None
        if columns == 1 and column == 0:
            left, right = 0, width
        elif columns == 2 and isinstance(cut, (int, float)) and 0 < cut < width and column in (0, 1):
            left, right = (0, cut) if column == 0 else (cut, width)
        else:
            issues.append("FIGURE_COLUMN_BOUNDARY_UNAVAILABLE")
            continue
        after = []
        for other in graph["payload"]["questions"]:
            line = lines.get(other.get("anchor_ref"))
            if (other["question_id"] != question["question_id"] and other["section_path"] == question["section_path"]
                    and line and line.get("location") == loc and line["bbox"][1] > anchor["bbox"][1]):
                after.append(line)
        if after:
            end = min(after, key=lambda line: line["bbox"][1])
            end_y, end_refs = end["bbox"][1], [end["line_id"]]
        elif (layout and layout.get("continuation_at_end") is False and window["y_range"][1] < height * .94
              and any(row["reason"] == "SECTION_HEADING" for row in layout.get("exclusions", []))):
            end_y = window["y_range"][1]
            end_refs = [row["line_id"] for row in layout["exclusions"] if row["reason"] == "SECTION_HEADING"]
        else:
            issues.append("FIGURE_QUESTION_END_UNVERIFIED")
            continue
        scopes.append({"asset_id": aid, "question_key": candidate["key"], "printed_number": candidate["printed_number"],
                       "section_path": candidate["section_path"], "column": column,
                       "section_bbox": [0, window["y_range"][0], width, window["y_range"][1]],
                       "column_bbox": [left, 0, right, height],
                       "question_bbox": [left, anchor["bbox"][1], right, end_y],
                       "boundary_status": "OBSERVED_CLOSED", "boundary_refs": {"start": [anchor["line_id"]], "end": end_refs}})
    return scopes, sorted(set(issues))


def candidate_support(candidate, pages, graph, evidence, layouts=(), *, raw_loader=None, cache=None):
    """State data only. Whole-zone editor/quality states are never rewritten."""
    view = projection(candidate, graph, evidence)
    requirements = figure_requirements(candidate, pages, graph, evidence)
    discovery = {"status": "NO_MISSING_QUESTION_FIGURE_REQUIREMENT", "proposals": [], "issues": [], "approved": False}
    if any(row["zone"] in {"question", "choice"} for row in requirements):
        scopes, issues = _scopes(candidate, graph, evidence, layouts)
        discovery.update(status="NEEDS_REVIEW", issues=issues)
        by_id = {p["asset_id"]: p for p in pages}
        ep = {p["asset_id"]: p for p in evidence.get("payload", {}).get("pages", [])}
        for scope in scopes:
            page = by_id.get(scope["asset_id"])
            if not page or page.get("kind") != "image" or scope["asset_id"] not in ep:
                discovery["issues"].append("FIGURE_ORIGINAL_SOURCE_UNAVAILABLE")
                continue
            try:
                from .store import digest
                key = digest([page["raw_sha256"], graph.get("content_hash"), evidence.get("content_hash"), scope])
                value = (cache or {}).get(key)
                if value is None:
                    raw = raw_loader(page) if raw_loader else Path(page["raw_path"]).read_bytes()
                    value = propose_figures(raw, page["raw_sha256"], ocr_lines=ep[scope["asset_id"]]["ocr_lines"], scope=scope)
                    if cache is not None:
                        cache[key] = copy.deepcopy(value)
                discovery["issues"].extend(value["issues"])
                discovery["proposals"].extend({**copy.deepcopy(p), "zone": "question"} for p in value["proposals"])
            except (ValueError, OSError, KeyError, TypeError) as exc:
                discovery["issues"].append("FIGURE_DISCOVERY_UNAVAILABLE:" + str(exc))
        discovery["issues"] = sorted(set(discovery["issues"]))
    from .graphic_options import review_proposals
    graphic = review_proposals(candidate)
    if graphic:
        discovery['proposals'].extend(graphic)
        discovery['status'] = 'NEEDS_REVIEW'
    from .reading_contexts import candidates as reading_candidates
    return {"source_projection": view, "figure_requirements": requirements, "figure_discovery": discovery,
            'reading_answer_candidates': reading_candidates(candidate, graph, evidence)}
