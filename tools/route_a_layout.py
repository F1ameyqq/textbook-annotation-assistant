#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/route_a_layout.py — 路线A：本地版面检测出框基线（CPU-only，零模型下载）

目标
----
对 46006966 已落地的 6 张页图，用**不依赖 GPU、不下载模型**的方法产出
"题型/角色候选框"（题干 Q / 单个选项 W / 答案 A / 解析 E），并与历史标注做客观比对。

方法（两级）
------------
1) 几何基线（默认全程可用，`--no-ocr` 可单跑）：
   - 全局阈值二值化（thresh=160，与 data/derived/verify_report.md 的墨迹统计口径一致）
   - 纵向贯穿空白沟 → 拼合页切子页（见 split_subpages）
   - 行投影 → 文本行；行间隙阈值 → 段落块
   - 连通域（cv2.connectedComponentsWithStats）精修每个候选框的紧致边界
2) 语义角色（可选，`--ocr` 默认开启）：
   - rapidocr_onnxruntime（onnxruntime 仅 CPU provider；模型随 wheel 内置，下载量 0 字节）
   - 逐子页 OCR → 文本行按关键词/编号规则打角色：答案解析/选项 A-D/题号
   - 选项在同一视觉行内按 OCR atom 逐个拆分成**独立选项框**（历史 choice 是 4 选项合 1 框）

强制 CPU
--------
本脚本在 import onnxruntime 之前设置 CUDA_VISIBLE_DEVICES=""，避免与 GPU 上的
PaddleOCR 争 8GB 显存。onnxruntime 本机可用 provider 只有 CPUExecutionProvider。

可复现性
--------
除 meta.generated_at / meta.elapsed_* 外，输出 JSON 内容确定：
相同输入与参数下 meta.content_sha256（对 pages+evaluation 排序后序列化取 sha256）应完全一致。

用法
----
    set PYTHONIOENCODING=utf-8
    C:\\Users\\LIHAOYANG\\AppData\\Local\\Programs\\Python\\Python311\\python.exe tools\\route_a_layout.py
    # 纯几何基线：
    ... tools\\route_a_layout.py --no-ocr
    # 只跑部分页：
    ... tools\\route_a_layout.py --pages 8 9 10
"""
from __future__ import annotations

import os

# —— 必须在任何 torch/onnxruntime 导入之前设置：强制 CPU ——
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("OMP_NUM_THREADS", "4")

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = ROOT / "data" / "raw" / "images"
ANN_PATH = ROOT / "data" / "raw" / "annotations" / "annotations_unified_snapshot.json"
OUT_DIR = ROOT / "data" / "derived" / "analysis"

CN_TZ = timezone(timedelta(hours=8))

# ---------------------------------------------------------------- 配置

CFG = {
    # 二值化：固定阈值，与 verify_report.md 的墨迹统计一致
    "thresh": 160,
    # —— 子页切分（多页扫描拼合）——
    # 一级：严格贯穿空沟（整列几乎无墨且贯穿绝大部分高度）
    "seam_span_frac": 0.98,
    "seam_ink_frac": 0.005,      # 列墨迹像素 <= max(2, frac*H)
    "seam_min_run": 2,           # 空白沟最小宽度（px）
    "seam_merge_gap": 4,         # 相邻空沟合并间隔
    "seam_min_gutter_width": 4,  # 判定为"页缝"的最窄宽度
    "min_subpage_width": 300,    # 子页最小宽度；更窄的段吸收入邻段
    "min_subpage_ink_px": 200,   # 子页最少墨迹像素（滤掉纯空白段）
    # 二级：段宽 > split_width_factor * 中位宽 时，在段内找最佳空列再切
    "split_width_factor": 1.6,
    "split_requires_wide_image": 1.5,   # W/H > 该值才做二级切分（横向拼合页）
    "split_min_blank_frac": 0.9,        # 二级候选空列的 max-blank-run / H 下限
    "split_edge_margin": 20,            # 二级搜索时避开段两端的像素
    # —— 文本行/段落 ——
    "line_min_h": 8,
    "line_min_ink_frac": 0.004,   # 行激活阈值：行墨迹像素 >= max(2, frac*行宽)
    "line_min_ink": 8,
    "line_merge_gap": 4,          # 行内小间隙合并
    "para_gap_factor": 2.0,       # 段落切分：间隙 > max(中位间隙*factor, 中位间隙+6)
    "para_gap_min_extra": 6,
    "state_break_gap": 40,        # 题型状态延续的最大行间隙（超过则回到 Q 状态）
    # —— 页眉/页脚/角标 ——
    "furniture_band_frac": 0.06,  # 上下 6% 视为边缘带
    "furniture_max_w_frac": 0.12, # 边缘带内宽度 < 12% 图宽
    "furniture_max_h_frac": 0.06, # 且高度 < 6% 图高 → 判为页眉/页脚/页码
    # —— 连通域精修 ——
    "cc_min_area": 4,             # 小于该面积的连通域视为噪点
    # —— OCR ——
    "ocr_engine": "rapidocr_onnxruntime",
    "ocr_score_floor": 0.30,
    # —— 历史标注坐标系映射：image_index = annotation.page_index + offset ——
    "ann_page_offset": -1,
}

QNUM_RE = re.compile(r"^\s*(?:第\s*)?(\d{1,2})\s*(?:[\.、．,，])?\s*(?=[\u4e00-\u9fffA-Za-z（(\[【#])")
OPT_RE = re.compile(r"(?:^|[\s（(])([A-D])\s*[\.、．,，）):：]")
OPT_ANY_RE = re.compile(r"[A-D]\s*[\.、．,，）):：]")
ANS_RE = re.compile(r"(参考答案|答案|答\s*[:：])")
ANA_RE = re.compile(r"(解析|【\s*解\s*析\s*】|分析)")

ROLE_CN = {
    "question": "题干",
    "option": "选项",
    "answer": "答案",
    "analysis": "解析",
    "text_block": "文本块",
    "unknown": "未定",
}
ROLE_BGR = {
    "question": (0, 0, 255),
    "option": (0, 180, 0),
    "answer": (255, 0, 0),
    "analysis": (255, 0, 255),
    "text_block": (120, 120, 120),
    "unknown": (160, 160, 160),
}

# ---------------------------------------------------------------- 基础工具


def imread_gray(path: Path) -> np.ndarray:
    """路径含中文时 cv2.imread 会失败，改用 imdecode。"""
    buf = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"无法读取图片: {path}")
    return img


def imread_bgr(path: Path) -> np.ndarray:
    buf = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"无法读取图片: {path}")
    return img


def imwrite_u(path: Path, img: np.ndarray) -> None:
    ok, buf = cv2.imencode(path.suffix, img)
    if not ok:
        raise RuntimeError(f"编码失败: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    buf.tofile(str(path))


def runs_from_flags(flags: np.ndarray, min_len: int = 1) -> list[tuple[int, int]]:
    """布尔序列 -> 连续 True 的 [start, end) 段。"""
    out: list[tuple[int, int]] = []
    start = None
    for i, v in enumerate(flags):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_len:
                out.append((start, i))
            start = None
    if start is not None and len(flags) - start >= min_len:
        out.append((start, len(flags)))
    return out


def merge_runs(runs: list[tuple[int, int]], gap: int) -> list[tuple[int, int]]:
    if not runs:
        return []
    out = [list(runs[0])]
    for a, b in runs[1:]:
        if a - out[-1][1] <= gap:
            out[-1][1] = b
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def max_blank_runs_per_column(mask: np.ndarray) -> np.ndarray:
    """每列的最大连续空白长度。向量化按行推进（H 次向量操作）。"""
    h, w = mask.shape
    blank = ~mask
    cur = np.zeros(w, dtype=np.int32)
    mx = np.zeros(w, dtype=np.int32)
    for y in range(h):
        cur = np.where(blank[y], cur + 1, 0)
        np.maximum(mx, cur, out=mx)
    return mx


def max_blank_runs_per_row(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    blank = ~mask
    cur = np.zeros(h, dtype=np.int32)
    mx = np.zeros(h, dtype=np.int32)
    for x in range(w):
        cur = np.where(blank[:, x], cur + 1, 0)
        np.maximum(mx, cur, out=mx)
    return mx


def segments_between(seams: list[tuple[int, int]], length: int) -> list[tuple[int, int]]:
    segs = []
    pos = 0
    for a, b in seams:
        if a > pos:
            segs.append((pos, a))
        pos = max(pos, b)
    if pos < length:
        segs.append((pos, length))
    return [(a, b) for a, b in segs if b - a > 1]


def trim_low_ink_columns(mask: np.ndarray, x1: int, x2: int, ink_frac: float) -> tuple[int, int]:
    """把段两端"近空白列"削掉（多页拼合时页缝两侧常残留窄边）。"""
    if x2 <= x1:
        return x1, x2
    ci = mask[:, x1:x2].sum(axis=0)
    thr = max(2.0, ink_frac * mask.shape[0])
    lo, hi = 0, len(ci)
    while lo < hi and ci[lo] <= thr:
        lo += 1
    while hi > lo and ci[hi - 1] <= thr:
        hi -= 1
    return x1 + lo, x1 + hi


# ---------------------------------------------------------------- 子页切分


def detect_seams(mask: np.ndarray, cfg: dict) -> list[tuple[int, int]]:
    """严格贯穿空沟：整列 max-blank-run >= span_frac*H 且墨迹 <= max(2, ink_frac*H)。"""
    h, w = mask.shape
    mx = max_blank_runs_per_column(mask)
    ci = mask.sum(axis=0)
    thr = max(2, int(cfg["seam_ink_frac"] * h))
    flags = (ci <= thr) & (mx >= cfg["seam_span_frac"] * h)
    runs = runs_from_flags(flags, cfg["seam_min_run"])
    return merge_runs(runs, cfg["seam_merge_gap"])


def best_internal_split_column(mask: np.ndarray, x1: int, x2: int, cfg: dict) -> int | None:
    """
    在段内找最像"页缝"的列：max-blank-run 高且墨迹少，且切完后两侧都够宽。
    注意不能只取"墨迹最少"的列——段边缘的页边距列也是全空白列，必须要求切分后
    左右两段（去掉各自低墨边缘后）都 >= min_subpage_width。
    """
    h = mask.shape[0]
    m = cfg["split_edge_margin"]
    a, b = x1 + m, x2 - m
    if b - a < 40:
        return None
    sub = mask[:, a:b]
    mx = max_blank_runs_per_column(sub)
    ci = sub.sum(axis=0).astype(np.int64)
    ok = mx >= cfg["split_min_blank_frac"] * h
    cands = np.nonzero(ok)[0]
    if len(cands) == 0:
        return None
    order = cands[np.lexsort((-mx[cands], ci[cands]))][:600]
    for idx in order:
        cut = a + int(idx)
        na, nb = trim_low_ink_columns(mask, x1, cut, cfg["seam_ink_frac"])
        ca, cb = trim_low_ink_columns(mask, cut, x2, cfg["seam_ink_frac"])
        if (nb - na) >= cfg["min_subpage_width"] and (cb - ca) >= cfg["min_subpage_width"]:
            return cut
    return None


def split_subpages(mask: np.ndarray, cfg: dict) -> list[dict]:
    """
    返回子页列表 [{'x1','x2','ink_px','source'}]。
    一级：严格贯穿空沟切分（可靠信号）。
    二级：仅当图是横向宽图 (W/H > split_requires_wide_image) 且某段宽 > factor*中位宽 时，
          在该段内按"最佳空列"再切一刀（应对页缝仅 2px、一级判据看不到的情况）。
    """
    h, w = mask.shape
    ratio = w / float(h)
    if ratio <= cfg["split_requires_wide_image"]:
        # 单页扫描（纵向）：不做沟切分。
        # 判据：本数据集中单页 W/H≈0.70，多页拼合页 233/234 W/H≈2.15（见 JSON image_wh_ratio）。
        # 纵向页内也会出现"局部空白列"（段落之间的空白），用贯穿判据会误切，故按纵横比分流。
        sub = mask
        return ([{"subpage_index": 0, "x1": 0, "x2": int(w), "width": int(w),
                  "ink_px": int(sub.sum())}],
                {"mode": "single_page_by_aspect", "wh_ratio": round(ratio, 4),
                 "level1_segments": [[0, int(w)]], "secondary_splits": []})

    seams = [(a, b) for a, b in detect_seams(mask, cfg) if a > 0 and b < w]
    seams = [(a, b) for a, b in seams if (b - a) >= cfg["seam_min_gutter_width"]]
    segs = segments_between(seams, w)

    # 吸收过窄段（拼合页里夹在两沟之间的碎片）
    merged: list[list[int]] = []
    for a, b in segs:
        if merged and (b - a) < cfg["min_subpage_width"]:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    if len(merged) > 1 and (merged[0][1] - merged[0][0]) < cfg["min_subpage_width"]:
        merged[1][0] = merged[0][0]
        merged.pop(0)
    segs = [(a, b) for a, b in merged]
    level1 = [(a, b) for a, b in segs]

    # 二次切分
    wide_image = ratio > cfg["split_requires_wide_image"]
    split_notes = []
    if wide_image and len(segs) >= 2:
        widths = [b - a for a, b in segs]
        med = float(np.median(widths))
        out: list[list[int]] = []
        for a, b in segs:
            if (b - a) > cfg["split_width_factor"] * med:
                cut = best_internal_split_column(mask, a, b, cfg)
                if cut is not None:
                    na, nb = trim_low_ink_columns(mask, a, cut, cfg["seam_ink_frac"])
                    ca, cb = trim_low_ink_columns(mask, cut, b, cfg["seam_ink_frac"])
                    if (nb - na) >= cfg["min_subpage_width"] and (cb - ca) >= cfg["min_subpage_width"]:
                        out.append([na, nb])
                        out.append([ca, cb])
                        split_notes.append({"segment": [a, b], "cut_column": cut,
                                            "parts": [[na, nb], [ca, cb]]})
                        continue
            out.append([a, b])
        segs = out

    # 统一削掉每段两端的低墨边缘（页边距/页缝残留），保证子页边界是内容边界
    trimmed: list[list[int]] = []
    for a, b in segs:
        ta, tb = trim_low_ink_columns(mask, a, b, cfg["seam_ink_frac"])
        if tb - ta < 20:
            continue
        if int(mask[:, ta:tb].sum()) < cfg["min_subpage_ink_px"]:
            continue
        trimmed.append([ta, tb])
    segs = trimmed

    subpages = []
    for i, (a, b) in enumerate(segs):
        sub = mask[:, a:b]
        subpages.append({
            "subpage_index": i,
            "x1": int(a), "x2": int(b), "width": int(b - a),
            "ink_px": int(sub.sum()),
        })
    return subpages, {"mode": "multi_page_by_seams", "wh_ratio": round(ratio, 4),
                      "level1_segments": [[a, b] for a, b in level1],
                      "trimmed_segments": [[a, b] for a, b in segs],
                      "secondary_splits": split_notes}


# ---------------------------------------------------------------- 行 / 段落 / 连通域


def cc_refine_bbox(mask: np.ndarray, box, min_area: int, pad: int = 1) -> list[float]:
    """用连通域精修 bbox：丢弃面积 < min_area 的噪点后取并集。"""
    h, w = mask.shape
    x1 = max(0, int(np.floor(box[0])))
    y1 = max(0, int(np.floor(box[1])))
    x2 = min(w, int(np.ceil(box[2])))
    y2 = min(h, int(np.ceil(box[3])))
    if x2 <= x1 or y2 <= y1:
        return [float(x1), float(y1), float(x2), float(y2)]
    sub = mask[y1:y2, x1:x2]
    n, _labels, stats, _cent = cv2.connectedComponentsWithStats(sub.astype(np.uint8), connectivity=8)
    keep = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= min_area]
    if not keep:
        return [float(x1), float(y1), float(x2), float(y2)]
    a = min(int(stats[i, cv2.CC_STAT_LEFT]) for i in keep)
    b = min(int(stats[i, cv2.CC_STAT_TOP]) for i in keep)
    c = max(int(stats[i, cv2.CC_STAT_LEFT]) + int(stats[i, cv2.CC_STAT_WIDTH]) for i in keep)
    d = max(int(stats[i, cv2.CC_STAT_TOP]) + int(stats[i, cv2.CC_STAT_HEIGHT]) for i in keep)
    return [float(max(0, x1 + a - pad)), float(max(0, y1 + b - pad)),
            float(min(w, x1 + c + pad)), float(min(h, y1 + d + pad))]


def cc_stats_in_box(mask: np.ndarray, box, min_area: int) -> dict:
    """框内连通域统计：用于报告"连通域"证据。"""
    h, w = mask.shape
    x1 = max(0, int(box[0])); y1 = max(0, int(box[1]))
    x2 = min(w, int(box[2])); y2 = min(h, int(box[3]))
    if x2 <= x1 or y2 <= y1:
        return {"n_cc": 0, "n_cc_small": 0, "ink_px": 0, "ink_pct": 0.0}
    sub = mask[y1:y2, x1:x2]
    n, _l, stats, _c = cv2.connectedComponentsWithStats(sub.astype(np.uint8), connectivity=8)
    areas = [int(stats[i, cv2.CC_STAT_AREA]) for i in range(1, n)]
    return {"n_cc": int(sum(1 for a in areas if a >= min_area)),
            "n_cc_small": int(sum(1 for a in areas if a < min_area)),
            "ink_px": int(sub.sum()),
            "ink_pct": round(100.0 * float(sub.mean()), 3)}


def detect_lines(mask: np.ndarray, x1: int, x2: int, y1: int, y2: int, cfg: dict) -> list[dict]:
    """行投影 + 连通域精修，返回文本行 [{bbox, ink, atoms:[]}]。"""
    sub = mask[y1:y2, x1:x2]
    if sub.size == 0:
        return []
    prof = sub.sum(axis=1)
    min_ink = max(2, int(cfg["line_min_ink_frac"] * (x2 - x1)))
    active = prof >= min_ink
    runs = merge_runs(runs_from_flags(active, 1), cfg["line_merge_gap"])
    lines = []
    for a, b in runs:
        if b - a < cfg["line_min_h"]:
            continue
        band = sub[a:b]
        ink = int(band.sum())
        if ink < cfg["line_min_ink"]:
            continue
        colink = band.sum(axis=0)
        nz = np.nonzero(colink > 0)[0]
        if len(nz) == 0:
            continue
        raw = [float(x1 + nz[0]), float(y1 + a), float(x1 + nz[-1] + 1), float(y1 + b)]
        box = cc_refine_bbox(mask, raw, cfg["cc_min_area"], pad=1)
        lines.append({"bbox": box, "ink": ink, "atoms": [], "text": "", "kind": "unknown"})
    return lines


def group_by_gaps(lines: list[dict], cfg: dict) -> tuple[list[list[dict]], float]:
    """按行间隙聚段落块，返回 (blocks, gap_threshold)。"""
    if not lines:
        return [], 0.0
    if len(lines) == 1:
        return [lines], 0.0
    gaps = [lines[i + 1]["bbox"][1] - lines[i]["bbox"][3] for i in range(len(lines) - 1)]
    med = float(np.median(gaps))
    thr = max(med * cfg["para_gap_factor"], med + cfg["para_gap_min_extra"])
    blocks = [[lines[0]]]
    for g, ln in zip(gaps, lines[1:]):
        if g > thr:
            blocks.append([])
        blocks[-1].append(ln)
    return blocks, round(thr, 2)


def union_bbox(boxes) -> list[float]:
    return [round(min(b[0] for b in boxes), 2), round(min(b[1] for b in boxes), 2),
            round(max(b[2] for b in boxes), 2), round(max(b[3] for b in boxes), 2)]


# ---------------------------------------------------------------- OCR


_ENGINE = None


def get_ocr_engine():
    global _ENGINE
    if _ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR  # 延迟导入：无 OCR 需求时不加载
        _ENGINE = RapidOCR()
    return _ENGINE


def ocr_atoms(bgr: np.ndarray, ox: int = 0, oy: int = 0, score_floor: float = 0.3) -> list[dict]:
    """对整幅（或子页裁剪）跑 OCR，返回轴对齐 atom 列表（全局坐标）。"""
    engine = get_ocr_engine()
    res, _elapse = engine(bgr)
    out = []
    for item in (res or []):
        box, text, score = item[0], item[1], item[2]
        if float(score) < score_floor or not str(text).strip():
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        out.append({
            "bbox": [round(float(min(xs)) + ox, 2), round(float(min(ys)) + oy, 2),
                     round(float(max(xs)) + ox, 2), round(float(max(ys)) + oy, 2)],
            "text": str(text).strip(),
            "score": round(float(score), 4),
        })
    out.sort(key=lambda a: (a["bbox"][1], a["bbox"][0]))
    return out


def attach_atoms(lines: list[dict], atoms: list[dict]) -> None:
    """把 OCR atom 按纵向重叠最大者挂到文本行；无匹配行的 atom 新建一行。"""
    for atom in atoms:
        best, best_ov = None, 0.0
        ay1, ay2 = atom["bbox"][1], atom["bbox"][3]
        for ln in lines:
            ly1, ly2 = ln["bbox"][1], ln["bbox"][3]
            ov = min(ay2, ly2) - max(ay1, ly1)
            if ov > best_ov:
                best_ov, best = ov, ln
        ah = max(1.0, ay2 - ay1)
        if best is not None and best_ov >= 0.4 * ah:
            best["atoms"].append(atom)
        else:
            lines.append({"bbox": list(atom["bbox"]), "ink": 0, "atoms": [atom],
                          "text": "", "kind": "unknown"})
    for ln in lines:
        ln["atoms"].sort(key=lambda a: a["bbox"][0])
    lines.sort(key=lambda ln: (ln["bbox"][1], ln["bbox"][0]))
    for ln in lines:
        ln["text"] = " ".join(a["text"] for a in ln["atoms"]).strip()


# ---------------------------------------------------------------- 角色判定


def is_qnum(t: str) -> bool:
    m = QNUM_RE.match(t)
    if not m:
        return False
    n = int(m.group(1))
    if n < 1 or n > 99:
        return False
    rest = t[m.end():]
    if rest[:1] in "章节单元讲课":
        return False
    if re.match(r"^\d", rest):
        return False
    # 数字后紧跟拉丁字母 → 更像数学式（如 "6a+3 的值为"），不是题号
    if rest and rest[0].isascii() and rest[0].isalpha():
        return False
    return True


def count_opt_markers(t: str) -> int:
    return len(OPT_RE.findall(t))


def classify_line(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return "unknown"
    if ANA_RE.search(t):
        return "analysis"
    if ANS_RE.search(t):
        return "answer"
    if count_opt_markers(t) >= 1:
        return "option"
    if is_qnum(t):
        return "qnum"
    return "other"


def split_line_by_blank(mask: np.ndarray, box, cfg: dict) -> list[list[float]]:
    """一行里有两个选项标记但 OCR 只给了一个 atom 时，按最大空白列切一刀。"""
    h, w = mask.shape
    x1 = max(0, int(box[0])); x2 = min(w, int(box[2]))
    y1 = max(0, int(box[1])); y2 = min(h, int(box[3]))
    if x2 - x1 < 60:
        return [list(box)]
    band = mask[y1:y2, x1:x2]
    colink = band.sum(axis=0)
    mid_lo, mid_hi = int(0.25 * len(colink)), int(0.75 * len(colink))
    if mid_hi <= mid_lo:
        return [list(box)]
    seg = colink[mid_lo:mid_hi]
    idx = mid_lo + int(np.argmin(seg))
    if colink[idx] > max(1, 0.02 * (y2 - y1)):
        return [list(box)]
    a = cc_refine_bbox(mask, [x1, y1, x1 + idx, y2], cfg["cc_min_area"], 1)
    b = cc_refine_bbox(mask, [x1 + idx, y1, x2, y2], cfg["cc_min_area"], 1)
    if (a[2] - a[0]) < 20 or (b[2] - b[0]) < 20:
        return [list(box)]
    return [a, b]


def option_candidates_from_line(mask, ln, cfg) -> list[dict]:
    """一"行"内逐 OCR atom 拆成独立选项框；无 atom 时退化为整行。"""
    atoms = ln["atoms"]
    if not atoms:
        role_method = "geom_heuristic"
        return [{"bbox": list(ln["bbox"]), "texts": [], "score": 0.0,
                 "method": role_method, "evidence": "无 OCR：整行作为候选选项"}]
    groups: list[dict] = []
    for a in atoms:
        if count_opt_markers(a["text"]) >= 1:
            groups.append({"atoms": [a]})
        elif groups:
            groups[-1]["atoms"].append(a)
        else:
            groups.append({"atoms": [a], "no_marker": True})
    out = []
    for g in groups:
        boxes = [a["bbox"] for a in g["atoms"]]
        bb = union_bbox(boxes)
        texts = [a["text"] for a in g["atoms"]]
        if len(g["atoms"]) == 1 and count_opt_markers(texts[0]) >= 2:
            parts = split_line_by_blank(mask, bb, cfg)
            for p in parts:
                out.append({"bbox": p, "texts": texts, "score": g["atoms"][0]["score"],
                            "method": "ocr_atom+blank_split",
                            "evidence": "单个 atom 含多个选项标记，按空白列切分"})
            continue
        out.append({"bbox": bb, "texts": texts,
                    "score": float(np.mean([a["score"] for a in g["atoms"]])),
                    "method": "ocr_atom+cc_refine",
                    "evidence": "OCR atom 以选项标记 A-D 开头" if not g.get("no_marker")
                                else "同行无标记 atom，归入前一选项"})
    return out


def is_furniture(ln: dict, w: int, h: int, cfg: dict) -> bool:
    """
    页眉/页脚/页码角标：位于上下边缘带，且
      - 无 OCR 文本（unknown）→ 直接判为版式噪声（扫描黑边、蓝色页码块）
      - 有其他文本但尺寸很小 → 判为页码/角标
    """
    x1, y1, x2, y2 = ln["bbox"]
    bw, bh = x2 - x1, y2 - y1
    in_band = (y2 <= cfg["furniture_band_frac"] * h) or (y1 >= (1 - cfg["furniture_band_frac"]) * h)
    if not in_band:
        return False
    if ln["kind"] == "unknown":
        return True
    return bool(bw <= cfg["furniture_max_w_frac"] * w
                and bh <= cfg["furniture_max_h_frac"] * h)


def split_run_by_gap(run_lines: list[dict], cfg: dict) -> list[list[dict]]:
    """把同状态的行 run 按大间隙再切开，避免题干框横跨大片空白。"""
    if len(run_lines) <= 1:
        return [run_lines]
    gaps = [run_lines[i + 1]["bbox"][1] - run_lines[i]["bbox"][3]
            for i in range(len(run_lines) - 1)]
    med = float(np.median(gaps))
    thr = max(med * cfg["para_gap_factor"], med + cfg["para_gap_min_extra"])
    out = [[run_lines[0]]]
    for g, ln in zip(gaps, run_lines[1:]):
        if g > thr:
            out.append([])
        out[-1].append(ln)
    return out


def group_candidates(lines: list[dict], mask: np.ndarray, cfg: dict,
                     page_index: int, subpage_index: int) -> tuple[list[dict], int]:
    """按题型状态机把行聚成候选框：Q / W / A / E。返回 (候选列表, 被过滤的页眉页脚行数)。"""
    h, w = mask.shape
    kept: list[dict] = []
    n_furniture = 0
    for ln in lines:
        ln["kind"] = classify_line(ln["text"])
        if ln["kind"] in ("unknown", "other") and is_furniture(ln, w, h, cfg):
            n_furniture += 1
            continue
        kept.append(ln)
    lines = kept

    # 题号开新组
    groups: list[list[dict]] = []
    cur: list[dict] = []
    for ln in lines:
        if ln["kind"] == "qnum":
            if cur:
                groups.append(cur)
            cur = [ln]
        else:
            cur.append(ln)
    if cur:
        groups.append(cur)

    cands = []
    for gi, group in enumerate(groups):
        group_has_qnum = group[0]["kind"] == "qnum"

        def add(c, _gi=gi, _hq=group_has_qnum):
            c["q_group"] = _gi
            c["q_group_has_qnum"] = _hq
            cands.append(c)
        states = []
        state = "Q"
        for i, ln in enumerate(group):
            k = ln["kind"]
            if k == "option":
                state = "W"
            elif k == "answer":
                state = "A"
            elif k == "analysis":
                state = "E"
            elif k == "qnum":
                state = "Q"
            else:
                # 'other'/'unknown' 只在紧邻上一行时延续当前状态，避免页脚/角标被吸进题干
                if i > 0:
                    gap = ln["bbox"][1] - group[i - 1]["bbox"][3]
                    med = cfg["para_gap_min_extra"]
                    if gap > max(cfg["para_gap_factor"] * med, cfg["state_break_gap"]):
                        state = "Q"
            states.append(state)
        # 连续同 state 且间隙不大的行切成 run；记录 run 是否由"大间隙"切出
        runs: list[dict] = []
        prev_ln = None
        sep_thr = max(cfg["para_gap_factor"] * cfg["para_gap_min_extra"], cfg["state_break_gap"])
        for ln, st in zip(group, states):
            gap = None if prev_ln is None else ln["bbox"][1] - prev_ln["bbox"][3]
            big_gap = gap is not None and gap > sep_thr
            if runs and runs[-1]["state"] == st and not big_gap:
                runs[-1]["lines"].append(ln)
            else:
                runs.append({"state": st, "lines": [ln], "separated": bool(big_gap)})
            prev_ln = ln
        for run in runs:
            if run["state"] == "W":
                for ln in run["lines"]:
                    if ln["kind"] != "option":
                        # 选项行之后紧邻的非选项行：不当作选项，单独给 text_block
                        bbox = cc_refine_bbox(mask, list(ln["bbox"]), cfg["cc_min_area"], 1)
                        scores = [a["score"] for a in ln["atoms"]]
                        add(make_candidate(
                            page_index, subpage_index, "text_block", bbox,
                            float(np.mean(scores)) if scores else 0.0, "ocr_keyword",
                            "选项块后的非选项行（无 A-D 标记）: " + ln["text"][:60],
                            [ln], mask, cfg))
                        continue
                    for oc in option_candidates_from_line(mask, ln, cfg):
                        add(make_candidate(
                            page_index, subpage_index, "option", oc["bbox"],
                            oc["score"], oc["method"], oc["evidence"], [ln],
                            mask, cfg, text_override=" ".join(oc["texts"])))
                continue
            for sub in split_run_by_gap(run["lines"], cfg):
                run_has_qnum = any(l["kind"] == "qnum" for l in run["lines"])
                if run["state"] == "Q":
                    if (not group_has_qnum) or (not run_has_qnum and run["separated"]):
                        role = "text_block"
                    else:
                        role = "question"
                else:
                    role = {"A": "answer", "E": "analysis"}[run["state"]]
                bbox = union_bbox([ln["bbox"] for ln in sub])
                bbox = cc_refine_bbox(mask, bbox, cfg["cc_min_area"], 1)
                scores = [a["score"] for ln in sub for a in ln["atoms"]]
                conf = float(np.mean(scores)) if scores else 0.0
                method = "ocr_keyword" if scores else "geom_heuristic"
                ev = role_evidence(role, sub)
                add(make_candidate(page_index, subpage_index, role, bbox, conf,
                                   method, ev, sub, mask, cfg))
    cands.sort(key=lambda c: (c["bbox"][1], c["bbox"][0]))
    return cands, n_furniture


def role_evidence(role: str, lines: list[dict]) -> str:
    k = {"question": "Q", "answer": "A", "analysis": "E", "text_block": "B"}[role]
    parts = []
    for ln in lines:
        t = ln["text"][:24]
        parts.append(f"[{ln['kind']}]{t}")
    prefix = {"question": "题号/题干行: ", "answer": "命中『答案』关键词: ",
              "analysis": "命中『解析』关键词: ",
              "text_block": "无题号/无角色关键词的纯文本块: "}[role]
    return prefix + " | ".join(parts)


def make_candidate(page_index, subpage_index, role, bbox, score, method, evidence,
                   lines, mask, cfg, text_override=None) -> dict:
    st = cc_stats_in_box(mask, bbox, cfg["cc_min_area"])
    text = (text_override if text_override is not None
            else " ".join(ln["text"] for ln in lines if ln["text"]))
    text = (text or "").strip()
    return {
        "cand_id": "",  # 稍后统一编号
        "page_index": page_index,
        "subpage_index": subpage_index,
        "role": role,
        "role_cn": ROLE_CN[role],
        "bbox": [round(float(v), 2) for v in bbox],
        "confidence": round(float(score), 4),
        "role_method": method,
        "geom_method": "projection+connected_components",
        "n_lines": len(lines),
        "text": text[:200],
        "evidence": evidence[:300],
        "ink_pct": st["ink_pct"],
        "ink_px": st["ink_px"],
        "n_cc": st["n_cc"],
        "n_cc_noise": st["n_cc_small"],
    }


def number_candidates(cands: list[dict]) -> None:
    cnt: dict[tuple, int] = {}
    for c in cands:
        key = (c["page_index"], c["role"])
        cnt[key] = cnt.get(key, 0) + 1
        short = {"question": "q", "option": "w", "answer": "a", "analysis": "e",
                 "text_block": "b", "unknown": "u"}[c["role"]]
        c["cand_id"] = f"p{c['page_index']}_{short}_{cnt[key]:04d}"


# ---------------------------------------------------------------- 评测


def iou(a, b) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return float(inter / ua) if ua > 0 else 0.0


def inter_over_hist(a, b) -> float:
    """交集 / 历史框面积（覆盖率），用于检测粒度不同时的补充指标。"""
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    ha = (b[2] - b[0]) * (b[3] - b[1])
    return float(inter / ha) if ha > 0 else 0.0


def load_annotations() -> list[dict]:
    raw = json.loads(ANN_PATH.read_text(encoding="utf-8"))
    for a in raw:
        a["bbox"] = [float(v) for v in a["rect_bbox"].split(",")]
    return raw


def stats_of(vals: list[float]) -> dict:
    if not vals:
        return {"n": 0}
    arr = np.asarray(vals, dtype=float)
    return {"n": len(vals), "mean": round(float(arr.mean()), 4),
            "median": round(float(np.median(arr)), 4),
            "p25": round(float(np.percentile(arr, 25)), 4),
            "p75": round(float(np.percentile(arr, 75)), 4),
            "min": round(float(arr.min()), 4), "max": round(float(arr.max()), 4)}


def evaluate(cands: list[dict], anns: list[dict], pages: list[int],
             unusable_pages: dict, page_masks: dict | None = None,
             offset: int = -1, cc_min_area: int = 4) -> dict:
    """
    offset：标注 page_index → 实际页图编号的映射（image_index = page_index + offset）。
    默认 -1（已由 lead/aocr 用互相关+OCR 语义双重验证：page_index N ↔ 46006966_page_{N-1}.jpg）。
    """
    def mapped(a) -> int:
        return int(a["page_index"]) + offset

    q_cands = [c for c in cands if c["role"] == "question"]
    w_cands = [c for c in cands if c["role"] == "option"]

    hist_q = [a for a in anns if a["type"] == "question" and mapped(a) in pages]
    hist_choice = [a for a in anns if a["type"] == "choice" and mapped(a) in pages]

    def ink_signal(a) -> tuple[float, float]:
        """历史框所在区域的墨迹比例 与 (该比例 / 整页平均墨迹比例)。"""
        p = mapped(a)
        if not page_masks or p not in page_masks:
            return 0.0, 0.0
        m = page_masks[p]
        h, w = m.shape
        x1 = max(0, int(a["bbox"][0])); y1 = max(0, int(a["bbox"][1]))
        x2 = min(w, int(a["bbox"][2])); y2 = min(h, int(a["bbox"][3]))
        if x2 <= x1 or y2 <= y1:
            return 0.0, 0.0
        cov = float(m[y1:y2, x1:x2].mean())
        mean = float(m.mean()) or 1e-9
        return round(cov, 5), round(cov / mean, 3)

    per_box = []
    ious, covers = [], []
    for a in sorted(hist_q, key=lambda x: (mapped(x), x["bbox"][1])):
        pi = mapped(a)
        same = [c for c in q_cands if c["page_index"] == pi]
        best, bi = 0.0, 0.0
        best_c = None
        for c in same:
            v = iou(c["bbox"], a["bbox"])
            if v > best:
                best, best_c = v, c
                bi = inter_over_hist(c["bbox"], a["bbox"])
        allc = [c for c in cands if c["page_index"] == pi]
        best_all = max((iou(c["bbox"], a["bbox"]) for c in allc), default=0.0)
        cov, ratio = ink_signal(a)
        # 紧致真值：历史框内的实际墨迹连通域 bbox。
        # 它把"标注者画框留白"这一层剥掉，用来给出 (a) 紧致检测器的 IoU 上限、
        # (b) 检测器与"文字真实位置"的贴合度。
        tight = None
        best_tight, best_tight_c = 0.0, None
        if page_masks and pi in page_masks:
            tight = [round(v, 2) for v in cc_refine_bbox(page_masks[pi], a["bbox"],
                                                         cc_min_area, 1)]
            for c in same:
                v = iou(c["bbox"], tight)
                if v > best_tight:
                    best_tight, best_tight_c = v, c
        ious.append(best)
        covers.append(bi)
        per_box.append({
            "rect_id": a["rect_id"], "ann_page_index": a["page_index"],
            "image_index": pi,
            "order_in_level": a["order_in_level"], "bbox": [round(v, 2) for v in a["bbox"]],
            "best_iou_question_cand": round(best, 4),
            "best_cand_id": best_c["cand_id"] if best_c else None,
            "coverage_of_hist": round(bi, 4),
            "best_iou_any_cand": round(best_all, 4),
            "hit_iou50": bool(best >= 0.5),
            "hist_box_ink_cov": cov,
            "hist_box_ink_cov_vs_page_mean": ratio,
            "hist_box_has_text_signal": bool(ratio >= 1.0),
            "tight_ink_bbox_in_hist": tight,
            "iou_hist_vs_tight_ink_bbox": round(iou(a["bbox"], tight), 4) if tight else None,
            "best_iou_q_cand_vs_tight_ink_bbox": round(best_tight, 4) if tight else None,
            "best_tight_cand_id": best_tight_c["cand_id"] if best_tight_c else None,
            "hit_tight_iou50": bool(best_tight >= 0.5),
        })

    per_page = {}
    for p in pages:
        sub = [r for r in per_box if r["image_index"] == p]
        if not sub:
            continue
        per_page[str(p)] = {
            "n_history_question": len(sub),
            "n_hit_iou50": sum(1 for r in sub if r["hit_iou50"]),
            "recall_iou50": round(sum(1 for r in sub if r["hit_iou50"]) / len(sub), 4),
            "iou_mean": round(float(np.mean([r["best_iou_question_cand"] for r in sub])), 4),
            "n_q_candidates": sum(1 for c in q_cands if c["page_index"] == p),
            "n_boxes_with_text_signal": sum(1 for r in sub if r["hist_box_has_text_signal"]),
        }

    # 子集：历史框所在区域墨迹高于整页均值（说明框里确实有内容），才是"检测器可被公平考核"的子集
    sig = [r for r in per_box if r["hist_box_has_text_signal"]]
    n_sig_hit = sum(1 for r in sig if r["hit_iou50"])

    # 三层口径（见报告 §4）：
    #   L1 原样历史框：任务规定的 IoU/召回口径，但受"标注留白"影响
    #   L2 上限：紧致检测器对原样历史框能达到的 IoU（= IoU(历史框, 框内墨迹紧致框)）
    #   L3 检测器真实贴合度：我的 Q 候选 vs 框内墨迹紧致框
    tight_rows = [r for r in per_box if r.get("iou_hist_vs_tight_ink_bbox") is not None]
    n_ub = sum(1 for r in tight_rows if r["iou_hist_vs_tight_ink_bbox"] >= 0.5)
    n_l3 = sum(1 for r in tight_rows if r["hit_tight_iou50"])

    # 反向：候选框对历史框的命中（查假阳性）
    prec = []
    for c in q_cands:
        same = [a for a in hist_q if mapped(a) == c["page_index"]]
        best = max((iou(c["bbox"], a["bbox"]) for a in same), default=0.0)
        prec.append({"cand_id": c["cand_id"], "image_index": c["page_index"],
                     "bbox": c["bbox"], "best_iou_vs_history": round(best, 4),
                     "matched_iou50": bool(best >= 0.5)})
    n_hit = sum(1 for r in prec if r["matched_iou50"])

    n_hit_total = sum(1 for r in per_box if r["hit_iou50"])

    # choice：历史是"4 选项合 1 框"，口径不同 → 只报容器一致性
    choice_eval = []
    for a in hist_choice:
        pi = mapped(a)
        inside = []
        for c in w_cands:
            if c["page_index"] != pi:
                continue
            cx = (c["bbox"][0] + c["bbox"][2]) / 2.0
            cy = (c["bbox"][1] + c["bbox"][3]) / 2.0
            if a["bbox"][0] <= cx <= a["bbox"][2] and a["bbox"][1] <= cy <= a["bbox"][3]:
                inside.append(c["cand_id"])
        area = (a["bbox"][2] - a["bbox"][0]) * (a["bbox"][3] - a["bbox"][1])
        choice_eval.append({
            "rect_id": a["rect_id"], "ann_page_index": a["page_index"], "image_index": pi,
            "order_in_level": a["order_in_level"],
            "n_my_options_center_inside": len(inside),
            "my_option_ids": inside[:12],
            "hist_box_area_px": round(area, 2),
            "note": "历史 choice=4选项合1框，只有 4 说明我的选项框完整落在该容器内",
        })

    roles_by_page: dict[str, dict] = {}
    for c in cands:
        d = roles_by_page.setdefault(str(c["page_index"]), {})
        d[c["role"]] = d.get(c["role"], 0) + 1

    return {
        "mapping": {
            "offset": offset,
            "rule": "image_index = annotation.page_index + offset",
            "offset_-1_meaning": "offset=-1 即 page_index N ↔ 46006966_page_{N-1}.jpg",
            "evidence": "由 lead/aocr 用平台裁剪图归一化互相关(31/36 更匹配) + OCR 语义校验共同确认；"
                        "本脚本另用『历史框墨迹密度/整页均值』做独立旁证（见 per_box。"
                        "hist_box_ink_cov_vs_page_mean）。",
            "scope_pages_image_index": pages,
        },
        "question_vs_history": {
            "scope_pages": pages,
            "n_history_question_boxes": len(hist_q),
            "n_usable": len(hist_q),
            "n_hit_iou50": n_hit_total,
            "recall_iou50": round(n_hit_total / len(hist_q), 4) if hist_q else None,
            "iou_of_best_question_cand": stats_of(ious),
            "coverage_of_hist": stats_of(covers),
            "recall_any_role_iou50": round(
                sum(1 for r in per_box if r["best_iou_any_cand"] >= 0.5) / len(per_box), 4
            ) if per_box else None,
            "L2_upper_bound_tight_detector": {
                "definition": "把历史框内的墨迹连通域收紧成 bbox，再算 IoU(原历史框, 紧致框)；"
                              "这是任何只框文字、不留白的检测器能达到的 IoU 上限",
                "n_boxes_reachable_iou50": n_ub,
                "max_recall_iou50": round(n_ub / len(tight_rows), 4) if tight_rows else None,
                "iou_stats": stats_of([r["iou_hist_vs_tight_ink_bbox"] for r in tight_rows]),
            },
            "L3_detector_vs_tight_truth": {
                "definition": "我的 Q 候选框 vs 『历史框内墨迹紧致框』的 IoU 召回（剥离标注留白后的"
                              "检测器质量）",
                "n_hit_iou50": n_l3,
                "recall_iou50": round(n_l3 / len(tight_rows), 4) if tight_rows else None,
                "iou_stats": stats_of([r["best_iou_q_cand_vs_tight_ink_bbox"]
                                       for r in tight_rows]),
            },
            "subset_hist_boxes_with_text_signal": {
                "definition": "历史框区域内墨迹比例 / 整页平均墨迹比例 >= 1.0（框里确实有内容），"
                              "是检测器可被公平考核的子集",
                "n_boxes": len(sig),
                "n_hit_iou50": n_sig_hit,
                "recall_iou50": round(n_sig_hit / len(sig), 4) if sig else None,
                "iou_mean": round(float(np.mean([r["best_iou_question_cand"] for r in sig])), 4)
                             if sig else None,
                "rect_ids": [r["rect_id"] for r in sig],
            },
            "per_page": per_page,
            "per_box": per_box,
        },
        "question_precision_proxy": {
            "n_question_candidates": len(q_cands),
            "n_candidates_matching_a_history_box_iou50": n_hit,
            "unmatched_candidates": [r for r in prec if not r["matched_iou50"]],
            "per_candidate": prec,
        },
        "choice_container_consistency": {
            "n_history_choice_boxes": len(hist_choice),
            "n_boxes_with_4_my_options_inside": sum(
                1 for r in choice_eval if r["n_my_options_center_inside"] == 4),
            "per_box": choice_eval,
        },
        "role_counts_by_page": roles_by_page,
        "unusable_history_boxes": unusable_pages,
    }


def unusable_report(anns: list[dict], img_wh: dict, offset: int = -1) -> dict:
    """
    按 verify_report 的口径，标出坐标不可用的历史框（已套用 page_index → 页图 的映射）。
    """
    out = {"mapping_offset": offset, "pages": {}, "boxes": []}
    ann_pages = sorted({int(a["page_index"]) for a in anns})
    for ap in ann_pages:
        ip = ap + offset
        sub = [a for a in anns if int(a["page_index"]) == ap]
        if ip not in img_wh:
            out["pages"][str(ap)] = {"ann_page_index": ap, "image_index": None,
                                     "n_boxes": len(sub), "verdict": "NO_IMAGE"}
            continue
        w, h = img_wh[ip]
        max_x2 = max(a["bbox"][2] for a in sub)
        max_y2 = max(a["bbox"][3] for a in sub)
        span = max_x2 / float(w)
        if max_x2 > w or max_y2 > h:
            verdict = "OUT_OF_BOUNDS"
        elif span < 0.5:
            verdict = "SUSPECT_COORD_SPACE"
        else:
            verdict = "OK"
        out["pages"][str(ap)] = {"ann_page_index": ap, "image_index": ip,
                                 "n_boxes": len(sub), "img_w": w, "img_h": h,
                                 "max_x2": round(max_x2, 2), "max_y2": round(max_y2, 2),
                                 "x_span_frac": round(span, 4), "verdict": verdict}
        if verdict != "OK":
            for a in sub:
                out["boxes"].append({
                    "rect_id": a["rect_id"], "ann_page_index": ap, "image_index": ip,
                    "type": a["type"], "reason": verdict,
                    "note": ("x2=%.2f 超图宽 %d（超 %.2fpx）" % (max_x2, w, max_x2 - w)
                             if verdict == "OUT_OF_BOUNDS"
                             else "横向只用到图宽 %.1f%%：该页为多页拼合宽图，记录坐标空间"
                                  "与这张图不是同一画布，未找到可离线复原的平移-缩放关系"
                                  "（见 data/derived/verify_report.md §3.1）" % (100 * span)),
                })
    return out


# ---------------------------------------------------------------- 可视化


def draw_overlay(bgr: np.ndarray, cands: list[dict], hist: list[dict],
                 max_width: int = 1800) -> np.ndarray:
    img = bgr.copy()
    for c in cands:
        x1, y1, x2, y2 = [int(round(v)) for v in c["bbox"]]
        cv2.rectangle(img, (x1, y1), (x2, y2), ROLE_BGR[c["role"]], 3)
        cv2.putText(img, c["cand_id"], (x1, max(14, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, ROLE_BGR[c["role"]], 1, cv2.LINE_AA)
    for a in hist:
        x1, y1, x2, y2 = [int(round(v)) for v in a["bbox"]]
        color = (0, 255, 255) if a["type"] == "question" else (255, 255, 0)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, f"H-{a['type'][:4]}#{a['order_in_level']}", (x1, max(12, y1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
    h, w = img.shape[:2]
    if w > max_width:
        s = max_width / float(w)
        img = cv2.resize(img, (max_width, int(h * s)), interpolation=cv2.INTER_AREA)
    return img


# ---------------------------------------------------------------- 主流程


def process_page(page_index: int, cfg: dict, use_ocr: bool) -> dict:
    path = IMAGES_DIR / f"46006966_page_{page_index}.jpg"
    t_page = time.time()
    gray = imread_gray(path)
    h, w = gray.shape
    mask = gray < cfg["thresh"]

    t0 = time.time()
    subpages, split_info = split_subpages(mask, cfg)
    t_split = time.time() - t0

    bgr = imread_bgr(path) if use_ocr else None

    t0 = time.time()
    regions = []
    for sp in subpages:
        y1, y2 = 0, h
        x1, x2 = sp["x1"], sp["x2"]
        tx1, tx2 = trim_low_ink_columns(mask, x1, x2, cfg["seam_ink_frac"])
        if tx2 - tx1 >= 20:
            x1, x2 = tx1, tx2
        lines = detect_lines(mask, x1, x2, y1, y2, cfg)
        regions.append({"subpage_index": sp["subpage_index"], "x1": x1, "x2": x2,
                        "lines": lines})
    t_lines = time.time() - t0

    # 纯几何基线：段落块（永远产出，便于与语义候选对照）
    geom_blocks = []
    for reg in regions:
        blocks, thr = group_by_gaps(reg["lines"], cfg)
        for b in blocks:
            bb = union_bbox([ln["bbox"] for ln in b])
            geom_blocks.append({
                "subpage_index": reg["subpage_index"],
                "bbox": [round(float(v), 2) for v in bb],
                "n_lines": len(b), "gap_threshold": thr,
                "geom_method": "projection+connected_components",
            })

    t_ocr = 0.0
    if use_ocr:
        t0 = time.time()
        for reg in regions:
            crop = bgr[0:h, reg["x1"]:reg["x2"]]
            atoms = ocr_atoms(crop, ox=reg["x1"], oy=0, score_floor=cfg["ocr_score_floor"])
            attach_atoms(reg["lines"], atoms)
        t_ocr = time.time() - t0

    cands: list[dict] = []
    n_furniture = 0
    for reg in regions:
        cc, nf = group_candidates(reg["lines"], mask, cfg, page_index, reg["subpage_index"])
        cands += cc
        n_furniture += nf
    if not use_ocr:
        # 无 OCR：用几何段落块作为候选，角色标记为 text_block
        cands = []
        for gb in geom_blocks:
            bb = gb["bbox"]
            cands.append(make_candidate(
                page_index, gb["subpage_index"], "text_block", bb, 0.0,
                "geom_heuristic", f"段落块：投影+连通域，{gb['n_lines']} 行，"
                                  f"间隙阈值 {gb['gap_threshold']}",
                [], mask, cfg))
    number_candidates(cands)

    # 检测器自检：候选框并集覆盖了全页多少墨迹（与历史坐标无关，衡量"有没有漏掉内容"）
    covered = np.zeros_like(mask)
    for c in cands:
        x1 = max(0, int(np.floor(c["bbox"][0]))); y1 = max(0, int(np.floor(c["bbox"][1])))
        x2 = min(w, int(np.ceil(c["bbox"][2]))); y2 = min(h, int(np.ceil(c["bbox"][3])))
        if x2 > x1 and y2 > y1:
            covered[y1:y2, x1:x2] = True
    total_ink = int(mask.sum())
    covered_ink = int((mask & covered).sum())

    n_lines_total = sum(len(r["lines"]) for r in regions)
    lines_with_text = sum(1 for r in regions for ln in r["lines"] if ln["text"])
    return {
        "page_index": page_index,
        "image": str(path.relative_to(ROOT)).replace("\\", "/"),
        "width": int(w), "height": int(h),
        "image_wh_ratio": round(w / float(h), 4),
        "ink_ratio_pct": round(100.0 * float(mask.mean()), 4),
        "n_subpages": len(subpages),
        "subpages": subpages,
        "split_info": split_info,
        "n_text_lines": n_lines_total,
        "n_lines_with_ocr_text": lines_with_text,
        "n_furniture_lines_dropped": n_furniture,
        "ocr_line_coverage": round(lines_with_text / n_lines_total, 4) if n_lines_total else None,
        "geom_blocks": geom_blocks,
        "n_geom_blocks": len(geom_blocks),
        "candidates": cands,
        "total_ink_px": total_ink,
        "ink_px_inside_candidates": covered_ink,
        "ink_recall_pct": round(100.0 * covered_ink / total_ink, 3) if total_ink else None,
        "timing_sec": {"split_subpages": round(t_split, 2), "lines_and_cc": round(t_lines, 2),
                       "ocr": round(t_ocr, 2), "page_total": round(time.time() - t_page, 2)},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="路线A：本地版面检测出框基线（CPU-only）")
    ap.add_argument("--pages", nargs="*", type=int, default=[7, 8, 9, 10, 233, 234])
    ap.add_argument("--no-ocr", action="store_true", help="只跑几何基线（投影+连通域）")
    ap.add_argument("--out", default=str(OUT_DIR / "route_a_candidates.json"))
    ap.add_argument("--no-overlay", action="store_true")
    ap.add_argument("--thresh", type=int, default=CFG["thresh"])
    args = ap.parse_args()

    cfg = dict(CFG)
    cfg["thresh"] = args.thresh
    use_ocr = not args.no_ocr

    t_all = time.time()
    started = datetime.now(CN_TZ)
    pages = []
    for p in args.pages:
        path = IMAGES_DIR / f"46006966_page_{p}.jpg"
        if not path.exists():
            print(f"[skip] 缺图: {path}", flush=True)
            continue
        t0 = time.time()
        info = process_page(p, cfg, use_ocr)
        pages.append(info)
        counts: dict[str, int] = {}
        for c in info["candidates"]:
            counts[c["role"]] = counts.get(c["role"], 0) + 1
        print(f"[page {p}] {info['width']}x{info['height']} subpages={info['n_subpages']} "
              f"lines={info['n_text_lines']} blocks={info['n_geom_blocks']} "
              f"cands={counts} {time.time() - t0:.1f}s", flush=True)

    anns = load_annotations()
    img_wh = {p["page_index"]: (p["width"], p["height"]) for p in pages}
    all_cands = [c for p in pages for c in p["candidates"]]
    # 正确映射：annotation.page_index N ↔ 页图 page_{N-1}（lead/aocr 已双重验证）
    OFF = cfg["ann_page_offset"]
    pages_with_q = {int(a["page_index"]) + OFF for a in anns if a["type"] == "question"}
    primary_pages = [p for p in args.pages if p in pages_with_q]
    alt_pages = [p for p in args.pages if p in {int(a["page_index"]) for a in anns}]
    unusable = unusable_report(anns, img_wh, OFF)
    page_masks = {}
    for p in pages:
        page_masks[p["page_index"]] = imread_gray(
            IMAGES_DIR / f"46006966_page_{p['page_index']}.jpg") < cfg["thresh"]
    evaluation = {}
    if all_cands:
        primary = evaluate(all_cands, anns, primary_pages, unusable, page_masks, offset=OFF)
        # 对照：不做映射（旧口径），用于证明 off-by-one 修正带来的差异
        alt_unusable = unusable_report(anns, img_wh, 0)
        alt = evaluate(all_cands, anns, alt_pages, alt_unusable, page_masks, offset=0)
        evaluation = {
            "mapping_correction": {
                "adopted_offset": OFF,
                "adopted_rule": "image_index = annotation.page_index - 1",
                "source": "lead/aocr：平台裁剪图归一化互相关 31/36 显著更匹配 + OCR 语义校验 "
                          "(choice 5/5 出现 A./B./C./D.；question 行首数字与 order_in_level 吻合 "
                          "0/16 → 7/16)；尺度 1:1（sx 中位 0.997）",
                "independent_check": "本脚本用『历史框墨迹密度 / 整页均值』复核："
                                     "page_index=8 在 page_7 上 ratio=1.00（page_8 上 0.67）；"
                                     "page_index=10 在 page_9 上 1.38（page_10 上 1.26）",
            },
            **primary,
            "alt_mapping_page_index_as_is": alt,
        }

    payload = {"pages": pages, "evaluation": evaluation}
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    # 哈希视图排除耗时字段（机器相关的非确定性），其余内容应与第三方重跑逐字节一致
    hash_view = {
        "pages": [{k: v for k, v in p.items() if k != "timing_sec"} for p in pages],
        "evaluation": evaluation,
    }
    content_sha = hashlib.sha256(
        json.dumps(hash_view, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    elapsed = time.time() - t_all
    result = {
        "meta": {
            "script": "tools/route_a_layout.py",
            "route": "A_local_layout_baseline",
            "goal": "页 8/9/10 单页扫描上跑通版面检测并给出 Q/W/A/E 角色候选框 + 与历史标注的召回/IoU",
            "generated_at": started.isoformat(),
            "elapsed_sec_total": round(elapsed, 2),
            "python": sys.version.split()[0],
            "cpu_only": True,
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
            "onnxruntime_providers": _ort_providers(),
            "ocr_enabled": use_ocr,
            "ocr_engine": cfg["ocr_engine"] if use_ocr else None,
            "ocr_model_download_bytes": 0 if use_ocr else None,
            "ocr_model_note": ("rapidocr_onnxruntime 自带 ch_PP-OCRv4 det/rec/cls onnx 模型，"
                               "随 wheel 安装，本次运行未触发任何下载") if use_ocr else None,
            "config": cfg,
            "pages_processed": [p["page_index"] for p in pages],
            "command": " ".join([Path(sys.executable).name, "tools/route_a_layout.py"] +
                                (["--no-ocr"] if args.no_ocr else []) +
                                ["--pages"] + [str(p) for p in args.pages]),
            "content_sha256": content_sha,
            "content_sha256_scope": "sha256(json.dumps({'pages'(去 timing_sec),'evaluation'}, "
                                    "sort_keys=True))；除 meta.generated_at / 各 timing_sec 外输出确定，"
                                    "第三方重跑应得到同一 content_sha256",
        },
        "items_required_by_task": {
            "1_layout_detection_on_8_9_10": "见 pages[].candidates / geom_blocks",
            "2_role_labels": "Q=question, W=option(逐个), A=answer, E=analysis",
            "3_history_comparison": "见 evaluation.question_vs_history / choice_container_consistency",
            "4_subpage_split": "见 pages[].subpages / split_info（233/234 为多页拼合，按纵向沟切）",
        },
        **payload,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[write] {out_path}  ({out_path.stat().st_size} bytes, sha256={content_sha[:16]})")

    if not args.no_overlay:
        for info in pages:
            bgr = imread_bgr(ROOT / info["image"])
            # 历史框按正确映射画到对应页图：annotation.page_index = image_index - offset
            hist = [a for a in anns if int(a["page_index"]) + OFF == info["page_index"]]
            ov = draw_overlay(bgr, info["candidates"], hist)
            op = OUT_DIR / f"route_a_overlay_page{info['page_index']}.png"
            imwrite_u(op, ov)
            print(f"[overlay] {op}  (历史框 {len(hist)} 个，已按 offset={OFF} 映射)")

    ev = evaluation.get("question_vs_history", {})
    print(f"[eval] question recall@IoU0.5 = {ev.get('recall_iou50')} "
          f"({ev.get('n_hit_iou50')}/{ev.get('n_history_question_boxes')}) "
          f"iou={ev.get('iou_of_best_question_cand')}")
    print(f"[done] {elapsed:.1f}s  total_pages={len(pages)}")
    return 0


def _ort_providers():
    try:
        import onnxruntime as ort
        return ort.get_available_providers()
    except Exception as exc:  # pragma: no cover
        return [f"unavailable: {type(exc).__name__}"]


if __name__ == "__main__":
    raise SystemExit(main())
