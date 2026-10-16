#!/usr/bin/env python
"""Read local credentials without echoing them; authenticate only to Usense.

The user explicitly authorized this local credential file and its use for login.
This utility does not select books, change annotations, or submit questions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".local" / "usense-login.json"
LOGIN_URL = "https://www.usense.com/qieti/login"
VIEWER_URL = "https://www.usense.com/qieti/annotateUnified"
VIEWER_MARKER = ".pdf-zones-container:visible"


class LoginError(Exception):
    """Messages must be fixed summaries, never raw browser/config exceptions."""


@dataclass(frozen=True)
class Credentials:
    username: str = field(repr=False)
    password: str = field(repr=False)


def load_credentials(path: Path = CONFIG) -> Credentials:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise LoginError("登录配置文件不存在。") from None
    except (OSError, UnicodeError, ValueError):
        raise LoginError("登录文件无法读取，请检查 JSON 格式和 UTF-8 编码。") from None
    if not isinstance(data, dict):
        raise LoginError("登录文件必须包含 username 和 password 两个文本字段。")
    username, password = data.get("username"), data.get("password")
    if not isinstance(username, str) or not username.strip():
        raise LoginError("账号尚未填写。")
    if not isinstance(password, str) or not password:
        raise LoginError("密码尚未填写。")
    # Preserve password whitespace and punctuation exactly as entered.
    return Credentials(username, password)


def trusted_url(url: str, *, login_only: bool = False) -> bool:
    try:
        parts = urlsplit(url)
        return (
            parts.scheme == "https"
            and parts.hostname == "www.usense.com"
            and parts.port in (None, 443)
            and parts.username is None
            and parts.password is None
            and (not login_only or parts.path == "/qieti/login")
        )
    except ValueError:
        return False


def require_login_origin(page) -> None:
    if not trusted_url(page.url, login_only=True):
        raise LoginError("当前页面不是已确认的 Usense 登录页，未填写凭证。")


def verify_viewer(page) -> bool:
    """A protected viewer marker is required; URL changes alone do not suffice."""
    if not trusted_url(page.url) or urlsplit(page.url).path != "/qieti/annotateUnified":
        return False
    return (
        not page.get_by_placeholder("请输入密码", exact=True).is_visible()
        and page.locator(VIEWER_MARKER).first.is_visible()
    )


def browser_failure(exc, stage: str, *, credentials_started: bool,
                    submission_attempted: bool) -> LoginError:
    """Only fixed summaries escape; browser exception text can contain secrets."""
    stages = {
        "launch": "启动专用浏览器",
        "open_viewer": "打开标注页",
        "open_login": "打开登录页",
        "fill": "填写登录信息",
        "submit": "提交登录",
        "verify": "确认标注页面",
    }
    # Match only during navigation, before credentials are passed to page methods.
    if stage in {"open_viewer", "open_login"} and not credentials_started:
        if "net::ERR_CERT_COMMON_NAME_INVALID" in str(exc):
            reason = "HTTPS 证书域名与目标站点不匹配。"
        elif "net::ERR_CERT_" in str(exc):
            reason = "HTTPS 证书校验失败。"
        else:
            reason = "页面连接或加载失败。"
    else:
        reason = "操作未完成或页面状态未确认。"
    if submission_attempted:
        state = "已尝试点击登录，提交结果需要核实；未自动重试。"
    elif credentials_started:
        state = "填写步骤已开始，尚未点击登录；未自动重试。"
    else:
        state = "账号密码尚未填写、尚未提交。"
    return LoginError(f"登录未确认（{stages.get(stage, '浏览器操作')}）：{reason}{state}")


def login(credentials: Credentials, *, headed: bool = False,
          ignore_https_errors: bool = False) -> str:
    # Prevent inherited Playwright diagnostics from printing fill() arguments.
    os.environ.pop("DEBUG", None)
    os.environ.pop("PWDEBUG", None)
    try:
        from playwright.sync_api import Error as BrowserError, sync_playwright
    except ImportError:
        raise LoginError("缺少 Playwright 依赖，请先配置运行环境。") from None

    # Separate browser state per account without using the account name in paths.
    account_key = hashlib.sha256(credentials.username.encode("utf-8")).hexdigest()[:20]
    profile = ROOT / ".local" / "browser-profiles" / account_key
    profile.mkdir(parents=True, exist_ok=True)
    stage = "launch"
    credentials_started = False
    submission_attempted = False
    try:
        with sync_playwright() as pw:
            context = pw.chromium.launch_persistent_context(
                str(profile), channel="msedge", headless=not headed,
                viewport={"width": 1440, "height": 1000},
                accept_downloads=False, timeout=30000,
                # Explicit per-run opt-in; no browser/system setting is changed.
                ignore_https_errors=ignore_https_errors,
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.set_default_timeout(15000)
                stage = "open_viewer"
                page.goto(VIEWER_URL, wait_until="domcontentloaded", timeout=45000)
                # SPA rendering may finish after DOMContentLoaded. Wait for either
                # the known viewer or the login form before deciding about reuse.
                page.locator(
                    VIEWER_MARKER + ', input[placeholder="请输入密码"]:visible'
                ).first.wait_for(state="visible", timeout=20000)
                if verify_viewer(page):
                    return "已复用登录状态，并读取到受保护的标注页面。"

                stage = "open_login"
                page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45000)
                require_login_origin(page)
                stage = "fill"
                credentials_started = True
                page.get_by_placeholder("请输入用户名", exact=True).fill(credentials.username)
                require_login_origin(page)
                page.get_by_placeholder("请输入密码", exact=True).fill(credentials.password)
                require_login_origin(page)
                stage = "submit"
                submission_attempted = True
                page.get_by_role("button", name="登录", exact=True).click()
                # Exactly one submission. CAPTCHA/rejection/timeout never retries.
                page.wait_for_url(
                    lambda url: trusted_url(str(url))
                    and urlsplit(str(url)).path != "/qieti/login",
                    timeout=30000,
                )
                stage = "verify"
                page.goto(VIEWER_URL, wait_until="domcontentloaded", timeout=45000)
                page.locator(VIEWER_MARKER).first.wait_for(state="visible", timeout=20000)
                if not verify_viewer(page):
                    raise LoginError("登录结果未确认，需要检查平台页面或额外验证。")
                return "登录成功，并读取到受保护的标注页面。"
            finally:
                context.close()
    except BrowserError as exc:
        raise browser_failure(
            exc, stage, credentials_started=credentials_started,
            submission_attempted=submission_attempted,
        ) from None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="使用本地配置登录 Usense，不回显账号密码。")
    parser.add_argument("--check", action="store_true", help="仅检查配置，不打开浏览器")
    parser.add_argument("--headed", action="store_true", help="使用专用可见窗口进行一次登录")
    parser.add_argument(
        "--ignore-https-errors", action="store_true",
        help="仅本次专用浏览器忽略 HTTPS 证书错误（需用户明确授权）",
    )
    args = parser.parse_args(argv)
    try:
        credentials = load_credentials()
        if args.check:
            print("账号和密码均已填写；内容未显示。")
        else:
            print(login(credentials, headed=args.headed,
                        ignore_https_errors=args.ignore_https_errors))
        return 0
    except LoginError as exc:
        print(str(exc))
        return 2
    except Exception:
        print("登录准备失败，未输出配置内容；需要检查本机运行环境。")
        return 3


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
