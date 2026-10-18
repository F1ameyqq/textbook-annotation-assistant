"""Read-only A07-F01 archive comparison; no planning, targets or dispatch."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

from annotation.contracts import content_digest, validate_bundle

WORKFLOW = "ca1fb902c2228579cd2d0c84d81fc72cd0643796"
OLD_REVIEW = "efe440d07d3600ee9755f1709778a2a742bb2f52"
OLD_RUN = "docs/evidence/A07/review/candidate-1/normal/run"
MODIFIED = {"src/annotation/source/b_q1/reader.py", "src/annotation/quality/q1_offline.py"}


def git(*args):
    return subprocess.check_output(["git", "-c", "core.longpaths=true", *args],
                                  env=dict(os.environ, GIT_NO_LAZY_FETCH="1"))


def raw(ref, path):
    return git("show", ref + ":" + path)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def rule_basis():
    path = "项目交接说明.md"
    text = raw(WORKFLOW, path)
    lines = text.decode("utf-8").splitlines()
    assert lines[71].startswith("| W | 选项 | 普通选择题各选项独立框")
    assert "普通选择题选项单独一个框" in lines[97] and "一个 W 框" in lines[97]
    policies = {}
    for name in ("usense-v1-proposal", "synthetic-choice-separate"):
        p = "config/policies/" + name + ".json"
        value = raw(WORKFLOW, p)
        mapping = json.loads(value)["role_mapping"]
        assert [mapping["stem"], mapping["option"], mapping["answer"]] == ["Q", "W", "A"]
        policies[p] = {"raw_sha256": digest(value), "ordinary_roles": {k: mapping[k] for k in ("stem", "option", "answer")}}
    return {"workflow": WORKFLOW, "rule_path": path, "rule_raw_sha256": digest(text),
        "lines": {"72": lines[71], "98": lines[97]}, "existing_policy_basis": policies,
        "expected_roles": ["Q", "W", "W", "W", "W", "A"], "expected_derived_from_old_readback": False}


def tree(ref):
    result = {}
    for record in git("ls-tree", "-r", "-z", ref).split(b"\0"):
        if record:
            head, name = record.split(b"\t", 1)
            result[name.decode("utf-8")] = head.decode().split()[2]
    return result


def without(value, keys):
    return {k: v for k, v in value.items() if k not in keys}


def archive_delta(new_run, candidate):
    root = Path(new_run)
    basis = rule_basis()
    new_exchange = json.loads((root / "exchange.json").read_bytes())
    valid = validate_bundle(new_exchange, asset_root=root)
    old_exchange = json.loads(raw(OLD_REVIEW, OLD_RUN + "/exchange.json"))
    old_read_raw = raw(OLD_REVIEW, OLD_RUN + "/assets/readback.json")
    assert digest(old_read_raw) == "df3c33600ca7c08b873b756466a1a269643263559439d50047fa536edcdac019"
    old = json.loads(old_read_raw)
    new = json.loads((root / "assets/readback.json").read_bytes())
    before = json.loads((root / "assets/before.json").read_bytes())
    assert new["read_sequence"] > before["read_sequence"] and new["instance_id"] == before["instance_id"]
    assert content_digest(new["view"]) == new["target_state_hash"]
    assert content_digest(before["view"]) == before["target_state_hash"]
    assert len(before["view"]["target"]["frames"]) == 0 and new["view"]["epoch"] == 1
    old_frames, new_frames = [x["view"]["target"]["frames"] for x in (old, new)]
    assert len(old_frames) == len(new_frames) == 6
    assert [f["platform_role"] for f in new_frames] == basis["expected_roles"]
    comparisons = []
    for i, (old_frame, new_frame) in enumerate(zip(old_frames, new_frames)):
        old_projection = old["view"]["frame_projections"][old_frame["platform_frame_id"]]
        new_projection = new["view"]["frame_projections"][new_frame["platform_frame_id"]]
        assert without(old_frame, {"platform_role"}) == without(new_frame, {"platform_role"})
        assert without(old_projection, {"platform_role"}) == without(new_projection, {"platform_role"})
        assert new_frame["box"] == new_projection["box"]
        comparisons.append({"index": i, "fragment_id": new_projection["fragment_id"], "region_id": new_projection["region_id"],
            "old_role": old_frame["platform_role"], "new_role": new_frame["platform_role"], "expected_role": basis["expected_roles"][i],
            "box": new_frame["box"], "all_non_role_frame_fields_equal": True, "all_non_role_projection_fields_equal": True})
    assert [i for i, row in enumerate(comparisons) if row["old_role"] != row["new_role"]] == [1, 2, 3, 4]
    assert old["view"]["internal_bindings"] == new["view"]["internal_bindings"]
    assert old["view"]["target"]["questions"] == new["view"]["target"]["questions"]
    old_policy = old_exchange["policies"][0]
    new_policy = new_exchange["policies"][0]
    expected_policy = copy.deepcopy(old_policy)
    expected_policy["role_mapping"]["option"] = "W"
    assert without(expected_policy, {"content_hash"}) == without(new_policy, {"content_hash"})
    assert new_policy["content_hash"] != old_policy["content_hash"]
    old_artifacts = {a["kind"]: a for a in old_exchange["artifacts"] if a["kind"] != "CheckReport"}
    new_artifacts = {a["kind"]: a for a in new_exchange["artifacts"] if a["kind"] != "CheckReport"}
    assert new_artifacts["SourceBundle"]["payload"] == old_artifacts["SourceBundle"]["payload"]
    for kind, refs in (("EvidenceBundle", {"source"}), ("QuestionGraph", {"source", "evidence"})):
        assert without(new_artifacts[kind]["payload"], refs) == without(old_artifacts[kind]["payload"], refs)
    old_regions = old_artifacts["EvidenceBundle"]["payload"]["regions"]
    new_regions = new_artifacts["EvidenceBundle"]["payload"]["regions"]
    assert old_regions == new_regions
    checks = {a.payload.stage: {c.check_id: c.outcome for c in a.payload.checks} for a in valid.artifacts if a.kind == "CheckReport"}
    assert len(checks["PRE_APPLY"]) == 5 and len(checks["TARGET"]) == 4
    assert all(v == "PASS" for stage in checks.values() for v in stage.values())
    summary = json.loads((root / "summary.json").read_bytes())
    assert summary["complete_attempts"] == summary["dispatches"] == summary["successful_closures"] == 1
    assert summary["question_count"] == 1 and summary["frame_count"] == 6 and summary["outcome"] == "APPLIED"
    assert summary["submission_status"] == "NOT_SUBMITTED" and summary["content_check_status"] == "PENDING"
    assert summary["platform_calls"] == summary["model_calls"] == 0
    assert all(a.producer.evidence_mode == "OBSERVED" for a in valid.artifacts if a.kind in ("SourceBundle", "EvidenceBundle", "QuestionGraph") or
               (a.kind == "CheckReport" and a.payload.stage == "PRE_APPLY"))
    assert all(a.producer.evidence_mode == "SYNTHETIC" for a in valid.artifacts if a.kind in ("PlatformSnapshot", "ApplyPlan", "ExecutionReceipt") or
               (a.kind == "CheckReport" and a.payload.stage == "TARGET"))
    assert new_policy["confirmation_status"] == "A_INTERNAL_PROPOSAL" and new_policy["applicability"] == "PROPOSAL_ONLY"
    archive_before, archive_after = tree(WORKFLOW), tree(candidate)
    changed = [name for name in archive_before if archive_before[name] != archive_after.get(name)]
    assert set(changed) == MODIFIED
    old_evidence = [name for name in archive_before if name.startswith("docs/evidence/")]
    assert all(archive_before[n] == archive_after.get(n) for n in old_evidence)
    authorizations = {p: digest(raw(WORKFLOW, p)) for p in
        ("docs/approvals/A07-Q1-offline-business-approval.json", "docs/approvals/A07-F01-role-correction-approval.json")}
    assert authorizations["docs/approvals/A07-Q1-offline-business-approval.json"] == summary["approval_sha256"]
    for name in ("approval", "policy", "history", "side-candidate", "side-manifest", "side-native-selection", "side-native-scope-issues", "side-scope-applicability-proposal", "base-check", "base-evidence", "base-graph", "provenance"):
        assert (root / ("assets/input/" + name + ".json")).read_bytes() == raw(OLD_REVIEW, OLD_RUN + "/assets/input/" + name + ".json")
    return {"product_candidate": candidate, "workflow": WORKFLOW, "old_review_commit": OLD_REVIEW,
        "old_readback_raw_sha256": digest(old_read_raw), "new_readback_raw_sha256": digest((root / "assets/readback.json").read_bytes()),
        "rule_basis": basis, "actual_frame_comparisons": comparisons, "content_regions_identical": old_regions == new_regions,
        "source_payload_identical": True, "graph_semantics_identical": True, "all_input_resource_bytes_identical": True,
        "old_paths_count": len(archive_before), "old_paths_preserved_except_two_authorized_modules": True,
        "old_evidence_paths_preserved": len(old_evidence), "old_paths_changed": changed,
        "two_authorizations_raw_sha256": authorizations, "input_sha256": summary["input_sha256"],
        "old_C01_policy_hash": old_policy["content_hash"], "new_C01_policy_hash": new_policy["content_hash"],
        "old_artifact_hashes": {a["artifact_id"]: a["content_hash"] for a in old_exchange["artifacts"]},
        "new_artifact_hashes": {a["artifact_id"]: a["content_hash"] for a in new_exchange["artifacts"]},
        "derived_changes": ["fresh run/artifact/target-instance identities and timestamps", "four option frame/projection roles Q to W",
            "C01 policy full-envelope hash and all dependent artifact hashes/references", "PRE_APPLY ordinary_choice and exact-role comparisons",
            "actual target-state/readback/comparator/receipt resource hashes"],
        "checks": checks, "read_sequences": [before["read_sequence"], new["read_sequence"]],
        "normal_attempts_in_checked_archive": 1, "business_dispatches_in_checked_archive": 1,
        "new_business_runs_by_this_checker": 0, "state": "READY_FOR_REVIEW", "submission_status": "NOT_SUBMITTED", "content_check_status": "PENDING"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--new-run", required=True)
    parser.add_argument("--product-candidate", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = archive_delta(args.new_run, args.product_candidate)
    with Path(args.output).open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"state": result["state"], "roles": [r["new_role"] for r in result["actual_frame_comparisons"]],
                      "old_evidence_paths_preserved": result["old_evidence_paths_preserved"], "new_business_runs": 0}))


if __name__ == "__main__":
    main()
