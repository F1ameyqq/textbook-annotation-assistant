#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/measure_page_adapt.py — A 侧 measure_page.py 的适配版（canvas 参数化）

A 原版（F1ameyqq/getaway-to-goal）把 ego 窗口的 canvas 尺寸写死：
  kind=q → (519.78, 669.1)；kind=a → (436.7, 669.0)；SRC 也写死。
本机用 playwright + OSS 原图，canvas 是 (592, 781) / (462, 781)，
所以这两处必须参数化，否则行号与坐标全错位。

用法：
    python -I tools/measure_page_adapt.py spec.json --dump-rows               # 打印行表
    python -I tools/measure_page_adapt.py spec.json out.json                  # 生成源坐标
    python -I tools/measure_page_adapt.py spec.json --dump-rows --canvas 592,781

约定：spec 里可加 "canvas": [w, h] 覆盖默认；SRC 一律读图片真实尺寸。
"""
import io
import json
import sys

import numpy as np
from PIL import Image

args = list(sys.argv[1:])
flags = [a for a in args if a.startswith("--")]
plain = [a for a in args if not a.startswith("--")]
if not plain:
    print(__doc__)
    sys.exit(2)
spec_path = plain[0]
out_path = plain[1] if len(plain) > 1 else None

DUMP_ROWS = "--dump-rows" in flags
CANVAS_OVERRIDE = None
if "--canvas" in flags:
    CANVAS_OVERRIDE = tuple(float(v) for v in args[args.index("--canvas") + 1].split(","))

spec = json.load(io.open(spec_path, encoding="utf-8"))
im = Image.open(spec["src"]).convert("L")
a = np.array(im)
SRC = (float(im.width), float(im.height))

KIND = spec["kind"]
default_canvas = (592.0, 781.0) if KIND == "q" else (462.0, 781.0)
CANVAS = CANVAS_OVERRIDE or tuple(spec.get("canvas", default_canvas))

SS = im.width / CANVAS[0]                      # CSS → 图像像素
s_src = min(CANVAS[0] / SRC[0], CANVAS[1] / SRC[1])
pad_x = (CANVAS[0] - SRC[0] * s_src) / 2.0
pad_y = (CANVAS[1] - SRC[1] * s_src) / 2.0

TH = spec.get("th", 200 if KIND == "q" else 225)
MIN_INK = spec.get("min_ink", 20 if KIND == "q" else 2)
MIN_H = 2.0
GAP_CSS = spec.get("gap_css", 4.0)
Y0, Y1 = spec.get("y", [20.0, CANVAS[1] - 21.0])


def px(v):
    return int(round(v * SS))


def row_blocks(X0, X1):
    sub = a[px(Y0):px(Y1), px(X0):px(X1)]
    ink_r = (sub < TH).sum(axis=1)
    raw, cur = [], None
    for i, v in enumerate(ink_r):
        if v > MIN_INK:
            cur = [i, i] if cur is None else [cur[0], i]
        else:
            if cur is not None:
                raw.append(cur)
                cur = None
    if cur:
        raw.append(cur)
    merged = []
    for r in raw:
        if merged and r[0] - merged[-1][1] <= 4:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    rows = []
    for ra, rb in merged:
        if (rb - ra) / SS < MIN_H:
            continue
        band = sub[ra:rb + 1]
        ink_c = (band < TH).sum(axis=0)
        segs, cur2 = [], None
        for i, v in enumerate(ink_c):
            if v > 0:
                cur2 = [i, i] if cur2 is None else [cur2[0], i]
            else:
                if cur2 is not None:
                    segs.append(cur2)
                    cur2 = None
        if cur2:
            segs.append(cur2)
        blocks = []
        for s in segs:
            if blocks and s[0] - blocks[-1][1] < GAP_CSS * SS:
                blocks[-1][1] = s[1]
            else:
                blocks.append(list(s))
        blocks = [b for b in blocks
                  if not ((b[1] - b[0]) / SS < 3.0 and X0 + b[1] / SS >= X1 - 6)]
        rows.append({"y0": Y0 + ra / SS, "y1": Y0 + rb / SS,
                     "blocks": [[X0 + b[0] / SS, X0 + b[1] / SS] for b in blocks]})
    return rows


CACHE = {}


def rows(tag):
    if tag not in CACHE:
        if KIND == "q":
            X0, X1 = spec["cols"][tag]
        else:
            X0, X1 = spec["x"]
        CACHE[tag] = row_blocks(float(X0), float(X1))
    return CACHE[tag]


def span(spec_str):
    tag = spec_str[0] if KIND == "q" else ""
    sp = spec_str[1:] if KIND == "q" else spec_str
    if "-" in sp:
        a1, a2 = sp.split("-")
        a2 = a2.lstrip("LR")
    else:
        a1 = a2 = sp
    return tag, int(a1), int(a2)


def merge_box(tag, i, j):
    rs = rows(tag)[i:j + 1]
    return [min(r["blocks"][0][0] for r in rs), min(r["y0"] for r in rs),
            max(r["blocks"][-1][1] for r in rs), max(r["y1"] for r in rs)]


def raw_box(sp):
    x0, y0, x1, y1 = map(float, sp[1:].split(","))
    return [x0, y0, x1, y1]


def ans_box(sp):
    body = sp[1:]
    rowpart, br = body.split(":")
    if "-" in rowpart:
        i, j = map(int, rowpart.split("-"))
    else:
        i = j = int(rowpart)
    if "-" in br:
        b0, b1 = map(int, br.split("-"))
    else:
        b0 = b1 = int(br)
    rs = rows("")[i:j + 1]
    return [min(r["blocks"][b0][0] for r in rs), min(r["y0"] for r in rs),
            max(r["blocks"][b1][1] for r in rs), max(r["y1"] for r in rs)]


def opt_boxes(spec_str):
    tag, i, j = span(spec_str.split("x")[0])
    per_row = int(spec_str.split("x")[1]) if "x" in spec_str else 1
    out = []
    for ri in range(i, j + 1):
        r = rows(tag)[ri]
        bl = r["blocks"]
        if per_row <= 1 or len(bl) < per_row:
            out.append([bl[0][0], r["y0"], bl[-1][1], r["y1"]])
            continue
        if len(bl) == per_row:
            for b in bl:
                out.append([b[0], r["y0"], b[1], r["y1"]])
            continue
        gaps = sorted(range(len(bl) - 1),
                      key=lambda k: bl[k + 1][0] - bl[k][1], reverse=True)
        cuts = sorted(gaps[:per_row - 1])
        segs, start = [], 0
        for c in cuts:
            segs.append((start, c))
            start = c + 1
        segs.append((start, len(bl) - 1))
        for lo, hi in segs:
            out.append([bl[lo][0], r["y0"], bl[hi][1], r["y1"]])
    return out


def to_src(b):
    return [int(round((b[0] - pad_x) / s_src)), int(round((b[1] - pad_y) / s_src)),
            int(round((b[2] - pad_x) / s_src)), int(round((b[3] - pad_y) / s_src))]


if DUMP_ROWS:
    print(f"SS={SS:.4f} s_src={s_src:.6f} pad=({pad_x:.2f},{pad_y:.2f}) "
          f"SRC={SRC} CANVAS={CANVAS}")
    tags = list(spec["cols"].keys()) if KIND == "q" else [""]
    for tag in tags:
        rs = rows(tag)
        print(f"=== 栏 {tag or 'A'} 共 {len(rs)} 行 ===")
        for i, r in enumerate(rs):
            print(f"  {tag}{i:02d}  y[{r['y0']:6.1f},{r['y1']:6.1f}]  "
                  f"blocks={len(r['blocks'])}  x[{r['blocks'][0][0]:6.1f}..{r['blocks'][-1][1]:6.1f}]")
    sys.exit(0)

items = []
for it in spec["items"]:
    q_boxes = []
    for sp in it.get("stem", []):
        if sp.startswith("@"):
            q_boxes.append(raw_box(sp))
            continue
        if sp.startswith("A"):
            q_boxes.append(ans_box(sp))
            continue
        tag, i, j = span(sp)
        q_boxes.append(merge_box(tag, i, j))
    w_boxes = []
    for sp in it.get("opt", []):
        if sp.startswith("@"):
            w_boxes.append(raw_box(sp))
        else:
            w_boxes.extend(opt_boxes(sp))
    items.append({"n": it["n"], "q": [to_src(b) for b in q_boxes],
                  "w": [to_src(b) for b in w_boxes],
                  "q_css": [[round(v, 1) for v in b] for b in q_boxes]})

if out_path:
    io.open(out_path, "w", encoding="utf-8").write(json.dumps(items, ensure_ascii=False, indent=1))
print("s_src=%.6f pad=(%.2f,%.2f) items=%d" % (s_src, pad_x, pad_y, len(items)))
for it in items:
    print("  n=%-2d q=%s w=%d" % (it["n"], it["q"], len(it["w"])))
