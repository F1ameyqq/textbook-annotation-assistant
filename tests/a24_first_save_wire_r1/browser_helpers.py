# Fixed synthetic object definitions only; no old test class.
"""Synthetic browser/CDP objects exercise the concrete platform binding, no browser."""
import asyncio
import base64
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from annotation.delivery.live_pilot import wire
from annotation.delivery.live_pilot.usense import CurrentPageIO, PAGE_UPLOAD, build_guard_binding, make_first_save_guard
from annotation.quality.live_pilot import PilotError
from annotation.runtime.storage.common import digest
from fixture import fixture


class Events:
    def __init__(self):
        self.handlers = {}
    def on(self, name, handler):
        self.handlers.setdefault(name, []).append(handler)
    def emit(self, name, value):
        for handler in self.handlers.get(name, []):
            handler(value)


class CDP(Events):
    def __init__(self):
        super().__init__()
        self.bodies = {}
    async def send(self, method, params):
        if method == "Network.getResponseBody":
            return {"body": self.bodies[params["requestId"]], "base64Encoded": False}
        return {}


class Policy:
    def decide(self, *args):
        return False, "SYNTHETIC_UNLISTED"


class BaseGuard:
    def __init__(self, context, page, policy):
        self.context, self.page, self.policy = context, page, policy
        self.session, self.events, self.stopped = CDP(), [], False
        self.auth, self.auth_frame, self.main_frame_id = SimpleNamespace(authenticated=True), page.main_frame, "frame"
    def record_failure(self, error):
        self.stopped = True
    async def route(self, route):
        self.stopped = True
        await route.abort("blockedbyclient")
    async def paused(self, event):
        self.stopped = True
    def native_response(self, event):
        pass
    async def capture(self, response):
        pass


class Context(Events):
    async def close(self):
        self.page.closed = True


class Route:
    def __init__(self, request):
        self.request, self.aborted = request, False
    async def continue_(self):
        pass
    async def abort(self, reason):
        self.aborted = True


class Page:
    url = "https://www.usense.com/qieti/annotateUnified"
    def __init__(self, context):
        self.context, self.main_frame = context, object()
        context.page = self
        self.closed, self.calls, self.cached, self.tamper = False, [], False, False
    async def evaluate(self, script, args):
        if script == PAGE_UPLOAD:
            boundary = "A24SyntheticBoundary"
            parts = []
            for name, value in args["fields"].items():
                parts.append(("--" + boundary + '\r\nContent-Disposition: form-data; name="' + name + '"\r\n\r\n' + value + "\r\n").encode())
            parts.append(("--" + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="crop.jpg"\r\nContent-Type: image/jpeg\r\n\r\n').encode() +
                         base64.b64decode(args["bytes"]) + ("\r\n--" + boundary + "--\r\n").encode())
            value = await self.emit_request("POST", args["host"].rstrip("/") + "/", b"".join(parts),
                                           {"content-type": "multipart/form-data; boundary=" + boundary})
            return {"http_status": value["http_status"]}
        payload = args["payload"]
        if self.tamper and payload is not None:
            payload = {"different": True}
        raw = json.dumps(payload).encode() if args["method"] == "POST" else None
        return await self.emit_request(args["method"], args["path"], raw, {"content-type": "application/json"})
    async def emit_request(self, method, url, raw=None, headers=None, kind="Fetch"):
        self.calls.append((method, url))
        request = SimpleNamespace(method=method, url=url, resource_type=kind.lower(), frame=self.main_frame,
                                  redirected_from=None, post_data_buffer=raw, headers=headers or {})
        route = Route(request)
        self.context.emit("request", request)
        nid = "native-" + str(len(self.calls))
        self.guard.session.emit("Network.requestWillBeSent", {"requestId": nid, "frameId": "frame", "request": {"method": method, "url": url}})
        await self.guard.paused({"requestId": "fetch-" + nid, "frameId": "frame", "resourceType": kind,
                                 "networkId": nid, "request": {"method": method, "url": url}})
        await self.guard.route(route)
        if route.aborted or self.guard.stopped:
            raise PilotError("SYNTHETIC_PRE_SEND_DENIED")
        body = json.dumps({"code": 0, "SYNTHETIC": True})
        self.guard.session.bodies[nid] = body
        native = {"requestId": nid, "response": {"status": 200, "fromDiskCache": self.cached}}
        self.guard.native_response(native)
        self.guard.session.emit("Network.responseReceived", native)
        self.guard.session.emit("Network.loadingFinished", {"requestId": nid})
        async def response_body():
            return body.encode()
        await self.guard.capture(SimpleNamespace(request=request, status=200, from_service_worker=False, body=response_body))
        return {"http_status": 200, "body": body}
    async def reload(self, **kwargs):
        value = await self.emit_request("GET", self.url, kind="Document")
        async def text():
            return value["body"]
        return SimpleNamespace(status=200, text=text)
    def locator(self, selector):
        async def wait_for(**kwargs):
            pass
        return SimpleNamespace(wait_for=wait_for)
    def is_closed(self):
        return self.closed


