"""Materialize a versioned assembly view from immutable, source-bound recovery.

Original OCR remains archived. A replacement is not a correction of ground
truth: CPU hypotheses and model visual references remain UNVERIFIED.
"""
import copy
import hashlib
import re
from pathlib import Path

from .baseline import digest, code_digest, valid_bbox


def reference(value):
    return {k: value[k] for k in ("artifact_id", "revision", "content_hash")}


def checked(value, schemas):
    if value.get("schema_version") not in schemas or value.get("content_hash") != digest(value.get("payload")):
        raise ValueError("unsupported or changed recovery artifact")


def validate_hypotheses(probe, variant):
    """Recompute the derived CPU fields from the retained raw engine result."""
    rows, lines = variant.get("raw_ocr_result") or [], variant["ocr_lines"]
    if len(rows) != len(lines):
        raise ValueError("raw OCR and derived lines disagree")
    scale, box = variant["scale"], probe["crop_bbox"]
    if variant["crop_to_original"] != [[1/scale,0,box[0]],[0,1/scale,box[1]],[0,0,1]]:
        raise ValueError("recovery coordinate transform changed")
    for ordinal, (row, line) in enumerate(zip(rows, lines)):
        if variant["use_det"]:
            polygon, text, score = row[:3]
            mapped = [[round(x/scale+box[0],4),round(y/scale+box[1],4)] for x,y in polygon]
            bbox = [min(x for x,y in mapped),min(y for x,y in mapped),max(x for x,y in mapped),max(y for x,y in mapped)]
        else:
            text, score = row[:2]
            mapped, bbox = None, list(box)
        if (line["line_id"] != f"recovery/{probe['probe_id']}/{variant['variant_id']}/{ordinal}"
                or line["text"] != text or line["score"] != float(score)
                or line["bbox"] != bbox or line.get("polygon") != mapped):
            raise ValueError("derived recovery line differs from raw CPU output")


def derive_evidence(base, recovery, source_review, make_artifact):
    checked(base, {"b-evidence-trial/0.2"})
    checked(recovery, {"b-recovery-trial/0.1"})
    checked(source_review, {"b-source-review-trial/0.1"})
    if recovery["payload"]["base_evidence_ref"] != reference(base) or source_review["payload"]["base_evidence_ref"] != reference(base):
        raise ValueError("recovery/review is stale for this base evidence")
    if source_review["payload"].get("recovery_ref") != reference(recovery):
        raise ValueError("source review is stale for this recovery evidence")
    for other in (recovery, source_review):
        if (other["book_id"], other["scope_id"]) != (base["book_id"], base["scope_id"]):
            raise ValueError("recovery book/scope mismatch")
    pages = {p["asset_id"]: p for p in base["payload"]["pages"]}
    raw = {line["line_id"]: (p, line) for p in pages.values() for line in p["ocr_lines"]}
    pool, probe_by_line = {}, {}
    for probe in recovery["payload"]["probes"]:
        if probe["asset_id"] not in pages or probe["source_sha256"] != pages[probe["asset_id"]]["source"]["sha256"]:
            raise ValueError("recovery probe source hash mismatch")
        for variant in probe["variants"]:
            validate_hypotheses(probe, variant)
            for line in variant["ocr_lines"]:
                if line["line_id"] in pool:
                    raise ValueError("recovery line ID reused")
                pool[line["line_id"]], probe_by_line[line["line_id"]] = line, (probe, variant)
    payload = copy.deepcopy(base["payload"])
    payload["base_evidence_archive"] = copy.deepcopy(base)
    payload["recovery_evidence_archive"] = copy.deepcopy(recovery)
    payload["recovery_ref"] = reference(recovery)
    payload["recovery_review_ref"] = reference(source_review)
    payload["recovery_source_review"] = copy.deepcopy(source_review["payload"])
    payload["source_review"] = copy.deepcopy(source_review["payload"])
    replaced, replacements, decisions = set(), [], []
    for plan in recovery["payload"]["supersession_plan"]:
        if plan["asset_id"] not in pages:
            raise ValueError("unknown recovery plan asset")
        asset = pages[plan["asset_id"]]["source"]
        if plan["action"] != "REPLACE_FOR_ASSEMBLY" or plan["source_sha256"] != asset["sha256"]:
            raise ValueError("unapproved recovery action or asset")
        if not plan["base_line_ids"] or not plan["replacement_line_ids"]:
            raise ValueError("replacement needs old and new evidence")
        if len(plan["base_line_ids"]) != len(set(plan["base_line_ids"])):
            raise ValueError("duplicate base line within supersession plan")
        if replaced.intersection(plan["base_line_ids"]):
            raise ValueError("overlapping supersession plans")
        for old in plan["base_line_ids"]:
            if old not in raw or raw[old][0]["asset_id"] != plan["asset_id"]:
                raise ValueError("unknown or cross-asset supersession")
        selected = []
        for new in plan["replacement_line_ids"]:
            if new not in pool:
                raise ValueError("unknown replacement OCR line")
            probe, variant = probe_by_line[new]
            if (probe["probe_id"] not in plan["selected_probe_ids"]
                    or probe["selected_variant_id"] != variant["variant_id"]):
                raise ValueError("replacement uses an unselected OCR hypothesis")
            line = copy.deepcopy(pool[new])
            if (probe["asset_id"] != plan["asset_id"] or line["asset_id"] != plan["asset_id"]
                    or line.get("location") != plan.get("location")
                    or not valid_bbox(line["bbox"], asset["width"], asset["height"])):
                raise ValueError("replacement geometry invalid")
            line.update(recovery_plan_id=plan["plan_id"], source_type="LOCAL_CPU_OCR_RECOVERY",
                        verification_status="UNVERIFIED", independent_confirmation=False)
            if probe["status"] == "ANCHOR_RECOVERED_FORMULAS_UNRESOLVED":
                line["reading_order_status"] = "UNRESOLVED_2D_FORMULA"
            selected.append(line)
        # Crop partitions provide explicit 2D reading groups: a numerator may
        # be above its primary anchor. Do not silently y-sort it into a prior
        # question. This ordering is confined to the source-bound plan block.
        top = min(l["bbox"][1] for l in selected)
        height = max(l["bbox"][3] for l in selected)-top
        for line in selected:
            if height <= 50:
                order = [top, line["bbox"][0], line["bbox"][1]]
            else:
                anchor = bool(re.match(r"^\d{1,2}[.．、]\s*解", line["text"]))
                order = [top, 0 if anchor else 1, line["bbox"][1], line["bbox"][0]]
            line["assembly_order"] = order
        replaced.update(plan["base_line_ids"])
        replacements.extend(selected)
        decisions.append(copy.deepcopy(plan))
    additions = []
    for selection in source_review["payload"].get("reviewed_probe_selections", []):
        new = selection["line_id"]
        if new not in pool:
            raise ValueError("review selected an unknown hypothesis")
        probe, variant = probe_by_line[new]
        if probe["source_sha256"] != selection["source_sha256"] or not selection.get("reason"):
            raise ValueError("reviewed selection lacks source proof")
        line = copy.deepcopy(pool[new])
        asset = pages[probe["asset_id"]]["source"]
        if (line["asset_id"] != probe["asset_id"] or line.get("location") != probe.get("location")
                or not valid_bbox(line["bbox"], asset["width"], asset["height"])):
            raise ValueError("reviewed selection geometry or location invalid")
        line.update(source_type="LOCAL_CPU_OCR_REVIEWED_SELECTION", verification_status="UNVERIFIED",
                    independent_confirmation=False, reviewed_marker=selection.get("reviewed_marker"),
                    selection_rationale=selection["reason"])
        additions.append(line)
    ids = [l["line_id"] for l in replacements+additions]
    if len(ids) != len(set(ids)):
        raise ValueError("recovery line applied twice")
    anchors = {item["line_id"]: item for item in source_review["payload"].get("reviewed_primary_anchors", [])}
    for line in replacements+additions:
        if line["line_id"] not in anchors:
            continue
        item = anchors[line["line_id"]]
        match = re.match(r"^\s*(\d{1,2})[.．、]", line["text"])
        if (not match or match[1] != item["printed_number"]
                or item["source_sha256"] != pages[line["asset_id"]]["source"]["sha256"]
                or not item.get("reason")):
            raise ValueError("reviewed primary anchor is not source bound")
        line["reviewed_primary_number"] = item["printed_number"]
    if set(anchors)-set(ids):
        raise ValueError("reviewed anchor not applied")
    for page in payload["pages"]:
        page["ocr_lines"] = [l for l in page["ocr_lines"] if l["line_id"] not in replaced]
        page["ocr_lines"].extend(l for l in replacements+additions if l["asset_id"] == page["asset_id"])
        page["answer_detail_lines"] = [l for l in page["answer_detail_lines"] if l["parent_line_id"] not in replaced]
    exclusions = source_review["payload"]["reviewed_exclusions"]
    for item in exclusions:
        if item["line_id"] not in raw:
            raise ValueError("review exclusion lacks original evidence")
        page, line = raw[item["line_id"]]
        if (item["source_sha256"] != page["source"]["sha256"]
                or item["source_text_sha256"] != hashlib.sha256(line["text"].encode()).hexdigest()
                or item["kind"] not in {"title", "footer"}):
            raise ValueError("review exclusion is not source bound")
        if item["kind"] == "footer" and line["bbox"][1] < .94*page["source"]["height"]:
            raise ValueError("reviewed footer is not at page edge")
        text = re.sub(r"\s+", "", line["text"])
        if item["kind"] == "title" and not re.fullmatch(r"(?:小专题[12].+|漫话勾股世界.+|☆问题解决策略：反思)", text):
            raise ValueError("reviewed exclusion is not a recognized source title")
        if item["kind"] == "footer" and not re.fullmatch(r"(?:\d{1,3}|数学·八年级上·BS)", text):
            raise ValueError("reviewed exclusion is not a recognized footer")
    payload["reviewed_exclusions"] = copy.deepcopy(exclusions)
    payload["recovery_application"] = {"supersession_plan": decisions, "replaced_base_line_ids": sorted(replaced),
                                        "replacement_line_ids": ids, "base_unchanged": True,
                                        "formula_candidates": source_review["payload"].get("formula_candidates", [])}
    return make_artifact("b-evidence-trial/0.3", "EvidenceBundleTrial", base, payload,
                         [reference(base), reference(recovery), reference(source_review)],
                         {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__)),
                          "source_evidence_preserved": True})


def derive_review(review, derived):
    """Versioned migration of known source references, never graph-generated gold."""
    result = copy.deepcopy(review)
    applied = derived["payload"]["recovery_application"]
    replaced = set(applied["replaced_base_line_ids"])
    retained, retired = [], []
    for group in result.get("unresolved_source_groups", []):
        (retired if set(group["source_line_ids"]) <= replaced else retained).append(group)
    result["unresolved_source_groups"] = retained
    result["retired_unresolved_source_groups"] = retired
    result["recovery_migration_ref"] = reference(derived)
    active = {line["line_id"]: line for p in derived["payload"]["pages"] for line in p["ocr_lines"]}
    additions = {item["case_id"]: item for item in derived["payload"]["recovery_source_review"].get("regression_additions", [])}
    for case in result.get("multiline_checks", []):
        expectation = additions.get(case["case_id"])
        new = expectation["line_id"] if expectation else None
        if new and new in active:
            text = active[new]["text"]
            if hashlib.sha256(text.encode()).hexdigest() != expectation["source_text_sha256"]:
                raise ValueError("recovery regression source text changed")
            case["expected_source_line_ids"].append(new)
            case["expected_source_spans"].append({key: copy.deepcopy(expectation[key]) for key in
                                                   ("line_id", "text_spans", "source_text_sha256")})
            for gap in case.get("observed_source_gaps", []):
                gap["recovery_status"] = "PARTIALLY_RECOVERED_UNVERIFIED" if "q1-" in case["case_id"] else "RECOVERED_CANDIDATE_UNVERIFIED"
                gap["recovered_line_ids"] = [new]
    return result
