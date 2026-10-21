"""Freeze the minimum gate delta as raw Git bytes; no live or old test entry."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"docs/evidence/A24/first-save-minimum-gate"
BASE="93649b44"
CHANGED={"src/annotation/runtime/live_pilot/authority.py","src/annotation/runtime/live_pilot/owner.py"}
PREFIXES=("tests/a24_first_save_current_body/","docs/evidence/A24/first-save-minimum-gate/")
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.run(["git","-c","core.longpaths=true",*args],cwd=ROOT,env=dict(os.environ,GIT_NO_LAZY_FETCH="1"),check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
def tree(commit):
    return {row.split(b"\t",1)[1].decode():row.split(b"\t",1)[0] for row in git("ls-tree","-r","-z",commit).split(b"\0") if row}
def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as h:h.write((json.dumps(value,indent=2)+"\n").encode())
def record(path,raw):return {"path":path,"bytes":len(raw),"sha256":sha(raw)}
def prepare():
    names=["docs/tasks/A24-first-save-current-body-and-minimal-reopen-continuation.md",
        "docs/evidence/coordinator/a24-first-save-wire-r1-independent-closure/independent-result.json",
        "docs/evidence/coordinator/a24-first-save-wire-r1-independent-closure/root-disposition.json",
        "docs/evidence/coordinator/a24-first-save-wire-r1-independent-closure/report.md"]
    records=[]
    for name in names:
        source=Path("D:/1800")/name;raw=source.read_bytes();dest=OUT/"inputs"/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open("xb") as h:h.write(raw)
        records.append(dict(record(dest.relative_to(ROOT).as_posix(),raw),source=str(source)))
    put(OUT/"input-provenance.json",{"schema":"A24MinimumGateInputs/v1","inputs":records,
        "actual_commit":git("rev-parse",BASE).decode().strip(),"actual_manifest_sha256":"c1cb281a94ee555eec669735ac732ac0e0c19f966e41807018786f16b3e3a467",
        "actual_round_remaining":0,"model_content_revalidation":False,"actual_source_body_snapshots":0})
def package(product):
    before,after=tree(BASE),tree(product)
    changed={p for p in before.keys()&after.keys() if before[p]!=after[p]};added=set(after)-set(before)
    assert not(set(before)-set(after)) and changed==CHANGED and all(p.startswith(PREFIXES) for p in added)
    put(OUT/"old-preservation.json",{"base":git("rev-parse",BASE).decode().strip(),"product":product,"old_members":len(before),
        "changed":sorted(changed),"added":sorted(added),"deleted":[],"all_other_raw_mode_type_blobs_preserved":True,
        "all_old_evidence_preserved":all(before[p]==after[p] for p in before if p.startswith("docs/evidence/"))})
    old=json.loads((ROOT/"docs/evidence/A24/first-save-wire-r1/candidate-manifest.json").read_bytes())
    selected={r["path"] for r in old["dependencies"]}
    selected.update(p for p in after if p.startswith("tests/a24_first_save_current_body/") and p.endswith(".py"))
    deps=[]
    for name in sorted(selected):
        raw=git("show",product+":"+name);dest=OUT/"raw-checkout"/name;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open("xb") as h:h.write(raw)
        deps.append(record(name,raw))
    put(OUT/"candidate-manifest.json",{"schema":"A24R1FrozenCandidate/v1","task":"A24","product":git("rev-parse",product).decode().strip(),
        "base":git("rev-parse",BASE).decode().strip(),"scope_sha256":old["scope_sha256"],"dependencies":deps,
        "status":"AUTHOR_OFFLINE_DELTA_PENDING_SAME_FORMAL_REVIEW","body_schema":"UNKNOWN_NO_NEW_FACTS",
        "actual_round_remaining":0,"save_authority_created":False,"actual_save":"NOT_RUN","source_model_revalidated":False})
    print(json.dumps({"dependencies":len(deps),"old_members":len(before),"changed":2,"old_evidence_preserved":True}))
def seal(commit):
    members=tree(commit);candidate=json.loads((OUT/"candidate-manifest.json").read_bytes())
    paths=set(CHANGED);paths.update(p for p in members if p.startswith(PREFIXES));paths.update(v["path"] for v in candidate["dependencies"])
    records=[record(p,git("show",commit+":"+p)) for p in sorted(paths)]
    put(OUT/"delivery-final-manifest.json",{"schema":"A24MinimumGateRawDelivery/v1","content_commit":commit,"self_excluded":True,
        "members":records,"members_count":len(records),"source":"RAW_GIT_BLOBS","formal_acceptance":"PENDING"})
    print(json.dumps({"members":len(records),"manifest_sha256":sha((OUT/"delivery-final-manifest.json").read_bytes())}))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("mode",choices=("prepare","package","seal"));p.add_argument("--commit");a=p.parse_args()
    if a.mode=="prepare":prepare()
    elif a.mode=="package":package(a.commit)
    else:seal(a.commit)
