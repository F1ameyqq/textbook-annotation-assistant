"""The sole structural authority for the C01 v1 exchange proposal (Python 3.9)."""
import math
import re
from datetime import datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0.0-a-proposal"
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")]
ExternalIdentifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")]
PositiveInt = Annotated[int, Field(gt=0)]
Nonnegative = Annotated[float, Field(ge=0)]
Kind = Literal["SourceBundle", "EvidenceBundle", "QuestionGraph", "PlatformSnapshot",
               "CheckReport", "ApplyPlan", "ExecutionReceipt", "ReviewPatch", "BatchReport"]
Role = Literal["stem", "option", "answer", "explanation", "shared_material"]
ContentType = Literal["text", "formula", "image", "table"]
Stage = Literal["PRE_APPLY", "TARGET", "POST_APPLY"]
Decision = Literal["PASS", "RETRY", "EXCEPTION", "HOLD"]
CapabilityName = Literal["persistent_draft", "frame_readback", "content_readback",
                         "ocr_before_submit", "resume_after_restart", "multi_session",
                         "same_session_handoff", "frame_update"]
FactValue = Union[str, int, float, bool, None]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


def relative_path(value: str) -> str:
    # Use a portable POSIX subset on every host; also reject Windows drives/UNC/ADS.
    if (not value or "\\" in value or ":" in value or "\x00" in value
            or PurePosixPath(value).is_absolute() or PureWindowsPath(value).drive
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise ValueError("resource path must be a portable relative path without traversal")
    if any(part.endswith((".", " ")) or re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", part, re.I)
           or any(c in part for c in '<>"|?*') or any(ord(c) < 32 for c in part)
           for part in value.split("/")):
        raise ValueError("resource path contains nonportable Windows path components")
    return value


class ArtifactRef(ContractModel):
    artifact_id: Identifier
    revision: PositiveInt
    kind: Kind
    content_hash: Digest


class PolicyRef(ContractModel):
    policy_id: Identifier
    revision: PositiveInt
    content_hash: Digest


class Producer(ContractModel):
    module: Identifier
    implementation_version: str = Field(min_length=1)
    config_version: str = Field(min_length=1)
    policy_versions: List[PolicyRef]
    model_version: Optional[str]
    prompt_version: Optional[str]
    evidence_mode: Literal["SYNTHETIC", "OBSERVED"]


class Envelope(ContractModel):
    schema_version: Literal["1.0.0-a-proposal"]
    artifact_id: Identifier
    revision: PositiveInt
    kind: Kind
    run_id: Identifier
    book_id: ExternalIdentifier
    scope_id: Identifier
    input_refs: List[ArtifactRef]
    producer: Producer
    content_hash: Digest
    created_at: str

    @field_validator("created_at")
    @classmethod
    def timestamp(cls, value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("expected ISO 8601 timestamp with timezone")
        if parsed.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return value


class Resource(ContractModel):
    path: str
    sha256: Digest
    media_type: Literal["image/png", "image/jpeg", "image/x-portable-graymap", "text/plain", "application/json"]

    _relative = field_validator("path")(relative_path)


class Asset(Resource):
    asset_id: Identifier
    width: PositiveInt
    height: PositiveInt
    source_label: str = Field(min_length=1)
    provenance: Literal["SYNTHETIC", "ORIGINAL"]


class ImageBinding(ContractModel):
    asset_id: Identifier
    width: PositiveInt
    height: PositiveInt
    sha256: Digest


class OriginalBox(ContractModel):
    image: ImageBinding
    bbox: List[float] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def bounds(self):
        x1, y1, x2, y2 = self.bbox
        if not all(math.isfinite(x) for x in self.bbox):
            raise ValueError("bbox requires finite original-image coordinates")
        if not (0 <= x1 < x2 <= self.image.width and 0 <= y1 < y2 <= self.image.height):
            raise ValueError("bbox must have positive area within bound original image")
        return self


class Directory(ContractModel):
    directory_id: Identifier
    parent_id: Optional[Identifier]
    label: str


class PageMapping(ContractModel):
    asset_id: Identifier
    directory_id: Identifier
    external_page: str
    mapping_status: Literal["CONFIRMED", "UNCERTAIN"]
    evidence_refs: List[Identifier] = Field(min_length=1)


class HistoryReference(ContractModel):
    resource: Resource
    quality: Literal["UNVERIFIED", "REVIEWED", "REJECTED"]
    reason: str = Field(min_length=1)


class SourcePayload(ContractModel):
    assets: List[Asset] = Field(min_length=1)
    directories: List[Directory] = Field(min_length=1)
    pages_expected: List[Identifier] = Field(min_length=1)
    pages_acquired: List[Identifier] = Field(min_length=1)
    external_page_mappings: List[PageMapping]
    history: List[HistoryReference]
    scope_manifest: List[Identifier] = Field(min_length=1)
    scope_manifest_basis: str = Field(min_length=1)
    metadata_page_count: Optional[PositiveInt]


class SourceBundle(Envelope):
    kind: Literal["SourceBundle"]
    payload: SourcePayload


class CropTransform(ContractModel):
    scale_x: float = Field(gt=0)
    scale_y: float = Field(gt=0)
    offset_x: float
    offset_y: float
    rotation_degrees: float
    padding: List[Nonnegative] = Field(min_length=4, max_length=4)
    processed_width: PositiveInt
    processed_height: PositiveInt
    invertible: bool


class Region(ContractModel):
    region_id: Identifier
    box: OriginalBox
    crop_transform: CropTransform
    content_type: ContentType
    text: Optional[str]
    source: Literal["SYNTHETIC", "OCR", "DETECTOR", "HUMAN", "HISTORICAL"]
    evidence_refs: List[Identifier] = Field(min_length=1)
    printed_number_candidates: List[str]
    certainty: Literal["CONFIRMED", "UNCERTAIN"]


class CoverageClue(ContractModel):
    clue_id: Identifier
    box: OriginalBox
    source: Literal["WHOLE_PAGE_SCAN", "INDEPENDENT_REVIEW", "SHARED_RECOGNITION", "SYNTHETIC"]
    disposition: Literal["ASSIGNED", "EXCLUDED", "UNASSIGNED"]
    region_ids: List[Identifier]
    reason: str = Field(min_length=1)
    evidence_refs: List[Identifier] = Field(min_length=1)


class EvidencePayload(ContractModel):
    source: ArtifactRef
    regions: List[Region]
    coverage_clues: List[CoverageClue] = Field(min_length=1)


class EvidenceBundle(Envelope):
    kind: Literal["EvidenceBundle"]
    payload: EvidencePayload


class ExternalRefs(ContractModel):
    printed_number: Optional[str]
    platform_question_id: Optional[str]
    platform_order: Optional[int]


class Fragment(ContractModel):
    fragment_id: Identifier
    region_ids: List[Identifier] = Field(min_length=1)
    role: Role
    content_type: ContentType
    reading_order: int = Field(ge=0)


class Question(ContractModel):
    question_id: Identifier
    directory_id: Identifier
    question_type: Literal["ordinary_choice", "free_response", "combination", "seven_choice", "unsupported"]
    fragment_ids: List[Identifier] = Field(min_length=1)
    parent_question_id: Optional[Identifier]
    shared_fragment_ids: List[Identifier]
    cross_page: bool
    external_refs: ExternalRefs


class AnswerRelation(ContractModel):
    relation_id: Identifier
    question_id: Identifier
    candidate_fragment_ids: List[Identifier]
    selected_fragment_ids: List[Identifier]
    status: Literal["SELECTED", "AMBIGUOUS", "UNRESOLVED"]
    evidence_refs: List[Identifier] = Field(min_length=1)


class GraphPayload(ContractModel):
    source: ArtifactRef
    evidence: ArtifactRef
    questions: List[Question] = Field(min_length=1)
    fragments: List[Fragment] = Field(min_length=1)
    answer_relations: List[AnswerRelation]
    identity_notes: str = Field(min_length=1)


class QuestionGraph(Envelope):
    kind: Literal["QuestionGraph"]
    payload: GraphPayload


class EvidenceRecord(ContractModel):
    evidence_id: Identifier
    resource: Resource
    description: str = Field(min_length=1)
    mode: Literal["SYNTHETIC", "OBSERVED"]


class Capability(ContractModel):
    name: CapabilityName
    status: Literal["VERIFIED", "UNKNOWN", "UNSUPPORTED"]
    platform_version: str = Field(min_length=1)
    evidence_refs: List[Identifier]

    @model_validator(mode="after")
    def proof(self):
        if self.status == "VERIFIED" and not self.evidence_refs:
            raise ValueError("VERIFIED capability requires evidence")
        return self


class PlatformQuestion(ContractModel):
    platform_question_id: str
    directory_id: str
    platform_order: int


class PlatformFrame(ContractModel):
    platform_frame_id: str
    platform_question_id: str
    box: OriginalBox
    platform_role: Literal["Q", "W", "A", "E"]


class SnapshotPayload(ContractModel):
    target_id: ExternalIdentifier
    platform_version: str = Field(min_length=1)
    observed_at: str
    observed_version: str = Field(min_length=1)
    observed_hash: Digest
    authorized_scope_id: Identifier
    directories: List[str]
    questions: List[PlatformQuestion]
    frames: List[PlatformFrame]
    capabilities: List[Capability]
    evidence_refs: List[Identifier] = Field(min_length=1)

    _timestamp = field_validator("observed_at")(Envelope.timestamp.__func__)


class PlatformSnapshot(Envelope):
    kind: Literal["PlatformSnapshot"]
    payload: SnapshotPayload


class Strategy(ContractModel):
    strategy_id: Literal["NONE", "LOAD_ADJACENT_PAGE", "EXPAND_CROP", "ADD_ANSWER_CONTEXT",
                         "SWITCH_RECOGNIZER", "HUMAN_REVIEW", "RECONCILE", "RECHECK_TARGET",
                         "WAIT_CONTENT", "HUMAN_SUBMIT", "LOGIN", "RAISE_BUDGET"]
    max_attempts: int = Field(ge=0)
    max_cost: Nonnegative


class Issue(ContractModel):
    issue_id: Identifier
    code: Literal["SOURCE_MISSING", "PAGE_MAPPING_UNCERTAIN", "UNASSIGNED_CONTENT", "CROSS_PAGE_OPEN",
                  "OPTION_INCOMPLETE", "ANSWER_AMBIGUOUS", "POLICY_UNRESOLVED", "UNSUPPORTED_LAYOUT",
                  "TARGET_CHANGED", "CONTENT_MISMATCH", "SAVE_UNKNOWN", "LOGIN_REQUIRED", "BUDGET_LIMIT"]
    scope_type: Literal["book", "scope", "page", "question", "fragment", "region", "action"]
    scope_id: ExternalIdentifier
    evidence_refs: List[Identifier] = Field(min_length=1)
    severity: Literal["blocking", "warning", "info"]
    blocks: List[Literal["PLAN", "APPLY", "COMPLETE"]]
    suggested_strategy: Strategy
    reason: str = Field(min_length=1)


class Coverage(ContractModel):
    scope_id: Identifier
    pages_expected: List[Identifier] = Field(min_length=1)
    pages_checked: List[Identifier]
    clue_ids: List[Identifier] = Field(min_length=1)
    unassigned_region_ids: List[Identifier]


CheckName = Literal["source_integrity", "structure", "answer_matching", "coverage", "policy",
                    "target_version", "authorized_scope", "capabilities", "frame_structure", "final_content"]


class CheckResult(ContractModel):
    check_id: CheckName
    outcome: Literal["PASS", "FAIL", "UNAVAILABLE"]
    evidence_refs: List[Identifier] = Field(min_length=1)
    reason: str = Field(min_length=1)


REQUIRED_CHECKS = {
    "PRE_APPLY": {"source_integrity", "structure", "answer_matching", "coverage", "policy"},
    "TARGET": {"target_version", "authorized_scope", "capabilities", "policy"},
    "POST_APPLY": {"frame_structure", "final_content"},
}


class CheckPayload(ContractModel):
    stage: Stage
    subject: ArtifactRef
    graph: ArtifactRef
    policy: PolicyRef
    snapshot: Optional[ArtifactRef]
    receipt: Optional[ArtifactRef]
    coverage: Coverage
    checks: List[CheckResult] = Field(min_length=1)
    issues: List[Issue]
    decision: Decision
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def decision_basis(self):
        names = [check.check_id for check in self.checks]
        if len(names) != len(set(names)):
            raise ValueError("duplicate check_id")
        if not REQUIRED_CHECKS[self.stage].issubset(names):
            raise ValueError("missing required checks for " + self.stage)
        if self.stage == "TARGET" and self.snapshot is None:
            raise ValueError("TARGET requires a snapshot version")
        if self.stage == "POST_APPLY" and self.receipt is None:
            raise ValueError("POST_APPLY requires a receipt version")
        if self.decision == "PASS":
            if any(check.outcome != "PASS" for check in self.checks) or any(i.blocks for i in self.issues):
                raise ValueError("PASS requires all checks PASS and no blocking issues")
            if set(self.coverage.pages_expected) != set(self.coverage.pages_checked) or self.coverage.unassigned_region_ids:
                raise ValueError("PASS requires complete page coverage without unassigned content")
        elif not self.issues:
            raise ValueError("non-PASS requires specific issues and evidence")
        if self.decision == "RETRY" and not any(i.suggested_strategy.max_attempts > 0 and
                i.suggested_strategy.strategy_id not in ("NONE", "HUMAN_REVIEW") for i in self.issues):
            raise ValueError("RETRY requires a bounded automatic remedy")
        return self


class CheckReport(Envelope):
    kind: Literal["CheckReport"]
    payload: CheckPayload


class ActionTarget(ContractModel):
    target_id: ExternalIdentifier
    question_id: Identifier
    platform_question_id: Optional[str]


class Action(ContractModel):
    action_id: Identifier
    target: ActionTarget
    source_entity_ids: List[Identifier] = Field(min_length=1)
    expected_before: Dict[str, FactValue] = Field(min_length=1)
    operation: Literal["CREATE_FRAMES", "UPDATE_FRAMES"]
    expected_after: Dict[str, FactValue] = Field(min_length=1)
    depends_on: List[Identifier]


class PlanPayload(ContractModel):
    graph: ArtifactRef
    precheck: ArtifactRef
    targetcheck: ArtifactRef
    snapshot: ArtifactRef
    policy: PolicyRef
    readiness: Literal["READY", "BLOCKED"]
    execution_mode: Literal["SIMULATED", "PLATFORM"]
    session_mode: Literal["PERSISTENT", "SAME_SESSION_HANDOFF"]
    required_capabilities: List[CapabilityName] = Field(min_length=1)
    actions: List[Action]
    blocked_issue_ids: List[Identifier]
    previous_receipt: Optional[ArtifactRef]
    final_submission: Literal["HUMAN_ONLY"]

    @model_validator(mode="after")
    def readiness_basis(self):
        if self.readiness == "READY" and (not self.actions or self.blocked_issue_ids):
            raise ValueError("READY requires actions and no blocked issues")
        if self.readiness == "BLOCKED" and (self.actions or not self.blocked_issue_ids):
            raise ValueError("BLOCKED is a diagnostic plan with no executable actions")
        return self


class ApplyPlan(Envelope):
    kind: Literal["ApplyPlan"]
    payload: PlanPayload


class ActionResult(ContractModel):
    action_id: Identifier
    outcome: Literal["APPLIED", "NOT_APPLIED", "UNKNOWN"]
    platform_ids: List[str]
    before_evidence_refs: List[Identifier] = Field(min_length=1)
    after_evidence_refs: List[Identifier]
    readback: Optional[Resource]
    effect_match: Literal["MATCH", "ABSENT", "INDETERMINATE"]
    next_step: Literal["POSTCHECK", "RECHECK_TARGET", "RECONCILE"]
    replay_allowed: Literal[False]
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def outcome_basis(self):
        expected = {"APPLIED": ("MATCH", "POSTCHECK"), "NOT_APPLIED": ("ABSENT", "RECHECK_TARGET"),
                    "UNKNOWN": ("INDETERMINATE", "RECONCILE")}
        if (self.effect_match, self.next_step) != expected[self.outcome]:
            raise ValueError("outcome/effect/next_step combination is inconsistent")
        if self.outcome != "UNKNOWN" and (not self.after_evidence_refs or self.readback is None):
            raise ValueError("conclusive outcome requires after evidence and readback")
        if self.outcome == "APPLIED" and not self.platform_ids:
            raise ValueError("APPLIED requires read-back platform identities")
        return self


class ReceiptPayload(ContractModel):
    plan: ArtifactRef
    execution_mode: Literal["SIMULATED", "PLATFORM_OBSERVED", "NOT_EXECUTED"]
    results: List[ActionResult]
    unresolved_issue_ids: List[Identifier]
    write_disposition: Literal["POSTCHECK", "RECHECK_TARGET", "PAUSE_RECONCILE", "NOT_EXECUTED"]


class ExecutionReceipt(Envelope):
    kind: Literal["ExecutionReceipt"]
    payload: ReceiptPayload


class PatchChange(ContractModel):
    entity_id: Identifier
    field: Literal["role", "printed_number", "selected_fragment_ids"]
    before: Union[str, List[Identifier], None]
    after: Union[str, List[Identifier], None]


class PatchPayload(ContractModel):
    baseline: ArtifactRef
    result_revision: PositiveInt
    changes: List[PatchChange] = Field(min_length=1)
    operator: Identifier
    reason: str = Field(min_length=1)
    related_issue_ids: List[Identifier]
    requires_recheck: Literal[True]


class ReviewPatch(Envelope):
    kind: Literal["ReviewPatch"]
    payload: PatchPayload


class QuestionStatus(ContractModel):
    question_id: Identifier
    state: Literal["PENDING", "VERIFIED", "EXCEPTION", "SKIPPED", "UNKNOWN"]
    reason: str = Field(min_length=1)


class Cost(ContractModel):
    model_calls: int = Field(ge=0)
    amount: Optional[Nonnegative]
    currency: str
    billing_status: Literal["KNOWN", "UNKNOWN"]
    human_minutes: Nonnegative

    @model_validator(mode="after")
    def unknown_cost(self):
        if (self.billing_status == "UNKNOWN") != (self.amount is None):
            raise ValueError("unknown billing must use null, known billing must use an amount")
        return self


class BatchPayload(ContractModel):
    source: ArtifactRef
    graph: ArtifactRef
    receipt: ArtifactRef
    postcheck: ArtifactRef
    scope_manifest: List[Identifier] = Field(min_length=1)
    questions: List[QuestionStatus] = Field(min_length=1)
    total_expected: PositiveInt
    coverage: Coverage
    cost: Cost
    unresolved_issue_ids: List[Identifier]
    submission_status: Literal["NOT_SUBMITTED", "CONFIRMED", "UNKNOWN"]
    submission_evidence_refs: List[Identifier]
    content_check_status: Literal["PENDING", "VERIFIED", "MISMATCH", "UNAVAILABLE"]
    frame_check_status: Literal["PASS", "FAIL", "UNAVAILABLE"]
    state: Literal["NEEDS_REVIEW", "NEEDS_RECONCILIATION", "CONTENT_PENDING",
                   "AWAITING_HUMAN_SUBMIT_FOR_OCR", "READY_FOR_SUBMISSION", "COMPLETED"]

    @model_validator(mode="after")
    def completion(self):
        if self.total_expected != len(self.scope_manifest):
            raise ValueError("denominator must retain every scoped question")
        if len(set(self.scope_manifest)) != len(self.scope_manifest):
            raise ValueError("scope_manifest contains duplicates")
        if {q.question_id for q in self.questions} != set(self.scope_manifest) or len(self.questions) != self.total_expected:
            raise ValueError("question statuses must include exceptions and skipped questions exactly once")
        if self.submission_status == "CONFIRMED" and not self.submission_evidence_refs:
            raise ValueError("confirmed submission requires independent observation evidence")
        if self.state in ("COMPLETED", "READY_FOR_SUBMISSION"):
            if (self.content_check_status != "VERIFIED" or self.frame_check_status != "PASS"
                    or self.unresolved_issue_ids or any(q.state != "VERIFIED" for q in self.questions)):
                raise ValueError("completion/readiness requires verified content, frames and all questions")
        if self.state == "COMPLETED" and self.submission_status != "CONFIRMED":
            raise ValueError("COMPLETED requires confirmed human submission")
        if self.state == "READY_FOR_SUBMISSION" and self.submission_status != "NOT_SUBMITTED":
            raise ValueError("READY_FOR_SUBMISSION requires NOT_SUBMITTED")
        if self.state in ("CONTENT_PENDING", "AWAITING_HUMAN_SUBMIT_FOR_OCR") and self.content_check_status != "PENDING":
            raise ValueError("content waiting state requires PENDING content")
        if self.state == "AWAITING_HUMAN_SUBMIT_FOR_OCR" and self.submission_status != "NOT_SUBMITTED":
            raise ValueError("human-submit waiting state requires NOT_SUBMITTED")
        return self


class BatchReport(Envelope):
    kind: Literal["BatchReport"]
    payload: BatchPayload


Artifact = Annotated[Union[SourceBundle, EvidenceBundle, QuestionGraph, PlatformSnapshot, CheckReport,
                           ApplyPlan, ExecutionReceipt, ReviewPatch, BatchReport], Field(discriminator="kind")]


class PlatformPolicy(ContractModel):
    policy_id: Identifier
    revision: PositiveInt
    content_hash: Digest
    confirmation_status: Literal["UNRESOLVED", "A_INTERNAL_PROPOSAL", "JOINT_CONFIRMED", "SYNTHETIC_ASSUMPTION"]
    option_grouping: Literal["UNRESOLVED", "SEPARATE", "COMBINED"]
    role_mapping: Dict[Role, Literal["Q", "W", "A", "E"]]
    source_notes: List[str] = Field(min_length=1)
    frame_save_status: Literal["UNVERIFIED", "BOUNDED_A05_OBSERVED", "SYNTHETIC"]
    ocr_status: Literal["UNVERIFIED", "VERIFIED", "SYNTHETIC"]
    applicability: Literal["PROPOSAL_ONLY", "SYNTHETIC_ONLY", "JOINT_CONFIRMED"]


class ExchangeBundle(ContractModel):
    format_version: Literal["c01-exchange-1"]
    evidence: List[EvidenceRecord] = Field(min_length=1)
    policies: List[PlatformPolicy] = Field(min_length=1)
    artifacts: List[Artifact] = Field(min_length=1)
