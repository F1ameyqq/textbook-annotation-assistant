"""Read-only breakdown of the 529 CUSTOMER_REVIEW pairing rows.

Prints reason distribution, per-scope counts and label samples. No writes.
"""
from __future__ import annotations

import collections
import json
import os
import sqlite3
import sys

BASE = r"C:\Users\LIHAOYANG\Documents\Codex\2026-10-24\jian\work"
NAME = "wholebook-source.sqlite"


def main() -> int:
    path = os.path.join(BASE, NAME)
    db = sqlite3.connect("file:///" + path.replace("\\", "/") + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in db.execute(
            "SELECT * FROM pairing_status WHERE status='CUSTOMER_REVIEW'")]
        print("CUSTOMER_REVIEW rows:", len(rows))

        reasons = collections.Counter(r["reason"] for r in rows)
        print("\n--- reason distribution ---")
        for reason, count in reasons.most_common():
            print("   %-64s %d" % (reason, count))

        print("\n--- per-scope counts (top 20) ---")
        scopes = collections.Counter(r["scope_id"] for r in rows)
        print("   distinct scopes:", len(scopes))
        for scope, count in scopes.most_common(20):
            print("   %-40s %d" % (scope, count))

        print("\n--- kind distribution from details_json ---")
        kinds = collections.Counter()
        has_answer = collections.Counter()
        labels = collections.Counter()
        for row in rows:
            try:
                details = json.loads(row["details_json"] or "{}")
            except json.JSONDecodeError:
                kinds["<BAD JSON>"] += 1
                continue
            kinds[str(details.get("kind"))] += 1
            has_answer[bool(row["answer_item_id"])] += 1
            labels[str(details.get("label"))] += 1
        for kind, count in kinds.most_common():
            print("   kind=%-16s %d" % (kind, count))
        print("   answer_item_id present:", dict(has_answer))
        print("   distinct labels:", len(labels), "| top:", labels.most_common(12))

        print("\n--- first 5 rows ---")
        for row in rows[:5]:
            try:
                details = json.loads(row["details_json"] or "{}")
            except json.JSONDecodeError:
                details = {}
            print("   scope=%s label=%s kind=%s" % (
                row["scope_id"], details.get("label"), details.get("kind")))
            print("      q=%s" % row["question_item_id"])
            print("      a=%s" % row["answer_item_id"])
            print("      reason=%s" % row["reason"])
            print("      detail_keys=%s" % sorted(details))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
