"""Bounded subprocess/evidence support for the all-synthetic A03 demos.

The harness never infers target effects from process markers. Markers only expose
control-flow arrival; a different process must reopen and read the target store.
No process outside this harness's Popen registry is ever signalled.
"""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2,
                  allow_nan=False)
        stream.write("\n")
    return path


class OwnedProcess:
    """One real process, its immutable request, streams and bounded lifetime."""

    def __init__(self, owner, name, argv, request=None):
        self.owner = owner
        self.name = name
        self.directory = owner.output / name
        self.directory.mkdir(parents=True, exist_ok=False)
        self.argv = [str(arg) for arg in argv]
        if request is not None:
            write_new(self.directory / "request.json", request)
        self.started_at = utc_now()
        self.started = time.monotonic()
        self.events = queue.Queue()
        self.lines = []
        self.error_lines = []
        self.forced_termination = False
        env = dict(os.environ)
        # Pin the exact checkout; do not borrow an installed annotation package.
        env["PYTHONPATH"] = str(owner.root / "src")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        self.child = subprocess.Popen(
            self.argv, cwd=str(owner.root), env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
            bufsize=1,
        )
        self.pid = self.child.pid
        owner.owned.append(self)
        self.readers = [
            threading.Thread(target=self._read, args=(self.child.stdout, self.lines,
                                                     "stdout.log", True), daemon=True),
            threading.Thread(target=self._read, args=(self.child.stderr, self.error_lines,
                                                     "stderr.log", False), daemon=True),
        ]
        for reader in self.readers:
            reader.start()
        write_new(self.directory / "launch.json", {
            "argv": self.argv, "cwd": str(owner.root), "pid": self.pid,
            "started_at": self.started_at,
            "pythonpath": env["PYTHONPATH"],
            "timeout_seconds": owner.timeout,
        })
        self.finished = None

    def _read(self, stream, destination, filename, parse):
        with (self.directory / filename).open("x", encoding="utf-8", newline="\n") as log:
            for line in stream:
                destination.append(line)
                log.write(line)
                log.flush()
                if parse:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        event = {"unparsed_stdout": line.rstrip("\r\n")}
                    self.events.put(event)
        stream.close()
        if parse:
            self.events.put({"stream_closed": True})

    def wait_event(self, predicate, timeout=5.0):
        """Await an observed child event, never a guessed fixed sleep."""
        deadline = time.monotonic() + min(timeout, self.owner.timeout)
        observed = []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("bounded marker wait expired: " + self.name)
            try:
                event = self.events.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError("bounded marker wait expired: " + self.name)
            observed.append(event)
            if predicate(event):
                write_new(self.directory / ("observed-marker-%d.json" % len(observed)),
                          {"observed_at": utc_now(), "event": event})
                return event
            if event.get("stream_closed"):
                raise RuntimeError("process ended before expected marker: " + self.name)

    def stop_owned(self):
        if self.child.poll() is None:
            self.forced_termination = True
            self.child.terminate()
            try:
                self.child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.child.kill()
                self.child.wait(timeout=5)
        return self.finish()

    def finish(self, timeout=None):
        if self.finished is not None:
            return self.finished
        limit = self.owner.timeout if timeout is None else min(timeout, self.owner.timeout)
        try:
            code = self.child.wait(timeout=max(0.01, limit))
        except subprocess.TimeoutExpired:
            self.forced_termination = True
            self.child.terminate()
            try:
                code = self.child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.child.kill()
                code = self.child.wait(timeout=5)
        for reader in self.readers:
            reader.join(timeout=2)
        parsed = []
        for line in self.lines:
            try:
                parsed.append(json.loads(line))
            except ValueError:
                pass
        self.finished = {
            "name": self.name, "pid": self.pid, "argv": self.argv,
            "cwd": str(self.owner.root), "exit_code": code,
            "started_at": self.started_at, "ended_at": utc_now(),
            "elapsed_seconds": round(time.monotonic() - self.started, 6),
            "forced_termination": self.forced_termination,
            "stdout_json": parsed, "alive": self.child.poll() is None,
        }
        write_new(self.directory / "completion.json", self.finished)
        return self.finished


class ProcessHarness:
    def __init__(self, root, output, *, timeout=65.0):
        self.root = Path(root).resolve()
        self.output = Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=False)
        self.timeout = timeout
        self.owned = []

    def launch(self, name, argv, request=None):
        return OwnedProcess(self, name, argv, request)

    def cli(self, name, request):
        request_path = self.output / name / "request.json"
        return self.launch(name, [sys.executable, "-B", "-m",
                                 "annotation.runtime.recovery.cli",
                                 "--request", str(request_path)], request)

    def wait_file(self, path, *, process, timeout=5.0):
        """Wait for an actual persisted barrier marker; retain its original bytes."""
        path = Path(path)
        deadline = time.monotonic() + min(timeout, self.timeout)
        tick = threading.Event()
        while not path.exists():
            if process.child.poll() is not None:
                process.finish()
                raise RuntimeError("process ended before file marker: " + process.name)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("bounded file marker wait expired: " + str(path))
            tick.wait(min(0.01, remaining))
        raw = path.read_bytes()
        write_new(process.directory / "observed-file-marker.json", {
            "path": str(path), "observed_at": utc_now(),
            "bytes_utf8": raw.decode("utf-8", errors="replace"),
        })
        return raw

    def close(self):
        results = []
        for process in self.owned:
            results.append(process.stop_owned() if process.child.poll() is None
                           else process.finish())
        release = {"recorded_at": utc_now(), "owned_processes": len(results),
                   "remaining_owned_processes": sum(r["alive"] for r in results),
                   "pids": [r["pid"] for r in results],
                   "only_popen_registry_signalled": True}
        path = self.output / "process-release.json"
        if not path.exists():
            write_new(path, release)
        return release

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
