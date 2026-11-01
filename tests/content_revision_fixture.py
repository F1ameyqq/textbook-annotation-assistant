"""Generated draft sources and explicitly synthetic OCR; no business gold."""
import copy
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"tests")]
from annotation.recognition import offline, inline_stage
from annotation.recognition.baseline import digest, file_digest
from annotation.recognition.inline_ocr import collect_inline_observations
from annotation.recognition.inline_math import build_inline_math_layout
from annotation.recognition.inline_formula import collect_inline_formula
from test_b_inline_formula import FormulaWorker
from test_b_inline_math import raw_row
from test_b_inline_stage import make_inline_fixture, refresh_inline_package, write


def make_content_fixture(directory, *, with_images=False, scalar_text="0", formula_outputs=("AB=1",)):
    """G05/Check05 with choice/scalar/body/analysis, or proven synthetic images."""
    root = Path(directory); root.mkdir(parents=True, exist_ok=True)
    if with_images:
        d = make_inline_fixture(root, continuation=True)
        prepared = inline_stage.prepare_inline_stage(d["evidence"], d["graph"], d["package_path"], d["original"])
        application = inline_stage.apply_inline_stage(prepared)
        check = inline_stage.build_inline_quality(prepared, application, d["base_check"])
        return {**d, "graph": application["payload"]["graph"], "check": check, "inline_prepared": prepared,
                "inline_application": application, "base_graph": d["graph"]}
    book, scope, path = "synthetic-content-book", "two-pages", ["Synthetic content section"]
    assets, pages = [], []
    rawtexts = {"question": ["1.选择正确的答案。", "A.甲", "B.乙", "C.丙", "D.丁", "4.计算一个数。"],
                "answer": ["1.答案：A", "4.答案："+scalar_text, "9.解：AB=", "25", "解析：先确定边长", "继续验证", "10.答案：5"]}
    for order, aid in enumerate(("question", "answer")):
        image = Image.new("RGB", (240, 300), "white")
        draw = ImageDraw.Draw(image)
        lines = []
        for i, text in enumerate(rawtexts[aid]):
            y = 15+i*28
            draw.text((15, y), "SYNTH "+str(i), fill="black")
            lines.append({"line_id": aid+"/ocr/"+str(i), "text": text, "score": .9,
                          "bbox": [10, y, 220, y+18], "location": {"column": 0, "window_index": 0, "section_path": path}})
        original = root/(aid+".png"); image.save(original)
        asset = {"asset_id": aid, "path": original.name, "sha256": file_digest(original), "width": 240,
                 "height": 300, "reading_order": order, "reference_quality": "SYNTHETIC_TEST"}
        assets.append(asset)
        pages.append({"asset_id": aid, "source": asset, "page_role": aid, "layout": {"mode": "two_columns", "cut_x": 230},
                      "ocr_lines": lines, "answer_detail_lines": [], "unscoped_line_ids": []})
    source = {"schema_version": "b-source-trial/0.1", "artifact_id": "synthetic-content-source", "book_id": book, "scope_id": scope, "assets": assets}
    context = {"schema_version": "b-context-trial/0.1", "artifact_id": "synthetic-content-context", "book_id": book, "scope_id": scope,
               "pages": {a["asset_id"]: {"sha256": a["sha256"], "role": a["asset_id"], "windows": [{"column": 0, "y_range": [0, 300], "path": path}]} for a in assets}}
    e = offline.artifact("b-evidence-trial/0.3", "EvidenceBundleTrial", source,
        {"pages": pages, "context": context, "history_annotations_consumed": False, "quality_decision": "NOT_EVALUATED"}, [],
        {"module": "SYNTHETIC_TEST", "execution_kind": "SYNTHETIC_TEST"})
    review = {"schema_version": "b-review-trial/0.1", "artifact_id": "synthetic-content-review", "book_id": book, "scope_id": scope,
              "reference_quality": "SYNTHETIC_TEST", "question_census": {"question": {"sha256": assets[0]["sha256"], "printed_numbers": ["1", "4"]}},
              "answer_checks": [{"case_id": "synthetic-q4-scalar", "asset_sha256": {"question": assets[0]["sha256"], "answer": assets[1]["sha256"]},
                                 "section_path": path, "printed_number": "4", "expected_scalar": 13}]}
    original, ids = root/"answer.png", ["answer/ocr/2", "answer/ocr/3"]
    def ordinary(bgr, **flags): return [raw_row("AB=", bgr.shape[1], bgr.shape[0])], [.01, 0, .02]
    observed = collect_inline_observations(e, original, asset_id="answer", line_ids=ids, recognizer=ordinary)
    layout = build_inline_math_layout(e, observed, original, line_ids=ids)
    journal = root/"formula"
    formulas, report = collect_inline_formula(e, layout, original, journal, line_ids=ids, recognizer=FormulaWorker(outputs=formula_outputs))
    docs = {"evidence": e, "rows": ids, "ocr_observations": observed, "formula_observations": formulas, "formula_report": report}
    manifest = {"schema_version": inline_stage.PACKAGE_SCHEMA, "artifact_id": "synthetic-content-inline-package", "book_id": book,
        "scope_id": scope, "asset_id": "answer", "line_ids": ids, "policy": inline_stage.POLICY, "journal_dir": "formula", "members": {},
        "documents": {name: {"path": "inline-"+name+".json", "sha256": None, "artifact_ref": None} for name in docs}}
    data = {"manifest": manifest, "documents": docs, "package_path": root/"inline-package.json", "journal_dir": journal}
    refresh_inline_package(data)
    base = offline.assemble(e)
    base_check = offline.quality_check(e, base, review)
    prepared = inline_stage.prepare_inline_stage(e, base, data["package_path"], original)
    application = inline_stage.apply_inline_stage(prepared)
    check = inline_stage.build_inline_quality(prepared, application, base_check)
    for name, value in (("source", source), ("context", context), ("review", review), ("evidence", e)):
        write(root/(name+".json"), value)
    return {**data, "evidence": e, "graph": application["payload"]["graph"], "check": check, "review": review, "original": original,
            "base_graph": base, "inline_prepared": prepared, "inline_application": application, "line_ids": ids,
            "source_path": root/"source.json", "context_path": root/"context.json", "review_path": root/"review.json", "evidence_path": root/"evidence.json"}


def edit_target(graph, *, answer_id=None, role="answer", fragment_id=None, span=None):
    for answer in graph["payload"]["answers"]:
        if answer_id is not None and answer["answer_id"] != answer_id: continue
        for fragment in answer["fragments"]:
            if (fragment["role"] != role or fragment.get("structural_marker") or fragment.get("represented_by_image_region") is not None
                    or fragment.get("render_as_separate_region") is False or (fragment_id is not None and fragment["fragment_id"] != fragment_id)): continue
            lo, hi = span if span is not None else (0, len(fragment["text"]))
            return {"answer_id": answer["answer_id"], "fragment_id": fragment["fragment_id"], "role": role,
                    "fragment_span": [lo, hi], "expected_text": fragment["text"][lo:hi]}
    raise ValueError("no matching visible source fragment for synthetic test")
