"""Independent raw-Git preservation, EOL diagnosis and six-package relocation."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
BOOT=json.loads((OUT/"bootstrap.json").read_text(encoding="utf-8"))
SNAPSHOT=Path(BOOT["snapshot"]);WORK=Path(BOOT["temporary_root"])
sys.path.insert(0,str(SNAPSHOT/"src"))
from PIL import Image
import annotation.contracts as contracts
import annotation.source.static.importer as importer

def read(path):return json.loads(path.read_text(encoding="utf-8-sig"))
def sha(data):return hashlib.sha256(data).hexdigest()
def hashes(folder):return {p.relative_to(folder).as_posix():sha(p.read_bytes()) for p in folder.rglob("*") if p.is_file()}
def tree(ref):
    rows=subprocess.run(["git","-C",str(ROOT),"ls-tree","-r","-z",ref],check=True,capture_output=True).stdout
    return {r.split(b"\t",1)[1].decode("utf-8"):r.split(b"\t",1)[0].split()[2].decode() for r in rows.split(b"\0") if r}

def main():
    evidence=OUT/"preservation-relocation";evidence.mkdir(exist_ok=False)
    work=WORK/"independent six package copies";work.mkdir(exist_ok=False)
    cwd=work/"unrelated cwd";cwd.mkdir()
    checks=[]
    def check(name,actual,expected):checks.append({"name":name,"actual":actual,"expected":expected,"pass":actual==expected})
    baseline=read(SNAPSHOT/"docs/evidence/A01/execution/R2/baseline.json")
    base_tree=tree(BOOT["R2_base"])
    preserved=[];disk_baseline_mismatches=[]
    for entry in baseline["preserved_tracked_files"]:
        path=entry["path"];data=(SNAPSHOT/path).read_bytes()
        oid=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
        check("preserved Git blob "+path,oid,base_tree[path])
        preserved.append({"path":path,"base_blob_oid":base_tree[path],"current_blob_oid":oid,"raw_git_sha256":sha(data)})
        if sha(data)!=entry["sha256"]:
            lf=data.replace(b"\r\n",b"\n");crlf=lf.replace(b"\n",b"\r\n")
            disk_baseline_mismatches.append({"path":path,"declared_disk_sha256":entry["sha256"],"raw_git_sha256":sha(data),
                                             "LF_sha256":sha(lf),"CRLF_sha256":sha(crlf),
                                             "difference_only_uniform_EOL":entry["sha256"] in (sha(lf),sha(crlf))})
    check("all author preservation mismatches explained solely by EOL",all(r["difference_only_uniform_EOL"] for r in disk_baseline_mismatches),True)
    original_inputs={}
    for book in ("46006966","46007447"):
        for entry in read(SNAPSHOT/"examples/a01/bundles"/book/"input-integrity.json")["inputs"]:original_inputs[entry["archive_path"]]=entry
    for path,entry in original_inputs.items():
        check("original before/after/Git bytes "+path,[entry["before_sha256"],entry["after_sha256"]],[sha((SNAPSHOT/path).read_bytes())]*2)
    read_only=[]
    for entry in baseline["read_only_inputs"]:
        path=Path(entry["path"]).resolve();path.relative_to((ROOT/"docs").resolve())
        actual=sha(path.read_bytes());check("frozen main input "+entry["path"],actual,entry["sha256"])
        read_only.append(dict(entry,actual_sha256=actual))
    env=dict(os.environ,PYTHONPATH=str(SNAPSHOT/"src"),PYTHONDONTWRITEBYTECODE="1",TMP=str(work),TEMP=str(work),TMPDIR=str(work))
    runs=[]
    for version,base,impl in (("legacy","examples/a01/bundles","a01-static-1"),("R1","examples/a01/R1/bundles","a01-static-1-r1"),("R2","examples/a01/R2/bundles","a01-static-1-r2")):
        for book,count,meta,origins in (("46006966",6,250,10),("46007447",2,214,4)):
            folder=SNAPSHOT/base/book;before=hashes(folder)
            bundle=importer.load_static_bundle(folder/"exchange.json",expected_book_id=book);source=bundle.artifacts[0]
            provenance=read(folder/"provenance.json");limits=read(folder/"limitations.json")
            check(version+book+" inventory",[len(source.payload.assets),source.payload.metadata_page_count,len(provenance["origins"]),source.producer.implementation_version],[count,meta,origins,impl])
            check(version+book+" reference-only status",[limits["coverage_eligible"],limits["independent_denominator_status"],limits["scope_manifest_status"]],[False,"UNKNOWN","REFERENCE_ONLY"])
            for asset in source.payload.assets:
                with Image.open(folder/asset.path) as image:
                    image.load();check(version+book+" decoded "+asset.asset_id,[image.width,image.height,sha((folder/asset.path).read_bytes())],[asset.width,asset.height,asset.sha256])
            for h in source.payload.history:
                check(version+book+" history quality "+h.resource.path,h.quality,"UNVERIFIED")
                if h.reason.startswith("Byte-preserved archived reference: "):
                    original=h.reason.split("Byte-preserved archived reference: ",1)[1].split(";",1)[0]
                    check(version+book+" history bytes "+original,sha((folder/h.resource.path).read_bytes()),sha((SNAPSHOT/original).read_bytes()))
            copied=work/("portable "+version+" "+book);shutil.copytree(folder,copied)
            check(version+book+" copy bytes",hashes(copied),before)
            command=[sys.executable,"-B",str(SNAPSHOT/"examples/a01/consume.py"),str(copied/"exchange.json"),"--book-id",book]
            proc=subprocess.run(command,cwd=cwd,env=env,capture_output=True)
            name=version+"-"+book;(evidence/(name+".stdout.txt")).write_bytes(proc.stdout);(evidence/(name+".stderr.txt")).write_bytes(proc.stderr)
            check(name+" relocated exit",proc.returncode,0);check(name+" source unchanged",hashes(folder),before)
            runs.append({"version":version,"book":book,"command":command,"cwd":str(cwd),"exit_code":proc.returncode,"files":before})
    archived=read(SNAPSHOT/"docs/evidence/A01/execution/R2/archive-manifest.json")
    manifest_entries=[]
    for entry in archived["files"]:
        actual=sha((SNAPSHOT/entry["path"]).read_bytes());check("R2 archive manifest "+entry["path"],actual,entry["sha256"])
        manifest_entries.append(dict(entry,actual_sha256=actual))
    patch=subprocess.run(["git","-C",str(ROOT),"diff",BOOT["R2_base"],BOOT["target_commit"],"--","tests/test_a01_rework_r1.py"],check=True,capture_output=True).stdout
    (evidence/"existing-R1-test-change.patch").write_bytes(patch)
    result={"target_commit":BOOT["target_commit"],"modules":{"contracts":contracts.__file__,"importer":importer.__file__},"temporary_root":str(WORK),
            "checks":checks,"preserved_raw_Git_files":preserved,"author_disk_baseline_EOL_differences":disk_baseline_mismatches,
            "original_inputs":original_inputs,"main_read_only_inputs":read_only,"package_runs":runs,"archive_manifest_entries":manifest_entries,
            "passed":sum(c["pass"] for c in checks),"failed":sum(not c["pass"] for c in checks)}
    with (evidence/"results.json").open("x",encoding="utf-8") as handle:json.dump(result,handle,ensure_ascii=False,indent=2)
    print(json.dumps({"passed":result["passed"],"failed":result["failed"],"preserved_Git_files":len(preserved),"original_inputs":len(original_inputs),"main_inputs":len(read_only),"relocated_packages":len(runs),"EOL_only_author_baseline_mismatches":len(disk_baseline_mismatches),"archive_entries":len(manifest_entries)}))
    raise SystemExit(bool(result["failed"]))

if __name__=="__main__":main()
