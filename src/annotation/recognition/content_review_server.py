"""Loopback-only UI adapter over the source-bound offline review workspace."""
from __future__ import annotations

from collections import Counter
import copy
import errno
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import parse_qs, urlsplit

from .formula_syntax import parse_inline_formula_latex

MAX_REQUEST_BYTES = 2 * 1024 * 1024
STATIC = {"/": ("review_ui.html", "text/html; charset=utf-8"),
          "/review.js": ("review_ui.js", "text/javascript; charset=utf-8"),
          "/review.css": ("review_ui.css", "text/css; charset=utf-8")}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def _finite(value):
    raise ValueError("nonfinite JSON value: " + value)


def _state(workspace, token):
    value = copy.deepcopy(workspace.state())
    value["csrf_token"] = token
    for answer in value["answers"]:
        for block in answer["blocks"]:
            for run in block["runs"]:
                if run["format"] == "latex":
                    run["math_preview"] = parse_inline_formula_latex(run["text"])
    return value


def make_server(workspace, *, host="127.0.0.1", port=0):
    """No website session, remote listener, platform action or model permission."""
    if host != "127.0.0.1":
        raise ValueError("offline review binds only to 127.0.0.1")
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("review port must be 0..65535")

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *args):
            pass

        def _send(self, status, data, mime="application/json; charset=utf-8", *, attachment=None):
            if isinstance(data, dict):
                data = (json.dumps(data, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            if attachment:
                self.send_header("Content-Disposition", 'attachment; filename="' + attachment + '"')
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _error(self, status, code, message):
            self._send(status, {"ok": False, "error": {"code": code, "message": str(message)[:800]}})

        def _origin(self, mutation=False):
            def reject(code, message):
                # Closing with an unread POST body can reset the TCP connection
                # on Windows before the browser receives the rejection.
                lengths = self.headers.get_all("Content-Length", [])
                if mutation and len(lengths) == 1 and lengths[0].isascii() and lengths[0].isdigit():
                    count = int(lengths[0])
                    if 0 < count <= MAX_REQUEST_BYTES and self.headers.get("Transfer-Encoding") is None:
                        old_timeout = self.connection.gettimeout()
                        try:
                            self.connection.settimeout(3)
                            self.rfile.read(count)
                        except OSError:
                            pass
                        finally:
                            self.connection.settimeout(old_timeout)
                self._error(403, code, message)
                return False

            actual_port = self.server.server_address[1]
            hosts = {"127.0.0.1:" + str(actual_port), "localhost:" + str(actual_port)}
            if self.headers.get("Host") not in hosts:
                return reject("HOST_REJECTED", "只接受本机复核页面的请求。")
            origin = self.headers.get("Origin")
            if origin is not None and origin not in {"http://" + h for h in hosts}:
                return reject("ORIGIN_REJECTED", "请求来源与本机复核页面不同。")
            token = self.headers.get("X-Review-Token", "")
            if mutation and (not token.isascii() or not secrets.compare_digest(token, self.server.review_token)):
                return reject("TOKEN_REJECTED", "页面已过期，请重新加载本地复核页面。")
            return True

        def _failure(self, exc):
            from .content_review import ReviewConflict, SourceChanged
            if isinstance(exc, ReviewConflict):
                self._error(409, "STALE_HEAD", str(exc))
            elif isinstance(exc, SourceChanged):
                self._error(409, "SOURCE_CHANGED", str(exc))
            elif isinstance(exc, (ValueError, KeyError, TypeError, FileNotFoundError)):
                self._error(400, "INVALID_REVIEW", str(exc))
            else:
                self._error(500, "REVIEW_FAILED", "本地复核未完成，请检查启动终端及保留的工作记录。")
                import traceback
                traceback.print_exc()

        def do_GET(self):
            if not self._origin():
                return
            parsed = urlsplit(self.path)
            self.server.request_counts["GET " + parsed.path] += 1
            try:
                if parsed.path in STATIC and not parsed.query:
                    name, mime = STATIC[parsed.path]
                    self._send(200, Path(__file__).with_name(name).read_bytes(), mime)
                elif parsed.path == "/api/state" and not parsed.query:
                    self._send(200, _state(workspace, self.server.review_token))
                elif parsed.path == "/api/export/plan" and not parsed.query:
                    plan = workspace.documents()["plan"]
                    encoded = (json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
                    self._send(200, encoded, attachment="content-review-plan.json")
                elif parsed.path == "/api/source":
                    values = parse_qs(parsed.query, keep_blank_values=True)
                    if set(values) - {"asset_id", "bbox"} or len(values.get("asset_id", [])) != 1 or any(len(v) != 1 for v in values.values()):
                        raise ValueError("source request requires one exact asset_id and optional bbox")
                    bbox = None
                    if "bbox" in values:
                        raw = values["bbox"][0].split(",")
                        if len(raw) != 4 or any(not v.isascii() or not v.isdigit() for v in raw):
                            raise ValueError("source bbox must be four nonnegative pixel integers")
                        bbox = [int(v) for v in raw]
                    self._send(200, workspace.source_png(values["asset_id"][0], bbox), "image/png")
                else:
                    self._error(404, "NOT_FOUND", "未找到本地复核资源。")
            except Exception as exc:
                self._failure(exc)

        def do_POST(self):
            if not self._origin(mutation=True):
                return
            parsed = urlsplit(self.path)
            self.server.request_counts["POST " + parsed.path] += 1
            try:
                if parsed.query or parsed.path not in {"/api/save", "/api/restore", "/api/preview"}:
                    self._error(404, "NOT_FOUND", "未找到本地复核操作。")
                    return
                lengths = self.headers.get_all("Content-Length", [])
                if (len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit()
                        or self.headers.get("Transfer-Encoding") is not None):
                    raise ValueError("one finite Content-Length is required")
                count = int(lengths[0])
                if not 0 < count <= MAX_REQUEST_BYTES:
                    self._error(413, "REQUEST_TOO_LARGE", "修订内容超出单次保存范围。")
                    return
                if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                    self._error(415, "JSON_REQUIRED", "复核操作需要JSON请求。")
                    return
                raw = self.rfile.read(count)
                if len(raw) != count:
                    raise ValueError("incomplete request body")
                request = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_finite)
                if parsed.path == "/api/preview":
                    if not isinstance(request, dict) or set(request) != {"text"} or not isinstance(request["text"], str):
                        raise ValueError("preview requires only raw text")
                    self._send(200, {"ok": True, "preview": parse_inline_formula_latex(request["text"])})
                else:
                    current = workspace.save(request) if parsed.path == "/api/save" else workspace.restore(request)
                    value = copy.deepcopy(current)
                    value["csrf_token"] = self.server.review_token
                    for answer in value["answers"]:
                        for block in answer["blocks"]:
                            for run in block["runs"]:
                                if run["format"] == "latex":
                                    run["math_preview"] = parse_inline_formula_latex(run["text"])
                    self._send(200, {"ok": True, "state": value})
            except Exception as exc:
                self._failure(exc)

        def _method_not_allowed(self):
            self._error(405, "METHOD_NOT_ALLOWED", "此本地复核入口不支持该方法。")

        do_OPTIONS = do_PUT = do_PATCH = do_DELETE = _method_not_allowed

    # Windows can occasionally choose an excluded ephemeral port for port=0.
    # Retry the OS allocation only; a user-specified port still fails explicitly.
    for attempt in range(8):
        try:
            server = ThreadingHTTPServer((host, port), Handler)
            break
        except PermissionError as exc:
            if port != 0 or exc.errno != errno.EACCES or attempt == 7:
                raise
    server.daemon_threads = True
    server.review_token = secrets.token_urlsafe(32)
    server.request_counts = Counter()
    return server
