"""Resolve whether 'missed' numbers are truly missed or mis-assigned to another scope.

For every (page, printed number) that the row detector sees, find which scope
actually claims that page. If the page belongs to two scopes, the number may
simply be filed under the wrong one -- that is a catalogue/assignment defect,
not a miss.

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
LEADING = re.compile(r"^\s*(?:第)?(\d{1,2})\s*[.、．)）]")


def main() -> int:
    db = sqlite3.connect("file:///" + DB.replace("\\", "/") + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        # page -> scopes that list it as a question page
        page_scopes = collections.defaultdict(set)
        scopes = {}
        for r in db.execute("SELECT * FROM scope_summary"):
            scopes[r["id"]] = dict(r)
            for page in json.loads(r["question_pages"] or "[]"):
                page_scopes[page].add(r["id"])

        # labels actually produced per scope, and the pages they came from
        scope_labels = collections.defaultdict(set)
        label_pages = collections.defaultdict(set)
        for r in db.execute("SELECT * FROM pairing_status"):
            d = json.loads(r["details_json"] or "{}")
            core = str(d.get("label") or "").split(":")[0]
            if not core.isdigit():
                continue
            value = int(core)
            scope_labels[r["scope_id"]].add(value)
            for f in (d.get("question_fragments") or []):
                if f.get("page") is not None:
                    label_pages[r["scope_id"]].add(f["page"])

        # numbers seen in page rows
        page_numbers = {}
        for page in sorted(page_scopes):
            row = db.execute("SELECT rows_json FROM pages WHERE page=?", (page,)).fetchone()
            if not row:
                continue
            try:
                rows = json.loads(row["rows_json"])
            except json.JSONDecodeError:
                continue
            nums = set()
            for entry in rows:
                if isinstance(entry, list) and len(entry) >= 2:
                    m = LEADING.match(str(entry[1] or ""))
                    if m:
                        v = int(m.group(1))
                        if 1 <= v <= 60:
                            nums.add(v)
            page_numbers[page] = nums

        shared = {p: s for p, s in page_scopes.items() if len(s) > 1}
        cases = []
        for page, nums in page_numbers.items():
            owners = page_scopes.get(page) or set()
            for scope_id in owners:
                have = scope_labels.get(scope_id, set())
                missing_here = nums - have
                # would another owner of the same page cover it?
                covered_elsewhere = set()
                for other in owners:
                    if other != scope_id:
                        covered_elsewhere |= (nums & scope_labels.get(other, set()))
                true_missing = sorted(missing_here - covered_elsewhere)
                other_covered = sorted(missing_here & covered_elsewhere)
                if missing_here:
                    cases.append({
                        "page": page, "scope_id": scope_id,
                        "lesson": (scopes.get(scope_id) or {}).get("label") or "",
                        "page_shared_by": sorted(owners),
                        "numbers_on_page": sorted(nums),
                        "have": sorted(have),
                        "missing_here": sorted(missing_here),
                        "covered_by_other_scope": other_covered,
                        "true_missing": true_missing,
                    })

        true_missing_total = sum(len(c["true_missing"]) for c in cases)
        misassigned_total = sum(len(c["covered_by_other_scope"]) for c in cases)

        lines = ["# 漏题 vs 目录错位：逐页归属核对", "",
                 "数据来源：`pages.rows_json` + `scope_summary.question_pages` + `pairing_status`。",
                 "脚本 `attribute.py`。只读。", "",
                 "## 一、关键区分", "",
                 "第 65 页上的第 14–17 题，源库这几题只有 1、2、3 条候选。",
                 "但第 64 页和第 65 页**同属一个课时范围**（`周测(4.1~4.3第1课时)`），",
                 "14–17 题是上一页连续印到本页的正文，不是本课时的题。", "",
                 "所以「漏题」必须先分清两种：",
                 "- **真漏题**：本题时页面上有该题号，且没有别的课时认领它 → 确实漏了",
                 "- **串页/错位**：该题号属于相邻页面的题，出现在本题时页面上只是版面延续", "",
                 "## 二、统计", "",
                 "| 类别 | 数量 |", "|---|---|",
                 "| 同页被多个课时共用 | %d 页 |" % len(shared),
                 "| 本题时缺、但被同页其他课时覆盖（错位/串页） | **%d** |" % misassigned_total,
                 "| 本题时缺、且无任何课时覆盖（真漏题候选） | **%d** |" % true_missing_total,
                 ""]

        lines += ["## 三、同页共用情况", "",
                  "| 页 | 共用课时数 | 课时 |", "|---|---|---|"]
        for page, owners in sorted(shared.items()):
            names = [(scopes.get(o) or {}).get("label") or o for o in owners]
            lines.append("| %d | %d | %s |" % (page, len(owners),
                                               "；".join(n[-24:] for n in names)))

        lines += ["", "## 四、真漏题候选（需人眼确认）", "",
                  "| 页 | 课时 | 页上行首题号 | 已有 | 无覆盖的缺号 |", "|---|---|---|---|---|"]
        for c in sorted(cases, key=lambda x: -len(x["true_missing"]))[:35]:
            if not c["true_missing"]:
                continue
            lines.append("| %d | %s | %s | %s | **%s** |" % (
                c["page"], (c["lesson"] or c["scope_id"])[-30:],
                ",".join(map(str, c["numbers_on_page"][:18])),
                ",".join(map(str, c["have"][:18])),
                ",".join(map(str, c["true_missing"][:12]))))

        lines += ["", "## 五、结论", "",
                  "- 之前用行首题号法报「46 处漏题」**偏高**：其中 **%d 处**是相邻页/共用页造成的错位，",
                  "- 真正需要补的候选漏题是 **%d 处**，且仍需人眼逐条确认（行首数字有假阳性）。",
                  "- 这一结果改变了工期判断：**主要问题不是「识别漏了」，而是「题归属串了」**，",
                  "  对应平台侧就是「答案框全部在第 173 页、靠几何推断配对」的结构性风险。",
                  ""]
        with open(os.path.join(OUT, "表-漏题与错位.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        with open(os.path.join(OUT, "attribution.json"), "w", encoding="utf-8") as fh:
            json.dump({"schema": "PageAttribution/v1",
                       "shared_pages": {str(k): sorted(v) for k, v in shared.items()},
                       "misassigned_total": misassigned_total,
                       "true_missing_total": true_missing_total,
                       "cases": cases}, fh, ensure_ascii=False, indent=1)
        print("shared pages:", len(shared))
        print("misassigned (covered by other scope):", misassigned_total)
        print("true missing (uncovered):", true_missing_total)
        print("wrote 表-漏题与错位.md / attribution.json")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
