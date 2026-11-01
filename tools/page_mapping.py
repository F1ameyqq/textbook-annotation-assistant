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

适用范围：仅样书 46006966 的已验证页 8/9/10/234。其他书和页须由来源适配器提供证据。
    页 234 正确对应 page_233.jpg；局部框只占宽图一部分，不说明坐标需缩放。
    四页均有原图尺度 1:1 的几何对齐证据；历史框仍未核准为业务真值。
"""
from __future__ import annotations

VERIFIED_BOOK_ID = "46006966"
COORD_SPACE_OK = {8, 9, 10, 234}
COORD_SPACE_UNDETERMINED: set[int] = set()


def oss_page_index(page_index: int, file_id: str | int = VERIFIED_BOOK_ID) -> int:
    """已验证样书页映射；不向其他书或未验证页推广。"""
    if str(file_id) != VERIFIED_BOOK_ID or type(page_index) is not int or page_index not in COORD_SPACE_OK:
        raise ValueError("page mapping has not been verified for this book/page")
    return page_index - 1


def image_name(file_id: str | int, page_index: int) -> str:
    """标注 page_index -> OSS 文件名。"""
    return f"{file_id}_page_{oss_page_index(page_index, file_id)}.jpg"


def is_coord_space_usable(page_index: int, file_id: str | int = VERIFIED_BOOK_ID) -> bool:
    """仅表示几何对齐已验证，不表示内容/角色/题答关系正确。"""
    return str(file_id) == VERIFIED_BOOK_ID and type(page_index) is int and page_index in COORD_SPACE_OK


def describe() -> str:
    lines = [
        "样书 46006966 已验证页：标注 page_index -> OSS 页图",
        "  page_index N  ->  {file_id}_page_{N-1}.jpg",
        "",
        "可直接用坐标的页: " + ", ".join(str(p) for p in sorted(COORD_SPACE_OK)),
        "坐标系未定的页  : " + ", ".join(str(p) for p in sorted(COORD_SPACE_UNDETERMINED)),
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(describe())
