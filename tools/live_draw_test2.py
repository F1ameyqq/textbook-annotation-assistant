#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/live_draw_test2.py — 实战验证 v2：等加载完成再画框（不提交）

v1 教训（2026-10-27）：dblclick 加载题目是**异步**的，读完 state 立刻画框，
框会被随后的重渲染清掉——表现为 counts 不增，且完全没有报错。
所以 v2：dblclick 后轮询状态栏，直到 counts 归一/当前题目变成目标值，才开始画。

同时在加载完成后，答案区会自动渲染该题对应的答案页（v1 已实测到 p174）。
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
SRC_W, SRC_H = 1220, 1693
MEASURE = ROOT / "data" / "derived" / "measure" / "p27.measure.json"

CLICK_NODE = """(label) => {
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
  const num = String(label).split(' ')[0];
  const nodes = [...document.querySelectorAll('.el-tree-node__content')];
  // 节点文本可能是 "64\\n插题"，也可能带徽标 "部分失败\\n64\\n插题"
  const hit = nodes.find(n => norm(n.innerText).split(' ').includes(num));
  if (!hit) {
    const sample = nodes.map(n => norm(n.innerText)).filter(t => t.includes(num)).slice(0, 5);
    return {ok: false, total: nodes.length, sample};
  }
  hit.dispatchEvent(new MouseEvent('dblclick', {bubbles: true, cancelable: true, view: window}));
  return {ok: true, text: norm(hit.innerText)};
}"""

CLICK_ROLE = """(name) => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const cands = [...document.querySelectorAll('button, .el-button, span, div')]
    .filter(vis).filter(e => (e.innerText || '').trim() === name);
  if (!cands.length) return {ok: false};
  const el = cands[cands.length - 1];
  el.click();
  return {ok: true, tag: el.tagName, cls: String(el.className).slice(0, 40)};
}"""


def wait_loaded(lv, target_cur=None, timeout_s=30):
    """轮询状态栏直到 counts 非全零（或 cur==target）。"""
    import time
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout_s:
        st = lv.read_state()
        last = st
        c = st.get("counts") or {}
        if sum(c.values()) > 0 or (target_cur and st.get("cur") == str(target_cur)):
            return st
        lv.page.wait_for_timeout(800)
    return last


def main() -> int:
    stamp = datetime.now().strftime("%H%M%S")
    LIVE.mkdir(parents=True, exist_ok=True)
    q1 = next(b for b in json.loads(MEASURE.read_text(encoding="utf-8"))["questions"]
              if b["num"] == 1)["bbox"]
    L = [int(v) for v in q1]

    with Live(headless=True) as lv:
        lv.open()
        print("[book]", json.dumps(lv.select_book(BOOK), ensure_ascii=False))

        node = lv.page.evaluate(CLICK_NODE, "64 插题")
        print("[node]", json.dumps(node, ensure_ascii=False))
        st0 = wait_loaded(lv)
        print("[state loaded]", json.dumps(st0, ensure_ascii=False))
        lv.page.wait_for_timeout(1200)
        lv.page.screenshot(path=str(LIVE / f"v2_loaded_{stamp}.png"))

        canv = lv.canvases()[0]
        k = SRC_W / canv["w"]
        pad = (canv["h"] - SRC_H / k) / 2
        x1, x2 = L[0] / k, L[2] / k
        y1, y2 = L[1] / k + pad, L[3] / k + pad
        print(f"[geom] canvas {canv['w']}x{canv['h']} k={k:.4f} pad={pad:.2f}")
        print(f"[coord] src {L} → css ({x1:.1f},{y1:.1f})-({x2:.1f},{y2:.1f})")

        print("[role]", json.dumps(lv.page.evaluate(CLICK_ROLE, "题目(Q)"), ensure_ascii=False))
        lv.page.wait_for_timeout(1600)

        ox, oy = canv["x"], canv["y"]
        lv.page.mouse.move(ox + x1, oy + y1)
        lv.page.wait_for_timeout(250)
        lv.page.mouse.down()
        lv.page.wait_for_timeout(250)
        lv.page.mouse.move(ox + x2, oy + y2, steps=18)
        lv.page.wait_for_timeout(300)
        lv.page.mouse.up()
        lv.page.wait_for_timeout(1500)

        st1 = lv.read_state()
        print("[state after draw]", json.dumps(st1, ensure_ascii=False))
        lv.page.screenshot(path=str(LIVE / f"v2_drawn_{stamp}.png"))

        # 回读服务端确认未写入（提交前不该有变化）
        readback = lv.page.evaluate("""async (q) => {
          const raw = localStorage.getItem('user');
          const tok = raw ? JSON.parse(raw).access_token : null;
          if (!tok) return {error: 'no token'};
          const r = await fetch(`/qieti/api/annotate_pic/get_manual_annotations_unified_by_order_in_level/46007447/${q}`,
            {headers: {Authorization: 'Bearer ' + tok}});
          const j = await r.json();
          const d = j.data || j || [];
          return {n: Array.isArray(d) ? d.length : null,
                  types: Array.isArray(d) ? [...new Set(d.map(x => x.type))] : null};
        }""", 64)
        print("[readback server]", json.dumps(readback, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
