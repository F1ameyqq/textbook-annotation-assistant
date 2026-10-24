"""Concrete Usense transport using the existing capture/writer and A29 holder.

No action at import. Each call is made only by the explicit customer start/login
entry after local preparation. This module is not exercised by offline checks.
"""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit
import urllib.request
import uuid

from annotation.runtime.usense_live.config import configure, endpoints
from annotation.runtime.usense_live.update import loads, json_same
from . import native_plan, wire
from .store import Hold, byte_hash, digest, encoded

ROOT = Path(__file__).resolve().parents[3]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Hold("原图下载发生重定向，保留原记录并停止。")


class UsenseTransport:
    def __init__(self, store, settings, book):
        self.store, self.settings, self.book = store, settings, book
        if settings.get("platform_enabled") is not True:
            raise Hold("尚未完成首次平台配置。离线准备与审校可以继续。")
        self.profile = Path(settings["profile"]).resolve()
        self.ledger = self.profile.parent / "usense-existing-ledger"
        if not self.profile.is_dir() or not self.ledger.is_dir():
            raise Hold("原专用登录目录或账本缺失；请回到首次配置，不能替换原状态。")
        self.out = store.root / "native" / uuid.uuid4().hex
        self.out.mkdir(parents=True)
        self.sequence = 0
        self.processes = []
        self.intent = "customer-start:" + book + ":" + self.out.name

    def _config(self, orders=(), pages=(), *, login=False):
        self.sequence += 1
        path = self.out / f"config-{self.sequence}.json"
        configure(profile=self.profile, output_root=self.out, config_path=path,
                  coordinator="customer-desktop", executor="native-child", reviewer="independent-readback-process",
                  authorization_reference=self.intent, book_id=self.book, orders=orders, pages=pages,
                  source=not login, login=login, tls_approval_reference=self.settings.get("tls_reference"),
                  proxy_server=self.settings.get("proxy_server"), seconds=900)
        return path, byte_hash(path.read_bytes())

    def _child(self, args, label):
        prefix = self.out / (label + "-" + uuid.uuid4().hex)
        holder = ROOT / "tools/run_usense_owned.py"
        command = [sys.executable, "-I", "-B", str(holder), "--record-prefix", str(prefix),
                   "--seconds", "960", "live", "--", *map(str, args)]
        started = datetime.now(timezone.utc).isoformat()
        # The nested Windows Job owns descendants and publishes original stdout,
        # stderr and process identities. Do not substitute a bare Popen writer.
        completed = subprocess.run(command, capture_output=True, timeout=1000)
        (prefix.with_suffix(".holder.stdout")).write_bytes(completed.stdout)
        (prefix.with_suffix(".holder.stderr")).write_bytes(completed.stderr)
        record_path = prefix.with_suffix(".process.json")
        if not record_path.is_file():
            raise Hold("外层进程释放记录缺失；停止后继并保留原状态。")
        process = loads(record_path.read_bytes())
        self.processes.append({"record": str(record_path), "sha256": byte_hash(record_path.read_bytes()),
                               "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat()})
        if completed.returncode or process.get("exit_code") != 0 or process.get("owned_os_release_confirmed") is not True:
            raise Hold("原生子进程失败或释放未证；不能自动重试。")
        output = prefix.with_suffix(".stdout").read_bytes().decode("utf-8")
        try:
            return loads(output.strip().splitlines()[-1])
        except (ValueError, IndexError):
            raise Hold("原生子进程结果未知；保留原始输出，不能重发。") from None

    def login(self):
        path, sha = self._config(login=True)
        return self._child(["login", "--config", path, "--sha256", sha], "login")

    def _capture(self, orders=(), pages=()):
        path, sha = self._config(orders, pages)
        value = self._child(["capture", "--config", path, "--sha256", sha], "read")
        # The public CLI may wrap a summary. Raw captured bytes and their own
        # summary are the business evidence, not the wrapper's exit status.
        config = loads(path.read_bytes())
        directory = self.out / config["run_id"]
        summary = loads((directory / "capture-summary.json").read_bytes())
        if summary.get("status") != "NATIVE_GETS_CAPTURED" or summary.get("save_attempts") != 0 or summary.get("release", {}).get("context_runtime_release_confirmed") is not True:
            raise Hold("当前状态采集失败或登录失效。保留原记录；请先处理该任务。")
        expected = endpoints(orders, pages, source=True, book_id=self.book)
        if set(summary["captures"]) != set(expected):
            raise Hold("采集范围与本次选择不一致。")
        flat = {}
        for name in expected:
            raw = (directory / (name + ".json")).read_bytes()
            descriptor = summary["captures"][name]
            if descriptor["sha256"] != byte_hash(raw) or descriptor["status"] != 200 or descriptor["request_counts"] != {"context": 1, "native": 1}:
                raise Hold("当前原生响应字节或读取次数未证。")
            flat[name] = loads(raw)
        return flat

    def capture(self, job, *, previous_pages=None):
        numbers = sorted({p.get("viewer_page") for p in job["pages"] if p["kind"] == "image"}, key=lambda x: x or 0)
        if not numbers or any(type(number) is not int or not 1 <= number <= 9999 for number in numbers):
            raise Hold("请为原图填写它在书中的页面号。文字预览坐标不能生成平台题框。")
        flat = self._capture()
        _, questions = native_plan.directory_rows(flat["directory"])
        if len(questions) > 128:
            raise Hold("本版本完整保全上限为 128 旧题；当前书需增量库存适配，未开始保存。")

        def merge(incoming):
            for name, value in incoming.items():
                if name in flat and not json_same(flat[name], value):
                    raise Hold("分批采集期间平台目录或题框变化，停止保存。")
                flat[name] = value
        for first in range(1, len(questions) + 1, 6):
            merge(self._capture(range(first, min(first + 6, len(questions) + 1))))
        for first in range(0, len(numbers), 8):
            merge(self._capture(pages=numbers[first:first + 8]))
        pages = {} if previous_pages is None else previous_pages
        if previous_pages is None:
            for source in job["pages"]:
                if source["kind"] != "image":
                    continue
                number = source["viewer_page"]
                data = native_plan._response(flat[f"page_{number}"])
                native_plan.require(data.get("file_id") == self.book and type(data.get("pages")) is list and len(data["pages"]) == 1,
                                    "来源页记录缺失或书籍不一致。")
                page = data["pages"][0]
                native_plan.require(page.get("page_index") == number - 1, "来源页号不一致。")
                url = page.get("image", "")
                parsed = urlsplit(url)
                native_plan.require(parsed.scheme == "https" and parsed.netloc.endswith(".aliyuncs.com")
                    and not parsed.query and not parsed.fragment and not parsed.username and ("/" + self.book + "/") in parsed.path,
                    "来源原图 URL 未绑定本书官方图片路径。")
                raw = self._source_image(url, source)
                from PIL import Image
                import io
                with Image.open(io.BytesIO(raw)) as image:
                    dimensions = list(image.size)
                native_plan.require(dimensions == [source["width"], source["height"]], "原图尺寸不一致。")
                pages[source["raw_sha256"]] = {"book_id": self.book, "sha256": byte_hash(raw),
                    "dimensions": dimensions, "viewer_page": number, "image_url": url}
        return wire.snapshot(flat, self.book, pages), flat

    def _source_image(self, url, source):
        key = digest([url, source["raw_sha256"]])
        old = self.store.operation("source-download", key)
        if old:
            if old["state"] != "COMPLETE":
                raise Hold("此来源下载已有失败或未知记录，不能自动重试。")
            receipt = self.store.get(old["output"])
            native_plan.require(receipt["sha256"] == source["raw_sha256"], "原图缓存身份不一致。")
            raw = Path(source["raw_path"]).read_bytes()
            native_plan.require(byte_hash(raw) == receipt["sha256"], "原图缓存字节已改变。")
            return raw
        self.store.begin("source-download", key)
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
            with opener.open(url, timeout=30) as response:
                native_plan.require(response.status == 200, "原图下载未成功。")
                raw = response.read(64 * 1024 * 1024 + 1)
            native_plan.require(len(raw) <= 64 * 1024 * 1024 and byte_hash(raw) == source["raw_sha256"], "本地原图与当前书页字节不一致。")
            self.store.finish("source-download", key, "COMPLETE", {"url": url, "sha256": byte_hash(raw),
                               "bytes": len(raw), "observed_at": datetime.now(timezone.utc).isoformat()})
            return raw
        except BaseException as exc:
            self.store.finish("source-download", key, "FAILED_NO_RETRY", {"type": type(exc).__name__, "message": str(exc)})
            raise

    def write_once(self, product, flat, job):
        used = {f["source_sha256"] for f in product["candidate"]["frames"]}
        sources = [{"path": p["raw_path"], "sha256": p["raw_sha256"]} for p in job["pages"] if p["raw_sha256"] in used]
        plan = wire.make_wire_plan(product, flat, sources)
        work = self.out / ("write-" + product["key"])
        work.mkdir()
        baseline = work / "baseline"; baseline.mkdir()
        for name, value in flat.items():
            (baseline / (name + ".json")).write_bytes(encoded(value))
        path = work / "plan.json"; path.write_bytes(encoded(plan))
        config, sha = self._config()
        result = self._child(["--insert-writer", "--config", config, "--sha256", sha,
            "--plan", path, "--plan-sha256", byte_hash(path.read_bytes()), "--baseline", baseline,
            "--ledger-root", self.ledger, "--authorization-reference", self.intent], "writer")
        native_plan.require(result.get("status") == "INSERT_RECEIPT_REQUIRES_INDEPENDENT_ALL23_READBACK"
            and result.get("post_attempts") == 1 and result.get("post_layers") == {"context": 1, "native": 1}
            and result.get("release", {}).get("context_runtime_release_confirmed") is True,
            "保存结果未知，停止后继，不能重发。")
        receipt = self.out / result["run_id"] / "native-receipt.json"
        native_plan.require(byte_hash(receipt.read_bytes()) == result["receipt_sha256"], "原始保存回执已改变。")
        return {"receipt": loads(receipt.read_bytes()), "writer": result, "processes": list(self.processes)}
