"""Read-only evidence audit, then create a new final matrix and SHA manifest."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import zipfile

ROOT=Path(__file__).resolve().parent
WORKSPACE=ROOT.parents[4]
REPORT=WORKSPACE/"docs/tasks/D01-review-report.md"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path,value):
    Path(path).write_bytes((json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode("utf-8"))


def inventory(root):
    return {p.relative_to(root).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(Path(root).rglob("*")) if p.is_file()}


def main():
    assert WORKSPACE.name=="1800"
    audit_path=ROOT/"closeout-audit.json"
    manifest_path=ROOT/"sha256-manifest.json"
    assert not audit_path.exists() and not manifest_path.exists()
    checks=[]
    process=load(ROOT/"process-observation.json")
    assert not process["observed_remaining"] and process["all_recorded_commands_returned"]
    first=load(ROOT/"commands.json")
    resume=load(ROOT/"resume01/commands.json")
    assert len(first)==28 and len(resume)==4
    for prefix,records in ((ROOT,first),(ROOT/"resume01",resume)):
        for record in records:
            assert record["synchronous_return"]
            for stream in ("stdout","stderr"):
                assert sha((prefix/record[stream+"_path"]).read_bytes())==record[stream+"_sha256"]
    assert [r["label"] for r in first+resume if r["exit_code"]!=r["expected_exit_code"]]==["contract-regression"]
    assert len([r for r in first+resume if r["expected_exit_code"]==1])==6
    for folder in ("collector-run01","collector-resume01"):
        outer=load(ROOT/folder/"command.json")
        assert outer["synchronous_return"]
        for stream in ("stdout","stderr"):
            assert sha((ROOT/folder/(stream+".bin")).read_bytes())==outer[stream+"_sha256"]
    first_outer=load(ROOT/"collector-run01/command.json")
    assert sha((ROOT/"collector-run01/run_review.py").read_bytes())==first_outer["runner_sha256"]
    assert sha((ROOT/"collector-run01/probe.py").read_bytes())==first_outer["probe_sha256"]
    assert (ROOT/"collector-run01/probe.py").read_bytes()==(ROOT/"probe.py").read_bytes()
    checks.append("32 synchronous command records and two outer collectors linked to raw outputs; initial failure preserved")
    protected=load(ROOT/"preparation-before.json")
    preparation=WORKSPACE/"docs/evidence/D01/review/preparation"
    assert inventory(preparation)==protected["files"]
    assert sha((WORKSPACE/"docs/tasks/D01-review-preparation.md").read_bytes())==protected["report_sha256"]
    for index_name in ("source-index.json","sample-index.json","regression-input-index.json"):
        for item in load(ROOT/index_name):
            raw=Path(item["destination"]).read_bytes()
            assert len(raw)==item["bytes"] and sha(raw)==item["sha256"]
    supplement=load(ROOT/"resume01/supplemental-input-index.json")
    assert len(supplement)==1
    assert sha(Path(supplement[0]["destination"]).read_bytes())==supplement[0]["sha256"]
    preservation=load(ROOT/"post-run-preservation.json")
    receipt=load(ROOT/"receipt.json")
    outside=Path(receipt["outside_root"])
    assert inventory(outside/"fixed R3 original")==preservation["original_samples"]
    assert inventory(outside/"relocated R3 packages with spaces")==preservation["relocated_samples"]
    checks.append("27 preparation files, fixed build/sample/regression inputs and one supplemental helper remain byte-identical")
    dependencies=load(ROOT/"public-dependency-index.json")
    assert len(dependencies)==9
    for item in dependencies:
        assert sha(Path(item["downloaded_location"]).read_bytes())==item["sha256"]
        public_path=ROOT/"pypi"/(item["name"].replace("-","_")+"-"+item["version"]+".json")
        public_raw=public_path.read_bytes()
        assert sha(public_raw)==item["public_metadata_sha256"]
        public=json.loads(public_raw)
        match=next(entry for entry in public["urls"] if entry["filename"]==item["filename"])
        assert match["digests"]["sha256"]==item["sha256"] and match["url"]==item["source_url"]
    checks.append("9 required public artifacts and raw PyPI metadata hashes linked")
    wheel_binding=load(ROOT/"wheel-source-binding.json")
    wheel=ROOT/"artifacts"/wheel_binding["wheel"]
    assert sha(wheel.read_bytes())==wheel_binding["sha256"]
    installed=load(ROOT/"installed-provenance.json")
    install=load(ROOT/"install-report.json")
    product=next(item for item in install["install"] if item["metadata"]["name"]=="annotation-contracts")
    assert product["download_info"]["archive_info"]["hashes"]["sha256"]==wheel_binding["sha256"]
    assert json.loads(installed["metadata"]["direct_url.json"])["archive_info"]["hashes"]["sha256"]==wheel_binding["sha256"]
    with zipfile.ZipFile(wheel) as archive:
        for item in installed["wheel_installed_binding"]:
            assert sha(archive.read(item["path"]))==item["sha256"]
            assert sha(Path(item["installed"]).read_bytes())==item["sha256"]
    assert len(installed["wheel_installed_binding"])==14
    checks.append("Git -> actual wheel -> install report/direct_url/RECORD -> 14 installed source files binding retained")
    for book,count in (("46006966",6),("46007447",2)):
        result=load(ROOT/("consumer-"+book+".json"))
        assert len(result["images"])==count
        assert result["limitations"]["scope_manifest_status"]=="REFERENCE_ONLY" and result["limitations"]["coverage_eligible"] is False
        for kind,code in (("missing","RESOURCE_MISSING"),("hash-damage","RESOURCE_HASH")):
            negative=load(ROOT/("negative-"+book+"-"+kind+".json"))
            assert negative["result"]=="REJECTED" and code in negative["error"]
        decode=load(ROOT/("negative-"+book+"-decode.json"))
        assert decode["public_resource_layer"]=="PASS" and decode["pillow_verify"]=="PASS_HEADER_ONLY"
        assert decode["pillow_full_load"]=="REJECTED" and decode["code"]=="IMAGE_DECODE"
    assert load(ROOT/"resume01/one-test-result.json")["successful"]
    checks.append("Both finite packages, 8 full image loads, 6 layered rejection receipts and corrected single test verified")
    # Static Git reads are not new product tests and do not modify Git configuration.
    git_records=[]
    def git(label,args,input=None,allowed=(0,)):
        process=subprocess.run(["git","-C",str(WORKSPACE),*args],input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        folder=ROOT/"closeout-git"/label
        folder.mkdir(parents=True,exist_ok=False)
        (folder/"stdout.bin").write_bytes(process.stdout)
        (folder/"stderr.bin").write_bytes(process.stderr)
        entry=dict(argv=process.args,cwd=str(WORKSPACE),exit_code=process.returncode,stdout_sha256=sha(process.stdout),stderr_sha256=sha(process.stderr),synchronous_return=True)
        write(folder/"command.json",entry)
        git_records.append(entry)
        assert process.returncode in allowed,(label,process.returncode)
        return process.stdout
    tracked=git("tracked-diff",["diff","--name-only","HEAD"])
    assert not tracked
    untracked=git("new-paths",["ls-files","--others","--exclude-standard","-z"]).decode().split("\0")
    report_paths={"docs/tasks/D01-review-preparation.md","docs/tasks/D01-review-report.md"}
    for path in filter(None,untracked):
        assert path in report_paths or path.startswith("docs/evidence/D01/review/preparation/") or path.startswith("docs/evidence/D01/review/formal/"),path
    tree_ids=git("fixed-trees",["rev-parse",receipt["base"]+"^{tree}",receipt["implementation"]+"^{tree}",receipt["delivery"]+"^{tree}",receipt["workflow"]+"^{tree}"]).decode().splitlines()
    assert tree_ids==["e6f8d89bceccd639d9d8cf4e5fd2766899dff59b","06ffc28412a7aff9dc16ebb517686fc3046b7814","ea3bd81d263642ea256a546aeebc0d73c64571bd","c55dd8f258af14727d41cc04b080acb2cf10b7aa"]
    scope_paths=[p.relative_to(WORKSPACE).as_posix() for p in ROOT.rglob("*") if p.is_file()]+[REPORT.relative_to(WORKSPACE).as_posix()]
    ignored=git("ignored-artifacts",["check-ignore","--stdin"],input=("\n".join(scope_paths)+"\n").encode(),allowed=(0,1)).decode().splitlines()
    text=REPORT.read_text(encoding="utf-8")
    assert not re.search(r"(?m)[ \t]+$",text)
    links=[]
    pending={audit_path,manifest_path}
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)",text):
        path=(REPORT.parent/target).resolve()
        assert path.exists() or path in pending,(target,path)
        links.append(target)
    for path in ROOT.glob("*.py"):
        compile(path.read_bytes(),str(path),"exec")
    matrix=load(preparation/"verification-matrix.json")
    bindings={
        "G01":["inputs/workflow/docs/tasks/D01-review-handoff.md","scope-audit.json"],
        "S01":["scope-audit.json"],"S02":["static-input-index.json","post-run-preservation.json"],
        "E01":["receipt.json","pyvenv.cfg"],"E02":["source-index.json","wheel-source-binding.json","install-report.json"],
        "E03":["installed-provenance.json","wheel-source-binding.json","install-report.json"],
        "E04":["public-dependency-index.json"],"E05":["commands/16-pip-check/command.json","installed-provenance.json"],
        "E06":["installed-provenance.json"],"C01":["sample-index.json","post-run-preservation.json"],
        "C02":["consumer-46006966.json","consumer-46007447.json"],"C03":["consumer-46006966.json","consumer-46007447.json"],
        "N01":["negative-input-index.json"],"N02":["negative-46006966-decode.json","negative-46007447-decode.json"],
        "R01":["contract-regression.json","resume01/one-test-result.json","resume01/reviewer-correction.json","source-regression.json"],
        "F01":["process-observation.json","closeout-audit.json","sha256-manifest.json"]
    }
    # Resolve actual pip-check path from command evidence, without guessing ordinal.
    pip_check=next(r for r in first if r["label"]=="pip-check")
    bindings["E05"][0]=str(Path(pip_check["stdout_path"]).parent/"command.json").replace("\\","/")
    matrix.update(status="INDEPENDENT_ACCEPTED_PENDING_COORDINATOR_INTEGRATION",functional_result="PASS",formal_dispatch_received=True,
                  workflow_commit=receipt["workflow"],frozen_delivery_commit=receipt["delivery"],implementation_commit=receipt["implementation"],
                  execution_report_sha256="19c9553422b3d42daa693e22bfaf135272f5ab36837c8180bcaba7b2a1076c8b",
                  execution_manifest_sha256="58336c047aa881e16bafff47a90ee9050a1af068bbc4a4065c27e9fc1040b2ad",
                  execution_session_release_evidence="inputs/delivery/docs/evidence/D01/execution/process-observation-final.json",
                  not_run=["Other Python versions","Full deployment","Full A01/geometry matrix","Platform/browser/OCR/paid model/B confirmation"],
                  next_action="Coordinator reproduces necessary checks and integrates; reviewer performs no integration or dependency release.")
    for row in matrix["results"]:
        row.update(result="PASS_AFTER_REVIEW_FIXTURE_CORRECTION" if row["id"]=="R01" else "PASS",evidence=bindings[row["id"]])
        for relative in row["evidence"]:
            path=ROOT/relative
            assert path.exists() or path in pending,relative
    for row in matrix["book_boundaries"]:
        row["result"]="PASS_FINITE_REFERENCE_ONLY"
    write(ROOT/"verification-matrix.json",matrix)
    write(audit_path,dict(schema="D01-independent-formal-closeout-v1",observed_unix=time.time(),conclusion="ACCEPTED_BOUNDED_FIXED_DELIVERY",
          input_versions=receipt,fixed_tree_ids=tree_ids,checks=checks,command_records=32,outer_records=2,
          report_links=links,preparation_unchanged=True,no_tracked_files_modified=True,
          untracked_path_scope_verified=True,actual_ignored_files=ignored,includes_ignored_files=True,
          static_git_records=git_records,final_replay_script_only_syntax_checked=True,
          original_executed_runner_sha256=first_outer["runner_sha256"],final_replay_script_sha256=sha((ROOT/"run_review.py").read_bytes()),
          first_regression_failure_preserved=True,affected_one_test_only_rerun=True,
          scope="CPython3.9.13 Windows; frozen finite packages; no integration or platform acceptance"))
    all_paths=[REPORT]+[p for p in sorted(ROOT.rglob("*")) if p.is_file()]
    entries=[dict(path=p.relative_to(WORKSPACE).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in all_paths]
    write(manifest_path,dict(schema="D01-independent-formal-sha256-v1",delivery=receipt["delivery"],workflow=receipt["workflow"],conclusion="ACCEPTED_BOUNDED_FIXED_DELIVERY",
          excludes=[manifest_path.relative_to(WORKSPACE).as_posix()],entries=entries))
    for item in entries:
        assert sha((WORKSPACE/item["path"]).read_bytes())==item["sha256"]
    for link in links:
        assert (REPORT.parent/link).exists()
    print(json.dumps(dict(result="FORMAL_CLOSEOUT_COMPLETE",report_sha256=sha(REPORT.read_bytes()),manifest_sha256=sha(manifest_path.read_bytes()),
                         manifest_entries=len(entries),report_links=len(links),ignored_files=len(ignored))))


if __name__=="__main__":
    main()
