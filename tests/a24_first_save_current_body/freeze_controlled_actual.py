"""Freeze existing successful four-read bytes and all private capture artifacts."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"docs/evidence/A24/controlled-capture-current-body-actual"
RUN=Path("D:/1800/.local/stages/A24-first-save-r1-controlled-capture-body-20261021t143424z")
SUP=Path("D:/1800/.local/stages/a24-controlled-capture-current-body-supervisor")
DISPATCH=Path("D:/1800/docs/evidence/coordinator/a24-controlled-capture-current-body-dispatch")
def sha(raw):return hashlib.sha256(raw).hexdigest()
def ref(path):
    raw=path.read_bytes();return {"path":str(path),"bytes":len(raw),"sha256":sha(raw)}
def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as handle:handle.write((json.dumps(value,indent=2)+"\n").encode())
OUT.mkdir(parents=True,exist_ok=False)
sources=[(p,"raw/run/"+p.name) for p in sorted(RUN.glob("*.json"))]
sources += [(SUP/name,"raw/outer/"+name) for name in ("held_launcher_once.py","outer-claimed.json","outer-result.json","raw-capture.json")]
sources += [(DISPATCH/name,"inputs/"+name) for name in ("authority.json","decision.json","prewrite-acceptance-binding.json")]
sources += [(Path("D:/1800/docs/tasks/A24-controlled-capture-current-body-single-live-continuation.md"),"inputs/task.md")]
records=[]
for source,name in sources:
    raw=source.read_bytes();dest=OUT/name;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("xb") as handle:handle.write(raw)
    records.append({"path":dest.relative_to(ROOT).as_posix(),"source":str(source),"bytes":len(raw),"sha256":sha(raw)})
worker=json.loads((RUN/"worker-result.json").read_bytes())
held={stage:json.loads((RUN/(stage+"-held-release.json")).read_bytes()) for stage in ("launcher","product","worker","occupancy")}
assert worker["status"]=="PREWRITE_BLOCKED_NO_EFFECT" and worker["first_error"] is None
assert worker["release"]["released"] and worker["release"]["context_closed"] and worker["release"]["runtime_stopped"] and worker["release"]["guard_failure"] is None
reads=worker["prewrite"]["reads"];assert [r["slot"] for r in reads]==["book","directory","frames","export"] and all(r["http_status"]==200 for r in reads)
assert all(v["released"] and v["stage_success"] and v["creation_identity_match"] and v["job_active_final"]==0 and v["job_closed"] and v["handle_closed"] for v in held.values())
private=[]
for path in sorted((RUN/"private").rglob("*")):
    if not path.is_file():continue
    relative=path.relative_to(RUN/"private").as_posix()
    kind="STREAM" if relative.startswith("owner-") else "BODY_SNAPSHOT" if relative.endswith("-snapshot.bin") else "CAPTURE_OWNER_MARKER" if relative.endswith("capture-owner.json") else "SCRIPT_PROVENANCE" if relative.endswith(".source.json") else "SCRIPT_RAW"
    private.append({"kind":kind,**ref(path)})
private += [{"kind":"OUTER_LAUNCHER_STREAM_COPY",**ref(SUP/("launcher-"+kind+".bin"))} for kind in ("stdout","stderr")]
by_path={r["path"]:r for r in private}
for release in held.values():
    for kind in ("stdout","stderr"):
        r=release["controlled_raw_output_refs"][kind];assert all(by_path[r["path"]][k]==r[k] for k in ("bytes","sha256"))
for read in reads:
    if "controlled_raw_ref" in read:
        r=read["controlled_raw_ref"];assert all(by_path[r["path"]][k]==r[k] for k in ("bytes","sha256"))
capture=worker["private_capture_evidence"];assert capture["status"]=="BOUND_PRIVATE_CAPTURE" and len(capture["assets"])==1
for asset in capture["assets"]:
    for name in ("private_raw_ref","private_provenance_ref"):
        r=asset[name];assert all(by_path[r["path"]][k]==r[k] for k in ("bytes","sha256"))
marker=json.loads((RUN/"private/source-capture/capture-owner.json").read_bytes());assert marker==capture["owner_binding"]
put(OUT/"private-raw-manifest.json",{"schema":"A24ControlledBodyAllPrivateRawRefs/v1","members":private,"raw_bytes_verified":True,
    "private_run_file_count":len(private)-2,"outer_stream_copies":2,"all_current_private_run_files_included":True,
    "body_snapshot_refs":[r["controlled_raw_ref"] for r in reads if "controlled_raw_ref" in r],"private_raw_bytes_added_to_git":False})
put(OUT/"actual-result.json",{"schema":"A24ControlledBodyFixedActual/v1","at":datetime.now(timezone.utc).isoformat(),
    "run_id":"A24-first-save-r1-controlled-capture-body-20261021t143424z","authority_sha256":"411ec3757822ed374ed7f4c13e6a0becc571609d2d2b4117991c8acc20c4e244",
    "frozen_candidate_sha256":"f1b31fe4e27b9cb47e5476805e00fc56ce49d33666fd8353c67ce43bd4d9326a","frozen_final":"61fb7157eb335d2a0b9348e8496ea0b4b8d17ad0",
    "status":"PREWRITE_BLOCKED_NO_EFFECT","first_error":None,"bootstrap_steps":worker["bootstrap_steps"],"steps":worker["steps"],"navigation":worker["navigation"],
    "business_get_count":4,"reads":reads,"book_raw_body":"NOT_PERSISTED_BY_FROZEN_COLLECTOR_FINITE_HASH_ONLY",
    "body_schema_qualification":"CURRENT_SCHEMA_UNBOUND_NOT_PROMOTED","five_zone_completeness_and_current_target_eligibility":"OFFLINE_ANALYSIS_PENDING",
    "signature":"NOT_RUN","upload":"NOT_RUN","commit":"NOT_RUN","refresh":"NOT_RUN","reopen":"NOT_RUN","login_submission":0,"credential_config_access":0,"model_calls":0,
    "worker_release":worker["release"],"context_closed":True,"runtime_stopped":True,"callback_pending":0,
    "held_identities_verified":4,"jobs_closed_empty":4,"held_handles_closed":4,"held_stage_exit_codes":{k:v["after"]["exit_code"] for k,v in held.items()},
    "guard_evidence_summary":{key:{field:worker[key].get(field) for field in ("status","total_events","retained_events","complete","truncated","first_failure","exclusions","settlement")} for key in ("guard_evidence_before_release","guard_evidence_after_release")},
    "private_capture_evidence":capture,"all_private_refs_including_capture_marker_provenance_raw_body_and_streams":len(private),
    "library_preflight":{"before_product_import":True,"candidate_dependencies_hash_verified":158,"installed_source_hashes_verified":4,"python":"3.9.13","playwright":"1.58.0","dependency_replaced":False},
    "old_tests_model_content_review_or_original_capture_replay":0,"outer_helper_tool_exit_code":0,"actual_launcher_held_exit_code":0,"outer_helper_own_os_identity":"NOT_SELF_CERTIFIED",
    "new_dispatch_attempts_spent":1,"new_dispatch_remaining":0,"earlier_current_body_remaining":[0,0,0,0],"old_readonly_remaining":[0,0],
    "retry_or_extension_allowed":False,"claims_cleared":False,"manual_profile_reset_edit_or_lock_removal":False,"browser_profile_effects":"NOT_INSPECTED",
    "frozen_product_modified":False,"self_acceptance":False,"formal_actual_review":"PENDING","actual_save":"NOT_RUN",
    "next_author_work":"OFFLINE_ACTUAL_SCHEMA_PRESERVATION_IDENTITY_APPEND_SAVEPAGE_ADAPTATION_SAME_CHAT"})
put(OUT/"input-preservation.json",{"schema":"A24ControlledBodyActualRawSources/v1","members":records,"source_bytes_modified":False,
    "postfailure_probe_or_retry":False,"private_images_urls_scripts_body_or_tokens_added_to_git":False})
put(OUT/"release.json",{"schema":"A24ControlledBodyAuthorFixedRelease/v1","author_thread":"01a15cf8-0c63-70d3-b374-ce85e6f29fd7",
    "held_processes_jobs_handles_released":4,"runtime_stopped":True,"context_closed":True,"callback_pending":0,
    "actual_round_fixed_and_no_retry":True,"new_dispatch_remaining":0,"formal_acceptance":"PENDING","self_acceptance":False,
    "outer_helper_own_os_identity":"NOT_SELF_CERTIFIED","next_work":"OFFLINE_SAME_QUESTION_SCHEMA_INTEGRATION"})
members=[{"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in sorted(OUT.rglob("*")) if p.is_file()]
put(OUT/"actual-manifest.json",{"schema":"A24ControlledBodyActualSourceManifest/v1","self_excluded":True,"members":members,"final_authoritative_manifest":"delivery-final-manifest.json"})
print(json.dumps({"source_members":len(members),"private_refs":len(private),"body_snapshots":3,"business_gets":4,"new_round_remaining":0,"context_closed":True,"runtime_stopped":True}))
