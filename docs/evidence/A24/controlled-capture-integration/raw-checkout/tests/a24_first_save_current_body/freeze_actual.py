"""Freeze this sole actual dispatch's existing files only; never launch/retry."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/"docs/evidence/A24/first-save-current-body-actual"
RUN = Path("D:/1800/.local/stages/A24-first-save-r1-current-body-20261021t121919z")
SUP = Path("D:/1800/.local/stages/a24-first-save-r1-current-body-supervisor")
DISPATCH = Path("D:/1800/docs/evidence/coordinator/a24-first-save-r1-current-body-dispatch")
def sha(raw): return hashlib.sha256(raw).hexdigest()
def ref(path):
    raw=path.read_bytes()
    return {"path":str(path),"bytes":len(raw),"sha256":sha(raw)}
def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as h:h.write((json.dumps(value,indent=2)+"\n").encode())
OUT.mkdir(parents=True,exist_ok=False)
sources=[(p,"raw/run/"+p.name) for p in sorted(RUN.glob("*.json"))]
sources += [(SUP/name,"raw/outer/"+name) for name in ("held_launcher_once.py","outer-claimed.json","outer-result.json","raw-capture.json")]
sources += [(DISPATCH/name,"inputs/"+name) for name in ("authority.json","decision.json","prewrite-acceptance-binding.json")]
sources += [(Path("D:/1800/docs/tasks/A24-first-save-current-body-and-minimal-reopen-continuation.md"),"inputs/task.md")]
records=[]
for source,name in sources:
    raw=source.read_bytes();dest=OUT/name;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("xb") as h:h.write(raw)
    records.append({"path":dest.relative_to(ROOT).as_posix(),"source":str(source),"bytes":len(raw),"sha256":sha(raw)})
worker=json.loads((RUN/"worker-result.json").read_bytes())
held={stage:json.loads((RUN/(stage+"-held-release.json")).read_bytes()) for stage in ("launcher","product","worker","occupancy")}
assert worker["steps"]["prewrite"]=="NOT_RUN" and not list(RUN.rglob("*-snapshot.bin"))
assert all(r["released"] and r["creation_identity_match"] and r["job_closed"] and r["handle_closed"] and r["job_active_final"]==0 for r in held.values())
raw_refs=[ref(SUP/name) for name in ("launcher-stdout.bin","launcher-stderr.bin")]
put(OUT/"actual-result.json",{"schema":"A24CurrentBodyFixedActual/v1","at":datetime.now(timezone.utc).isoformat(),
    "run_id":"A24-first-save-r1-current-body-20261021t121919z","authority_sha256":"86f3ad15d1aeab1e7bd50b143f44cee280b9f54aa559faab9b88d942325b5d98",
    "frozen_candidate_sha256":"ade52cb3cff54f7ed094f921daa4be55d747ed28beb2fc16c80312b176584c67",
    "frozen_final":"2dcead75c317d3d46b56c1f2bc00583394daaea7","status":"FIXED_BOOTSTRAP_TIMEOUT_AND_PARTIAL_RELEASE_EVIDENCE_ONLY",
    "first_error":worker["first_error"],"failure_substep":"UNKNOWN_NOT_RETAINED","root_cause":"UNKNOWN",
    "main_document_http":"UNKNOWN_NOT_RETAINED","actual_navigation_count":"UNKNOWN_NOT_RETAINED",
    "book":"NOT_RUN","directory":"NOT_RUN","frames":"NOT_RUN","natural_export":"NOT_RUN",
    "body_snapshots":[],"schema_qualification":"UNKNOWN_NO_NEW_BODY_FACTS","signature":"NOT_RUN","upload":"NOT_RUN",
    "commit":"NOT_RUN","refresh":"NOT_RUN","reopen":"NOT_RUN","login_submission":0,"model_calls":0,
    "worker_release":worker["release"],"full_context_runtime_release":"UNPROVEN_CONTEXT_CLOSE_FALSE",
    "held_identities_verified":4,"jobs_closed_empty":4,"held_handles_closed":4,"held_stage_exit_codes":{k:v["after"]["exit_code"] for k,v in held.items()},
    "launcher_stdout_stderr_private_raw_refs":raw_refs,
    "worker_stderr":{"bytes":held["worker"]["stderr_bytes"],"sha256":held["worker"]["stderr_sha256"],"raw_bytes":"NOT_RETAINED_BY_FROZEN_SUPERVISOR"},
    "other_descendant_stdout_stderr":"HASH_AND_LENGTH_ONLY_IN_FROZEN_HELD_REPORTS",
    "outer_helper_tool_exit_code":1,"actual_launcher_held_exit_code":2,"outer_helper_own_os_identity":"NOT_SELF_CERTIFIED",
    "new_dispatch_attempts_spent":1,"new_dispatch_remaining":0,"old_readonly_remaining":[0,0],
    "retry_or_extension_allowed":False,"claims_cleared":False,"profile_or_lock_changed":False,
    "self_acceptance":False,"formal_actual_review":"PENDING","subsequent_work":"OFFLINE_MINIMUM_R1_R_GATE_ONLY_WITH_MISSING_SOURCE_FACTS_EXPLICIT"})
put(OUT/"input-preservation.json",{"schema":"A24CurrentBodyActualRawSources/v1","members":records,"source_bytes_modified":False,
    "source_profile_inspected_after_failure":False,"private_originals_or_body_added_to_git":False})
put(OUT/"release.json",{"schema":"A24CurrentBodyAuthorFixedRelease/v1","author_thread":"01a15cf8-0c63-70d3-b374-ce85e6f29fd7",
    "held_processes_and_jobs_released":True,"runtime_stopped":True,"context_closed":"UNPROVEN_FALSE_FLAG_PRESERVED",
    "all_resources_release_claimed":False,"actual_round_fixed_and_no_retry":True,"new_dispatch_remaining":0,
    "next_work_offline_only":True,"formal_acceptance":"PENDING"})
members=[]
for path in sorted(OUT.rglob("*")):
    if path.is_file():members.append({"path":path.relative_to(ROOT).as_posix(),"bytes":path.stat().st_size,"sha256":sha(path.read_bytes())})
put(OUT/"actual-manifest.json",{"schema":"A24CurrentBodyActualRawManifest/v1","self_excluded":True,"members":members})
print(json.dumps({"actual_members":len(members),"manifest_sha256":sha((OUT/"actual-manifest.json").read_bytes()),"business_gets":"NOT_RUN","new_attempts_remaining":0,"full_context_release":"UNPROVEN"}))
