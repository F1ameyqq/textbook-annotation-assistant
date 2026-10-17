"""Trace why the informational reference_commit mutation passed focused tests."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path

EVIDENCE=Path(__file__).resolve().parent
bootstrap=json.loads((EVIDENCE.parent/"bootstrap.json").read_text(encoding="utf-8"))
root=Path(bootstrap["raw"])
stage=Path(bootstrap["stage"])/"negative"/"root metadata proof"
stage.mkdir(exist_ok=False)
fixture=stage/"fixture"; fixture.mkdir()
raw=(EVIDENCE/"I04-root-reference-identity/mutation/changed.bin").read_bytes()
(fixture/"reference.json").write_bytes(raw)
original=json.loads((root/"tests/fixtures/a01/R3/preservation-manifest.json").read_text(encoding="utf-8"))
entries={e["path"]:e for e in original["files"]}
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
fixed=load("root_commit_probe_fixed",root/"examples/a01/integration-R1/fixed_inputs.py")
preservation=load("root_commit_probe_preservation",root/"examples/a01/R3/preservation.py")
selected=fixed.materialize(fixture,stage/"materialized")
audit=preservation.audit(stage/"materialized",selected)
records=[]
for entry in selected["files"]:
    data=(stage/"materialized"/entry["path"]).read_bytes()
    records.append(dict(path=entry["path"],equals_original_manifest_entry=entry==entries[entry["path"]],
                        sha256_matches_original=hashlib.sha256(data).hexdigest()==entries[entry["path"]]["git_sha256"],
                        recomputed_git_blob_oid=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest(),
                        original_git_blob_oid=entries[entry["path"]]["git_blob_oid"]))
assert all(r["equals_original_manifest_entry"] and r["sha256_matches_original"] and r["recomputed_git_blob_oid"]==r["original_git_blob_oid"] for r in records)
assert selected["reference_commit"]=="0"*40 and audit["passed"]
result=dict(changed_fixture_sha256=hashlib.sha256(raw).hexdigest(),changed_reference_commit=selected["reference_commit"],
            original_reference_commit=original["reference_commit"],source_manifest_sha256=selected["source_manifest_sha256"],
            source_manifest_sha256_matches_original=selected["source_manifest_sha256"]==hashlib.sha256((root/"tests/fixtures/a01/R3/preservation-manifest.json").read_bytes()).hexdigest(),
            unchanged_fixed_module=str(root/"examples/a01/integration-R1/fixed_inputs.py"),unchanged_preservation_module=str(root/"examples/a01/R3/preservation.py"),
            records=records,all_original_entries_and_payloads_still_match=True,audit_passed=audit["passed"],
            interpretation="The unasserted top-level reference_commit is informational in this path; no per-file original Git OID/SHA/length/representation or source-manifest digest was bypassed.")
with (EVIDENCE/"root-reference-proof.json").open("w",encoding="utf-8",newline="\n") as handle:
    json.dump(result,handle,ensure_ascii=False,indent=2); handle.write("\n")
print(json.dumps(result,ensure_ascii=False,indent=2))
