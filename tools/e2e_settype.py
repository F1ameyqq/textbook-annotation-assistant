#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/e2e_settype.py — 补 SOP 步骤 4：加载指定 order → 选题型 → 提交（更新）→ 回读

背景（2026-10-27 自查）：首次端到端提交只画了 Q 框就提交，**漏了选题型**，
服务端回读 tishi/tilei/tihao 全为 null。本脚本补这一步并验证。

题型选项实测可用值：选择 / 填空（其余需先列出 dropdown 项确认）
本页 Q1「化简：(1)…=____」按 SOP §5.2 判据（有下划线）→ 填空
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

DBLCLICK_NODE = """(num) => {
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
  const nodes = [...document.querySelectorAll('.el-tree-node__content')];
  const hit = nodes.find(n => norm(n.innerText).split(' ').includes(String(num)));
  if (!hit) return {ok: false, total: nodes.length};
  hit.dispatchEvent(new MouseEvent('dblclick', {bubbles: true, cancelable: true, view: window}));
  return {ok: true, text: norm(hit.innerText)};
}"""

OPEN_TYPE_SELECT = """() => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const sels = [...document.querySelectorAll('.el-select')].filter(vis);
  if (!sels.length) return {ok: false};
  const el = sels[0];
  const r = el.getBoundingClientRect();
  return {ok: true, x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2)};
}"""

PICK_ITEM = """(name) => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const items = [...document.querySelectorAll('.el-select-dropdown__item')].filter(vis);
  const hit = items.find(e => (e.innerText || '').trim() === name);
  if (!hit) return {ok: false, options: items.map(e => (e.innerText || '').trim())};
  for (const t of ['mousedown', 'mouseup', 'click']) {
    hit.dispatchEvent(new MouseEvent(t, {bubbles: true, cancelable: true, view: window}));
  }
  return {ok: true, options: items.map(e => (e.innerText || '').trim())};
}"""

HOOK = """() => {
  window.__cap3 = {commit: null};
  const OX = window.XMLHttpRequest;
  const op = OX.prototype.open, se = OX.prototype.send;
  OX.prototype.open = function (m, u) { this.__u = u; return op.apply(this, arguments); };
  OX.prototype.send = function (b) {
    this.addEventListener('load', () => {
      if (String(this.__u || '').includes('commit_unified_submit'))
        window.__cap3.commit = {req: typeof b === 'string' ? b.slice(0, 4000) : null,
                                body: String(this.responseText).slice(0, 3000)};
    });
    return se.apply(this, arguments);
  };
  return 'hooked';
}"""

CLICK_TEXT = """(name) => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const c = [...document.querySelectorAll('button, .el-button, span, div')]
    .filter(vis).filter(e => (e.innerText || '').trim() === name);
  if (!c.length) return {ok: false};
  c[c.length - 1].click();
  return {ok: true};
}"""

TYPE_TEXT = """() => {
  const m = document.body.innerText.replace(/\\s+/g, ' ').match(/题型[:：]\\s*(\\S{0,8})/);
  return m ? m[1] : null;
}"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--order", type=int, required=True)
    ap.add_argument("--type", default="填空")
    args = ap.parse_args()
    stamp = datetime.now().strftime("%H%M%S")

    with LiveCDP() as lv:
        print("[load]", json.dumps(lv.page.evaluate(DBLCLICK_NODE, args.order), ensure_ascii=False))
        # 判据：当前题目 == 目标，且 counts 连续两次相同（counts 非零不足以说明加载完成）
        ok = False
        last = None
        for _ in range(40):
            lv.page.wait_for_timeout(800)
            st = lv.read_state()
            if st.get("cur") == str(args.order):
                c = st.get("counts") or {}
                key = json.dumps(c, sort_keys=True)
                if key == last:
                    ok = True
                    break
                last = key
        st = lv.read_state()
        print("[state]", json.dumps(st, ensure_ascii=False), "loaded=", ok)
        if not ok:
            print("[中止] 题目没加载稳")
            return 2

        sel = lv.page.evaluate(OPEN_TYPE_SELECT)
        print("[select]", json.dumps(sel, ensure_ascii=False))
        if not sel.get("ok"):
            print("[中止] 找不到题型下拉")
            return 3
        lv.page.mouse.click(sel["x"], sel["y"])
        lv.page.wait_for_timeout(900)
        pick = lv.page.evaluate(PICK_ITEM, args.type)
        print("[pick]", json.dumps(pick, ensure_ascii=False))
        if not pick.get("ok"):
            print("[中止] 下拉里没有这个选项")
            return 4
        lv.page.wait_for_timeout(1200)
        print("[题型显示]", lv.page.evaluate(TYPE_TEXT))

        lv.page.evaluate(HOOK)
        print("[submit]", json.dumps(lv.page.evaluate(CLICK_TEXT, "提交修改"), ensure_ascii=False))
        commit = None
        for _ in range(40):
            lv.page.wait_for_timeout(1000)
            commit = lv.page.evaluate("() => window.__cap3.commit")
            if commit:
                break
        if not commit:
            print("[中止] 没拿到提交响应")
            return 5
        body = json.loads(commit["body"])
        d = body.get("data") or {}
        print("[响应]", json.dumps({k: d.get(k) for k in
                                   ("inserted", "question_order", "success")}, ensure_ascii=False))
        # 更新已有题 → inserted 应为 false（SOP：inserted:false 说明更新了旧题，属预期）
        if str(d.get("question_order")) != str(args.order):
            print("[警告] order 与预期不符，回读核查")

        rb = lv.page.evaluate("""async (order) => {
          const raw = localStorage.getItem('user'); const tok = JSON.parse(raw).access_token;
          const r = await fetch(`/qieti/api/annotate_pic/get_manual_annotations_unified_by_order_in_level/46007447/${order}`,
            {headers: {Authorization: 'Bearer ' + tok}});
          const j = await r.json(); const d = j.data || [];
          return d.map(x => ({type: x.type, page: x.page_index, tishi: x.tishi,
                              tilei: x.tilei, tihao: x.tihao}));
        }""", args.order)
        print("[回读]", json.dumps(rb, ensure_ascii=False))
        shot = LIVE / f"e2e_type_{stamp}.png"
        lv.page.screenshot(path=str(shot))
        print("[shot]", shot)
        return 0


if __name__ == "__main__":
    sys.exit(main())
