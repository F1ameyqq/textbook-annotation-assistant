#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/live_probe.py — 实战侦察：选书 → 看输入框 → 翻到 p28/p174 → 抓图片资源 URL

用法：
    bin/live_probe.py [--book 46007447] [--qpage 28] [--apage 174]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live import LIVE, Live  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default="46007447")
    ap.add_argument("--qpage", type=int, default=28)
    ap.add_argument("--apage", type=int, default=174)
    args = ap.parse_args()

    stamp = datetime.now().strftime("%H%M%S")
    LIVE.mkdir(parents=True, exist_ok=True)
    with Live(headless=True) as lv:
        lv.start_image_watch()
        lv.open()
        print("[book]", json.dumps(lv.select_book(args.book), ensure_ascii=False))
        print("[canvases]", json.dumps(lv.canvases(), ensure_ascii=False))
        print("[inputs]", json.dumps(lv.inputs(), ensure_ascii=False, indent=1))

        q = lv.goto_page("q", args.qpage)
        print("[goto q]", json.dumps(q, ensure_ascii=False))
        a = lv.goto_page("a", args.apage)
        print("[goto a]", json.dumps(a, ensure_ascii=False))

        print("[state]", json.dumps(lv.read_state(), ensure_ascii=False))
        lv.shot_canvas("q", LIVE / f"q_{stamp}.png")
        lv.shot_canvas("a", LIVE / f"a_{stamp}.png")
        print(f"[shots] {LIVE / f'q_{stamp}.png'} , {LIVE / f'a_{stamp}.png'}")

        # 图片资源（源图线索）
        uniq = {}
        for im in lv.images:
            uniq[im["url"]] = im
        print(f"[images] {len(uniq)} 条")
        for u in list(uniq)[:25]:
            print("   ", u[:160])
        (LIVE / f"images_{stamp}.json").write_text(
            json.dumps(list(uniq.values()), ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
