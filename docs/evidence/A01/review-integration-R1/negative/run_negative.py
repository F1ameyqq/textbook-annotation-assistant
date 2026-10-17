"""Independent bounded offline corruption controls; do not modify reviewed sources."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

EVIDENCE = Path(__file__).resolve().parent
BOOT = json.loads((EVIDENCE.parent / "bootstrap.json").read_text(encoding="utf-8"))
STAGE = Path(BOOT["stage"]) / "negative"
RAW = Path(BOOT["raw"])
FROZEN = Path(BOOT["frozen"])
PYTHON = Path(BOOT["environment"]["executable"])
assert BOOT["final"] == "5f872150a237b195f73c78e02e13a91d2f4f46a7"
assert BOOT["base"] == "180bb1e86fb2a7eb1546be85af70f466f069daf5"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w",encoding="utf-8",newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

def index(root):
    return {str(p.relative_to(root)).replace("\\", "/"): dict(sha256=sha(p.read_bytes()), bytes=p.stat().st_size)
            for p in root.rglob("*") if p.is_file()}

def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value

def execute(label, args, cwd, env):
    out=EVIDENCE/label; out.mkdir(exist_ok=False)
    command=[str(PYTHON),"-B",*map(str,args)]
    start=datetime.now(timezone.utc).isoformat()
    result=subprocess.run(command,cwd=cwd,env=env,capture_output=True)
    (out/"stdout.txt").write_bytes(result.stdout); (out/"stderr.txt").write_bytes(result.stderr)
    record=dict(label=label,argv=command,cwd=str(cwd),environment={k:env[k] for k in ("PATH","PYTHONPATH","PYTHONDONTWRITEBYTECODE","TMP","TEMP","TMPDIR")},
                exit_code=result.returncode,started_at=start,finished_at=datetime.now(timezone.utc).isoformat(),
                stdout_sha256=sha(result.stdout),stderr_sha256=sha(result.stderr))
    write(out/"command.json",record)
    return record

def save_mutation(label, relative, before, after, detail):
    out=EVIDENCE/label/"mutation"; out.mkdir(parents=True,exist_ok=True)
    (out/"original.bin").write_bytes(before); (out/"changed.bin").write_bytes(after)
    write(out/"input.json",dict(path=relative,original_sha256=sha(before),original_bytes=len(before),changed_sha256=sha(after),changed_bytes=len(after),detail=detail))

def main():
    assert not (STAGE/"integrated").exists() and not (STAGE/"frozen").exists()
    inherited=index(RAW); old=index(FROZEN)
    selected=("src","tests","examples/a01","data/derived","data/raw/images","data/raw/annotations","技术证据/只读样本-46006966","docs/evidence/A05")
    integrated=STAGE/"integrated"
    for relative in selected:
        shutil.copytree(RAW/relative,integrated/relative)
    frozen=STAGE/"frozen"; shutil.copytree(FROZEN,frozen)
    integrated_before=index(integrated); frozen_before=index(frozen)
    assert all(inherited[p]==v for p,v in integrated_before.items())
    assert frozen_before==old
    write(EVIDENCE/"source-index.json",dict(raw_source=str(RAW),raw_subset=integrated_before,frozen_source=str(FROZEN),frozen_files=frozen_before,subsets=list(selected),bootstrap_sha256=sha((EVIDENCE.parent/"bootstrap.json").read_bytes())))
    ordinary=Path(tempfile.mkdtemp(prefix="A01-integration-R1-negative-"))
    other_cwd=ordinary/"different cwd"; other_cwd.mkdir()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",TMP=str(ordinary),TEMP=str(ordinary),TMPDIR=str(ordinary),PATH=r"C:\Windows\System32;C:\Windows")
    cases=[]
    def run_integrated(label, relative=None, changed=None, detail=None, expected=1):
        env["PYTHONPATH"]=str(integrated/"src")
        command=execute(label,[integrated/"examples/a01/integration-R1/verify.py",EVIDENCE/label/"result","--focused"],other_cwd,env) if relative is None else None
        if relative:
            target=integrated/relative; original=target.read_bytes()
            target.write_bytes(changed)
            # Record a real import and behavior in the same isolated source tree.
            if relative.endswith("importer.py"):
                probe=execute(label+"-actual-import",["-c","import hashlib,json; from pathlib import Path; import annotation.source.static.importer as m; print(json.dumps(dict(file=m.__file__,sha256=hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest(),index=m.url_index('https://archive.example.invalid/upload_images/46007447/46007447_page_13.jpg','46007447','review.image'))))"],other_cwd,env)
                assert probe["exit_code"]==0
            try:
                command=execute(label,[integrated/"examples/a01/integration-R1/verify.py",EVIDENCE/label/"result","--focused"],other_cwd,env)
                save_mutation(label,relative,original,changed,detail)
            finally:
                target.write_bytes(original)
        assert index(integrated)==integrated_before
        result=json.loads((EVIDENCE/label/"result/results.json").read_text(encoding="utf-8"))
        child=result["commands"][0]
        cases.append(dict(label=label,expected_exit_code=expected,actual_exit_code=command["exit_code"],expected_matched=command["exit_code"]==expected,
                          child_exit_code=child["exit_code"],passed=result["passed"],first_load_bundle="NOT_APPLICABLE: code/fixture preservation control",source_restored=True))

    run_integrated("I00-clean",expected=0)
    relative="src/annotation/source/static/importer.py"
    original=(integrated/relative).read_bytes(); assert original.count(b"return int(match[3])")==1
    run_integrated("I01-source-functional",relative,original.replace(b"return int(match[3])",b"return int(match[3])+1"),"Change actual production URL source-index computation by +1; valid Python")
    fixture_relative="tests/fixtures/a01/integration-R1/reference.json"
    original=(integrated/fixture_relative).read_bytes()
    data=json.loads(original)
    payload=base64.b64decode(data["files"][0]["git_original_base64"])
    data["files"][0]["git_original_base64"]=base64.b64encode(bytes([payload[0]^1])+payload[1:]).decode("ascii")
    changed=(json.dumps(data,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    run_integrated("I02-encoded-content",fixture_relative,changed,"Flip the first decoded payload byte; preserve all expected hashes, paths, OIDs, lengths and identities")
    data=json.loads(original); prior=data["files"][0]["git_blob_oid"]
    data["files"][0]["git_blob_oid"]=("0" if prior[0]!="0" else "1")+prior[1:]
    changed=(json.dumps(data,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    run_integrated("I03-file-identity",fixture_relative,changed,"Change first file Git blob OID only; leave payload/expected SHA and length fixed")
    data=json.loads(original); data["reference_commit"]="0"*40
    changed=(json.dumps(data,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    run_integrated("I04-root-reference-identity",fixture_relative,changed,"Change top-level fixed reference_commit only; keep every payload and per-file identity/expected byte fixed")
    data=json.loads(original); data["source_manifest_sha256"]="0"*64
    changed=(json.dumps(data,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    run_integrated("I05-source-manifest-identity",fixture_relative,changed,"Change top-level source_manifest_sha256 only; keep every payload and per-file identity/expected byte fixed")

    fixed=load("independent_negative_fixed_inputs",integrated/"examples/a01/integration-R1/fixed_inputs.py")
    preservation=load("independent_negative_preservation",integrated/"examples/a01/R3/preservation.py")
    fixed_folder=STAGE/"selected originals"; reference=fixed.materialize(integrated/"tests/fixtures/a01/integration-R1",fixed_folder)
    write(EVIDENCE/"selected-reference.json",reference)
    auxiliary=[]
    for label,relative,mode,expected in (("F00-raw","tests/test_contracts.py","unchanged",True),("F01-allowed-CRLF","tests/test_contracts.py","crlf",True),("F02-mixed-EOL","tests/test_contracts.py","mixed",False),("F03-unlisted-CRLF","examples/a01/build.py","crlf",False),("F04-binary","tests/fixtures/contracts/normal/assets/asset-page-a1.pgm","binary",False)):
        target=fixed_folder/relative; before=target.read_bytes()
        if mode=="unchanged": after=before
        elif mode=="crlf": after=before.replace(b"\n",b"\r\n")
        elif mode=="mixed": after=before.replace(b"\n",b"\r\n",1)
        else: middle=len(before)//2; after=before[:middle]+bytes([before[middle]^1])+before[middle+1:]
        target.write_bytes(after)
        try:
            audit=preservation.audit(fixed_folder,reference)
            save_mutation(label,relative,before,after,"Independent exact-byte policy sample: "+mode)
            write(EVIDENCE/label/"audit.json",audit)
            assert audit["passed"]==expected
            if not expected: assert audit["errors"]==[dict(code="CONTENT_MISMATCH",path=relative,actual_sha256=sha(after),accepted_sha256=[r["sha256"] for e in reference["files"] if e["path"]==relative for r in e["representations"]])]
            auxiliary.append(dict(label=label,path=relative,expected_passed=expected,actual_passed=audit["passed"],expected_matched=True))
        finally: target.write_bytes(before)

    release=[]
    def run_frozen(label,relative=None,after=None,expected=1):
        env["PYTHONPATH"]=str(frozen/"src")
        target=frozen/relative if relative else None
        if target:
            before=target.read_bytes(); target.write_bytes(after)
        try:
            command=execute(label,[frozen/"examples/a01/R3/verify.py",EVIDENCE/label/"result","--preservation-only"],other_cwd,env)
            if target: save_mutation(label,relative,before,after,"Original unchanged 180bb1e bound gate; independent byte corruption")
        finally:
            if target: target.write_bytes(before)
        assert index(frozen)==frozen_before
        assert command["exit_code"]==expected
        stdout=(EVIDENCE/label/"stdout.txt").read_text(encoding="utf-8")
        outcome=json.loads(stdout.strip())
        release.append(dict(label=label,expected_exit_code=expected,actual_exit_code=command["exit_code"],outcome=outcome,source_restored=True))
    run_frozen("R00-clean",expected=0)
    relative="src/annotation/source/static/consistency.py"; before=(frozen/relative).read_bytes()
    run_frozen("R01-source",relative,before+b"\n# independent real source corruption\n")
    ref=json.loads((frozen/"tests/fixtures/a01/R3/preservation-manifest.json").read_text(encoding="utf-8"))
    relative=next(e["path"] for e in ref["files"] if e["path"].endswith(".jpg"))
    before=(frozen/relative).read_bytes(); mid=len(before)//2
    run_frozen("R02-image",relative,before[:mid]+bytes([before[mid]^1])+before[mid+1:])
    assert index(RAW)==inherited and index(FROZEN)==old
    summary=dict(final=BOOT["final"],patch=BOOT["patch"],main_parent=BOOT["main_parent"],base=BOOT["base"],integration_tree=BOOT["integration_tree"],
                 task="independent bounded negative controls",temporary=str(ordinary),stage=str(STAGE),python=str(PYTHON),focused=cases,auxiliary=auxiliary,original_release=release,
                 focused_expected_failures=[c["label"] for c in cases if not c["expected_matched"]],raw_root_files_unchanged=len(inherited),frozen_root_files_unchanged=len(old),
                 independent_subset_files=len(integrated_before),original_release_files=len(frozen_before),old_evidence_written=False,network_browser_platform_credential_model_calls=0,sessions_to_release=0)
    write(EVIDENCE/"summary.json",summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
