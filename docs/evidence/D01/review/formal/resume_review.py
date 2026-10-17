"""Add one missing fixed helper and continue only unfinished review closeout."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent


def main():
    spec=importlib.util.spec_from_file_location("review_tools",ROOT/"run_review.py")
    tools=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tools)
    resume=ROOT/"resume01"
    resume.mkdir(exist_ok=False)
    tools.EVIDENCE=resume
    receipt=json.loads((ROOT/"receipt.json").read_text(encoding="utf-8"))
    outside=Path(receipt["outside_root"])
    tools.ENV.update(TMP=str(outside/"tmp"),TEMP=str(outside/"tmp"))
    python=Path(receipt["exclusive_stage"])/"cp39/Scripts/python.exe"
    regression=outside/"fixed regression no source"
    path="examples/contracts/build_fixtures.py"
    assert not (regression/path).exists()
    frozen_oid=tools.git("helper-frozen-oid","rev-parse",tools.DELIVERY+":"+path).decode().strip()
    base_oid=tools.git("helper-base-oid","rev-parse",tools.BASE+":"+path).decode().strip()
    assert frozen_oid==base_oid
    raw=tools.git("helper-raw","cat-file","blob",frozen_oid)
    assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==frozen_oid
    (regression/path).write_bytes(raw)
    (resume/"build_fixtures.py").write_bytes(raw)
    tools.write(resume/"supplemental-input-index.json",[dict(commit=tools.DELIVERY,base_commit=tools.BASE,path=path,git_blob_oid=frozen_oid,sha256=tools.sha(raw),bytes=len(raw),destination=str(regression/path),reason="Reviewer fixture export omitted consumer helper; fixed Git bytes only")])
    tools.run("rerun-one-contract-test",[python,"-I",ROOT/"resume_probe.py",ROOT/"probe.py",regression,resume/"one-test-result.json"],outside)
    original=json.loads((ROOT/"contract-regression.json").read_text(encoding="utf-8"))
    fixed=json.loads((resume/"one-test-result.json").read_text(encoding="utf-8"))
    assert original["tests_run"]==70 and original["failures"]==2 and original["errors"]==0
    assert fixed["successful"] and fixed["tests_run"]==1 and not fixed["skipped"]
    tools.write(resume/"reviewer-correction.json",dict(cause="Reviewer exported examples/contracts/consume.py without its build_fixtures.py helper.",
         first_actual_result="70 tests executed; one test method had two failing subprocess subtests, both ModuleNotFoundError: build_fixtures.",
         resolution="Added only exact base/frozen Git helper bytes; reran only the one affected test method with original assertions unchanged.",
         first_failure_preserved=["commands/28-contract-regression","contract-regression.json","attempt-failure.json","collector-run01"],
         rerun_result=fixed,product_changed=False,venv_reused="Only the independent new review environment; no reinstall or successful feature replay."))
    source_index=json.loads((ROOT/"source-index.json").read_text(encoding="utf-8"))
    regression_index=json.loads((ROOT/"regression-input-index.json").read_text(encoding="utf-8"))
    sample_index=json.loads((ROOT/"sample-index.json").read_text(encoding="utf-8"))
    protected=json.loads((ROOT/"preparation-before.json").read_text(encoding="utf-8"))
    preparation=tools.WORKSPACE/"docs/evidence/D01/review/preparation"
    assert tools.files(preparation)==protected["files"]
    assert tools.sha((tools.WORKSPACE/"docs/tasks/D01-review-preparation.md").read_bytes())==protected["report_sha256"]
    for item in source_index+regression_index+sample_index:
        assert tools.sha(Path(item["destination"]).read_bytes())==item["sha256"],item["path"]
    expected={item["path"]:dict(bytes=item["bytes"],sha256=item["sha256"]) for item in sample_index}
    relocated=outside/"relocated R3 packages with spaces"
    assert tools.files(relocated)==expected
    assert tools.sha((regression/path).read_bytes())==tools.sha(raw)
    tools.write(ROOT/"post-run-preservation.json",dict(preparation_files_unchanged=len(protected["files"]),preparation_report_unchanged=True,
         source_input_files_unchanged=len(source_index),regression_input_files_unchanged=len(regression_index),supplemental_fixed_helper_unchanged=True,
         original_sample_files_unchanged=len(sample_index),relocated_sample_files_unchanged=len(sample_index),
         original_samples=expected,relocated_samples=tools.files(relocated)))
    initial_commands=json.loads((ROOT/"commands.json").read_text(encoding="utf-8"))
    assert all(r["synchronous_return"] for r in initial_commands+tools.COMMANDS)
    assert [r["label"] for r in initial_commands if r["exit_code"]!=r["expected_exit_code"]]==["contract-regression"]
    tools.write(ROOT/"run-result.json",dict(result="INDEPENDENT_REQUIRED_CHECKS_PASSED_AFTER_REVIEW_FIXTURE_CORRECTION",base=tools.BASE,
        implementation=tools.IMPLEMENTATION,delivery=tools.DELIVERY,workflow=tools.WORKFLOW,
        first_commands=len(initial_commands),resume_commands=len(tools.COMMANDS),all_commands_returned=True,expected_rejection_subprocesses=6,
        reviewer_fixture_failure_preserved=True,only_failed_contract_method_rerun=True,product_defects_found=0,
        scope="CPython3.9 Windows only; finite REFERENCE_ONLY packages; independent acceptance report and coordinator integration remain separate."))
    print(json.dumps(dict(result="RESUME_COMPLETE",rerun_tests=1,first_commands=len(initial_commands),resume_commands=len(tools.COMMANDS))))


if __name__=="__main__":
    if "--inner" in sys.argv:
        try:
            main()
        except BaseException as error:
            (ROOT/"resume-attempt-failure.json").write_bytes((json.dumps(dict(error=str(error),traceback=traceback.format_exc()),indent=2)+"\n").encode())
            raise
    else:
        target=ROOT/"collector-resume01"
        target.mkdir(exist_ok=False)
        for name in ("resume_review.py","resume_probe.py"):
            (target/name).write_bytes((ROOT/name).read_bytes())
        argv=[sys.executable,"-I",str(Path(__file__).resolve()),"--inner"]
        started=time.time()
        process=subprocess.Popen(argv,cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout,stderr=process.communicate()
        (target/"stdout.bin").write_bytes(stdout)
        (target/"stderr.bin").write_bytes(stderr)
        record=dict(argv=argv,cwd=str(ROOT),pid=process.pid,collector_pid=__import__("os").getpid(),started_unix=started,finished_unix=time.time(),exit_code=process.returncode,
                    synchronous_return=True,stdout_sha256=hashlib.sha256(stdout).hexdigest(),stderr_sha256=hashlib.sha256(stderr).hexdigest())
        (target/"command.json").write_bytes((json.dumps(record,indent=2,sort_keys=True)+"\n").encode())
        print(stdout.decode("utf-8",errors="replace"),end="")
        print(stderr.decode("utf-8",errors="replace"),end="",file=sys.stderr)
        print(json.dumps(record))
        raise SystemExit(process.returncode)
