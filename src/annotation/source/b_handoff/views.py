"""Views retain native fields and explicit layers, without projecting platform boxes."""
import math

from .reader import fail, ref, version_policy, walk, sha


def archive_views(nodes):
    views = []
    index = dict(nodes)
    for location, obj in nodes:
        version = obj.get("schema_version")
        if version not in ("b-graph-trial/0.4", "b-graph-trial/0.5", "b-check-trial/0.4", "b-check-trial/0.5"):
            continue
        # Only actual *_archive payload children with an exact sibling ref bind as archives.
        if not location.endswith("_archive"):
            continue
        parent_path, key = location.rsplit("/", 1)
        parent = index.get(parent_path, {})
        binding_path = parent_path + "/" + key[:-8] + "_ref"
        bound = parent.get(key[:-8] + "_ref") == ref(obj)
        if not bound and key == "base_check_archive" and parent.get("inline_basis", {}).get("base_check_ref") == ref(obj):
            envelope = index.get(parent_path[:-8], {}) if parent_path.endswith("/payload") else {}
            bound = ref(obj) in envelope.get("input_refs", [])
            binding_path = parent_path + "/inline_basis/base_check_ref"
        policy = version_policy(version, kind=obj.get("kind"), location="ARCHIVE", bound_archive=bound, path=location)
        views.append({"path": location, "reference": ref(obj), "schema_version": version, "disposition": policy,
                      "binding_path": binding_path,
                      "preservation": "UNCHANGED_NATIVE_JSON_IN_DOCUMENTS", "business_acceptance": False,
                      "semantic_interpretation": "ARCHIVE_FIELDS_AND_CANDIDATES_ONLY_NOT_CURRENT_VALIDATION",
                      "payload_fields": sorted(obj["payload"]),
                      "candidate_risk_core_paths": [p for p, value in walk(obj["payload"], location + "/payload")
                                                    if any(word in p.rsplit("/", 1)[-1] for word in ("candidate", "risk", "core", "basis"))][:80],
                      "native_value": {"document": location.split("#", 1)[0], "pointer": location.split("#", 1)[1]}})
    return views


def consume_current(graph, check, assets):
    def box(obj, path):
        if "bbox" not in obj:
            return
        aid, bounds = obj.get("asset_id"), obj["bbox"]
        if aid not in assets or len(bounds) != 4 or any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in bounds):
            fail("INVALID_REGION", path, "unknown asset or invalid coordinates", "CONTENT")
        asset = assets[aid]
        if not (0 <= bounds[0] < bounds[2] <= asset["width"] and 0 <= bounds[1] < bounds[3] <= asset["height"]):
            fail("INVALID_REGION", path, "outside source dimensions", "CONTENT")
        if "source_sha256" in obj and obj["source_sha256"] != asset["sha256"]:
            fail("INVALID_REGION", path, "source SHA mismatch", "CONTENT")
        if "source_size" in obj and obj["source_size"] != [asset["width"], asset["height"]]:
            fail("INVALID_REGION", path, "source size mismatch", "CONTENT")

    entities, drafts, spans = [], [], []
    for group, identity in (("questions", "question_id"), ("answers", "answer_id")):
        for i, entity in enumerate(graph["payload"][group]):
            path = f"artifacts/graph.json#/payload/{group}/{i}"
            # Preserve all original entity fields. Layer views are pointers, not replacements.
            source_fragments = {f["fragment_id"]: f for f in entity.get("fragments", [])}
            content_fragments = {f["content_fragment_id"]: f for f in entity.get("content_fragments", [])}
            if len(source_fragments) != len(entity.get("fragments", [])) or len(content_fragments) != len(entity.get("content_fragments", [])):
                fail("DUPLICATE_FRAGMENT_ID", path, "duplicate source/content fragment", "CONTENT")
            for j, fragment in enumerate(entity.get("content_fragments", [])):
                fp = path + "/content_fragments/" + str(j)
                box(fragment, fp)
                if "source_region" in fragment:
                    box(fragment["source_region"], fp + "/source_region")
                if fragment.get("kind") == "REGION_DRAFT":
                    if not fragment.get("source_region"):
                        fail("INVALID_REGION_DRAFT", fp, "REGION_DRAFT needs source_region", "CONTENT")
                    drafts.append({"path": fp, "id": fragment["content_fragment_id"],
                                   "source_fragment_ids": fragment.get("source_fragment_ids", []),
                                   "source_region": fragment["source_region"], "preserved": True})
                for run in fragment.get("runs", []):
                    if run.get("format") not in ("plain", "latex") or not isinstance(run.get("text"), str):
                        fail("UNSUPPORTED_CONTENT_RUN", fp + "/runs", str(run), "CONTENT")
                if "runs" in fragment and "".join(r["text"] for r in fragment["runs"]) != fragment["text"]:
                    fail("CONTENT_RUN_MISMATCH", fp, "runs do not reconstruct current text", "CONTENT")
                text = fragment.get("text", "")
                source_fragment = None
                if "source_fragment_id" in fragment:
                    source_fragment = source_fragments.get(fragment["source_fragment_id"])
                    if source_fragment is None or sha(source_fragment["text"].encode("utf-8")) != fragment.get("source_fragment_text_sha256"):
                        fail("CONTENT_SOURCE_MISMATCH", fp, "source fragment identity/text SHA mismatch", "CONTENT")
                    if "source_text_span" in fragment and fragment["source_text_span"] != source_fragment.get("text_span"):
                        fail("CHARACTER_SPAN_MISMATCH", fp + "/source_text_span", "source span differs", "CONTENT")
                for k, piece in enumerate(fragment.get("pieces", [])):
                    a, b = piece["output_span"]
                    if not (0 <= a <= b <= len(text)) or text[a:b] != piece["text"]:
                        fail("CHARACTER_SPAN_MISMATCH", fp + "/pieces/" + str(k), "Unicode code-point half-open span mismatch", "CONTENT")
                    spans.append({"path": fp + "/pieces/" + str(k), "output_span": [a, b], "text": text[a:b]})
                    if source_fragment is not None:
                        sa, sb = piece["source_fragment_span"]
                        source_text = source_fragment["text"]
                        if not (0 <= sa <= sb <= len(source_text)) or (piece.get("kind") == "SOURCE" and source_text[sa:sb] != piece["text"]):
                            fail("CHARACTER_SPAN_MISMATCH", fp + "/pieces/" + str(k), "source code-point span mismatch", "CONTENT")
            for field in ("fragments", "regions", "render_regions"):
                for j, region in enumerate(entity.get(field, [])):
                    rp = path + "/" + field + "/" + str(j)
                    box(region, rp)
                    if field == "render_regions" and region.get("content_type") not in ("text", "formula", "image", "table"):
                        fail("UNSUPPORTED_REGION_TYPE", rp, str(region.get("content_type")), "CONTENT")
                    for fid in region.get("content_fragment_ids", []):
                        if fid not in content_fragments:
                            fail("CONTENT_FRAGMENT_UNRESOLVED", rp + "/content_fragment_ids", fid, "CONTENT")
            entities.append({"id": entity[identity], "group": group, "path": path, "native": entity,
                             "layers": {k: path + "/" + k for k in ("fragments", "content_fragments", "regions", "render_regions") if k in entity}})
    return {"entities": entities, "region_drafts": drafts, "character_spans": spans,
            "span_convention": "UNICODE_CODE_POINTS_LEFT_CLOSED_RIGHT_OPEN",
            "unselected_history": "PRESERVED_IN_NATIVE_ARCHIVES_AND_INLINE_CONTENT_CANDIDATES",
            "platform_box_count": None, "unknown_fields": "PRESERVED_UNINTERPRETED_IN_NATIVE_VALUES",
            "check_source_layer_proof": check["payload"].get("source_layer_proof"),
            "check_review_basis": check["payload"].get("review_basis")}
