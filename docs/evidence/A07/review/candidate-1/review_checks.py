"""Independent A07 finite review; never performs a successful business dispatch."""
import argparse
import copy
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import zipfile
from dataclasses import replace
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
WORKFLOW = "b1c84db9d1d5603a4fd6aa5487d7c45ec6fca50a"
CANDIDATE = "6dad9b9a40a10989c102d91cf7b54f19c012015f"
DELIVERY = "d2e710c817cf85505ac4fad4919dd51d1062d33a"
APPROVAL = "cf6f675cfd98d438d7d465fc553e0ebbf1bfff71bd62f8453854f8527015cb6c"
INPUT = REPO / ".local/a07/review-inputs"

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def encoded(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def save(name, obj):
    path = OUT / name
    if path.exists():
        raise RuntimeError("refusing to overwrite evidence: " + str(path))
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def git(*args):
    return subprocess.check_output(["git", "-c", "core.longpaths=true", *args], cwd=REPO,
                                   env=dict(os.environ, GIT_NO_LAZY_FETCH="1"))

def tree(commit):
    result = {}
    for entry in git("ls-tree", "-rz", commit).split(b"\0"):
        if entry:
            head, name = entry.split(b"\t", 1)
            result[name.decode("utf-8")] = head.decode("ascii").split()
    return result

def blobs(oids):
    process = subprocess.Popen(["git", "-c", "core.longpaths=true", "cat-file", "--batch"],
                               cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               env=dict(os.environ, GIT_NO_LAZY_FETCH="1"))
    raw, _ = process.communicate(("\n".join(oids) + "\n").encode("ascii"))
    assert process.returncode == 0
    output, offset = {}, 0
    for oid in oids:
        newline = raw.index(b"\n", offset)
        header = raw[offset:newline].split()
        assert header[0].decode() == oid and header[1] == b"blob"
        count = int(header[2]); start = newline + 1
        output[oid] = raw[start:start+count]
        assert raw[start+count:start+count+1] == b"\n"
        offset = start + count + 1
    assert offset == len(raw)
    return output

def static():
    import PIL, pydantic
    trees = {c: tree(c) for c in (WORKFLOW, CANDIDATE, DELIVERY)}
    original, product, final = [trees[c] for c in (WORKFLOW, CANDIDATE, DELIVERY)]
    assert all(final.get(p) == spec and product.get(p) == spec for p, spec in original.items())
    assert all(final.get(p) == spec for p, spec in product.items())
    added = sorted(set(final)-set(original))
    product_added = sorted(set(product)-set(original))
    allowed = lambda p: (p.startswith(("src/annotation/source/b_q1/", "src/annotation/delivery/q1_offline/", "examples/a07/", "tests/fixtures/a07/", "docs/evidence/A07/execution/")) or p in ("src/annotation/quality/q1_offline.py", "config/policies/a07-q1-offline-v1.json", "docs/tasks/A07-Q1-execution-report.md") or p.startswith("tests/test_a07_"))
    assert len(product_added) == 11 and len(added) == 64 and all(map(allowed, added))
    manifest_path = "docs/evidence/A07/execution/delivery-raw-git-manifest.json"
    manifest_raw = git("show", DELIVERY+":"+manifest_path)
    assert digest(manifest_raw) == "111918592d83446bba6d485f4d3f49d797787e925ed630f31f149c14c1ddcdcf"
    manifest = json.loads(manifest_raw)
    assert manifest["self_excluded_path"] == manifest_path
    assert {x["path"] for x in manifest["members"]} == set(added)-{manifest_path}
    raw_blobs = blobs(list(dict.fromkeys(x["blob_oid"] for x in manifest["members"])))
    for member in manifest["members"]:
        raw = raw_blobs[member["blob_oid"]]
        assert final[member["path"]][2] == member["blob_oid"]
        assert len(raw) == member["bytes"] and digest(raw) == member["sha256"]
    assert len(manifest["members"]) == 63 and sum(x["bytes"] for x in manifest["members"]) == 10217431
    assert digest(git("show", DELIVERY+":docs/tasks/A07-Q1-execution-report.md")) == "404e3795d99b13312783fc8cfc46575a3d0b60c7050488ae62d54fb2724044df"
    assert digest(git("show", WORKFLOW+":docs/approvals/A07-Q1-offline-business-approval.json")) == APPROVAL
    save("reviewed-delivery-raw-members.json", {"delivery":DELIVERY, "basis":"raw Git blobs, independent cat-file --batch", "members":manifest["members"], "manifest_self":{"path":manifest_path,"sha256":digest(manifest_raw),"bytes":len(manifest_raw)}})
    save("static-review.json", {"result":"PASS", "workflow":WORKFLOW,"candidate":CANDIDATE,"delivery":DELIVERY,
        "trees":{c:git("rev-parse",c+"^{tree}").decode().strip() for c in trees},
        "workflow_paths_preserved":len(original),"candidate_paths_preserved":len(product),"product_added":product_added,
        "delivery_added_count":len(added),"delivery_manifest_members":len(manifest["members"]),"delivery_manifest_bytes":10217431,
        "old_blob_or_mode_changes":[],"scope_violations":[],"approval_sha256":APPROVAL,
        "runtime":{"python":sys.version,"executable":sys.executable,"platform":platform.platform(),"pydantic":pydantic.__version__,"pillow":PIL.__version__},
        "complete_business_attempts":0,"business_dispatches":0})
    print("static preservation and raw member verification PASS")

def pointer(files, reference):
    name, fragment = reference.split("#",1)
    value = json.loads(files[name])
    for token in fragment.split("/")[1:]:
        token = token.replace("~1","/").replace("~0","~")
        value = value[int(token)] if isinstance(value,list) else value[token]
    return value

def read_archive(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names))
        files = {n:archive.read(n) for n in names}
    entries = json.loads(files["manifest.json"])["files"]
    assert {e["path"] for e in entries} == set(files)-{"manifest.json"}
    for e in entries:
        assert digest(files[e["path"]]) == e["sha256"] and len(files[e["path"]]) == e["bytes"]
    return files

def inputs_audit():
    from PIL import Image
    base, side = read_archive(INPUT/"base.zip"), read_archive(INPUT/"candidate.zip")
    candidate = json.loads(side["candidate.json"])
    payload = candidate["payload"]
    approval = json.loads((INPUT/"approval.json").read_bytes())
    policy = json.loads((REPO/"config/policies/a07-q1-offline-v1.json").read_bytes())
    assert digest((INPUT/"approval.json").read_bytes()) == APPROVAL
    pins = {"base_zip":digest((INPUT/"base.zip").read_bytes()),"candidate_zip":digest((INPUT/"candidate.zip").read_bytes()),
        "candidate_file":digest(side["candidate.json"]),"manifest":digest(side["manifest.json"]),
        "scope_proposal":digest(side["scope-applicability-proposal.json"]),"history":digest((INPUT/"history.json").read_bytes())}
    assert pins == policy["input_sha256"]
    assert {k:candidate[k] for k in ("artifact_id","revision","content_hash")} == approval["candidate_ref"]
    assert candidate["kind"] == "QuestionSourceReviewCandidate" and candidate["schema_version"] == "b-question-source-review-trial/0.1"
    assert digest(encoded(payload)) == candidate["content_hash"]
    assert payload["decision"] == "HOLD" and all(payload[k] is False for k in ("human_verified","business_acceptance","a_accepted","production_applied"))
    selection = json.loads(side["native-selection.json"])
    q = pointer(base,selection["object_paths"]["question"])
    a = pointer(base,selection["object_paths"]["answer"])
    assert q == selection["native_question_snapshot"] and a == selection["native_answer_snapshot"]
    assert q["question_id"] == approval["question_id"] and a["answer_id"] == approval["answer_id"]
    assert q["selected_answer_id"] == a["answer_id"] and q["section_path"] == a["section_path"] == payload["section_path"]
    assert a["fragments"][0]["raw_text"] == "1.D" and a["fragments"][0]["text_span"] == [2,3]
    binding = json.loads(side["base-package-binding.json"])
    references = []
    for path, info in binding["source_artifacts"].items():
        doc = json.loads(base[path]); reference = {k:doc[k] for k in ("artifact_id","revision","content_hash")}
        assert reference == info["reference"] and digest(base[path]) == info["file_sha256"]
        assert digest(encoded(doc["payload"])) == doc["content_hash"]
        references.append(reference)
    assert references == candidate["input_refs"]
    history = json.loads((INPUT/"history.json").read_bytes())
    assert all(history[k] == selection["historical_evidence"][k] for k in ("kind","schema_version","artifact_id","revision","content_hash"))
    assert digest(encoded(history["payload"])) == history["content_hash"]
    content = payload["candidate_content"]
    assert content["stem_with_number_and_source_linebreaks"].startswith("1.")
    assert content["stem_with_number_and_source_linebreaks"][2:].replace("\n","") == content["stem_body_normalized_without_number"] == approval["approved_content"]["stem"]
    assert content["option_texts"] == ["A.2","B.3","C.4","D.5"] and content["answer_text"] == "D"
    assert content["explanation_present"] is False and content["explanation_text"] == ""
    assert [ord(x) for x in content["stem_body_normalized_without_number"][-4:]] == [0xff08,0x3000,0x3000,0xff09]
    selected = [next(r for r in payload["regions"] if r["region_id"] == rid) for rid in payload["proposed_semantic_region_ids"]]
    expected_boxes = [[70,332,590,445],[96,453,153,486],[207,453,262,486],[320,453,374,486],[430,453,486,486],[72,239,88,258]]
    assert payload["proposed_semantic_region_ids"] == policy["semantic_region_ids"] and len(selected) == 6
    assert [r["role"] for r in selected] == ["stem","option","option","option","option","answer"]
    assert [r["bbox"] for r in selected] == expected_boxes
    images, image_records = {}, []
    for item in payload["sources"]:
        raw = side[item["path"]]
        assert raw == base[item["source_package_path"]] and digest(raw) == item["sha256"]
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        assert list(image.size) == [item["width"],item["height"]]
        images[item["asset_id"]] = image
        image_records.append({"asset_id":item["asset_id"],"size":list(image.size),"sha256":digest(raw)})
    assert len(images) == 2 and len(payload["regions"]) == 13
    for r in payload["regions"]:
        crop = r["crop"]; image = images[r["asset_id"]]
        actual = Image.open(io.BytesIO(side[crop["path"]])).convert("RGB")
        assert actual.tobytes() == image.crop(r["bbox"]).tobytes()
        assert list(actual.size) == crop["size"] and digest(side[crop["path"]]) == crop["sha256"] and digest(actual.tobytes()) == crop["rgb_sha256"]
        assert crop["crop_to_original"] == [[1,0,r["bbox"][0]],[0,1,r["bbox"][1]],[0,0,1]]
    mapped = [fid for r in selected for fid in r["source_fragment_ids"]]
    assert sorted(mapped) == sorted(f["fragment_id"] for f in q["fragments"]+a["fragments"]) and len(mapped) == len(set(mapped)) == 7
    proposal = json.loads(side["scope-applicability-proposal.json"])
    issues = json.loads(side["native-scope-issues.json"])["scope_issues"]
    assert len(issues) == len(proposal["dispositions"]) == 31
    assert {e["issue"]["issue_id"] for e in issues} == {d["issue_id"] for d in proposal["dispositions"]}
    for entry in issues:
        assert pointer(base,entry["pointer"]) == entry["issue"]
    exclusion_ids, proof_count, business_ids = [],0,[]
    for d in proposal["dispositions"]:
        original = pointer(base,d["original_issue_pointer"])
        assert original["issue_id"] == d["issue_id"] and original["code"] == d["code"]
        if d["code"] == "BUSINESS_REVIEW_REQUIRED":
            assert d["issue_id"] == policy["business_issue_id"] and d["proof"] == []
            business_ids.append(d["issue_id"]); continue
        ex = next(e for e in policy["exclusions"] if e["issue_id"] == d["issue_id"])
        assert digest(encoded(d)) == ex["entry_sha256"] and ex["proof_pointers"] == [p["pointer"] for p in d["proof"]]
        assert ex["original_issue_pointer"] == d["original_issue_pointer"] and ex["reason"] == d["reason"]
        for proof in d["proof"]:
            value = pointer(base,proof["pointer"])
            assert value == proof["value"]
            if "affected_answer_ids" in value:
                assert value["affected_answer_ids"] and approval["answer_id"] not in value["affected_answer_ids"]
            else:
                boxes = [value["bbox"]] if "bbox" in value else [v["bbox"] for v in value["source_regions"]]
                assert boxes
                for box in boxes:
                    for region in selected:
                        if proof["asset_id"] == region["asset_id"]:
                            target = region["bbox"]
                            assert not (max(box[0],target[0]) < min(box[2],target[2]) and max(box[1],target[1]) < min(box[3],target[3]))
            proof_count += 1
        exclusion_ids.append(d["issue_id"])
    assert len(exclusion_ids) == len(policy["exclusions"]) == 30 and proof_count == 78 and len(business_ids) == 1
    original_check = json.loads(base["artifacts/check.json"])
    original_graph = json.loads(base["artifacts/graph.json"])
    assert len(original_check["payload"]["issues"]) == 127
    assert sum(v["status"] == "UNASSIGNED" for v in original_graph["payload"]["answer_coverage"]) == 19
    save("input-binding-review.json",{"result":"PASS","input_sha256":pins,"approval_sha256":APPROVAL,
        "policy_sha256":digest((REPO/"config/policies/a07-q1-offline-v1.json").read_bytes()),"candidate_ref":approval["candidate_ref"],
        "base_input_refs":references,"archive_member_counts":{"base":len(base),"side":len(side)},"images":image_records,
        "six_groups":[{"region_id":r["region_id"],"role":r["role"],"asset_id":r["asset_id"],"bbox":r["bbox"]} for r in selected],
        "raw_stem":content["stem_with_number_and_source_linebreaks"],"normalized_stem":content["stem_body_normalized_without_number"],
        "options":content["option_texts"],"answer":"D","answer_original_text":"1.D","answer_span":[2,3],"explanation":False,
        "crops_pixel_compared":13,"native_fragments_mapped":7,"original_check_issues":127,"scoped_issues":31,"proof_objects":78,
        "exclusion_ids":exclusion_ids,"business_ids":business_ids,"original_unassigned_ledger":19,"original_B_HOLD_flags_preserved":True,
        "A_only_approval":True,"B_joint_adoption":False,"human_visual_acceptance_claim":False,"whole_page_coverage_claim":False})
    print("independent input, geometry, issue and authorization review PASS")

def negative():
    from annotation.contracts import artifact_ref,seal_artifact,validate_bundle
    from annotation.delivery.q1_offline import MemoryTarget,prepare,execute
    from annotation.source.b_q1.reader import Q1Error,load_inputs,archive
    inputs = load_inputs(INPUT/"base.zip",INPUT/"candidate.zip",INPUT/"history.json",INPUT/"approval.json",REPO/"config/policies/a07-q1-offline-v1.json")
    target = MemoryTarget(); root = REPO/".local/a07/review-negative-assets"
    root.mkdir(parents=True,exist_ok=False)
    run_id, now = "a07-review-negative-1","2026-10-18T12:25:00+00:00"
    bundle,plan,_ = prepare(inputs,target,root,run_id,now)
    calls = []
    def refused(name,operation,observed,expected,envelope_valid=None):
        before = observed.snapshot_view()
        try:
            operation()
        except Q1Error as error:
            assert error.code == expected,(name,error.layer,error.code)
            assert observed.snapshot_view() == before
            calls.append({"case":name,"layer":error.layer,"code":error.code,"zero_target_change":True,
                          "zero_consumed_plan":not observed._consumed,"business_dispatches":0,"envelope_validated_before_call":envelope_valid})
        else:
            raise AssertionError("negative call accepted: "+name)
    def call(changed=inputs,observed=target,data=bundle,reference=None):
        return lambda:execute(changed,observed,data,reference or artifact_ref(plan),root,run_id,now)
    refused("missing authorization",call(replace(inputs,approval_raw=b"")),target,"APPROVAL_MISSING")
    forged = json.loads(inputs.approval_raw); forged["allowed_use"] = "PLATFORM"
    refused("forged broadened authority",call(replace(inputs,approval_raw=encoded(forged))),target,"APPROVAL_FORGED")
    with zipfile.ZipFile(io.BytesIO(inputs.candidate_raw)) as z:
        files = {n:z.read(n) for n in z.namelist()}
    modified = json.loads(files["candidate.json"])
    modified["payload"]["candidate_content"]["option_texts"][2] = "C.6"
    modified["content_hash"] = digest(encoded(modified["payload"]))
    files["candidate.json"] = encoded(modified)
    manifest = json.loads(files["manifest.json"])
    for entry in manifest["files"]:
        entry.update(bytes=len(files[entry["path"]]),sha256=digest(files[entry["path"]]))
    files["manifest.json"] = encoded(manifest)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream,"w") as z:
        for name,raw in files.items(): z.writestr(name,raw)
    mutated_raw = stream.getvalue(); archive(mutated_raw)
    refused("self-rehashed changed option with valid ZIP manifest",call(replace(inputs,candidate_raw=mutated_raw)),target,"INPUT_BINDING",True)
    history = json.loads(inputs.history_raw); history["revision"] += 1
    archive(inputs.base_raw); archive(inputs.candidate_raw)
    refused("changed associated history identity",call(replace(inputs,history_raw=encoded(history))),target,"INPUT_BINDING",True)
    refused("platform mode",lambda:prepare(inputs,target,root,run_id,now,execution_mode="PLATFORM"),target,"PLATFORM_MODE_FORBIDDEN")
    wrong = MemoryTarget(target_id="review-other-target")
    refused("wrong target",call(observed=wrong),wrong,"TARGET_IDENTITY")
    outside = MemoryTarget(scope_id="review-other-scope")
    refused("outside approved single-question scope",call(observed=outside),outside,"TARGET_IDENTITY")
    drift = MemoryTarget(); drift._state["epoch"] = 1
    refused("changed current target",call(observed=drift),drift,"TARGET_CHANGED")
    forged_bundle = bundle.model_dump(mode="json"); modified_plan = copy.deepcopy(plan)
    modified_plan["payload"]["actions"][0]["expected_after"]["frame_count"] = 7
    modified_plan = seal_artifact(modified_plan); forged_bundle["artifacts"][-1] = modified_plan
    validate_bundle(forged_bundle,asset_root=root)
    refused("C01-valid resealed seven-frame effect",call(data=forged_bundle,reference=artifact_ref(modified_plan)),target,"PLAN_RECOMPUTATION",True)
    assert not target.snapshot_view()["target"]["frames"] and not target._consumed
    save("negative-calls.json",{"calls":calls,"planning_only_positive":True,"complete_business_attempts":0,
        "business_dispatches":0,"successful_closures":0,"final_target":target.snapshot_view(),"pid":os.getpid()})
    print("independent finite negative checks PASS; 9 rejected, zero business dispatch")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("phase",choices=("static","inputs","negative"))
    phase = parser.parse_args().phase
    {"static":static,"inputs":inputs_audit,"negative":negative}[phase]()
