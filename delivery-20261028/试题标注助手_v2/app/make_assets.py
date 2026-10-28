#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
app/make_assets.py — 第 3 步：给一页生成「行号叠加图」+ 空白 spec 模板

用法（由 3_出图.bat 调用）：
    python make_assets.py 35 36
输出：
    报告/p35_rows.png       行号叠加图（人眼确认哪些行属于哪题）
    specs/p35_qspec.json    空白模板（把行号填进 stem/opt 即可）
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
    # 支持 "35" / "35,36" / "35-37" 三种写法
    spec_arg = " ".join(sys.argv[1:])
    pages = []
    for part in spec_arg.replace("，", ",").split(","):
        part = part.strip().replace(" ", "")
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")[:2]
            pages.extend(range(int(a), int(b) + 1))
        elif part.isdigit():
            pages.append(int(part))
    if not pages:
        print("用法：python make_assets.py <页码，如 35 / 35,36 / 35-37>")
        return 2

    for page in pages:
        print(f"\n===== 第 {page} 页 =====")
        try:
            img = L.download(page)
            print(f"源图: {img}  ({img.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f"[失败] 下载源图失败：{e}")
            continue

        spec = L.base_spec(img)
        png = L.OUT_DIR / f"p{page}_rows.png"
        try:
            n = L.draw_rowmap(spec, png)
        except Exception as e:
            print(f"[失败] 行分割失败：{e}")
            continue
        print(f"行数: {n}  行号图: {png}")

        # 空白模板：把行号图里看到的分组填进 items
        tpl = dict(spec)
        tpl["items"] = [{"n": 1, "stem": ["L00-L01"], "opt": []}]
        tpl_path = L.SPEC_DIR / f"p{page}_qspec.json"
        L.SPEC_DIR.mkdir(parents=True, exist_ok=True)
        tpl_path.write_text(json.dumps(tpl, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"模板: {tpl_path}  ← 照着行号图把 L/R 行号填进去")
    print("\n下一步：打开 报告\\pNN_rows.png 看行号，然后编辑 specs\\pNN_qspec.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
