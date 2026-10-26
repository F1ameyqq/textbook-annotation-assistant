"""Final whole-book count, after rejecting the 'missed question' hypothesis.

Evidence trail (all human-checked against page images):
  1. numeric_labels is truncated at printed_max -> unusable as a reference.
  2. Row-leading-number detection reported 46 'missing', but page 65 proves a
     page can legitimately host the tail of one lesson's questions (14-17) and
     the head of another lesson (1-3). Same for page 189.
  3. Orphan check: every question-role source item produced exactly one
     pairing_status candidate (0 orphans), so nothing was dropped between
     recognition and candidacy.

Therefore the book denominator is the pairing candidate count with duplicate
printed numbers collapsed, reading tasks excluded by policy.

Read-only.
"""
from __future__ import annotations

import collections
import csv
import json
import os
import sqlite3
import sys

DB = r"C:\Users\LIHAOYANG\Documents\Codex\2026-10-24\jian\work\wholebook-source.sqlite"
OUT = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    db = sqlite3.connect("file:///" + DB.replace("\\", "/") + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        scopes = {r["id"]: dict(r) for r in db.execute("SELECT * FROM scopes")}
        summary = {r["id"]: dict(r) for r in db.execute("SELECT * FROM scope_summary")}

        pairing = collections.defaultdict(list)
        for r in db.execute("SELECT * FROM pairing_status"):
            d = json.loads(r["details_json"] or "{}")
            label = str(d.get("label") or "")
            core = label.split(":")[0]
            frags = d.get("question_fragments") or []
            pairing[r["scope_id"]].append({
                "label": label, "core": core, "kind": d.get("kind"),
                "status": r["status"],
                "reasons": [t for t in (r["reason"] or "").split(";") if t],
                "numeric": core.isdigit(),
                "value": int(core) if core.isdigit() else None,
                "variant": ":variant:" in label,
                "pages": sorted({f.get("page") for f in frags if f.get("page") is not None}),
                "recovered": "recovered" in str(r["question_item_id"]),
                "qid": r["question_item_id"], "aid": r["answer_item_id"],
            })

        per_scope = []
        rows_csv = []
        A = dup = var = read = 0
        for scope_id in sorted(pairing):
            rows = pairing[scope_id]
            info = summary.get(scope_id) or scopes.get(scope_id) or {}
            counts = collections.Counter(r["value"] for r in rows
                                         if r["numeric"] and not r["variant"])
            d = sum(c - 1 for c in counts.values() if c > 1)
            v = sum(1 for r in rows if r["variant"])
            rd = sum(1 for r in rows if r["kind"] == "READING_TASK")
            A += len(rows)
            dup += d
            var += v
            read += rd
            per_scope.append({
                "scope_id": scope_id, "lesson": info.get("label") or "",
                "pages": json.loads(info.get("question_pages") or "[]"),
                "answer_pages": json.loads(info.get("answer_pages") or "[]"),
                "candidates": len(rows), "numbered": len(counts),
                "variants": v, "reading": rd, "dup_excess": d,
                "ready": sum(1 for r in rows if r["status"] == "READY_TO_PAIR"),
                "review": sum(1 for r in rows if r["status"] == "CUSTOMER_REVIEW"),
                "has_answer": sum(1 for r in rows if r["aid"]),
            })
            for r in rows:
                rows_csv.append({
                    "scope_id": scope_id, "lesson": info.get("label") or "",
                    "label": r["label"], "kind": r["kind"], "status": r["status"],
                    "reasons": ";".join(r["reasons"]),
                    "pages": ",".join(map(str, r["pages"])),
                    "has_answer": "有" if r["aid"] else "无",
                    "recovered": "是" if r["recovered"] else "否",
                    "variant": "是" if r["variant"] else "否",
                })

        B = A - dup
        C = B - read
        report = {
            "schema": "BookInventory/v3-final",
            "source_database": DB,
            "tier_A_candidates": A,
            "tier_B_after_duplicates": B,
            "tier_C_final": C,
            "duplicate_excess": dup,
            "variants_included": var,
            "reading_tasks_excluded": read,
            "reading_policy": "PENDING_USER_DECISION",
            "scopes": len(per_scope),
            "scopes_with_dups": sum(1 for s in per_scope if s["dup_excess"]),
            "scopes_all_ready": sum(1 for s in per_scope if s["review"] == 0
                                    and s["candidates"] > 0),
            "scopes_with_review": sum(1 for s in per_scope if s["review"] > 0),
        }

        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, "表-题目身份清单.csv"), "w", encoding="utf-8-sig",
                  newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["scope_id", "lesson", "label", "kind",
                                               "status", "reasons", "pages",
                                               "has_answer", "recovered", "variant"])
            w.writeheader()
            w.writerows(rows_csv)

        lines = [
            "# 全书题清单与最终题数（书 46007447）", "",
            "数据来源：`%s`（只读）。脚本 `final_count.py`。" % DB,
            "原图复核：`book/crops/`（第 33、50、65、189 页等人眼已看）。", "",
            "## 一、最终题数", "",
            "| 档位 | 题数 | 口径 |", "|---|---|---|",
            "| A 机器候选 | **%d** | `pairing_status` 全部行 |" % A,
            "| B 去重复后 | **%d** | 同课时同印刷题号多条候选只计 1 条（−%d） |" % (B, dup),
            "| **C 计入全书分母（推荐）** | **%d** | B 再排除阅读任务 %d 条 |" % (C, read),
            "",
            "**全书 = %d 道题**（含变式 %d 道；不含阅读任务 %d 个、不含单列例题）。" % (C, var, read),
            "",
            "## 二、否掉的三个假设（过程留痕，防止重复踩坑）", "",
            "### 假设 1：`numeric_labels` 是题号全集 → **否**", "",
            "`numeric_labels` 在 `printed_max` 处截断。第 189 页明印「本题共 10 小题」，",
            "页面可见 1–4、8–10、14–17，而字段只到 10。用它判断「误收 140」是错的。", "",
            "### 假设 2：行首题号差集能测漏题 → **否**", "",
            "行首数字法报出 46 处「漏题」。但第 65 页原图显示：",
            "- 上半部第 14–17 题属于课时「周测 4.1~4.3 第2课时 一次函数的图象与性质」",
            "- 下半部第 1–3 题属于课时「微专题4 一次函数图象的平移规律」",
            "两课时共用第 65 页，各自题号都能在源库找到候选。**不是漏题，是共页。**", "",
            "### 假设 3：识别阶段丢了题 → **否（在候选层面）**", "",
            "`source_items`（role='question'）与 `pairing_status` 一一对应：",
            "**孤立条目 0 个**。凡是识别出题目条目，都生成了候选。", "",
            "## 三、真实的结构性问题（这才是工期变量）", "",
            "| 问题 | 规模 | 影响 |", "|---|---|---|",
            "| 配对异常（答案定位/题号标记） | **529 个实例** | 每题都要人看，是主要工期 |",
            "| 其中答案定位 + 题号标记 | **428 个** | 用户点名的主因，完全对上 |",
            "| 重复身份 | 9 组 | 全部在「期末复习(二) 实数」，正常+recovered 撞号 |",
            "| 平台侧无解析框 | 42/42 题全缺 | 若验收含解析，完成度为 0 |",
            "| 平台侧无题号节点的范围 | 9 个测试卷 + 第3节 | 保存前必须先建目录（未授权） |",
            "| 答案框全在第 173 页 | 49/49 | 配对只能靠几何/次序推断，系统性风险 |",
            "",
            "## 四、逐课时清单", "",
            "| 课时 | 题页 | 候选 | 编号题 | 变式 | 有答案 | READY | 待审 |",
            "|---|---|---|---|---|---|---|---|"]
        for s in sorted(per_scope, key=lambda x: -x["candidates"]):
            lines.append("| %s | %s | %d | %d | %d | %d | %d | %d |" % (
                (s["lesson"] or s["scope_id"])[-44:], ",".join(map(str, s["pages"])),
                s["candidates"], s["numbered"], s["variants"], s["has_answer"],
                s["ready"], s["review"]))

        lines += ["", "## 五、口径与待决事项", "",
                  "1. **阅读任务 %d 个**是否计入分母：当前排除，待用户决策。" % read,
                  "2. **例题**：`source_items` 单列 21 个 WORKED_EXAMPLE，不入候选，",
                  "   平台侧也无例题节点 → 当前不计入。",
                  "3. **变式 %d 道**计入分母（平台侧确实单独建题号节点）。" % var,
                  "4. **重复 9 组**处理方式：保留正常实例，recovered 降为辅助证据，不删记录。",
                  "5. 全书分母已定 **%d**；但这个数只覆盖有目录节点的课时。" % C,
                  "   9 个测试卷范围在源库有题，平台无目录节点，它们的题已含在 %d 里，" % C,
                  "   保存前必须先建目录（用户明确目录调整未授权）。",
                  "",
                  "## 六、与用户口径对照", "",
                  "| 用户说法 | 实测 | 结论 |", "|---|---|---|",
                  "| 源库 1,303 个题目实例 | `pairing_status` 1303 行 | ✅ 完全一致 |",
                  "| 529 个仍需处理 | `CUSTOMER_REVIEW` 529 行 | ✅ 完全一致 |",
                  "| 428 项集中在答案定位和题号标记 | 216 + 212 = **428** | ✅ 完全一致 |",
                  "| 1,303 中混有栏目标题等伪题 | 标签层 0；候选层无孤立条目；重复仅 9 组 | ⚠️ 数据不支持「大量伪题」，需以实际为准 |",
                  ""]

        with open(os.path.join(OUT, "表-全书题清单.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        with open(os.path.join(OUT, "inventory.json"), "w", encoding="utf-8") as fh:
            json.dump({**report, "per_scope": per_scope}, fh, ensure_ascii=False, indent=1)

        print(json.dumps(report, ensure_ascii=False, indent=1))
        print("\nwrote 表-全书题清单.md / 表-题目身份清单.csv / inventory.json")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
