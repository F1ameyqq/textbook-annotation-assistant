#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
app/make_submit_runner.py — 生成提交用的包装脚本（客户不直接调用）

A 侧的 pageRun.mjs 没有 CLI，靠一个包装 mjs 调用 main(coordFile, opts)。
run_ego.ps1 只能跑一个 js 文件、参数走环境变量，所以这里把参数**写死**进包装脚本，
最简单也最不容易出错。

用法：
    python make_submit_runner.py pages\\p35.json --dry
    python make_submit_runner.py pages\\p35.json --commit --from 11 --to 17
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent
ROOT = APP.parent

# 控制台编码交给调用方（bat 里设 PYTHONIOENCODING=gbk），避免中文乱码
if hasattr(sys.stdout, "reconfigure") and not __import__("os").environ.get("PYTHONIOENCODING"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        print("用法：python make_submit_runner.py <页面json> [--dry|--commit] [--from N] [--to M]")
        return 2

    coord = Path(argv[0])
    if not coord.is_absolute():
        coord = (ROOT / coord).resolve()
    if not coord.exists():
        print(f"[失败] 找不到页面文件：{coord}")
        return 2

    opts: dict = {"dry": "--dry" in argv or "--commit" not in argv}
    for i, a in enumerate(argv):
        if a in ("--from", "--to") and i + 1 < len(argv):
            opts[a[2:]] = int(argv[i + 1])

    # ego 的 cmd 包装按 ANSI 写文件，非 ASCII 路径会让它找不到 _run.mjs（实测）
    bad = [part for part in str(ROOT).split("\\") if any(ord(ch) > 127 for ch in part)]
    if bad and not "--dry" in argv:
        print(f"[中止] 安装路径含非 ASCII 字符：{bad}")
        print("       ego 的启动包装不支持中文路径，请把整个文件夹移到 C:/anno-helper 这类纯英文路径后重试。")
        print("       （DRY RUN 不受影响，可以照常跑）")
        return 4

    data = json.loads(coord.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        print(f"页面：{coord.name}  题数 {len(data.get('items', []))}  "
              f"qPage={data.get('qPage')} aPage={data.get('aPage')} lesson={data.get('lesson')}")
        if not data.get("lesson") and not opts["dry"]:
            print("[中止] 页面文件里没有 lesson 字段 —— 真提交时 restore 会找不到课时。")
            print("       请在 json 里补 \"lesson\": \"第N课时 xxx\"")
            return 3

    js = f'''import {{ main }} from "./pageRun.mjs";
const res = await main({json.dumps(str(coord).replace(chr(92), "/"))},
  {json.dumps(opts, ensure_ascii=False)});
console.log(JSON.stringify(res));
'''
    out = APP / "_submit_run.mjs"
    out.write_text(js, encoding="utf-8")
    mode = "DRY RUN（只演练，不写库）" if opts["dry"] else "真提交（不可逆）"
    print(f"已生成 {out.name}  模式={mode}  范围={opts.get('from','全部')}..{opts.get('to','全部')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
