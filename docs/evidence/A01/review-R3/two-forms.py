"""Run the Git-free verifier against controlled checkout and raw Git bytes."""
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
BOOT=json.loads((OUT/"bootstrap.json").read_text(encoding="utf-8"))
FINAL=Path(BOOT["snapshot"]);WORK=Path(BOOT["temporary_root"])
REFERENCE=BOOT["reference_commit"]
def sha(data):return hashlib.sha256(data).hexdigest()
def write(path,data):
    with path.open("x",encoding="utf-8",newline="\n") as handle:json.dump(data,handle,ensure_ascii=False,indent=2);handle.write("\n")
def main():
    evidence=OUT/"two-forms";evidence.mkdir(exist_ok=False)
    listing=subprocess.run(["git","-C",str(ROOT),"ls-tree","-r","-z",REFERENCE],check=True,capture_output=True).stdout
    rows=[]
    for raw in listing.split(b"\0"):
        if not raw:continue
        metadata,path_raw=raw.split(b"\t",1);mode,kind,oid=metadata.split();path=path_raw.decode("utf-8")
        assert kind==b"blob" and mode in (b"100644",b"100755")
        data=(FINAL/path).read_bytes()
        assert hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()==oid.decode(),path
        rows.append({"path":path,"git_blob_oid":oid.decode(),"sha256":sha(data),"bytes":len(data)})
    normal=WORK/"controlled checkout";raw_tree=WORK/"raw Git no-git export"
    setup_commands=[]
    for command in (["git","clone","--shared","--no-checkout","--quiet",str(ROOT),str(normal)],
                    ["git","-C",str(normal),"-c","core.autocrlf=false","checkout","--quiet","--detach",REFERENCE]):
        proc=subprocess.run(command,capture_output=True)
        setup_commands.append({"command":command,"exit_code":proc.returncode,"stdout":proc.stdout.decode("utf-8","replace"),"stderr":proc.stderr.decode("utf-8","replace")})
        if proc.returncode:raise RuntimeError(setup_commands[-1])
    raw_tree.mkdir(exist_ok=False)
    restored=[]
    for row in rows:
        path=row["path"];data=(FINAL/path).read_bytes()
        current=normal/path
        if current.read_bytes()!=data:
            restored.append({"path":path,"checkout_sha256":sha(current.read_bytes()),"fixed_git_sha256":sha(data)})
            current.write_bytes(data)
        target=raw_tree/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    # This is an explicitly controlled checkout representation, not a claim
    # about all Windows autocrlf configurations. Use only committed candidates.
    candidates={}
    for name in ("preservation-manifest.json","code-reference.json"):
        manifest=json.loads((FINAL/"tests/fixtures/a01/R3"/name).read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            crlf=[r for r in entry["representations"] if r["kind"]=="FIXED_CRLF_TEXT_REPRESENTATION"]
            if crlf:candidates[entry["path"]]=crlf[0]
    converted=[]
    for path,candidate in candidates.items():
        original=(FINAL/path).read_bytes();assert b"\r" not in original
        data=original.replace(b"\n",b"\r\n")
        assert sha(data)==candidate["sha256"] and len(data)==candidate["bytes"]
        (normal/path).write_bytes(data)
        converted.append({"path":path,"representation":"FIXED_CRLF_TEXT_REPRESENTATION","sha256":sha(data),"bytes":len(data)})
    exported=[]
    for tree,label in ((normal,"controlled-checkout"),(raw_tree,"raw-Git-no-git")):
        records=[]
        for row in rows:
            path=row["path"];data=(tree/path).read_bytes();expected=candidates.get(path) if label=="controlled-checkout" else None
            assert sha(data)==(expected["sha256"] if expected else row["sha256"]),path
            records.append(dict(row,actual_disk_sha256=sha(data),representation="FIXED_CRLF_TEXT_REPRESENTATION" if expected else "GIT_BLOB"))
        exported.append({"label":label,"path":str(tree),"source_commit":REFERENCE,"git_present":(tree/".git").exists(),"files":records})
    assert (normal/".git").exists() and not (raw_tree/".git").exists()
    write(evidence/"source-exports.json",{"final_delivery":BOOT["target_commit"],"runtime_source_commit":REFERENCE,"setup_commands":setup_commands,"checkout_attribute_restores":restored,
                                         "normal_fixed_CRLF_files":converted,"forms":exported,"normal_scope":"Controlled per-file representations explicitly committed in fixed references; not arbitrary checkout/EOL support"})
    def run(tree,label):
        result_folder=evidence/label
        env=dict(os.environ,PYTHONPATH=str(tree/"src"),PYTHONDONTWRITEBYTECODE="1",TMP=str(WORK),TEMP=str(WORK),TMPDIR=str(WORK))
        if label=="raw-Git-no-git":
            windows=os.environ.get("SystemRoot",r"C:\Windows")
            env["PATH"]=str(Path(windows)/"System32")+os.pathsep+windows
            assert shutil.which("git",path=env["PATH"]) is None
        command=[sys.executable,"-B",str(tree/"examples/a01/R3/verify.py"),str(result_folder)]
        start=time.monotonic();proc=subprocess.run(command,cwd=tree,env=env,capture_output=True)
        (evidence/(label+".stdout.txt")).write_bytes(proc.stdout);(evidence/(label+".stderr.txt")).write_bytes(proc.stderr)
        result={"label":label,"command":command,"cwd":str(tree),"source_commit":REFERENCE,"exit_code":proc.returncode,"seconds":round(time.monotonic()-start,3),
                "git_directory_present":(tree/".git").exists(),"git_available_on_runtime_PATH":shutil.which("git",path=env["PATH"]) is not None,
                "environment_overrides":{k:env[k] for k in ("PYTHONPATH","PYTHONDONTWRITEBYTECODE","TMP","TEMP","TMPDIR","PATH")},
                "stdout":label+".stdout.txt","stderr":label+".stderr.txt","results":label+"/results.json"}
        write(evidence/(label+"-command.json"),result)
        print(label+": exit="+str(proc.returncode),flush=True)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run,tree,label) for tree,label in ((normal,"controlled-checkout"),(raw_tree,"raw-Git-no-git"))]
        results=[future.result() for future in futures]
    write(evidence/"commands.json",results)
    raise SystemExit(any(r["exit_code"] for r in results))

if __name__=="__main__":main()
