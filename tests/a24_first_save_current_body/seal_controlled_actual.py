"""Seal the current fixed successful acquisition from raw Git bytes only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2];PREFIX="docs/evidence/A24/controlled-capture-current-body-actual/";OUT=ROOT/PREFIX
BASE="61fb7157eb335d2a0b9348e8496ea0b4b8d17ad0"
HELPERS={"tests/a24_first_save_current_body/freeze_controlled_actual.py","tests/a24_first_save_current_body/seal_controlled_actual.py"}
def git(*args):return subprocess.run(["git","-c","core.longpaths=true",*args],cwd=ROOT,env=dict(os.environ,GIT_NO_LAZY_FETCH="1"),check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
def tree(commit):return {r.split(b"\t",1)[1].decode():r.split(b"\t",1)[0] for r in git("ls-tree","-r","-z",commit).split(b"\0") if r}
p=argparse.ArgumentParser();p.add_argument("--commit",required=True);args=p.parse_args();before,after=tree(BASE),tree(args.commit)
assert set(before)<=set(after) and all(before[n]==after[n] for n in before)
added=set(after)-set(before);assert all(n.startswith(PREFIX) or n in HELPERS for n in added)
members=[]
for name in sorted(added):
    raw=git("show",args.commit+":"+name);members.append({"path":name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})
value={"schema":"A24ControlledBodyFinalRawDelivery/v1","content_commit":git("rev-parse",args.commit).decode().strip(),"base":BASE,"source":"RAW_GIT_BLOBS",
    "members":members,"members_count":len(members),"self_excluded":True,"all_old_mode_type_blob_members_preserved":len(before),"all_old_evidence_preserved":True,
    "product_source_changes":[],"formal_acceptance":"PENDING_SAME_REVIEWER","new_dispatch_spent":1,"new_dispatch_remaining":0,"actual_save":"NOT_RUN"}
raw=(json.dumps(value,indent=2)+"\n").encode()
with (OUT/"delivery-final-manifest.json").open("xb") as handle:handle.write(raw)
print(json.dumps({"members":len(members),"sha256":hashlib.sha256(raw).hexdigest(),"all_old_members_preserved":len(before),"new_dispatch_remaining":0}))
