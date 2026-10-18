"""Deterministic TEST_VARIANT recipes; never executes B code or edits its ZIP."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import zipfile

ORIGINAL_SHA = "b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def payload_sha(obj):
    return sha(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))


def make_variants(source, destination):
    original = Path(source).read_bytes()
    if sha(original) != ORIGINAL_SHA:
        raise ValueError("recipe requires the exact original B ZIP")
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(Path(source)) as archive:
        original_files = {n: archive.read(n) for n in archive.namelist()}
    results = []
    for variant in ("bad-resource", "stale-check", "unknown-version"):
        files = dict(original_files)
        manifest = json.loads(files.pop("manifest.json"))
        docs = {n: json.loads(b) for n, b in files.items() if n.endswith(".json")}
        changes = {}
        if variant == "bad-resource":
            target = "supporting-fixtures/q4-stem.jpg"
            files[target] = b"A06 TEST_VARIANT: intentionally undecodable image\n"
            mutation = {"path": target, "before_sha256": sha(original_files[target]), "after_sha256": sha(files[target])}
        else:
            target = "artifacts/check.json" if variant == "stale-check" else "artifacts/graph.json"
            identity = docs[target]["artifact_id"]
            before = copy.deepcopy(docs[target])
            for doc in docs.values():
                def mutate(value):
                    if isinstance(value, dict):
                        if value.get("artifact_id") == identity and "payload" in value:
                            if variant == "stale-check":
                                value["payload"]["graph_ref"] = copy.deepcopy(before["payload"]["base_check_archive"]["payload"]["graph_ref"])
                            else:
                                value["schema_version"] = "b-graph-trial/9.9"
                        for child in value.values():
                            mutate(child)
                    elif isinstance(value, list):
                        for child in value:
                            mutate(child)
                mutate(doc)
            mutation = {"path": target, "artifact_id": identity,
                        "field": "payload.graph_ref" if variant == "stale-check" else "schema_version",
                        "before": before["payload"]["graph_ref"] if variant == "stale-check" else before["schema_version"],
                        "after": docs[target]["payload"]["graph_ref"] if variant == "stale-check" else docs[target]["schema_version"]}

        # Rebind changed payloads, wrapper/result references, file-addressed paths,
        # downstream stage dependencies, pipeline report and manifest to a fixed point.
        # Source declarations and the intentionally stale graph reference are unchanged.
        replacements = {}
        for iteration in range(40):
            new_replacements = {}
            def update(value):
                if isinstance(value, str):
                    return replacements.get(value, value)
                if isinstance(value, list):
                    return [update(v) for v in value]
                if not isinstance(value, dict):
                    return value
                result = {k: update(v) for k, v in value.items()}
                if "payload" in result and "content_hash" in result:
                    new = payload_sha(result["payload"])
                    if new != result["content_hash"]:
                        new_replacements[result["content_hash"]] = new
                    result["content_hash"] = new
                return result
            moved = {}
            any_change = False
            for name, doc in list(docs.items()):
                updated = update(doc)
                old_blob = files[name]
                # Preserve all unmodified files byte for byte, including their formatting.
                blob = encoded(updated) if updated != json.loads(old_blob) else old_blob
                new_name = name
                if blob != old_blob:
                    any_change = True
                    old_sha, new_sha = sha(old_blob), sha(blob)
                    new_replacements[old_sha] = new_sha
                    if name.startswith("objects/"):
                        new_name = "objects/" + new_sha + ".json"
                        new_replacements[name] = new_name
                        del files[name]
                    files[new_name] = blob
                moved[new_name] = updated
            docs = moved
            manifest = update(manifest)
            replacements.update(new_replacements)
            # Collapse replacement chains while retaining old identifiers for nested copies.
            for key in list(replacements):
                seen = set()
                value = replacements[key]
                while value in replacements and value not in seen:
                    seen.add(value)
                    value = replacements[value]
                replacements[key] = value
            if not any_change and not new_replacements:
                break
        else:
            raise RuntimeError("variant binding did not converge within recipe bound")
        manifest["files"] = [{"path": n, "bytes": len(b), "sha256": sha(b)} for n, b in sorted(files.items())]
        files["manifest.json"] = encoded(manifest)
        output = dest / (variant + ".zip")
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, blob in sorted(files.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 10, 18, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, blob, compresslevel=9)
        for name in sorted(set(original_files) | set(files)):
            old, new = original_files.get(name), files.get(name)
            if old != new:
                changes[name] = {"before": None if old is None else {"sha256": sha(old), "bytes": len(old)},
                                 "after": None if new is None else {"sha256": sha(new), "bytes": len(new)}}
        result = {"identity": "TEST_VARIANT", "case": variant, "path": str(output.resolve()),
                  "sha256": sha(output.read_bytes()), "bytes": output.stat().st_size,
                  "manifest_sha256": sha(files["manifest.json"]), "original_sha256": ORIGINAL_SHA,
                  "mutation": mutation, "changed_members": changes, "binding_iterations": iteration + 1,
                  "expected_code": {"bad-resource": "RESOURCE_INVALID", "stale-check": "STALE_CHECK", "unknown-version": "UNSUPPORTED_VERSION"}[variant],
                  "expected_layer": {"bad-resource": "RESOURCE", "stale-check": "CURRENT_BINDING", "unknown-version": "VERSION"}[variant]}
        (dest / (variant + "-recipe.json")).write_bytes(encoded(result))
        results.append(result)
    (dest / "variants.json").write_bytes(encoded(results))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("destination")
    args = parser.parse_args()
    print(json.dumps(make_variants(args.source, args.destination), ensure_ascii=False, sort_keys=True))
