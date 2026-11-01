#!/usr/bin/env python3
"""Map the frozen B Q1 source-review candidate into a narrow C01 candidate bundle.

This adapter deliberately produces only SourceBundle, EvidenceBundle and
QuestionGraph artifacts. It never produces a PASS check, READY plan, execution
receipt, policy confirmation, human approval, or platform action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


QUESTION_ID = "q-e92a499995ca1bbd570a2a09"
EXPECTED_B_SCHEMA = "b-question-source-review-trial/0.1"
EXPECTED_B_KIND = "QuestionSourceReviewCandidate"
EXPECTED_B_ARTIFACT_ID = "b-q1-source-review-08f4a1948c7f26003795e797"
EXPECTED_B_HASH = "08f4a1948c7f26003795e797acd7d2d9069f4b2ddde77d2968a05945f249df30"
EXPECTED_B_MANIFEST_SHA256 = "240622443df3c1f31cf76dc490fb7b2cedb9cecb09f47f086909cbe9e9fbd345"
EXPECTED_A_HEAD = "37089f9e0229da76ae1c45461b7e63929590be56"
MAPPER_CONFIG_VERSION = "q1-c01-mapping-v2"
EXPECTED_KEYS = (
    "stem-with-parentheses",
    "option-A",
    "option-B",
    "option-C",
    "option-D",
    "answer-D",
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def content_hash(value: Dict[str, Any]) -> str:
    clean = dict(value)
    clean.pop("content_hash", None)
    return hashlib.sha256(canonical_bytes(clean)).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def derived_id(prefix: str, *parts: Any) -> str:
    seed = canonical_bytes(list(parts))
    return f"{prefix}-{hashlib.sha256(seed).hexdigest()[:24]}"


def load_json(path: Path) -> Any:
    def unique(pairs: Iterable):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def within(inner: List[float], outer: List[float]) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def normalize_created_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("--created-at must be ISO 8601 with a timezone") from error
    require(parsed.tzinfo is not None, "--created-at must include a timezone")
    return value


def validate_frozen_manifest(b_dir: Path) -> Dict[str, Dict[str, Any]]:
    manifest_path = b_dir / "manifest.json"
    require(file_hash(manifest_path) == EXPECTED_B_MANIFEST_SHA256, "unexpected B package manifest SHA-256")
    manifest = load_json(manifest_path)
    require(manifest.get("schema_version") == "b-q1-candidate-package/0.1", "unexpected B package manifest schema")
    require(manifest.get("decision") == "HOLD", "B package manifest decision must remain HOLD")
    entries: Dict[str, Dict[str, Any]] = {}
    for entry in manifest.get("files", []):
        relative = entry.get("path")
        require(isinstance(relative, str) and relative and "\\" not in relative, "invalid B manifest path")
        parts = relative.split("/")
        require(all(part not in ("", ".", "..") for part in parts), f"unsafe B manifest path: {relative}")
        require(relative not in entries, f"duplicate B manifest path: {relative}")
        path = b_dir.joinpath(*parts)
        require(path.is_file(), f"missing B manifest member: {relative}")
        require(path.stat().st_size == entry.get("bytes"), f"B manifest byte count mismatch: {relative}")
        require(file_hash(path) == entry.get("sha256"), f"B manifest SHA-256 mismatch: {relative}")
        entries[relative] = entry
    require(len(entries) == len(manifest.get("files", [])), "B manifest member count mismatch")
    return entries


def image_binding(source: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "asset_id": source["asset_id"],
        "width": int(source["width"]),
        "height": int(source["height"]),
        "sha256": source["sha256"],
    }


def original_box(region: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    return {"image": image_binding(source), "bbox": [float(x) for x in region["bbox"]]}


def identity_transform(region: Dict[str, Any]) -> Dict[str, Any]:
    x0, y0, x1, y1 = region["bbox"]
    return {
        "scale_x": 1.0,
        "scale_y": 1.0,
        "offset_x": float(x0),
        "offset_y": float(y0),
        "rotation_degrees": 0.0,
        "padding": [0.0, 0.0, 0.0, 0.0],
        "processed_width": int(x1 - x0),
        "processed_height": int(y1 - y0),
        "invertible": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a-source", type=Path, required=True, help="fixed A source snapshot root")
    parser.add_argument("--b-candidate-dir", type=Path, required=True, help="frozen B Q1 candidate directory")
    parser.add_argument("--output-dir", type=Path, required=True, help="new empty output directory")
    parser.add_argument(
        "--created-at",
        help="artifact ISO-8601 timestamp; defaults to current UTC, pass explicitly for deterministic replay",
    )
    args = parser.parse_args()

    a_source = args.a_source.resolve()
    b_dir = args.b_candidate_dir.resolve()
    out = args.output_dir.resolve()
    require((a_source / "src/annotation/contracts/models.py").is_file(), "A C01 models.py not found")
    require((a_source / "src/annotation/contracts/validation.py").is_file(), "A C01 validation.py not found")
    require((a_source / "src/annotation/contracts/integrity.py").is_file(), "A C01 integrity.py not found")
    require(not out.exists(), "output directory already exists; refusing to overwrite")
    created_at = normalize_created_at(args.created_at)

    manifest_entries = validate_frozen_manifest(b_dir)

    candidate_path = b_dir / "candidate.json"
    candidate = load_json(candidate_path)
    require(candidate["schema_version"] == EXPECTED_B_SCHEMA, "unexpected B candidate schema")
    require(candidate["kind"] == EXPECTED_B_KIND, "unexpected B candidate kind")
    require(candidate["artifact_id"] == EXPECTED_B_ARTIFACT_ID, "unexpected B candidate artifact ID")
    require(candidate["content_hash"] == EXPECTED_B_HASH, "unexpected B candidate content hash")
    require(
        hashlib.sha256(canonical_bytes(candidate["payload"])).hexdigest() == EXPECTED_B_HASH,
        "B candidate payload content hash mismatch",
    )
    payload = candidate["payload"]
    require(payload["question_id"] == QUESTION_ID, "candidate is not the authorized Q1")
    require(payload["decision"] == "HOLD", "B candidate decision must remain HOLD")
    for name in ("business_acceptance", "human_verified", "production_applied", "a_accepted"):
        require(payload[name] is False, f"B candidate {name} must remain false")
    require(payload["platform_actions"] == [], "B candidate must not contain platform actions")

    source_by_id = {item["asset_id"]: item for item in payload["sources"]}
    region_by_id = {item["region_id"]: item for item in payload["regions"]}
    semantic_regions = [region_by_id[item] for item in payload["proposed_semantic_region_ids"]]
    require(tuple(item["key"] for item in semantic_regions) == EXPECTED_KEYS, "unexpected semantic-region order")
    require(len(semantic_regions) == 6, "exactly six semantic candidate regions are required")
    placeholder = next(item for item in payload["regions"] if item["key"] == "response-parentheses")
    require(placeholder["region_id"] not in payload["proposed_semantic_region_ids"], "parentheses cannot be emitted twice")
    require(within(placeholder["bbox"], semantic_regions[0]["bbox"]), "parentheses must remain inside the stem region")

    input_names = (
        "candidate.json",
        "manifest.json",
        "base-package-binding.json",
        "native-selection.json",
        "scope-applicability-proposal.json",
    )
    for name in input_names:
        require((b_dir / name).is_file(), f"missing B sidecar dependency: {name}")
        if name != "manifest.json":
            require(name in manifest_entries, f"B manifest does not bind required sidecar: {name}")
    for source in source_by_id.values():
        source_path = b_dir / source["path"]
        require(source_path.is_file(), f"missing B source asset: {source['path']}")
        require(file_hash(source_path) == source["sha256"], f"source hash mismatch: {source['asset_id']}")

    sys.path.insert(0, str(a_source / "src"))
    from annotation.contracts import (  # pylint: disable=import-outside-toplevel
        artifact_ref,
        policy_ref,
        seal_artifact,
        seal_policy,
        validate_bundle,
    )

    entity_seed = [
        candidate["artifact_id"],
        candidate["revision"],
        candidate["content_hash"],
        EXPECTED_B_MANIFEST_SHA256,
        EXPECTED_A_HEAD,
        MAPPER_CONFIG_VERSION,
    ]
    artifact_seed = [*entity_seed, created_at]
    scope_id = "single-question-q-e92a499995ca1bbd570a2a09"
    run_id = derived_id("run-q1-c01", artifact_seed)
    policy_id = derived_id("policy-q1-c01", entity_seed)

    policy = seal_policy(
        {
            "policy_id": policy_id,
            "revision": 1,
            "content_hash": "0" * 64,
            "confirmation_status": "UNRESOLVED",
            "option_grouping": "UNRESOLVED",
            "role_mapping": {
                "stem": "Q",
                "option": "W",
                "answer": "A",
                "explanation": "E",
                "shared_material": "Q",
            },
            "source_notes": [
                "Diagnostic adapter policy only; not A policy and not jointly confirmed.",
                "Observed Q1 uses six candidate source regions; no platform-frame decision is made.",
                "B candidate decision remains HOLD and the answer relation remains UNRESOLVED.",
            ],
            "frame_save_status": "UNVERIFIED",
            "ocr_status": "UNVERIFIED",
            "applicability": "PROPOSAL_ONLY",
        }
    )
    producer = {
        "module": "annotation.q1_c01_mapping",
        "implementation_version": "0.1.0",
        "config_version": MAPPER_CONFIG_VERSION,
        "policy_versions": [policy_ref(policy)],
        "model_version": None,
        "prompt_version": None,
        "evidence_mode": "OBSERVED",
    }

    asset_evidence_ids = {
        asset_id: derived_id("ev-q1-source", entity_seed, asset_id) for asset_id in sorted(source_by_id)
    }
    candidate_evidence_id = derived_id("ev-q1-b-candidate", entity_seed)
    evidence_records = [
        {
            "evidence_id": candidate_evidence_id,
            "resource": {
                "path": "inputs/candidate.json",
                "sha256": file_hash(candidate_path),
                "media_type": "application/json",
            },
            "description": "Frozen B Q1 model-visual source-review candidate; HOLD and not human approved.",
            "mode": "OBSERVED",
        }
    ]
    for asset_id in sorted(source_by_id):
        source = source_by_id[asset_id]
        evidence_records.append(
            {
                "evidence_id": asset_evidence_ids[asset_id],
                "resource": {
                    "path": f"assets/{asset_id}.jpg",
                    "sha256": source["sha256"],
                    "media_type": "image/jpeg",
                },
                "description": f"Original immutable source image {asset_id} retained from the B candidate.",
                "mode": "OBSERVED",
            }
        )

    directory_book = derived_id("dir-book", candidate["book_id"])
    directory_chapter = derived_id("dir-chapter", candidate["book_id"], payload["section_path"][0])
    directory_unit = derived_id("dir-unit", candidate["book_id"], payload["section_path"][:2])
    directory_lesson = derived_id("dir-lesson", candidate["book_id"], payload["section_path"])

    source_artifact = seal_artifact(
        {
            "schema_version": "1.0.0-a-proposal",
            "artifact_id": derived_id("source-q1-c01", artifact_seed),
            "revision": 1,
            "kind": "SourceBundle",
            "run_id": run_id,
            "book_id": candidate["book_id"],
            "scope_id": scope_id,
            "input_refs": [],
            "producer": producer,
            "content_hash": "0" * 64,
            "created_at": created_at,
            "payload": {
                "assets": [
                    {
                        "asset_id": source["asset_id"],
                        "path": f"assets/{source['asset_id']}.jpg",
                        "sha256": source["sha256"],
                        "media_type": "image/jpeg",
                        "width": int(source["width"]),
                        "height": int(source["height"]),
                        "source_label": f"B Q1 candidate original image {source['asset_id']}",
                        "provenance": "ORIGINAL",
                    }
                    for source in (source_by_id["viewer-10"], source_by_id["viewer-173"])
                ],
                "directories": [
                    {"directory_id": directory_book, "parent_id": None, "label": "书 46007447"},
                    {"directory_id": directory_chapter, "parent_id": directory_book, "label": payload["section_path"][0]},
                    {"directory_id": directory_unit, "parent_id": directory_chapter, "label": payload["section_path"][1]},
                    {"directory_id": directory_lesson, "parent_id": directory_unit, "label": payload["section_path"][2]},
                ],
                "pages_expected": ["viewer-10", "viewer-173"],
                "pages_acquired": ["viewer-10", "viewer-173"],
                "external_page_mappings": [
                    {
                        "asset_id": asset_id,
                        "directory_id": directory_lesson,
                        "external_page": asset_id,
                        "mapping_status": "UNCERTAIN",
                        "evidence_refs": [asset_evidence_ids[asset_id], candidate_evidence_id],
                    }
                    for asset_id in ("viewer-10", "viewer-173")
                ],
                "history": [
                    {
                        "resource": {
                            "path": "inputs/candidate.json",
                            "sha256": file_hash(candidate_path),
                            "media_type": "application/json",
                        },
                        "quality": "UNVERIFIED",
                        "reason": "B candidate is model-visual source review, not human approval or A acceptance.",
                    }
                ],
                "scope_manifest": [QUESTION_ID],
                "scope_manifest_basis": "Narrow Q1 diagnostic candidate only; not a whole-chapter denominator.",
                "metadata_page_count": None,
            },
        }
    )
    source_ref = artifact_ref(source_artifact)

    mapped_regions = []
    mapping_rows = []
    role_by_key = {
        "stem-with-parentheses": "stem",
        "option-A": "option",
        "option-B": "option",
        "option-C": "option",
        "option-D": "option",
        "answer-D": "answer",
    }
    for order, region in enumerate(semantic_regions):
        source = source_by_id[region["asset_id"]]
        c01_region_id = derived_id("region-q1-c01", entity_seed, region["key"], region["bbox"])
        fragment_id = derived_id("fragment-q1-c01", entity_seed, region["key"], region["text"])
        mapped_regions.append(
            {
                "region_id": c01_region_id,
                "box": original_box(region, source),
                "crop_transform": identity_transform(region),
                "content_type": "text",
                "text": region["text"],
                "source": "HISTORICAL",
                "evidence_refs": [candidate_evidence_id, asset_evidence_ids[region["asset_id"]]],
                "printed_number_candidates": [payload["printed_number"]] if region["key"] == "stem-with-parentheses" else [],
                "certainty": "UNCERTAIN",
            }
        )
        mapping_rows.append(
            {
                "semantic_order": order,
                "semantic_key": region["key"],
                "b_region_id": region["region_id"],
                "c01_region_id": c01_region_id,
                "c01_fragment_id": fragment_id,
                "c01_role": role_by_key[region["key"]],
                "asset_id": region["asset_id"],
                "bbox": region["bbox"],
                "source_fragment_ids": region["source_fragment_ids"],
                "b_verification_status": region["verification_status"],
                "c01_source_enum": "HISTORICAL",
                "c01_certainty": "UNCERTAIN",
            }
        )

    coverage_clues = []
    for mapped, region in zip(mapped_regions, semantic_regions):
        source = source_by_id[region["asset_id"]]
        coverage_clues.append(
            {
                "clue_id": derived_id("clue-q1-c01", entity_seed, region["key"]),
                "box": original_box(region, source),
                "source": "SHARED_RECOGNITION",
                "disposition": "ASSIGNED",
                "region_ids": [mapped["region_id"]],
                "reason": "Assigned only within the narrow six-region Q1 candidate; remains unverified.",
                "evidence_refs": [candidate_evidence_id, asset_evidence_ids[region["asset_id"]]],
            }
        )

    evidence_artifact = seal_artifact(
        {
            "schema_version": "1.0.0-a-proposal",
            "artifact_id": derived_id("evidence-q1-c01", artifact_seed),
            "revision": 1,
            "kind": "EvidenceBundle",
            "run_id": run_id,
            "book_id": candidate["book_id"],
            "scope_id": scope_id,
            "input_refs": [source_ref],
            "producer": producer,
            "content_hash": "0" * 64,
            "created_at": created_at,
            "payload": {
                "source": source_ref,
                "regions": mapped_regions,
                "coverage_clues": coverage_clues,
            },
        }
    )
    evidence_ref = artifact_ref(evidence_artifact)

    fragments = [
        {
            "fragment_id": row["c01_fragment_id"],
            "region_ids": [row["c01_region_id"]],
            "role": row["c01_role"],
            "content_type": "text",
            "reading_order": row["semantic_order"],
        }
        for row in mapping_rows
    ]
    question_fragment_ids = [row["c01_fragment_id"] for row in mapping_rows if row["c01_role"] != "answer"]
    answer_fragment_id = next(row["c01_fragment_id"] for row in mapping_rows if row["c01_role"] == "answer")
    answer_region_id = next(row["c01_region_id"] for row in mapping_rows if row["c01_role"] == "answer")
    relation_id = derived_id("relation-q1-c01", entity_seed, QUESTION_ID, answer_fragment_id)

    graph_artifact = seal_artifact(
        {
            "schema_version": "1.0.0-a-proposal",
            "artifact_id": derived_id("graph-q1-c01", artifact_seed),
            "revision": 1,
            "kind": "QuestionGraph",
            "run_id": run_id,
            "book_id": candidate["book_id"],
            "scope_id": scope_id,
            "input_refs": [source_ref, evidence_ref],
            "producer": producer,
            "content_hash": "0" * 64,
            "created_at": created_at,
            "payload": {
                "source": source_ref,
                "evidence": evidence_ref,
                "questions": [
                    {
                        "question_id": QUESTION_ID,
                        "directory_id": directory_lesson,
                        "question_type": "ordinary_choice",
                        "fragment_ids": question_fragment_ids,
                        "parent_question_id": None,
                        "shared_fragment_ids": [],
                        "cross_page": False,
                        "external_refs": {
                            "printed_number": payload["printed_number"],
                            "platform_question_id": None,
                            "platform_order": None,
                        },
                    }
                ],
                "fragments": fragments,
                "answer_relations": [
                    {
                        "relation_id": relation_id,
                        "question_id": QUESTION_ID,
                        "candidate_fragment_ids": [answer_fragment_id],
                        "selected_fragment_ids": [],
                        "status": "UNRESOLVED",
                        "evidence_refs": [candidate_evidence_id, answer_region_id],
                    }
                ],
                "identity_notes": (
                    "Narrow observed Q1 candidate mapped from the frozen B source-review sidecar. "
                    "Six semantic regions only; response parentheses are contained in the stem region and not duplicated. "
                    "The D answer is a candidate only: relation status is UNRESOLVED, with no human or A acceptance."
                ),
            },
        }
    )
    graph_ref = artifact_ref(graph_artifact)

    bundle = {
        "format_version": "c01-exchange-1",
        "evidence": evidence_records,
        "policies": [policy],
        "artifacts": [source_artifact, evidence_artifact, graph_artifact],
    }
    validated = validate_bundle(bundle, asset_root=None)
    bundle = validated.model_dump(mode="json")

    context_regions = [item for item in payload["regions"] if item["region_id"] not in payload["proposed_semantic_region_ids"]]
    copied_inputs = [
        {"path": f"inputs/{name}", "sha256": file_hash(b_dir / name)} for name in input_names
    ]
    mapping_sidecar = {
        "schema_version": "b-q1-c01-mapping-candidate/0.1",
        "kind": "Q1C01MappingCandidate",
        "artifact_id": derived_id("mapping-q1-c01", artifact_seed),
        "revision": 1,
        "content_hash": "0" * 64,
        "created_at": created_at,
        "decision": "HOLD",
        "business_acceptance": False,
        "human_verified": False,
        "a_accepted": False,
        "platform_actions": [],
        "a_source_identity": {
            "reported_head": EXPECTED_A_HEAD,
            "identity_basis": "PINNED_BY_COORDINATOR_OUTSIDE_HASH_BOUND_SIDECAR",
            "contract_schema": "1.0.0-a-proposal",
            "exchange_format": "c01-exchange-1",
        },
        "mapper_config_version": MAPPER_CONFIG_VERSION,
        "b_manifest": {
            "path": "inputs/manifest.json",
            "sha256": EXPECTED_B_MANIFEST_SHA256,
            "verified_member_count": len(manifest_entries),
            "all_members_verified_before_mapping": True,
        },
        "b_candidate_ref": {
            "schema_version": candidate["schema_version"],
            "kind": candidate["kind"],
            "artifact_id": candidate["artifact_id"],
            "revision": candidate["revision"],
            "content_hash": candidate["content_hash"],
            "scope_id": candidate["scope_id"],
            "input_refs": candidate["input_refs"],
            "hash_convention": "SHA256_CANONICAL_PAYLOAD_ONLY",
        },
        "c01_refs": {"source": source_ref, "evidence": evidence_ref, "graph": graph_ref, "policy": policy_ref(policy)},
        "mapping": mapping_rows,
        "parentheses_mapping": {
            "b_region_id": placeholder["region_id"],
            "bbox": placeholder["bbox"],
            "disposition": "NOT_EMITTED_AS_SEPARATE_C01_REGION",
            "absorbed_by_b_region_id": semantic_regions[0]["region_id"],
            "absorbed_by_c01_region_id": mapping_rows[0]["c01_region_id"],
            "reason": "The evidence crop is wholly contained in the stem candidate; emitting it separately would duplicate the parentheses frame.",
        },
        "relation_mapping": {
            "b_answer_id": payload["answer_id"],
            "b_status": payload["relation_review"]["status"],
            "b_human_approved": payload["relation_review"]["human_approved"],
            "c01_relation_id": relation_id,
            "c01_status": "UNRESOLVED",
            "c01_selected_fragment_ids": [],
            "candidate_fragment_ids": [answer_fragment_id],
        },
        "not_representable_in_c01": {
            "external_b_input_refs": {
                "disposition": "PRESERVED_SIDECAR_ONLY",
                "reason": "C01 ArtifactRef requires a C01 kind and cannot honestly relabel B trial artifacts.",
                "value": candidate["input_refs"],
            },
            "b_hash_convention": {
                "disposition": "PRESERVED_NOT_RELABELED_AS_C01",
                "reason": "The B trial candidate hashes only payload; C01 hashes the normalized full artifact except content_hash.",
                "value": "SHA256_CANONICAL_PAYLOAD_ONLY",
            },
            "model_visual_source_status": {
                "disposition": "MAPPED_TO_HISTORICAL_PLUS_UNCERTAIN",
                "reason": "C01 Region.source has no MODEL_VISUAL value; HUMAN would be false and OCR/DETECTOR would misstate the review method.",
            },
            "b_normalizations": {
                "disposition": "PRESERVED_SIDECAR_ONLY",
                "value": payload["candidate_content"]["normalizations"],
            },
            "b_changes": {"disposition": "PRESERVED_SIDECAR_ONLY", "value": payload["changes"]},
            "context_only_regions": {
                "disposition": "PRESERVED_NOT_EMITTED_AS_SEMANTIC_REGIONS",
                "count": len(context_regions),
                "value": context_regions,
            },
            "scope_applicability": {
                "disposition": "COPIED_INPUT_NOT_CONVERTED_TO_POLICY_DECISION",
                "path": "inputs/scope-applicability-proposal.json",
            },
            "platform_frame_count": {
                "disposition": "REMAINS_UNKNOWN",
                "value": payload["coverage"]["platform_frame_count"],
            },
        },
        "invariants": {
            "semantic_region_count": len(mapped_regions),
            "parentheses_region_count_in_c01": 1,
            "answer_relation_selected": False,
            "observed_artifacts": True,
            "original_source_assets": True,
            "policy_confirmation_status": "UNRESOLVED",
            "policy_applicability": "PROPOSAL_ONLY",
            "c01_validation": "VALID_SOURCE_EVIDENCE_GRAPH_CANDIDATE_ONLY",
            "positive_target_or_dispatch_claim": False,
        },
        "copied_inputs": copied_inputs,
        "remaining_limits": [
            "No PRE_APPLY or TARGET CheckReport is produced by this adapter.",
            "No READY ApplyPlan, dispatch, platform write, or ExecutionReceipt is produced.",
            "A analyze_target synthetic-only path is not applicable to these OBSERVED/ORIGINAL inputs.",
            "The unresolved proposal policy is diagnostic scaffolding and is not A policy or joint confirmation.",
            "The Q1-to-D relation remains a candidate and is intentionally UNRESOLVED.",
            "The two-page list is the narrow question/answer source set, not a complete chapter denominator.",
            "The closed C01 bundle contains its direct resource closure only; the original B package remains required for all embedded crop/context dependencies carried by candidate.json.",
        ],
    }
    mapping_sidecar["content_hash"] = content_hash(mapping_sidecar)

    out.mkdir(parents=True)
    (out / "assets").mkdir()
    (out / "inputs").mkdir()
    for source in source_by_id.values():
        shutil.copyfile(b_dir / source["path"], out / f"assets/{source['asset_id']}.jpg")
    for name in input_names:
        shutil.copyfile(b_dir / name, out / "inputs" / name)
    write_json(out / "c01-candidate-bundle.json", bundle)
    write_json(out / "mapping-sidecar.json", mapping_sidecar)

    verified = validate_bundle(load_json(out / "c01-candidate-bundle.json"), asset_root=out)
    refs = {item.kind: artifact_ref(item) for item in verified.artifacts}
    report = f"""# Q1 B source candidate → A C01 mapping candidate

Technical mapping result: **VALID C01 source/evidence/graph candidate**  
Business/release result: **HOLD**

Mapper configuration: `{MAPPER_CONFIG_VERSION}`  
Artifact creation time: `{created_at}`

This directory maps only `Q1 {QUESTION_ID}` from the frozen B source-review candidate into the fixed A C01 proposal types. It does not create a check, plan, receipt, PASS decision, READY state, platform action, human approval, or A policy confirmation.

## C01 artifact refs

- Source: `{refs['SourceBundle']['artifact_id']}` / revision `{refs['SourceBundle']['revision']}` / `{refs['SourceBundle']['content_hash']}`
- Evidence: `{refs['EvidenceBundle']['artifact_id']}` / revision `{refs['EvidenceBundle']['revision']}` / `{refs['EvidenceBundle']['content_hash']}`
- Graph: `{refs['QuestionGraph']['artifact_id']}` / revision `{refs['QuestionGraph']['revision']}` / `{refs['QuestionGraph']['content_hash']}`
- Diagnostic policy: `{policy['policy_id']}` / revision `{policy['revision']}` / `{policy['content_hash']}`; `UNRESOLVED`, `PROPOSAL_ONLY`

## Deliberate semantics

- Both C01 assets retain the B candidate's exact JPEG SHA-256, dimensions, asset IDs, and `ORIGINAL` provenance.
- All three artifacts use `evidence_mode=OBSERVED`.
- Exactly six semantic regions are emitted: stem including the printed response parentheses, options A–D, and the D answer crop.
- The nested parentheses evidence region is not emitted separately. It is recorded in `mapping-sidecar.json` as absorbed by the stem, preventing a duplicate frame.
- Region provenance is `HISTORICAL` with `certainty=UNCERTAIN`; C01 has no honest `MODEL_VISUAL` enum and these regions are neither HUMAN-confirmed nor newly OCR/DETECTOR-produced.
- The answer fragment is the sole candidate, but `selected_fragment_ids=[]` and relation status is `UNRESOLVED`.

## Contract gaps preserved outside C01

`mapping-sidecar.json` retains the external B trial refs, source fragment IDs, normalization proposal, B changes, context-only regions and crops, relation-review basis, scope-applicability input, and HOLD flags. These are not forced into incompatible C01 fields.

Before mapping, the generator verifies the frozen B manifest SHA-256 `{EXPECTED_B_MANIFEST_SHA256}` and every one of its listed members by path, byte count, and SHA-256. The closed C01 bundle carries only its direct resource closure; the original B package remains required for the candidate's embedded crop/context dependency closure.

The included policy exists only because a closed `c01-exchange-1` requires a policy list. It is explicitly `UNRESOLVED` / `PROPOSAL_ONLY`, with frame and OCR status `UNVERIFIED`; it is not A policy and cannot support an ordinary-choice positive target.

## Verification performed

The script validates the generated closed bundle with the fixed A `annotation.contracts.validate_bundle` consumer, including local JPEG bytes, dimensions, hashes, references, geometry, scope, question ownership, and the unresolved answer relation. Re-running into a new empty directory is deterministic.

## Remaining boundary

Root may append diagnostic PRE_APPLY/TARGET handling, but real Q1 inputs must remain OBSERVED/ORIGINAL. The A synthetic positive-target helper is inapplicable. Any plan should remain BLOCKED and any receipt NOT_EXECUTED unless a later, separately authorized and valid policy/check chain changes that conclusion. Business status remains HOLD.
"""
    (out / "mapping-limitations.md").write_text(report, encoding="utf-8", newline="\n")

    manifest = {
        "schema_version": "q1-c01-mapping-manifest/0.1",
        "generator": {"path": "../build_q1_c01_mapping.py", "sha256": file_hash(Path(__file__).resolve())},
        "a_reported_head": EXPECTED_A_HEAD,
        "mapper_config_version": MAPPER_CONFIG_VERSION,
        "created_at": created_at,
        "b_manifest_sha256": EXPECTED_B_MANIFEST_SHA256,
        "b_manifest_members_verified": len(manifest_entries),
        "b_candidate_ref": {
            "artifact_id": candidate["artifact_id"],
            "revision": candidate["revision"],
            "content_hash": candidate["content_hash"],
        },
        "files": [],
        "decision": "HOLD",
    }
    for path in sorted(item for item in out.rglob("*") if item.is_file()):
        manifest["files"].append(
            {"path": path.relative_to(out).as_posix(), "sha256": file_hash(path), "bytes": path.stat().st_size}
        )
    write_json(out / "manifest.json", manifest)

    print(
        json.dumps(
            {
                "valid": True,
                "decision": "HOLD",
                "artifacts": refs,
                "policy": policy_ref(policy),
                "semantic_regions": 6,
                "parentheses_regions": 1,
                "answer_relation": "UNRESOLVED",
                "mapper_config_version": MAPPER_CONFIG_VERSION,
                "created_at": created_at,
                "b_manifest_members_verified": len(manifest_entries),
                "output_dir": str(out),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
