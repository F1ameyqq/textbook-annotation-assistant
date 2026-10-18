"""Read bytes/JSON only; B code and databases are never executed or queried."""
import hashlib
import io
import json
import stat
import struct
import warnings
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from PIL import Image

ORIGINAL_SHA256 = "b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d"
ORIGINAL_MANIFEST_SHA256 = "3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f"
RUN_ID = "pipeline-run-0a2c03e193694ef88953f3ca08b8cde2"
HISTORY_REF = {"artifact_id": "b-evidence-18e2d1ee2a22288f585513f0", "revision": 1,
               "content_hash": "a2e53e1fc5ddee5ed0eaa57102af074a9b20b7815aa065116464446b9be7a8da"}
CURRENT = {"EvidenceBundleTrial": "b-evidence-trial/0.3",
           "QuestionGraphTrial": "b-graph-trial/0.7", "CheckReportTrial": "b-check-trial/0.7"}


class HandoffError(ValueError):
    def __init__(self, code, path, message, layer):
        self.code, self.path, self.message, self.layer = code, path, message, layer
        super().__init__(f"{code}: {path}: {message}")

    def as_dict(self):
        return {"decision": "REJECTED", "business_acceptance": False,
                "c01_execution_eligible": False, "error": {
                    "code": self.code, "path": self.path, "message": self.message, "layer": self.layer}}


def fail(code, path, message, layer):
    raise HandoffError(code, path, message, layer)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def ref(obj):
    return {key: obj[key] for key in ("artifact_id", "revision", "content_hash") if key in obj}


def ref_key(obj):
    return tuple(sorted(ref(obj).items()))


def walk(obj, path):
    if isinstance(obj, dict):
        yield path, obj
        for key, value in obj.items():
            yield from walk(value, path + "/" + key.replace("~", "~0").replace("/", "~1"))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from walk(value, path + "/" + str(i))


def parse(data, path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                fail("DUPLICATE_JSON_KEY", path, key, "JSON")
            result[key] = value
        return result
    try:
        return json.loads(data.decode("utf-8-sig"), object_pairs_hook=pairs,
                          parse_constant=lambda value: fail("INVALID_JSON", path, value, "JSON"))
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, HandoffError):
            raise
        fail("INVALID_JSON", path, str(exc), "JSON")


def version_policy(schema_version, *, kind, location, bound_archive=False, path="$"):
    """Explicit dispatch only. An archive must be bound by a verified native reference."""
    if kind not in CURRENT or location not in ("CURRENT", "ARCHIVE"):
        fail("UNSUPPORTED_ENTRY_SHAPE", path, f"kind={kind}; location={location}", "VERSION")
    prefix = {"QuestionGraphTrial": "b-graph-trial/", "CheckReportTrial": "b-check-trial/"}.get(kind)
    if prefix and schema_version in (prefix + "0.4", prefix + "0.5"):
        if location == "CURRENT":
            fail("ARCHIVE_ONLY_NOT_CURRENT", path, schema_version, "VERSION")
        if not bound_archive:
            fail("UNBOUND_ARCHIVE", path, schema_version, "VERSION")
        return "ARCHIVE_ONLY"
    if schema_version != CURRENT[kind] or location != "CURRENT":
        fail("UNSUPPORTED_VERSION", path, str(schema_version), "VERSION")
    return "READ_ONLY_HOLD"


def safe_member(name, path):
    if (not isinstance(name, str) or not name or "\\" in name or ":" in name or
            any(ord(c) < 32 for c in name) or name.startswith("/") or
            any(p in ("", ".", "..") for p in name.split("/")) or PurePosixPath(name).is_absolute()):
        fail("UNSAFE_MEMBER_PATH", path, repr(name), "PACKAGE")
    return name


def zip_members(data, path):
    """No extraction, filesystem joins, symlink following or execution."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > 512 or sum(i.file_size for i in infos) > 128 * 1024 * 1024:
                fail("PACKAGE_LIMIT", path, "bounded receiver limit exceeded", "PACKAGE")
            result, folded = {}, set()
            for info in infos:
                name = safe_member(info.filename, path)
                if name.casefold() in folded:
                    fail("DUPLICATE_MEMBER", path + "!/" + name, "duplicate/case collision", "PACKAGE")
                folded.add(name.casefold())
                if info.flag_bits & 1 or stat.S_ISLNK(info.external_attr >> 16) or info.is_dir():
                    fail("UNSUPPORTED_MEMBER", path + "!/" + name, "encrypted/link/directory member", "PACKAGE")
                if info.file_size > 32 * 1024 * 1024:
                    fail("PACKAGE_LIMIT", name, "member too large", "PACKAGE")
                result[name] = archive.read(info)
            return result
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        fail("INVALID_ZIP", path, str(exc), "PACKAGE")


def decode_image(data, path):
    try:
        # Pillow can accept incomplete PNG scanlines: also check the complete raw stream.
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            offset, packed, header, ended = 8, b"", None, False
            while offset < len(data):
                size = struct.unpack(">I", data[offset:offset + 4])[0]
                tag = data[offset + 4:offset + 8]
                body = data[offset + 8:offset + 8 + size]
                crc = data[offset + 8 + size:offset + 12 + size]
                if len(body) != size or len(crc) != 4 or zlib.crc32(tag + body) & 0xffffffff != struct.unpack(">I", crc)[0]:
                    raise ValueError("incomplete chunk or invalid CRC")
                if tag == b"IHDR":
                    header = struct.unpack(">IIBBBBB", body)
                if tag == b"IDAT":
                    packed += body
                offset += size + 12
                if tag == b"IEND":
                    ended = offset == len(data)
                    break
            if not ended or header is None:
                raise ValueError("missing final IEND/IHDR")
            width, height, depth, color, compression, filtering, interlace = header
            if interlace or color not in (0, 2, 3, 4, 6) or compression or filtering:
                raise ValueError("unsupported PNG encoding in bounded reader")
            stride = (width * {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color] * depth + 7) // 8 + 1
            expected = stride * height
            if expected > 64 * 1024 * 1024:
                raise ValueError("PNG pixel limit")
            decoder = zlib.decompressobj()
            pixels = decoder.decompress(packed, expected + 1)
            if (len(pixels) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail or
                    any(pixels[i] > 4 for i in range(0, expected, stride))):
                raise ValueError("incomplete/extra PNG scanlines or invalid filters")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                if image.width * image.height > 16 * 1024 * 1024:
                    raise ValueError("image pixel limit")
                image.load()
                return image.convert("RGB").copy()
    except Exception as exc:
        fail("RESOURCE_INVALID", path, str(exc), "RESOURCE")


@dataclass
class ReceivedHandoff:
    receipt: dict
    documents: dict
    # These are unchanged native JSON values, including every archived/unknown field.
    # They are evidence for inspection, not converted C01 envelopes.


def receive_package(package_path, *, expected_sha256, expected_manifest_sha256=None):
    try:
        return _receive_package(package_path, expected_sha256=expected_sha256,
                                expected_manifest_sha256=expected_manifest_sha256)
    except HandoffError:
        raise
    except (KeyError, TypeError, IndexError, AttributeError, ValueError, RecursionError) as exc:
        fail("UNSUPPORTED_ENTRY_SHAPE", "$", str(exc), "SHAPE")


def _receive_package(package_path, *, expected_sha256, expected_manifest_sha256=None):
    """Read one explicitly pinned ZIP; return diagnostics or raise HandoffError.

    expected_sha256 is mandatory, including for TEST_VARIANT inputs. No implicit
    install, network lookup, file write, model call, platform or SQLite operation.
    """
    path = Path(package_path)
    try:
        if path.stat().st_size > 64 * 1024 * 1024:
            fail("PACKAGE_LIMIT", str(path), "compressed package too large", "PACKAGE")
        data = path.read_bytes()
    except OSError as exc:
        fail("INPUT_UNAVAILABLE", str(path), str(exc), "PACKAGE")
    digest = sha(data)
    if digest != expected_sha256:
        fail("PACKAGE_SHA_MISMATCH", str(path), f"expected {expected_sha256}; observed {digest}", "PACKAGE")
    files = zip_members(data, str(path))
    if "manifest.json" not in files:
        fail("MISSING_MANIFEST", "manifest.json", "required", "PACKAGE")
    manifest_sha = sha(files["manifest.json"])
    if expected_manifest_sha256 is not None and manifest_sha != expected_manifest_sha256:
        fail("MANIFEST_SHA_MISMATCH", "manifest.json", manifest_sha, "PACKAGE")
    manifest = parse(files["manifest.json"], "manifest.json")
    if manifest.get("schema_version") != "b-handoff-package-trial/0.1":
        fail("UNSUPPORTED_VERSION", "manifest.json#/schema_version", str(manifest.get("schema_version")), "VERSION")
    if manifest.get("run_id") != RUN_ID or manifest.get("book_id") != "46007447":
        fail("UNSUPPORTED_INPUT_IDENTITY", "manifest.json", "only fixed A06 run/book is registered", "PACKAGE")
    listed = set()
    for i, row in enumerate(manifest.get("files", [])):
        name = safe_member(row["path"], f"manifest.json#/files/{i}/path")
        if name in listed:
            fail("DUPLICATE_MANIFEST_ENTRY", name, "duplicate", "PACKAGE")
        listed.add(name)
        if name not in files or len(files[name]) != row["bytes"] or sha(files[name]) != row["sha256"]:
            fail("MEMBER_MISMATCH", name, "missing/length/SHA mismatch", "PACKAGE")
    if set(files) != listed | {"manifest.json"}:
        fail("MEMBER_SET_MISMATCH", "manifest.json#/files", "manifest must enumerate every other member", "PACKAGE")

    documents = {n: parse(b, n) for n, b in files.items() if n.endswith(".json") and n != "manifest.json"}
    required = ["artifacts/" + n + ".json" for n in ("evidence", "graph", "check", "pipeline-report")]
    for name in required + ["inputs/source.json", "inputs/inline-package.json"]:
        if name not in documents:
            fail("MISSING_DOCUMENT", name, "required entry", "PACKAGE")
    evidence, graph, check, report = (documents[n] for n in required)
    for obj, name in zip((evidence, graph, check), required):
        version_policy(obj.get("schema_version"), kind=obj.get("kind"), location="CURRENT", path=name + "#/schema_version")
        if obj.get("book_id") != manifest["book_id"] or obj.get("scope_id") != manifest["scope_id"] + "+adjacent-resource-173-prefix":
            fail("CURRENT_SCOPE_MISMATCH", name, "fixed book/adjacent-prefix scope differs", "CURRENT_BINDING")
    # Validate the declared nested members without opening the SQLite database.
    inner = zip_members(files["inputs/inline-observed.zip"], "inputs/inline-observed.zip")
    inline = documents["inputs/inline-package.json"]
    for name, declaration in inline["members"].items():
        safe_member(name, "inputs/inline-package.json#/members")
        if name not in inner or len(inner[name]) != declaration["bytes"] or sha(inner[name]) != declaration["sha256"]:
            fail("MEMBER_MISMATCH", "inputs/inline-observed.zip!/" + name, "declared consumed member mismatch", "PACKAGE")
    for row in inline["documents"].values():
        if row["path"] not in inline["members"] or sha(inner[row["path"]]) != row["sha256"]:
            fail("MEMBER_MISMATCH", row["path"], "inline document binding", "PACKAGE")
    all_bytes = dict(files)
    for name, blob in inner.items():
        location = "inputs/inline-observed.zip!/" + name
        all_bytes[location] = blob
        if name.endswith(".json"):
            documents[location] = parse(blob, location)

    objects, values, references, nodes = {}, {}, [], []
    for name, doc in documents.items():
        for location, obj in walk(doc, name + "#"):
            nodes.append((location, obj))
            if "artifact_id" in obj:
                if "payload" in obj and "content_hash" in obj:
                    if sha(canonical(obj["payload"])) != obj["content_hash"]:
                        fail("CONTENT_HASH_MISMATCH", location + "/content_hash", "B canonical payload SHA mismatch", "OBJECT")
                    objects.setdefault(ref_key(obj), []).append(location)
                else:
                    values.setdefault((obj["artifact_id"], sha(canonical(obj))), []).append(location)
            for i, item in enumerate(obj.get("input_refs", [])):
                references.append((location + "/input_refs/" + str(i), item))

    def exact(expected, actual, location, code="REFERENCE_MISMATCH"):
        if expected != ref(actual):
            fail(code, location, f"expected {expected}; observed {ref(actual)}", "CURRENT_BINDING")

    # Check current relation first, independently of any archived Check or core proof.
    exact(check["payload"]["graph_ref"], graph, "artifacts/check.json#/payload/graph_ref", "STALE_CHECK")
    exact(check["payload"]["evidence_ref"], evidence, "artifacts/check.json#/payload/evidence_ref")
    if ref(graph) not in check["input_refs"] or ref(evidence) not in graph["input_refs"] or ref(evidence) not in check["input_refs"]:
        fail("CURRENT_INPUT_MISMATCH", "artifacts/", "current E/G/Check input_refs differ", "CURRENT_BINDING")
    if report.get("schema_version") != "b-pipeline-report-trial/0.1" or report.get("kind") != "PipelineReportTrial":
        fail("UNSUPPORTED_VERSION", "artifacts/pipeline-report.json", str(report.get("schema_version")), "VERSION")
    exact(manifest["report_ref"], report, "manifest.json#/report_ref")
    if report.get("run_id") != RUN_ID or report["payload"].get("run_id") != RUN_ID or report.get("scope_id") != manifest["scope_id"]:
        fail("RUN_BINDING_MISMATCH", "artifacts/pipeline-report.json", "report/manifest run/scope differs", "CURRENT_BINDING")
    finals = {"evidence_ref": evidence, "graph_ref": graph, "quality_ref": check}
    for key, obj in finals.items():
        exact(manifest["final_outputs"][key], obj, "manifest.json#/final_outputs/" + key)
        exact(report["payload"]["final_outputs"][key], obj, "artifacts/pipeline-report.json#/payload/final_outputs/" + key)
    stage_bindings, bound_results = [], set()
    stages = report["payload"]["stages"]
    if report["payload"].get("pipeline_state") != "READY" or len(stages) != 14 or len({s["stage_id"] for s in stages}) != 14:
        fail("INCOMPLETE_PIPELINE", "artifacts/pipeline-report.json#/payload/stages", "expected fixed 14-stage READY pipeline", "CURRENT_BINDING")
    for i, stage in enumerate(stages):
        loc = f"artifacts/pipeline-report.json#/payload/stages/{i}"
        output = stage["output"]
        name = safe_member(output["path"], loc + "/output/path")
        if name not in files or sha(files[name]) != output["sha256"]:
            fail("WRAPPER_FILE_MISMATCH", loc + "/output", name, "CURRENT_BINDING")
        wrapper = documents[name]
        if wrapper.get("schema_version") != "b-pipeline-stage-trial/0.1" or wrapper.get("kind") != "PipelineStageTrial":
            fail("UNSUPPORTED_VERSION", name, str(wrapper.get("schema_version")), "VERSION")
        exact(output["artifact_ref"], wrapper, loc + "/output/artifact_ref")
        result = wrapper["payload"]["result"]
        exact(stage["result_ref"], result, loc + "/result_ref")
        if (stage["state"] != "DONE" or stage["current_run_receipt"]["run_id"] != RUN_ID or
                wrapper["payload"]["stage_id"] != stage["stage_id"] or wrapper.get("book_id") != "46007447" or
                wrapper.get("scope_id") != manifest["scope_id"]):
            fail("STAGE_BINDING_MISMATCH", loc, "stage state/run/book/scope mismatch", "CURRENT_BINDING")
        final_routes = {"continuation_prepare": ("evidence_ref", ("payload", "evidence")),
                        "content_apply": ("graph_ref", ("payload", "graph")),
                        "content_quality": ("quality_ref", ())}
        final_route = None
        if stage["stage_id"] in final_routes:
            key, route = final_routes[stage["stage_id"]]
            final = result
            for field in route:
                final = final[field]
            if final != finals[key]:
                fail("RESULT_IDENTITY_MISMATCH", name + "#/payload/result/" + "/".join(route),
                     "exact final envelope differs from current artifact", "CURRENT_BINDING")
            bound_results.add(key)
            final_route = {"final_output": key, "path": name + "#/payload/result" + ("/" + "/".join(route) if route else "")}
        stage_bindings.append({"stage_id": stage["stage_id"], "wrapper_path": name,
                               "wrapper_ref": ref(wrapper), "result_ref": ref(result),
                               "run_receipt": stage["current_run_receipt"], "final_route": final_route})
    if bound_results != set(finals):
        fail("UNBOUND_FINAL_OUTPUT", "artifacts/pipeline-report.json", str(sorted(bound_results)), "CURRENT_BINDING")

    from .views import consume_current, archive_views
    archives = archive_views(nodes)
    # Decode every supplied image, and bind actual source/crop declarations by SHA.
    byte_index, images = {}, {}
    for name, blob in all_bytes.items():
        byte_index.setdefault(sha(blob), []).append(name)
        if name.lower().endswith((".png", ".jpg", ".jpeg")):
            images[name] = decode_image(blob, name)
    assets = {}
    for i, page in enumerate(evidence["payload"]["pages"]):
        source = page["source"]
        candidates = [n for n in byte_index.get(source["sha256"], []) if n in images]
        if not candidates or any(images[n].size != (source["width"], source["height"]) for n in candidates):
            fail("RESOURCE_IDENTITY_MISMATCH", f"artifacts/evidence.json#/payload/pages/{i}/source", "source SHA/size not decoded", "RESOURCE")
        if page["asset_id"] != source["asset_id"] or source["asset_id"] in assets:
            fail("RESOURCE_IDENTITY_MISMATCH", f"artifacts/evidence.json#/payload/pages/{i}", "duplicate/inconsistent asset identity", "RESOURCE")
        assets[source["asset_id"]] = {**source, "resolved_paths": candidates}
    for source in documents["inputs/source.json"]["assets"]:
        if source["asset_id"] not in assets or any(source[k] != assets[source["asset_id"]][k] for k in ("sha256", "width", "height", "path")):
            fail("RESOURCE_IDENTITY_MISMATCH", "inputs/source.json", source["asset_id"], "RESOURCE")
    crop_checks = set()
    for location, obj in nodes:
        if all(k in obj for k in ("file_sha256", "crop_size", "source_sha256", "crop_bbox")):
            key = (obj["file_sha256"], obj["source_sha256"], tuple(obj["crop_bbox"]))
            if key in crop_checks:
                continue
            crop_checks.add(key)
            crop_paths = [n for n in byte_index.get(obj["file_sha256"], []) if n in images]
            source_paths = [n for n in byte_index.get(obj["source_sha256"], []) if n in images]
            if not crop_paths or not source_paths or images[crop_paths[0]].size != tuple(obj["crop_size"]):
                fail("CROP_IDENTITY_MISMATCH", location, "crop/source SHA/size missing", "RESOURCE")
            crop, source_image = images[crop_paths[0]], images[source_paths[0]]
            box = obj["crop_bbox"]
            if (len(box) != 4 or not 0 <= box[0] < box[2] <= source_image.width or
                    not 0 <= box[1] < box[3] <= source_image.height):
                fail("CROP_GEOMETRY_MISMATCH", location, "crop outside source", "RESOURCE")
            for field, observed in (("crop_rgb_sha256", sha(crop.tobytes())),
                                    ("source_crop_rgb_sha256", sha(source_image.crop(tuple(box)).tobytes()))):
                if field in obj and obj[field] != observed:
                    fail("CROP_IDENTITY_MISMATCH", location + "/" + field, observed, "RESOURCE")
    for row in manifest["receipt_files"] + [manifest["adjacent_source"]]:
        if row["path"] not in files or sha(files[row["path"]]) != row["sha256"]:
            fail("RESOURCE_IDENTITY_MISMATCH", row["path"], "receipt resource SHA mismatch", "RESOURCE")
    for aid in ("viewer-173", "resource-173"):
        if aid not in assets:
            fail("RESOURCE_IDENTITY_MISMATCH", "artifacts/evidence.json#/payload/pages", aid, "RESOURCE")
    if assets["viewer-173"]["sha256"] == assets["resource-173"]["sha256"]:
        fail("RESOURCE_IDENTITY_MISMATCH", "artifacts/evidence.json#/payload/pages", "distinct 173 assets collapsed", "RESOURCE")
    content = consume_current(graph, check, assets)

    classifications, history_locations = [], []
    for location, item in references:
        classification, resolved = None, []
        if item == HISTORY_REF:
            classification = "UNRESOLVED_HISTORY_REFERENCE"
            history_locations.append(location)
        elif "artifact_id" in item:
            resolved = objects.get(ref_key(item), []) or values.get((item["artifact_id"], item.get("content_hash")), [])
            if resolved:
                classification = "NATIVE_ARTIFACT" if ref_key(item) in objects else "NATIVE_DOCUMENT"
            elif "revision" not in item and item.get("content_hash") in byte_index:
                classification, resolved = "CROP_BYTES", byte_index[item["content_hash"]]
            elif item.get("artifact_id") == "anonymous-source-get-resource-173":
                resolved = [p for p, obj in nodes if p.endswith("/acquisition_receipt") and sha(canonical(obj)) == item["content_hash"]]
                classification = "EMBEDDED_ACQUISITION_RECEIPT" if resolved else None
        elif "asset_id" in item and "sha256" in item:
            if item["asset_id"] in assets and assets[item["asset_id"]]["sha256"] == item["sha256"]:
                classification, resolved = "ASSET_BYTES", assets[item["asset_id"]]["resolved_paths"]
        elif "crop_sha256" in item and item["crop_sha256"] in byte_index:
            classification, resolved = "CROP_BYTES", byte_index[item["crop_sha256"]]
        if not classification:
            fail("UNSUPPORTED_REFERENCE", location, json.dumps(item, ensure_ascii=False), "REFERENCE")
        classifications.append({"path": location, "reference": item, "classification": classification, "resolved_paths": resolved})
    if not history_locations:
        fail("UNSUPPORTED_INPUT_IDENTITY", "input_refs", "fixed historical gap missing", "REFERENCE")
    for obj, name in ((report, "pipeline-report"), (graph, "graph"), (check, "check")):
        if obj["payload"].get("decision") != "HOLD" or obj["payload"].get("business_acceptance") is not False or obj["payload"].get("transcription_verified") is not False:
            fail("UNSUPPORTED_BUSINESS_STATE", "artifacts/" + name + ".json#/payload", "fixed draft HOLD state required", "DIAGNOSTIC")
    counts = {"question_candidates": len(graph["payload"]["questions"]),
              "answer_candidates": len(graph["payload"]["answers"]), "current_check_issues": len(check["payload"]["issues"])}
    if list(counts.values()) != [34, 66, 127]:
        fail("UNSUPPORTED_INPUT_IDENTITY", "artifacts/", str(counts), "DIAGNOSTIC")
    receipt = {"receiver_version": "a06-native-diagnostic/0.1", "decision": "HOLD",
               "business_acceptance": False, "c01_execution_eligible": False,
               "transcription_verified": False, "joint_mapping_confirmed": False,
               "semantic_closure": "UNCONFIRMED_REQUIREDNESS", "counts": counts,
               "input": {"sha256": digest, "bytes": len(data), "manifest_sha256": manifest_sha,
                         "identity": "ORIGINAL_B_PACKAGE" if digest == ORIGINAL_SHA256 else "TEST_VARIANT",
                         "run_id": RUN_ID, "book_id": manifest["book_id"]},
               "versions": {name: obj["schema_version"] for name, obj in zip(required, (evidence, graph, check, report))},
               "scopes": {"package": manifest["scope_id"], "source": documents["inputs/source.json"]["scope_id"],
                          **{name: {"scope_id": obj.get("scope_id"), "run_id": obj.get("run_id")}
                             for name, obj in zip(required, (evidence, graph, check, report))}},
               "pipeline": {"state": report["payload"]["pipeline_state"], "run_binding": "CURRENT_RUN_RECEIPT_AND_EXACT_WRAPPER_RESULT", "stages": stage_bindings},
               "integrity": {"outer_members": len(files), "manifest_files": len(listed),
                             "inner_members": len(inner), "inner_declared_consumed": len(inline["members"]),
                             "unique_payload_identities": len(objects), "decoded_images": len(images), "crop_checks": len(crop_checks)},
               "history_gap": {"reference": HISTORY_REF, "statuses": ["UNRESOLVED_HISTORY_REFERENCE", "UNCONFIRMED_REQUIREDNESS"],
                               "locations": history_locations, "requiredness": "UNCONFIRMED", "optional": None},
               "assets": assets, "archives": archives, "references": classifications,
               "content": content, "issues": check["payload"]["issues"],
               "limitations": ["FIXED_RUN_ONLY", "NATIVE_DIAGNOSTIC_NOT_C01", "UNCONFIRMED_SHARED_MAPPING",
                               "NO_CONTENT_OR_COVERAGE_ACCEPTANCE", "NO_EXECUTION_OR_PLATFORM_QUALIFICATION",
                               "SQLITE_AND_SCRIPTS_BYTES_ONLY", "UNKNOWN_FIELDS_PRESERVED_IN_DOCUMENTS_NOT_INTERPRETED",
                               "G06_CHECK06_NO_COMPLETE_POSITIVE_SAMPLE", "NO_JOINT_BUSINESS_ACCEPTANCE"],
               "native_document_paths": sorted(documents)}
    return ReceivedHandoff(receipt, documents)
