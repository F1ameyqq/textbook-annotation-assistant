#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/login_assist.py — 人工登录辅助（方案一）

用工作区 profile 开一个带界面的 Edge 窗口，停在 usense 登录页。
用户手动登录后，本脚本轮询 localStorage，检测到 access_token 即确认成功并关窗。
登录态由 Edge 自己写回 profile，后续所有无人值守脚本复用。

安全：只报告 token 是否存在与长度，绝不打印 token 本体（SOP §8 口径）。

用法：
    bin/venv311/Scripts/python.exe -X utf8 bin/login_assist.py [profile-dir]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROFILE = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "bin" / "browser-profiles" / "work-default")
TARGET = "https://www.usense.com/qieti/annotateUnified"
TIMEOUT_S = 15 * 60  # 等人登录最多 15 分钟

READ_TOKEN = """() => {
  const raw = localStorage.getItem('user');
  if (!raw) return {hasUser: false};
  try {
    const u = JSON.parse(raw);
    return {hasUser: true, hasToken: !!(u && u.access_token),
            tokenLen: u && u.access_token ? u.access_token.length : 0,
            url: location.href};
  } catch (e) { return {hasUser: true, hasToken: false, parseError: true}; }
}"""


def main() -> int:
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, channel="msedge", headless=False, ignore_https_errors=True,
            args=["--start-maximized"],
        )
        try:
            page = ctx.pages[0]
            page.goto(TARGET, wait_until="domcontentloaded", timeout=45000)
            print("[login-assist] 窗口已打开，请在 Edge 里完成登录（含可能的证书确认）。")
            print("[login-assist] 检测到 access_token 后会自动确认并关窗，最多等 15 分钟。", flush=True)

            deadline = time.time() + TIMEOUT_S
            while time.time() < deadline:
                time.sleep(3)
                try:
                    info = page.evaluate(READ_TOKEN)
                except Exception:
                    continue  # 导航中，下轮再读
                if info.get("hasToken"):
                    print("[login-assist] 登录成功："
                          + json.dumps(info, ensure_ascii=False), flush=True)
                    page.wait_for_timeout(1500)  # 让 SPA 把状态写稳
                    return 0
            print("[login-assist] 超时：15 分钟内未检测到 access_token。", flush=True)
            return 1
        finally:
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
