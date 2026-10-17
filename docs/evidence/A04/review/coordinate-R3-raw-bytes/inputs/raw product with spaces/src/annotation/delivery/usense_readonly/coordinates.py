"""Usense canvas/CSS adaptation around the accepted A01 original pixel domain.

Canvas draw destinations, CTM and CSS rectangles are fractional platform state.
They are never misrepresented as integer A01 processing padding or raster sizes.
"""
from dataclasses import dataclass
import copy
import hashlib
import math
from pathlib import Path

from annotation.geometry import ImageBinding, Transform, GeometryError, SPEC_VERSION, IMPLEMENTATION_VERSION

DEPENDENCY_COMMIT = "c6bebdf43eb93f7a6ae21e96ec07ed155686777d"


class CoordinateError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _numbers(values, length):
    if (not isinstance(values, (list, tuple)) or len(values) != length
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
        raise CoordinateError("INVALID_VIEWER_STATE")
    return tuple(float(v) for v in values)


def binding_from_file(path, asset_id):
    from PIL import Image
    path = Path(path)
    with Image.open(path) as image:
        image.load()
        width, height = image.size
    return ImageBinding(asset_id=asset_id, width=width, height=height,
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest())


@dataclass(frozen=True)
class ViewerMapping:
    image: ImageBinding
    viewer_page: int
    source_index: int
    observation: dict

    def __post_init__(self):
        if (type(self.viewer_page) is not int or self.viewer_page <= 0
                or type(self.source_index) is not int or self.source_index < 0):
            raise CoordinateError("INVALID_VIEWER_STATE")
        object.__setattr__(self,"observation",copy.deepcopy(self.observation))
        image = ImageBinding.model_validate(self.image)
        object.__setattr__(self, "image", image)
        # The viewer draws the original unchanged. The correct A01 image-domain
        # transform is identity; fractional presentation is separate below.
        transform = Transform(image=image)
        object.__setattr__(self, "original_domain", transform)
        o = self.observation
        if (o.get("viewer_page") != self.viewer_page or o.get("source_index") != self.source_index
                or o.get("image") != image.model_dump(mode="json")):
            raise CoordinateError("IMAGE_BINDING_MISMATCH")
        cw, ch = _numbers(o.get("canvas_size"), 2)
        if cw <= 0 or ch <= 0 or not cw.is_integer() or not ch.is_integer():
            raise CoordinateError("INVALID_VIEWER_STATE")
        x, y, w, h = _numbers(o.get("css_rect"), 4)
        if min(w, h) <= 0:
            raise CoordinateError("INVALID_VIEWER_STATE")
        sx, sy, sw, sh = _numbers(o.get("draw_source"), 4)
        if (sx, sy, sw, sh) != (0, 0, image.width, image.height):
            raise CoordinateError("UNSUPPORTED_DRAW_SOURCE")
        dx, dy, dw, dh = _numbers(o.get("draw_destination"), 4)
        a, b, c, d, e, f = _numbers(o.get("canvas_ctm"), 6)
        if b != 0 or c != 0 or min(a, d, dw, dh) <= 0:
            raise CoordinateError("UNSUPPORTED_CANVAS_TRANSFORM")
        if min(_numbers(o.get("viewport"), 2)) <= 0:
            raise CoordinateError("INVALID_VIEWER_STATE")
        _numbers(o.get("scroll"), 2)
        dpr = _numbers([o.get("dpr")], 1)[0]
        if dpr <= 0:
            raise CoordinateError("INVALID_VIEWER_STATE")
        object.__setattr__(self, "_scale", (a*dw/image.width, d*dh/image.height))
        object.__setattr__(self, "_offset", (a*dx+e, d*dy+f))
        object.__setattr__(self, "_css", (x, y, w/cw, h/ch))

    def _same_page(self, image, viewer_page, source_index):
        if (ImageBinding.model_validate(image) != self.image
                or viewer_page != self.viewer_page or source_index != self.source_index):
            raise CoordinateError("IMAGE_BINDING_MISMATCH")

    def original_to_canvas(self, point, image, *, viewer_page, source_index):
        self._same_page(image, viewer_page, source_index)
        x, y = self.original_domain.forward_point(point, image)
        sx, sy = self._scale; ox, oy = self._offset
        return (x*sx+ox, y*sy+oy)

    def canvas_to_original(self, point, image, *, viewer_page, source_index):
        self._same_page(image, viewer_page, source_index)
        x, y = _numbers(point, 2)
        sx, sy = self._scale; ox, oy = self._offset
        # A01 enforces the strict original image domain, without clipping.
        return self.original_domain.inverse_point(((x-ox)/sx, (y-oy)/sy), image, image)

    def canvas_to_css(self, point):
        x, y = _numbers(point, 2); ox, oy, sx, sy = self._css
        return (ox+x*sx, oy+y*sy)

    def css_to_canvas(self, point):
        x, y = _numbers(point, 2); ox, oy, sx, sy = self._css
        return ((x-ox)/sx, (y-oy)/sy)

    def original_to_css(self, point, image, *, viewer_page, source_index):
        return self.canvas_to_css(self.original_to_canvas(point, image,
                   viewer_page=viewer_page, source_index=source_index))

    def css_to_original(self, point, image, *, viewer_page, source_index):
        return self.canvas_to_original(self.css_to_canvas(point), image,
                   viewer_page=viewer_page, source_index=source_index)

    def describe(self):
        return {"dependency_commit":DEPENDENCY_COMMIT,"spec_version":SPEC_VERSION,
                "implementation_version":IMPLEMENTATION_VERSION,
                "a01_original_transform":{"crop":list(self.original_domain.crop),"scale":[1,1],
                                          "padding":[0,0,0,0],"rotation_degrees":0},
                "canvas_scale":list(self._scale),"canvas_offset":list(self._offset),
                "css_origin_and_ratio":list(self._css),
                "dpr_note":"Observed separately; backing/CSS ratio is measured, never inferred from DPR."}


def check_reference_points(mapping, references, *, canvas_tolerance=2.5, original_tolerance=8):
    """Compare independently located pixels, not forward/inverse self-consistency."""
    if len(references) < 3:
        raise CoordinateError("REFERENCE_POINTS_MISSING")
    result = []
    for ref in references:
        original = _numbers(ref["original"], 2)
        measured = _numbers(ref["measured_canvas"], 2)
        expected = mapping.original_to_canvas(original, mapping.image,
                   viewer_page=mapping.viewer_page, source_index=mapping.source_index)
        measured_css = _numbers(ref["measured_css"], 2)
        predicted_css = mapping.original_to_css(original, mapping.image,
                   viewer_page=mapping.viewer_page, source_index=mapping.source_index)
        try:
            recovered = mapping.css_to_original(measured_css, mapping.image,
                       viewer_page=mapping.viewer_page, source_index=mapping.source_index)
        except GeometryError:
            raise CoordinateError("REFERENCE_MAPPING_MISMATCH") from None
        forward_error = math.dist(expected, measured)
        inverse_error = math.dist(original, recovered)
        css_error = math.dist(predicted_css, measured_css)
        if forward_error > canvas_tolerance or css_error > canvas_tolerance or inverse_error > original_tolerance:
            raise CoordinateError("REFERENCE_MAPPING_MISMATCH")
        result.append({"original":list(original),"measured_canvas":list(measured),
                       "predicted_canvas":list(expected),"measured_css":list(measured_css),
                       "predicted_css":list(predicted_css),"css_error":css_error,
                       "inverse_original":list(recovered),"canvas_error":forward_error,
                       "original_error":inverse_error})
    return result
