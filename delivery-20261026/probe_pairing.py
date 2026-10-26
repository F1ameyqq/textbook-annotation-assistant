"""Read-only probe of pairing_status in the newest whole-book source DB.

Prints schema, status distribution and issue-kind distribution only.
"""
from __future__ import annotations

import collections
import os
import sqlite3
import sys

BASE = r"C:\Users\LIHAOYANG\Documents\Codex\2026-10-24\jian\work"
NAME = "wholebook-source.sqlite"


def main() -> int:
    path = os.path.join(BASE, NAME)
    uri = "file:///" + path.replace("\\", "/") + "?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    try:
        print("--- pairing_status columns ---")
        for row in db.execute("PRAGMA table_info(pairing_status)"):
            print("   %-24s %s" % (row["name"], row["type"]))
        rows = [dict(r) for r in db.execute("SELECT * FROM pairing_status")]
        print("\nrows:", len(rows))
        print("\n--- distribution of every low-cardinality text column ---")
        for key in rows[0]:
            values = collections.Counter(str(r[key]) for r in rows)
            if len(values) <= 12:
                print("\n%s (%d distinct):" % (key, len(values)))
                for value, count in values.most_common():
                    print("   %-52s %d" % (value[:52], count))
        print("\n--- sample row ---")
        for key, value in rows[0].items():
            print("   %-24s %r" % (key, str(value)[:140]))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
