"""Focused A24 old-question preservation negative tests.

This is an independent audit harness.  It imports the frozen release copy but
does not modify it, contact the network, or exercise a save path.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE = WORKSPACE / "work" / "a24-independent-takeover-20261022" / "source-original"
sys.path.insert(0, str(SOURCE / "src"))

from annotation.delivery.live_pilot.wire import (  # noqa: E402
    ROW_FIELDS,
    ZONES,
    build_payload,
    decode_complete_export,
)
from annotation.quality.live_pilot import PilotError, check_preservation, global_order  # noqa: E402
from annotation.runtime.storage.common import digest  # noqa: E402


def expect_denial(name, expected_code, action):
    try:
        action()
    except PilotError as exc:
        passed = exc.code == expected_code
        return {"name": name, "passed": passed, "expected_code": expected_code, "actual_code": exc.code}
    except Exception as exc:  # A crash is not an acceptable fail-closed contract.
        return {"name": name, "passed": False, "expected_code": expected_code,
                "actual_code": type(exc).__name__, "detail": str(exc)}
    return {"name": name, "passed": False, "expected_code": expected_code, "actual_code": "ACCEPTED"}


def export_codec():
    return {
        "schema": "A24CompleteExportCodec/v1",
        "kind_path": ["kind"],
        "metadata_value": "metadata",
        "question_value": "question",
        "metadata_fields": {key: [key] for key in
                            ("book_id", "complete", "question_ids", "zones", "state_version")},
        "question_fields": {key: [key] for key in
                            ("platform_question_id", "question_type", "parts", "wire_zones",
                             "question_info", "rect_ids")},
    }


def question_row(*, include_all_zones=True):
    zones = {zone: ("" if zone in ("analysis", "knowledge_point") else zone) for zone in ZONES}
    if not include_all_zones:
        zones.pop("knowledge_point")
    return {
        "kind": "question",
        "platform_question_id": "q-old",
        "question_type": "ordinary_choice",
        "parts": [{"role": "stem", "text": "old"}],
        "wire_zones": zones,
        "question_info": {"tishi": "xuanze", "tilei": None, "tihao": None},
        "rect_ids": ["r-old"],
    }


def metadata_row():
    return {
        "kind": "metadata",
        "book_id": "46007447",
        "complete": True,
        "question_ids": ["q-old"],
        "zones": list(ZONES),
        "state_version": "observed-state-token",
    }


def inventory():
    return [{"platform_question_id": "q-old"}]


def observation():
    content = {
        "status": "AVAILABLE",
        "question_type": "ordinary_choice",
        "parts": [{"role": "stem", "text": "old"}],
        "wire_zones": {zone: ("" if zone in ("analysis", "knowledge_point") else zone) for zone in ZONES},
        "question_info": {"tishi": "xuanze", "tilei": None, "tihao": None},
        "rect_ids": ["r-old"],
        "raw_record_hash": "frozen-record-hash",
    }
    return {
        "book_id": "46007447",
        "platform_version": "observed-version",
        "directory_details": [{"directory_id": "d-leaf", "parent_id": None}],
        "source_bindings": {"page": {"sha256": "a" * 64}},
        "submission_status": "NOT_SUBMITTED",
        "complete": True,
        "read_status": "OK",
        "view": {
            "target": {
                "questions": [{"platform_question_id": "q-old", "platform_order": 1,
                               "directory_id": "d-leaf"}],
                "frames": [{"platform_frame_id": "r-old", "platform_question_id": "q-old",
                            "platform_type": "text", "box": [0, 0, 10, 10]}],
                "directories": ["d-leaf"],
            },
            "internal_bindings": {},
            "frame_projections": {"r-old": {"platform_question_id": "q-old"}},
            "question_content": {"q-old": content},
        },
    }


def savepage_plan_and_profile():
    frames = []
    parts = []
    bindings = {}
    rows = []
    roles = ["question", "choice", "choice", "choice", "choice", "answer"]
    image_orders = [0, 0, 1, 2, 3, 0]
    for index in range(6):
        aid = f"asset-{index}"
        fragment = f"fragment-{index}"
        bbox = [index * 10, 0, index * 10 + 8, 8]
        frames.append({"fragment_id": fragment, "box": {"bbox": bbox, "image": {"asset_id": aid}}})
        parts.append({"role": "stem" if index == 0 else "answer" if index == 5 else "option",
                      "text": f"part-{index}"})
        bindings[aid] = {"sha256": f"{index:x}" * 64, "save_page": 7, "resource_id": f"page-{index}"}
        row = {
            "rect_id": f"rect-{index}", "type": roles[index], "belong_to_level": "question_level",
            "order_in_level": "2", "image_order_in_annotation_zone": image_orders[index],
            "rect_bbox": ",".join(str(value) for value in bbox), "page_index": 7,
            "image_path": f"https://objects.invalid/crop-{index}.jpg", "parent_rect_id": None,
            "directory_id": "d-leaf", "content_type": "text", "user_id": "user-observed",
            "is_pre_annotation": False, "pre_annotations_id": None,
        }
        assert set(row) == ROW_FIELDS
        rows.append({"fragment_id": fragment,
                     "crop": {"source_sha256": bindings[aid]["sha256"], "bbox": bbox,
                              "save_page": 7, "image_path": row["image_path"]},
                     "fields": row})
    info = {"tishi": "xuanze", "tilei": None, "tihao": None}
    plan = {
        "frames": frames, "approved_parts": parts, "source_bindings": bindings,
        "action": {"expected_after": {"directory_id": "d-leaf"}}, "insert_after_order": 1,
    }
    profile = {"wire": {
        "identity_fields": {"user_id": ["user", "id"], "username": ["user", "name"]},
        "rows": rows, "directory_id": "d-leaf", "insert_after_order": 1,
        "tentative_annotation_order": "2", "choice_separator": "\n",
        "empty_zones": [{"zone": "analysis", "operation": "DELETE_NEW_QUESTION_ONLY"},
                        {"zone": "knowledge_point", "operation": "DELETE_NEW_QUESTION_ONLY"}],
        "question_info": info, "created_by": "observed-user",
        "question_info_approved_hash": digest(info),
    }}
    return plan, profile


def main():
    tests = []

    no_authority = json.dumps(question_row(), separators=(",", ":"))
    tests.append(expect_denial(
        "question_rows_without_authoritative_completeness_record",
        "AUTHORITATIVE_EXPORT_COMPLETENESS_REQUIRED",
        lambda: decode_complete_export(no_authority, export_codec(), inventory()),
    ))

    natural_codec_without_route_authority = {
        "schema": "A24NaturalExportCodec/v1",
        "question_fields": export_codec()["question_fields"],
        "qualification": {
            "schema": "A24FullBodyRouteQualification/v1",
            "status": "UNBOUND",
            "route": "/qieti/api/annotate_ocr/export-paper-questions/46007447",
            "book_id": "46007447",
            "authoritative_catalog_complete": False,
            "all_business_fields_covered": False,
            "zones": list(ZONES),
            "state_binding": None,
            "evidence_refs": [],
        },
    }
    tests.append(expect_denial(
        "natural_export_without_observed_route_qualification",
        "NATURAL_EXPORT_AUTHORITY_UNBOUND",
        lambda: decode_complete_export(no_authority, natural_codec_without_route_authority, inventory()),
    ))

    incomplete_zone = "\n".join(json.dumps(value, separators=(",", ":"))
                                  for value in (metadata_row(), question_row(include_all_zones=False)))
    tests.append(expect_denial(
        "authoritative_row_missing_one_of_five_zones",
        "EXPORT_QUESTION_COVERAGE",
        lambda: decode_complete_export(incomplete_zone, export_codec(), inventory()),
    ))

    missing_content = observation()
    missing_content["view"]["question_content"] = {}
    tests.append(expect_denial(
        "target_inventory_without_full_old_content_denominator",
        "OLD_CONTENT_INCOMPLETE",
        lambda: global_order(missing_content),
    ))

    before = observation()
    mutated = copy.deepcopy(before)
    mutated["view"]["question_content"]["q-old"]["question_info"]["tihao"] = "changed"
    tests.append(expect_denial(
        "old_question_info_mutated_after_save",
        "OLD_QUESTION_CONTENT_CHANGED",
        lambda: check_preservation(before, mutated, "q-new"),
    ))

    plan, profile = savepage_plan_and_profile()
    profile["wire"]["rows"][0]["crop"]["save_page"] = 8
    tests.append(expect_denial(
        "crop_save_page_not_bound_to_source_save_page",
        "CROP_SOURCE_BINDING",
        lambda: build_payload(plan, profile),
    ))

    result = {
        "schema": "A24OldPreservationNegativeTests/v1",
        "source": str(SOURCE),
        "tests": tests,
        "passed": all(test["passed"] for test in tests),
        "counts": {"total": len(tests), "passed": sum(test["passed"] for test in tests)},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
