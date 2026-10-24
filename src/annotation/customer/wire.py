"""Adapter from customer plans to the existing owned native insertion writer."""
from __future__ import annotations

import copy
from pathlib import Path

from annotation.runtime.usense_live.config import endpoints
from annotation.runtime.usense_live.update import json_same
from . import native_plan as native
from .store import byte_hash, digest

SCHEMA = "CustomerNativeWirePlan/v1"


def snapshot(flat, book, pages):
    _, questions = native.directory_rows(flat["directory"])
    records = {}
    for index, row in enumerate(questions, 1):
        prefix = f"q{index}_"
        records[row["node"]["id"]] = {"info": flat[prefix + "info"], "annotations": flat[prefix + "annotations"],
            "zones": {zone: flat[prefix + zone] for zone in native.ZONES}}
    value = {"schema": "CustomerNativeSnapshot/v1", "book_id": book, "directory": flat["directory"],
             "frames": flat["frames"], "questions": records, "pages": pages}
    native.validate_current(value)
    # Bind each declared source identity to the observed native page response.
    source = native._response(flat["source"])
    native.require(source.get("file_id") == book, "原生来源书籍不一致。")
    for descriptor in pages.values():
        page = native._response(flat[f"page_{descriptor['viewer_page']}"])
        native.require(page.get("file_id") == book and type(page.get("pages")) is list and len(page["pages"]) == 1
                       and page["pages"][0].get("image") == descriptor["image_url"]
                       and page["pages"][0].get("page_index") == descriptor["viewer_page"] - 1,
                       "原生来源页面与原图绑定不一致。")
    return value


def full_endpoints(plan):
    product = plan["product"]
    pages = sorted({p["viewer_page"] for p in product["before"]["pages"].values()})
    result = endpoints((), (), source=True, book_id=product["book_id"])
    for start in range(0, len(pages), 8):
        result.update(endpoints((), pages[start:start + 8], book_id=product["book_id"]))
    for first in range(1, product["before_count"] + 1, 6):
        result.update(endpoints(range(first, min(first + 6, product["before_count"] + 1)), book_id=product["book_id"]))
    return result


def make_wire_plan(product, flat, sources):
    native.check_plan(product)
    native.require(json_same(snapshot(flat, product["book_id"], product["before"]["pages"]), product["before"]), "原生快照与准备计划不一致。")
    value = {"schema": SCHEMA, "operation": "CUSTOMER_SOURCE_BOUND_EXISTING_FILL" if product['schema']=='CustomerNativeExistingFillPlan/v1' else "CUSTOMER_SOURCE_BOUND_INSERT", "book_id": product["book_id"],
             "product": copy.deepcopy(product), "before_full": copy.deepcopy(flat),
             "payload_candidate": copy.deepcopy(product["payload"]), "source_refs": sources,
             "ledger_key": "customer-" + product["key"], "new_order": product["new_order"]}
    native.require(set(flat) == set(full_endpoints(value)), "当前快照响应集合不完整。")
    # The response collection is an application envelope, assembled in batches.
    # Canonical endpoint order does not normalize any native response content.
    value['before_full']={name:copy.deepcopy(flat[name]) for name in full_endpoints(value)}
    value["plan_sha256"] = digest(value)
    verify_evidence(value)
    return value


def validate_insert_plan(plan):
    native.require(type(plan) is dict and plan.get("schema") == SCHEMA, "生产接线计划类型无效。")
    rebuilt = make_wire_plan(plan["product"], plan["before_full"], plan["source_refs"])
    native.require(json_same(rebuilt, plan), "生产接线计划已改变。")


def verify_evidence(plan):
    refs = plan["source_refs"]
    native.require(type(refs) is list and refs, "来源原件引用缺失。")
    hashes = set()
    for ref in refs:
        native.require(set(ref) == {"path", "sha256"} and Path(ref["path"]).is_absolute(), "来源引用无效。")
        native.require(byte_hash(Path(ref["path"]).read_bytes()) == ref["sha256"], "来源原件字节已改变。")
        hashes.add(ref["sha256"])
    native.require(hashes == {f["source_sha256"] for f in plan["product"]["candidate"]["frames"]}, "来源范围不完整或包含无关材料。")


def check_prewrite(plan, flat):
    validate_insert_plan(plan)
    native.require(set(flat)==set(plan['before_full']) and all(json_same(flat[name],plan['before_full'][name]) for name in flat),
                   "保存前当前状态已改变。")
    native.check_prewrite(plan["product"], snapshot(flat, plan["book_id"], plan["product"]["before"]["pages"]))
    return {"ok": True}


def decode_receipt(plan, receipt):
    validate_insert_plan(plan)
    if plan['product']['schema']=='CustomerNativeExistingFillPlan/v1':
        from .existing_fill import decode
        return decode(plan['product'],receipt)
    data = native._response(receipt)
    old_ids = {row["node"]["id"] for row in native.directory_rows(plan["before_full"]["directory"])[0]}
    node = data.get("inserted_question_node")
    native.require(data.get("inserted") is True and data.get("success") is True
                   and type(data.get("question_order")) is int and data["question_order"] == plan["new_order"]
                   and type(node) is dict and type(node.get("id")) is str and node["id"] not in old_ids
                   and node.get("isQuestion") is True and node.get("order_in_level") == str(plan["new_order"]),
                   "插入回执身份未知，禁止重发。")
    return {"ok": True, "node_id": node["id"], "new_order": plan["new_order"]}


def compare_insert_readback(plan, flat, receipt):
    validate_insert_plan(plan)
    return native.compare_readback(plan["product"], snapshot(flat, plan["book_id"], plan["product"]["before"]["pages"]), receipt)
