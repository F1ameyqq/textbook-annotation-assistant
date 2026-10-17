"""Machine-check declared chapter evidence for B-side G2.

This tool checks consistency in two supplied JSON documents. It cannot establish
that their author is an independent reviewer or that any reviewer read the source
pages. Therefore ``decision`` is the G2 acceptance status and this tool never
sets it to PASS; ``machine_evidence_decision`` reports only structural checks.
Internal trial graphs and Check07 are not accepted inputs until an adapter exists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA = "chapter-delivery-b/1"
CANDIDATE_SCHEMA = "chapter-candidate-b/1"


def evidence_binding(manifest: dict[str, Any], candidate: dict[str, Any]) -> dict[str, str]:
    """Bind declared checks to current inventory/content; this is not a signature."""
    def digest(value):
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return {"manifest_sha256": digest(manifest),
            "candidate_content_sha256": digest({k: v for k, v in candidate.items() if k not in {"checks", "human_review"}})}


def input_contract() -> dict[str, Any]:
    """Return the input contract. JSON fields are claims, not verified signatures."""
    return {
        "manifest": {
            "schema": SCHEMA,
            "required": ["book_id", "chapter_id", "toc_entry_id", "complete", "pages", "questions", "answers", "materials"],
            "pages": "[{page_id, role:question|answer|contents|material, asset_id, sha256, complete_page:true}]",
            "questions": "[{question_id, page_ids:[string,...], material_ids:[string,...]}]",
            "answers": "[{answer_id, question_id, page_ids:[string,...]}]",
            "materials": "[{material_id, page_ids:[string,...], identity_status:CONFIRMED}]",
            "denominator": "complete must be true and each inventory must be explicit; empty arrays count as denominators only when a reviewer has established the scope independently.",
        },
        "candidate": {
            "schema": CANDIDATE_SCHEMA,
            "required": ["book_id", "chapter_id", "source_pages", "questions", "answers", "materials", "checks", "human_review"],
            "source_pages": "[{page_id, asset_id, sha256, observed_scope:FULL_PAGE}]",
            "questions": "[{question_id, page_ids:[string,...], material_ids:[string,...], content_status:READY|OPEN}]",
            "answers": "[{answer_id, question_id, page_ids:[string,...], content_status:READY|OPEN}]",
            "materials": "[{material_id, page_ids:[string,...], identity_status:CONFIRMED|UNKNOWN}]",
            "checks": "{status:PASS|HOLD, unresolved_count:nonnegative integer, binding:{manifest_sha256,candidate_content_sha256}}. Digests use canonical UTF-8 JSON (sorted keys, compact separators, ensure_ascii=false); candidate content excludes checks/human_review. Binding proves consistency only, never independent review.",
            "human_review": "Self-reported review fields only; they are never proof of independent review or G2 acceptance.",
        },
        "output": "machine_evidence_decision may be PASS/PARTIAL/HOLD. Overall decision is G2 acceptance and stays HOLD until a separate authorized acceptance record verifies source-bound independent human review.",
    }


class _DuplicateKey(ValueError):
    pass


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read(path: Path) -> tuple[Any, str | None]:
    try:
        def invalid_constant(value):
            raise ValueError("nonfinite JSON: " + value)
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys, parse_constant=invalid_constant)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        return None, f"unreadable or malformed JSON ({type(exc).__name__})"
    return value, None


def _valid_id_list(items: Any, key: str, label: str, gaps: list[str]) -> list[str] | None:
    if not isinstance(items, list):
        gaps.append(f"{label}: inventory must be a JSON array")
        return None
    ids: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get(key), str) or not item[key].strip():
            gaps.append(f"{label}[{index}]: expected object with non-empty string {key}")
            return None
        ids.append(item[key])
    if len(ids) != len(set(ids)):
        gaps.append(f"{label}: duplicate IDs")
        return None
    return ids


def _index(items: Any, key: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        return {}
    return {row[key]: row for row in items if isinstance(row, dict) and isinstance(row.get(key), str)}


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _valid_refs(row: dict[str, Any], field: str, label: str, gaps: list[str]) -> set[str] | None:
    value = row.get(field)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        gaps.append(f"{label}: {field} must be an array of non-empty strings")
        return None
    if len(value) != len(set(value)):
        gaps.append(f"{label}: {field} contains duplicate references")
        return None
    return set(value)


def _empty_report(gaps: list[str], manifest: Any = None) -> dict[str, Any]:
    return {
        "schema": "chapter-delivery-b-report/1",
        "book_id": manifest.get("book_id") if isinstance(manifest, dict) else None,
        "chapter_id": manifest.get("chapter_id") if isinstance(manifest, dict) else None,
        "machine_evidence_decision": "HOLD",
        "decision": "HOLD",
        "g2_acceptance": "HOLD",
        "g2_acceptance_basis": "This machine checker cannot verify reviewer identity, independence, or source-by-source human inspection.",
        "gaps": gaps,
        "comparisons": {},
        "declared_human_review_claim": "NOT_ASSESSED",
    }


def check_delivery(manifest_path: Path, candidate_path: Path) -> dict[str, Any]:
    manifest, manifest_error = _read(manifest_path)
    candidate, candidate_error = _read(candidate_path)
    gaps: list[str] = []
    if manifest_error:
        gaps.append(f"manifest: {manifest_error}")
    elif not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        gaps.append(f"manifest: top-level object schema must be {SCHEMA}")
    if candidate_error:
        gaps.append(f"candidate: {candidate_error}")
    elif not isinstance(candidate, dict) or candidate.get("schema") != CANDIDATE_SCHEMA:
        gaps.append(f"candidate: top-level object schema must be {CANDIDATE_SCHEMA}")
    if gaps:
        return _empty_report(gaps, manifest)
    assert isinstance(manifest, dict) and isinstance(candidate, dict)

    fatal = False
    partial = False
    for field in ("book_id", "chapter_id", "toc_entry_id"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            gaps.append(f"manifest: {field} must be a non-empty stable identifier")
            fatal = True
    for field in ("book_id", "chapter_id"):
        if candidate.get(field) != manifest.get(field):
            gaps.append(f"identity: candidate {field} does not match manifest")
            fatal = True
    if type(manifest.get("complete")) is not bool or manifest.get("complete") is not True:
        gaps.append("denominator: manifest complete must be boolean true")
        fatal = True

    declared = {
        "pages": _valid_id_list(manifest.get("pages"), "page_id", "pages", gaps),
        "questions": _valid_id_list(manifest.get("questions"), "question_id", "questions", gaps),
        "answers": _valid_id_list(manifest.get("answers"), "answer_id", "answers", gaps),
        "materials": _valid_id_list(manifest.get("materials"), "material_id", "materials", gaps),
    }
    if any(ids is None for ids in declared.values()):
        fatal = True
    declared_rows = {
        "pages": _index(manifest.get("pages"), "page_id"),
        "questions": _index(manifest.get("questions"), "question_id"),
        "answers": _index(manifest.get("answers"), "answer_id"),
        "materials": _index(manifest.get("materials"), "material_id"),
    }

    seen_assets, seen_hashes = set(), set()
    for pid, row in declared_rows["pages"].items():
        role = row.get("role")
        if not isinstance(role, str) or role not in {"question", "answer", "contents", "material"} or row.get("complete_page") is not True:
            gaps.append(f"pages: {pid} has unknown role or is not declared a complete page")
            fatal = True
        if not isinstance(row.get("asset_id"), str) or not row["asset_id"] or not _is_sha256(row.get("sha256")):
            gaps.append(f"pages: {pid} lacks asset identity or recorded SHA-256")
            fatal = True
        else:
            if row["asset_id"] in seen_assets or row["sha256"].lower() in seen_hashes:
                gaps.append(f"pages: {pid} aliases an already declared source asset or byte content")
                fatal = True
            seen_assets.add(row["asset_id"])
            seen_hashes.add(row["sha256"].lower())
    for label, key, fields in (("questions", "question_id", ("page_ids", "material_ids")), ("answers", "answer_id", ("page_ids",)), ("materials", "material_id", ("page_ids",))):
        for item_id, row in declared_rows[label].items():
            for field in fields:
                refs = _valid_refs(row, field, f"{label}.{item_id}", gaps)
                if refs is None or (field == "page_ids" and not refs):
                    if refs is not None:
                        gaps.append(f"{label}.{item_id}: page_ids must not be empty")
                    fatal = True
            if label == "answers" and (not isinstance(row.get("question_id"), str) or not row["question_id"]):
                gaps.append(f"answers.{item_id}: question_id must be a non-empty string")
                fatal = True
            if label == "materials" and row.get("identity_status") != "CONFIRMED":
                gaps.append(f"materials.{item_id}: identity_status must be CONFIRMED in the frozen manifest")
                fatal = True
    question_ids = set(declared["questions"] or [])
    material_ids = set(declared["materials"] or [])
    page_ids = set(declared["pages"] or [])
    for item_id, row in declared_rows["questions"].items():
        q_pages = _valid_refs(row, "page_ids", f"manifest.questions.{item_id}", gaps)
        q_materials = _valid_refs(row, "material_ids", f"manifest.questions.{item_id}", gaps)
        if q_pages is not None and not q_pages.issubset(page_ids):
            gaps.append(f"questions.{item_id}: references page IDs outside the declared page inventory")
            fatal = True
        if q_materials is not None and not q_materials.issubset(material_ids):
            gaps.append(f"questions.{item_id}: references material IDs outside the declared material inventory")
            fatal = True
    for item_id, row in declared_rows["answers"].items():
        if isinstance(row.get("question_id"), str) and row["question_id"] not in question_ids:
            gaps.append(f"answers.{item_id}: references question ID outside the declared question inventory")
            fatal = True
        a_pages = _valid_refs(row, "page_ids", f"manifest.answers.{item_id}", gaps)
        if a_pages is not None and not a_pages.issubset(page_ids):
            gaps.append(f"answers.{item_id}: references page IDs outside the declared page inventory")
            fatal = True
    for item_id, row in declared_rows["materials"].items():
        m_pages = _valid_refs(row, "page_ids", f"manifest.materials.{item_id}", gaps)
        if m_pages is not None and not m_pages.issubset(page_ids):
            gaps.append(f"materials.{item_id}: references page IDs outside the declared page inventory")
            fatal = True

    for label, role in (("questions", "question"), ("answers", "answer")):
        for item_id, row in declared_rows[label].items():
            refs = _valid_refs(row, "page_ids", f"{label}.{item_id}", gaps)
            if refs is not None and any(declared_rows["pages"].get(pid, {}).get("role") != role for pid in refs):
                gaps.append(f"{label}.{item_id}: source page role conflicts with {role} content")
                fatal = True

    candidate_specs = (("pages", "source_pages", "page_id"), ("questions", "questions", "question_id"), ("answers", "answers", "answer_id"), ("materials", "materials", "material_id"))
    comparisons: dict[str, Any] = {}
    candidate_rows: dict[str, dict[str, dict[str, Any]]] = {}
    for label, field, key in candidate_specs:
        rows = candidate.get(field)
        observed_ids = _valid_id_list(rows, key, f"candidate.{field}", gaps)
        if observed_ids is None:
            fatal = True
            observed_ids = []
        indexed = _index(rows, key)
        candidate_rows[label] = indexed
        expected_ids = declared[label] or []
        missing = sorted(set(expected_ids) - set(indexed))
        extra = sorted(set(indexed) - set(expected_ids))
        conflicts: list[str] = []
        if missing or extra:
            gaps.append(f"{label}: candidate inventory does not reconcile to declared denominator")
            partial = True
        comparisons[label] = {"expected": len(expected_ids), "observed": len(indexed), "missing": missing, "extra": extra, "conflicts": conflicts}

    for pid in sorted(set(declared["pages"] or []) & set(candidate_rows["pages"])):
        expected, observed = declared_rows["pages"][pid], candidate_rows["pages"][pid]
        if any(observed.get(k) != expected.get(k) for k in ("asset_id", "sha256")) or observed.get("observed_scope") != "FULL_PAGE":
            comparisons["pages"]["conflicts"].append(pid)
    if comparisons["pages"]["conflicts"]:
        gaps.append("pages: candidate source identity or full-page scope conflicts with manifest")
        fatal = True

    for item_id in sorted(set(declared["questions"] or []) & set(candidate_rows["questions"])):
        exp, got = declared_rows["questions"][item_id], candidate_rows["questions"][item_id]
        refs_ok = True
        for field in ("page_ids", "material_ids"):
            left = _valid_refs(exp, field, f"manifest.questions.{item_id}", gaps)
            right = _valid_refs(got, field, f"candidate.questions.{item_id}", gaps)
            refs_ok = refs_ok and left is not None and right is not None and left == right
        if not refs_ok or got.get("content_status") != "READY":
            comparisons["questions"]["conflicts"].append(item_id)
    for item_id in sorted(set(declared["answers"] or []) & set(candidate_rows["answers"])):
        exp, got = declared_rows["answers"][item_id], candidate_rows["answers"][item_id]
        left = _valid_refs(exp, "page_ids", f"manifest.answers.{item_id}", gaps)
        right = _valid_refs(got, "page_ids", f"candidate.answers.{item_id}", gaps)
        if left is None or right is None or left != right or got.get("question_id") != exp.get("question_id") or got.get("content_status") != "READY":
            comparisons["answers"]["conflicts"].append(item_id)
    for item_id in sorted(set(declared["materials"] or []) & set(candidate_rows["materials"])):
        exp, got = declared_rows["materials"][item_id], candidate_rows["materials"][item_id]
        left = _valid_refs(exp, "page_ids", f"manifest.materials.{item_id}", gaps)
        right = _valid_refs(got, "page_ids", f"candidate.materials.{item_id}", gaps)
        if left is None or right is None or left != right or got.get("identity_status") != "CONFIRMED":
            comparisons["materials"]["conflicts"].append(item_id)
    for label in ("questions", "answers", "materials"):
        if comparisons[label]["conflicts"]:
            gaps.append(f"{label}: content, relationship, or identity claim is incomplete or conflicts with manifest")
            partial = True

    checks = candidate.get("checks")
    check_status = checks.get("status") if isinstance(checks, dict) else None
    if not isinstance(checks, dict) or not isinstance(check_status, str) or check_status not in {"PASS", "HOLD"} or type(checks.get("unresolved_count")) is not int or checks["unresolved_count"] < 0:
        gaps.append("checks: malformed; status and nonnegative integer unresolved_count are required")
        fatal = True
    elif checks["status"] != "PASS" or checks["unresolved_count"] != 0:
        gaps.append("checks: declared checks are non-PASS or unresolved findings remain")
        partial = True
    if isinstance(checks, dict):
        if set(checks) - {"status", "unresolved_count", "binding"}:
            gaps.append("checks: unsupported fields cannot establish a current check binding")
            fatal = True
        if checks.get("binding") != evidence_binding(manifest, candidate):
            gaps.append("checks: missing or stale manifest/candidate content binding")
            partial = True

    review = candidate.get("human_review")
    review_claim = "INCOMPLETE_OR_MALFORMED"
    if isinstance(review, dict):
        review_claim = "COMPLETE_CLAIMED" if review.get("status") == "COMPLETE" else "INCOMPLETE_CLAIMED"
        # Validate shape only. These self-reported fields cannot authenticate a review.
        reviewers = review.get("reviewer_ids")
        rq, ra = review.get("reviewed_question_ids"), review.get("reviewed_answer_ids")
        if (not isinstance(reviewers, list) or not reviewers
                or any(not isinstance(x, str) or not x.strip() for x in reviewers)
                or len(reviewers) != len(set(reviewers))):
            gaps.append("human review claim: reviewer_ids must be an array of strings")
            review_claim = "INCOMPLETE_OR_MALFORMED"
        if not isinstance(rq, list) or any(not isinstance(x, str) for x in rq) or set(rq) != set(declared["questions"] or []):
            gaps.append("human review claim: reviewed question IDs do not match declared denominator")
            review_claim = "INCOMPLETE_OR_MALFORMED"
        if not isinstance(ra, list) or any(not isinstance(x, str) for x in ra) or set(ra) != set(declared["answers"] or []):
            gaps.append("human review claim: reviewed answer IDs do not match declared denominator")
            review_claim = "INCOMPLETE_OR_MALFORMED"
    else:
        gaps.append("human review claim: absent or malformed")
    if review_claim != "COMPLETE_CLAIMED":
        gaps.append("human review claim: incomplete; no independent acceptance established")
        partial = True

    machine = "HOLD" if fatal else "PARTIAL" if partial else "PASS"
    # This utility only checks claims in unsigned JSON. G2 requires separately
    # authenticated, source-by-source independent review and acceptance evidence.
    return {
        "schema": "chapter-delivery-b-report/1",
        "book_id": manifest.get("book_id"),
        "chapter_id": manifest.get("chapter_id"),
        "machine_evidence_decision": machine,
        "decision": "HOLD",
        "g2_acceptance": "HOLD",
        "g2_acceptance_basis": "No separately authenticated independent human acceptance record is consumed by this tool.",
        "declared_human_review_claim": review_claim,
        "gaps": gaps,
        "comparisons": comparisons,
        "limits": [
            "Machine comparison covers only fields in the supplied manifest and candidate JSON; it cannot show that a manifest is a complete real chapter inventory.",
            "Unsigned human_review fields are claims and do not establish reviewer identity, independence, source-by-source inspection, or business acceptance.",
            "The tool does not read source pixels or establish transcription correctness and does not adapt current internal trial graph/Check07 objects.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--contract", action="store_true", help="print the input contract")
    args = parser.parse_args()
    if not args.contract and (args.manifest is None or args.candidate is None):
        parser.error("--manifest and --candidate are required unless --contract is set")
    result = input_contract() if args.contract else check_delivery(args.manifest, args.candidate)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
