#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/live_cdp.py — 接管「已经开着的可见 Edge」（远程调试 9222）

为什么要它：端到端验证时人要能全程看着浏览器。用 CDP 接管同一个窗口，
既可视、又可编程，避免"脚本自己开一个看不见的浏览器"。

用法（先确保 Edge 已用 --remote-debugging-port=9222 启动）：
    from live_cdp import LiveCDP
    with LiveCDP() as lv:
        lv.select_book("46007447")
        lv.goto_page("q", 34)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CDP_URL = "http://127.0.0.1:9222"
TARGET = "https://www.usense.com/qieti/annotateUnified"


class LiveCDP:
    def __init__(self, cdp: str = CDP_URL):
        self.cdp = cdp
        self._pw = None
        self.browser = None
        self.ctx = None
        self.page = None

    def __enter__(self) -> "LiveCDP":
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.connect_over_cdp(self.cdp)
        self.ctx = self.browser.contexts[0]
        self.page = self._find_page()
        return self

    def __exit__(self, *exc):
        # 只断开工作线程，不关闭用户的浏览器
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass

    def _find_page(self):
        for p in self.ctx.pages:
            if "annotateUnified" in p.url:
                return p
        for p in self.ctx.pages:
            if "usense.com" in p.url:
                return p
        return self.ctx.pages[0]

    # ---------- 与 Live 对齐的最小能力集 ----------
    def open(self) -> None:
        if "annotateUnified" not in self.page.url:
            self.page.goto(TARGET, wait_until="load", timeout=60000)
        self.page.wait_for_timeout(3000)

    def select_book(self, book_id: str, wait_ms: int = 6500) -> dict:
        self.page.get_by_text("选择书籍", exact=True).first.click()
        self.page.wait_for_timeout(2000)
        res = self.page.evaluate("""(bookId) => {
          const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
          const row = [...document.querySelectorAll('.el-table__row')].filter(vis)
            .find(tr => tr.innerText.includes(bookId));
          if (!row) return {ok: false, reason: 'row not found'};
          const btn = [...row.querySelectorAll('button, .el-button')]
            .find(b => b.innerText.trim().includes('选择'));
          if (!btn) return {ok: false, reason: 'button not found'};
          btn.click();
          return {ok: true};
        }""", book_id)
        self.page.wait_for_timeout(wait_ms)
        return res

    def inputs(self) -> list[dict]:
        return self.page.evaluate("""() => {
          const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
          return [...document.querySelectorAll('input')].filter(vis).map((e, i) => {
            const r = e.getBoundingClientRect();
            return {i, ph: e.placeholder || '', x: Math.round(r.x), y: Math.round(r.y),
                    w: Math.round(r.width), h: Math.round(r.height), val: e.value};
          });
        }""")

    def _page_input(self, panel: str) -> dict:
        cands = [i for i in self.inputs() if not i["ph"] and i["y"] < 120 and i["w"] <= 60]
        cands.sort(key=lambda i: i["x"])
        if len(cands) < 2:
            raise RuntimeError(f"找不到两个页码框: {json.dumps(self.inputs(), ensure_ascii=False)}")
        return cands[0] if panel == "q" else cands[1]

    def goto_page(self, panel: str, page_no: int, wait_ms: int = 4000) -> dict:
        before = self.page_url_value(panel)
        inp = self._page_input(panel)
        self.page.mouse.click(inp["x"] + inp["w"] / 2, inp["y"] + inp["h"] / 2)
        self.page.wait_for_timeout(400)
        self.page.keyboard.down("Control")
        self.page.keyboard.press("a")
        self.page.keyboard.up("Control")
        self.page.keyboard.type(str(page_no), delay=80)
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(wait_ms)
        after = self.page_url_value(panel)
        return {"panel": panel, "want": page_no, "before": before, "after": after,
                "changed": before != after, "ok": after == str(page_no)}

    def page_url_value(self, panel: str) -> str:
        """工具栏页码框的 value —— 权威判据（画布指纹会被异步重绘干扰）。"""
        try:
            return str(self._page_input(panel)["val"])
        except Exception:
            return ""

    def canvases(self) -> list[dict]:
        return self.page.evaluate("""() => {
          return [...document.querySelectorAll('canvas.pdf-canvas')].map((c, i) => {
            const r = c.getBoundingClientRect();
            return {i, w: c.width, h: c.height, cssW: Math.round(r.width),
                    cssH: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y),
                    dpr: window.devicePixelRatio};
          });
        }""")

    def read_state(self) -> dict:
        return self.page.evaluate("""() => {
          const t = document.body.innerText.replace(/\\s+/g, ' ');
          const m = t.match(/题目框\\s*(\\d+)\\s*答案\\s*(\\d+)\\s*选项\\s*(\\d+)\\s*解析\\s*(\\d+)\\s*知识点\\s*(\\d+)/);
          return {
            counts: m ? {question: +m[1], answer: +m[2], choice: +m[3],
                         analysis: +m[4], knowledge: +m[5]} : null,
            cur: (t.match(/当前题目[:：]\\s*(\\d+)/) || [])[1] || null,
            type: (t.match(/题型[:：]\\s*(\\S+)/) || [])[1] || null,
            done: (t.match(/已完成题目[^0-9]*([0-9]+)/) || [])[1] || null,
          };
        }""")
