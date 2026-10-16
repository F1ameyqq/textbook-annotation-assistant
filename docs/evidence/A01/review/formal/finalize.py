"""Seal formal review evidence after all producers have finished."""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.dont_write_bytecode=True
FORMAL=Path(__file__).resolve().parent
ROOT=FORMAL.parents[4]
REPORT=ROOT/"docs/tasks/A01-review-final-report.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(name,value):
    with (FORMAL/name).open("x",encoding="utf-8",newline="\n") as handle:
        json.dump(value,handle,ensure_ascii=False,indent=2); handle.write("\n")


def main():
    bootstrap=load(FORMAL/"bootstrap.json")
    snapshot=Path(bootstrap["snapshot"])
    changed=[]
    for item in bootstrap["exported_files_verified"]:
        if sha(snapshot/item["path"]) != item["sha256"]:
            changed.append(item["path"])
    tracked={r["path"] for r in bootstrap["exported_files_verified"]}
    extras=[p.relative_to(snapshot).as_posix() for p in snapshot.rglob("*") if p.is_file() and p.relative_to(snapshot).as_posix() not in tracked]
    prep_manifest=ROOT/"docs/evidence/A01/review/sha256-manifest.json"
    prep_archive=subprocess.run(["git","-C",str(ROOT),"show","60ad7be2766c6a645a747006203297d658ea7fa7:docs/evidence/A01/review/sha256-manifest.json"],check=True,capture_output=True).stdout
    prep_mismatches=[r["path"] for r in load(prep_manifest)["records"] if sha(ROOT/r["path"]) != r["sha256"]]
    prep_manifest_unchanged=prep_manifest.read_bytes() == prep_archive
    inputs=load(ROOT/"docs/evidence/A01/review/input-inventory-before.json")["records"]
    input_mismatches=[r["path"] for r in inputs if sha(ROOT/r["path"]) != r["sha256"] or sha(snapshot/r["path"]) != r["sha256"]]
    child_validation=[]
    for name in ("geometry-independent","source-independent"):
        folder=FORMAL/name
        manifest=load(folder/"sha256-manifest.json")
        items=manifest if isinstance(manifest,list) else manifest.get("files",manifest.get("records"))
        if isinstance(items,dict):
            entries=[{"path":p,"sha256":h} for p,h in items.items()]
        else:
            entries=items
        mismatches=[]
        for item in entries:
            if sha(folder/item["path"]) != item["sha256"]:
                mismatches.append(item["path"])
        child_validation.append({"folder":name,"manifest_sha256":sha(folder/"sha256-manifest.json"),"entries":len(entries),"mismatches":mismatches})
    reproduction=load(FORMAL/"reproduction/commands.json")
    inventory=load(FORMAL/"inventory-relocation/run-02/results.json")
    geometry=load(FORMAL/"geometry-independent/summary.json")
    source=load(FORMAL/"source-independent/results.json")
    summary={"task":"A01","phase":"FORMAL_INDEPENDENT_REVIEW","decision":"REWORK",
             "reviewed_at":datetime.now(timezone(timedelta(hours=8))).isoformat(),
             "target_commit":bootstrap["target_commit"],"implementation_commit":"c8b8c6e158547954c59017211507755f67eda0e8",
             "base_commit":bootstrap["base_commit"],"workflow_commit":bootstrap["workflow_commit"],
             "execution_report_sha256":bootstrap["execution_report_sha256"],
             "review_report":"docs/tasks/A01-review-final-report.md","review_report_sha256":sha(REPORT),
             "reproduction_commands":len(reproduction),"reproduction_exit_codes":[r["exit_code"] for r in reproduction],
             "author_tests":{"A01_pass":22,"A01_skip":1,"C01_pass":70},
             "inventory_independent":{"pass":inventory["passed"],"fail":inventory["failed"]},
             "geometry_independent":{"assertions":geometry["independent_assertions"],"pass":geometry["pass"],"fail":geometry["fail"]},
             "source_independent":{"cases":len(source["cases"]),"counts":source["counts"],"unexpected_accepts":source["unexpected_accepts"]},
             "primary_confirmation":"primary-confirmation/results.json",
             "S01_exact_frozen_source_proof":"primary-confirmation/S01-fixed-delivery-gate.json",
             "required_repairs":["R01 valid forward/inverse boundary rejected","R02 padding-domain input incorrectly accepted","R03 integer padding silently changed","R04 source/history internal contradictions accepted"],
             "integration_gaps":["S01 typed completeness/public PRE_APPLY eligibility gate absent","D01 Pillow undeclared in root dependencies"],
             "not_executed":["Windows file symlink branch: WinError 1314","clean environment installation","A04/platform/browser/CSS-DPR","OCR/recognition/answer quality","whole-page/book denominator","B confirmation"],
             "no_integration":True,"A04_dependency_released":False,"network_browser_platform_model_tool_calls":0,"paid_model_tool_cost":0,
             "reproduction_entries":{"author":"reproduce.py","source_safe_replay":"replay-source.py","geometry":"geometry-independent/run_geometry_review.py","primary":"confirm-findings.py","S01_exact":"confirm-s01-fixed-delivery.py"}}
    save("review-summary.json",summary)
    issues=[]
    if changed or prep_mismatches or input_mismatches or not prep_manifest_unchanged or any(x["mismatches"] for x in child_validation):
        issues.append("integrity mismatch")
    link_checks=[]
    # The final manifest is created after this check; its planned target is known.
    for target in re.findall(r"\]\(([^)]+)\)",REPORT.read_text(encoding="utf-8")):
        if target.startswith(("http:","https:","#")):
            continue
        path=(REPORT.parent/target.split("#")[0]).resolve()
        exists=path.exists() or path in {FORMAL/"sha256-manifest.json", FORMAL/"final-integrity.json"}
        link_checks.append({"target":target,"exists_or_planned_manifest":exists})
        if not exists:
            issues.append("missing report link: "+target)
    result={"target_commit":bootstrap["target_commit"],"Git_tracked_export_files":len(tracked),"changed_tracked_files":changed,
            "non_Git_export_files":extras,"non_Git_files_are_only_bytecode":all(p.endswith(".pyc") and "__pycache__" in p for p in extras),
            "preparation_manifest_matches_archive_commit":prep_manifest_unchanged,"preparation_record_mismatches":prep_mismatches,
            "original_input_mismatches":input_mismatches,"child_evidence_manifests":child_validation,
            "report_links":link_checks,"issues":issues}
    save("final-integrity.json",result)
    paths=sorted(p for p in FORMAL.rglob("*") if p.is_file() and p != FORMAL/"sha256-manifest.json")+[REPORT]
    records=[{"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p)} for p in paths]
    save("sha256-manifest.json",{"target_commit":bootstrap["target_commit"],"decision":"REWORK","records":records})
    print(json.dumps({"decision":"REWORK","tracked_files_verified":len(tracked),"evidence_files_hashed":len(records),
                      "review_report_sha256":sha(REPORT),"manifest_sha256":sha(FORMAL/"sha256-manifest.json"),"issues":issues}))
    raise SystemExit(bool(issues))


if __name__ == "__main__":
    main()
