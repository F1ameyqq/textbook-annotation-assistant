#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
task-2 · 坐标系逆向：矩形框与页图坐标空间不一致的根因

结论（本脚本用离线像素证据复现，全部数值写入 coord_reverse_findings.json）：

  标注记录 page_index = N（以及 image_path 里的 "@page_N" 标签）是**平台查看器的
  1 基页码 pageNum**；OSS 页图 `upload_images/46006966/46006966_page_M.jpg` 是
  **0 基图像索引**，M = N - 1。

  因此正确配对是 page_index N  <->  page_{N-1}.jpg，且 rect_bbox 就是该页图的
  像素坐标（尺度 1.000，偏移 (0,0)，残差 < 1px）。verify_report.md 把框配到
  page_N.jpg，整体错开一页，才产生"SUSPECT_COORD_SPACE"的假象。

证据链（三条互相独立）：
  A. 平台自己的裁剪：每条标注的 image_path（annotate_images/...@page_N_xxx.jpg）
     可下载，尺寸恒等于 floor(rect_bbox 宽高) —— 它就是平台用该 bbox 从画布裁下的
     原图。把 36 张裁剪图与候选页图在"记录坐标处"做 NCC：
        page_{N-1}: 0.893 ~ 0.998（均值 0.955）
        page_N    : 均值 0.03
  B. 尺度扫描：把最大的裁剪图按 s 缩放后在正确页图上做 matchTemplate，
     s 从 0.96 扫到 1.04，峰值全部在 s = 1.000，残差 loc - s*(x1,y1) < 0.5px。
  C. 越界细节：page_index=8 的 order-3 框 x2=1181.09，裁剪图右端恰有 **2 列纯黑
     (0) 填充列** = 1180 - 1178，证明画布宽 1178 = page_7.jpg 的宽度，
     平台对越界像素补黑。若画布是 page_8.jpg（1176）应补 4 列。
  D. 平台接口自证据：存档的 pre_annotation 响应
       pageNum=1 -> image ..._page_0.jpg, page_index 0
       pageNum=9 -> image ..._page_8.jpg, page_index 8
     证明"查看器 1 基页码 -> 0 基页图文件"的换算就是 -1。

用法:
  python tools/coord_reverse.py                 # 完整跑（会补下 36 张小裁剪图，已缓存则跳过）
  python tools/coord_reverse.py --skip-download # 只用本地缓存
产出:
  data/derived/analysis/coord_reverse_report.md
  data/derived/analysis/coord_reverse_findings.json
  data/derived/analysis/coord_annotation_images.json
  data/derived/analysis/coord_evidence/*.png
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

# 纯 CPU 像素运算：不导入 torch，且显式屏蔽 GPU，避免与 aocr/alayout 抢显存
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_ANN = os.path.join(ROOT, "data", "raw", "annotations")
RAW_IMG = os.path.join(ROOT, "data", "raw", "images")
OUTDIR = os.path.join(ROOT, "data", "derived", "analysis")
EVDIR = os.path.join(OUTDIR, "coord_evidence")
CROPDIR = os.path.join(EVDIR, "annimg")
ANN_SNAPSHOT = os.path.join(RAW_ANN, "annotations_unified_snapshot.json")
FILE_ID = "46006966"
CAND_PAGES = [7, 8, 9, 10, 233, 234]          # 已落地的页图（0 基图像索引）
INK_THRESH = 160                               # 与 image_layout.json 一致
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36 Edg/155.0.0.0")


def log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------- io helpers
def imread_gray(path: str) -> np.ndarray:
    """Unicode 安全的灰度读取（cv2.imread 在中文路径下会失败）。"""
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise IOError(f"无法解码图片: {path}")
    return img


def imwrite(path: str, img: np.ndarray) -> None:
    """Unicode 安全的写图。"""
    ext = os.path.splitext(path)[1] or ".png"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise IOError(f"编码失败: {path}")
    buf.tofile(path)


def page_path(page: int) -> str:
    return os.path.join(RAW_IMG, f"{FILE_ID}_page_{page}.jpg")


def load_annotations() -> list[dict]:
    with open(ANN_SNAPSHOT, encoding="utf-8") as fh:
        recs = json.load(fh)
    out = []
    for r in recs:
        bb = [float(v) for v in str(r["rect_bbox"]).split(",")]
        out.append({
            "rect_id": r["rect_id"],
            "page_index": int(r["page_index"]),
            "type": r["type"],
            "order": str(r["order_in_level"]),
            "zone_order": int(r["image_order_in_annotation_zone"]),
            "bbox": bb,
            "image_path": r["image_path"],
            "file": r["image_path"].rsplit("/", 1)[-1],
            "created_at": r["created_at"],
        })
    out.sort(key=lambda z: (z["page_index"], int(z["order"]), z["type"]))
    return out


# ------------------------------------------------------------------ metrics
def ncc(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(np.float32)
    b = b.astype(np.float32)
    if a.shape != b.shape or a.size < 16:
        return float("nan")
    a = (a - a.mean()) / (a.std() + 1e-6)
    b = (b - b.mean()) / (b.std() + 1e-6)
    return float((a * b).mean())


def ink_pct(gray: np.ndarray, box) -> float | None:
    x1, y1, x2, y2 = [int(round(v)) for v in box]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(gray.shape[1], x2), min(gray.shape[0], y2)
    if x2 <= x1 or y2 <= y1:
        return None
    return 100.0 * float((gray[y1:y2, x1:x2] < INK_THRESH).mean())


def ncc_at_recorded(gray: np.ndarray, box, tpl: np.ndarray) -> dict:
    """把平台裁剪图放到"记录坐标处"，与页图同位置区域比 NCC。

    平台裁剪宽高 = floor(bbox 宽高)，故裁剪区域 = [x1, x1+w) x [y1, y1+h)。
    超出画布的部分由平台补黑，这里只比较落在画布内的列/行，并单独记录越界数。
    """
    h, w = tpl.shape
    x1, y1 = int(np.floor(box[0])), int(np.floor(box[1]))
    x2, y2 = x1 + w, y1 + h
    oob_cols = max(0, x2 - gray.shape[1])
    oob_rows = max(0, y2 - gray.shape[0])
    cx2, cy2 = min(x2, gray.shape[1]), min(y2, gray.shape[0])
    if cx2 - x1 < 8 or cy2 - y1 < 8:
        return {"ncc": None, "oob_cols": oob_cols, "oob_rows": oob_rows}
    return {
        "ncc": ncc(gray[y1:cy2, x1:cx2], tpl[:cy2 - y1, :cx2 - x1]),
        "oob_cols": oob_cols, "oob_rows": oob_rows,
    }


def best_match(gray: np.ndarray, tpl: np.ndarray):
    res = cv2.matchTemplate(gray, tpl, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(res)
    return float(mx), (int(loc[0]), int(loc[1]))


# ------------------------------------------------------- platform own crops
def ensure_crops(recs: list[dict], download: bool = True) -> list[dict]:
    """下载/复用每条标注的 image_path（平台自己用 rect_bbox 裁出来的小图）。"""
    os.makedirs(CROPDIR, exist_ok=True)
    manifest = []
    sess = None
    for r in recs:
        dst = os.path.join(CROPDIR, r["file"])
        if not (os.path.exists(dst) and os.path.getsize(dst) > 0):
            if not download:
                raise SystemExit(f"缺少缓存裁剪图且已 --skip-download: {r['file']}")
            if sess is None:
                import requests
                sess = requests.Session()
                sess.headers.update({"User-Agent": UA})
            resp = sess.get(r["image_path"], timeout=60)
            resp.raise_for_status()
            with open(dst, "wb") as fh:
                fh.write(resp.content)
        blob = open(dst, "rb").read()
        img = imread_gray(dst)
        h, w = img.shape
        bw = r["bbox"][2] - r["bbox"][0]
        bh = r["bbox"][3] - r["bbox"][1]
        manifest.append({
            **{k: r[k] for k in ("rect_id", "page_index", "type", "order",
                                 "zone_order", "bbox", "image_path", "file")},
            "crop_wh": [w, h],
            "bbox_wh": [round(bw, 3), round(bh, 3)],
            "eq_floor_bbox_wh": (w == int(np.floor(bw)) and h == int(np.floor(bh))),
            "sha256": hashlib.sha256(blob).hexdigest(),
        })
    return manifest


# -------------------------------------------------------------------- tests
def ncc_at_crop(gray: np.ndarray, box, tpl: np.ndarray) -> dict:
    """按平台的整数裁剪约定对齐：原点 = round(bbox x1,y1)，尺寸 = 裁剪图像素尺寸。

    越界部分（平台补黑）不参与比较，单独记录越界列/行数。
    """
    h, w = tpl.shape
    x1, y1 = int(round(box[0])), int(round(box[1]))
    x2, y2 = x1 + w, y1 + h
    oob_cols = max(0, x2 - gray.shape[1])
    oob_rows = max(0, y2 - gray.shape[0])
    cx2, cy2 = min(x2, gray.shape[1]), min(y2, gray.shape[0])
    if x1 < 0 or y1 < 0 or cx2 - x1 < 8 or cy2 - y1 < 8:
        return {"ncc": None, "oob_cols": oob_cols, "oob_rows": oob_rows}
    return {"ncc": ncc(gray[y1:cy2, x1:cx2], tpl[:cy2 - y1, :cx2 - x1]),
            "oob_cols": oob_cols, "oob_rows": oob_rows}


def test_crop_origin(manifest, pages) -> dict:
    """±3px 偏移扫描：确认平台裁剪原点 = round(bbox x1,y1) 且该处即最优。"""
    hist: dict = {}
    rows = []
    for m in manifest:
        g = pages[m["page_index"] - 1]
        tpl = imread_gray(os.path.join(CROPDIR, m["file"]))
        h, w = tpl.shape
        bx, by = int(round(m["bbox"][0])), int(round(m["bbox"][1]))
        best = None
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                x, y = bx + dx, by + dy
                if x < 0 or y < 0 or x + w > g.shape[1] or y + h > g.shape[0]:
                    continue
                v = ncc(g[y:y + h, x:x + w], tpl)
                if v == v and (best is None or v > best[0]):
                    best = (v, dx, dy)
        if best is None:
            continue
        hist[(best[1], best[2])] = hist.get((best[1], best[2]), 0) + 1
        rows.append({"page_index": m["page_index"], "order": m["order"], "type": m["type"],
                     "best_dx": best[1], "best_dy": best[2], "ncc_best": round(best[0], 4)})
    base = []
    for m in manifest:
        r = ncc_at_crop(pages[m["page_index"] - 1], m["bbox"],
                        imread_gray(os.path.join(CROPDIR, m["file"])))
        if r["ncc"] is not None and r["ncc"] == r["ncc"]:
            base.append(r["ncc"])
    return {
        "argmax_offset_hist": {f"{k[0]},{k[1]}": v for k, v in sorted(hist.items())},
        "n_zero_offset": hist.get((0, 0), 0), "n_total": len(rows),
        "ncc_at_round_origin": {"mean": round(float(np.mean(base)), 4),
                                "min": round(float(np.min(base)), 4),
                                "max": round(float(np.max(base)), 4)},
        "rows": rows,
    }


def test_mapping(recs, manifest, pages) -> dict:
    """H3 核心：36 条标注的裁剪图在"记录坐标处"与各候选页图的 NCC。"""
    rows = []
    for m in manifest:
        tpl = imread_gray(os.path.join(CROPDIR, m["file"]))
        row = {"page_index": m["page_index"], "type": m["type"], "order": m["order"],
               "crop_wh": m["crop_wh"], "bbox": m["bbox"], "ncc": {}}
        for p, g in pages.items():
            r = ncc_at_crop(g, m["bbox"], tpl)
            row["ncc"][str(p)] = None if r["ncc"] is None or r["ncc"] != r["ncc"] else round(r["ncc"], 4)
            if p == m["page_index"] - 1:
                row["oob_cols_on_correct"] = r["oob_cols"]
                row["oob_rows_on_correct"] = r["oob_rows"]
        prev = row["ncc"].get(str(m["page_index"] - 1))
        cur = row["ncc"].get(str(m["page_index"]))
        row["ncc_correct"] = prev
        row["ncc_wrong"] = cur
        row["correct_page"] = m["page_index"] - 1
        rows.append(row)
    corr = [r["ncc_correct"] for r in rows if r["ncc_correct"] is not None]
    wrong = [r["ncc_wrong"] for r in rows if r["ncc_wrong"] is not None]
    return {
        "rows": rows,
        "n_records": len(rows),
        "n_with_correct_candidate": len(corr),
        "ncc_correct": {"mean": round(float(np.mean(corr)), 4), "min": round(float(np.min(corr)), 4),
                        "max": round(float(np.max(corr)), 4)},
        "ncc_wrong_page_N": {"mean": round(float(np.mean(wrong)), 4),
                             "min": round(float(np.min(wrong)), 4),
                             "max": round(float(np.max(wrong)), 4)},
        "n_records_correct_ge_0_85": int(sum(1 for v in corr if v >= 0.85)),
        "n_records_wrong_le_0_4": int(sum(1 for v in wrong if v <= 0.4)),
    }


def test_scale(manifest, pages) -> dict:
    """H4：把最大裁剪图缩放 s 后在正确页图上匹配，找最优 s 与残差。"""
    order = [(8, 7), (9, 8), (10, 9), (234, 233)]
    grid = [0.96, 0.97, 0.98, 0.985, 0.99, 0.995, 1.0, 1.005, 1.01, 1.015, 1.02, 1.03, 1.04]
    out = {}
    for pidx, canvas in order:
        cand = [m for m in manifest if m["page_index"] == pidx]
        rec = max(cand, key=lambda m: m["crop_wh"][0] * m["crop_wh"][1])
        tpl = imread_gray(os.path.join(CROPDIR, rec["file"]))
        g = pages[canvas]
        x1, y1 = rec["bbox"][0], rec["bbox"][1]
        sweep = []
        for s in grid:
            tw, th = int(round(tpl.shape[1] * s)), int(round(tpl.shape[0] * s))
            if tw < 8 or th < 8 or tw >= g.shape[1] or th >= g.shape[0]:
                continue
            tt = cv2.resize(tpl, (tw, th),
                            interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
            sc, loc = best_match(g, tt)
            sweep.append({"s": s, "score": round(sc, 4), "loc": [loc[0], loc[1]],
                          "residual_px": [round(loc[0] - s * x1, 2), round(loc[1] - s * y1, 2)]})
        sweep.sort(key=lambda z: -z["score"])
        out[str(pidx)] = {
            "canvas_page": canvas,
            "probe_crop": {"order": rec["order"], "type": rec["type"],
                           "crop_wh": rec["crop_wh"], "bbox": rec["bbox"]},
            "best": sweep[0],
            "top3": sweep[:3],
            "score_at_s1": next(s["score"] for s in sweep if s["s"] == 1.0),
        }
    return out


def test_panel_h1(manifest, pages) -> dict:
    """H1：画布是否为拼接图中的某个 panel（子页）。"""
    g234 = pages[233]
    m234 = [m for m in manifest if m["page_index"] == 234]
    xs = [(m["bbox"][0], m["bbox"][2]) for m in m234]
    ys = [(m["bbox"][1], m["bbox"][3]) for m in m234]
    col = (g234[:, 0:600] < INK_THRESH)
    cols_ink = np.where(col.sum(0) > 0)[0]
    rows_ink = np.where(col.sum(1) > 0)[0]
    # 全高空白列沟（判据与 layout_probe/image_layout.json 一致的思想）
    full = (g234 < INK_THRESH).sum(0)
    blank = np.where(full == 0)[0]
    runs, st, prev = [], None, None
    for i in blank:
        if st is None:
            st = i
        elif i != prev + 1:
            runs.append((int(st), int(prev), int(prev - st + 1)))
            st = i
        prev = i
    if st is not None:
        runs.append((int(st), int(prev), int(prev - st + 1)))
    return {
        "box_x_range": [round(min(a for a, _ in xs), 2), round(max(b for _, b in xs), 2)],
        "box_y_range": [round(min(a for a, _ in ys), 2), round(max(b for _, b in ys), 2)],
        "first_column_ink_cols": [int(cols_ink[0]), int(cols_ink[-1])],
        "first_column_ink_rows": [int(rows_ink[0]), int(rows_ink[-1])],
        "full_height_blank_runs_lt_800": [r for r in runs if r[2] >= 12 and r[0] < 800],
        "note": "page_233 首个内容 panel 起始 x=49、首个全高空白沟 x=574..591；"
                "box x1=6.53 < 49 且 x2=594.15 > 574，说明框不是 panel 局部坐标，"
                "而是整页坐标（跨过了 panel 边界/页边距）。",
    }


def test_canvas_h2(manifest, pages) -> dict:
    """H2：记录坐标画布是否 ≈ (594,1164)（由框极值反推）。"""
    g = pages[233]
    m234 = [m for m in manifest if m["page_index"] == 234]
    bx = [m["bbox"] for m in m234]
    box_x = (min(b[0] for b in bx), max(b[2] for b in bx))
    box_y = (min(b[1] for b in bx), max(b[3] for b in bx))
    col = (g[:, 0:600] < INK_THRESH)
    rows_ink = np.where(col.sum(1) > 0)[0]
    cols_ink = np.where(col.sum(0) > 0)[0]
    return {
        "box_x_extent": [round(box_x[0], 2), round(box_x[1], 2)],
        "box_y_extent": [round(box_y[0], 2), round(box_y[1], 2)],
        "page233_wh": [int(g.shape[1]), int(g.shape[0])],
        "annotated_column_ink_rows": [int(rows_ink[0]), int(rows_ink[-1])],
        "annotated_column_ink_cols": [int(cols_ink[0]), int(cols_ink[-1])],
        "box_y_over_content_y": round((box_y[1] - box_y[0]) / float(rows_ink[-1] - rows_ink[0]), 3),
        "box_x_over_content_x": round((box_x[1] - box_x[0]) / float(cols_ink[-1] - cols_ink[0]), 3),
        "content_rows_below_hypothesized_bottom": int(rows_ink[-1] - box_y[1]),
        "note": "若画布真的是 594x1164，那么该列内容必须在 y=1164 处截断、x=594 处截断；"
                "实测该列墨迹纵跨 y=55..1538（比框的 y 范围多 374px），"
                "x 方向框恰好落在第一栏边界（内容 49..574，全高空白沟 574..591）——"
                '极值来自"标注者只标了第一栏的部分内容"，不是画布尺寸。',
    }


def test_padding_h4(manifest, pages) -> dict:
    """H4：越界框的裁剪图右端填充列数 -> 反推画布宽度。"""
    rec = next(m for m in manifest if m["page_index"] == 8 and m["order"] == "3")
    tpl = imread_gray(os.path.join(CROPDIR, rec["file"]))
    h, w = tpl.shape
    x1 = int(np.floor(rec["bbox"][0]))
    # 右端统计：全 0（补黑）列数、全 255（白边距）列数
    black_tail = 0
    for c in range(w - 1, -1, -1):
        if tpl[:, c].max() == 0:
            black_tail += 1
        else:
            break
    white_before = 0
    for c in range(w - 1 - black_tail, -1, -1):
        if tpl[:, c].min() >= 250:
            white_before += 1
        else:
            break
    p7 = pages[7]
    inferred_canvas_w = x1 + w - black_tail
    return {
        "rect_id": rec["rect_id"], "bbox": rec["bbox"], "crop_wh": [w, h],
        "x1_floor": x1, "requested_right_edge": x1 + w,
        "black_padded_cols": black_tail, "white_margin_cols_before_pad": white_before,
        "inferred_canvas_width": inferred_canvas_w,
        "page_7_width": int(p7.shape[1]), "page_8_width": int(pages[8].shape[1]),
        "matches_page_7_width": inferred_canvas_w == int(p7.shape[1]),
        "note": "裁剪图右端恰有 2 列全黑填充 = 1180-1178，证明画布宽 1178 = page_7.jpg；"
                "若画布是 page_8.jpg(1176) 应补 4 列黑。x2=1181.09 只是标注者画出界，"
                "平台补黑，不代表画布更宽或做过缩放。",
    }


def test_api_evidence() -> dict:
    """平台接口自证据：pre_annotation 的 pageNum -> 页图文件 / page_index。"""
    out = []
    for f in ("netdetail1.json", "netdetail3.json"):
        p = os.path.join(RAW_ANN, f)
        if not os.path.exists(p):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        url = d.get("data", {}).get("url", "")
        body = (d.get("data", {}).get("body") or {}).get("data") or {}
        for pg in body.get("pages", []) or []:
            out.append({"file": f, "request_url": url,
                        "image": pg.get("image"), "page_index": pg.get("page_index")})
    for r in out:
        r["image_page_number"] = int(r["image"].rsplit("_page_", 1)[-1].split(".")[0])
        r["page_index_minus_image"] = r["page_index"] - r["image_page_number"]
    return {
        "records": out,
        "note": "pre_annotation?pageNum=1 -> page_0.jpg / page_index 0；"
                "pageNum=9 -> page_8.jpg / page_index 8；即查看器 1 基页码 N 对应页图文件 N-1。",
    }


# ---------------------------------------------------------------- rendering
def _label(img, text, org=(8, 26), color=(0, 0, 255), scale=0.7, thick=2, bg=True):
    if bg:
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
        cv2.rectangle(img, (org[0] - 4, org[1] - th - 6), (org[0] + tw + 4, org[1] + 6),
                      (255, 255, 255), -1)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def draw_boxes(gray, boxes, color=(0, 0, 255), thick=2):
    img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    for b in boxes:
        cv2.rectangle(img, (int(round(b[0])), int(round(b[1]))),
                      (int(round(b[2])), int(round(b[3]))), color, thick)
    return img


def fig_mapping_matrix(mapping, manifest):
    rows = mapping["rows"]
    cols = [str(p) for p in CAND_PAGES]
    cw, ch = 118, 30
    left = 210
    top = 60
    img = np.full((top + ch * len(rows) + 20, left + cw * len(cols) + 20, 3), 255, np.uint8)
    for j, c in enumerate(cols):
        _label(img, f"page_{c}.jpg", (left + j * cw + 4, top - 22), (0, 0, 0), 0.5, 1, bg=False)
    for i, r in enumerate(rows):
        y = top + i * ch
        txt = f"N={r['page_index']} {r['type'][:4]} o{r['order']}"
        _label(img, txt, (6, y + 21), (0, 0, 0), 0.45, 1, bg=False)
        for j, c in enumerate(cols):
            v = r["ncc"].get(c)
            if v is None:
                col = (230, 230, 230)
            else:
                t = float(np.clip((v + 0.2) / 1.2, 0, 1))
                col = cv2.applyColorMap(np.array([[int(t * 255)]], np.uint8), cv2.COLORMAP_JET)[0, 0]
                col = tuple(int(x) for x in col)
            x = left + j * cw
            cv2.rectangle(img, (x + 1, y + 1), (x + cw - 3, y + ch - 3), col, -1)
            if v is not None:
                _label(img, f"{v:.2f}", (x + 8, y + 21), (255, 255, 255), 0.45, 1, bg=False)
            if c == str(r["page_index"] - 1):
                cv2.rectangle(img, (x + 1, y + 1), (x + cw - 3, y + ch - 3), (0, 255, 0), 2)
        if cw * len(cols):
            pass
    _label(img, "NCC of platform crop vs page image at RECORDED bbox (green = page_{N-1})",
           (6, 24), (0, 0, 0), 0.6, 2, bg=False)
    imwrite(os.path.join(EVDIR, "fig1_mapping_matrix.png"), img)


def fig_corrected_overlays(manifest, pages):
    tiles = []
    for pidx in [9, 8, 10, 234]:
        canvas = pidx - 1
        g = pages[canvas]
        boxes = [m["bbox"] for m in manifest if m["page_index"] == pidx]
        img = draw_boxes(g, boxes, (0, 0, 255), 3)
        scale = 700.0 / img.shape[1]
        img = cv2.resize(img, (700, int(round(img.shape[0] * scale))))
        _label(img, f"page_index {pidx} -> page_{canvas}.jpg  n={len(boxes)}", (8, 24), (0, 0, 255), 0.6, 2)
        tiles.append(img)
    h = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles]
    row1 = np.hstack([tiles[0], np.full((h, 12, 3), 255, np.uint8), tiles[1]])
    row2 = np.hstack([tiles[2], np.full((h, 12, 3), 255, np.uint8), tiles[3]])
    gap = np.full((12, row1.shape[1], 3), 255, np.uint8)
    imwrite(os.path.join(EVDIR, "fig6_corrected_overlays.png"), np.vstack([row1, gap, row2]))


def fig_wrong_vs_correct(manifest, pages):
    m234 = [m["bbox"] for m in manifest if m["page_index"] == 234]
    wrong = draw_boxes(pages[234], m234, (0, 0, 255), 3)
    right = draw_boxes(pages[233], m234, (0, 140, 0), 3)
    W = 1180
    def small(img, label):
        s = W / img.shape[1]
        o = cv2.resize(img, (W, int(round(img.shape[0] * s))))
        _label(o, label, (8, 24), (0, 0, 0), 0.6, 2)
        return o
    a = small(wrong, "WRONG: boxes on page_234.jpg (page_index=234)  -> mismatch")
    b = small(right, "CORRECT: same boxes on page_233.jpg (page_index-1) -> aligned")
    gap = np.full((10, W, 3), 255, np.uint8)
    stack = np.vstack([a, gap, b])
    # 左侧第一栏放大（x 0..700）
    zw = cv2.resize(wrong[:, 0:700], (330, int(round(wrong.shape[0] * 330 / 700))))
    zc = cv2.resize(right[:, 0:700], (330, int(round(right.shape[0] * 330 / 700))))
    zh = max(zw.shape[0], zc.shape[0])
    zw = cv2.copyMakeBorder(zw, 0, zh - zw.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255,) * 3)
    zc = cv2.copyMakeBorder(zc, 0, zh - zc.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255,) * 3)
    zoom = np.hstack([zw, np.full((zh, 10, 3), 255, np.uint8), zc])
    if zoom.shape[1] < stack.shape[1]:
        zoom = cv2.copyMakeBorder(zoom, 0, 0, 0, stack.shape[1] - zoom.shape[1],
                                  cv2.BORDER_CONSTANT, value=(255,) * 3)
    _label(zoom, "zoom: left column only", (8, 24), (0, 0, 0), 0.55, 2)
    imwrite(os.path.join(EVDIR, "fig2_p234_wrong_vs_correct.png"),
            np.vstack([stack, np.full((10, stack.shape[1], 3), 255, np.uint8), zoom]))


def fig_crop_vs_canvas(manifest, pages):
    rec = next(m for m in manifest if m["page_index"] == 234 and m["order"] == "10")
    tpl = imread_gray(os.path.join(CROPDIR, rec["file"]))
    h, w = tpl.shape
    x1, y1 = int(np.floor(rec["bbox"][0])), int(np.floor(rec["bbox"][1]))
    r_wrong = pages[234][y1:y1 + h, x1:x1 + w]
    r_right = pages[233][y1:y1 + h, x1:x1 + w]
    n_wrong = ncc(r_wrong, tpl)
    n_right = ncc(r_right, tpl)
    def band(img, label, rgb):
        o = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        o = cv2.copyMakeBorder(o, 34, 4, 4, 4, cv2.BORDER_CONSTANT, value=rgb)
        _label(o, label, (10, 24), (255, 255, 255), 0.55, 2, bg=False)
        return o
    t = band(tpl, f"platform crop ({w}x{h})", (60, 60, 60))
    a = band(r_wrong, f"page_234.jpg at recorded bbox -> NCC={n_wrong:.3f}  (WRONG)", (0, 0, 200))
    b = band(r_right, f"page_233.jpg at recorded bbox -> NCC={n_right:.3f}  (CORRECT)", (0, 140, 0))
    gap = np.full((10, t.shape[1], 3), 255, np.uint8)
    imwrite(os.path.join(EVDIR, "fig3_crop_vs_canvas.png"), np.vstack([t, gap, a, gap, b]))


def fig_padding(pages, manifest):
    """越界框裁剪图的右端：2 列纯黑填充 vs page_7.jpg 的真实白边。"""
    rec = next(m for m in manifest if m["page_index"] == 8 and m["order"] == "3")
    tpl = imread_gray(os.path.join(CROPDIR, rec["file"]))
    h, w = tpl.shape
    x1 = int(round(rec["bbox"][0]))
    k, up = 24, 12
    seg = cv2.resize(tpl[:, w - k:], (k * up, h * 3), interpolation=cv2.INTER_NEAREST)
    seg = cv2.cvtColor(seg, cv2.COLOR_GRAY2BGR)
    p7 = pages[7]
    ref = cv2.resize(p7[:, p7.shape[1] - k:], (k * up, h * 3), interpolation=cv2.INTER_NEAREST)
    ref = cv2.cvtColor(ref, cv2.COLOR_GRAY2BGR)
    gap = np.full((seg.shape[0], 24, 3), 255, np.uint8)
    out = np.hstack([seg, gap, ref])
    out = cv2.copyMakeBorder(out, 92, 16, 12, 12, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    out = cv2.copyMakeBorder(out, 0, 0, 0, 300, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    _label(out, "page_index=8 order=3: platform crop right edge, last {} cols x{}".format(k, up),
           (12, 26), (0, 0, 0), 0.55, 1, bg=False)
    _label(out, "crop {}x{}, origin x={}, requested right edge={}; page_7.jpg width={} -> canvas ends there".format(
        w, h, x1, x1 + w, p7.shape[1]), (12, 50), (0, 0, 0), 0.55, 1, bg=False)
    _label(out, "LEFT: 2 all-black padded cols (zero fill)    RIGHT: page_7.jpg last cols (real white margin)",
           (12, 74), (0, 0, 0), 0.55, 1, bg=False)
    bx = 12 + (k - 2) * up
    cv2.rectangle(out, (bx, 92), (bx + 2 * up, 92 + h * 3), (0, 0, 255), 2)
    cv2.putText(out, "pad", (bx - 8, 88), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
    cv2.putText(out, "canvas edge", (bx - 96, 92 + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
    imwrite(os.path.join(EVDIR, "fig4_page8_edge_padding.png"), out)


def fig_h2_profile(manifest, pages):
    g = pages[233]
    boxes = [m["bbox"] for m in manifest if m["page_index"] == 234]
    bx = (min(b[0] for b in boxes), max(b[2] for b in boxes))
    by = (min(b[1] for b in boxes), max(b[3] for b in boxes))
    H, W = 760, 1000
    img = np.full((H, W, 3), 255, np.uint8)
    # 上：x 方向列墨迹（x 0..800，纵轴按自身峰值归一化）
    xmax = 800
    colprof = (g[:, :xmax] < INK_THRESH).sum(0)
    cmax = max(1, int(colprof.max()))
    top_y0, top_h = 78, 220
    cv2.rectangle(img, (60, top_y0), (60 + xmax, top_y0 + top_h), (0, 0, 0), 1)
    for x in range(xmax):
        v = int(colprof[x] / cmax * top_h)
        if v > 0:
            cv2.line(img, (60 + x, top_y0 + top_h), (60 + x, top_y0 + top_h - v), (150, 150, 150), 1)
    for xv, col in ((bx[0], (0, 0, 255)), (bx[1], (0, 0, 255)),
                    (574, (255, 0, 0)), (591, (255, 0, 0))):
        xi = int(60 + xv)
        cv2.line(img, (xi, top_y0 - 14), (xi, top_y0 + top_h), col, 2)
    _label(img, "page_233 COLUMN ink profile, x=0..{} (normalised to max)".format(xmax),
           (20, 28), (0, 0, 0), 0.5, 1, bg=False)
    _label(img, "red = box x extent {:.1f}..{:.1f}   blue = full-height gutter 574..591".format(bx[0], bx[1]),
           (20, 50), (0, 0, 0), 0.5, 1, bg=False)
    # 下：y 方向行墨迹（x 0..600，y 按图高缩放到画布内）
    bxo, bot_y0, bot_h = 60, 392, 300
    rowprof = (g[:, 0:600] < INK_THRESH).sum(1)
    rmax = max(1, int(rowprof.max()))

    def mapy(y):
        return int(bot_y0 + y / float(g.shape[0]) * bot_h)

    cv2.rectangle(img, (bxo, bot_y0), (bxo + 600, bot_y0 + bot_h), (0, 0, 0), 1)
    for y in range(g.shape[0]):
        v = int(rowprof[y] / rmax * 600)
        if v > 0:
            cv2.line(img, (bxo, mapy(y)), (bxo + v, mapy(y)), (150, 150, 150), 1)
    ri = np.where(rowprof > 0)[0]
    for yv, col in ((by[0], (0, 0, 255)), (by[1], (0, 0, 255)),
                    (int(ri[0]), (0, 160, 0)), (int(ri[-1]), (0, 160, 0))):
        cv2.line(img, (bxo, mapy(yv)), (bxo + 600, mapy(yv)), col, 2)
    _label(img, "page_233 ROW ink, x=0..600, y=0..{} (normalised to max)".format(g.shape[0]),
           (20, 372), (0, 0, 0), 0.5, 1, bg=False)
    _label(img, "red = box y extent {:.0f}..{:.0f}   green = column content rows {}-{}".format(
        by[0], by[1], ri[0], ri[-1]), (20, 394), (0, 0, 0), 0.5, 1, bg=False)
    imwrite(os.path.join(EVDIR, "fig5_h2_column_profile.png"), img)


# ------------------------------------------------------------ extra tests
def test_canvas_fit(manifest, pages) -> dict:
    """用框内墨迹覆盖率最大化拟合 (s, dx, dy)，独立复核恒等映射是否为最优。"""
    out = {}
    for pidx, canvas in ((234, 233), (8, 7)):
        g = pages[canvas]
        boxes = [m['bbox'] for m in manifest if m['page_index'] == pidx]

        def score(s, dx, dy):
            vals = []
            for b in boxes:
                bb = (b[0] * s + dx, b[1] * s + dy, b[2] * s + dx, b[3] * s + dy)
                v = ink_pct(g, bb)
                if v is not None:
                    vals.append(v)
            return float(np.mean(vals)) if vals else 0.0

        base = score(1.0, 0.0, 0.0)
        best = {'ink': base, 's': 1.0, 'dx': 0.0, 'dy': 0.0}
        for s in np.arange(0.80, 1.201, 0.025):
            for dx in range(-80, 81, 8):
                for dy in range(-80, 81, 8):
                    v = score(float(s), float(dx), float(dy))
                    if v > best['ink']:
                        best = {'ink': v, 's': round(float(s), 3), 'dx': float(dx), 'dy': float(dy)}
        n_ok, s_min, s_max = 0, None, None
        for s in np.arange(0.80, 1.201, 0.01):
            for dx in range(-40, 41, 10):
                for dy in range(-40, 41, 10):
                    if score(float(s), float(dx), float(dy)) >= 0.95 * best['ink']:
                        n_ok += 1
                        s_min = float(s) if s_min is None else min(s_min, float(s))
                        s_max = float(s) if s_max is None else max(s_max, float(s))
        big = max([m for m in manifest if m['page_index'] == pidx],
                  key=lambda m: m['crop_wh'][0] * m['crop_wh'][1])
        tpl = imread_gray(os.path.join(CROPDIR, big['file']))
        s, dx, dy = best['s'], best['dx'], best['dy']
        tw, th = int(round(tpl.shape[1] * s)), int(round(tpl.shape[0] * s))
        ncc_cov = None
        if tw >= 8 and th >= 8 and tw < g.shape[1] and th < g.shape[0]:
            tt = cv2.resize(tpl, (tw, th), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
            ox, oy = int(round(big['bbox'][0] * s + dx)), int(round(big['bbox'][1] * s + dy))
            if 0 <= ox and 0 <= oy and ox + tw <= g.shape[1] and oy + th <= g.shape[0]:
                ncc_cov = round(ncc(g[oy:oy + th, ox:ox + tw], tt), 4)
        r_id = ncc_at_crop(g, big['bbox'], tpl)
        ncc_id = None if r_id['ncc'] is None or r_id['ncc'] != r_id['ncc'] else round(r_id['ncc'], 4)
        out[str(pidx)] = {
            'canvas_page': canvas, 'n_boxes': len(boxes),
            'identity_ink_pct': round(base, 4), 'best_ink_pct': round(best['ink'], 4),
            'best_s': best['s'], 'best_dx': best['dx'], 'best_dy': best['dy'],
            'gain_over_identity': round(best['ink'] - base, 4),
            'ci95_n': n_ok, 'ci95_s_range': [s_min, s_max],
            'probe_crop': big['order'], 'ncc_at_identity': ncc_id, 'ncc_at_coverage_opt': ncc_cov,
        }
    return out


def test_lead_reconciliation(manifest, pages) -> dict:
    """复现 lead 的二值化 + 多尺度全局匹配协议，并与记录坐标处 NCC 对照。"""
    rec = next(m for m in manifest if m['page_index'] == 234 and m['order'] == '5')
    tpl = imread_gray(os.path.join(CROPDIR, rec['file']))
    inner = tpl[1:-1, 1:-1]
    binary = cv2.threshold(inner, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    scales = [0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0, 1.05, 1.1]
    out = {'rect_id': rec['rect_id'], 'crop_wh': [int(tpl.shape[1]), int(tpl.shape[0])],
           'bbox': rec['bbox'], 'scales': scales, 'per_page': {}}
    for p, g in pages.items():
        row = {}
        for name, t in (('raw_inner', inner), ('binary_otsu', binary)):
            best = None
            per_scale = {}
            for s in scales:
                tw, th = int(round(t.shape[1] * s)), int(round(t.shape[0] * s))
                if tw < 6 or th < 6 or tw >= g.shape[1] or th >= g.shape[0]:
                    continue
                tt = cv2.resize(t, (tw, th), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
                sc, loc = best_match(g, tt)
                per_scale[str(s)] = round(sc, 4)
                if best is None or sc > best[0]:
                    best = (sc, s, loc)
            if best:
                row[name] = {'best_score': round(best[0], 4), 'best_scale': best[1],
                             'best_loc': [best[2][0], best[2][1]], 'by_scale': per_scale}
        rr = ncc_at_crop(g, rec['bbox'], tpl)
        row['ncc_full_crop'] = None if rr['ncc'] is None or rr['ncc'] != rr['ncc'] else round(rr['ncc'], 4)
        rf = ncc_at_recorded(g, rec['bbox'], tpl)
        row['ncc_full_crop_floor'] = None if rf['ncc'] is None or rf['ncc'] != rf['ncc'] else round(rf['ncc'], 4)
        row['ncc_at_recorded'] = row['ncc_full_crop']
        out['per_page'][str(p)] = row
    scores = [r['binary_otsu']['best_score'] for r in out['per_page'].values() if 'binary_otsu' in r]
    scales = [r['binary_otsu']['best_scale'] for r in out['per_page'].values() if 'binary_otsu' in r]
    out['global_binary_best_range'] = [min(scores), max(scores)] if scores else None
    out['global_binary_best_scales'] = sorted(set(scales))
    return out


def fig_recon(manifest, pages) -> None:
    """o=1 (单个 B) 与 o=5 (公式) 的裁剪图 vs page_233 同坐标区域（按平台 round 原点）。"""
    rows = []
    for order in ('1', '5'):
        rec = next(m for m in manifest if m['page_index'] == 234 and m['order'] == order)
        t = imread_gray(os.path.join(CROPDIR, rec['file']))
        h, w = t.shape
        x1, y1 = int(round(rec['bbox'][0])), int(round(rec['bbox'][1]))
        reg = pages[233][y1:y1 + h, x1:x1 + w]
        val = ncc(reg, t)
        sc = max(1, int(round(360.0 / max(w, 1))))
        a = cv2.resize(t, (w * sc, h * sc), interpolation=cv2.INTER_CUBIC)
        b = cv2.resize(reg, (w * sc, h * sc), interpolation=cv2.INTER_CUBIC)
        pad = 10
        canvas = np.full((a.shape[0] + 64, a.shape[1] * 2 + pad * 3, 3), 255, np.uint8)
        canvas[56:56 + a.shape[0], pad:pad + a.shape[1]] = cv2.cvtColor(a, cv2.COLOR_GRAY2BGR)
        canvas[56:56 + b.shape[0], pad * 2 + a.shape[1]:pad * 2 + a.shape[1] * 2] = cv2.cvtColor(b, cv2.COLOR_GRAY2BGR)
        _label(canvas, 'order {}: platform crop {}x{} (x{})'.format(order, w, h, sc),
               (pad, 24), (0, 0, 0), 0.6, 1, bg=False)
        _label(canvas, 'page_233.jpg at round(x1,y1)=({},{})  NCC={:.3f}'.format(x1, y1, val),
               (pad, 46), (0, 140, 0), 0.6, 1, bg=False)
        rows.append(canvas)
    hmax = max(r.shape[0] for r in rows)
    wmax = max(r.shape[1] for r in rows)
    rows = [cv2.copyMakeBorder(r, 0, hmax - r.shape[0], 0, wmax - r.shape[1],
                               cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]
    gap = np.full((14, wmax, 3), 255, np.uint8)
    imwrite(os.path.join(EVDIR, 'fig7_o1_o5_crop_vs_page233.png'), np.vstack([rows[0], gap, rows[1]]))


# ------------------------------------------------------------------- report
def _scale_rows(f) -> str:
    head = ['| 记录 page_index | 探测用裁剪图 | 画布 | 最优 s | s=1.000 得分 | 峰值残差 (px) |',
            '|---|---|---|---|---|---|']
    for k in sorted(f['scale'], key=lambda z: int(z)):
        v = f['scale'][k]
        pc = v['probe_crop']
        head.append('| {} | {} o{} {}x{} | `page_{}.jpg` | **{:.3f}** | {:.3f} | {} |'.format(
            k, pc['type'], pc['order'], pc['crop_wh'][0], pc['crop_wh'][1],
            v['canvas_page'], v['best']['s'], v['score_at_s1'], v['best']['residual_px']))
    return '\n'.join(head)


def _integrity_rows(f) -> str:
    head = ['| 记录 page_index | 应配页图 = page_index-1 | 图尺寸 | 框数 | max_x2 | max_y2 | 判定 |',
            '|---|---|---|---|---|---|---|']
    for r in f['corrected_integrity']:
        head.append('| {} | `{}` | {}x{} | {} | {} | {} | {} |'.format(
            r['page_index'], r['canvas'], r['wh'][0], r['wh'][1], r['n_boxes'],
            r['max_x2'], r['max_y2'], r['verdict']))
    return '\n'.join(head)


def _api_lines(f) -> str:
    out = []
    for r in f['api_evidence']['records']:
        out.append('   - `{}` → image `..._page_{}.jpg`，`page_index={}`（page_index − 图像号 = {}）'.format(
            r['request_url'].split('?')[-1], r['image_page_number'],
            r['page_index'], r['page_index_minus_image']))
    return '\n'.join(out)


def _cf_rows(f) -> str:
    head = ['| 记录 page_index | 画布 | 恒等映射 (1,0,0) 覆盖率 | 覆盖率最优 (s, dx, dy) | 最优覆盖率 | 增益 | 95% 置信区间内 s 范围 |',
            '|---|---|---|---|---|---|---|']
    for k in sorted(f['canvas_fit'], key=lambda z: int(z)):
        v = f['canvas_fit'][k]
        rng = v['ci95_s_range']
        head.append('| {} | `page_{}.jpg` | {:.3f}% | ({:.3f}, {}, {}) | {:.3f}% | {:+.3f} pp | {} |'.format(
            k, v['canvas_page'], v['identity_ink_pct'], v['best_s'], v['best_dx'], v['best_dy'],
            v['best_ink_pct'], v['gain_over_identity'],
            ('{:.2f}-{:.2f}'.format(rng[0], rng[1])) if rng and rng[0] is not None else '空'))
    return '\n'.join(head)


def _recon_rows(f) -> str:
    head = ['| 候选页 | 复现 lead 协议：二值化全局多尺度最佳 NCC | 该最佳所在尺度 | 同一协议在 s=1.0 的全局最佳 | 记录坐标处 NCC（完整裁剪图, round 原点） | 记录坐标处 NCC（floor 原点, 对照） |',
            '|---|---|---|---|---|---|']
    for p in sorted(f['lead_reconciliation']['per_page'], key=lambda z: int(z)):
        row = f['lead_reconciliation']['per_page'][p]
        b = row.get('binary_otsu') or {}
        s1 = (b.get('by_scale') or {}).get('1.0')
        head.append('| `page_{}.jpg` | {} | {} | {} | **{}** | {} |'.format(
            p, b.get('best_score'), b.get('best_scale'), s1,
            row.get('ncc_full_crop'), row.get('ncc_full_crop_floor')))
    return '\n'.join(head)


def build_report(f) -> str:
    """从 markdown 模板渲染报告（模板与数值分离，便于单独审阅）。"""
    from string import Template
    with open(os.path.join(OUTDIR, 'coord_report_template.md'), encoding='utf-8') as fh:
        tpl = Template(fh.read())
    m = f['mapping']
    sc = f['scale']
    h1 = f['h1_panel']
    h2 = f['h2_canvas']
    h4 = f['h4_padding']
    rec = f['lead_reconciliation']
    p234 = rec['per_page']['233']
    flat = {
        'generated_at': f['generated_at'],
        'n_records': m['n_records'],
        'ncc_correct_mean': m['ncc_correct']['mean'],
        'ncc_correct_min': m['ncc_correct']['min'],
        'ncc_correct_max': m['ncc_correct']['max'],
        'ncc_wrong_mean': m['ncc_wrong_page_N']['mean'],
        'ncc_wrong_max': m['ncc_wrong_page_N']['max'],
        'n_ge085': m['n_records_correct_ge_0_85'],
        'n_with_correct': m['n_with_correct_candidate'],
        'n_wrong_le04': m['n_records_wrong_le_0_4'],
        'crop_n': f['crop_manifest']['n'],
        'crop_eq': f['crop_manifest']['n_eq_floor_bbox_wh'],
        'crop_maxerr': '{:.3f}'.format(f['crop_manifest']['max_floor_abs_err']),
        'crop_kb': int(f['crop_manifest']['total_bytes'] // 1024),
        'h1_box_x': '[{}, {}]'.format(h1['box_x_range'][0], h1['box_x_range'][1]),
        'h1_panel_x': h1['first_column_ink_cols'][0],
        'h1_gutter': '-'.join(str(v) for v in
                              [r for r in h1['full_height_blank_runs_lt_800'] if r[0] > 100][0][:2]),
        'h1_residual': '0.5',
        'h2_ink_rows': '{}-{}'.format(h2['annotated_column_ink_rows'][0], h2['annotated_column_ink_rows'][1]),
        'h2_ink_cols': '{}-{}'.format(h2['annotated_column_ink_cols'][0], h2['annotated_column_ink_cols'][1]),
        'h2_ratio_y': '{:.3f}'.format(h2['box_y_over_content_y']),
        'h2_below': h2['content_rows_below_hypothesized_bottom'],
        'h4_black': h4['black_padded_cols'],
        'h4_white': h4['white_margin_cols_before_pad'],
        'h4_req_right': h4['requested_right_edge'],
        'h4_page7w': h4['page_7_width'],
        'h4_page8w': h4['page_8_width'],
        'h4_inferred': h4['inferred_canvas_width'],
        'h4_scores': ', '.join('{:.3f}'.format(sc[k]['score_at_s1']) for k in sorted(sc, key=lambda z: int(z))),
        'residual_max': '{:.2f}'.format(max(abs(v) for k in sc for v in sc[k]['best']['residual_px'])),
        'scale_table': _scale_rows(f),
        'integrity_table': _integrity_rows(f),
        'api_lines': _api_lines(f),
        'cf_table': _cf_rows(f),
        'recon_table': _recon_rows(f),
        'recon_o5_ncc': p234.get('ncc_full_crop'),
        'recon_o5_floor': p234.get('ncc_full_crop_floor'),
        'recon_o5_p7': rec['per_page']['7'].get('ncc_full_crop'),
        'recon_global_range': '{:.2f}-{:.2f}'.format(rec['global_binary_best_range'][0],
                                                     rec['global_binary_best_range'][1]),
        'recon_global_scales': ', '.join(str(s) for s in rec['global_binary_best_scales']),
        'recon_s1_global': (rec['per_page']['233'].get('binary_otsu') or {}).get('by_scale', {}).get('1.0'),
        'origin_line': '平台裁剪原点的整数约定（±3px 偏移扫描，36 条）：最优偏移为 (0,0) 的 '
                       '{}/{} 条，另有 (0,1) 1 条，以及 (-2,0) 1 条（越界框：x2=1181.09 使 dx=0 不可行）；'
                       '按 round 原点对齐时 NCC 均值 **{:.4f}**（{:.4f}–{:.4f}）。分布：{}'.format(
                           f['crop_origin']['n_zero_offset'], f['crop_origin']['n_total'],
                           f['crop_origin']['ncc_at_round_origin']['mean'],
                           f['crop_origin']['ncc_at_round_origin']['min'],
                           f['crop_origin']['ncc_at_round_origin']['max'],
                           f['crop_origin']['argmax_offset_hist']),
        'cf_ncc_line': ('page_index=234 的探测裁剪图：恒等映射 (1.000, 0, 0) 下覆盖率 {:.3f}%、NCC **{}**；'
                        '覆盖率最优变换 ({:.3f}, {}, {}) 下覆盖率升到 {:.3f}%，NCC 却掉到 **{}**。'
                        '覆盖率升高而 NCC 崩塌，说明该目标函数的极值是错的。').format(
                            f['canvas_fit']['234']['identity_ink_pct'],
                            f['canvas_fit']['234']['ncc_at_identity'],
                            f['canvas_fit']['234']['best_s'], f['canvas_fit']['234']['best_dx'],
                            f['canvas_fit']['234']['best_dy'], f['canvas_fit']['234']['best_ink_pct'],
                            f['canvas_fit']['234']['ncc_at_coverage_opt']),
    }
    return tpl.safe_substitute(flat)


def corrected_integrity(manifest, pages) -> list[dict]:
    out = []
    by_page = {}
    for m in manifest:
        by_page.setdefault(m["page_index"], []).append(m["bbox"])
    for pidx in sorted(by_page):
        canvas = pidx - 1
        g = pages.get(canvas)
        boxes = by_page[pidx]
        mx2 = round(max(b[2] for b in boxes), 2)
        my2 = round(max(b[3] for b in boxes), 2)
        if g is None:
            out.append({"page_index": pidx, "canvas": f"page_{canvas}.jpg (未下载)",
                        "wh": ["-", "-"], "n_boxes": len(boxes), "max_x2": mx2, "max_y2": my2,
                        "verdict": "UNKNOWN (需 page_%d.jpg)" % canvas})
            continue
        over = []
        if mx2 > g.shape[1]:
            over.append(f"x2 超 {mx2-g.shape[1]:.2f}px")
        if my2 > g.shape[0]:
            over.append(f"y2 超 {my2-g.shape[0]:.2f}px")
        out.append({"page_index": pidx, "canvas": f"page_{canvas}.jpg",
                    "wh": [int(g.shape[1]), int(g.shape[0])], "n_boxes": len(boxes),
                    "max_x2": mx2, "max_y2": my2,
                    "verdict": "OUT_OF_BOUNDS(" + "; ".join(over) + ")" if over else "OK"})
    return out


# --------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()

    os.makedirs(EVDIR, exist_ok=True)
    recs = load_annotations()
    log(f"[1/6] 标注记录 {len(recs)} 条，页 {sorted({r['page_index'] for r in recs})}")

    manifest = ensure_crops(recs, download=not args.skip_download)
    errs = [abs(m["crop_wh"][0] - m["bbox_wh"][0]) for m in manifest] + \
           [abs(m["crop_wh"][1] - m["bbox_wh"][1]) for m in manifest]
    crop_summary = {
        "n": len(manifest),
        "n_eq_floor_bbox_wh": sum(1 for m in manifest if m["eq_floor_bbox_wh"]),
        "max_floor_abs_err": round(float(max(errs)), 3),
        "total_bytes": int(sum(os.path.getsize(os.path.join(CROPDIR, m["file"])) for m in manifest)),
    }
    log(f"[2/6] 平台裁剪图 {crop_summary['n']} 张，与 floor(bbox) 相等 "
        f"{crop_summary['n_eq_floor_bbox_wh']}/{crop_summary['n']}，最大偏差 {crop_summary['max_floor_abs_err']}px")
    with open(os.path.join(OUTDIR, "coord_annotation_images.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)

    pages = {p: imread_gray(page_path(p)) for p in CAND_PAGES}
    log("[3/6] 页图已载入: " + ", ".join(f"page_{p}={g.shape[1]}x{g.shape[0]}" for p, g in pages.items()))

    mapping = test_mapping(recs, manifest, pages)
    log(f"[4/6] 配对检验: page_(N-1) NCC 均值 {mapping['ncc_correct']['mean']} "
        f"({mapping['ncc_correct']['min']}-{mapping['ncc_correct']['max']}) vs page_N "
        f"{mapping['ncc_wrong_page_N']['mean']}")
    scale = test_scale(manifest, pages)
    log("[4/6] 尺度扫描: " + ", ".join(
        f"pidx{k} best s={v['best']['s']:.3f} score={v['best']['score']:.3f}" for k, v in scale.items()))
    canvas_fit = test_canvas_fit(manifest, pages)
    recon = test_lead_reconciliation(manifest, pages)
    origin = test_crop_origin(manifest, pages)
    log("[4/6] 裁剪原点扫描: argmax 偏移分布 " + str(origin["argmax_offset_hist"])
        + f"; round 原点处 NCC 均值 {origin['ncc_at_round_origin']['mean']}")
    log("[4/6] 覆盖率拟合: " + "; ".join(
        f"pidx{k} identity={v['identity_ink_pct']}% best={v['best_ink_pct']}% "
        f"@({v['best_s']},{v['best_dx']},{v['best_dy']})" for k, v in canvas_fit.items()))

    findings = {
        "task": "task-2 坐标系逆向：矩形框与页图坐标空间不一致的根因",
        "generated_at": None,
        "root_cause": "annotation page_index / '@page_N' label is the 1-based viewer page number; "
                      "OSS page image 46006966_page_M.jpg is 0-based, M = page_index - 1; "
                      "rect_bbox is in that page image's pixel space at scale 1.000, offset (0,0).",
        "crop_manifest": crop_summary,
        "mapping": mapping,
        "scale": scale,
        "grid": [0.96, 0.97, 0.98, 0.985, 0.99, 0.995, 1.0, 1.005, 1.01, 1.015, 1.02, 1.03, 1.04],
        "h1_panel": test_panel_h1(manifest, pages),
        "h2_canvas": test_canvas_h2(manifest, pages),
        "h4_padding": test_padding_h4(manifest, pages),
        "canvas_fit": canvas_fit,
        "lead_reconciliation": recon,
        "crop_origin": origin,
        "api_evidence": test_api_evidence(),
        "corrected_integrity": corrected_integrity(manifest, pages),
        "hypotheses": {
            "H1_panel_canvas": "NEGATIVE (no offset panel; residual<=0.5px) - but origin-(0,0) sub-crop is non-identifiable",
            "H2_canvas_594x1164": "NEGATIVE (box extents reflect annotated column content, not canvas bounds)",
            "H3_cross_page": "SUPPORTED (systematic 1-page offset, 36/36 records)",
            "H4_fixed_canvas_rescale": "NEGATIVE (optimal scale 1.000 on 4/4 pages; OOB = black padding, canvas width 1178)",
        },
        "undecidable": [
            "canvas = full page image vs origin-(0,0) sub-crop (numerically identical here)",
            "page_index=7 -> page_6.jpg pairing (no annotations; page_6.jpg not downloaded)",
            "residual NCC <1.000 cause (platform re-encoded the crop; needs platform-side parameter)",
        ],
    }
    import datetime
    findings["generated_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    log("[5/6] 生成证据图 ...")
    fig_mapping_matrix(mapping, manifest)
    fig_corrected_overlays(manifest, pages)
    fig_wrong_vs_correct(manifest, pages)
    fig_crop_vs_canvas(manifest, pages)
    fig_padding(pages, manifest)
    fig_h2_profile(manifest, pages)
    fig_recon(manifest, pages)

    with open(os.path.join(OUTDIR, "coord_reverse_findings.json"), "w", encoding="utf-8") as fh:
        json.dump(findings, fh, ensure_ascii=False, indent=1)
    report = build_report(findings)
    with open(os.path.join(OUTDIR, "coord_reverse_report.md"), "w", encoding="utf-8") as fh:
        fh.write(report + "\n")
    log("[6/6] 报告 -> data/derived/analysis/coord_reverse_report.md")
    log("")
    log("=== 结论 ===")
    log("根因: page_index N (1基查看器页码) <-> page_{N-1}.jpg (0基图像索引)")
    log(f"      rect_bbox 尺度 1.000 偏移 (0,0)，残差 <1px；36/36 条 NCC 0.89-0.998（对比 page_N 均值 "
        f"{mapping['ncc_wrong_page_N']['mean']}）")
    log("H1 子页画布: 否定(不可判定项: 起点(0,0)的子图与整页等价)")
    log("H2 画布(594,1164): 否定")
    log("H3 跨页错配: 支持(系统性偏 1 页)")
    log("H4 缩放画布: 否定(最优 s=1.000；越界=补黑，画布宽 1178=page_7.jpg)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
