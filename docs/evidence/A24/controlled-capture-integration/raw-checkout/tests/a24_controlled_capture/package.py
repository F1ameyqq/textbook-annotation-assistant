"""Raw Git packaging of the one-owner-file capture integration delta."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"docs/evidence/A24/controlled-capture-integration"
BASE="bf92c7b6e1c30a5dd0e4667c3d523ef77af39e01";CHANGED={"src/annotation/runtime/live_pilot/owner.py"}
PREFIXES=("tests/a24_controlled_capture/","docs/evidence/A24/controlled-capture-integration/")
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.run(["git","-c","core.longpaths=true",*args],cwd=ROOT,env=dict(os.environ,GIT_NO_LAZY_FETCH="1"),check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
def tree(commit):return {row.split(b"\t",1)[1].decode():row.split(b"\t",1)[0] for row in git("ls-tree","-r","-z",commit).split(b"\0") if row}
def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as handle:handle.write((json.dumps(value,indent=2)+"\n").encode())
def records(commit,paths):
    paths=sorted(paths);queries="".join(commit+":"+p+"\n" for p in paths).encode()
    raw=subprocess.run(["git","-c","core.longpaths=true","cat-file","--batch"],input=queries,cwd=ROOT,env=dict(os.environ,GIT_NO_LAZY_FETCH="1"),check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
    pos=0;result=[]
    for path in paths:
        end=raw.index(b"\n",pos);header=raw[pos:end].split();assert header[1]==b"blob";count=int(header[2]);pos=end+1
        content=raw[pos:pos+count];pos+=count+1;assert raw[pos-1:pos]==b"\n";result.append((path,content))
    assert pos==len(raw);return result
def prepare():
    task=Path("D:/1800/docs/tasks/A24-controlled-capture-owner-integration-continuation.md");raw=task.read_bytes()
    with (OUT/"task.md").open("xb") as handle:handle.write(raw)
    sources=[{"source":str(task),"copy":"docs/evidence/A24/controlled-capture-integration/task.md","bytes":len(raw),"sha256":sha(raw)}]
    names={"src/annotation/runtime/live_pilot/owner.py","src/annotation/delivery/live_pilot/usense.py","tools/a16_current_state_probe.py",
        "src/annotation/source/usense/current_readonly/auth.py","docs/evidence/A16/current-readonly/dependencies/a15_native_reference.py",
        "docs/evidence/A24/bootstrap-current-body-actual/actual-result.json","docs/evidence/A24/bootstrap-current-body-actual/static-output-integration-finding.json"}
    for name,raw in records(BASE,names):sources.append({"source":name,"git_commit":BASE,"bytes":len(raw),"sha256":sha(raw)})
    put(OUT/"source-evidence.json",{"schema":"A24ControlledCaptureSourceEvidence/v1","base":BASE,"sources":sources,
        "old_actual_root_causes_reclassified":False,"original_P3_failure_retained":True,"all_old_authorities_remaining":0,"new_actual_resources":0})
def package(product):
    product=git("rev-parse",product).decode().strip();before,after=tree(BASE),tree(product)
    changed={p for p in before.keys()&after.keys() if before[p]!=after[p]};added=set(after)-set(before)
    assert not(set(before)-set(after)) and changed==CHANGED and all(p.startswith(PREFIXES) for p in added)
    put(OUT/"old-preservation.json",{"base":BASE,"product":product,"old_members":len(before),"changed":sorted(changed),"added":sorted(added),"deleted":[],
        "all_other_raw_mode_type_blobs_preserved":True,"all_old_evidence_preserved":all(before[p]==after[p] for p in before if p.startswith("docs/evidence/"))})
    old=json.loads((ROOT/"docs/evidence/A24/bootstrap-exclusion-minimum/candidate-manifest.json").read_bytes())
    selected={r["path"] for r in old["dependencies"]};selected.update(p for p in after if p.startswith("tests/a24_controlled_capture/") and p.endswith(".py"))
    selected.update({"docs/evidence/A24/controlled-capture-integration/source-evidence.json","docs/evidence/A24/controlled-capture-integration/task.md",
        "docs/evidence/A24/bootstrap-current-body-actual/actual-result.json","docs/evidence/A24/bootstrap-current-body-actual/static-output-integration-finding.json"})
    deps=[]
    for name,raw in records(product,selected):
        dest=OUT/"raw-checkout"/name;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open("xb") as handle:handle.write(raw)
        deps.append({"path":name,"bytes":len(raw),"sha256":sha(raw)})
    put(OUT/"candidate-manifest.json",{"schema":"A24R1FrozenCandidate/v1","task":"A24","product":product,"base":BASE,"scope_sha256":old["scope_sha256"],
        "dependencies":deps,"status":"AUTHOR_OFFLINE_CURRENT_OWNER_CAPTURE_DELTA_PENDING_REVIEW","actual_source_final":BASE,"all_old_authorities_remaining":0,
        "new_live_authority_created":False,"actual_save":"NOT_RUN","body_schema":"UNKNOWN","private_capture_root_template":"{NEW_AUTHORITY_OUTPUT}/private/source-capture"})
    print(json.dumps({"product":product,"dependencies":len(deps),"old_members":len(before),"old_source_paths_changed":1,"old_evidence_preserved":True}))
def seal(commit):
    commit=git("rev-parse",commit).decode().strip();members=tree(commit);candidate=json.loads((OUT/"candidate-manifest.json").read_bytes())
    paths=set(CHANGED);paths.update(p for p in members if p.startswith(PREFIXES));paths.update(v["path"] for v in candidate["dependencies"])
    data=[{"path":name,"bytes":len(raw),"sha256":sha(raw)} for name,raw in records(commit,paths)]
    put(OUT/"delivery-final-manifest.json",{"schema":"A24ControlledCaptureRawDelivery/v1","content_commit":commit,"self_excluded":True,"members":data,
        "members_count":len(data),"source":"RAW_GIT_BLOBS","formal_acceptance":"PENDING"})
    print(json.dumps({"members":len(data),"manifest_sha256":sha((OUT/"delivery-final-manifest.json").read_bytes())}))
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("mode",choices=("prepare","package","seal"));parser.add_argument("--commit");args=parser.parse_args()
    if args.mode=="prepare":prepare()
    elif args.mode=="package":package(args.commit)
    else:seal(args.commit)
