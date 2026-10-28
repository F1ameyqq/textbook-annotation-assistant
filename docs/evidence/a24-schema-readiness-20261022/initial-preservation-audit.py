"""Focused, offline A24 preservation bypass audit against the reviewed tree."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE = WORKSPACE / "work" / "a24-offline-replay-v2-final-independent-20261022" / "effective-tree"
sys.path.insert(0, str(SOURCE / "src"))

from annotation.delivery.live_pilot.wire import ZONES, decode_complete_export, decode_natural_export, project  # noqa: E402
from annotation.quality.live_pilot import PilotError, check_preservation, global_order  # noqa: E402


def base_observation():
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
            "question_content": {
                "q-old": {
                    "status": "AVAILABLE",
                    "question_type": "ordinary_choice",
                    "parts": [{"role": "stem", "text": "old"}],
                    "wire_zones": {zone: ("" if zone in ("analysis", "knowledge_point") else zone)
                                   for zone in ZONES},
                    "question_info": {"tishi": "xuanze"},
                    "rect_ids": ["r-old"],
                    "raw_record_hash": "stable-raw-question-record",
                }
            },
        },
    }


def complete_codec():
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


def natural_codec():
    return {
        "schema": "A24NaturalExportCodec/v1",
        "question_fields": complete_codec()["question_fields"],
        "qualification": {
            "schema": "A24FullBodyRouteQualification/v1",
            "status": "VERIFIED",
            "route": "/qieti/api/annotate_ocr/export-paper-questions/46007447",
            "book_id": "46007447",
            "authoritative_catalog_complete": True,
            "all_business_fields_covered": True,
            "zones": list(ZONES),
            "state_binding": "truthy-but-not-compared-to-current-snapshot",
            "evidence_refs": ["synthetic-audit-ref"],
        },
    }


def export_row(*, qid="q-old", rect_ids=None, extra="A", parts=None, zones=None):
    return {
        "kind": "question",
        "platform_question_id": qid,
        "question_type": "ordinary_choice",
        "parts": [{"role": "stem", "text": "old"}] if parts is None else parts,
        "wire_zones": ({zone: ("" if zone in ("analysis", "knowledge_point") else zone)
                        for zone in ZONES} if zones is None else zones),
        "question_info": {"tishi": "xuanze"},
        "rect_ids": ["r-old"] if rect_ids is None else rect_ids,
        "business_extra": extra,
    }


def accepted(action):
    try:
        value = action()
        return {"accepted": True, "value": value}
    except Exception as exc:
        return {"accepted": False, "error": getattr(exc, "code", type(exc).__name__)}


def denied_code(action):
    result = accepted(action)
    return None if result["accepted"] else result["error"]


def main():
    findings = []

    empty = base_observation()
    empty["view"]["target"]["questions"] = []
    empty["view"]["target"]["frames"] = []
    empty["view"]["question_content"] = {}
    empty["view"]["frame_projections"] = {}
    result = accepted(lambda: global_order(empty))
    findings.append({
        "id": "EMPTY_DENOMINATOR_ACCEPTED",
        "expected_secure_behavior": "DENY_UNBOUND_OR_UNPROVEN_CATALOG",
        "observed": result,
        "vulnerable": result["accepted"] and result["value"] == 0,
    })

    metadata = {"kind": "metadata", "book_id": "46007447", "complete": True,
                "question_ids": [None], "zones": list(ZONES), "state_version": "self-filled"}
    invalid = export_row(qid=None, rect_ids=[None], parts=[None], zones={zone: None for zone in ZONES})
    invalid["question_info"] = {}
    text = "\n".join(json.dumps(row, separators=(",", ":")) for row in (metadata, invalid))
    result = accepted(lambda: decode_complete_export(text, complete_codec(), [{"platform_question_id": None}]))
    findings.append({
        "id": "NONSTRING_IDS_AND_SELF_FILLED_BODY_ACCEPTED",
        "expected_secure_behavior": "DENY_INVALID_OLD_IDENTITY_OR_BODY_SHAPE",
        "observed": {"accepted": result["accepted"], "error": result.get("error")},
        "vulnerable": result["accepted"],
    })

    frame_rule = {"object": {
        "platform_frame_id": {"from": {"response": "$", "path": ["id"]}},
        "platform_question_id": {"from": {"response": "$", "path": ["question_id"]}},
        "platform_type": {"from": {"response": "$", "path": ["type"]}},
        "box": {"from": {"response": "$", "path": ["box"]}},
    }}
    raw_before = {"id": "r-old", "question_id": "q-old", "type": "text",
                  "box": [0, 0, 10, 10], "business_extra": "A"}
    raw_after = dict(raw_before, business_extra="B")
    before, after = base_observation(), base_observation()
    before["view"]["target"]["frames"] = [project(frame_rule, {}, raw_before)]
    after["view"]["target"]["frames"] = [project(frame_rule, {}, raw_after)]
    result = accepted(lambda: check_preservation(before, after, "q-new"))
    findings.append({
        "id": "UNPROJECTED_FRAME_EXTRA_CHANGE_ACCEPTED",
        "expected_secure_behavior": "DENY_OR_RAW_HASH_BIND_UNKNOWN_FRAME_FIELDS",
        "projected_records_equal": before["view"]["target"]["frames"] == after["view"]["target"]["frames"],
        "observed": {"accepted": result["accepted"], "error": result.get("error")},
        "vulnerable": result["accepted"],
    })

    alias_rule = {"lookup": {
        "key": {"from": {"response": "$", "path": ["raw_id"]}},
        "table": {"Q-RAW-A": "q-old", "Q-RAW-B": "q-old"},
    }}
    alias_before = project(alias_rule, {}, {"raw_id": "Q-RAW-A"})
    alias_after = project(alias_rule, {}, {"raw_id": "Q-RAW-B"})
    before, after = base_observation(), base_observation()
    before["view"]["target"]["questions"][0]["platform_question_id"] = alias_before
    after["view"]["target"]["questions"][0]["platform_question_id"] = alias_after
    result = accepted(lambda: check_preservation(before, after, "q-new"))
    findings.append({
        "id": "MANY_TO_ONE_ID_ALIAS_ACCEPTED",
        "expected_secure_behavior": "IDENTITY_FIELDS_MUST_BE_DIRECT_AND_INJECTIVE",
        "raw_before": "Q-RAW-A",
        "raw_after": "Q-RAW-B",
        "projected_before": alias_before,
        "projected_after": alias_after,
        "observed": {"accepted": result["accepted"], "error": result.get("error")},
        "vulnerable": result["accepted"],
    })

    duplicate = base_observation()
    duplicate["view"]["target"]["frames"].append(copy.deepcopy(duplicate["view"]["target"]["frames"][0]))
    missing_zone_metadata = {"kind": "metadata", "book_id": "46007447", "complete": True,
                             "question_ids": ["q-old"], "zones": list(ZONES), "state_version": "state"}
    missing_zones = export_row(zones={zone: zone for zone in ZONES if zone != "knowledge_point"})
    missing_zone_text = "\n".join(json.dumps(row, separators=(",", ":"))
                                      for row in (missing_zone_metadata, missing_zones))

    natural_before = json.dumps(export_row(extra="A"), separators=(",", ":"))
    natural_after = json.dumps(export_row(extra="B"), separators=(",", ":"))
    old_content, _ = decode_natural_export(natural_before, natural_codec(), [{"platform_question_id": "q-old"}])
    new_content, _ = decode_natural_export(natural_after, natural_codec(), [{"platform_question_id": "q-old"}])
    before, after = base_observation(), base_observation()
    before["view"]["question_content"] = old_content
    after["view"]["question_content"] = new_content
    controls = [
        {"id": "DUPLICATE_FRAME_ID_REJECTED", "expected": "TARGET_IDENTITY_DUPLICATE",
         "observed": denied_code(lambda: global_order(duplicate))},
        {"id": "MISSING_FIFTH_ZONE_REJECTED", "expected": "EXPORT_QUESTION_COVERAGE",
         "observed": denied_code(lambda: decode_complete_export(
             missing_zone_text, complete_codec(), [{"platform_question_id": "q-old"}]))},
        {"id": "NATURAL_RAW_EXTRA_DELTA_REJECTED", "expected": "OLD_QUESTION_CONTENT_CHANGED",
         "observed": denied_code(lambda: check_preservation(before, after, "q-new"))},
    ]
    for control in controls:
        control["passed"] = control["observed"] == control["expected"]

    receipt = {
        "schema": "A24PreservationBypassAudit/v1",
        "source": str(SOURCE),
        "findings": findings,
        "vulnerability_count": sum(item["vulnerable"] for item in findings),
        "controls": controls,
        "controls_passed": all(item["passed"] for item in controls),
        "network_browser_live_model_calls": 0,
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=2, default=str))
    return 0 if receipt["vulnerability_count"] == 4 and receipt["controls_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
