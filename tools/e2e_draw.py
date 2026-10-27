#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/e2e_draw.py — 端到端第 1 步：选目录 → 画题目框 → 校验 counts（不提交）

目标：书 46007447 / 题目页 34 / 课时「第2课时 二次根式的化简及加减运算」
题目 Q1 源图 bbox = [75, 356, 590, 620]（page_measure 产出）

坐标换算（SOP §6.3，系数现算）：
    k   = 源图宽 / canvas宽
    pad = (canvas高 − 源图高/k) / 2
    x_css = x_src/k ,  y_css = y_src/k + pad
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_cdp import LiveCDP  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "data" / "derived" / "live"
SRC_W, SRC_H = 1219, 1693
Q1 = [75, 356, 590, 620]
LESSON = "第2课时 二次根式的化简及加减运算"

CLICK_LESSON = """(label) => {
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
  const nodes = [...document.querySelectorAll('.el-tree-node__content')];
  const hit = nodes.find(n => norm(n.innerText) === label);
  if (!hit) {
    return {ok: false, near: nodes.map(n => norm(n.innerText)).filter(t => t.includes('化简')).slice(0, 6)};
  }
  hit.click();                      // 单击 = 选中目录（双击会加载题目）
  return {ok: true, text: norm(hit.innerText)};
}"""

CLICK_ROLE = """(name) => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const cands = [...document.querySelectorAll('button, .el-button, span, div')]
    .filter(vis).filter(e => (e.innerText || '').trim() === name);
  if (!cands.length) return {ok: false};
  const el = cands[cands.length - 1];
  el.click();
  return {ok: true, cls: String(el.className).slice(0, 40)};
}"""

CUR_DIR = """() => {
  const cur = document.querySelector('.el-tree-node.is-current .el-tree-node__content');
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
  return cur ? norm(cur.innerText) : null;
}"""


def main() -> int:
    stamp = datetime.now().strftime("%H%M%S")
    LIVE.mkdir(parents=True, exist_ok=True)
    with LiveCDP() as lv:
        if not lv.canvases():
            lv.select_book("46007447")
        print("[page]", json.dumps(lv.goto_page("q", 34), ensure_ascii=False))

        print("[lesson]", json.dumps(lv.page.evaluate(CLICK_LESSON, LESSON), ensure_ascii=False))
        lv.page.wait_for_timeout(2500)
        print("[cur-dir]", json.dumps(lv.page.evaluate(CUR_DIR), ensure_ascii=False))
        st0 = lv.read_state()
        print("[state0]", json.dumps(st0, ensure_ascii=False))

        canv = lv.canvases()[0]
        k = SRC_W / canv["w"]
        pad = (canv["h"] - SRC_H / k) / 2
        x1, x2 = Q1[0] / k, Q1[2] / k
        y1, y2 = Q1[1] / k + pad, Q1[3] / k + pad
        print(f"[geom] canvas {canv['w']}x{canv['h']} k={k:.4f} pad={pad:.2f}")
        print(f"[coord] src {Q1} → css ({x1:.1f},{y1:.1f})-({x2:.1f},{y2:.1f})")

        print("[role Q]", json.dumps(lv.page.evaluate(CLICK_ROLE, "题目(Q)"), ensure_ascii=False))
        lv.page.wait_for_timeout(1600)

        ox, oy = canv["x"], canv["y"]
        lv.page.mouse.move(ox + x1, oy + y1)
        lv.page.wait_for_timeout(250)
        lv.page.mouse.down()
        lv.page.wait_for_timeout(250)
        lv.page.mouse.move(ox + x2, oy + y2, steps=20)
        lv.page.wait_for_timeout(300)
        lv.page.mouse.up()
        lv.page.wait_for_timeout(1500)

        st1 = lv.read_state()
        print("[state1 after draw]", json.dumps(st1, ensure_ascii=False))
        shot = LIVE / f"e2e_draw_{stamp}.png"
        lv.page.screenshot(path=str(shot))
        print("[shot]", shot)
        return 0


if __name__ == "__main__":
    sys.exit(main())
