"""Finite A08 R0-R7 driver, invoked explicitly against one frozen candidate.

No old suites, B scripts, producer, database or execution path are called.
The original package is received once. Each listed negative is received once.
"""

import argparse
import copy
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXED_SHA = "b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)


def repack(members):
    """Refresh all internal case/receipt/manifest links; leave production pins alone."""
    result = dict(members)
    batch = json.loads(result["staging/batch.json"])
    for case in batch["cases"]:
        result["staging/cases/" + case["case_id"] + ".json"] = encode(case)
    result["staging/batch.json"] = encode(batch)
    receipt = json.loads(result["staging/receipt.json"])
    receipt["batch_file_sha256"] = sha(result["staging/batch.json"])
    result["staging/receipt.json"] = encode(receipt)
    for name, prefix in (("staging/manifest.json", "staging/"), ("manifest.json", "")):
        manifest = json.loads(result[name])
        for row in manifest["files"]:
            raw = result[prefix + row["path"]]
            row["bytes"], row["sha256"] = len(raw), sha(raw)
        result[name] = encode(manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in result.items():
            archive.writestr(name, raw)
    return output.getvalue()


def mutate(members, name):
    data = dict(members)
    batch = json.loads(data["staging/batch.json"])
    cases = {c["case_id"]: c for c in batch["cases"]}
    q4, q9, q16 = (cases[c] for c in ("q4-first-lesson", "q9-reflection-continuation", "q16-unit2-formulas"))
    if name == "R1-schema":
        batch["schema_version"] = "b-complex-batch-proposal/99.0"
    elif name == "R1-kind":
        batch["kind"] = "ExecutableBatch"
    elif name == "R2-member-digest":
        # Repack first, then corrupt one resource without refreshing either manifest.
        good = repack(data)
        with zipfile.ZipFile(io.BytesIO(good)) as archive:
            corrupted = {n: archive.read(n) for n in archive.namelist()}
        asset = "staging/assets/viewer-173.jpg"
        corrupted[asset] = corrupted[asset][:-1] + bytes([corrupted[asset][-1] ^ 1])
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for n, raw in corrupted.items():
                archive.writestr(n, raw)
        return output.getvalue()
    elif name == "R3-cross-section-q4":
        other = cases["q4-topic-fraction"]
        q4["answer_id"] = other["answer_id"]
        q4["answer_snapshot"] = copy.deepcopy(other["answer_snapshot"])
        q4["question_snapshot"]["candidate_answer_ids"] = [other["answer_id"]]
        q4["question_snapshot"]["selected_answer_id"] = other["answer_id"]
    elif name == "R4-invented-q9-question":
        q9["question_id"] = "invented-from-printed-number-9"
        q9["question_snapshot"] = copy.deepcopy(q4["question_snapshot"])
        q9["mode"] = "QUESTION_ANSWER_CANDIDATE"
    elif name == "R5-resource-alias":
        asset = next(a for a in batch["assets"] if a["asset_id"] == "resource-173")
        asset["asset_id"] = "viewer-173"
    elif name == "R5-invented-viewer":
        asset = next(a for a in batch["assets"] if a["asset_id"] == "resource-173")
        asset["external_refs"]["viewer_page"] = 174
    elif name == "R6-q9-continuation-region":
        q9["answer_snapshot"]["render_regions"].pop()
        q9["answer_snapshot"]["regions"].pop()
        q9["counts"]["render_regions"] -= 1
    elif name == "R6-q16-latex-run":
        content = q16["answer_snapshot"]["content_fragments"][0]
        index = next(i for i, run in enumerate(content["runs"]) if run["format"] == "latex")
        content["runs"].pop(index)
        q16["counts"]["latex_runs"] -= 1
    elif name == "R7-q1-approval":
        q16["approval_ref"] = "docs/approvals/A07-Q1-offline-business-approval.json"
        q16["q1_exclusions"] = list(range(30))
    elif name == "R7-approved-marker":
        q4["business_approved"] = True
    else:
        raise AssertionError(name)
    data["staging/batch.json"] = encode(batch)
    return repack(data)


NEGATIVES = [
    ("R1-schema", "VERSION", "UNSUPPORTED_BATCH_VERSION", "/schema_version"),
    ("R1-kind", "VERSION", "UNSUPPORTED_BATCH_VERSION", "/kind"),
    ("R2-member-digest", "MANIFEST", "MEMBER_DIGEST", "viewer-173.jpg"),
    ("R3-cross-section-q4", "IDENTITY", "CROSS_SCOPE_OR_CASE_IDENTITY", "/answer_id"),
    ("R4-invented-q9-question", "IDENTITY", "FABRICATED_QUESTION_OR_RELATION", "/cases/2"),
    ("R5-resource-alias", "SOURCE", "ASSET_IDENTITY_CONFLICT", "/assets/2"),
    ("R5-invented-viewer", "SOURCE", "ASSET_IDENTITY_CONFLICT", "/external_refs"),
    ("R6-q9-continuation-region", "STRUCTURE", "FIXED_COUNT_MISMATCH", "/render_regions"),
    ("R6-q16-latex-run", "STRUCTURE", "FIXED_COUNT_MISMATCH", "/latex_runs"),
    ("R7-q1-approval", "AUTHORIZATION", "CASE_APPROVAL_ESCALATION", "/approval_ref"),
    ("R7-approved-marker", "AUTHORIZATION", "CASE_APPROVAL_ESCALATION", "/business_approved"),
]


def verify_original(report, members):
    batch = json.loads(members["staging/batch.json"])
    assert report["status"] == "RECEIVED_READONLY_HOLD"
    assert report["summary"] == {"cases": 4, "assets": 3, "question_answer_candidates": 1,
                                  "answer_evidence_only": 3, "hold_cases": 4}
    assert report["cases"][0]["case_id"] == "q4-first-lesson"
    assert report["input"]["zip_sha256"] == FIXED_SHA
    assert (report["input"]["zip_member_count"], report["input"]["outer_manifest_entries"],
            report["input"]["inner_manifest_entries"]) == (24, 23, 9)
    assert report["assets"] == batch["assets"]
    assert report["external_objects"]["complete_G_Check_plan_objects_loaded"] is False
    assert report["external_objects"]["status"] == "DECLARED_ONLY_EXTERNAL_NOT_LOADED"
    assert report["q1_authorization_transfer_allowed"] is False
    for observed, source in zip(report["cases"], batch["cases"]):
        assert observed["source_snapshot"] == source
        assert observed["decision"] == "HOLD" and observed["business_acceptance"] is False
        assert all(observed[k] == "PENDING" for k in ("content_approval", "region_approval", "case_policy_approval"))
        if source["question_id"] is None:
            assert observed["candidate_relation"] is None and observed["mode"] == "ANSWER_EVIDENCE_ONLY"
    first = report["cases"][0]
    assert first["candidate_relation"]["status"] == "B_DECLARED_CANDIDATE_ONLY"
    assert first["candidate_relation"]["a_selected_relation_created"] is False
    answer = first["source_snapshot"]["answer_snapshot"]
    assert answer["text"] == "13" and answer["fragments"][0]["raw_text"] == "4.13"
    assert answer["fragments"][0]["text_span"] == [2, 4]
    assert first["source_snapshot"]["question_snapshot"]["flags"] == ["FIGURE_EXTENT_UNVERIFIED"]
    assert first["structure"]["observed_counts"]["render_regions"] == 0
    q9 = report["cases"][2]["structure"]
    assert len(q9["text_source_fragment_order"]) == q9["render_text_source_count"] == 10
    assert q9["render_image_source_count"] == 23
    assert len(report["cases"][3]["structure"]["structured_latex_runs"]) == 11
    assert set(report["support_matrix"]) == {"N%02d" % i for i in range(1, 9)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--candidate", required=True, choices=("1", "2"))
    args = parser.parse_args()
    evidence = Path(args.evidence_dir).resolve()
    assert ROOT in evidence.parents and "docs/evidence/A08/execution/" in evidence.as_posix() + "/"
    assert not evidence.exists(), "each frozen candidate needs a fresh evidence directory"
    evidence.mkdir(parents=True)
    original = Path(args.package).read_bytes()
    assert sha(original) == FIXED_SHA
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        members = {n: archive.read(n) for n in archive.namelist()}
    scratch_root = ROOT / "examples/a08"
    scratch_root.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="candidate-" + args.candidate + "-", dir=str(scratch_root)))
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1",
               GIT_NO_LAZY_FETCH="1")
    results, failed = [], False
    rows = [("R0-original", None, None, None)] + NEGATIVES
    for name, layer, code, suffix in rows:
        if failed:
            results.append({"case": name, "status": "NOT_RUN"})
            continue
        try:
            if name == "R0-original":
                package = Path(args.package)
                raw = original
            else:
                raw = mutate(members, name)
                package = scratch / (name + ".zip")
                write(package, raw)
            report_path = evidence / (name + ".json")
            command = [sys.executable, "-m", "annotation.source.b_batch", str(package),
                       "--priority-case", "q4-first-lesson", "--report", str(report_path)]
            with subprocess.Popen(command, cwd=str(ROOT), env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE) as child:
                try:
                    stdout, stderr = child.communicate(timeout=30)
                except subprocess.TimeoutExpired:
                    child.kill()
                    stdout, stderr = child.communicate()
                    write(evidence / (name + ".stdout.txt"), stdout)
                    write(evidence / (name + ".stderr.txt"), stderr)
                    raise AssertionError("first failure: receiver exceeded 30 seconds; child killed and joined")
                pid, exit_code = child.pid, child.returncode
            write(evidence / (name + ".stdout.txt"), stdout)
            write(evidence / (name + ".stderr.txt"), stderr)
            report = json.loads(stdout)
            row = {"case": name, "command": command, "cwd": str(ROOT), "exit_code": exit_code,
                   "pid": pid, "joined": True,
                   "variant_sha256": sha(raw), "variant_bytes": len(raw),
                   "actual_layer": report.get("layer"), "actual_code": report.get("code"),
                   "actual_path": report.get("path"), "status": "PASS"}
            results.append(row)
            assert json.loads(report_path.read_bytes()) == report
            assert all(value == 0 for value in report["actions"].values())
            assert stderr == b""
            if name == "R0-original":
                assert exit_code == 0
                verify_original(report, members)
            else:
                assert exit_code == 2
                assert report["status"] == "REJECTED" and report["decision"] == "HOLD"
                assert (report["layer"], report["code"]) == (layer, code)
                assert report["path"].endswith(suffix)
        except Exception as exc:
            failed = True
            if results and results[-1]["case"] == name:
                results[-1]["status"] = "FAIL"
                results[-1]["failure"] = repr(exc)
            else:
                results.append({"case": name, "status": "FAIL", "failure": repr(exc)})
    unchanged = Path(args.package).read_bytes() == original
    if not failed:
        # Verified absolute target is a newly created child of this task's scratch root.
        assert scratch.resolve().parent == scratch_root.resolve() and ROOT in scratch.resolve().parents
        shutil.rmtree(str(scratch))
    summary = {"candidate": args.candidate, "status": "FAIL" if failed else "PASS_AUTHOR_FINITE_CHECKS_ONLY",
               "original_sha256_before": FIXED_SHA, "original_sha256_after": sha(Path(args.package).read_bytes()),
               "original_bytes_unchanged": unchanged, "results": results,
               "groups": ["R%d" % i for i in range(8)], "original_receives": 1,
               "negative_receives": sum(r["case"] != "R0-original" and r["status"] != "NOT_RUN" for r in results),
               "subprocesses_joined": True, "owned_services_started": 0,
               "scratch_removed": not scratch.exists(), "failure_scratch": str(scratch) if failed else None,
               "mutant_recipe": "tests/test_a08_reception.py: mutate + repack; no production pins modified"}
    write(evidence / "finite-results.json", encode(summary))
    print(json.dumps({"status": summary["status"], "cases": len(results), "evidence": str(evidence)}, ensure_ascii=False))
    return 1 if failed or not unchanged else 0


if __name__ == "__main__":
    sys.exit(main())
