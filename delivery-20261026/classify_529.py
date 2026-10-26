"""Classify the 529 CUSTOMER_REVIEW instances by primary root cause.

Read-only. Emits inventory/表-529异常分类.md and inventory/review-529.json.
"""
from __future__ import annotations

import collections
import json
import os
import sqlite3

BASE = r"C:\Users\LIHAOYANG\Documents\Codex\2026-10-24\jian\work"
NAME = "wholebook-source.sqlite"
OUT = os.path.dirname(os.path.abspath(__file__))

# reason token -> readable bucket
BUCKETS = [
    ("MISSING_OR_MULTIPLE_ANSWER_ANCHORS", "答案定位：缺锚点或多个候选"),
    ("ANSWER_MARKER_REQUIRES_REVIEW", "题号标记：答案标记需人工确认"),
    ("UNSPLIT_NUMERIC_CHAIN_REVIEW", "答案定位：连续数字串未切分"),
    ("RECOVERED_SOURCE_REGION_REVIEW", "来源区域：靠恢复规则找回，需复核"),
    ("GRAPHIC_OPTIONS_REQUIRE_REVIEW", "图形选项：需确认选项图归属"),
    ("MATH_OR_UNCLEAR_ANCHOR_REVIEW", "公式/锚点不清晰"),
    ("DUPLICATE_QUESTION_IDENTITY", "题号重复：同号多实例未消解"),
    ("ANSWER_BLOCK_CONTEXT_REVIEW", "答案块上下文：相邻答案归属不确定"),
    ("GEOMETRY_SOURCE_CONFLICT_REVIEW", "几何答案：来源分组冲突"),
    ("NO_BODY_AFTER_EXCLUSIONS", "排除页眉页脚后无正文"),
]


def main() -> int:
    db = sqlite3.connect("file:///" + os.path.join(BASE, NAME).replace("\\", "/") + "?mode=ro",
                         uri=True)
    db.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in db.execute(
            "SELECT * FROM pairing_status WHERE status='CUSTOMER_REVIEW'")]
        scopes = {r["id"]: dict(r) for r in db.execute("SELECT * FROM scopes")}
        summary = {r["id"]: dict(r) for r in db.execute("SELECT * FROM scope_summary")}

        bucket_counts = collections.Counter()
        bucket_primary = collections.Counter()
        multi = 0
        per_scope = collections.defaultdict(lambda: collections.Counter())
        records = []
        for row in rows:
            tokens = [t for t in (row["reason"] or "").split(";") if t]
            details = json.loads(row["details_json"] or "{}")
            if len(tokens) > 1:
                multi += 1
            for token in tokens:
                bucket_counts[token] += 1
            primary = tokens[0] if tokens else "UNKNOWN"
            bucket_primary[primary] += 1
            per_scope[row["scope_id"]][primary] += 1
            records.append({
                "scope_id": row["scope_id"],
                "lesson": (summary.get(row["scope_id"]) or {}).get("label")
                          or (scopes.get(row["scope_id"]) or {}).get("label"),
                "question_item_id": row["question_item_id"],
                "answer_item_id": row["answer_item_id"],
                "label": details.get("label"),
                "kind": details.get("kind"),
                "reasons": tokens,
                "primary": primary,
                "answer_candidate_count": len(details.get("answer_candidates") or []),
            })

        readable = dict(BUCKETS)
        lines = ["# 529 个待客户审校实例的按因分类", "",
                 "数据来源：`C:/Users/LIHAOYANG/Documents/Codex/2026-10-24/jian/work/wholebook-source.sqlite`"
                 " 的 `pairing_status` 表（只读）。",
                 "总计 1303 个题目实例，其中 **774 READY_TO_PAIR**、**529 CUSTOMER_REVIEW**。", "",
                 "## 一、按主因（取第一条 reason）", "",
                 "| 主因 | 可读解释 | 实例数 | 占 529 |", "|---|---|---|---|"]
        for token, count in bucket_primary.most_common():
            lines.append("| `%s` | %s | %d | %.1f%% |" % (
                token, readable.get(token, token), count, count * 100.0 / len(rows)))
        lines += ["", "## 二、按出现的全部原因（多个原因会重复计数）", "",
                  "| 原因 | 可读解释 | 出现次数 |", "|---|---|---|"]
        for token, count in bucket_counts.most_common():
            lines.append("| `%s` | %s | %d |" % (token, readable.get(token, token), count))
        lines += ["", "## 三、共性问题归并", ""]
        answer_tokens = {"MISSING_OR_MULTIPLE_ANSWER_ANCHORS", "ANSWER_MARKER_REQUIRES_REVIEW",
                         "UNSPLIT_NUMERIC_CHAIN_REVIEW"}
        answer_hit = sum(1 for r in records if answer_tokens & set(r["reasons"]))
        lines.append("- 命中「答案定位 / 题号标记」类原因的实例：**%d**" % answer_hit)
        lines.append("- 同时带 ≥2 个原因的实例：**%d**" % multi)
        lines.append("- 有 answer_item_id 的实例：**%d**；无答案的：**%d**" % (
            sum(1 for r in records if r["answer_item_id"]),
            sum(1 for r in records if not r["answer_item_id"])))
        lines += ["", "## 四、按课时分布（主因）", "",
                  "| 课时 | 待审校 | 主要主因 |", "|---|---|---|"]
        for scope_id, counter in sorted(per_scope.items(), key=lambda kv: -sum(kv[1].values())):
            lesson = ""
            for rec in records:
                if rec["scope_id"] == scope_id and rec["lesson"]:
                    lesson = rec["lesson"]
                    break
            top = counter.most_common(2)
            lines.append("| %s（%s） | %d | %s |" % (
                lesson or scope_id, scope_id[-8:], sum(counter.values()),
                "；".join("%s×%d" % (t, c) for t, c in top)))
        with open(os.path.join(OUT, "表-529异常分类.md"), "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        with open(os.path.join(OUT, "review-529.json"), "w", encoding="utf-8") as handle:
            json.dump({"schema": "Review529/v1", "total": len(rows),
                       "primary": dict(bucket_primary), "all": dict(bucket_counts),
                       "answer_or_marker_hit": answer_hit, "records": records},
                      handle, ensure_ascii=False, indent=1)
        print("wrote 表-529异常分类.md and review-529.json")
        print("primary:", dict(bucket_primary.most_common(6)))
        print("answer/marker hit:", answer_hit, "multi-reason:", multi)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
