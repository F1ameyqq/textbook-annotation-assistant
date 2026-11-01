"""Visible, human-operated login only; no programmatic credential access/fill."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from urllib.parse import urlsplit

from .core import LOGIN, LOGIN_POST, load_login_binding, owned_manual_login_context, write_new, utc


async def run(config, digest):
    binding = load_login_binding(config, digest)
    result = {"schema": "UsenseManualLoginResult/v1", "status": "NOT_STARTED", "config_sha256": digest,
              "credential_values_read": False, "credential_values_filled": False, "login_clicked_by_program": False,
              "save_attempts": 0, "login_http_status": None, "session_authenticated": "NOT_INDEPENDENTLY_VERIFIED"}
    owner = None
    try:
        async with owned_manual_login_context(binding) as owner:
            def response(response):
                if response.url == LOGIN_POST and response.request.method == "POST":
                    result["login_http_status"] = response.status
            owner.page.on("response", response)
            await owner.navigate()
            print(json.dumps({"status": "WAITING_FOR_USER_IN_VISIBLE_EDGE", "automatic_login": False}), flush=True)
            while datetime.now(timezone.utc) < utc(binding.data["expires_at"]):
                binding.check()
                if owner.page.is_closed():
                    result["status"] = "USER_CLOSED_PAGE"
                    break
                if owner.policy.blocked:
                    result["status"] = "LOGIN_GUARD_STOPPED_NO_RETRY"
                    break
                current = urlsplit(owner.page.url)
                password_present = await owner.page.locator('input[type="password"]:visible').count() > 0
                if (result["login_http_status"] == 200 and current.netloc == "www.usense.com" and
                        current.path.startswith("/qieti/") and current.path != "/qieti/login" and not password_present):
                    result["status"] = "LOGIN_HTTP200_NAVIGATION_OBSERVED"
                    break
                await asyncio.sleep(1)
            else:
                result["status"] = "LOGIN_WINDOW_EXPIRED_NO_RETRY"
    except BaseException as exc:
        result["status"] = "BLOCKED_OR_UNKNOWN_NO_RETRY"
        result["error"] = {"code": getattr(exc, "code", "RUNTIME_ERROR"), "type": type(exc).__name__}
    finally:
        if owner is not None:
            result["release"] = owner.release
        if binding.output.exists():
            write_new(binding.output/"manual-login-result.json", result)
    return result

