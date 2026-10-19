"""Independent A08 frozen review: no imports or execution of the author driver.

Phases: preflight, run, preserve. Each phase writes new evidence exclusively.
The run phase has exactly one original CLI call and the eleven dispatched variants.
"""
import argparse
import ast
import copy
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
DELIVERY = "83f119fae8e84b30332ac50288b74049514c9b4e"
PRODUCT = "04762d78eae18449d7fcf3c0de20aec23b1f6881"
BASE = "6fac939cf6cae0df88fab12d9669090c325897fc"
WORKFLOW = "88c89cf3d855f4d01b13e6e3c98079fc9827e8ad"
PACKAGE = Path("D:/1800/.local/stages/a08-inputs/B-46007447-Q4-Q9-Q16-next-batch-HOLD-2026-10-19.zip")
PACKAGE_SHA = "b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673"
ZERO_KEYS = {"plans", "targets", "new_c01_execution_objects", "simulation_dispatches",
             "platform_calls", "paid_model_calls", "b_messages", "pushes"}
SPECS = [
    ("R0-original", None, None, None),
    ("R1-schema", "VERSION", "UNSUPPORTED_BATCH_VERSION", "/schema_version"),
    ("R1-kind", "VERSION", "UNSUPPORTED_BATCH_VERSION", "/kind"),
    ("R2-member-digest", "MANIFEST", "MEMBER_DIGEST", "staging/assets/viewer-173.jpg"),
    ("R3-cross-section-q4", "IDENTITY", "CROSS_SCOPE_OR_CASE_IDENTITY", "/cases/0/answer_id"),
    ("R4-invented-q9-question", "IDENTITY", "FABRICATED_QUESTION_OR_RELATION", "/cases/2"),
    ("R5-resource-alias", "SOURCE", "ASSET_IDENTITY_CONFLICT", "/assets/2"),
    ("R5-invented-viewer", "SOURCE", "ASSET_IDENTITY_CONFLICT", "/assets/2/external_refs"),
    ("R6-q9-continuation-region", "STRUCTURE", "FIXED_COUNT_MISMATCH", "/observed_counts/render_regions"),
    ("R6-q16-latex-run", "STRUCTURE", "FIXED_COUNT_MISMATCH", "/observed_counts/latex_runs"),
    ("R7-q1-approval", "AUTHORIZATION", "CASE_APPROVAL_ESCALATION", "/cases/3/approval_ref"),
    ("R7-approved-marker", "AUTHORIZATION", "CASE_APPROVAL_ESCALATION", "/cases/0/business_approved"),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(obj):
    # Independent serialization, intentionally different from the author driver.
    return (json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def save(name, value, raw=False):
    target = OUT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as handle:
        handle.write(value if raw else encoded(value))


def git(*args):
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1")
    return subprocess.check_output(["git", "-c", "core.longpaths=true", *args], cwd=str(ROOT), env=env)


def blobs(revision, paths):
    command = ["git", "-c", "core.longpaths=true", "cat-file", "--batch"]
    requests = b"".join((revision + ":" + p + "\n").encode("utf-8") for p in paths)
    raw = subprocess.check_output(command, cwd=str(ROOT), input=requests,
                                  env=dict(os.environ, GIT_NO_LAZY_FETCH="1"))
    stream = io.BytesIO(raw)
    answer = {}
    for path in paths:
        header = stream.readline().decode("ascii").strip().split()
        assert len(header) == 3 and header[1] == "blob", (path, header)
        content = stream.read(int(header[2]))
        assert stream.read(1) == b"\n"
        answer[path] = (header[0], content)
    assert stream.read() == b""
    return answer


def tree(revision):
    result = {}
    for line in git("ls-tree", "-r", "-z", revision).split(b"\0"):
        if line:
            metadata, path = line.split(b"\t", 1)
            mode, kind, oid = metadata.decode("ascii").split()
            result[path.decode("utf-8")] = (mode, kind, oid)
    return result


def inventory(paths):
    return [{"path": p, "bytes": len(data), "sha256": sha(data)}
            for p in sorted(paths) for data in [(ROOT / p).read_bytes()]]


def validate_manifest(members, name, prefix):
    manifest = json.loads(members[name])
    keys = []
    for row in manifest["files"]:
        path = prefix + row["path"]
        assert path in members and len(members[path]) == row["bytes"]
        assert sha(members[path]) == row["sha256"], path
        keys.append(path)
    assert len(keys) == len(set(keys))
    assert set(keys) == {p for p in members if p.startswith(prefix)} - {name}
    return len(keys)


def input_data():
    raw = PACKAGE.read_bytes()
    assert sha(raw) == PACKAGE_SHA and len(raw) == 1440149
    assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == "4f49f37d81427e9aa8d2acf1c1919c1df8f10ce2"
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist())) == 24
        members = {info.filename: archive.read(info) for info in archive.infolist()}
    assert validate_manifest(members, "manifest.json", "") == 23
    assert validate_manifest(members, "staging/manifest.json", "staging/") == 9
    batch = json.loads(members["staging/batch.json"])
    for case in batch["cases"]:
        assert json.loads(members["staging/cases/" + case["case_id"] + ".json"]) == case
    assert json.loads(members["staging/receipt.json"])["batch_file_sha256"] == sha(members["staging/batch.json"])
    return raw, members, batch


def preflight():
    assert git("rev-parse", "HEAD").decode().strip() == DELIVERY
    assert git("branch", "--show-current").decode().strip() == "codex/a08-readonly-review"
    delivered, old, product = tree(DELIVERY), tree(BASE), tree(PRODUCT)
    assert len(old) == 12491 and all(delivered.get(p) == oid for p, oid in old.items())
    assert len(set(delivered) - set(old)) == 52
    manpath = "docs/evidence/A08/execution/delivery-raw-manifest.json"
    manifest = json.loads(blobs(DELIVERY, [manpath])[manpath][1])
    manifest_data = blobs(DELIVERY, [row["path"] for row in manifest["entries"]])
    for row in manifest["entries"]:
        oid, raw = manifest_data[row["path"]]
        assert (oid, len(raw), sha(raw)) == (row["git_blob"], row["bytes"], row["sha256"])
    assert len(manifest["entries"]) == 51 and sum(r["bytes"] for r in manifest["entries"]) == 525774
    pinpath = "docs/evidence/A08/execution/candidate-1-raw-git.json"
    pins = json.loads(manifest_data[pinpath][1])["added_paths"]
    product_paths = [row["path"] for row in pins]
    exact = []
    for row in pins:
        path = row["path"]
        raw = manifest_data[path][1]
        assert delivered[path] == product[path]
        assert (ROOT / path).read_bytes() == raw
        exact.append({"path": path, "git_blob": delivered[path][2], "bytes": len(raw),
                      "sha256": sha(raw), "product_delivery_disk_exact": True})
    assert len(exact) == 9
    source_imports = {}
    for p in product_paths:
        if p.startswith("src/") and p.endswith(".py"):
            module = ast.parse((ROOT / p).read_text(encoding="utf-8"))
            imports = [n.module or "" for n in ast.walk(module) if isinstance(n, ast.ImportFrom)]
            imports += [a.name for n in ast.walk(module) if isinstance(n, ast.Import) for a in n.names]
            assert not any(any(bad in name for bad in ("delivery", "runtime", "sqlite", "urllib", "requests", "socket", "subprocess")) for name in imports)
            source_imports[p] = imports
    raw, members, batch = input_data()
    from PIL import Image, __version__ as pillow_version
    assets = []
    for asset in batch["assets"]:
        data = members["staging/" + asset["path"]]
        assert sha(data) == asset["sha256"]
        with Image.open(io.BytesIO(data)) as im:
            im.load()
            assert im.format == "JPEG" and im.size == (asset["width"], asset["height"])
        assets.append({"asset_id": asset["asset_id"], "sha256": sha(data),
                       "dimensions": [asset["width"], asset["height"]], "decoded": True})
    save("baseline-files.json", {"delivery": DELIVERY, "entries": inventory(delivered)})
    save("provenance.json", {"status": "PASS_PREFLIGHT_NOT_ACCEPTANCE", "workflow": WORKFLOW,
         "product": PRODUCT, "delivery": DELIVERY, "execution_start": BASE,
         "branch": "codex/a08-readonly-review", "cwd": str(ROOT),
         "old_git_paths_preserved": len(old), "delivery_added_paths": 52,
         "author_manifest_raw_members_verified": 51, "author_manifest_raw_bytes_verified": 525774,
         "raw_product_driver_doc_paths": exact, "initial_git_status": git("status", "--short").decode("utf-8"),
         "initial_status_explanation": "Two cached modification markers have empty diff and exact frozen raw bytes; no reset or rewrite performed",
         "source_imports": source_imports, "input_sha256": sha(raw), "input_bytes": len(raw),
         "zip_members": 24, "outer_manifest_entries": 23, "inner_manifest_entries": 9,
         "decoded_assets": assets, "python": sys.version, "python_executable": sys.executable,
         "pillow": pillow_version, "os": platform.platform(), "driver_sha256": sha(Path(__file__).read_bytes()),
         "author_release_proof": json.loads(manifest_data["docs/evidence/A08/execution/process-release.json"][1]),
         "receiver_calls_in_preflight": 0, "actions": {k: 0 for k in sorted(ZERO_KEYS)}})
    print("PASS_PREFLIGHT_NOT_ACCEPTANCE: 51 raw members, 9 exact paths, 12491 old paths; 0 receiver calls")


def packed(members):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 19, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, members[name])
    return stream.getvalue()


def create_variant(original, label):
    members = dict(original)
    batch = json.loads(members["staging/batch.json"])
    case = {c["case_id"]: c for c in batch["cases"]}
    first, topic, q9, q16 = [case[k] for k in ("q4-first-lesson", "q4-topic-fraction", "q9-reflection-continuation", "q16-unit2-formulas")]
    recipe = {"label": label, "source": "registered original ZIP; fresh JSON parse for each variant"}
    if label == "R1-schema":
        batch["schema_version"] = "b-complex-batch-proposal/99.0"
    elif label == "R1-kind":
        batch["kind"] = "ExecutableBatch"
    elif label == "R2-member-digest":
        pass
    elif label == "R3-cross-section-q4":
        first["answer_id"] = topic["answer_id"]
        first["answer_snapshot"] = copy.deepcopy(topic["answer_snapshot"])
        first["question_snapshot"]["candidate_answer_ids"] = [topic["answer_id"]]
        first["question_snapshot"]["selected_answer_id"] = topic["answer_id"]
    elif label == "R4-invented-q9-question":
        q9["mode"] = "QUESTION_ANSWER_CANDIDATE"
        q9["question_id"] = "invented-from-printed-number-9"
        q9["question_snapshot"] = copy.deepcopy(first["question_snapshot"])
    elif label in ("R5-resource-alias", "R5-invented-viewer"):
        asset = next(a for a in batch["assets"] if a["asset_id"] == "resource-173")
        if label.endswith("resource-alias"):
            asset["asset_id"] = "viewer-173"
        else:
            asset["external_refs"]["viewer_page"] = 174
    elif label == "R6-q9-continuation-region":
        ans = q9["answer_snapshot"]
        # Same dispatched removal, independently bind it to the continuation page and ID.
        victim = ans["render_regions"][-1]
        assert victim["asset_id"] == "resource-173" and victim["region_id"] == "reflection-q9-figure-7"
        recipe["removed_region"] = copy.deepcopy(victim)
        ans["render_regions"] = ans["render_regions"][:-1]
        assert ans["regions"][-1]["region_id"] == victim["region_id"]
        ans["regions"] = ans["regions"][:-1]
        q9["counts"]["render_regions"] = 14
    elif label == "R6-q16-latex-run":
        runs = q16["answer_snapshot"]["content_fragments"][0]["runs"]
        index = next(i for i, r in enumerate(runs) if r["format"] == "latex")
        recipe["removed_run"] = {"content_fragment": 0, "index": index, "run": runs[index]}
        del runs[index]
        q16["counts"]["latex_runs"] = 10
    elif label == "R7-q1-approval":
        q16["approval_ref"] = "docs/approvals/A07-Q1-offline-business-approval.json"
        q16["q1_exclusions"] = list(range(30))
    elif label == "R7-approved-marker":
        first["business_approved"] = True
    else:
        raise AssertionError(label)
    members["staging/batch.json"] = encoded(batch)
    for item in batch["cases"]:
        members["staging/cases/" + item["case_id"] + ".json"] = encoded(item)
    receipt = json.loads(members["staging/receipt.json"])
    receipt["batch_file_sha256"] = sha(members["staging/batch.json"])
    members["staging/receipt.json"] = encoded(receipt)
    for name, prefix in (("staging/manifest.json", "staging/"), ("manifest.json", "")):
        manifest = json.loads(members[name])
        for item in manifest["files"]:
            value = members[prefix + item["path"]]
            item.update(bytes=len(value), sha256=sha(value))
        members[name] = encoded(manifest)
    assert validate_manifest(members, "manifest.json", "") == 23
    assert validate_manifest(members, "staging/manifest.json", "staging/") == 9
    recipe["both_manifests_valid_before_intentional_corruption"] = True
    if label == "R2-member-digest":
        name = "staging/assets/viewer-173.jpg"
        damaged = bytearray(members[name])
        damaged[-1] ^= 1
        members[name] = bytes(damaged)
        recipe["intentional_corruption"] = {"path": name, "offset": len(damaged) - 1, "operation": "xor 1 after sealing both manifests"}
    recipe["modified_members"] = [{"path": p, "original_sha256": sha(original[p]),
                                    "variant_sha256": sha(v), "bytes": len(v)}
                                   for p, v in sorted(members.items()) if v != original[p]]
    recipe["receipt_batch_sha_valid"] = json.loads(members["staging/receipt.json"])["batch_file_sha256"] == sha(members["staging/batch.json"])
    return packed(members), recipe


def check_original(report, original, members, batch):
    assert report["status"] == "RECEIVED_READONLY_HOLD" and report["decision"] == "HOLD"
    assert report["business_acceptance"] is False and report["q1_authorization_transfer_allowed"] is False
    assert report["summary"] == dict(cases=4, assets=3, question_answer_candidates=1, answer_evidence_only=3, hold_cases=4)
    assert report["priority_case"] == report["cases"][0]["case_id"] == "q4-first-lesson"
    assert report["input"]["zip_sha256"] == PACKAGE_SHA and report["input"]["zip_bytes"] == len(original)
    assert (report["input"]["zip_member_count"], report["input"]["outer_manifest_entries"], report["input"]["inner_manifest_entries"]) == (24, 23, 9)
    assert {r["path"]: (r["bytes"], r["sha256"]) for r in report["input"]["raw_members"]} == {p: (len(v), sha(v)) for p, v in members.items()}
    assert report["assets"] == batch["assets"]
    asset = {a["asset_id"]: a for a in report["assets"]}
    assert (asset["viewer-173"]["external_refs"]["resource_index"], asset["viewer-173"]["width"], asset["viewer-173"]["height"]) == (172, 1148, 1621)
    assert (asset["resource-173"]["external_refs"]["resource_index"], asset["resource-173"]["width"], asset["resource-173"]["height"], asset["resource-173"]["external_refs"]["viewer_page"]) == (173, 1145, 1620, None)
    ext = report["external_objects"]
    assert ext["status"] == "DECLARED_ONLY_EXTERNAL_NOT_LOADED" and ext["complete_G_Check_plan_objects_loaded"] is False
    for field in ("source_graph_ref", "source_graph_file_sha256", "source_package_sha256"):
        assert ext[field] == batch[field]
    assert report["embedded_code_or_historical_test_results_used_as_acceptance"] is False
    diag = {c["case_id"]: c for c in report["cases"]}
    observations = []
    for source in batch["cases"]:
        item = diag[source["case_id"]]
        assert item["source_snapshot"] == source
        assert item["decision"] == "HOLD" and item["business_acceptance"] is item["platform_eligible"] is False
        assert all(item[k] == "PENDING" for k in ("content_approval", "region_approval", "case_policy_approval"))
        assert item["question_id"] == source["question_id"] and item["answer_id"] == source["answer_id"]
        assert item["source_case_sha256"] == sha(members[item["source_case_member"]])
        assert item["section_path"] == source["section_path"] and item["blockers"] == source["blockers"]
        answer = source["answer_snapshot"]
        assert answer["verification_status"] == "UNVERIFIED"
        observed_runs = item["structure"]["structured_latex_runs"]
        expected_runs = [(i, j, run) for i, frag in enumerate(answer.get("content_fragments", []))
                         for j, run in enumerate(frag.get("runs", [])) if run["format"] == "latex"]
        assert len(observed_runs) == len(expected_runs)
        for displayed, (i, j, run) in zip(observed_runs, expected_runs):
            assert displayed["run"] == run and displayed["run_index"] == j
            assert displayed["source_path"].endswith("/content_fragments/%d/runs/%d" % (i, j))
        if source["question_id"] is None:
            assert source["question_snapshot"] is None and item["candidate_relation"] is None
            assert item["mode"] == "ANSWER_EVIDENCE_ONLY"
        else:
            relation = item["candidate_relation"]
            assert relation["status"] == "B_DECLARED_CANDIDATE_ONLY" and relation["a_selected_relation_created"] is False
            assert relation["source_selected_answer_id"] == source["question_snapshot"]["selected_answer_id"]
        observations.append({"case_id": item["case_id"], "question_id": item["question_id"], "answer_id": item["answer_id"],
                             "section_path": item["section_path"], "decision": item["decision"], "mode": item["mode"],
                             "counts": item["structure"]["observed_counts"], "source_snapshot_equal": True})
    q4 = diag["q4-first-lesson"]["source_snapshot"]
    assert q4["question_id"] == "q-260d10c51f2b7c16fb6fefb5" and q4["answer_id"] == "a-92c4d2164ab878c8e6d4c88d"
    assert q4["question_snapshot"]["verification_status"] == "UNVERIFIED"
    assert q4["question_snapshot"]["flags"] == ["FIGURE_EXTENT_UNVERIFIED"]
    assert len(q4["question_snapshot"]["fragments"]) == 4
    answer, fragment = q4["answer_snapshot"], q4["answer_snapshot"]["fragments"][0]
    assert answer["text"] == "13" and fragment["raw_text"] == "4.13" and fragment["text_span"] == [2, 4]
    assert fragment["bbox"] == [308.667, 241.667, 340.0, 254.333] and fragment["evidence_refs"] == ["viewer-173/ocr/10/detail/5"]
    q9 = diag["q9-reflection-continuation"]
    assert q9["structure"]["observed_counts"] == dict(raw_fragments=33, render_regions=15, latex_runs=0)
    assert len(q9["structure"]["text_source_fragment_order"]) == q9["structure"]["render_text_source_count"] == 10
    assert q9["structure"]["render_image_source_count"] == 23
    assert "ANSWER_SPATIAL_GAP_UNRESOLVED" in q9["source_snapshot"]["answer_snapshot"]["assembly_flags"]
    q16 = diag["q16-unit2-formulas"]
    assert q16["structure"]["observed_counts"] == dict(raw_fragments=17, render_regions=3, latex_runs=11)
    assert len(q16["source_snapshot"]["answer_snapshot"]["content_fragments"]) == 3
    assert "60 61" in q16["source_snapshot"]["answer_snapshot"]["content_fragments"][0]["text"]
    assert set(report["support_matrix"]) == {"N%02d" % i for i in range(1, 9)}
    assert report["support_matrix"]["N06"]["status"] == report["support_matrix"]["N07"]["status"] == "PENDING"
    save("original-observations.json", {"cases": observations, "q4_question": q4["question_snapshot"],
         "q4_answer": q4["answer_snapshot"], "assets": report["assets"], "external_objects": ext,
         "support_matrix": report["support_matrix"], "all_four_full_source_snapshots_equal": True,
         "q9_full_order_regions_continuations_equal": True, "q16_all_11_runs_and_source_paths_equal": True})


def run():
    assert not (OUT / "finite-results.json").exists(), "one finite run only"
    provenance = json.loads((OUT / "provenance.json").read_bytes())
    assert provenance["status"] == "PASS_PREFLIGHT_NOT_ACCEPTANCE"
    assert sha(Path(__file__).read_bytes()) == provenance["driver_sha256"]
    baseline = json.loads((OUT / "baseline-files.json").read_bytes())["entries"]
    assert inventory(r["path"] for r in baseline) == baseline
    original, members, batch = input_data()
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1", PYTHONDONTWRITEBYTECODE="1",
               PYTHONIOENCODING="utf-8", PYTHONPATH=str(ROOT / "src"))
    results, stopped, processes = [], False, []
    for label, layer, code, suffix in SPECS:
        if stopped:
            results.append({"case": label, "status": "NOT_RUN"})
            continue
        row = {"case": label, "status": "FAIL"}
        try:
            if layer is None:
                variant, path = original, PACKAGE
            else:
                variant, recipe = create_variant(members, label)
                path = OUT / "variants" / (label + ".zip")
                save("variants/" + label + ".zip", variant, raw=True)
                save(label + ".recipe.json", recipe)
            report_path = OUT / (label + ".json")
            argv = [sys.executable, "-B", "-m", "annotation.source.b_batch", str(path),
                    "--priority-case", "q4-first-lesson", "--report", str(report_path)]
            row.update(command=argv, cwd=str(ROOT), package_sha256=sha(variant), package_bytes=len(variant),
                       started_at_utc=datetime.now(timezone.utc).isoformat())
            start = time.monotonic()
            proc = subprocess.Popen(argv, cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            processes.append(proc)
            try:
                stdout, stderr = proc.communicate(timeout=30)
                timed_out = False
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                timed_out = True
            row.update(pid=proc.pid, exit_code=proc.returncode, joined=proc.poll() is not None,
                       elapsed_seconds=round(time.monotonic() - start, 6), timed_out=timed_out)
            save(label + ".stdout.txt", stdout, raw=True)
            save(label + ".stderr.txt", stderr, raw=True)
            assert not timed_out, "first failure: child timed out; killed and joined"
            report = json.loads(stdout)
            row.update(actual_layer=report.get("layer"), actual_code=report.get("code"), actual_path=report.get("path"))
            assert json.loads(report_path.read_bytes()) == report and stderr == b""
            assert set(report["actions"]) == ZERO_KEYS and all(type(v) is int and v == 0 for v in report["actions"].values())
            if layer is None:
                assert proc.returncode == 0
                check_original(report, original, members, batch)
            else:
                assert proc.returncode == 2 and report["status"] == "REJECTED" and report["decision"] == "HOLD"
                assert report["business_acceptance"] is False
                assert (report["layer"], report["code"]) == (layer, code)
                assert report["path"].endswith(suffix), report["path"]
            row["status"] = "PASS"
        except Exception:
            stopped = True
            row["failure"] = traceback.format_exc()
        results.append(row)
    unchanged = PACKAGE.read_bytes() == original
    summary = {"status": "REWORK" if stopped or not unchanged else "PASS_INDEPENDENT_FINITE_READONLY",
               "product": PRODUCT, "delivery": DELIVERY, "original_calls": sum(r["case"] == "R0-original" and "pid" in r for r in results),
               "negative_calls": sum(r["case"] != "R0-original" and "pid" in r for r in results),
               "results": results, "input_unchanged": unchanged, "actions": {k: 0 for k in sorted(ZERO_KEYS)},
               "author_driver_executed": False, "additional_api_calls": 0,
               "R6_reached_scope": "fixed structural inventory counts, not formula or continuation business semantics"}
    save("finite-results.json", summary)
    save("process-release.json", {"all_owned_children_joined": all(p.poll() is not None for p in processes),
         "children": [{"pid": p.pid, "exit_code": p.returncode, "joined": p.poll() is not None} for p in processes],
         "owned_services_started": 0, "other_processes_stopped": 0,
         "driver_run_phase_returning": True, "variants_retained": True})
    print(json.dumps({"status": summary["status"], "original_calls": summary["original_calls"], "negative_calls": summary["negative_calls"],
                      "failed": [r for r in results if r["status"] == "FAIL"]}, ensure_ascii=False))
    return 1 if stopped or not unchanged else 0


def preserve():
    baseline = json.loads((OUT / "baseline-files.json").read_bytes())["entries"]
    after = inventory(r["path"] for r in baseline)
    mismatches = [{"before": a, "after": b} for a, b in zip(baseline, after) if a != b]
    assert git("rev-parse", "HEAD").decode().strip() == DELIVERY
    assert sha(PACKAGE.read_bytes()) == PACKAGE_SHA
    save("preservation.json", {"status": "PASS" if not mismatches else "FAIL", "files_checked": len(baseline),
         "bytes_checked": sum(r["bytes"] for r in baseline), "mismatches": mismatches,
         "author_evidence_and_all_existing_worktree_paths_unchanged": not mismatches,
         "baseline_sha256": sha((OUT / "baseline-files.json").read_bytes()),
         "input_sha256_after": sha(PACKAGE.read_bytes()), "git_head_before_report_commit": DELIVERY})
    assert not mismatches
    print("PASS_PRESERVATION: %d existing paths unchanged" % len(baseline))


if __name__ == "__main__":
    assert os.environ.get("GIT_NO_LAZY_FETCH") == "1"
    assert ROOT == Path("C:/Users/ASUS/.codex/worktrees/a08-readonly-review/1800")
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("preflight", "run", "preserve"))
    phase = parser.parse_args().phase
    if phase == "preflight":
        preflight()
    elif phase == "preserve":
        preserve()
    else:
        sys.exit(run())
