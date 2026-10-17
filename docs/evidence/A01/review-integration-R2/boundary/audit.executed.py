"""Read-only boundary audit for fixed integration-R2; no functional re-execution."""
import argparse
import base64
import hashlib
import json
import re
import subprocess
from pathlib import Path

REPO = Path(r"D:\1800")
OUT = Path(__file__).resolve().parent
EVIDENCE = OUT.parent
WORKFLOW = "fe91c27939d13f9be290f8274a0d46d90f4de2f0"
MAIN = "2d1dc8b97713ee06ec5bf35febe0b894ece584b2"
A01 = "5f872150a237b195f73c78e02e13a91d2f4f46a7"
TREE = "0645ac862f79fb4e232e4cfbd5f6bb5055a68d62"
OLD_REFERENCE = "c3aff9598b6705ab4122062615a13ae3774698b2"
commands = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args, repo=REPO):
    argv = ["git", "-C", str(repo), *map(str, args)]
    process = subprocess.run(argv, capture_output=True)
    commands.append(dict(argv=argv, exit_code=process.returncode,
                         stdout_sha256=sha(process.stdout), stdout_bytes=len(process.stdout),
                         stderr=process.stderr.decode("utf-8", "replace")))
    assert process.returncode == 0, commands[-1]
    return process.stdout


def blob(commit, path):
    return git("show", commit + ":" + path)


def tree_files(commit):
    result = {}
    for row in git("ls-tree", "-rz", commit).split(b"\0"):
        if row:
            metadata, path = row.split(b"\t", 1)
            mode, kind, oid = metadata.decode("ascii").split()
            result[path.decode("utf-8")] = dict(mode=mode, kind=kind, oid=oid)
    return result


def selected_a01(path):
    return (path.startswith(("src/annotation/source/static/", "src/annotation/geometry/",
                             "examples/a01/", "tests/fixtures/a01/"))
            or path.startswith("tests/test_a01") and path.endswith(".py"))


def static_audit():
    bootstrap = json.loads((EVIDENCE / "bootstrap.json").read_text(encoding="utf-8"))
    assert bootstrap["workflow"] == WORKFLOW
    assert bootstrap["main_parent"] == MAIN and bootstrap["A01_delivery"] == A01
    assert bootstrap["integration_tree"] == TREE
    checkout = Path(bootstrap["checkout"])
    temp = bootstrap["temporary_commit"]
    actual = git("show", "-s", "--format=%P%n%T", temp, repo=checkout).decode("ascii").splitlines()
    assert actual == [MAIN + " " + A01, TREE], actual
    handoff = blob(WORKFLOW, "docs/tasks/A01-integration-R2-review-handoff.md")
    assert handoff == (EVIDENCE / "frozen-handoff.md").read_bytes()
    assert sha(handoff) == bootstrap["handoff_sha256"]
    merged, frozen, main = tree_files(TREE), tree_files(A01), tree_files(MAIN)
    expected_a01 = {path: value for path, value in frozen.items() if selected_a01(path)}
    actual_a01 = {path: value for path, value in merged.items() if selected_a01(path)}
    assert actual_a01 == expected_a01
    a02_paths = ("examples/a02/R1/identity.py", "tests/test_a02_r1.py", "tests/test_a02_portability_r2.py")
    for path in a02_paths:
        assert merged[path] == main[path]
    for path in (".gitattributes", ".gitignore", "pyproject.toml"):
        assert merged[path] == main[path]

    policy_path = "tests/fixtures/a01/R3/preservation-manifest.json"
    code_path = "tests/fixtures/a01/R3/code-reference.json"
    fixture_path = "tests/fixtures/a01/integration-R1/reference.json"
    policy_raw, code_raw, fixture_raw = (blob(A01, path) for path in (policy_path, code_path, fixture_path))
    policy, code, fixture = map(json.loads, (policy_raw, code_raw, fixture_raw))
    assert sha(policy_raw) == "9ea7a71204c0417b16b232511010a781ad5a9c001287cc89c059b87a2b6ec795"
    assert policy["reference_commit"] == OLD_REFERENCE
    assert len(policy["files"]) == len({row["path"] for row in policy["files"]}) == 971
    assert sum(len(row["representations"]) > 1 for row in policy["files"]) == 25
    assert len(code["files"]) == 62
    assert sum(len(row["representations"]) > 1 for row in code["files"]) == 3
    assert len(fixture_raw) == 86374
    assert sha(fixture_raw) == "51e2fd08803cfc918f62a23327da99993bf2a91363ef2ec3960f37765ee241db"
    author_representation = fixture_raw.replace(b"\n", b"\r\n")
    assert len(author_representation) == 86438
    assert sha(author_representation) == "9b979d4b18ffe4db50ad5473c218ba28fdcbed0515d68ce324894be09cc2d0eb"
    originals = {row["path"]: row for row in policy["files"]}
    fixed = []
    for source in fixture["files"]:
        entry = {key: value for key, value in source.items() if key != "git_original_base64"}
        data = base64.b64decode(source["git_original_base64"], validate=True)
        oid = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        assert entry == originals[entry["path"]]
        assert data == blob(OLD_REFERENCE, entry["path"])
        assert sha(data) == entry["git_sha256"] and oid == entry["git_blob_oid"]
        fixed.append(dict(path=entry["path"], oid=oid, sha256=sha(data), bytes=len(data)))
    assert len(fixed) == 4
    assert fixture["reference_commit"] == OLD_REFERENCE
    assert fixture["source_manifest_sha256"] == sha(policy_raw)
    return dict(workflow=WORKFLOW, main_parent=MAIN, A01_delivery=A01, integration_tree=TREE,
                observed_temporary_commit=temp, observed_parent_order=actual[0].split(),
                selected_A01_paths_unchanged=len(expected_a01),
                A02_dependency_paths_from_new_main={path: merged[path] for path in a02_paths},
                root_attributes_and_dependencies_from_new_main=True,
                policy=dict(path=policy_path, sha256=sha(policy_raw), files=971, finite_CRLF_candidates=25),
                code_policy=dict(path=code_path, sha256=sha(code_raw), files=62, finite_CRLF_candidates=3),
                fixed_originals=fixed,
                I04=dict(status="unchanged disclosed non-blocking limitation",
                         label_is_not_authenticated=True,
                         content_and_entry_identity_still_bound=True),
                fixture_representations=dict(Git=dict(bytes=len(fixture_raw), sha256=sha(fixture_raw)),
                                             original_author_manifest=dict(bytes=len(author_representation), sha256=sha(author_representation))),
                functional_regressions_run_by_this_subreview=0,
                network_browser_platform_credentials_model_calls=0,
                own_running_subprocesses_or_sessions=0)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def runtime_audit():
    bootstrap = read(EVIDENCE / "bootstrap.json")
    merged = tree_files(TREE)
    blob_cache = {}
    forms = []
    for label in ("checkout", "raw"):
        tree = Path(bootstrap[label]).resolve()
        folder = EVIDENCE / "runtime" / label
        index = {row["path"]: row for row in read(EVIDENCE / ("checkout-input-index.json" if label == "checkout" else "raw-input-index.json"))}
        launch = read(folder / "launch/command.json")
        entry = read(folder / "entry/results.json")
        launches = read(folder / "imports/launches.json")
        assert launch["exit_code"] == 0
        assert entry["passed"] is True
        assert len(entry["commands"]) == len(launches) == 11
        assert all(row["exit_code"] == 0 for row in entry["commands"])
        assert (tree / ".git").exists() is (label == "checkout")
        if label == "raw":
            assert launch["git_available"] is None
            assert launch["environment_selected"]["PATH"] == r"C:\Windows\System32;C:\Windows"
        counts = []
        for command, expected in zip(entry["commands"][:4], (52, 70, 62, 8)):
            found = re.search(r"Ran (\d+) tests?", command["stderr"])
            assert found and int(found[1]) == expected
            counts.append(dict(label=command["label"], ran=int(found[1]), exit_code=command["exit_code"],
                               skip_summary=re.findall(r"OK \(skipped=\d+\)", command["stderr"])))
        urls = read(folder / "entry/URL-replay/results.json")
        assert urls["passed"] == 5 and urls["failed"] == 0
        seen = {}
        annotation = {}
        generated = []
        probes = []
        for number, row in enumerate(launches, start=1):
            trace_path = folder / "imports" / ("%02d.json" % number)
            child = read(trace_path)
            assert Path(row["trace"]).resolve() == trace_path.resolve()
            assert row["original_argv"][2:] == child["original_python_arguments"]
            assert Path(row["cwd"]).resolve() == Path(child["cwd"]).resolve()
            assert Path(child["root"]).resolve() == tree
            assert row["executed_argv"][2:] == [str(EVIDENCE / "trace_child.py"), str(trace_path), str(tree), *child["original_python_arguments"]]
            probe = child["git_probe"]
            assert probe["argv"] == ["git", "--version"]
            assert Path(probe["cwd"]).resolve() == Path(child["cwd"]).resolve()
            if label == "raw":
                assert probe["which"] is None and probe["PATH"] == r"C:\Windows\System32;C:\Windows"
                assert probe["exception"] == "FileNotFoundError" and probe["actual_OS_spawn_failed"] is True
                assert probe["errno"] == 2
            else:
                assert probe["which"] and probe["exit_code"] == 0
            probes.append(dict(trace=trace_path.relative_to(EVIDENCE).as_posix(), **probe))
            for item in child["executed_modules"] + child["loaded_annotation_modules"]:
                if item["origin"] == "GENERATED_IDENTITY_COPY":
                    expected = index["examples/a02/R1/identity.py"]
                    assert item["sha256"] == expected.get("disk_sha256", expected.get("sha256"))
                    generated.append(dict(trace=trace_path.relative_to(EVIDENCE).as_posix(), **item))
                    continue
                relative = item["relative"]
                assert relative and not relative.startswith("OUTSIDE:")
                expected = index[relative]
                assert expected["oid"] == merged[relative]["oid"]
                assert item["sha256"] == expected.get("disk_sha256", expected.get("sha256"))
                assert Path(item["resolved_path"]).resolve() == (tree / relative).resolve()
                assert sha(Path(item["resolved_path"]).read_bytes()) == item["sha256"]
                if relative not in blob_cache:
                    blob_cache[relative] = blob(TREE, relative)
                original = blob_cache[relative]
                assert hashlib.sha1(b"blob " + str(len(original)).encode("ascii") + b"\0" + original).hexdigest() == merged[relative]["oid"]
                if label == "raw":
                    assert item["sha256"] == sha(original)
                else:
                    assert item["sha256"] in (sha(original), sha(original.replace(b"\n", b"\r\n")))
                    assert expected["git_sha256"] == sha(original)
                seen.setdefault(relative, []).append(trace_path.relative_to(EVIDENCE).as_posix())
                if item["module"] == "annotation" or item["module"].startswith("annotation."):
                    annotation[item["module"]] = dict(relative=relative, oid=merged[relative]["oid"], sha256=item["sha256"])
        required = {"src/annotation/source/static/importer.py", "src/annotation/source/static/consistency.py",
                    "src/annotation/geometry/__init__.py", "src/annotation/contracts/models.py",
                    "examples/a02/R1/identity.py", "tests/test_a02_r1.py", "tests/test_a02_portability_r2.py"}
        required.update(path for path in merged if path.startswith(("tests/test_a01", "tests/test_contracts")) and path.endswith(".py"))
        assert required <= set(seen)
        assert annotation
        forms.append(dict(label=label, full_entry_exit_code=launch["exit_code"], child_commands=11,
                          all_child_exit_zero=True, suites=counts, URL_cases=5, direct_and_relocated_consumers=6,
                          required_actual_files={path: sorted(set(seen[path])) for path in sorted(required)},
                          all_observed_annotation_modules=annotation,
                          all_actual_imports_match_before_index_and_frozen_tree=True,
                          generated_identity_copies=generated, real_child_git_probes=probes))

    bare = EVIDENCE / "bare-case"
    command = read(bare / "test/command.json")
    probe_command = read(bare / "environment-probe/command.json")
    probe = read(bare / "environment-probe/stdout.txt")
    stderr = (bare / "test/stderr.txt").read_text(encoding="utf-8", errors="replace")
    expected_arguments = ["-B", "-m", "unittest", "test_a02_r1.A02R1Tests.test_export_subdirectory_cannot_borrow_enclosing_git_head", "-v"]
    assert command["argv"][1:] == expected_arguments
    assert Path(command["cwd"]).resolve() == (Path(bootstrap["raw"]) / "tests").resolve()
    assert command["environment_selected"]["PYTHONPATH"] == str(Path(bootstrap["raw"]) / "src")
    assert command["environment_selected"]["PATH"] == r"C:\Windows\System32;C:\Windows"
    assert command["git_available"] is None and command["exit_code"] == 0
    assert re.search(r"Ran 1 test\b", stderr) and re.search(r"\bOK\b", stderr)
    assert not re.search(r"\bskipped\b", stderr, re.I)
    assert probe_command["exit_code"] == 0
    assert probe["which"] is None and probe["raw_has_dot_git"] is False
    assert probe["actual_OS_spawn_failed"] is True and probe["exception"] == "FileNotFoundError" and probe["errno"] == 2
    collector = read(EVIDENCE / "collector-runtime/command.json")
    assert collector["exit_code"] == 0
    assert collector["script_sha256_before"] == collector["script_sha256_after"] == sha((EVIDENCE / "run_forms.py").read_bytes())
    return dict(forms=forms,
                bare_original_I1_GIT_01=dict(exit_code=0, actual_test_count=1, skip=False, observer="none", real_no_Git_OS_probe=probe,
                                             command_receipt="bare-case/test/command.json"),
                collector_exit_code=collector["exit_code"],
                trace_semantics=dict(original_child_argv_and_cwd_preserved=True,
                    observer_adds_only_preexecution_Git_availability_probe_and_import_profile=True,
                    subprocess_error_or_unittest_assertions_not_rewritten=True,
                    runpy_reconstructs_module_or_script_sys_path_zero=True,
                    generated_identity_copies_recorded_and_bound_not_claimed_as_snapshot_paths=True,
                    actual_commands_are_observer_wrapped_not_bare_full_entry=True),
                recommendation="ACCEPTED for bounded fixed combination I1-GIT-01 closure; no main integration or dependent release")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("static", "final"), default="static")
    args = parser.parse_args()
    result = static_audit()
    if args.phase == "final":
        result["runtime"] = runtime_audit()
    else:
        result["runtime_status"] = "not counted; waiting for root frozen R2 runtime receipts"
    result.update(phase=args.phase, passed=True, read_only_commands=commands)
    with (OUT / (args.phase + ".json")).open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(phase=args.phase, selected_A01_paths_unchanged=result["selected_A01_paths_unchanged"],
                         fixed_originals=len(result["fixed_originals"]), read_only_commands=len(commands), passed=True)))


if __name__ == "__main__":
    main()
