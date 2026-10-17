"""Independent frozen D01 validation; host process uses only Python stdlib."""
import email
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.parse
import urllib.request
import zipfile

BASE = "c6bebdf43eb93f7a6ae21e96ec07ed155686777d"
IMPLEMENTATION = "9a7b9d7e374ee7a3ee124c9ff20e0b4003e57464"
DELIVERY = "48accd7d885fbc7ecdd8b438ada33a0eafd5bc55"
WORKFLOW = "2ef3bfda20476dff3bdd23912d5bf2d1e3eb5ce1"
REPOSITORY = Path("D:/1800")
WORKSPACE = Path(__file__).resolve().parents[5]
EVIDENCE = Path(__file__).resolve().parent
STAGE = WORKSPACE / ".local" / "d01-formal-48accd7d"
PROBE = EVIDENCE / "probe.py"
COMMANDS = []
ENV = os.environ.copy()
for key in list(ENV):
    if key.startswith("PIP_") or key.startswith("PYTHON"):
        ENV.pop(key)
ENV.update(PIP_CONFIG_FILE=os.devnull, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)+"\n").encode("utf-8"))


def files(root):
    return {p.relative_to(root).as_posix(): dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
            for p in sorted(Path(root).rglob("*")) if p.is_file()}


def run(label, argv, cwd, expected=0, stdin=None, timeout=300):
    target = EVIDENCE / "commands" / ("%02d-" % (len(COMMANDS)+1) + label)
    target.mkdir(parents=True, exist_ok=False)
    started = time.time()
    process = subprocess.Popen([str(a) for a in argv], cwd=str(cwd), env=ENV,
                               stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(input=stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        (target/"stdout.bin").write_bytes(stdout)
        (target/"stderr.bin").write_bytes(stderr)
        write(target/"timeout.json", dict(pid=process.pid, timeout_seconds=timeout, exit_code=process.returncode))
        raise
    (target/"stdout.bin").write_bytes(stdout)
    (target/"stderr.bin").write_bytes(stderr)
    record = dict(label=label, argv=[str(a) for a in argv], cwd=str(cwd), pid=process.pid,
                  started_unix=started, finished_unix=time.time(), exit_code=process.returncode,
                  expected_exit_code=expected, synchronous_return=True,
                  stdout_sha256=sha(stdout), stderr_sha256=sha(stderr),
                  stdout_path=(target/"stdout.bin").relative_to(EVIDENCE).as_posix(),
                  stderr_path=(target/"stderr.bin").relative_to(EVIDENCE).as_posix(),
                  selected_environment={k:ENV.get(k) for k in ("PIP_CONFIG_FILE", "PYTHONUTF8", "PYTHONDONTWRITEBYTECODE", "SOURCE_DATE_EPOCH", "TMP", "TEMP")},
                  removed_environment_names=[k for k in os.environ if k.startswith("PIP_") or k.startswith("PYTHON")])
    write(target/"command.json", record)
    COMMANDS.append(record)
    write(EVIDENCE/"commands.json", COMMANDS)
    if process.returncode != expected:
        raise RuntimeError("Unexpected exit for %s: %s, expected %s; see %s" % (label, process.returncode, expected, target))
    return stdout


def git(label, *args, stdin=None):
    return run("git-"+label, ["git", "-c", "core.longpaths=true", *args], REPOSITORY, stdin=stdin)


def tree(commit):
    output = git("tree-"+commit[:8], "ls-tree", "-rz", commit)
    result = {}
    for raw in output.split(b"\0"):
        if not raw:
            continue
        meta, path = raw.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        result[path.decode("utf-8")] = dict(mode=mode, kind=kind, oid=oid)
    return result


def blobs(label, refs):
    # refs is [(commit, path, tree_entry)]; raw Git output, never a text pipe.
    raw = git("blobs-"+label, "cat-file", "--batch", stdin=("\n".join(r[2]["oid"] for r in refs)+"\n").encode())
    pos = 0
    values = {}
    entries = []
    for commit, path, item in refs:
        end = raw.index(b"\n", pos)
        oid, kind, size = raw[pos:end].decode().split()
        size = int(size)
        start = end+1
        body = raw[start:start+size]
        assert len(body) == size and raw[start+size:start+size+1] == b"\n"
        assert kind == "blob" and oid == item["oid"]
        assert hashlib.sha1(b"blob "+str(size).encode()+b"\0"+body).hexdigest() == oid
        values[(commit, path)] = body
        entries.append(dict(commit=commit, path=path, git_blob_oid=oid, bytes=size, sha256=sha(body), representation="RAW_GIT_BLOB"))
        pos = start+size+1
    assert pos == len(raw)
    return values, entries


def materialize(root, commit, paths, mapping, values):
    entries = []
    for path in paths:
        body = values[(commit, path)]
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        assert target.read_bytes() == body
        entries.append(dict(commit=commit, path=path, git_blob_oid=mapping[path]["oid"], bytes=len(body), sha256=sha(body), destination=str(target)))
    return entries


def main():
    assert sys.version_info[:2] == (3, 9) and sys.flags.isolated
    assert not STAGE.exists(), "Exclusive stage must not exist"
    assert not (EVIDENCE/"run-result.json").exists()
    STAGE.mkdir(parents=True)
    outside = Path(tempfile.mkdtemp(prefix="1800 D01 independent "))
    assert WORKSPACE not in outside.parents and REPOSITORY not in outside.parents
    ENV.update(TMP=str(outside/"tmp"), TEMP=str(outside/"tmp"))
    (outside/"tmp").mkdir()
    write(EVIDENCE/"receipt.json", dict(base=BASE, implementation=IMPLEMENTATION, delivery=DELIVERY, workflow=WORKFLOW,
          host_python=sys.executable, exclusive_stage=str(STAGE), stage_previously_existed=False,
          outside_root=str(outside), cwd=str(outside), preparation_preservation="read-only before/after hashes"))
    preparation = WORKSPACE/"docs/evidence/D01/review/preparation"
    protected = files(preparation)
    protected_report = sha((WORKSPACE/"docs/tasks/D01-review-preparation.md").read_bytes())
    write(EVIDENCE/"preparation-before.json", dict(files=protected, report_sha256=protected_report))
    trees = {c:tree(c) for c in (BASE, IMPLEMENTATION, DELIVERY, WORKFLOW)}
    b, i, d, w = [trees[c] for c in (BASE, IMPLEMENTATION, DELIVERY, WORKFLOW)]
    changed_i = sorted(p for p in set(b)|set(i) if b.get(p) != i.get(p))
    assert changed_i == ["pyproject.toml"], changed_i
    changed_d = sorted(p for p in set(b)|set(d) if b.get(p) != d.get(p))
    allowed = lambda p: p == "pyproject.toml" or p == "docs/tasks/D01-execution-report.md" or p.startswith("examples/d01/") or p.startswith("docs/evidence/D01/execution/")
    assert all(allowed(p) for p in changed_d)
    assert all(p in d for p in b)
    assert all(i[p] == d[p] for p in i)
    workflow_paths = ["AGENTS.md", "docs/architecture.md", "docs/contracts-v1.md", "docs/coordination.md", "docs/tasks/D01-review-handoff.md", "docs/tasks/D01-independent-review.md", "docs/tasks/D01-dependency-implementation.md"]
    refs = [(WORKFLOW,p,w[p]) for p in workflow_paths] + [(DELIVERY,"docs/evidence/D01/execution/SHA256SUMS.json",d["docs/evidence/D01/execution/SHA256SUMS.json"])]
    first, first_index = blobs("handoff", refs)
    manifest_raw = first[(DELIVERY,"docs/evidence/D01/execution/SHA256SUMS.json")]
    assert sha(manifest_raw) == "58336c047aa881e16bafff47a90ee9050a1af068bbc4a4065c27e9fc1040b2ad"
    manifest = json.loads(manifest_raw)
    assert len(manifest["files"]) == 188
    author_paths = [item["path"] for item in manifest["files"]]
    source_paths = sorted(p for p in d if p.startswith("src/")) + ["pyproject.toml"]
    sample_paths = sorted(p for p in d if p.startswith("examples/a01/R3/bundles/")) + ["examples/a01/consume.py"]
    regression_paths = sorted(p for p in d if p.startswith("tests/fixtures/contracts/")) + ["tests/test_contracts.py", "tests/test_contracts_platform_refs.py", "examples/contracts/consume.py", "examples/contracts/build_fixtures.py"]
    inputs = sorted(set(author_paths+source_paths+sample_paths+regression_paths))
    all_values, all_index = blobs("fixed-inputs", [(DELIVERY,p,d[p]) for p in inputs] + [(BASE,"pyproject.toml",b["pyproject.toml"])])
    for item in manifest["files"]:
        body = all_values[(DELIVERY,item["path"])]
        assert len(body) == item["bytes"] and sha(body) == item["sha256"], item["path"]
    assert sha(all_values[(DELIVERY,"docs/tasks/D01-execution-report.md")]) == "19c9553422b3d42daa693e22bfaf135272f5ab36837c8180bcaba7b2a1076c8b"
    before = all_values[(BASE,"pyproject.toml")]
    expected = before.replace(b'dependencies = ["pydantic==2.12.5"]', b'dependencies = ["pydantic==2.12.5", "Pillow==11.3.0"]')
    assert expected != before and all_values[(DELIVERY,"pyproject.toml")] == expected
    author_outer = json.loads(all_values[(DELIVERY,"docs/evidence/D01/execution/collector-run03/command.json")])
    author_ledger = json.loads(all_values[(DELIVERY,"docs/evidence/D01/execution/run03/process-ledger.json")])
    release = json.loads(all_values[(DELIVERY,"docs/evidence/D01/execution/process-observation-final.json")])
    assert author_outer["exit_code"] == 0 and author_outer["synchronous_return"] and not release["observed_remaining"]
    for path in workflow_paths:
        target = EVIDENCE/"inputs/workflow"/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(first[(WORKFLOW,path)])
    for path in ("docs/tasks/D01-execution-report.md", "docs/evidence/D01/execution/SHA256SUMS.json", "docs/evidence/D01/execution/collector-run03/command.json", "docs/evidence/D01/execution/run03/process-ledger.json", "docs/evidence/D01/execution/process-observation-final.json"):
        target = EVIDENCE/"inputs/delivery"/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(all_values.get((DELIVERY,path),first.get((DELIVERY,path))))
    write(EVIDENCE/"static-input-index.json", first_index+all_index)
    write(EVIDENCE/"scope-audit.json", dict(base=BASE, implementation=IMPLEMENTATION, delivery=DELIVERY,
          implementation_changes=changed_i, delivery_changes=[dict(path=p, before=b.get(p), after=d.get(p)) for p in changed_d],
          base_files_preserved_except_pyproject=len(b)-1, root_dependency_exact_change=True, author_manifest_entries_verified=188,
          author_release_gate_verified=True, author_ledger=author_ledger, author_functional_results_used_for_independent_acceptance=False))
    fixed_source = STAGE/"fixed source"
    source_index = materialize(fixed_source, DELIVERY, source_paths, d, all_values)
    write(EVIDENCE/"source-index.json", source_index)
    original = outside/"fixed R3 original"
    sample_index = materialize(original, DELIVERY, sample_paths, d, all_values)
    assert all(d[p] == b[p] for p in sample_paths)
    write(EVIDENCE/"sample-index.json", sample_index)
    original_hashes = files(original)
    relocated = outside/"relocated R3 packages with spaces"
    shutil.copytree(original, relocated)
    assert files(relocated) == original_hashes
    regression_root = outside/"fixed regression no source"
    regression_index = materialize(regression_root, DELIVERY, regression_paths, d, all_values)
    write(EVIDENCE/"regression-input-index.json", regression_index)
    assert not (regression_root/"src").exists()
    source_before = {x["path"]:x["sha256"] for x in source_index}
    venv = STAGE/"cp39"
    assert not venv.exists()
    run("create-venv", [sys.executable,"-I","-m","venv",venv], outside)
    python = venv/"Scripts/python.exe"
    cfg = (venv/"pyvenv.cfg").read_bytes()
    assert b"include-system-site-packages = false" in cfg
    (EVIDENCE/"pyvenv.cfg").write_bytes(cfg)
    run("new-venv-identity",[python,"-I","-c","import json,sys,site; print(json.dumps(dict(executable=sys.executable,version=sys.version,prefix=sys.prefix,base_prefix=sys.base_prefix,path=sys.path,user_site_enabled=site.ENABLE_USER_SITE,isolated=sys.flags.isolated)))"],outside)
    downloads = STAGE/"public wheels"
    downloads.mkdir()
    pip = [python,"-I","-m","pip","--isolated","--disable-pip-version-check","--no-input"]
    run("download-pip",pip+["download","--index-url","https://pypi.org/simple","--no-deps","--only-binary=:all:","--dest",downloads,"pip==25.3"],outside)
    pip_wheel = next(downloads.glob("pip-25.3-*.whl"))
    run("bootstrap-own-pip",pip+["install","--no-index","--no-deps",pip_wheel],outside)
    run("download-public-dependencies",pip+["download","--index-url","https://pypi.org/simple","--only-binary=:all:","--dest",downloads,"setuptools==80.9.0","wheel==0.45.1","pydantic==2.12.5","Pillow==11.3.0"],outside)
    dependency_index = []
    for wheel in sorted(downloads.glob("*.whl")):
        with zipfile.ZipFile(wheel) as z:
            message = email.message_from_bytes(z.read(next(n for n in z.namelist() if n.endswith(".dist-info/METADATA"))))
        name, version = message["Name"], message["Version"]
        url = "https://pypi.org/pypi/"+urllib.parse.quote(name,safe="")+"/"+urllib.parse.quote(version,safe="")+"/json"
        request_started = time.time()
        with urllib.request.urlopen(url, timeout=30) as response:
            raw = response.read()
            status = response.status
        filename = name.replace("-","_")+"-"+version+".json"
        (EVIDENCE/"pypi").mkdir(exist_ok=True)
        (EVIDENCE/"pypi"/filename).write_bytes(raw)
        public = json.loads(raw)
        matching = [r for r in public["urls"] if r["filename"] == wheel.name]
        assert len(matching) == 1 and matching[0]["digests"]["sha256"] == sha(wheel.read_bytes())
        dependency_index.append(dict(name=name,version=version,filename=wheel.name,bytes=wheel.stat().st_size,sha256=sha(wheel.read_bytes()),
              source_url=matching[0]["url"],public_metadata_url=url,public_metadata_sha256=sha(raw),http_status=status,
              request_started_unix=request_started,request_finished_unix=time.time(),requires_python=message["Requires-Python"], downloaded_location=str(wheel)))
    write(EVIDENCE/"public-dependency-index.json",dependency_index)
    run("install-build-tools",pip+["install","--no-index","--find-links",downloads,"--report",EVIDENCE/"build-tools-install-report.json","setuptools==80.9.0","wheel==0.45.1"],outside)
    epoch = git("source-epoch","show","-s","--format=%ct",IMPLEMENTATION).decode().strip()
    ENV["SOURCE_DATE_EPOCH"] = epoch
    artifacts = EVIDENCE/"artifacts"
    artifacts.mkdir()
    run("build-fixed-wheel",pip+["wheel","--no-deps","--no-build-isolation","--no-index","--wheel-dir",artifacts,fixed_source],outside)
    wheel = next(artifacts.glob("annotation_contracts-*.whl"))
    binding = []
    with zipfile.ZipFile(wheel) as z:
        for path in source_paths:
            if path.startswith("src/"):
                name = path[len("src/"):]
                assert z.read(name) == all_values[(DELIVERY,path)]
                binding.append(dict(wheel_path=name,source_path=path,source_oid=d[path]["oid"],sha256=sha(z.read(name))))
    write(EVIDENCE/"wheel-source-binding.json",dict(wheel=wheel.name,sha256=sha(wheel.read_bytes()),bytes=wheel.stat().st_size,source_commit=DELIVERY,implementation_commit=IMPLEMENTATION,source_files=binding))
    run("install-fixed-wheel",pip+["install","--no-index","--find-links",downloads,"--report",EVIDENCE/"install-report.json",wheel],outside)
    install_report=json.loads((EVIDENCE/"install-report.json").read_text(encoding="utf-8"))
    product_report=next(x for x in install_report["install"] if x["metadata"]["name"].replace("_","-").lower()=="annotation-contracts")
    assert product_report["download_info"]["archive_info"]["hashes"]["sha256"]==sha(wheel.read_bytes())
    run("pip-check",pip+["check"],outside)
    run("pip-list",pip+["list","--format=json"],outside)
    run("installed-provenance",[python,"-I",PROBE,"provenance",wheel,EVIDENCE/"installed-provenance.json"],outside)
    consumer=relocated/"examples/a01/consume.py"
    source_cases=[]
    negative=[]
    for book in ("46006966","46007447"):
        bundle=relocated/"examples/a01/R3/bundles"/book
        run("consume-"+book,[python,"-I",PROBE,"consume",consumer,bundle/"exchange.json",book,EVIDENCE/("consumer-"+book+".json")],outside)
        data=json.loads((bundle/"exchange.json").read_text(encoding="utf-8"))
        resource=data["artifacts"][0]["payload"]["assets"][0]["path"]
        for kind,code in (("missing","RESOURCE_MISSING"),("hash-damage","RESOURCE_HASH")):
            copy_root=outside/"negative copies"/(book+"-"+kind)
            shutil.copytree(bundle,copy_root)
            before_files=files(copy_root)
            asset=copy_root/resource
            if kind=="missing": asset.unlink()
            else:
                raw=bytearray(asset.read_bytes()); raw[len(raw)//2]^=1; asset.write_bytes(raw)
            after_files=files(copy_root)
            changed=sorted(p for p in set(before_files)|set(after_files) if before_files.get(p)!=after_files.get(p))
            assert changed==[resource]
            output=EVIDENCE/("negative-"+book+"-"+kind+".json")
            run("negative-"+book+"-"+kind,[python,"-I",PROBE,"consume",consumer,copy_root/"exchange.json",book,output],outside,expected=1)
            observed=json.loads(output.read_text(encoding="utf-8"))
            assert code in observed["error"] and observed["result"]=="REJECTED"
            delta=EVIDENCE/"negative-deltas"/(book+"-"+kind)
            delta.mkdir(parents=True)
            if kind!="missing": (delta/Path(resource).name).write_bytes(asset.read_bytes())
            mutation=dict(book_id=book,kind=kind,expected_code=code,changed_paths=changed,before=before_files,after=after_files,
                          replay="Copy fixed R3 package, replace or remove the one changed resource; exchange remains fixed.")
            write(delta/"mutation.json",mutation)
            negative.append(mutation)
        copy_root=outside/"negative copies"/(book+"-decode")
        shutil.copytree(bundle,copy_root)
        before_decode=files(copy_root)
        output=EVIDENCE/("negative-"+book+"-decode.json")
        run("decode-layer-"+book,[python,"-I",PROBE,"decode",copy_root/"exchange.json",book,output,EVIDENCE/"negative-deltas"/(book+"-decode")],outside,expected=1)
        observed=json.loads(output.read_text(encoding="utf-8"))
        assert observed["public_resource_layer"]=="PASS" and observed["pillow_full_load"]=="REJECTED" and observed["code"]=="IMAGE_DECODE"
        after_decode=files(copy_root)
        changed=sorted(p for p in set(before_decode)|set(after_decode) if before_decode.get(p)!=after_decode.get(p))
        assert set(changed)==set(observed["changed_paths"])
        mutation=dict(book_id=book,kind="decode",changed_paths=changed,before=before_decode,after=after_decode)
        negative.append(mutation)
    write(EVIDENCE/"negative-input-index.json",negative)
    run("source-regression",[python,"-I",PROBE,"source-regression",relocated/"examples/a01/R3/bundles/46006966/exchange.json",relocated/"examples/a01/R3/bundles/46007447/exchange.json",EVIDENCE/"source-regression.json"],outside)
    run("contract-regression",[python,"-I",PROBE,"regression",regression_root,EVIDENCE/"contract-regression.json"],outside)
    assert files(original)==original_hashes and files(relocated)==original_hashes
    assert {path:sha((fixed_source/path).read_bytes()) for path in source_before}==source_before
    assert files(preparation)==protected and sha((WORKSPACE/"docs/tasks/D01-review-preparation.md").read_bytes())==protected_report
    assert all(sha(Path(item["destination"]).read_bytes())==item["sha256"] for item in regression_index)
    write(EVIDENCE/"post-run-preservation.json",dict(preparation_files_unchanged=len(protected),preparation_report_unchanged=True,
          source_input_files_unchanged=len(source_before),regression_input_files_unchanged=len(regression_index),
          original_sample_files_unchanged=len(original_hashes),relocated_sample_files_unchanged=len(original_hashes),
          original_samples=original_hashes,relocated_samples=files(relocated)))
    write(EVIDENCE/"run-result.json",dict(result="INDEPENDENT_FUNCTIONAL_CHECKS_PASSED",base=BASE,implementation=IMPLEMENTATION,delivery=DELIVERY,workflow=WORKFLOW,
          wheel_sha256=sha(wheel.read_bytes()),commands=len(COMMANDS),all_commands_returned=True,
          expected_rejection_subprocesses=6,remaining_own_background_processes_started=0,
          scope="CPython3.9 Windows only; finite REFERENCE_ONLY R3 packages; coordinator integration still required."))
    print(json.dumps(dict(result="INDEPENDENT_FUNCTIONAL_CHECKS_PASSED",commands=len(COMMANDS),wheel_sha256=sha(wheel.read_bytes()),outside=str(outside))))


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description="Replay into NEW exclusive stage/evidence directories; never overwrite this review.")
    parser.add_argument("--stage",type=Path,required=True)
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    args.stage.resolve().relative_to((WORKSPACE/".local").resolve())
    args.evidence.resolve().relative_to(EVIDENCE.resolve())
    if args.stage.exists() or args.evidence.exists():
        raise SystemExit("Both replay targets must be nonexistent; existing evidence is protected.")
    STAGE=args.stage.resolve()
    EVIDENCE=args.evidence.resolve()
    EVIDENCE.mkdir(parents=True)
    try:
        main()
    except BaseException as error:
        write(EVIDENCE/"attempt-failure.json",dict(error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),commands_returned=COMMANDS))
        raise
