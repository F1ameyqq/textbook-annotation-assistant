#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/page_mapping.py — 标注 page_index 与 OSS 页图的**权威映射**

结论（已用两条独立证据复核，见 tools/verify_page_mapping.py）：
    标注记录里的 `page_index = N`  →  OSS 文件 `{file_id}_page_{N-1}.jpg`

即：
    page_index 8   -> 46006966_page_7.jpg
    page_index 9   -> 46006966_page_8.jpg
    page_index 10  -> 46006966_page_9.jpg
    page_index 234 -> 46006966_page_233.jpg

为什么容易搞错：
    OSS 资源索引是 0 基的，而标注记录的 page_index 以 1 为起点（或存在历史偏移）。
    两个编号只差 1，用错不会抛异常——只会让所有坐标"看起来有点错但又不完全错"，
    从而被误判成"缩放/平移问题"。这是本项目踩过的最贵的一个坑。

坐标系差异（重要，别和 off-by-one 混为一谈）：
    * 页 8/9/10 的框：与 page_7/8/9.jpg 是**同一坐标空间**，尺度 1:1，
      可以把 rect_bbox 当像素真值直接用。
    * 页 234 的框：内容能在 page_233.jpg 上匹配到（NCC≈0.85），但框只用到
      x 0–594、y 254–1164，说明它记录在一个**窄画布（约 594×≤1165）**上，
      而不是 3467×1615 的拼合图。该页坐标**不可直接复用**，需单独标定。
"""
from __future__ import annotations

# 页 8/9/10 的框与对应页图同坐标空间、1:1，可作评测真值
COORD_SPACE_OK = {8, 9, 10}
# 页 234 的框坐标系未定，不可直接作真值
COORD_SPACE_UNDETERMINED = {234}


def oss_page_index(page_index: int) -> int:
    """标注 page_index -> OSS 页图索引。"""
    return page_index - 1


def image_name(file_id: str | int, page_index: int) -> str:
    """标注 page_index -> OSS 文件名。"""
    return f"{file_id}_page_{oss_page_index(page_index)}.jpg"


def is_coord_space_usable(page_index: int) -> bool:
    """该页的 rect_bbox 能否直接当像素坐标真值使用。"""
    return page_index in COORD_SPACE_OK


def describe() -> str:
    lines = [
        "标注 page_index -> OSS 页图（权威映射）",
        "  page_index N  ->  {file_id}_page_{N-1}.jpg",
        "",
        "可直接用坐标的页: " + ", ".join(str(p) for p in sorted(COORD_SPACE_OK)),
        "坐标系未定的页  : " + ", ".join(str(p) for p in sorted(COORD_SPACE_UNDETERMINED)),
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(describe())
