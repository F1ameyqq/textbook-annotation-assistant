"""Offline display check for one generated A30 native delivery.

Reuses the A28 check_display DOM checks, without its fixed question keys or
screenshots. No platform/transport imports, profile, save, export or retries.
Public inspect_delivery owns a fresh worker/browser through owned_process.py.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

HOLDER_SHA256 = "e21314716eb27dd7176fcd995fa137f806c1c6a9ec3750f2dd798f8a318e2063"
MATHJAX_SHA256 = "d4295dc33744836935c1399feece5159577b34c5c8ffb9f1c6324cd82e03a882"
FILES = ("index.html", "receipt.json", "mapping.json", "formulas.json", "assets/tex-svg.js")


def _need(value, code):
    if not value:
        raise ValueError(code)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _write(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def _local(path):
    path = Path(path).resolve()
    _need(not str(path).startswith(("\\\\", "//")), "LOCAL_DRIVE_REQUIRED")
    return path


class _Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        _need(tag not in ("base", "iframe", "object", "embed"), "UNEXPECTED_ACTIVE_ELEMENT")
        if tag == "img":
            _need(attrs.get("src", "").startswith(("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")), "INLINE_IMAGE_REQUIRED")
            width, height = int(attrs["width"]), int(attrs["height"])
            _need(width > 0 and height > 0, "POSITIVE_IMAGE_DIMENSIONS_REQUIRED")
            self.images.append({"width": width, "height": height})
        if tag == "script" and "src" in attrs:
            _need(attrs["src"] == "assets/tex-svg.js", "ONLY_LOCAL_MATHJAX_SCRIPT_ALLOWED")

    handle_startendtag = handle_starttag


def _snapshot(delivery):
    paths = {name: (delivery / name).resolve() for name in FILES}
    _need(all(path.is_relative_to(delivery) and path.is_file() for path in paths.values()), "DELIVERY_FILES_REQUIRED_INSIDE_TARGET")
    raw = {name: path.read_bytes() for name, path in paths.items()}
    hashes = {name: _sha(data) for name, data in raw.items()}
    _need(hashes["assets/tex-svg.js"] == MATHJAX_SHA256, "FIXED_MATHJAX_CHANGED")
    receipt = json.loads(raw["receipt.json"])
    mapping = json.loads(raw["mapping.json"])
    formulas = json.loads(raw["formulas.json"])
    _need(receipt.get("schema") == "CustomerNativeDelivery/v1", "A30_NATIVE_DELIVERY_REQUIRED")
    _need(isinstance(mapping, list) and mapping and isinstance(formulas, list), "DELIVERY_INDEX_REQUIRED")
    _need(receipt["mapped_count"] == len(mapping) and receipt["formula_count"] == len(formulas), "INDEX_COUNTS_DIFFER")
    _need(len({row["id"] for row in formulas}) == len(formulas), "DUPLICATE_FORMULA_ID")
    parser = _Images()
    parser.feed(raw["index.html"].decode("utf-8")); parser.close()
    return {"hashes": hashes, "formulas": formulas, "images": parser.images,
            "titles": ["第 " + row["printed_number"] + " 题" for row in mapping]}


def _allowed_url(url, delivery):
    # No file traversal, UNC, HTTP(S), WebSocket, blob, external CSS or fonts.
    return url.startswith(("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")) or url in {
        (delivery / "index.html").as_uri(), (delivery / "assets/tex-svg.js").as_uri()}


DOM_SCRIPT = r"""() => {
  const inside = (box, parent) => !!parent && box.left >= parent.left - 1 && box.right <= parent.right + 1;
  return {
    articles: [...document.querySelectorAll('article')].map(e => ({title:e.querySelector('h2')?.textContent,
      overflow:e.scrollWidth > e.clientWidth + 1})),
    formulas: [...document.querySelectorAll('.formula')].map(e => {
      const b=e.getBoundingClientRect(), p=e.closest('article')?.getBoundingClientRect();
      const boxes=[...e.querySelectorAll('mjx-container,svg')].map(x=>x.getBoundingClientRect());
      return {id:e.id,tex:e.dataset.tex,containers:e.querySelectorAll('mjx-container').length,
        svgCount:e.querySelectorAll('svg').length,merror:e.querySelectorAll('[data-mml-node="merror"],merror,mjx-merror').length,
        width:b.width,height:b.height,insideArticle:inside(b,p)&&boxes.every(x=>inside(x,p)),
        visibleSvg:boxes.some(x=>x.width>0&&x.height>0)};
    }),
    images:[...document.images].map(e=>{const b=e.getBoundingClientRect(),p=e.closest('article')?.getBoundingClientRect();return {
      complete:e.complete,naturalWidth:e.naturalWidth,naturalHeight:e.naturalHeight,width:b.width,height:b.height,
      insideArticle:inside(b,p),aspectError:Math.abs((b.width/b.height)/(e.naturalWidth/e.naturalHeight)-1)}}),
    errors:[...document.querySelectorAll('[data-mml-node="merror"],merror,mjx-merror')].map(e=>e.textContent),
    documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth
  };
}"""


def _validate_dom(dom, expected):
    _need([x["title"] for x in dom["articles"]] == expected["titles"], "ARTICLE_SEQUENCE")
    _need(not any(x["overflow"] for x in dom["articles"]), "ARTICLE_OVERFLOW")
    forms = dom["formulas"]
    _need([(x["id"], x["tex"]) for x in forms] == [(x["id"], x["tex"]) for x in expected["formulas"]], "FORMULA_SEQUENCE")
    _need(not dom["errors"] and all(x["containers"] == 1 and x["svgCount"] >= 1 and x["merror"] == 0 and x["width"] > 0 and x["height"] > 0 and x["insideArticle"] and x["visibleSvg"] for x in forms), "FORMULA_RENDER_LAYOUT")
    _need(dom["documentWidth"] <= dom["viewportWidth"] + 1, "PAGE_OVERFLOW")
    _need(len(dom["images"]) == len(expected["images"]), "IMAGE_COUNT")
    for actual, image in zip(dom["images"], expected["images"]):
        _need(actual["complete"] and actual["naturalWidth"] == image["width"] and actual["naturalHeight"] == image["height"] and actual["width"] > 0 and actual["height"] > 0 and actual["insideArticle"] and actual["aspectError"] < .001, "IMAGE_DECODE_OR_LAYOUT")


async def _worker(delivery, output, channel):
    result = {"schema": "CustomerDeliveryDisplayCheck/v1", "status": "STARTED", "started_at": _now(),
              "delivery": str(delivery), "profile_used": False, "scope": "LOCAL_DISPLAY_ONLY",
              "blocked_requests": [], "console_errors": [], "page_errors": [], "release_errors": [],
              "context_closed": True, "browser_closed": True, "runtime_stopped": True,
              "save_calls": 0, "export_calls": 0, "recheck_allowed": True}
    runtime = browser = context = None
    try:
        expected = _snapshot(delivery)
        result["inputs"] = expected["hashes"]
        from playwright.async_api import async_playwright
        result["runtime_stopped"] = False
        runtime = await async_playwright().start()
        result["browser_closed"] = False
        browser = await runtime.chromium.launch(channel=channel, headless=True, timeout=15000,
            args=["--disable-background-networking", "--disable-extensions", "--disable-component-update",
                  "--disable-sync", "--no-first-run", "--proxy-server=http://127.0.0.1:9",
                  "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost"])
        result["browser_version"] = browser.version
        result["context_closed"] = False
        context = await browser.new_context(offline=True, service_workers="block", accept_downloads=False,
                                            viewport={"width": 1440, "height": 1000}, device_scale_factor=1)

        async def route(request):
            if _allowed_url(request.request.url, delivery):
                await request.continue_()
            else:
                result["blocked_requests"].append({"kind": "request", "scheme": urlsplit(request.request.url).scheme,
                                                    "url_sha256": _sha(request.request.url.encode())})
                await request.abort("blockedbyclient")

        async def websocket(socket):
            result["blocked_requests"].append({"kind": "websocket", "url_sha256": _sha(socket.url.encode())})
            await socket.close(code=1008, reason="Offline delivery only")

        await context.route("**/*", route)
        await context.route_web_socket("**/*", websocket)
        page = await context.new_page()
        page.on("pageerror", lambda exc: result["page_errors"].append(str(exc)))
        page.on("console", lambda msg: result["console_errors"].append(msg.text) if msg.type == "error" else None)
        await page.goto((delivery / "index.html").as_uri(), wait_until="load", timeout=15000)
        await page.wait_for_function("window.MathJax && MathJax.startup && MathJax.startup.promise", timeout=15000)
        await asyncio.wait_for(page.evaluate("async()=>{await MathJax.startup.promise;await document.fonts.ready;await Promise.all([...document.images].map(i=>i.decode()));return true}"), 20)
        result["dom"] = await page.evaluate(DOM_SCRIPT)
        _validate_dom(result["dom"], expected)
        _need(not result["blocked_requests"] and not result["page_errors"] and not result["console_errors"], "RENDER_ERROR_OR_BLOCKED_REQUEST")
        result["status"] = "AUTOMATED_DISPLAY_CHECK_PASSED"
    except BaseException as exc:
        result.update(status="DISPLAY_CHECK_FAILED", error_type=type(exc).__name__, error=str(exc))
    finally:
        for resource, method, field in ((context, "close", "context_closed"), (browser, "close", "browser_closed"), (runtime, "stop", "runtime_stopped")):
            if resource is not None:
                try:
                    await asyncio.wait_for(getattr(resource, method)(), 5)
                    result[field] = True
                except BaseException as exc:
                    result["release_errors"].append({"phase": field, "type": type(exc).__name__})
        try:
            if "inputs" in result:
                _need(_snapshot(delivery)["hashes"] == result["inputs"], "DELIVERY_CHANGED_DURING_CHECK")
        except BaseException as exc:
            result.update(status="DISPLAY_CHECK_FAILED", error_type=type(exc).__name__, error=str(exc))
        if not all(result[k] for k in ("context_closed", "browser_closed", "runtime_stopped")) or result["release_errors"]:
            result["status"] = "RELEASE_UNPROVEN"
        result["finished_at"] = _now()
        _write(output / "worker-result.json", result)
    return result


def inspect_delivery(delivery, output, *, holder_path=None, channel="msedge", seconds=100):
    """Check an existing delivery; output must be a NEW directory outside it.

    Each explicit call can recheck the same unchanged delivery after a local
    rendering issue. It never resaves, exports, or modifies delivery/job state.
    The app supplies paths from its own job record; customers need no manifest.
    """
    delivery, output = _local(delivery), _local(output)
    _need(not output.is_relative_to(delivery) and not delivery.is_relative_to(output), "SEPARATE_CHECK_OUTPUT_REQUIRED")
    _need(channel in ("msedge", "chrome", "chromium") and 60 <= seconds <= 180, "BOUNDED_BROWSER_CONFIGURATION_REQUIRED")
    holder_path = _local(holder_path or Path(__file__).resolve().parents[3] / "tools/owned_process.py")
    _need(_sha(holder_path.read_bytes()) == HOLDER_SHA256, "FROZEN_HOLDER_CHANGED")
    output.mkdir(parents=True, exist_ok=False)
    result = {"schema": "CustomerDeliveryDisplayCheck/v1", "status": "DISPLAY_CHECK_FAILED",
              "delivery": str(delivery), "started_at": _now(), "recheck_allowed": True,
              "save_calls": 0, "export_calls": 0, "owned_os_release_confirmed": False}
    try:
        _snapshot(delivery)  # fail before starting any worker/browser
        spec = importlib.util.spec_from_file_location("customer_display_owned_process", holder_path)
        holder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(holder)
        process = holder.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--worker",
                              "--delivery", str(delivery), "--output", str(output), "--channel", channel],
                             output, output / "browser", seconds)
        worker_path = output / "worker-result.json"
        if worker_path.is_file():
            result.update(json.loads(worker_path.read_bytes()))
        result["process_record"] = str(output / "browser.process.json")
        result["owned_os_release_confirmed"] = process.get("owned_os_release_confirmed") is True
        if not result["owned_os_release_confirmed"]:
            result["status"] = "RELEASE_UNPROVEN"
        elif process.get("exit_code") != 0 or process.get("timeout"):
            result["status"] = "DISPLAY_CHECK_FAILED"
        result["process_record_sha256"] = _sha((output / "browser.process.json").read_bytes())
    except BaseException as exc:
        result.update(status="DISPLAY_CHECK_FAILED", error_type=type(exc).__name__, error=str(exc))
    result["finished_at"] = _now()
    _write(output / "display-check.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delivery", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--holder-path")
    parser.add_argument("--channel", default="msedge", choices=("msedge", "chrome", "chromium"))
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        result = asyncio.run(_worker(_local(args.delivery), _local(args.output), args.channel))
    else:
        result = inspect_delivery(args.delivery, args.output, holder_path=args.holder_path, channel=args.channel)
    print(json.dumps({k: result.get(k) for k in ("status", "owned_os_release_confirmed", "error")}))
    return 0 if result["status"] == "AUTOMATED_DISPLAY_CHECK_PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
