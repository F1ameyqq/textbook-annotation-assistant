"""Feasibility test: can the 36 unbound answers be re-bound by scope+label?

Rebinds in memory only. Reports how many of the 36 become bindable and what the
remaining few look like. Writes nothing to the source DB or the package.
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import sys

ROOT = r"C:\Users\LIHAOYANG\Desktop\网页标注自动化"
DB = r"C:\Users\LIHAOYANG\Documents\Codex\2026-10-24\jian\work\wholebook-source.sqlite"
PILOT = os.path.join(ROOT, "pilot50", "表-50题清单.csv")


def main() -> int:
    with open(PILOT, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    needy = [r for r in rows if r["判定"] != "DELIVERABLE"]

    db = sqlite3.connect("file:///" + DB.replace("\\", "/") + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        # index resolved answers by (scope, normalised label)
        resolved = {}
        for r in db.execute("SELECT * FROM resolved_answer_items"):
            key = (r["scope_id"], str(r["label"] or "").strip())
            resolved.setdefault(key, []).append(dict(r))

        bindable, ambiguous, absent = [], [], []
        for row in needy:
            scope = row["scope_id"]
            label = str(row["印刷题号"]).strip().split(":")[0]
            hits = resolved.get((scope, label), [])
            item = {"label": label, "lesson": row["课时"][-34:],
                    "reason": row["原因"][:34]}
            if len(hits) == 1:
                frags = json.loads(hits[0].get("fragments_json") or "[]")
                item["pages"] = sorted({f.get("page") for f in frags if f.get("page")})
                bindable.append(item)
            elif len(hits) > 1:
                item["count"] = len(hits)
                ambiguous.append(item)
            else:
                absent.append(item)

        print("pilot needy questions:", len(needy))
        print("  uniquely bindable by scope+label :", len(bindable))
        print("  multiple candidates (need rule)  :", len(ambiguous))
        print("  no resolved answer at all        :", len(absent))
        print("\n-- bindable sample --")
        for b in bindable[:10]:
            print("   %-34s label=%-6s pages=%s" % (b["lesson"], b["label"], b.get("pages")))
        print("\n-- ambiguous --")
        for a in ambiguous[:10]:
            print("   %-34s label=%-6s candidates=%s" % (a["lesson"], a["label"], a.get("count")))
        print("\n-- absent --")
        for a in absent[:10]:
            print("   %-34s label=%-6s %s" % (a["lesson"], a["label"], a["reason"]))

        out = {"schema": "RebindFeasibility/v1",
               "needy": len(needy), "bindable": len(bindable),
               "ambiguous": len(ambiguous), "absent": len(absent),
               "detail": {"bindable": bindable, "ambiguous": ambiguous, "absent": absent}}
        with open(os.path.join(ROOT, "pilot50", "重绑可行性.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
        print("\nwrote pilot50/重绑可行性.json")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
