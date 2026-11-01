"""Loopback-only service for human-edited draft boxes; no platform connection."""
from __future__ import annotations

import copy
import errno
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import unquote, urlsplit

MAX_BODY = 80 * 1024 * 1024
STATIC = {"/": ("ui.html", "text/html; charset=utf-8"),
          "/geometry.js": ("geometry.js", "text/javascript; charset=utf-8"),
          "/ui.js": ("ui.js", "text/javascript; charset=utf-8"),
          "/ui.css": ("ui.css", "text/css; charset=utf-8")}


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("重复的JSON字段")
        result[key] = value
    return result


def make_server(workspace, *, host="127.0.0.1", port=58635):
    if host != "127.0.0.1":
        raise ValueError("预框工具仅监听本机127.0.0.1")
    token = secrets.token_urlsafe(32)

    def state():
        value = copy.deepcopy(workspace.state())
        value["csrf_token"] = token
        for page in value["pages"]:
            page["image_url"] = "/assets/" + page["page_id"]
        return value

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *args):
            pass

        def send(self, status, value, mime="application/json; charset=utf-8", download=False):
            data = (json.dumps(value, ensure_ascii=False, allow_nan=False)+"\n").encode() if isinstance(value, (dict, list)) else value
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            if download:
                self.send_header("Content-Disposition", 'attachment; filename="prebox-draft.json"')
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def error(self, status, code, message):
            self.send(status, {"error": {"code": code, "message": str(message)[:1000]}})

        def valid_host(self):
            expected = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != expected:
                self.error(403, "LOCAL_ONLY", "请使用本机启动地址")
                return False
            origin = self.headers.get("Origin")
            if origin is not None and origin != "http://"+expected:
                self.error(403, "ORIGIN_REJECTED", "不接受其他页面发起的请求")
                return False
            return True

        def do_GET(self):
            if not self.valid_host():
                return
            path = urlsplit(self.path).path
            try:
                if path in STATIC:
                    filename, mime = STATIC[path]
                    self.send(200, (Path(__file__).parent/filename).read_bytes(), mime)
                elif path == "/api/state":
                    self.send(200, state())
                elif path == "/api/history":
                    self.send(200, {"revisions": workspace.history()})
                elif path == "/api/export":
                    self.send(200, workspace.export_document(), download=True)
                elif path.startswith("/assets/"):
                    page_id = unquote(path[len("/assets/"):])
                    page = next((p for p in workspace.state()["pages"] if p["page_id"] == page_id), None)
                    if page is None:
                        self.error(404, "UNKNOWN_PAGE", "未找到书页")
                        return
                    data = workspace.asset_bytes(page_id)
                    mime = "image/png" if data.startswith(b"\x89PNG\r\n\x1a\n") else "image/jpeg"
                    self.send(200, data, mime)
                else:
                    self.error(404, "NOT_FOUND", "未找到页面")
            except (ValueError, OSError, KeyError) as exc:
                self.error(422, "INVALID_WORKSPACE", exc)

        def do_POST(self):
            if not self.valid_host():
                return
            if self.headers.get("X-CSRF-Token") != token:
                self.error(403, "CSRF_REJECTED", "页面会话已失效，请刷新后重试")
                return
            if self.headers.get("Transfer-Encoding") or self.headers.get_content_type() != "application/json":
                self.error(415, "JSON_REQUIRED", "需要JSON请求")
                return
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit() or not 0 < int(lengths[0]) <= MAX_BODY:
                self.error(413, "REQUEST_TOO_LARGE", "单批导入请少于80MB")
                return
            try:
                self.connection.settimeout(30)
                raw = self.rfile.read(int(lengths[0]))
                if len(raw) != int(lengths[0]):
                    raise ValueError("请求内容不完整")
                body = json.loads(raw, object_pairs_hook=_unique,
                                  parse_constant=lambda value: (_ for _ in ()).throw(ValueError("无效数值")))
                if not isinstance(body, dict) or type(body.get("expected_revision")) is not int:
                    raise ValueError("缺少当前版本")
                revision = body["expected_revision"]
                path = urlsplit(self.path).path
                if path == "/api/import-images":
                    workspace.import_images(body["files"], revision)
                elif path == "/api/save":
                    workspace.save(body["pages"], revision)
                elif path == "/api/import":
                    workspace.import_document(body["document_text"] if "document_text" in body else body["document"], revision)
                elif path == "/api/restore":
                    workspace.restore(body["revision"], revision)
                else:
                    self.error(404, "NOT_FOUND", "未知操作")
                    return
                self.send(200, state())
            except Exception as exc:
                # The store defines ConflictError; avoid turning stale writes into a generic success.
                if type(exc).__name__ == "ConflictError":
                    self.error(409, "STALE_REVISION", exc)
                elif isinstance(exc, (ValueError, KeyError, TypeError, OSError)):
                    self.error(422, "INVALID_INPUT", exc)
                else:
                    self.error(500, "SAVE_FAILED", "操作未完成，请保留草稿并检查本地工作区")

    for attempt in range(32):
        try:
            server = ThreadingHTTPServer((host, port), Handler)
            break
        except OSError as exc:
            if port != 0 or exc.errno != errno.EACCES or attempt == 31:
                raise
    server.daemon_threads = True
    return server
