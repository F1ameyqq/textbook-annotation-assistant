"""Data-driven insertion contract; no hard-coded book, lesson, frame total or answer.

Consumes a complete current native snapshot with independently acquired page
byte identities. Its result is a plan, never an authorization or platform result.
The A28 finite contract remains unchanged for its already completed inputs.
"""
from __future__ import annotations

import copy
import re
import math
from datetime import timedelta
from urllib.parse import urlsplit
from uuid import UUID, uuid5, NAMESPACE_URL

from annotation.runtime.usense_live.update import json_same
from .prepare import candidate_hash
from .store import Hold, digest

ZONES = ("question", "choice", "answer", "analysis", "knowledge_point")
CLOCK_TOLERANCE_SECONDS = 5


def require(value, message):
    if not value:
        raise Hold(message)


def _response(response):
    require(type(response) is dict and type(response.get("code")) is int and response["code"] == 0
            and "data" in response, "当前原生响应无效。")
    return response["data"]


def directory_rows(directory):
    data = _response(directory)
    require(type(data) is dict and type(data.get("directory_data")) is list, "目录来源不完整。")
    rows, seen = [], set()

    def walk(nodes, path, parent):
        require(type(nodes) is list, "目录节点结构未知。")
        for node in nodes:
            require(type(node) is dict and isinstance(node.get("id"), str) and node["id"]
                    and node["id"] not in seen and isinstance(node.get("label"), str), "目录节点身份缺失或重复。")
            seen.add(node["id"])
            question = node.get("isQuestion") is True
            current = path if question else path + [node["label"]]
            rows.append({"node": node, "parent": parent, "path": current, "question": question})
            require(not question or not node.get("children"), "题节点含子目录，当前结构不支持。")
            walk(node.get("children", []), current, node["id"])
    walk(data["directory_data"], [], None)
    questions = [row for row in rows if row["question"]]
    for index, row in enumerate(questions, 1):
        require(row["node"].get("order_in_level") == str(index), "目录原生序号不连续，先核对当前状态。")
    return rows, questions


def validate_current(current):
    require(type(current) is dict and current.get("schema") == "CustomerNativeSnapshot/v1", "缺少完整当前平台快照。")
    book = current.get("book_id")
    require(type(book) is str and re.fullmatch(r"[1-9][0-9]{0,31}", book), "当前书籍身份未知。")
    rows, questions = directory_rows(current["directory"])
    frames = _response(current["frames"])
    require(type(frames) is list, "当前题框库存缺失。")
    ids = [f.get("rect_id") for f in frames if type(f) is dict]
    require(len(ids) == len(frames) and all(type(i) is str and i for i in ids) and len(set(ids)) == len(ids), "题框身份缺失或重复。")
    native = current.get("questions")
    require(type(native) is dict and set(native) == {q["node"]["id"] for q in questions}, "全书旧题正文未采齐，不能保全未知旧题。")
    info_ids = set()
    for order, row in enumerate(questions, 1):
        record = native[row["node"]["id"]]
        require(set(record) == {"info", "annotations", "zones"} and set(record["zones"]) == set(ZONES), "旧题字段或分区未采齐。")
        info = _response(record["info"])
        require(type(info) is dict and type(info.get("id")) is str and info["id"] not in info_ids
                and info.get("file_id") == book and info.get("order_in_level") == str(order), "旧题 info 身份不一致。")
        info_ids.add(info["id"])
        selected = [f for f in frames if f.get("order_in_level") == str(order)]
        require(all(f.get("file_id") == book and f.get("directory_id") == row["parent"]
                    and f.get("type") in ZONES for f in selected), "题框书籍或目录归属不一致。")
        require(json_same(_response(record["annotations"]), selected), "逐题题框与全书库存不一致。")
        for zone in ZONES:
            value = _response(record["zones"][zone])
            require(type(value) is dict and type(value.get("success")) is bool, "旧题 OCR 响应不完整。")
            if value["success"]:
                require(type(value.get("ocr_result")) is str and type(value.get("rect_ids")) is list
                        and set(value["rect_ids"]) == {f["rect_id"] for f in selected if f["type"] == zone}, "旧题 OCR 与题框关联不一致。")
    require(all(f.get("order_in_level") in {str(i) for i in range(1, len(questions) + 1)} for f in frames), "库存含未归属题框。")
    require(type(current.get("pages")) is dict, "当前来源页绑定缺失。")
    return rows, questions


def source_key(book, candidate):
    return digest([book, sorted((f["source_sha256"], f["bbox"], f["zone"]) for f in candidate["frames"])])


def _overlap(left, right):
    return max(left[0], right[0]) < min(left[2], right[2]) and max(left[1], right[1]) < min(left[3], right[3])


def make_plan(current, candidate, lesson):
    rows, questions = validate_current(current)
    require(candidate["content_hash"] == candidate_hash(candidate), "候选内容已改变。")
    from .graphic_options import all_confirmed
    require(all_confirmed(candidate),'图形选项仍有未逐框核对的原图范围。')
    require(candidate["content_status"] in {"READY_EXACT_TEXT", "READY_CUSTOMER_REVIEWED", "READY_SOURCE_CHECKED"}
            and not candidate["issues"], "候选仍需内容审校。")
    if candidate['content_status']=='READY_SOURCE_CHECKED':
        quality=candidate.get('quality',{})
        require(quality.get('machine_checked') is True and quality.get('exceptions')==[]
                and quality.get('content_hash')==candidate_hash(candidate),'来源质量记录与当前内容不一致。')
    from .review_features import figure_requirements
    image_pages={}
    for frame in candidate['frames']:
        source=current['pages'].get(frame['source_sha256'])
        if source:image_pages[frame['asset_id']]={'kind':'image','asset_id':frame['asset_id'],'raw_sha256':source['sha256'],'width':source['dimensions'][0],'height':source['dimensions'][1]}
    require(not figure_requirements(candidate,list(image_pages.values())),'明确图引用还没有已确认且来源一致的原始题图区域。')
    if candidate["content_status"] == "READY_CUSTOMER_REVIEWED":
        receipt = candidate.get("review") or {}
        require(receipt.get("content_hash") == candidate_hash(candidate) and receipt.get("source_checked") is True
                and receipt.get("content_checked") is True, "审校记录与当前内容不一致。")
    directories = [r for r in rows if not r["question"] and
                   (r["path"] == lesson if isinstance(lesson, list) else r["node"]["label"] == lesson)]
    require(len(directories) == 1, "课时目录不存在或重名，请在书籍目录中选择完整路径。")
    target = directories[0]
    target_index = rows.index(target)
    descendants = []
    for row in rows[target_index + 1:]:
        if not row["path"][:len(target["path"])] == target["path"]:
            break
        descendants.append(row)
    selected = [r for r in descendants if r["question"]]
    insert_after = max((int(r["node"]["order_in_level"]) for r in selected),
                       default=sum(r["question"] for r in rows[:target_index]))
    # A parent with child directories would need an explicit subdirectory
    # selection; appending to it can create ambiguous traversal order.
    require(not any(not r["question"] for r in descendants), "请选择末级课时目录。")
    from .existing_fill import locate,make
    if locate(current,candidate) is not None:return make(current,candidate,lesson,target)
    book, new_order = current["book_id"], insert_after + 1
    key = source_key(book, candidate)
    native_frames = _response(current["frames"])
    new_frames, zone_counts = [], {}
    for index, frame in enumerate(candidate["frames"]):
        require(frame["coordinate_space"] == "ORIGINAL_PIXELS", "文字材料已可离线组题；平台题框仍需原书页面像素绑定。")
        page = current["pages"].get(frame["source_sha256"])
        require(type(page) is dict and page.get("sha256") == frame["source_sha256"]
                and page.get("dimensions") == frame["source_dimensions"] and page.get("book_id") == book,
                "本地原图尚未绑定当前书籍的来源页面。")
        require(type(page.get("viewer_page")) is int and page["viewer_page"] >= 1, "来源页号未知。")
        parsed = urlsplit(page.get("image_url", ""))
        require(parsed.scheme == "https" and not parsed.query and not parsed.fragment and not parsed.username
                and parsed.netloc.endswith(".aliyuncs.com") and ("/" + book + "/") in parsed.path,
                "原图 URL 未绑定当前书籍的官方图片来源。")
        x1, y1, x2, y2 = frame["bbox"]
        width, height = frame["source_dimensions"]
        require(all(type(v) is int for v in frame["bbox"]) and 0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height,
                "候选来源框越界。")
        for old in native_frames:
            if old.get("page_index") == page["viewer_page"] and old.get("type") == frame["zone"]:
                try:
                    old_box = [float(x) for x in old["rect_bbox"].split(",")]
                except (ValueError, AttributeError, KeyError):
                    raise Hold("既有题框几何未知，先核对，不能重复插入。") from None
                require(len(old_box) == 4 and all(math.isfinite(x) for x in old_box)
                        and old_box[0]<old_box[2] and old_box[1]<old_box[3]
                        and not _overlap(frame["bbox"], old_box),
                        "第" + str(candidate.get('printed_number','?')) + "题 · "
                        + {'question':'题干','choice':'选项','answer':'答案','analysis':'解析'}.get(frame['zone'],frame['zone'])
                        + " · 来源页" + str(page['viewer_page']) + " · 来源框" + str(index+1)
                        + " 与已有同区题框重叠；请返回本题审校，核对对应来源范围，不能重复保存。")
        rect_id = str(uuid5(NAMESPACE_URL, "customer/" + key + "/" + str(index)))
        require(rect_id not in {f["rect_id"] for f in native_frames}, "候选题框已存在，先对账。")
        zone = frame["zone"]
        image_order = zone_counts.get(zone, 0); zone_counts[zone] = image_order + 1
        new_frames.append({"rect_id": rect_id, "type": zone, "belong_to_level": "question_level",
            "order_in_level": str(new_order), "image_order_in_annotation_zone": image_order,
            "rect_bbox": ",".join(map(str, frame["bbox"])), "page_index": page["viewer_page"],
            "image_path": page["image_url"] + f"?x-oss-process=image/crop,x_{x1},y_{y1},w_{x2-x1},h_{y2-y1}",
            "parent_rect_id": None, "directory_id": target["node"]["id"], "content_type": frame.get('content_type','text'),
            "user_id": None, "is_pre_annotation": False, "pre_annotations_id": None})
    require(set(candidate["zones"]) == set(zone_counts) and {"question", "answer"} <= set(zone_counts), "内容分区缺少来源题框。")
    # Plain text is escaped before entering the platform's HTML-bearing field.
    from .rich_content import zone_html
    zone_values = {name: zone_html(text,[f for f in new_frames if f['type']==name and f['content_type']=='image'])
                   for name,text in candidate['zones'].items()}
    if candidate.get('graphic_option_proposals'):
        from .graphic_options import choice_html
        zone_values['choice'] = choice_html(candidate['zones']['choice'],candidate['frames'],new_frames)
    payload = {"file_id": book, "target_directory_id": target["node"]["id"], "question_order": None,
        "is_new_question_insertion": True, "insert_after_order": insert_after,
        "annotations_upsert": new_frames, "annotations_delete_rect_ids": [],
        "ocr_submissions": [{"zone": zone, "ocr_result": text, "rect_ids": [f["rect_id"] for f in new_frames if f["type"] == zone],
                             "question_order": None} for zone, text in zone_values.items()],
        "ocr_delete_zones": [], "question_info": {"tishi": "xuanze" if "choice" in zone_counts else "wenda", "tilei": None, "tihao": None},
        "created_by": None}
    result = {"schema": "CustomerNativeInsertPlan/v1", "book_id": book, "key": key,
        "candidate": copy.deepcopy(candidate), "before": copy.deepcopy(current), "lesson": lesson,
        "new_order": new_order, "before_count": len(questions), "before_frame_count": len(native_frames),
        "payload": payload, "write_authorized": False, "automatic_retry": False}
    result["hash"] = digest(result)
    return result


def check_plan(plan):
    rebuilt = make_plan(plan["before"], plan["candidate"], plan["lesson"])
    require(json_same(plan, rebuilt), "生产计划已改变。")


def check_prewrite(plan, current):
    check_plan(plan); validate_current(current)
    require(json_same(current, plan["before"]), "平台当前状态已变化，停止保存并重新核对。")


def send_window_bounds(send_window):
    """Customer native metadata: bounded aware send plus five seconds of skew.

    Keep the original at-most-120-second, aware send interval validation.
    This finite tolerance already exists in the native finalize contract; it
    does not change timestamps, infer a clock cause, or relax content/identity.
    """
    from annotation.runtime.usense_live.lesson_insert import _window
    start, end = _window(send_window)  # Includes one second on each side.
    extra = timedelta(seconds=CLOCK_TOLERANCE_SECONDS - 1)
    return start - extra, end + extra


def compare_readback(plan, after, receipt, *, runtime_actor_hashes=None, send_window=None):
    """Strict whole-book preservation. Unknown metadata changes are held."""
    check_plan(plan)
    if plan.get('schema')=='CustomerNativeExistingFillPlan/v1':
        from .existing_fill import compare
        return compare(plan,after,receipt,runtime_actor_hashes=runtime_actor_hashes,send_window=send_window)
    _, old_questions = validate_current(plan["before"])
    _, new_questions = validate_current(after)
    from annotation.runtime.usense_live import insertion, lesson_insert
    window = send_window_bounds(send_window) if send_window is not None else None

    def shifted(old, actual):
        expected = copy.deepcopy(old)
        expected["order_in_level"] = str(int(old["order_in_level"]) + 1)
        if old.get("updated_at") != actual.get("updated_at"):
            require(window is not None, "旧题时间戳变化但缺少实际发送窗口。")
            prior = lesson_insert._native_time(old.get("updated_at"))
            stamp = lesson_insert._native_time(actual.get("updated_at"))
            require(prior < stamp and window[0] <= stamp <= window[1], "旧题时间戳不在实际发送窗口或未单调推进。")
            expected["updated_at"] = actual["updated_at"]
        return expected

    def new_time(record):
        if window is not None:
            stamp = lesson_insert._native_time(record.get("created_at"))
            require(record.get("created_at") == record.get("updated_at") and window[0] <= stamp <= window[1], "新增记录时间戳不在实际发送窗口。")
    data = _response(receipt)
    require(type(data) is dict and data.get("inserted") is True and data.get("success") is True
            and type(data.get("question_order")) is int and data["question_order"] == plan["new_order"], "保存回执未知，禁止重发。")
    new_node = data.get("inserted_question_node")
    actual_node = new_questions[plan["new_order"] - 1]["node"]
    require(type(new_node) is dict and new_node.get("id") not in {q["node"]["id"] for q in old_questions}
            and set(actual_node) == set(new_node)
            and all(json_same(actual_node[key], new_node[key]) for key in new_node), "新题节点回执与读回不一致。")
    require(len(new_questions) == len(old_questions) + 1 and after["book_id"] == plan["book_id"], "读回题数或书籍不一致。")
    expected_directory = copy.deepcopy(plan["before"]["directory"])
    rows, _ = directory_rows(expected_directory)
    for row in rows:
        if row["question"] and int(row["node"]["order_in_level"]) >= plan["new_order"]:
            if row["node"]["label"] == row["node"]["order_in_level"]:
                row["node"]["label"] = str(int(row["node"]["label"]) + 1)
            row["node"]["order_in_level"] = str(int(row["node"]["order_in_level"]) + 1)
    parent = next(r["node"] for r in rows if r["node"]["id"] == plan["payload"]["target_directory_id"])
    # The save receipt and directory GET serialize the same new node's keys
    # in different orders. Only this cross-endpoint new object uses field
    # equality. Every old directory object retains the original strict order.
    parent.setdefault("children", []).append(copy.deepcopy(actual_node))
    require(json_same(expected_directory, after["directory"]), "目录旧值或新增节点位置未保全。")
    expected_frames = copy.deepcopy(_response(plan["before"]["frames"]))
    actual_frames = _response(after["frames"])
    actual_by_id = {f["rect_id"]: f for f in actual_frames}
    for index, frame in enumerate(expected_frames):
        if int(frame["order_in_level"]) >= plan["new_order"]:
            expected_frames[index] = shifted(frame, actual_by_id.get(frame["rect_id"], {}))
    new_ids = {f["rect_id"] for f in plan["payload"]["annotations_upsert"]}
    require(json_same([f for f in actual_frames if f["rect_id"] not in new_ids], expected_frames), "旧题框原值未严格保全。")
    require(len(actual_frames) == len(expected_frames) + len(new_ids), "新增题框数量不一致。")
    for row in old_questions:
        node_id = row["node"]["id"]
        expected = copy.deepcopy(plan["before"]["questions"][node_id])
        order = int(row["node"]["order_in_level"])
        if order >= plan["new_order"]:
            expected["info"]["data"] = shifted(expected["info"]["data"], after["questions"][node_id]["info"]["data"])
            expected["annotations"]["data"] = [shifted(frame, actual_by_id.get(frame["rect_id"], {}))
                                                for frame in expected["annotations"]["data"]]
        require(json_same(expected, after["questions"].get(node_id)), "旧题完整正文或身份未保全。")
    record = after["questions"][new_node["id"]]
    info = _response(record["info"])
    require(set(info) == set(insertion.INFO_KEYS) and info.get("tixu") is None, "新增 info 字段未知。")
    new_time(info)
    require(info["id"] not in {r["info"]["data"]["id"] for r in plan["before"]["questions"].values()}, "新题 info 身份与旧题重复。")
    for field, expected in plan["payload"]["question_info"].items():
        require(info.get(field) == expected, "新题题型读回不一致。")
    for zone in ZONES:
        actual = _response(record["zones"][zone])
        expected = next((z for z in plan["payload"]["ocr_submissions"] if z["zone"] == zone), None)
        if expected is None:
            require(actual.get("success") is False, "新增题出现未计划分区。")
        else:
            require(actual.get("success") is True and actual.get("ocr_result") == expected["ocr_result"]
                    and actual.get("rect_ids") == expected["rect_ids"], "新增内容或题框关联读回不一致。")
    for expected in plan["payload"]["annotations_upsert"]:
        actual = next((f for f in actual_frames if f["rect_id"] == expected["rect_id"]), None)
        require(actual is not None and set(actual) == set(insertion.ROW_KEYS)
                and all(type(actual.get(k)) is type(v) and actual.get(k) == v for k, v in expected.items() if k != "user_id")
                and type(actual.get("verified")) is int and actual["verified"] == 0
                and actual.get("file_id") == plan["book_id"], "新增题框读回不一致。")
        new_time(actual)
        if runtime_actor_hashes is not None:
            from annotation.runtime.usense_live.update import text_digest
            require(type(actual.get("user_id")) is str and text_digest(actual["user_id"]) == runtime_actor_hashes.get("runtime_user_id_sha256"),
                    "新增题框操作者身份与发送时身份不一致。")
    require(json_same(plan["before"]["pages"], after["pages"]), "来源页字节绑定已变化。")
    return {"match": True, "old_questions_preserved": len(old_questions), "old_frames_preserved": len(expected_frames),
            "new_node_id": new_node["id"], "new_info_id": info["id"], "readback_hash": digest(after),
            "native_clock_tolerance_seconds": CLOCK_TOLERANCE_SECONDS if window is not None else None,
            "runtime_actor_and_send_window_checked": runtime_actor_hashes is not None and window is not None}
