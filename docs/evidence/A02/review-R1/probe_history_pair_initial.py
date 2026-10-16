"""Independent R1 probe: two books retain historical UNKNOWN without live intents.

Only public APIs from the fixed raw-Git export are imported. Historical receipts
are synthetic contract inputs, not results of executing their old READY plans.
A fresh MockSession executes only zero-action BLOCKED diagnostics successfully.
Fresh READY retries omit all receipt history and must both be BOOK_WRITE_PAUSED.
No author R1 scenario helpers, private session collections, platform or model APIs.
"""
import argparse
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import sys


COMMIT = "38aca9dcc8d027409b95193e9cc142c2336b76d3"
HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source-38aca9dc"
ORIGIN = SOURCE / "tests/fixtures/contracts/unknown"
TIME = "2026-10-17T00:00:00Z"


def put_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")


def walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def akey(ref):
    return tuple(ref[name] for name in ("artifact_id", "revision", "kind", "content_hash"))


def pkey(ref):
    return tuple(ref[name] for name in ("policy_id", "revision", "content_hash"))


def clone_history(api, prefix, output):
    """Prefix identities/resources, then reseal every dependency in topological order."""
    raw = api.load_bundle(ORIGIN / "input.json").model_dump(mode="json")
    identities = {}
    resources = {}
    for node in walk(raw):
        if not isinstance(node, dict):
            continue
        for name, value in node.items():
            if name.endswith("_id") and isinstance(value, str):
                identities[value] = prefix + value
        if {"path", "sha256", "media_type"}.issubset(node):
            original = node["path"]
            resources[original] = "assets/" + prefix.rstrip("-") + "/" + original
    for original, relative in sorted(resources.items()):
        source = (ORIGIN / original).resolve()
        source.relative_to(ORIGIN.resolve())
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError("resource destination already exists: " + str(target))
        shutil.copyfile(source, target)

    def rename(value):
        if isinstance(value, dict):
            return {key: rename(child) for key, child in value.items()}
        if isinstance(value, list):
            return [rename(child) for child in value]
        if isinstance(value, str):
            return resources.get(value, identities.get(value, value))
        return value

    data = rename(raw)
    policy_refs = {}
    sealed_policies = []
    for policy in data["policies"]:
        sealed = api.seal_policy(policy)
        policy_refs[pkey(api.policy_ref(policy))] = api.policy_ref(sealed)
        sealed_policies.append(sealed)
    artifact_refs = {}

    def rebind(value):
        if isinstance(value, dict):
            if set(value) == {"artifact_id", "revision", "kind", "content_hash"}:
                return deepcopy(artifact_refs[akey(value)])
            if set(value) == {"policy_id", "revision", "content_hash"}:
                return deepcopy(policy_refs[pkey(value)])
            return {key: rebind(child) for key, child in value.items()}
        if isinstance(value, list):
            return [rebind(child) for child in value]
        return value

    pending = list(data["artifacts"])
    sealed_artifacts = []
    while pending:
        progressed = False
        for old in list(pending):
            if any(akey(ref) not in artifact_refs for ref in old["input_refs"]):
                continue
            sealed = api.seal_artifact(rebind(old))
            artifact_refs[akey(api.artifact_ref(old))] = api.artifact_ref(sealed)
            sealed_artifacts.append(sealed)
            pending.remove(old)
            progressed = True
        if not progressed:
            raise AssertionError("independent clone has unresolved/cyclic artifact references")
    data["artifacts"] = sealed_artifacts
    data["policies"] = sealed_policies
    bundle = api.validate_bundle(data, asset_root=output)
    return bundle, identities


def select(bundle, kind, book, revision=None, stage=None):
    matches = [a for a in bundle.artifacts if a.kind == kind and a.book_id == book
               and (revision is None or a.revision == revision)
               and (stage is None or a.payload.stage == stage)]
    if len(matches) != 1:
        raise AssertionError("ambiguous independent selection: {} {} {} {}".format(kind, book, revision, stage))
    return matches[0]


def save_bundle(api, bundle, output, name):
    bundle = api.validate_bundle(bundle, asset_root=output)
    api.write_bundle(bundle, output / name)
    return api.load_bundle(output / name)


def prepare_ready_retry(api, targetcheck, planner, original, book, prefix, config, output):
    """A separately constructed supported graph and PRE_APPLY stub, with no receipts."""
    source = select(original, "SourceBundle", book)
    evidence = select(original, "EvidenceBundle", book)
    snapshot = select(original, "PlatformSnapshot", book)
    old_graph = select(original, "QuestionGraph", book, revision=2)
    old_pre = select(original, "CheckReport", book, stage="PRE_APPLY")
    graph_data = old_graph.model_dump(mode="json")
    graph_data.update(artifact_id=prefix + "fresh-graph", revision=1,
                      run_id=prefix + "fresh-run", created_at=TIME,
                      input_refs=[api.artifact_ref(source), api.artifact_ref(evidence)])
    graph_data["payload"]["identity_notes"] = (
        "SYNTHETIC independent supported graph for an omitted-history gate probe; no historical patch derivation is claimed.")
    for question in graph_data["payload"]["questions"]:
        question["parent_question_id"] = None
        if question["question_type"] == "combination":
            question["question_type"] = "free_response"
    graph = api.seal_artifact(graph_data)
    pre_data = old_pre.model_dump(mode="json")
    pre_data.update(artifact_id=prefix + "fresh-preapply", revision=1,
                    run_id=prefix + "fresh-run", created_at=TIME,
                    input_refs=[api.artifact_ref(graph)])
    pre_data["producer"].update(module="independent-preapply-contract-stub", config_version="history-pair-1")
    pre_data["payload"].update(subject=api.artifact_ref(graph), graph=api.artifact_ref(graph),
                               snapshot=None, receipt=None,
                               reason="SYNTHETIC PRE_APPLY contract stub for a pause-gate probe; no algorithm quality claim.")
    for check in pre_data["payload"]["checks"]:
        check["reason"] = "SYNTHETIC contract stub; not independent algorithm quality evidence."
    pre = api.seal_artifact(pre_data)
    clean = api.validate_bundle({"format_version": "c01-exchange-1",
                                 "evidence": [e.model_dump(mode="json") for e in original.evidence],
                                 "policies": [p.model_dump(mode="json") for p in original.policies],
                                 "artifacts": [source.model_dump(mode="json"), evidence.model_dump(mode="json"),
                                               graph, snapshot.model_dump(mode="json"), pre]}, asset_root=output)
    clean = save_bundle(api, clean, output, prefix + "omitted-input.json")
    graph_model = select(clean, "QuestionGraph", book)
    pre_model = select(clean, "CheckReport", book, stage="PRE_APPLY")
    checked = targetcheck.check_target(clean, api.artifact_ref(graph_model), api.artifact_ref(snapshot),
                                      api.artifact_ref(snapshot), api.policy_ref(clean.policies[0]), config,
                                      artifact_id=prefix + "fresh-targetcheck", created_at=TIME)
    target = checked.artifacts[-1]
    planned = planner.create_plan(checked, api.artifact_ref(graph_model), api.artifact_ref(pre_model),
                                  api.artifact_ref(target), api.artifact_ref(snapshot), api.artifact_ref(snapshot),
                                  api.policy_ref(clean.policies[0]), config,
                                  artifact_id=prefix + "fresh-plan", created_at=TIME)
    planned = save_bundle(api, planned, output, prefix + "omitted-plan.json")
    plan = select(planned, "ApplyPlan", book)
    if target.payload.decision != "PASS" or plan.payload.readiness != "READY":
        raise AssertionError("omitted-history retry must independently be a legal READY plan")
    if any(a.kind == "ExecutionReceipt" for a in planned.artifacts):
        raise AssertionError("retry unexpectedly contains receipt history")
    api.assert_plan_ready(planned, api.artifact_ref(plan), api.artifact_ref(snapshot))
    return planned, plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "newdir/independent/history-pair")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("output must be a new directory: " + str(output))
    manifest = json.loads((HERE / "frozen-export.json").read_text(encoding="utf-8"))
    if manifest["target_commit"] != COMMIT:
        raise AssertionError("frozen-export identity differs from the explicitly assigned R1 commit")
    expected_files = {item["path"]: item["sha256"] for item in manifest["files"]}
    source_hashes = {}
    for relative in sorted(path for path in expected_files if path.startswith("src/")):
        digest = hashlib.sha256((SOURCE / relative).read_bytes()).hexdigest()
        if digest != expected_files[relative]:
            raise AssertionError("fixed source bytes changed: " + relative)
        source_hashes[relative] = digest
    sys.path.insert(0, str(SOURCE / "src"))
    import annotation.contracts as api
    import annotation.delivery.mock as mock
    import annotation.delivery.planner as planner
    import annotation.quality.targetcheck as targetcheck
    imports = {}
    for module in (api, mock, planner, targetcheck):
        location = Path(module.__file__).resolve()
        location.relative_to((SOURCE / "src").resolve())
        imports[module.__name__] = str(location)
    output.mkdir(parents=True)
    checks = []

    def expect(name, condition, detail=None):
        checks.append({"name": name, "passed": bool(condition), "detail": detail})

    books = []
    for label, prefix in (("book-a", "history-a-"), ("book-b", "history-b-")):
        original, identities = clone_history(api, prefix, output)
        book = identities["synthetic-book"]
        snapshot = select(original, "PlatformSnapshot", book)
        source = select(original, "SourceBundle", book)
        config = targetcheck.SimulationConfig(
            book_id=book, target_id=snapshot.payload.target_id, scope_id=snapshot.scope_id,
            directory_map={identities["directory-a"]: identities["directory-a"],
                           identities["directory-b"]: identities["directory-b"]})
        original = save_bundle(api, original, output, label + "-historical-input.json")
        retry_bundle, retry_plan = prepare_ready_retry(api, targetcheck, planner, original, book, prefix, config, output)
        book_dir = output / label
        book_dir.mkdir()
        put_json(book_dir / "config.json", asdict(config))
        books.append({"label": label, "prefix": prefix, "book": book, "original": original,
                      "snapshot": snapshot, "source": source, "config": config,
                      "retry_bundle": retry_bundle, "retry_plan": retry_plan, "directory": book_dir})
    mixed = api.validate_bundle({"format_version": "c01-exchange-1",
                                 "evidence": [e.model_dump(mode="json") for b in books for e in b["original"].evidence],
                                 "policies": [p.model_dump(mode="json") for b in books for p in b["original"].policies],
                                 "artifacts": [a.model_dump(mode="json") for b in books for a in b["original"].artifacts]},
                                asset_root=output)
    mixed = save_bundle(api, mixed, output, "input.json")
    session = mock.MockSession()
    initial_states = {}
    for b in books:
        session.register_target(mixed, api.artifact_ref(b["snapshot"]), asset_root=output,
                                source_ref=api.artifact_ref(b["source"]))
        initial_states[b["book"]] = session.read_target(b["book"])
        put_json(b["directory"] / "registered-state.json", initial_states[b["book"]])
        expect(b["label"] + ":fresh-session-not-paused", not session.is_paused(b["book"]))
        expect(b["label"] + ":fresh-session-history-empty", not session.receipt_history(b["book"]))
    expect("fresh-session-has-zero-log-events", len(session.action_log) == 0)
    diagnostic_observations = []
    for b in books:
        book, prefix = b["book"], b["prefix"]
        graph = select(mixed, "QuestionGraph", book, revision=2)
        pre = select(mixed, "CheckReport", book, stage="PRE_APPLY")
        policy = next(p for p in mixed.policies if p.policy_id == b["original"].policies[0].policy_id)
        save_bundle(api, mixed, output, b["label"] + "-diagnostic-input.json")
        checked = targetcheck.check_target(mixed, api.artifact_ref(graph), api.artifact_ref(b["snapshot"]),
                                          api.artifact_ref(b["snapshot"]), api.policy_ref(policy), b["config"],
                                          artifact_id=prefix + "diagnostic-targetcheck", created_at=TIME)
        target = checked.artifacts[-1]
        planned = planner.create_plan(checked, api.artifact_ref(graph), api.artifact_ref(pre), api.artifact_ref(target),
                                      api.artifact_ref(b["snapshot"]), api.artifact_ref(b["snapshot"]),
                                      api.policy_ref(policy), b["config"], artifact_id=prefix + "diagnostic-plan", created_at=TIME)
        plan = planned.artifacts[-1]
        if plan.payload.readiness != "BLOCKED" or plan.payload.actions:
            raise AssertionError("history import must use a zero-action BLOCKED diagnostic")
        save_bundle(api, planned, output, b["label"] + "-plan.json")
        returned = session.execute(planned, api.artifact_ref(plan), b["config"], asset_root=output,
                                   receipt_id=prefix + "diagnostic-receipt", created_at=TIME)
        returned = save_bundle(api, returned, output, b["label"] + "-receipt.json")
        receipt = next(a for a in returned.artifacts if a.artifact_id == prefix + "diagnostic-receipt")
        expect(b["label"] + ":diagnostic-not-executed", receipt.payload.execution_mode == "NOT_EXECUTED"
               and receipt.payload.write_disposition == "NOT_EXECUTED" and not receipt.payload.results)
        expect(b["label"] + ":zero-intent-after-diagnostic", len(session.action_log) == 0)
        expect(b["label"] + ":target-unchanged-after-diagnostic", session.read_target(book) == initial_states[book])
        history = session.receipt_history(book)
        for retained in history:
            api.validate_bundle(retained, asset_root=output)
        own_unknown = [a for packet in history for a in packet["artifacts"]
                       if a["kind"] == "ExecutionReceipt" and a["book_id"] == book
                       and any(r["outcome"] == "UNKNOWN" for r in a["payload"]["results"])]
        foreign_unknown = [a for packet in history for a in packet["artifacts"]
                           if a["kind"] == "ExecutionReceipt" and a["book_id"] != book
                           and any(r["outcome"] == "UNKNOWN" for r in a["payload"]["results"])]
        expect(b["label"] + ":one-own-historical-unknown-retained", len(own_unknown) == 1)
        expect(b["label"] + ":foreign-unknown-retained-in-full-mixed-packet", len(foreign_unknown) == 1)
        expect(b["label"] + ":history-only-pause", session.is_paused(book))
        diagnostic_observations.append({"book_id": book, "own_unknown_receipt_refs": [api.artifact_ref(a) for a in own_unknown],
                                        "foreign_unknown_receipt_refs": [api.artifact_ref(a) for a in foreign_unknown],
                                        "history_packets": len(history), "is_paused": session.is_paused(book),
                                        "action_log_length": len(session.action_log),
                                        "receipt_ref": api.artifact_ref(receipt)})
        put_json(b["directory"] / "after-diagnostic-state.json", session.read_target(book))
        if b is books[0]:
            other = books[1]
            expect("foreign-history-not-implicitly-imported-to-other-book", not session.is_paused(other["book"])
                   and not session.receipt_history(other["book"]))
        mixed = returned
    histories_before = {b["book"]: session.receipt_history(b["book"]) for b in books}
    retry_observations = []
    for b in books:
        book, plan = b["book"], b["retry_plan"]
        expect(b["label"] + ":retry-is-ready-and-omits-receipts", plan.payload.readiness == "READY"
               and bool(plan.payload.actions) and not any(a.kind == "ExecutionReceipt" for a in b["retry_bundle"].artifacts))
        api.assert_plan_ready(b["retry_bundle"], api.artifact_ref(plan), api.artifact_ref(session.read_snapshot(book)))
        observation = {"book_id": book, "plan_ref": api.artifact_ref(plan),
                       "public_contract_eligibility_without_history": "PASS", "caller_receipt_count": 0}
        try:
            unexpected = session.execute(b["retry_bundle"], api.artifact_ref(plan), b["config"], asset_root=output,
                                         receipt_id=b["prefix"] + "forbidden-retry-receipt", created_at=TIME)
        except api.ContractError as error:
            codes = [issue["code"] for issue in error.issues]
            observation.update(result="REJECTED", error_type=type(error).__name__, issues=error.issues)
            expect(b["label"] + ":omitted-history-still-book-write-paused", codes == ["BOOK_WRITE_PAUSED"], codes)
        else:
            save_bundle(api, unexpected, output, b["label"] + "-UNEXPECTED-executed.json")
            observation.update(result="UNEXPECTED_EXECUTION_RETURNED")
            expect(b["label"] + ":omitted-history-still-book-write-paused", False)
        retry_observations.append(observation)
        put_json(b["directory"] / "retry-observation.json", observation)
        expect(b["label"] + ":target-unchanged-after-omitted-retry", session.read_target(book) == initial_states[book])
        expect(b["label"] + ":complete-history-unchanged-after-retry", session.receipt_history(book) == histories_before[book])
        expect(b["label"] + ":still-paused-after-retry", session.is_paused(book))
    for b in books:
        history = session.receipt_history(b["book"])
        for retained in history:
            api.validate_bundle(retained, asset_root=output)
        put_json(b["directory"] / "history.json", history)
        put_json(b["directory"] / "state.json", session.read_target(b["book"]))
        put_json(b["directory"] / "action-log.json", [item for item in session.action_log if item.get("book_id") == b["book"]])
    log = list(session.action_log)
    expect("final-zero-log-events-and-zero-intents", not log)
    put_json(output / "action-log.json", log)
    actual = {"source_commit": COMMIT, "source_root": str(SOURCE), "checkout_commit": None,
              "imported_modules": imports, "source_sha256": source_hashes,
              "python": sys.version, "executable": sys.executable,
              "provenance": "SYNTHETIC", "execution_mode": "SIMULATED",
              "construction": "Two independently prefixed C01 UNKNOWN input bundles; fresh session; only BLOCKED diagnostics succeeded. No private pending/history mutation or inspection.",
              "successful_execute_paths": ["BLOCKED", "BLOCKED"] + ["READY_UNEXPECTED" for item in retry_observations if item["result"] == "UNEXPECTED_EXECUTION_RETURNED"],
              "no_pending_basis": "Before retries: fresh MockSession + only successful zero-action NOT_EXECUTED diagnostics + zero intent/log events + unchanged epoch/target; private pending collection was neither read nor changed.",
              "diagnostics": diagnostic_observations, "omitted_history_retries": retry_observations,
              "checks": checks, "all_checks_passed": all(check["passed"] for check in checks),
              "platform_actions": 0, "browser_actions": 0, "model_calls": 0,
              "mock_intent_count": sum(item.get("event") == "intent" for item in log),
              "action_log_length": len(log)}
    put_json(output / "actual.json", actual)
    print(json.dumps({"source_commit": COMMIT, "all_checks_passed": actual["all_checks_passed"],
                      "check_count": len(checks), "mock_intent_count": actual["mock_intent_count"],
                      "output": str(output)}, ensure_ascii=False, sort_keys=True))
    if not actual["all_checks_passed"]:
        raise AssertionError("history-pair probe failed: " + ", ".join(c["name"] for c in checks if not c["passed"]))


if __name__ == "__main__":
    main()
