"""Durable book ownership, immutable blobs, and no-retry operation records."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def byte_hash(value):
    return hashlib.sha256(value).hexdigest()


class Hold(ValueError):
    """A resumable missing input or an unresolved operation, never permission."""


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "blobs").mkdir(exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS operations(
                kind TEXT, key TEXT, state TEXT NOT NULL, output TEXT,
                PRIMARY KEY(kind,key));
            CREATE TABLE IF NOT EXISTS jobs(
                id TEXT PRIMARY KEY, book TEXT NOT NULL, head TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(
                seq INTEGER PRIMARY KEY, job TEXT, at REAL, event TEXT, body TEXT);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.root / "state.sqlite", timeout=15)
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def book_lock(self, book):
        # A kernel lock is released on process death. The durable operation
        # intent remains and blocks a second send after such a death.
        path = self.root / ("book-" + digest(str(book)) + ".lock")
        with path.open("a+b") as stream:
            if path.stat().st_size == 0:
                stream.write(b"\0"); stream.flush()
            stream.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (OSError, BlockingIOError):
                raise Hold("这本书已有任务在运行，请回到原任务。") from None
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def put(self, value):
        raw = encoded(value)
        key = byte_hash(raw)
        path = self.root / "blobs" / (key + ".json")
        if path.exists():
            if path.read_bytes() != raw:
                raise Hold("本地记录损坏，请保留工作目录。")
            return key
        temp = path.with_suffix("." + uuid.uuid4().hex + ".tmp")
        with temp.open("xb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        # Content-addressed identical writes are safe; partial blobs are never
        # published, even if an OCR process dies during serialization.
        os.replace(temp, path)
        return key

    def get(self, key):
        if not isinstance(key, str) or len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise Hold("本地记录编号无效。")
        raw = (self.root / "blobs" / (key + ".json")).read_bytes()
        if byte_hash(raw) != key:
            raise Hold("本地记录已改变。")
        return json.loads(raw)

    def operation(self, kind, key):
        with self.connect() as db:
            row = db.execute("SELECT state,output FROM operations WHERE kind=? AND key=?", (kind, key)).fetchone()
        return None if row is None else {"state": row[0], "output": row[1]}

    def begin(self, kind, key):
        try:
            with self.connect() as db:
                db.execute("INSERT INTO operations VALUES(?,?,?,NULL)", (kind, key, "INTENT"))
        except sqlite3.IntegrityError:
            raise Hold("已有执行记录；成功项直接复用，未知或失败项必须先对账，不能重发。") from None

    def finish(self, kind, key, state, value):
        ref = self.put(value)
        with self.connect() as db:
            changed = db.execute("UPDATE operations SET state=?,output=? WHERE kind=? AND key=? AND state='INTENT'",
                                 (state, ref, kind, key)).rowcount
            if changed != 1:
                raise Hold("操作记录已变化，停止后继。")
        return ref

    def resolve(self, kind, key, previous, value):
        """Preserve the original unknown receipt by reference; never erase it."""
        ref = self.put({**value, "previous_state": previous["state"], "previous_output": previous["output"]})
        with self.connect() as db:
            changed = db.execute("UPDATE operations SET state='COMPLETE',output=? WHERE kind=? AND key=? AND state=? AND output=?",
                (ref, kind, key, previous["state"], previous["output"])).rowcount
            if changed != 1:
                raise Hold("原未知记录已变化，停止对账。")
        return ref

    def save_job(self, job, expected=None, event="PREPARED"):
        head = self.put(job)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT head FROM jobs WHERE id=?", (job["id"],)).fetchone()
            if (row[0] if row else None) != expected:
                from annotation.recognition.content_review import ReviewConflict
                raise ReviewConflict("任务已更新，请刷新后再保存。")
            db.execute("INSERT OR REPLACE INTO jobs VALUES(?,?,?)", (job["id"], job["book_id"], head))
            db.execute("INSERT INTO events(job,at,event,body) VALUES(?,?,?,?)",
                       (job["id"], time.time(), event, head))
        return head

    def job(self, identity):
        with self.connect() as db:
            row = db.execute("SELECT head FROM jobs WHERE id=?", (identity,)).fetchone()
        if row is None:
            raise Hold("没有找到此任务。")
        return self.get(row[0]), row[0]
