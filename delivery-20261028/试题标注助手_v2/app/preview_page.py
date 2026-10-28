#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
app/preview_page.py — 第 4 步：按 spec 出「框位验收图」

用法（由 4_预览.bat 调用）：
    python preview_page.py p35_qspec        # 省略 .json 也行
输出：
    报告/p35_overlay.png   题干框(红) + 选项框(绿)，用于人眼验收
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pack_lib as L

# 控制台编码交给调用方（bat 里设 PYTHONIOENCODING=gbk），避免中文乱码
if hasattr(sys.stdout, "reconfigure") and not __import__("os").environ.get("PYTHONIOENCODING"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：python preview_page.py <spec 名，如 p35_qspec>")
        return 2
    name = sys.argv[1]
    spec_path = L.SPEC_DIR / (name if name.endswith(".json") else name + ".json")
    if not spec_path.exists():
        print(f"[失败] 找不到 spec：{spec_path}")
        return 2

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    out_json = spec_path.with_name(spec_path.stem.replace("_qspec", "") + "_out.json")
    out = L.run_measure(spec_path, out_json)
    print(out.strip()[-800:])

    if not out_json.exists():
        print("[失败] 没有生成坐标文件")
        return 3
    data = json.loads(out_json.read_text(encoding="utf-8"))
    png = L.OUT_DIR / (spec_path.stem.replace("_qspec", "") + "_overlay.png")
    nq, nw = L.draw_overlay(data, Path(spec["src"]), png)
    print(f"\n题干框 {nq} 个，选项框 {nw} 个")
    print(f"验收图：{png}")
    print("请在图上确认：每个红框圈住一道完整题干、每个绿框圈住一个选项、没有框到隔壁题。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
