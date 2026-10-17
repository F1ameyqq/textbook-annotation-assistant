"""Export exact R3 final Git bytes, record immutable references and old reviews."""
import hashlib
import io
import json
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
COMMIT="180bb1e86fb2a7eb1546be85af70f466f069daf5"
BASE="c3aff9598b6705ab4122062615a13ae3774698b2"
REFERENCE="aeb7ca306b3dba9d51740071f96592d8e677ec66"
IMPLEMENTATION="31d715a5f2e6435af3a7e98a6c19b41b72d883bd"
def git(*args):return subprocess.run(["git","-C",str(ROOT),*args],check=True,capture_output=True).stdout
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    snapshot=ROOT/".local/stages/A01-review-R3"/COMMIT/"snapshot";snapshot.mkdir(parents=True,exist_ok=False)
    archive=git("-c","core.autocrlf=false","archive","--format=zip",COMMIT)
    with zipfile.ZipFile(io.BytesIO(archive)) as handle:
        for entry in handle.infolist():(snapshot/entry.filename).resolve().relative_to(snapshot.resolve())
        handle.extractall(snapshot)
    records=[];restored=[]
    for entry in git("ls-tree","-r","-z",COMMIT).split(b"\0"):
        if not entry:continue
        metadata,path_raw=entry.split(b"\t",1);mode,kind,oid=metadata.split();path=path_raw.decode("utf-8")
        if kind!=b"blob" or mode==b"120000":raise RuntimeError("unsupported tree entry: "+path)
        data=(snapshot/path).read_bytes()
        if hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()!=oid.decode():
            data=git("cat-file","blob",oid.decode());(snapshot/path).write_bytes(data);restored.append(path)
        assert hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()==oid.decode()
        records.append({"path":path,"bytes":len(data),"sha256":sha(data),"git_blob_oid":oid.decode()})
    report=sha((snapshot/"docs/tasks/A01-rework-R3-report.md").read_bytes());manifest=sha((snapshot/"docs/evidence/A01/execution/R3/archive-manifest.json").read_bytes())
    assert report=="e8218a0083029ffe3e14bf0dfa29db33e0f049e77241c89fced5a84ccabe9472"
    assert manifest=="1798832a3fe194b0b5e9751dd42b99ff5788b85a774eae6d88a4436aef928084"
    handoff=ROOT/"docs/tasks/A01-review-R3-handoff.md";assert sha(handoff.read_bytes())=="b5bf336ced03fff3a3ca975cae8188691a2a4b6526fa3affd59d5399e02b0581"
    changed=[p for p in git("diff","--name-only","-z",BASE,COMMIT).decode("utf-8").split("\0") if p]
    prefixes=("src/annotation/source/static/","tests/fixtures/a01/R3/","examples/a01/R3/","docs/evidence/A01/execution/R3/")
    explicit={"docs/a01-source-geometry.md","docs/tasks/A01-rework-R3-report.md","tests/test_a01_rework_r3.py"}
    out_of_scope=[p for p in changed if p not in explicit and not p.startswith(prefixes)]
    old=[]
    for folder in ("docs/evidence/A01/review","docs/evidence/A01/review-R1","docs/evidence/A01/review-R2"):
        old.extend(p for p in (ROOT/folder).rglob("*") if p.is_file())
    old.extend(ROOT/p for p in ("docs/tasks/A01-review-report.md","docs/tasks/A01-review-final-report.md","docs/tasks/A01-review-R1-report.md","docs/tasks/A01-review-R2-report.md"))
    old_records=[{"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in sorted(set(old))]
    temporary=Path(tempfile.gettempdir()).resolve();assert ".local" not in temporary.parts
    work=Path(tempfile.mkdtemp(prefix="A01-review-R3-180bb1e8-",dir=str(temporary)))
    geometry=(snapshot/"src/annotation/geometry/__init__.py").read_bytes();assert sha(geometry)=="3b707579cd586887da3b5125048b17c5baf548010fccf6cb21cc386baddaacf0"
    assert geometry==git("show",BASE+":src/annotation/geometry/__init__.py")
    ancestors={ref:subprocess.run(["git","-C",str(ROOT),"merge-base","--is-ancestor",ref,COMMIT]).returncode==0 for ref in (BASE,IMPLEMENTATION,REFERENCE,"4e42668ab28eda37a37285285d2f6c595d3bba12")}
    result={"observed_at":datetime.now(timezone(timedelta(hours=8))).isoformat(),"target_commit":COMMIT,"implementation_commit":IMPLEMENTATION,"reference_commit":REFERENCE,"R3_base":BASE,
            "original_workflow":"39341c98d73c354d639f3beeb55429f55d0e9be5","snapshot":str(snapshot),"temporary_root":str(work),"verified_blobs":records,
            "archive_attribute_restored":restored,"execution_report_sha256":report,"archive_manifest_sha256":manifest,"handoff_sha256":sha(handoff.read_bytes()),
            "changed_paths":changed,"out_of_scope":out_of_scope,"ancestors":ancestors,"old_review_records":old_records,
            "geometry_sha256":sha(geometry),"R1_geometry_630_independent_rerun":False}
    with (OUT/"bootstrap.json").open("x",encoding="utf-8",newline="\n") as handle:json.dump(result,handle,ensure_ascii=False,indent=2);handle.write("\n")
    print(json.dumps({"snapshot":str(snapshot),"temporary_root":str(work),"Git_files":len(records),"changed_paths":len(changed),"out_of_scope":out_of_scope,"old_review_files":len(old_records)}))

if __name__=="__main__":main()
