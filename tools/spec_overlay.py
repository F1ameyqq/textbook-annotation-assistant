#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/spec_overlay.py — 把 spec 生成的坐标画回页图，用于人眼验收

用法：
    python -I tools/spec_overlay.py specs/p34_out.json data/raw/images/46007447/p34.jpg out.png
颜色：题干框=红，选项框=绿；标签 = 题号 + Q/W + 序号
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    img_path, out_path = Path(sys.argv[2]), Path(sys.argv[3])
    img = cv2.imdecode(np.frombuffer(img_path.read_bytes(), np.uint8), cv2.IMREAD_COLOR)

    def draw(b, color, label):
        x0, y0, x1, y1 = [int(v) for v in b]
        cv2.rectangle(img, (x0, y0), (x1, y1), color, 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(img, (x0, max(y0 - th - 5, 0)), (x0 + tw + 4, max(y0 - 1, th + 4)), color, -1)
        cv2.putText(img, label, (x0 + 2, max(y0 - 4, th + 2)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    nq = nw = 0
    for it in data:
        for i, b in enumerate(it.get("q") or []):
            draw(b, (40, 40, 220), f"Q{it['n']}" + (f".{i+1}" if len(it['q']) > 1 else ""))
            nq += 1
        for i, b in enumerate(it.get("w") or []):
            draw(b, (40, 160, 40), f"W{it['n']}.{i+1}")
            nw += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(out_path.suffix or ".png", img)
    out_path.write_bytes(buf.tobytes())
    print(f"[overlay] {out_path}  题干框 {nq}，选项框 {nw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
