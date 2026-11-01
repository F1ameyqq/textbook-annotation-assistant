"""Static verification of the fixed Q1 source-review candidate; never grants PASS."""
from pathlib import Path
from io import BytesIO
import argparse
import hashlib
import json
import zipfile
from PIL import Image


def sha(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def pointer(value, path):
    for token in path.lstrip("/").split("/") if path else []:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def verify(folder, base_package):
    root = Path(folder)
    read = lambda name: json.loads((root / name).read_bytes())
    binding = read("base-package-binding.json")
    assert sha(Path(base_package).read_bytes()) == binding["sha256"], "wrong original package"
    with zipfile.ZipFile(base_package) as archive:
        assert sha(archive.read("manifest.json")) == binding["manifest_sha256"]
        native = {name: json.loads(archive.read(name)) for name in binding["source_artifacts"]}
        for name, expected in binding["source_artifacts"].items():
            assert sha(archive.read(name)) == expected["file_sha256"]
            assert all(native[name][key] == value for key, value in expected["reference"].items())
        candidate = read("candidate.json")
        assert candidate["kind"] == "QuestionSourceReviewCandidate"
        assert candidate["schema_version"] == "b-question-source-review-trial/0.1"
        assert candidate["revision"] == 1
        p = candidate["payload"]
        assert sha(canonical(p)) == candidate["content_hash"], "candidate payload changed"
        assert candidate["artifact_id"] == "b-q1-source-review-"+candidate["content_hash"][:24]
        assert candidate["input_refs"] == [binding["source_artifacts"][name]["reference"] for name in (
            "artifacts/evidence.json", "artifacts/graph.json", "artifacts/check.json")]
        assert p["decision"] == "HOLD" and not any(p[k] for k in (
            "business_acceptance", "human_verified", "production_applied", "a_accepted", "platform_actions"))
        selection = read("native-selection.json")
        assert sha((root / "native-selection.json").read_bytes()) == binding["native_selection_sha256"]
        graph = native["artifacts/graph.json"]
        q = next(x for x in graph["payload"]["questions"] if x["question_id"] == p["question_id"])
        a = next(x for x in graph["payload"]["answers"] if x["answer_id"] == p["answer_id"])
        assert q == selection["native_question_snapshot"] and a == selection["native_answer_snapshot"]
        assert candidate["book_id"] == q["book_id"] == "46007447"
        assert candidate["scope_id"] == "single-question/"+q["question_id"]
        assert q["selected_answer_id"] == a["answer_id"]
        assert q["printed_number"] == "1" and q["section_path"] == a["section_path"]
        source_images = {}
        for asset in p["sources"]:
            data = (root / asset["path"]).read_bytes()
            assert data == archive.read(asset["source_package_path"])
            assert sha(data) == asset["sha256"]
            im = Image.open(BytesIO(data)).convert("RGB")
            assert list(im.size) == [asset["width"], asset["height"]]
            source_images[asset["asset_id"]] = im
        by_id = {r["region_id"]: r for r in p["regions"]}
        assert len(by_id) == len(p["regions"])
        by_key = {r["key"]: r for r in p["regions"]}
        assert len(by_key) == len(p["regions"])
        for region in p["regions"]:
            source = source_images[region["asset_id"]]
            x0, y0, x1, y1 = region["bbox"]
            assert 0 <= x0 < x1 <= source.width and 0 <= y0 < y1 <= source.height
            assert list(source.size) == region["source_size"]
            assert next(x["sha256"] for x in p["sources"] if x["asset_id"] == region["asset_id"]) == region["source_sha256"]
            receipt = region["crop"]
            assert receipt["crop_to_original"] == [[1, 0, x0], [0, 1, y0], [0, 0, 1]]
            data = (root / receipt["path"]).read_bytes()
            assert sha(data) == receipt["sha256"]
            crop = Image.open(BytesIO(data)).convert("RGB")
            assert list(crop.size) == receipt["size"] == [x1-x0, y1-y0]
            assert crop.tobytes() == source.crop(region["bbox"]).tobytes(), "crop pixels or transform changed"
            assert sha(crop.tobytes()) == receipt["rgb_sha256"]
            assert region["human_verified"] is False and region["platform_region"] is False
        primary = [by_id[rid] for rid in p["proposed_semantic_region_ids"]]
        assert [x["role"] for x in primary] == ["stem", "option", "option", "option", "option", "answer"]
        assert all(not x["context_only"] for x in primary)
        for i, left in enumerate(primary):
            for right in primary[i+1:]:
                assert left["asset_id"] != right["asset_id"] or not overlap(left["bbox"], right["bbox"])
        stem, response = primary[0], by_key["response-parentheses"]
        assert stem["bbox"][0] <= response["bbox"][0] < response["bbox"][2] <= stem["bbox"][2]
        assert stem["bbox"][1] <= response["bbox"][1] < response["bbox"][3] <= stem["bbox"][3]
        assert response["source_fragment_ids"] == [] and response["region_id"] not in p["proposed_semantic_region_ids"]
        assert not overlap(primary[-1]["bbox"], by_key["answer-number-context"]["bbox"])
        assert not overlap(primary[-1]["bbox"], by_key["answer-next-item-context"]["bbox"])
        mapped = [fid for region in primary for fid in region["source_fragment_ids"]]
        assert len(mapped) == len(set(mapped)) == 7
        assert set(mapped) == {f["fragment_id"] for f in q["fragments"]+a["fragments"]}
        content = p["candidate_content"]
        assert content["stem_with_number_and_source_linebreaks"] == "\n".join(f["text"] for f in q["fragments"][:2])+"\n（　　）"
        body = q["fragments"][0]["text"][2:]+q["fragments"][1]["text"]+"（　　）"
        assert content["stem_body_normalized_without_number"] == body
        lo, hi = content["response_output_span"]
        assert body[lo:hi] == response["text"] == "（　　）"
        assert content["option_texts"] == [f["text"] for f in q["fragments"][2:]]
        assert [r["text"] for r in primary[1:5]] == content["option_texts"]
        assert stem["text"] == content["stem_with_number_and_source_linebreaks"]
        assert content["answer_text"] == a["text"] == "D"
        assert primary[-1]["text"] == "D" and primary[-1]["asset_id"] == a["asset_id"]
        assert content["explanation_text"] == "" and content["explanation_present"] is False
        mapping = p["source_mapping"]["answer"]
        lo, hi = mapping["source_text_span"]
        assert mapping["raw_text"][lo:hi] == "D" and mapping["old_bbox"] == a["bbox"]
        assert p["relation_review"]["human_approved"] is False
        scope = read(p["scope_applicability_file"])
        old = native["artifacts/check.json"]["payload"]["issues"]
        expected = {i["issue_id"] for i in old if i["scope_type"] == "scope"}
        assert len(scope["dispositions"]) == 31 and {i["issue_id"] for i in scope["dispositions"]} == expected
        cache = dict(native)
        for d in scope["dispositions"]:
            name, path = d["original_issue_pointer"].split("#")
            original = pointer(cache[name], path)
            assert original["issue_id"] == d["issue_id"] and original["code"] == d["code"]
            assert not d["a_confirmed"] and not d["original_issue_removed"]
            for proof in d["proof"]:
                name, path = proof["pointer"].split("#")
                if name not in cache:
                    cache[name] = json.loads(archive.read(name))
                assert pointer(cache[name], path) == proof["value"], "scope proof differs from original"
                value = proof["value"]
                if "bbox" in value:
                    assert all(r["asset_id"] != proof["asset_id"] or not overlap(value["bbox"], r["bbox"]) for r in primary)
                if "source_regions" in value:
                    assert all(not overlap(v["bbox"], primary[-1]["bbox"]) for v in value["source_regions"])
                if "affected_answer_ids" in value:
                    assert a["answer_id"] not in value["affected_answer_ids"]
        assert sum(d["proposed_applicability"] == "APPLICABLE_REMAINS_HOLD" for d in scope["dispositions"]) == 1
    return {"decision": "HOLD", "validation": "STATIC_SOURCE_BYTES_GEOMETRY_MAPPING_ONLY",
            "source_images": 2, "crop_pixel_and_transform_checks": len(by_id),
            "native_fragments_accounted_for": len(mapped), "semantic_region_proposals": len(primary),
            "scope_issues_traced": 31, "original_scope_issues_removed": 0,
            "original_question_graph_changed": False, "new_model_calls": 0,
            "platform_actions": 0, "human_acceptance": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_directory")
    parser.add_argument("--base-package", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = verify(args.candidate_directory, args.base_package)
    data = json.dumps(result, ensure_ascii=False, indent=2)+"\n"
    if args.output:
        Path(args.output).write_bytes(data.encode("utf-8"))
    print(data)
