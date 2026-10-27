#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/probe_login.py — 诊断 usense 登录态是否真的可用（只读，不写平台）

做三件事：
1. 用工作区 profile 启动 Edge（headless）
2. 读 localStorage.user，看有没有 access_token
3. 带 Bearer 请求一个只读 API，报告状态码 / 是否被重定向

不调用任何写接口，不保存任何东西。
"""
from __future__ import annotations

import json
import sys
from playwright.sync_api import sync_playwright

PROFILE = sys.argv[1] if len(sys.argv) > 1 else None
PROXY = sys.argv[2] if len(sys.argv) > 2 else None
TARGET = "https://www.usense.com/qieti/annotateUnified"
API = "/qieti/api/annotate_ocr/directory/get?file_id=46007447"

READ_LOCAL = """() => {
  const raw = localStorage.getItem('user');
  let obj = null;
  try { obj = raw ? JSON.parse(raw) : null; } catch (e) { obj = null; }
  return {
    url: location.href,
    hasUser: !!raw,
    userKeys: obj ? Object.keys(obj) : [],
    tokenLen: (obj && typeof obj.access_token === 'string') ? obj.access_token.length : 0,
    tokenHead: (obj && typeof obj.access_token === 'string') ? obj.access_token.slice(0, 12) : null,
    cookieNames: document.cookie ? document.cookie.split(';').map(s => s.trim().split('=')[0]) : []
  };
}"""

PROBE_FETCH = """async (path) => {
  const raw = localStorage.getItem('user');
  if (!raw) return {error: 'NO_LOCALSTORAGE_USER'};
  let u; try { u = JSON.parse(raw); } catch (e) { return {error: 'BAD_JSON'}; }
  if (!u || !u.access_token) return {error: 'NO_ACCESS_TOKEN'};
  const out = {};
  try {
    const r = await fetch(path, {method: 'GET', redirect: 'follow',
      headers: {Authorization: 'Bearer ' + u.access_token, Accept: 'application/json'}});
    const text = await r.text();
    out.follow = {status: r.status, redirected: r.redirected, finalUrl: r.url, bodyHead: text.slice(0, 200)};
  } catch (e) { out.follow = {error: String(e)}; }
  try {
    const r2 = await fetch(path, {method: 'GET', redirect: 'manual',
      headers: {Authorization: 'Bearer ' + u.access_token, Accept: 'application/json'}});
    out.manual = {status: r2.status, type: r2.type};
  } catch (e) { out.manual = {error: String(e)}; }
  return out;
}"""


def main() -> int:
    if not PROFILE:
        print("用法: probe_login.py <profile-dir> [proxy-url]")
        return 2
    launch = {"channel": "msedge", "headless": True, "ignore_https_errors": True}
    if PROXY:
        launch["proxy"] = {"server": PROXY}
        print(f"代理: {PROXY}")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFILE, **launch)
        try:
            page = ctx.pages[0]
            page.goto(TARGET, wait_until="load", timeout=45000)
            page.wait_for_timeout(2500)  # SPA 路由二次导航后再读，避免 context destroyed
            info = page.evaluate(READ_LOCAL)
            print("=== localStorage / cookie ===")
            print(json.dumps(info, ensure_ascii=False, indent=2))
            print()
            print("=== 带 Bearer 请求只读 API ===")
            try:
                res = page.evaluate(PROBE_FETCH, API)
            except Exception as e:
                # 导航尚未稳定时重试一次
                page.wait_for_timeout(3000)
                res = page.evaluate(PROBE_FETCH, API)
            print(json.dumps(res, ensure_ascii=False, indent=2))
        finally:
            ctx.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
