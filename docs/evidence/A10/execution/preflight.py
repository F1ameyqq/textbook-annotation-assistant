"""A10 single-round, read-only preflight; no retry command is provided.

prepare is entirely offline. run consumes the exclusive run marker once.
The frozen A04 dependencies are reused only for this bounded observation.
"""
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "docs/evidence/A10/execution"
STAGE = ROOT / ".local/stages/a10-preflight"
FROZEN = STAGE / "frozen"
WORKFLOW = "6dcea351b4be4608d4d2a185a4721b4daf6ba286"
A04 = "6c8137a4fadddc01a47906d564ab3460277c8958"
os.environ["GIT_NO_LAZY_FETCH"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True


def now():
    return datetime.now(timezone.utc).isoformat()


def write(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def digest(path):
    blob = Path(path).read_bytes()
    return {"sha256": hashlib.sha256(blob).hexdigest(), "size": len(blob)}


def git(*args):
    return subprocess.check_output(["git", "-c", "core.longpaths=true", *args], cwd=ROOT)


def processes():
    # CommandLine is never retrieved or serialized. Only own ancestry is retained.
    script = "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,CreationDate | ConvertTo-Json -Compress"
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                            capture_output=True, text=True, timeout=20,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError("PROCESS_METADATA_UNAVAILABLE")
    values = json.loads(result.stdout)
    return values if isinstance(values, list) else [values]


def descendants(rows, root_pid):
    owned = {root_pid}
    while True:
        more = {int(row["ProcessId"]) for row in rows if int(row["ParentProcessId"]) in owned}
        if more <= owned:
            break
        owned |= more
    return [row for row in rows if int(row["ProcessId"]) in owned]


def prepare():
    FROZEN.mkdir(parents=True, exist_ok=False)
    manifest = []
    paths = git("ls-tree", "-r", "--name-only", A04, "src").decode().splitlines()
    for relative in paths:
        blob = git("cat-file", "blob", A04 + ":" + relative)
        destination = FROZEN / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(blob)
        manifest.append({"origin": "A04_RAW_GIT", "commit": A04, "path": relative,
                         "git_blob": git("rev-parse", A04 + ":" + relative).decode().strip(),
                         "absolute_input": str(destination), **digest(destination)})
    for relative in ["AGENTS.md", "docs/coordination.md", "docs/development-plan.md",
                     "docs/tasks/A10-platform-readiness-preflight.md",
                     "docs/approvals/A10-platform-readonly-approval.json", "docs/local-login.md",
                     "tools/usense_login.py"]:
        blob = git("cat-file", "blob", WORKFLOW + ":" + relative)
        if (ROOT / relative).read_bytes() != blob:
            # CRLF checkout equivalence is not enough for executable inputs.
            if relative == "tools/usense_login.py":
                raise RuntimeError("LOGIN_HELPER_RAW_BYTES_DIFFER")
        destination = FROZEN / "workflow" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(blob)
        manifest.append({"origin": "WORKFLOW_RAW_GIT", "commit": WORKFLOW, "path": relative,
                         "git_blob": git("rev-parse", WORKFLOW + ":" + relative).decode().strip(),
                         "absolute_input": str(destination), **digest(destination),
                         "working_bytes_match": (ROOT / relative).read_bytes() == blob})
    sys.path.insert(0, str(FROZEN / "src"))
    import annotation.source.usense.collector
    import annotation.source.usense.viewer_observation
    import playwright.sync_api
    import PIL.Image
    imported = []
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if path and Path(path).is_file() and name.split(".")[0] in {
                "annotation", "playwright", "pydantic", "pydantic_core", "PIL", "greenlet", "pyee"}:
            imported.append({"module": name, "absolute_input": str(Path(path).resolve()), **digest(path)})
    for relative in ("docs/coordination-state.json", "tools/usense_login.py"):
        manifest.append({"origin": "CURRENT_LOCAL_INPUT", "path": relative,
                         "absolute_input": str(ROOT / relative), **digest(ROOT / relative)})
    for path in [Path(__file__), *FROZEN.rglob("*.py")]:
        ast.parse(path.read_text(encoding="utf-8-sig"))
    write("static-preparation.json", {"at": now(), "syntax": "PASS", "offline_import": "PASS",
          "platform_operations": 0, "browser_launches": 0,
          "versions": {name: importlib.metadata.version(name) for name in ("playwright", "Pillow", "pydantic")},
          "python": sys.version, "python_executable": sys.executable,
          "selected_viewer_pages": [14, 15, 173], "viewer10": "NOT_SELECTED_EXISTING_POLICY_SUPPORTS_14_15_173"})
    write("input-raw-manifest.json", {"frozen_at": now(), "workflow": WORKFLOW, "A04_reference": A04,
          "driver": {"absolute_input": str(Path(__file__).resolve()), **digest(__file__)},
          "inputs": manifest, "imported_runtime_files": imported,
          "secrets_and_profiles_in_manifest": False})


def worker():
    sys.path.insert(0, str(FROZEN / "src"))
    from annotation.runtime.browser.session import HeadlessSession
    from annotation.runtime.browser.lease import ProfileLease
    from annotation.runtime.browser.guard import BrowserSafetyError
    from annotation.source.usense.collector import (
        get_business, _book, _directory, _annotations, _subset, _original, _jump, _canvas_proof)
    from annotation.source.usense.parser import _image_inventory
    from annotation.source.usense.viewer_observation import DRAW_OBSERVER, READ_DRAW

    plan = ["profile_exclusivity", "login", "target_book", "directory", "frames", "source_metadata"]
    for viewer in (14, 15, 173):
        plan += [f"viewer{viewer}_identity", f"viewer{viewer}_original", f"viewer{viewer}_visible_geometry"]
    steps = {name: {"status": "NOT_RUN"} for name in plan}
    active = "profile_exclusivity"
    started = None
    elapsed_origin = None
    first_network_failure = None
    own_processes = []

    class Session(HeadlessSession):
        def _route(self, route):
            nonlocal started, elapsed_origin, first_network_failure, own_processes
            if started is None:
                started, elapsed_origin = now(), time.monotonic()
                write("live-start.json", {"at": started, "round": 1, "outer_seconds": 900})
                own_processes = descendants(processes(), os.getpid())
                write("owned-processes-during.json", {"at": now(), "processes": own_processes})
            if first_network_failure or time.monotonic() - elapsed_origin >= 900:
                route.abort("blockedbyclient")
                return
            before = len(self.audit.records)
            super()._route(route)
            for record in self.audit.records[before:]:
                if record["decision"] == "BLOCK" and record["category"] != "LOCAL_EMPTY_BOOTSTRAP":
                    first_network_failure = {"at": record["time"], "category": record["category"],
                                             "status": record["status"], "transport": dict(self.transport_failures)}
                    break

        def _response(self, response):
            nonlocal first_network_failure
            super()._response(response)
            if response.status >= 400 and first_network_failure is None:
                record = self.audit.records[-1]
                first_network_failure = {"at": record["time"], "category": record["category"],
                                         "status": record["status"], "transport": dict(self.transport_failures)}

    def check():
        if first_network_failure:
            raise BrowserSafetyError("RESOURCE_FAILED", "fetch")
        if elapsed_origin is not None and time.monotonic() - elapsed_origin >= 900:
            raise BrowserSafetyError("TIMEOUT", "collect")

    def step(name, action):
        nonlocal active
        active = name
        check()
        value = action()
        check()
        steps[name] = {"status": "PASS", "at": now()}
        return value

    session = Session(ROOT, ignore_https_errors=False, timeout_ms=30000, init_script=DRAW_OBSERVER)
    failure = None
    try:
        # Independent real-process and lock snapshot before the existing session
        # repeats its own atomic lease checks. No credential file is read here.
        profiles = [path for path in (ROOT / ".local/browser-profiles").iterdir() if path.is_dir()]
        if len(profiles) != 1:
            raise BrowserSafetyError("PROFILE_PATH_UNAVAILABLE", "preflight")
        probe = ProfileLease(profiles[0])
        snapshot = probe._snapshot()
        write("independent-profile-precheck.json", {"at": now(), **snapshot})
        if any(snapshot.values()):
            raise BrowserSafetyError("PROFILE_IN_USE", "preflight")
        steps[active] = {"status": "PASS", "at": now()}
        step("login", session.__enter__)
        def target():
            page = session.page
            page.get_by_role("button", name="选择书籍", exact=True).click()
            check()
            row = page.locator(".el-table__row").filter(has_text="46007447")
            row.wait_for(state="visible", timeout=30000)
            check()
            row.get_by_role("button", name="选择", exact=True).click()
            check()
            page.get_by_text("46007447", exact=False).first.wait_for(state="visible", timeout=30000)
            value = _book(get_business(session, "/qieti/api/claim_book/books?page=1&pageSize=10&id=46007447"))
            write("book.json", value)
            return value
        step("target_book", target)
        directory = step("directory", lambda: _directory(get_business(session, "/qieti/api/annotate_ocr/directory/get?file_id=46007447")))
        write("directory.json", directory)
        annotations = step("frames", lambda: _annotations(get_business(session, "/qieti/api/annotate_pic/get_manual_annotations_unified/46007447")))
        write("frames.json", annotations)
        source = step("source_metadata", lambda: get_business(session, "/qieti/api/annotate_pic/pre_annotation_source/46007447?annotationType=mr_pre"))
        write("source-metadata.json", _subset(source["data"], ("file_id", "total_pages", "annotation_type", "source", "manifest_exists")))
        for viewer, zone in ((14, 0), (15, 0), (173, 1)):
            def identity():
                raw = get_business(session, f"/qieti/api/annotate_pic/pre_annotation/46007447?pageNum={viewer}&annotationType=mr_pre")
                data = raw.get("data", {})
                pages = data.get("pages", [])
                if str(data.get("file_id")) != "46007447" or len(pages) != 1 or type(pages[0].get("page_index")) is not int:
                    raise BrowserSafetyError("TARGET_MISMATCH", "collect")
                session.policy.register_image(pages[0].get("image"))
                return pages[0]
            pg = step(f"viewer{viewer}_identity", identity)
            asset = OUT / f"assets/viewer-{viewer}.jpg"
            asset.parent.mkdir(exist_ok=True)
            def original():
                _original(session, pg["image"], asset)
                return _image_inventory(asset, "original")
            image = step(f"viewer{viewer}_original", original)
            write(f"viewer-{viewer}-identity.json", {"book_id": "46007447", "viewer_page": viewer,
                  "source_index": pg["page_index"], "resource_url_retained": False, **image})
            def geometry():
                _jump(session.page, zone, viewer)
                check()
                proof, canvas = _canvas_proof(session.page, zone, pg["page_index"], pg["image"])
                draw = session.page.evaluate(READ_DRAW, zone)
                if not draw or draw["source_index"] != pg["page_index"] or draw["natural_size"] != [image["width"], image["height"]]:
                    raise BrowserSafetyError("UI_MISMATCH", "verify")
                (OUT / f"assets/viewer-{viewer}-canvas.png").write_bytes(canvas)
                write(f"viewer-{viewer}-geometry.json", {"at": now(), "proof": proof, "draw": draw,
                      "scope": "Actual resource identity, natural size, canvas/CSS bounds and draw transform only; no full coordinate acceptance"})
            step(f"viewer{viewer}_visible_geometry", geometry)
    except Exception as exc:
        steps[active] = {"status": "FAIL", "at": now()}
        failure = {"step": active, "code": getattr(exc, "code", "PRECHECK_FAILED"),
                   "stage": getattr(exc, "stage", "prepare"), "first_network_failure": first_network_failure}
    finally:
        close_ok = session.close()
        ended = now()
        write("network-audit.json", session.audit.records)
        write("session-release.json", {"at": ended, "close_returned_success": close_ok, **session.report()})
        write("result.json", {"task": "A10", "workflow": WORKFLOW, "A04_reference": A04,
              "status": "FAILED_STOPPED" if failure else "READONLY_OBSERVATIONS_COMPLETE",
              "failure": failure, "steps": steps, "live_started_at": started, "live_ended_at": ended if started else None,
              "live_elapsed_seconds": round(time.monotonic()-elapsed_origin, 6) if elapsed_origin else 0,
              "rounds": int(started is not None), "attempt_markers": 1, "retries": 0,
              "business_writes": 0, "ocr_calls": 0, "paid_model_calls": 0,
              "login_attempted": session.policy.login_attempted,
              "viewer10": "NOT_SELECTED_EXISTING_POLICY_SUPPORTS_14_15_173",
              "whole_A04_accepted": False, "write_ready": False})
    return 2 if failure else 0


def run():
    frozen = json.loads((OUT / "input-raw-manifest.json").read_text(encoding="utf-8"))
    for item in [frozen["driver"], *frozen["inputs"], *frozen["imported_runtime_files"]]:
        # Mutable scheduler ownership is attested separately; only its frozen
        # prelaunch snapshot is retained, not treated as an executable input.
        if item.get("path") == "docs/coordination-state.json":
            continue
        if digest(item["absolute_input"]) != {key: item[key] for key in ("sha256", "size")}:
            raise RuntimeError("FROZEN_INPUT_CHANGED")
    state = json.loads((ROOT / "docs/coordination-state.json").read_text(encoding="utf-8-sig"))
    if state["tasks"]["A10"]["execution_agent"] != "/root/a10_platform_preflight" or state["platform_session"]["reservation_agent"] != "/root/a10_platform_preflight":
        raise RuntimeError("OWNERSHIP_NOT_CONFIRMED")
    write("run-once-marker.json", {"at": now(), "round_limit": 1, "owner": "/root/a10_platform_preflight",
          "input_manifest": digest(OUT / "input-raw-manifest.json"), "driver": digest(__file__)})
    child = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "worker"], cwd=ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    own = next((row for row in processes() if int(row["ProcessId"]) == child.pid), None)
    write("worker-created.json", {"at": now(), "process": own, "watchdog_seconds_from_spawn": 900})
    try:
        output, errors = child.communicate(timeout=900)
    except subprocess.TimeoutExpired:
        # The worker has a stricter deadline from spawn than first network use.
        # Do not terminate any process outside its verified ancestry.
        owned = descendants(processes(), child.pid)
        write("watchdog-timeout.json", {"at": now(), "owned": owned})
        for row in reversed(owned):
            check_rows = processes()
            if any(item["ProcessId"] == row["ProcessId"] and item["CreationDate"] == row["CreationDate"] for item in check_rows):
                subprocess.run(["taskkill.exe", "/PID", str(row["ProcessId"]), "/F"], capture_output=True)
        output, errors = child.communicate(timeout=20)
    identities = [own] if own else []
    during = OUT / "owned-processes-during.json"
    if during.exists():
        identities += json.loads(during.read_text(encoding="utf-8"))["processes"]
    current = processes()
    remaining = [row for row in identities if row and any(item["ProcessId"] == row["ProcessId"] and item["CreationDate"] == row["CreationDate"] for item in current)]
    write("worker-ended.json", {"at": now(), "exit_code": child.returncode,
          "stdout_bytes": len(output), "stderr_bytes": len(errors), "raw_output_not_persisted": True,
          "same_pid_and_creation_remaining": remaining, "release_confirmed": not remaining})
    print(json.dumps({"worker_exit_code": child.returncode, "owned_processes_remaining": len(remaining)}))


if __name__ == "__main__":
    try:
        command = sys.argv[1]
        if command == "prepare":
            prepare()
        elif command == "run":
            run()
        elif command == "worker":
            raise SystemExit(worker())
        else:
            raise RuntimeError("UNKNOWN_COMMAND")
    except Exception:
        print("A10_LOCAL_PREPARATION_OR_SUPERVISOR_FAILED_NO_RAW_DETAILS")
        raise SystemExit(3)
