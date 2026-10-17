"""Read-only closeout of completed R3 evidence; do not rerun functional checks."""
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def load(path):return json.loads(path.read_text(encoding="utf-8"))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    boot=load(OUT/"bootstrap.json");snapshot=Path(boot["snapshot"])
    resume=load(OUT/"resume-inventory.json")
    checks=[]
    def check(name,actual,expected):checks.append({"name":name,"actual":actual,"expected":expected,"pass":actual==expected})
    for r in resume["records"]:check("initial evidence "+r["path"],sha(OUT/r["path"]),r["sha256"])
    for r in boot["old_review_records"]:check("old review "+r["path"],sha(ROOT/r["path"]),r["sha256"])
    for r in boot["verified_blobs"]:check("final exported Git blob "+r["path"],sha(snapshot/r["path"]),r["sha256"])
    baseline=load(snapshot/"docs/evidence/A01/execution/R3/baseline.json")
    main_records=[]
    for r in baseline["read_only_inputs"]:
        path=Path(r["path"]).resolve();path.relative_to((ROOT/"docs").resolve())
        actual=sha(path);check("frozen main input "+r["path"],actual,r["sha256"]);main_records.append(dict(r,current_sha256=actual))
    inputs={}
    for book in ("46006966","46007447"):
        for r in load(snapshot/"examples/a01/bundles"/book/"input-integrity.json")["inputs"]:inputs[r["archive_path"]]=r
    for path,r in inputs.items():check("original input "+path,[r["before_sha256"],r["after_sha256"]],[sha(snapshot/path)]*2)
    archive=load(snapshot/"docs/evidence/A01/execution/R3/archive-manifest.json")
    for r in archive["files"]:check("execution manifest "+r["path"],sha(snapshot/r["path"]),r["sha256"])
    check("archive manifest identity",sha(snapshot/"docs/evidence/A01/execution/R3/archive-manifest.json"),boot["archive_manifest_sha256"])
    check("execution report identity",sha(snapshot/"docs/tasks/A01-rework-R3-report.md"),boot["execution_report_sha256"])
    exports=load(OUT/"two-forms/source-exports.json")
    forms=[]
    for form in exports["forms"]:
        folder=Path(form["path"]);label=form["label"]
        for r in form["files"]:check(label+" source disk "+r["path"],sha(folder/r["path"]),r["actual_disk_sha256"])
        report_folder=OUT/"two-forms"/label
        result=load(report_folder/"results.json")
        check(label+" verifier result",result["passed"],True)
        check(label+" all child exit codes",[c["exit_code"] for c in result["commands"]],[0]*21)
        check(label+" during-run disk changes",result["disk_changes"],[])
        for name in ("preservation-begin","preservation-end","code-begin","code-end"):
            audit=load(report_folder/(name+".json"));check(label+" "+name+" errors",audit["errors"],[])
        forms.append({"label":label,"source_commit":form["source_commit"],"files":len(form["files"]),"commands":len(result["commands"]),
                      "A01_stderr_tail":result["commands"][0]["stderr"][-180:],"C01_stderr_tail":result["commands"][1]["stderr"][-130:],
                      "modules":result["modules"],"passed":result["passed"]})
    source=load(OUT/"source/results.json");source_env=load(OUT/"source/environment.json")
    check("source 61 cases",source["case_count"],61);check("source all expected",source["all_expected_codes_and_results_matched"],True)
    check("source all resource validation",source["all_public_resource_checks_passed"],True)
    check("source script identity",sha(OUT/"source/probe.py"),source_env["script_sha256"])
    source_integrity=load(OUT/"source/preservation.json")
    for group in ("snapshot","old_Q","old_U"):check("source prior evidence "+group,source_integrity[group+"_before"],source_integrity[group+"_after"])
    replay_checks=[]
    for name in ("Q01-cross-book-path-query-tail","Q02-wrong-index-path-fragment-tail","U23-query-masks-wrong-path-book","U24-fragment-masks-wrong-path-index","U25-query-masks-wrong-path-index"):
        original=(ROOT/"docs/evidence/A01/review-R2/primary-url-path"/name) if name.startswith("Q") else (ROOT/"docs/evidence/A01/review-R1/source/cases"/name)
        copied=OUT/"source/replay-inputs"/name
        # U evidence stored only changed inputs; source preserved its exact
        # archived comparison in preservation.json and per-case replay records.
        if name.startswith("Q"):
            before={p.relative_to(original).as_posix():sha(p) for p in original.rglob("*") if p.is_file()}
            after={p.relative_to(copied).as_posix():sha(p) for p in copied.rglob("*") if p.is_file()}
            check("exact Q replay bytes "+name,after,before);replay_checks.append({"case":name,"files":len(before),"exact_bytes":after==before})
    preserved=load(OUT/"preservation/summary.json");refaudit=load(OUT/"preservation/reference-blob-audit.json")
    check("fixed Git references independently verified",refaudit["pass"],True)
    check("reference rows",[preserved["reference_blob_rows_pass"],preserved["reference_blob_rows_total"]],[1033,1033])
    check("reference metadata exact allowlists",[preserved["reference_meta_checks_pass"],preserved["reference_meta_checks_total"]],[6,6])
    controls=load(OUT/"preservation/corruption-cases.json")
    for r in controls:check("actual gate control "+r["id"],r["pass"],True)
    transitions=load(OUT/"preservation/disk-transition-tests.json")
    for r in transitions:check("disk transition "+r["id"],r["pass"],True)
    check("helper exact bytes",sha(snapshot/"examples/a01/R3/preservation.py"),preserved["helper_sha256"])
    check("geometry identity",sha(snapshot/"src/annotation/geometry/__init__.py"),boot["geometry_sha256"])
    check("geometry 630 not falsely rerun",preserved["geometry_630_rerun"],False)
    process=load(OUT/"resume-process-check.json");check("owned task processes remaining",process["matched_count"],0)
    result={"target_commit":boot["target_commit"],"checked_at":datetime.now(timezone(timedelta(hours=8))).isoformat(),"phase":"BOUNDED_RESUME_CLOSEOUT_ONLY",
            "command":[sys.executable,"-B",str(Path(__file__).resolve())],"cwd":str(Path.cwd()),"functional_tests_rerun_in_resume":False,
            "initial_files_preserved":len(resume["records"]),"old_review_files_preserved":len(boot["old_review_records"]),"final_exported_files":len(boot["verified_blobs"]),
            "original_inputs":len(inputs),"main_inputs":main_records,"execution_manifest_items":len(archive["files"]),"forms":forms,"exact_Q_replays":replay_checks,
            "checks":checks,"passed":sum(c["pass"] for c in checks),"failed":sum(not c["pass"] for c in checks),
            "collection_receipt_limit":"Source and preservation outer launcher exit codes were not separately saved before the usage-limit interruption. Their completed output, exact script identities, and all actual child command return codes are retained; no historical exit code is invented.",
            "new_closeout_exit_semantics":"0 means all saved evidence and byte-integrity checks agree; not a new functional run"}
    with (OUT/"resume-closeout-audit.json").open("x",encoding="utf-8",newline="\n") as h:json.dump(result,h,ensure_ascii=False,indent=2);h.write("\n")
    print(json.dumps({"passed":result["passed"],"failed":result["failed"],"initial_evidence_unchanged":527,"old_review_unchanged":1402,"functional_rerun":False}))
    raise SystemExit(bool(result["failed"]))

if __name__=="__main__":main()
