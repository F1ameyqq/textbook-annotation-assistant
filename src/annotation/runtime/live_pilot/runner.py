"""Sequential A11 orchestration. Quality owns all question and projection rules."""
from dataclasses import replace

from annotation.delivery.live_pilot.plan import VERSION, create_live_plan, verify_plan
from annotation.delivery.live_pilot.usense import build_offline_command, parse_business_receipt, validate_offline_command
from annotation.quality.live_pilot import (PilotError, check_input, check_preservation, check_target,
    compare_saved, require, state_facts)
from annotation.runtime.storage.common import digest


def apply(request, asset_root, journal, transport, *, fault=None):
    require(journal.offline and transport.offline, "LIVE_CORE_BLOCKED")
    admission = check_input(request, asset_root, offline=True)
    hit = fault or (lambda point: None)
    with journal:
        journal.begin(admission.input_hash, [q["question_id"] for q in admission.questions])
        for fact in admission.questions:
            qid, intent = fact["question_id"], None
            result = {"question_id": qid, "state": "HOLD", "frames": "UNAVAILABLE", "content": "PENDING"}
            try:
                baseline = transport.observe("baseline")
                plan = create_live_plan(admission, request, qid, baseline)
                current = transport.observe("prewrite")
                check_target(replace(admission, questions=(fact,)), request, current, expected=baseline)
                require(current["read_sequence"] > baseline["read_sequence"] and
                        current["source_ref"] != baseline["source_ref"], "PREWRITE_NOT_FRESH")
                verify_plan(admission, request, plan, baseline)
                command = build_offline_command(plan)
                validate_offline_command(command)
                hit("before_intent")
                intent = journal.intent(qid, {"code_version": VERSION, "input_hash": admission.input_hash,
                    "approval_hash": admission.approval_hash, "policy": plan["policy"], "plan_hash": digest(plan),
                    "baseline_hash": digest(baseline), "payload_hash": digest(command),
                    "plan": plan, "baseline": baseline, "payload": command})
                hit("after_intent")
                journal.claim(qid, intent)
                hit("after_claim")
                raw = transport.send_once(command)
                hit("after_effect")
                hit("before_receipt")
                journal.append("BUSINESS_RECEIPT", {"question_id": qid, "raw": raw})
                pid = parse_business_receipt(raw, offline=True)
                previous = current
                for phase in ("get", "refresh", "reopen"):
                    observed = transport.observe(phase)
                    compared = compare_saved(plan, baseline, observed, phase=phase, previous=previous)
                    require(compared["platform_question_id"] == pid, "RECEIPT_IDENTITY_MISMATCH")
                    journal.append("READBACK", {"question_id": qid, "phase": phase,
                                              "observation": observed, "comparison": compared})
                    previous = observed
                result.update(state="APPLIED_OFFLINE", frames="PASS", content="VERIFIED",
                              independent_acceptance="PENDING", platform_fact="OFFLINE_ONLY")
            except Exception as exc:
                result.update(state="UNKNOWN" if intent is not None else "HOLD",
                              reason=getattr(exc, "code", type(exc).__name__))
            finally:
                try:
                    release = transport.close()
                    require(isinstance(release, dict) and release.get("released") is True, "RELEASE_UNPROVEN")
                except Exception as exc:
                    release = {"released": False, "reason": getattr(exc, "code", type(exc).__name__)}
                journal.append("RELEASE", dict(release, question_id=qid))
                if not release["released"]:
                    result.update(state="HOLD_RELEASE", release="UNPROVEN")
                journal.append("RESULT", result)
            if result["state"] != "APPLIED_OFFLINE":
                break
        return journal.report()


def reconcile_readonly(journal, transport, question_id):
    """One read only; UNKNOWN and NOT_RUN remain unchanged, including after MATCH/ABSENT."""
    require(journal.offline and transport.offline, "LIVE_READBACK_CODEC_UNAVAILABLE")
    with journal:
        events = journal.read()
        candidates = [e["data"] for e in events if e["kind"] == "INTENT" and e["data"]["question_id"] == question_id]
        require(len(candidates) == 1, "INTENT_REQUIRED")
        require(not any(e["kind"] == "RECONCILE_CLAIM" and e["data"]["question_id"] == question_id for e in events),
                "RECONCILE_ALREADY_USED")
        intent = candidates[0]
        journal.append("RECONCILE_CLAIM", {"question_id": question_id, "intent_hash": digest(intent)})
        result = {"question_id": question_id, "effect_match": "INDETERMINATE", "resend_allowed": False}
        try:
            observed = transport.observe("reconcile")
            baseline, plan = intent["baseline"], intent["plan"]
            pid = observed["view"]["internal_bindings"].get(question_id)
            check_preservation(baseline, observed, pid)
            require(observed.get("origin") == "FAKE_BACKEND_READ" and observed.get("source_ref") !=
                    baseline.get("source_ref") and observed["read_sequence"] > baseline["read_sequence"],
                    "READBACK_NOT_INDEPENDENT")
            if state_facts(observed) == state_facts(baseline):
                result["effect_match"] = "ABSENT"
            else:
                # Reconcile accepts a new readonly session but does not erase the prior UNKNOWN.
                previous = dict(baseline, session_id=observed["session_id"])
                compare_saved(plan, baseline, observed, phase="reconcile", previous=previous)
                result["effect_match"] = "MATCH"
            result["observation"] = observed
        except Exception as exc:
            result.update(effect_match="CONFLICT" if isinstance(exc, PilotError) else "INDETERMINATE",
                          reason=getattr(exc, "code", type(exc).__name__))
        finally:
            try:
                release = transport.close()
                if not isinstance(release, dict):
                    release = {"released": False, "reason": "RELEASE_UNPROVEN"}
                elif release.get("released") is not True:
                    release = dict(release, released=False)
                    release.setdefault("reason", "RELEASE_UNPROVEN")
            except Exception as exc:
                release = {"released": False, "reason": getattr(exc, "code", type(exc).__name__)}
            release = dict(release, question_id=question_id)
            journal.append("RECONCILE_RELEASE", release)
        apply_releases = [event["data"] for event in events if event["kind"] == "RELEASE"]
        result.update(apply_release=apply_releases[-1] if apply_releases else {"released": False},
                      reconcile_release=release, release=release,
                      status="REVIEW" if release["released"] is True else "HOLD",
                      write_disposition="HOLD", resend_allowed=False)
        journal.append("RECONCILIATION", result)
        return result
