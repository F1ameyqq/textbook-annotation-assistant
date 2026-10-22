"""Book 46007447 portable read-only runtime. Configuration is a binding, never a save authority.

Import and doctor perform no browser acquisition. The explicit open API requires
a fresh, hash-bound configuration. Read-only contexts cannot POST; manual login has a separate visible mode.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import socket
import ssl
import sys
import tempfile
from urllib.parse import parse_qsl, urlsplit

SCHEMA = "UsenseLiveReadConfig/v1"
TARGET = "https://www.usense.com/qieti/annotateUnified"
ORIGIN = "https://www.usense.com"
LOGIN = ORIGIN + "/qieti/login"
LOGIN_POST = ORIGIN + "/qieti/api/user_login/login"
APPROVED_CERT_DER = "52d8642145282846969a29b97c5c3aaae4c0203c4a6bc06906478f13445e3941"
APPROVED_SPKI = "Wlnek+vSltKGp2xIsXuyk4SecrEEbf38ppvOnLuzz7A="
KINDS = {"document", "script", "stylesheet", "image", "font", "xhr", "fetch", "other"}
LOCKS = ("SingletonLock", "SingletonCookie", "lockfile")


class BindingError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(value, code):
    if not value:
        raise BindingError(code)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()


def implementation_digest():
    """Bind every Python file in this installed package, not machine paths."""
    root = Path(__file__).resolve().parent
    members = [{"path": p.name, "sha256": sha(p.read_bytes())}
               for p in sorted(root.glob("*.py"))]
    return sha(canonical(members))


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: require(False, "NONFINITE_JSON"))


def utc(value):
    require(isinstance(value, str) and re.fullmatch(
        r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)", value), "UTC_WINDOW_REQUIRED")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def plain_path(value, *, must_exist=True):
    require(isinstance(value, str) and value.strip() == value and value, "ABSOLUTE_PATH_REQUIRED")
    path = Path(value)
    require(path.is_absolute() and ".." not in path.parts and path != Path(path.anchor),
            "SCOPED_ABSOLUTE_PATH_REQUIRED")
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            require(not item.is_symlink() and not (getattr(info, "st_file_attributes", 0) & 0x400),
                    "REPARSE_PATH_REJECTED")
    require(not must_exist or path.exists(), "PATH_MISSING")
    return path.resolve()


def profile_identity(directory):
    """Read directory metadata only: never enumerate/read any profile file."""
    path = plain_path(directory)
    require(path.is_dir(), "PROFILE_DIRECTORY_REQUIRED")
    require(path.name.lower() not in ("default", "user data", "guest profile") and
            not re.fullmatch(r"profile \d+", path.name.lower()), "DEDICATED_PROFILE_REQUIRED")
    info = path.stat()
    require(info.st_ino > 0, "PROFILE_IDENTITY_UNAVAILABLE")
    identity = {"schema": "UsenseProfileDirectoryIdentity/v1", "path": os.path.normcase(str(path)),
                "device": info.st_dev, "inode": info.st_ino}
    return path, sha(canonical(identity))


@dataclass(frozen=True)
class LocalBinding:
    path: Path
    raw_sha256: str
    data: dict
    data_sha256: str

    @property
    def output(self):
        return Path(self.data["output_root"]) / self.data["run_id"]

    def check(self, *, now=None, profile=False):
        require(sha(self.path.read_bytes()) == self.raw_sha256, "CONFIG_CHANGED")
        require(sha(canonical(self.data)) == self.data_sha256, "CONFIG_IN_MEMORY_CHANGED")
        require(implementation_digest() == self.data["implementation_sha256"], "IMPLEMENTATION_CHANGED")
        current = now or datetime.now(timezone.utc)
        require(current.tzinfo is not None and utc(self.data["not_before"]) <= current < utc(self.data["expires_at"]),
                "WINDOW_EXPIRED_OR_NOT_STARTED")
        plain_path(self.data["output_root"])
        if profile:
            path, fingerprint = profile_identity(self.data["profile"]["directory"])
            require(fingerprint == self.data["profile"]["fingerprint"], "PROFILE_IDENTITY_CHANGED")
            require(not any((path / name).exists() for name in LOCKS), "PROFILE_LOCK_PRESENT")
        return self


def load_binding(path, expected_sha256, *, now=None):
    return _load_binding(path, expected_sha256, now=now, manual_login=False)


def load_login_binding(path, expected_sha256, *, now=None):
    return _load_binding(path, expected_sha256, now=now, manual_login=True)


def _load_binding(path, expected_sha256, *, now=None, manual_login=False):
    require(isinstance(expected_sha256, str) and re.fullmatch("[0-9a-f]{64}", expected_sha256), "CONFIG_DIGEST_REQUIRED")
    file = plain_path(str(path))
    raw = file.read_bytes()
    require(sha(raw) == expected_sha256, "CONFIG_DIGEST_MISMATCH")
    data = parse(raw)
    require(isinstance(data, dict) and set(data) == {
        "schema", "book_id", "operation", "run_id", "actors", "target_url", "profile", "output_root",
        "not_before", "expires_at", "headless", "allowed_get", "static_get", "tls", "implementation_sha256", "authorization_reference"},
        "CONFIG_FIELDS")
    expected_schema = "UsenseLiveManualLoginConfig/v1" if manual_login else SCHEMA
    expected_operation = "MANUAL_LOGIN_ONLY" if manual_login else "READONLY_CAPTURE"
    expected_target = LOGIN if manual_login else TARGET
    require(data["schema"] == expected_schema and data["book_id"] == "46007447" and
            data["operation"] == expected_operation and data["target_url"] == expected_target,
            "USENSE_READONLY_SCOPE_REQUIRED")
    run_pattern = r"usense-login-[a-z0-9-]{1,64}" if manual_login else r"usense-readonly-[a-z0-9-]{1,64}"
    require(isinstance(data["run_id"], str) and re.fullmatch(run_pattern, data["run_id"]), "FRESH_RUN_ID_REQUIRED")
    require(type(data["headless"]) is bool, "HEADLESS_BOOLEAN_REQUIRED")
    require(not manual_login or data["headless"] is False, "LOGIN_REQUIRES_VISIBLE_BROWSER")
    require(isinstance(data["authorization_reference"], str) and 1 <= len(data["authorization_reference"]) <= 512,
            "CURRENT_USER_INTENT_REFERENCE_REQUIRED")
    actors = data["actors"]
    require(isinstance(actors, dict) and set(actors) == {"coordinator", "executor", "reviewer"} and
            all(isinstance(v, str) and re.fullmatch(r"[a-zA-Z0-9_:/.-]{3,160}", v) for v in actors.values()) and
            actors["executor"] != actors["reviewer"], "CURRENT_ACTORS_REQUIRED")
    start, end = utc(data["not_before"]), utc(data["expires_at"])
    require(0 < (end-start).total_seconds() <= 900, "BOUNDED_WINDOW_REQUIRED")
    output = plain_path(data["output_root"])
    require(output.is_dir(), "OUTPUT_ROOT_REQUIRED")
    profile = data["profile"]
    require(isinstance(profile, dict) and set(profile) == {"directory", "fingerprint", "usage"} and
            profile["usage"] == "DEDICATED_PROJECT" and isinstance(profile["fingerprint"], str) and
            re.fullmatch("[0-9a-f]{64}", profile["fingerprint"]), "EXPLICIT_PROFILE_BINDING_REQUIRED")
    profile_path = plain_path(profile["directory"])
    require(output != profile_path and output not in profile_path.parents and profile_path not in output.parents,
            "PROFILE_OUTPUT_SEPARATION_REQUIRED")
    rows = data["allowed_get"]
    require(isinstance(rows, list) and 1 <= len(rows) <= 64, "EXACT_GET_ALLOWLIST_REQUIRED")
    seen = set()
    for row in rows:
        require(isinstance(row, dict) and set(row) == {"url", "resource_types", "max_requests"}, "GET_RULE_FIELDS")
        url = row["url"]
        require(isinstance(url, str) and len(url) <= 4096, "GET_URL_REQUIRED")
        parsed = urlsplit(url)
        require(parsed.scheme == "https" and parsed.netloc == "www.usense.com" and
                not parsed.username and not parsed.password and not parsed.fragment and
                not any(ord(c) < 32 for c in url) and url not in seen, "EXACT_SAME_ORIGIN_URL_REQUIRED")
        seen.add(url)
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
        require(not any(re.search("token|password|secret|authorization|cookie", key, re.I) for key, _ in pairs),
                "CREDENTIAL_QUERY_REJECTED")
        require(type(row["max_requests"]) is int and 1 <= row["max_requests"] <= 4 and
                isinstance(row["resource_types"], list) and row["resource_types"] and
                len(set(row["resource_types"])) == len(row["resource_types"]) and
                set(row["resource_types"]) <= KINDS, "GET_RULE_LIMIT_REQUIRED")
        # Any business read must contain the fixed book id. Session metadata is
        # limited to the same three reads used by the current product.
        if "/api/" in parsed.path:
            session = parsed.path in {"/qieti/api/user_login/profile", "/qieti/api/user_login/config/permissions",
                                      "/qieti/api/user_login/config/teams"}
            book_fields = [value for key, value in pairs if key in ("file_id", "book_id", "id")]
            book_path = re.search(r"(?:^|/)46007447(?:/|$)", parsed.path) is not None
            require((session and not parsed.query) or
                    ((book_path or "46007447" in book_fields) and all(value == "46007447" for value in book_fields)),
                    "BOOK_BOUND_READ_REQUIRED")
    require(expected_target in seen and next(r for r in rows if r["url"] == expected_target)["resource_types"] == ["document"],
            "TARGET_NAVIGATION_RULE_REQUIRED")
    static = data["static_get"]
    require(isinstance(static, dict) and set(static) == {"mode", "max_requests"} and
            static["mode"] in ("DISABLED", "SAME_ORIGIN_ASSETS") and type(static["max_requests"]) is int and
            0 <= static["max_requests"] <= 64 and (static["mode"] != "DISABLED" or static["max_requests"] == 0),
            "BOUNDED_STATIC_POLICY_REQUIRED")
    tls = data["tls"]
    require(tls == {"mode": "STRICT"} or (isinstance(tls, dict) and set(tls) == {
        "mode", "origin", "leaf_der_sha256", "spki_sha256_base64", "approval_reference"} and
        tls["mode"] == "USER_APPROVED_EXACT_CERT" and tls["origin"] == ORIGIN and
        tls["leaf_der_sha256"] == APPROVED_CERT_DER and tls["spki_sha256_base64"] == APPROVED_SPKI and
        isinstance(tls["approval_reference"], str) and bool(tls["approval_reference"])), "TLS_SCOPE_REQUIRED")
    binding = LocalBinding(file, expected_sha256, copy.deepcopy(data), sha(canonical(data)))
    return binding.check(now=now)


def write_new(path, value):
    with path.open("xb") as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())


class ReadonlyPolicy:
    def __init__(self, binding):
        self.binding = binding
        self.rules = {r["url"]: r for r in binding.data["allowed_get"]}
        self.counts = {}
        self.events = []
        self.blocked = False
        self.static_counts = {}

    def static_allowed(self, layer, url, kind):
        config = self.binding.data["static_get"]
        if config["mode"] != "SAME_ORIGIN_ASSETS":
            return False
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.netloc != "www.usense.com" or parsed.query or parsed.fragment or
                any(v in parsed.path for v in ("%", "\\", "..", "/api/")) or not re.fullmatch(
                    r"/(?:qieti/)?(?:assets|static)/[^?]+\.(?:js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|webp)", parsed.path)):
            return False
        extension = parsed.path.rsplit(".", 1)[-1]
        expected = "script" if extension == "js" else "stylesheet" if extension == "css" else (
            "font" if extension in ("woff", "woff2", "ttf") else "image")
        if kind.lower() not in (expected, "other"):
            return False
        self.static_counts[layer] = self.static_counts.get(layer, 0) + 1
        return self.static_counts[layer] <= config["max_requests"]

    def decide(self, layer, method, url, kind, *, redirected=False):
        try:
            self.binding.check()
            rule = self.rules.get(url)
            document_redirect = (kind.lower() == "document" and rule is not None and
                                 urlsplit(url).path.startswith("/qieti/") and "/api/" not in urlsplit(url).path)
            allowed = (not self.blocked and method == "GET" and (not redirected or document_redirect) and
                       ((rule is not None and kind.lower() in rule["resource_types"]) or
                        (not redirected and self.static_allowed(layer, url, kind))))
            key = (layer, url)
            if allowed:
                self.counts[key] = self.counts.get(key, 0) + 1
                allowed = self.counts[key] <= (rule["max_requests"] if rule is not None else 1)
        except Exception:
            allowed = False
        if not allowed:
            self.blocked = True
        if len(self.events) < 256:
            self.events.append({"layer": layer, "method": method if method in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS") else "OTHER",
                                "url_sha256": sha(url.encode()), "kind": kind.lower() if kind.lower() in KINDS else "other",
                                "allowed": allowed, "redirected": bool(redirected)})
        return allowed


class ManualLoginPolicy(ReadonlyPolicy):
    """One user-operated login POST, no business writes or automatic submission."""
    def __init__(self, binding):
        super().__init__(binding)
        self.login_armed = False
        self.login_counts = {}

    def decide(self, layer, method, url, kind, *, redirected=False):
        if method == "POST" and url == LOGIN_POST:
            try:
                self.binding.check()
                self.login_counts[layer] = self.login_counts.get(layer, 0) + 1
                allowed = (self.login_armed and not self.blocked and not redirected and
                           kind.lower() in ("xhr", "fetch") and self.login_counts[layer] == 1)
            except Exception:
                allowed = False
            if not allowed:
                self.blocked = True
            self.events.append({"layer": layer, "method": "POST", "url_sha256": sha(url.encode()),
                                "kind": kind.lower(), "allowed": allowed, "body_read": False})
            return allowed
        # Login may redirect to its same-origin landing page. No business API
        # may ride this document rule, and all request bodies remain untouched.
        p = urlsplit(url)
        if (method == "GET" and kind.lower() == "document" and p.scheme == "https" and
                p.netloc == "www.usense.com" and p.path.startswith("/qieti/") and "/api/" not in p.path and
                not p.query and not p.fragment and not any(c in p.path for c in ("%", "\\", ".."))):
            if url not in self.rules:
                self.rules[url] = {"resource_types": ["document"], "max_requests": 1}
        before = self.blocked
        allowed = super().decide(layer, method, url, kind, redirected=redirected)
        if not allowed and not before and method == "GET":
            # A known login page can issue unrelated books reads or optional CDN
            # resources. Deny them, without making the user's login impossible.
            # They are never forwarded and never granted to the readonly mode.
            self.blocked = False
        return allowed


def tls_launch_arguments(binding):
    """Exact leaf checked before HTTP, public-key pin then enforced by Chromium."""
    setting = binding.data["tls"]
    if setting["mode"] == "STRICT":
        return []
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with socket.create_connection(("www.usense.com", 443), timeout=10) as sock:
        with context.wrap_socket(sock, server_hostname="www.usense.com") as secure:
            cert = secure.getpeercert(binary_form=True)
    require(sha(cert) == setting["leaf_der_sha256"], "APPROVED_CERTIFICATE_CHANGED")
    return ["--ignore-certificate-errors-spki-list=" + setting["spki_sha256_base64"]]


class OwnedReadonlyContext:
    """One fresh persistent context; caller owns its supervised Python process.

This class closes context/runtime and settles callbacks. It deliberately does
not certify Windows process/Job release; an outer process holder must do that.
No token/cookie/profile contents are read or returned by this module.
"""
    operation = "READONLY_CAPTURE"
    policy_class = ReadonlyPolicy

    def __init__(self, binding):
        require(type(binding) is LocalBinding, "VALIDATED_BINDING_REQUIRED")
        require(binding.data["operation"] == self.operation, "CONTEXT_MODE_MISMATCH")
        self.binding = binding
        self.policy = self.policy_class(binding)
        self.runtime = self.context = self.page = self.cdp = None
        self.pending = set()
        self.closed = False
        self.release = None

    def schedule(self, awaitable):
        task = asyncio.create_task(awaitable)
        self.pending.add(task)
        def done(value):
            self.pending.discard(value)
            if not value.cancelled() and value.exception() is not None:
                self.policy.blocked = True
        task.add_done_callback(done)

    async def route(self, route):
        req = route.request
        if self.policy.decide("context", req.method, req.url, req.resource_type,
                              redirected=req.redirected_from is not None):
            await route.continue_()
        else:
            await route.abort("blockedbyclient")

    async def paused(self, event):
        req = event.get("request", {})
        if self.policy.decide("native", req.get("method", ""), req.get("url", ""),
                              event.get("resourceType", "other"), redirected=bool(event.get("redirectedRequestId"))):
            await self.cdp.send("Fetch.continueRequest", {"requestId": event["requestId"]})
        else:
            await self.cdp.send("Fetch.failRequest", {"requestId": event["requestId"], "errorReason": "BlockedByClient"})

    async def deny_websocket(self, ws):
        self.policy.blocked = True
        await ws.close(code=1008, reason="Read-only scope")

    async def close_extra(self, page):
        self.policy.blocked = True
        await page.close()

    async def __aenter__(self):
        self.binding.check(profile=True)
        require(os.name == "nt", "WINDOWS_REQUIRED")
        # Fail before creating a run marker if the required library is absent.
        from playwright.async_api import async_playwright
        self.binding.output.mkdir(exist_ok=False)
        write_new(self.binding.output / "claim.json", {"schema": "UsenseReadonlyClaim/v1",
            "config_sha256": self.binding.raw_sha256, "run_id": self.binding.data["run_id"],
            "operation": self.operation, "automatic_retry_allowed": False})
        try:
            tls_args = await asyncio.to_thread(tls_launch_arguments, self.binding)
            self.runtime = await async_playwright().start()
            self.context = await self.runtime.chromium.launch_persistent_context(
                self.binding.data["profile"]["directory"], channel="msedge", headless=self.binding.data["headless"],
                offline=True, service_workers="block", ignore_https_errors=False, accept_downloads=False,
                viewport={"width": 1440, "height": 1000}, timeout=15000,
                args=["--disable-session-crashed-bubble", "--disable-extensions", "--disable-background-networking"] + tls_args)
            # Edge may restore its own welcome/previous tab for this dedicated
            # project profile. Normalize while the entire context is still
            # offline, before installing the guards and enabling networking.
            if not self.context.pages:
                await self.context.new_page()
            for extra in list(self.context.pages[1:]):
                await extra.close()
            if self.context.pages[0].url != "about:blank":
                await self.context.pages[0].goto("about:blank", wait_until="domcontentloaded")
            require(len(self.context.pages) == 1 and self.context.pages[0].url == "about:blank", "FRESH_BLANK_CONTEXT_REQUIRED")
            self.page = self.context.pages[0]
            self.context.on("page", lambda page: self.schedule(self.close_extra(page)))
            self.page.on("dialog", lambda dialog: self.schedule(dialog.dismiss()))
            await self.context.route("**/*", self.route)
            await self.context.route_web_socket("**/*", self.deny_websocket)
            self.cdp = await self.context.new_cdp_session(self.page)
            self.cdp.on("Fetch.requestPaused", lambda event: self.schedule(self.paused(event)))
            await self.cdp.send("Fetch.enable", {"patterns": [{"urlPattern": "*", "requestStage": "Request"}]})
            self.binding.check(profile=False)
            await self.context.set_offline(False)
            return self
        except BaseException:
            await self.close()
            raise

    async def navigate(self):
        self.binding.check()
        require(not self.policy.blocked, "READONLY_GUARD_STOPPED")
        response = await self.page.goto(self.binding.data["target_url"], wait_until="domcontentloaded", timeout=45000)
        require(not self.policy.blocked, "READONLY_GUARD_STOPPED")
        return response

    async def close(self):
        if self.closed:
            return self.release
        self.closed = True
        self.policy.blocked = True
        result = {"schema": "UsenseReadonlyRelease/v1", "config_sha256": self.binding.raw_sha256,
                  "context_closed": self.context is None, "runtime_stopped": self.runtime is None,
                  "pending_callbacks": None, "errors": [], "os_process_release": "REQUIRES_OUTER_HOLDER",
                  "save_attempts": 0, "login_requests_per_layer": getattr(self.policy, "login_counts", {}),
                  "automatic_login_performed": False, "automatic_retry_allowed": False}
        if self.context is not None:
            try:
                await asyncio.wait_for(self.context.close(), 15)
                result["context_closed"] = True
            except BaseException as exc:
                result["errors"].append({"phase": "context_close", "type": type(exc).__name__})
        if self.pending:
            pending = list(self.pending)
            for task in pending:
                task.cancel()
            try:
                await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), 5)
            except BaseException as exc:
                result["errors"].append({"phase": "callbacks", "type": type(exc).__name__})
        result["pending_callbacks"] = len(self.pending)
        if self.runtime is not None:
            try:
                await asyncio.wait_for(self.runtime.stop(), 15)
                result["runtime_stopped"] = True
            except BaseException as exc:
                result["errors"].append({"phase": "runtime_stop", "type": type(exc).__name__})
        result["context_runtime_release_confirmed"] = bool(result["context_closed"] and
            result["runtime_stopped"] and result["pending_callbacks"] == 0 and not result["errors"])
        self.release = result
        if self.binding.output.exists():
            write_new(self.binding.output / "network-events.json", self.policy.events)
            write_new(self.binding.output / "release.json", result)
        return result

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
        require(self.release["context_runtime_release_confirmed"], "CONTEXT_RUNTIME_RELEASE_UNPROVEN")
        return False


def owned_readonly_context(binding):
    return OwnedReadonlyContext(binding)


class OwnedManualLoginContext(OwnedReadonlyContext):
    operation = "MANUAL_LOGIN_ONLY"
    policy_class = ManualLoginPolicy

    async def navigate(self):
        response = await super().navigate()
        # Arm only after initial navigation and certificate-pinned startup.
        self.policy.login_armed = True
        return response


def owned_manual_login_context(binding):
    return OwnedManualLoginContext(binding)


def doctor(config=None, digest=None):
    packages = {}
    for name in ("playwright", "pydantic", "Pillow"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    result = {"schema": "UsenseRuntimeDoctor/v1", "python": sys.version.split()[0], "windows": os.name == "nt",
              "packages": packages, "implementation_sha256": implementation_digest(),
              "configuration_valid": False, "browser_started": False, "platform_ready": False,
              "save_implemented": False, "missing": []}
    if packages["playwright"] is None:
        result["missing"].append("PYTHON_PLAYWRIGHT")
    if config is None:
        result["missing"].append("EXPLICIT_FRESH_USENSE_CONFIG")
    else:
        try:
            load_binding(config, digest).check(profile=True)
            result["configuration_valid"] = True
        except Exception as exc:
            result["missing"].append(getattr(exc, "code", "CONFIG_UNREADABLE"))
    return result


def freeze(draft, output):
    """Seal an explicit draft. Only code hash and directory fingerprint are filled.

    Actors, operation, time window, allowlist and authorization reference must be
    supplied by the caller. This function grants no permissions or save power.
    """
    data = parse(Path(draft).read_bytes())
    data["implementation_sha256"] = implementation_digest()
    _, data["profile"]["fingerprint"] = profile_identity(data["profile"]["directory"])
    out = plain_path(str(output), must_exist=False)
    require(out.parent.is_dir() and not out.exists(), "NEW_CONFIG_OUTPUT_REQUIRED")
    raw = canonical(data)
    with tempfile.NamedTemporaryFile(dir=out.parent, suffix=".config-check.json", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(raw)
    try:
        loader = load_login_binding if data.get("schema") == "UsenseLiveManualLoginConfig/v1" else load_binding
        loader(temporary, sha(raw)).check(profile=True)
        with out.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        temporary.unlink()
    return {"schema": "UsenseConfigFrozen/v1", "sha256": sha(raw), "bytes": len(raw),
            "configuration_valid": True, "platform_ready": False, "save_authority_created": False}

