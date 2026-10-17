"""Frozen source-bound region candidates for the local draft review editor.

Catalog validation replays existing observations, never models or a reference
transcription. Candidate provenance does not establish character ownership or
content correctness. A plain exported revision plan preserves selection notes;
it does not independently revalidate this optional frozen workspace catalog.
"""
from __future__ import annotations

import base64
import binascii
from collections import OrderedDict
import copy
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import tempfile
import threading

from PIL import Image

from .baseline import code_digest, digest, valid_bbox
from .content_revision import _region, _visible, reference
from .region_draft import build_region_draft

INPUT_SCHEMA = "b-region-review-inputs-trial/0.1"
CATALOG_SCHEMA = "b-region-review-catalog-trial/0.1"
_CAPSULE = {"answer_id", "draft", "crop_png_base64"}
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_CACHE = OrderedDict()
_CACHE_LOCK = threading.RLock()


def _same(left, right):
    return digest(left) == digest(right)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _ref(value):
    return (isinstance(value, dict) and set(value) == {"artifact_id", "revision", "content_hash"}
            and _text(value["artifact_id"]) and type(value["revision"]) is int and value["revision"] > 0
            and isinstance(value["content_hash"], str) and bool(_HASH.fullmatch(value["content_hash"])))


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value: raise ValueError("duplicate JSON key: "+key)
        value[key] = item
    return value


def _float(value):
    number = float(value)
    if not math.isfinite(number): raise ValueError("nonfinite JSON number")
    return number


def _constant(value):
    raise ValueError("nonfinite JSON constant: "+value)


def _receipt(receipts, path, raw):
    sha = hashlib.sha256(raw).hexdigest()
    if path in receipts and receipts[path] != sha:
        raise ValueError("catalog member bytes changed between references")
    receipts[path] = sha


def _read(path, receipts):
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_float=_float, parse_constant=_constant)
    except (OSError, UnicodeError) as exc:
        raise ValueError("local region JSON is missing, unreadable or not UTF-8") from exc
    _receipt(receipts, path, raw)
    return value


def _local_path(path):
    raw = str(path)
    drive = PureWindowsPath(raw).drive
    if raw.startswith(("\\\\", "//")) or (_SCHEME.match(raw) and not re.fullmatch(r"[A-Za-z]:", drive)):
        raise ValueError("region catalog accepts local paths, never network or scheme paths")
    return Path(path).resolve()


def _relative(root, value):
    if (not _text(value) or "\\" in value or _SCHEME.match(value) or PurePosixPath(value).is_absolute()
            or PureWindowsPath(value).drive or ".." in PurePosixPath(value).parts):
        raise ValueError("catalog members must use portable local relative paths")
    path = (root/value).resolve()
    if not path.is_relative_to(root): raise ValueError("catalog member escapes its local root")
    return path


def _capsule(value, *, indexed=False):
    if (not isinstance(value, dict) or set(value) not in (_CAPSULE, _CAPSULE|{"source_rows"})
            or not _text(value.get("answer_id")) or not isinstance(value.get("draft"), dict)
            or not isinstance(value.get("crop_png_base64"), str)):
        raise ValueError("region attachment fields are invalid")
    if indexed and "source_rows" not in value: raise ValueError("region options require a source-validated catalog")
    try:
        raw = base64.b64decode(value["crop_png_base64"], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("region crop must use strict canonical base64") from exc
    if base64.b64encode(raw).decode("ascii") != value["crop_png_base64"] or not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("region crop must retain the original PNG bytes")
    if "source_rows" in value:
        if not isinstance(value["source_rows"], dict): raise ValueError("invalid derived source row index")
        all_ids = []
        for rid, row in value["source_rows"].items():
            if (not _text(rid) or not isinstance(row, dict) or set(row) != {"asset_id", "bbox", "role", "source_fragment_ids"}
                    or not _text(row.get("asset_id")) or row.get("role") not in ("answer", "explanation")
                    or not isinstance(row.get("bbox"), list) or len(row["bbox"]) != 4 or any(type(n) is not int for n in row["bbox"])
                    or not isinstance(row.get("source_fragment_ids"), list) or not all(_text(fid) for fid in row["source_fragment_ids"])):
                raise ValueError("invalid derived source row fields")
            all_ids.extend(row["source_fragment_ids"])
        if len(all_ids) != len(set(all_ids)): raise ValueError("source fragments occur in multiple catalog rows")
    return raw


def load_region_catalog(path):
    """Load either path-based inputs or an exported frozen local catalog."""
    path = _local_path(path); receipts = {}; manifest = _read(path, receipts)
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "entries"} or not isinstance(manifest["entries"], list):
        raise ValueError("region catalog manifest has unknown or missing fields")
    result = []
    if manifest["schema_version"] == CATALOG_SCHEMA:
        for capsule in manifest["entries"]:
            _capsule(capsule)
            result.append(copy.deepcopy(capsule))
    elif manifest["schema_version"] == INPUT_SCHEMA:
        for entry in manifest["entries"]:
            if not isinstance(entry, dict) or set(entry) != {"answer_id", "draft", "crop"} or not _text(entry.get("answer_id")):
                raise ValueError("region input entry fields are invalid")
            draft = _read(_relative(path.parent, entry["draft"]), receipts)
            crop_path = _relative(path.parent, entry["crop"])
            try: crop = crop_path.read_bytes()
            except OSError as exc: raise ValueError("local region PNG is missing or unreadable") from exc
            _receipt(receipts, crop_path, crop)
            capsule = dict(answer_id=entry["answer_id"], draft=draft, crop_png_base64=base64.b64encode(crop).decode("ascii"))
            _capsule(capsule); result.append(capsule)
    else:
        raise ValueError("unsupported local region catalog schema")
    for member, sha in receipts.items():
        try: current = hashlib.sha256(member.read_bytes()).hexdigest()
        except OSError as exc: raise ValueError("catalog member disappeared during loading") from exc
        if current != sha: raise ValueError("catalog member bytes changed during loading")
    return result


def _artifact(value, schemas, kind):
    if (not isinstance(value, dict) or value.get("schema_version") not in schemas or value.get("kind") != kind
            or not _ref({k: value.get(k) for k in ("artifact_id", "revision", "content_hash")})
            or not isinstance(value.get("payload"), dict) or value["content_hash"] != digest(value["payload"])):
        raise ValueError("region catalog artifact schema, payload or identity differs")


def _bundle(capsule):
    raw = _capsule(capsule); draft = capsule["draft"]
    _artifact(draft, {"b-region-draft-trial/0.1"}, "RegionDraftTrial")
    if draft["artifact_id"] != "region-draft-"+digest([draft.get("input_refs"), draft.get("producer"), draft["payload"]])[:24]:
        raise ValueError("region draft deterministic identity changed")
    source = draft["payload"]["source"]
    if hashlib.sha256(raw).hexdigest() != source["crop_sha256"]: raise ValueError("region catalog crop SHA differs")
    try:
        with Image.open(io.BytesIO(raw)) as opened:
            if opened.format != "PNG": raise ValueError("catalog crop is not the original PNG")
            crop = opened.convert("RGB")
    except OSError as exc: raise ValueError("region catalog crop is not decodable") from exc
    box = source["crop_bbox"]
    if (crop.size != (box[2]-box[0], box[3]-box[1])
            or hashlib.sha256(crop.tobytes()).hexdigest() != source["crop_rgb_sha256"]):
        raise ValueError("region catalog crop pixels differ")
    # A cache only avoids recomputing the same frozen pure projection. The key
    # includes every archived byte and current replay implementation; it is not
    # a source-file approval token and source JPGs are rechecked separately.
    modules = ("region_review", "region_draft", "region_runs", "region_ocr", "formula_candidates", "formula_canvas",
               "formula_canvas_quality", "formula_quality", "formula_backend", "formula_syntax", "math_reading",
               "recovery_apply", "baseline")
    key = digest([draft, source["crop_sha256"], {n: code_digest(Path(__file__).with_name(n+".py")) for n in modules}])
    with _CACHE_LOCK:
        checked = key in _CACHE
    if not checked:
        archives = draft["payload"]["archives"]
        with tempfile.TemporaryDirectory(prefix="b-region-review-") as folder:
            path = Path(folder)/"crop.png"; path.write_bytes(raw)
            rebuilt = build_region_draft(archives["plan"], archives["observations"], archives["legacy"],
                                         archives["canvas"], archives["roles"], path)
        if not _same(rebuilt, draft): raise ValueError("region draft differs from the complete source observation replay")
        with _CACHE_LOCK:
            _CACHE[key] = True; _CACHE.move_to_end(key)
            while len(_CACHE) > 8: _CACHE.popitem(last=False)
    return draft, crop, raw


def _inside(box, outer):
    return outer[0] <= box[0] < box[2] <= outer[2] and outer[1] <= box[1] < box[3] <= outer[3]


def _overlap(left, right):
    return max(left[0], right[0]) < min(left[2], right[2]) and max(left[1], right[1]) < min(left[3], right[3])


def _source_rows(draft, evidence, graph, answer_id):
    source = draft["payload"]["source"]; answers = [a for a in graph["payload"]["answers"] if a["answer_id"] == answer_id]
    if len(answers) != 1: raise ValueError("catalog answer is missing or ambiguous")
    visible, _ = _visible(answers[0])
    fragments = [f for f in visible if f["asset_id"] == source["asset_id"] and _overlap(f["bbox"], source["crop_bbox"])]
    roles = {f["role"] for f in fragments}
    if not fragments or len(roles) != 1 or any(not _inside(f["bbox"], source["crop_bbox"]) for f in fragments):
        raise ValueError("catalog source region crosses a role or clips its visible source fragments")
    role = next(iter(roles)); result = {}; allocated = []
    for row in draft["payload"]["rows"]:
        if row["row_id"] in result: raise ValueError("duplicate region source row")
        ids = [f["fragment_id"] for f in fragments if _inside(f["bbox"], row["source_bbox"])]
        result[row["row_id"]] = dict(asset_id=source["asset_id"], bbox=copy.deepcopy(row["source_bbox"]), role=role, source_fragment_ids=ids)
        allocated.extend(ids)
    if len(allocated) != len(fragments) or set(allocated) != {f["fragment_id"] for f in fragments}:
        raise ValueError("catalog row boundaries do not uniquely cover current source fragments")
    # Reuse the existing geometry/ledger barrier, not a guessed nearest row.
    _region(evidence, graph, dict(target=dict(answer_id=answer_id, role=role, source_fragment_ids=[f["fragment_id"] for f in fragments]),
        source_region=dict(asset_id=source["asset_id"], source_sha256=source["source_sha256"], source_size=source["source_size"], bbox=source["crop_bbox"]),
        blocks=[dict(bbox=row["bbox"], source_fragment_ids=row["source_fragment_ids"]) for row in result.values()]))
    return result


def validate_region_catalog(attachments, evidence, graph05, source_paths):
    """Rebuild a catalog and bind exact actual sources/current source owners."""
    if not isinstance(attachments, list): raise ValueError("region catalog must be a list")
    if not attachments: return []
    _artifact(evidence, {"b-evidence-trial/0.2", "b-evidence-trial/0.3"}, "EvidenceBundleTrial")
    _artifact(graph05, {"b-graph-trial/0.5"}, "QuestionGraphTrial")
    if ((evidence["book_id"], evidence["scope_id"]) != (graph05["book_id"], graph05["scope_id"])
            or not any(_same(r, reference(evidence)) for r in graph05.get("input_refs", []))
            or not isinstance(source_paths, dict)):
        raise ValueError("region review current graph/source scope differs")
    original = digest(attachments); frozen = copy.deepcopy(attachments); receipts = {}; regions = []
    for capsule in frozen:
        draft, crop, _ = _bundle(capsule); source = draft["payload"]["source"]
        if draft["book_id"] != evidence["book_id"]: raise ValueError("catalog belongs to another book")
        pages = [p for p in evidence["payload"]["pages"] if p["asset_id"] == source["asset_id"]]
        if len(pages) != 1 or source["asset_id"] not in source_paths: raise ValueError("catalog source asset is not available in current evidence")
        page = pages[0]; asset = page["source"]
        if (asset["asset_id"] != source["asset_id"] or asset["sha256"] != source["source_sha256"]
                or not _same([asset["width"], asset["height"]], source["source_size"])
                or not valid_bbox(source["crop_bbox"], asset["width"], asset["height"])):
            raise ValueError("catalog full original identity differs from current evidence")
        path = _local_path(source_paths[source["asset_id"]])
        try:
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != source["source_sha256"]: raise ValueError("catalog actual original SHA differs")
            with Image.open(io.BytesIO(raw)) as opened:
                actual = opened.convert("RGB")
            if actual.size != tuple(source["source_size"]) or actual.crop(source["crop_bbox"]).tobytes() != crop.tobytes():
                raise ValueError("catalog crop is not pixel-identical to the actual original")
        except OSError as exc: raise ValueError("catalog original image is missing or not decodable") from exc
        receipts[path] = hashlib.sha256(raw).hexdigest()
        current = {line["line_id"]: line for line in page["ocr_lines"]}
        if len(current) != len(page["ocr_lines"]): raise ValueError("current source OCR identities are ambiguous")
        layout = draft["payload"]["archives"]["plan"]["payload"]["layout_archive"]
        for line in layout["payload"]["source_ocr"]:
            if line["line_id"] not in current or not _same(line, {k: current[line["line_id"]].get(k) for k in line}):
                raise ValueError("catalog original OCR snapshot differs from current evidence")
        for other in regions:
            if source["asset_id"] == other["asset_id"] and _overlap(source["crop_bbox"], other["bbox"]):
                raise ValueError("catalog contains duplicate or overlapping source regions")
        rows = _source_rows(draft, evidence, graph05, capsule["answer_id"])
        if "source_rows" in capsule and not _same(capsule["source_rows"], rows): raise ValueError("derived catalog source row index changed")
        capsule["source_rows"] = rows
        regions.append(dict(asset_id=source["asset_id"], bbox=source["crop_bbox"]))
    for path, sha in receipts.items():
        try: current = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc: raise ValueError("catalog original disappeared during validation") from exc
        if current != sha: raise ValueError("catalog original bytes changed during validation")
    if digest(attachments) != original: raise ValueError("catalog attachment objects changed during validation")
    return frozen


def _runs(value):
    if not isinstance(value, list) or not value: raise ValueError("mapped region runs must be nonempty")
    for run in value:
        if (not isinstance(run, dict) or set(run) != {"format", "text"} or run.get("format") not in ("plain", "latex")
                or not isinstance(run.get("text"), str) or not run["text"] or "\r" in run["text"] or "\0" in run["text"]):
            raise ValueError("region runs must retain exact plain/LaTeX text without extra fields")


def _mapping(attachments, answer_id, block):
    if not isinstance(attachments, list): raise ValueError("region catalog must be a list")
    if not isinstance(block, dict) or block.get("kind") != "REGION": return None
    try: _runs(block.get("runs"))
    except ValueError: return None
    found = []
    for capsule in attachments:
        _capsule(capsule)
        # Loading a bundle does not establish current fragment ownership. A
        # caller may inspect an unvalidated catalog, but it offers no choices.
        if "source_rows" not in capsule: continue
        if capsule["answer_id"] != answer_id: continue
        draft, _, _ = _bundle(capsule)
        for row in draft["payload"]["rows"]:
            expected = capsule["source_rows"].get(row["row_id"])
            if expected is None: raise ValueError("validated catalog source row is missing")
            if (not _same(expected["asset_id"], block.get("asset_id")) or not _same(expected["bbox"], block.get("bbox"))
                    or not _same(expected["source_fragment_ids"], block.get("source_fragment_ids")) or expected["role"] != block.get("role")):
                continue
            if [v["format"] for v in block["runs"]] != [v["format"] for v in row["runs"]]: continue
            found.append((capsule, row))
    if len(found) > 1: raise ValueError("multiple catalog rows match one current region block")
    return found[0] if found else None


def _origin(fraction, candidate):
    if candidate["kind"] == "WHOLE_MODEL_OBSERVATION": return copy.deepcopy(candidate["origin"])
    components = {c["component_id"]: c for values in fraction["components"].values() for c in values}
    return dict(kind="DERIVED_ROLE_COMPOSITION", component_refs=copy.deepcopy(candidate["component_refs"]),
                components=[{k: copy.deepcopy(components[cid][k]) for k in ("component_id", "fraction_id", "role", "latex", "origin")} for cid in candidate["component_refs"]])


def region_options(attachments, answer_id, block):
    """Expose all formula choices only for an exact current source/run mapping."""
    mapped = _mapping(attachments, answer_id, block)
    if mapped is None: return []
    capsule, row = mapped; draft = capsule["draft"]
    slots = {s["slot_id"]: s for s in draft["payload"]["archives"]["plan"]["payload"]["fraction_slots"]}
    fractions = {f["fraction_id"]: f for f in draft["payload"]["fractions"]}; groups = []
    for binding in row["bindings"]:
        slot = slots.get(binding["slot_id"])
        if slot is None: continue  # Body/context/fallback is never a formula choice.
        index = binding["run_index"]
        if type(index) is not int or not 0 <= index < len(block["runs"]) or block["runs"][index]["format"] != "latex":
            raise ValueError("source formula run binding is invalid")
        fraction = fractions[slot["fraction_id"]]; choices = []
        for candidate in fraction["whole_candidates"]+fraction["composed_candidates"]:
            choices.append(dict(candidate_id=candidate["candidate_id"], kind=candidate["kind"], latex=candidate["latex"],
                parse_supported=candidate["parse_result"]["supported"] is True, origin=_origin(fraction, candidate),
                complete_model_call=candidate["kind"] == "WHOLE_MODEL_OBSERVATION"))
        groups.append(dict(bundle_ref=reference(draft), row_id=row["row_id"], run_index=index, fraction_id=fraction["fraction_id"],
            source_bbox=copy.deepcopy(slot["source_bbox"]), matching_candidate_ids=[c["candidate_id"] for c in choices if c["latex"] == block["runs"][index]["text"]],
            default_candidate_id=fraction["draft_candidate_id"], choices=choices, decision="HOLD", transcription_verified=False))
    return groups


def validate_region_selections(attachments, answer_id, block, runs, selections, author):
    """Validate explicit choices and retain source-only provenance, never gold."""
    if (not isinstance(author, dict) or set(author) != {"kind", "id", "note"}
            or author.get("kind") not in ("MODEL_DRAFT", "HUMAN_DRAFT", "SYNTHETIC_TEST")
            or not all(_text(author.get(k)) for k in ("id", "note"))):
        raise ValueError("selection author must be an explicit draft editor")
    _runs(runs)
    if not isinstance(selections, list) or not selections: raise ValueError("explicit region selections must be nonempty")
    groups = region_options(attachments, answer_id, block)
    if not groups or [v["format"] for v in runs] != [v["format"] for v in block["runs"]]:
        raise ValueError("selected region topology or source mapping changed")
    mapped = _mapping(attachments, answer_id, block)
    if mapped[0]["draft"]["producer"]["execution_kind"] == "SYNTHETIC_TEST" and author["kind"] != "SYNTHETIC_TEST":
        raise ValueError("synthetic region candidates require a synthetic editor")
    records, seen = [], set()
    for selection in selections:
        if (not isinstance(selection, dict) or set(selection) != {"bundle_ref", "row_id", "run_index", "fraction_id", "candidate_id"}
                or not _ref(selection.get("bundle_ref")) or type(selection.get("run_index")) is not int
                or selection["run_index"] in seen):
            raise ValueError("region selection fields, source reference or unique run index are invalid")
        seen.add(selection["run_index"])
        matches = [g for g in groups if all(_same(g[k], selection[k]) for k in ("bundle_ref", "row_id", "run_index", "fraction_id"))]
        if len(matches) != 1: raise ValueError("region choice belongs to another source/run/fraction")
        group = matches[0]; choices = [c for c in group["choices"] if c["candidate_id"] == selection["candidate_id"]]
        if len(choices) != 1: raise ValueError("unknown region candidate ID")
        choice = choices[0]; proposed = runs[selection["run_index"]]
        if proposed["format"] != "latex" or proposed["text"] != choice["latex"]:
            raise ValueError("selected candidate LaTeX changed; use an explicit draft edit instead")
        records.append(dict(**copy.deepcopy(selection), kind=choice["kind"], latex=choice["latex"], source_bbox=copy.deepcopy(group["source_bbox"]),
            origin=copy.deepcopy(choice["origin"]), complete_model_call=choice["complete_model_call"], editor_kind=author["kind"],
            decision="HOLD", transcription_verified=False))
    return records
