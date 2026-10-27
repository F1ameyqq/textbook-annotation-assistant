#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/live_draw_test.py — 实战验证：答案区翻页复测 + 按测量坐标画框（不提交）

流程
----
1. 开平台 → 选书 46007447
2. 题目区翻 p28、答案区翻 p174，各自用画布指纹验证"页真的换了"
3. dblclick 目录节点加载某题（默认 77 插题），读状态栏 counts
4. 用 p27 测量的 Q1 bbox（源图像素）按 SOP §6.3 换算成 CSS，点「题目(Q)」后拖拽画框
5. 再读 counts，确认 +1；截图留证
6. reload 丢弃未提交框（零残留），并复核 counts 回到原值

坐标换算（SOP §6.3，系数随 canvas 尺寸变，必须现算）：
    k    = 源图宽 / canvas宽
    pad  = (canvas高 − 源图高 / k) / 2
    x_css = x_src / k
    y_css = y_src / k + pad
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live import LIVE, Live  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BOOK = "46007447"
QPAGE, APAGE = 28, 174
SRC_W, SRC_H = 1220, 1693          # data/raw/images/46007447/p27.jpg
MEASURE = ROOT / "data" / "derived" / "measure" / "p27.measure.json"

CLICK_NODE = """(label) => {
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
  const nodes = [...document.querySelectorAll('.el-tree-node__content, .el-tree-node__label, .el-tree-node')];
  const hit = nodes.find(n => norm(n.innerText).startsWith(label));
  if (!hit) {
    const all = [...document.querySelectorAll('.el-tree-node')].slice(0, 40)
      .map(n => norm(n.innerText).slice(0, 20));
    return {ok: false, sample: all};
  }
  const ev = new MouseEvent('dblclick', {bubbles: true, cancelable: true, view: window});
  hit.dispatchEvent(ev);
  return {ok: true, text: norm(hit.innerText).slice(0, 30)};
}"""

CLICK_ROLE = """(name) => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const cands = [...document.querySelectorAll('button, .el-button, span, div')]
    .filter(vis).filter(e => (e.innerText || '').trim() === name);
  if (!cands.length) return {ok: false};
  const el = cands[cands.length - 1];
  el.click();
  return {ok: true, tag: el.tagName, cls: el.className};
}"""


def main() -> int:
    stamp = datetime.now().strftime("%H%M%S")
    LIVE.mkdir(parents=True, exist_ok=True)
    boxes = json.loads(MEASURE.read_text(encoding="utf-8"))["questions"]
    q1 = next(b for b in boxes if b["num"] == 1)["bbox"]
    L = [int(v) for v in q1]

    with Live(headless=True) as lv:
        lv.open()
        print("[book]", json.dumps(lv.select_book(BOOK), ensure_ascii=False))

        # ---- 1. 翻页复测（题目区 + 答案区）----
        rq = lv.goto_page("q", QPAGE)
        print("[goto q]", json.dumps(rq, ensure_ascii=False))
        ra = lv.goto_page("a", APAGE)
        print("[goto a]", json.dumps(ra, ensure_ascii=False))
        lv.page.screenshot(path=str(LIVE / f"drawtest_before_{stamp}.png"))

        # ---- 2. 加载目标题 ----
        node = lv.page.evaluate(CLICK_NODE, "77")
        print("[node]", json.dumps(node, ensure_ascii=False))
        lv.page.wait_for_timeout(3000)
        st0 = lv.read_state()
        print("[state0]", json.dumps(st0, ensure_ascii=False))

        # ---- 3. 坐标换算 ----
        canv = lv.canvases()[0]
        k = SRC_W / canv["w"]
        pad = (canv["h"] - SRC_H / k) / 2
        x1 = L[0] / k
        y1 = L[1] / k + pad
        x2 = L[2] / k
        y2 = L[3] / k + pad
        print(f"[geom] canvas {canv['w']}x{canv['h']}  k={k:.4f}  pad={pad:.2f}")
        print(f"[coord] src {L} → css ({x1:.1f},{y1:.1f})-({x2:.1f},{y2:.1f})")

        # ---- 4. 进入画框模式并拖拽 ----
        role = lv.page.evaluate(CLICK_ROLE, "题目(Q)")
        print("[role Q]", json.dumps(role, ensure_ascii=False))
        lv.page.wait_for_timeout(1600)

        ox, oy = canv["x"], canv["y"]
        lv.page.mouse.move(ox + x1, oy + y1)
        lv.page.wait_for_timeout(250)
        lv.page.mouse.down()
        lv.page.wait_for_timeout(250)
        lv.page.mouse.move(ox + x2, oy + y2, steps=18)
        lv.page.wait_for_timeout(300)
        lv.page.mouse.up()
        lv.page.wait_for_timeout(1200)

        st1 = lv.read_state()
        print("[state1 after draw]", json.dumps(st1, ensure_ascii=False))
        lv.page.screenshot(path=str(LIVE / f"drawtest_after_{stamp}.png"))

        # ---- 5. reload 丢弃未提交框 ----
        lv.page.reload(wait_until="load")
        lv.page.wait_for_timeout(6000)
        st2 = lv.read_state()
        print("[state2 after reload]", json.dumps(st2, ensure_ascii=False))
        print(f"[shots] {LIVE / f'drawtest_before_{stamp}.png'} / drawtest_after_{stamp}.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
