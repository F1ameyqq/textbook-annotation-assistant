"""Seal R1 review and verify old evidence remains unchanged."""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
REPORT=ROOT/"docs/tasks/A01-review-R1-report.md"

def load(path):return json.loads(path.read_text(encoding="utf-8"))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):
    with (OUT/name).open("x",encoding="utf-8",newline="\n") as handle:json.dump(value,handle,ensure_ascii=False,indent=2);handle.write("\n")

def main():
    boot=load(OUT/"bootstrap.json")
    snapshot=Path(boot["snapshot"])
    changed=[r["path"] for r in boot["verified_blobs"] if sha(snapshot/r["path"]) != r["sha256"]]
    tracked={r["path"] for r in boot["verified_blobs"]}
    extras=[p.relative_to(snapshot).as_posix() for p in snapshot.rglob("*") if p.is_file() and p.relative_to(snapshot).as_posix() not in tracked]
    old_changed=[r["path"] for r in boot["old_review_records"] if sha(ROOT/r["path"]) != r["sha256"]]
    children=[]
    for folder in ("geometry","source"):
        path=OUT/folder/"sha256-manifest.json"
        manifest=load(path)
        entries=manifest if isinstance(manifest,list) else manifest.get("files",manifest.get("records"))
        if isinstance(entries,dict):entries=[{"path":p,"sha256":s} for p,s in entries.items()]
        mismatch=[r["path"] for r in entries if sha(OUT/folder/r["path"]) != r["sha256"]]
        children.append({"folder":folder,"manifest_sha256":sha(path),"entries":len(entries),"mismatches":mismatch})
    reproduction=load(OUT/"reproduction/commands.json")
    geometry=load(OUT/"geometry/summary.json")
    source=load(OUT/"source/results.json")
    preservation=load(OUT/"preservation-relocation/results.json")
    primary=load(OUT/"primary-source-confirmation/results.json")
    summary={"task":"A01-R1","decision":"REWORK","reviewed_at":datetime.now(timezone(timedelta(hours=8))).isoformat(),
             "target_commit":boot["target_commit"],"implementation_commit":"0ee7e836e3bc1849f91840b4271d233bbd8e72dd",
             "R1_base":boot["R1_base"],"original_base_workflow":boot["original_base_workflow"],
             "execution_report_sha256":boot["report_sha256"],"review_report_sha256":sha(REPORT),
             "temporary_root":boot["temporary_root"],"author_commands":len(reproduction),"author_command_exit_codes":[r["exit_code"] for r in reproduction],
             "author_tests":{"A01_pass":30,"A01_skip":1,"C01_pass":70,"original_replay":16},
             "original_repairs":{"R01":"ACCEPTED limited to listed checks","R02":"ACCEPTED limited to listed checks","R03":"ACCEPTED explicit integer limits","R04_original_S12_to_S20":"ACCEPTED","R04_neighbor_consistency":"REWORK"},
             "geometry":{"pass":geometry["pass"],"fail":geometry["fail"],"observations":geometry["observations"],"original_regressions_pass":geometry["original_regressions_pass"]},
             "source":{"counts":source.get("counts"),"unexpected_accepts":source.get("unexpected_accepts")},
             "preservation":{"pass":preservation["passed"],"fail":preservation["failed"],"legacy_files":45,"original_inputs":31,"relocated_packages":4},
             "primary_neighbor_confirmation":{"pass":primary["passed"],"fail":primary["failed"],"expected_script_exit_code":1},
             "remaining_findings":["R1-F01 acquired/missing scope partition contradictions","R1-F02 history image URL book/index contradictions","R1-F03 observation index digest contradiction"],
             "known_integration_gaps":["S01 public completeness gate not implemented","D01 Pillow missing from root dependency declarations"],
             "unverified":["Windows file symlink branch WinError1314","clean installation","A04/CSS-DPR/browser/platform","OCR/recognition/answer quality","whole-page/book independent denominator","B confirmation"],
             "command_results":[
                 {"command":[sys.executable,"-B",str(OUT/"bootstrap.py")],"exit_code":0,"output":"bootstrap.json"},
                 {"command":[sys.executable,"-B",str(OUT/"reproduce.py")],"exit_code":0,"output":"reproduction/commands.json"},
                 {"command":[sys.executable,"-B",str(OUT/"preservation-relocation.py")],"exit_code":0,"output":"preservation-relocation/results.json"},
                 {"command":[sys.executable,"-B",str(OUT/"primary-source-confirmation.py")],"exit_code":1,"output":"primary-source-confirmation/results.json"}],
             "no_implementation_modification":True,"no_contract_state_modification":True,"integrated":False,"A04_dependency_released":False,
             "network_browser_platform_OCR_model_tool_calls":0,"paid_model_tool_cost":0}
    save("review-summary.json",summary)
    links=[]
    issues=[]
    for target in re.findall(r"\]\(([^)]+)\)",REPORT.read_text(encoding="utf-8")):
        if target.startswith(("http:","https:","#")):continue
        path=(REPORT.parent/target.split("#")[0]).resolve()
        exists=path.exists() or path in {OUT/"final-integrity.json",OUT/"sha256-manifest.json"}
        links.append({"target":target,"exists_or_planned":exists})
        if not exists:issues.append("missing report link: "+target)
    if changed or old_changed or extras or any(c["mismatches"] for c in children):issues.append("integrity mismatch or unexpected exported file")
    integrity={"target_commit":boot["target_commit"],"verified_Git_files":len(tracked),"changed_tracked_files":changed,"extra_snapshot_files":extras,
               "old_review_files":len(boot["old_review_records"]),"changed_old_review_files":old_changed,
               "child_manifests":children,"report_links":links,"issues":issues}
    save("final-integrity.json",integrity)
    files=sorted(p for p in OUT.rglob("*") if p.is_file() and p != OUT/"sha256-manifest.json")+[REPORT]
    save("sha256-manifest.json",{"target_commit":boot["target_commit"],"decision":"REWORK", "records":[{"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]})
    print(json.dumps({"decision":"REWORK","verified_git_files":len(tracked),"preserved_old_review_files":len(boot["old_review_records"]),"evidence_files":len(files),
                      "review_report_sha256":sha(REPORT),"manifest_sha256":sha(OUT/"sha256-manifest.json"),"issues":issues}))
    raise SystemExit(bool(issues))

if __name__=="__main__":main()
