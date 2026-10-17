"""Independent hand-calculated renderer examples, never the mapper's inverse."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image,ImageDraw
from annotation.geometry import GeometryError,Transform
from annotation.delivery.usense_readonly.coordinates import (
    CoordinateError,ViewerMapping,binding_from_file,check_reference_points,
)
from annotation.delivery.usense_readonly.pixel_reference import locate_patch


def fixture(dpr=1):
    image={'asset_id':'original14','width':100,'height':200,'sha256':'a'*64}
    o={'viewer_page':14,'source_index':13,'image':image,
       'canvas_size':[300,400],'css_rect':[10.25,-8.5,150.5,201.25],
       'draw_source':[0,0,100,200],'draw_destination':[50,20,200,300],
       'canvas_ctm':[1,0,0,1,7,-5],'viewport':[1440,1000],'scroll':[0,50],'dpr':dpr}
    return image,o


class CoordinateTests(unittest.TestCase):
    def test_independent_canvas_css_expected_and_inverse(self):
        image,o=fixture();m=ViewerMapping(image,14,13,o)
        self.assertIsInstance(m.original_domain,Transform)
        # Original (25,80) -> draw (100,140), then CTM +(7,-5).
        self.assertEqual(m.original_to_canvas((25,80),image,viewer_page=14,source_index=13),(107,135))
        css=(10.25+107*150.5/300,-8.5+135*201.25/400)
        self.assertEqual(m.original_to_css((25,80),image,viewer_page=14,source_index=13),css)
        self.assertEqual(m.css_to_original(css,image,viewer_page=14,source_index=13),(25,80))
        self.assertEqual(m.original_domain.padding,(0,0,0,0))

    def test_non_one_dpr_is_not_a_backing_css_ratio_assumption(self):
        image,o=fixture(2.5);m=ViewerMapping(image,14,13,o)
        for actual,expected in zip(m.canvas_to_css((300,400)),(160.75,192.75)):
            self.assertAlmostEqual(actual,expected)
        for actual,expected in zip(m.css_to_canvas((160.75,192.75)),(300,400)):
            self.assertAlmostEqual(actual,expected)

    def test_known_points_detect_mutually_cancelling_wrong_mapping(self):
        image,o=fixture();m=ViewerMapping(image,14,13,o)
        refs=[]
        for x,y in [(10,20),(50,100),(75,150)]:
            canvas=[2*x+57,1.5*y+15]
            refs.append({'original':[x,y],'measured_canvas':canvas,
                         'measured_css':[10.25+canvas[0]*150.5/300,-8.5+canvas[1]*201.25/400]})
        self.assertEqual(len(check_reference_points(m,refs)),3)
        for field,index,delta in [('canvas_ctm',4,20),('css_rect',0,20),('draw_destination',2,10)]:
            bad=copy.deepcopy(o);bad[field][index]+=delta;wrong=ViewerMapping(image,14,13,bad)
            p=(50,100);css=wrong.original_to_css(p,image,viewer_page=14,source_index=13)
            self.assertAlmostEqual(wrong.css_to_original(css,image,viewer_page=14,source_index=13)[0],50)
            with self.assertRaisesRegex(CoordinateError,'REFERENCE_MAPPING_MISMATCH'):
                check_reference_points(wrong,refs)

    def test_wrong_page_digest_dimension_and_asset_rejected(self):
        image,o=fixture();m=ViewerMapping(image,14,13,o)
        for key,value in [('asset_id','other'),('sha256','b'*64),('width',101),('height',201)]:
            bad=dict(image,**{key:value})
            with self.assertRaises(CoordinateError):
                m.original_to_canvas((25,80),bad,viewer_page=14,source_index=13)
        for page,index in [(15,13),(14,14),(173,172)]:
            with self.assertRaises(CoordinateError):
                m.original_to_canvas((25,80),image,viewer_page=page,source_index=index)
        with self.assertRaises(CoordinateError):
            ViewerMapping(image,15,13,o)

    def test_unknown_crop_rotation_nonfinite_and_zero_scale_rejected(self):
        image,o=fixture()
        for field,value in [('draw_source',[0,0,99,200]),('canvas_ctm',[1,.1,0,1,0,0]),
                             ('draw_destination',[0,0,0,20]),('css_rect',[0,0,float('nan'),2]),
                             ('dpr',0),('canvas_size',[300.5,400])]:
            bad=copy.deepcopy(o);bad[field]=value
            with self.assertRaises(CoordinateError):ViewerMapping(image,14,13,bad)

    def test_original_and_padding_inverse_domain_not_silently_clipped(self):
        image,o=fixture();m=ViewerMapping(image,14,13,o)
        with self.assertRaises(GeometryError):m.original_to_canvas((-1,0),image,viewer_page=14,source_index=13)
        with self.assertRaises(GeometryError):m.canvas_to_original((0,0),image,viewer_page=14,source_index=13)
        self.assertEqual(m.original_to_canvas((100,200),image,viewer_page=14,source_index=13),(257,315))

    def test_real_image_binding_reads_bytes_and_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'original.png';Image.new('RGB',(31,27),'white').save(p)
            binding=binding_from_file(p,'test-original')
            self.assertEqual((binding.width,binding.height),(31,27))
            self.assertEqual(binding.sha256,hashlib.sha256(p.read_bytes()).hexdigest())

    def test_pixel_localization_searches_unpredicted_position(self):
        original=Image.new('RGB',(120,100),'white');draw=ImageDraw.Draw(original)
        for i in range(12):
            draw.rectangle((20+i*3,20,21+i*3,70-i*2),fill=(i*8,40,90))
        draw.line((20,68,60,21),fill='black',width=2)
        target=Image.new('RGB',(220,180),'white');patch=original.crop((15,15,65,75))
        target.paste(patch,(131,83))
        found=locate_patch(original,target,(15,15,65,75),(1,1))
        self.assertEqual(found['center'],[156,113])
        self.assertEqual(found['mean_absolute_probe_error'],0)


if __name__=='__main__':unittest.main()
