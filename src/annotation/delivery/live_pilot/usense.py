"""Narrow injected I/O; no browser/client/login/upload is constructed here."""
import copy
import asyncio
import base64
from datetime import datetime, timezone
from functools import wraps
import hashlib
import json
from collections import Counter
from urllib.parse import urlencode
from typing import Protocol

from annotation.quality.live_pilot import PilotError, require
from annotation.runtime.storage.common import digest
from annotation.delivery.live_pilot import wire


# Direct fetch only. The existing page-local token never crosses into Python.
# No axios interceptor, login, redirect, refresh-token, fallback or retry chain.
PAGE_FETCH = """async a => {
 const c=new AbortController(),t=setTimeout(()=>c.abort(),20000);
 try {
  const u=JSON.parse(localStorage.getItem('user')||'{}');
  if(!u.access_token)return {http_status:401,body:''};
  if(a.method==='POST'){
   const get=p=>{let v=u;for(const k of p||[]){if(v===null||typeof v!=='object'||!(k in v))return undefined;v=v[k];}return v;};
   if(!a.identity||!Array.isArray(a.identity.user_id)||!Array.isArray(a.identity.username)||
      String(get(a.identity.username))!==String(a.payload.created_by)||
      !a.payload.annotations_upsert.every(x=>String(x.user_id)===String(get(a.identity.user_id))))
     return {http_status:0,body:'',context_status:'IDENTITY_CHANGED'};
  }
  const h={Authorization:'Bearer '+u.access_token};
  if(a.method==='POST')h['Content-Type']='application/json';
  const r=await fetch(a.path,{method:a.method,headers:h,credentials:'same-origin',
    redirect:'error',cache:'no-store',signal:c.signal,
    ...(a.method==='POST'?{body:JSON.stringify(a.payload)}:{})});
  return {http_status:r.status,body:await r.text()};
 } catch(e) {return {http_status:0,body:''};} finally {clearTimeout(t);}
}"""
PAGE_UPLOAD = """async a => {
 const c=new AbortController(),t=setTimeout(()=>c.abort(),20000);
 try {
  const f=new FormData();for(const [k,v] of Object.entries(a.fields))f.append(k,v);
  const b=Uint8Array.from(atob(a.bytes),x=>x.charCodeAt(0));
  f.append('file',new Blob([b],{type:'image/jpeg'}),'crop.jpg');
  const r=await fetch(a.host,{method:'POST',body:f,credentials:'omit',redirect:'error',
    cache:'no-store',signal:c.signal});
  return {http_status:r.status};
 } catch(e) {return {http_status:0};} finally {clearTimeout(t);}
}"""


def build_guard_binding(request, profile, activation):
    """Pure exact slot compiler. It neither creates nor spends an activation."""
    require(activation.get("schema") == "A24FirstSaveActivation/v1" and activation.get("activated") is True and
            activation.get("request_hash") == digest(request) and activation.get("profile_hash") == digest(profile) and
            activation.get("decision_ref") and activation.get("independent_report_ref") and
            activation.get("dependency_manifest_hash") and activation.get("mode") in
            ("AUTHOR_SAVE", "READONLY_REOPEN", "READONLY_RECONCILE"), "FIRST_SAVE_ACTIVATION_REQUIRED")
    mode = activation["mode"]
    phases = ("baseline", "prewrite", "get", "refresh") if mode == "AUTHOR_SAVE" else (
        "reopen" if mode == "READONLY_REOPEN" else "reconcile",)
    slots = []
    def add(phase, method, path, params=None):
        suffix = "?{OFFICIAL_BOOK_QUERY}" if path == "/qieti/api/claim_book/books" else (("?" + urlencode(params)) if params else "")
        slots.append([phase, method, "https://www.usense.com" + path + suffix])
    for phase in phases:
        spec = profile["reads"][phase]
        for r in spec.get("requests", [spec]):
            add(phase, "GET", r["path"], r["params"])
        if "export" in spec:
            add(phase, "GET", spec["export"]["path"])
        if phase in ("get", "refresh", "reopen", "reconcile"):
            suffix = "/" + wire.BOOK + "/{SERVER_RECEIPT_ORDER}"
            if profile.get("aggregate_readback"):
                if profile["aggregate_readback"]["mode"] == "ALL_ZONES_INFO_GET":
                    add(phase, "GET", wire.INFO + suffix)
                continue
            add(phase, "GET", wire.FRAMES + suffix)
            add(phase, "GET", wire.INFO + suffix)
            for zone in ("question", "choice", "answer"):
                add(phase, "GET", wire.CONTENT, {"file_id": wire.BOOK,
                    "question_order": "{SERVER_RECEIPT_ORDER}", "zone": zone})
    if mode == "AUTHOR_SAVE":
        add("save", "POST", wire.COMMIT)
        add("refresh_document", "GET", "/qieti/annotateUnified")
        if profile["limits"]["upload"]:
            add("upload", "GET", wire.SIGNATURE, {"file_id": wire.BOOK, "dir_type": "annotate_images"})
            slots.extend([["upload", "POST", profile["signature"]["host"].rstrip("/") + "/"] for _ in range(6)])
    require(isinstance(activation.get("session_id"), str) and activation["session_id"] and
            activation.get("executor") == profile["session"]["executor" if mode == "AUTHOR_SAVE" else "reviewer"] and
            activation.get("payload_hash") == request["approval"].get("payload_hash") and activation.get("payload_hash"),
            "EXACT_PLATFORM_ACTIVATION_REQUIRED")
    window = request["approval"] if mode == "AUTHOR_SAVE" else activation
    require(isinstance(window.get("starts_at"), str) and isinstance(window.get("ends_at"), str), "READ_WINDOW_REQUIRED")
    return {**copy.deepcopy(activation), "schema": "A24FirstSaveGuardBinding/v1", "lease_kind": "NEW_A24_FIRST_SAVE",
            "request_slots": slots, "upload_objects": copy.deepcopy(profile.get("uploads", [])),
            "identity_fields": copy.deepcopy(profile["wire"]["identity_fields"]),
            "starts_at": window["starts_at"], "ends_at": window["ends_at"],
            "platform_version": profile["platform_version"], "evidence_mode": profile["mode"]}


def make_first_save_guard(base_guard_class, context, page, base_policy, binding):
    """Create a DISTINCT guard from the existing native guard implementation.

    The caller installs this on its newly authorized owned context before going
    online. Never replace a policy, cache, marker or budget on an old guard.
    Unchanged base handling retains static/session/child-target/OS boundaries.
    Exact wire slots bypass the readonly *cache* path, not either send barrier.
    """
    binding = copy.deepcopy(binding)
    require(binding.get("schema") == "A24FirstSaveGuardBinding/v1" and binding.get("activated") is True and
            binding.get("lease_kind") == "NEW_A24_FIRST_SAVE" and binding.get("decision_ref") and
            binding.get("independent_report_ref") and binding.get("request_hash") and binding.get("profile_hash"),
            "FIRST_SAVE_ACTIVATION_REQUIRED")

    def track_callback(function):
        @wraps(function)
        async def tracked(self, *args, **kwargs):
            current = asyncio.current_task()
            self.callbacks.add(current)
            try:
                return await function(self, *args, **kwargs)
            finally:
                self.callbacks.discard(current)
        return tracked

    class ExactPolicy:
        def __init__(self, owner):
            self.owner = owner

        def __getattr__(self, name):
            return getattr(base_policy, name)

        def decide(self, method, url, kind, redirected=False):
            active = self.owner.wire_active
            if active is not None and (method, url) == active[1:]:
                kinds = ("Fetch", "XHR") if self.owner.wire_kind == "Fetch" else (self.owner.wire_kind,)
                return (not redirected and kind in kinds), "FIRST_SAVE_WIRE"
            if self.owner.passive_phase is not None and method == "GET" and kind in ("Fetch", "XHR"):
                try:
                    self.owner.wire_slot(self.owner.passive_phase, method, url)
                    return not redirected, "FIRST_SAVE_WIRE"
                except PilotError:
                    pass
            if self.owner.wire_started and "/qieti/api/" in url:
                allowed, category = base_policy.decide(method, url, kind, redirected)
                if allowed is False and category == "EXPECTED_PASSIVE_DENIAL":
                    return False, category
                return False, "UNMANIFESTED_FIRST_SAVE_API"
            return base_policy.decide(method, url, kind, redirected)

    class FirstSaveGuard(base_guard_class):
        def __init__(self):
            super().__init__(context, page, base_policy)
            self.a24_first_save_binding = copy.deepcopy(binding)
            self.wire_limits = Counter(tuple(slot) for slot in binding["request_slots"])
            self.wire_used, self.wire_layers = Counter(), set()
            self.wire_active, self.wire_started = None, False
            self.server_receipt = None
            self.official_book_urls = {}
            self.passive_phase, self.passive_reads = None, {}
            if not hasattr(self, "callbacks"):
                self.callbacks = set()
            self.policy = ExactPolicy(self)

        async def install(self):
            await super().install()
            self.session.on("Network.requestServedFromCache", self.wire_cached)

        def begin_passive_phase(self, phase):
            require(self.passive_phase is None and phase == "refresh", "PASSIVE_PHASE_ALREADY_STARTED")
            self.passive_phase = phase

        def passive_state(self, method, url):
            if self.passive_phase is None or method != "GET":
                return None
            try:
                slot = self.wire_slot(self.passive_phase, method, url)
            except PilotError:
                return None
            key = (self.passive_phase, method, url)
            if key not in self.passive_reads:
                require(self.wire_used[slot] < self.wire_limits[slot], "PASSIVE_SLOT_SPENT")
                self.wire_used[slot] += 1
                self.passive_reads[key] = {"layers": set(), "future": asyncio.get_running_loop().create_future(),
                                           "cached": False, "consumed": False}
            return self.passive_reads[key]

        def claim_passive(self, layer, method, url, kind, redirected, owned):
            state = self.passive_state(method, url)
            require(state is not None and kind in ("Fetch", "XHR") and not redirected and owned and
                    layer not in state["layers"] and not self.stopped and not getattr(self, "sealed", False) and
                    not getattr(self, "shutdown_started", False), "PASSIVE_REQUEST_REJECTED")
            state["layers"].add(layer)
            return state

        async def consume_passive(self, phase, method, url):
            state = self.passive_reads.get((phase, method, url))
            if state is None:
                return None
            require(not state["consumed"], "PASSIVE_SLOT_ALREADY_CONSUMED")
            state["consumed"] = True
            value = await asyncio.wait_for(asyncio.shield(state["future"]), timeout=20)
            require(value is not None and not self.stopped, "PASSIVE_RESPONSE_UNPROVEN")
            return value

        def native_response(self, event):
            super().native_response(event)
            for state in self.passive_reads.values():
                if event.get("requestId") == state.get("network_id"):
                    response = event.get("response", {})
                    state["status"] = response.get("status")
                    state["cached"] |= any(response.get(k, False) for k in ("fromDiskCache", "fromServiceWorker", "fromPrefetchCache"))

        def wire_cached(self, event):
            for state in self.passive_reads.values():
                if event.get("requestId") == state.get("network_id"):
                    state["cached"] = True

        async def capture(self, response):
            for key, state in self.passive_reads.items():
                if response.request is state.get("request"):
                    try:
                        raw = await response.body()
                        require(state["layers"] == {"context", "native"} and state.get("network_id") and
                                state.get("status") == response.status == 200 and not state["cached"] and
                                not response.from_service_worker and not self.stopped, "PASSIVE_RESPONSE_UNPROVEN")
                        native_body = await self.session.send("Network.getResponseBody", {"requestId": state["network_id"]})
                        native_raw = (base64.b64decode(native_body["body"], validate=True) if native_body.get("base64Encoded")
                                      else native_body["body"].encode("utf-8"))
                        require(native_raw == raw and not state["future"].done(), "PASSIVE_RESPONSE_BYTES_MISMATCH")
                        state["future"].set_result({"http_status": 200, "body": raw.decode("utf-8"),
                            "request_id": state["network_id"], "session_id": binding["session_id"], "fresh": True, "cache": False,
                            "platform_version": binding["platform_version"]})
                    except BaseException as exc:
                        self.record_failure(exc)
                        if not state["future"].done():
                            state["future"].set_result(None)
                    return
            await super().capture(response)

        def wire_slot(self, phase, method, url):
            found = []
            for slot in self.wire_limits:
                rendered = slot[2]
                if "{OFFICIAL_BOOK_QUERY}" in rendered:
                    if phase not in self.official_book_urls:
                        continue
                    rendered = self.official_book_urls[phase]
                if "SERVER_RECEIPT_ORDER" in rendered:
                    if self.server_receipt is None:
                        continue
                    rendered = rendered.replace("{SERVER_RECEIPT_ORDER}", str(self.server_receipt["question_order"]))
                    rendered = rendered.replace("%7BSERVER_RECEIPT_ORDER%7D", str(self.server_receipt["question_order"]))
                if (phase, method, url) == (slot[0], slot[1], rendered):
                    found.append(slot)
            require(len(found) == 1, "NATIVE_MANIFEST_NOT_ADMITTED")
            return found[0]

        def bind_official_book(self, phase, endpoint):
            from annotation.source.usense.current_readonly.context_query import validate_endpoint
            validate_endpoint(endpoint)
            require(phase not in self.official_book_urls and
                    (phase, "GET", "https://www.usense.com/qieti/api/claim_book/books?{OFFICIAL_BOOK_QUERY}") in self.wire_limits,
                    "OFFICIAL_BOOK_SLOT_ALREADY_BOUND")
            self.official_book_urls[phase] = "https://www.usense.com" + endpoint  # Ephemeral only.

        def bind_server_receipt(self, value):
            require(self.server_receipt is None and value.get("identity_source") == "SERVER_RESPONSE" and
                    value.get("evidence_mode") == binding["evidence_mode"] and
                    value.get("payload_hash") == binding["payload_hash"] and
                    type(value.get("question_order")) is int and value["question_order"] > 0,
                    "RECEIPT_PLAN_BINDING")
            self.server_receipt = copy.deepcopy(value)

        def arm_wire(self, phase, method, url, *, kind="Fetch", body=None):
            wire.require_window(binding)
            slot = self.wire_slot(phase, method, url)
            require(not self.stopped and self.wire_active is None and self.wire_limits[slot] > self.wire_used[slot],
                    "NATIVE_WIRE_SLOT_SPENT")
            self.wire_used[slot] += 1
            self.wire_active, self.wire_layers, self.wire_started = (phase, method, url), set(), True
            self.wire_kind = kind
            self.wire_body = body

        def validate_wire_body(self, request):
            if request.method != "POST":
                return
            raw = request.post_data_buffer
            require(isinstance(raw, bytes) and self.wire_body is not None, "WIRE_REQUEST_BYTES_UNAVAILABLE")
            if self.wire_active[0] == "save":
                value = json.loads(raw, object_pairs_hook=wire.unique_object)
                require(digest(value) == binding["payload_hash"] == self.wire_body["payload_hash"], "WIRE_POST_BODY_CHANGED")
                return
            from email.parser import BytesParser
            from email.policy import default
            content_type = request.headers.get("content-type", "")
            message = BytesParser(policy=default).parsebytes(("Content-Type: " + content_type + "\r\nMIME-Version: 1.0\r\n\r\n").encode("ascii") + raw)
            require(message.is_multipart(), "UPLOAD_MULTIPART_UNAVAILABLE")
            fields, files = {}, []
            for part in message.iter_parts():
                name = part.get_param("name", header="content-disposition")
                value = part.get_payload(decode=True)
                if name == "file":
                    require(part.get_content_type() == "image/jpeg", "UPLOAD_MULTIPART_CHANGED")
                    files.append(value)
                else:
                    require(isinstance(name, str) and name not in fields, "UPLOAD_MULTIPART_CHANGED")
                    fields[name] = value.decode("utf-8")
            require(fields == self.wire_body["fields"] and len(files) == 1 and
                    hashlib.sha256(files[0]).hexdigest() == self.wire_body["content_sha256"] and
                    any(e["key"] == fields["key"] and e["resource"]["sha256"] == self.wire_body["content_sha256"]
                        for e in binding["upload_objects"]), "UPLOAD_MULTIPART_CHANGED")

        def finish_wire(self, success):
            complete = self.wire_layers == {"context", "native"}
            self.wire_active = None
            self.wire_body = None
            if not success or not complete:
                self.record_failure(PilotError("NATIVE_WIRE_EFFECT_UNKNOWN"))
            require(success and complete and not self.stopped, "NATIVE_WIRE_EFFECT_UNKNOWN")

        def claim_wire_layer(self, layer, method, url, kind, redirected, owned):
            require(not self.stopped and self.wire_active is not None and self.wire_active[1:] == (method, url) and
                    kind in (("Fetch", "XHR") if self.wire_kind == "Fetch" else (self.wire_kind,)) and
                    not redirected and owned and layer not in self.wire_layers and
                    self.auth.authenticated and not getattr(self, "sealed", False) and
                    not getattr(self, "shutdown_started", False), "NATIVE_WIRE_REQUEST_REJECTED")
            self.wire_layers.add(layer)

        @track_callback
        async def route(self, route):
            request = route.request
            active = self.wire_active
            if active is None or (request.method, request.url) != active[1:]:
                if self.passive_phase is None or request.method != "GET":
                    return await super().route(route)
                try:
                    self.wire_slot(self.passive_phase, request.method, request.url)
                except PilotError:
                    return await super().route(route)
                try:
                    state = self.claim_passive("context", request.method, request.url, "XHR" if request.resource_type.lower() == "xhr" else request.resource_type.title(),
                                               request.redirected_from is not None, request.frame is self.auth_frame)
                    state["request"] = request
                    await route.continue_()
                except BaseException as exc:
                    self.record_failure(exc)
                    await route.abort("blockedbyclient")
                return
            try:
                self.claim_wire_layer("context", request.method, request.url, "XHR" if request.resource_type.lower() == "xhr" else request.resource_type.title(),
                                      request.redirected_from is not None, request.frame is self.auth_frame)
                self.validate_wire_body(request)
                await route.continue_()
            except BaseException as exc:
                self.record_failure(exc)
                await route.abort("blockedbyclient")

        @track_callback
        async def paused(self, event):
            request = event.get("request", {})
            active = self.wire_active
            if active is None or (request.get("method"), request.get("url")) != active[1:]:
                if self.passive_phase is None or request.get("method") != "GET":
                    return await super().paused(event)
                try:
                    self.wire_slot(self.passive_phase, request["method"], request["url"])
                except PilotError:
                    return await super().paused(event)
                try:
                    state = self.claim_passive("native", request["method"], request["url"], event.get("resourceType"),
                                               bool(event.get("redirectedRequestId")), event.get("frameId") == self.main_frame_id)
                    require(isinstance(event.get("networkId"), str) and event["networkId"], "PASSIVE_NETWORK_ID_UNPROVEN")
                    state["network_id"] = event["networkId"]
                    await self.session.send("Fetch.continueRequest", {"requestId": event["requestId"]})
                except BaseException as exc:
                    self.record_failure(exc)
                    await self.session.send("Fetch.failRequest", {"requestId": event["requestId"], "errorReason": "BlockedByClient"})
                return
            try:
                self.claim_wire_layer("native", request["method"], request["url"], event.get("resourceType"),
                                      bool(event.get("redirectedRequestId")), event.get("frameId") == self.main_frame_id)
                await self.session.send("Fetch.continueRequest", {"requestId": event["requestId"]})
            except BaseException as exc:
                self.record_failure(exc)
                await self.session.send("Fetch.failRequest", {"requestId": event["requestId"], "errorReason": "BlockedByClient"})

    return FirstSaveGuard()


class CurrentPageIO:
    """Concrete async-Playwright binding for the existing guarded original page.

    Called from the runner worker while the owning event loop keeps both network
    barriers alive. It creates no context/runtime/profile and cannot substitute
    the exhausted readonly guard: a new exact first-save binding is mandatory.
    Guard capture must identify actual network response bytes, not cache reuse.
    """
    def __init__(self, page, context, guard, loop, binding, *, synthetic=False, owner_authority=None):
        self.page, self.context, self.guard, self.loop = page, context, guard, loop
        self.binding = copy.deepcopy(binding)
        self.owner_authority = owner_authority
        self.offline, self.evidence_mode = synthetic, "SYNTHETIC" if synthetic else "OBSERVED"
        self.session_id, self.actor = binding["session_id"], binding["executor"]
        self.serial = 0
        self._capture_installed, self._active_capture = False, None

    def _run(self, awaitable):
        future = asyncio.run_coroutine_threadsafe(awaitable, self.loop)
        try:
            return future.result(timeout=30)
        except BaseException:
            future.cancel()
            raise

    def _admit(self, method, url, phase):
        b, g = self.binding, self.guard
        if not self.offline:
            from annotation.runtime.live_pilot.authority import Authority
            require(type(self.owner_authority) is Authority, "VALIDATED_OWNER_AUTHORITY_REQUIRED")
            self.owner_authority.check()
            require(b.get("owner_authority_hash") == self.owner_authority.raw_hash and
                    getattr(g, "owner_authority_hash", None) == self.owner_authority.raw_hash,
                    "VALIDATED_OWNER_AUTHORITY_REQUIRED")
        wire.require_window(b)
        require(getattr(g, "a24_first_save_binding", None) == b and b.get("evidence_mode") == self.evidence_mode and
                b.get("schema") == "A24FirstSaveGuardBinding/v1" and b.get("activated") is True and
                b.get("decision_ref") and b.get("independent_report_ref") and
                getattr(g, "page", None) is self.page and getattr(g, "context", None) is self.context and
                not g.stopped and g.auth.authenticated and self.page.main_frame is g.auth_frame and
                self.page.url == "https://www.usense.com/qieti/annotateUnified", "FIRST_SAVE_GUARD_NOT_BOUND")
        require(callable(getattr(g, "arm_wire", None)) and callable(getattr(g, "finish_wire", None)) and
                callable(getattr(g, "wire_slot", None)), "NATIVE_MANIFEST_NOT_ADMITTED")
        g.wire_slot(phase, method, url)

    def bind_receipt(self, receipt):
        async def bind():
            self.guard.bind_server_receipt(receipt)
        self._run(bind())

    def request_once(self, method, path, *, params, payload, phase):
        return self._run(self.fetch_async(method, path, params=params, payload=payload, phase=phase))

    async def fetch_async(self, method, path, *, params, payload, phase):
        if path == "/qieti/api/claim_book/books":
            from annotation.source.usense.current_readonly.context_query import PREPARE_JS, SEND_JS, validate_endpoint
            require(method == "GET" and set(params).issubset({"_template"}), "OFFICIAL_BOOK_QUERY_TEMPLATE_REQUIRED")
            prepared = await self.page.evaluate(PREPARE_JS)
            require(isinstance(prepared, dict) and prepared.get("status") == "PREPARED", "CURRENT_BOOK_CONTEXT_UNAVAILABLE")
            endpoint = validate_endpoint(prepared.get("endpoint"))
            self.guard.bind_official_book(phase, endpoint)
            self._book_query_provenance = {"query_keys": ["page", "pageSize", "status_list", "id", "title", "team_name", "username", "role", "is_admin"],
                                           "query_hash": digest(endpoint)}
            async def official_send():
                response = await self.page.evaluate(SEND_JS.replace("body:await r.json()", "body:await r.text()"), endpoint)
                require(response.get("context_status") == "BOUND_CONTEXT_UNCHANGED", "CURRENT_BOOK_CONTEXT_CHANGED")
                return response
            return await self._fetch(method, "https://www.usense.com"+endpoint, payload, phase, operation=official_send)
        url = "https://www.usense.com" + path + (("?" + urlencode(params)) if params else "")
        return await self._fetch(method, url, payload, phase)

    def query_provenance(self, path, params):
        if path == "/qieti/api/claim_book/books":
            return dict(self._book_query_provenance)
        return {"query_keys": sorted(params), "query_hash": digest(params)}

    async def _fetch(self, method, url, payload, phase, *, operation=None):
        self._admit(method, url, phase)
        passive = await self.guard.consume_passive(phase, method, url)
        if passive is not None:
            return passive
        result, capture = await self._network_once(method, url, phase, PAGE_FETCH,
                                                   {"method": method, "path": url, "payload": payload,
                                                    "identity": self.binding["identity_fields"]}, operation=operation)
        self._admit(method, url, phase)
        require(capture["response_sha256"] == hashlib.sha256(result.get("body", "").encode("utf-8")).hexdigest() and
                capture["status"] == result["http_status"], "NATIVE_RESPONSE_BYTES_MISMATCH")
        self.serial += 1
        return {"http_status": result["http_status"], "body": result["body"],
                "request_id": capture["network_id"], "session_id": self.session_id,
                "fresh": True, "cache": False, "platform_version": self.binding["platform_version"]}

    def upload_once(self, host, *, fields, content):
        return self._run(self._upload(host, fields, content))

    async def _upload(self, host, fields, content):
        url = host.rstrip("/") + "/"
        self._admit("POST", url, "upload")
        result, capture = await self._network_once("POST", url, "upload", PAGE_UPLOAD, {"host": host, "fields": fields,
                                    "bytes": base64.b64encode(content).decode("ascii")},
                                    body={"fields": fields, "content_sha256": hashlib.sha256(content).hexdigest()})
        self._admit("POST", url, "upload")
        require(type(result.get("http_status")) is int and 200 <= result["http_status"] < 300, "UPLOAD_UNKNOWN")
        self.serial += 1
        return {"http_status": result["http_status"], "request_id": capture["network_id"],
                "session_id": self.session_id, "fresh": True, "cache": False,
                "response_hash": capture["response_sha256"]}

    async def _network_once(self, method, url, phase, script=None, args=None, *, operation=None, kind="Fetch", body=None):
        """Observe actual context + CDP identity/bytes; no supplied readback function."""
        require(self._active_capture is None, "CONCURRENT_WIRE_REQUEST")
        if not self._capture_installed:
            self.context.on("request", self._context_request)
            self.guard.session.on("Network.requestWillBeSent", self._native_request)
            self.guard.session.on("Network.responseReceived", self._native_response)
            self.guard.session.on("Network.requestServedFromCache", self._native_cached)
            self.guard.session.on("Network.loadingFinished", self._native_finished)
            self.guard.session.on("Network.loadingFailed", self._native_failed)
            await self.guard.session.send("Network.setCacheDisabled", {"cacheDisabled": True})
            self._capture_installed = True
        if method == "POST" and phase == "save":
            body = {"payload_hash": digest(args["payload"])}
        self.guard.arm_wire(phase, method, url, kind=kind, body=body)
        capture = {"method": method, "url": url, "context_count": 0, "native_count": 0,
                   "cached": False, "done": asyncio.get_running_loop().create_future()}
        self._active_capture = capture
        success = False
        try:
            result = await operation() if operation is not None else await self.page.evaluate(script, args)
            require(result.get("context_status") != "IDENTITY_CHANGED", "CURRENT_IDENTITY_CHANGED")
            await asyncio.wait_for(asyncio.shield(capture["done"]), timeout=5)
            require(capture["context_count"] == capture["native_count"] == 1 and not capture["cached"] and
                    capture.get("status") == result.get("http_status") and not capture.get("failed") and
                    not self.guard.stopped, "FRESH_NATIVE_RESPONSE_UNPROVEN")
            body = await self.guard.session.send("Network.getResponseBody", {"requestId": capture["network_id"]})
            raw = base64.b64decode(body["body"], validate=True) if body.get("base64Encoded") else body["body"].encode("utf-8")
            capture["response_sha256"] = hashlib.sha256(raw).hexdigest()
            success = True
            return result, capture
        finally:
            self._active_capture = None
            self.guard.finish_wire(success)

    def _context_request(self, request):
        c = self._active_capture
        if c is not None and request.method == c["method"] and request.url == c["url"]:
            c["context_count"] += 1
            if request.redirected_from is not None or request.frame is not self.guard.auth_frame:
                c["failed"] = True

    def _native_request(self, event):
        c, request = self._active_capture, event.get("request", {})
        if c is not None and request.get("method") == c["method"] and request.get("url") == c["url"]:
            c["native_count"] += 1
            c["network_id"] = event["requestId"]
            if event.get("redirectResponse") or event.get("frameId") != self.guard.main_frame_id:
                c["failed"] = True

    def _native_response(self, event):
        c, response = self._active_capture, event.get("response", {})
        if c is not None and event.get("requestId") == c.get("network_id"):
            c["status"] = response.get("status")
            c["cached"] |= any(response.get(k, False) for k in ("fromDiskCache", "fromServiceWorker", "fromPrefetchCache"))

    def _native_cached(self, event):
        c = self._active_capture
        if c is not None and event.get("requestId") == c.get("network_id"):
            c["cached"] = True

    def _native_finished(self, event):
        c = self._active_capture
        if c is not None and event.get("requestId") == c.get("network_id") and not c["done"].done():
            c["done"].set_result(True)

    def _native_failed(self, event):
        c = self._active_capture
        if c is not None and event.get("requestId") == c.get("network_id"):
            c["failed"] = True
            if not c["done"].done():
                c["done"].set_result(False)

    def refresh_once(self):
        return self._run(self._refresh())

    async def _refresh(self):
        self._admit("GET", self.page.url, "refresh_document")
        self.guard.begin_passive_phase("refresh")
        async def reload_once():
            response = await self.page.reload(wait_until="domcontentloaded", timeout=20000)
            require(response is not None, "REFRESH_UNPROVEN")
            return {"http_status": response.status, "body": await response.text()}
        result, capture = await self._network_once("GET", self.page.url, "refresh_document", operation=reload_once, kind="Document")
        require(result["http_status"] == 200 and capture["status"] == 200 and self.page.main_frame is self.guard.auth_frame and
                not self.guard.stopped, "REFRESH_UNPROVEN")
        await self.page.locator(".pdf-zones-container:visible").wait_for(state="visible", timeout=5000)
        return {"refreshed": True, "session_id": self.session_id}

    def close(self):
        return self._run(self._close())

    async def _close(self):
        # This lease owns only the explicitly supplied context, never sibling apps.
        if getattr(self.guard, "owner_authority_hash", None) == self.binding.get("owner_authority_hash") and self.binding.get("owner_authority_hash"):
            return {"released": True, "session_id": self.session_id, "adapter_capability_released": True,
                    "release_scope": "ADAPTER_ONLY", "physical_context_runtime_release": "PENDING_OUTER_OWNER"}
        await self.context.close()
        require(self.page.is_closed(), "CONTEXT_RELEASE_UNPROVEN")
        return {"released": True, "session_id": self.session_id, "context_closed": True,
                "runtime_release": "OWNER_MUST_PROVE"}

    def finish_read_phase(self, phase):
        if phase == "refresh":
            async def finish():
                for key, state in self.guard.passive_reads.items():
                    if key[0] == phase and key[2].split("?", 1)[0] in (
                            "https://www.usense.com/qieti/api/user_login/profile",
                            "https://www.usense.com/qieti/api/user_login/config/permissions",
                            "https://www.usense.com/qieti/api/user_login/config/teams") and not state["consumed"]:
                        value = await self.guard.consume_passive(*key)
                        require(value["http_status"] == 200, "REFRESH_SESSION_UNPROVEN")
                        # The raw session response stays ephemeral and is discarded.
                require(all(state["consumed"] and state["future"].done() for key, state in self.guard.passive_reads.items()
                            if key[0] == phase), "UNCONSUMED_PASSIVE_READ")
                self.guard.passive_phase = None
            self._run(finish())


class Transport(Protocol):
    offline: bool
    def observe(self, phase: str): ...
    def send_once(self, payload): ...
    def close(self): ...


class UsenseTransport:
    """One leased session, an exact GET manifest and one claimed POST.

    The owner supplies request_once/refresh_once/close capabilities. A fake lease
    must declare offline=True and SYNTHETIC. Merely relabeling a snapshot cannot
    register it as an observation. Current proof resources are checked at bind.
    """
    wire_enabled = True
    offline = False
    missing = ("CURRENT_JOINT_POLICY_PROOF", "CURRENT_COMPLETE_TARGET_AND_ALL_OLD_BODY",
               "CURRENT_RECEIPT_AND_READBACK_SCHEMA", "FINAL_CROP_BYTES_AND_UPLOAD_CONTRACT",
               "CURRENT_SOURCE_SAVE_PAGE_RELATION", "NEW_EXACT_BUSINESS_MANIFEST_AND_ACTIVATION",
               "EXCLUSIVE_SESSION_AND_OUTER_OWNER_RELEASE")

    def __init__(self, session=None, wire_profile=None, *, readonly=False):
        require(wire_profile is None, "PROFILE_MUST_BE_HASH_BOUND_INPUT")
        self._session = session
        self.readonly = readonly
        self.profile = None
        self._used, self._request_ids, self._observations = set(), set(), {}
        self._ledger, self._sequence = [], 0
        self._plan = self._payload = self._receipt = self._armed = None
        self._predecessor = None
        self._closed = self._touched = False

    def bind(self, admission, request, asset_root):
        require(self.profile is None and not self._closed, "TRANSPORT_ALREADY_BOUND")
        profile = wire.validate_profile(admission, request, asset_root)
        if not admission.offline:
            from annotation.runtime.live_pilot.authority import Authority
            require(type(self._session) is CurrentPageIO and type(self._session.owner_authority) is Authority,
                    "VALIDATED_OWNER_TRANSPORT_REQUIRED")
            self._session.owner_authority.check()
        require(self._session is not None and getattr(self._session, "offline", None) is admission.offline and
                getattr(self._session, "evidence_mode", None) == profile["mode"], "IO_PROVENANCE_REQUIRED")
        session_id = self._session.session_id
        identity = profile["session"]
        require(isinstance(session_id, str) and session_id and
                self._session.actor == identity["reviewer" if self.readonly else "executor"], "SESSION_OWNER")
        require((session_id != identity["session_id"]) if self.readonly else
                (session_id == identity["session_id"]), "SESSION_IDENTITY")
        self.offline = admission.offline
        self.profile, self._request, self.session_id = profile, copy.deepcopy(request), session_id
        self._asset_root = asset_root
        self._profile_hash, self._fact = digest(profile), copy.deepcopy(admission.questions[0])

    def _bound(self):
        require(self.profile is not None and digest(self.profile) == self._profile_hash and
                self._request["approval"]["wire_profile_hash"] == self._profile_hash, "WIRE_PROFILE_CHANGED")

    def readonly_admission_time(self, request):
        require(self.readonly and isinstance(self._session, CurrentPageIO), "CURRENT_READONLY_AUTHORITY_REQUIRED")
        b = self._session.binding
        require(b.get("mode") in ("READONLY_REOPEN", "READONLY_RECONCILE") and b.get("request_hash") == digest(request) and
                b.get("activated") is True and b.get("decision_ref") and b.get("independent_report_ref"),
                "CURRENT_READONLY_AUTHORITY_REQUIRED")
        wire.require_window(b)
        start = datetime.fromisoformat(b["starts_at"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(b["ends_at"].replace("Z", "+00:00"))
        require((end-start).total_seconds() <= 900, "BOUNDED_READONLY_WINDOW")
        # Historical approval is validated at its original time, never renewed.
        return datetime.fromisoformat(request["approval"]["starts_at"].replace("Z", "+00:00"))

    def _read(self, path, params, phase, slot, *, json_body=True):
        self._bound()
        window = self._session.binding if self.readonly and isinstance(self._session, CurrentPageIO) else self._request["approval"]
        wire.require_window(window)
        wire.safe_get(path, params)
        require(self.profile is not None and not self._closed and (phase, slot) not in self._used, "READ_SLOT_SPENT")
        self._used.add((phase, slot))  # Burn BEFORE I/O, also on timeout/unknown response.
        self._touched = True
        response = self._session.request_once("GET", path, params=copy.deepcopy(params), payload=None, phase=phase)
        body = wire.checked_response(response, json_body=json_body)
        require(response["session_id"] == self.session_id and
                response["platform_version"] == self.profile["platform_version"] and
                response["request_id"] not in self._request_ids, "RESPONSE_SESSION_OR_REPLAY")
        self._request_ids.add(response["request_id"])
        self._sequence += 1
        query_provenance = (self._session.query_provenance(path, params) if hasattr(self._session, "query_provenance") else
                            {"query_keys": sorted(params), "query_hash": digest(params)})
        self._ledger.append({"sequence": self._sequence, "phase": phase, "slot": slot,
                             "method": "GET", "path_template": path,
                             **query_provenance,
                             "request_id": response["request_id"], "response_hash": digest(response)})
        return body

    def observe(self, phase):
        require(self.profile is not None, "CURRENT_WIRE_PROFILE_REQUIRED")
        require(phase in self.profile["reads"] and
                (self.readonly if phase == "reconcile" else (phase == "reopen") == self.readonly),
                "READ_PHASE_AUTHORITY")
        if phase == "baseline":
            require(not self._used, "PHASE_ORDER")
        elif phase == "prewrite":
            require("baseline" in getattr(self, "_finished_phases", set()) and self._receipt is None, "PHASE_ORDER")
        elif phase in ("get", "refresh"):
            require(self._receipt is not None and self._plan is not None and
                    (phase != "refresh" or "get" in getattr(self, "_finished_phases", set())), "PHASE_ORDER")
        else:
            require(self._predecessor is not None and (self._receipt is not None or phase == "reconcile"), "REOPEN_CHAIN")
        if phase == "refresh":
            require((phase, "refresh") not in self._used, "REFRESH_ALREADY_USED")
            self._used.add((phase, "refresh"))
            self._touched = True
            refreshed = self._session.refresh_once()
            require(refreshed == {"refreshed": True, "session_id": self.session_id}, "REFRESH_UNPROVEN")
        start = len(self._ledger)
        spec = self.profile["reads"][phase]
        if "requests" in spec:
            responses = {r["name"]: self._read(r["path"], r["params"], phase, r["name"]) for r in spec["requests"]}
            result = {k: wire.project(rule, responses) for k, rule in spec["projection"].items()}
        else:
            body = self._read(spec["path"], spec["params"], phase, "snapshot")
            result = {k: copy.deepcopy(wire.field(body, path)) for k, path in spec["response_fields"].items()}
        require(result["platform_version"] == self.profile["platform_version"], "CAPABILITY_VERSION")
        if "export" in spec:
            export = spec["export"]
            text = self._read(export["path"], export["params"], phase, "export", json_body=False)
            content, coverage = wire.decode_complete_export(text, export["codec"], result["view"]["target"]["questions"])
            # The snapshot must separately prove authoritative complete inventory.
            require(result["complete"] is True, "FULL_TARGET_REQUIRED")
            for q in result["view"]["target"]["questions"]:
                actual = {f["platform_frame_id"] for f in result["view"]["target"]["frames"]
                          if f["platform_question_id"] == q["platform_question_id"]}
                require(set(content[q["platform_question_id"]]["rect_ids"]) == actual, "EXPORT_FRAME_ASSOCIATION")
            result["view"]["question_content"] = content
            result["export_coverage"] = coverage
        if phase not in ("baseline", "prewrite") and self._receipt is not None:
            result["wire_readback"] = self._read_aggregate_new(result, phase) if self.profile.get("aggregate_readback") else self._read_new(phase)
        source = digest({"session": self.session_id, "ledger": self._ledger[start:]})
        result.update(origin="A24_WIRE_READ", evidence_mode=self.profile["mode"], phase=phase,
                      source_ref=source, read_sequence=self._sequence, session_id=self.session_id,
                      provenance={"profile_hash": digest(self.profile), "requests": copy.deepcopy(self._ledger[start:]),
                                  "executor": self._session.actor})
        if self._predecessor is not None:
            result.update(predecessor_session_id=self._predecessor["session_id"], released_predecessor=True,
                          predecessor_release_hash=digest(self._predecessor))
        self._observations[source] = digest(result)
        self._last_observation = copy.deepcopy(result)
        if not hasattr(self, "_finished_phases"):
            self._finished_phases = set()
        self._finished_phases.add(phase)
        if hasattr(self._session, "finish_read_phase"):
            self._session.finish_read_phase(phase)
        return result

    def verify_observation(self, value, phase):
        require(value.get("origin") == "A24_WIRE_READ" and value.get("evidence_mode") == self.profile["mode"] and
                value.get("phase") == phase and self._observations.get(value.get("source_ref")) == digest(value),
                "UNREGISTERED_WIRE_OBSERVATION")

    def _read_new(self, phase):
        receipt, codec = self._receipt, self.profile["readback"]
        order = receipt["question_order"]
        suffix = "/" + wire.BOOK + "/" + str(order)
        raw = self._read(wire.FRAMES + suffix, {}, phase, "frames")
        records = wire.field(raw, codec["frames_path"])
        require(isinstance(records, list), "READBACK_FRAME_CODEC")
        rows = [{k: wire.field(row, path) for k, path in codec["frame_fields"].items()} for row in records]
        info = wire.field(self._read(wire.INFO + suffix, {}, phase, "info"), codec["info_path"])
        if "info_fields" in codec:
            require(set(codec["info_fields"]) == {"tishi", "tilei", "tihao"}, "QUESTION_INFO_CODEC")
            info = {key: wire.field(info, path) for key, path in codec["info_fields"].items()}
        content = []
        for submission in self._payload["ocr_submissions"]:
            zone = submission["zone"]
            raw = self._read(wire.CONTENT, {"file_id": wire.BOOK, "question_order": order, "zone": zone}, phase, zone)
            require(wire.field(raw, codec["content_success_path"]) is True, "CONTENT_UNAVAILABLE")
            text = wire.field(raw, codec["content_text_path"])
            require(isinstance(text, str), "CONTENT_UNAVAILABLE")
            rects = (wire.field(raw, codec["content_rect_ids_path"]) if codec["association"] == "RETURNED_RECT_IDS"
                     else [r["rect_id"] for r in sorted(rows, key=lambda r: r["image_order_in_annotation_zone"]) if r["type"] == zone])
            content.append({"zone": zone, "ocr_result": text, "rect_ids": rects, "question_order": None})
        return {"rows": rows, "question_info": info, "body_submissions": content,
                "association": codec["association"], "receipt_hash": digest(receipt)}

    def _read_aggregate_new(self, snapshot, phase):
        p, receipt = self.profile["aggregate_readback"], self._receipt
        pid = receipt["platform_question_id"]
        by_question = wire.field(snapshot, p["rows_path"])
        require(isinstance(by_question, dict) and isinstance(by_question.get(pid), list), "AGGREGATE_FRAME_ASSOCIATION")
        rows = by_question[pid]
        require(len(rows) == 6 and all(set(row) == wire.ROW_FIELDS for row in rows), "AGGREGATE_FRAME_ASSOCIATION")
        content = snapshot["view"]["question_content"].get(pid)
        require(isinstance(content, dict) and content.get("status") == "AVAILABLE" and
                set(content.get("wire_zones", {})) == set(wire.ZONES), "CONTENT_UNAVAILABLE")
        bodies = []
        for submitted in self._payload["ocr_submissions"]:
            zone = submitted["zone"]
            actual_ids = [r["rect_id"] for r in sorted(rows, key=lambda r: r["image_order_in_annotation_zone"]) if r["type"] == zone]
            actual_text = content["wire_zones"][zone]
            require(isinstance(actual_text, str), "CONTENT_UNAVAILABLE")
            bodies.append({"zone": zone, "ocr_result": actual_text, "rect_ids": actual_ids, "question_order": None})
        info = content.get("question_info")
        if p["mode"] == "ALL_ZONES_INFO_GET":
            info = wire.field(self._read(wire.INFO+"/"+wire.BOOK+"/"+str(receipt["question_order"]), {}, phase, "info"),
                              self.profile["readback"]["info_path"])
        return {"rows": rows, "question_info": info, "body_submissions": bodies,
                "association": "AUTHORITATIVE_FRESH_AGGREGATE_RECT_ZONE_MEMBERSHIP", "receipt_hash": digest(receipt)}

    def build_commit(self, plan):
        self._bound()
        require(self.profile is not None and not self.readonly, "CURRENT_WIRE_PROFILE_REQUIRED")
        payload = wire.build_payload(plan, self.profile)
        uploads = wire.upload_manifest(plan, self.profile)
        require(plan["payload"] == payload and plan["upload_manifest"] == uploads and
                plan["write_set"] == wire.write_set(payload, uploads), "PLAN_PAYLOAD_CHANGED")
        require(self.offline or self._request["approval"].get("payload_hash") == digest(payload), "EXACT_PAYLOAD_APPROVAL_REQUIRED")
        self._crops = wire.load_crops(uploads, self._asset_root)
        self._plan, self._payload = copy.deepcopy(plan), copy.deepcopy(payload)
        return payload

    def arm(self, journal, question_id, intent):
        require(not self.readonly and self._armed is None and journal.offline is self.offline and
                self._payload is not None and intent["payload_hash"] == digest(self._payload) and
                intent["plan_hash"] == digest(self._plan), "DURABLE_INTENT_REQUIRED")
        require(any(e["kind"] == "SEND_CLAIMED" and e["data"] ==
                    {"question_id": question_id, "intent_hash": digest(intent)} for e in journal.read()),
                "DURABLE_CLAIM_REQUIRED")
        self._armed = digest(intent)

    def upload_crops_once(self, journal, question_id):
        """Exact six objects, no dataURL, retries, credential logging or cleanup."""
        require(not self.readonly and self._armed is not None and self._plan is not None, "DURABLE_CLAIM_REQUIRED")
        objects = self._plan["upload_manifest"]
        if not objects:
            return
        contract = self.profile["signature"]
        raw = self._read(wire.SIGNATURE, {"file_id": wire.BOOK, "dir_type": "annotate_images"}, "upload", "signature")
        signature = wire.field(raw, contract["response_path"])
        require(isinstance(signature, dict) and all(isinstance(signature.get(k), str) and signature[k]
                for k in ("accessid", "host", "policy", "signature", "dir")) and
                signature["host"] == contract["host"] and signature["dir"] == contract["dir"] and
                hashlib.sha256(signature["policy"].encode("utf-8")).hexdigest() == contract["policy_sha256"] and
                type(signature.get("expire")) is int and signature["expire"] >= contract["minimum_expire"] and
                signature["expire"] >= int(datetime.fromisoformat(self._request["approval"]["ends_at"].replace("Z", "+00:00")).timestamp()) + 300 and
                signature["expire"] > int(datetime.now(timezone.utc).timestamp()) + 300, "UPLOAD_SIGNATURE_UNPROVEN")
        journal.append("SIGNATURE_RECEIVED", {"question_id": question_id, "contract_hash": digest(contract),
                                             "values_retained": False, "object_count": len(objects)})
        for index, (entry, blob) in enumerate(zip(objects, self._crops)):
            wire.require_window(self._request["approval"])
            slot = ("upload", entry["rect_id"])
            require(slot not in self._used, "UPLOAD_SLOT_SPENT")
            journal.append("UPLOAD_CLAIM", {"question_id": question_id, "index": index, "object_hash": digest(entry)})
            self._used.add(slot)
            form = {"key": entry["key"], "policy": signature["policy"], "OSSAccessKeyId": signature["accessid"],
                    "success_action_status": "200", "signature": signature["signature"], "Content-Type": "image/jpeg"}
            if signature.get("securityToken"):
                require(isinstance(signature["securityToken"], str), "UPLOAD_SIGNATURE_UNPROVEN")
                form["x-oss-security-token"] = signature["securityToken"]
            response = self._session.upload_once(contract["host"], fields=form, content=blob)
            require(isinstance(response, dict) and set(response) == {"http_status", "request_id", "session_id", "fresh", "cache", "response_hash"} and
                    type(response["http_status"]) is int and 200 <= response["http_status"] < 300 and
                    response["fresh"] is True and response["cache"] is False and
                    isinstance(response["response_hash"], str) and len(response["response_hash"]) == 64 and
                    response["session_id"] == self.session_id and isinstance(response["request_id"], str) and
                    response["request_id"] and response["request_id"] not in self._request_ids, "UPLOAD_UNKNOWN")
            self._request_ids.add(response["request_id"])
            journal.append("UPLOAD_RECEIPT", {"question_id": question_id, "index": index, "object_hash": digest(entry),
                "http_status": response["http_status"], "response_hash": response["response_hash"],
                "server_acknowledgement": "NATIVE_OBSERVED_HTTP_OK_ONLY", "host_key_echo_required": False,
                "object_identity_source": "APPROVED_REQUEST_MANIFEST_NOT_SERVER_ECHO", "content_save_proved": False})
        self._used.add(("upload", "complete"))

    def send_once(self, payload):
        self._bound()
        require(not self.readonly and not self._closed and self._armed is not None and
                ("save", "commit") not in self._used and "prewrite" in getattr(self, "_finished_phases", set()) and
                payload == self._payload, "SEND_NOT_CLAIMED_OR_SPENT")
        require(not self._plan["upload_manifest"] or ("upload", "complete") in self._used, "UPLOADS_INCOMPLETE")
        approval = self._request["approval"]
        now = datetime.now(timezone.utc)
        require(datetime.fromisoformat(approval["starts_at"].replace("Z", "+00:00")) <= now <=
                datetime.fromisoformat(approval["ends_at"].replace("Z", "+00:00")), "AUTHORIZATION_WINDOW")
        self._used.add(("save", "commit"))
        self._touched = True
        raw = self._session.request_once("POST", wire.COMMIT, params={}, payload=copy.deepcopy(payload), phase="save")
        wire.checked_response(raw)
        require(raw["session_id"] == self.session_id and raw["platform_version"] == self.profile["platform_version"] and
                raw["request_id"] not in self._request_ids, "RESPONSE_SESSION_OR_REPLAY")
        self._request_ids.add(raw["request_id"])
        return raw

    def accept_receipt(self, raw):
        require(("save", "commit") in self._used, "SEND_REQUIRED")
        self._receipt = wire.decode_receipt(raw, self.profile, self._payload)
        require(self._receipt["platform_question_id"] not in
                {q["platform_question_id"] for q in self._plan["baseline"]["view"]["target"]["questions"]},
                "RECEIPT_NOT_NEW_QUESTION")
        if hasattr(self._session, "bind_receipt"):
            self._session.bind_receipt(self._receipt)
        return copy.deepcopy(self._receipt)

    def resume_readonly(self, plan, receipt, release):
        self._bound()
        require(plan["frames"] == self._fact["frames"] and plan["approved_parts"] == self._fact["parts"] and
                plan["action"]["target"]["question_id"] == self._fact["question_id"] and
                plan["payload"] == wire.build_payload(plan, self.profile), "FROZEN_PLAN_SOURCE_BINDING")
        require(self.readonly and self.profile is not None and not self._used and
                release.get("released") is True and release.get("session_id") == self.profile["session"]["session_id"] and
                release.get("session_id") != self.session_id and release.get("profile_hash") == digest(self.profile),
                "REOPEN_CHAIN")
        require(receipt.get("payload_hash") == digest(plan["payload"]) and
                receipt.get("evidence_mode") == self.profile["mode"] and
                plan["wire_profile_hash"] == digest(self.profile), "RECEIPT_PLAN_BINDING")
        self._plan, self._payload = copy.deepcopy(plan), copy.deepcopy(plan["payload"])
        self._receipt, self._predecessor = copy.deepcopy(receipt), copy.deepcopy(release)
        if hasattr(self._session, "bind_receipt"):
            self._session.bind_receipt(receipt)

    def resume_reconcile(self, plan, release):
        require(self.readonly and self.profile is not None and not self._used and
                release.get("released") is True and release.get("session_id") == self.profile["session"]["session_id"] and
                release.get("session_id") != self.session_id and release.get("profile_hash") == digest(self.profile) and
                release.get("plan_hash") == digest(plan) and plan["wire_profile_hash"] == digest(self.profile), "REOPEN_CHAIN")
        self._plan, self._payload, self._predecessor = copy.deepcopy(plan), copy.deepcopy(plan["payload"]), copy.deepcopy(release)

    def close(self):
        require(not self._closed, "TRANSPORT_ALREADY_RELEASED")
        self._closed = True
        if self.profile is None:
            if isinstance(self._session, CurrentPageIO):
                return self._session.close()
            return {"released": True, "session_created": False, "platform_calls": 0}
        released = self._session.close()
        require(isinstance(released, dict) and released.get("released") is True and
                released.get("session_id") == self.session_id, "RELEASE_UNPROVEN")
        return dict(released, profile_hash=digest(self.profile), evidence_mode=self.profile["mode"],
                    plan_hash=digest(self._plan) if self._plan is not None else None,
                    receipt_hash=digest(self._receipt) if self._receipt is not None else None,
                    last_observation_hash=digest(self._last_observation) if hasattr(self, "_last_observation") else None,
                    read_count=len(self._ledger), save_count=int(("save", "commit") in self._used),
                    refresh_count=int(("refresh", "refresh") in self._used),
                    uploads=sum(("upload", row["fields"]["rect_id"]) in self._used for row in self.profile["wire"]["rows"]),
                    signature_count=int(("upload", "signature") in self._used), login=0, ocr=0)


def build_offline_command(plan):
    require(plan["mode"] == "OFFLINE", "OFFLINE_ONLY")
    return {"namespace": "A11_SYNTHETIC_OFFLINE_ONLY", "operation": "CREATE_FRAMES",
            "book_id": "46007447", "question_id": plan["action"]["target"]["question_id"],
            "directory_id": plan["action"]["expected_after"]["directory_id"],
            "insert_after_order": plan["insert_after_order"], "frames": plan["frames"],
            "approved_parts": plan["approved_parts"], "deletes": [], "uploads": [],
            "submit": False, "ocr": False}


def validate_offline_command(command):
    require(set(command) == {"namespace", "operation", "book_id", "question_id", "directory_id",
        "insert_after_order", "frames", "approved_parts", "deletes", "uploads", "submit", "ocr"},
        "UNAUTHORIZED_PAYLOAD_FIELD")
    require(command["namespace"] == "A11_SYNTHETIC_OFFLINE_ONLY" and command["book_id"] == "46007447"
            and command["operation"] == "CREATE_FRAMES" and command["deletes"] == [] and
            command["uploads"] == [] and command["submit"] is False and command["ocr"] is False,
            "FORBIDDEN_OPERATION")


def parse_business_receipt(value, *, offline, transport=None):
    if transport is not None:
        require(transport.offline is offline, "RECEIPT_PROVENANCE")
        return transport.accept_receipt(value)
    require(offline, "LIVE_RECEIPT_CODEC_UNAVAILABLE")
    require(isinstance(value, dict) and value.get("namespace") == "A11_SYNTHETIC_OFFLINE_ONLY" and
            value.get("business_code") == 0 and value.get("operation") == "inserted" and
            value.get("platform_question_id") and value.get("append_at_global_end") is True,
            "BUSINESS_RECEIPT_UNKNOWN")
    return value["platform_question_id"]


def decode_a05_history(value):
    """Historical whitelist decoder only; never returns content VERIFIED or live eligibility."""
    return {"historical_only": True, "frame_business_success": value.get("code") == 0,
            "content_status": "CONTENT_PENDING", "text_persistence_proved": False,
            "live_eligible": False, "submission_status": "NOT_SUBMITTED"}
