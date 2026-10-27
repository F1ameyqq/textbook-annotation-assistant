#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/explore_page.py — 平台页面侦察（只读）

打开 annotateUnified，采集：
  - 当前 URL / 是否停在首页或书籍选择
  - canvas 数量与尺寸（SOP §3.1）
  - 可见按钮/下拉的文本清单（用来定位「选择书籍」等控件）
  - body 文本头部（判断当前处于哪一步）
  - 全页截图（data/derived/live/explore_NN.png）

不点任何按钮，不写任何数据。
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

COLLECT = """() => {
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const canvases = [...document.querySelectorAll('canvas')].map((c, i) => {
    const r = c.getBoundingClientRect();
    return {i, cls: c.className, w: c.width, h: c.height,
            cssW: Math.round(r.width), cssH: Math.round(r.height),
            x: Math.round(r.x), y: Math.round(r.y)};
  });
  const buttons = [...document.querySelectorAll('button, .el-button, a')]
    .filter(visible).slice(0, 60)
    .map(e => (e.innerText || '').replace(/\\s+/g, ' ').trim())
    .filter(t => t && t.length < 30);
  const inputs = [...document.querySelectorAll('input')]
    .filter(visible)
    .map(e => ({ph: e.placeholder || '', type: e.type, val: e.value}));
  return {
    url: location.href,
    title: document.title,
    nCanvas: canvases.length,
    canvases,
    buttons: [...new Set(buttons)],
    inputs,
    bodyHead: document.body.innerText.replace(/\\s+/g, ' ').slice(0, 1200),
  };
}"""


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%H%M%S")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, channel="msedge", headless=True, ignore_https_errors=True,
            viewport={"width": 1600, "height": 1000},
        )
        try:
            page = ctx.pages[0]
            page.goto(TARGET, wait_until="load", timeout=60000)
            page.wait_for_timeout(6000)
            info = page.evaluate(COLLECT)
            print(json.dumps(info, ensure_ascii=False, indent=1))
            shot = OUT / f"explore_{stamp}.png"
            page.screenshot(path=str(shot), full_page=False)
            print(f"[shot] {shot}")
            (OUT / f"explore_{stamp}.json").write_text(
                json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
        finally:
            ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
