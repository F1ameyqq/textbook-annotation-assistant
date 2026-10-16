"""A-internal a01-geometry-1; continuous pixel boundaries, no browser semantics."""
import math
from dataclasses import dataclass
from typing import Optional, Tuple

from annotation.contracts import OriginalBox
from annotation.contracts.models import ImageBinding

SPEC_VERSION = "a01-geometry-1"
TOLERANCE = 1e-9


class GeometryError(ValueError):
    def __init__(self, code, location, detail):
        self.code, self.location = code, location
        super().__init__("{}: [{}] {}".format(location, code, detail))


def _fail(code, location, detail):
    raise GeometryError(code, location, detail)


def _numbers(values, count, location):
    if not isinstance(values, (tuple, list)) or len(values) != count:
        _fail("SHAPE", location, "expected {} numbers".format(count))
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in values):
        _fail("NUMBER", location, "expected real numbers")
    try:
        result = tuple(float(v) for v in values)
    except (ValueError, OverflowError):
        _fail("NONFINITE", location, "numbers must be finite")
    if not all(math.isfinite(v) for v in result):
        _fail("NONFINITE", location, "numbers must be finite")
    return result


def _binding(value):
    try:
        data = value.model_dump() if isinstance(value, ImageBinding) else value
        return ImageBinding.model_validate(data)
    except ValueError as error:
        _fail("IMAGE_BINDING", "image", str(error))


def _same(actual, expected):
    if _binding(actual) != expected:
        _fail("IMAGE_BINDING", "image", "asset_id, dimensions or digest differs")


def invert_affine(matrix):
    """Invert six affine coefficients (a,b,c,d,e,f); reject singular/nonfinite values.

    This is a math helper, not a declaration of support for arbitrary transforms.
    x'=a*x+b*y+c; y'=d*x+e*y+f.
    """
    a, b, c, d, e, f = _numbers(matrix, 6, "matrix")
    determinant = a * e - b * d
    if not math.isfinite(determinant) or determinant == 0:
        _fail("NONINVERTIBLE", "matrix", "finite nonzero determinant required")
    inverse = (e / determinant, -b / determinant, (b*f-e*c) / determinant,
               -d / determinant, a / determinant, (d*c-a*f) / determinant)
    if not all(math.isfinite(v) for v in inverse):
        _fail("NONINVERTIBLE", "matrix", "inverse cannot be represented finitely")
    return inverse


def _apply(matrix, point):
    a, b, c, d, e, f = matrix
    x, y = point
    return _numbers((a*x+b*y+c, d*x+e*y+f), 2, "result")


def _point(point, domain, location):
    x, y = _numbers(point, 2, location)
    left, top, right, bottom = domain
    if not (left <= x <= right and top <= y <= bottom):
        _fail("BOUNDS", location, "point outside declared content domain")
    return x, y


def _box(box, binding, domain):
    try:
        value = OriginalBox.model_validate(box.model_dump() if isinstance(box, OriginalBox) else box)
    except ValueError as error:
        _fail("BOX", "bbox", str(error))
    _same(value.image, binding)
    x1, y1, x2, y2 = value.bbox
    return [_point(p, domain, "bbox") for p in ((x1,y1),(x2,y1),(x2,y2),(x1,y2))]


@dataclass(frozen=True)
class Transform:
    image: ImageBinding
    crop: Optional[Tuple[float, float, float, float]] = None
    scale: Tuple[float, float] = (1.0, 1.0)
    padding: Tuple[int, int, int, int] = (0, 0, 0, 0)
    rotation_degrees: int = 0
    spec_version: str = SPEC_VERSION

    def __post_init__(self):
        image = _binding(self.image)
        object.__setattr__(self, "image", image)
        if self.spec_version != SPEC_VERSION:
            _fail("SPEC_VERSION", "spec_version", "explicit a01-geometry-1 required")
        crop = _numbers(self.crop if self.crop is not None else (0,0,image.width,image.height), 4, "crop")
        x1, y1, x2, y2 = crop
        if not (0 <= x1 < x2 <= image.width and 0 <= y1 < y2 <= image.height):
            _fail("BOUNDS", "crop", "positive area within original required")
        scale = _numbers(self.scale, 2, "scale")
        if min(scale) <= 0:
            _fail("UNSUPPORTED_SCALE", "scale", "positive x/y scales required; no reflection")
        padding = _numbers(self.padding, 4, "padding")
        if any(p < 0 or not p.is_integer() for p in padding):
            _fail("PADDING", "padding", "nonnegative integer processing pixels required")
        degrees = self.rotation_degrees
        if isinstance(degrees, bool) or not isinstance(degrees, int) or degrees % 90:
            _fail("UNSUPPORTED_ROTATION", "rotation_degrees", "integer multiples of 90 required")
        object.__setattr__(self, "crop", crop)
        object.__setattr__(self, "scale", scale)
        object.__setattr__(self, "padding", tuple(int(p) for p in padding))
        object.__setattr__(self, "rotation_degrees", degrees % 360)
        # Validate dimensions and numerical invertibility before accepting the transform.
        self.output_size
        invert_affine(self.matrix)

    @classmethod
    def from_contract_crop_transform(cls, *args, **kwargs):
        _fail("AMBIGUOUS_SPEC", "crop_transform", "C01 fields do not name offset/rotation/order semantics; use explicit Transform")

    @property
    def padded_size(self):
        x1, y1, x2, y2 = self.crop
        sx, sy = self.scale
        sizes = _numbers(((x2-x1)*sx, (y2-y1)*sy), 2, "scaled_size")
        if any(v <= 0 or not v.is_integer() for v in sizes):
            _fail("DIMENSIONS", "scaled_size", "positive integer pixel dimensions required")
        left, top, right, bottom = self.padding
        width, height = int(sizes[0])+left+right, int(sizes[1])+top+bottom
        _numbers((width,height), 2, "padded_size")
        return width, height

    @property
    def output_size(self):
        width, height = self.padded_size
        return (height,width) if self.rotation_degrees in (90,270) else (width,height)

    @property
    def matrix(self):
        x1, y1, _, _ = self.crop
        sx, sy = self.scale
        left, top, _, _ = self.padding
        c, f = left-sx*x1, top-sy*y1
        width, height = self.padded_size
        if self.rotation_degrees == 0:
            matrix = (sx,0,c,0,sy,f)
        elif self.rotation_degrees == 90:
            matrix = (0,-sy,height-f,sx,0,c)
        elif self.rotation_degrees == 180:
            matrix = (-sx,0,width-c,0,-sy,height-f)
        else:
            matrix = (0,sy,f,-sx,0,width-c)
        return _numbers(matrix, 6, "matrix")

    def processed_binding(self, asset_id, sha256):
        width, height = self.output_size
        return _binding(dict(asset_id=asset_id, width=width, height=height, sha256=sha256))

    def _processed(self, binding):
        value = _binding(binding)
        if (value.width,value.height) != self.output_size:
            _fail("IMAGE_BINDING", "processed_image", "processed dimensions differ")
        return value

    def forward_point(self, point, image):
        _same(image, self.image)
        width,height = self.output_size
        return _point(_apply(self.matrix, _point(point, self.crop, "point")),(0,0,width,height),"processed_point")

    def inverse_point(self, point, processed_image, expected_processed_image):
        binding = self._processed(expected_processed_image)
        _same(processed_image, binding)
        point = _point(point, (0,0,binding.width,binding.height), "processed_point")
        return _point(_apply(invert_affine(self.matrix), point), self.crop, "original_point")

    def forward_box(self, box, processed_image):
        binding = self._processed(processed_image)
        corners = _box(box, self.image, self.crop)
        return self._envelope([self.forward_point(p,self.image) for p in corners], binding)

    def inverse_box(self, box, expected_processed_image):
        binding = self._processed(expected_processed_image)
        corners = _box(box, binding, (0,0,binding.width,binding.height))
        return self._envelope([self.inverse_point(p,binding,binding) for p in corners], self.image)

    @staticmethod
    def _envelope(corners, image):
        xs, ys = zip(*corners)
        return OriginalBox(image=image, bbox=[min(xs),min(ys),max(xs),max(ys)])


__all__ = ["Transform", "GeometryError", "ImageBinding", "OriginalBox", "invert_affine", "SPEC_VERSION"]
