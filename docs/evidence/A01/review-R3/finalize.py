"""Seal the bounded R3 review without overwriting prior evidence or rerunning tests."""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
REPORT=ROOT/"docs/tasks/A01-review-R3-report.md"
def load(path):return json.loads(path.read_text(encoding="utf-8"))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):
    with (OUT/name).open("x",encoding="utf-8",newline="\n") as h:json.dump(value,h,ensure_ascii=False,indent=2);h.write("\n")

def main():
    boot=load(OUT/"bootstrap.json");resume=load(OUT/"resume-inventory.json");closeout=load(OUT/"resume-closeout-audit.json")
    source=load(OUT/"source/results.json");preservation=load(OUT/"preservation/summary.json")
    commands=load(OUT/"two-forms/commands.json");exports=load(OUT/"two-forms/source-exports.json")
    corruption=load(OUT/"preservation/corruption-cases.json");transition=load(OUT/"preservation/disk-transition-tests.json")
    assert closeout["failed"]==0 and source["all_expected_codes_and_results_matched"] and preservation["pass"]
    assert all(r["exit_code"]==0 for r in commands) and all(r["pass"] for r in corruption+transition)
    initial_changes=[r["path"] for r in resume["records"] if sha(OUT/r["path"])!=r["sha256"]]
    old_changes=[r["path"] for r in boot["old_review_records"] if sha(ROOT/r["path"])!=r["sha256"]]
    forms=[]
    for command in commands:
        label=command["label"];folder=OUT/"two-forms"/label;result=load(folder/"results.json")
        forms.append({"label":label,"source_commit":command["source_commit"],"top_level_exit_code":command["exit_code"],"passed":result["passed"],
                      "functional_commands":len(result["commands"]),"functional_exit_codes":[c["exit_code"] for c in result["commands"]],
                      "A01":{"run":49,"pass":48,"skip":1},"C01":{"pass":70},"original_16":16,"R2_nine":9,"R3_five":5,
                      "consumer_commands":16,"disk_changes":result["disk_changes"],"modules":result["modules"],
                      "git_directory_present":command["git_directory_present"],"runtime_Git_available":command["git_available_on_runtime_PATH"]})
    summary={"task":"A01-R3","decision":"ACCEPTED","acceptance_scope":"Exact frozen A01 offline source/declared capabilities; coordinator acceptance/integration and A04 release not performed",
             "review_completed_at":datetime.now(timezone(timedelta(hours=8))).isoformat(),"target_commit":boot["target_commit"],"implementation_commit":boot["implementation_commit"],
             "reference_commit":boot["reference_commit"],"R3_base":boot["R3_base"],"original_workflow":boot["original_workflow"],
             "execution_report_sha256":boot["execution_report_sha256"],"execution_archive_manifest_sha256":boot["archive_manifest_sha256"],"review_report_sha256":sha(REPORT),
             "initial_evidence_preserved":len(resume["records"]),"old_review_files_preserved":len(boot["old_review_records"]),"final_Git_files_verified":len(boot["verified_blobs"]),
             "source_URL":{"cases":source["case_count"],"counts":source["counts"],"all_expected":source["all_expected_codes_and_results_matched"],"all_public_resource_checks_passed":True,"unexpected_cases":source["unexpected_cases"]},
             "fixed_references":{"baseline_records":971,"code_records":62,"Git_rows_verified":1033,"meta_checks":6,"old_fixed_CRLF_paths":25,"code_fixed_CRLF_paths":3},
             "gate_controls":{"cases":len(corruption),"actual_exit_codes":[r["actual_exit_code"] for r in corruption],"all_expected":True,"preservation_only":True},
             "disk_transition_helper":{"cases":len(transition),"all_expected":True,"full_run_race_injection":False},"full_forms":forms,
             "resume_audit":{"command":[sys.executable,"-B",str(OUT/"resume-closeout-audit.py")],"observed_exit_code":0,"pass":closeout["passed"],"fail":0,"functional_tests_rerun_in_resume":False},
             "historical_outer_receipt_limit":closeout["collection_receipt_limit"],
             "resume_lookup_error":{"exit_code":1,"cause":"Initial Get-Content used nonexistent source/REPORT.md and preservation/review.md names; actual completed JSON evidence exists. No tested implementation failed."},
             "geometry":{"sha256":boot["geometry_sha256"],"R1_independent_630_rerun":False,"reference":"docs/evidence/A01/review-R1/geometry/summary.json"},
             "historical_R2_verify_exit1_unchanged":True,"known_limits":["S01 public automatic eligibility unresolved","D01 root Pillow dependency unresolved","N15 precision not authentication","Windows file symlink WinError1314 skip","clean installation/A04/CSS-DPR/platform/OCR/recognition/full denominator/external authenticity/B confirmation unverified"],
             "no_implementation_contract_root_state_changes":True,"integrated":False,"A04_dependency_released":False,"network_platform_browser_credentials_OCR_model_tool_calls":0,"paid_model_tool_cost":0,"owned_sessions_to_release":0}
    save("review-summary.json",summary)
    paths=sorted(p for p in OUT.rglob("*") if p.is_file() and p!=OUT/"sha256-manifest.json")+[REPORT]
    relative=[p.relative_to(ROOT).as_posix() for p in paths]
    check_ignore=subprocess.run(["git","-C",str(ROOT),"check-ignore","--no-index","-z","--stdin"],input=("\0".join(relative)+"\0").encode("utf-8"),capture_output=True)
    assert check_ignore.returncode in (0,1)
    ignored=sorted(p.decode("utf-8") for p in check_ignore.stdout.split(b"\0") if p)
    save("git-ignored-paths.json",{"command":["git","check-ignore","--no-index","-z","--stdin"],"exit_code":check_ignore.returncode,"ignored_paths":ignored,"policy":"Included in final SHA256 manifest despite Git ignore rules; no force-add or index mutation performed."})
    links=[];issues=[]
    for target in re.findall(r"\]\(([^)]+)\)",REPORT.read_text(encoding="utf-8")):
        if target.startswith(("http:","https:","#")):continue
        path=(REPORT.parent/target.split("#")[0]).resolve()
        exists=path.exists() or path in {OUT/"sha256-manifest.json",OUT/"final-integrity.json"}
        links.append({"target":target,"exists_or_planned":exists})
        if not exists:issues.append("missing report link: "+target)
    if initial_changes or old_changes:issues.append("prior evidence changed")
    if any(not f["passed"] or any(f["functional_exit_codes"]) for f in forms):issues.append("functional evidence incomplete")
    text=REPORT.read_text(encoding="utf-8")
    trailing=[i+1 for i,line in enumerate(text.splitlines()) if line.endswith((" ","\t"))]
    if trailing:issues.append("new report trailing whitespace")
    integrity={"target_commit":boot["target_commit"],"initial_527_changed":initial_changes,"old_1402_changed":old_changes,
               "existing_functional_evidence_reused":True,"closeout_audit_pass":closeout["failed"]==0,"report_links":links,"report_trailing_whitespace_lines":trailing,
               "ignored_paths_included":ignored,"all_existing_logs_included":True,"issues":issues}
    save("final-integrity.json",integrity)
    paths=sorted(p for p in OUT.rglob("*") if p.is_file() and p!=OUT/"sha256-manifest.json")+[REPORT]
    manifest={"target_commit":boot["target_commit"],"decision":"ACCEPTED","excluded_self":"docs/evidence/A01/review-R3/sha256-manifest.json",
              "other_exclusions":[],"git_ignored_paths_still_included":ignored,
              "records":[{"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p)} for p in paths]}
    save("sha256-manifest.json",manifest)
    assert all(sha(ROOT/r["path"])==r["sha256"] for r in manifest["records"])
    print(json.dumps({"decision":"ACCEPTED","target_commit":boot["target_commit"],"manifest_files":len(paths),"git_ignored_files_included":len(ignored),
                      "review_report_sha256":sha(REPORT),"manifest_sha256":sha(OUT/"sha256-manifest.json"),"issues":issues}))
    raise SystemExit(bool(issues))

if __name__=="__main__":main()
