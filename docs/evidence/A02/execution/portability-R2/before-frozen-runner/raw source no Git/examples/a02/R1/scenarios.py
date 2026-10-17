"""R1 author matrix. Full legal multi-book bundles retained, all SYNTHETIC/SIMULATED."""
import copy
import json
from pathlib import Path
import traceback

from annotation.contracts import (
    ContractError, artifact_ref, assert_plan_ready, load_bundle, policy_ref,
    seal_artifact, validate_bundle, write_bundle,
)
from annotation.delivery.mock import MockSession
from annotation.delivery.planner import create_plan
from annotation.quality.targetcheck import SimulationConfig, check_target

TIME = "2026-10-16T00:00:00Z"


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def copy_assets(fixture, output):
    destination = output / "assets"
    destination.mkdir(parents=True, exist_ok=True)
    # Copy every REFERENCED resource; unused C01 readback examples need not collide
    # with unused A02 companion files. No registered evidence/artifact is removed.
    resources = set()

    def visit(value):
        if isinstance(value, dict):
            if {"path", "sha256", "media_type"}.issubset(value):
                resources.add(value["path"])
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(load_bundle(fixture / "input.json").model_dump(mode="json"))
    for source in (fixture / "assets").iterdir():
        if source.is_file() and "assets/" + source.name in resources:
            path = destination / source.name
            if path.exists():
                assert path.read_bytes() == source.read_bytes(), "shared resource bytes differ"
            else:
                with path.open("xb") as handle:
                    handle.write(source.read_bytes())


def clone_input(fixture, output, book, tag, *, scope=None, new_question=False):
    """Rebind explicit immutable identities, not printed numbers or target effects."""
    copy_assets(fixture, output)
    data = load_bundle(fixture / "input.json").model_dump(mode="json")
    changed = {}

    def refs(value):
        if isinstance(value, list):
            return [refs(item) for item in value]
        if isinstance(value, dict):
            if set(value) == {"artifact_id", "revision", "kind", "content_hash"}:
                return copy.deepcopy(changed.get((value["artifact_id"], value["revision"]), value))
            return {key: refs(item) for key, item in value.items()}
        return value

    for index, original in enumerate(data["artifacts"]):
        item = refs(original)
        old_book, old_scope = item["book_id"], item["scope_id"]
        item.update(artifact_id="r1-" + tag + "-" + original["artifact_id"], book_id=book, run_id="r1-run-" + tag)
        if scope is not None:
            item["scope_id"] = scope
            if "coverage" in item["payload"]:
                item["payload"]["coverage"]["scope_id"] = scope
        for issue in item["payload"].get("issues", []):
            if issue["scope_type"] == "book" and issue["scope_id"] == old_book:
                issue["scope_id"] = book
            if scope is not None and issue["scope_type"] == "scope" and issue["scope_id"] == old_scope:
                issue["scope_id"] = scope
        if item["kind"] == "PlatformSnapshot":
            item["payload"]["target_id"] = "target-" + book
            if scope is not None:
                item["payload"]["authorized_scope_id"] = scope
        if item["kind"] == "ApplyPlan":
            for action in item["payload"]["actions"]:
                action["target"]["target_id"] = "target-" + book
        if new_question and item["kind"] == "SourceBundle":
            item["payload"]["scope_manifest"][0] = "question-r1-different"
        if new_question and item["kind"] == "QuestionGraph":
            item["payload"]["questions"][0]["question_id"] = "question-r1-different"
            item["payload"]["answer_relations"][0]["question_id"] = "question-r1-different"
        sealed = seal_artifact(item)
        data["artifacts"][index] = sealed
        changed[(original["artifact_id"], original["revision"])] = artifact_ref(sealed)
    return validate_bundle(data, asset_root=output)


def own_input(source, output, book, tag, case="normal", **kwargs):
    fixture = Path(source) / "tests/fixtures/a02" / case
    bundle = clone_input(fixture, output, book, tag, **kwargs)
    data = json.loads((fixture / "config.json").read_text(encoding="utf-8"))
    data.update(book_id=book, target_id="target-" + book)
    if kwargs.get("scope") is not None:
        data["scope_id"] = kwargs["scope"]
    data["allowed_operations"] = tuple(data["allowed_operations"])
    return bundle, SimulationConfig(**data)


def merge(output, *bundles):
    result = {"format_version": "c01-exchange-1", "artifacts": [], "policies": [], "evidence": []}
    registries = {"artifacts": {}, "policies": {}, "evidence": {}}
    for bundle in bundles:
        data = bundle.model_dump(mode="json")
        for name in registries:
            for item in data[name]:
                key = ((item["artifact_id"], item["revision"]) if name == "artifacts" else
                       (item["policy_id"], item["revision"]) if name == "policies" else item["evidence_id"])
                if key in registries[name]:
                    assert registries[name][key] == item, "immutable registry collision"
                else:
                    registries[name][key] = item
                    result[name].append(item)
    return validate_bundle(result, asset_root=output)


def prepare(inputs, config, output, tag, foreign=None):
    bundle = merge(output, inputs, foreign) if foreign is not None else inputs
    graph = next(a for a in inputs.artifacts if a.kind == "QuestionGraph")
    snapshot = next(a for a in inputs.artifacts if a.kind == "PlatformSnapshot")
    pre = next(a for a in inputs.artifacts if a.kind == "CheckReport" and a.payload.stage == "PRE_APPLY")
    pref = policy_ref(inputs.policies[0])
    bundle = check_target(bundle, artifact_ref(graph), artifact_ref(snapshot), artifact_ref(snapshot), pref, config,
                          artifact_id="r1-target-" + tag, created_at=TIME)
    bundle = create_plan(bundle, artifact_ref(graph), artifact_ref(pre), artifact_ref(bundle.artifacts[-1]),
                         artifact_ref(snapshot), artifact_ref(snapshot), pref, config,
                         artifact_id="r1-plan-" + tag, created_at=TIME)
    plan = bundle.artifacts[-1]
    if plan.payload.readiness == "READY":
        assert_plan_ready(bundle, artifact_ref(plan), artifact_ref(snapshot))
    return bundle, plan, snapshot


def execute(session, bundle, plan, config, output, tag, fault="applied"):
    faults = {plan.payload.actions[0].action_id: fault} if plan.payload.actions else {}
    result = session.execute(bundle, artifact_ref(plan), config, asset_root=output,
                             receipt_id="r1-receipt-" + tag, created_at=TIME, faults=faults)
    receipt = next(a for a in result.artifacts if a.artifact_id == "r1-receipt-" + tag)
    write_bundle(result, output / (tag + "-receipt.json"))
    return result, receipt


def capture(output, tag, session, books):
    value = {"provenance": "SYNTHETIC", "execution_mode": "SIMULATED",
             "pause": {book: session.is_paused(book) for book in books},
             "targets": {book: session.read_target(book) for book in books},
             "action_log": session.action_log,
             "receipt_history": {book: session.receipt_history(book) for book in books}}
    write_json(output / (tag + "-state-log-history.json"), value)
    return value


def rejected(code, action):
    try:
        action()
    except ContractError as error:
        assert code in {i["code"] for i in error.issues}, error
        return error.issues
    raise AssertionError("expected rejection " + code)


def crossbook(source, output, book="book-alpha", foreign_book="book-beta", mode="diagnostic"):
    """Exact defect shape plus conclusive receipt variants, with the full foreign chain."""
    output.mkdir(parents=True, exist_ok=False)
    foreign = clone_input(Path(source) / "tests/fixtures/contracts/unknown", output, foreign_book, "foreign")
    inputs, config = own_input(source, output, book, "own")
    ready, plan, snapshot = prepare(inputs, config, output, "ready", foreign)
    write_bundle(ready, output / "ready-planned.json")
    session = MockSession()
    session.register_target(ready, artifact_ref(snapshot), asset_root=output)
    before = capture(output, "before", session, [book])
    initial = ready
    initial_plan = plan
    if mode == "diagnostic":
        diagnostic, diagnostic_config = own_input(source, output, book, "diagnostic", "exceptions")
        initial, initial_plan, _ = prepare(diagnostic, diagnostic_config, output, "diagnostic", foreign)
        write_bundle(initial, output / "diagnostic-planned.json")
        initial, receipt = execute(session, initial, initial_plan, diagnostic_config, output, "diagnostic")
        assert receipt.payload.execution_mode == "NOT_EXECUTED" and not receipt.payload.results
        mid = capture(output, "after-diagnostic", session, [book])
        assert not session.is_paused(book), "FOREIGN_UNKNOWN_FALSELY_PAUSES_OTHER_BOOK"
        assert before["targets"] == mid["targets"] and not session.action_log
    else:
        initial, receipt = execute(session, initial, plan, config, output, "initial", mode)
        mid = capture(output, "after-initial", session, [book])
        assert not session.is_paused(book), "foreign UNKNOWN contaminated conclusive own receipt"
        expected = "NOT_APPLIED" if mode == "not_applied" else "APPLIED"
        assert all(r.outcome == expected and not r.replay_allowed for r in receipt.payload.results)
        rejected("REPLAY_FORBIDDEN", lambda: execute(session, ready, plan, config, output, "replay"))
    foreign_refs = {a.content_hash for a in foreign.artifacts}
    history = session.receipt_history(book)
    assert all(foreign_refs.issubset({a["content_hash"] for a in b["artifacts"]}) for b in history)
    assert any(a["kind"] == "ExecutionReceipt" and a["book_id"] == foreign_book and
               any(r["outcome"] == "UNKNOWN" for r in a["payload"]["results"])
               for b in history for a in b["artifacts"]), "foreign UNKNOWN history lost"
    if mode == "not_applied":
        ready, plan, _ = prepare(inputs, config, output, "fresh-after-absent", initial)
        write_bundle(ready, output / "fresh-after-absent-planned.json")
    if mode != "applied":
        final, receipt = execute(session, ready, plan, config, output, "ready")
        assert [r.outcome for r in receipt.payload.results] == ["APPLIED"] * 3
        assert all(r.platform_ids for r in receipt.payload.results)
    state = capture(output, "final", session, [book])
    assert not session.is_paused(book)
    assert len(state["targets"][book]["target"]["questions"]) == 3
    assert len(state["targets"][book]["target"]["frames"]) == 9
    assert all(b["artifacts"] for b in session.receipt_history(book))
    return {"book": book, "foreign_book": foreign_book, "mode": mode, "foreign_unknown_retained": True,
            "pause_after_history": False, "target_questions": 3, "target_frames": 9,
            "history_count": len(session.receipt_history(book)), "public_ready_gate_passed": True}


def two_books(source, output, first="book-alpha", second="book-beta", second_fault="lost_response", mixed=True):
    """Real in-session UNKNOWN in book one; isolated or mixed book two remains independent."""
    output.mkdir(parents=True, exist_ok=False)
    session = MockSession()
    inputs, config = own_input(source, output, first, "first")
    bundle, plan, snapshot = prepare(inputs, config, output, "first")
    session.register_target(bundle, artifact_ref(snapshot), asset_root=output)
    first_result, first_receipt = execute(session, bundle, plan, config, output, "first", "lost_response")
    assert first_receipt.payload.results[0].outcome == "UNKNOWN" and session.is_paused(first)
    first_history = session.receipt_history(first)
    second_inputs, second_config = own_input(source, output, second, "second")
    second_bundle, second_plan, second_snapshot = prepare(second_inputs, second_config, output, "second", first_result if mixed else None)
    write_bundle(second_bundle, output / "second-planned.json")
    session.register_target(second_bundle, artifact_ref(second_snapshot), asset_root=output)
    capture(output, "before-second", session, [first, second])
    result, receipt = execute(session, second_bundle, second_plan, second_config, output, "second", second_fault)
    assert session.is_paused(first)
    assert session.receipt_history(first) == first_history
    unknown_second = second_fault == "lost_response"
    assert session.is_paused(second) == unknown_second
    state = capture(output, "after-second", session, [first, second])
    for book, base, cfg in ((first, inputs, config), (second, second_inputs, second_config)):
        if session.is_paused(book):
            candidate, candidate_plan, _ = prepare(base, cfg, output, "omit-history-" + book)
            error = rejected("BOOK_WRITE_PAUSED", lambda: execute(session, candidate, candidate_plan, cfg, output, "blocked-" + book))
            write_json(output / (book + "-paused-error.json"), error)
    assert session.read_target(first) == state["targets"][first]
    assert session.read_target(second) == state["targets"][second]
    assert session.action_log == tuple(state["action_log"])
    return {"first": first, "second": second, "second_fault": second_fault, "mixed": mixed,
            "first_paused": True, "second_paused": unknown_second,
            "second_outcomes": [r.outcome for r in receipt.payload.results],
            "first_history_preserved": True, "target_frames": {b: len(session.read_target(b)["target"]["frames"]) for b in (first, second)}}


def same_book_and_replay(source, output):
    output.mkdir(parents=True, exist_ok=False)
    outcomes = {}
    for fault in ("applied", "not_applied", "lost_response"):
        case = output / fault
        case.mkdir()
        inputs, config = own_input(source, case, "book-same", "original")
        bundle, plan, snapshot = prepare(inputs, config, case, "original")
        session = MockSession()
        session.register_target(bundle, artifact_ref(snapshot), asset_root=case)
        result, receipt = execute(session, bundle, plan, config, case, "original", fault)
        before = capture(case, "before-replay", session, [config.book_id])
        code = "BOOK_WRITE_PAUSED" if fault == "lost_response" else "REPLAY_FORBIDDEN"
        error = rejected(code, lambda: execute(session, bundle, plan, config, case, "old-plan-replay"))
        write_json(case / "old-plan-error.json", error)
        attempts = []
        if fault == "lost_response":
            for variant in ("run", "action", "question", "scope"):
                kwargs = {"new_question": True} if variant == "question" else {"scope": "r1-other-scope"} if variant == "scope" else {}
                fresh_inputs, fresh_config = own_input(source, case, config.book_id, variant, **kwargs)
                fresh, fresh_plan, _ = prepare(fresh_inputs, fresh_config, case, "fresh-" + variant)
                write_bundle(fresh, case / (variant + "-omitted-history-planned.json"))
                error = rejected("BOOK_WRITE_PAUSED", lambda: execute(session, fresh, fresh_plan, fresh_config, case, "bypass-" + variant))
                attempts.append({"variant": variant, "first_action_id": fresh_plan.payload.actions[0].action_id,
                                 "first_question_id": fresh_plan.payload.actions[0].target.question_id,
                                 "run_id": fresh_plan.run_id, "scope_id": fresh_plan.scope_id, "error": error})
        after = capture(case, "after-rejections", session, [config.book_id])
        assert before == after, "rejected plans changed target/log/history"
        write_json(case / "bypass-attempts.json", attempts)
        outcomes[fault] = {"results": [r.outcome for r in receipt.payload.results], "replay_error": code,
                           "bypass_count": len(attempts), "frames": len(session.read_target(config.book_id)["target"]["frames"])}
    return outcomes


def same_book_history_only(source, output):
    """Own imported UNKNOWN must pause even when this session has no pending intent."""
    output.mkdir(parents=True, exist_ok=False)
    book = "book-history-only"
    prior = clone_input(Path(source) / "tests/fixtures/contracts/unknown", output, book, "prior")
    diagnostic, config = own_input(source, output, book, "diagnostic", "exceptions")
    bundle, plan, _ = prepare(diagnostic, config, output, "history-only", prior)
    write_bundle(bundle, output / "diagnostic-planned.json")
    session = MockSession()
    initial_pause = session.is_paused(book)
    result, receipt = execute(session, bundle, plan, config, output, "diagnostic")
    assert not initial_pause and receipt.payload.execution_mode == "NOT_EXECUTED"
    assert not session.action_log and session.is_paused(book), "own historical UNKNOWN must pause without intent"
    before = session.receipt_history(book)
    fresh_inputs, fresh_config = own_input(source, output, book, "omitted")
    fresh, fresh_plan, _ = prepare(fresh_inputs, fresh_config, output, "omitted")
    write_bundle(fresh, output / "omitted-history-ready.json")
    error = rejected("BOOK_WRITE_PAUSED", lambda: execute(session, fresh, fresh_plan, fresh_config, output, "blocked"))
    assert before == session.receipt_history(book) and not session.action_log
    write_json(output / "history-and-error.json", {"provenance": "SYNTHETIC", "history": before, "error": error,
                                                  "paused": session.is_paused(book), "action_log": session.action_log})
    return {"initial_pause": False, "own_historical_unknown_pause": True,
            "pending_intents_created": 0, "history_preserved": True, "omitted_history_error": "BOOK_WRITE_PAUSED"}


def run_matrix(source, output):
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for swapped in (False, True):
        book, foreign = ("book-beta", "book-alpha") if swapped else ("book-alpha", "book-beta")
        suffix = "swapped" if swapped else "forward"
        for mode in ("diagnostic", "applied", "not_applied"):
            cases.append(("mixed-" + mode + "-" + suffix, lambda folder, b=book, f=foreign, m=mode: crossbook(source, folder, b, f, m)))
        for fault in ("lost_response", "applied", "not_applied"):
            cases.append(("two-books-" + fault + "-" + suffix,
                          lambda folder, b=book, f=foreign, fault=fault: two_books(source, folder, b, f, fault)))
        cases.append(("standalone-" + suffix, lambda folder, b=book, f=foreign: two_books(source, folder, b, f, "applied", mixed=False)))
    cases.append(("same-book-and-replay", lambda folder: same_book_and_replay(source, folder)))
    cases.append(("same-book-history-only", lambda folder: same_book_history_only(source, folder)))
    results = []
    for name, run in cases:
        try:
            observed = run(output / name)
            result = {"case": name, "status": "PASS", "observations": observed}
        except Exception:
            result = {"case": name, "status": "FAIL", "traceback": traceback.format_exc()}
        write_json(output / (name + "-result.json"), result)
        results.append(result)
    write_json(output / "results.json", {"provenance": "SYNTHETIC", "execution_mode": "SIMULATED",
                                          "acceptance_state": "REVIEW", "cases": results,
                                          "platform_browser_model_calls": 0})
    assert all(r["status"] == "PASS" for r in results), "R1 matrix failures; inspect results.json"
    return results
