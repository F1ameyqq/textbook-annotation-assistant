#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/proj.py — 墨迹投影 CLI（复刻 SOP §6.2 的用法）

用法
----
    python -I tools/proj.py page.png S "lines,x1,x2,y1,y2,LABEL" ["cols,y1,y2,x1,x2,LABEL" ...]

- S : 截图相对源图的倍率（输出像素 = clip × scale × devicePixelRatio）。
      本机 dpr=1.5、scale=2 时 S=3。**所有坐标参数与输出都按源图像素**，
      内部读图时按 S 放大对应区域。
- lines : 在 x∈[x1,x2] 范围内逐行统计墨迹，输出 y∈[y1,y2] 窗口内的
          文本行段（ink run，间隔 < min_gap 合并）与空白沟（gap run）。
- cols  : 在 y∈[y1,y2] 范围内逐列统计墨迹，输出 x∈[x1,x2] 窗口内的
          墨迹列段与空白列沟（用于找题间竖缝、题号"."的位置）。

墨迹口径与 layout_probe.py / SOP 一致：gray < 165 记为墨。

可调参数（有默认值，命令行尾追加 `--key=value` 可覆盖）：
    --thresh=165     墨迹灰度阈值
    --min-gap=4      行/段合并间隙（源图像素）
    --max-ink=0      一行/列允许的最大墨像素数（> 此值才算"有墨"行）
    --min-len=3      输出段的最小长度（源图像素）

输出每段一行：`LABEL  LINES  y  60-73  h=14` 或 `LABEL  GAP  y  73-79`。
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台默认 GBK，强制 UTF-8 防注释行乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout_probe import ink_mask  # noqa: E402

DEFAULTS = {"thresh": 165, "min-gap": 4, "max-ink": 0, "min-len": 3}


def _runs(flags: np.ndarray, min_len: int = 1) -> list[tuple[int, int]]:
    """布尔一维数组 → True 段 [(start, end)]。"""
    out: list[tuple[int, int]] = []
    start = None
    for i, v in enumerate(flags):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_len:
                out.append((start, i))
            start = None
    if start is not None and len(flags) - start >= min_len:
        out.append((start, len(flags)))
    return out


def _merge_gap(runs: list[tuple[int, int]], gap: int) -> list[tuple[int, int]]:
    if not runs:
        return []
    out = [runs[0]]
    for s, e in runs[1:]:
        if s - out[-1][1] < gap:
            out[-1] = (out[-1][0], e)
        else:
            out.append((s, e))
    return out


def project(mask: np.ndarray, mode: str, lo1: int, hi1: int, lo2: int, hi2: int,
            max_ink: int) -> tuple[np.ndarray, np.ndarray]:
    """
    返回 (ink_flags, offsets)：
      mode="lines": 统计 x∈[lo1,hi1) 内每行墨数，取 y∈[lo2,hi2) 的行；
      mode="cols" : 统计 y∈[lo1,hi1) 内每列墨数，取 x∈[lo2,hi2) 的列。
    ink_flags[i] = 该线墨数 > max_ink。
    """
    if mode == "lines":
        sub = mask[lo2:hi2, lo1:hi1]
        counts = sub.sum(axis=1)
    else:
        sub = mask[lo1:hi1, lo2:hi2]
        counts = sub.sum(axis=0)
    return counts > max_ink, np.arange(lo2, hi2)


def parse_spec(spec: str) -> tuple[str, int, int, int, int, str]:
    parts = spec.split(",")
    if len(parts) != 6:
        raise SystemExit(f"规格格式错误: {spec!r}（应为 lines,x1,x2,y1,y2,LABEL）")
    mode = parts[0].strip().lower()
    if mode not in ("lines", "cols"):
        raise SystemExit(f"mode 只能是 lines/cols: {spec!r}")
    nums = [int(float(p)) for p in parts[1:5]]
    return mode, nums[0], nums[1], nums[2], nums[3], parts[5].strip()


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    opts = dict(DEFAULTS)
    for a in argv:
        if a.startswith("--") and "=" in a:
            k, v = a[2:].split("=", 1)
            opts[k] = float(v) if "." in v else int(v)

    if len(args) < 3:
        print(__doc__)
        return 2
    img_path, s = Path(args[0]), float(args[1])
    specs = [parse_spec(a) for a in args[2:]]

    mask = ink_mask(Image.open(img_path), thresh=int(opts["thresh"]))
    H, W = mask.shape

    for mode, a1, a2, b1, b2, label in specs:
        # 坐标是源图像素 → 内部按 S 放大
        if mode == "lines":
            lo1, hi1 = int(a1 * s), int(a2 * s)   # x 范围
            lo2, hi2 = int(b1 * s), int(b2 * s)   # y 窗口
        else:
            lo1, hi1 = int(b1 * s), int(b2 * s)   # y 窗口
            lo2, hi2 = int(a1 * s), int(a2 * s)   # x 范围
        lo1, hi1 = max(0, lo1), min(W if mode == "lines" else H, hi1)
        lo2, hi2 = max(0, lo2), min(H if mode == "lines" else W, hi2)

        flags, offs = project(mask, mode, lo1, hi1, lo2, hi2, int(opts["max-ink"]))
        unit = "y" if mode == "lines" else "x"
        ink_runs = _merge_gap(_runs(flags), int(opts["min-gap"]))
        print(f"# {label}  {mode}  扫描{'x' if mode == 'lines' else 'y'}=[{a1},{a2}] "
              f"{'y' if mode == 'lines' else 'x'}窗口=[{b1},{b2}]  S={s}")
        for st, en in ink_runs:
            st_s, en_s = int(offs[st] / s), int(offs[en - 1] / s) + 1
            if en_s - st_s >= int(opts["min-len"]):
                print(f"{label}\t{unit}\t{st_s}-{en_s}\th={en_s - st_s}")
        # 空白沟（仅在 min-len 以上的）
        gap_flags = ~flags
        for st, en in _runs(gap_flags):
            st_s, en_s = int(offs[st] / s), int(offs[en - 1] / s) + 1
            if en_s - st_s >= int(opts["min-len"]):
                print(f"{label}\tGAP\t{unit}\t{st_s}-{en_s}\tw={en_s - st_s}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
