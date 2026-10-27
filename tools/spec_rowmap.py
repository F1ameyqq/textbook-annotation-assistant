#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/spec_rowmap.py — 把行分割结果画到页图上，给人工/模型确认"行号 → 内容"

用法：
    python -I tools/spec_rowmap.py specs/p34_base.json data/derived/measure/p34_rowmap.png
输出：左/右栏每行画一条横线 + 行号标签（行号与 spec 里的 L00/R00 一致）
"""
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
ROW_RE = re.compile(r"^([LR]\d+|\d+)\s+y\[\s*([\d.]+),\s*([\d.]+)\]")


def rows_from_adapter(spec_path: Path) -> dict:
    """调用适配器的 --dump-rows，解析出 {栏: [(idx, y0, y1), ...]}"""
    out = subprocess.run(
        [sys.executable, "-I", str(ROOT / "tools" / "measure_page_adapt.py"),
         str(spec_path), "--dump-rows"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = out.stdout.splitlines()
    res = {}
    for ln in lines:
        m = ROW_RE.match(ln.strip())
        if not m:
            continue
        label, y0, y1 = m.group(1), float(m.group(2)), float(m.group(3))
        tag = label[0] if label[0].isalpha() else ""
        idx = int(label[len(tag):])
        res.setdefault(tag, []).append((idx, y0, y1))
    return res


def main() -> int:
    spec_path = Path(sys.argv[1])
    out_png = Path(sys.argv[2])
    spec = json.load(io.open(spec_path, encoding="utf-8"))
    img = cv2.imdecode(np.frombuffer(Path(spec["src"]).read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    rows = rows_from_adapter(spec_path)

    for tag, rs in rows.items():
        x0, x1 = spec["cols"][tag] if tag else (0, img.shape[1])
        color = (0, 120, 255) if tag == "L" else (0, 180, 120)
        for idx, y0, y1 in rs:
            cv2.line(img, (int(x0), int(y0)), (int(x1), int(y0)), color, 1)
            cv2.putText(img, f"{tag}{idx:02d}", (int(x0) - 52 if tag == "L" else int(x0) + 2,
                                                 int(y0) + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(out_png.suffix or ".png", img)
    out_png.write_bytes(buf.tobytes())
    print(f"[rowmap] {out_png}  行数 L={len(rows.get('L', []))} R={len(rows.get('R', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
