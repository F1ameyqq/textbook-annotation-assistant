"""Sequential A11 orchestration. Quality owns all question and projection rules."""
from dataclasses import replace

from annotation.delivery.live_pilot.plan import VERSION, create_live_plan, verify_plan
from annotation.delivery.live_pilot.usense import build_offline_command, parse_business_receipt, validate_offline_command
from annotation.quality.live_pilot import (PilotError, check_input, check_preservation, check_target,
    compare_saved, require, state_facts)
from annotation.runtime.storage.common import digest


async def apply_current_context(request, asset_root, *, page, context, guard, binding, owner_authority=None):
    """Concrete PLATFORM entry on a separately activated, already owned context.

    No context acquisition, credentials, native/OS launch or old budget reset.
    The caller retains responsibility for launcher/runtime release evidence.
    """
    import asyncio
    from annotation.delivery.live_pilot.usense import CurrentPageIO, UsenseTransport
    from annotation.runtime.live_pilot.journal import Journal
    from annotation.runtime.live_pilot.authority import Authority
    from annotation.runtime.live_pilot.private_payload import ControlledVault
    require(type(owner_authority) is Authority, "VALIDATED_OWNER_AUTHORITY_REQUIRED")
    owner_authority.check()
    require(owner_authority.role == "AUTHOR_SAVE" and binding.get("owner_authority_hash") == owner_authority.raw_hash and
            getattr(guard, "owner_authority_hash", None) == owner_authority.raw_hash,
            "VALIDATED_OWNER_AUTHORITY_REQUIRED")
    require(binding.get("mode") == "AUTHOR_SAVE" and binding.get("request_hash") == digest(request) and binding.get("executor") ==
            "01a15cf8-0c63-70d3-b374-ce85e6f29fd7" and binding.get("activated") is True and
            binding.get("evidence_mode") == owner_authority.data["mode"] and binding.get("profile_hash") ==
            request["approval"].get("wire_profile_hash"), "FIRST_SAVE_ACTIVATION_REQUIRED")
    io = CurrentPageIO(page, context, guard, asyncio.get_running_loop(), binding, synthetic=owner_authority.synthetic, owner_authority=owner_authority)
    journal = Journal(owner_authority.output / "synthetic-journal", offline=True) if owner_authority.synthetic else Journal()
    return await asyncio.to_thread(apply, request, asset_root, journal, UsenseTransport(io), private_vault=ControlledVault(owner_authority))


async def reopen_current_context(request, asset_root, *, page, context, guard, binding, owner_authority=None, **frozen_author_inputs):
    """Concrete readonly entry for the designated independent new context."""
    import asyncio
    from annotation.delivery.live_pilot.usense import CurrentPageIO, UsenseTransport
    from annotation.runtime.live_pilot.authority import Authority
    require(type(owner_authority) is Authority, "VALIDATED_OWNER_AUTHORITY_REQUIRED")
    owner_authority.check()
    require(owner_authority.role == "INDEPENDENT_REOPEN" and binding.get("owner_authority_hash") == owner_authority.raw_hash and
            getattr(guard, "owner_authority_hash", None) == owner_authority.raw_hash, "VALIDATED_OWNER_AUTHORITY_REQUIRED")
    require(binding.get("request_hash") == digest(request) and binding.get("mode") == "READONLY_REOPEN" and
            binding.get("activated") is True and binding.get("evidence_mode") == owner_authority.data["mode"] and
            binding.get("profile_hash") == request["approval"].get("wire_profile_hash"), "READONLY_REOPEN_ACTIVATION_REQUIRED")
    io = CurrentPageIO(page, context, guard, asyncio.get_running_loop(), binding, synthetic=owner_authority.synthetic, owner_authority=owner_authority)
    result = await asyncio.to_thread(independent_reopen, request, asset_root, UsenseTransport(io, readonly=True),
                                    **frozen_author_inputs)
    if "observation" in result:
        from annotation.runtime.live_pilot.private_payload import ControlledVault
        result["observation_ref"] = ControlledVault(owner_authority).freeze("reopen",
            owner_authority.schema_profile["question_id"], result.pop("observation"))
    return result


def apply(request, asset_root, journal, transport, *, fault=None, private_vault=None):
    """Release an injected lease also on admission/lock/already-started failures."""
    try:
        return _apply(request, asset_root, journal, transport, fault=fault, private_vault=private_vault)
    except BaseException as exc:
        if getattr(transport, "wire_enabled", False) and not transport._closed:
            try:
                transport.close()
            except Exception as release_error:
                exc.release_failure = getattr(release_error, "code", type(release_error).__name__)
        raise


def _apply(request, asset_root, journal, transport, *, fault=None, private_vault=None):
    wire = transport if getattr(transport, "wire_enabled", False) else None
    require(wire is not None or journal.offline and transport.offline, "LIVE_CORE_BLOCKED")
    admission = check_input(request, asset_root, offline=journal.offline, wire=wire)
    hit = fault or (lambda point: None)
    with journal:
        journal.begin(admission.input_hash, [q["question_id"] for q in admission.questions])
        for fact in admission.questions:
            qid, intent = fact["question_id"], None
            plan = baseline = receipt = previous = None
            result = {"question_id": qid, "state": "HOLD", "frames": "UNAVAILABLE", "content": "PENDING"}
            try:
                baseline = transport.observe("baseline")
                plan = create_live_plan(admission, request, qid, baseline)
                current = transport.observe("prewrite")
                check_target(replace(admission, questions=(fact,)), request, current, expected=baseline)
                require(current["read_sequence"] > baseline["read_sequence"] and
                        current["source_ref"] != baseline["source_ref"], "PREWRITE_NOT_FRESH")
                verify_plan(admission, request, plan, baseline)
                command = wire.build_commit(plan) if wire is not None else build_offline_command(plan)
                if wire is None:
                    validate_offline_command(command)
                hit("before_intent")
                full_intent = {"code_version": plan["version"], "input_hash": admission.input_hash,
                    "approval_hash": admission.approval_hash, "policy": plan["policy"], "plan_hash": digest(plan),
                    "baseline_hash": digest(baseline), "payload_hash": digest(command),
                    "plan": plan, "baseline": baseline, "payload": command}
                stored_intent = full_intent
                if private_vault is not None:
                    reference = private_vault.freeze("intent", qid, full_intent)
                    stored_intent = {k: v for k, v in full_intent.items() if k not in ("plan", "baseline", "payload")}
                    stored_intent["private_intent_ref"] = reference
                intent = journal.intent(qid, stored_intent)
                hit("after_intent")
                journal.claim(qid, intent)
                hit("after_claim")
                if wire is not None:
                    wire.arm(journal, qid, intent)
                    wire.upload_crops_once(journal, qid)
                raw = transport.send_once(command)
                hit("after_effect")
                hit("before_receipt")
                try:
                    receipt = parse_business_receipt(raw, offline=journal.offline, transport=wire)
                except Exception as receipt_error:
                    # Unapproved response members never enter the generic ledger,
                    # including when decoding fails after a possible effect.
                    journal.append("BUSINESS_RECEIPT", {"question_id": qid, "status": "UNKNOWN",
                        "response_hash": digest(raw), "payload_hash": digest(command),
                        "reason": getattr(receipt_error, "code", type(receipt_error).__name__)})
                    raise
                journal.append("BUSINESS_RECEIPT", {"question_id": qid, "status": "STRICT_DECODED",
                    "receipt": receipt, "response_hash": digest(raw), "payload_hash": digest(command)})
                pid = receipt["platform_question_id"] if wire is not None else receipt
                if wire is not None:
                    journal.append("STRICT_RECEIPT", {"question_id": qid, "receipt": receipt})
                previous = current
                for phase in (("get", "refresh") if wire is not None else ("get", "refresh", "reopen")):
                    observed = transport.observe(phase)
                    compared = compare_saved(plan, baseline, observed, phase=phase, previous=previous,
                                             wire=wire, receipt=receipt if wire is not None else None)
                    require(compared["platform_question_id"] == pid, "RECEIPT_IDENTITY_MISMATCH")
                    readback = {"question_id": qid, "phase": phase, "comparison": compared}
                    readback["observation_ref" if private_vault is not None else "observation"] = (
                        private_vault.freeze(phase, qid, observed) if private_vault is not None else observed)
                    journal.append("READBACK", readback)
                    previous = observed
                state = ("APPLIED_SYNTHETIC_WIRE" if journal.offline else "READBACK_PENDING_INDEPENDENT") if wire else "APPLIED_OFFLINE"
                result.update(state=state, frames="PASS", content="VERIFIED", independent_acceptance="PENDING",
                              platform_fact="OFFLINE_ONLY" if journal.offline else "AUTHOR_READBACK_ONLY")
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
                if private_vault is not None and intent is not None:
                    private_vault.author_evidence_ref = private_vault.freeze("author-evidence", qid, {
                        "frozen_author_inputs": {"plan": plan, "baseline": baseline, "receipt": receipt,
                            "author_observation": previous, "release": dict(release, question_id=qid)},
                        "original_intent_ref": intent["private_intent_ref"], "question_id": qid,
                        "result": result, "independent_acceptance": "PENDING"})
            if result["state"] != "APPLIED_OFFLINE":
                break
        report = journal.report()
        if private_vault is not None:
            report["private_author_evidence_ref"] = private_vault.author_evidence_ref
        return report


def independent_reopen(request, asset_root, transport, *, plan, baseline, receipt, author_observation, release):
    """Designated reviewer entry, after author release; never calls a sender.

    Returns evidence for formal review, not independent acceptance. No author
    journal mutation and no reopening or clearing an UNKNOWN claim.
    """
    require(getattr(transport, "wire_enabled", False) and transport.readonly, "INDEPENDENT_READER_REQUIRED")
    mode = getattr(transport._session, "offline", None)
    require(type(mode) is bool, "IO_PROVENANCE_REQUIRED")
    check_input(request, asset_root, offline=mode, wire=transport)
    result = {"status": "HOLD", "independent_acceptance": "PENDING", "resend_allowed": False}
    try:
        if not transport.offline:
            from annotation.delivery.live_pilot.wire import verify_owner_release
            verify_owner_release(release, asset_root)
        require(plan["input_hash"] == digest(request) and plan["baseline"] == baseline and
                author_observation["phase"] == "refresh" and author_observation["session_id"] == release["session_id"] and
                author_observation["evidence_mode"] == transport.profile["mode"] and
                release.get("last_observation_hash") == digest(author_observation) and
                release.get("plan_hash") == digest(plan) and release.get("receipt_hash") == digest(receipt),
                "REOPEN_INPUT_BINDING")
        transport.resume_readonly(plan, receipt, release)
        observed = transport.observe("reopen")
        compared = compare_saved(plan, baseline, observed, phase="reopen", previous=author_observation,
                                 wire=transport, receipt=receipt)
        result.update(status="REVIEW", observation=observed, comparison=compared)
    except Exception as exc:
        result["reason"] = getattr(exc, "code", type(exc).__name__)
    finally:
        try:
            closed = transport.close()
            require(closed.get("released") is True, "RELEASE_UNPROVEN")
        except Exception as exc:
            closed = {"released": False, "reason": getattr(exc, "code", type(exc).__name__)}
            result["status"] = "HOLD"
        result["release"] = closed
    return result


def reconcile_readonly(journal, transport, question_id, *, request=None, asset_root=None, private_vault=None):
    """One read only; UNKNOWN and NOT_RUN remain unchanged, including after MATCH/ABSENT."""
    wire = transport if getattr(transport, "wire_enabled", False) else None
    if wire is not None:
        require(wire.readonly and request is not None and asset_root is not None, "READONLY_RECONCILE_INPUTS_REQUIRED")
        check_input(request, asset_root, offline=journal.offline, wire=wire)
    else:
        require(journal.offline and transport.offline, "LIVE_READBACK_CODEC_UNAVAILABLE")
    with journal:
        events = journal.read()
        candidates = [e["data"] for e in events if e["kind"] == "INTENT" and e["data"]["question_id"] == question_id]
        require(len(candidates) == 1, "INTENT_REQUIRED")
        require(not any(e["kind"] == "RECONCILE_CLAIM" and e["data"]["question_id"] == question_id for e in events),
                "RECONCILE_ALREADY_USED")
        from annotation.runtime.live_pilot.private_payload import resolve_intent
        stored_intent = candidates[0]
        intent = resolve_intent(stored_intent, private_vault)
        receipt = None
        if wire is not None:
            require(intent["input_hash"] == digest(request), "RECONCILE_INPUT_BINDING")
            receipts = [e["data"]["receipt"] for e in events if e["kind"] == "STRICT_RECEIPT" and
                        e["data"]["question_id"] == question_id]
            releases = [e["data"] for e in events if e["kind"] == "RELEASE" and e["data"]["question_id"] == question_id]
            require(len(releases) == 1 and releases[0].get("released") is True, "REOPEN_CHAIN")
            receipt = receipts[0] if len(receipts) == 1 else None
            if receipt is not None:
                wire.resume_readonly(intent["plan"], receipt, releases[0])
            else:
                wire.resume_reconcile(intent["plan"], releases[0])
        journal.append("RECONCILE_CLAIM", {"question_id": question_id, "intent_hash": digest(stored_intent)})
        result = {"question_id": question_id, "effect_match": "INDETERMINATE", "resend_allowed": False}
        try:
            observed = transport.observe("reconcile")
            baseline, plan = intent["baseline"], intent["plan"]
            pid = observed["view"]["internal_bindings"].get(question_id)
            check_preservation(baseline, observed, pid)
            if wire is not None:
                wire.verify_observation(observed, "reconcile")
            else:
                require(observed.get("origin") == "FAKE_BACKEND_READ" and observed.get("source_ref") !=
                        baseline.get("source_ref") and observed["read_sequence"] > baseline["read_sequence"],
                        "READBACK_NOT_INDEPENDENT")
            if state_facts(observed) == state_facts(baseline):
                result["effect_match"] = "ABSENT"
            elif wire is None or receipt is not None:
                # Reconcile accepts a new readonly session but does not erase the prior UNKNOWN.
                previous = dict(baseline, session_id=observed["session_id"])
                compare_saved(plan, baseline, observed, phase="reconcile", previous=previous, wire=wire, receipt=receipt)
                result["effect_match"] = "MATCH"
            else:
                result.update(effect_match="INDETERMINATE", reason="STRICT_RECEIPT_ABSENT_NO_IDENTITY_INFERENCE")
            result["observation_ref" if private_vault is not None else "observation"] = (
                private_vault.freeze("reconcile", question_id, observed) if private_vault is not None else observed)
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
