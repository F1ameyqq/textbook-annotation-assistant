#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/layout_probe.py — 版面结构探针（只读，零模型推理）

用途：判断一张 OSS 页图到底是"单页扫描"还是"多页拼合"，并给出拼合网格。
方法：暗像素阈值 -> 行/列投影 -> 找长零墨空白沟（gutter）。

本模块不调用任何模型，只做可复现的像素统计。
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def ink_mask(img: Image.Image, thresh: int = 160) -> np.ndarray:
    """返回布尔墨迹掩码：True = 有墨。"""
    return np.asarray(img.convert("L")) < thresh


def _runs(mask1d: np.ndarray, min_len: int) -> list[tuple[int, int, int]]:
    out: list[tuple[int, int, int]] = []
    start = None
    for i, v in enumerate(mask1d):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_len:
                out.append((start, i, i - start))
            start = None
    if start is not None and len(mask1d) - start >= min_len:
        out.append((start, len(mask1d), len(mask1d) - start))
    return out


def _max_blank_run(mask1d: np.ndarray) -> int:
    """一维布尔掩码（True=墨）中最长的连续空白长度。"""
    best = cur = 0
    for v in mask1d:
        if v:
            cur = 0
        else:
            cur += 1
            if cur > best:
                best = cur
    return best


def _spanning_gutters(mask: np.ndarray, axis: int, frac: float,
                      max_ink: int) -> list[tuple[int, int, int]]:
    """薄封装：返回贯穿式空白带的 (start, end, width) 列表。"""
    return _runs(_spanning_flags(mask, axis, frac, max_ink), 1)


def find_gutters(img: Image.Image, thresh: int = 160, min_run: int = 12,
                 max_ink: int = 2, span_frac: float = 0.7) -> dict:
    """
    找贯穿式纵向/横向空白沟，并按此切出拼合网格。

    参数（默认值已用 46006966 的 6 张页图校准）:
      thresh    : 灰度阈值，< thresh 记为墨
      min_run   : 空白沟的最小宽度（像素）。12 可滤掉"文字行间的窄空列"。
      max_ink   : 一条线允许的最大墨迹像素数（容忍噪点/页眉线）
      span_frac : 空白必须贯穿该方向总长的比例。0.7 可滤掉段落间距。

    校准结果（min_run=12, span_frac=0.7）:
      页 7/8/9/10  -> 无内部纵向沟 -> 单一页扫描
      页 233       -> 5 条内部沟 -> 横向多页拼合
      页 234       -> 3 条内部沟 -> 横向多页拼合

    已知局限（重要）:
      纵向判定可靠（页与页之间是整列空白）。
      横向判定不可靠：单页里的段落间距/短行文本同样能形成贯穿宽度的空白。
      因此横向带数量只作参考，拼合网格的行数必须人工看图确认。

    返回:
      v_gutters: [(start, end, width)]  纵向空白带（切列）
      h_gutters: [(start, end, width)]  横向空白带（切行）
      panels_v / panels_h: 内容段
    """
    ink = ink_mask(img, thresh)
    h, w = ink.shape
    v = _runs(_spanning_flags(ink, 0, span_frac, max_ink), min_run)
    hh = _runs(_spanning_flags(ink, 1, span_frac, max_ink), min_run)

    def segments(gutters, length):
        segs, pos = [], 0
        for s, e, _ in gutters:
            if s > pos:
                segs.append((pos, s))
            pos = max(pos, e)
        if pos < length:
            segs.append((pos, length))
        return [(a, b) for a, b in segs if b - a > 1]

    # 内部纵向沟 = 不在图像边缘的纵向空白带
    inner_v = [(a, b) for a, b, _ in v if a > 0 and b < w]

    return {
        "width": w, "height": h,
        "ink_ratio": float(ink.mean()),
        "span_frac": span_frac, "min_run": min_run,
        "v_gutters": v, "h_gutters": hh,
        "inner_v_gutters": inner_v,
        "panels_v": segments(v, w),
        "panels_h": segments(hh, h),
    }


def _spanning_flags(ink: np.ndarray, axis: int, frac: float, max_ink: int) -> np.ndarray:
    n_perp, n_along = (ink.shape[0], ink.shape[1]) if axis == 0 else (ink.shape[1], ink.shape[0])
    need = frac * n_perp
    flags = np.zeros(n_along, dtype=bool)
    for i in range(n_along):
        line = ink[:, i] if axis == 0 else ink[i, :]
        if line.sum() <= max_ink and _max_blank_run(line) >= need:
            flags[i] = True
    return flags


def ink_coverage(img: Image.Image, bbox, thresh: int = 160) -> tuple[float, int]:
    """bbox 落在图内的墨迹覆盖率(%) 与墨迹像素数。"""
    ink = ink_mask(img, thresh)
    h, w = ink.shape
    x1 = max(0, int(bbox[0])); y1 = max(0, int(bbox[1]))
    x2 = min(w, int(bbox[2])); y2 = min(h, int(bbox[3]))
    if x2 <= x1 or y2 <= y1:
        return 0.0, 0
    sub = ink[y1:y2, x1:x2]
    return 100.0 * float(sub.mean()), int(sub.sum())


def describe_layout(img: Image.Image, **kw) -> str:
    r = find_gutters(img, **kw)
    n_inner = len(r["inner_v_gutters"])
    verdict = f"横向多页拼合({n_inner+1}栏)" if n_inner else "单一页扫描"
    return (f"{r['width']}x{r['height']} 墨迹{r['ink_ratio']*100:.2f}% "
            f"内部纵向沟{n_inner} -> {verdict}")
