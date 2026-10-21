"""Raw Git packaging of the one-file callback delta; no tests or live entry."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"docs/evidence/A24/route-callback-minimum"
BASE="23d6743a1f9540016af5581dcc0d587a052cf309"
CHANGED={"src/annotation/delivery/live_pilot/usense.py"}
PREFIXES=("tests/a24_route_callback/","docs/evidence/A24/route-callback-minimum/")
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.run(["git","-c","core.longpaths=true",*args],cwd=ROOT,env=dict(os.environ,GIT_NO_LAZY_FETCH="1"),check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
def tree(commit):return {row.split(b"\t",1)[1].decode():row.split(b"\t",1)[0] for row in git("ls-tree","-r","-z",commit).split(b"\0") if row}
def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as h:h.write((json.dumps(value,indent=2)+"\n").encode())
def records(commit,paths):
    paths=sorted(paths);queries="".join(commit+":"+p+"\n" for p in paths).encode()
    raw=subprocess.run(["git","-c","core.longpaths=true","cat-file","--batch"],input=queries,cwd=ROOT,env=dict(os.environ,GIT_NO_LAZY_FETCH="1"),check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
    pos=0;result=[]
    for path in paths:
        end=raw.index(b"\n",pos);header=raw[pos:end].split();assert header[1]==b"blob";count=int(header[2]);pos=end+1
        content=raw[pos:pos+count];pos+=count+1;assert raw[pos-1:pos]==b"\n"
        result.append((path,content))
    assert pos==len(raw)
    return result
def package(product):
    before,after=tree(BASE),tree(product)
    changed={p for p in before.keys()&after.keys() if before[p]!=after[p]};added=set(after)-set(before)
    assert not(set(before)-set(after)) and changed==CHANGED and all(p.startswith(PREFIXES) for p in added)
    put(OUT/"old-preservation.json",{"base":BASE,"product":product,"old_members":len(before),"changed":sorted(changed),"added":sorted(added),"deleted":[],
        "all_other_raw_mode_type_blobs_preserved":True,"all_old_evidence_preserved":all(before[p]==after[p] for p in before if p.startswith("docs/evidence/"))})
    old=json.loads((ROOT/"docs/evidence/A24/first-save-minimum-gate/candidate-manifest.json").read_bytes())
    selected={r["path"] for r in old["dependencies"]}
    selected.update(p for p in after if p.startswith("tests/a24_route_callback/") and p.endswith(".py"))
    selected.update({"docs/evidence/A24/route-callback-minimum/library-provenance.json","docs/evidence/A24/route-callback-minimum/task.md",
        "docs/evidence/A24/minimum-gate-current-body-actual/stderr-finite-facts.json","docs/evidence/A24/minimum-gate-current-body-actual/private-raw-manifest.json"})
    deps=[]
    for name,raw in records(product,selected):
        dest=OUT/"raw-checkout"/name;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open("xb") as h:h.write(raw)
        deps.append({"path":name,"bytes":len(raw),"sha256":sha(raw)})
    put(OUT/"candidate-manifest.json",{"schema":"A24R1FrozenCandidate/v1","task":"A24","product":git("rev-parse",product).decode().strip(),"base":BASE,
        "scope_sha256":old["scope_sha256"],"dependencies":deps,"status":"AUTHOR_OFFLINE_CALLBACK_DELTA_PENDING_SAME_REVIEWER",
        "actual_source_final":BASE,"actual_round_remaining":0,"new_live_authority_created":False,"actual_save":"NOT_RUN",
        "body_schema":"UNKNOWN","library_provenance":"docs/evidence/A24/route-callback-minimum/library-provenance.json"})
    print(json.dumps({"dependencies":len(deps),"old_members":len(before),"old_product_paths_changed":1,"old_evidence_preserved":True}))
def seal(commit):
    members=tree(commit);candidate=json.loads((OUT/"candidate-manifest.json").read_bytes())
    paths=set(CHANGED);paths.update(p for p in members if p.startswith(PREFIXES));paths.update(v["path"] for v in candidate["dependencies"])
    data=[{"path":p,"bytes":len(raw),"sha256":sha(raw)} for p,raw in records(commit,paths)]
    put(OUT/"delivery-final-manifest.json",{"schema":"A24CallbackMinimumRawDelivery/v1","content_commit":git("rev-parse",commit).decode().strip(),"self_excluded":True,
        "members":data,"members_count":len(data),"source":"RAW_GIT_BLOBS","formal_acceptance":"PENDING"})
    print(json.dumps({"members":len(data),"manifest_sha256":sha((OUT/"delivery-final-manifest.json").read_bytes())}))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("mode",choices=("package","seal"));p.add_argument("--commit",required=True);args=p.parse_args()
    package(args.commit) if args.mode=="package" else seal(args.commit)
