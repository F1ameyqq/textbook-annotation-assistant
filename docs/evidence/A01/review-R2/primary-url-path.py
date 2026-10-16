"""Check actual URL path binding independently of query/fragment suffix text."""
import hashlib
import json
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
BOOT=json.loads((OUT/"bootstrap.json").read_text(encoding="utf-8"))
SNAPSHOT=Path(BOOT["snapshot"]);WORK=Path(BOOT["temporary_root"])
sys.path.insert(0,str(SNAPSHOT/"src"))
import annotation.contracts as contracts
import annotation.source.static.importer as importer

def read(path):return json.loads(path.read_text(encoding="utf-8"))
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def update(data,folder,name):
    digest=sha(folder/name)
    for e in data["evidence"]:
        if e["resource"]["path"]==name:e["resource"]["sha256"]=digest
    for h in data["artifacts"][0]["payload"]["history"]:
        if h["resource"]["path"]==name:h["resource"]["sha256"]=digest

def main():
    evidence=OUT/"primary-url-path";evidence.mkdir(exist_ok=False)
    work=WORK/"primary actual URL path";work.mkdir(exist_ok=False)
    rows=[]
    for case in ("Q01-cross-book-path-query-tail","Q02-wrong-index-path-fragment-tail"):
        folder=work/case;shutil.copytree(SNAPSHOT/"examples/a01/R2/bundles/46007447",folder)
        path=folder/"exchange.json";data=read(path)
        relative="history/00-independent-source-page14.json";body=read(folder/relative)
        original=body["data"]["pages"][0]["image"];parts=urlsplit(original)
        if case.startswith("Q01"):
            actual_path=parts.path.replace("/46007447/46007447_","/46006966/46006966_")
            changed=urlunsplit((parts.scheme,parts.netloc,actual_path,"echo="+parts.path,""))
            expected="reject actual URL path for book 46006966 despite correct-book string in query"
        else:
            actual_path=parts.path.replace("_page_13.jpg","_page_172.jpg")
            changed=urlunsplit((parts.scheme,parts.netloc,actual_path,"","echo="+parts.path))
            expected="reject actual URL source index 172 despite source13 string in fragment"
        assert actual_path!=parts.path
        body["data"]["pages"][0]["image"]=changed;write(folder/relative,body);update(data,folder,relative)
        integrity=read(folder/"input-integrity.json")
        entry=next(r for r in integrity["inputs"] if r["archive_path"].endswith("/independent-source-page14.json"))
        entry["before_sha256"]=entry["after_sha256"]=sha(folder/relative)
        write(folder/"input-integrity.json",integrity);update(data,folder,"input-integrity.json")
        data["artifacts"][0]=contracts.seal_artifact(data["artifacts"][0]);write(path,data)
        public=contracts.load_bundle(path,verify_assets=True)
        try:
            loaded=importer.load_static_bundle(path,expected_book_id="46007447")
            actual={"result":"ACCEPT","book":loaded.artifacts[0].book_id}
        except Exception as error:
            actual={"result":"REJECT","exception":type(error).__name__,"code":getattr(error,"code",None),"location":getattr(error,"location",None),"message":str(error)}
        rows.append({"id":case,"original_url":original,"changed_url":changed,"parsed_path":urlsplit(changed).path,
                     "body_file_id":body["data"]["file_id"],"body_page_index":body["data"]["pages"][0]["page_index"],
                     "expected":expected,"public_resource_validation":"ACCEPT","source_content_hash":public.artifacts[0].content_hash,
                     "actual":actual,"matches_expectation":actual.get("exception")=="StaticSourceError" and bool(actual.get("code")) and bool(actual.get("location"))})
        shutil.copytree(folder,evidence/case)
    result={"target_commit":BOOT["target_commit"],"command":[sys.executable,"-B",str(Path(__file__).resolve())],"cwd":str(Path.cwd()),
            "modules":{"contracts":contracts.__file__,"importer":importer.__file__},"temporary_root":str(WORK),"rows":rows,
            "passed":sum(r["matches_expectation"] for r in rows),"failed":sum(not r["matches_expectation"] for r in rows),
            "interpretation":"URI path book/index binding only; no host authentication, external authenticity or network request"}
    write(evidence/"results.json",result)
    print(json.dumps({"passed":result["passed"],"failed":result["failed"],"actual":[r["actual"] for r in rows]}))
    raise SystemExit(bool(result["failed"]))

if __name__=="__main__":main()
