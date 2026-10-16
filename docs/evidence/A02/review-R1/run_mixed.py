"""Independent regression of original legal multibook input, with repaired expectations."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

OUT=Path(__file__).resolve().parent
SOURCE=OUT/'source-38aca9dc'
OLD=OUT.parent/'review/formal/probe_crossbook.py'
text=OLD.read_text(encoding='utf-8').split('\ndef run(output):',1)[0]
text=text.replace('Path("D:/1800/.local/stages/A02-review/frozen-5c928572")','Path('+repr(SOURCE.as_posix())+')')
text=text.replace('5c9285720c8628c5198bedeadfc9f6bc7826a914','38aca9dcc8d027409b95193e9cc142c2336b76d3')
text=text.replace('foreign = load_bundle(FROZEN / "tests/fixtures/contracts/unknown/input.json").model_dump(mode="json")',
    'foreign = rebook(load_bundle(FROZEN / "tests/fixtures/contracts/unknown/input.json").model_dump(mode="json"), FOREIGN_BOOK) if INCLUDE_FOREIGN else {"artifacts": [], "policies": [], "evidence": []}')
suffix=r'''

FOREIGN_BOOK = "synthetic-book"
INCLUDE_FOREIGN = True

def rebook(data, book):
    data=copy.deepcopy(data); refs={}
    def replace_refs(value):
        if isinstance(value,list): return [replace_refs(v) for v in value]
        if isinstance(value,dict):
            if set(value)=={"artifact_id","revision","kind","content_hash"}:
                return refs.get((value["artifact_id"],value["revision"]),value)
            return {k:replace_refs(v) for k,v in value.items()}
        return value
    for i,item in enumerate(data["artifacts"]):
        raw=replace_refs(item);raw["book_id"]=book;sealed=seal_artifact(raw)
        refs[(item["artifact_id"],item["revision"])]=artifact_ref(sealed);data["artifacts"][i]=sealed
    return data

def state_files(root, label, session, books):
    write_json(root/(label+"-states.json"),{b:session.read_target(b) for b in books})
    write_json(root/(label+"-history.json"),{b:session.receipt_history(b) for b in books})
    write_json(root/(label+"-log.json"),session.action_log)

def mixed(root, current, foreign):
    global OTHER_BOOK,FOREIGN_BOOK,INCLUDE_FOREIGN
    OTHER_BOOK,FOREIGN_BOOK,INCLUDE_FOREIGN=current,foreign,True
    root.mkdir(parents=True,exist_ok=False)
    shutil.copytree(FROZEN/"tests/fixtures/contracts/unknown/assets",root/"assets")
    blocked,bp,_,bc=prepare("exceptions","independent-blocked",root)
    ready,rp,snap,rc=prepare("normal","independent-ready",root)
    assert_plan_ready(ready,artifact_ref(rp),artifact_ref(snap))
    originals={(a.artifact_id,a.revision):a.model_dump(mode="json") for a in blocked.artifacts if a.book_id==foreign}
    session=MockSession();session.register_target(ready,artifact_ref(snap),asset_root=root)
    before=session.read_target(current);state_files(root,"before",session,[current])
    diagnosis=session.execute(blocked,artifact_ref(bp),bc,asset_root=root,receipt_id="independent-diagnosis",created_at=TIME)
    write_bundle(diagnosis,root/"diagnostic-result.json")
    dr=next(a for a in diagnosis.artifacts if a.artifact_id=="independent-diagnosis")
    after_pause=session.is_paused(current)
    assert dr.payload.execution_mode=="NOT_EXECUTED" and not dr.payload.results
    assert after_pause is False and before==session.read_target(current) and session.action_log==()
    assert all(a.model_dump(mode="json")==originals[(a.artifact_id,a.revision)] for a in diagnosis.artifacts if a.book_id==foreign)
    state_files(root,"after-diagnostic",session,[current])
    executed=session.execute(ready,artifact_ref(rp),rc,asset_root=root,receipt_id="independent-ready-receipt",created_at=TIME)
    write_bundle(executed,root/"executed.json")
    receipt=next(a for a in executed.artifacts if a.artifact_id=="independent-ready-receipt")
    state=session.read_target(current);target=state["target"]
    assert [r.outcome for r in receipt.payload.results]==["APPLIED"]*3
    assert len(target["questions"])==3 and len(target["frames"])==9
    assert [q["platform_order"] for q in target["questions"]]==[1,2,1]
    assert len([e for e in session.action_log if e["event"]=="intent"])==3
    assert len(session.receipt_history(current))==2 and not session.is_paused(current)
    for action,result in zip(rp.payload.actions,receipt.payload.results):
        pid=state["internal_bindings"][action.target.question_id]
        frames=[f for f in target["frames"] if f["platform_question_id"]==pid]
        assert len(frames) in (4,3,2)
        assert [state["frame_projections"][f["platform_frame_id"]] for f in frames]==json.loads(action.expected_after["frames"])
        assert result.platform_ids==[pid]+[f["platform_frame_id"] for f in frames]
        assert result.effect_match=="MATCH" and not result.replay_allowed
    state_files(root,"after-ready",session,[current])
    for path in root.glob("*.json"):
        if path.name.endswith(("-input.json","-checked.json","-planned.json")) or path.name in ("diagnostic-result.json","executed.json"):
            load_bundle(path)
    result={"current_book":current,"foreign_book":foreign,"pause_after_diagnostic":after_pause,
        "diagnostic":"NOT_EXECUTED","ready_outcomes":[r.outcome for r in receipt.payload.results],"actual_questions":3,"actual_frames":9,
        "foreign_artifacts_retained":len(originals),"history_bundle_count":2,"intents":3,"current_paused_after_ready":False}
    write_json(root/"observations.json",result);return result

def interaction(root, mode):
    global OTHER_BOOK,FOREIGN_BOOK,INCLUDE_FOREIGN
    root.mkdir(parents=True,exist_ok=False)
    shutil.copytree(FROZEN/"tests/fixtures/contracts/unknown/assets",root/"assets")
    INCLUDE_FOREIGN=False;OTHER_BOOK="book-actual-unresolved"
    a,ap,asp,ac=prepare("normal","actual-a",root)
    session=MockSession();session.register_target(a,artifact_ref(asp),asset_root=root)
    ao=session.execute(a,artifact_ref(ap),ac,asset_root=root,receipt_id="actual-a-unknown",created_at=TIME,
        faults={ap.payload.actions[0].action_id:"lost_response"})
    write_bundle(ao,root/"a-unknown-result.json")
    astate=session.read_target(OTHER_BOOK);ahistory=session.receipt_history(OTHER_BOOK)
    alog=[e for e in session.action_log if e.get("book_id")==OTHER_BOOK]
    assert session.is_paused(OTHER_BOOK) and len(astate["target"]["frames"])==4
    OTHER_BOOK="book-other-active"
    b,bp,bsp,bc=prepare("exceptions" if mode=="NOT_EXECUTED" else "normal","actual-b",root)
    session.register_target(b,artifact_ref(bsp),asset_root=root)
    fault={bp.payload.actions[0].action_id:"not_applied"} if mode=="NOT_APPLIED" else {}
    bo=session.execute(b,artifact_ref(bp),bc,asset_root=root,receipt_id="actual-b-receipt",created_at=TIME,faults=fault)
    write_bundle(bo,root/"b-result.json")
    receipt=next(a for a in bo.artifacts if a.artifact_id=="actual-b-receipt")
    if mode=="NOT_EXECUTED":assert not receipt.payload.results and receipt.payload.execution_mode==mode
    else:assert [r.outcome for r in receipt.payload.results]==[mode]*3
    assert not session.is_paused(OTHER_BOOK)
    assert session.is_paused("book-actual-unresolved")
    assert astate==session.read_target("book-actual-unresolved") and ahistory==session.receipt_history("book-actual-unresolved")
    assert alog==[e for e in session.action_log if e.get("book_id")=="book-actual-unresolved"]
    state_files(root,"after-b",session,["book-actual-unresolved",OTHER_BOOK])
    oldlog=session.action_log;oldstate=session.read_target(OTHER_BOOK)
    try:session.execute(b,artifact_ref(bp),bc,asset_root=root,receipt_id="repeat-b",created_at=TIME)
    except ContractError as e:assert any(i["code"]=="REPLAY_FORBIDDEN" for i in e.issues);write_json(root/"replay-error.json",e.issues)
    else:raise AssertionError("old plan replayed")
    assert oldlog==session.action_log and oldstate==session.read_target(OTHER_BOOK)
    result={"other_book_outcome":mode,"original_book_still_paused":True,"original_state_history_log_unchanged":True,
        "other_book_paused":False,"other_old_plan_rejected":True}
    write_json(root/"observations.json",result);return result

def main():
    root=Path(sys.argv[sys.argv.index("--output")+1]).resolve() if "--output" in sys.argv else Path(__file__).resolve().parent/"independent/mixed"
    root.mkdir(parents=True,exist_ok=False)
    results=[mixed(root/"forward","book-current-blue","synthetic-book"),mixed(root/"swapped","synthetic-book","book-current-blue")]
    for mode in ("APPLIED","NOT_APPLIED","NOT_EXECUTED"):results.append(interaction(root/("interaction-"+mode.lower()),mode))
    write_json(root/"results.json",{"target_commit":COMMIT,"provenance":"SYNTHETIC","execution_mode":"SIMULATED","cases":results,"platform_actions":0,"model_calls":0})
    print(json.dumps({"cases":len(results),"status":"PASS","forward_and_swapped_actual_frames":9}))

if __name__=="__main__":main()
'''
path=OUT/'acceptance_mixed.py'
path.write_text(text+suffix,encoding='utf-8')
argv=[sys.executable,'-B',str(path)]+sys.argv[1:]
result=subprocess.run(argv,cwd=OUT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
label='mixed-final' if '--output' in sys.argv else 'mixed'
(OUT/(label+'.stdout.txt')).write_bytes(result.stdout);(OUT/(label+'.stderr.txt')).write_bytes(result.stderr)
(OUT/(label+'-command.json')).write_text(json.dumps({'argv':argv,'cwd':str(OUT),'exit_code':result.returncode,
    'derived_from':str(OLD),'original_script_sha256':hashlib.sha256(OLD.read_bytes()).hexdigest(),
    'acceptance_script_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'note':'Original input constructor retained; new-book rebind and repaired behavior assertions added. Original reviewer evidence untouched.'},indent=2)+'\n',encoding='utf-8')
print(result.stdout.decode(errors='replace'))
if result.returncode:print(result.stderr.decode(errors='replace'))
sys.exit(result.returncode)
