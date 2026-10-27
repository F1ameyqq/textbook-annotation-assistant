#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/answer_rows.py — 答案页「一行多题」切分（几何行 + OCR 题号锚点）

问题
----
答案页是密集排版：`1.A 2.D 3.24` 一行挤三道题的答案；而 `4.解:…` 这类是
多行连续段。纯阈值/投影切不出「长短悬殊」的行（2026-10-27 阈值扫描实测：
170→245 全程块数 16/22/21/20/18/16/14/10/10/8，永远得不到正确的 4 块）。

做法
----
1. 行投影得到 y 行段（rows2 的墨迹比例法）
2. 在区域内跑 OCR，取形如 `N.` 的 atom 作为**题号锚点**，记 x 位置
3. 同一行内按锚点 x 排序 → 相邻锚点之间即为该题答案的横向范围
4. 没有锚点的行 → 判定为上一题答案的续行（多行段落），并入上一题的框
5. 输出每题的答案框 bbox（源图像素），并标出缺失题号供人工确认

用法
----
    python -I tools/answer_rows.py page.jpg --x1 615 --x2 1120 --y1 1140 --y2 1320 \
        --nums 1-14 [--out data/derived/measure/ans_p173.json]
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
NUM_RE = re.compile(r"^\s*(\d{1,2})\s*[.．]")
# 行内题号：不允许前面紧贴数字，否则 "12.11" 会同时匹配出 "2."
NUM_INLINE = re.compile(r"(?<!\d)(\d{1,2})\s*[.．]")


def anchors_from_atoms(atoms):
    """
    从 atom 里抽题号锚点。
    - atom 以题号开头 → x 用 atom 左缘（最可靠）
    - 题号夹在文本中间（`1.A 2.D 3.24`、`10.B 11.±3 12.11`）→ 按字符位置**比例反推 x**
      （RapidOCR 只给四点多边形，拿不到逐字坐标；比例反推是近似，交 contact sheet 人确认）
    """
    anchors = []
    for a in atoms:
        text = a["text"]
        n = max(1, len(text))
        for m in NUM_INLINE.finditer(text):
            idx = m.start()
            if idx == 0:
                x = a["x1"]
                reliable = True
            else:
                x = a["x1"] + int((a["x2"] - a["x1"]) * idx / n)
                reliable = False
            anchors.append({"num": int(m.group(1)), "x": x, "y": a["y1"],
                            "text": text[max(0, idx - 2): idx + 6],
                            "reliable": reliable})
    return anchors


def ink_mask(gray, thresh=THRESH):
    return gray < thresh


def rows_in(mask, x1, x2, y1, y2, ink_frac=0.01, min_gap=4):
    sub = mask[y1:y2, x1:x2]
    frac = sub.sum(axis=1) / max(1, x2 - x1)
    flags = frac >= ink_frac
    runs, start = [], None
    for i, v in enumerate(flags):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append([start + y1, i + y1])
            start = None
    if start is not None:
        runs.append([start + y1, len(flags) + y1])
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] < min_gap:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def ocr_atoms(img_path: Path, region, scale: float = 2.0):
    """把裁剪区放大后再 OCR —— 答案页字高只有 10–14px，原尺寸 OCR 全漏（2026-10-27 实测 0 锚点）。"""
    from rapidocr_onnxruntime import RapidOCR
    img = cv2.imread(str(img_path))
    x1, y1, x2, y2 = region
    crop = img[y1:y2, x1:x2]
    if scale and scale != 1.0:
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    res, _ = RapidOCR()(crop)
    out = []
    for item in res or []:
        box, text = item[0], str(item[1])
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        out.append({"text": text,
                    "x1": int(min(xs) / scale) + x1, "x2": int(max(xs) / scale) + x1,
                    "y1": int(min(ys) / scale) + y1, "y2": int(max(ys) / scale) + y1})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--x1", type=int, required=True)
    ap.add_argument("--x2", type=int, required=True)
    ap.add_argument("--y1", type=int, required=True)
    ap.add_argument("--y2", type=int, required=True)
    ap.add_argument("--nums", default="1-14", help="期望题号范围，如 1-14")
    ap.add_argument("--out", default=None)
    ap.add_argument("--pad-x", type=int, default=6, help="框左右留白（源 px）")
    ap.add_argument("--pad-y", type=int, default=6)
    ap.add_argument("--scale", type=float, default=2.0,
                    help="OCR 前放大倍数（答案页字高仅 10-14px，1.0 会全漏）")
    args = ap.parse_args()

    m = re.match(r"(\d+)-(\d+)$", args.nums)
    if not m:
        raise SystemExit("--nums 格式应为 a-b")
    lo, hi = int(m.group(1)), int(m.group(2))
    expect = list(range(lo, hi + 1))

    img_path = Path(args.image)
    bgr = cv2.imread(str(img_path))
    if bgr is None:
        raise SystemExit(f"读不到图片: {img_path}")
    mask = ink_mask(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
    region = (args.x1, args.y1, args.x2, args.y2)

    rows = rows_in(mask, args.x1, args.x2, args.y1, args.y2)
    print(f"[行] {len(rows)} 行段: {rows}")
    atoms = ocr_atoms(img_path, region, args.scale)
    anchors = anchors_from_atoms(atoms)
    # 只保留期望范围内的题号（页面上还有别的题号，如相邻课时）
    anchors = [a for a in anchors if lo <= a["num"] <= hi]
    # 同一题号可能出现多次（正文里的 "3." 之类）→ 取最靠上、最可靠的一个
    dedup: dict[int, dict] = {}
    for a in sorted(anchors, key=lambda a: (a["y"], not a["reliable"], a["x"])):
        dedup.setdefault(a["num"], a)
    anchors = sorted(dedup.values(), key=lambda a: (a["y"], a["x"]))
    print(f"[锚点] {len(anchors)} 个: "
          + ", ".join(f"{a['num']}@{a['x']}{'' if a['reliable'] else '*'}" for a in anchors))

    # 每行分配锚点：用"最近行"而不是区间命中（放大后的坐标有 ±几 px 抖动，
    # 区间判定会把锚点丢到相邻行，2026-10-27 实测造成 Q5/Q6 互换）
    boxes = []   # {num, bbox}
    by_num: dict[int, dict] = {}
    row_of = {}  # anchor id → row index
    for ai, a in enumerate(anchors):
        best = min(range(len(rows)),
                   key=lambda ri: min(abs(a["y"] - rows[ri][0]), abs(a["y"] - rows[ri][1])))
        row_of[ai] = best
    for ridx, (ry1, ry2) in enumerate(rows):
        row_anchors = [(ai, anchors[ai]) for ai in row_of if row_of[ai] == ridx]
        row_anchors.sort(key=lambda t: t[1]["x"])
        if not row_anchors:
            # 续行：并入上一题（上一行里最后一个锚点的题号）
            prev_rows = [ri for ri in range(ridx) if any(row_of[ai] == ri for ai in row_of)]
            if prev_rows:
                last_row = max(prev_rows)
                prev_anchors = sorted([anchors[ai] for ai in row_of if row_of[ai] == last_row],
                                      key=lambda a: a["x"])
                if prev_anchors:
                    num = prev_anchors[-1]["num"]
                    if num in by_num:
                        by_num[num][-1][3] = max(by_num[num][-1][3], ry2 + args.pad_y)
                        by_num[num][-1][2] = max(by_num[num][-1][2], args.x2 - 2)
            continue
        for i, (ai, a) in enumerate(row_anchors):
            right = row_anchors[i + 1][1]["x"] - 3 if i + 1 < len(row_anchors) else args.x2
            left = max(args.x1, a["x"] - args.pad_x)
            by_num.setdefault(a["num"], []).append(
                [left, ry1 - args.pad_y, right, ry2 + args.pad_y])

    # 合并同一题的多段（续行可能被行投影切碎）
    for num, segs in by_num.items():
        segs.sort(key=lambda s: s[1])
        merged = [segs[0]]
        for s in segs[1:]:
            if s[1] - merged[-1][3] < 8:      # 竖直相邻 → 合并
                merged[-1][2] = max(merged[-1][2], s[2])
                merged[-1][3] = max(merged[-1][3], s[3])
            else:
                merged.append(s)
        by_num[num] = merged

    missing = [n for n in expect if n not in by_num]
    extra = [n for n in by_num if n not in expect]
    print(f"[结果] 命中 {len(by_num)} 题；缺 {missing}；超出范围 {extra}")
    for n in sorted(by_num):
        for j, b in enumerate(by_num[n]):
            print(f"   Q{n:>2}{'' if j == 0 else f'#{j+1}'}  bbox={b}")

    out = Path(args.out) if args.out else OUT_DIR / f"{img_path.stem}_ans.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    flat = [{"num": n, "bbox": b, "seg": j} for n in sorted(by_num) for j, b in enumerate(by_num[n])]
    out.write_text(json.dumps({"region": region, "expect": expect,
                               "missing": missing, "boxes": flat},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[out] {out}")

    # contact sheet 用的候选框
    cs = out.with_name(out.stem + ".contact.json")
    cs.write_text(json.dumps([{"bbox": f["bbox"], "role": "answer", "id": f"A{f['num']}"}
                              for f in flat], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[contact] {cs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
