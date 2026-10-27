#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/e2e_answer.py — 端到端补答案框：p175 上给 order 95 画 2 个答案框 → 识别 → 提交 → 回读

为什么是两个框：p175 的 Q1 答案跨两行，第二行右侧紧挨着 Q2 的答案「2.B」。
按 SOP R04（答案必须按题号拆分），必须把第二行左半（√64 √5/8）单独切出来，
否则 OCR 会把 Q2 的答案吃进 Q1。

坐标（源图像素，p174.jpg = 平台答案页 175，尺寸 1147×1620）：
    A1: x 56..532, y 1462..1496   （第 1 行：(1)(2)(3) 的答案值）
    A2: x 56..140, y 1494..1526   （第 2 行左半：√64  √5/8，避开右侧 2.B）

换算：k = 源图宽/canvas宽；pad = (canvas高 − 源图高/k)/2；x=x_src/k，y=y_src/k+pad

第二个框用**反向拖拽**（右下→左上），避开第一个框的 resize handle（SOP #26）。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_cdp import LiveCDP  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "data" / "derived" / "live"
SRC_A_W, SRC_A_H = 1147, 1620
ANS_PAGE = 175
A1 = [56, 1462, 532, 1496]
A2 = [56, 1494, 140, 1526]

DBLCLICK_NODE = """(num) => {
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
  const hit = [...document.querySelectorAll('.el-tree-node__content')]
    .find(n => norm(n.innerText).split(' ').includes(String(num)));
  if (!hit) return {ok: false};
  hit.dispatchEvent(new MouseEvent('dblclick', {bubbles: true, cancelable: true, view: window}));
  return {ok: true, text: norm(hit.innerText)};
}"""

CLICK_ROLE = """(name) => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const c = [...document.querySelectorAll('button, .el-button, span, div')]
    .filter(vis).filter(e => (e.innerText || '').trim() === name);
  if (!c.length) return {ok: false};
  c[c.length - 1].click();
  return {ok: true, cls: String(c[c.length - 1].className).slice(0, 40)};
}"""


def drag(lv, ox, oy, p1, p2, steps=18):
    lv.page.mouse.move(ox + p1[0], oy + p1[1])
    lv.page.wait_for_timeout(250)
    lv.page.mouse.down()
    lv.page.wait_for_timeout(250)
    lv.page.mouse.move(ox + p2[0], oy + p2[1], steps=steps)
    lv.page.wait_for_timeout(300)
    lv.page.mouse.up()
    lv.page.wait_for_timeout(1300)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--order", type=int, default=95)
    args = ap.parse_args()
    stamp = datetime.now().strftime("%H%M%S")

    with LiveCDP() as lv:
        print("[load]", json.dumps(lv.page.evaluate(DBLCLICK_NODE, args.order), ensure_ascii=False))
        last, ok = None, False
        for _ in range(40):
            lv.page.wait_for_timeout(800)
            st = lv.read_state()
            if st.get("cur") == str(args.order):
                key = json.dumps(st.get("counts"), sort_keys=True)
                if key == last:
                    ok = True
                    break
                last = key
        st = lv.read_state()
        print("[state]", json.dumps(st, ensure_ascii=False), "loaded=", ok)
        if not ok:
            print("[中止] 题目未加载稳")
            return 2

        print("[goto a]", json.dumps(lv.goto_page("a", ANS_PAGE), ensure_ascii=False))
        canv = lv.canvases()[1]
        k = SRC_A_W / canv["w"]
        pad = (canv["h"] - SRC_A_H / k) / 2
        ox, oy = canv["x"], canv["y"]
        print(f"[geom] answer canvas {canv['w']}x{canv['h']} k={k:.4f} pad={pad:.2f}")

        def to_css(b):
            return [b[0] / k, b[1] / k + pad, b[2] / k, b[3] / k + pad]

        c1, c2 = to_css(A1), to_css(A2)
        print(f"[css] A1=({c1[0]:.1f},{c1[1]:.1f})-({c1[2]:.1f},{c1[3]:.1f})  "
              f"A2=({c2[0]:.1f},{c2[1]:.1f})-({c2[2]:.1f},{c2[3]:.1f})")

        print("[role A]", json.dumps(lv.page.evaluate(CLICK_ROLE, "答案(A)"), ensure_ascii=False))
        lv.page.wait_for_timeout(1700)

        drag(lv, ox, oy, (c1[0], c1[1]), (c1[2], c1[3]))
        print("[counts after A1]", json.dumps(lv.read_state(), ensure_ascii=False))

        # 第二个框反向拖（右下 → 左上），避开前一个框的 handle
        drag(lv, ox, oy, (c2[2], c2[3]), (c2[0], c2[1]))
        st = lv.read_state()
        print("[counts after A2]", json.dumps(st, ensure_ascii=False))
        shot = LIVE / f"e2e_ans_{stamp}.png"
        lv.page.screenshot(path=str(shot))
        print("[shot]", shot)
        return 0


if __name__ == "__main__":
    sys.exit(main())
