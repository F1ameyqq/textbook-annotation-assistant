#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 1 · 数据落地（零模型推理，零线上写入）

做三件事：
  1. 读取 46006966 全量人工标注（get_manual_annotations_unified）并原样存档；
  2. 从 OSS 下载被标注引用到的页图 + 重点页（含第 234 页六栏答案图）；
  3. 校验图片真实尺寸，并计算历史框的越界/跨框问题清单（只读分析）。

用法:
  python tools/land_data.py            # 完整跑
  python tools/land_data.py --no-download
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RAW_IMG = os.path.join(DATA, "raw", "images")
RAW_ANN = os.path.join(DATA, "raw", "annotations")
DERIVED = os.path.join(DATA, "derived")

FILE_ID = "46006966"
OSS_BASE = "https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com/upload_images"
# 交接包第 2 节：原图 4 张 = 查看器页 8/9/10/234。
# 实测标注的 page_index 取值就是 {8, 9, 10, 234}，与"0 基资源索引 7/8/9/233"
# 的说法差 1；两种编号都下，落地后用真实像素尺寸判定哪套成立。
PRIORITY_PAGES = [7, 8, 9, 10, 233, 234]
CST = timezone(timedelta(hours=8))

# 本机存档的原始标注响应（读接口 200），只读引用
LEGACY_SOURCES = {
    "netdetail1.json": r"C:\Users\LIHAOYANG\Documents\kimi\tasks\2026-10-15\21-28-40-0b776da9\netdetail1.json",
    "netdetail2.json": r"C:\Users\LIHAOYANG\Documents\kimi\tasks\2026-10-15\21-28-40-0b776da9\netdetail2.json",
    "netdetail3.json": r"C:\Users\LIHAOYANG\Documents\kimi\tasks\2026-10-15\21-28-40-0b776da9\netdetail3.json",
    "savectx.json": r"C:\Users\LIHAOYANG\Documents\kimi\tasks\2026-10-15\21-28-40-0b776da9\savectx.json",
    "workspace1.jpg": r"C:\Users\LIHAOYANG\Documents\kimi\tasks\2026-10-15\21-28-40-0b776da9\workspace1.jpg",
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36 Edg/155.0.0.0")


def log(msg: str) -> None:
    print(msg, flush=True)


def ensure_dirs() -> None:
    for d in (RAW_IMG, RAW_ANN, DERIVED):
        os.makedirs(d, exist_ok=True)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- annotations
def load_legacy_annotations() -> tuple[list[dict], list[dict]]:
    """从本地存档响应里抽出全部标注记录，并把原始文件复制存档。"""
    records: list[dict] = []
    provenance: list[dict] = []

    for name, src in LEGACY_SOURCES.items():
        if not os.path.exists(src):
            provenance.append({"file": name, "source": src, "status": "MISSING"})
            continue
        with open(src, "rb") as fh:
            blob = fh.read()
        dst = os.path.join(RAW_ANN, name)
        with open(dst, "wb") as fh:
            fh.write(blob)
        provenance.append({
            "file": name, "source": src, "status": "COPIED",
            "bytes": len(blob), "sha256": sha256_bytes(blob),
        })

        if not name.startswith("netdetail"):
            continue
        try:
            doc = json.loads(blob.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            provenance[-1]["status"] = f"PARSE_FAIL: {exc}"
            continue
        body = (doc.get("data") or {}).get("body") or {}
        payload = body.get("data")
        if payload is None:
            continue
        # 兼容三种形状：
        #   get_manual_annotations_unified -> data 直接是标注数组
        #   {annotations: [...]}
        #   {pages: [{blocks: [...]}]}
        if isinstance(payload, list):
            anns = [a for a in payload if isinstance(a, dict)]
        elif isinstance(payload, dict):
            anns = payload.get("annotations")
            if anns is None:
                anns = []
                for pg in payload.get("pages", []) or []:
                    for blk in pg.get("blocks", []) or []:
                        anns.append({**blk, "page_index": pg.get("page_index")})
        else:
            continue
        for a in anns:
            a.setdefault("_origin_file", name)
            a.setdefault("_origin_url", (doc.get("data") or {}).get("url"))
        records.extend(anns)
        provenance[-1]["annotations_extracted"] = len(anns)

    # 去重：同一 rect_id 只保留一条
    uniq: dict[str, dict] = {}
    dup = 0
    for a in records:
        key = str(a.get("rect_id"))
        if key in uniq:
            dup += 1
            continue
        uniq[key] = a
    log(f"[annotations] 提取 {len(records)} 条，去重后 {len(uniq)} 条（重复 {dup}）")
    return list(uniq.values()), provenance


def fetch_annotations_live() -> dict:
    """经 WebBridge 会话只读拉取全量人工标注。失败不致命（有本地存档）。"""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    try:
        from bridge import BridgeError, call
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "stage": "import", "error": str(exc)}

    api = (f"https://www.usense.com/qieti/api/annotate_pic/"
           f"get_manual_annotations_unified/{FILE_ID}")
    try:
        tabs = call("list_tabs", {}).get("data", {}).get("tabs", [])
    except BridgeError as exc:
        return {"ok": False, "stage": "list_tabs", "error": str(exc)}

    if not tabs:
        return {"ok": False, "stage": "list_tabs",
                "error": "当前会话无标签页，需先 navigate 到标注平台"}

    try:
        resp = call("fetch", {"url": api, "method": "GET"})
    except BridgeError as exc:
        return {"ok": False, "stage": "fetch", "error": str(exc)}
    return {"ok": bool(resp.get("ok")), "raw": resp}


# ---------------------------------------------------------------------- images
def download_image(page: int, session: requests.Session) -> dict:
    url = f"{OSS_BASE}/{FILE_ID}/{FILE_ID}_page_{page}.jpg"
    out = os.path.join(RAW_IMG, f"{FILE_ID}_page_{page}.jpg")
    rec = {"page_index": page, "url": url, "path": os.path.relpath(out, ROOT)}
    if os.path.exists(out) and os.path.getsize(out) > 0:
        with open(out, "rb") as fh:
            blob = fh.read()
        rec.update(status="CACHED", bytes=len(blob), sha256=sha256_bytes(blob))
        return rec
    t0 = time.time()
    try:
        r = session.get(url, timeout=60)
        rec["http_status"] = r.status_code
        if r.status_code != 200:
            rec["status"] = "HTTP_FAIL"
            return rec
        blob = r.content
        with open(out, "wb") as fh:
            fh.write(blob)
        rec.update(status="OK", bytes=len(blob), sha256=sha256_bytes(blob),
                   elapsed_s=round(time.time() - t0, 2),
                   content_type=r.headers.get("Content-Type"))
        return rec
    except Exception as exc:  # noqa: BLE001
        rec["status"] = f"ERROR: {type(exc).__name__}"
        rec["error"] = str(exc)[:200]
        return rec


def probe_dims(path: str) -> dict:
    """用 PIL 读真实像素尺寸 + 页图是否有嵌入资源线索。"""
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
            info = {"width": w, "height": h, "mode": im.mode,
                    "format": im.format}
            try:
                info["dpi"] = im.info.get("dpi")
            except Exception:  # noqa: BLE001
                pass
            return info
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


# ------------------------------------------------------------- quality checks
def bbox_of(rec: dict) -> tuple[float, float, float, float] | None:
    bb = rec.get("rect_bbox")
    if isinstance(bb, str):
        try:
            parts = [float(x) for x in bb.split(",")]
        except Exception:  # noqa: BLE001
            return None
    elif isinstance(bb, (list, tuple)):
        try:
            parts = [float(x) for x in bb]
        except Exception:  # noqa: BLE001
            return None
    else:
        return None
    return tuple(parts[:4]) if len(parts) >= 4 else None


def intersection(a, b) -> float:
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def area(b) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def quality_report(records: list[dict], dims: dict[int, dict]) -> dict:
    findings: list[dict] = []
    type_counts: dict[str, int] = {}
    page_counts: dict[str, int] = {}
    verified_counts: dict[str, int] = {}

    for r in records:
        t = str(r.get("type"))
        type_counts[t] = type_counts.get(t, 0) + 1
        pg = r.get("page_index")
        page_counts[str(pg)] = page_counts.get(str(pg), 0) + 1
        v = str(r.get("verified"))
        verified_counts[v] = verified_counts.get(v, 0) + 1

    # 1) 越界
    for r in records:
        b = bbox_of(r)
        if b is None:
            findings.append({"kind": "bbox_unparseable", "rect_id": r.get("rect_id"),
                             "raw": r.get("rect_bbox")})
            continue
        pg = r.get("page_index")
        d = dims.get(pg)
        if not d or "width" not in d:
            continue
        w, h = d["width"], d["height"]
        over = []
        if b[0] < 0: over.append(f"x1={b[0]:.2f}<0")
        if b[1] < 0: over.append(f"y1={b[1]:.2f}<0")
        if b[2] > w: over.append(f"x2={b[2]:.2f}>{w} (超 {b[2]-w:.2f}px)")
        if b[3] > h: over.append(f"y3={b[3]:.2f}>{h} (超 {b[3]-h:.2f}px)")
        if over:
            findings.append({
                "kind": "out_of_bounds", "rect_id": r.get("rect_id"),
                "type": r.get("type"), "page_index": pg,
                "bbox": list(b), "image_wh": [w, h], "detail": "; ".join(over),
            })

    # 2) 跨框重叠（同页、不同 type、重叠占较小框比例 > 50%）
    by_page: dict[int, list[dict]] = {}
    for r in records:
        by_page.setdefault(r.get("page_index"), []).append(r)
    for pg, items in by_page.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b_ = items[i], items[j]
                if a.get("type") == b_.get("type"):
                    continue
                ba, bb = bbox_of(a), bbox_of(b_)
                if not ba or not bb:
                    continue
                inter = intersection(ba, bb)
                if inter <= 0:
                    continue
                sa, sb = area(ba), area(bb)
                smaller = min(sa, sb) or 1.0
                ratio = inter / smaller
                if ratio >= 0.5:
                    findings.append({
                        "kind": "cross_type_overlap",
                        "rect_id_a": a.get("rect_id"), "type_a": a.get("type"),
                        "rect_id_b": b_.get("rect_id"), "type_b": b_.get("type"),
                        "page_index": pg, "intersection_px2": round(inter, 2),
                        "ratio_of_smaller": round(ratio, 4),
                        "bbox_a": list(ba), "bbox_b": list(bb),
                    })

    # 3) HTML 残留
    import re
    tag_re = re.compile(r"</?(span|div|p|br|img|a|b|i|em|strong)\b", re.I)
    for r in records:
        txt = json.dumps(r, ensure_ascii=False)
        hits = tag_re.findall(txt)
        if hits:
            findings.append({"kind": "html_residue", "rect_id": r.get("rect_id"),
                             "type": r.get("type"), "tags": sorted(set(hits))})

    return {
        "type_counts": type_counts,
        "page_counts": page_counts,
        "verified_counts": verified_counts,
        "findings": findings,
    }


# ------------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-download", action="store_true")
    args = ap.parse_args()

    ensure_dirs()
    log(f"工作区: {ROOT}")

    records, provenance = load_legacy_annotations()

    # 原样保存合并后的标注快照
    merged = os.path.join(RAW_ANN, "annotations_unified_snapshot.json")
    with open(merged, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)
    log(f"[annotations] 快照 -> {os.path.relpath(merged, ROOT)}")

    # 线上只读复核（有标签页才可能成功）
    live = fetch_annotations_live()
    log(f"[annotations-live] {json.dumps({k: v for k, v in live.items() if k != 'raw'}, ensure_ascii=False)}")

    # 汇总引用的页
    pages = set(PRIORITY_PAGES)
    for r in records:
        if isinstance(r.get("page_index"), int):
            pages.add(r["page_index"])
    pages = sorted(pages)
    log(f"[images] 待下载页（0 基）: {pages}")

    images: list[dict] = []
    if not args.no_download:
        s = requests.Session()
        s.headers.update({"User-Agent": UA})
        for pg in pages:
            rec = download_image(pg, s)
            images.append(rec)
            log(f"  page {pg:>3}: {rec.get('status')} "
                f"{rec.get('bytes', '-')}B")
    else:
        for pg in pages:
            p = os.path.join(RAW_IMG, f"{FILE_ID}_page_{pg}.jpg")
            if os.path.exists(p):
                images.append({"page_index": pg, "status": "PRESENT",
                               "bytes": os.path.getsize(p),
                               "path": os.path.relpath(p, ROOT)})
            else:
                images.append({"page_index": pg, "status": "ABSENT"})

    # 尺寸校验
    dims: dict[int, dict] = {}
    for rec in images:
        p = os.path.join(ROOT, rec.get("path", ""))
        if rec.get("status") in ("OK", "CACHED", "PRESENT") and os.path.exists(p):
            rec["dims"] = probe_dims(p)
            dims[rec["page_index"]] = rec["dims"]
    for rec in images:
        d = rec.get("dims") or {}
        if "width" in d:
            log(f"  page {rec['page_index']:>3}: {d['width']}x{d['height']} {d.get('mode')}")

    qr = quality_report(records, dims)

    manifest = {
        "generated_at": datetime.now(CST).isoformat(),
        "file_id": FILE_ID,
        "book": "0908-171-9787539585406-通城学典课时作业本九年级数学上册（苏科版九年级数学上）",
        "phase": "Phase 1 · 数据落地（零模型推理 / 零线上写入）",
        "annotation_total": len(records),
        "type_counts": qr["type_counts"],
        "page_counts": qr["page_counts"],
        "verified_counts": qr["verified_counts"],
        "images": images,
        "provenance": provenance,
        "finding_count": len(qr["findings"]),
        "findings_by_kind": {},
    }
    for f in qr["findings"]:
        k = f["kind"]
        manifest["findings_by_kind"][k] = manifest["findings_by_kind"].get(k, 0) + 1

    with open(os.path.join(DERIVED, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    with open(os.path.join(DERIVED, "quality_findings.json"), "w", encoding="utf-8") as fh:
        json.dump(qr["findings"], fh, ensure_ascii=False, indent=2)

    log("")
    log("=== 汇总 ===")
    log(f"标注记录: {len(records)}  type={qr['type_counts']}")
    log(f"图片: {len([i for i in images if i.get('status') in ('OK','CACHED','PRESENT')])}/{len(images)} 就绪")
    log(f"verified 分布: {qr['verified_counts']}")
    log(f"质量问题: {manifest['findings_by_kind']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
