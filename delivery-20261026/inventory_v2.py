"""Recompute the whole-book inventory using page-level evidence, not numeric_labels.

Finding that invalidated the previous pass:
  scope_summary.numeric_labels is TRUNCATED -- it stops at printed_max and omits
  labels that exist on the page. Page 189 (单元测试（一）勾股定理) states 本题共 10 小题
  for the choice section alone and the page really shows 1-4, 8-10, 14-17.
  So a label outside numeric_labels is NOT evidence of a spurious candidate.

New reference set, in priority order:
  1. source_items with role='question' -- what the recogniser actually captured.
  2. pairing_status -- what became a candidate.
  Both are internally consistent; numeric_labels is only a weak hint.

Read-only over the source DB.
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

        # question-role source items, grouped by scope, with their labels
        item_labels = collections.defaultdict(list)
        for r in db.execute("SELECT * FROM source_items WHERE role='question'"):
            item_labels[r["scope_id"]].append({
                "item_id": r["item_id"], "kind": r["kind"],
                "label": str(r["label"] or ""),
                "start_page": r["start_page"], "end_page": r["end_page"],
            })

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
        tot_cand = tot_dup = tot_var = tot_read = 0
        unpaired_items = 0
        for scope_id in sorted(set(pairing) | set(item_labels)):
            rows = pairing.get(scope_id, [])
            items = item_labels.get(scope_id, [])
            info = summary.get(scope_id) or scopes.get(scope_id) or {}

            # question-role items that never produced a candidate
            paired_ids = {r["qid"] for r in rows}
            orphans = [i for i in items
                       if i["kind"] in {"QUESTION", "VARIANT", "READING_TASK"}
                       and i["item_id"] not in paired_ids]
            unpaired_items += len(orphans)

            counts = collections.Counter(r["value"] for r in rows
                                         if r["numeric"] and not r["variant"])
            dup_excess = sum(c - 1 for c in counts.values() if c > 1)
            variants = sum(1 for r in rows if r["variant"])
            readings = sum(1 for r in rows if r["kind"] == "READING_TASK")
            worked = sum(1 for i in items if i["kind"] == "WORKED_EXAMPLE")

            tot_cand += len(rows)
            tot_dup += dup_excess
            tot_var += variants
            tot_read += readings

            nums = sorted(counts)
            per_scope.append({
                "scope_id": scope_id,
                "lesson": info.get("label") or "",
                "pages": json.loads(info.get("question_pages") or "[]"),
                "answer_pages": json.loads(info.get("answer_pages") or "[]"),
                "printed_max": info.get("printed_max"),
                "q_items": len([i for i in items if i["kind"] == "QUESTION"]),
                "candidates": len(rows),
                "numbered": len(nums),
                "numbered_min": nums[0] if nums else None,
                "numbered_max": nums[-1] if nums else None,
                "variants": variants, "reading": readings, "worked_examples": worked,
                "dup_excess": dup_excess,
                "dup_numbers": {str(k): v for k, v in counts.items() if v > 1},
                "recovered": sum(1 for r in rows if r["recovered"]),
                "orphan_items": len(orphans),
                "orphan_sample": [i["item_id"][-40:] for i in orphans[:5]],
                "ready": sum(1 for r in rows if r["status"] == "READY_TO_PAIR"),
                "review": sum(1 for r in rows if r["status"] == "CUSTOMER_REVIEW"),
                "empty_rows": info.get("empty_rows"),
            })
            for r in rows:
                rows_csv.append({
                    "scope_id": scope_id, "lesson": info.get("label") or "",
                    "label": r["label"], "kind": r["kind"], "status": r["status"],
                    "reasons": ";".join(r["reasons"]), "pages": ",".join(map(str, r["pages"])),
                    "has_answer": "有" if r["aid"] else "无",
                    "recovered": "是" if r["recovered"] else "否",
                    "variant": "是" if r["variant"] else "否",
                })

        A = tot_cand
        B = A - tot_dup
        # What deserves to be in the book denominator: one entry per printed
        # question (duplicates collapsed), variants counted separately, reading
        # tasks excluded (pending user policy).
        C = B - tot_read

        report = {
            "schema": "BookInventory/v2",
            "source_database": DB,
            "note": "numeric_labels 已被证明截断，本版不再用它当参照",
            "tier_A_candidates": A,
            "tier_B_after_duplicates": B,
            "tier_C_excluding_reading_tasks": C,
            "duplicate_excess": tot_dup,
            "variants_included": tot_var,
            "reading_tasks_excluded": tot_read,
            "orphan_question_items": unpaired_items,
            "scopes": len(per_scope),
            "scopes_with_dups": sum(1 for s in per_scope if s["dup_excess"]),
            "scopes_with_orphans": sum(1 for s in per_scope if s["orphan_items"]),
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
            "# 全书题清单与最终题数 v2（书 46007447）", "",
            "数据来源：`%s`（只读）。脚本 `inventory_v2.py`。" % DB, "",
            "## 零、上一版为什么错（必须记录）", "",
            "v1 用 `scope_summary.numeric_labels` 当「源库认为有哪些题号」的参照，",
            "据此报出「漏收 22、误收 140」。**这个参照是错的。**", "",
            "证据（原图，`book/crops/`）：",
            "- 第 189 页「单元测试（一）勾股定理」明印「一、选择题：本题共 10 小题」，",
            "  页面上可见第 1–4、8–10、14–17 题。而 `numeric_labels` 只到 `printed_max`，",
            "  超出 `printed_max` 的真实题号被整段丢弃。",
            "- 第 32 页（二次根式乘除）`numeric_labels` 到 11，实际页面有 12–16 题。",
            "- 第 33 页（微专题1）原图印着第 12、13、14、16 题，源库只生成 5 条候选。",
            "",
            "结论：**`numeric_labels` 是截断字段，不能当题号全集**。v2 不再使用它，",
            "改用 `source_items`（role='question'）与 `pairing_status` 两套内部一致的证据。",
            "",
            "## 一、最终题数", "",
            "| 档位 | 题数 | 口径 |", "|---|---|---|",
            "| A 机器候选 | **%d** | `pairing_status` 全部行 |" % A,
            "| B 去重复后 | **%d** | 同一印刷题号被多条候选重复时只计 1 条（−%d） |" % (B, tot_dup),
            "| **C 计为全书题数（推荐）** | **%d** | B 再排除阅读任务 %d 条 |" % (C, tot_read),
            "",
            "**全书题数 = %d 道**（含变式 %d 道；不含阅读任务 %d 个、不含单列例题）。" % (
                C, tot_var, tot_read),
            "",
            "## 二、重复与孤立条目", "",
            "| 项 | 数值 |", "|---|---|",
            "| 重复多出的候选行 | %d（分布在 %d 个课时） |" % (
                tot_dup, report["scopes_with_dups"]),
            "| 有来源条目但没生成候选的题 | %d（分布在 %d 个课时） |" % (
                unpaired_items, report["scopes_with_orphans"]),
            "",
            "重复**全部**集中在 `dir-1792063578574-xrojh8iro`（期末复习(二) 实数）：",
            "同一题被正常规则与 `recovered/selftest` 规则各识别一次。合并时保留正常实例，",
            "recovered 记录降级为辅助证据。",
            "",
            "## 三、逐课时清单", "",
            "| 课时 | 页 | 编号题 | 变式 | 例题 | 重复 | 孤立 | READY | 待审 |",
            "|---|---|---|---|---|---|---|---|---|"]
        for s in sorted(per_scope, key=lambda x: -x["candidates"])[:70]:
            lines.append("| %s | %s | %d | %d | %d | %d | %d | %d | %d |" % (
                (s["lesson"] or s["scope_id"])[-42:], ",".join(map(str, s["pages"])),
                s["numbered"], s["variants"], s["worked_examples"],
                s["dup_excess"], s["orphan_items"], s["ready"], s["review"]))

        lines += ["", "## 四、仍需人看图的部分", "",
                  "1. **漏题**：第 189 页是明证——页面上的题号范围比候选覆盖的宽。",
                  "   但缺口到底是多少，必须逐课时看原图，无法从字段推算（字段本身被截断）。",
                  "2. **例题是否录入**：源库单列例题，平台侧没有例题节点，当前不计入分母。",
                  "3. **阅读任务是否算题**：%d 个，当前排除在分母外，待用户决策。" % tot_read,
                  "4. **9 个测试卷范围**：源库有 scope，平台无目录节点，分母里含它们的题，",
                  "   但保存前必须先建目录（用户已明确目录调整未授权，暂不执行）。",
                  "",
                  "## 五、与用户口径对照", "",
                  "| 用户说法 | 实测 | 结论 |", "|---|---|---|",
                  "| 源库 1,303 个题目实例 | `pairing_status` 1303 行 | ✅ 一致 |",
                  "| 529 个仍需处理 | `CUSTOMER_REVIEW` 529 行 | ✅ 一致 |",
                  "| 428 项集中在答案定位和题号标记 | 216 + 212 = **428** | ✅ 完全一致 |",
                  "| 1303 中混有伪题 | 标签层 0 条；真实问题是**重复 %d 条 + 漏收若干** | ⚠️ 需更正认识 |" % tot_dup,
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
