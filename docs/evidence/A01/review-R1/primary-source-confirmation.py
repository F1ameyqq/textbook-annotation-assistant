"""Confirm remaining R1 contradictions with independently assembled sealed inputs."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
BOOT=json.loads((OUT/"bootstrap.json").read_text(encoding="utf-8"))
SNAPSHOT=Path(BOOT["snapshot"])
WORK=Path(BOOT["temporary_root"])
sys.path.insert(0,str(SNAPSHOT/"src"))
import annotation.contracts as contracts
import annotation.source.static.importer as importer

def read(path):return json.loads(path.read_text(encoding="utf-8"))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def update_resource(data,folder,name):
    digest=sha(folder/name)
    for item in data["evidence"]:
        if item["resource"]["path"]==name:item["resource"]["sha256"]=digest
    for item in data["artifacts"][0]["payload"]["history"]:
        if item["resource"]["path"]==name:item["resource"]["sha256"]=digest

def main():
    evidence=OUT/"primary-source-confirmation"
    evidence.mkdir(exist_ok=False)
    work=WORK/"primary source contradictions"
    work.mkdir(exist_ok=False)
    records=[]
    cases=[("P01-acquired-also-missing","46006966","provenance.json"),
           ("P02-page-response-cross-book-url","46007447","history/00-independent-source-page14.json"),
           ("P03-page-response-index-url-conflict","46007447","history/00-independent-source-page14.json"),
           ("P04-observation-index-digest-conflict","46007447","provenance.json")]
    for name,book,resource in cases:
        folder=work/name
        shutil.copytree(SNAPSHOT/"examples/a01/R1/bundles"/book,folder)
        data=read(folder/"exchange.json")
        value=read(folder/resource)
        if name.startswith("P01"):
            value["selected_missing_source_indices"]=[7]
            expected="reject acquired source index 7 simultaneously listed missing"
        elif name.startswith("P02"):
            value["data"]["pages"][0]["image"]=value["data"]["pages"][0]["image"].replace("46007447","46006966")
            expected="reject page response file_id 46007447 with image URL for book 46006966"
        elif name.startswith("P03"):
            value["data"]["pages"][0]["image"]=value["data"]["pages"][0]["image"].replace("_page_13.jpg","_page_172.jpg")
            expected="reject page_index 13 with same-book URL source index 172"
        else:
            value["observation"]["observation_index_source"]["sha256"]="0"*64
            expected="reject observation source digest inconsistent with same archive path retained in input-integrity"
        write(folder/resource,value)
        update_resource(data,folder,resource)
        if resource.startswith("history/"):
            # Keep byte-level import records self-consistent so this probe tests
            # the response's semantic contradiction instead of HISTORY_BYTES.
            integrity=read(folder/"input-integrity.json")
            matches=[r for r in integrity["inputs"] if r["archive_path"].endswith("/independent-source-page14.json")]
            assert len(matches)==1
            matches[0]["before_sha256"]=matches[0]["after_sha256"]=sha(folder/resource)
            write(folder/"input-integrity.json",integrity)
            update_resource(data,folder,"input-integrity.json")
        data["artifacts"][0]=contracts.seal_artifact(data["artifacts"][0])
        write(folder/"exchange.json",data)
        public=contracts.load_bundle(folder/"exchange.json",verify_assets=True)
        try:
            result=importer.load_static_bundle(folder/"exchange.json",expected_book_id=book)
            actual={"result":"ACCEPT","book_id":result.artifacts[0].book_id}
        except Exception as error:
            actual={"result":"REJECT","exception":type(error).__name__,"code":getattr(error,"code",None),"message":str(error)}
        records.append({"id":name,"book":book,"input_resource":resource,"changed_value":value,"expected":expected,
                        "public_resource_validation":"ACCEPT","source_content_hash":public.artifacts[0].content_hash,
                        "actual":actual,"matches_expectation":actual["result"]=="REJECT"})
        shutil.copytree(folder,evidence/name)
    result={"target_commit":BOOT["target_commit"],"module_paths":{"contracts":contracts.__file__,"importer":importer.__file__},
            "command":[sys.executable,"-B",str(Path(__file__).resolve())],"temporary_root":str(WORK),"records":records,
            "passed":sum(r["matches_expectation"] for r in records),"failed":sum(not r["matches_expectation"] for r in records)}
    write(evidence/"results.json",result)
    print(json.dumps({"passed":result["passed"],"failed":result["failed"],"actual":[{"id":r["id"],"result":r["actual"]["result"]} for r in records]}))
    raise SystemExit(bool(result["failed"]))

if __name__=="__main__":main()
