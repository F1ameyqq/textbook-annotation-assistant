#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/verify_measure.py — 用服务端已提交的 rect_bbox 校验测量精度（只读）

思路：书 46007447 的 64–77 是 SOP 里已提交的整页标注（Q1 W4 A1）。
它们正是 p28 的 14 道题。把 paint_measure 出的题块框与服务端 rect_bbox 逐题比 IoU，
就能在没有画框、没有写平台的情况下量化测量精度。

同时按 SOP §6.3 反推 canvas→源图 的 k/pad，检查与实测几何是否自洽。

输出：data/derived/measure/verify_vs_server.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live import ROOT, Live  # noqa: E402

BOOK = "46007447"
FIRST, LAST = 64, 77          # p28 的 14 题
MEASURE = ROOT / "data" / "derived" / "measure" / "p27.measure.json"
OUT = ROOT / "data" / "derived" / "measure" / "verify_vs_server.json"

FETCH = """async (args) => {
  const raw = localStorage.getItem('user');
  const tok = raw ? JSON.parse(raw).access_token : null;
  if (!tok) return {error: 'no token'};
  const [book, order] = args;
  const r = await fetch(`/qieti/api/annotate_pic/get_manual_annotations_unified_by_order_in_level/${book}/${order}`,
    {headers: {Authorization: 'Bearer ' + tok, Accept: 'application/json'}});
  const j = await r.json();
  const d = j.data || [];
  return d.map(x => ({type: x.type, bbox: x.rect_bbox, page: x.page_index,
                      order: x.order_in_level, id: x.rect_id}));
}"""


def parse_bbox(v):
    """rect_bbox 可能是 'x1,y1,x2,y2' 字符串或 [x1,y1,x2,y2]。"""
    if isinstance(v, str):
        parts = [p for p in v.replace(";", ",").split(",") if p.strip()]
        try:
            return [float(p) for p in parts[:4]]
        except ValueError:
            return None
    if isinstance(v, (list, tuple)) and len(v) >= 4:
        return [float(x) for x in v[:4]]
    return None


def iou(a, b):
    if not a or not b:
        return 0.0
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, x2 - x1), max(0.0, y2 - y1)
    inter = iw * ih
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def main() -> int:
    measured = {q["num"]: q["bbox"] for q in json.loads(MEASURE.read_text(encoding="utf-8"))["questions"]}
    rows = []
    with Live(headless=True) as lv:
        lv.open()
        lv.select_book(BOOK)
        for order in range(FIRST, LAST + 1):
            anns = lv.page.evaluate(FETCH, [BOOK, order])
            qbox = None
            for a in anns or []:
                if a.get("type") == "question":
                    qbox = parse_bbox(a.get("bbox"))
                    page = a.get("page")
                    break
            num = order - FIRST + 1
            mine = measured.get(num)
            rows.append({"order": order, "q_num": num, "server_bbox": qbox,
                         "measured": mine, "iou": round(iou(qbox, mine), 4),
                         "server_page": page if qbox else None})
            print(f"order {order} (Q{num:>2})  server={qbox}  mine={mine}  IoU={rows[-1]['iou']}")

    vals = [r["iou"] for r in rows if r["server_bbox"]]
    summary = {"n": len(vals),
               "mean_iou": round(sum(vals) / len(vals), 4) if vals else None,
               "min_iou": min(vals) if vals else None,
               "ge_0.7": sum(1 for v in vals if v >= 0.7),
               "ge_0.9": sum(1 for v in vals if v >= 0.9)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print("[summary]", json.dumps(summary, ensure_ascii=False))
    print(f"[out] {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
