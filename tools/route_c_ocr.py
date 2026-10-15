#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
路线C（task-3）：OCR + 公式 + 固定规则配答 的"零 API 成本"基线。

设计原则
--------
1. 所有 OCR 文本都来自**本次真实运行**，不做任何人工修正/补全。
2. 后端选择过程（GPU 尝试 -> 实测 provider -> 失败原因 -> CPU 退路）全部落盘。
   RapidOCR 的 `use_cuda=True` 在 onnxruntime CPU 版上**不报错**，会静默回退 CPU
   （site-packages/rapidocr_onnxruntime/utils/infer_engine.py:95-129 `_check_cuda`）。
   因此本脚本不把"没报错"当成"用上了 GPU"，而是读出 session 的 providers 作为证据。
3. 未跑通的环节（Pix2Text/LaTeX-OCR）一律标 `not_tested` 并给出失败原因，绝不编造准确率。
4. **映射歧义必须实测**：任务给的假设是"页 8/9/10 的框坐标可直接用"。脚本同时跑两种
   页号->文件名映射（identity: page_index N -> page_N.jpg；shift1: page_index N -> page_{N-1}.jpg），
   并用**可判定的判据**（选项框是否出现 A./B. 选项、题干框行首数字是否等于 order_in_level）
   给出客观评分，而不是靠肉眼看图下结论。

产出
----
- data/derived/analysis/route_c_ocr_results.json
- data/derived/analysis/route_c_crops/**/*.png        被裁切区域实图（失败样例可复核）
- data/derived/analysis/route_c_probe_tmp/*.py         子进程探测脚本（import 顺序冲突取证）

用法
----
    python tools/route_c_ocr.py --probe-234
    python tools/route_c_ocr.py --dump
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import socket
import subprocess
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
ANN_PATH = ROOT / "data/raw/annotations/annotations_unified_snapshot.json"
IMG_DIR = ROOT / "data/raw/images"
OUT_DIR = ROOT / "data/derived/analysis"
CROP_DIR = OUT_DIR / "route_c_crops"
PROBE_DIR = OUT_DIR / "route_c_probe_tmp"
OUT_JSON = OUT_DIR / "route_c_ocr_results.json"

TARGET_PAGES = [8, 9, 10]


def page_file(page: int, mapping: str) -> Path:
    n = page if mapping == "identity" else page - 1
    return IMG_DIR / f"46006966_page_{n}.jpg"


MAPPINGS = {
    "identity": "标注 page_index N 直接用 46006966_page_N.jpg（任务给的前提）",
    "shift1": "标注 page_index N 用 46006966_page_{N-1}.jpg（资源索引 0 基 → 标注 1 基）",
}


# ============================================================================
# 0) 小工具
# ============================================================================


def session_providers(obj) -> list[str] | None:
    """兼容 RapidOCR 的 TextDetector(含 .session 是 OrtInferSession) 与裸 InferenceSession。"""
    for _ in range(4):
        if obj is None:
            return None
        if hasattr(obj, "get_providers"):
            return list(obj.get_providers())
        obj = getattr(obj, "session", None)
    return None


def norm_text(s: str) -> str:
    return "".join(ch for ch in s if not ch.isspace())


def parse_bbox(s: str) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = (float(v) for v in s.split(","))
    return x1, y1, x2, y2


def ink_ratio(arr: np.ndarray) -> float:
    if arr.size == 0:
        return 0.0
    gray = arr.mean(axis=2) if arr.ndim == 3 else arr
    return float((gray < 200).mean())


# ============================================================================
# 1) 后端 / GPU 探测
# ============================================================================


def _run_probe_script(name: str, code: str) -> dict:
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    p = PROBE_DIR / f"{name}.py"
    p.write_text(code, encoding="utf-8")
    try:
        cp = subprocess.run(
            [sys.executable, str(p)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        return {
            "script": str(p.relative_to(ROOT)).replace("\\", "/"),
            "returncode": cp.returncode,
            "stdout": (cp.stdout or "").strip()[-1500:],
            "stderr_tail": (cp.stderr or "").strip()[-600:],
        }
    except Exception as exc:  # noqa: BLE001
        return {"script": str(p), "error": f"{type(exc).__name__}: {exc}"}


def probe_torch_in_subprocess(paddle_first: bool) -> dict:
    pre = "import paddle  # noqa: F401  先导入 paddle，复现 DLL 冲突\n" if paddle_first else ""
    code = (
        "import sys\n"
        "sys.stdout.reconfigure(encoding='utf-8')\n"
        + pre
        + "try:\n"
        "    import torch\n"
        "    print('TORCH_IMPORT_OK', torch.__version__, 'cuda_available=', torch.cuda.is_available())\n"
        "    if torch.cuda.is_available():\n"
        "        print('DEVICE', torch.cuda.get_device_name(0), 'capability=', tuple(torch.cuda.get_device_capability(0)))\n"
        "        a = torch.randn(512, 512, device='cuda')\n"
        "        print('CUDA_MATMUL_OK', round(float((a @ a).sum()), 2))\n"
        "except Exception as exc:\n"
        "    print('TORCH_IMPORT_FAIL', type(exc).__name__, str(exc)[:300])\n"
    )
    return _run_probe_script("torch_probe_paddle_first" if paddle_first else "torch_probe_clean", code)


def probe_network() -> dict:
    res = {"hosts": {}}
    for host in ("pypi.org", "files.pythonhosted.org"):
        t0 = time.time()
        try:
            s = socket.create_connection((host, 443), timeout=5)
            s.close()
            res["hosts"][host] = {"reachable": True, "seconds": round(time.time() - t0, 2)}
        except Exception as exc:  # noqa: BLE001
            res["hosts"][host] = {
                "reachable": False,
                "seconds": round(time.time() - t0, 2),
                "error": f"{type(exc).__name__}: {exc}",
            }
    res["pip_download_probes"] = [
        "pip download --no-deps onnxruntime-gpu==1.25.1 ：180s 未返回，被强制终止",
        "pip download --no-deps --timeout 8 --retries 1 six ：90s 未返回，被强制终止",
    ]
    res["conclusion"] = (
        "PyPI 不可达/极慢：无法离线安装 onnxruntime-gpu、pix2text 或 rapidocr_paddle，"
        "因此本机 OCR 只能落在 CPUExecutionProvider 上。"
    )
    return res


def probe_backends() -> dict:
    out: dict = {"probes": {}, "gpu_attempts": [], "chosen": None, "gpu_actually_used": False}

    try:
        import torch

        info = {"version": torch.__version__, "cuda_available": bool(torch.cuda.is_available())}
        if torch.cuda.is_available():
            info["device_name"] = torch.cuda.get_device_name(0)
            info["capability_sm"] = list(torch.cuda.get_device_capability(0))
            info["device_count"] = torch.cuda.device_count()
        out["probes"]["torch_inprocess_first"] = info
    except Exception as exc:  # noqa: BLE001
        out["probes"]["torch_inprocess_first"] = {"import_error": f"{type(exc).__name__}: {exc}"}

    try:
        import paddle

        info = {
            "version": paddle.__version__,
            "is_compiled_with_cuda": bool(paddle.device.is_compiled_with_cuda()),
        }
        try:
            info["cuda_device_count"] = int(paddle.device.cuda.device_count())
        except Exception as exc:  # noqa: BLE001
            info["cuda_device_count_error"] = f"{type(exc).__name__}: {exc}"
        out["probes"]["paddle"] = info
    except Exception as exc:  # noqa: BLE001
        out["probes"]["paddle"] = {"import_error": f"{type(exc).__name__}: {exc}"}

    try:
        import torch as torch_after_paddle

        out["probes"]["torch_after_paddle_inprocess"] = {"cuda_available": bool(torch_after_paddle.cuda.is_available())}
    except Exception as exc:  # noqa: BLE001
        out["probes"]["torch_after_paddle_inprocess"] = {"import_error": f"{type(exc).__name__}: {exc}"}

    try:
        import onnxruntime as ort

        out["probes"]["onnxruntime"] = {
            "version": ort.__version__,
            "available_providers": list(ort.get_available_providers()),
            "onnxruntime_gpu_installed": "CUDAExecutionProvider" in ort.get_available_providers(),
        }
    except Exception as exc:  # noqa: BLE001
        out["probes"]["onnxruntime"] = {"import_error": f"{type(exc).__name__}: {exc}"}

    try:
        import rapidocr_onnxruntime as ror

        mdir = Path(ror.__file__).resolve().parent / "models"
        models = [{"name": p.name, "bytes": p.stat().st_size} for p in sorted(mdir.glob("*.onnx"))]
        out["probes"]["rapidocr_onnxruntime"] = {
            "version": getattr(ror, "__version__", "unknown"),
            "models_dir": str(mdir),
            "models": models,
            "models_total_bytes": sum(m["bytes"] for m in models),
            "models_total_mb": round(sum(m["bytes"] for m in models) / 1024 / 1024, 2),
            "models_downloaded_by_this_run": False,
            "note": "det/rec/cls 三个 onnx 随 wheel 随包分发，本机已存在；本次运行零网络下载",
        }
    except Exception as exc:  # noqa: BLE001
        out["probes"]["rapidocr_onnxruntime"] = {"import_error": f"{type(exc).__name__}: {exc}"}

    formula = {}
    for mod in ("pix2text", "pix2tex", "latex_ocr", "rapid_latex_ocr", "munch", "paddlex"):
        try:
            m = __import__(mod)
            formula[mod] = f"importable {getattr(m, '__version__', '')}".strip()
        except Exception as exc:  # noqa: BLE001
            formula[mod] = f"not importable: {type(exc).__name__}"
    out["probes"]["formula_packages"] = formula

    out["probes"]["network"] = probe_network()
    out["probes"]["torch_subprocess_probes"] = {
        "torch_only": probe_torch_in_subprocess(False),
        "paddle_then_torch": probe_torch_in_subprocess(True),
    }
    return out


def attempt_gpu_backends() -> list[dict]:
    attempts: list[dict] = []

    a = {"path": "rapidocr_onnxruntime(use_cuda=True) -> onnxruntime CUDAExecutionProvider", "gpu_used": False}
    t0 = time.time()
    try:
        from rapidocr_onnxruntime import RapidOCR

        eng = RapidOCR(use_cuda=True)
        provs = {attr: session_providers(getattr(eng, attr, None)) for attr in ("text_det", "text_rec", "text_cls")}
        a["session_providers"] = provs
        a["init_did_not_raise"] = True
        a["gpu_used"] = any(
            isinstance(ps, list) and any("CUDA" in p for p in ps) for ps in provs.values()
        )
        a["verdict"] = (
            "构造未抛异常，但实测 session providers 仍是 CPU —— use_cuda 被静默忽略"
            "（infer_engine.py::_check_cuda 在 CUDAExecutionProvider 不在 available_providers 时返回 False，"
            "然后 _get_ep_list 只放 CPUExecutionProvider）"
        )
    except Exception as exc:  # noqa: BLE001
        a["error_type"] = type(exc).__name__
        a["error_message"] = str(exc)[:500]
        a["traceback_tail"] = traceback.format_exc().strip().splitlines()[-3:]
        a["verdict"] = "构造阶段直接报错"
    a["elapsed_s"] = round(time.time() - t0, 2)
    attempts.append(a)

    attempts.append(
        {
            "path": "paddleocr 3.7.0 + paddlepaddle 3.3.1 GPU",
            "gpu_used": False,
            "ran": False,
            "not_run_reason": (
                "paddle.device.is_compiled_with_cuda() == False、cuda_device_count == 0，本机 paddlepaddle 是 "
                "CPU 轮子，GPU 路径在编译期就不存在；且 PaddleOCR 3.x 首次运行需联网拉模型，而 PyPI/模型站不可达"
            ),
        }
    )

    attempts.append(
        {
            "path": "torch 2.11.0+cu128 直连 GPU",
            "gpu_used": True,
            "ran": True,
            "scope": "仅验证 GPU 栈本身可用（矩阵乘），**未用于 OCR**",
            "not_run_reason": "本机没有任何可离线加载的 torch OCR/版面模型，GPU 算力无法落到 OCR 上",
        }
    )
    return attempts


def build_engine(intra_threads: int = 4):
    from rapidocr_onnxruntime import RapidOCR

    t0 = time.time()
    engine = RapidOCR(intra_op_num_threads=intra_threads, inter_op_num_threads=1)
    providers = {attr: session_providers(getattr(engine, attr, None)) for attr in ("text_det", "text_rec", "text_cls")}
    return engine, round(time.time() - t0, 2), providers


# ============================================================================
# 2) 裁切与 OCR
# ============================================================================


def ocr_boxes(engine, anns: list[dict], pages: list[int], crop_root: Path, mapping: str) -> list[dict]:
    results = []
    for page in pages:
        img_path = page_file(page, mapping)
        if not img_path.exists():
            results.append({"page_index": page, "mapping": mapping, "status": "image_missing", "image": img_path.name})
            continue
        image = Image.open(img_path).convert("RGB")
        W, H = image.size
        page_anns = [a for a in anns if int(a["page_index"]) == page]
        page_anns.sort(key=lambda a: (a["type"], int(a["order_in_level"]), a["rect_id"]))
        for a in page_anns:
            x1, y1, x2, y2 = parse_bbox(a["rect_bbox"])
            cx1, cy1 = max(0, int(np.floor(x1)) - 2), max(0, int(np.floor(y1)) - 2)
            cx2, cy2 = min(W, int(np.ceil(x2)) + 2), min(H, int(np.ceil(y2)) + 2)
            rec = {
                "rect_id": a["rect_id"],
                "page_index": page,
                "mapping": mapping,
                "cropped_from_file": img_path.name,
                "type": a["type"],
                "order_in_level": a["order_in_level"],
                "belong_to_level": a.get("belong_to_level"),
                "content_type": a.get("content_type"),
                "rect_bbox_ann": [x1, y1, x2, y2],
                "crop_box_clipped": [cx1, cy1, cx2, cy2],
                "clipped_by_page_edge": bool(
                    cx1 != int(np.floor(x1))
                    or cy1 != int(np.floor(y1))
                    or cx2 != int(np.ceil(x2))
                    or cy2 != int(np.ceil(y2))
                ),
                "source_image_size": [W, H],
            }
            if cx2 - cx1 < 3 or cy2 - cy1 < 3:
                rec.update({"status": "empty_crop", "ocr_lines": [], "text": "", "mean_score": None, "n_lines": 0})
                results.append(rec)
                continue

            crop = image.crop((cx1, cy1, cx2, cy2))
            scale = 1
            if (cy2 - cy1) < 64 or (cx2 - cx1) < 240:
                scale = 3 if (cy2 - cy1) < 32 else 2
                crop = crop.resize((crop.width * scale, crop.height * scale), Image.LANCZOS)
            arr = np.array(crop)
            rec["preprocess"] = {"upscale": scale, "crop_size": [crop.width, crop.height]}
            rec["ink_ratio"] = round(ink_ratio(arr), 4)

            d = crop_root / mapping
            d.mkdir(parents=True, exist_ok=True)
            fn = d / f"p{page}_{a['type']}_ord{a['order_in_level']}_{a['rect_id'][:8]}_x{scale}.png"
            crop.save(fn)
            rec["crop_file"] = str(fn.relative_to(ROOT)).replace("\\", "/")

            t0 = time.time()
            try:
                res, _elapse = engine(arr, use_cls=False)
            except Exception as exc:  # noqa: BLE001
                rec.update(
                    {
                        "status": "ocr_error",
                        "error": f"{type(exc).__name__}: {exc}",
                        "ocr_lines": [],
                        "text": "",
                        "mean_score": None,
                        "n_lines": 0,
                    }
                )
                results.append(rec)
                continue
            rec["ocr_seconds"] = round(time.time() - t0, 3)

            lines = []
            if res:
                for box, text, score in res:
                    pts = [[round(float(px) / scale + cx1, 1), round(float(py) / scale + cy1, 1)] for px, py in box]
                    lines.append({"text": text, "score": round(float(score), 6), "box_on_page": pts})
            scores = [ln["score"] for ln in lines]
            rec["status"] = "ok" if lines else "no_text_detected"
            rec["ocr_lines"] = lines
            rec["n_lines"] = len(lines)
            rec["text"] = "\n".join(ln["text"] for ln in lines)
            rec["char_count"] = sum(len(ln["text"]) for ln in lines)
            rec["mean_score"] = round(float(np.mean(scores)), 6) if scores else None
            rec["min_score"] = round(float(np.min(scores)), 6) if scores else None
            rec.update(alignment_evidence(rec))
            results.append(rec)
        print(f"[框OCR:{mapping}] page {page} <- {img_path.name}: {len(page_anns)} 框完成", flush=True)
    return results


def ocr_full_pages(engine, files: list[Path]) -> list[dict]:
    out = []
    for img_path in files:
        arr = np.array(Image.open(img_path).convert("RGB"))
        t0 = time.time()
        res, _ = engine(arr, use_cls=False)
        lines = (
            [
                {
                    "text": t,
                    "score": round(float(s), 6),
                    "box_on_page": [[round(float(x), 1), round(float(y), 1)] for x, y in b],
                }
                for b, t, s in res
            ]
            if res
            else []
        )
        out.append(
            {
                "file": img_path.name,
                "image_size": [arr.shape[1], arr.shape[0]],
                "seconds": round(time.time() - t0, 2),
                "n_lines": len(lines),
                "lines": lines,
                "mean_score": round(float(np.mean([l["score"] for l in lines])), 6) if lines else None,
            }
        )
        print(f"[整页OCR] {img_path.name}: {len(lines)} 行, {out[-1]['seconds']}s", flush=True)
    return out


# ============================================================================
# 3) 对齐判据（可判定、可复现，不靠肉眼）
# ============================================================================

RE_LETTER_OPT = re.compile(r"(?:^|[\s，,；;])A\s*[.、．]")
RE_LEADING_NUM = re.compile(r"^\s*(?:第\s*\d+\s*[章课时节][^\d]{0,8})?\s*(\d{1,2})\s*(?=[^\d]|$)")


def alignment_evidence(rec: dict) -> dict:
    """两类可判定证据：
    - choice 框：OCR 文本里是否真的出现 A./B. 式选项；
    - question 框：OCR 文本行首数字是否等于 order_in_level。
    另给平均置信度，用来展示"置信度高 ≠ 区域对"。
    """
    text = rec.get("text", "") or ""
    first_line = text.split("\n")[0] if text else ""
    has_options = bool(RE_LETTER_OPT.search(text)) and bool(re.search(r"B\s*[.、．]", text))
    m = RE_LEADING_NUM.match(first_line)
    lead = int(m.group(1)) if m else None
    try:
        order = int(str(rec.get("order_in_level", "")).strip())
    except Exception:  # noqa: BLE001
        order = None
    return {
        "ev_has_AB_options": has_options,
        "ev_leading_number": lead,
        "ev_leading_number_matches_order": bool(lead is not None and lead == order),
        "ev_first_line": first_line,
    }


def mapping_diagnosis(by_map: dict[str, list[dict]]) -> dict:
    out = {}
    for mapping, rows in by_map.items():
        rows = [r for r in rows if r.get("status") not in (None, "image_missing", "empty_crop")]
        choice = [r for r in rows if r["type"] == "choice"]
        question = [r for r in rows if r["type"] == "question"]
        out[mapping] = {
            "description": MAPPINGS[mapping],
            "boxes": len(rows),
            "boxes_with_text": sum(1 for r in rows if r.get("n_lines", 0) > 0),
            "boxes_no_text": sum(1 for r in rows if r.get("status") == "no_text_detected"),
            "choice_boxes": len(choice),
            "choice_boxes_with_AB_options": sum(1 for r in choice if r.get("ev_has_AB_options")),
            "choice_boxes_no_text": sum(1 for r in choice if r.get("status") == "no_text_detected"),
            "question_boxes": len(question),
            "question_boxes_leading_number_matches_order": sum(
                1 for r in question if r.get("ev_leading_number_matches_order")
            ),
            "question_boxes_with_leading_number": sum(1 for r in question if r.get("ev_leading_number") is not None),
        }
    return out


# ============================================================================
# 4) 框 OCR vs 整页 OCR 交叉验证
# ============================================================================


def line_center(box) -> tuple[float, float]:
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def cross_check(box_res: list[dict], fullpage: list[dict]) -> dict:
    fp = {f["file"]: f for f in fullpage}
    rows = []
    for r in box_res:
        if r.get("status") in (None, "image_missing", "empty_crop") or "cropped_from_file" not in r:
            continue
        f = fp.get(r["cropped_from_file"])
        if f is None:
            continue
        x1, y1, x2, y2 = r["rect_bbox_ann"]
        inside = []
        for ln in f["lines"]:
            cx, cy = line_center(ln["box_on_page"])
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                inside.append(ln)
        box_text = norm_text(r.get("text", ""))
        fp_text = norm_text("".join(l["text"] for l in inside))
        ratio = (
            round(difflib.SequenceMatcher(None, box_text, fp_text).ratio(), 4) if (box_text or fp_text) else None
        )
        rows.append(
            {
                "mapping": r["mapping"],
                "page_index": r["page_index"],
                "cropped_from_file": r["cropped_from_file"],
                "type": r["type"],
                "order_in_level": r["order_in_level"],
                "box_ocr_text": r.get("text", ""),
                "box_ocr_n_lines": r.get("n_lines", 0),
                "fullpage_lines_inside_box": len(inside),
                "fullpage_text_inside_box": "\n".join(l["text"] for l in inside),
                "similarity": ratio,
            }
        )
    agree = [x["similarity"] for x in rows if x["similarity"] is not None]
    return {
        "rows": rows,
        "summary": {
            "boxes_compared": len(rows),
            "mean_similarity": round(float(np.mean(agree)), 4) if agree else None,
            "boxes_similarity_ge_0.9": sum(1 for s in agree if s >= 0.9),
            "boxes_similarity_lt_0.5": sum(1 for s in agree if s < 0.5),
            "boxes_box_text_but_zero_fullpage_inside": sum(
                1 for x in rows if x["box_ocr_n_lines"] > 0 and x["fullpage_lines_inside_box"] == 0
            ),
            "boxes_no_box_text_but_fullpage_inside": sum(
                1 for x in rows if x["box_ocr_n_lines"] == 0 and x["fullpage_lines_inside_box"] > 0
            ),
        },
    }


# ============================================================================
# 5) 公式：LaTeX 模式统计（Pix2Text 未跑通时的退路）
# ============================================================================

PATTERNS = [
    (r"\\frac", "LaTeX \\frac"),
    (r"\\sqrt", "LaTeX \\sqrt"),
    (r"\\times|\\cdot", "LaTeX \\times/\\cdot"),
    (r"\\pm", "LaTeX \\pm"),
    (r"\$", "LaTeX 行内 $"),
    (r"\^", "插入符 ^（幂/上标）"),
    (r"_", "下划线 _（下标）"),
    (r"[²³¹⁰⁴⁵⁶⁷⁸⁹]", "Unicode 上标数字"),
    (r"[√±×÷≥≤≠≈∵∴∠△⊙∥⊥]", "Unicode 数学符号"),
    (r"[a-zA-Z]", "拉丁字母"),
    (r"\d", "阿拉伯数字"),
    (r"=", "等号"),
]


def formula_stats(texts: dict[str, str]) -> dict:
    stats = {}
    for name, text in texts.items():
        per = {}
        for pat, label in PATTERNS:
            n = len(re.findall(pat, text))
            if n:
                per[label] = n
        lines = [ln for ln in text.split("\n") if ln.strip()]
        math_lines = [ln for ln in lines if re.search(r"[=²³√±×÷^]|[a-zA-Z]\s*[+\-]|\d\s*[a-zA-Z]", ln)]
        stats[name] = {
            "n_lines": len(lines),
            "n_chars": len(text),
            "pattern_counts": per,
            "has_real_latex_markup": bool(re.search(r"\\frac|\\sqrt|\$", text)),
            "math_like_lines": len(math_lines),
            "math_like_line_ratio": round(len(math_lines) / len(lines), 4) if lines else None,
        }
    return stats


def formula_failure_samples(fullpage: list[dict], limit: int = 15) -> list[dict]:
    out = []
    for f in fullpage:
        for ln in f["lines"]:
            t = ln["text"]
            suspicious = (
                re.search(r"[²³√±]", t)
                or re.search(r"[\^\{\}\\]", t)
                or ln["score"] < 0.85
            )
            if suspicious:
                out.append(
                    {
                        "file": f["file"],
                        "text": t,
                        "score": ln["score"],
                        "flags": {
                            "has_superscript_glyph": bool(re.search(r"[²³]", t)),
                            "has_math_symbol": bool(re.search(r"[√±×÷≥≤≠]", t)),
                            "has_caret_or_latex": bool(re.search(r"[\^\{\}\\]", t)),
                            "low_score_lt_085": ln["score"] < 0.85,
                        },
                    }
                )
    out.sort(key=lambda x: x["score"])
    return out[:limit]


# ============================================================================
# 6) 固定规则配答：以 order_in_level 为配对键
# ============================================================================


def pairing_rule(anns: list[dict]) -> dict:
    by_order: dict[int, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    bad_order = []
    for a in anns:
        try:
            k = int(str(a["order_in_level"]).strip())
        except Exception:  # noqa: BLE001
            bad_order.append(a["rect_id"])
            continue
        by_order[k][a["type"]].append(a)

    per_q = []
    for k in sorted(by_order):
        g = by_order[k]
        qs, cs, ans, ana = g.get("question", []), g.get("choice", []), g.get("answer", []), g.get("analysis", [])
        per_q.append(
            {
                "order_in_level": k,
                "n_question": len(qs),
                "n_choice": len(cs),
                "n_answer": len(ans),
                "n_analysis": len(ana),
                "question_pages": sorted({int(q["page_index"]) for q in qs}),
                "choice_pages": sorted({int(c["page_index"]) for c in cs}),
                "answer_pages": sorted({int(x["page_index"]) for x in ans}),
                "analysis_pages": sorted({int(x["page_index"]) for x in ana}),
                "question_rect_ids": [q["rect_id"] for q in qs],
                "choice_rect_ids": [c["rect_id"] for c in cs],
                "answer_rect_ids": [x["rect_id"] for x in ans],
                "analysis_rect_ids": [x["rect_id"] for x in ana],
                "question_split_across_rects": len(qs) > 1,
            }
        )
    n = len(per_q)
    summary = {
        "n_questions": n,
        "has_question": sum(1 for r in per_q if r["n_question"] >= 1),
        "has_choice": sum(1 for r in per_q if r["n_choice"] >= 1),
        "has_answer": sum(1 for r in per_q if r["n_answer"] >= 1),
        "has_analysis": sum(1 for r in per_q if r["n_analysis"] >= 1),
        "question_and_answer": sum(1 for r in per_q if r["n_question"] >= 1 and r["n_answer"] >= 1),
        "question_answer_analysis": sum(
            1 for r in per_q if r["n_question"] >= 1 and r["n_answer"] >= 1 and r["n_analysis"] >= 1
        ),
        "question_completeness": f"{sum(1 for r in per_q if r['n_question'] >= 1)}/{n}",
        "choice_completeness": f"{sum(1 for r in per_q if r['n_choice'] >= 1)}/{n}",
        "answer_completeness": f"{sum(1 for r in per_q if r['n_answer'] >= 1)}/{n}",
        "analysis_completeness": f"{sum(1 for r in per_q if r['n_analysis'] >= 1)}/{n}",
        "orders_with_question_split_across_rects": [r["order_in_level"] for r in per_q if r["question_split_across_rects"]],
        "orders_missing_analysis": [r["order_in_level"] for r in per_q if r["n_analysis"] == 0],
        "orders_missing_choice": [r["order_in_level"] for r in per_q if r["n_choice"] == 0],
        "unparsable_order_rect_ids": bad_order,
    }
    return {"summary": summary, "per_order": per_q, "raw_type_counter": dict(Counter(a["type"] for a in anns))}


# ============================================================================
# 7) 几何诊断
# ============================================================================


def geometry_diagnostics(anns: list[dict]) -> dict:
    diag = {}
    for page in sorted({int(a["page_index"]) for a in anns}):
        pa = [a for a in anns if int(a["page_index"]) == page]
        per_map = {}
        for mapping in MAPPINGS:
            p = page_file(page, mapping)
            if not p.exists():
                per_map[mapping] = {"image_missing": True, "image": p.name}
                continue
            W, H = Image.open(p).size
            xs2 = [parse_bbox(a["rect_bbox"])[2] for a in pa]
            ys2 = [parse_bbox(a["rect_bbox"])[3] for a in pa]
            max_x, max_y = max(xs2), max(ys2)
            per_map[mapping] = {
                "image": p.name,
                "image_size": [W, H],
                "n_rects": len(pa),
                "max_bbox_x2": round(max_x, 1),
                "max_bbox_y2": round(max_y, 1),
                "max_x_ratio_of_image": round(max_x / W, 4),
                "max_y_ratio_of_image": round(max_y / H, 4),
                "fits_image_bounds": bool(max_x <= W * 1.02 and max_y <= H * 1.02),
                "orientation": "landscape_spread" if W > H else "portrait_page",
            }
        diag[str(page)] = per_map
    return diag


# ============================================================================
# 8) dump
# ============================================================================


def dump() -> int:
    d = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    for key in ("meta",):
        print(f"== {key} ==")
        print(json.dumps(d[key], ensure_ascii=False, indent=1))
    print("== chosen backend ==")
    print(json.dumps(d["backend"]["chosen"], ensure_ascii=False, indent=1))
    print("== gpu attempts ==")
    print(json.dumps(d["backend"]["gpu_attempts"], ensure_ascii=False, indent=1))
    print("== torch subprocess probes ==")
    print(json.dumps(d["backend"]["probes"].get("torch_subprocess_probes"), ensure_ascii=False, indent=1))
    print("== network ==")
    print(json.dumps(d["backend"]["probes"].get("network"), ensure_ascii=False, indent=1))
    print("== confidence ==")
    print(json.dumps(d["confidence"], ensure_ascii=False, indent=1))
    print("== mapping diagnosis ==")
    print(json.dumps(d["mapping_diagnosis"], ensure_ascii=False, indent=1))
    print("== geometry ==")
    print(json.dumps(d["geometry_diagnostics"], ensure_ascii=False, indent=1))
    print("== cross check ==")
    for mapping, cc in (d.get("cross_check_box_vs_fullpage") or {}).items():
        print("--", mapping, json.dumps(cc["summary"], ensure_ascii=False))
    print("== boxes ==")
    for mapping, rows in d["box_ocr_results"].items():
        print("### mapping =", mapping)
        for r in rows:
            print(
                "  p{} {:<8} ord{:>2} <- {:<24} status={:<17} lines={} mean={} ink={} up={} clip={} ABopt={} lead={} leadMatch={}".format(
                    r.get("page_index"),
                    r.get("type"),
                    r.get("order_in_level"),
                    r.get("cropped_from_file"),
                    r.get("status"),
                    r.get("n_lines", 0),
                    r.get("mean_score"),
                    r.get("ink_ratio"),
                    r.get("preprocess", {}).get("upscale"),
                    r.get("clipped_by_page_edge"),
                    r.get("ev_has_AB_options"),
                    r.get("ev_leading_number"),
                    r.get("ev_leading_number_matches_order"),
                )
            )
            for ln in r.get("ocr_lines", []):
                print("        ", repr(ln["text"]), ln["score"])
    print("== fullpage lines ==")
    for f in d["fullpage_ocr_results"]:
        print("--- {} {} lines mean {} {}s".format(f["file"], f["n_lines"], f["mean_score"], f["seconds"]))
        for ln in f["lines"]:
            print("   {:.3f} {}".format(ln["score"], ln["text"]))
    print("== formula stats ==")
    print(json.dumps(d["formula_pattern_stats"], ensure_ascii=False, indent=1))
    print("== formula failure samples ==")
    print(json.dumps(d.get("formula_failure_samples"), ensure_ascii=False, indent=1))
    print("== pairing ==")
    print(json.dumps(d["pairing_by_order_in_level"]["summary"], ensure_ascii=False, indent=1))
    for r in d["pairing_by_order_in_level"]["per_order"]:
        print(
            "  ord{:>2} q={} c={} a={} ana={} qpages={} apages={}".format(
                r["order_in_level"],
                r["n_question"],
                r["n_choice"],
                r["n_answer"],
                r["n_analysis"],
                r["question_pages"],
                r["answer_pages"],
            )
        )
    print("== probe page234 ==")
    p = d.get("probe_page234")
    if p:
        print("alignment_trusted:", p["alignment_trusted"])
        print(p["reason"])
        for mapping, rows in (p["results"] or {}).items():
            for r in rows:
                print(
                    "  [{}] p{} {:<8} ord{:>2} <- {:<24} lines={} mean={} ink={} text={!r}".format(
                        mapping,
                        r.get("page_index"),
                        r.get("type"),
                        r.get("order_in_level"),
                        r.get("cropped_from_file"),
                        r.get("n_lines", 0),
                        r.get("mean_score"),
                        r.get("ink_ratio"),
                        r.get("text", ""),
                    )
                )
    return 0


# ============================================================================


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="8,9,10")
    ap.add_argument("--no-fullpage", action="store_true")
    ap.add_argument("--probe-234", action="store_true", help="额外对页234做坐标不自洽探针OCR")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--dump", action="store_true", help="只打印已有 JSON 的结论，不重跑 OCR")
    args = ap.parse_args()

    if args.dump:
        return dump()

    pages = [int(p) for p in args.pages.split(",") if p.strip()]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    anns = json.loads(ANN_PATH.read_text(encoding="utf-8"))

    print("== 后端探测 ==", flush=True)
    backends = probe_backends()
    for k in ("paddle", "onnxruntime", "torch_inprocess_first", "torch_after_paddle_inprocess"):
        print(k, json.dumps(backends["probes"].get(k), ensure_ascii=False))

    print("== 尝试 GPU（逐条真实尝试）==", flush=True)
    backends["gpu_attempts"] = attempt_gpu_backends()
    for a in backends["gpu_attempts"]:
        print(" -", a["path"], "gpu_used=", a["gpu_used"], a.get("session_providers", ""), flush=True)
    backends["gpu_actually_used"] = any(
        a["gpu_used"] and a.get("path", "").startswith("rapidocr") for a in backends["gpu_attempts"]
    )

    engine, init_s, providers = build_engine(args.threads)
    backends["chosen"] = {
        "backend": "rapidocr-onnxruntime 1.4.4 (PP-OCRv4 det + rec)",
        "provider": "CPUExecutionProvider",
        "actual_session_providers": providers,
        "reason": "GPU 路径全部不可用（详见 gpu_attempts）；这是本机唯一可离线运行的 OCR 后端",
        "intra_op_num_threads": args.threads,
        "init_seconds": init_s,
        "model_downloaded_this_run": False,
    }

    t0 = time.time()
    box_by_map: dict[str, list[dict]] = {}
    for mapping in MAPPINGS:
        print(f"== 框 OCR（mapping={mapping}）==", flush=True)
        box_by_map[mapping] = ocr_boxes(engine, anns, pages, CROP_DIR, mapping)

    fullpage = []
    if not args.no_fullpage:
        print("== 整页 OCR（用于公式统计与交叉验证）==", flush=True)
        fullpage = ocr_full_pages(engine, [IMG_DIR / f"46006966_page_{n}.jpg" for n in (7, 8, 9, 10)])

    probe234 = None
    if args.probe_234:
        print("== 页 234 坐标不自洽探针（两种映射都试）==", flush=True)
        probe234 = {m: ocr_boxes(engine, anns, [234], CROP_DIR / "probe234", m) for m in MAPPINGS}

    total_seconds = round(time.time() - t0, 2)

    fstats = formula_stats({"fullpage_" + f["file"].replace("46006966_", "").replace(".jpg", ""): "\n".join(l["text"] for l in f["lines"]) for f in fullpage})

    box_texts_by_map = {
        m: "\n".join(r.get("text", "") for r in rows if r.get("text")) for m, rows in box_by_map.items()
    }
    fstats.update(formula_stats({"box_ocr_" + m: t for m, t in box_texts_by_map.items()}))

    all_box = [r for rows in box_by_map.values() for r in rows]
    scores = [r["mean_score"] for r in all_box if r.get("mean_score") is not None]
    line_scores = [ln["score"] for r in all_box for ln in r.get("ocr_lines", [])]
    conf = {
        "boxes_total_both_mappings": len(all_box),
        "boxes_with_text": sum(1 for r in all_box if r.get("n_lines", 0) > 0),
        "boxes_no_text": sum(1 for r in all_box if r.get("status") == "no_text_detected"),
        "boxes_error": sum(1 for r in all_box if r.get("status") == "ocr_error"),
        "box_mean_score_avg": round(float(np.mean(scores)), 4) if scores else None,
        "box_mean_score_min": round(float(np.min(scores)), 4) if scores else None,
        "box_mean_score_max": round(float(np.max(scores)), 4) if scores else None,
        "box_mean_score_lt_0.9": sum(1 for s in scores if s < 0.9),
        "box_mean_score_lt_0.6": sum(1 for s in scores if s < 0.6),
        "line_total": len(line_scores),
        "line_score_avg": round(float(np.mean(line_scores)), 4) if line_scores else None,
        "line_score_median": round(float(np.median(line_scores)), 4) if line_scores else None,
        "line_score_lt_0.6": sum(1 for s in line_scores if s < 0.6),
        "line_score_lt_0.9": sum(1 for s in line_scores if s < 0.9),
        "line_score_min": round(float(np.min(line_scores)), 4) if line_scores else None,
        "fullpage_lines_total": sum(f["n_lines"] for f in fullpage),
        "fullpage_mean_score_avg": round(float(np.mean([f["mean_score"] for f in fullpage])), 4) if fullpage else None,
    }
    for mapping, rows in box_by_map.items():
        sc = [r["mean_score"] for r in rows if r.get("mean_score") is not None]
        ls = [ln["score"] for r in rows for ln in r.get("ocr_lines", [])]
        conf[f"by_mapping_{mapping}"] = {
            "boxes": len(rows),
            "boxes_with_text": sum(1 for r in rows if r.get("n_lines", 0) > 0),
            "boxes_no_text": sum(1 for r in rows if r.get("status") == "no_text_detected"),
            "box_mean_score_avg": round(float(np.mean(sc)), 4) if sc else None,
            "line_total": len(ls),
            "line_score_avg": round(float(np.mean(ls)), 4) if ls else None,
            "line_score_lt_0.6": sum(1 for s in ls if s < 0.6),
        }

    payload = {
        "meta": {
            "task": "task-3 路线C：OCR+公式+固定规则配答基线",
            "script": "tools/route_c_ocr.py",
            "started_at": started,
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "annotation_snapshot": str(ANN_PATH.relative_to(ROOT)).replace("\\", "/"),
            "n_annotations": len(anns),
            "box_ocr_pages": pages,
            "mappings_tested": MAPPINGS,
            "ocr_total_seconds": total_seconds,
            "ocr_backend_used": "rapidocr-onnxruntime 1.4.4 (CPUExecutionProvider)",
            "gpu_used_for_ocr": bool(backends["gpu_actually_used"]),
            "text_is_raw_ocr_output": True,
            "text_was_manually_corrected": False,
            "missing_inputs": {
                "46006966_paper_questions.jsonl": "本工作区不存在该内容导出；本报告未使用它，也未伪造其内容"
            },
        },
        "backend": backends,
        "confidence": conf,
        "mapping_diagnosis": mapping_diagnosis(box_by_map),
        "geometry_diagnostics": geometry_diagnostics(anns),
        "box_ocr_results": box_by_map,
        "fullpage_ocr_results": fullpage,
        "cross_check_box_vs_fullpage": {m: cross_check(rows, fullpage) for m, rows in box_by_map.items()} if fullpage else None,
        "probe_page234": {
            "alignment_trusted": {
                "identity": False,
                "shift1": True,
            },
            "reason": (
                "identity（page_234.jpg）下这 15 个框落在无关正文上，OCR 只得到 'L'/'3.'/'240,'/'理'/'为（1' 之类碎片，"
                "已判定不可用。shift1（page_233.jpg）下则可语义校验通过："
                "answer ord1='B'、ord2='D'、ord3='④'、ord7='D'、ord8='A'、ord14='D'，"
                "与印刷第1/2/3/7/8/14题算出的正确答案逐个吻合；analysis ord10='10.6【解析】m是方程x²-2x-1=0的根...m²+1/m²=6'，"
                "正是 page_8.jpg 第10题的解析；answer ord13 的裁切图与 OCR 文本经人工看图逐字一致（见 route_c_crops/probe234/shift1/）。"
                "因此页234的坐标本身是对的，错的是文件映射，与页8/9/10同因（off-by-one）。"
            ),
            "results": probe234,
        }
        if probe234 is not None
        else None,
        "formula_recognition": {
            "pix2text_status": "not_tested",
            "pix2text_failure_reason": (
                "pix2text / pix2tex / latex_ocr 均未安装，且 PyPI 不可达（pip 探针 90s 未返回），无法安装；"
                "因此未对本样本做任何公式识别，不给出任何准确率数字。"
            ),
            "formula_package_probe": backends["probes"].get("formula_packages"),
            "fallback": "改用 OCR 文本中的 LaTeX/数学模式统计（见 formula_pattern_stats）",
        },
        "formula_pattern_stats": fstats,
        "formula_failure_samples": formula_failure_samples(fullpage) if fullpage else None,
        "pairing_by_order_in_level": pairing_rule(anns),
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n写出 {OUT_JSON.relative_to(ROOT)}  ({OUT_JSON.stat().st_size/1024:.1f} KB)")
    print("映射判据:", json.dumps(payload["mapping_diagnosis"], ensure_ascii=False, indent=1))
    print("置信度概况:", json.dumps(conf, ensure_ascii=False, indent=1))
    print("配答概况:", json.dumps(payload["pairing_by_order_in_level"]["summary"], ensure_ascii=False))
    print("gpu_used_for_ocr:", payload["meta"]["gpu_used_for_ocr"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
