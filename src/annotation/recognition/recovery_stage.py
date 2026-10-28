"""Exact-payload migration of existing local recovery evidence, with no new OCR.

Historical base, OCR and source-review envelopes retain their original identity.
Only a current E0.2 with exactly the same complete canonical payload can use the
package. A new E0.3 records the migration instead of pretending old observations
were collected for a newer artifact ID. All outputs remain unverified and HOLD.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath

import numpy as np
from PIL import Image, ImageEnhance

from .baseline import code_digest, digest, file_digest, load_source, valid_bbox
from .offline import artifact, check_artifact, validate_context
from .recovery_apply import derive_evidence, derive_review, reference, validate_hypotheses

PACKAGE_SCHEMA = "b-recovery-package-trial/0.1"
REVIEW_SCHEMA = "b-recovery-review-trial/0.1"
POLICY = "EXACT_PAYLOAD_EQUIVALENCE_ONLY/0.1"
CONTENT_POLICY = "NORMALIZED_TEXT_CONTENT/0.1"
IDENTITY_POLICY = "REFERENCE_BOUND_EXECUTION_TIME_IN_JOURNAL/0.1"


def _text(path):
    text = Path(path).read_text(encoding="utf-8")
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def _path(root, relative):
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or PurePosixPath(relative).is_absolute() or PureWindowsPath(relative).drive
            or ".." in PurePosixPath(relative).parts):
        raise ValueError("recovery package paths must be portable and remain inside the package")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("missing recovery package file or escaping symlink")
    return path


def _rgb_sha(image):
    return hashlib.sha256(np.asarray(image, dtype=np.uint8).tobytes()).hexdigest()


def content_receipt(receipt):
    """Stable document content binding; full byte receipts stay in the journal.

    Only text-file byte hashes are projected away. Crop bytes, source pixels,
    normalized document text hashes and every original artifact reference stay.
    """
    result = copy.deepcopy(receipt)
    result["package"].pop("file_sha256")
    for document in result["documents"].values(): document.pop("file_sha256")
    result["receipt_policy"] = CONTENT_POLICY
    return result


def _identity_source(value):
    source = {"book_id": value["book_id"], "scope_id": value["scope_id"],
              "identity_ref": reference(value)}
    if value.get("run_id"): source["run_id"] = value["run_id"]
    return source


def _base(base, source, context):
    check_artifact(base, {"b-evidence-trial/0.2"})
    assets = sorted(source["assets"], key=lambda a: a["reading_order"])
    pages = base["payload"].get("pages", [])
    if (base.get("kind") != "EvidenceBundleTrial"
            or (base.get("book_id"), base.get("scope_id")) != (source["book_id"], source["scope_id"])
            or base["payload"].get("context") != context or base["payload"].get("history_annotations_consumed") is not False
            or "recovery_application" in base["payload"] or "recovery_migration" in base["payload"]
            or base["payload"].get("business_acceptance", False) is not False
            or base["payload"].get("transcription_verified", False) is not False
            or base["payload"].get("platform_actions", []) != []
            or [p.get("asset_id") for p in pages] != [a["asset_id"] for a in assets]
            or [p.get("source") for p in pages] != assets):
        raise ValueError("recovery base must match the complete current source and context")
    seen = set()
    for page in pages:
        asset = page["source"]
        raw_ids = {line.get("line_id") for line in page["ocr_lines"]}
        if page["page_role"] != context["pages"][asset["asset_id"]]["role"]:
            raise ValueError("recovery base page role changed")
        for line in page["ocr_lines"]+page["answer_detail_lines"]:
            if (not isinstance(line.get("line_id"), str) or not line["line_id"] or line["line_id"] in seen
                    or not valid_bbox(line.get("bbox", []), asset["width"], asset["height"])
                    or not isinstance(line.get("text"), str)
                    or ("parent_line_id" in line and line["parent_line_id"] not in raw_ids)):
                raise ValueError("recovery base OCR provenance or geometry is invalid")
            seen.add(line["line_id"])


def load_recovery_package(package_path, source_path, context):
    """Validate the entire package, current original images and all crop pixels.

    Document text hashes normalize platform newlines. Runtime file-byte hashes
    are additionally retained and participate in pipeline cache/input receipts.
    Crop paths, like document paths, are relative to the package manifest folder.
    No model, network, visual transcription, or historical platform state runs.
    """
    package_path = Path(package_path)
    text, text_sha = _text(package_path)
    manifest = json.loads(text)
    source, paths = load_source(Path(source_path))
    validate_context(source, context)
    names = {"base_evidence", "recovery", "source_review"}
    if (set(manifest) != {"schema_version", "artifact_id", "book_id", "scope_id", "policy", "documents"}
            or manifest.get("schema_version") != PACKAGE_SCHEMA or manifest.get("policy") != POLICY
            or not isinstance(manifest.get("artifact_id"), str) or not manifest["artifact_id"]
            or (manifest.get("book_id"), manifest.get("scope_id")) != (source["book_id"], source["scope_id"])
            or not isinstance(manifest.get("documents"), dict) or set(manifest["documents"]) != names):
        raise ValueError("unsupported recovery package, policy or full source identity")
    root, documents, document_receipts = package_path.parent, {}, {}
    schemas = {"base_evidence": {"b-evidence-trial/0.2"}, "recovery": {"b-recovery-trial/0.1"},
               "source_review": {"b-source-review-trial/0.1"}}
    kinds = {"base_evidence": {"EvidenceBundleTrial"}, "recovery": {"RecoveryEvidenceTrial"},
             "source_review": {"SourceRecoveryReviewTrial"}}
    for name in ("base_evidence", "recovery", "source_review"):
        descriptor = manifest["documents"][name]
        if set(descriptor) != {"path", "text_sha256", "artifact_ref"}:
            raise ValueError("invalid recovery document descriptor")
        path = _path(root, descriptor["path"])
        raw, sha = _text(path)
        value = json.loads(raw)
        check_artifact(value, schemas[name])
        if (sha != descriptor["text_sha256"] or reference(value) != descriptor["artifact_ref"] or value.get("kind") not in kinds[name]
                or (value.get("book_id"), value.get("scope_id")) != (source["book_id"], source["scope_id"])):
            raise ValueError("recovery document text, reference or source scope changed")
        documents[name] = value
        document_receipts[name] = {"path": descriptor["path"], "file_sha256": file_digest(path),
                                   "text_sha256": sha, "artifact_ref": reference(value)}
    base, recovery, review = [documents[name] for name in ("base_evidence", "recovery", "source_review")]
    _base(base, source, context)
    if (recovery["payload"]["base_evidence_ref"] != reference(base)
            or review["payload"]["base_evidence_ref"] != reference(base)
            or review["payload"].get("recovery_ref") != reference(recovery)
            or not recovery.get("input_refs") or recovery["input_refs"][0] != reference(base)
            or review.get("input_refs") != [reference(base), reference(recovery)]):
        raise ValueError("historical recovery/source-review references must retain their original base")
    originals = {}
    for asset, path in paths:
        with Image.open(path) as image:
            originals[asset["asset_id"]] = (asset, image.convert("RGB"))
    crops, seen = [], set()
    for probe in recovery["payload"]["probes"]:
        if probe.get("probe_id") in seen or probe.get("asset_id") not in originals:
            raise ValueError("duplicate recovery probe or unknown source asset")
        seen.add(probe["probe_id"])
        asset, original = originals[probe["asset_id"]]
        box = probe["crop_bbox"]
        if (probe["source_sha256"] != asset["sha256"] or probe["source_size"] != [asset["width"], asset["height"]]
                or not valid_bbox(box, asset["width"], asset["height"]) or any(type(v) is not int for v in box)):
            raise ValueError("recovery crop source SHA, dimensions or geometry changed")
        path = _path(root, probe["crop_path"])
        if file_digest(path) != probe["crop_sha256"]:
            raise ValueError("recovery crop bytes changed")
        with Image.open(path) as image:
            crop = image.convert("RGB")
        expected = original.crop(box)
        if crop.size != expected.size or not np.array_equal(np.asarray(crop), np.asarray(expected)):
            raise ValueError("recovery crop does not equal original source pixels")
        for variant in probe["variants"]:
            validate_hypotheses(probe, variant)
            scale = variant["scale"]
            if type(scale) is not int or scale < 1 or scale > 32 or not 0 < variant["contrast"] <= 8:
                raise ValueError("unsupported recovery preprocessing")
            pixels = crop.resize((crop.width*scale, crop.height*scale), Image.Resampling.LANCZOS)
            if variant["contrast"] != 1:
                pixels = ImageEnhance.Contrast(pixels).enhance(variant["contrast"])
            bgr = np.ascontiguousarray(np.asarray(pixels)[:, :, ::-1])
            if hashlib.sha256(bgr.tobytes()).hexdigest() != variant["transformed_pixels_sha256"]:
                raise ValueError("recovery preprocessing pixels changed")
        crops.append({"probe_id": probe["probe_id"], "asset_id": probe["asset_id"], "path": probe["crop_path"],
                      "crop_bbox": list(box), "file_sha256": file_digest(path), "crop_rgb_sha256": _rgb_sha(crop),
                      "source_crop_rgb_sha256": _rgb_sha(expected), "source_sha256": asset["sha256"],
                      "crop_size": list(crop.size)})
    # The existing pure projection rejects malformed plans/roles before a live
    # pipeline could spend time generating a new base. Its inputs stay unchanged.
    derive_evidence(base, recovery, review, artifact)
    receipt = {"package": {"file_sha256": file_digest(package_path), "text_sha256": text_sha,
                           "reference": {"artifact_id": manifest["artifact_id"], "content_hash": digest(manifest)}},
               "documents": document_receipts, "crops": crops,
               "source_ref": {"artifact_id": source["artifact_id"], "content_hash": digest(source)},
               "source_assets": sorted(source["assets"], key=lambda a: a["reading_order"])}
    return {"manifest": manifest, "documents": documents, "receipt": receipt}


def recover_evidence(current_base, package_path, source_path, context):
    """Apply historical observations only after exact whole-payload equivalence."""
    package = load_recovery_package(package_path, source_path, context)
    source, _ = load_source(Path(source_path))
    _base(current_base, source, context)
    base, recovery, source_review = [package["documents"][name] for name in ("base_evidence", "recovery", "source_review")]
    if current_base["payload"] != base["payload"] or digest(current_base["payload"]) != digest(base["payload"]):
        raise ValueError("recovery migration requires exact complete canonical base payload equivalence")
    legacy = derive_evidence(base, recovery, source_review, artifact)
    payload = copy.deepcopy(legacy["payload"])
    payload["recovery_migration"] = {
        "policy": POLICY, "current_base_ref": reference(current_base), "original_base_ref": reference(base),
        "original_recovery_ref": reference(recovery), "original_source_review_ref": reference(source_review),
        "legacy_derived_ref": reference(legacy), "package_receipt": content_receipt(package["receipt"]),
        "current_payload_sha256": digest(current_base["payload"]), "original_payload_sha256": digest(base["payload"]),
        "payloads_equal": True, "current_identity_differs": reference(current_base) != reference(base),
        "original_source_review_archive": copy.deepcopy(source_review), "decision": "HOLD",
        "transcription_verified": False, "business_acceptance": False, "new_ocr_calls": 0, "platform_actions": []}
    result = artifact("b-evidence-trial/0.3", "EvidenceBundleTrial", _identity_source(current_base), payload,
                    [reference(current_base), reference(base), reference(recovery), reference(source_review),
                     package["receipt"]["package"]["reference"]],
                    {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__)),
                     "recovery_apply_code_sha256": code_digest(Path(__file__).with_name("recovery_apply.py")),
                     "policy": POLICY, "identity_policy": IDENTITY_POLICY, "new_ocr_calls": 0})
    # The journal and stage wrapper record execution time. It must not alter
    # downstream identities merely because their legacy source is a full E3.
    result.pop("created_at", None)
    return result


def build_recovery_review(review, recovered):
    """Derive review references separately, without rerunning source recovery."""
    check_artifact(recovered, {"b-evidence-trial/0.3"})
    migration = recovered["payload"].get("recovery_migration", {})
    if (migration.get("policy") != POLICY or migration.get("payloads_equal") is not True
            or migration.get("new_ocr_calls") != 0 or review.get("schema_version") != "b-review-trial/0.1"
            or (review.get("book_id"), review.get("scope_id")) != (recovered["book_id"], recovered["scope_id"])
            or "recovery_migration_ref" in review):
        raise ValueError("recovery review requires an unmigrated review and explicit exact-payload migration")
    derived = derive_review(review, recovered)
    input_ref = {"artifact_id": review["artifact_id"], "content_hash": digest(review)}
    payload = {"review": derived, "input_review_ref": input_ref, "recovered_evidence_ref": reference(recovered),
               "package_receipt": copy.deepcopy(migration["package_receipt"]), "decision": "HOLD",
               "transcription_verified": False, "business_acceptance": False, "new_ocr_calls": 0, "platform_actions": []}
    result = artifact(REVIEW_SCHEMA, "RecoveryReviewTrial", _identity_source(recovered), payload, [input_ref, reference(recovered)],
                    {"module": __name__, "version": "0.1.0", "code_sha256": code_digest(Path(__file__)),
                     "recovery_apply_code_sha256": code_digest(Path(__file__).with_name("recovery_apply.py")),
                     "policy": POLICY, "identity_policy": IDENTITY_POLICY, "new_ocr_calls": 0})
    result.pop("created_at", None)
    return result
