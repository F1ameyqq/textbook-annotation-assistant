"""Ordinary local images/text -> immutable source pages and source-bound OCR.

No network client or remote model backend is used here. Cache misses are explicit;
an interrupted/failed recognition intent is never retried by changing the lesson.
"""
from __future__ import annotations

import copy
import importlib.metadata
import io
import math
from pathlib import Path
import re

from .store import Hold, byte_hash, digest, encoded

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def page_numbers(value, count):
    if not value or value.strip() in {"全部", "all", "*"}:
        return list(range(1, count + 1))
    result = []
    for piece in value.replace("，", ",").split(","):
        match = re.fullmatch(r"\s*([1-9][0-9]*)(?:\s*[-—]\s*([1-9][0-9]*))?\s*", piece)
        if not match:
            raise Hold("页范围请填写 1-3,5 或 全部。")
        lo, hi = int(match[1]), int(match[2] or match[1])
        if not 1 <= lo <= hi <= count:
            raise Hold("页范围超出所选材料。")
        result.extend(range(lo, hi + 1))
    if len(set(result)) != len(result) or result != sorted(result):
        raise Hold("请按顺序选择页码，不要重复。")
    return result


def _local(path):
    value = str(path)
    if value.startswith(("\\\\", "//")) or "://" in value:
        raise Hold("请选择本地材料。")
    path = Path(path).resolve(strict=True)
    if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES | {".txt"}:
        raise Hold("当前支持 PNG/JPEG/TIFF 等单页图片及 UTF-8 TXT；请先导出其他文档的页面。")
    if path.stat().st_size > 64 * 1024 * 1024:
        raise Hold("单个材料超过 64 MiB，请分成页面。")
    return path


def _copy_bytes(store, raw, suffix):
    directory = store.root / "sources"
    directory.mkdir(exist_ok=True)
    path = directory / (byte_hash(raw) + suffix)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
    except FileExistsError:
        if path.read_bytes() != raw:
            raise Hold("缓存来源字节已改变。")
    return str(path)


def import_pages(store, files, *, role, pages="全部"):
    from PIL import Image
    if role not in {"question", "answer"}:
        raise Hold("请选择题目材料或答案材料。")
    available = []
    for supplied in files:
        path = _local(supplied)
        raw = path.read_bytes()
        stored = _copy_bytes(store, raw, path.suffix.lower())
        base = {"raw_sha256": byte_hash(raw), "raw_path": stored, "filename": path.name, "role": role}
        if path.suffix.lower() == ".txt":
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeError:
                raise Hold("文字材料需要 UTF-8 编码。") from None
            if "\0" in text:
                raise Hold("文字材料含二进制内容。")
            for index, chunk in enumerate(text.split("\f"), 1):
                available.append({**base, "kind": "text", "file_page": index, "text": chunk})
        else:
            with Image.open(io.BytesIO(raw)) as image:
                if getattr(image, "n_frames", 1) != 1:
                    raise Hold("请将多页图片拆成单页后选择。")
                if image.width * image.height > 40_000_000:
                    raise Hold("单页像素超过 4000 万，请先降低分辨率。")
                image.load()
                available.append({**base, "kind": "image", "file_page": 1,
                                  "width": image.width, "height": image.height})
    selected = page_numbers(pages, len(available))
    if not selected:
        return []
    result = []
    seen = set()
    for number in selected:
        item = available[number - 1]
        identity = digest([item["raw_sha256"], item["file_page"]])
        if identity in seen:
            raise Hold("同一来源页被重复选择。")
        seen.add(identity)
        item.update(asset_id="page-" + identity[:24], selected_page=number)
        result.append(item)
    return result


def verify_sources(pages):
    from annotation.recognition.content_review import SourceChanged
    for item in pages:
        if byte_hash(Path(item["raw_path"]).read_bytes()) != item["raw_sha256"]:
            raise SourceChanged("材料原件已改变，请保留任务并重新导入正确材料。")


def engine_identity():
    from annotation.recognition import baseline
    versions = {}
    for package in ("numpy", "Pillow", "rapidocr-onnxruntime", "onnxruntime"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    versions["opencv"] = None
    for package in ("opencv-python-headless", "opencv-python"):
        try:
            versions["opencv"] = importlib.metadata.version(package)
            break
        except importlib.metadata.PackageNotFoundError:
            pass
    return {"name": "B_LOCAL_RAPIDOCR", "baseline": byte_hash(Path(baseline.__file__).read_bytes()),
            "backend": byte_hash(baseline.LEGACY_PATH.read_bytes()), "packages": versions}


def ocr_page(store, page, book, *, allow_local_ocr=False):
    """Call the existing B adapter once; the customer never supplies evidence."""
    from annotation.recognition.baseline import recognize
    identity = engine_identity()
    key = digest([book, page["raw_sha256"], identity])
    prior = store.operation("recognition", key)
    if prior is not None:
        if prior["state"] != "COMPLETE":
            raise Hold("这张原图已有未完成或失败的识别记录；先核对原记录，不能自动重跑。")
        cached = store.get(prior["output"])
        if cached["raw_sha256"] != page["raw_sha256"] or cached["engine"] != identity:
            raise Hold("识别缓存与原图或本机识别器不一致。")
        return copy.deepcopy(cached["lines"]), "CACHE"
    if not allow_local_ocr:
        raise Hold("这张图片没有当前识别缓存。安装首次配置中的本地识别依赖后，勾选本地识别再启动。")
    if any(value is None for value in identity["packages"].values()):
        raise Hold("本地识别依赖未安装，见首次配置；没有调用模型。")
    directory = store.root / "recognition" / key
    directory.mkdir(parents=True, exist_ok=True)
    asset = {"asset_id": page["asset_id"], "path": "original" + Path(page["raw_path"]).suffix,
             "sha256": page["raw_sha256"], "width": page["width"], "height": page["height"], "reading_order": 0}
    image_path = directory / asset["path"]
    raw = Path(page["raw_path"]).read_bytes()
    if byte_hash(raw) != page["raw_sha256"]:
        raise Hold("原图已改变。")
    image_path.write_bytes(raw)
    source = {"schema_version": "b-source-trial/0.1", "artifact_id": "customer-source-" + key[:24],
              "book_id": book, "scope_id": "image-" + page["raw_sha256"], "assets": [asset]}
    source_path = directory / "source.json"
    source_path.write_bytes(encoded(source))
    store.begin("recognition", key)
    try:
        evidence, _ = recognize(source_path, use_ocr=True)
        lines = evidence["payload"]["pages"][0]["ocr_lines"]
        validate_lines(lines, page["width"], page["height"])
        store.finish("recognition", key, "COMPLETE", {"raw_sha256": page["raw_sha256"],
                     "engine": identity, "evidence": evidence, "lines": lines})
    except BaseException as exc:
        store.finish("recognition", key, "FAILED_NO_RETRY", {"type": type(exc).__name__, "message": str(exc)})
        raise
    return lines, "LOCAL_OCR"


def validate_lines(lines, width, height):
    from annotation.recognition.baseline import valid_bbox
    if not isinstance(lines, list) or not lines:
        raise Hold("该页没有可用文字，需补充材料或人工审校。")
    for line in lines:
        if (not isinstance(line, dict) or not isinstance(line.get("text"), str)
                or not line["text"].strip() or not valid_bbox(line.get("bbox", []), width, height)):
            raise Hold("识别行内容或坐标无效。")
        score = line.get("score", line.get("confidence", 0))
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
            raise Hold("识别行置信值无效。")


def text_lines(page):
    # Coordinates are explicitly a local text-preview canvas, not textbook
    # pixels. Native frame planning rejects this coordinate space.
    lines = []
    for number, text in enumerate(page["text"].splitlines()):
        if text.strip():
            lines.append({"text": text, "bbox": [20, 20 + number * 30, 1180, 45 + number * 30], "score": 1.0,
                          "original_line": number + 1})
    page.update(width=1200, height=max(100, 60 + len(page["text"].splitlines()) * 30),
                coordinate_space="TEXT_PREVIEW_ONLY")
    return lines
