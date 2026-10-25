#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
packaging/patch_runtime.py — 把 a30 的运行时绑定指向本机 Python

问题：
  runtime/customer-runtimes.json 记录的是 A 机器上的绝对路径，
  venv 未随交接包分发，导致 START_CUSTOMER.cmd 直接退出。

做法：
  用产品自己的 byte_hash 计算本机 python.exe 摘要后写入绑定，
  让应用的 packaged_runtime() 校验自然通过（不是绕过校验）。

用法:
  python packaging/patch_runtime.py --app . --python C:\\Path\\To\\python.exe
  python packaging/patch_runtime.py --app .            # 用当前解释器
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", type=Path, required=True, help="a30 产品根目录（含 src/ tools/ runtime/）")
    ap.add_argument("--python", type=Path, default=None, help="要绑定的 python.exe；默认当前解释器")
    ap.add_argument("--formula-python", type=Path, default=None,
                    help="公式环境 python.exe；默认同 text_python")
    args = ap.parse_args()

    app = args.app.resolve()
    src = app / "src"
    if not (src / "annotation" / "customer" / "store.py").is_file():
        print(f"错误：{app} 看起来不是 a30 产品根目录（缺 src/annotation/customer/store.py）")
        return 2
    sys.path.insert(0, str(src))

    py_exe = (args.python or Path(sys.executable)).resolve()
    f_exe = (args.formula_python or py_exe).resolve()
    for p in (py_exe, f_exe):
        if not p.is_file():
            print(f"错误：找不到 python.exe: {p}")
            return 2

    from annotation.customer.store import byte_hash  # noqa: E402

    def entry(p: Path) -> dict:
        return {"path": str(p), "sha256": byte_hash(p.read_bytes())}

    runtime_dir = app / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    (runtime_dir / "customer-python.path").write_text(str(py_exe), encoding="utf-8")

    cfg_path = runtime_dir / "customer-runtimes.json"
    old = {}
    if cfg_path.is_file():
        try:
            old = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            old = {}

    # 公式后端是否可用：能 import rapid_latex_ocr 才算可用
    formula_ok = False
    try:
        if f_exe == Path(sys.executable).resolve():
            import importlib
            importlib.import_module("rapid_latex_ocr")
            formula_ok = True
        else:
            formula_ok = False  # 另一个解释器无法在本进程内验证
    except Exception:  # noqa: BLE001
        formula_ok = False

    cfg = {
        "schema": "CustomerPreparedRuntimes/v1",
        "scope": "CURRENT_MACHINE_ONLY",
        "text_python": entry(py_exe),
        "formula_python": entry(f_exe),
        "formula_models": old.get("formula_models", {}),
        "formula_inference": "CANDIDATE_EXPLICIT_GUI_ACTION_ONLY_NOT_EXECUTED",
        "portable_new_machine": "NOT_VALIDATED",
        "formula_inference_activated": formula_ok,
        "note": "由 packaging/patch_runtime.py 生成；公式后端未安装时 formula_inference_activated=false",
    }
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"text_python    : {py_exe}")
    print(f"formula_python : {f_exe}")
    print(f"formula_ready  : {formula_ok}")
    print(f"已写 {cfg_path}")
    print(f"已写 {runtime_dir / 'customer-python.path'}")

    # 用产品自己的校验函数验证
    import importlib.util
    spec = importlib.util.spec_from_file_location("customer_entry", app / "tools" / "customer.py")
    mod = importlib.util.module_from_spec(spec)
    sys.argv = [str(app / "tools" / "customer.py")]
    try:
        spec.loader.exec_module(mod)
        inst = mod.packaged_runtime()
        print("\npackaged_runtime() 校验通过")
        print(json.dumps({k: inst[k] for k in ("scope", "formula_inference_activated")},
                         ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"\n校验失败：{type(exc).__name__}: {exc}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
