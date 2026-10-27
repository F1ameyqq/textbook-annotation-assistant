#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/contact_sheet.py — 候选框 contact sheet 生成器

把候选框/候选分割线画在原图上并编号，一次看图确认，
替代"裁一块→问一次→再裁"的多轮往返（对应测量成本优化的路线B）。

输入
----
1. 页图（png/jpg）
2. 候选框 JSON，两种格式皆可：
   a) 简单列表：[{"bbox":[x1,y1,x2,y2], "role":"question", "id":"q1"}, ...]
   b) 带 candidates 键：{"candidates":[...同上...]}
   role 取值：question/choice/answer/analysis/text_block/figure（缺省 gray）
   bbox 一律为**源图像素**（与服务端 rect_bbox 同口径）。

输出
----
一张 PNG：原图 + 角色色矩形 + 左上角编号（与输入顺序一致）。
--max-width 控制输出宽度（默认 1600，等比缩放，编号随缩放绘制保证可读）。

用法
----
    python -I tools/contact_sheet.py page.png boxes.json out.png
    python -I tools/contact_sheet.py page.png boxes.json out.png --max-width 2000
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# BGR，与 route_a_layout.draw_overlay 同色系
ROLE_COLORS = {
    "question": (60, 60, 220),      # 红
    "choice": (60, 170, 60),        # 绿
    "answer": (220, 120, 40),       # 蓝
    "analysis": (180, 60, 180),     # 紫
    "figure": (40, 180, 200),       # 青
    "text_block": (140, 140, 140),  # 灰
}
DEFAULT_COLOR = (140, 140, 140)


def load_boxes(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("candidates", data.get("boxes", []))
    out = []
    for i, b in enumerate(data):
        bbox = b.get("bbox") or b.get("rect") or b.get("box")
        if not bbox or len(bbox) != 4:
            raise SystemExit(f"第 {i} 条缺 bbox: {b!r}")
        out.append({"bbox": [float(v) for v in bbox],
                    "role": str(b.get("role", b.get("type", "text_block"))),
                    "id": str(b.get("id", i + 1))})
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="候选框 contact sheet 生成器")
    ap.add_argument("image")
    ap.add_argument("boxes_json")
    ap.add_argument("out")
    ap.add_argument("--max-width", type=int, default=1600)
    args = ap.parse_args(argv)

    boxes = load_boxes(Path(args.boxes_json))
    img = cv2.imread(args.image)
    if img is None:
        raise SystemExit(f"读不到图片: {args.image}")
    H, W = img.shape[:2]

    scale = min(1.0, args.max_width / W)
    if scale < 1.0:
        img = cv2.resize(img, (int(W * scale), int(H * scale)), interpolation=cv2.INTER_AREA)

    thick = max(2, int(2 * scale) + 1)
    font = cv2.FONT_HERSHEY_SIMPLEX
    fscale = max(0.5, 0.9 * scale)
    for idx, b in enumerate(boxes, 1):
        x1, y1, x2, y2 = [int(v * scale) for v in b["bbox"]]
        color = ROLE_COLORS.get(b["role"], DEFAULT_COLOR)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thick)
        label = f'{idx}:{b["role"][:1].upper()}'
        (tw, th), _ = cv2.getTextSize(label, font, fscale, 2)
        ty = max(y1 - 6, th + 4)
        cv2.rectangle(img, (x1, ty - th - 4), (x1 + tw + 6, ty + 4), color, -1)
        cv2.putText(img, label, (x1 + 3, ty), font, fscale, (255, 255, 255), 2, cv2.LINE_AA)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), img)
    print(f"[contact-sheet] {out_path}  共 {len(boxes)} 个候选框  缩放={scale:.3f}")
    # 同步输出编号对照表，方便审阅时按编号反馈
    legend = out_path.with_suffix(".legend.json")
    legend.write_text(json.dumps(
        [{"n": i, **b} for i, b in enumerate(boxes, 1)],
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[contact-sheet] 编号对照表: {legend}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
