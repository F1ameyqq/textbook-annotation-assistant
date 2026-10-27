#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/page_measure.py — 题目页版面测量（几何行投影为骨架 + OCR 题号贴标签 → 题块框）

为什么不是"OCR 找题号→直接切"（2026-10-27 实测教训）
---------------------------------------------------
p27.jpg 上 OCR 把 Q1 的公式行切成了 5 个碎片（`3` / `的数学表达式是（` / `25`…），
`1.“9/25` 这个题号根本没成为一个 atom；另一处又把页中间的 `9` 误认成题号 9。
所以**不能用 OCR 题号当唯一骨架**。正确做法：

1. 几何：墨迹投影 → 栏 → 行段（rows2 的墨迹比例法），行段带"左缘 x"
2. 语义：OCR 只负责给行贴「题号」标签（能贴上的更可信，贴不上靠结构补）
3. 补漏：把「左缘齐栏（±8px）且不含章节关键词」的行当作题号候选行，
   在已识别锚点之间按序号连续性补号；补不上就标 low_confidence，交人确认

用法
----
    python -I tools/page_measure.py page.jpg [--no-ocr] [--ink-frac 0.01]
输出
----
    data/derived/measure/<stem>.measure.json   行段 + 题块 + 锚点来源
    data/derived/measure/<stem>.contact.json   contact sheet 用的候选框
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "derived" / "measure"
THRESH = 165
QNUM_RE = re.compile(r"^\s*(\d{1,2})\s*[.．、]")
# 这些行不是题号行（章节/栏目标题、徽标）
SECTION_KW = ("知识点", "基础题", "中档题", "综合题", "易错点", "微专题", "小专题",
              "变式", "章末", "复习", "回顾", "课时", "教材", "考点", "核心素养",
              "专题", "答案", "解析")


def ink_mask(gray: np.ndarray, thresh: int = THRESH) -> np.ndarray:
    return gray < thresh


def column_windows(mask: np.ndarray, min_gap: int = 8) -> list[tuple[int, int]]:
    H, W = mask.shape
    col_ink = mask.sum(axis=0)
    blank = col_ink <= max(2, int(0.005 * H))
    runs, start = [], None
    for i, v in enumerate(blank):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_gap:
                runs.append((start, i))
            start = None
    if start is not None and len(blank) - start >= min_gap:
        runs.append((start, len(blank)))
    panels, cur = [], 0
    for s, e in runs:
        if s - cur > 40:
            panels.append((cur, s))
        cur = e
    if W - cur > 40:
        panels.append((cur, W))
    return panels


def row_segments(mask: np.ndarray, x1: int, x2: int, y1: int, y2: int,
                 ink_frac: float = 0.01, min_gap: int = 4) -> list[dict]:
    """行段 + 左缘 x（左缘 = 行内第一列有墨的 x）。"""
    sub = mask[y1:y2, x1:x2]
    frac = sub.sum(axis=1) / max(1, x2 - x1)
    flags = frac >= ink_frac
    runs, start = [], None
    for i, v in enumerate(flags):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append([start, i])
            start = None
    if start is not None:
        runs.append([start, len(flags)])
    merged: list[list[int]] = []
    for s, e in runs:
        if merged and s - merged[-1][1] < min_gap:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    out = []
    for s, e in merged:
        band = sub[s:e, :]
        cols = np.where(band.any(axis=0))[0]
        left = int(cols[0]) + x1 if len(cols) else x1
        right = int(cols[-1]) + x1 if len(cols) else x2
        out.append({"y1": s + y1, "y2": e + y1, "left": left, "right": right})
    return out


def ocr_atoms(img_path: Path) -> list[dict]:
    from rapidocr_onnxruntime import RapidOCR
    res, _ = RapidOCR()(str(img_path))
    out = []
    for item in res or []:
        box, text, score = item[0], item[1], float(item[2]) if len(item) > 2 else 0.0
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        out.append({"text": str(text), "score": score,
                    "x1": int(min(xs)), "y1": int(min(ys)),
                    "x2": int(max(xs)), "y2": int(max(ys))})
    return out


def build_questions(panels, rows_by_panel, atoms, img_h: int) -> tuple[list[dict], list[dict]]:
    """返回 (questions, debug_anchors)。img_h = 页图高度，用于最后一题的框底。"""
    H = img_h
    questions, debug = [], []

    def panel_of(xc):
        for i, (x1, x2) in enumerate(panels):
            if x1 <= xc <= x2:
                return i
        return None

    # 行 → 该行的 OCR 文本（用于章节关键词判断）。
    # 折衷过两次才定：±16px 会吸到邻行徽标（p34 Q5 被误杀）；
    # 用整行区间（y1..y2）会吸到同一块里的「知识点3」（p34 Q6 被误杀）。
    # 正解：只看**与锚点同一行**的 atom（y1 落在 [y1-6, y1+26]）。
    def line_text(y, x1=None, x2=None) -> str:
        hs = [a["text"] for a in atoms
              if -6 <= a["y1"] - y <= 26
              and (x1 is None or (x1 - 5 <= a["x1"] <= x2 + 5))]
        return " ".join(hs)

    # 行区间内所有 atom 文本（仅用于剪掉尾部徽标行，范围要宽）
    def row_text(rows, y, y2=None) -> str:
        if y2 is None:
            hs = [a["text"] for a in atoms if abs(a["y1"] - y) < 16]
        else:
            hs = [a["text"] for a in atoms
                  if not (a["y2"] < y - 2 or a["y1"] > y2 + 2)]
        return " ".join(hs)

    for pi, (px1, px2) in enumerate(panels):
        rows = rows_by_panel[pi]
        if not rows:
            continue
        # 1) OCR 锚点：题号 atom 贴近栏左 → 吸附到最近行
        anchors: dict[int, dict] = {}
        for a in atoms:
            m = QNUM_RE.match(a["text"])
            if not m or a["x1"] - px1 > 60:
                continue
            if panel_of((a["x1"] + a["x2"]) // 2) != pi:
                continue
            nearest = min(rows, key=lambda r: abs(r["y1"] - a["y1"]))
            if abs(nearest["y1"] - a["y1"]) > 14:
                debug.append({"panel": pi, "num": int(m.group(1)), "y": a["y1"],
                              "status": "rejected: no row nearby", "text": a["text"][:24]})
                continue
            txt = line_text(nearest["y1"], px1, px2)
            if any(k in txt for k in SECTION_KW):
                debug.append({"panel": pi, "num": int(m.group(1)), "y": a["y1"],
                              "status": "rejected: section keyword", "text": a["text"][:24]})
                continue
            num = int(m.group(1))
            anchors.setdefault(num, {"num": num, "row": nearest, "source": "ocr"})
        # 2) 齐栏行候选（补漏用）
        flush = [r for r in rows if r["left"] - px1 <= 8]
        flush = [r for r in flush if not any(k in line_text(r["y1"], px1, px2) for k in SECTION_KW)]
        # 3) 补号：先补已有锚点之间的空号，再补首个锚点之前的号
        anchors_sorted = sorted(anchors.values(), key=lambda x: x["row"]["y1"])
        existing_nums = [a["num"] for a in anchors_sorted]
        extra = []
        for i in range(len(anchors_sorted) - 1):
            a, b = anchors_sorted[i], anchors_sorted[i + 1]
            gap = b["num"] - a["num"]
            if gap <= 1:
                continue
            between = [r for r in flush
                       if a["row"]["y1"] < r["y1"] < b["row"]["y1"]
                       and all(abs(r["y1"] - e["row"]["y1"]) > 6 for e in anchors_sorted)]
            need = gap - 1
            if len(between) == need:
                for k, r in enumerate(between, 1):
                    extra.append({"num": a["num"] + k, "row": r, "source": "fill_between"})
            else:
                debug.append({"panel": pi, "num": f"{a['num']}..{b['num']}",
                              "status": f"fill_between ambiguous: {len(between)} rows vs {need}",
                              "y": a["row"]["y1"]})
        if anchors_sorted:
            first = anchors_sorted[0]
            above = [r for r in flush if r["y1"] < first["row"]["y1"]
                     and all(abs(r["y1"] - e["row"]["y1"]) > 6 for e in anchors_sorted)]
            need = first["num"] - 1
            if 0 < need <= len(above):
                picked = above[-need:]
                for k, r in enumerate(picked):
                    extra.append({"num": first["num"] - need + k, "row": r,
                                  "source": "fill_before"})
                if len(above) > need:
                    debug.append({"panel": pi, "num": f"<{first['num']}",
                                  "status": f"{len(above)} flush rows above but only {need} needed",
                                  "y": first["row"]["y1"]})
        merged = {a["num"]: a for a in anchors_sorted}
        for e in extra:
            merged.setdefault(e["num"], e)
        ordered = sorted(merged.values(), key=lambda x: x["row"]["y1"])

        # 4) 题块：本栏该题号行顶 → 下一题号行顶；
        #    但要把「下一节徽标」（知识点/中档题/综合题…）和尾部空白剪掉，
        #    否则徽标文字会被 OCR 吃进上一题的题干（2026-10-27 实测）。
        for i, a in enumerate(ordered):
            nxt = ordered[i + 1] if i + 1 < len(ordered) else None
            y1 = a["row"]["y1"] - 4
            limit = (nxt["row"]["y1"] - 1) if nxt else H - 1
            inside = [r for r in rows if y1 <= r["y1"] < max(y1 + 1, limit)]
            # 去掉尾部徽标行
            while inside and any(k in row_text(rows, inside[-1]["y1"], inside[-1]["y2"]) for k in SECTION_KW):
                inside.pop()
            y2 = (inside[-1]["y2"] + 4) if inside else a["row"]["y2"] + 4
            y2 = min(y2, limit)
            questions.append({
                "num": a["num"], "panel": pi,
                "bbox": [px1, max(0, y1), px2, y2],
                "anchor_source": a["source"],
                "confidence": "high" if a["source"] == "ocr" else "low",
            })
    questions.sort(key=lambda q: (q["panel"], q["num"]))
    return questions, debug


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--ink-frac", type=float, default=0.01)
    args = ap.parse_args()

    img_path = Path(args.image)
    bgr = cv2.imread(str(img_path))
    if bgr is None:
        raise SystemExit(f"读不到图片: {img_path}")
    H, W = bgr.shape[:2]
    mask = ink_mask(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))

    panels = column_windows(mask)
    print(f"[版面] {img_path.name} {W}x{H}  栏: {panels}")
    rows_by_panel = [row_segments(mask, x1, x2, 0, H, args.ink_frac) for x1, x2 in panels]
    for i, rows in enumerate(rows_by_panel):
        print(f"[行] panel{i} 共 {len(rows)} 行段")

    atoms, questions, debug = [], [], []
    if not args.no_ocr:
        print("[OCR] 识别中…")
        atoms = ocr_atoms(img_path)
        print(f"[OCR] {len(atoms)} atom")
        questions, debug = build_questions(panels, rows_by_panel, atoms, H)

    result = {"image": str(img_path), "w": W, "h": H, "panels": panels,
              "rows": rows_by_panel, "questions": questions,
              "anchor_debug": debug, "n_atoms": len(atoms)}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUT_DIR / f"{img_path.stem}.measure.json"
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    hi = [q for q in questions if q["confidence"] == "high"]
    print(f"[题块] 共 {len(questions)} 个（高置信 {len(hi)}，待确认 {len(questions) - len(hi)}）")
    for q in questions:
        flag = "" if q["confidence"] == "high" else "  ← 待确认"
        print(f"   Q{q['num']:>2} panel{q['panel']} y[{q['bbox'][1]},{q['bbox'][3]}]"
              f" src={q['anchor_source']}{flag}")
    for d in debug:
        print(f"   [debug] {d}")

    boxes = [{"bbox": q["bbox"], "role": "question", "id": f"Q{q['num']}"} for q in questions]
    if boxes:
        cs = OUT_DIR / f"{img_path.stem}.contact.json"
        cs.write_text(json.dumps(boxes, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[contact] {cs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------- 选项框（W）
OPT_RE = re.compile(r"^\s*([A-D])\s*[.．、]\s*")


def options_in_block(atoms: list[dict], bbox, pad: int = 3) -> list[dict]:
    """从 OCR atom 里挑出落在题块内、且以 A./B./C./D. 开头的 atom，作为选项框候选。"""
    x1, y1, x2, y2 = bbox
    out = []
    for a in atoms:
        m = OPT_RE.match(a["text"])
        if not m:
            continue
        ax1, ay1, ax2, ay2 = a["x1"], a["y1"], a["x2"], a["y2"]
        if not (x1 - 4 <= ax1 <= x2 and y1 - 6 <= ay1 <= y2):
            continue
        out.append({"label": m.group(1),
                    "bbox": [max(x1, ax1 - pad), max(y1, ay1 - pad),
                             min(x2, ax2 + pad), min(y2, ay2 + pad)],
                    "text": a["text"][:24]})
    out.sort(key=lambda o: (o["bbox"][1], o["bbox"][0]))
    return out
