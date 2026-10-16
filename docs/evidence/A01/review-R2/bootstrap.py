"""Export exact R2 Git bytes; preserve prior review artifacts."""
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
COMMIT="c3aff9598b6705ab4122062615a13ae3774698b2"
BASE="03c1af41a134945c406a52a48e3d4f6f0da33eb2"

def git(*args):return subprocess.run(["git","-C",str(ROOT),*args],check=True,capture_output=True).stdout
def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    snapshot=ROOT/".local/stages/A01-review-R2"/COMMIT/"snapshot"
    snapshot.mkdir(parents=True,exist_ok=False)
    archive=git("-c","core.autocrlf=false","archive","--format=zip",COMMIT)
    with zipfile.ZipFile(io.BytesIO(archive)) as handle:
        for entry in handle.infolist():(snapshot/entry.filename).resolve().relative_to(snapshot.resolve())
        handle.extractall(snapshot)
    records,restored=[],[]
    for entry in git("ls-tree","-r","-z",COMMIT).split(b"\0"):
        if not entry:continue
        metadata,path_raw=entry.split(b"\t",1)
        mode,kind,oid=metadata.split();path=path_raw.decode("utf-8")
        if kind != b"blob" or mode == b"120000":raise RuntimeError("unsupported export: "+path)
        data=(snapshot/path).read_bytes()
        if hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()!=oid.decode():
            data=git("cat-file","blob",oid.decode());(snapshot/path).write_bytes(data);restored.append(path)
        if hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()!=oid.decode():raise RuntimeError("blob mismatch")
        records.append({"path":path,"bytes":len(data),"sha256":sha(data),"git_blob_oid":oid.decode()})
    report_sha=sha((snapshot/"docs/tasks/A01-rework-R2-report.md").read_bytes())
    manifest_sha=sha((snapshot/"docs/evidence/A01/execution/R2/archive-manifest.json").read_bytes())
    assert report_sha=="3aeaaf40e55163541921ec5915995cc9d01b878bb6843f76fb9f048d5dba8d50"
    assert manifest_sha=="ed4aee2d5aaf4b71f5eee6c60c90c0b58c1672a4803507bb03d1056c00000576"
    paths=[p for p in git("diff","--name-only","-z",BASE,COMMIT).decode("utf-8").split("\0") if p]
    prefixes=("src/annotation/source/static/","tests/test_a01","tests/fixtures/a01/R2/","examples/a01/R2/","docs/evidence/A01/execution/R2/")
    explicit={"docs/a01-source-geometry.md","docs/tasks/A01-rework-R2-report.md"}
    out_of_scope=[p for p in paths if p not in explicit and not p.startswith(prefixes)]
    old=[]
    for folder in ("docs/evidence/A01/review","docs/evidence/A01/review-R1"):
        old.extend(p for p in (ROOT/folder).rglob("*") if p.is_file())
    old.extend(ROOT/p for p in ("docs/tasks/A01-review-report.md","docs/tasks/A01-review-final-report.md","docs/tasks/A01-review-R1-report.md"))
    old_records=[{"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in sorted(set(old))]
    temporary=Path(tempfile.gettempdir()).resolve()
    assert ".local" not in temporary.parts
    work=Path(tempfile.mkdtemp(prefix="A01-review-R2-c3aff959-",dir=str(temporary)))
    geometry="src/annotation/geometry/__init__.py"
    geometry_data=(snapshot/geometry).read_bytes()
    assert geometry_data==git("show",BASE+":"+geometry)
    assert sha(geometry_data)=="3b707579cd586887da3b5125048b17c5baf548010fccf6cb21cc386baddaacf0"
    ancestors={ref:subprocess.run(["git","-C",str(ROOT),"merge-base","--is-ancestor",ref,COMMIT]).returncode==0 for ref in (BASE,"63ac5a184798326d629a43d1dfed25fa73a1a27e","4e42668ab28eda37a37285285d2f6c595d3bba12")}
    result={"observed_at":datetime.now(timezone(timedelta(hours=8))).isoformat(),"target_commit":COMMIT,"implementation_commit":"63ac5a184798326d629a43d1dfed25fa73a1a27e","R2_base":BASE,
            "original_base_workflow":"39341c98d73c354d639f3beeb55429f55d0e9be5","snapshot":str(snapshot),"temporary_root":str(work),
            "verified_blobs":records,"archive_attribute_restored":restored,"report_sha256":report_sha,"archive_manifest_sha256":manifest_sha,
            "changed_paths":paths,"out_of_scope":out_of_scope,"ancestors":ancestors,"old_review_records":old_records,
            "geometry_sha256":sha(geometry_data),"geometry_independent_630_rerun":False,
            "geometry_reference":"docs/evidence/A01/review-R1/geometry/summary.json"}
    with (OUT/"bootstrap.json").open("x",encoding="utf-8",newline="\n") as handle:json.dump(result,handle,ensure_ascii=False,indent=2);handle.write("\n")
    print(json.dumps({"snapshot":str(snapshot),"temporary_root":str(work),"blobs":len(records),"changed_paths":len(paths),"out_of_scope":out_of_scope,"old_review_files":len(old_records)}))

if __name__=="__main__":main()
