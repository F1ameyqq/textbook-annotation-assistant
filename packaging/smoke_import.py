#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
packaging/smoke_import.py — 逐模块导入检查（验证 Python 版本兼容性）

A 原文档要求 Python 3.12；实测 3.11 全部兼容。
本脚本用于在新机器上确认没有版本/依赖导致的导入失败。

用法:
  python packaging/smoke_import.py --app .
"""
from __future__ import annotations

import argparse
import importlib
import pkgutil
import sys
from pathlib import Path

PACKAGES = ("annotation.customer", "annotation.recognition",
            "annotation.runtime", "annotation.prebox")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", type=Path, required=True)
    args = ap.parse_args()

    app = args.app.resolve()
    sys.path.insert(0, str(app / "src"))

    print(f"Python: {sys.version.split()[0]}")
    print(f"app   : {app}\n")

    ok, bad = 0, []
    for pkg_name in PACKAGES:
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception as exc:  # noqa: BLE001
            bad.append((pkg_name, f"{type(exc).__name__}: {exc}"))
            print(f"--- {pkg_name}: 包导入失败 {type(exc).__name__}: {exc}")
            continue
        mods = [m.name for m in pkgutil.walk_packages(
            pkg.__path__, prefix=pkg.__name__ + ".")]
        fail_here = 0
        for name in mods:
            saved = sys.argv
            sys.argv = [name]
            try:
                importlib.import_module(name)
                ok += 1
            except SystemExit:
                # 导入期解析 argv（__main__ 类），不算兼容性失败
                pass
            except Exception as exc:  # noqa: BLE001
                bad.append((name, f"{type(exc).__name__}: {exc}"))
                fail_here += 1
                print(f"  FAIL {name}: {type(exc).__name__}: {str(exc)[:110]}")
            finally:
                sys.argv = saved
        print(f"--- {pkg_name}: {len(mods)} 个子模块，失败 {fail_here}")

    print(f"\n导入成功 {ok} 个，失败 {len(bad)} 个")
    if bad:
        print("\n失败清单：")
        for n, e in bad[:20]:
            print(f"  {n}\n      {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
