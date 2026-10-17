"""Project observed G07/Check07 candidates into the provisional chapter gate shape.

This is a read-only adapter. It reports observed candidate rows only and keeps
chapter/page/question-material denominators and content approval unknown.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


GRAPH_SCHEMA = "b-graph-trial/0.7"
CHECK_SCHEMA = "b-check-trial/0.7"


def _read_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _ref(value: dict[str, Any]) -> dict[str, Any]:
    return {key: value.get(key) for key in ("artifact_id", "revision", "content_hash")}


def adapt(graph_path: Path, check_path: Path) -> dict[str, Any]:
    graph = _read_object(graph_path, "G07 graph")
    check = _read_object(check_path, "Check07")
    if graph.get("schema_version") != GRAPH_SCHEMA:
        raise ValueError(f"G07 graph schema must be {GRAPH_SCHEMA}")
    if check.get("schema_version") != CHECK_SCHEMA:
        raise ValueError(f"Check07 schema must be {CHECK_SCHEMA}")
    if any(graph.get(k) != check.get(k) for k in ("book_id", "scope_id")):
        raise ValueError("G07 and Check07 book/scope identity differs")
    gp, cp = graph.get("payload"), check.get("payload")
    if not isinstance(gp, dict) or not isinstance(cp, dict):
        raise ValueError("G07 and Check07 payload objects are required")
    if cp.get("graph_ref") != _ref(graph):
        raise ValueError("Check07 graph_ref does not bind the supplied G07 object")
    if gp.get("decision") != "HOLD" or cp.get("decision") != "HOLD":
        raise ValueError("adapter accepts only the observed HOLD G07/Check07 pair")
    if gp.get("business_acceptance") is not False or cp.get("business_acceptance") is not False:
        raise ValueError("G07/Check07 must explicitly retain business_acceptance=false")
    if gp.get("transcription_verified") is not False or cp.get("transcription_verified") is not False:
        raise ValueError("G07/Check07 must explicitly retain transcription_verified=false")
    graph_questions, graph_answers = gp.get("questions"), gp.get("answers")
    if not isinstance(graph_questions, list) or not isinstance(graph_answers, list):
        raise ValueError("G07 questions and answers must be arrays")

    qrows: dict[str, dict[str, Any]] = {}
    answer_to_questions: dict[str, list[str]] = {}
    for row in graph_questions:
        if not isinstance(row, dict) or not isinstance(row.get("question_id"), str):
            raise ValueError("G07 contains a question without a stable internal question_id")
        qid = row["question_id"]
        if qid in qrows:
            raise ValueError("G07 contains duplicate question IDs")
        qrows[qid] = row
        for answer_id in row.get("candidate_answer_ids", []):
            if isinstance(answer_id, str):
                answer_to_questions.setdefault(answer_id, []).append(qid)

    questions = []
    for qid, row in qrows.items():
        aid = row.get("asset_id")
        questions.append({
            "question_id": qid,
            "page_ids": [],
            "material_ids": [],
            "content_status": "OPEN",
            "identity_basis": "G07_INTERNAL_CANDIDATE_ID",
            "observed_asset_id": aid,
            "source_page_status": "UNKNOWN",
            "material_identity_status": "UNKNOWN",
            "verification_status": row.get("verification_status", "UNKNOWN"),
        })

    answers = []
    for row in graph_answers:
        if not isinstance(row, dict) or not isinstance(row.get("answer_id"), str):
            raise ValueError("G07 contains an answer without a stable internal answer_id")
        answer_id = row["answer_id"]
        linked_questions = sorted(set(answer_to_questions.get(answer_id, [])))
        # Links stay candidate-only. The source page of each answer remains
        # unknown in this adapter, even when an internal asset pointer exists.
        answers.append({
            "answer_id": answer_id,
            "question_id": linked_questions[0] if len(linked_questions) == 1 else None,
            "page_ids": [],
            "content_status": "OPEN",
            "relationship_status": "CANDIDATE_OPEN" if len(linked_questions) == 1 else "UNKNOWN",
            "candidate_question_ids": linked_questions,
            "observed_asset_id": row.get("asset_id"),
            "source_page_status": "UNKNOWN",
            "verification_status": row.get("verification_status", "UNKNOWN"),
        })

    issue_count = len(cp.get("issues")) if isinstance(cp.get("issues"), list) else None
    return {
        "schema": "chapter-candidate-b/1",
        "book_id": graph.get("book_id"),
        "chapter_id": None,
        "candidate_state": "PARTIAL",
        "chapter_identity_status": "UNKNOWN_NO_INDEPENDENT_TOC_ID",
        "source_pages": [],
        "questions": questions,
        "answers": answers,
        "materials": [],
        "coverage_status": {
            "chapter_denominator": "UNKNOWN",
            "source_page_denominator": "UNKNOWN",
            "question_denominator": "UNKNOWN",
            "answer_denominator": "UNKNOWN",
            "material_inventory": "UNKNOWN",
        },
        "checks": {"status": "HOLD", "unresolved_count": issue_count if issue_count is not None else 1},
        "human_review": {
            "status": "INCOMPLETE",
            "reviewer_ids": [],
            "reviewed_question_ids": [],
            "reviewed_answer_ids": [],
        },
        "source_basis": {
            "graph_ref": _ref(graph),
            "check_ref": _ref(check),
            "graph_schema": graph["schema_version"],
            "check_schema": check["schema_version"],
            "scope_id": graph.get("scope_id"),
        },
        "limits": [
            "G07/Check07 are B-internal trial artifacts for observed local candidates, not an independent chapter manifest.",
            "chapter_id, source page identities and all chapter denominators remain UNKNOWN; internal asset IDs are observations, not page IDs.",
            "Question and answer source page_ids intentionally remain empty/UNKNOWN; candidate links do not establish page provenance.",
            "Question/answer content is OPEN because G07 verification is unverified; Check07 HOLD and unresolved findings are preserved.",
            "An empty material candidate list means no stable material IDs were projected; it does not claim the chapter has no shared materials.",
            "No human review or business acceptance is created by this adapter.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, required=True, help="fixed G07 b-graph-trial/0.7 JSON")
    parser.add_argument("--check", type=Path, required=True, help="fixed Check07 b-check-trial/0.7 JSON")
    parser.add_argument("--out", type=Path, required=True, help="candidate JSON output path")
    args = parser.parse_args(argv)
    try:
        candidate = adapt(args.graph, args.check)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "candidate_state": candidate["candidate_state"],
        "questions": len(candidate["questions"]), "answers": len(candidate["answers"]),
        "source_pages": len(candidate["source_pages"]), "decision": "HOLD"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
