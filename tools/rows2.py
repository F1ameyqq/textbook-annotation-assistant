#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/rows2.py — proj.py 的加强版：可调 y 窗口 / min_gap / 墨迹比例

proj.py 回答"行段在哪"；rows2 回答"在页面边缘暗带/噪点干扰下，行边界
还稳不稳"。区别：

1. --ink-frac：一行算"有墨"的门槛从绝对像素数（proj 的 --max-ink）
   改成**墨迹比例**（墨像素 / 扫描宽度）。页边暗带是"满宽浅灰"，
   按灰度阈值它本来就不是墨；真正要防的是扫描噪点——几个离散噪点
   占不满 ink-frac，就不会把空白行误判成文本行。
2. --dump：打印每一行的墨比例曲线，人肉找阈值/窗口用。
3. 滑窗模式（--win > 0）：以 win 行为窗口计算滑动墨比例，
   对"行内有大片留白（插图、公式）导致单行墨比例偏低"的边界判断更稳。

用法
----
    python -I tools/rows2.py page.png --mode lines --x1 44 --x2 244 \
        --y1 60 --y2 640 --S 3 --ink-frac 0.01 --min-gap 4

    # 看比例曲线（不定阈值，先观察）：
    python -I tools/rows2.py page.png --mode lines --x1 44 --x2 244 \
        --y1 60 --y2 640 --S 3 --dump

所有坐标参数与输出均为源图像素；--S 为截图倍率（同 proj.py）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台默认 GBK，强制 UTF-8 防乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout_probe import ink_mask  # noqa: E402
from proj import _merge_gap, _runs  # noqa: E402


def frac_curve(mask: np.ndarray, mode: str, lo1: int, hi1: int,
               lo2: int, hi2: int) -> np.ndarray:
    """每行/列的墨迹比例（0..1）。"""
    if mode == "lines":
        sub = mask[lo2:hi2, lo1:hi1]
        return sub.sum(axis=1) / max(1, (hi1 - lo1))
    sub = mask[lo1:hi1, lo2:hi2]
    return sub.sum(axis=0) / max(1, (hi1 - lo1))


def sliding(frac: np.ndarray, win: int) -> np.ndarray:
    """滑动平均（边界取短窗），win<=1 时原样返回。"""
    if win <= 1:
        return frac
    k = np.ones(win) / win
    return np.convolve(frac, k, mode="same")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="墨迹投影加强版（rows2）")
    ap.add_argument("image")
    ap.add_argument("--mode", choices=["lines", "cols"], default="lines")
    ap.add_argument("--S", type=float, default=1.0, help="截图倍率（默认 1）")
    ap.add_argument("--x1", type=float, required=True)
    ap.add_argument("--x2", type=float, required=True)
    ap.add_argument("--y1", type=float, required=True)
    ap.add_argument("--y2", type=float, required=True)
    ap.add_argument("--thresh", type=int, default=165, help="墨迹灰度阈值")
    ap.add_argument("--ink-frac", type=float, default=0.01,
                    help="行/列算「有墨」的比例门槛（默认 0.01）")
    ap.add_argument("--min-gap", type=int, default=4, help="段合并间隙（源 px）")
    ap.add_argument("--min-len", type=int, default=3, help="输出段最小长度（源 px）")
    ap.add_argument("--win", type=int, default=1, help="滑窗行数（>1 启用滑动平均）")
    ap.add_argument("--dump", action="store_true", help="打印比例曲线")
    ap.add_argument("--label", default="R2")
    args = ap.parse_args(argv)

    mask = ink_mask(Image.open(args.image), thresh=args.thresh)
    H, W = mask.shape
    s = args.S
    if args.mode == "lines":
        lo1, hi1 = int(args.x1 * s), int(args.x2 * s)
        lo2, hi2 = int(args.y1 * s), int(args.y2 * s)
        lo1, hi1 = max(0, lo1), min(W, hi1)
        lo2, hi2 = max(0, lo2), min(H, hi2)
    else:
        lo1, hi1 = int(args.y1 * s), int(args.y2 * s)
        lo2, hi2 = int(args.x1 * s), int(args.x2 * s)
        lo1, hi1 = max(0, lo1), min(H, hi1)
        lo2, hi2 = max(0, lo2), min(W, hi2)

    frac = frac_curve(mask, args.mode, lo1, hi1, lo2, hi2)
    frac = sliding(frac, args.win)
    flags = frac >= args.ink_frac
    offs = np.arange(lo2, hi2)

    if args.dump:
        axis = "y" if args.mode == "lines" else "x"
        for i, f in enumerate(frac):
            pos = int(offs[i] / s)
            bar = "#" * int(f * 200)
            print(f"{pos:>6}  {f:6.3f}  {bar}")

    unit = "y" if args.mode == "lines" else "x"
    for st, en in _merge_gap(_runs(flags), args.min_gap):
        st_s, en_s = int(offs[st] / s), int(offs[en - 1] / s) + 1
        if en_s - st_s >= args.min_len:
            print(f"{args.label}\t{unit}\t{st_s}-{en_s}\th={en_s - st_s}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
