"""Independent R1 preservation and legacy/current package relocation checks."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
BOOT=json.loads((OUT/"bootstrap.json").read_text(encoding="utf-8"))
SNAPSHOT=Path(BOOT["snapshot"])
WORK=Path(BOOT["temporary_root"])
sys.path.insert(0,str(SNAPSHOT/"src"))
from PIL import Image
import annotation.contracts as contracts
import annotation.source.static.importer as importer

def read(path):return json.loads(path.read_text(encoding="utf-8-sig"))
def digest(data):return hashlib.sha256(data).hexdigest()
def file_hashes(folder):return {p.relative_to(folder).as_posix():digest(p.read_bytes()) for p in folder.rglob("*") if p.is_file()}

def main():
    evidence=OUT/"preservation-relocation"
    evidence.mkdir(exist_ok=False)
    work=WORK/"independent packages and copies"
    work.mkdir(exist_ok=False)
    cwd=work/"different cwd"
    cwd.mkdir()
    env=dict(os.environ,PYTHONPATH=str(SNAPSHOT/"src"),PYTHONDONTWRITEBYTECODE="1",TMP=str(work),TEMP=str(work),TMPDIR=str(work))
    checks=[]
    def check(name,actual,expected):checks.append({"name":name,"actual":actual,"expected":expected,"pass":actual==expected})
    baseline=read(SNAPSHOT/"docs/evidence/A01/execution/R1/baseline.json")
    preserved=[]
    for entry in baseline["preserved_files"]:
        path=entry["path"]
        old=subprocess.run(["git","-C",str(ROOT),"show",BOOT["R1_base"]+":"+path],check=True,capture_output=True).stdout
        actual=(SNAPSHOT/path).read_bytes()
        check("legacy file unchanged "+path,digest(actual),digest(old))
        check("legacy declared hash "+path,digest(actual),entry["sha256"])
        preserved.append({"path":path,"sha256":digest(actual),"base_blob_sha256":digest(old)})
    input_inventory={}
    for book in ("46006966","46007447"):
        for entry in read(SNAPSHOT/"examples/a01/bundles"/book/"input-integrity.json")["inputs"]:
            input_inventory[entry["archive_path"]]=entry
    for path,entry in input_inventory.items():
        actual=(SNAPSHOT/path).read_bytes()
        base=subprocess.run(["git","-C",str(ROOT),"show",BOOT["R1_base"]+":"+path],check=True,capture_output=True).stdout
        check("input blob unchanged "+path,digest(actual),digest(base))
        check("input before-after "+path,[entry["before_sha256"],entry["after_sha256"]],[digest(actual),digest(actual)])
    records=[]
    for version,base,impl in (("legacy","examples/a01/bundles","a01-static-1"),("R1","examples/a01/R1/bundles","a01-static-1-r1")):
        for book,count,meta,origins in (("46006966",6,250,10),("46007447",2,214,4)):
            folder=SNAPSHOT/base/book
            before=file_hashes(folder)
            loaded=importer.load_static_bundle(folder/"exchange.json",expected_book_id=book)
            source=loaded.artifacts[0]
            provenance=read(folder/"provenance.json")
            limitations=read(folder/"limitations.json")
            check(version+book+" producer",source.producer.implementation_version,impl)
            check(version+book+" inventory",[len(source.payload.assets),source.payload.metadata_page_count,len(provenance["origins"])],[count,meta,origins])
            check(version+book+" no independent denominator",[limitations["coverage_eligible"],limitations["independent_denominator_status"],limitations["scope_manifest_status"]],[False,"UNKNOWN","REFERENCE_ONLY"])
            check(version+book+" history quality",all(h.quality=="UNVERIFIED" for h in source.payload.history),True)
            for asset in source.payload.assets:
                with Image.open(folder/asset.path) as image:
                    image.load()
                    check(version+book+" image "+asset.asset_id,[image.width,image.height,digest((folder/asset.path).read_bytes())],[asset.width,asset.height,asset.sha256])
            for history in source.payload.history:
                if history.reason.startswith("Byte-preserved archived reference: "):
                    original=history.reason.split("Byte-preserved archived reference: ",1)[1].split(";",1)[0]
                    check(version+book+" history bytes "+original,digest((folder/history.resource.path).read_bytes()),digest((SNAPSHOT/original).read_bytes()))
            copy=work/("complete portable "+version+" book "+book)
            shutil.copytree(folder,copy)
            check(version+book+" full copy",file_hashes(copy),before)
            command=[sys.executable,"-B",str(SNAPSHOT/"examples/a01/consume.py"),str(copy/"exchange.json"),"--book-id",book]
            proc=subprocess.run(command,cwd=cwd,env=env,capture_output=True)
            name=version+"-"+book
            (evidence/(name+".stdout.txt")).write_bytes(proc.stdout)
            (evidence/(name+".stderr.txt")).write_bytes(proc.stderr)
            check(name+" relocated exit",proc.returncode,0)
            check(name+" original package unchanged",file_hashes(folder),before)
            records.append({"version":version,"book":book,"command":command,"cwd":str(cwd),"exit_code":proc.returncode,"source_content_hash":source.content_hash,"files":before})
    proof=ROOT/"docs/evidence/A01/review/formal/primary-confirmation/S01-fixed-delivery-input/exchange.json"
    expanded=contracts.load_bundle(proof,verify_assets=True)
    gate=next(a for a in expanded.artifacts if a.kind=="CheckReport")
    check("S01 remains unresolved in unchanged public contracts",[gate.payload.stage,gate.payload.decision],["PRE_APPLY","PASS"])
    result={"target_commit":BOOT["target_commit"],"actual_modules":{"contracts":contracts.__file__,"importer":importer.__file__},
            "temporary_root":str(WORK),"checks":checks,"preserved_legacy_files":preserved,"original_inputs":input_inventory,
            "package_runs":records,"S01_public_synthetic_PASS_still_accepted":True,
            "passed":sum(c["pass"] for c in checks),"failed":sum(not c["pass"] for c in checks)}
    (evidence/"results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"passed":result["passed"],"failed":result["failed"],"legacy_files":len(preserved),"original_inputs":len(input_inventory),"relocated_packages":len(records)}))
    raise SystemExit(bool(result["failed"]))

if __name__=="__main__":main()
