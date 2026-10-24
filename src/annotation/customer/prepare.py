"""Selected source pages -> B assembly -> review queue -> production candidates."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import re
import time

from .source import import_pages, ocr_page, text_lines, validate_lines, verify_sources
from .store import Hold, digest


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def _union(boxes):
    return [int(min(b[0] for b in boxes)), int(min(b[1] for b in boxes)),
            int(max(b[2] for b in boxes) + .999), int(max(b[3] for b in boxes) + .999)]


def _located(page, lines, lesson):
    from annotation.recognition.offline import detect_columns
    columns, split = 1, None
    if page["kind"] == "image":
        import numpy as np
        from PIL import Image
        with Image.open(page["raw_path"]) as image:
            layout = detect_columns(np.asarray(image.convert("L")) < 160, lines)
        if layout["mode"] == "two_columns":
            columns, split = 2, layout["cut_x"]
    windows = [{"column": column, "y_range": [0, page["height"]], "path": [lesson]}
               for column in range(columns)]
    located = []
    for index, original in enumerate(lines):
        line = copy.deepcopy(original)
        column = 0 if split is None or (line["bbox"][0] + line["bbox"][2]) / 2 < split else 1
        # A crossing line in an inferred two-column layout is not assigned by
        # its center. It remains visible in the global exception queue.
        crossing = split is not None and line["bbox"][0] < split < line["bbox"][2]
        line.update(line_id=page["asset_id"] + "/line/" + str(index),
                    location=None if crossing else {"column": column, "window_index": column, "section_path": [lesson]})
        located.append(line)
    return located, windows


def _frame_fragments(fragments, pages, zone):
    grouped = {}
    for fragment in fragments:
        grouped.setdefault((fragment["asset_id"], fragment.get("column", 0)), []).append(fragment)
    result = []
    for (aid, column), selected in grouped.items():
        page = pages[aid]
        result.append({"zone": zone, "content_type": "text", "asset_id": aid,
                       "bbox": _union([f["bbox"] for f in selected]),
                       "source_sha256": page["raw_sha256"], "source_dimensions": [page["width"], page["height"]],
                       "coordinate_space": page.get("coordinate_space", "ORIGINAL_PIXELS"),
                       "source_fragment_ids": [f["fragment_id"] for f in selected], "column": column})
    return result


def candidates_from_graph(graph, pages):
    """No accepted flag is copied from a legacy graph or an author manifest."""
    from annotation.recognition.policy import option_set_valid, choice_answer_valid
    page_map = {p["asset_id"]: p for p in pages}
    answers = {a["answer_id"]: a for a in graph["payload"]["answers"]}
    candidates = []
    for question in graph["payload"]["questions"]:
        answer = answers.get(question["selected_answer_id"])
        stem = [f for f in question["fragments"] if f["role"] == "stem"]
        choices = [f for f in question["fragments"] if f["role"] == "option"]
        zones = {"question": "\n".join(f["text"] for f in stem)}
        if choices:
            zones["choice"] = "\n".join(f["text"] for f in choices)
        zones["answer"] = answer["text"] if answer else ""
        if answer and answer.get("explanation_text"):
            zones["analysis"] = answer["explanation_text"]
        frames = _frame_fragments(stem, page_map, "question") + _frame_fragments(choices, page_map, "choice")
        if answer:
            for zone, role in (("answer", "answer"), ("analysis", "explanation")):
                frames += _frame_fragments([f for f in answer["fragments"] if f["role"] == role], page_map, zone)
        issues = list(question["flags"])
        if not answer:
            issues.append("ANSWER_MISSING_OR_AMBIGUOUS")
        elif not answer["complete"]:
            flags = answer["assembly_flags"] or ["ANSWER_BOUNDARY_UNRESOLVED"]
            # B's scanned-page edge stays OPEN in the retained graph. For an
            # exact digital excerpt, the imported page's explicit end bounds
            # this local excerpt (not completeness of the original textbook).
            digital_excerpt_end = (page_map[answer["asset_id"]]["kind"] == "text"
                                   and answer.get("boundary", {}).get("kind") == "ANSWER_PAGE_EDGE")
            issues += [flag for flag in flags if not (digital_excerpt_end and flag == "ANSWER_BOUNDARY_UNRESOLVED")]
        labels = [f["option_label"] for f in choices if f.get("option_start")]
        if choices and (not option_set_valid(labels) or not choice_answer_valid(zones["answer"], labels)):
            issues.append("CHOICE_OR_ANSWER_STRUCTURE")
        if not zones["question"].strip():
            issues.append("QUESTION_EMPTY")
        source_pages = {f["asset_id"] for f in frames}
        image_based = any(page_map[aid]["kind"] == "image" for aid in source_pages)
        # Detection confidence cannot certify mathematical transcription or
        # missing figures. Images always enter a source-visible review queue.
        if image_based:
            issues.append("IMAGE_TRANSCRIPTION_AND_FIGURES_REVIEW")
        if re.search(r"如图|图示|下图|[\\$<>]", "\n".join(zones.values())):
            issues.append("FIGURE_OR_FORMULA_REVIEW")
        stable = digest({"book": graph["book_id"], "lesson": question["section_path"],
                         "number": question["printed_number"],
                         "anchor": question["anchor_ref"]})
        candidate = {"key": stable, "printed_number": question["printed_number"],
                     "question_id": question["question_id"], "section_path": question["section_path"],
                     "zones": zones, "frames": frames, "issues": sorted(set(issues)),
                     "source_kind": "IMAGE_OCR" if image_based else "EXACT_TEXT_IMPORT",
                     "content_status": "NEEDS_REVIEW" if issues else "READY_EXACT_TEXT",
                     "review": None, "platform_status": "NOT_RUN"}
        candidate["content_hash"] = candidate_hash(candidate)
        candidates.append(candidate)
    # Printed numbers are local to a selected lesson, never global order IDs.
    for item in candidates:
        if sum(q["printed_number"] == item["printed_number"] for q in candidates) != 1:
            item["issues"].append("DUPLICATE_PRINTED_NUMBER")
            item["content_status"] = "NEEDS_REVIEW"
    return candidates


def candidate_hash(candidate):
    return digest({key: candidate[key] for key in ("key", "printed_number", "section_path", "zones", "frames", "source_kind")})


def prepare(store, *, book, lesson, question_files, answer_files=(), question_pages="全部",
            answer_pages="全部", allow_local_ocr=False, question_first_page=None, answer_first_page=None):
    from annotation.recognition.offline import artifact, assemble
    started = time.perf_counter()
    if not isinstance(book, str) or not re.fullmatch(r"[1-9][0-9]{0,31}", book):
        raise Hold("请输入书籍编号。")
    if not isinstance(lesson, str) or not lesson.strip() or len(lesson) > 200:
        raise Hold("请输入本次课时名称。")
    lesson = lesson.strip()
    pages = import_pages(store, question_files, role="question", pages=question_pages)
    pages += import_pages(store, answer_files, role="answer", pages=answer_pages)
    for page in pages:
        first = question_first_page if page["role"] == "question" else answer_first_page
        if first is not None:
            if type(first) is not int or not 1 <= first <= 9999:
                raise Hold("书中页码需要为正整数。")
            page["viewer_page"] = first + page["selected_page"] - 1
    if not any(p["role"] == "question" for p in pages):
        raise Hold("请至少选择一页题目材料。")
    if len({p["asset_id"] for p in pages}) != len(pages):
        raise Hold("题目与答案使用了同一页；当前请分别导入题页和答案页。")
    identity = digest([book, lesson, [(p["asset_id"], p["role"], p.get("viewer_page")) for p in pages]])
    with store.book_lock(book):
        with store.connect() as db:
            existing = db.execute("SELECT head FROM jobs WHERE id=?", (identity,)).fetchone()
        if existing:
            job, _ = store.job(identity)
            verify_sources(job["pages"])
            return job  # exact input resumes the edited task, never re-recognizes
        job = {"schema": "CustomerPreparation/v1", "id": identity, "book_id": book, "lesson": lesson,
               "pages": pages, "candidates": [], "issues": [], "created_at": utcnow(), "revision": 1,
               "recognition": [], "status": "PREPARING", "platform_status": "NOT_RUN",
               "metrics": {"prepare_invocations": 1, "review_actions": 0, "new_model_pages": 0,
                           "cache_pages": 0, "elapsed_seconds": None},
               "customer_ready": False, "legacy_decision": "HOLD"}
        head = store.save_job(job)
        return _continue(store, job, head, started, allow_local_ocr=allow_local_ocr)


def resume(store, identity, *, allow_local_ocr=False):
    job, head = store.job(identity)
    with store.book_lock(job["book_id"]):
        job, head = store.job(identity)
        if job["status"] not in {"WAITING_SOURCE", "PREPARING"}:
            verify_sources(job["pages"])
            return job
        return _continue(store, job, head, time.perf_counter(), allow_local_ocr=allow_local_ocr)


def _continue(store, job, head, started, *, allow_local_ocr):
    from annotation.recognition.offline import artifact, assemble
    verify_sources(job["pages"])
    pages, context = [], {}
    try:
        for page in job["pages"]:
            if page["kind"] == "text":
                lines, mode = text_lines(page), "EXACT_TEXT_IMPORT"
            else:
                lines, mode = ocr_page(store, page, job["book_id"], allow_local_ocr=allow_local_ocr)
            validate_lines(lines, page["width"], page["height"])
            located, windows = _located(page, lines, job["lesson"])
            context[page["asset_id"]] = {"role": page["role"], "windows": windows, "sha256": page["raw_sha256"]}
            source = {"asset_id": page["asset_id"], "width": page["width"], "height": page["height"], "sha256": page["raw_sha256"]}
            pages.append({"asset_id": page["asset_id"], "source": source, "page_role": page["role"],
                          "ocr_lines": located, "answer_detail_lines": [],
                          "unscoped_line_ids": [line["line_id"] for line in located if not line["location"]]})
            job["recognition"].append({"asset_id": page["asset_id"], "mode": mode, "at": utcnow()})
            job["metrics"]["new_model_pages"] += int(mode == "LOCAL_OCR")
            job["metrics"]["cache_pages"] += int(mode == "CACHE")
        evidence = artifact("b-evidence-trial/0.2", "EvidenceBundleTrial",
            {"book_id": job["book_id"], "scope_id": job["id"]},
            {"pages": pages, "context": {"pages": context}, "quality_decision": "NOT_EVALUATED",
             "limitations": ["Customer selects semantic scope; automatic physical layout is unverified.",
                             "No dense answer-row rerun or remote model calls."]}, [],
            {"module": __name__, "version": "1", "input_kind": "ORDINARY_LOCAL_MATERIALS"})
        graph = assemble(evidence)
        job["evidence_ref"], job["graph_ref"] = store.put(evidence), store.put(graph)
        job["candidates"] = candidates_from_graph(graph, job["pages"])
        # Answer-specific diagnostics remain on their candidates. Retain all
        # original diagnostics unchanged in graph_ref; global orphans still
        # stop the whole selected range.
        job["issues"] = copy.deepcopy([i for i in graph["payload"]["issues"] if "answer_id" not in i])
        for page in pages:
            if page["unscoped_line_ids"]:
                job["issues"].append({"code": "UNSCOPED_SOURCE_LINES", "evidence_refs": page["unscoped_line_ids"]})
        if graph["payload"]["unmatched_answer_ids"]:
            job["issues"].append({"code": "UNMATCHED_ANSWERS", "evidence_refs": graph["payload"]["unmatched_answer_ids"]})
        if not job["candidates"]:
            job["issues"].append({"code": "NO_QUESTION_ANCHORS", "detail": "未识别到可靠题号；补充清晰来源或拆分混合页。"})
        job["status"] = preparation_status(job)
    except Hold as exc:
        job.update(status="WAITING_SOURCE", last_message=str(exc))
    except BaseException as exc:
        job.update(status="FAILED_NO_RETRY", last_message=str(exc), error_type=type(exc).__name__)
        job["metrics"]["elapsed_seconds"] = time.perf_counter() - started
        store.save_job(job, head, "PREPARATION_FAILED")
        raise
    job["metrics"]["elapsed_seconds"] = time.perf_counter() - started
    store.save_job(job, head, "PREPARATION_RESULT")
    return job


def preparation_status(job):
    if job["issues"] or any(q["content_status"] == "NEEDS_REVIEW" for q in job["candidates"]):
        return "NEEDS_REVIEW"
    return "PREPARED_OFFLINE" if job["candidates"] else "WAITING_SOURCE"
