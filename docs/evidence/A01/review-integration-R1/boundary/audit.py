"""Read-only exact-Git boundary reasoning and existing real-import trace checks."""
import base64
import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(r"D:\1800")
OUT = Path(__file__).resolve().parent
EVIDENCE = OUT.parent
FINAL = "5f872150a237b195f73c78e02e13a91d2f4f46a7"
REFERENCE = "c3aff9598b6705ab4122062615a13ae3774698b2"
EXPECTED_MANIFEST = "9ea7a71204c0417b16b232511010a781ad5a9c001287cc89c059b87a2b6ec795"
commands = []


def git_blob(commit, path):
    argv = ["git", "-C", str(REPO), "show", commit + ":" + path]
    process = subprocess.run(argv, capture_output=True)
    commands.append(dict(argv=argv, exit_code=process.returncode,
                         stdout_sha256=hashlib.sha256(process.stdout).hexdigest(),
                         stdout_bytes=len(process.stdout),
                         stderr=process.stderr.decode("utf-8", "replace")))
    if process.returncode:
        raise RuntimeError(commands[-1])
    return process.stdout


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


raw_manifest = git_blob(FINAL, "tests/fixtures/a01/R3/preservation-manifest.json")
manifest = json.loads(raw_manifest)
fixture = json.loads(git_blob(FINAL, "tests/fixtures/a01/integration-R1/reference.json"))
assert sha(raw_manifest) == EXPECTED_MANIFEST
assert manifest["reference_commit"] == fixture["reference_commit"] == REFERENCE
assert fixture["source_manifest_sha256"] == EXPECTED_MANIFEST
original = {entry["path"]: entry for entry in manifest["files"]}
assert len(original) == len(manifest["files"]) == 971
assert sum(len(entry["representations"]) > 1 for entry in manifest["files"]) == 25
fixed = []
for encoded in fixture["files"]:
    entry = {key: value for key, value in encoded.items() if key != "git_original_base64"}
    data = base64.b64decode(encoded["git_original_base64"], validate=True)
    git_data = git_blob(REFERENCE, entry["path"])
    oid = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    assert entry == original[entry["path"]]
    assert data == git_data
    assert sha(data) == entry["git_sha256"]
    assert oid == entry["git_blob_oid"]
    fixed.append(dict(path=entry["path"], bytes=len(data), sha256=sha(data), git_blob_oid=oid,
                      equals_original_metadata=True, equals_reference_commit_blob=True))
assert len(fixed) == 4
assert {row["path"] for row in fixed} == {
    "docs/coordination.md", "examples/a01/build.py", "tests/test_contracts.py",
    "tests/fixtures/contracts/normal/assets/asset-page-a1.pgm"}

identity_source = git_blob("4946b8ab307f88bdc25c14ace5ead774e3119fc5", "examples/a02/R1/identity.py")
a02_test = git_blob("4946b8ab307f88bdc25c14ace5ead774e3119fc5", "tests/test_a02_r1.py")
assert b'subprocess.run(["git", "rev-parse", "--show-toplevel"]' in identity_source
assert b"FileNotFoundError" not in identity_source
assert b"test_export_subdirectory_cannot_borrow_enclosing_git_head" in a02_test
runtime = []
required = {
    "src/annotation/source/static/importer.py", "src/annotation/source/static/consistency.py",
    "src/annotation/geometry/__init__.py", "src/annotation/contracts/models.py",
    "tests/test_a01_rework_r3.py", "tests/test_a01_integration_r1.py"}
for label in ("checkout", "raw"):
    folder = EVIDENCE / "runtime" / label
    launches_path = folder / "imports/launches.json"
    if not launches_path.exists():
        runtime.append(dict(label=label, status="pending root runtime completion"))
        continue
    launches = json.loads(launches_path.read_text(encoding="utf-8"))
    rows = []
    for index, launch in enumerate(launches, start=1):
        child = json.loads((folder / "imports" / ("%02d.json" % index)).read_text(encoding="utf-8"))
        assert launch["original_argv"][2:] == child["original_python_arguments"]
        assert Path(launch["cwd"]).resolve() == Path(child["cwd"]).resolve()
        for record in child["executed_modules"] + child["loaded_annotation_modules"]:
            rows.append(dict(trace=str(Path("runtime") / label / "imports" / ("%02d.json" % index)), **record))
    index_name = "checkout-input-index.json" if label == "checkout" else "raw-input-index.json"
    index = {row["path"]: row for row in json.loads((EVIDENCE / index_name).read_text(encoding="utf-8"))}
    by_relative = {}
    for row in rows:
        assert not row["relative"].startswith("OUTSIDE:"), row
        assert sha(Path(row["resolved_path"]).read_bytes()) == row["sha256"]
        fixed_index = index[row["relative"]]
        assert row["sha256"] == fixed_index.get("disk_sha256", fixed_index.get("sha256")), row
        by_relative.setdefault(row["relative"], []).append(row["trace"])
    assert required <= set(by_relative)
    assert len(launches) == 11
    command = json.loads((folder / "command.json").read_text(encoding="utf-8"))
    entry = json.loads((folder / "entry/results.json").read_text(encoding="utf-8"))
    runtime.append(dict(label=label, status="checked", launches=len(launches),
                        entry_exit_code=command["exit_code"], entry_passed=entry["passed"],
                        child_exit_codes=[dict(label=row["label"], exit_code=row["exit_code"]) for row in entry["commands"]],
                        required_real_module_files={path: sorted(set(by_relative[path])) for path in sorted(required)},
                        all_recorded_annotation_files_inside_snapshot=True,
                        actual_observation_bytes_match_current_frozen_input=True,
                        actual_observation_bytes_match_preexecution_fixed_input_index=True,
                        source="external profiler of module frame __file__ plus loaded sys.modules; not author source_files"))

minimal = []
for label, expected in (("minimal-with-git", 0), ("minimal-without-git", 1)):
    path = EVIDENCE / "git-availability" / label / "command.json"
    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["exit_code"] == expected and row["has_dot_git"] is False
    assert row["observer"] == "none; direct original Python command"
    minimal.append(dict(label=label, command_json=str(path.relative_to(EVIDENCE)),
                        command_sha256=sha(path.read_bytes()), exit_code=row["exit_code"],
                        git_executable=row["git_executable"], has_dot_git=row["has_dot_git"]))

result = dict(final_commit=FINAL, frozen_reference=REFERENCE, fixed_originals=fixed,
              bounded_acceptance_recommendation="REWORK: full required Git-free entry exits 1; exact content identity safeguards otherwise remain bound",
              source_manifest_sha256=EXPECTED_MANIFEST,
              original_policy=dict(files=971, explicit_CRLF_candidates=25),
              reference_commit_label=dict(asserted_by_conventional_suite=False,
                  actual_frozen_value_correct=True, effect_of_label_only_edit="Returned provenance label changes; accepted bytes, Git blob IDs, original manifest SHA and finite representations do not change.",
                  acceptance_significance="Non-blocking provenance-label omission for this bounded acceptance, because original identity and all four fixed originals are already bound by independent exact SHA/entry assertions. Do not claim this redundant label has a rejection test."),
              git_free_entry_dependency=dict(blocking=True,
                  call_chain="integration-R1/verify.py always runs A02 unittest discovery -> test_a02_r1.py calls identity.git_identity -> unhandled subprocess git launch when executable absent",
                  inherited_unchanged_A02_does_not_remove_new_entry_dependency=True,
                  no_dot_git_differs_from_no_git_executable=True,
                  full_suite_cannot_be_replaced_by_focused_mode=True,
                  identity_source_sha256=sha(identity_source), a02_test_sha256=sha(a02_test),
                  acceptance_basis="Exact delivery report claims no Git dependency; review handoff required relocated Git-free execution. Current raw runtime exits 1 with missing executable while other children still run."),
              runtime=runtime, original_A02_minimal_command_comparison=minimal,
              read_commands=commands, functional_test_commands_run_by_this_script=0,
              network_browser_platform_credentials_model_calls=0,
              subprocess_sessions_to_release=0)
with (OUT / "result.json").open("w", encoding="utf-8", newline="\n") as handle:
    handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(dict(fixed_originals=len(fixed), commands=len(commands), runtime=runtime), ensure_ascii=False))
