"""Formula syntax and local observation contracts; no model or network needed."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'tests/fixtures/book46007447'
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from annotation.recognition.baseline import digest
from annotation.recognition.formula_backend import CONFIG,collect_formula_observations,plan_formula_units
from annotation.recognition.formula_candidates import build_formula_candidates
from annotation.recognition.formula_syntax import fraction_count,parse_formula_latex
from replay_math_b import replay


class FormulaSyntaxRegression(unittest.TestCase):
    def test_actual_fraction_expression_keeps_power_and_denominator_scope(self):
        raw=r'\frac{a^{4}+2a^{2}+1}{4}'
        p=parse_formula_latex(raw)
        self.assertTrue(p['supported'],p['errors'])
        ast=p['normalized_ast']
        self.assertEqual(ast['type'],'fraction')
        self.assertEqual(ast['denominator'],{'type':'number','value':'4'})
        self.assertEqual(ast['numerator']['items'][0]['exponent'],{'type':'number','value':'4'})
        self.assertEqual(ast['numerator']['items'][3]['exponent'],{'type':'number','value':'2'})
        for token in p['tokens']:
            self.assertEqual(raw[token['start']:token['end']],token['text'])

    def test_presentation_and_redundant_braces_keep_same_syntax_scopes(self):
        a=parse_formula_latex(r'\frac{a^{2}+1}{2}')
        b=parse_formula_latex(r'{\displaystyle\dfrac { a^2 + 1 } {2}}')
        self.assertTrue(b['supported'],b['errors'])
        self.assertEqual(a['normalized_ast'],b['normalized_ast'])
        self.assertTrue(any(t['kind']=='presentation' for t in b['tokens']))

    def test_unknown_command_and_trailing_content_never_disappear(self):
        for raw in [r'\frac{a+1}{2}\input{secret}',r'\sqrt{x}',r'\frac{a+1}{2}@',r'a^{2',r'a^23']:
            with self.subTest(raw=raw):
                p=parse_formula_latex(raw)
                self.assertFalse(p['supported'])
                self.assertEqual(p['raw_latex'],raw)
                self.assertIsNone(p['ast'])
                self.assertTrue(p['errors'])
                self.assertIsNotNone(p['unparsed_tail'])

    def test_nested_fraction_and_outer_power_are_retained_as_distinct_shapes(self):
        nested=parse_formula_latex(r'\frac{\frac{a}{2}+1}{4}')
        squared=parse_formula_latex(r'(\frac{a+1}{2})^2')
        self.assertTrue(nested['supported'])
        self.assertEqual(fraction_count(nested['ast']),2)
        self.assertTrue(squared['supported'])
        self.assertEqual(squared['normalized_ast']['type'],'power')
        self.assertEqual(squared['normalized_ast']['base']['delimiters'],'()')
        self.assertEqual(squared['normalized_ast']['exponent'],{'type':'number','value':'2'})


class FormulaObservationRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout,cls.check,cls.crop=replay(FIXTURE)

    def observation(self,text=r'\frac{a^{2}+1}{2}'):
        return collect_formula_observations(self.layout,self.crop,recognizer=lambda image:(text,.1))

    def test_all_real_fraction_crops_keep_source_context_and_actual_call_count(self):
        calls=[]
        def recognizer(image):
            calls.append(tuple(image.shape))
            return r'\frac{a^{2}+1}{2}',.1
        value=collect_formula_observations(self.layout,self.crop,recognizer=recognizer)
        self.assertEqual((len(value['payload']['units']),len(calls)),(11,22))
        self.assertEqual(value['producer']['execution_kind'],'SYNTHETIC_TEST')
        self.assertEqual(value['producer']['configuration_sha256'],digest(CONFIG))
        self.assertEqual(value['producer']['version'],'0.1.0')
        self.assertEqual(value['payload']['units'][-1]['source_bbox'],[928,337,971,367])
        self.assertFalse(value['payload']['expected_text_consumed'])

    def test_injected_backend_cannot_promote_itself_and_cannot_change_random_state(self):
        class PretendingBackend:
            execution_kind='CPU_RAPID_LATEX_OCR'
            def __call__(self,image):
                np.random.choice(3)
                return r'\frac{1}{2}',.01
        before=np.random.get_state()
        value=collect_formula_observations(self.layout,self.crop,recognizer=PretendingBackend())
        after=np.random.get_state()
        self.assertEqual(value['producer']['execution_kind'],'SYNTHETIC_TEST')
        self.assertEqual(before[0],after[0]);self.assertTrue(np.array_equal(before[1],after[1]))
        self.assertEqual(before[2:],after[2:])

    def test_backend_failure_or_nonfinite_elapsed_is_explicit_unparsed_observation(self):
        value=collect_formula_observations(self.layout,self.crop,recognizer=lambda image:('fake',float('nan')))
        for unit in value['payload']['units']:
            for variant in unit['variants']:
                self.assertIsNone(variant['raw_latex'])
                self.assertIsNotNone(variant['recognition_error'])
        candidate=build_formula_candidates(self.layout,value,self.crop)
        self.assertTrue(candidate['payload']['issues'])
        self.assertFalse(candidate['payload']['complete'])

    def test_successful_syntax_and_two_variant_agreement_still_do_not_verify_transcription(self):
        value=self.observation()
        before=copy.deepcopy((self.layout,value))
        candidate=build_formula_candidates(self.layout,value,self.crop)
        self.assertEqual((self.layout,value),before)
        for unit in candidate['payload']['units']:
            self.assertTrue(unit['exact_ast_agreement'])
            self.assertEqual(unit['selected_candidate_refs'],[])
            self.assertTrue(all(v['source_fraction_shape_matches'] for v in unit['variants']))
            self.assertFalse(unit['complete'])
        self.assertFalse(candidate['payload']['entire_answer_reconstructed'])
        self.assertEqual(candidate['payload']['decision'],'HOLD')

    def test_model_output_without_source_fraction_or_with_extra_fraction_is_not_shape_complete(self):
        for text in ['a+1',r'\frac{\frac{a}{2}}{3}',r'(\frac{a+1}{2})^2']:
            with self.subTest(text=text):
                candidate=build_formula_candidates(self.layout,self.observation(text),self.crop)
                self.assertTrue(all(not v['source_fraction_shape_matches']
                    for u in candidate['payload']['units'] for v in u['variants']))
                self.assertIn('FORMULA_SOURCE_FRACTION_SHAPE_MISMATCH',{i['code'] for i in candidate['payload']['issues']})

    def test_cached_source_transform_rewrite_even_rehashed_is_rejected(self):
        value=self.observation()
        value['payload']['units'][0]['variants'][0]['transformed_rgb_sha256']='0'*64
        value['content_hash']=digest(value['payload'])
        with self.assertRaises(ValueError):build_formula_candidates(self.layout,value,self.crop)

    def test_model_files_are_required_before_backend_import_or_automatic_download(self):
        with mock.patch.dict(sys.modules,{'rapid_latex_ocr':None}):
            with self.assertRaisesRegex(ValueError,'explicit local formula model'):
                collect_formula_observations(self.layout,self.crop)


if __name__=='__main__':unittest.main()
