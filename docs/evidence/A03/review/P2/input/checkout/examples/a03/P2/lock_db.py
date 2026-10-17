"""Hold a real SQLite transaction behind a bounded explicit test barrier.

The parent supplies an existing database created by this exact test scene. This
worker makes no business-state changes and always rolls back before normal exit.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import threading
import time


def lock(database, marker, release):
    database, marker, release = Path(database), Path(marker), Path(release)
    if not database.is_file():
        raise FileNotFoundError("test lock must not create a missing runtime database")
    connection = sqlite3.connect(str(database), timeout=1, isolation_level=None)
    try:
        connection.execute("BEGIN EXCLUSIVE")
        with marker.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump({"point": "SQLITE_EXCLUSIVE_LOCK_ACQUIRED"}, stream)
        deadline = time.monotonic() + 5
        tick = threading.Event()
        while not release.exists():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("bounded lock barrier expired")
            tick.wait(min(0.01, remaining))
        connection.execute("ROLLBACK")
    finally:
        connection.close()
    print(json.dumps({"ok": True, "result": {"released": True}}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--marker", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    args = parser.parse_args()
    lock(args.database, args.marker, args.release)
