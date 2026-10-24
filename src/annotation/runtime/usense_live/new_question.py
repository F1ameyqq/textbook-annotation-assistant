"""Offline, reviewed single-question middle-insert drafts. No send entry exists.

Generalizes the observed unified payload and strict Q7 preservation comparison;
does not relax or replace the Q7 implementation or its writer.
"""
import copy
import re
import struct
import uuid

from . import update as u
from .batch import ref_bytes
from .insertion import ROW_KEYS, INFO_KEYS, NODE_KEYS, OBSERVED_INSERTED_NODE_KEYS, _new_timestamp_pair, flat_digest, SUFFIXES
from .structure import check_protocol, directories, fingerprint, full_snapshot, COMMIT
from .core import utc

SCHEMA = "b-usense-reviewed-new-question-draft/0.1"


def image_size(raw):
    """Read source/crop pixel dimensions without an image runtime or network."""
    if raw[:8] == b"\x89PNG\r\n\x1a\n" and raw[12:16] == b"IHDR":
        return list(struct.unpack(">II", raw[16:24]))
    u.require(raw[:2] == b"\xff\xd8", "NEW_IMAGE_HEADER_UNSUPPORTED")
    offset = 2
    while offset < len(raw):
        u.require(raw[offset] == 255, "NEW_JPEG_HEADER_INVALID")
        while offset < len(raw) and raw[offset] == 255:
            offset += 1
        marker = raw[offset]; offset += 1
        if marker in (0x01, *range(0xd0, 0xd9)):
            continue
        length = int.from_bytes(raw[offset:offset+2], "big")
        u.require(length >= 2 and offset+length <= len(raw), "NEW_JPEG_SEGMENT_INVALID")
        if marker in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf):
            return [int.from_bytes(raw[offset+5:offset+7], "big"), int.from_bytes(raw[offset+3:offset+5], "big")]
        u.require(marker != 0xda, "NEW_JPEG_SIZE_MISSING")
        offset += length
    raise ValueError("NEW_JPEG_SIZE_MISSING")


def _frame(frame, before, directory, temporary_order, allowed_pages):
    keys = {"key", "rect_id", "zone", "index", "content_type", "viewer_page", "bbox", "source", "source_binding", "crop", "crop_evidence"}
    u.require(type(frame) is dict and set(frame) == keys, "NEW_FRAME_SHAPE")
    rect = frame["rect_id"]
    u.require(type(rect) is str and str(uuid.UUID(rect)) == rect, "NEW_FRAME_UUID_REQUIRED")
    zone, page, bbox = frame["zone"], frame["viewer_page"], frame["bbox"]
    u.require(zone in u.ZONES and type(page) is int and page in allowed_pages.get(zone, []), "NEW_WRONG_SOURCE_PAGE_FOR_ZONE")
    u.require(type(frame["index"]) is int and frame["index"] >= 0 and frame["content_type"] in ("text", "image", "table"), "NEW_FRAME_ROLE")
    source = ref_bytes(frame["source"])
    dims = image_size(source)
    u.require(type(bbox) is list and len(bbox) == 4 and all(type(v) is int for v in bbox) and
              0 <= bbox[0] < bbox[2] <= dims[0] and 0 <= bbox[1] < bbox[3] <= dims[1], "NEW_SOURCE_BOUNDS")
    metadata = u._response(before.get(f"page_{page}"))
    u.require(type(metadata) is dict and metadata.get("file_id") == u.BOOK and len(metadata.get("pages", [])) == 1,
              "NEW_NATIVE_SOURCE_METADATA_REQUIRED")
    native = metadata["pages"][0]
    u.require(type(native.get("page_index")) is int and native["page_index"] == page-1 and type(native.get("image")) is str,
              "NEW_VIEWER_SOURCE_INDEX_MISMATCH")
    url = native["image"]
    expected_base = f"https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com/upload_images/{u.BOOK}/{u.BOOK}_page_{page-1}.jpg"
    u.require(url == expected_base, "NEW_NATIVE_SOURCE_URL_UNKNOWN")
    binding = u.loads(ref_bytes(frame["source_binding"]))
    u.require(binding.get("book_id") == u.BOOK and binding.get("schema") in
              ("CurrentPlatformSources/v1","UsenseObservedPageSourceDownload/v1"), "NEW_OBSERVED_SOURCE_BINDING_REQUIRED")
    matches = [row for row in binding.get("pages",[]) if type(row.get("viewer_page")) is int and row["viewer_page"] == page]
    u.require(len(matches) == 1,"NEW_SOURCE_PAGE_MAPPING_AMBIGUOUS")
    asset = matches[0]
    if binding["schema"] == "CurrentPlatformSources/v1":
        from pathlib import Path
        asset_path = (Path(frame["source_binding"]["path"]).resolve().parent/asset["file"]).resolve()
        u.require(str(asset_path) == str(Path(frame["source"]["path"]).resolve()) and asset.get("source_page_index") == page-1 and
                  asset.get("url") == expected_base,"NEW_SOURCE_LOCAL_FILE_PAGE_URL_MISMATCH")
    else:
        from pathlib import Path
        u.require(str(Path(asset["path"]).resolve()) == str(Path(frame["source"]["path"]).resolve()) and
                  asset.get("source_url") == expected_base and asset.get("width") == dims[0] and asset.get("height") == dims[1] and
                  asset.get("http_status") == 200,"NEW_SOURCE_LOCAL_FILE_PAGE_URL_MISMATCH")
        metadata_ref = {"path":asset["metadata_path"],"sha256":asset["metadata_sha256"]}
        u.require(u.json_same(u.loads(ref_bytes(metadata_ref)),before[f"page_{page}"]),"NEW_SOURCE_METADATA_BYTES_OR_PAGE_MISMATCH")
    u.require(asset.get("sha256") == frame["source"]["sha256"] and asset.get("bytes") == len(source),"NEW_SOURCE_ASSET_HASH_MISMATCH")
    x1,y1,x2,y2 = bbox
    url += f"?x-oss-process=image/crop,x_{x1},y_{y1},w_{x2-x1},h_{y2-y1}"
    crop = ref_bytes(frame["crop"])
    u.require(image_size(crop) == [x2-x1,y2-y1], "NEW_CROP_PIXEL_DIMENSIONS_MISMATCH")
    proof = u.loads(ref_bytes(frame["crop_evidence"]))
    expected_proof = {"schema": "b-usense-observed-frame-crop/0.1", "book_id": u.BOOK,
                      "viewer_page": page, "source": frame["source"], "source_url": expected_base,
                      "source_dimensions": dims, "bbox": bbox, "crop": frame["crop"],
                      "crop_url": url, "http_status": 200, "dimensions": [x2-x1,y2-y1]}
    u.require(u.json_same(proof, expected_proof), "NEW_SOURCE_CROP_BINDING_MISMATCH")
    return {"rect_id": rect, "type": zone, "belong_to_level": "question_level", "order_in_level": str(temporary_order),
            "image_order_in_annotation_zone": frame["index"], "rect_bbox": ",".join(map(str,bbox)), "page_index": page,
            "image_path": url, "parent_rect_id": None, "directory_id": directory, "content_type": frame["content_type"],
            "user_id": None, "is_pre_annotation": False, "pre_annotations_id": None}


def make_new_draft(before, candidate, scope, content_review, protocol, observed_at):
    check_protocol(protocol); utc(observed_at)
    identities = full_snapshot(before)
    u.require(type(candidate) is dict and set(candidate) == {"schema", "book_id", "logical_key", "printed_number", "variant",
              "target_directory_id", "server_identity", "anchor", "frames", "zone_values", "question_info"} and
              candidate["schema"] == "b-usense-new-question-candidate/0.1" and candidate["book_id"] == u.BOOK, "NEW_CANDIDATE_SHAPE")
    u.require(type(candidate["logical_key"]) is str and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",candidate["logical_key"])) and
              all(u._id(candidate[k]) for k in ("printed_number", "variant")), "NEW_LOGICAL_MAPPING_REQUIRED")
    u.require(u.json_same(candidate["server_identity"], {"node_id": None, "info_id": None, "question_order": None}), "NEW_SERVER_IDENTITY_MUST_BE_UNKNOWN")
    directory = candidate["target_directory_id"]
    current = [t for t in identities if t["lesson_directory_id"] == directory]
    u.require(bool(current) and directory in directories(before["directory"]), "NEW_DESTINATION_MUST_FIRST_HAVE_VERIFIED_EXISTING_BINDINGS")
    scope_expected_keys = {"schema", "book_id", "source_lesson", "directory_id", "existing_targets", "allowed_new_items", "completed_logical_keys", "allowed_pages_by_zone", "decision"}
    u.require(type(scope) is dict and set(scope) == scope_expected_keys and scope["schema"] == "b-usense-new-question-scope-review/0.1" and
              scope["book_id"] == u.BOOK and scope["directory_id"] == directory and u._id(scope["source_lesson"]) and
              scope["decision"] == "SOURCE_LESSON_AND_EXISTING_BINDINGS_REVIEWED" and u.json_same(scope["existing_targets"],current),
              "NEW_SCOPE_BINDINGS_REQUIRE_CURRENT_DIRECTORY_READBACK")
    logical = {k:candidate[k] for k in ("logical_key", "printed_number", "variant")}
    u.require(type(scope["allowed_new_items"]) is list and sum(u.json_same(logical,item) for item in scope["allowed_new_items"]) == 1 and
              type(scope["completed_logical_keys"]) is list and candidate["logical_key"] not in scope["completed_logical_keys"], "NEW_ITEM_NOT_EXPLICITLY_REVIEWED_OR_ALREADY_DONE")
    u.require(type(scope["allowed_pages_by_zone"]) is dict and set(scope["allowed_pages_by_zone"]) <= set(u.ZONES), "NEW_ZONE_PAGE_SCOPE_REQUIRED")
    anchor = candidate["anchor"]
    u.require(any(u.json_same(anchor,t) for t in current) and anchor == current[-1] and anchor["question_order"] < len(identities),
              "NEW_MIDDLE_INSERT_AFTER_LAST_REVIEWED_LESSON_ITEM_ONLY")
    u.require(u.json_same(content_review,{"schema":"b-usense-new-question-content-review/0.1", "candidate_object_sha256":u.digest(candidate),
              "scope_object_sha256":u.digest(scope), "decision":"SOURCE_CONTENT_AND_FRAME_BOUNDARIES_REVIEWED"}), "NEW_CONTENT_REVIEW_REQUIRED")
    frames = candidate["frames"]
    u.require(type(frames) is list and 1 <= len(frames) <= 40, "NEW_EXPLICIT_REVIEWED_FRAMES_REQUIRED")
    u.require(len({f["rect_id"] for f in frames}) == len(frames) and len({f["key"] for f in frames}) == len(frames), "NEW_DUPLICATE_FRAME_ID_OR_KEY")
    u.require(not ({f["rect_id"] for f in frames} & {f["rect_id"] for f in before["frames"]["data"]}), "NEW_RECT_ID_ALREADY_EXISTS")
    rows = [_frame(frame,before,directory,len(identities)+1,scope["allowed_pages_by_zone"]) for frame in frames]
    zones = candidate["zone_values"]
    u.require(type(zones) is dict and {"question","answer"} <= set(zones) <= set(u.ZONES) and
              all(type(text) is str and bool(text.strip()) for text in zones.values()), "NEW_REVIEWED_QUESTION_AND_ANSWER_REQUIRED")
    submissions = []
    for zone in u.ZONES:
        subset = [r for r in rows if r["type"] == zone]
        indexes = [r["image_order_in_annotation_zone"] for r in subset]
        u.require(sorted(indexes) == list(range(len(indexes))), "NEW_ZONE_FRAME_ORDER_AMBIGUOUS")
        u.require(bool(subset) == (zone in zones), "NEW_ZONE_TEXT_FRAME_MISMATCH")
        if subset:
            subset.sort(key=lambda r:r["image_order_in_annotation_zone"])
            image_rows = [r["image_path"] for r in subset if r["content_type"] in ("image","table")]
            references = u.image_references(zones[zone])
            u.require(all(references[url] >= image_rows.count(url) for url in image_rows) and
                      all(url in [r["image_path"] for r in subset] for url in references), "NEW_FIGURE_REFERENCE_NOT_BOUND_TO_REVIEWED_FRAMES")
            submissions.append({"zone":zone,"ocr_result":zones[zone],"rect_ids":[r["rect_id"] for r in subset],"question_order":None})
    info = candidate["question_info"]
    u.require(type(info) is dict and set(info) == {"tishi","tilei","tihao"} and u._id(info["tishi"]) and
              all(info[k] is None or type(info[k]) is str for k in ("tilei","tihao")), "NEW_EXPLICIT_NATIVE_QUESTION_INFO_REQUIRED")
    payload = {"file_id":u.BOOK,"target_directory_id":directory,"question_order":None,"is_new_question_insertion":True,
               "insert_after_order":anchor["question_order"],"annotations_upsert":rows,"annotations_delete_rect_ids":[],
               "ocr_submissions":submissions,"ocr_delete_zones":[],"question_info":copy.deepcopy(info),"created_by":None}
    key = "usense-new-" + u.digest({"book_id":u.BOOK,"directory_id":directory,"logical_key":candidate["logical_key"]})
    plan = {"schema":SCHEMA,"status":"OFFLINE_SINGLE_INSERT_DRAFT_NOT_EXECUTABLE","book_id":u.BOOK,"protocol":copy.deepcopy(protocol),
            "baseline_observed_at":observed_at,"before_full":copy.deepcopy(before),"before_sha256":flat_digest(before),
            "old_identities":identities,"candidate":copy.deepcopy(candidate),"scope_review":copy.deepcopy(scope),"content_review":copy.deepcopy(content_review),
            "new_order":anchor["question_order"]+1,"request":{"method":"POST","path":COMMIT,"body":payload},
            "ledger_key":key,"write_authorized":False,"automatic_retry_allowed":False,
            "blockers":["GENERAL_INSERT_WRITER_NOT_IMPLEMENTED","FRESH_FULL_BOOK_AND_INDEPENDENT_PROCESS_EVIDENCE_REQUIRED"]}
    plan["plan_sha256"] = fingerprint(plan)
    return plan


def verify_new(plan, after, receipt, runtime_actor_hashes):
    u.require(fingerprint(plan) == plan["plan_sha256"],"NEW_DRAFT_CHANGED")
    rebuilt = make_new_draft(plan["before_full"],plan["candidate"],plan["scope_review"],plan["content_review"],plan["protocol"],plan["baseline_observed_at"])
    u.require(u.json_same(plan,rebuilt),"NEW_DRAFT_TAMPERED")
    identities = full_snapshot(after)
    u.require({name for name in after if not name.startswith("q")} ==
              {name for name in plan["before_full"] if not name.startswith("q")},"NEW_GLOBAL_CAPTURE_SCOPE_CHANGED")
    u.require(len(identities) == len(plan["old_identities"])+1,"NEW_ONE_QUESTION_ONLY")
    raw = u._response(receipt,code=(0,))
    u.require(type(raw) is dict and set(raw) == {"inserted","question_order","inserted_question_node","success","append_at_global_end"} and
              raw["inserted"] is True and raw["success"] is True and raw["append_at_global_end"] is False and
              type(raw["question_order"]) is int and raw["question_order"] == plan["new_order"],"NEW_RECEIPT_UNKNOWN_NO_RETRY")
    node = raw["inserted_question_node"]; order = plan["new_order"]; before = plan["before_full"]
    u.require(type(node) is dict and tuple(node) in (NODE_KEYS,OBSERVED_INSERTED_NODE_KEYS) and
              node.get("isQuestion") is True and node.get("label") == node.get("order_in_level") == str(order) and
              u._id(node.get("id")) and node["id"] not in {t["node_id"] for t in plan["old_identities"]},"NEW_RECEIPT_NODE_IDENTITY_UNKNOWN")
    u.require(type(runtime_actor_hashes) is dict and set(runtime_actor_hashes) == {"runtime_actor_sha256","runtime_user_id_sha256"} and
              all(type(v) is str and re.fullmatch(r"[0-9a-f]{64}",v) for v in runtime_actor_hashes.values()),"NEW_RUNTIME_ACTOR_HASH_REQUIRED")
    delta = []
    def same(expected,actual,path):
        if not u.json_same(expected,actual): delta.append(path)
    def shifted(row):
        value = copy.deepcopy(row)
        if u._order(value["order_in_level"]) >= order:
            old=value["order_in_level"]; value["order_in_level"]=str(int(old)+1) if type(old) is str else old+1
        return value
    expected_dir = copy.deepcopy(before["directory"])
    def walk(nodes):
        for old in list(nodes):
            if old.get("isQuestion",False):
                if u._order(old["order_in_level"]) >= order:
                    old["order_in_level"]=str(int(old["order_in_level"])+1);old["label"]=str(int(old["label"])+1)
                if old["id"] == plan["candidate"]["anchor"]["node_id"]: nodes.insert(nodes.index(old)+1,copy.deepcopy(node))
            else: walk(old.get("children",[]))
    walk(expected_dir["data"]["directory_data"])
    same(expected_dir,after["directory"],"directory")
    for name in before:
        if name in ("directory","frames") or name.startswith("q"): continue
        same(before[name],after.get(name),name)
    for old in plan["old_identities"]:
        q=old["question_order"]; nq=q+(q>=order)
        target=copy.deepcopy(old);target["question_order"]=nq
        same(target,identities[nq-1],f"q{q}.stable_identity")
        for suffix in SUFFIXES:
            expected=copy.deepcopy(before[f"q{q}_{suffix}"])
            if suffix=="info": expected["data"]=shifted(expected["data"])
            if suffix=="annotations": expected["data"]=[shifted(r) for r in expected["data"]]
            same(expected,after[f"q{nq}_{suffix}"],f"q{q}->{nq}.{suffix}")
    rows=plan["request"]["body"]["annotations_upsert"]; newids={r["rect_id"] for r in rows}; oldids={r["rect_id"] for r in before["frames"]["data"]}
    actual=after["frames"]["data"]
    same(oldids|newids,{r["rect_id"] for r in actual},"frames.identity_set")
    expected_global=copy.deepcopy(before["frames"]); expected_global["data"]=[shifted(r) for r in before["frames"]["data"]]
    old_global=copy.deepcopy(after["frames"]);old_global["data"]=[r for r in actual if r["rect_id"] in oldids]
    same(expected_global,old_global,"frames.old_subsequence")
    byid={r["rect_id"]:r for r in actual}
    for row in rows:
        got=byid.get(row["rect_id"],{}); expected={key:copy.deepcopy(row[key]) if key in row else got.get(key) for key in ROW_KEYS}
        expected.update(order_in_level=str(order),file_id=u.BOOK,verified=0,user_id=got.get("user_id"))
        same(expected,got,"new_frame."+row["rect_id"])
        same(True,_new_timestamp_pair(got),"new_frame.timestamps")
        same(runtime_actor_hashes["runtime_user_id_sha256"],u.text_digest(got.get("user_id","")),"new_frame.runtime_actor")
    target=identities[order-1]
    same(node["id"],target["node_id"],"new_node.receipt_binding")
    same(plan["candidate"]["target_directory_id"],target["lesson_directory_id"],"new_node.parent")
    same(False,target["info_id"] in {t["info_id"] for t in plan["old_identities"]},"new_info.unique")
    anchor=plan["candidate"]["anchor"]["question_order"]
    ann=copy.deepcopy(before[f"q{anchor}_annotations"]);ann["data"]=[r for r in actual if r["rect_id"] in newids]
    same(ann,after[f"q{order}_annotations"],"new_question.annotations")
    got=after[f"q{order}_info"]["data"]
    expected_info={key:got.get(key) for key in INFO_KEYS}
    expected_info.update(plan["candidate"]["question_info"],id=target["info_id"],file_id=u.BOOK,order_in_level=str(order),tixu=None)
    info=copy.deepcopy(before[f"q{anchor}_info"]);info["data"]=expected_info
    same(info,after[f"q{order}_info"],"new_question.info")
    same(True,_new_timestamp_pair(got),"new_info.timestamps")
    submissions={s["zone"]:s for s in plan["request"]["body"]["ocr_submissions"]}
    for zone in u.ZONES:
        value=copy.deepcopy(before[f"q{anchor}_{zone}"])
        value["data"]={"rect_ids":submissions[zone]["rect_ids"],"ocr_result":submissions[zone]["ocr_result"],"success":True} if zone in submissions else copy.deepcopy(u.ABSENT)
        same(value,after[f"q{order}_{zone}"],"new_question."+zone)
    return {"schema":"b-usense-new-question-native-comparison/0.1","match":not delta,
            "status":"NATIVE_MATCH_REQUIRES_PROCESS_RECEIPT_AND_EXPORT" if not delta else "HOLD","differences":delta,
            "new_identity":target,"all_old_questions_checked":len(plan["old_identities"]),"old_metadata_changes_allowed":[],
            "platform_acceptance":False,"automatic_retry_allowed":False}
