"""Pilot-50 closed loop with a delivery-oriented verdict.

Verdict is NOT 'has an issue' (the package flags 91.9% of the book that way).
It separates:
  DELIVERABLE  zones complete (question+answer, plus choice when the type needs it)
               and no structural blocker
  NEEDS_WORK   a structural blocker that no automation can settle
  MISSING      a zone or candidate is absent

Structural blockers are the issues that mean content is absent or mis-assigned,
not merely 'low confidence / math layout / unexplained ink', which are advisory.

Recording only; no platform writes.
"""
from __future__ import annotations

import collections
import csv
import json
import os
import sys
import time

ROOT = r"C:\Users\LIHAOYANG\Desktop\网页标注自动化"
PKG = os.path.join(ROOT, "bin", "wholebook-single-entry")
STATE = os.path.join(PKG, "workspace")
OUT = os.path.join(ROOT, "pilot50")
sys.path.insert(0, os.path.join(PKG, "app", "src"))

# Issues that genuinely block delivery: content absent or structurally wrong.
BLOCKERS = {
    "ANSWER_MISSING_OR_AMBIGUOUS",
    "ANSWER_ROLE_REGIONS_UNSPLIT",
    "CHOICE_OR_ANSWER_STRUCTURE",
    "FIGURE_REFERENCE_MISSING_CONFIRMED_SOURCE_IMAGE",
    "GRAPHIC_OPTIONS_REQUIRE_SOURCE_REVIEW",
}
# Advisory: worth a human glance, but content is present.
ADVISORY = {
    "LOW_OR_MISSING_OCR_CONFIDENCE",
    "FORMULA_LAYOUT_REVIEW",
    "UNEXPLAINED_SOURCE_INK",
    "FIGURE_OR_FORMULA_REVIEW",
    "FIGURE_EXTENT_UNVERIFIED",
}


def issue_codes(cand):
    out = set()
    for issue in cand.get("issues") or []:
        if isinstance(issue, dict):
            out.add(str(issue.get("code")))
        else:
            out.add(str(issue))
    return out


def main() -> int:
    from annotation.customer.store import Store

    with open(os.path.join(OUT, "表-50题选型.csv"), encoding="utf-8-sig") as fh:
        selected = list(csv.DictReader(fh))
    by_scope = collections.defaultdict(list)
    for row in selected:
        by_scope[row["scope_id"]].append(row)

    with open(os.path.join(STATE, "offline-results.json"), encoding="utf-8") as fh:
        results = json.load(fh)
    job_of = {r["scope_id"]: r["job"] for r in results["results"]}
    store = Store(STATE)

    records = []
    t_all = time.perf_counter()
    for scope_id, rows in by_scope.items():
        job_id = job_of.get(scope_id)
        if not job_id:
            for row in rows:
                records.append({**row, "判定": "MISSING", "原因": "该课时未产出 job",
                                "有题干": "否", "有选项": "否", "有答案": "否",
                                "框数": 0, "阻塞issue": "", "提示issue": "",
                                "耗时毫秒": 0})
            continue
        t_load = time.perf_counter()
        job, _ = store.job(job_id)
        load_ms = (time.perf_counter() - t_load) * 1000
        index = collections.defaultdict(list)
        for cand in job.get("candidates") or []:
            index[str(cand.get("printed_number")).strip()].append(cand)

        for i, row in enumerate(rows):
            label = str(row["印刷题号"]).strip()
            cands = index.get(label, [])
            share = load_ms / max(len(rows), 1) if i == 0 else 0
            zones = (cands[0].get("zones") if cands else {}) or {}
            frames = (cands[0].get("frames") if cands else []) or []
            text = {z: str(zones.get(z) or "").strip() for z in ("question", "choice", "answer")}
            qtype = (cands[0].get("question_type") or {}).get("question_type") if cands else None
            codes = issue_codes(cands[0]) if cands else set()
            blockers = sorted(codes & BLOCKERS)
            advisories = sorted(codes & ADVISORY)
            frame_zones = {f.get("zone") for f in frames}
            missing_frames = [z for z, v in text.items() if v and z not in frame_zones]

            if not cands:
                verdict, reason = "MISSING", "题号在该课时候选中不存在"
            elif not text["question"]:
                verdict, reason = "MISSING", "缺题干文本"
            elif not text["answer"]:
                verdict, reason = "NEEDS_WORK", "缺答案区域"
            elif missing_frames:
                verdict, reason = "NEEDS_WORK", "区域有文本但缺框:" + ",".join(missing_frames)
            elif blockers:
                verdict, reason = "NEEDS_WORK", "结构性问题:" + ",".join(blockers)
            else:
                verdict, reason = "DELIVERABLE", "区域齐备且无阻塞问题"

            records.append({
                **row,
                "判定": verdict, "原因": reason,
                "有题干": "是" if text["question"] else "否",
                "有选项": "是" if text["choice"] else "否",
                "有答案": "是" if text["answer"] else "否",
                "框数": len(frames),
                "阻塞issue": ",".join(blockers),
                "提示issue": ",".join(advisories),
                "耗时毫秒": round(share, 3),
            })

    total_s = time.perf_counter() - t_all
    verdicts = collections.Counter(r["判定"] for r in records)
    by_type = collections.defaultdict(collections.Counter)
    blocker_counter = collections.Counter()
    for r in records:
        for tag in str(r["覆盖类型"]).split("/"):
            by_type[tag][r["判定"]] += 1
        for b in str(r["阻塞issue"]).split(","):
            if b:
                blocker_counter[b] += 1

    report = {
        "schema": "Pilot50Verdict/v1",
        "questions": len(records),
        "verdicts": dict(verdicts),
        "by_archetype": {k: dict(v) for k, v in by_type.items()},
        "blockers": dict(blocker_counter),
        "wall_seconds": round(total_s, 3),
        "note": "判定口径=区域齐备+无结构性阻塞；低置信度/公式排版为提示项，不阻塞",
    }
    with open(os.path.join(OUT, "pilot-verdict.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    fields = ["序号", "覆盖类型", "scope_id", "课时", "kind", "印刷题号", "起始状态",
              "判定", "原因", "有题干", "有选项", "有答案", "框数",
              "阻塞issue", "提示issue", "耗时毫秒"]
    with open(os.path.join(OUT, "表-50题清单.csv"), "w", encoding="utf-8-sig",
              newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow(r)

    print(json.dumps(report, ensure_ascii=False, indent=1))
    print("\nwrote 表-50题清单.csv / pilot-verdict.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
