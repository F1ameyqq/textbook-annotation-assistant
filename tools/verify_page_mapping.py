#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/verify_page_mapping.py — 用两条独立证据复核 "page_index N -> page_{N-1}" 映射

证据 A（跨模态相关）：拿平台自己生成的裁剪图（annotate_images）与候选页的对应区域
    做归一化互相关(NCC)。裁剪图是平台按 rect_bbox 从**源图**上真实裁下来的，
    因此它在哪张页图上能对应上，就直接证明该页是源图。

证据 B（尺度关系）：比较 rect_bbox 宽高与裁剪图实际宽高。若两者接近 1:1，
    说明记录坐标就是源图像素坐标，不需要任何缩放。

不依赖任何模型；NCC 用 numpy 手算，避免 cv2 版本差异。

用法:
  python tools/verify_page_mapping.py [--annimg DIR] [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

DEFAULT_ANNIMG = os.path.join(ROOT, "data", "derived", "analysis", "coord_evidence", "annimg")
IMAGES = os.path.join(ROOT, "data", "raw", "images")
ANN = os.path.join(ROOT, "data", "raw", "annotations", "annotations_unified_snapshot.json")


def load_gray(path: str) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L")).astype(np.float32)


def ncc(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    den = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float((a * b).sum() / den) if den > 0 else 0.0


def best_ncc(search: np.ndarray, tmpl: np.ndarray, cx: float, cy: float,
             win: int = 6, step: int = 2) -> float:
    """在 (cx,cy) 附近搜索模板的最佳 NCC。"""
    H, W = search.shape
    th, tw = tmpl.shape
    best = -1.0
    for dy in range(-win, win + 1, step):
        for dx in range(-win, win + 1, step):
            x = int(round(cx)) + dx
            y = int(round(cy)) + dy
            if x < 0 or y < 0 or x + tw > W or y + th > H:
                continue
            s = ncc(search[y:y + th, x:x + tw], tmpl)
            if s > best:
                best = s
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--annimg", default=DEFAULT_ANNIMG)
    ap.add_argument("--json", default=os.path.join(ROOT, "data", "derived", "analysis",
                                                   "page_mapping_verification.json"))
    args = ap.parse_args()

    with open(ANN, encoding="utf-8") as fh:
        ann = json.load(fh)
    if not os.path.isdir(args.annimg):
        print(f"缺少裁剪图目录 {args.annimg}，无法验证。")
        return 2

    rows: list[dict] = []
    for r in ann:
        fn = os.path.basename(r["image_path"])
        cp = os.path.join(args.annimg, fn)
        if not os.path.exists(cp):
            continue
        crop = load_gray(cp)
        # 关键：裁剪图尺寸 == round(bbox 宽高)，**没有额外边框**，不要 trim。
        # （早期版本假设有 1px 边框并去掉，导致对齐整体偏移、NCC 从 0.99 掉到 0.60。）
        tmpl = crop
        ch, cw = tmpl.shape
        tiny = min(ch, cw) < 24
        x1, y1, x2, y2 = (float(v) for v in r["rect_bbox"].split(","))
        bw, bh = x2 - x1, y2 - y1
        N = int(r["page_index"])
        rec = {
            "type": r["type"], "page_index": N, "order_in_level": r["order_in_level"],
            "crop_wh": [cw, ch], "bbox_wh": [round(bw, 2), round(bh, 2)],
            "size_delta": [round(cw - bw, 2), round(ch - bh, 2)],
            "tiny_box": tiny, "scores": {},
        }
        for tgt in (N, N - 1):
            ip = os.path.join(IMAGES, f"46006966_page_{tgt}.jpg")
            if not os.path.exists(ip):
                continue
            g = load_gray(ip)
            rec["scores"][f"page_{tgt}"] = round(best_ncc(g, tmpl, x1, y1), 4)
        if len(rec["scores"]) == 2:
            k_n, k_n1 = f"page_{N}", f"page_{N-1}"
            rec["winner"] = k_n1 if rec["scores"][k_n1] > rec["scores"][k_n] else k_n
            rows.append(rec)

    decisive = [r for r in rows if not r["tiny_box"]]
    win_n1 = sum(1 for r in decisive if r["winner"].endswith(str(r["page_index"] - 1)))
    print(f"参与判定 {len(rows)} 个框，其中有判别力的（非极小框）{len(decisive)} 个")
    print(f"  非极小框中，page_{{N-1}} 胜出: {win_n1}/{len(decisive)}")
    print()
    print("判定阈值：NCC >= 0.5 视为真实匹配（相关是逐像素比对，真匹配通常 >0.9）")
    print()
    print(f"{'type':<9}{'pg':>5}{'ord':>4}{'NCC(N)':>10}{'NCC(N-1)':>11}  胜出")
    for r in sorted(rows, key=lambda x: (x["page_index"], x["type"])):
        a = r["scores"].get(f"page_{r['page_index']}", float("nan"))
        b = r["scores"].get(f"page_{r['page_index']-1}", float("nan"))
        mark = "  (极小框)" if r["tiny_box"] else ""
        print(f"{r['type']:<9}{r['page_index']:>5}{r['order_in_level']:>4}"
              f"{a:>10.3f}{b:>11.3f}  {r['winner']:<8}{mark}")

    strong_n1 = sum(1 for r in decisive
                    if r["scores"].get(f"page_{r['page_index']-1}", 0) >= 0.5)
    strong_n = sum(1 for r in decisive
                   if r["scores"].get(f"page_{r['page_index']}", 0) >= 0.5)
    verdict = (f"支持 page_index N -> page_{{N-1}}"
               if strong_n1 > strong_n else "证据不足")
    print()
    print(f"NCC>=0.5 的框数：page_{{N-1}} = {strong_n1}，page_N = {strong_n}  -> {verdict}")

    out = {
        "verdict": verdict,
        "n_boxes": len(rows), "n_decisive": len(decisive),
        "n_strong_match_page_N_minus_1": strong_n1,
        "n_strong_match_page_N": strong_n,
        "criterion": ("裁剪图(平台按 rect_bbox 从源图裁得，无边框) 与 page_N / page_{N-1} "
                      "在 bbox 原点的逐像素归一化互相关；真匹配通常 >0.9"),
        "boxes": rows,
    }
    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print("写出:", os.path.relpath(args.json, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
