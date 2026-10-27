#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/live.py — 平台实战封装（playwright 版 SOP 驱动层）

把 SOP 里依赖 ego 的动作封装成可复用函数：
  select_book / goto_page / read_state / shot_canvas / capture_images

约定与 SOP 一致：
  - 坐标一律 CSS px（相对 canvas 左上角），换源图像素用 §6.3 的 k/pad 公式
  - 翻页只用真实键盘（click → Ctrl+A → type → Enter）
  - 不打印 token
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROFILE = str(ROOT / "bin" / "browser-profiles" / "work-default")
TARGET = "https://www.usense.com/qieti/annotateUnified"
LIVE = ROOT / "data" / "derived" / "live"


class Live:
    def __init__(self, headless: bool = True, viewport=(1600, 1000), profile=None):
        # profile: 可选，指定持久化 profile 目录（并行探针用；默认 work-default）
        self.profile = str(profile) if profile else PROFILE
        self._pw = None
        self.ctx: BrowserContext | None = None
        self.page: Page | None = None
        self.headless = headless
        self.viewport = viewport
        self.images: list[dict] = []

    # ---------- 生命周期 ----------
    def __enter__(self) -> "Live":
        self._pw = sync_playwright().start()
        self.ctx = self._pw.chromium.launch_persistent_context(
            self.profile, channel="msedge", headless=self.headless,
            ignore_https_errors=True, viewport={"width": self.viewport[0],
                                                "height": self.viewport[1]})
        self.page = self.ctx.pages[0]
        return self

    def __exit__(self, *exc):
        try:
            if self.ctx:
                self.ctx.close()
        finally:
            if self._pw:
                self._pw.stop()

    # ---------- 导航 ----------
    def open(self) -> None:
        self.page.goto(TARGET, wait_until="load", timeout=60000)
        self.page.wait_for_timeout(5000)

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
        """所有可见 input 的 DOM 顺序、位置、placeholder —— 用于定位页码框。"""
        return self.page.evaluate("""() => {
          const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
          return [...document.querySelectorAll('input')].filter(vis).map((e, i) => {
            const r = e.getBoundingClientRect();
            return {i, ph: e.placeholder || '', x: Math.round(r.x), y: Math.round(r.y),
                    w: Math.round(r.width), h: Math.round(r.height), val: e.value};
          });
        }""")

    def _page_input(self, panel: str) -> dict:
        """
        题目区/答案区各自的「跳转到」页码框。
        实测(2026-10-27)：工具栏内的页码框是 y<120、无 placeholder、w≈30 的 input；
        右侧编辑区的题号框 y≈149、题号框 placeholder="题号"、页码显示 y≈965，都要排除。
        按 x 排序：题目区在左，答案区在右。
        """
        ins = self.inputs()
        cands = [i for i in ins
                 if not i["ph"] and i["y"] < 120 and i["w"] <= 60]
        cands.sort(key=lambda i: i["x"])
        if len(cands) < 2:
            raise RuntimeError(f"找不到两个页码输入框: {json.dumps(ins, ensure_ascii=False)}")
        return cands[0] if panel == "q" else cands[1]

    def goto_page(self, panel: str, page_no: int, wait_ms: int = 4000) -> dict:
        """
        真实键盘翻页（SOP §3.5），返回翻页前后 canvas 截图哈希，用于确认"画布真的变了"。
        """
        before = self._canvas_hash(panel)
        inp = self._page_input(panel)
        self.page.mouse.click(inp["x"] + inp["w"] / 2, inp["y"] + inp["h"] / 2)
        self.page.wait_for_timeout(400)
        self.page.keyboard.down("Control")
        self.page.keyboard.press("a")
        self.page.keyboard.up("Control")
        self.page.keyboard.type(str(page_no), delay=80)
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(wait_ms)
        after = self._canvas_hash(panel)
        return {"panel": panel, "page_no": page_no, "changed": before != after,
                "before": before[:12], "after": after[:12]}

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
            head: t.slice(0, 160),
          };
        }""")

    def _canvas_hash(self, panel: str, box=(0, 0, 40, 40)) -> str:
        """取 canvas 一小块指纹，用来判断内容是否真的换了页。"""
        idx = 0 if panel == "q" else 1
        return self.page.evaluate("""([idx, bx, by, bw, bh]) => {
          const c = document.querySelectorAll('canvas.pdf-canvas')[idx];
          if (!c) return '';
          const g = c.getContext('2d');
          try {
            const d = g.getImageData(bx, by, bw, bh).data;
            let h = 0;
            for (let i = 0; i < d.length; i += 97) h = (h * 31 + d[i]) >>> 0;
            return String(h);
          } catch (e) { return 'ERR'; }
        }""", [idx, box[0], box[1], box[2], box[3]])

    def shot_canvas(self, panel: str, out: Path, scale: float = 2.0) -> Path:
        idx = 0 if panel == "q" else 1
        el = self.page.locator("canvas.pdf-canvas").nth(idx)
        out.parent.mkdir(parents=True, exist_ok=True)
        el.screenshot(path=str(out))
        return out

    def capture_images(self, page_urls_from: float = 0) -> list[dict]:
        """返回本次会话记录到的图片响应 URL 列表（需在导航前开始监听）。"""
        return self.images

    def start_image_watch(self) -> None:
        def on_resp(resp):
            try:
                ct = resp.headers.get("content-type", "")
                if ct.startswith("image/") or "/image" in resp.url or "page" in resp.url:
                    self.images.append({"url": resp.url, "ct": ct, "status": resp.status})
            except Exception:
                pass
        self.page.on("response", on_resp)
