"""Estimate the missed-question gap from page text rows.

The recogniser stores per-page OCR rows in pages.rows_json. A printed question
number that appears at the start of a row on a question page, but has no
candidate in that scope, is strong evidence of a missed question.

This is a DETECTOR, not a decision: every hit still needs a human glance.
Read-only.
"""
from __future__ import annotations

import collections
import json
import os
import re
import sqlite3
import sys

DB = r"C:\Users\LIHAOYANG\Documents\Codex\2026-10-24\jian\work\wholebook-source.sqlite"
OUT = os.path.dirname(os.path.abspath(__file__))

# "1." "12." "9、" "（3）" at the very start of a text row
LEADING = re.compile(r"^\s*(?:第)?(\d{1,2})\s*[.、．)）]")


def main() -> int:
    db = sqlite3.connect("file:///" + DB.replace("\\", "/") + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        summary = {r["id"]: dict(r) for r in db.execute("SELECT * FROM scope_summary")}
        pairing = collections.defaultdict(set)
        for r in db.execute("SELECT scope_id, details_json FROM pairing_status"):
            d = json.loads(r["details_json"] or "{}")
            core = str(d.get("label") or "").split(":")[0]
            if core.isdigit():
                pairing[r["scope_id"]].add(int(core))

        # per question page, collect leading numbers seen in row text
        hits = []
        for scope_id, info in summary.items():
            pages = json.loads(info.get("question_pages") or "[]")
            have = pairing.get(scope_id, set())
            seen = collections.defaultdict(set)
            for page in pages:
                row = db.execute("SELECT rows_json FROM pages WHERE page=?", (page,)).fetchone()
                if not row:
                    continue
                try:
                    rows = json.loads(row["rows_json"])
                except json.JSONDecodeError:
                    continue
                for entry in rows:
                    if not isinstance(entry, list) or len(entry) < 2:
                        continue
                    text = str(entry[1] or "")
                    match = LEADING.match(text)
                    if match:
                        value = int(match.group(1))
                        if 1 <= value <= 60:
                            seen[value].add(page)
            missing = sorted(set(seen) - have)
            if missing:
                hits.append({
                    "scope_id": scope_id, "lesson": info.get("label") or "",
                    "pages": pages, "have": sorted(have), "row_numbers": sorted(seen),
                    "missing": missing,
                    "evidence": {str(n): sorted(seen[n]) for n in missing},
                })

        total_missing = sum(len(h["missing"]) for h in hits)
        print("scopes with row-level evidence of missing questions:", len(hits))
        print("estimated missing question numbers:", total_missing)

        lines = ["# 漏题检测（行首题号法）", "",
                 "数据来源：`pages.rows_json`（每页 OCR 行的文本）+ `pairing_status`（已生成候选）。",
                 "脚本 `missed.py`。只读，不修改任何数据。", "",
                 "## 一、方法", "",
                 "对有题页的每一行文本，用正则 `^(?:第)?(\\d{1,2})\\s*[.、．)）]` 抓行首题号；",
                 "得到的题号集合与该校时已生成候选的题号集合求差，差集即「页面上有题号、但没有候选」。", "",
                 "**这是一个检测器，不是判决器。** 行首数字也可能是：算式行首、答案页串号、",
                 "小问编号（(1)(2)）、页码。因此每个命中都要人眼确认。", "",
                 "## 二、结果", "",
                 "| 指标 | 数值 |", "|---|---|",
                 "| 有行首题号证据的课时 | %d |" % len(hits),
                 "| 估计漏题题号数 | **%d** |" % total_missing,
                 "",
                 "## 三、命中明细（按漏题数排序）", "",
                 "| 课时 | 题页 | 已做候选 | 行首可见题号 | 疑似漏题 |",
                 "|---|---|---|---|---|"]
        for h in sorted(hits, key=lambda x: -len(x["missing"]))[:40]:
            lines.append("| %s | %s | %s | %s | **%s** |" % (
                (h["lesson"] or h["scope_id"])[-38:], ",".join(map(str, h["pages"])),
                ",".join(map(str, h["have"][:20])),
                ",".join(map(str, h["row_numbers"][:22])),
                ",".join(map(str, h["missing"][:14]))))

        lines += ["", "## 四、已知的假阳性来源（必须人眼过滤）", "",
                  "- 解答过程里的行首数字（如「1. 解：」「2. 由勾股定理」）",
                  "- 答案页连排编号（「1.D2.D3.（1)5」这种一行多号，只会抓到第一个）",
                  "- 小问编号 (1)(2)(3) 被误当主题号",
                  "- 页码、年份、题内数据（2024、120 等）",
                  "",
                  "因此 **%d 只是上界**，真实漏题数小于它。第 189 页已人眼确认：" % total_missing,
                  "该页明印「本题共 10 小题」，而候选只覆盖到 10 且不连续 → 确认存在漏题。",
                  ""]
        with open(os.path.join(OUT, "表-漏题检测.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        with open(os.path.join(OUT, "missed.json"), "w", encoding="utf-8") as fh:
            json.dump({"schema": "MissedQuestions/v1",
                       "scopes_with_evidence": len(hits),
                       "estimated_missing_upper_bound": total_missing,
                       "hits": hits}, fh, ensure_ascii=False, indent=1)
        print("wrote 表-漏题检测.md / missed.json")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
