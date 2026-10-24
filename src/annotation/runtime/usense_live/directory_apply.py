"""Bind an observed native preview to one exact apply plan. No network here."""
import copy
from pathlib import Path

from . import structure as s, update as u
from .batch import file_ref, ref_bytes
from .core import sha, utc
from .revision import released

SCHEMA = "b-usense-preview-bound-directory-apply/0.1"


def read_ref(ref): return u.loads(ref_bytes(ref))


def verify_preview(move, refs):
    u.require(set(refs) == {"request","response","execution","network","readback"},"APPLY_COMPLETE_PREVIEW_EVIDENCE_REQUIRED")
    request,response,execution,events,readback = (read_ref(refs[k]) for k in ("request","response","execution","network","readback"))
    u.require(u.json_same(request,move["preview_request"]),"APPLY_PAYLOAD_DIFFERS_FROM_REAL_PREVIEW")
    expected_moves=[{"node_id":t["node_id"],"old_order":t["question_order"],"new_order":t["question_order"],
                     "old_directory_id":t["lesson_directory_id"],"new_directory_id":move["destination_directory_id"]} for t in move["targets"]]
    expected={"code":0,"message":"success","data":{"has_changes":True,"directory_additions":[],"directory_renames":[],
      "directory_deletions":[],"directory_moves":[],"question_deletions":[],"question_moves":expected_moves,
      "question_order_changes":[],"risk_summary":[],"summary":{"added_dirs":0,"renamed_dirs":0,"deleted_dirs":0,
      "moved_dirs":0,"deleted_questions":0,"moved_questions":len(expected_moves),"changed_questions":0}}}
    # This is the actually observed preview shape, not an invented apply receipt.
    u.require(u.json_same(response,expected),"APPLY_PREVIEW_NOT_EXACT_TARGET_MOVES")
    u.require(execution.get("schema")=="UsenseDirectoryPreviewCapture/v1" and
      execution.get("status")=="PREVIEW_RESPONSE_CAPTURED_REQUIRES_REVIEW" and type(execution.get("http_status")) is int and
      execution["http_status"]==200 and type(execution.get("post_attempts")) is int and execution["post_attempts"]==1 and
      type(execution.get("apply_attempts")) is int and execution["apply_attempts"]==0 and
      type(execution.get("commit_attempts")) is int and execution["commit_attempts"]==0 and released(execution.get("release",{})),
      "APPLY_PREVIEW_EXECUTION_NOT_PROVEN")
    counts=execution.get("post_counts")
    u.require(type(counts) is dict and set(counts)=={"context","native"} and
      all(type(v) is int and v==1 for v in counts.values()),"APPLY_PREVIEW_DUAL_GUARD_COUNTS")
    u.require(execution["request_sha256"]==refs["request"]["sha256"] and execution["response_sha256"]==refs["response"]["sha256"],
      "APPLY_PREVIEW_REQUEST_RESPONSE_HASH_MISMATCH")
    post_hash=sha(("https://www.usense.com"+s.PREVIEW).encode())
    u.require(type(events) is list and all(e.get("allowed") is True for e in events) and
      all(e.get("method") in ("GET","POST") for e in events) and sum(e.get("method")=="POST" for e in events)==2 and
      all(sum(e.get("method")=="POST" and e.get("layer")==layer and e.get("url_sha256")==post_hash for e in events)==1
          for layer in ("context","native")),"APPLY_PREVIEW_NETWORK_SCOPE_UNPROVEN")
    u.require(readback.get("schema")=="UsenseDirectoryPreviewReadback/v1" and
      readback.get("status")=="PREVIEW_MATCHES_INTENDED_FIVE_MOVES_AND_GLOBAL_STATE_UNCHANGED" and
      type(readback.get("checks")) is dict and set(readback["checks"])=={"directory","frames","source"} and
      all(value is True for value in readback["checks"].values()) and
      all(type(readback.get(k)) is int and readback[k]==v for k,v in (("actual_preview_posts",1),("apply_posts",0),("commit_posts",0))) and
      readback.get("response_sha256")==refs["response"]["sha256"],"APPLY_PREVIEW_READBACK_NOT_PROVEN")
    preview_dir=Path(refs["execution"]["path"]).resolve().parent
    reader=Path(readback["readback_directory"]).resolve()
    summary= u.loads((reader/"capture-summary.json").read_bytes())
    u.require(summary.get("status")=="NATIVE_GETS_CAPTURED" and type(summary.get("save_attempts")) is int and summary["save_attempts"]==0 and
      released(summary.get("release",{})) and utc(summary["finished_at"])>utc(execution["finished_at"]),"APPLY_PREVIEW_INDEPENDENT_CAPTURE_UNPROVEN")
    evidence={str(Path(ref["path"]).resolve()):ref["sha256"] for ref in refs.values()}
    evidence[str(reader/"capture-summary.json")]=sha((reader/"capture-summary.json").read_bytes())
    for name in ("directory","frames","source"):
        before_path=preview_dir/("before-"+name+".json");after_path=reader/(name+".json")
        before_raw,after_raw=before_path.read_bytes(),after_path.read_bytes();cap=summary["captures"][name]
        u.require(before_raw==after_raw and u.json_same(u.loads(before_raw),move["before_full"][name]) and
          cap.get("sha256")==sha(after_raw) and cap.get("bytes")==len(after_raw) and type(cap.get("status")) is int and cap["status"]==200 and
          utc(cap["observed_at"])>utc(execution["finished_at"]),"APPLY_PREVIEW_GLOBAL_STATE_CHANGED")
        u.require(type(cap.get("request_counts")) is dict and set(cap["request_counts"])=={"context","native"} and
          all(type(v) is int and v==1 for v in cap["request_counts"].values()),"APPLY_PREVIEW_READER_COUNTS")
        evidence[str(before_path)]=sha(before_raw);evidence[str(after_path)]=sha(after_raw)
    return evidence


def make_apply_plan(move, preview_refs):
    u.require(move.get("schema")==s.MOVE_SCHEMA and s.fingerprint(move)==move["plan_sha256"],"APPLY_MOVE_DRAFT_REQUIRED")
    rebuilt=s.make_move_draft(move["before_full"],move["targets"],move["destination_directory_id"],move["scope_review"],move["protocol"],move["baseline_observed_at"])
    u.require(u.json_same(move,rebuilt),"APPLY_MOVE_DRAFT_CHANGED")
    evidence=verify_preview(move,preview_refs)
    plan={"schema":SCHEMA,"operation":"PREVIEW_BOUND_DIRECTORY_APPLY","book_id":u.BOOK,"move_draft":copy.deepcopy(move),
      "before_full":copy.deepcopy(move["before_full"]),"before_sha256":move["before_sha256"],
      "preview_refs":copy.deepcopy(preview_refs),"evidence_file_sha256":evidence,
      "request":{"method":"POST","path":s.APPLY,"body":copy.deepcopy(move["preview_request"]["body"])},
      "ledger_key":move["ledger_key"],"targets":copy.deepcopy(move["targets"]),
      "fresh_complete_prewrite_required":True,"seed_observed_at":move["baseline_observed_at"],
      "automatic_retry_allowed":False,"independent_readback_required":True,"platform_acceptance":False,
      "receipt_policy":"RAW_BYTES_FIRST_UNKNOWN_APPLY_SCHEMA_REQUIRES_INDEPENDENT_FULL_READBACK"}
    plan["plan_sha256"]=s.fingerprint(plan)
    return plan


def validate(plan):
    u.require(plan.get("schema")==SCHEMA and s.fingerprint(plan)==plan["plan_sha256"],"APPLY_PLAN_CHANGED")
    rebuilt=make_apply_plan(plan["move_draft"],plan["preview_refs"])
    u.require(u.json_same(plan,rebuilt),"APPLY_PLAN_EVIDENCE_CHANGED")
    return plan
