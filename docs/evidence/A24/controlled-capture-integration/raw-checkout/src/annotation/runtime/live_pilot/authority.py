"""A24 R1 immutable owner authority. Verification performs file reads only.

No profile/native/browser/process import or acquisition precedes this verifier.
An activated label/reference alone is never an Authority capability.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import re

from annotation.contracts.integrity import unique_object
from annotation.quality.live_pilot import require
from annotation.runtime.storage.common import digest

AUTHOR = "01a15cf8-0c63-70d3-b374-ce85e6f29fd7"
REVIEWER = "01a15cf8-68e0-7b63-91a3-657a567b344c"
COORDINATOR = "01a15dfa-9556-7812-9ed5-1b3bce53555e"
PROFILE = "b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00"
BOOK = "46007447"
TARGET = "https://www.usense.com/qieti/annotateUnified"
_SEAL = object()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def is_hash(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


def parse(raw):
    return json.loads(raw, object_pairs_hook=unique_object,
                      parse_constant=lambda value: require(False, "NONFINITE_AUTHORITY"))


def utc(value):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)", value),
            "AUTHORITY_UTC_REQUIRED")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def same(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(same(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(same(a, b) for a, b in zip(actual, expected))
    return actual == expected


def read_ref(reference, roots):
    require(isinstance(reference, dict) and set(reference) == {"path", "sha256", "bytes"} and
            is_hash(reference["sha256"]) and type(reference["bytes"]) is int and reference["bytes"] >= 0,
            "AUTHORITY_RESOURCE_REF")
    path = Path(reference["path"]).resolve()
    require(any(path == root or root in path.parents for root in roots) and not path.is_symlink(), "AUTHORITY_RESOURCE_PATH")
    raw = path.read_bytes()
    require(len(raw) == reference["bytes"] and sha(raw) == reference["sha256"], "AUTHORITY_RESOURCE_HASH")
    return raw


def validate_plan(plan):
    """Typed complete scope, including bootstrap and independent context slots."""
    require(isinstance(plan, dict) and plan.get("schema") == "A24FirstSaveExecutablePlan/v1" and
            plan.get("task") == "A24" and plan.get("book_id") == BOOK and
            plan.get("candidate_identity") == "section2-basic-printed1-viewer14" and
            plan.get("target_leaf") == "dir-1792063578574-g0n3ulsni" and
            plan.get("insert_after_order") == 22 and type(plan["insert_after_order"]) is int and
            plan.get("tentative_annotation_order") == "23" and
            plan.get("question_info") == {"tishi": "xuanze", "tilei": None, "tihao": None}, "FIRST_SAVE_PLAN_SCOPE")
    require(same(plan.get("limits"), {"author_context": 1, "reopen_context": 1, "author_navigation": 2,
        "reopen_navigation": 1, "signature_get": 1, "object_post": 6, "commit_post": 1,
        "login_post": 0, "refresh_token_post": 0, "credential_config_reads": 0,
        "ocr_model_calls": 0, "redirects": 0, "retries": 0, "old_mutations": 0, "book_submit": 0,
        "author_seconds": 900, "reopen_seconds": 900}), "FIRST_SAVE_PLAN_LIMITS")
    require(plan.get("readback_strategy") in ("AUTHORITATIVE_AGGREGATE", "AUTHORITATIVE_AGGREGATE_PLUS_INFO"),
            "FIRST_SAVE_READBACK_STRATEGY")
    expected = {"baseline": 4, "prewrite": 3, "get": 3, "refresh": 3, "reopen": 4}
    if plan["readback_strategy"].endswith("PLUS_INFO"):
        expected = dict(expected, get=4, refresh=4, reopen=5)
    require(same(plan.get("business_get_counts"), expected), "FIRST_SAVE_BUSINESS_COUNTS")
    require(plan.get("body_admission") in ("CURRENT_SCHEMA_UNBOUND", "FROZEN_QUALIFIED_ROUTE_CODEC") and
            plan.get("save_page_status") == "PROPOSED_14_173_CURRENT_SOURCE_AND_POSTSAVE_PROOF_REQUIRED" and
            plan.get("source_actual_final") == "dceda09db31487d64654e23dd36ccd3705c740fc", "FIRST_SAVE_FACT_STATE")
    bootstrap = plan.get("bootstrap")
    require(isinstance(bootstrap, dict) and set(bootstrap) == {"target", "session_paths", "session_get_per_path_per_context",
        "static_path_hashes", "static_get_per_path_per_document", "version_path", "version_get_per_context",
        "version_repeat_denial_events", "passive_book_denial_events", "combined_excluded_denial_events"} and
        bootstrap["target"] == TARGET and bootstrap["session_paths"] == ["/qieti/api/user_login/profile",
            "/qieti/api/user_login/config/permissions", "/qieti/api/user_login/config/teams"] and
        bootstrap["session_get_per_path_per_context"] == 2 and type(bootstrap["session_get_per_path_per_context"]) is int and
        bootstrap["static_get_per_path_per_document"] == 1 and bootstrap["version_path"] == "/qieti/version.json" and
        bootstrap["version_get_per_context"] == 1 and bootstrap["version_repeat_denial_events"] == 2 and
        bootstrap["passive_book_denial_events"] == 4 and bootstrap["combined_excluded_denial_events"] == 16,
        "FIRST_SAVE_BOOTSTRAP_SCOPE")
    require(isinstance(bootstrap["static_path_hashes"], list) and len(bootstrap["static_path_hashes"]) == 4 and
            all(set(v) == {"kind", "path_sha256"} and is_hash(v["path_sha256"]) and
                v["kind"] in ("Script", "Stylesheet", "Image", "Other") for v in bootstrap["static_path_hashes"]),
            "FIRST_SAVE_STATIC_SCOPE")
    require(plan.get("upload_host") == "https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com" and
            plan.get("oss_success_contract") == "NATIVE_OBSERVED_HTTP_2XX_NO_SERVER_HOST_KEY_ECHO" and
            plan.get("old_budgets_restored") is False and plan.get("other_cases") == "HOLD" and
            plan.get("Q22") == "NATURAL_AGGREGATE_ONLY", "FIRST_SAVE_UPLOAD_SCOPE")
    require(plan.get("model_requirement") == "ACTUAL_B_ENTRY_OUTPUT_WITH_EXPLICIT_CONVERSION_AND_APPROVAL" and
            plan.get("human_text_use") == "EVALUATION_ONLY_NO_SECOND_SAVE", "FIRST_SAVE_MODEL_SOURCE_SCOPE")
    return digest(plan)


@dataclass(frozen=True)
class Authority:
    data: dict
    plan: dict
    candidate: dict
    request: dict
    schema_profile: object
    crop_manifest: dict
    author_release: object
    fingerprint: str
    raw_hash: str
    package_root: Path
    output: Path
    starts_at: datetime
    expires_at: datetime
    _seal: object

    @property
    def synthetic(self):
        return self.data["mode"] == "SYNTHETIC"

    @property
    def role(self):
        return self.data["role"]

    def check(self, now=None):
        require(self._seal is _SEAL and sha(self.fingerprint.encode()) == self.data["verified_capability_hash"],
                "VALIDATED_OWNER_AUTHORITY_REQUIRED")
        current = now or datetime.now(timezone.utc)
        require(current.tzinfo is not None and self.starts_at <= current < self.expires_at, "OWNER_AUTHORITY_EXPIRED")
        require(digest(self.plan) == self.data["scope_sha256"], "OWNER_SCOPE_CHANGED")
        plain = {k: v for k, v in self.data.items() if k != "verified_capability_hash"}
        require(digest({"data": plain, "plan": self.plan, "request": self.request,
                        "schema_profile": self.schema_profile, "crop_manifest": self.crop_manifest,
                        "candidate": self.candidate, "author_release": self.author_release}) == self.fingerprint, "OWNER_VERIFIED_INPUT_CHANGED")
        validate_predecessor(self.role, self.plan, self.request, self.schema_profile, self.author_release,
                             self.data["mode"], self.output.parent if self.synthetic else Path("D:/1800/.local/stages"))
        return self


def verify_authority(path, expected_sha256, package_root, *, now=None, synthetic_root=None):
    """Verify every binding before returning an owner capability. No activation creation."""
    require(is_hash(expected_sha256), "EXPLICIT_AUTHORITY_DIGEST_REQUIRED")
    raw = Path(path).read_bytes()
    require(sha(raw) == expected_sha256, "OWNER_AUTHORITY_DIGEST")
    data = parse(raw)
    fields = {"schema", "task", "mode", "role", "run_id", "coordinator", "executor", "profile_fingerprint",
              "not_before", "expires_at", "scope_sha256", "refs", "output_directory", "ignore_https_errors",
              "original_and_crop_roots", "old_budgets_restored"}
    require(isinstance(data, dict) and set(data) == fields and data["schema"] == "A24FirstSaveOwnerAuthority/v1" and
            data["task"] == "A24" and data["mode"] in ("OBSERVED", "SYNTHETIC") and
            data["role"] in ("AUTHOR_SAVE", "INDEPENDENT_REOPEN") and
            data["coordinator"] == COORDINATOR and data["executor"] == (AUTHOR if data["role"] == "AUTHOR_SAVE" else REVIEWER) and
            data["profile_fingerprint"] == PROFILE and data["old_budgets_restored"] is False and
            type(data["ignore_https_errors"]) is bool and re.fullmatch(r"A24-first-save-r1-[a-z0-9-]{1,64}", data["run_id"]),
            "OWNER_AUTHORITY_FIELDS")
    start, end = utc(data["not_before"]), utc(data["expires_at"])
    current = now or datetime.now(timezone.utc)
    require(current.tzinfo is not None and 0 < (end-start).total_seconds() <= 900 and start <= current < end,
            "OWNER_AUTHORITY_WINDOW")
    package = Path(package_root).resolve()
    if data["mode"] == "SYNTHETIC":
        require(synthetic_root is not None, "SYNTHETIC_OWNER_CANNOT_LAUNCH")
        roots = [package, Path(synthetic_root).resolve()]
    else:
        require(synthetic_root is None, "OBSERVED_AUTHORITY_CANNOT_USE_FAKE_ROOT")
        roots = [package, Path("D:/1800/docs").resolve(), Path("D:/1800/.local/stages/a24-first-save-r1-inputs").resolve(),
                 Path("D:/1800-worktrees/a24-first-save/.local/a24-first-save-wire-r1").resolve(),
                 Path("D:/1800/.local/stages/a24-model-one-question").resolve()]
    refs = data["refs"]
    require(isinstance(refs, dict) and set(refs) == {"candidate", "decision", "independent_report", "plan", "request", "schema_profile", "crop_manifest", "author_release"},
            "OWNER_AUTHORITY_REFS")
    documents = {key: parse(read_ref(refs[key], roots)) for key in ("candidate", "decision", "independent_report", "plan")}
    candidate, decision, report, plan = (documents[k] for k in ("candidate", "decision", "independent_report", "plan"))
    scope_hash = validate_plan(plan)
    common = {"task": "A24", "mode": data["mode"], "run_id": data["run_id"], "role": data["role"],
              "coordinator": COORDINATOR, "executor": data["executor"], "scope_sha256": scope_hash,
              "candidate_sha256": refs["candidate"]["sha256"], "plan_sha256": refs["plan"]["sha256"],
              "request_sha256": refs["request"]["sha256"], "schema_profile_sha256": None if refs["schema_profile"] is None else refs["schema_profile"]["sha256"],
              "crop_manifest_sha256": refs["crop_manifest"]["sha256"], "author_release_sha256": None if refs["author_release"] is None else refs["author_release"]["sha256"],
              "not_before": data["not_before"], "expires_at": data["expires_at"]}
    require(data["scope_sha256"] == scope_hash and all(same(doc.get(k), v) for doc in (decision, report) for k, v in common.items()),
            "OWNER_DECISION_REPORT_SCOPE")
    require(decision.get("schema") == "A24FirstSaveUserDecision/v1" and decision.get("live_authorized") is True and
            decision.get("authorization_basis") == "USER_REQUESTED_A24_FIRST_SAVE_BOUND_TO_THIS_EXACT_SCOPE" and
            decision.get("credential_submission_authorized") is False and decision.get("credential_config_access_authorized") is False and
            decision.get("tls_exception_authorized") is data["ignore_https_errors"] and
            decision.get("upload_origin") == plan["upload_host"] and
            report.get("schema") == "A24FirstSaveIndependentAcceptance/v1" and
            report.get("reviewer") == REVIEWER and report.get("result") == "ACCEPTED_OFFLINE_ONLY", "OWNER_NEW_DECISION_ACCEPTANCE_REQUIRED")
    require(candidate.get("schema") == "A24R1FrozenCandidate/v1" and candidate.get("scope_sha256") == scope_hash and
            isinstance(candidate.get("dependencies"), list) and candidate["dependencies"], "OWNER_CANDIDATE_SCOPE")
    names = set()
    for item in candidate["dependencies"]:
        require(set(item) == {"path", "bytes", "sha256"} and isinstance(item["path"], str) and
                item["path"] not in names and not Path(item["path"]).is_absolute(), "OWNER_DEPENDENCY_FIELDS")
        names.add(item["path"])
        target = (package / item["path"]).resolve()
        require(package in target.parents and not target.is_symlink(), "OWNER_DEPENDENCY_PATH")
        frozen = target.read_bytes()
        require(type(item["bytes"]) is int and len(frozen) == item["bytes"] and sha(frozen) == item["sha256"], "OWNER_DEPENDENCY_HASH")
    required = {"tools/a24_first_save_launcher.py", "src/annotation/runtime/live_pilot/owner.py",
        "src/annotation/runtime/live_pilot/authority.py", "src/annotation/runtime/live_pilot/runner.py",
        "src/annotation/runtime/live_pilot/private_payload.py", "src/annotation/delivery/live_pilot/usense.py",
        "src/annotation/delivery/live_pilot/wire.py", "src/annotation/delivery/live_pilot/plan.py",
        "src/annotation/quality/live_pilot.py", "src/annotation/runtime/live_pilot/journal.py",
        "tools/a16_current_state_probe.py", "docs/evidence/A16/current-readonly/dependencies/a15_native_reference.py",
        "docs/evidence/A15/certificate-exception/reviewed-native/native_windows.py",
        "docs/evidence/A15/certificate-exception/reviewed-native/process_check.py"}
    require(required.issubset(names), "OWNER_REQUIRED_DEPENDENCY_OMITTED")
    # Private business inputs are read only after exact decision/report verification.
    request = parse(read_ref(refs["request"], roots))
    schema_profile = None if refs["schema_profile"] is None else parse(read_ref(refs["schema_profile"], roots))
    crops = parse(read_ref(refs["crop_manifest"], roots))
    require(crops.get("schema") == "A24R1ExactCropBindings/v1" and len(crops.get("regions", [])) == 6 and
            [r["role"] for r in crops["regions"]] == ["Q", "W", "W", "W", "W", "A"], "OWNER_CROP_MANIFEST")
    crop_roots = [Path(p).resolve() for p in data["original_and_crop_roots"]]
    if not synthetic_root:
        require(crop_roots == [Path("D:/1800-worktrees/a24-first-save/.local/a24-first-save-wire-r1/crops").resolve()],
                "OWNER_FIXED_CROP_ROOT")
    for region in crops["regions"]:
        target = Path(region["private_path"]).resolve()
        require(any(root in target.parents for root in crop_roots), "OWNER_CROP_PATH")
        content = target.read_bytes()
        require(len(content) == region["jpeg_bytes"] and sha(content) == region["jpeg_sha256"], "OWNER_CROP_BYTES")
    if data["mode"] == "OBSERVED":
        validate_fixed_content(request, crops, roots)
        if schema_profile is not None:
            validate_bound_counts(plan, schema_profile)
            require(all(spec.get("export", {}).get("codec", {}).get("schema") == "A24NaturalExportCodec/v1"
                        for spec in schema_profile["reads"].values()), "OBSERVED_NATURAL_EXPORT_REQUIRED")
    author_release = None
    if data["role"] != "AUTHOR_SAVE":
        require(refs["author_release"] is not None, "OWNER_AUTHOR_RELEASE_REQUIRED")
        author_release = parse(read_ref(refs["author_release"], roots))
    else:
        require(refs["author_release"] is None, "OWNER_AUTHOR_RELEASE_SCOPE")
    output = Path(data["output_directory"]).resolve()
    expected_output = Path("D:/1800/.local/stages") / data["run_id"]
    require(output == (Path(synthetic_root)/data["run_id"]).resolve() if synthetic_root else output == expected_output.resolve(),
            "OWNER_NEW_OUTPUT_ONLY")
    fingerprint = digest({"data": data, "plan": plan, "request": request,
                          "schema_profile": schema_profile, "crop_manifest": crops, "candidate": candidate,
                          "author_release": author_release})
    sealed = copy.deepcopy(data)
    sealed["verified_capability_hash"] = sha(fingerprint.encode())
    return Authority(sealed, copy.deepcopy(plan), candidate, request, schema_profile, crops, author_release, fingerprint,
                     sha(raw), package, output, start, end, _SEAL).check(current)


def validate_fixed_content(request, crops, roots):
    """Bind the already accepted fixed artifacts; never invoke or relabel OCR."""
    expected = {"reviewed_candidate": "cd4ee0c6a379fa5bf8cc87dccdb010c423a9e2f9a2382336efaa00cefe103b5a",
        "raw_regional": "6452f279a70151721115cd1f8bef1d4995a0e296ad10239694fc23bf9acf322d",
        "input_manifest": "f478e2b47c1338ff303612d3d99967811b7dea5c5b4b7a204faf7f9e789055be",
        "result_manifest": "ec45a2c44e262a96b210aa5fd8a00a8a360721a4773cbaede4a7d22596ee3108"}
    model = request.get("model_binding", {})
    require(set(model) == set(expected) and all(model[k]["sha256"] == v for k, v in expected.items()), "ACTUAL_MODEL_BINDING_REQUIRED")
    values = {k: parse(read_ref(v, roots)) for k, v in model.items()}
    acceptance = request.get("content_acceptance", {})
    require(set(acceptance) == {"independent", "root"} and
            acceptance["independent"]["sha256"] == "1dad447c41ee2d8a8ce79e02d3aef2c5ef0238be07278759a118d0273ab6e9e0" and
            acceptance["root"]["sha256"] == "9feb5218e54b561a5d094d5bbd86604a8574b3c773722ce768f31924fa123d2e", "FIXED_CONTENT_ACCEPTANCE_REQUIRED")
    accepted = {k: parse(read_ref(v, roots)) for k, v in acceptance.items()}
    require(accepted["root"]["corrected_content_sha256"] == expected["reviewed_candidate"] and
            accepted["root"]["human_user_content_review"] is False and
            values["raw_regional"]["status"] == "FAILED_HOLD_ANSWER_REGION_EMPTY" and
            not values["raw_regional"]["records"][5]["B_ocr_atoms"], "FIXED_MODEL_FAILURE_MUST_REMAIN")
    for asset, crop in zip(values["input_manifest"]["assets"], crops["regions"]):
        require(asset["pixel_sha256"] == crop["source_crop_RGB_sha256"] and
                asset["original_bbox"] == crop["original_bbox_xyxy"] and
                asset["source_original_sha256"] == crop["original_sha256"], "ACTUAL_MODEL_INPUT_IDENTITY")
    conversion = parse(read_ref(request["native_conversion_ref"], roots))
    fragments = values["reviewed_candidate"]["fragments"]
    texts = [(v["label"] + ". " if v.get("label") else "") + v["approved_text"] for v in fragments]
    require([v["text"] for v in conversion["parts"]] == texts and
            conversion["human_content_approval_claimed"] is False, "FIXED_CONTENT_CONVERSION")
    if request.get("approval") is not None:
        require(request["approval"]["questions"][0]["approved_parts"] == conversion["parts"], "FIXED_CONTENT_APPROVAL_BINDING")
    return True


def validate_bound_counts(plan, profile):
    """Compile the real profile's business counts against the same fixed plan."""
    require(profile.get("aggregate_readback", {}).get("mode") == (
        "ALL_ZONES_INFO_GET" if plan["readback_strategy"].endswith("PLUS_INFO") else "ALL_ZONES_AND_INFO"),
        "OWNER_AGGREGATE_STRATEGY_MISMATCH")
    extra = 1 if plan["readback_strategy"].endswith("PLUS_INFO") else 0
    counts = {}
    for phase in ("baseline", "prewrite", "get", "refresh", "reopen"):
        spec = profile["reads"][phase]
        counts[phase] = (len(spec["requests"]) if "requests" in spec else 1) + int("export" in spec)
        if phase in ("get", "refresh", "reopen"):
            counts[phase] += extra
    require(same(counts, plan["business_get_counts"]) and
            same(profile.get("limits"), {"save": 1, "upload": 6, "signature": 1, "login": 0, "ocr": 0, "refresh": 1}),
            "OWNER_PROFILE_COUNTS_MISMATCH")
    return counts


def validate_predecessor(role, executable_plan, request, profile, evidence, mode, asset_root):
    """Read-only predecessor admission, before profile/native/context acquisition."""
    if role == "AUTHOR_SAVE":
        return
    require(role == "INDEPENDENT_REOPEN" and isinstance(profile, dict) and profile.get("mode") == mode and
            executable_plan["body_admission"] == "FROZEN_QUALIFIED_ROUTE_CODEC", "REOPEN_QUALIFIED_PREDECESSOR_REQUIRED")
    require(isinstance(evidence, dict) and isinstance(evidence.get("result"), dict) and
            evidence["result"].get("state") == ("APPLIED_SYNTHETIC_WIRE" if mode == "SYNTHETIC" else "READBACK_PENDING_INDEPENDENT") and
            evidence["result"].get("frames") == "PASS" and evidence["result"].get("content") == "VERIFIED" and
            evidence["question_id"] == profile["question_id"], "REOPEN_KNOWN_AUTHOR_SUCCESS_REQUIRED")
    inputs = evidence.get("frozen_author_inputs")
    require(isinstance(inputs, dict) and set(inputs) == {"plan", "baseline", "receipt", "author_observation", "release"},
            "REOPEN_FROZEN_AUTHOR_INPUTS_REQUIRED")
    plan, baseline, receipt, observed, release = (inputs[k] for k in ("plan", "baseline", "receipt", "author_observation", "release"))
    require(all(isinstance(v, dict) for v in (plan, baseline, receipt, observed, release)), "REOPEN_STRICT_RECEIPT_REQUIRED")
    payload = plan.get("payload")
    require(isinstance(payload, dict) and plan.get("input_hash") == digest(request) and plan.get("baseline") == baseline and
            plan.get("wire_profile_hash") == digest(profile), "REOPEN_AUTHOR_PLAN_BINDING")
    require(set(receipt) == {"code", "file_id", "platform_question_id", "question_order", "inserted", "rect_ids",
                             "response_hash", "payload_hash", "identity_source", "evidence_mode"} and
            type(receipt["code"]) is int and receipt["code"] in (0, 200) and str(receipt["file_id"]) == BOOK and
            receipt["identity_source"] == "SERVER_RESPONSE" and receipt["evidence_mode"] == mode and
            is_hash(receipt["response_hash"]) and receipt["payload_hash"] == digest(payload) and
            isinstance(receipt["platform_question_id"], str) and receipt["platform_question_id"] and
            type(receipt["question_order"]) is int and type(payload.get("insert_after_order")) is int and
            receipt["question_order"] > payload["insert_after_order"] and receipt["inserted"] is True and
            isinstance(receipt["rect_ids"], list) and len(receipt["rect_ids"]) == len(set(receipt["rect_ids"])) == 6 and
            sorted(receipt["rect_ids"]) == sorted(r["rect_id"] for r in payload["annotations_upsert"]), "REOPEN_STRICT_RECEIPT_REQUIRED")
    require(release.get("released") is True and release.get("evidence_mode") == mode and
            release.get("session_id") == profile["session"]["session_id"] == observed.get("session_id") and
            observed.get("phase") == "refresh" and observed.get("evidence_mode") == mode and
            release.get("profile_hash") == digest(profile) and release.get("plan_hash") == digest(plan) and
            release.get("receipt_hash") == digest(receipt) and release.get("last_observation_hash") == digest(observed),
            "REOPEN_AUTHOR_RELEASE_CHAIN_REQUIRED")
    resource = release.get("owner_release_evidence")
    require(isinstance(resource, dict) and set(resource) == {"path", "sha256", "media_type"} and
            resource["media_type"] == "application/json", "REOPEN_OUTER_CERTIFICATE_REQUIRED")
    root = Path(asset_root).resolve()
    path = (root/resource["path"]).resolve()
    require(root in path.parents and is_hash(resource["sha256"]), "REOPEN_OUTER_CERTIFICATE_REQUIRED")
    raw = path.read_bytes()
    require(sha(raw) == resource["sha256"], "REOPEN_OUTER_CERTIFICATE_HASH")
    certificate = parse(raw)
    subject = {k:v for k,v in release.items() if k != "owner_release_evidence"}
    require(certificate.get("schema") == "A24OwnedRelease/v1" and certificate.get("mode") == mode and
            certificate.get("issuer") == COORDINATOR and certificate.get("status") == "RELEASED" and
            certificate.get("subject_release_hash") == digest(subject) and
            certificate.get("author_result_hash") == digest(evidence["result"]) and
            certificate.get("context_closed") is True and certificate.get("runtime_stopped") is True and
            certificate.get("held_identities_released") is True and certificate.get("jobs_closed") is True and
            certificate.get("launcher_released") is True and type(certificate.get("pending_tasks")) is int and
            certificate["pending_tasks"] == 0 and isinstance(certificate.get("raw_evidence_refs"), list) and
            certificate["raw_evidence_refs"], "REOPEN_OUTER_RELEASE_UNPROVEN")
    for reference in certificate["raw_evidence_refs"]:
        read_ref(reference, [root])
