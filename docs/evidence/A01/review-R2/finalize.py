"""Verify all review producers and seal R2 evidence with explicit self exclusion."""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
REPORT=ROOT/"docs/tasks/A01-review-R2-report.md"
def load(path):return json.loads(path.read_text(encoding="utf-8"))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,data):
    with (OUT/name).open("x",encoding="utf-8",newline="\n") as handle:json.dump(data,handle,ensure_ascii=False,indent=2);handle.write("\n")

def main():
    boot=load(OUT/"bootstrap.json");snapshot=Path(boot["snapshot"])
    ordinary=Path(boot["temporary_root"])/"verified author source"
    source_changes={str(folder):[r["path"] for r in boot["verified_blobs"] if sha(folder/r["path"])!=r["sha256"]] for folder in (snapshot,ordinary)}
    tracked={r["path"] for r in boot["verified_blobs"]}
    extras={str(folder):[p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p.relative_to(folder).as_posix() not in tracked] for folder in (snapshot,ordinary)}
    old_changes=[r["path"] for r in boot["old_review_records"] if sha(ROOT/r["path"])!=r["sha256"]]
    child_checks=[]
    for name in ("partition","source"):
        folder=OUT/name;manifest_path=folder/"sha256-manifest.json";m=load(manifest_path)
        entries=m if isinstance(m,list) else m.get("files",m.get("records"))
        if isinstance(entries,dict):entries=[{"path":p,"sha256":s} for p,s in entries.items()]
        mismatches=[r["path"] for r in entries if sha(folder/r["path"])!=r["sha256"]]
        child_checks.append({"folder":name,"manifest_sha256":sha(manifest_path),"entries":len(entries),"mismatches":mismatches})
    commands=load(OUT/"reproduction/commands.json")
    author=load(OUT/"reproduction/author-verify-results.json")
    preservation=load(OUT/"preservation-relocation/results.json")
    partition=load(OUT/"partition/summary.json")
    source=load(OUT/"source/results.json")
    primary=load(OUT/"primary-url-path/results.json")
    summary={"task":"A01-R2","decision":"REWORK","reviewed_at":datetime.now(timezone(timedelta(hours=8))).isoformat(),
             "target_commit":boot["target_commit"],"implementation_commit":boot["implementation_commit"],"R2_base":boot["R2_base"],"original_base_workflow":boot["original_base_workflow"],
             "execution_report_sha256":boot["report_sha256"],"archive_manifest_sha256":boot["archive_manifest_sha256"],"review_report_sha256":sha(REPORT),
             "temporary_root":boot["temporary_root"],"top_level_commands":len(commands),"top_level_command_exit_codes":[r["exit_code"] for r in commands],
             "author_results":{"A01_pass":40,"A01_skip":1,"C01_pass":70,"original_16_pass":16,"R2_nine_pass":9,"verify_functional_commands":len(author["commands"]),
                               "verify_functional_exit_codes":[r["exit_code"] for r in author["commands"]],"verify_final_exit_code":1,"verify_failure":"25 preservation hashes bind checkout EOL, not raw Git bytes; all 25 differences independently explained by LF/CRLF"},
             "independent_preservation":{"pass":preservation["passed"],"fail":preservation["failed"],"old_Git_files":886,"original_inputs":31,"main_inputs":7,"relocated_packages":6,"archive_entries":87,"EOL_only_baseline_differences":len(preservation["author_disk_baseline_EOL_differences"])},
             "partition":{"conclusion":"ACCEPTED bounded","pass":partition["pass"],"fail":partition["fail"],"legal_cases":partition["legal_cases"],"source_rejection_cases":partition["source_rejection_cases"],"public_controls":partition["public_control_cases"]},
             "source":{"conclusion":"R2-02 REWORK; R2-03 ACCEPTED bounded","cases":len(source["cases"]),
                       "counts":source["counts"],"matches_expectation":sum(r["matches_expectation"] for r in source["cases"]),
                       "unexpected_cases":source["unexpected_cases"],"all_public_resource_checks_passed":source["all_public_resource_checks_passed"]},
             "primary_URL_path":{"passed":primary["passed"],"failed":primary["failed"],"expected_script_exit_code":1},
             "remaining_bounded_gap":"R2-02 regex reads whole URL; query/fragment suffix masks actual path book/index conflict",
             "geometry":{"sha256":boot["geometry_sha256"],"independent_630_rerun":False,"reference":boot["geometry_reference"],"note":"Author suite geometry unit checks did run; prior independent 630 matrix only referenced after byte verification"},
             "known_limits":["S01 public completeness gate unresolved","D01 root Pillow dependency unresolved","N15 precision is not authentication","Windows file symlink skipped WinError1314","clean installation and A04/CSS-DPR/platform/OCR/algorithm/whole-book denominator/B confirmation unverified"],
             "command_results":[{"command":[sys.executable,"-B",str(OUT/"bootstrap.py")],"exit_code":0},
                                {"command":[sys.executable,"-B",str(OUT/"reproduce.py")],"exit_code":1},
                                {"command":[sys.executable,"-B",str(OUT/"preservation-relocation.py")],"exit_code":0},
                                {"command":[sys.executable,"-B",str(OUT/"primary-url-path.py")],"exit_code":1}],
             "integrated":False,"A04_dependency_released":False,"implementation_contract_state_changed":False,"network_browser_platform_OCR_model_tool_calls":0,"paid_model_tool_cost":0}
    save("review-summary.json",summary)
    issues=[];links=[]
    for target in re.findall(r"\]\(([^)]+)\)",REPORT.read_text(encoding="utf-8")):
        if target.startswith(("http:","https:","#")):continue
        path=(REPORT.parent/target.split("#")[0]).resolve()
        exists=path.exists() or path in {OUT/"final-integrity.json",OUT/"sha256-manifest.json"}
        links.append({"target":target,"exists_or_planned":exists})
        if not exists:issues.append("missing report link: "+target)
    if any(source_changes.values()) or any(extras.values()) or old_changes or any(c["mismatches"] for c in child_checks):issues.append("integrity mismatch or unexpected source file")
    integrity={"target_commit":boot["target_commit"],"verified_files_per_source":len(tracked),"source_file_changes":source_changes,"non_Git_source_files":extras,
               "old_review_files":len(boot["old_review_records"]),"changed_old_review_files":old_changes,"child_manifests":child_checks,"report_links":links,"issues":issues}
    save("final-integrity.json",integrity)
    paths=sorted(p for p in OUT.rglob("*") if p.is_file() and p!=OUT/"sha256-manifest.json")+[REPORT]
    save("sha256-manifest.json",{"target_commit":boot["target_commit"],"decision":"REWORK","excluded_self":"docs/evidence/A01/review-R2/sha256-manifest.json",
                                 "records":[{"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p)} for p in paths]})
    print(json.dumps({"decision":"REWORK","verified_files_per_source":len(tracked),"old_review_files_preserved":len(boot["old_review_records"]),"evidence_files":len(paths),
                      "review_report_sha256":sha(REPORT),"manifest_sha256":sha(OUT/"sha256-manifest.json"),"issues":issues}))
    raise SystemExit(bool(issues))

if __name__=="__main__":main()
