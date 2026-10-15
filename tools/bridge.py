#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebBridge 本地守护调用封装 (http://127.0.0.1:10086/command)

约束（来自交接包 + 实测）：
  * 每个请求体必须写成 UTF-8 JSON 临时文件，用 --data-binary @file 发送；
    内联中文/非 ASCII 会损坏；用完即删。
  * 请求体形状: {"action": "<tool>", "args": {...}, "session": "..."}
  * 不提取令牌、不记录账号密码；一切访问走浏览器会话。
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid

DEFAULT_ENDPOINT = "http://127.0.0.1:10086/command"
CURL = r"C:\Windows\system32\curl.exe"
SESSION = "标注平台探路"


class BridgeError(RuntimeError):
    pass


def call(action: str, args: dict | None = None, session: str = SESSION,
         endpoint: str = DEFAULT_ENDPOINT, timeout: int = 60) -> dict:
    """调用一次 WebBridge 工具，返回解析后的 JSON dict。"""
    body = {"action": action, "args": args or {}, "session": session}
    payload = json.dumps(body, ensure_ascii=False)

    fd, path = tempfile.mkstemp(prefix="webbridge-req-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        proc = subprocess.run(
            [CURL, "-s", "-S", "-m", str(timeout), "-X", "POST", endpoint,
             "--data-binary", "@" + path],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0:
            raise BridgeError(
                f"curl exit {proc.returncode}: {(proc.stderr or '').strip()[:400]}"
            )
        raw = (proc.stdout or "").strip()
        if not raw:
            raise BridgeError("empty response from WebBridge daemon")
        return json.loads(raw)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def list_tabs(session: str = SESSION) -> list[dict]:
    resp = call("list_tabs", {}, session=session)
    return (resp.get("data") or {}).get("tabs", [])


def find_tab(pattern: str = "usense.com", session: str = SESSION) -> dict:
    """在当前会话中按 URL/标题片段找标签页。"""
    for tab in list_tabs(session):
        hay = f"{tab.get('url', '')} {tab.get('title', '')}"
        if pattern in hay:
            return tab
    raise BridgeError(
        f"no tab matching {pattern!r} in session {session!r}; "
        f"tabs present: {[t.get('url') for t in list_tabs(session)]}"
    )


if __name__ == "__main__":
    import sys

    act = sys.argv[1] if len(sys.argv) > 1 else "list_tabs"
    a = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    print(json.dumps(call(act, a), ensure_ascii=False, indent=2))
