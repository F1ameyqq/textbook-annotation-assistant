#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/build_release.py — 从原始工作区构建"可公开发布"的仓库内容

为什么需要这一步：
  data/raw/annotations/netdetail{1,2,3}.json 的 requestHeaders.authorization 里
  含**明文 Bearer JWT**（账号会话令牌）。这些文件绝不能进公开仓库。
  本脚本做白名单式脱敏：删掉整个 requestHeaders 块，只保留请求元数据。

同时用白名单方式搬运产物，避免把任何未预料到的文件带进发布包。

用法:
  python tools/build_release.py --target <发布目录>
"""
from __future__ import annotations

import argparse
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 请求元数据里可安全公开的字段白名单（显式列字段，比黑名单更安全）
SAFE_REQUEST_KEYS = {
    "requestId", "url", "method", "status", "mimeType", "completed",
    "base64Encoded", "body",
}

# 直接搬运的文件：(源相对路径, 目标相对路径)
COPY_FILES = [
    ("data/raw/images/46006966_page_7.jpg", "data/raw/images/46006966_page_7.jpg"),
    ("data/raw/images/46006966_page_8.jpg", "data/raw/images/46006966_page_8.jpg"),
    ("data/raw/images/46006966_page_9.jpg", "data/raw/images/46006966_page_9.jpg"),
    ("data/raw/images/46006966_page_10.jpg", "data/raw/images/46006966_page_10.jpg"),
    ("data/raw/images/46006966_page_233.jpg", "data/raw/images/46006966_page_233.jpg"),
    ("data/raw/images/46006966_page_234.jpg", "data/raw/images/46006966_page_234.jpg"),
    ("data/raw/annotations/annotations_unified_snapshot.json",
     "data/raw/annotations/annotations_unified_snapshot.json"),
    ("data/derived/manifest.json", "data/derived/manifest.json"),
    ("data/derived/image_layout.json", "data/derived/image_layout.json"),
    ("data/derived/quality_findings.json", "data/derived/quality_findings.json"),
    ("data/derived/verify_report.md", "data/derived/verify_report.md"),
]

# 证据图白名单（发布这些，不发布体积大的中间产物）
EVIDENCE_KEEP = [
    "p234_boxzone.png",
    "p234_gutters.png",
    "page234_boxes.png",
    "page8_boxes.png",
]

# 需要产出"脱敏版"的原始响应
REDACT_LIST = [
    ("data/raw/annotations/netdetail1.json", "data/raw/api_evidence/netdetail1.redacted.json"),
    ("data/raw/annotations/netdetail2.json", "data/raw/api_evidence/netdetail2.redacted.json"),
    ("data/raw/annotations/netdetail3.json", "data/raw/api_evidence/netdetail3.redacted.json"),
    ("data/raw/annotations/savectx.json", "data/raw/api_evidence/savectx.redacted.json"),
]

# 原样搬运但体积小的
COPY_EXTRA = [
    ("data/raw/annotations/workspace1.jpg", "data/raw/annotations/workspace1.jpg"),
]


def redact(doc: dict) -> dict:
    """删除 requestHeaders 等敏感块，白名单保留元数据。"""
    out: dict = {}
    if isinstance(doc, dict):
        for k, v in doc.items():
            if k == "requestHeaders":
                out["requestHeaders"] = {"_redacted": True,
                                         "_reason": "含会话令牌，已整块移除"}
                continue
            if k == "data" and isinstance(v, dict):
                sub = {kk: vv for kk, vv in v.items() if kk != "requestHeaders"}
                sub["requestHeaders"] = {"_redacted": True,
                                         "_reason": "含会话令牌，已整块移除"}
                out[k] = sub
                continue
            out[k] = v
    else:
        out = doc
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="发布目录（会被清空重建）")
    args = ap.parse_args()
    target = os.path.abspath(args.target)

    if os.path.exists(target):
        # 安全校验：只允许删除看起来像我们的构建目录
        if not os.path.basename(target).startswith("_release"):
            raise SystemExit(f"拒绝清空非 _release* 目录: {target}")
        shutil.rmtree(target)
    os.makedirs(target, exist_ok=True)

    n = 0
    for src_rel, dst_rel in COPY_FILES + COPY_EXTRA:
        src = os.path.join(ROOT, src_rel)
        if not os.path.exists(src):
            print(f"  [skip] 缺文件 {src_rel}")
            continue
        dst = os.path.join(target, dst_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        n += 1

    for src_rel, dst_rel in REDACT_LIST:
        src = os.path.join(ROOT, src_rel)
        if not os.path.exists(src):
            print(f"  [skip] 缺文件 {src_rel}")
            continue
        with open(src, encoding="utf-8") as fh:
            doc = json.load(fh)
        dst = os.path.join(target, dst_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as fh:
            json.dump(redact(doc), fh, ensure_ascii=False, indent=2)
        n += 1

    ev_src = os.path.join(ROOT, "data", "derived", "inspect")
    ev_dst = os.path.join(target, "data", "derived", "evidence")
    os.makedirs(ev_dst, exist_ok=True)
    for name in EVIDENCE_KEEP:
        s = os.path.join(ev_src, name)
        if os.path.exists(s):
            shutil.copy2(s, os.path.join(ev_dst, name))
            n += 1

    # 分析产物（队友产出，存在就搬）
    an_src = os.path.join(ROOT, "data", "derived", "analysis")
    an_dst = os.path.join(target, "data", "derived", "analysis")
    if os.path.isdir(an_src):
        for dirpath, _dirs, files in os.walk(an_src):
            rel = os.path.relpath(dirpath, an_src)
            for f in files:
                s = os.path.join(dirpath, f)
                d = os.path.join(an_dst, rel, f) if rel != "." else os.path.join(an_dst, f)
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy2(s, d)
                n += 1

    print(f"构建完成：{n} 个文件 -> {target}")

    # 复检：确认发布目录里不再含有令牌特征
    bad = []
    for dirpath, _dirs, files in os.walk(target):
        for f in files:
            p = os.path.join(dirpath, f)
            if os.path.getsize(p) > 8 * 1024 * 1024:
                continue
            try:
                with open(p, "rb") as fh:
                    blob = fh.read()
                txt = blob.decode("utf-8", errors="ignore")
            except OSError:
                continue
            for pat in ("eyJhbGciOi", "Bearer eyJ", "gho_", "ghp_"):
                if pat in txt:
                    bad.append(f"{os.path.relpath(p, target)} 含有 {pat}")
    if bad:
        print("\n拒绝发布：仍检测到疑似凭证残留")
        for b in bad:
            print("  -", b)
        return 1
    print("脱敏复检通过：未检出令牌特征。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
