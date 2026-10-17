"""Read-only integrity replay of the 19 source-local material identity candidates.

This checks retained source pixels and raw CPU receipts, not mathematical truth.
Frozen local labels below are a MODEL development review, never human gold or
public question IDs. No recognition engine, graph writer or website is called.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from annotation.recognition.baseline import digest, load_source
from annotation.recognition.recovery_apply import validate_hypotheses


FIXTURE = ROOT / "tests/fixtures/book46007447"
REVIEW = ROOT / "evaluation/book-46007447-unassigned-identities.json"
ASSET = "viewer-173"
SOURCE_HASH = "a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be"
GROUP_ROWS = {
    "topic1-examples": (86, 87),
    "math-world": (102, 104, 108, 110, 112),
    "topic2-example": (111, 113, 114, 115, 116, 117),
    "topic2-training": (119, 120, 121, 122, 123, 125),
}
GROUP_BOUNDARIES = {
    "topic1-examples": (82, "title-topic1", 6, [577, 837, 1079, 889], (89, 92)),
    "math-world": (98, "title-math-world", 2, [54, 1012, 548, 1240], (124,)),
    "topic2-example": (109, "title-topic2", 7, [576, 1113, 1079, 1207], (118, 126)),
    "topic2-training": (109, "title-topic2", 7, [577, 1224, 805, 1261], (118, 126)),
}
TITLES = {
    "topic1-examples": "小专题1 方程思想在勾股定理中的运用",
    "math-world": "漫话勾股世界—教材P6“阅读·思考”变式",
    "topic2-example": "小专题2 勾股定理在折叠问题中的运用",
    "topic2-training": "小专题2 勾股定理在折叠问题中的运用",
}
PIXEL_PROBES = {
    "topic1-examples", "title-topic1", "math-world", "title-math-world",
    "topic2-example", "title-topic2", "topic2-training", "title-reflection",
}
# Explicit source-local labels from this independent pixel review. In particular
# a bare 【例】 and the reading material never acquire a fabricated number1.
MATERIALS = {
    "topic1-examples/example-1": ("NUMBERED_EXAMPLE_REFERENCE", "【例1】", 1,
        [580, 840, 631, 861], ("scale3/2", "scale4-contrast/2")),
    "topic1-examples/example-2": ("NUMBERED_EXAMPLE_REFERENCE", "【例2】", 2,
        [580, 868, 631, 889], ("scale3/7", "scale4-contrast/6")),
    "math-world/unnumbered-reading": ("UNNUMBERED_WORKED_READING_REFERENCE", None, None,
        [54, 1012, 150, 1042], ("scale3/0", "scale4-contrast/0")),
    "topic2-example/unnumbered-example": ("UNNUMBERED_EXAMPLE_REFERENCE", "【例】", None,
        [580, 1113, 621, 1134], ("scale3/0", "scale4-contrast/0")),
    "topic2-training/training-1": ("NUMBERED_TRAINING_REFERENCE", "1.", 1,
        [582, 1232, 613, 1253], ("scale3/2", "scale4-contrast/2")),
    "topic2-training/training-2": ("NUMBERED_TRAINING_REFERENCE", "2.", 2,
        [620, 1231, 638, 1254], ("scale3/4", "scale4-contrast/4")),
    "topic2-training/training-3": ("NUMBERED_TRAINING_REFERENCE", "3.", 3,
        [672, 1232, 701, 1253], ("scale3/5", "scale4-contrast/5")),
    "topic2-training/training-4": ("NUMBERED_TRAINING_REFERENCE", "4.", 4,
        [710, 1231, 728, 1253], ("scale3/7", "scale4-contrast/7")),
    "topic2-training/training-5": ("NUMBERED_TRAINING_REFERENCE", "5.", 5,
        [759, 1231, 780, 1254], ("scale3/8", "scale4-contrast/8")),
}
ROW_IDENTITIES = {
    86: ("topic1-examples/example-1",), 87: ("topic1-examples/example-2",),
    **{n: ("math-world/unnumbered-reading",) for n in (102, 104, 108, 110, 112)},
    **{n: ("topic2-example/unnumbered-example",) for n in (111, 113, 114, 115, 116, 117)},
    119: ("topic2-training/training-2",), 120: ("topic2-training/training-4",),
    121: ("topic2-training/training-5",),
    122: ("topic2-training/training-1", "topic2-training/training-2"),
    123: ("topic2-training/training-3", "topic2-training/training-4"),
    125: ("topic2-training/training-2",),
}
ROW_ROLES = {
    86: "FORMULA_DENOMINATOR", 87: "EXAMPLE_TABLE_ROW_WITH_GARBLED_RAW_OCR",
    102: "WORKED_ANSWER_SUBPART_TEXT", 104: "FORMULA_NUMERATOR",
    108: "MIXED_SUBPART_WORKED_ANSWER_TEXT", 110: "WORKED_ANSWER_CONTINUATION",
    112: "DIAGRAM_LABEL", 111: "UNNUMBERED_EXAMPLE_ANCHOR_AND_WORKED_TEXT",
    113: "WORKED_ANSWER_CONTINUATION", 114: "WORKED_ANSWER_CONTINUATION",
    115: "FORMULA_NUMERATOR", 116: "WORKED_ANSWER_CONTINUATION",
    117: "FORMULA_DENOMINATOR", 119: "FORMULA_NUMERATOR", 120: "FORMULA_NUMERATOR",
    121: "NUMBERED_TRAINING_ANSWER", 122: "MIXED_NUMBERED_TRAINING_ROW",
    123: "MIXED_NUMBERED_TRAINING_ROW", 125: "FORMULA_DENOMINATOR",
}
ROW_CPU = {
    86: ("topic1-examples/scale3/5", "topic1-examples/scale4-contrast/5"),
    87: ("topic1-examples/scale3/7", "topic1-examples/scale4-contrast/6"),
    112: ("math-world/scale4-contrast/8",),
    119: ("topic2-training/scale3/0", "topic2-training/scale4-contrast/0"),
    120: ("topic2-training/scale3/1", "topic2-training/scale4-contrast/1",
        "topic2-training/scale3/11", "topic2-training/scale4-contrast/11"),
    121: ("topic2-training/scale3/8", "topic2-training/scale3/9",
        "topic2-training/scale4-contrast/8", "topic2-training/scale4-contrast/9"),
    122: tuple(f"topic2-training/{v}/{i}" for v in ("scale3", "scale4-contrast") for i in (2, 3, 4)),
    123: tuple(f"topic2-training/{v}/{i}" for v in ("scale3", "scale4-contrast") for i in (5, 6, 7)),
    125: ("topic2-training/scale3/10", "topic2-training/scale4-contrast/10"),
}
INVENTORY = dict(original_unassigned_rows=19, source_groups=4,
    source_local_material_candidates=9, numbered_example_candidates=2,
    unnumbered_reading_candidates=1, unnumbered_example_candidates=1,
    numbered_training_candidates=5, mixed_primary_rows=2, mixed_subpart_rows=1,
    excluded_noncontent_rows=0, graph_rows_changed=0)


def reference(value):
    return {k: value[k] for k in ("artifact_id", "revision", "content_hash")}


def text_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def pixels(image):
    rgb = image.convert("RGB")
    mask = bytes(x < 160 for x in rgb.convert("L").tobytes())
    return hashlib.sha256(rgb.tobytes()).hexdigest(), hashlib.sha256(mask).hexdigest(), sum(mask)


def verify(review, fixture=FIXTURE, source_path=None):
    """Return a source-integrity report; the business decision always stays HOLD."""
    fixture = Path(fixture)
    issues, cpu_seen = [], set()
    original_pixels_checked = False

    def fail(code, detail=""):
        issues.append({"code": code, "detail": detail})

    def require(condition, code, detail=""):
        if not condition:
            fail(code, detail)

    def unique(items, key, code):
        values = [item[key] for item in items]
        require(len(values) == len(set(values)), code)
        return {item[key]: item for item in items}

    try:
        def read(name):
            return json.loads((fixture / name).read_text(encoding="utf-8"))

        base, recovery, old_review, context = (read(name) for name in
            ("ocr-evidence.json", "recovery-evidence.json", "source-recovery-review.json", "context.json"))
        for value in (base, recovery, old_review, review):
            require(value["content_hash"] == digest(value["payload"]), "INPUT_CONTENT_HASH_MISMATCH", value["artifact_id"])
        payload = review["payload"]
        require(review["schema_version"] == "b-unassigned-identity-review-trial/0.1"
            and review["kind"] == "SourceMaterialIdentityReviewTrial" and review["revision"] == 1,
            "IDENTITY_REVIEW_SCHEMA_MISMATCH")
        require(review["artifact_id"] == "source-material-identities-" + digest(payload)[:24], "IDENTITY_REVIEW_ID_MISMATCH")
        require(review["book_id"] == base["book_id"] == "46007447"
            and review["scope_id"] == base["scope_id"] == recovery["scope_id"] == old_review["scope_id"],
            "IDENTITY_SCOPE_MISMATCH")
        refs = [reference(base), reference(recovery), reference(old_review)]
        require(review["input_refs"] == refs, "IDENTITY_INPUT_REFS_MISMATCH")
        require(payload["input_refs"] == dict(base_evidence=refs[0], recovery_evidence=refs[1],
            source_recovery_review=refs[2], context=dict(artifact_id=context["artifact_id"],
                canonical_sha256=digest(context))),
            "IDENTITY_INPUT_REFS_MISMATCH")
        require(context == base["payload"]["context"], "IDENTITY_CONTEXT_MISMATCH")
        require(review["producer"]["reference_quality"] == payload["reference_quality"]
            == "MODEL_VISUAL_DEVELOPMENT_REVIEW", "IDENTITY_FALSE_VERIFICATION")
        require(payload["decision"] == "HOLD" and payload["semantic_verification"] == "UNVERIFIED"
            and payload["human_verified"] is False and payload["business_accepted"] is False
            and payload["graph_assignment_performed"] is False and payload["platform_actions"] == [],
            "IDENTITY_FALSE_VERIFICATION")
        require(payload["identity_inventory"] == INVENTORY, "IDENTITY_INVENTORY_MISMATCH")
        page = next(p for p in base["payload"]["pages"] if p["asset_id"] == ASSET)
        source = page["source"]
        require(source["sha256"] == SOURCE_HASH, "IDENTITY_SOURCE_MISMATCH")
        require(payload["source"] == dict(asset_id=ASSET, sha256=SOURCE_HASH,
            size=[source["width"], source["height"]], descriptor=source,
            printed_page_model_visual=25, printed_page_is_not_platform_mapping=True), "IDENTITY_SOURCE_MISMATCH")
        raw = {line["line_id"]: line for line in page["ocr_lines"]}

        def snapshot(line_id):
            line = raw[line_id]
            return dict(line_id=line_id, text=line["text"], text_sha256=text_hash(line["text"]),
                bbox=line["bbox"], location=line["location"], source_sha256=SOURCE_HASH)

        def same_raw(actual):
            expected = snapshot(actual["line_id"])
            require(all(actual.get(k) == v for k, v in expected.items()),
                "IDENTITY_RAW_SOURCE_CHANGED", actual["line_id"])

        probe_map = {p["probe_id"]: p for p in recovery["payload"]["probes"]}
        hypotheses = {}
        for pid in PIXEL_PROBES:
            pr = probe_map[pid]
            require(pr["asset_id"] == ASSET and pr["source_sha256"] == SOURCE_HASH
                and pr["source_size"] == [source["width"], source["height"]], "IDENTITY_PROBE_SOURCE_MISMATCH", pid)
            for variant in pr["variants"]:
                validate_hypotheses(pr, variant)
                for index, line in enumerate(variant["ocr_lines"]):
                    hypotheses[line["line_id"]] = (pr, variant, index, line)

        def same_cpu(actual):
            line_id = actual["line_id"]
            pr, variant, index, line = hypotheses[line_id]
            cpu_seen.add(line_id)
            require(actual == dict(line_id=line_id, probe_id=pr["probe_id"], variant_id=variant["variant_id"],
                raw_result_index=index, text=line["text"], text_sha256=text_hash(line["text"]), bbox=line["bbox"],
                geometry_precision=line["geometry_precision"], source_sha256=pr["source_sha256"],
                independently_confirmed=False), "IDENTITY_CPU_RECEIPT_CHANGED", line_id)

        original_image = None
        if source_path is not None:
            _, resolved = load_source(Path(source_path))
            descriptor, path = next((d, p) for d, p in resolved if d["asset_id"] == ASSET)
            require(descriptor == source, "IDENTITY_ORIGINAL_SOURCE_MISMATCH")
            with Image.open(path) as image:
                original_image = image.convert("RGB")

        receipts = unique(payload["pixel_receipts"], "probe_id", "IDENTITY_DUPLICATE_PIXEL_RECEIPT")
        require(set(receipts) == PIXEL_PROBES, "IDENTITY_PIXEL_RECEIPT_COVERAGE")
        crop_images = {}
        for pid, receipt in receipts.items():
            pr = probe_map[pid]
            crop_path = (fixture / pr["crop_path"]).resolve()
            require(crop_path.is_relative_to(fixture.resolve()), "IDENTITY_CROP_PATH_ESCAPE", pid)
            encoded_hash = hashlib.sha256(crop_path.read_bytes()).hexdigest()
            with Image.open(crop_path) as image:
                image = image.convert("RGB")
            crop_images[pid] = image
            rgb_hash, mask_hash, ink_count = pixels(image)
            require(receipt == dict(probe_id=pid, asset_id=ASSET, source_sha256=SOURCE_HASH,
                source_size=pr["source_size"], source_bbox=pr["crop_bbox"], crop_path=pr["crop_path"],
                crop_sha256=pr["crop_sha256"], crop_size=list(image.size), decoded_rgb_sha256=rgb_hash,
                threshold_160_mask_sha256=mask_hash, threshold_160_ink_pixels=ink_count,
                role="SOURCE_PIXEL_INTEGRITY_ONLY", semantic_verification="UNVERIFIED"),
                "IDENTITY_PIXEL_RECEIPT_CHANGED", pid)
            box = pr["crop_bbox"]
            require(encoded_hash == pr["crop_sha256"] and image.size == (box[2] - box[0], box[3] - box[1])
                and ink_count > 0, "IDENTITY_CROP_CHANGED", pid)
            if original_image is not None:
                require(original_image.crop(box).tobytes() == image.tobytes(), "IDENTITY_ORIGINAL_PIXEL_MISMATCH", pid)
        if original_image is not None:
            original_pixels_checked = True

        def same_region(actual, expected_pid, expected_box):
            require(actual["probe_id"] == expected_pid and actual["source_bbox"] == expected_box,
                "IDENTITY_ANCHOR_REGION_MISMATCH")
            box, outer = actual["source_bbox"], probe_map[expected_pid]["crop_bbox"]
            require(outer[0] <= box[0] < box[2] <= outer[2] and outer[1] <= box[1] < box[3] <= outer[3],
                "IDENTITY_ANCHOR_OUTSIDE_CROP")
            rgb_hash, _, ink = pixels(crop_images[expected_pid].crop(
                (box[0] - outer[0], box[1] - outer[1], box[2] - outer[0], box[3] - outer[1])))
            require(actual["decoded_rgb_sha256"] == rgb_hash and actual["threshold_160_ink_pixels"] == ink
                and ink > 0 and actual["semantic_basis"] == "MODEL_VISUAL_DEVELOPMENT_REVIEW"
                and actual["semantic_verification"] == "UNVERIFIED", "IDENTITY_ANCHOR_PIXELS_CHANGED")

        groups = unique(payload["groups"], "group_id", "IDENTITY_DUPLICATE_GROUP")
        require(set(groups) == set(GROUP_ROWS), "IDENTITY_GROUP_COVERAGE")
        old_groups = {g["group_id"]: g for g in old_review["payload"]["remaining_source_groups"]}
        for gid, group in groups.items():
            ids = [f"{ASSET}/ocr/{i}" for i in GROUP_ROWS[gid]]
            require(group["source_line_ids"] == ids == old_groups[gid]["source_line_ids"], "IDENTITY_GROUP_SOURCE_MISMATCH", gid)
            require(group["candidate_namespace"] == f"book46007447/source-{SOURCE_HASH}/{gid}"
                and group["namespace_scope"] == "SOURCE_LOCAL_INTERNAL_ONLY_NOT_A_OR_PLATFORM_ID"
                and group["assignment_status"] == "UNASSIGNED" and group["verification_status"] == "UNVERIFIED",
                "IDENTITY_FALSE_ASSIGNMENT", gid)
            expected_kind = {"topic1-examples": "NUMBERED_EXAMPLE_REFERENCES",
                "math-world": "UNNUMBERED_WORKED_READING_REFERENCE",
                "topic2-example": "UNNUMBERED_EXAMPLE_REFERENCE",
                "topic2-training": "NUMBERED_TRAINING_REFERENCES"}[gid]
            require(group["material_kind"] == expected_kind, "IDENTITY_GROUP_KIND_MISMATCH", gid)
            title, title_probe, wi, window_box, adjacent = GROUP_BOUNDARIES[gid]
            require(group["title_raw_evidence"] == snapshot(f"{ASSET}/ocr/{title}")
                and group["title_model_visual_text"] == TITLES[gid], "IDENTITY_TITLE_MISMATCH", gid)
            require(group["context_window"] == dict(window_index=wi, **context["pages"][ASSET]["windows"][wi]),
                "IDENTITY_WINDOW_MISMATCH", gid)
            require(group["proposed_activity_window"] == dict(asset_id=ASSET,
                column=0 if gid == "math-world" else 1, source_bbox=window_box,
                reference_quality="MODEL_VISUAL_DEVELOPMENT_REVIEW", not_exact_glyph_segmentation=True),
                "IDENTITY_ACTIVITY_BOUNDARY_MISMATCH", gid)
            require(group["adjacent_markers"] == [snapshot(f"{ASSET}/ocr/{i}") for i in adjacent],
                "IDENTITY_ADJACENT_MARKER_MISMATCH", gid)
            require([l["line_id"] for l in group["title_cpu_evidence"]] ==
                [f"recovery/{title_probe}/{variant}/0" for variant in ("scale3", "scale4-contrast")],
                "IDENTITY_TITLE_CPU_MISMATCH", gid)
            require(group["crop_probe_ids"] == [gid, title_probe] +
                (["title-reflection"] if gid in ("topic2-example", "topic2-training") else []),
                "IDENTITY_GROUP_PIXEL_COVERAGE", gid)
            for line in group["title_cpu_evidence"]:
                same_cpu(line)

        materials = unique(payload["material_candidates"], "material_candidate_id", "IDENTITY_DUPLICATE_MATERIAL")
        require(set(materials) == set(MATERIALS), "IDENTITY_MATERIAL_COVERAGE")
        for mid, material in materials.items():
            kind, label, number, box, markers = MATERIALS[mid]
            gid = mid.split("/")[0]
            require(material["group_id"] == gid and material["candidate_namespace"] == groups[gid]["candidate_namespace"]
                and material["material_kind"] == kind and material["local_printed_label_model_visual"] == label
                and material["printed_number"] == number and type(material["printed_number"]) is type(number)
                and material["printed_number_status"] ==
                ("EXPLICIT_LOCAL_NUMBER" if number is not None else "NO_PRINTED_PRIMARY_NUMBER")
                and material["primary_number_must_not_be_invented"] is (number is None), "IDENTITY_PRINTED_LABEL_MISMATCH", mid)
            require(material["source_role"] == "WORKED_ANSWER_MATERIAL"
                and material["explicit_explanation_heading_present"] is False
                and material["question_identity_status"] == "QUESTION_SOURCE_NOT_CAPTURED_OR_NOT_MAPPED"
                and material["platform_question_id"] is None and material["a_contract_id"] is None
                and material["identity_status"] == "SOURCE_LOCAL_CANDIDATE"
                and material["verification_status"] == "UNVERIFIED"
                and material["human_verified"] is False and material["business_accepted"] is False,
                "IDENTITY_FALSE_VERIFICATION", mid)
            require(material["subparts"] == (["(1)", "(2)", "(3)"] if gid == "math-world" else []),
                "IDENTITY_SUBPART_MISMATCH", mid)
            same_region(material["anchor_pixel_region"], gid, box)
            require([l["line_id"] for l in material["cpu_marker_evidence"]] ==
                [f"recovery/{gid}/{marker}" for marker in markers], "IDENTITY_PRIMARY_CPU_MISMATCH", mid)
            for line in material["cpu_marker_evidence"]:
                same_cpu(line)

        rows = unique(payload["source_rows"], "line_id", "IDENTITY_DUPLICATE_SOURCE_ROW")
        expected_ids = [f"{ASSET}/ocr/{i}" for ids in GROUP_ROWS.values() for i in ids]
        require([r["line_id"] for r in payload["source_rows"]] == expected_ids, "IDENTITY_SOURCE_ROW_COVERAGE")
        for line_id, row in rows.items():
            same_raw(row)
            n = int(line_id.rsplit("/", 1)[1])
            gid = next(g for g, ids in GROUP_ROWS.items() if n in ids)
            require(row["group_id"] == row["title_ref"] == gid
                and row["classification"] == ROW_ROLES[n]
                and row["material_candidate_ids"] == list(ROW_IDENTITIES[n]), "IDENTITY_ROW_OWNERSHIP_MISMATCH", line_id)
            require(row["assignment_status"] == "UNASSIGNED" and row["verification_status"] == "UNVERIFIED"
                and row["source_semantics_human_verified"] is False
                and row["printed_scope_basis"] == "MODEL_VISUAL_PIXELS_WITH_RETAINED_CPU_MARKER_EVIDENCE",
                "IDENTITY_FALSE_ASSIGNMENT", line_id)
            memberships = row["raw_span_memberships"]
            expected_spans = ([[0, 3], [3, 5]] if n == 122 else [[0, 3], [3, 4]] if n == 123 else
                [[0, row["text"].index("（3）")], [row["text"].index("（3）"), len(row["text"])]] if n == 108 else
                [[0, len(row["text"])]] )
            expected_members = list(ROW_IDENTITIES[n]) if n in (122, 123) else [ROW_IDENTITIES[n][0]] * len(expected_spans)
            require([p["span"] for p in memberships] == expected_spans
                and [p["material_candidate_id"] for p in memberships] == expected_members,
                "IDENTITY_RAW_SPAN_MEMBERSHIP_MISMATCH", line_id)
            require(all(p["text"] == row["text"][p["span"][0]:p["span"][1]] for p in memberships)
                and "".join(p["text"] for p in memberships) == row["text"], "IDENTITY_RAW_SPAN_LOSS", line_id)
            expected_roles = (["NUMBERED_TRAINING_ANSWER", "PRINTED_PRIMARY_MARKER"] if n == 122 else
                ["NUMBERED_TRAINING_ANSWER", "PARTIAL_PRINTED_PRIMARY_MARKER"] if n == 123 else
                ["WORKED_ANSWER_SUBPART_TEXT"] * 2 if n == 108 else [ROW_ROLES[n]])
            require([p["source_role"] for p in memberships] == expected_roles,
                "IDENTITY_RAW_SPAN_ROLE_MISMATCH", line_id)
            require(row["subpart_candidates"] == ({102: ["(1)"], 104: ["(2)"],
                108: ["(2)", "(3)"], 110: ["(3)"], 112: ["(3)"]}.get(n, [])),
                "IDENTITY_SUBPART_MISMATCH", line_id)
            if n == 123:
                require(memberships[1].get("missing_in_raw") == ".", "IDENTITY_RAW_MISSING_MARKER_HIDDEN", line_id)
            if n == 108:
                require([p.get("subpart") for p in memberships] == ["(2)", "(3)"], "IDENTITY_SUBPART_MISMATCH", line_id)
            require([l["line_id"] for l in row["cpu_support"]] == ["recovery/" + suffix for suffix in ROW_CPU.get(n, ())],
                "IDENTITY_ROW_CPU_COVERAGE", line_id)
            for line in row["cpu_support"]:
                same_cpu(line)

        additional = payload["additional_cpu_evidence"]
        expected_additional = {
            "topic2_training4_denominator6": ["recovery/topic2-training/scale3/11", "recovery/topic2-training/scale4-contrast/11"],
            "topic2_example_first_fraction55_over16": ["recovery/topic2-example/scale3/3", "recovery/topic2-example/scale3/7"],
            "topic2_example_final_fraction55_over16": ["recovery/topic2-example/scale3/4", "recovery/topic2-example/scale3/8"],
            "math_world_subpart2_markers": ["recovery/math-world/scale3/2", "recovery/math-world/scale4-contrast/3"],
        }
        require(set(additional) == set(expected_additional), "IDENTITY_ADDITIONAL_CPU_COVERAGE")
        for name, expected in expected_additional.items():
            require([l["line_id"] for l in additional[name]] == expected, "IDENTITY_COMPONENT_OWNERSHIP_MISMATCH", name)
            for line in additional[name]:
                same_cpu(line)
        require({g["gap_id"] for g in payload["remaining_gaps"]} == {
            "QUESTION_IDENTITY_NOT_CAPTURED", "FORMULA_TRANSCRIPTION_UNVERIFIED",
            "RAW_MIXED_ROW_GEOMETRY", "READING_DIAGRAM_REGION"}
            and all(g["status"] == "OPEN" for g in payload["remaining_gaps"]), "IDENTITY_GAPS_PROMOTED")
    except (KeyError, ValueError, TypeError, OSError, StopIteration) as exc:
        fail("IDENTITY_MALFORMED_OR_MISSING_INPUT", str(exc))
    return dict(accepted=not issues, decision="HOLD", verification_scope="SOURCE_INTEGRITY_ONLY",
        semantic_verification="UNVERIFIED", human_verified=False, business_accepted=False,
        original_pixels_checked=original_pixels_checked,
        issues=issues, summary={**INVENTORY, "pixel_crops": len(PIXEL_PROBES),
            "distinct_cpu_lines_checked": len(cpu_seen), "issues": len(issues)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=REVIEW)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--source", type=Path, help="optional original-image manifest for exact decoded-pixel comparison")
    args = parser.parse_args()
    try:
        review = json.loads(args.review.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    result = verify(review, args.fixture, args.source)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
