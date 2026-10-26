"""Select a 50-question pilot covering five question archetypes.

Read-only over the whole-book source DB. Writes pilot50/ selection tables.
"""
from __future__ import annotations

import collections
import csv
import json
import os
import sqlite3

BASE = r"C:\Users\LIHAOYANG\Documents\Codex\2026-10-24\jian\work"
NAME = "wholebook-source.sqlite"
ROOT = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    path = os.path.join(BASE, NAME)
    db = sqlite3.connect("file:///" + path.replace("\\", "/") + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        summary = {r["id"]: dict(r) for r in db.execute("SELECT * FROM scope_summary")}
        scopes = {r["id"]: dict(r) for r in db.execute("SELECT * FROM scopes")}
        windows = collections.defaultdict(list)
        for r in db.execute("SELECT * FROM scope_windows ORDER BY scope_id, page"):
            windows[r["scope_id"]].append(dict(r))

        rows = []
        for r in db.execute("SELECT * FROM pairing_status"):
            details = json.loads(r["details_json"] or "{}")
            tokens = [t for t in (r["reason"] or "").split(";") if t]
            s = summary.get(r["scope_id"]) or {}
            sc = scopes.get(r["scope_id"]) or {}
            qpages = []
            try:
                qpages = json.loads(s.get("question_pages") or sc.get("question_pages") or "[]")
            except (TypeError, json.JSONDecodeError):
                qpages = []
            fragments = details.get("question_fragments") or []
            frag_pages = sorted({f.get("page") for f in fragments if f.get("page") is not None})
            rows.append({
                "scope_id": r["scope_id"],
                "lesson": s.get("label") or sc.get("label") or "",
                "kind": details.get("kind"),
                "label": details.get("label"),
                "status": r["status"],
                "reasons": tokens,
                "answer_item_id": r["answer_item_id"],
                "answer_candidates": len(details.get("answer_candidates") or []),
                "graphic_regions": len(details.get("option_graphic_regions") or []),
                "stem_figures": len(details.get("stem_figure_regions") or []),
                "frag_pages": frag_pages,
                "cross_page": len(frag_pages) > 1,
                "scope_qpages": qpages,
            })

        print("total instances:", len(rows))
        print("cross-page (fragments span >1 page):", sum(r["cross_page"] for r in rows))
        print("with option graphic regions:", sum(1 for r in rows if r["graphic_regions"]))
        print("with stem figures:", sum(1 for r in rows if r["stem_figures"]))
        print("kinds:", collections.Counter(r["kind"] for r in rows))
        print("labels sample:", collections.Counter(r["label"] for r in rows).most_common(8))

        # ---- archetype tagging ----
        ANCHOR_TOKENS = {"MISSING_OR_MULTIPLE_ANSWER_ANCHORS",
                         "ANSWER_MARKER_REQUIRES_REVIEW",
                         "UNSPLIT_NUMERIC_CHAIN_REVIEW"}

        def archetypes(row):
            tags = []
            reasons = set(row["reasons"])
            if row["cross_page"]:
                tags.append("跨页题")
            if row["graphic_regions"] or row["stem_figures"] or "GRAPHIC_OPTIONS_REQUIRE_REVIEW" in reasons:
                tags.append("图形题")
            if {"MATH_OR_UNCLEAR_ANCHOR_REVIEW", "UNSPLIT_NUMERIC_CHAIN_REVIEW"} & reasons:
                tags.append("公式题")
            if "DUPLICATE_QUESTION_IDENTITY" in reasons or row["kind"] == "VARIANT":
                tags.append("同号题")
            if ANCHOR_TOKENS & reasons:
                tags.append("答案定位/题号标记")
            if not tags and row["status"] == "READY_TO_PAIR":
                tags.append("普通题")
            if not tags:
                tags.append("其他异常")
            return tags

        for row in rows:
            row["archetypes"] = archetypes(row)

        by_arch = collections.Counter()
        for row in rows:
            for tag in row["archetypes"]:
                by_arch[tag] += 1
        print("\narchetype coverage (instances):")
        for tag, count in by_arch.most_common():
            print("   %-10s %d" % (tag, count))

        # ---- pick 50: weighted to the real work profile ----
        # 435/529 of the review load is answer-anchor / marker work, so the pilot
        # must be dominated by it; the four structural archetypes keep a floor.
        # Within each archetype, round-robin across lessons so the pilot is not
        # dominated by whichever scope sorts first.
        TARGET = {"普通题": 5, "答案定位/题号标记": 22, "图形题": 8,
                  "公式题": 5, "跨页题": 5, "同号题": 5}
        picked, excluded = [], set()
        picked_scope = collections.Counter()

        def spread(pool, quota):
            """Round-robin over lessons so each pick widens lesson coverage."""
            by_lesson = collections.OrderedDict()
            for row in sorted(pool, key=lambda r: (r["scope_id"], str(r["label"]))):
                by_lesson.setdefault(row["scope_id"], []).append(row)
            out = []
            while len(out) < quota and any(by_lesson.values()):
                for scope_id in list(by_lesson):
                    if len(out) >= quota:
                        break
                    bucket = by_lesson[scope_id]
                    if not bucket:
                        continue
                    out.append(bucket.pop(0))
            return out

        for tag, quota in TARGET.items():
            pool = [r for r in rows if tag in r["archetypes"] and id(r) not in excluded]
            for row in spread(pool, quota):
                picked.append(row)
                excluded.add(id(row))
                picked_scope[row["scope_id"]] += 1

        print("\npicked:", len(picked))
        print("distinct lessons:", len({r["scope_id"] for r in picked}))

        os.makedirs(os.path.join(ROOT, "exports"), exist_ok=True)
        with open(os.path.join(ROOT, "表-50题选型.csv"), "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["序号", "覆盖类型", "scope_id", "课时", "kind", "印刷题号",
                             "起始状态", "原因", "答案候选数", "图形区数", "跨页", "题干页"])
            for i, row in enumerate(picked, 1):
                writer.writerow([i, "/".join(row["archetypes"]), row["scope_id"], row["lesson"],
                                 row["kind"], row["label"], row["status"],
                                 ";".join(row["reasons"]), row["answer_candidates"],
                                 row["graphic_regions"], "是" if row["cross_page"] else "否",
                                 ",".join(str(p) for p in row["frag_pages"])])
        with open(os.path.join(ROOT, "selection.json"), "w", encoding="utf-8") as fh:
            json.dump({"schema": "Pilot50Selection/v1", "total_instances": len(rows),
                       "archetype_counts": dict(by_arch), "targets": TARGET,
                       "picked": picked}, fh, ensure_ascii=False, indent=1)
        print("wrote 表-50题选型.csv and selection.json")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
