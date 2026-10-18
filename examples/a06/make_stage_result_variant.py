"""F01 only: one non-final inline_apply result version TEST_VARIANT."""
import argparse
import copy
import json
from pathlib import Path
import zipfile

from make_variants import ORIGINAL_SHA, encoded, payload_sha, sha


def native_ref(obj):
    return {key: obj[key] for key in ("artifact_id", "revision", "content_hash")}


def make_stage_result_variant(source, destination):
    original = Path(source).read_bytes()
    if sha(original) != ORIGINAL_SHA:
        raise ValueError("F01 recipe requires original fixed ZIP")
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(Path(source)) as archive:
        original_files = {name: archive.read(name) for name in archive.namelist()}
    files = dict(original_files)
    manifest = json.loads(files.pop("manifest.json"))
    docs = {name: json.loads(blob) for name, blob in files.items() if name.endswith(".json")}
    report = docs["artifacts/pipeline-report.json"]
    stage = next(s for s in report["payload"]["stages"] if s["stage_id"] == "inline_apply")
    original_wrapper_path = stage["output"]["path"]
    result = docs[original_wrapper_path]["payload"]["result"]
    before = copy.deepcopy(result)
    if (before["kind"], before["schema_version"]) != ("InlineApplyStageTrial", "b-inline-apply-stage-trial/0.1"):
        raise ValueError("fixed observed result differs")
    result["schema_version"] = "b-inline-apply-stage-trial/9.9"
    replacements = {}
    for iteration in range(40):
        next_replacements = {}
        def update(value):
            if isinstance(value, str):
                return replacements.get(value, value)
            if isinstance(value, list):
                return [update(v) for v in value]
            if not isinstance(value, dict):
                return value
            updated = {k: update(v) for k, v in value.items()}
            if "payload" in updated and "content_hash" in updated:
                digest = payload_sha(updated["payload"])
                if digest != updated["content_hash"]:
                    next_replacements[updated["content_hash"]] = digest
                updated["content_hash"] = digest
            return updated
        moved = {}
        changed = False
        for name, doc in list(docs.items()):
            updated = update(doc)
            old_blob = files[name]
            blob = encoded(updated) if updated != json.loads(old_blob) else old_blob
            new_name = name
            if blob != old_blob:
                changed = True
                next_replacements[sha(old_blob)] = sha(blob)
                if name.startswith("objects/"):
                    new_name = "objects/" + sha(blob) + ".json"
                    next_replacements[name] = new_name
                    del files[name]
                files[new_name] = blob
            moved[new_name] = updated
        docs = moved
        manifest = update(manifest)
        replacements.update(next_replacements)
        for key in list(replacements):
            seen, value = set(), replacements[key]
            while value in replacements and value not in seen:
                seen.add(value)
                value = replacements[value]
            replacements[key] = value
        if not changed and not next_replacements:
            break
    else:
        raise RuntimeError("fixed recipe binding did not converge")
    manifest["files"] = [{"path": name, "bytes": len(blob), "sha256": sha(blob)} for name, blob in sorted(files.items())]
    files["manifest.json"] = encoded(manifest)
    report = docs["artifacts/pipeline-report.json"]
    original_report = json.loads(original_files["artifacts/pipeline-report.json"])
    stage = next(s for s in report["payload"]["stages"] if s["stage_id"] == "inline_apply")
    target = stage["output"]["path"]
    after = docs[target]["payload"]["result"]
    restored = copy.deepcopy(after)
    restored["schema_version"] = before["schema_version"]
    assert restored == before
    assert native_ref(before) == native_ref(after)
    assert report["payload"]["final_outputs"] == original_report["payload"]["final_outputs"]
    verified = []
    for current, old in zip(report["payload"]["stages"], original_report["payload"]["stages"]):
        output = current["output"]
        wrapper = docs[output["path"]]
        assert sha(files[output["path"]]) == output["sha256"]
        assert native_ref(wrapper) == output["artifact_ref"]
        assert native_ref(wrapper["payload"]["result"]) == current["result_ref"]
        if current["stage_id"] != "inline_apply":
            assert wrapper["payload"]["result"] == json.loads(original_files[old["output"]["path"]])["payload"]["result"]
        verified.append(current["stage_id"])
    def audit_payloads(obj):
        if isinstance(obj, dict):
            if "payload" in obj and "content_hash" in obj:
                assert obj["content_hash"] == payload_sha(obj["payload"])
            for v in obj.values():
                audit_payloads(v)
        elif isinstance(obj, list):
            for v in obj:
                audit_payloads(v)
    for doc in docs.values():
        audit_payloads(doc)
    for name in ("artifacts/evidence.json", "artifacts/graph.json", "artifacts/check.json"):
        assert files[name] == original_files[name]
    assert manifest["report_ref"] == native_ref(report)
    output = dest / "unknown-stage-result.zip"
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, blob in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 18, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, blob, compresslevel=9)
    changes = {}
    for name in sorted(set(original_files) | set(files)):
        old, new = original_files.get(name), files.get(name)
        if old != new:
            changes[name] = {"before": None if old is None else {"sha256": sha(old), "bytes": len(old)},
                             "after": None if new is None else {"sha256": sha(new), "bytes": len(new)}}
    recipe = {"identity": "TEST_VARIANT", "original_sha256": ORIGINAL_SHA,
              "path": str(output.resolve()), "bytes": output.stat().st_size, "sha256": sha(output.read_bytes()),
              "manifest_sha256": sha(files["manifest.json"]), "binding_iterations": iteration + 1,
              "stage_id": "inline_apply", "mutation": {"before_path": original_wrapper_path + "#/payload/result/schema_version",
              "after_path": target + "#/payload/result/schema_version", "before": before["schema_version"], "after": after["schema_version"],
              "kind": after["kind"], "result_ref_before": native_ref(before), "result_ref_after": native_ref(after)},
              "expected_code": "UNSUPPORTED_VERSION", "expected_layer": "VERSION", "expected_error_path": target + "#/payload/result/schema_version",
              "static_audit": {"all_outer_members_resealed": True, "all_payload_hashes_valid": True,
                               "all_wrapper_and_result_refs_valid": verified, "final_E_G_Check_bytes_unchanged": True,
                               "other_13_stage_results_unchanged": True, "target_result_payload_and_identity_unchanged": True},
              "changed_members": changes}
    (dest / "recipe.json").write_bytes(encoded(recipe))
    return recipe


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("destination")
    args = parser.parse_args()
    print(json.dumps(make_stage_result_variant(args.source, args.destination), ensure_ascii=False, sort_keys=True))
