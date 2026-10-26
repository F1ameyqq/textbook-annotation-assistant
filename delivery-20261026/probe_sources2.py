"""Read-only probe of whole-book source sqlite candidates.

Reports table row counts only. No writes, no OCR, no platform access.
"""
from __future__ import annotations

import os
import sqlite3
import sys

BASE = r"C:\Users\LIHAOYANG\Documents\Codex\2026-10-24\jian\work"
FILES = [
    "wholebook-source.sqlite",
    "wholebook-source-answer-materials-v2-fixed.sqlite",
    "wholebook-source-missing-triplets-fixed.sqlite",
    "wholebook-source-independent-roi-v2-fixed.sqlite",
]


def main() -> int:
    for name in FILES:
        path = os.path.join(BASE, name)
        if not os.path.exists(path):
            print("missing", name)
            continue
        uri = "file:///" + path.replace("\\", "/") + "?mode=ro"
        db = sqlite3.connect(uri, uri=True)
        try:
            tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            print("===", name, round(os.path.getsize(path) / 1048576, 1), "MB")
            for table in tables:
                try:
                    count = db.execute('SELECT COUNT(*) FROM "%s"' % table).fetchone()[0]
                except Exception as exc:  # noqa: BLE001
                    count = "ERR:%s" % exc
                print("    %-28s %s" % (table, count))
        finally:
            db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
