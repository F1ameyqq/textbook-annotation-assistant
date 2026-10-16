"""Export exact R1 blobs and preserve all previous review evidence."""
import hashlib
import io
import json
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
COMMIT="03c1af41a134945c406a52a48e3d4f6f0da33eb2"
BASE="a8d5e96d128e10d341de935d4856682e50df79d9"
STAGE=ROOT/".local/stages/A01-review-R1"/COMMIT

def git(*args):
    return subprocess.run(["git","-C",str(ROOT),*args],check=True,capture_output=True).stdout

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    snapshot=STAGE/"snapshot"
    snapshot.mkdir(parents=True,exist_ok=False)
    archive=git("-c","core.autocrlf=false","archive","--format=zip",COMMIT)
    with zipfile.ZipFile(io.BytesIO(archive)) as handle:
        for entry in handle.infolist():
            (snapshot/entry.filename).resolve().relative_to(snapshot.resolve())
        handle.extractall(snapshot)
    records,restored=[],[]
    for entry in git("ls-tree","-r","-z",COMMIT).split(b"\0"):
        if not entry: continue
        metadata,path_raw=entry.split(b"\t",1)
        mode,kind,oid=metadata.split()
        path=path_raw.decode("utf-8")
        if kind != b"blob" or mode == b"120000": raise RuntimeError("unsupported tree entry: "+path)
        data=(snapshot/path).read_bytes()
        actual=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
        if actual != oid.decode():
            data=git("cat-file","blob",oid.decode())
            (snapshot/path).write_bytes(data)
            restored.append(path)
        if hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest() != oid.decode():
            raise RuntimeError("blob mismatch: "+path)
        records.append({"path":path,"bytes":len(data),"sha256":sha(data),"git_blob_oid":oid.decode()})
    report_sha=sha((snapshot/"docs/tasks/A01-rework-R1-report.md").read_bytes())
    if report_sha != "61eb2ec6c666d112caf7eb07367f5d35d48ce596453215d92001614000bf2b40":
        raise RuntimeError("R1 report mismatch")
    paths=git("diff","--name-only","-z",BASE,COMMIT).decode("utf-8").split("\0")
    paths=[p for p in paths if p]
    prefixes=("src/annotation/source/static/","src/annotation/geometry/","tests/test_a01","tests/fixtures/a01/","examples/a01/R1/","docs/evidence/A01/execution/R1/")
    explicit={"docs/a01-source-geometry.md","docs/tasks/A01-rework-R1-report.md"}
    out_of_scope=[p for p in paths if p not in explicit and not p.startswith(prefixes)]
    old_folder=ROOT/"docs/evidence/A01/review"
    old_paths=sorted(p for p in old_folder.rglob("*") if p.is_file())
    old_paths += [ROOT/"docs/tasks/A01-review-report.md",ROOT/"docs/tasks/A01-review-final-report.md"]
    old_records=[{"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in old_paths]
    temp_parent=Path(tempfile.gettempdir()).resolve()
    if ".local" in temp_parent.parts: raise RuntimeError("ordinary temporary root required")
    work=Path(tempfile.mkdtemp(prefix="A01-review-R1-03c1af41-",dir=str(temp_parent)))
    ancestors={ref:subprocess.run(["git","-C",str(ROOT),"merge-base","--is-ancestor",ref,COMMIT]).returncode == 0 for ref in (BASE,"0ee7e836e3bc1849f91840b4271d233bbd8e72dd","4e42668ab28eda37a37285285d2f6c595d3bba12")}
    result={"observed_at":datetime.now(timezone(timedelta(hours=8))).isoformat(),"target_commit":COMMIT,"R1_base":BASE,
            "original_base_workflow":"39341c98d73c354d639f3beeb55429f55d0e9be5","snapshot":str(snapshot),"temporary_root":str(work),
            "archive_attribute_restored":restored,"verified_blobs":records,"report_sha256":report_sha,
            "changed_paths":paths,"out_of_scope":out_of_scope,"ancestors":ancestors,"old_review_records":old_records}
    with (OUT/"bootstrap.json").open("x",encoding="utf-8",newline="\n") as handle:
        json.dump(result,handle,ensure_ascii=False,indent=2);handle.write("\n")
    print(json.dumps({"target_commit":COMMIT,"snapshot":str(snapshot),"temporary_root":str(work),"blobs":len(records),"changed_paths":len(paths),"out_of_scope":out_of_scope,"old_review_files":len(old_records),"ancestors":ancestors}))

if __name__ == "__main__":main()
