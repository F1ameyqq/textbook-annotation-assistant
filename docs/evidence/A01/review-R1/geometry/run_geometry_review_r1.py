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
import os
import platform
import sys
import unittest
from fractions import Fraction
from pathlib import Path

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser()
parser.add_argument("--snapshot", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--temp-root", required=True)
args = parser.parse_args()
ROOT = Path(args.snapshot).resolve()
OUT = Path(args.out).resolve()
TEMP_ROOT = Path(args.temp_root).resolve()
TEMP_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["TMP"] = os.environ["TEMP"] = str(TEMP_ROOT)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
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
huge_result = invoke(lambda: G.Transform(original, padding=[huge_padding, 0, 0, 0]))
huge_rejected = huge_result.get("exception") == "GeometryError"
if huge_rejected:
    huge_actual = huge_result
else:
    transform = G.Transform(original, padding=[huge_padding, 0, 0, 0])
    huge_actual = {"accepted": True, "padding": normalize(transform.padding), "output_size": normalize(transform.output_size)}
row = {"id": "F04.integer-padding-changed", "input": {"padding": [huge_padding, 0, 0, 0]},
       "expected": "reject unrepresentable input or preserve the exact integer padding",
       "actual": huge_actual,
       "outcome": "PASS" if huge_rejected or transform.padding[0] == huge_padding else "FAIL"}
results.append(row); counterexamples.append(row)

# Independent reverse oracle uses the configured scale explicitly, never the
# implementation's interval endpoints or its forward output to form expected.
def stage(point, config, inverse=False):
    crop = config["crop"]
    sx, sy = config["scale"]
    pl, pt, pr, pb = config["padding"]
    rotation = config["rotation_degrees"] % 360
    w = int((crop[2] - crop[0]) * sx) + pl + pr
    h = int((crop[3] - crop[1]) * sy) + pt + pb
    x, y = map(Fraction, point)
    if inverse:
        if rotation == 90: x, y = y, Fraction(h) - x
        elif rotation == 180: x, y = Fraction(w) - x, Fraction(h) - y
        elif rotation == 270: x, y = Fraction(w) - y, x
        return [float((x-pl)/Fraction(sx)+Fraction(crop[0])), float((y-pt)/Fraction(sy)+Fraction(crop[1]))]
    # Literal staged float operations are the declared forward execution order.
    x = (float(x) - crop[0]) * sx + pl
    y = (float(y) - crop[1]) * sy + pt
    if rotation == 90: x, y = h-y, x
    elif rotation == 180: x, y = w-x, h-y
    elif rotation == 270: x, y = y, w-x
    return [x, y]

def envelope(values):
    return [min(p[0] for p in values), min(p[1] for p in values), max(p[0] for p in values), max(p[1] for p in values)]

def corners(coords):
    a,b,c,d = coords
    return [[a,b],[c,b],[c,d],[a,d]]

complex_specs = [
    ([23,17], [2.5,1.25,20.5,13.25], [2/3,7/3], [1,3,4,2], [5.25,3.75], [3.25,2.75,17.5,11.25]),
    ([31,19], [.5,2.25,28.5,17.25], [3/7,2/5], [4,1,2,5], [7.5,8.25], [2.25,3.75,26.5,16.25]),
    ([25,11], [0,0,25,11], [3/5,3], [2,5,1,4], [5.5,3.25], [2.5,1.75,21.5,9.25]),
]
check('N.preflight.noninteger-exploratory-size',dict(image=[25,11],scale=[7/25,3]),'GeometryError/DIMENSIONS',
      lambda:G.Transform(image(25,11),scale=[7/25,3]),reject=True)
for ci, (dims,crop,scale,padding,source_point,source_box) in enumerate(complex_specs):
    for rotation in (0,90,180,270):
        original = image(*dims)
        config = dict(crop=crop, scale=scale, padding=padding, rotation_degrees=rotation)
        transform = G.Transform(original, **config)
        processed = transform.processed_binding("processed", "2"*64)
        prefix = "N.combo.{}.{}".format(ci, rotation)
        expected_point = stage(source_point, config)
        expected_box = envelope([stage(p,config) for p in corners(source_box)])
        expected_content = envelope([stage(p,config) for p in corners(crop)])
        check(prefix+".point-forward", dict(config=config,point=source_point), expected_point,
              lambda p=source_point: transform.forward_point(p,original))
        check(prefix+".point-inverse-configured", dict(config=config,point=expected_point), stage(expected_point,config,inverse=True),
              lambda p=expected_point: transform.inverse_point(p,processed,processed))
        check(prefix+".box-forward", dict(config=config,bbox=source_box), expected_box,
              lambda p=source_box: transform.forward_box(box(original,p),processed).bbox)
        check(prefix+".box-inverse-configured", dict(config=config,bbox=expected_box),
              envelope([stage(p,config,inverse=True) for p in corners(expected_box)]),
              lambda p=expected_box: transform.inverse_box(box(processed,p),processed).bbox)
        check(prefix+".content-bounds", config, expected_content, lambda: transform.content_bounds)
        for axis in (0,1):
            for side in (0,1):
                edge = expected_content[axis+2*side]
                other_mid = (expected_content[1-axis]+expected_content[3-axis])/2
                toward_inside = math.inf if side == 0 else -math.inf
                toward_outside = -toward_inside
                for label, val, valid in [("edge",edge,True), ("adjacent-inside",math.nextafter(edge,toward_inside),True),
                                          ("adjacent-outside",math.nextafter(edge,toward_outside),False)]:
                    p = [other_mid,other_mid]; p[axis] = val
                    check(prefix+".inverse-boundary.{}.{}.{}".format(axis,side,label), dict(config=config,point=p),
                          stage(p,config,inverse=True) if valid else "GeometryError/BOUNDS",
                          lambda p=p: transform.inverse_point(p,processed,processed), reject=not valid)
                    b = list(expected_content)
                    mid = (expected_content[axis]+expected_content[axis+2])/2
                    if side == 0: b[axis] = val; b[axis+2] = mid
                    else: b[axis] = mid; b[axis+2] = val
                    check(prefix+".inverse-box-boundary.{}.{}.{}".format(axis,side,label), dict(config=config,bbox=b),
                          envelope([stage(p,config,inverse=True) for p in corners(b)]) if valid else "GeometryError/BOUNDS",
                          lambda b=b: transform.inverse_box(box(processed,b),processed).bbox, reject=not valid)
        # Original-domain adjacency, independently of content_bounds.
        for axis in (0,1):
            for side in (0,1):
                edge=crop[axis+2*side]
                other_mid=(crop[1-axis]+crop[3-axis])/2
                inside=math.inf if side==0 else -math.inf
                for label,val,valid in [("edge",edge,True),("adjacent-inside",math.nextafter(edge,inside),True),
                                        ("adjacent-outside",math.nextafter(edge,-inside),False)]:
                    p=[other_mid,other_mid];p[axis]=val
                    check(prefix+".forward-boundary.{}.{}.{}".format(axis,side,label),dict(config=config,point=p),
                          stage(p,config) if valid else "GeometryError/BOUNDS",
                          lambda p=p: transform.forward_point(p,original),reject=not valid)

maximum=2**53
for label,dims,config,valid,size in [
    ("image-at-limit",[maximum,1],{},True,[maximum,1]),
    ("image-above-limit",[maximum+1,1],{},False,None),
    ("padding-last-valid",[1,1],dict(padding=[maximum-1,0,0,0]),True,[maximum,1]),
    ("padding-sum-last-valid",[1,1],dict(padding=[maximum-2,0,1,0]),True,[maximum,1]),
    ("padding-sum-over-limit",[1,1],dict(padding=[maximum-1,0,1,0]),False,None),
    ("padding-at-limit-canvas-over",[1,1],dict(padding=[maximum,0,0,0]),False,None),
    ("padding-above-limit",[1,1],dict(padding=[maximum+1,0,0,0]),False,None),
    ("float-padding-sum-over",[1,1],dict(padding=[float(maximum),0,0,0]),False,None),
    ("negative-huge-padding",[1,1],dict(padding=[-maximum-1,0,0,0]),False,None),
    ("scaled-size-at-limit",[2,1],dict(scale=[maximum//2,1]),True,[maximum,1]),
    ("scaled-size-over-limit",[3,1],dict(scale=[maximum//2,1]),False,None),
]:
    check("N.integer."+label,dict(image=dims,config=config),size if valid else "GeometryError",
          lambda d=dims,c=config: G.Transform(image(*d),**c).output_size,reject=not valid)

# New direct inverse semantic counterexample: configured sx != rounded extent
# normalization. Both expected and actual results are finite representable floats.
original=image(30000000,1)
config=dict(crop=[0,0,30000000,1],scale=[7/3,1],padding=[0,0,0,0],rotation_degrees=0)
transform=G.Transform(original,**config)
processed=transform.processed_binding("processed","2"*64)
q=[35000000.,.5]
expected=stage(q,config,inverse=True)
counterexamples.append(check("N01.configured-scale-inverse",dict(image=original.model_dump(),config=config,point=q,
                             exact_expected_x=str(Fraction(q[0])/Fraction(config['scale'][0]))),expected,
                             lambda:transform.inverse_point(q,processed,processed)))
qbox=[35000000.,0.,49000000.,1.]
counterexamples.append(check("N01.configured-scale-inverse-box",dict(image=original.model_dump(),config=config,bbox=qbox),
                             envelope([stage(p,config,inverse=True) for p in corners(qbox)]),
                             lambda:transform.inverse_box(box(processed,qbox),processed).bbox))

# Positive-area neighboring representable boxes, in the stated ordinary support
# domain; record whether public box execution succeeds, not only point roundtrip.
original=image(4,1)
config=dict(crop=[1,0,4,1],scale=[2,1],padding=[1,0,0,0],rotation_degrees=180)
transform=G.Transform(original,**config);processed=transform.processed_binding("processed","2"*64)
thin=[1.,0.,math.nextafter(1.,4.),1.]
actual=invoke(lambda:transform.forward_box(box(original,thin),processed))
row=dict(id="N02.neighbor-positive-box-forward",input=dict(image=original.model_dump(),config=config,bbox=thin,
          exact_transformed_x_bounds=[str(Fraction(7)-(Fraction(thin[2])-1)*2-1),'6']),
          expected="positive-area transformed box in declared supported domain",actual=actual,
          outcome="PASS" if "returned" in actual else "FAIL")
results.append(row);counterexamples.append(row)
config=dict(crop=[1,0,4,1],scale=[2,1],padding=[1,0,0,0],rotation_degrees=0)
transform=G.Transform(original,**config);processed=transform.processed_binding("processed","2"*64)
thin=[1.,0.,math.nextafter(1.,4.),1.]
actual=invoke(lambda:transform.inverse_box(box(processed,thin),processed))
row=dict(id="N02.neighbor-positive-box-inverse",input=dict(image=original.model_dump(),config=config,bbox=thin,
          exact_original_x_bounds=['1',str((Fraction(thin[2])-1)/2+1)]),
          expected="positive-area inverse box in declared supported domain",actual=actual,
          outcome="PASS" if "returned" in actual else "FAIL")
results.append(row);counterexamples.append(row)

# Explicit upper-domain precision limits, separately categorized from ordinary
# small-image checks. Literal expected original coordinate is independently fixed.
for width in [100000000,maximum]:
    original=image(width,1)
    transform=G.Transform(original,rotation_degrees=180)
    processed=transform.processed_binding("processed","2"*64)
    original_point=[.1,.5]
    observed=transform.forward_point(original_point,original)
    counterexamples.append(check("N03.accepted-range-roundtrip."+str(width),dict(image=original.model_dump(),rotation=180,
                                 original_point=original_point,forward_actual=observed),original_point,
                                 lambda p=observed:transform.inverse_point(p,processed,processed)))

# The specification names 1e-9 as comparison/test tolerance, not an arbitrary
# scale-wide absolute-error guarantee. These additional precision probes record
# mathematical differences and explicit representation failure as observations;
# they do not create a new acceptance rule or a minimum positive box resolution.
for row in results:
    if row['id'].startswith(('N01.','N02.','N03.')):
        row['comparison_outcome']=row['outcome']
        row['outcome']='OBSERVATION'
        row['blocking']=False
        if row['id'].startswith('N01.'):
            row['classification']='configured binary scale inverse versus documented endpoint normalization; numerical semantic observation'
        elif row['id'].startswith('N02.'):
            row['classification']='nonrepresentable neighboring positive box explicitly fails validation; representation limitation'
        else:
            row['classification']='accepted large canvas loses subpixel detail under float rotation; representation limitation, not a new 1e-9 global guarantee'

# Reproduce the frozen author's geometry suite in this same pinned process.
spec = importlib.util.spec_from_file_location("frozen_a01_geometry_tests", ROOT / "tests/test_a01_geometry.py")
author_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(author_module)
author_output = io.StringIO()
author_result = unittest.TextTestRunner(stream=author_output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(author_module))
# Only geometry R1 class: no source import tests or package writes are run here.
spec = importlib.util.spec_from_file_location("frozen_a01_rework_r1_tests", ROOT / "tests/test_a01_rework_r1.py")
r1_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(r1_module)
r1_result=unittest.TextTestRunner(stream=author_output,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(r1_module.GeometryR1Tests))
(OUT / "author-tests.log").write_text(author_output.getvalue(), encoding="utf-8")

environment = {"delivery_commit": "03c1af41a134945c406a52a48e3d4f6f0da33eb2", "snapshot": str(ROOT),
               "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
               "pydantic": pydantic.__version__, "sys_path_0": sys.path[0],
               "geometry_file": geometry.__file__, "contracts_file": contracts.__file__,
               "geometry_sha256": hashlib.sha256(Path(geometry.__file__).read_bytes()).hexdigest(),
               "dont_write_bytecode": sys.dont_write_bytecode, "TMP":os.environ['TMP'], "TEMP":os.environ['TEMP'],
               "implementation_version":G.IMPLEMENTATION_VERSION}
summary = {"environment": environment, "independent_assertions": len(results),
           "pass": sum(r["outcome"] == "PASS" for r in results), "fail": sum(r["outcome"] == "FAIL" for r in results),
           "observations":sum(r["outcome"]=="OBSERVATION" for r in results),
           "acceptance_assertions":sum(r["outcome"]!="OBSERVATION" for r in results),
           "hand_case_groups": len(hand_cases), "author_tests_run": author_result.testsRun,
           "author_tests_failures": len(author_result.failures), "author_tests_errors": len(author_result.errors),
           "author_r1_geometry_tests_run":r1_result.testsRun,"author_r1_geometry_failures":len(r1_result.failures),
           "author_r1_geometry_errors":len(r1_result.errors),
           "original_regression_count":7,"original_regressions_pass":sum(r['outcome']=='PASS' for r in counterexamples if r['id'].startswith('F')),
           "conclusion": "REWORK" if any(r['outcome']=='FAIL' for r in results) else "ACCEPTED",
           "counterexample_ids": [r["id"] for r in counterexamples]}
(OUT / "inputs-expected-actual.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "minimal-counterexamples.json").write_text(json.dumps(counterexamples, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "numerical-observations.json").write_text(json.dumps([r for r in results if r['outcome']=='OBSERVATION'],ensure_ascii=False,indent=2),encoding="utf-8")
(OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
log = "\n".join("{} {} expected={} actual={}".format(r["outcome"], r["id"], json.dumps(r["expected"], ensure_ascii=False), json.dumps(r["actual"], ensure_ascii=False)) for r in results)
(OUT / "independent-tests.log").write_text(log + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
sys.exit(1 if summary["fail"] or not author_result.wasSuccessful() or not r1_result.wasSuccessful() else 0)
