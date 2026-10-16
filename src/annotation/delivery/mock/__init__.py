"""A02 in-memory synthetic target and executor with independent readback.

No platform, browser, network, content recognition, persistence or reconciliation.
Keep the SAME instance alive for the whole simulation; a new process is A03's gap.
"""
import copy
import hashlib
import json
from pathlib import Path

from annotation.contracts import (
    artifact_ref, assert_plan_ready, content_digest, seal_artifact, validate_bundle,
)
from annotation.delivery.planner import encoded, frame_facts, verify_generated_plan
from annotation.quality.targetcheck import (
    append_artifacts, coverage_for, make_artifact, reject, resolve_artifact,
)

FAULTS = {"applied", "not_applied", "lost_response", "response_lost_readable",
          "readback_failure", "contradictory", "partial"}


class MockSession:
    """One serial writer; defensive-copy reads, append-only in-session history.

    UNKNOWN locks are keyed by book, independent of run/scope/question/action IDs.
    No unlock/reset/history-removal API is provided. This is not a crash-safe store.
    """

    def __init__(self):
        self._targets = {}
        self._log = []
        self._history = {}
        self._pending = set()
        self._used_plans = set()
        self._used_actions = set()
        self._serial = 0

    @property
    def action_log(self):
        return tuple(copy.deepcopy(self._log))

    def receipt_history(self, book_id):
        """Full immutable-by-copy bundles, including unresolved receipts and evidence refs."""
        return tuple(copy.deepcopy(self._history.get(book_id, [])))

    def is_paused(self, book_id):
        return book_id in self._pending or any(
            a["kind"] == "ExecutionReceipt" and a["book_id"] == book_id
            and any(r["outcome"] == "UNKNOWN" for r in a["payload"]["results"])
            for b in self._history.get(book_id, []) for a in b["artifacts"])

    def register_target(self, bundle, snapshot_ref, *, asset_root, source_ref=None):
        bundle = validate_bundle(bundle, asset_root=asset_root)
        snapshot = resolve_artifact(bundle, snapshot_ref, "PlatformSnapshot")
        if snapshot.producer.evidence_mode != "SYNTHETIC":
            reject("SYNTHETIC_ONLY", "mock target requires SYNTHETIC snapshot")
        if snapshot.book_id in self._targets:
            reject("TARGET_ALREADY_REGISTERED", "cannot replace target state or clear book history")
        if source_ref is None:
            sources = [a for a in bundle.artifacts if a.kind == "SourceBundle" and
                       a.book_id == snapshot.book_id and a.scope_id == snapshot.scope_id]
            if len(sources) != 1:
                reject("SOURCE_BINDING", "mock snapshot needs an explicit unambiguous image SourceBundle")
            source_ref = artifact_ref(sources[0])
        else:
            source_ref = artifact_ref(resolve_artifact(bundle, source_ref, "SourceBundle"))
        self._targets[snapshot.book_id] = {"base": snapshot.model_dump(mode="json"),
                                           "payload": snapshot.payload.model_dump(mode="json"),
                                           "source_ref": source_ref, "epoch": 0, "bindings": {}, "projections": {}}

    def _target(self, book_id):
        if book_id not in self._targets:
            reject("TARGET_NOT_REGISTERED", "register this synthetic book's snapshot first")
        return self._targets[book_id]

    def read_target(self, book_id):
        """Read target facts independently of execute() responses and planned expectations."""
        target = self._target(book_id)
        return copy.deepcopy({"provenance": "SYNTHETIC", "execution_mode": "SIMULATED",
                              "book_id": book_id, "epoch": target["epoch"],
                              "target": target["payload"], "internal_bindings": target["bindings"],
                              "frame_projections": target["projections"]})

    def read_snapshot(self, book_id):
        target = self._target(book_id)
        data = copy.deepcopy(target["base"])
        if not target["epoch"]:
            return data
        data["revision"] += target["epoch"]
        data["payload"] = copy.deepcopy(target["payload"])
        data["payload"]["observed_hash"] = content_digest(self.read_target(book_id))
        data["payload"]["observed_version"] = "a02-mock-epoch-" + str(target["epoch"])
        data["producer"].update(module="a02-mock", implementation_version="a02-1")
        data["input_refs"] = [r for r in data["input_refs"] if r["kind"] != "SourceBundle"] + [target["source_ref"]]
        return seal_artifact(data)

    def inject_external_change(self, book_id, *, platform_version=None):
        """Explicit synthetic outside-actor fault; never used to resolve a paused book."""
        target = self._target(book_id)
        if platform_version is not None:
            target["payload"]["platform_version"] = platform_version
        target["epoch"] += 1
        self._log.append({"event": "external_change", "book_id": book_id, "epoch": target["epoch"]})

    def _facts(self, action, view):
        before = action.expected_before
        directory = before["directory_id"]
        pid = action.target.platform_question_id
        if pid is None:
            pid = view["internal_bindings"].get(action.target.question_id)
        question = next((q for q in view["target"]["questions"] if q["platform_question_id"] == pid), None)
        frames = [f for f in view["target"]["frames"] if f["platform_question_id"] == pid] if question else []
        facts = {"question_exists": question is not None, "platform_question_id": pid,
                 "directory_id": question["directory_id"] if question else directory,
                 "frame_count": len(frames), "frames_hash": frame_facts(frames)}
        if "platform_order" in before:
            facts["platform_order"] = question["platform_order"] if question else None
        if "next_order" in before:
            facts["next_order"] = max([q["platform_order"] for q in view["target"]["questions"]
                                       if q["directory_id"] == directory] + [0]) + 1
        return facts

    def _write(self, book_id, action, partial=False):
        target = self._target(book_id)
        payload = target["payload"]
        pid = action.target.platform_question_id
        if pid is None:
            number = len(payload["questions"]) + 1
            existing = {q["platform_question_id"] for q in payload["questions"]}
            while "mock-question-" + str(number) in existing:
                number += 1
            pid = "mock-question-" + str(number)
            directory = action.expected_before["directory_id"]
            order = max([q["platform_order"] for q in payload["questions"] if q["directory_id"] == directory] + [0]) + 1
            payload["questions"].append({"platform_question_id": pid, "directory_id": directory, "platform_order": order})
        target["bindings"][action.target.question_id] = pid
        projected = json.loads(action.expected_after["frames"])
        if partial:
            projected = projected[:-1]
        for frame in projected:
            number = len(payload["frames"]) + 1
            existing = {f["platform_frame_id"] for f in payload["frames"]}
            while "mock-frame-" + str(number) in existing:
                number += 1
            fid = "mock-frame-" + str(number)
            payload["frames"].append({"platform_frame_id": fid, "platform_question_id": pid,
                                      "box": frame["box"], "platform_role": frame["platform_role"]})
            target["projections"][fid] = copy.deepcopy(frame)
        target["epoch"] += 1
        return {"status": "OK", "platform_question_id": pid}

    def _compare(self, action, before, readback):
        """Only evidence comparisons determine outcomes; response status is not an input."""
        if readback.get("read_status") != "OK":
            return "UNKNOWN", [], "readback unavailable or contradictory"
        after = readback["view"]
        pid = action.target.platform_question_id or after["internal_bindings"].get(action.target.question_id)
        question = next((q for q in after["target"]["questions"] if q["platform_question_id"] == pid), None)
        frames = [f for f in after["target"]["frames"] if f["platform_question_id"] == pid] if question else []
        projected = [after["frame_projections"].get(f["platform_frame_id"]) for f in frames]
        expected = action.expected_after
        if (question and question["directory_id"] == expected["directory_id"] and
                question["platform_order"] == expected["platform_order"] and
                encoded(projected) == expected["frames"] and frames and
                all(f["box"] == p["box"] and f["platform_role"] == p["platform_role"]
                    for f, p in zip(frames, projected))):
            return "APPLIED", [pid] + [f["platform_frame_id"] for f in frames], "independent target readback matches all projected frames"
        # A conclusive absence needs BOTH a known pre-state and an unchanged relevant target.
        facts_before, facts_after = self._facts(action, before), self._facts(action, after)
        if (facts_after == facts_before and
                facts_after["frame_count"] == 0):
            return "NOT_APPLIED", [], "explicit readback proves projected frames ABSENT and relevant target unchanged"
        return "UNKNOWN", [], "effect is partial, changed, or lacks a provable ABSENT baseline"

    def execute(self, bundle, plan_ref, config, *, asset_root, receipt_id, created_at, faults=None):
        """Execute once and return a validated bundle with a calculated receipt.

        lost_response = mutation plus unavailable readback (UNKNOWN).
        response_lost_readable = mutation plus lost response, complete readback (APPLIED).
        Remaining actions after a non-APPLIED result are read but never dispatched.
        """
        bundle = validate_bundle(bundle, asset_root=asset_root)
        plan = resolve_artifact(bundle, plan_ref, "ApplyPlan")
        book = plan.book_id
        if self.is_paused(book):
            reject("BOOK_WRITE_PAUSED", "same-book UNKNOWN/pending intent retained; A03 reconciliation interface required")
        plan_key = (book, plan.artifact_id, plan.revision)
        if plan_key in self._used_plans:
            reject("REPLAY_FORBIDDEN", "old plan was already attempted; recheck target and generate a new plan")
        faults = dict(faults or {})
        action_ids = {a.action_id for a in plan.payload.actions}
        if set(faults) - action_ids or any(f not in FAULTS for f in faults.values()):
            reject("INVALID_FAULT", "unknown action ID or unsupported synthetic fault")
        if any((book, a.action_id) in self._used_actions for a in plan.payload.actions):
            reject("REPLAY_FORBIDDEN", "an action ID in this book was already attempted")
        if any(a.artifact_id == receipt_id for a in bundle.artifacts):
            reject("DUPLICATE_ID", "receipt identity already exists")
        if plan.payload.readiness == "BLOCKED":
            receipt = make_artifact("ExecutionReceipt", receipt_id, plan,
                                    {"plan": artifact_ref(plan), "execution_mode": "NOT_EXECUTED", "results": [],
                                     "unresolved_issue_ids": plan.payload.blocked_issue_ids, "write_disposition": "NOT_EXECUTED"},
                                    [plan], config.version, "a02-mock", created_at)
            output = append_artifacts(bundle, receipt, asset_root=asset_root)
            self._history.setdefault(book, []).append(output.model_dump(mode="json"))
            self._used_plans.add(plan_key)
            return output
        current = self.read_snapshot(book)
        if not any(artifact_ref(a) == artifact_ref(current) for a in bundle.artifacts):
            bundle = append_artifacts(bundle, current, asset_root=asset_root)
        assert_plan_ready(bundle, artifact_ref(plan), artifact_ref(current))
        verify_generated_plan(bundle, plan, artifact_ref(current), config)
        self._used_plans.add(plan_key)
        self._used_actions.update((book, a.action_id) for a in plan.payload.actions)
        self._pending.add(book)  # Any exception after this point closes the in-session write gate.
        self._serial += 1
        serial = self._serial
        root = Path(asset_root)
        results, new_records, generated_issues = [], [], []
        stopped = False

        def record(label, value):
            # Immutable content-addressed bytes: same names may be safely referenced, never overwritten.
            raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
            digest = hashlib.sha256(raw).hexdigest()
            relative = "assets/a02-" + digest + ".json"
            path = root / relative
            try:
                path.resolve().relative_to(root.resolve())
            except ValueError:
                reject("EVIDENCE_PATH", "evidence path resolves outside exchange root")
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with path.open("xb") as handle:
                    handle.write(raw)
            except FileExistsError:
                if path.read_bytes() != raw:
                    reject("EVIDENCE_CONFLICT", "immutable evidence resource differs")
            identity = "proof-a02-" + str(serial) + "-" + label
            if any(e.evidence_id == identity for e in bundle.evidence):
                reject("DUPLICATE_ID", "evidence ID already exists; use one serial MockSession")
            resource = {"path": relative, "sha256": digest, "media_type": "application/json"}
            new_records.append({"evidence_id": identity, "resource": resource,
                                "description": "SYNTHETIC / SIMULATED independently captured " + label, "mode": "SYNTHETIC"})
            return identity, resource

        for index, action in enumerate(plan.payload.actions):
            before = self.read_target(book)
            before_id, _ = record(str(index) + "-before", before)
            fault = faults.get(action.action_id, "applied")
            precondition = self._facts(action, before) == action.expected_before
            dispatched = not stopped and precondition
            response = {"status": "NOT_DISPATCHED", "reason": "earlier action requires recheck/reconciliation" if stopped else "precondition mismatch"}
            if dispatched:
                self._used_actions.add((book, action.action_id))
                self._log.append({"event": "intent", "book_id": book, "plan": artifact_ref(plan),
                                  "action": action.model_dump(mode="json"), "before_evidence": before_id})
                response = {"status": "REJECTED"} if fault == "not_applied" else self._write(book, action, fault == "partial")
                if fault in ("lost_response", "response_lost_readable"):
                    response = {"status": "TIMEOUT"}
                self._log.append({"event": "response", "book_id": book, "action_id": action.action_id, "response": response})
            actual = self.read_target(book)
            readback = {"provenance": "SYNTHETIC", "execution_mode": "SIMULATED", "read_status": "OK", "view": actual}
            if dispatched and fault in ("lost_response", "readback_failure"):
                readback = {"provenance": "SYNTHETIC", "execution_mode": "SIMULATED", "read_status": "UNAVAILABLE"}
            elif dispatched and fault == "contradictory":
                alternate = copy.deepcopy(actual)
                alternate["target"]["frames"] = alternate["target"]["frames"][:-1]
                readback.update(read_status="CONTRADICTORY", second_view=alternate)
            after_id, resource = record(str(index) + "-readback", readback)
            outcome, ids, reason = self._compare(action, before, readback)
            # Precondition/dependency failures never gain APPLIED from unrelated state.
            if not dispatched and outcome == "APPLIED":
                outcome, ids, reason = "UNKNOWN", [], "not dispatched but effect already present; reconcile ownership"
            self._log.append({"event": "readback", "book_id": book, "action_id": action.action_id,
                              "dispatched": dispatched, "readback_evidence": after_id, "outcome": outcome})
            stopped = stopped or outcome != "APPLIED"
            if outcome == "UNKNOWN":
                generated_issues.append({"issue_id": "issue-a02-save-" + receipt_id + "-" + str(index),
                                         "code": "SAVE_UNKNOWN", "scope_type": "action", "scope_id": action.action_id,
                                         "evidence_refs": [before_id, after_id], "severity": "blocking", "blocks": ["APPLY", "COMPLETE"],
                                         "suggested_strategy": {"strategy_id": "RECONCILE", "max_attempts": 0, "max_cost": 0.0},
                                         "reason": reason + "; no ReconciliationResult in C01/A02; book remains paused"})
            results.append({"action_id": action.action_id, "outcome": outcome, "platform_ids": ids,
                            "before_evidence_refs": [before_id], "after_evidence_refs": [after_id], "readback": resource,
                            "effect_match": {"APPLIED": "MATCH", "NOT_APPLIED": "ABSENT", "UNKNOWN": "INDETERMINATE"}[outcome],
                            "next_step": {"APPLIED": "POSTCHECK", "NOT_APPLIED": "RECHECK_TARGET", "UNKNOWN": "RECONCILE"}[outcome],
                            "replay_allowed": False, "reason": reason})
        data = bundle.model_dump(mode="json")
        data["evidence"].extend(new_records)
        dependencies = [plan]
        # C01 stores Issue objects in CheckReport. This comparison report does NOT certify final content.
        if generated_issues:
            graph = resolve_artifact(bundle, plan.payload.graph, "QuestionGraph")
            coverage, _ = coverage_for(bundle, graph)
            comparison = make_artifact("CheckReport", "comparison-" + receipt_id, plan,
                                       {"stage": "POST_APPLY", "subject": {"artifact_id": receipt_id, "revision": 1,
                                        "kind": "ExecutionReceipt", "content_hash": "0" * 64},
                                        "graph": artifact_ref(graph), "policy": plan.payload.policy.model_dump(mode="json"),
                                        "snapshot": None, "receipt": {"artifact_id": receipt_id, "revision": 1,
                                        "kind": "ExecutionReceipt", "content_hash": "0" * 64},
                                        "coverage": coverage, "checks": [
                                            {"check_id": "frame_structure", "outcome": "UNAVAILABLE", "evidence_refs": [new_records[-1]["evidence_id"]],
                                             "reason": "SYNTHETIC readback cannot confirm every planned effect"},
                                            {"check_id": "final_content", "outcome": "UNAVAILABLE", "evidence_refs": [new_records[-1]["evidence_id"]],
                                             "reason": "A02 has no OCR/final-content checker"}],
                                        "issues": generated_issues, "decision": "HOLD", "reason": "SIMULATED unknown-effect comparison; no quality acceptance"},
                                       [plan, graph], config.version, "a02-mock-comparison", created_at)
        outcomes = {r["outcome"] for r in results}
        disposition = "PAUSE_RECONCILE" if "UNKNOWN" in outcomes else "RECHECK_TARGET" if "NOT_APPLIED" in outcomes else "POSTCHECK"
        receipt = make_artifact("ExecutionReceipt", receipt_id, plan,
                                {"plan": artifact_ref(plan), "execution_mode": "SIMULATED", "results": results,
                                 "unresolved_issue_ids": [i["issue_id"] for i in generated_issues], "write_disposition": disposition},
                                dependencies, config.version, "a02-mock", created_at)
        data["artifacts"].append(receipt)
        if generated_issues:
            # Build the report AFTER the receipt, avoiding an artificial cyclic dependency.
            comparison["payload"]["subject"] = artifact_ref(receipt)
            comparison["payload"]["receipt"] = artifact_ref(receipt)
            comparison["input_refs"].append(artifact_ref(receipt))
            data["artifacts"].append(seal_artifact(comparison))
        output = validate_bundle(data, asset_root=asset_root)
        self._history.setdefault(book, []).append(output.model_dump(mode="json"))
        self._log.append({"event": "receipt", "book_id": book, "receipt": artifact_ref(receipt),
                          "write_disposition": disposition})
        if disposition != "PAUSE_RECONCILE":
            self._pending.discard(book)
        return output
