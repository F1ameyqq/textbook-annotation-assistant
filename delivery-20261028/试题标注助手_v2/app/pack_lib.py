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
    with urllib.request.urlopen(req, timeout=90) as r, open(out, "wb") as f:
        f.write(r.read())
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


def base_spec(img: Path) -> dict:
    """生成只含栏窗口的骨架 spec（栏窗口按图片宽度自动估）。"""
    im = read_img(img)
    h, w = im.shape[:2]
    return {
        "src": str(img),
        "kind": "q",
        "canvas": [w, h],
        "cols": {"L": [int(w * 0.06), int(w * 0.48)], "R": [int(w * 0.49), int(w * 0.94)]},
        "y": [0, h],
        "items": [],
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
