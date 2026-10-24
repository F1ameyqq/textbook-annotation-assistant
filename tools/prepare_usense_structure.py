"""Offline structural evidence/prepare/preflight/verify. No platform operation."""
import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from annotation.runtime.usense_live import structure as s, new_question as n
from annotation.runtime.usense_live.batch import file_ref, ref_bytes, read, write_new
from annotation.runtime.usense_live import update as u


def load_native(root):
    pattern=r"directory|frames|source|page_[0-9]+|q[1-9][0-9]*_(?:annotations|info|question|choice|answer|analysis|knowledge_point)"
    files={p.stem:file_ref(p) for p in Path(root).resolve().glob("*.json") if re.fullmatch(pattern,p.stem)}
    native={key:u.loads(ref_bytes(ref)) for key,ref in files.items()}
    s.full_snapshot(native)
    return native,files


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    p=commands.add_parser("protocol")
    p.add_argument("--frontend",required=True);p.add_argument("--out",required=True)
    for command in ("prepare-move","prepare-new"):
        p=commands.add_parser(command)
        for name in ("baseline","scope-review","protocol","observed-at","out"):
            p.add_argument("--"+name,required=True)
        if command=="prepare-move":
            p.add_argument("--targets",required=True);p.add_argument("--destination",required=True)
        else:
            p.add_argument("--candidate",required=True);p.add_argument("--content-review",required=True)
    p=commands.add_parser("preflight")
    for name in ("bundle","sha256","fresh","ledger-root","out"):
        p.add_argument("--"+name,required=True)
    p=commands.add_parser("verify")
    for name in ("bundle","sha256","after","out"):
        p.add_argument("--"+name,required=True)
    p.add_argument("--receipt");p.add_argument("--runtime-actor-hashes")
    args=parser.parse_args(argv)
    try:
        if args.command=="protocol":
            value=s.protocol_evidence(args.frontend)
        elif args.command.startswith("prepare-"):
            before,files=load_native(args.baseline)
            inputs={key:file_ref(getattr(args,key.replace("-","_"))) for key in ("scope-review","protocol")}
            scope,protocol=read(args.scope_review),read(args.protocol)
            if args.command=="prepare-move":
                inputs["targets"]=file_ref(args.targets)
                draft=s.make_move_draft(before,read(args.targets),args.destination,scope,protocol,args.observed_at)
            else:
                inputs.update(candidate=file_ref(args.candidate),content_review=file_ref(args.content_review))
                draft=n.make_new_draft(before,read(args.candidate),scope,read(args.content_review),protocol,args.observed_at)
            value={"schema":"b-usense-offline-structural-bundle/0.1","draft":draft,"raw_baseline_files":files,
                   "input_files":inputs,"write_authorized":False,"automatic_retry_allowed":False}
        else:
            value=u.loads(ref_bytes({"path":str(Path(args.bundle).resolve()),"sha256":args.sha256}))
            u.require(value["schema"]=="b-usense-offline-structural-bundle/0.1","STRUCTURE_BUNDLE_SCHEMA")
            for ref in (*value["raw_baseline_files"].values(),*value["input_files"].values()):ref_bytes(ref)
            draft=value["draft"]
            if args.command=="preflight":
                fresh,_=load_native(args.fresh)
                value=s.preflight(draft,fresh,args.ledger_root)
            else:
                after,_=load_native(args.after)
                if draft["schema"]==s.MOVE_SCHEMA:value=s.verify_move(draft,after)
                else:
                    u.require(args.receipt and args.runtime_actor_hashes,"NEW_RECEIPT_AND_RUNTIME_ACTOR_PROOF_REQUIRED")
                    value=n.verify_new(draft,after,read(args.receipt),read(args.runtime_actor_hashes))
        write_new(args.out,value)
        print(json.dumps({"status":value.get("status",value.get("schema")),"output":str(Path(args.out).resolve()),
              "sha256":file_ref(args.out)["sha256"],"platform_requests":0,"write_authorized":False,"match":value.get("match")}))
        return 2 if value.get("match") is False else 0
    except (ValueError,OSError,KeyError,TypeError,IndexError) as exc:
        print(json.dumps({"status":"HOLD_NO_RETRY","error":getattr(exc,"code",type(exc).__name__),"platform_requests":0,"write_authorized":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
