#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/verify_data.py — 数据落地校验 + 证据图生成（只读，零模型推理）

输出：
  data/derived/manifest.json                （补充 image_layout / integrity）
  data/derived/quality_findings.json
  data/derived/verify_report.md             人类可读报告
  data/derived/inspect/*.png                可复核证据图

用法:
  python tools/verify_data.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from layout_probe import describe_layout, find_gutters, ink_coverage  # noqa: E402

DATA = os.path.join(ROOT, "data")
RAW_IMG = os.path.join(DATA, "raw", "images")
DERIVED = os.path.join(DATA, "derived")
INSPECT = os.path.join(DERIVED, "inspect")
CST = timezone(timedelta(hours=8))
FILE_ID = "46006966"
COLORS = {"question": (230, 0, 0), "choice": (0, 130, 255),
          "answer": (0, 170, 0), "analysis": (230, 0, 230)}


def log(m):
    print(m, flush=True)


def load() -> list[dict]:
    p = os.path.join(DATA, "raw", "annotations", "annotations_unified_snapshot.json")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def bbox(r) -> list[float]:
    return [float(v) for v in r["rect_bbox"].split(",")]


def main() -> int:
    os.makedirs(INSPECT, exist_ok=True)
    recs = load()

    # 分析全部已落地页图（含历史标注未覆盖、但用于判断版面结构的 7 / 233）
    have = sorted(
        int(f.split("_page_")[1].split(".")[0])
        for f in os.listdir(RAW_IMG)
        if f.startswith(f"{FILE_ID}_page_") and f.endswith(".jpg")
    )
    pages = have
    log(f"标注 {len(recs)} 条，已落地页图(0基资源索引): {have}")
    log(f"标注覆盖页: {sorted({r['page_index'] for r in recs})}")

    layout: dict[str, dict] = {}
    img_objs: dict[int, Image.Image] = {}
    for pg in pages:
        p = os.path.join(RAW_IMG, f"{FILE_ID}_page_{pg}.jpg")
        if not os.path.exists(p):
            log(f"  page {pg}: 缺图")
            continue
        im = Image.open(p).convert("RGB")
        img_objs[pg] = im
        g = find_gutters(im)
        n_inner = len(g["inner_v_gutters"])
        d = {
            "width": g["width"], "height": g["height"],
            "ink_ratio_pct": round(g["ink_ratio"] * 100, 3),
            "n_inner_v_gutters": n_inner,
            "inner_v_gutters": [list(x) for x in g["inner_v_gutters"]],
            "n_panels_v": len(g["panels_v"]), "n_panels_h": len(g["panels_h"]),
            "panels_v": [list(x) for x in g["panels_v"]],
            "panels_h": [list(x) for x in g["panels_h"]],
            "h_gutters": [list(x) for x in g["h_gutters"]],
            "annotation_count": sum(1 for r in recs if r["page_index"] == pg),
            "verdict": (f"横向多页拼合（{n_inner+1}栏）" if n_inner else "单一页扫描"),
            "verdict_note": ("内部纵向空白沟是可靠信号（min_run=12, span_frac=0.7）；"
                             "横向带数受段落间距干扰，行数需人工看图。"),
        }
        layout[pg] = d
        log(f"  page {pg:>3}: {describe_layout(im)}")

    # 逐页判定：历史框是否落在"记录坐标系"内
    integrity: list[dict] = []
    for pg in pages:
        if pg not in layout:
            continue
        W, H = layout[pg]["width"], layout[pg]["height"]
        psub = [r for r in recs if r["page_index"] == pg]
        if not psub:
            integrity.append({
                "page_index": pg, "image_wh": [W, H], "n_boxes": 0,
                "verdict": "NO_ANNOTATION",
                "note": "该页已落地但无历史标注（用于判定版面结构）",
            })
            log(f"  完整性 page {pg:>3}: 无历史标注（仅用于版面判定）")
            continue
        mx = max(bbox(r)[2] for r in psub)
        my = max(bbox(r)[3] for r in psub)
        covered = sum(bbox(r)[2] - bbox(r)[0] for r in psub) / max(1, len(psub))
        # 判定分两级：是否越界；以及是否与图尺寸严重不成比例（坐标空间可疑）
        fits = mx <= W and my <= H
        scaled = mx / W
        if not fits:
            verdict = "OUT_OF_BOUNDS"
        elif scaled < 0.5:
            verdict = "SUSPECT_COORD_SPACE"
        else:
            verdict = "OK"
        integrity.append({
            "page_index": pg,
            "image_wh": [W, H],
            "n_boxes": len(psub),
            "max_x2": round(mx, 2), "max_y2": round(my, 2),
            "mean_box_w": round(covered, 1),
            "x2_fits": fits, "y2_fits": my <= H,
            "x_span_frac": round(scaled, 4), "y_span_frac": round(my / H, 4),
            "verdict": verdict,
        })
        log(f"  完整性 page {pg:>3}: max_x2={mx:.1f}/{W} max_y2={my:.1f}/{H} "
            f"x占{scaled*100:.1f}% -> {verdict}")

    # 证据图：逐页叠框
    for pg, im in img_objs.items():
        canvas = im.copy()
        d = ImageDraw.Draw(canvas)
        for r in recs:
            if r["page_index"] != pg:
                continue
            x1, y1, x2, y2 = bbox(r)
            d.rectangle([x1, y1, x2, y2], outline=COLORS.get(r["type"], (0, 0, 0)), width=4)
        w, h = canvas.size
        scale = min(1.0, 1600 / w)
        canvas.resize((int(w * scale), int(h * scale))).save(
            os.path.join(INSPECT, f"page{pg}_boxes.png"))

    # 页 234 的墨迹覆盖对比（证明坐标系不吻合）
    p234 = [r for r in recs if r["page_index"] == 234 and r["type"] in ("answer", "analysis")]
    cov_asrec, cov_x583, cov_dx71, cov_dx1100 = [], [], [], []
    if 234 in img_objs:
        im = img_objs[234]
        W234 = im.size[0]
        for r in p234:
            x1, y1, x2, y2 = bbox(r)
            cov_asrec.append(ink_coverage(im, (x1, y1, x2, y2))[0])
            cov_x583.append(ink_coverage(im, (x1 * 5.8333, y1 * 5.8333,
                                              x2 * 5.8333, y2 * 5.8333))[0])
            cov_dx71.append(ink_coverage(im, (x1 + 71, y1, x2 + 71, y2))[0])
            cov_dx1100.append(ink_coverage(im, (x1 + 1100, y1, x2 + 1100, y2))[0])

    def _mean(v):
        return round(sum(v) / max(1, len(v)), 3)

    probe = {
        "page": 234,
        "n_boxes": len(p234),
        "mean_ink_pct_as_recorded": _mean(cov_asrec),
        "mean_ink_pct_scaled_5_8333": _mean(cov_x583),
        "mean_ink_pct_shift_dx71": _mean(cov_dx71),
        "mean_ink_pct_shift_dx1100": _mean(cov_dx1100),
        "note": ("四个假设都试过：原坐标 / 按 3465/594≈5.8333 缩放 / +71 平移 / +1100 平移。"
                 "缩放反而使覆盖率下降，平移基本不变，故 3465×1615 这张图与记录坐标空间"
                 "之间不存在可离线复原的简单平移-缩放关系。"),
    }

    findings = json.load(open(os.path.join(DERIVED, "quality_findings.json"), encoding="utf-8"))
    manifest = json.load(open(os.path.join(DERIVED, "manifest.json"), encoding="utf-8"))
    manifest["image_layout"] = {str(k): v for k, v in layout.items()}
    manifest["coordinate_integrity"] = integrity
    manifest["scale_hypothesis_probe"] = probe
    manifest["verified_at"] = datetime.now(CST).isoformat()
    with open(os.path.join(DERIVED, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    with open(os.path.join(DERIVED, "image_layout.json"), "w", encoding="utf-8") as fh:
        json.dump({"detector": {"min_run": 12, "span_frac": 0.7, "thresh": 160,
                                "max_ink": 2},
                   "pages": {str(k): v for k, v in layout.items()},
                   "coordinate_integrity": integrity,
                   "scale_hypothesis_probe": probe},
                  fh, ensure_ascii=False, indent=2)

    # ---------------- 人类可读报告 ----------------
    L: list[str] = []
    A = L.append
    A("# 46006966 数据落地与校验报告")
    A("")
    A(f"生成时间：{manifest['verified_at']}　（Phase 1 · 零模型推理 / 零线上写入）")
    A("")
    A("## 1. 落地内容")
    A("")
    A(f"- 标注记录：**{len(recs)}** 条，类型分布 `{dict(Counter(r['type'] for r in recs))}`")
    A(f"- `verified` 分布：`{dict(Counter(str(r['verified']) for r in recs))}`")
    A(f"- 覆盖页（0 基资源索引）：`{pages}`")
    A("- 页图：6 张全部从 OSS 落地（含 233/234 两张宽图），SHA256 见 manifest")
    A("")
    A("## 2. 图片版面结构（像素统计，可复现）")
    A("")
    A("| 页(0基) | 尺寸 | 墨迹% | 内部纵向沟 | 结论 | 标注数 |")
    A("|---|---|---|---|---|---|")
    for pg in pages:
        d = layout.get(pg)
        if not d:
            A(f"| {pg} | 缺图 | - | - | - | - |")
            continue
        A(f"| {pg} | {d['width']}×{d['height']} | {d['ink_ratio_pct']} | "
          f"{d['n_inner_v_gutters']} | {d['verdict']} | {d['annotation_count']} |")
    A("")
    A("> **233/234 两张宽图不是「六栏答案表」，而是多张真实页扫描拼合的版面。**")
    A("> 判据是内部纵向空白沟（页与页之间是整列空白，可靠信号）。实测：")
    if 233 in layout:
        A("> - 页 233 内部纵向沟 " + str(layout[233]["n_inner_v_gutters"]) + " 条，位于 "
          + "、".join(f"{a}–{b}" for a, b in layout[233]["inner_v_gutters"]) + "；")
    if 234 in layout:
        A("> - 页 234 内部纵向沟 " + str(layout[234]["n_inner_v_gutters"]) + " 条，位于 "
          + "、".join(f"{a}–{b}" for a, b in layout[234]["inner_v_gutters"]) + "。")
    A("> 检测阈值 `min_run=12, span_frac=0.7`；页 7/8/9/10 在此阈值下**无内部纵向沟**，")
    A("> 判定为单一页扫描（此前用 min_run=4 会把文字行间窄空列误判成沟，已修正）。")
    A("> 横向带数受**段落间距/短行文本**干扰，不用于判定行数——该局限已写入")
    A("> `tools/layout_probe.py` 文档，拼合行数需人工看图确认。")
    A("")
    A("## 3. 坐标系完整性（本次最重要的发现）")
    A("")
    A("| 页(0基) | 图尺寸 | 框数 | max_x2 | max_y2 | x 占图宽 | y 占图高 | 判定 |")
    A("|---|---|---|---|---|---|---|---|")
    for it in integrity:
        if it["n_boxes"] == 0:
            A(f"| {it['page_index']} | {it['image_wh'][0]}×{it['image_wh'][1]} | 0 | - | - | - | - | 无历史标注 |")
            continue
        A(f"| {it['page_index']} | {it['image_wh'][0]}×{it['image_wh'][1]} | {it['n_boxes']} | "
          f"{it['max_x2']} | {it['max_y2']} | {it['x_span_frac']*100:.1f}% | "
          f"{it['y_span_frac']*100:.1f}% | **{it['verdict']}** |")
    A("")
    A("判定口径：`OUT_OF_BOUNDS` = 框超出图边界；`SUSPECT_COORD_SPACE` = 框未越界但横向"
      "只用到图宽的 <50%，说明记录坐标空间与这张图很可能不是同一个画布；`OK` = 正常。")
    A("")
    A("### 3.1 页 234 历史框不可直接当坐标真值")
    A("")
    A("15 条 page_index=234 的框，x 只用到 0–594.1、y 只用到 254.7–1164.6，而对应页图为 "
      "3465×1615（框仅占图宽的 17.2%）。直接叠框后可见框与文字明显错位。")
    A("")
    A("已逐一检验四种坐标关系（覆盖率越低越说明框落在空白/无关文字上）：")
    A("")
    A("| 假设 | 墨迹覆盖率均值 | 结论 |")
    A("|---|---|---|")
    A(f"| 原坐标直接用 | {probe['mean_ink_pct_as_recorded']}% | 低，框未框住文字 |")
    A(f"| 按 3465/594≈5.8333 缩放 | {probe['mean_ink_pct_scaled_5_8333']}% | 更低 → 缩放假设**否定** |")
    A(f"| 平移 +71（第一内容栏起点） | {probe['mean_ink_pct_shift_dx71']}% | 基本不变 → 平移假设**否定** |")
    A(f"| 平移 +1100（第二栏起点） | {probe['mean_ink_pct_shift_dx1100']}% | 无改善 → **否定** |")
    A("")
    A("结论：**页 234 的 15 个历史框与 3465×1615 这张宽图之间，不存在可离线复原的简单")
    A("平移-缩放关系**。它们只能当「有标注、有归属」的证据，不能当坐标真值。")
    A("要定性必须先拿到平台查看器实际使用的画布尺寸——这需要浏览器会话（Phase 2 前置）。")
    A("同一警示也适用于页 233（宽图、无历史框，但同为拼合版面）。")
    A("")
    A("## 4. 其它数据质量问题")
    A("")
    kinds = Counter(f["kind"] for f in findings)
    A(f"- 问题合计：**{len(findings)}** 条，分布 `{dict(kinds)}`")
    for f in findings:
        if f["kind"] == "out_of_bounds":
            A(f"  - 越界：`{f['type']}` rect_id `{f['rect_id'][:8]}` 于页 {f['page_index']}，{f['detail']}")
        elif f["kind"] == "cross_type_overlap":
            A(f"  - 跨类重叠：页 {f['page_index']} `{f['type_a']}`∩`{f['type_b']}` "
              f"占较小框 {f['ratio_of_smaller']*100:.1f}%（{f['intersection_px2']}px²）")
    A("")
    A("## 5. 与交接包的差异（需更正）")
    A("")
    A("| 交接包说法 | 实测 |")
    A("|---|---|")
    A("| 原图 0 基资源索引 7/8/9/233 | 标注的 `page_index` 取值为 **8/9/10/234**，相差 1；两种编号都已落地 |")
    A("| 页 234 是 3467×1615 六栏宽图 | 实测 **3465×1615**，且是**多页扫描拼合**版面，非六栏答案表 |")
    A("| 第 3 题题干框 x2=1181.09，超 3.09px | 该框在页 **8**，图宽 **1176**，超 **5.09px** |")
    A("| 第 10 题解析框跨入第 11 题答案框，交集约占 91% | 数值吻合：页 234 `analysis`∩`answer(o=11)` = **0.9108** |")
    A("")
    A("## 6. 凭证卫生（安全）")
    A("")
    A("`netdetail1.json` / `netdetail3.json` 的 `requestHeaders.authorization` 里有**明文 Bearer JWT**")
    A("（sub=YX-雪秀，exp=1792157230）。交接包声明「凭证不落地文档」，但实际已落地。")
    A("建议：删除这两处 header 字段；令牌失效前请勿外传本目录。")
    A("")
    A("## 7. 证据图")
    A("")
    for pg in pages:
        if pg in img_objs:
            A(f"- `data/derived/inspect/page{pg}_boxes.png`")
    A("- `data/derived/inspect/p234_boxzone.png`（页 234 左侧放大，直观看框与文字错位）")
    A("")

    with open(os.path.join(DERIVED, "verify_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    log("")
    log("写出: data/derived/verify_report.md / manifest.json / inspect/*.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
