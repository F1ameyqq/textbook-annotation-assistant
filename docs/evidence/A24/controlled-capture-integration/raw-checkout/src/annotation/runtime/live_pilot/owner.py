"""A24 R1 concrete owned launcher/worker and original-context transaction.

The default backend is Windows + async Playwright. Test backends are accepted
only with a separately verified SYNTHETIC authority. Old activation/main paths
are never called. Existing native guard/Job/identity helpers are reused verbatim.
"""
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urlsplit, urlencode

from annotation.quality.live_pilot import PilotError, require
from annotation.runtime.live_pilot.authority import Authority, AUTHOR, COORDINATOR, PROFILE, TARGET, verify_authority, sha
from annotation.runtime.storage.common import canonical, digest

ORIGIN = "https://www.usense.com"
TOKENS = {"product": b"A24_FIRST_SAVE_R1_PRODUCT\n", "worker": b"A24_FIRST_SAVE_R1_WORKER\n",
          "occupancy": b"A24_FIRST_SAVE_R1_OCCUPANCY\n"}


def safe_error(error):
    # Never serialize exception messages, URLs, paths, response text or locals.
    code = getattr(error, "code", "")
    approved = {"OWNER_AUTHORITY_EXPIRED", "OWNER_SCOPE_CHANGED", "OWNER_NEW_DECISION_ACCEPTANCE_REQUIRED",
        "OWNER_DEPENDENCY_HASH", "OWNER_CROP_BYTES", "OWNER_PROFILE_MISMATCH", "OWNER_PROFILE_OCCUPIED",
        "OWNER_PROFILE_LOCK_PRESENT", "OWNER_CHILD_TIMEOUT", "OWNER_HELD_IDENTITY_MISMATCH", "OWNER_JOB_NOT_EMPTY",
        "OWNER_NATIVE_RELEASE_UNPROVEN", "OWNER_CONTEXT_RELEASE_UNPROVEN", "OWNER_RUNTIME_RELEASE_UNPROVEN",
        "OWNER_CALLBACK_RELEASE_UNPROVEN", "OWNER_BOOTSTRAP_FAILED", "OWNER_FIRST_SAVE_BLOCKED",
        "CURRENT_SCHEMA_UNBOUND", "CURRENT_SOURCE_MAPPING_UNPROVEN", "OWNER_PRIVATE_REQUEST_UNBOUND",
        "FIRST_SAVE_ACTIVATION_REQUIRED", "BUSINESS_RECEIPT_UNKNOWN", "UPLOAD_UNKNOWN", "OLD_CONTENT_INCOMPLETE",
        "OWNER_MARKER_EXISTS", "OWNER_OUTPUT_EXISTS", "OWNER_PARENT_GATE_REQUIRED", "SYNTHETIC_OWNER_CANNOT_LAUNCH"}
    return {"code": code if code in approved else "OWNER_ERROR", "type": type(error).__name__ if
            type(error).__name__ in ("PilotError", "OSError", "TimeoutError", "ValueError", "Error", "ContractError") else "OTHER"}


def save_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical(value))
        handle.flush()
        os.fsync(handle.fileno())


def claim(authority, stage):
    authority.check()
    path = authority.output / (stage + "-claimed.json")
    require(not path.exists(), "OWNER_MARKER_EXISTS")
    save_new(path, {"schema": "A24FirstSaveOwnerClaim/v1", "run_id": authority.data["run_id"],
        "authority_sha256": authority.raw_hash, "candidate_sha256": authority.data["refs"]["candidate"]["sha256"],
        "stage": stage, "scope_sha256": authority.data["scope_sha256"]})


def require_claim(authority, stage):
    actual = json.loads((authority.output/(stage+"-claimed.json")).read_bytes())
    require(actual == {"schema": "A24FirstSaveOwnerClaim/v1", "run_id": authority.data["run_id"],
        "authority_sha256": authority.raw_hash, "candidate_sha256": authority.data["refs"]["candidate"]["sha256"],
        "stage": stage, "scope_sha256": authority.data["scope_sha256"]}, "OWNER_PARENT_GATE_REQUIRED")


def load_framework(authority):
    """Import definitions only, after raw dependency and authority validation."""
    authority.check()
    require(not authority.synthetic, "SYNTHETIC_OWNER_CANNOT_LAUNCH")
    path = authority.package_root / "tools/a16_current_state_probe.py"
    name = "a24_first_save_r1_frozen_native_framework"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    # Its old main/authorize/markers/open_owned are deliberately never invoked.
    return module


class BootstrapPolicy:
    """Exact frozen bootstrap resources. Business API is only via wire slots."""
    business, request_urls, page_modes = {}, {}, {}
    _book_endpoint = None

    def __init__(self, authority):
        self.authority = authority
        self.scope = authority.plan["bootstrap"]
        self.static = {(v["kind"], v["path_sha256"]) for v in self.scope["static_path_hashes"]}

    def public_page(self, url):
        return False

    def decide(self, method, url, kind, redirected=False):
        from annotation.source.usense.current_readonly.policy import excluded_static, EXCLUDED_STATIC
        if excluded_static(method, url, kind, redirected):
            return False, EXCLUDED_STATIC  # Existing bounded denial only; never send.
        parsed = urlsplit(url)
        if redirected or method != "GET" or parsed.username or parsed.password or parsed.fragment:
            return False, "FIRST_SAVE_BOOTSTRAP_BLOCKED"
        if parsed.scheme != "https" or parsed.netloc != "www.usense.com":
            return False, "ORIGIN_BLOCKED"
        path_hash = hashlib.sha256(parsed.path.encode()).hexdigest()
        if url == TARGET and kind == "Document":
            return True, "NAVIGATION"
        if (kind, path_hash) in self.static and not parsed.query:
            return True, "STATIC"
        if parsed.path in self.scope["session_paths"] and kind in ("XHR", "Fetch") and not parsed.query:
            return True, "SESSION_GET"
        if parsed.path == self.scope["version_path"] and kind in ("XHR", "Fetch"):
            return True, "VERSION_CHECK"
        if parsed.path == "/qieti/api/claim_book/books" and kind in ("XHR", "Fetch"):
            return False, "EXPECTED_PASSIVE_DENIAL"
        return False, "PATH_BLOCKED"


def owner_guard_class(framework, authority):
    """Small bootstrap counter subclass; original guard code remains unchanged."""
    class OwnerGuard(framework.CurrentGuard):
        def __init__(self, context, page, policy):
            super().__init__(context, page, policy)
            self.owner_static_counts, self.owner_book_denials = {}, 0
            self.owner_authority_hash = authority.raw_hash

        def bootstrap_claim(self, layer, method, url, kind):
            authority.check()
            parsed = urlsplit(url)
            if method == "GET" and parsed.path == "/qieti/api/claim_book/books":
                self.owner_book_denials += 1
                require(self.owner_book_denials <= authority.plan["bootstrap"]["passive_book_denial_events"],
                        "OWNER_BOOTSTRAP_FAILED")
            signature = (kind, hashlib.sha256(parsed.path.encode()).hexdigest())
            if signature in {(v["kind"], v["path_sha256"]) for v in authority.plan["bootstrap"]["static_path_hashes"]}:
                phase = "refresh" if getattr(self, "passive_phase", None) == "refresh" else "bootstrap"
                key = (phase, layer, signature)
                self.owner_static_counts[key] = self.owner_static_counts.get(key, 0) + 1
                require(self.owner_static_counts[key] == 1, "OWNER_BOOTSTRAP_FAILED")

        async def route(self, route):
            request = route.request
            try:
                self.bootstrap_claim("context", request.method, request.url, framework.resource_type(request.resource_type))
            except BaseException as error:
                self.record_failure(error)
                await route.abort("blockedbyclient")
                return
            await super().route(route)

        async def paused(self, event):
            request = event.get("request", {})
            try:
                self.bootstrap_claim("native", request.get("method"), request.get("url", ""), event.get("resourceType"))
            except BaseException as error:
                self.record_failure(error)
                await self.session.send("Fetch.failRequest", {"requestId": event["requestId"], "errorReason": "BlockedByClient"})
                return
            await super().paused(event)

        async def capture(self, response):
            validate_capture_owner(authority, framework, self)
            await super().capture(response)
    return OwnerGuard


def capture_binding(authority):
    return {"schema": "A24OwnedPrivateCapture/v1", "run_id": authority.data["run_id"],
        "authority_sha256": authority.raw_hash, "candidate_sha256": authority.data["refs"]["candidate"]["sha256"],
        "scope_sha256": authority.data["scope_sha256"], "directory": str(authority.output / "private" / "source-capture")}


def bind_capture_owner(authority, framework, guard):
    """Bind only this fresh definitions module, never its historical output."""
    require(type(authority) is Authority, "VALIDATED_OWNER_AUTHORITY_REQUIRED")
    authority.check()
    require(getattr(guard, "owner_authority_hash", None) == authority.raw_hash and guard.output is None and
            not hasattr(framework, "a24_capture_owner_binding"), "OWNER_CAPTURE_ALREADY_BOUND")
    require(authority.output == Path(authority.data["output_directory"]) and authority.output == authority.output.resolve(),
            "OWNER_CAPTURE_PATH")
    framework.require_plain_path(authority.output)
    private = authority.output / "private"
    framework.require_plain_path(private, missing_leaf=True)
    private.mkdir(exist_ok=True)
    binding = capture_binding(authority)
    target = Path(binding["directory"])
    framework.require_plain_path(target, missing_leaf=True)
    require(not target.exists() and target != framework.LIVE_OUT, "OWNER_CAPTURE_PATH")
    target.mkdir(exist_ok=False)
    save_new(target / "capture-owner.json", binding)
    # CurrentGuard.capture retains its original output==LIVE_OUT check and xb.
    # This module was freshly loaded for this sole owner; old entrypoints stay inert.
    framework.LIVE_OUT = target
    framework.a24_capture_owner_binding = binding
    guard.output, guard.owner_capture_binding = target, binding


def validate_capture_owner(authority, framework, guard):
    authority.check()
    expected = capture_binding(authority)
    require(getattr(guard, "owner_authority_hash", None) == authority.raw_hash and
            getattr(guard, "owner_capture_binding", None) == expected and
            getattr(framework, "a24_capture_owner_binding", None) == expected and
            guard.output == framework.LIVE_OUT == Path(expected["directory"]), "OWNER_CAPTURE_BINDING")
    framework.require_plain_path(guard.output)
    framework.require_plain_path(guard.output / "capture-owner.json")
    require((guard.output / "capture-owner.json").read_bytes() == canonical(expected), "OWNER_CAPTURE_BINDING")


def capture_evidence(framework, guard):
    if guard is None or not hasattr(guard, "owner_capture_binding"):
        return {"status": "NOT_CONFIGURED", "assets": []}
    try:
        assets = []
        for asset in framework.public_assets(guard):
            raw_path = guard.output / asset["ref"]
            source_path = guard.output / (asset["ref"] + ".source.json")
            framework.require_plain_path(raw_path)
            framework.require_plain_path(source_path)
            raw, source = raw_path.read_bytes(), source_path.read_bytes()
            require(len(raw) == asset["size"] and sha(raw) == asset["sha256"], "OWNER_CAPTURE_BINDING")
            assets.append({**asset, "private_raw_ref": {"path": str(raw_path), "bytes": len(raw), "sha256": sha(raw)},
                "private_provenance_ref": {"path": str(source_path), "bytes": len(source), "sha256": sha(source)}})
        return {"status": "BOUND_PRIVATE_CAPTURE", "owner_binding": dict(guard.owner_capture_binding), "assets": assets,
                "source_urls_exported": False, "captured_code_executed_by_collector": False}
    except BaseException as error:
        return {"status": "CAPTURE_EVIDENCE_ERROR", "complete": False, "error": safe_error(error)}


def guard_evidence(guard):
    """Bounded projection of existing audit events only; never add a listener."""
    if guard is None:
        return {"status": "NOT_CREATED", "complete": True, "total_events": 0, "events": []}
    try:
        from annotation.source.usense.current_readonly.policy import FIXED, SESSION, VERSION_PATH, LOGIN_POST, BOOK
        templates = {urlsplit(ORIGIN + path).path.replace(BOOK, "{book_id}") for path in FIXED.values()}
        templates.update(SESSION | {VERSION_PATH, urlsplit(LOGIN_POST).path})
        query_names = {"t", "page", "pageSize", "status_list", "id", "title", "team_name", "username", "role", "is_admin",
                       "file_id", "pageNum", "annotationType", "type", "order_in_level"}
        booleans = {"redirect_hop", "main_navigation", "business_read", "scoped_source_read", "expected_passive_denial",
                    "expected_excluded_static_denial", "expected_excluded_path_denial", "expected_excluded_version_repeat"}
        def project(event):
            require(isinstance(event, dict), "GUARD_EVENT_PROJECTION")
            result = {}
            for key, value in event.items():
                if key == "decision":
                    require(value in ("ALLOW", "BLOCK"), "GUARD_EVENT_PROJECTION")
                elif key in ("method", "category", "source", "resource_type", "known_route"):
                    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_]{1,100}", value), "GUARD_EVENT_PROJECTION")
                elif key == "time":
                    require(isinstance(value, str) and re.fullmatch(r"[0-9T:+.Z-]{10,40}", value), "GUARD_EVENT_PROJECTION")
                elif key == "path_sha256":
                    require(value is None or isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value), "GUARD_EVENT_PROJECTION")
                elif key == "path_template":
                    require(value is None or value in templates, "GUARD_EVENT_PROJECTION")
                elif key == "query_parameter_names":
                    require(isinstance(value, list) and len(value) <= len(query_names) and all(v in query_names for v in value), "GUARD_EVENT_PROJECTION")
                elif key in ("query_names_redacted", "port"):
                    require(value is None and key == "port" or type(value) is int and 0 <= value <= 65535, "GUARD_EVENT_PROJECTION")
                elif key == "hostname":
                    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9.-]{1,253}", value), "GUARD_EVENT_PROJECTION")
                elif key == "scheme":
                    require(value in ("https", "http", "wss", "ws", "data", "blob", "OTHER"), "GUARD_EVENT_PROJECTION")
                elif key in booleans:
                    require(type(value) is bool, "GUARD_EVENT_PROJECTION")
                else:
                    continue  # No raw URL/query/body/token/exception fields.
                result[key] = value
            return result
        events = guard.events
        require(isinstance(events, list), "GUARD_EVENT_PROJECTION")
        failure = guard.failure
        require(failure is None or isinstance(failure, dict), "GUARD_EVENT_PROJECTION")
        first_failure = None if failure is None else {"exception_type": failure.get("exception_type") if
            failure.get("exception_type") in ("Stop", "PilotError", "TimeoutError", "Error", "OTHER") else "OTHER",
            "codes": [v for v in failure.get("codes", []) if isinstance(v, str) and re.fullmatch("[A-Z0-9_]{1,100}", v)][:8]}
        blocked = next((i for i, event in enumerate(events) if event.get("decision") == "BLOCK"), None)
        matched = next((i for i, event in enumerate(events) if first_failure and event.get("category") in first_failure["codes"]), None)
        retained = sorted(set(range(min(128, len(events)))) | ({blocked} if blocked is not None else set()) | ({matched} if matched is not None else set()))
        summary = guard.exclusion_summary()
        require(set(summary) == {"combined_guard_events", "completed_denial_calls", "event_limit", "double_layer_events_count_separately",
            "http_send_count", "dns_tcp_tls_activity", "script_necessity", "pending_callbacks"} and
            all(type(summary[k]) is int and summary[k] >= 0 for k in ("combined_guard_events", "completed_denial_calls", "event_limit", "pending_callbacks")) and
            summary["event_limit"] == 16 and summary["double_layer_events_count_separately"] is True and
            all(summary[k] == "UNKNOWN" for k in ("http_send_count", "dns_tcp_tls_activity", "script_necessity")), "GUARD_EVENT_PROJECTION")
        return {"status": "PROJECTED", "total_events": len(events), "retained_events": len(retained), "limit": 128,
            "maximum_retained": 130, "completeness_scope": "SAFE_EXISTING_EVENT_PROJECTION_ONLY",
            "selection": "FIRST_128_PLUS_EARLIEST_BLOCK_AND_FIRST_FAILURE_CATEGORY_MATCH", "truncated": len(retained) < len(events),
            "complete": len(retained) == len(events), "events": [{"index": i, **project(events[i])} for i in retained],
            "earliest_block_index": blocked, "first_failure_category_event_index": matched,
            "failure_event_link": "CATEGORY_MATCH_ONLY_NOT_CAUSAL_PROOF" if matched is not None else "NOT_RECORDED",
            "first_failure": first_failure, "exclusions": dict(summary), "settlement": {"sealed": guard.sealed,
                "shutdown_started": guard.shutdown_started, "stopped": guard.stopped, "pending_callbacks": summary["pending_callbacks"]}}
    except BaseException as error:
        return {"status": "PROJECTION_ERROR", "complete": False, "total_events": "UNKNOWN", "error": safe_error(error)}


def base_binding(authority):
    """Finite binding for prewrite acquisition even when server schema is unbound."""
    a = authority.data
    slots = [["acquire", "GET", ORIGIN + "/qieti/api/claim_book/books?{OFFICIAL_BOOK_QUERY}"],
             ["acquire", "GET", ORIGIN + "/qieti/api/annotate_ocr/directory/get?file_id=46007447"],
             ["acquire", "GET", ORIGIN + "/qieti/api/annotate_pic/get_manual_annotations_unified/46007447"],
             ["acquire", "GET", ORIGIN + "/qieti/api/annotate_ocr/export-paper-questions/46007447"]]
    return {"schema": "A24FirstSaveGuardBinding/v1", "activated": True, "lease_kind": "NEW_A24_FIRST_SAVE",
        "mode": a["role"], "evidence_mode": a["mode"], "decision_ref": a["refs"]["decision"]["sha256"],
        "independent_report_ref": a["refs"]["independent_report"]["sha256"], "request_hash": digest(authority.request),
        "profile_hash": digest(authority.schema_profile), "payload_hash": (authority.request.get("approval") or {}).get("payload_hash"),
        "session_id": a["run_id"], "executor": a["executor"], "request_slots": slots,
        "upload_objects": [], "identity_fields": {"user_id": ["id"], "username": ["username"]},
        "starts_at": a["not_before"], "ends_at": a["expires_at"], "platform_version": "UNBOUND",
        "owner_authority_hash": authority.raw_hash}


class WindowsBackend:
    """Concrete resource operations; never instantiated for an unverified authority."""
    def __init__(self, authority):
        authority.check()
        require(not authority.synthetic, "SYNTHETIC_OWNER_CANNOT_LAUNCH")
        self.authority = authority
        self.framework = load_framework(authority)
        self.runtime = self.context = self.guard = None
        self.bootstrap_steps = {}

    def profile(self):
        profile, fingerprint = self.framework.native.profile_binding()
        require(fingerprint == PROFILE, "OWNER_PROFILE_MISMATCH")
        return profile

    def occupancy(self, command, marker):
        record = supervise(self.authority, self.framework, command, "occupancy", marker, limit=4, expect_zero=True)
        require(record["stage_success"], "OWNER_PROFILE_OCCUPIED")
        return record

    async def open(self, profile, binding):
        from playwright.async_api import async_playwright
        from annotation.delivery.live_pilot.usense import make_first_save_guard
        self.authority.check()
        self.bootstrap_steps["runtime_start"] = "STARTED"
        self.runtime = await async_playwright().start()
        self.bootstrap_steps["runtime_start"] = "DONE"
        self.bootstrap_steps["context_launch"] = "STARTED"
        self.context = await self.runtime.chromium.launch_persistent_context(str(profile), channel="msedge", headless=True,
            offline=True, service_workers="block", ignore_https_errors=self.authority.data["ignore_https_errors"],
            accept_downloads=False, viewport={"width": 1440, "height": 1000}, timeout=15000,
            args=["--disable-session-crashed-bubble", "--disable-extensions"])
        self.bootstrap_steps["context_launch"] = "DONE"
        require(len(self.context.pages) == 1 and self.context.pages[0].url == "about:blank", "OWNER_BOOTSTRAP_FAILED")
        page = self.context.pages[0]
        page.set_default_timeout(5000)
        guard_class = owner_guard_class(self.framework, self.authority)
        self.guard = make_first_save_guard(guard_class, self.context, page, BootstrapPolicy(self.authority), binding)
        self.guard.profile = profile
        bind_capture_owner(self.authority, self.framework, self.guard)
        self.bootstrap_steps["guard_install"] = "STARTED"
        await self.guard.install()
        self.bootstrap_steps["guard_install"] = "DONE"
        self.context.on("page", lambda extra: self.guard.schedule(extra.close()))
        page.on("dialog", lambda dialog: self.guard.schedule(dialog.dismiss()))
        page.on("response", self.guard.response)
        self.guard.auth.arm_navigation(TARGET)
        self.bootstrap_steps["online"] = "STARTED"
        await self.context.set_offline(False)  # Both barriers installed first.
        self.bootstrap_steps["online"] = "DONE"
        self.bootstrap_steps["navigation"] = "STARTED"
        since = self.guard.navigation.begin("goto")
        try:
            response = await page.goto(TARGET, wait_until="domcontentloaded", timeout=45000)
        except BaseException as error:
            self.guard.navigation.end("goto", since, error)
            raise
        self.guard.navigation.end("goto", since, response=response)
        self.bootstrap_steps["navigation"] = "DONE"
        self.bootstrap_steps["session_completion"] = "STARTED"
        await self.framework.complete_current_session(page, self.guard)
        self.bootstrap_steps["session_completion"] = "DONE"
        self.bootstrap_steps["viewer_admission"] = "STARTED"
        await self.framework.admit_current_viewer(page, self.guard)
        self.bootstrap_steps["viewer_admission"] = "DONE"
        return page, self.context, self.guard

    async def close(self):
        release = {"context_created": self.context is not None, "context_closed": self.context is None,
            "runtime_created": self.runtime is not None, "runtime_stopped": self.runtime is None,
            "callback_pending": 0, "errors": []}
        if self.guard is not None:
            try:
                if not self.guard.stopped:
                    await self.framework.drain(self.guard)
            except BaseException as error:
                release["guard_drain_error"] = safe_error(error)
            try:
                self.guard.begin_shutdown()
            except BaseException as error:
                release["errors"].append(dict(safe_error(error), step="guard_shutdown"))
        if self.context is not None:
            try:
                await asyncio.wait_for(self.context.close(), 5)
                release["context_closed"] = True
            except BaseException as error:
                release["errors"].append(dict(safe_error(error), step="context_close"))
        if self.runtime is not None:
            try:
                await asyncio.wait_for(self.runtime.stop(), 3)
                release["runtime_stopped"] = True
            except BaseException as error:
                release["errors"].append(dict(safe_error(error), step="runtime_stop"))
        if self.guard is not None:
            try:
                await self.framework.settle_callbacks(self.guard, seconds=2)
                self.guard.sealed = True
                release["callback_pending"] = len(self.guard.callbacks) + sum(not t.done() for t in self.guard.tasks)
                release["guard_failure"] = self.guard.failure
            except BaseException as error:
                release["errors"].append(dict(safe_error(error), step="callback_settlement"))
        release["released"] = (release["context_closed"] and release["runtime_stopped"] and
                               release["callback_pending"] == 0 and not release["errors"])
        return release

    @property
    def asset_root(self):
        # Source originals stay in their retained directory; resource paths are
        # hash-bound relative to this controlled .local/stages root.
        return Path("D:/1800/.local/stages")

    def author_inputs(self):
        return self.authority.author_release["frozen_author_inputs"]


async def acquire_current_schema(authority, page, context, guard, binding):
    """Four exact prewrite reads, no invented export metadata and no write path."""
    require(authority.role == "AUTHOR_SAVE", "CURRENT_SCHEMA_ACQUISITION_AUTHOR_ONLY")
    from annotation.delivery.live_pilot.usense import CurrentPageIO
    io = CurrentPageIO(page, context, guard, asyncio.get_running_loop(), binding, synthetic=authority.synthetic, owner_authority=authority)
    result = {"status": "CURRENT_SCHEMA_UNBOUND", "write_allowed": False, "successors": "NOT_RUN", "reads": []}
    requests = [("book", "/qieti/api/claim_book/books", {}),
                ("directory", "/qieti/api/annotate_ocr/directory/get", {"file_id": "46007447"}),
                ("frames", "/qieti/api/annotate_pic/get_manual_annotations_unified/46007447", {}),
                ("export", "/qieti/api/annotate_ocr/export-paper-questions/46007447", {})]
    for slot, path, params in requests:
        authority.check()
        response = await io.fetch_async("GET", path, params=params, payload=None, phase="acquire")
        require(response["http_status"] == 200, "OWNER_FIRST_SAVE_BLOCKED")
        raw = response["body"].encode("utf-8")
        observation = {"slot": slot, "path_template": path, "query_keys": sorted(params),
                       "http_status": 200, "bytes": len(raw), "sha256": sha(raw)}
        if slot in ("directory", "frames", "export"):
            private = authority.output / "private" / (slot + "-snapshot.bin")
            private.parent.mkdir(parents=True, exist_ok=True)
            with private.open("xb") as handle:
                handle.write(raw)
            observation["controlled_raw_ref"] = {"path": str(private), "sha256": sha(raw), "bytes": len(raw)}
        # Unknown server fields remain private; no synthetic completeness row is added.
        result["reads"].append(observation)
    return result


async def run_owned_worker(authority, backend, *, occupancy_command=None):
    """One owner path for real and fake-owner validation, including every failure exit."""
    authority.check()
    require(authority.synthetic or type(backend) is WindowsBackend, "OBSERVED_OWNER_BACKEND_REQUIRED")
    result = {"schema": "A24FirstSaveOwnedWorker/v1", "run_id": authority.data["run_id"], "role": authority.role,
              "status": "ERROR", "first_error": None, "steps": {k: "NOT_RUN" for k in
              ("profile", "occupancy", "context", "bootstrap", "prewrite", "adapter", "release")}}
    binding = base_binding(authority)
    try:
        profile = backend.profile()
        result["steps"]["profile"] = "DONE"
        backend.occupancy(occupancy_command, TOKENS["occupancy"])
        result["steps"]["occupancy"] = "DONE"
        require(not any((profile / name).exists() for name in ("SingletonLock", "SingletonCookie", "lockfile")), "OWNER_PROFILE_LOCK_PRESENT")
        if authority.schema_profile is not None:
            from annotation.delivery.live_pilot.usense import build_guard_binding
            activation = {"schema": "A24FirstSaveActivation/v1", "activated": True,
                "mode": "AUTHOR_SAVE" if authority.role == "AUTHOR_SAVE" else "READONLY_REOPEN",
                "request_hash": digest(authority.request), "profile_hash": digest(authority.schema_profile),
                "decision_ref": authority.data["refs"]["decision"]["sha256"],
                "independent_report_ref": authority.data["refs"]["independent_report"]["sha256"],
                "dependency_manifest_hash": authority.data["refs"]["candidate"]["sha256"],
                "payload_hash": authority.request.get("approval", {}).get("payload_hash"),
                "session_id": authority.data["run_id"], "executor": authority.data["executor"],
                "starts_at": authority.data["not_before"], "ends_at": authority.data["expires_at"]}
            binding = build_guard_binding(authority.request, authority.schema_profile, activation)
            binding["owner_authority_hash"] = authority.raw_hash
            if authority.role == "AUTHOR_SAVE":
                binding["request_slots"].extend([["refresh", "GET", ORIGIN + path]
                    for path in authority.plan["bootstrap"]["session_paths"]])
        page, context, guard = await backend.open(profile, binding)
        result["steps"]["context"] = result["steps"]["bootstrap"] = "DONE"
        authority.check()
        result["steps"]["prewrite"] = "STARTED"
        if authority.schema_profile is None or authority.plan["body_admission"] == "CURRENT_SCHEMA_UNBOUND":
            result["prewrite"] = await acquire_current_schema(authority, page, context, guard, binding)
            result["steps"]["prewrite"] = "BLOCKED_UNBOUND_CURRENT_FACTS"
            result["status"] = "PREWRITE_BLOCKED_NO_EFFECT"
        else:
            from annotation.runtime.live_pilot.runner import apply_current_context, reopen_current_context
            result["steps"]["prewrite"] = "BOUND_CODEC_PENDING_FRESH_READS"
            result["steps"]["adapter"] = "STARTED"
            if authority.role == "AUTHOR_SAVE":
                result["adapter"] = await apply_current_context(authority.request, backend.asset_root, page=page,
                    context=context, guard=guard, binding=binding, owner_authority=authority)
            else:
                inputs = backend.author_inputs()
                result["adapter"] = await reopen_current_context(authority.request, backend.asset_root, page=page,
                    context=context, guard=guard, binding=binding, owner_authority=authority, **inputs)
            result["steps"]["adapter"] = "RETURNED_PENDING_FORMAL_REVIEW"
            returned = result["adapter"]
            passed = (all(q.get("state") in ("READBACK_PENDING_INDEPENDENT", "APPLIED_SYNTHETIC_WIRE")
                          for q in returned.get("questions", {}).values()) and bool(returned.get("questions"))) if authority.role == "AUTHOR_SAVE" else returned.get("status") == "REVIEW"
            result["status"] = ("AUTHOR_EVIDENCE_PENDING_REVIEW" if authority.role == "AUTHOR_SAVE" else
                                "INDEPENDENT_EVIDENCE_PENDING_FORMAL_REVIEW") if passed else "ERROR_STOPPED_NO_RETRY"
    except BaseException as error:
        result["first_error"] = safe_error(error)
        result["status"] = "ERROR_STOPPED_NO_RETRY"
    finally:
        result["guard_evidence_before_release"] = guard_evidence(getattr(backend, "guard", None))
        try:
            if isinstance(getattr(backend, "bootstrap_steps", None), dict):
                result["bootstrap_steps"] = dict(backend.bootstrap_steps)
            if getattr(backend, "guard", None) is not None and hasattr(backend.guard, "navigation"):
                result["navigation"] = backend.guard.navigation.snapshot()
        except BaseException as error:
            result["passive_evidence_error"] = safe_error(error)
        try:
            release = await backend.close()
        except BaseException as error:
            release = {"released": False, "first_error": safe_error(error), "outer_job_reap_required": True}
        result["guard_evidence_after_release"] = guard_evidence(getattr(backend, "guard", None))
        result["private_capture_evidence"] = capture_evidence(getattr(backend, "framework", None), getattr(backend, "guard", None))
        result["steps"]["release"] = "DONE" if release.get("released") is True else "UNKNOWN"
        result["release"] = release
        if release.get("released") is not True:
            result["status"] = "OWNER_RELEASE_UNPROVEN"
        result["resend_allowed"] = False
        save_new(authority.output / "worker-result.json", result)
    return result


def supervise(authority, framework, command, stage, token, *, limit, expect_zero=False):
    """Same held-handle/Job model; fresh stage tokens and fresh marker namespace."""
    authority.check()
    api = None
    job = child = None
    record = {"schema": "A24FirstSaveHeldOwner/v1", "stage": stage, "authority_sha256": authority.raw_hash,
              "before": None, "after": None, "job_active_final": None, "job_closed": False,
              "handle_closed": False, "errors": [], "state": "UNKNOWN", "stdin_token_sent_after_job_assignment": False}
    try:
        api_class, _ = framework.load_native()
        api = api_class()
        job = framework.OwnedJob()
        child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=0x08000000, env={k: v for k, v in os.environ.items() if k not in ("DEBUG", "PWDEBUG", "DEBUG_FILE")})
        record["before"] = api.held_identity(int(child._handle))
        job.assign(child)
        record["job_assigned"] = True
        record["stdin_token_sent_after_job_assignment"] = True
        remaining = min(limit, (authority.expires_at-datetime.now(timezone.utc)).total_seconds()-6)
        require(remaining > 0, "OWNER_AUTHORITY_EXPIRED")
        output, errors = child.communicate(input=token, timeout=remaining)
        private = authority.output / "private"
        private.mkdir(parents=True, exist_ok=True)
        raw_refs = {}
        for label, raw in (("stdout", output), ("stderr", errors)):
            path = private / ("owner-" + stage + "-" + label + ".bin")
            with path.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            raw_refs[label] = {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}
        record["controlled_raw_output_refs"] = raw_refs
        record.update(stdout_bytes=len(output), stdout_sha256=sha(output), stderr_bytes=len(errors), stderr_sha256=sha(errors))
        if expect_zero:
            framework.native.accept_occupancy_zero(output, errors, child.returncode)
            record["matching_profile_processes"] = 0
        else:
            require(not errors, "OWNER_NATIVE_RELEASE_UNPROVEN")
            projection = json.loads(output)
            require(isinstance(projection, dict) and set(projection) == {"schema", "stage", "status", "released"} and
                    projection["schema"] == "A24FirstSaveStageResult/v1" and projection["stage"] == stage,
                    "OWNER_NATIVE_RELEASE_UNPROVEN")
            record["child_projection"] = projection
    except BaseException as error:
        record["errors"].append(safe_error(error))
    finally:
        if child is not None:
            try:
                if child.poll() is None:
                    if record.get("job_assigned"):
                        job.terminate()
                    else:
                        child.kill()
                    child.wait(timeout=2)
                record["after"] = api.held_identity(int(child._handle))
                require(all(type(v.get(k)) is int and v[k] > 0 for v in (record["before"], record["after"])
                            for k in ("pid", "created_filetime")) and
                        all(record["before"][k] == record["after"][k] for k in ("pid", "created_filetime")) and
                        record["after"].get("exit_observed") is True, "OWNER_HELD_IDENTITY_MISMATCH")
                record["creation_identity_match"] = True
            except BaseException as error:
                record["errors"].append(safe_error(error))
            finally:
                for stream in (child.stdin, child.stdout, child.stderr):
                    if stream is not None and not stream.closed:
                        try:
                            stream.close()
                        except BaseException as error:
                            record["errors"].append(safe_error(error))
                try:
                    child._handle.Close()
                    record["handle_closed"] = True
                except BaseException as error:
                    record["errors"].append(safe_error(error))
        if job is not None:
            try:
                count = job.active()
                if count:
                    job.terminate()
                    deadline = time.monotonic()+2
                    while count and time.monotonic() < deadline:
                        time.sleep(.02)
                        count = job.active()
                record["job_active_final"] = count
            except BaseException as error:
                record["errors"].append(safe_error(error))
            finally:
                try:
                    job.close()
                    record["job_closed"] = True
                except BaseException as error:
                    record["errors"].append(safe_error(error))
        record["released"] = (record.get("creation_identity_match") is True and record["handle_closed"] and
                              record["job_closed"] and record["job_active_final"] == 0)
        record["state"] = "RELEASED" if record["released"] else "UNKNOWN"
        record["stage_success"] = record["released"] and not record["errors"] and record.get("after", {}).get("exit_code") == 0
        save_new(authority.output / (stage + "-held-release.json"), record)
    return record


def stage_command(script, authority_path, authority_hash, stage):
    return [sys.executable, "-B", str(script), "run", "--authority", str(authority_path),
            "--authority-sha256", authority_hash, "--_stage", stage]


def run_stage(authority, authority_path, script, stage):
    authority.check()
    if stage == "launcher":
        require(not authority.output.exists(), "OWNER_OUTPUT_EXISTS")
        authority.output.mkdir(parents=True, exist_ok=False)
    else:
        require(sys.stdin.buffer.readline() == TOKENS[stage], "OWNER_PARENT_GATE_REQUIRED")
        require_claim(authority, "launcher" if stage == "product" else "product" if stage == "worker" else "worker")
    claim(authority, stage)
    framework = load_framework(authority)
    status, released = "ERROR", False
    try:
        if stage in ("launcher", "product"):
            child_stage = "product" if stage == "launcher" else "worker"
            record = supervise(authority, framework, stage_command(script, authority_path, authority.raw_hash, child_stage),
                               child_stage, TOKENS[child_stage], limit=880 if stage == "launcher" else 860)
            released = record["released"]
            status = record.get("child_projection", {}).get("status", "ERROR_STOPPED_NO_RETRY") if record["stage_success"] else "ERROR_STOPPED_NO_RETRY"
        elif stage == "occupancy":
            profile, fingerprint = framework.native.profile_binding()
            require(fingerprint == PROFILE, "OWNER_PROFILE_MISMATCH")
            api_class, count = framework.load_native()
            framework.native.emit_occupancy_count(count(api_class(), str(profile)))
            return 0
        else:
            backend = WindowsBackend(authority)
            result = asyncio.run(asyncio.wait_for(run_owned_worker(authority, backend,
                occupancy_command=stage_command(script, authority_path, authority.raw_hash, "occupancy")),
                timeout=max(.01, (authority.expires_at-datetime.now(timezone.utc)).total_seconds()-12)))
            released = result["release"].get("released") is True
            status = result["status"]
    except BaseException as error:
        save_new(authority.output / (stage + "-failure.json"), {"first_error": safe_error(error),
            "successors": "NOT_RUN", "resend_allowed": False})
    # Outer launcher's own running OS exit cannot be self-observed or fabricated.
    if stage == "launcher":
        save_new(authority.output / "launcher-summary.json", {"schema": "A24FirstSaveLauncherSummary/v1", "status": status,
            "owned_descendants_released": released, "launcher_own_exit_identity": "UNKNOWN_WHILE_RUNNING",
            "authority_sha256": authority.raw_hash, "coordinator_release_certificate_required_before_reopen": True})
    print(json.dumps({"schema": "A24FirstSaveStageResult/v1", "stage": stage, "status": status, "released": released}))
    return 0 if released and status in ("AUTHOR_EVIDENCE_PENDING_REVIEW", "INDEPENDENT_EVIDENCE_PENDING_FORMAL_REVIEW",
                                        "PREWRITE_BLOCKED_NO_EFFECT") else 2
