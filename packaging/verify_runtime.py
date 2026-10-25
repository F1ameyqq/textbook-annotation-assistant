#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
packaging/verify_runtime.py — 运行端自检：绑定 / 依赖 / 工作区 / 入口

用法:
  python packaging/verify_runtime.py --app .
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", type=Path, required=True)
    ap.add_argument("--workspace", type=Path, default=None)
    args = ap.parse_args()

    app = args.app.resolve()
    sys.path.insert(0, str(app / "src"))
    ok = True

    print("=" * 66)
    print(f"运行端自检   app={app}")
    print("=" * 66)

    path_file = app / "runtime" / "customer-python.path"
    if path_file.is_file():
        exe = Path(path_file.read_text(encoding="utf-8").strip())
        print(f"1) 启动解释器  : {exe}")
        print(f"   存在        : {exe.is_file()}")
        ok &= exe.is_file()
    else:
        print("1) 启动解释器  : 缺少 runtime/customer-python.path")
        ok = False

    cfg_path = app / "runtime" / "customer-runtimes.json"
    if cfg_path.is_file():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        print(f"2) 绑定 scope  : {cfg.get('scope')}")
        for k in ("text_python", "formula_python"):
            it = cfg.get(k) or {}
            p = Path(it.get("path", "")) if it.get("path") else None
            print(f"   {k:<14}: 存在={bool(p and p.is_file())}")
            ok &= bool(p and p.is_file())
        print(f"   formula_ready: {cfg.get('formula_inference_activated')}")
    else:
        print("2) 绑定        : 缺少 runtime/customer-runtimes.json")
        ok = False

    print("3) 依赖:")
    for mod in ("numpy", "cv2", "PIL", "onnxruntime"):
        try:
            m = __import__(mod)
            print(f"   OK   {mod:<14} {getattr(m, '__version__', '?')}")
        except Exception:  # noqa: BLE001
            print(f"   MISS {mod}")
            ok = False
    try:
        import rapid_latex_ocr  # noqa: F401
        print("   OK   rapid_latex_ocr（公式后端）")
    except Exception:  # noqa: BLE001
        print("   MISS rapid_latex_ocr（公式推理不可用，非阻塞）")

    print("4) 入口模块:")
    try:
        from annotation.customer.store import Store  # noqa: F401
        from annotation.customer.prepare import prepare  # noqa: F401
        from annotation.customer.review import CustomerReviewWorkspace  # noqa: F401
        from annotation.customer.production import produce  # noqa: F401
        print("   store / prepare / review / production 可导入")
    except Exception as exc:  # noqa: BLE001
        print(f"   导入失败: {type(exc).__name__}: {exc}")
        ok = False

    if args.workspace:
        db = args.workspace / "state.sqlite"
        print(f"5) 工作区      : {args.workspace}")
        print(f"   state.sqlite: 存在={db.is_file()}")
        if db.is_file():
            con = sqlite3.connect("file:" + str(db).replace("\\", "/") + "?mode=ro", uri=True)
            tables = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")]
            print(f"   表          : {tables}")
            for t in tables:
                try:
                    print(f"     {t:<12} "
                          f"{con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]} 行")
                except Exception:  # noqa: BLE001
                    pass
            con.close()

    print()
    print("结论：", "可启动" if ok else "存在阻塞项")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
