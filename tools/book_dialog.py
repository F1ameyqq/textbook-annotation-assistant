#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/book_dialog.py — 打开「选择书籍」对话框并 dump 结构（只读，不选书）

用法：
    bin/book_dialog.py dump        # 打开对话框，打印行/按钮结构 + 截图
    bin/book_dialog.py pick 46007447  # 找到该书的行，点它的「选择」，等6s，回报 canvas
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROFILE = str(ROOT / "bin" / "browser-profiles" / "work-default")
TARGET = "https://www.usense.com/qieti/annotateUnified"
OUT = ROOT / "data" / "derived" / "live"

DUMP = """() => {
  const visible = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const dlg = [...document.querySelectorAll('.el-dialog, .el-drawer, .el-message-box')].filter(visible);
  const rows = [...document.querySelectorAll('.el-table__row')].filter(visible);
  const rowData = rows.slice(0, 12).map(tr => ({
    text: tr.innerText.replace(/\\s+/g, ' ').trim().slice(0, 120),
    buttons: [...tr.querySelectorAll('button, .el-button')].map(b => b.innerText.trim()).filter(Boolean),
    cls: tr.className,
  }));
  return {
    nDialogs: dlg.length,
    dialogText: dlg.map(d => d.innerText.replace(/\\s+/g, ' ').slice(0, 600)),
    nRows: rows.length,
    rowData,
  };
}"""

PICK = """(bookId) => {
  const visible = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const rows = [...document.querySelectorAll('.el-table__row')].filter(visible);
  const hit = rows.find(tr => tr.innerText.includes(bookId));
  if (!hit) return {ok: false, reason: 'row not found', scanned: rows.length,
                     sample: rows.slice(0, 5).map(r => r.innerText.replace(/\\s+/g, ' ').trim().slice(0, 80))};
  const btn = [...hit.querySelectorAll('button, .el-button')]
    .find(b => b.innerText.trim().includes('选择'));
  if (!btn) return {ok: false, reason: 'select button not found'};
  btn.click();
  return {ok: true, clicked: btn.innerText.trim()};
}"""


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "dump"
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%H%M%S")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, channel="msedge", headless=True, ignore_https_errors=True,
            viewport={"width": 1600, "height": 1000})
        try:
            page = ctx.pages[0]
            page.goto(TARGET, wait_until="load", timeout=60000)
            page.wait_for_timeout(5000)
            page.get_by_text("选择书籍", exact=True).first.click()
            page.wait_for_timeout(2500)
            print(json.dumps(page.evaluate(DUMP), ensure_ascii=False, indent=1))
            page.screenshot(path=str(OUT / f"bookdialog_{stamp}.png"))
            print(f"[shot] {OUT / f'bookdialog_{stamp}.png'}")
            if mode == "pick":
                book = sys.argv[2]
                res = page.evaluate(PICK, book)
                print("[pick]", json.dumps(res, ensure_ascii=False))
                page.wait_for_timeout(6500)
                state = page.evaluate("""() => {
                  const cs = [...document.querySelectorAll('canvas')].map(c => ({cls: c.className, w: c.width, h: c.height}));
                  const t = document.body.innerText.replace(/\\s+/g, ' ');
                  return {nCanvas: cs.length, canvases: cs, has410To447: t.includes('46007447'),
                          bodyHead: t.slice(0, 500)};
                }""")
                print("[after]", json.dumps(state, ensure_ascii=False, indent=1))
                page.screenshot(path=str(OUT / f"bookpicked_{stamp}.png"))
                print(f"[shot] {OUT / f'bookpicked_{stamp}.png'}")
        finally:
            ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
