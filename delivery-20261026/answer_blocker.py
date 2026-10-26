"""Investigate the dominant blocker: ANSWER_MISSING_OR_AMBIGUOUS.

For the pilot questions flagged as missing answers, check the source DB: does a
resolved answer item exist for that scope+label? If yes the defect is binding;
if no the answer genuinely is not in the source.
Read-only.
"""
from __future__ import annotations

import collections
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
        # what does the source DB hold for answer items?
        have_ans = collections.defaultdict(set)
        for r in db.execute("SELECT * FROM source_items WHERE role='answer'"):
            have_ans[r["scope_id"]].add(str(r["label"] or ""))

        resolved = collections.defaultdict(dict)
        for r in db.execute("SELECT * FROM resolved_answer_items"):
            cols = r.keys()
            scope = r["scope_id"] if "scope_id" in cols else None
            label = None
            for key in ("label", "printed_label", "marker"):
                if key in cols:
                    label = r[key]
                    break
            resolved[scope][str(label)] = dict(r)

        print("resolved_answer_items sample columns:",
              [c for c in db.execute("SELECT * FROM resolved_answer_items LIMIT 1").fetchone().keys()])
        print("answer source items total:",
              db.execute("SELECT COUNT(*) FROM source_items WHERE role='answer'").fetchone()[0])
        print("resolved answer items total:",
              db.execute("SELECT COUNT(*) FROM resolved_answer_items").fetchone()[0])

        buckets = collections.Counter()
        detail = []
        for r in needy:
            scope = r["scope_id"]
            label = str(r["印刷题号"]).strip().split(":")[0]
            in_source = label in have_ans.get(scope, set())
            in_resolved = label in resolved.get(scope, {})
            if in_resolved:
                buckets["源库有已解析答案 → 绑定失败"] += 1
            elif in_source:
                buckets["源库有答案条目但未解析 → 解析失败"] += 1
            else:
                buckets["源库该课时无此号答案 → 答案确实不在"] += 1
            detail.append({"label": label, "lesson": r["课时"][-30:],
                           "verdict": r["判定"], "reason": r["原因"][:40],
                           "in_source": in_source, "in_resolved": in_resolved})

        print("\n=== 缺答案的归因 ===")
        for k, v in buckets.most_common():
            print("  %-40s %d" % (k, v))
        print("\n=== 明细（前 20） ===")
        for d in detail[:20]:
            print("  %-34s label=%-8s verdict=%-10s src=%-5s resolved=%-5s" % (
                d["lesson"], d["label"], d["verdict"], d["in_source"], d["in_resolved"]))

        with open(os.path.join(ROOT, "pilot50", "缺答案归因.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"schema": "AnswerBlockerAttribution/v1",
                       "needy": len(needy), "buckets": dict(buckets),
                       "detail": detail}, fh, ensure_ascii=False, indent=1)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
