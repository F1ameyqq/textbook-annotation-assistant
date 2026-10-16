"""Offline independent A01 geometry review. All expectations below are literal.

Run with -B. This process inserts the frozen snapshot/src at sys.path[0].
The snapshot is read only; all outputs go to the supplied review evidence dir.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import math
import platform
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser()
parser.add_argument("--snapshot", required=True)
parser.add_argument("--out", required=True)
args = parser.parse_args()
ROOT = Path(args.snapshot).resolve()
OUT = Path(args.out).resolve()
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))
import annotation.geometry as geometry
import annotation.contracts.models as contracts
import pydantic

assert Path(geometry.__file__).resolve() == ROOT / "src/annotation/geometry/__init__.py"
assert Path(contracts.__file__).resolve() == ROOT / "src/annotation/contracts/models.py"
G = geometry
results = []


def normalize(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, (tuple, list)):
        return [normalize(v) for v in value]
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    return value


def invoke(fn):
    try:
        return {"returned": normalize(fn())}
    except Exception as exc:
        return {"exception": type(exc).__name__, "code": getattr(exc, "code", None), "message": str(exc)}


def check(name, inputs, expected, fn, *, reject=False, type_error=False):
    actual = invoke(fn)
    if reject:
        passed = actual.get("exception") == ("TypeError" if type_error else "GeometryError")
    else:
        def close(a, b):
            if isinstance(b, (list, tuple)):
                return isinstance(a, (list, tuple)) and len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
            if isinstance(b, (int, float)):
                return isinstance(a, (int, float)) and math.isfinite(a) and abs(a - b) <= 1e-9
            return a == b
        passed = "returned" in actual and close(actual["returned"], expected)
    row = {"id": name, "input": normalize(inputs), "expected": normalize(expected), "actual": actual,
           "outcome": "PASS" if passed else "FAIL"}
    results.append(row)
    return row


def image(width, height, asset_id="original", digest="1"):
    return G.ImageBinding(asset_id=asset_id, width=width, height=height, sha256=digest * 64)


def box(binding, coordinates):
    return G.OriginalBox(image=binding, bbox=[float(v) for v in coordinates])


hand_cases = [
    dict(id="G01", image=[13, 9], crop=[2, 1, 11, 7], scale=[2, 3], padding=[1, 4, 3, 2], rotation=0,
         size=[22, 24], points=[[[4, 3], [5, 10]]], boxes=[[[3, 2, 7, 5], [3, 7, 11, 16]]]),
    dict(id="G02", image=[13, 9], crop=[2, 1, 11, 7], scale=[2, 3], padding=[1, 4, 3, 2], rotation=90,
         size=[24, 22], points=[[[4, 3], [14, 5]]], boxes=[[[3, 2, 7, 5], [8, 3, 17, 11]]]),
    dict(id="G03", image=[13, 9], crop=[2, 1, 11, 7], scale=[2, 3], padding=[1, 4, 3, 2], rotation=180,
         size=[22, 24], points=[[[4, 3], [17, 14]]], boxes=[[[3, 2, 7, 5], [11, 8, 19, 17]]]),
    dict(id="G04", image=[13, 9], crop=[2, 1, 11, 7], scale=[2, 3], padding=[1, 4, 3, 2], rotation=270,
         size=[24, 22], points=[[[4, 3], [10, 17]]], boxes=[[[3, 2, 7, 5], [7, 11, 16, 19]]]),
    dict(id="G05", image=[11, 7], crop=[3, 2, 9, 6], scale=[1, 1], padding=[2, 1, 4, 3], rotation=90,
         size=[8, 12], points=[[[3, 2], [7, 2]], [[3.5, 2.5], [6.5, 2.5]]],
         boxes=[[[3, 2, 4, 3], [6, 2, 7, 3]], [[3, 2, 9, 6], [3, 2, 7, 8]]]),
    dict(id="G06", image=[17, 11], crop=[3, 2, 15, 10], scale=[.5, 1.5], padding=[1, 2, 4, 3], rotation=270,
         size=[17, 11], points=[[[7, 4], [5, 8]]], boxes=[[[5, 3, 11, 7], [3.5, 6, 9.5, 9]]]),
    dict(id="G07", image=[15, 9], crop=[1, 2, 13, 8], scale=[2, .5], padding=[3, 1, 5, 4], rotation=90,
         size=[8, 32], points=[[[4, 4], [6, 9]]], boxes=[[[2, 3, 9, 7], [4.5, 5, 6.5, 19]]]),
    dict(id="G08", image=[16, 10], crop=[2, 1, 14, 9], scale=[1.5, 2.5], padding=[4, 3, 1, 2], rotation=270,
         size=[25, 23], points=[[[6, 3], [8, 13]]], boxes=[[[4, 2, 10, 6], [5.5, 7, 15.5, 16]]]),
]
for case in hand_cases:
    original = image(*case["image"])
    config = dict(crop=case["crop"], scale=case["scale"], padding=case["padding"], rotation_degrees=case["rotation"])
    transform = G.Transform(original, **config)
    processed = transform.processed_binding("processed", "2" * 64)
    check(case["id"] + ".size", case, case["size"], lambda: transform.output_size)
    for i, (before, after) in enumerate(case["points"]):
        check(case["id"] + ".point.forward." + str(i), dict(config=config, point=before), after,
              lambda p=before: transform.forward_point(p, original))
        check(case["id"] + ".point.inverse.literal." + str(i), dict(config=config, point=after), before,
              lambda p=after: transform.inverse_point(p, processed, processed))
    for i, (before, after) in enumerate(case["boxes"]):
        check(case["id"] + ".box.forward." + str(i), dict(config=config, bbox=before), after,
              lambda p=before: transform.forward_box(box(original, p), processed).bbox)
        check(case["id"] + ".box.inverse.literal." + str(i), dict(config=config, bbox=after), before,
              lambda p=after: transform.inverse_box(box(processed, p), processed).bbox)

original = image(13, 9)
invalid_transforms = [
    ("nan-scale", dict(scale=[math.nan, 1])), ("positive-inf-scale", dict(scale=[1, math.inf])),
    ("negative-inf-scale", dict(scale=[-math.inf, 1])), ("zero-scale", dict(scale=[0, 1])),
    ("negative-scale-reflection", dict(scale=[-1, 1])), ("bool-scale", dict(scale=[True, 1])),
    ("nan-crop", dict(crop=[0, 0, math.nan, 3])), ("inf-crop", dict(crop=[0, 0, 3, math.inf])),
    ("zero-area-crop", dict(crop=[1, 1, 1, 3])), ("negative-area-crop", dict(crop=[3, 1, 1, 3])),
    ("outside-crop", dict(crop=[0, 0, 14, 9])), ("tiny-outside-crop", dict(crop=[-1e-12, 0, 13, 9])),
    ("noninteger-size", dict(scale=[1.01, 1])), ("sub-tolerance-noninteger-size", dict(scale=[1 + 1e-12, 1])),
    ("negative-padding", dict(padding=[-1, 0, 0, 0])), ("fractional-padding", dict(padding=[.5, 0, 0, 0])),
    ("nan-padding", dict(padding=[math.nan, 0, 0, 0])), ("inf-padding", dict(padding=[0, math.inf, 0, 0])),
    ("bool-padding", dict(padding=[True, 0, 0, 0])), ("unsupported-45", dict(rotation_degrees=45)),
    ("float-rotation", dict(rotation_degrees=90.0)), ("bool-rotation", dict(rotation_degrees=True)),
    ("nan-rotation", dict(rotation_degrees=math.nan)), ("unknown-spec", dict(spec_version="unnamed")),
    ("overflow-scale", dict(scale=[1e308, 1e308])), ("underflow-scale", dict(scale=[1e-300, 1e-300])),
]
for label, config in invalid_transforms:
    check("reject.transform." + label, config, "GeometryError", lambda c=config: G.Transform(original, **c), reject=True)
for label, config in [("matrix", dict(matrix=[1, 0, 0, 0, 1, 0])), ("perspective", dict(perspective=True)),
                      ("reflection", dict(reflection=True)), ("nonlinear", dict(nonlinear=True))]:
    check("reject.transform." + label, config, "TypeError", lambda c=config: G.Transform(original, **c), reject=True, type_error=True)
check("reject.ambiguous-contract", {"offset_x": 1, "rotation": 90}, "GeometryError/AMBIGUOUS_SPEC",
      lambda: G.Transform.from_contract_crop_transform({"offset_x": 1, "rotation": 90}), reject=True)

transform = G.Transform(original, crop=[2, 1, 11, 7], padding=[1, 4, 3, 2])
processed = transform.processed_binding("processed", "2" * 64)
for label, point in [("nan", [math.nan, 1]), ("inf", [math.inf, 1]), ("negative-inf", [2, -math.inf]),
                     ("zero-shape", []), ("bool", [True, 1]), ("tiny-left-outside", [2 - 1e-12, 1]),
                     ("tiny-right-outside", [11 + 1e-12, 1]), ("below-crop", [2, 8])]:
    check("reject.forward-point." + label, point, "GeometryError", lambda p=point: transform.forward_point(p, original), reject=True)
for label, coords in [("nan", [2, 1, math.nan, 3]), ("inf", [2, 1, 4, math.inf]),
                      ("zero-area", [2, 1, 2, 3]), ("reverse", [4, 1, 2, 3]),
                      ("tiny-left-outside", [2 - 1e-12, 1, 4, 3]), ("tiny-right-outside", [2, 1, 11 + 1e-12, 3])]:
    check("reject.forward-box." + label, coords, "GeometryError",
          lambda p=coords: transform.forward_box({"image": original.model_dump(), "bbox": p}, processed), reject=True)
for label, point in [("left-padding", [0, 4]), ("tiny-left-padding", [1 - 1e-12, 4]),
                     ("right-padding", [11, 4]), ("top-padding", [1, 3]), ("bottom-padding", [1, 11]),
                     ("canvas-outside", [-1e-12, 4]), ("nan", [math.nan, 4]), ("inf", [1, math.inf])]:
    check("reject.inverse-point." + label, point, "GeometryError",
          lambda p=point: transform.inverse_point(p, processed, processed), reject=True)
for label, coords in [("padding", [0, 4, 2, 6]), ("zero-area", [1, 4, 1, 5]),
                      ("tiny-padding", [1 - 1e-12, 4, 2, 6])]:
    check("reject.inverse-box." + label, coords, "GeometryError",
          lambda p=coords: transform.inverse_box({"image": processed.model_dump(), "bbox": p}, processed), reject=True)
for field, value in [("asset_id", "other"), ("width", 14), ("height", 10), ("sha256", "3" * 64)]:
    data = original.model_dump(); data[field] = value
    bad_original = G.ImageBinding.model_validate(data)
    check("reject.forward-binding." + field, data, "GeometryError",
          lambda b=bad_original: transform.forward_point([2, 1], b), reject=True)
    data = processed.model_dump(); data[field] = value
    bad_processed = G.ImageBinding.model_validate(data)
    check("reject.inverse-binding." + field, data, "GeometryError",
          lambda b=bad_processed: transform.inverse_point([1, 4], b, processed), reject=True)
check("reject.forward-box-binding", processed.model_dump(), "GeometryError",
      lambda: transform.forward_box(box(processed, [1, 4, 2, 5]), processed), reject=True)
check("reject.inverse-box-binding", original.model_dump(), "GeometryError",
      lambda: transform.inverse_box(box(original, [2, 1, 3, 2]), processed), reject=True)

for label, matrix in [("singular", [1, 2, 0, 2, 4, 0]), ("zero-scale", [1, 0, 0, 0, 0, 0]),
                      ("nan", [math.nan, 0, 0, 0, 1, 0]), ("inf", [1, 0, 0, 0, math.inf, 0]),
                      ("underflow-determinant", [1e-300, 0, 0, 0, 1e-300, 0]),
                      ("overflow-determinant", [1e300, 0, 0, 0, 1e300, 0]),
                      ("unrepresentable-inverse", [5e-324, 0, 0, 0, 1, 0])]:
    check("reject.inverse-affine." + label, matrix, "GeometryError", lambda m=matrix: G.invert_affine(m), reject=True)
check("affine.finite-literal", [2, 0, 4, 0, 3, 9], [.5, 0, -2, 0, 1 / 3, -3],
      lambda: G.invert_affine([2, 0, 4, 0, 3, 9]))

# Minimal counterexamples. Expectations follow the stated staged equations, not
# the implementation matrix or a round trip. Constructor acceptance is recorded.
counterexamples = []
original = image(5, 1)
config = dict(crop=[2, 0, 5, 1], scale=[7 / 3, 1])
transform = G.Transform(original, **config)
processed = transform.processed_binding("processed", "2" * 64)
context = dict(image=original.model_dump(), config=config, output_size=transform.output_size,
               matrix=transform.matrix, expanded_endpoint=transform.matrix[0] * 5 + transform.matrix[2],
               staged_endpoint=(5 - 2) * (7 / 3))
counterexamples.append(check("F01.legal-forward-boundary", dict(context, point=[5, 0]), [7, 0],
                             lambda: transform.forward_point([5, 0], original)))
counterexamples.append(check("F01.legal-forward-box", dict(context, bbox=[2, 0, 5, 1]), [0, 0, 7, 1],
                             lambda: transform.forward_box(box(original, [2, 0, 5, 1]), processed).bbox))

original = image(3, 7)
config = dict(crop=[0, 1, 3, 7], scale=[1 / 3, 1], rotation_degrees=90)
transform = G.Transform(original, **config)
processed = transform.processed_binding("processed", "2" * 64)
inverse = G.invert_affine(transform.matrix)
context = dict(image=original.model_dump(), config=config, output_size=transform.output_size,
               matrix=transform.matrix, inverse_matrix=inverse, raw_inverse_y=inverse[3] * 6 + inverse[5])
check("F02.forward-confirmation", dict(context, point=[0, 1]), [6, 0], lambda: transform.forward_point([0, 1], original))
counterexamples.append(check("F02.legal-inverse-boundary", dict(context, point=[6, 0]), [0, 1],
                             lambda: transform.inverse_point([6, 0], processed, processed)))
counterexamples.append(check("F02.legal-inverse-box", dict(context, bbox=[0, 0, 6, 1]), [0, 1, 3, 7],
                             lambda: transform.inverse_box(box(processed, [0, 0, 6, 1]), processed).bbox))

original = image(4, 1)
config = dict(crop=[1, 0, 4, 1], scale=[2, 1], padding=[1, 0, 0, 0])
transform = G.Transform(original, **config)
processed = transform.processed_binding("processed", "2" * 64)
outside = math.nextafter(1.0, 0.0)
context = dict(image=original.model_dump(), config=config, output_size=transform.output_size,
               content_left=1, outside_lt_content_left=(outside < 1), outside_hex=outside.hex(),
               inverse_matrix=G.invert_affine(transform.matrix))
counterexamples.append(check("F03.padding-point-leak", dict(context, point=[outside, 0]), "GeometryError/BOUNDS",
                             lambda: transform.inverse_point([outside, 0], processed, processed), reject=True))
counterexamples.append(check("F03.padding-box-leak", dict(context, bbox=[outside, 0, 3, 1]), "GeometryError/BOUNDS",
                             lambda: transform.inverse_box(box(processed, [outside, 0, 3, 1]), processed).bbox, reject=True))

original = image(1, 1)
huge_padding = 2 ** 53 + 1
transform = G.Transform(original, padding=[huge_padding, 0, 0, 0])
row = {"id": "F04.integer-padding-changed", "input": {"padding": [huge_padding, 0, 0, 0]},
       "expected": "reject unrepresentable input or preserve the exact integer padding",
       "actual": {"accepted": True, "padding": normalize(transform.padding), "output_size": normalize(transform.output_size)},
       "outcome": "PASS" if transform.padding[0] == huge_padding else "FAIL"}
results.append(row); counterexamples.append(row)

# Reproduce the frozen author's geometry suite in this same pinned process.
spec = importlib.util.spec_from_file_location("frozen_a01_geometry_tests", ROOT / "tests/test_a01_geometry.py")
author_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(author_module)
author_output = io.StringIO()
author_result = unittest.TextTestRunner(stream=author_output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(author_module))
(OUT / "author-tests.log").write_text(author_output.getvalue(), encoding="utf-8")

environment = {"delivery_commit": "a8d5e96d128e10d341de935d4856682e50df79d9", "snapshot": str(ROOT),
               "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
               "pydantic": pydantic.__version__, "sys_path_0": sys.path[0],
               "geometry_file": geometry.__file__, "contracts_file": contracts.__file__,
               "geometry_sha256": hashlib.sha256(Path(geometry.__file__).read_bytes()).hexdigest(),
               "dont_write_bytecode": sys.dont_write_bytecode}
summary = {"environment": environment, "independent_assertions": len(results),
           "pass": sum(r["outcome"] == "PASS" for r in results), "fail": sum(r["outcome"] == "FAIL" for r in results),
           "hand_case_groups": len(hand_cases), "author_tests_run": author_result.testsRun,
           "author_tests_failures": len(author_result.failures), "author_tests_errors": len(author_result.errors),
           "conclusion": "REWORK", "counterexample_ids": [r["id"] for r in counterexamples]}
(OUT / "inputs-expected-actual.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "minimal-counterexamples.json").write_text(json.dumps(counterexamples, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
log = "\n".join("{} {} expected={} actual={}".format(r["outcome"], r["id"], json.dumps(r["expected"], ensure_ascii=False), json.dumps(r["actual"], ensure_ascii=False)) for r in results)
(OUT / "independent-tests.log").write_text(log + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
sys.exit(1 if summary["fail"] or not author_result.wasSuccessful() else 0)
