"""Fixed F01 review: static, two non-writing gates, read-only archive, sealing."""
import argparse
import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
PRODUCT = "3d22524ff626fc7b0376b7312be6fe75f2e73aab"
DELIVERY = "6f8f1d6fa4c8db9678738673a54fa862df9a666e"
WORKFLOW = "ca1fb902c2228579cd2d0c84d81fc72cd0643796"
DISPATCH = "53d1249887eabf9ee77fde6b0edf0f4d279016bd"
OLD_REVIEW = "efe440d07d3600ee9755f1709778a2a742bb2f52"
OLD_RUN = "docs/evidence/A07/review/candidate-1/normal/run/"
INPUT = ROOT / ".local/a07/f01-review-inputs"
EXPECTED = ["Q", "W", "W", "W", "W", "A"]
AUTH = {"A07-Q1-offline-business-approval.json":"cf6f675cfd98d438d7d465fc553e0ebbf1bfff71bd62f8453854f8527015cb6c",
        "A07-F01-role-correction-approval.json":"7c6c2e9ceaa2abfb5d6379498d859c3411d13f60e89fed2914e999788fa32b8e"}
REPORT = "docs/tasks/A07-F01-review-report.md"
MANIFEST = "docs/evidence/A07/F01/review/raw-git-manifest.json"

def enc(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")

def sha(raw): return hashlib.sha256(raw).hexdigest()
def full_hash(obj):
    obj = dict(obj); obj.pop("content_hash",None)
    return sha(enc(obj))
def load(path): return json.loads(Path(path).read_bytes())
def git(*args):
    return subprocess.check_output(["git","-c","core.longpaths=true",*args],cwd=ROOT,env=dict(os.environ,GIT_NO_LAZY_FETCH="1"))
def blob(commit,path): return git("show",commit+":"+path)
def tree(commit):
    result = {}
    for row in git("ls-tree","-rz",commit).split(b"\0"):
        if row:
            head,path = row.split(b"\t",1)
            result[path.decode("utf-8")] = head.decode().split()
    return result
def batch(oids):
    process = subprocess.Popen(["git","-c","core.longpaths=true","cat-file","--batch"],cwd=ROOT,
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,env=dict(os.environ,GIT_NO_LAZY_FETCH="1"))
    raw,_ = process.communicate(("\n".join(oids)+"\n").encode())
    assert process.returncode == 0
    result,offset = {},0
    for oid in oids:
        end = raw.index(b"\n",offset); header = raw[offset:end].split(); size = int(header[2]); start = end+1
        assert header[0].decode() == oid and header[1] == b"blob"
        result[oid] = raw[start:start+size]; assert raw[start+size:start+size+1] == b"\n"
        offset = start+size+1
    assert offset == len(raw)
    return result
def save(name,obj):
    path = OUT/name
    assert not path.exists(),str(path)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def static():
    base,product,final,old = [tree(c) for c in (WORKFLOW,PRODUCT,DELIVERY,OLD_REVIEW)]
    modified = sorted(p for p,v in base.items() if product.get(p) != v)
    assert modified == ["src/annotation/quality/q1_offline.py","src/annotation/source/b_q1/reader.py"]
    assert all(final.get(p) == v for p,v in product.items())
    added = set(product)-set(base)
    allowed = lambda p: p.startswith("docs/evidence/A07/F01/execution/") or p in ("tests/test_a07_role_delta.py","examples/a07/role_delta_check.py","docs/tasks/A07-F01-execution-report.md")
    assert len(added) == 9 and all(map(allowed,added))
    assert all(final.get(p) == v for p,v in base.items() if p not in modified)
    assert all(final.get(p) == v for p,v in old.items() if p.startswith("docs/evidence/"))
    assert final["docs/tasks/A07-Q1-review-report.md"] == old["docs/tasks/A07-Q1-review-report.md"]
    changes = {p for p,v in final.items() if base.get(p) != v}
    assert all(p in modified or allowed(p) for p in changes)
    mp = "docs/evidence/A07/F01/execution/delivery-raw-manifest.json"
    raw = blob(DELIVERY,mp); assert sha(raw) == "afb1c565ba4619c3cdc075a97ee0fbe2cca9d2613a3ee376ddcd43aef538a9ee"
    manifest = json.loads(raw); members = manifest["members"]
    assert len(members) == 58 and sum(m["bytes"] for m in members) == 10200306
    assert {m["path"] for m in members} == changes-{mp}
    values = batch(list(dict.fromkeys(m["blob_oid"] for m in members)))
    for m in members:
        data = values[m["blob_oid"]]
        assert final[m["path"]][2] == m["blob_oid"] and len(data) == m["bytes"] and sha(data) == m["sha256"]
    assert sha(blob(DELIVERY,"docs/tasks/A07-F01-execution-report.md")) == "2652db7d1feb595ba8b2a51e6e7e187e860a8f2d0c2258a063bce37924567e0f"
    authorities = {}
    for name,expected in AUTH.items():
        raw = blob(DISPATCH,"docs/approvals/"+name)
        assert sha(raw) == expected
        (OUT/name).write_bytes(raw)
        authorities[name] = expected
    new_authority = load(OUT/"A07-F01-role-correction-approval.json")
    assert new_authority["expected_roles"] == EXPECTED and new_authority["additional_offline_delta_attempts"]["independent_review"] == 1
    assert new_authority["resets_previous_allowances"] is False
    rule_raw = blob(PRODUCT,"项目交接说明.md"); lines = rule_raw.decode("utf-8").splitlines()
    assert "| W | 选项 |" in lines[71] and "普通选择题各选项独立框" in lines[71]
    assert "每个普通选择题选项单独一个框" in lines[97] and "四个选项合成一个 W 框" in lines[97]
    assert "| Q | 题干 |" in lines[70] and "| A | 答案 |" in lines[72]
    policies = {}
    for path in ("config/policies/usense-v1-proposal.json","config/policies/synthetic-choice-separate.json"):
        raw = blob(PRODUCT,path); policy = json.loads(raw)
        assert policy["role_mapping"]["option"] == "W" and policy["role_mapping"]["stem"] == "Q" and policy["role_mapping"]["answer"] == "A"
        policies[path] = {"sha256":sha(raw),"role_mapping":policy["role_mapping"]}
    save("original-rule-basis.json",{"primary":"Original project handoff rules, not old plan/readback expectations",
        "path":"项目交接说明.md","sha256":sha(rule_raw),"lines":{str(n):lines[n-1] for n in (71,72,73,74,98,99)},
        "supporting_policies":policies,"expected_roles":EXPECTED,"shared_material_not_exercised_or_repaired":True})
    save("reviewed-author-raw-members.json",{"delivery":DELIVERY,"manifest_sha256":sha(blob(DELIVERY,mp)),"members":members})
    save("static-review.json",{"result":"PASS","workflow":WORKFLOW,"dispatch":DISPATCH,"product":PRODUCT,"delivery":DELIVERY,
        "workflow_paths":len(base),"old_other_paths_preserved":len(base)-2,"modified_paths":modified,"product_added_paths":sorted(added),
        "candidate_paths_preserved":len(product),"old_evidence_paths_preserved":sum(p.startswith("docs/evidence/") for p in base),
        "old_independent_evidence_and_report_preserved":True,"author_members":58,"author_member_bytes":10200306,
        "authorizations":authorities,"normal_attempts":0,"targets_created":0,"business_dispatches":0})
    print("fixed source scope, original rules, two authorizations and raw manifest PASS")

def rebind_policy(bundle):
    from annotation.contracts import artifact_ref,policy_ref,seal_policy,seal_artifact
    data = bundle.model_dump(mode="json")
    policy = copy.deepcopy(data["policies"][0]); old_ref = policy_ref(policy)
    policy["role_mapping"]["option"] = "Q"; policy = seal_policy(policy)
    refs = [(old_ref,policy_ref(policy))]
    def replace(value):
        if isinstance(value,dict):
            for old,new in refs:
                if value == old:return copy.deepcopy(new)
            return {k:replace(v) for k,v in value.items()}
        if isinstance(value,list):return [replace(v) for v in value]
        return value
    artifacts = []
    for old in data["artifacts"]:
        updated = seal_artifact(replace(old)); refs.append((artifact_ref(old),artifact_ref(updated))); artifacts.append(updated)
    data.update(policies=[policy],artifacts=artifacts)
    return data

def gates():
    from annotation.contracts import validate_bundle
    from annotation.quality.q1_offline import pre_apply
    from annotation.source.b_q1.reader import build_source,load_inputs
    inputs = load_inputs(INPUT/"base.zip",INPUT/"candidate.zip",INPUT/"history.json",INPUT/"approval.json",ROOT/"config/policies/a07-q1-offline-v1.json")
    calls = []
    for role in ("W","Q"):
        assets = ROOT/(".local/a07/f01-gate-"+role); assets.mkdir(parents=True,exist_ok=False)
        run_id,now = "a07-f01-review-gate-"+role,"2026-10-18T13:28:00+00:00"
        bundle,_ = build_source(inputs,assets,run_id,now)
        valid = validate_bundle(bundle if role == "W" else rebind_policy(bundle),asset_root=assets)
        graph = next(a for a in valid.artifacts if a.kind == "QuestionGraph")
        actual = [valid.policies[0].role_mapping[f.role] for f in sorted(graph.payload.fragments,key=lambda f:f.reading_order)]
        assert graph.payload.questions[0].question_type == "ordinary_choice"
        _checked,report = pre_apply(valid,inputs,assets,run_id,now)
        outcomes = {c["check_id"]:c["outcome"] for c in report["payload"]["checks"]}
        assert all(outcomes[k] == "PASS" for k in outcomes if k != "policy")
        if role == "W":
            assert actual == EXPECTED and outcomes["policy"] == report["payload"]["decision"] == "PASS"
        else:
            assert actual == ["Q","Q","Q","Q","Q","A"] and outcomes["policy"] == "FAIL" and report["payload"]["decision"] == "HOLD"
            assert "ordinary_choice_role_mapping=False" in next(c["reason"] for c in report["payload"]["checks"] if c["check_id"] == "policy")
            assert len(report["payload"]["issues"]) == 1 and report["payload"]["issues"][0]["blocks"] == ["PLAN","APPLY"]
        calls.append({"option_role":role,"roles":actual,"expected_from_original_rules":EXPECTED,"C01_valid_before_check":True,
            "layer":"PRE_APPLY.policy.ordinary_choice_role_mapping","checks":outcomes,"decision":report["payload"]["decision"],
            "target_changes":0,"targets_created":0,"business_dispatches":0})
    save("role-gate-calls.json",{"pid":os.getpid(),"calls":calls,"targets_created":0,"business_dispatches":0,"normal_attempts":0})
    print("two independent role gates PASS; old Q reaches policy FAIL/HOLD after valid resealing; zero targets")

def archive():
    from annotation.contracts import artifact_ref,assert_plan_ready,validate_bundle
    run = OUT/"normal/run"; exchange = load(run/"exchange.json"); valid = validate_bundle(exchange,asset_root=run)
    old_exchange = json.loads(blob(OLD_REVIEW,OLD_RUN+"exchange.json"))
    new = {a["kind"]:a for a in exchange["artifacts"] if a["kind"] != "CheckReport"}
    old = {a["kind"]:a for a in old_exchange["artifacts"] if a["kind"] != "CheckReport"}
    plan,receipt,snapshot = [new[k] for k in ("ApplyPlan","ExecutionReceipt","PlatformSnapshot")]
    assert_plan_ready(valid,artifact_ref(plan),artifact_ref(snapshot))
    for obj in exchange["artifacts"]+exchange["policies"]:assert full_hash(obj) == obj["content_hash"]
    original = json.loads(blob(OLD_REVIEW,OLD_RUN+"assets/readback.json"))
    assert sha(blob(OLD_REVIEW,OLD_RUN+"assets/readback.json")) == "df3c33600ca7c08b873b756466a1a269643263559439d50047fa536edcdac019"
    before,after = load(run/"assets/before.json"),load(run/"assets/readback.json")
    assert [before["read_sequence"],after["read_sequence"]] == [1,2] and before["instance_id"] == after["instance_id"] != original["instance_id"]
    assert full_hash(before["view"]) == before["target_state_hash"] and full_hash(after["view"]) == after["target_state_hash"]
    assert not before["view"]["target"]["frames"] and not before["view"]["target"]["questions"] and before["view"]["epoch"] == 0
    view,prior = after["view"],original["view"]
    assert view["epoch"] == 1 and len(view["target"]["questions"]) == 1 and len(view["target"]["frames"]) == 6
    actual,previous = view["target"]["frames"],prior["target"]["frames"]
    projected = json.loads(plan["payload"]["actions"][0]["expected_after"]["frames"])
    assert [f["platform_role"] for f in actual] == [f["platform_role"] for f in projected] == EXPECTED
    with __import__('zipfile').ZipFile(INPUT/"candidate.zip") as z:
        candidate_raw = z.read("candidate.json"); candidate = json.loads(candidate_raw)
    cp = candidate["payload"]
    assert sha(candidate_raw) == "0ce9ffb0f468ba0cc07f37978121e7f9b991b07b94335d117da3e8ea241aea5c"
    selected = [next(r for r in cp["regions"] if r["region_id"] == rid) for rid in cp["proposed_semantic_region_ids"]]
    changed = []
    for i,(frame,oldframe,projection,region) in enumerate(zip(actual,previous,projected,selected)):
        assert {k:v for k,v in frame.items() if k != "platform_role"} == {k:v for k,v in oldframe.items() if k != "platform_role"}
        oldprojection = prior["frame_projections"][oldframe["platform_frame_id"]]
        state_projection = view["frame_projections"][frame["platform_frame_id"]]
        assert state_projection == projection
        assert {k:v for k,v in projection.items() if k != "platform_role"} == {k:v for k,v in oldprojection.items() if k != "platform_role"}
        assert frame["box"]["bbox"] == region["bbox"] and frame["box"]["image"]["asset_id"] == region["asset_id"] and frame["box"]["image"]["sha256"] == region["source_sha256"]
        assert [frame["box"]["image"]["width"],frame["box"]["image"]["height"]] == region["source_size"]
        assert projection["region_id"] == region["region_id"] and projection["fragment_id"] == "a07-fragment-"+str(i)
        if frame["platform_role"] != oldframe["platform_role"]:changed.append(i)
    assert changed == [1,2,3,4]
    assert {k:v for k,v in view.items() if k not in ("target","frame_projections")} == {k:v for k,v in prior.items() if k not in ("target","frame_projections")}
    assert {k:v for k,v in view["target"].items() if k != "frames"} == {k:v for k,v in prior["target"].items() if k != "frames"}
    assert new["SourceBundle"]["payload"] == old["SourceBundle"]["payload"]
    for kind,excluded in (("EvidenceBundle",{"source"}),("QuestionGraph",{"source","evidence"})):
        assert {k:v for k,v in new[kind]["payload"].items() if k not in excluded} == {k:v for k,v in old[kind]["payload"].items() if k not in excluded}
    assert exchange["policies"][0]["role_mapping"]["option"] == "W" and exchange["policies"][0]["role_mapping"]["shared_material"] == old_exchange["policies"][0]["role_mapping"]["shared_material"]
    expected_texts = [cp["candidate_content"]["stem_body_normalized_without_number"],"A.2","B.3","C.4","D.5","D"]
    assert [r["text"] for r in new["EvidenceBundle"]["payload"]["regions"]] == expected_texts
    for kind in ("SourceBundle","EvidenceBundle","QuestionGraph"):assert new[kind]["producer"]["evidence_mode"] == "OBSERVED"
    for kind in ("PlatformSnapshot","ApplyPlan","ExecutionReceipt"):assert new[kind]["producer"]["evidence_mode"] == "SYNTHETIC"
    reports = {a["payload"]["stage"]:a for a in exchange["artifacts"] if a["kind"] == "CheckReport"}
    for stage,names in (("PRE_APPLY",{"source_integrity","structure","answer_matching","coverage","policy"}),("TARGET",{"target_version","authorized_scope","capabilities","policy"})):
        report = reports[stage]["payload"]; calc = load(run/("assets/calculations/"+stage.lower()+".json"))
        assert set(calc) == {c["check_id"] for c in report["checks"]} == names
        assert report["decision"] == "PASS" and not report["issues"] and all(c["outcome"] == "PASS" for c in report["checks"])
        assert all(all(v is True for v in values.values()) for values in calc.values())
    assert load(run/"assets/calculations/pre_apply.json")["policy"]["ordinary_choice_role_mapping"] is True
    result = receipt["payload"]["results"][0]
    assert result["outcome"] == "APPLIED" and result["effect_match"] == "MATCH" and result["next_step"] == "POSTCHECK" and result["replay_allowed"] is False
    assert result["readback"]["sha256"] == sha((run/"assets/readback.json").read_bytes())
    assert receipt["payload"]["execution_mode"] == plan["payload"]["execution_mode"] == "SIMULATED"
    assert exchange["policies"][0]["confirmation_status"] == "A_INTERNAL_PROPOSAL" and exchange["policies"][0]["applicability"] == "PROPOSAL_ONLY"
    summary = load(run/"summary.json"); supervisor = load(OUT/"normal/supervisor.json")
    assert summary["complete_attempts"] == summary["dispatches"] == summary["successful_closures"] == 1
    assert summary["submission_status"] == "NOT_SUBMITTED" and summary["content_check_status"] == "PENDING"
    assert summary["platform_calls"] == summary["model_calls"] == summary["services_started"] == summary["browsers_started"] == 0
    assert supervisor["candidate_commit"] == PRODUCT and supervisor["child_pid"] == summary["pid"]
    assert supervisor["child_exit_code"] == 0 and supervisor["child_reaped"] and not supervisor["timed_out"]
    assert supervisor["outer_experiment_seconds"] == 180 and supervisor["outer_reclaim_seconds"] == 240
    replay = load(run/"replay-rejection.json"); assert replay == {"layer":"EXECUTION","code":"PLAN_REPLAY","zero_target_change":True,"business_dispatches":0}
    for name,record in load(INPUT/"copy-manifest.json").items():
        assert sha((INPUT/name).read_bytes()) == record["sha256"] and len((INPUT/name).read_bytes()) == record["bytes"]
    assert summary["input_sha256"] == json.loads(blob(PRODUCT,"config/policies/a07-q1-offline-v1.json"))["input_sha256"]
    save("archive-delta-review.json",{"result":"PASS","product":PRODUCT,"delivery":DELIVERY,"old_review":OLD_REVIEW,
        "expected_from_original_rules":EXPECTED,"plan_roles":[f["platform_role"] for f in projected],"actual_roles":[f["platform_role"] for f in actual],
        "changed_role_indices":changed,"all_other_frame_and_projection_fields_equal":True,"source_payload_equal":True,
        "evidence_and_graph_nonreference_payload_equal":True,"old_original_content_and_coordinates_preserved":True,
        "C01_valid_and_ready":True,"full_hashes_recomputed":True,"before_state_hash":before["target_state_hash"],"after_state_hash":after["target_state_hash"],
        "plan_ref":artifact_ref(plan),"receipt_ref":artifact_ref(receipt),"readback_raw_sha256":sha((run/"assets/readback.json").read_bytes()),
        "policy_hash":exchange["policies"][0]["content_hash"],"new_independent_instance":after["instance_id"],"replay":replay,
        "additional_business_attempts_by_this_archive_check":0,"normal_attempts_this_round":1,"targets_this_round":1,"dispatches_this_round":1,"successes_this_round":1,
        "historical_review_attempts":1,"historical_review_successes":1,"cumulative_review_attempts":2,"cumulative_review_successes":2,
        "role_gate_calls_this_round":2,"replay_rejections_this_round":1,"old_nine_case_matrix_rerun":False})
    print("independent original-rule roles and six-frame archival delta PASS; only indices 1-4 Q->W")

def seal(verify=False):
    allowed = lambda p:p == REPORT or p.startswith("docs/evidence/A07/F01/review/")
    if not verify:
        assert git("rev-parse","HEAD").decode().strip() == PRODUCT
        changes = git("diff","--cached","--name-status","HEAD").decode().splitlines()
        assert changes and all(row.startswith("A\t") and allowed(row[2:]) for row in changes)
        members = []
        for row in git("ls-files","--stage","-z","--",REPORT,"docs/evidence/A07/F01/review/").split(b"\0"):
            if row:
                head,path = row.split(b"\t",1); mode,oid,stage = head.decode().split(); path = path.decode()
                assert stage == "0" and path != MANIFEST and allowed(path)
                members.append({"path":path,"mode":mode,"blob_oid":oid})
        values = batch(list(dict.fromkeys(m["blob_oid"] for m in members)))
        for m in members:m.update(bytes=len(values[m["blob_oid"]]),sha256=sha(values[m["blob_oid"]]))
        save("raw-git-manifest.json",{"parent_product_commit":PRODUCT,"reviewed_author_delivery":DELIVERY,"old_review_preserved":OLD_REVIEW,
            "basis":"raw staged Git blobs; final commit verified after seal","self_excluded_path":MANIFEST,
            "members_count":len(members),"bytes":sum(m["bytes"] for m in members),"members":members})
    else:
        head = git("rev-parse","HEAD").decode().strip(); actual,base = tree(head),tree(PRODUCT)
        assert all(actual.get(p) == v for p,v in base.items())
        added = set(actual)-set(base); assert all(map(allowed,added))
        raw = blob(head,MANIFEST); manifest = json.loads(raw)
        assert {m["path"] for m in manifest["members"]} == added-{MANIFEST}
        values = batch(list(dict.fromkeys(m["blob_oid"] for m in manifest["members"])))
        for m in manifest["members"]:
            assert actual[m["path"]][2] == m["blob_oid"] and sha(values[m["blob_oid"]]) == m["sha256"] and len(values[m["blob_oid"]]) == m["bytes"]
        import re
        report = ROOT/REPORT; links = re.findall(r'\]\(([^)]+)\)',report.read_text(encoding="utf-8"))
        assert all((report.parent/link.split("#")[0]).resolve().exists() for link in links if "://" not in link)
        print(json.dumps({"result":"PASS","review_commit":head,"tree":git("rev-parse",head+"^{tree}").decode().strip(),
            "members":manifest["members_count"],"bytes":manifest["bytes"],"added_paths":len(added),"old_candidate_paths_preserved":True,
            "report_sha256":sha(blob(head,REPORT)),"manifest_sha256":sha(raw),"links_checked":len(links)}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("phase",choices=("static","gates","archive","seal","verify"))
    phase = parser.parse_args().phase
    {"static":static,"gates":gates,"archive":archive,"seal":seal,"verify":lambda:seal(True)}[phase]()
