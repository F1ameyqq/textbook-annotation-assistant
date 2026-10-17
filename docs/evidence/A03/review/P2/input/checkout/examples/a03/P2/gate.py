"""Exercise public recovery admission in a separate bounded process.

New negative files are deliberately untrusted inputs. This process never grants
runtime permission and never opens a target or runtime database.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, allow_nan=False)
        stream.write("\n")


def gate(request):
    from annotation.contracts import (
        ContractError, convert_synthetic_fixture, load_archive_bundle,
        load_recovery_bundle,
    )
    source = Path(request["input_path"])
    digest_before = hashlib.sha256(source.read_bytes()).hexdigest()
    operation = request["gate_operation"]
    try:
        if operation == "archive":
            archive = load_archive_bundle(source)
            if archive["eligibility"] != "ARCHIVE_ONLY":
                raise AssertionError("legacy archive acquired execution eligibility")
            result = {"eligibility": archive["eligibility"]}
        elif operation == "reject-old":
            load_recovery_bundle(source)
            raise AssertionError("legacy bundle entered recovery namespace")
        elif operation == "convert-history":
            convert_synthetic_fixture(source, request["conversion_output"], conversion_id="a03-refused-history",
                                      expected_input_sha256=digest_before)
            raise AssertionError("legacy UNKNOWN history converted into new fixture")
        else:
            data = copy.deepcopy(json.loads(source.read_text(encoding="utf-8")))
            if operation == "wrong-exchange-version":
                data["format_version"] = "a03-exchange-unsupported"
            elif operation == "resource-digest":
                data["evidence"][0]["resource"]["sha256"] = "0" * 64
            elif operation == "reference-extra-field":
                plan = next(a for a in data["artifacts"] if a["kind"] == "ApplyPlan")
                plan["payload"]["graph"]["undeclared_scope"] = "other-scope"
            elif operation in ("nested-original", "nested-observed"):
                origin = "ORIGINAL" if operation.endswith("original") else "OBSERVED"
                resource_path = source.parent / "assets" / ("process-gate-" + operation + ".json")
                write_new(resource_path, {"origin": origin})
                data["evidence"].append({
                    "evidence_id": "process-gate-" + operation,
                    "resource": {"path": "assets/" + resource_path.name,
                                 "sha256": hashlib.sha256(resource_path.read_bytes()).hexdigest(),
                                 "media_type": "application/json", "origin": "SYNTHETIC"},
                    "mode": "SYNTHETIC", "description": "author negative nested provenance",
                })
            else:
                raise ValueError(operation)
            path = source.parent / ("process-gate-" + operation + ".json")
            write_new(path, data)
            load_recovery_bundle(path, asset_root=request["asset_root"])
            raise AssertionError("untrusted negative input was admitted")
    except ContractError as error:
        codes = [issue["code"] for issue in error.issues]
        if request.get("expected_code") not in codes:
            raise AssertionError("wrong public refusal: " + repr(error.issues))
        result = {"rejected": True, "codes": codes, "issues": error.issues}
    digest_after = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest_before != digest_after:
        raise AssertionError("public gate or conversion changed source input")
    result.update({"source_sha256_before": digest_before, "source_sha256_after": digest_after})
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    gate(json.loads(args.request.read_text(encoding="utf-8")))
