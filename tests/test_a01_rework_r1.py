"""R01-R04 literal formal regressions and adjacent valid/invalid inputs."""
import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path

from annotation import geometry
from annotation.contracts import load_bundle, seal_artifact
from annotation.source.static import StaticSourceError, import_book, load_static_bundle

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("a01_r1_cases",ROOT/"examples/a01/R1/cases.py")
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)


def image(width,height):
    return geometry.ImageBinding(asset_id="original",width=width,height=height,sha256="1"*64)


class GeometryR1Tests(unittest.TestCase):
    def test_seven_formal_geometry_regressions(self):
        rows = cases.geometry_cases(geometry)
        self.assertEqual(len(rows),7)
        for row in rows:
            with self.subTest(case=row["id"]):
                self.assertTrue(row["matches_expectation"],row)

    def test_rotated_domains_and_nearest_inside_outside_points_and_boxes(self):
        original = image(5,2)
        # Literal content bounds, derived by hand from a padded 11x8 canvas.
        for rotation,bounds in ((0,(1,2,8,4)),(90,(4,1,6,8)),(180,(3,4,10,6)),(270,(2,3,4,10))):
            transform = geometry.Transform(original,crop=(2,0,5,2),scale=(7/3,1),padding=(1,2,3,4),rotation_degrees=rotation)
            processed = transform.processed_binding("processed","2"*64)
            self.assertEqual(transform.content_bounds,bounds)
            full = geometry.OriginalBox(image=original,bbox=[2.,0.,5.,2.])
            self.assertEqual(transform.forward_box(full,processed).bbox,list(bounds))
            output = geometry.OriginalBox(image=processed,bbox=[float(v) for v in bounds])
            self.assertEqual(transform.inverse_box(output,processed).bbox,full.bbox)
            left,top,right,bottom = bounds
            for axis in (0,1):
                low,high = (left,right) if axis == 0 else (top,bottom)
                for edge,toward_inside,toward_outside in ((low,math.inf,-math.inf),(high,-math.inf,math.inf)):
                    for value,valid in ((edge,True),(math.nextafter(edge,toward_inside),True),
                                        (math.nextafter(edge,toward_outside),False)):
                        point = [(left+right)/2,(top+bottom)/2]
                        point[axis] = value
                        with self.subTest(rotation=rotation,axis=axis,edge=edge,value=value):
                            if valid:
                                result = transform.inverse_point(point,processed,processed)
                                self.assertTrue(2 <= result[0] <= 5 and 0 <= result[1] <= 2)
                            else:
                                with self.assertRaisesRegex(geometry.GeometryError,"BOUNDS"):
                                    transform.inverse_point(point,processed,processed)
                                box = list(bounds)
                                box[axis if edge == low else axis+2] = value
                                with self.assertRaisesRegex(geometry.GeometryError,"BOUNDS"):
                                    transform.inverse_box(geometry.OriginalBox(image=processed,bbox=[float(v) for v in box]),processed)

    def test_reciprocal_scale_inverse_neighbors_all_quarter_turns(self):
        original = image(3,7)
        for rotation,bounds in ((0,(0,0,1,6)),(90,(0,0,6,1)),(180,(0,0,1,6)),(270,(0,0,6,1))):
            transform = geometry.Transform(original,crop=(0,1,3,7),scale=(1/3,1),rotation_degrees=rotation)
            processed = transform.processed_binding("processed","2"*64)
            for point in ((0,0),(bounds[2],0),(0,bounds[3]),(bounds[2],bounds[3]),
                          (math.nextafter(float(bounds[2]),0.),math.nextafter(float(bounds[3]),0.))):
                with self.subTest(rotation=rotation,point=point):
                    result = transform.inverse_point(point,processed,processed)
                    self.assertTrue(0 <= result[0] <= 3 and 1 <= result[1] <= 7)
            for point in ((math.nextafter(0.,-math.inf),0),(0,math.nextafter(0.,-math.inf)),
                          (math.nextafter(float(bounds[2]),math.inf),0),(0,math.nextafter(float(bounds[3]),math.inf))):
                with self.subTest(rotation=rotation,invalid=point),self.assertRaisesRegex(geometry.GeometryError,"BOUNDS"):
                    transform.inverse_point(point,processed,processed)

    def test_forward_crop_neighbors_checked_before_arithmetic(self):
        original = image(5,1)
        transform = geometry.Transform(original,crop=(2,0,5,1),scale=(7/3,1))
        for x in (2.,5.,math.nextafter(2.,5.),math.nextafter(5.,2.)):
            with self.subTest(x=x):
                point = transform.forward_point((x,0),original)
                self.assertTrue(0 <= point[0] <= 7)
        for x in (math.nextafter(2.,0.),math.nextafter(5.,math.inf)):
            with self.subTest(x=x),self.assertRaisesRegex(geometry.GeometryError,"BOUNDS"):
                transform.forward_point((x,0),original)

    def test_exact_integer_limit_and_combined_canvas_limit(self):
        original = image(1,1)
        maximum = 2**53
        accepted = geometry.Transform(original,padding=(maximum-1,0,0,0))
        self.assertEqual(accepted.padding[0],maximum-1)
        self.assertEqual(accepted.output_size,(maximum,1))
        for padding in (maximum,maximum+1,maximum+2):
            with self.subTest(padding=padding),self.assertRaisesRegex(geometry.GeometryError,"REPRESENTATION"):
                geometry.Transform(original,padding=(padding,0,0,0))
        for crop in ((0,0,maximum+1,1),(0,0,2**54,1)):
            with self.subTest(crop=crop),self.assertRaisesRegex(geometry.GeometryError,"REPRESENTATION"):
                geometry.Transform(original,crop=crop)
        with self.assertRaisesRegex(geometry.GeometryError,"REPRESENTATION"):
            geometry.Transform(image(maximum+1,1))

    def test_fractional_crop_nearest_interior_is_not_rejected_by_inverse_rounding(self):
        original = image(100,100)
        for crop,scale,rotation,point in (
            ((29.415655395341002,27.037172500510106,63.981123665426615,61.49427019984308),
             (2.690546509404186,1.712274217487044),270,(60.99999999999999,49.5)),
            ((22.918214395986034,16.637557732304785,87.35213265164738,74.42079758565743),
             (0.4811130665218586,0.7095483068109955),0,(31.999999999999996,22.5)),
        ):
            with self.subTest(crop=crop):
                transform = geometry.Transform(original,crop=crop,scale=scale,padding=(1,2,3,4),rotation_degrees=rotation)
                processed = transform.processed_binding("processed","2"*64)
                result = transform.inverse_point(point,processed,processed)
                self.assertTrue(crop[0] <= result[0] <= crop[2] and crop[1] <= result[1] <= crop[3])
                bounds = transform.content_bounds
                for axis in (0,1):
                    outside = list(point)
                    outside[axis] = math.nextafter(float(bounds[axis]),-math.inf)
                    with self.assertRaisesRegex(geometry.GeometryError,"BOUNDS"):
                        transform.inverse_point(outside,processed,processed)


class SourceR1Tests(unittest.TestCase):
    def test_nine_resealed_formal_source_regressions(self):
        expected = {"S12":"SOURCE_ORIGINS","S13":"SOURCE_MANIFEST","S14":"MAPPING_EVIDENCE",
                    "S15":"MISSING_SOURCES","S16":"INPUT_CHANGED","S17":"HISTORY_BYTES",
                    "S18":"HISTORY_QUALITY","S19":"DENOMINATOR_UNKNOWN","S20":"REFERENCE_RECORDS"}
        with tempfile.TemporaryDirectory(prefix="a01-R1-tests-") as folder:
            for case in cases.SOURCE_IDS:
                with self.subTest(case=case):
                    path = cases.mutated_source(ROOT/"examples/a01/bundles/46006966",Path(folder)/case,case,seal_artifact)
                    load_bundle(path,verify_assets=True)
                    with self.assertRaises(StaticSourceError) as error:
                        load_static_bundle(path,expected_book_id="46006966")
                    self.assertEqual(error.exception.code,expected[case])
                    self.assertTrue(error.exception.location)

    def test_legacy_and_new_r1_imports_both_books_remain_valid(self):
        with tempfile.TemporaryDirectory(prefix="a01-R1-books-") as folder:
            for book in ("46006966","46007447"):
                with self.subTest(book=book):
                    original = ROOT/"examples/a01/bundles"/book/"exchange.json"
                    legacy = load_static_bundle(original,expected_book_id=book)
                    self.assertEqual(legacy.artifacts[0].producer.implementation_version,"a01-static-1")
                    path = import_book(ROOT,book,Path(folder)/book)
                    current = load_static_bundle(path,expected_book_id=book)
                    self.assertEqual(current.artifacts[0].producer.implementation_version,"a01-static-1-r1")
                    self.assertEqual(current.artifacts[0].payload.assets,legacy.artifacts[0].payload.assets)
                    self.assertEqual(current.artifacts[0].payload.scope_manifest,legacy.artifacts[0].payload.scope_manifest)
                    self.assertFalse(json.loads((path.parent/"limitations.json").read_text(encoding="utf-8"))["coverage_eligible"])


if __name__ == "__main__":
    unittest.main()
