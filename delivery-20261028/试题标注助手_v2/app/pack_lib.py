#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
app/pack_lib.py — 交付包内部共用函数（客户不需要直接调用）

职责：
  1. 从 OSS 下载教材页图（公开直链，无需登录）
  2. 调用 measure_page_adapt.py 做行分割
  3. 画「行号叠加图」和「框位验收图」

坐标系：一律用**源图像素**（canvas 设成图片尺寸，SS=1），避免 canvas 裁切带来的漂移。
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import cv2
import numpy as np

APP = Path(__file__).resolve().parent
ROOT = APP.parent                      # 交付包根目录
SRC_DIR = ROOT / "源图"
SPEC_DIR = ROOT / "specs"
OUT_DIR = ROOT / "报告"

OSS = "https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com/upload_images"


def cfg_book() -> str:
    """书号：优先 config.json，缺失时退回 config.example.json（并提示）。"""
    for name in ("config.json", "config.example.json"):
        p = APP / name
        if p.exists():
            cfg = json.loads(p.read_text(encoding="utf-8"))
            book = str(cfg["platform"]["fileId"])
            if name != "config.json":
                print(f"[提示] 没有 config.json，暂用模板里的书号 {book}（请运行 1_安装.bat 生成配置）")
            return book
    raise SystemExit("[错误] app 目录下找不到 config.json / config.example.json，请重新解压交付包")


def download(page: int, book: str | None = None) -> Path:
    """平台页码 page → OSS 文件 page-1。"""
    book = book or cfg_book()
    out = SRC_DIR / f"{book}_p{page}.jpg"
    if out.exists() and out.stat().st_size > 10_000:
        return out
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    n = page - 1
    url = f"{OSS}/{book}/{book}_page_{n}.jpg"
    req = urllib.request.Request(url, headers={"User-Agent": "annotation-helper/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r, open(out, "wb") as f:
            f.write(r.read())
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:200]
        except Exception:
            pass
        if e.code == 403 and "UserDisable" in body:
            raise SystemExit(
                "\n[图床不可用] 平台图床返回 403 UserDisable —— 通常是平台方停用了 OSS 账号。\n"
                "  这不是本工具的配置问题，请联系平台方恢复图床，或改用浏览器截图取图。\n"
                f"  下载地址：{url}\n")
        if e.code == 404:
            raise SystemExit(f"\n[页码不存在] {url} 返回 404，请确认平台页码是否正确。\n")
        raise SystemExit(f"\n[下载失败] HTTP {e.code}：{url}\n{body}\n")
    return out


def read_img(path: Path):
    return cv2.imdecode(np.frombuffer(Path(path).read_bytes(), np.uint8), cv2.IMREAD_COLOR)


def write_img(path: Path, img) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(Path(path).suffix or ".png", img)
    if not ok:
        raise RuntimeError(f"图片编码失败: {path}")
    Path(path).write_bytes(buf.tobytes())


def dump_rows(spec_path: Path) -> str:
    r = subprocess.run([sys.executable, "-I", str(APP / "measure_page_adapt.py"),
                        str(spec_path), "--dump-rows"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout


def run_measure(spec_path: Path, out_path: Path) -> str:
    r = subprocess.run([sys.executable, "-I", str(APP / "measure_page_adapt.py"),
                        str(spec_path), str(out_path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def detect_cols(img: Path, thresh: int = 170):
    """
    按墨迹投影自动找双栏窗口（不要用页宽比例猜——实测会切掉行尾括号、把栏间竖线算进右栏）。

    做法：整页列投影 → 找贯穿高度的空白带 → 取中间最宽的那条当栏缝 →
    L = [左墨迹起点, 缝左], R = [缝右, 右墨迹终点]。
    找不到缝（单栏页）时退回整幅宽度。
    """
    im = read_img(img)
    h, w = im.shape[:2]
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    ink = (gray < thresh).sum(axis=0)
    blank = ink <= 2                              # 该列几乎无墨（绝对阈值；2% 会把右栏首字误判为空白）
    runs, start = [], None
    for x, b in enumerate(blank):
        if b and start is None:
            start = x
        elif not b and start is not None:
            runs.append((start, x)); start = None
    if start is not None:
        runs.append((start, w))
    # 只考虑页面中部（10%~90%）的空白带，取最宽
    mid = [(a, b) for a, b in runs if a > w * 0.10 and b < w * 0.90]
    mid.sort(key=lambda r: r[1] - r[0], reverse=True)
    if not mid or (mid[0][1] - mid[0][0]) < 6:
        # 单栏
        cols = {"L": [int(w * 0.04), int(w * 0.96)], "R": [int(w * 0.04), int(w * 0.96)]}
        return cols, False
    inked = [x for x in range(w) if ink[x] > 0]
    left_edge = max(0, inked[0] - 4)
    right_edge = min(w, inked[-1] + 4)

    # 优先找「竖向分隔线」：贯穿式高墨列（实测 617-629 那条线，墨值 100-180）。
    # 之前按空白带切会把线右侧的首字归到左栏，或把线算进右栏。
    dividers = [x for x in range(int(w * 0.30), int(w * 0.70)) if ink[x] > h * 0.35]
    if dividers:
        cut = (dividers[0] + dividers[-1]) // 2
        cols = {"L": [left_edge, cut - 1], "R": [cut + 1, right_edge]}
        return cols, True

    g0, g1 = mid[0]
    cols = {"L": [left_edge, g0 - 3], "R": [g1 + 3, right_edge]}
    return cols, True


def base_spec(img: Path) -> dict:
    """生成骨架 spec：栏窗口自动检测 + 更宽松的墨迹阈值（保分数细线）。"""
    im = read_img(img)
    h, w = im.shape[:2]
    cols, two_col = detect_cols(img)
    return {
        "src": str(img),
        "kind": "q",
        "canvas": [w, h],
        "cols": cols,
        "y": [0, h],
        "th": 170,        # 实测 200 会切掉分数上横线；170 能保住
        "min_ink": 5,     # 20 会把细带当噪声
        "items": [],
        "_two_col": two_col,
    }


def draw_rowmap(spec: dict, out_png: Path) -> int:
    """把行号画到图上。返回行数。"""
    tmp = SPEC_DIR / "_rows_tmp.json"
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    out = dump_rows(tmp)
    import re
    pat = re.compile(r"^([LR]\d+|\d+)\s+y\[\s*([\d.]+),\s*([\d.]+)\]")
    rows = {}
    for ln in out.splitlines():
        m = pat.match(ln.strip())
        if not m:
            continue
        label, y0, y1 = m.group(1), float(m.group(2)), float(m.group(3))
        tag = label[0] if label[0].isalpha() else ""
        rows.setdefault(tag, []).append((int(label[len(tag):]), y0, y1))

    img = read_img(Path(spec["src"]))
    for tag, rs in rows.items():
        x0, x1 = spec["cols"][tag]
        color = (0, 120, 255) if tag == "L" else (0, 180, 120)
        for idx, ya, yb in rs:
            cv2.line(img, (x0, int(ya)), (x1, int(ya)), color, 1)
            cv2.putText(img, f"{tag}{idx:02d}", (x0 - 52 if tag == "L" else x0 + 2, int(ya) + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    write_img(out_png, img)
    return sum(len(v) for v in rows.values())


def draw_overlay(data: list[dict], img_path: Path, out_png: Path) -> tuple[int, int]:
    img = read_img(img_path)
    nq = nw = 0

    def box(b, color, label):
        x0, y0, x1, y1 = [int(v) for v in b]
        cv2.rectangle(img, (x0, y0), (x1, y1), color, 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(img, (x0, max(y0 - th - 5, 0)), (x0 + tw + 4, max(y0 - 1, th + 4)), color, -1)
        cv2.putText(img, label, (x0 + 2, max(y0 - 4, th + 2)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    for it in data:
        for i, b in enumerate(it.get("q") or []):
            box(b, (40, 40, 220), f"Q{it['n']}")
            nq += 1
        for i, b in enumerate(it.get("w") or []):
            box(b, (40, 160, 40), f"W{it['n']}.{i+1}")
            nw += 1
    write_img(out_png, img)
    return nq, nw
