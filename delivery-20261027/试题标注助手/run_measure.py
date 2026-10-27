#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_measure.py — 试题版面测量（交付版，纯本地，不需要登录/浏览器）

客户只需要：输入页码 → 得到每页的「题块候选图」+ 汇总表。

流程
----
1. 从 OSS 公开直链下载源图（无需鉴权、无需登录）
   地址：{oss}/upload_images/{book_id}/{book_id}_page_{N}.jpg，N = 平台页码 − 1
2. 版面测量：栏缝 → 行投影 → OCR 题号锚点 → 题块框
3. 生成确认图（原图 + 彩色框 + 编号）与汇总表

用法
----
    python run_measure.py --pages 28-30
    python run_measure.py --pages 28,29,31 --answer-pages 174-176
    python run_measure.py --pages 28-30 --out 报告_20261027
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 兼容三种放置方式：随包 tools/、仓库根 tools/、同级 tools/
for cand in (HERE / "tools", HERE.parent / "tools", HERE.parent.parent / "tools"):
    if (cand / "page_measure.py").exists():
        sys.path.insert(0, str(cand))
        break

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONFIG_DEFAULT = {
    "book_id": "46007447",
    "oss_base": "https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com/upload_images",
    "page_offset": -1,          # OSS 文件名 = 平台页码 + offset
    "max_width": 1220,
    "thresh": 165,
    "ink_frac": 0.01,
}


def load_config() -> dict:
    cfg = dict(CONFIG_DEFAULT)
    for p in (HERE / "config.json", HERE.parent / "config.json"):
        if p.exists():
            try:
                cfg.update(json.loads(p.read_text(encoding="utf-8")))
            except Exception as e:
                print(f"[警告] config.json 读取失败，用默认值: {e}")
            break
    return cfg


def parse_pages(spec: str) -> list[int]:
    out = []
    for part in spec.replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")[:2]
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def fetch_page(cfg: dict, page: int, cache_dir: Path) -> Path:
    """下载源图；失败抛异常（调用方记录并继续）。"""
    n = page + cfg.get("page_offset", -1)
    url = f"{cfg['oss_base']}/{cfg['book_id']}/{cfg['book_id']}_page_{n}.jpg"
    out = cache_dir / f"{cfg['book_id']}_p{page}.jpg"
    if out.exists() and out.stat().st_size > 10_000:
        return out
    cache_dir.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "measure-helper/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(out, "wb") as f:
        f.write(r.read())
    return out


def imread_u(path: Path):
    """OpenCV 在 Windows 上读不了中文路径 → 自己读字节再解码。"""
    import cv2
    import numpy as np
    buf = np.frombuffer(Path(path).read_bytes(), dtype=np.uint8)
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def imwrite_u(path: Path, img) -> None:
    """同上：中文路径写图。"""
    import cv2
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(path.suffix or ".png", img)
    if not ok:
        raise RuntimeError(f"图片编码失败: {path}")
    path.write_bytes(buf.tobytes())


def measure_ans_page(img: Path, cfg: dict) -> dict:
    """
    答案页只输出「行带」（R1..Rn），不猜题块。
    原因：答案册一页里会横跨多个课时，题号在页内重复（实测 P174: 1,2,5,6,9,11,16,1,4…），
    整页按题号切必然错位；正确做法是人眼先圈定所在课时的那一块。
    """
    import cv2
    import page_measure as pm
    bgr = imread_u(img)
    H, W = bgr.shape[:2]
    mask = pm.ink_mask(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), cfg.get("thresh", 165))
    panels = pm.column_windows(mask)
    bands = []
    for pi, (x1, x2) in enumerate(panels):
        for r in pm.row_segments(mask, x1, x2, 0, H, cfg.get("ink_frac", 0.01)):
            bands.append({"panel": pi, "x1": x1, "x2": x2, "y1": r["y1"], "y2": r["y2"]})
    bands.sort(key=lambda b: (b["panel"], b["y1"]))
    return {"image": str(img), "w": W, "h": H, "panels": panels, "bands": bands}


def make_band_sheet(img: Path, bands: list[dict], out_png: Path, max_width: int) -> None:
    """答案页确认图：每行标 R1..Rn，方便人指定题目块范围。"""
    import cv2
    bgr = imread_u(img)
    H, W = bgr.shape[:2]
    scale = min(1.0, max_width / W)
    if scale < 1.0:
        bgr = cv2.resize(bgr, (int(W * scale), int(H * scale)), interpolation=cv2.INTER_AREA)
    for i, b in enumerate(bands, 1):
        x1, y1, x2, y2 = [int(v * scale) for v in (b["x1"], b["y1"], b["x2"], b["y2"])]
        cv2.rectangle(bgr, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), (200, 160, 60), 1)
        cv2.putText(bgr, f"R{i}", (max(x1 - 46, 4), y2 - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 90, 200), 1, cv2.LINE_AA)
    imwrite_u(out_png, bgr)


def measure_page(img: Path, cfg: dict) -> dict:
    """题目页测量：栏缝 → 行投影 → OCR 题号锚点 → 题块框。"""
    import cv2
    import numpy as np
    import page_measure as pm
    from rapidocr_onnxruntime import RapidOCR

    bgr = imread_u(img)
    if bgr is None:
        raise RuntimeError("图片读取失败")
    H, W = bgr.shape[:2]
    mask = pm.ink_mask(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), cfg.get("thresh", 165))
    panels = pm.column_windows(mask)
    rows_by_panel = [pm.row_segments(mask, x1, x2, 0, H, cfg.get("ink_frac", 0.01))
                     for x1, x2 in panels]
    # OCR 直接吃 ndarray，避免再走中文路径
    res, _ = RapidOCR()(bgr)
    atoms = []
    for item in res or []:
        box, text = item[0], str(item[1])
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        atoms.append({"text": text, "score": float(item[2]) if len(item) > 2 else 0.0,
                      "x1": int(min(xs)), "y1": int(min(ys)),
                      "x2": int(max(xs)), "y2": int(max(ys))})
    questions, debug = pm.build_questions(panels, rows_by_panel, atoms, H)
    return {"image": str(img), "w": W, "h": H, "panels": panels,
            "questions": questions, "debug": debug, "n_atoms": len(atoms)}


def make_sheet(img: Path, questions: list[dict], out_png: Path, max_width: int) -> None:
    """画候选框确认图（不依赖 contact_sheet.py，保持交付包少依赖）。"""
    import cv2
    bgr = imread_u(img)
    H, W = bgr.shape[:2]
    scale = min(1.0, max_width / W)
    if scale < 1.0:
        bgr = cv2.resize(bgr, (int(W * scale), int(H * scale)), interpolation=cv2.INTER_AREA)
    for q in questions:
        x1, y1, x2, y2 = [int(v * scale) for v in q["bbox"]]
        color = (60, 60, 220) if q.get("confidence") == "high" else (0, 165, 255)
        cv2.rectangle(bgr, (x1, y1), (x2, y2), color, 2)
        label = f"Q{q['num']}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        ty = max(y1 - 6, th + 4)
        cv2.rectangle(bgr, (x1, ty - th - 4), (x1 + tw + 6, ty + 4), color, -1)
        cv2.putText(bgr, label, (x1 + 3, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (255, 255, 255), 2, cv2.LINE_AA)
    imwrite_u(out_png, bgr)


def main() -> int:
    ap = argparse.ArgumentParser(description="试题版面测量（交付版）")
    ap.add_argument("--pages", required=True, help="题目页码，如 28-30 或 28,29,31")
    ap.add_argument("--answer-pages", default="", help="答案页码（可选），如 174-176")
    ap.add_argument("--out", default="报告", help="输出目录")
    args = ap.parse_args()

    cfg = load_config()
    out_dir = (HERE / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = out_dir / "_源图"
    pages = parse_pages(args.pages)
    apages = parse_pages(args.answer_pages) if args.answer_pages else []

    print("=" * 62)
    print(f"  试题版面测量   书号 {cfg['book_id']}")
    print(f"  题目页 {pages[0]}–{pages[-1] if len(pages) > 1 else pages[0]}（共 {len(pages)} 页）")
    if apages:
        print(f"  答案页 {apages[0]}–{apages[-1]}（共 {len(apages)} 页）")
    print(f"  输出目录：{out_dir}")
    print("=" * 62)

    rows = []
    all_pages = [(p, "题目") for p in pages] + [(p, "答案") for p in apages]
    for page, kind in all_pages:
        tag = f"{kind}页 P{page}"
        try:
            print(f"\n[{tag}] 下载源图 …")
            img = fetch_page(cfg, page, cache)
            if kind == "答案":
                print(f"[{tag}] 切分行带 …")
                res = measure_ans_page(img, cfg)
                bands = res["bands"]
                png = out_dir / f"第{page}页_答案.png"
                make_band_sheet(img, bands, png, cfg.get("max_width", 1220))
                print(f"[{tag}] 行带 {len(bands)} 条（R1..R{len(bands)}）"
                      f" — 请在这张图上指定「第N课时」所在的行带范围")
                rows.append({"页": page, "类型": kind, "题块数": len(bands),
                             "题号": f"R1-R{len(bands)}",
                             "待确认": "需人工指定课时块范围",
                             "确认图": png.name, "状态": "成功"})
                continue
            print(f"[{tag}] 测量中（OCR 约 20–60 秒）…")
            res = measure_page(img, cfg)
            qs = res["questions"]
            if not qs:
                # 兜底：本页是"上页续页/变式"结构时没有可锚定的题号，给行带 + 明确警告，
                # 不能静默返回 0 题（2026-10-27 P30 实测踩到）
                print(f"[{tag}] 未自动识别出题号（可能是续页/变式结构），改输出行带供人工指定")
                bre = measure_ans_page(img, cfg)
                bands = bre["bands"]
                png = out_dir / f"第{page}页_{kind}_行带.png"
                make_band_sheet(img, bands, png, cfg.get("max_width", 1220))
                rows.append({"页": page, "类型": kind, "题块数": 0,
                             "题号": "-",
                             "待确认": f"未识别题号，已输出 {len(bands)} 条行带（R1-R{len(bands)}），请人工圈定",
                             "确认图": png.name, "状态": "需人工"})
                continue
            low = [q for q in qs if q.get("confidence") != "high"]
            png = out_dir / f"第{page}页_{kind}.png"
            make_sheet(img, qs, png, cfg.get("max_width", 1220))
            nums = [q["num"] for q in qs]
            print(f"[{tag}] 题块 {len(qs)} 个：{nums}" + (f"  待确认 {[q['num'] for q in low]}" if low else ""))
            rows.append({"页": page, "类型": kind, "题块数": len(qs),
                         "题号": " ".join(str(n) for n in nums),
                         "待确认": " ".join(str(q["num"]) for q in low) or "-",
                         "确认图": png.name, "状态": "成功"})
        except Exception as e:
            print(f"[{tag}] 失败：{e}")
            rows.append({"页": page, "类型": kind, "题块数": 0, "题号": "",
                         "待确认": "-", "确认图": "", "状态": f"失败: {e}"})

    # 汇总表
    csv_path = out_dir / "汇总.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["页", "类型", "题块数", "题号", "待确认", "确认图", "状态"])
        w.writeheader()
        w.writerows(rows)

    md = out_dir / "汇总.md"
    ok = sum(1 for r in rows if r["状态"] == "成功")
    need = sum(1 for r in rows if r["状态"] == "需人工")
    bad = len(rows) - ok - need
    lines = [f"# 测量汇总（书 {cfg['book_id']}）", "",
             f"生成时间：{datetime.now():%Y-%m-%d %H:%M}", "",
             f"- 页面共 {len(rows)} 个：**自动成功 {ok}**，需人工 {need}，失败 {bad}",
             f"- 待确认题块 = 脚本没能自动定位题号、靠结构推断的，需要人眼核对", "",
             "| 页 | 类型 | 题块数 | 题号 | 待确认 | 确认图 | 状态 |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['页']} | {r['类型']} | {r['题块数']} | {r['题号']} | "
                     f"{r['待确认']} | {r['确认图']} | {r['状态']} |")
    lines += ["", "## 怎么确认", "",
              "1. 打开 `确认图` 列对应的 PNG，看彩色框是否框住了每道题。",
              "2. 红色框 = 自动定位（可信）；橙色框 = 结构推断（请重点看）。",
              "3. 有问题只需回一句「第N页第X题框偏了」，不用自己改。", ""]
    md.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n完成：自动成功 {ok}，需人工 {need}，失败 {bad}（共 {len(rows)} 页）")
    print(f"汇总表：{md}")
    print(f"明细表：{csv_path}")
    print(f"确认图：{out_dir}")
    return 0 if ok == len(rows) else 0


if __name__ == "__main__":
    sys.exit(main())
