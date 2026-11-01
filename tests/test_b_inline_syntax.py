"""Inline roots preserve raw scope; historical fraction parsing stays bounded."""
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from annotation.recognition.formula_syntax import parse_formula_latex,parse_inline_formula_latex


class InlineSyntaxTests(unittest.TestCase):
    def test_radical_scope_does_not_evaluate_or_drop_the_root(self):
        raw=r'\sqrt{625}=25'
        parsed=parse_inline_formula_latex(raw)
        self.assertTrue(parsed['supported'])
        root=parsed['ast']['items'][0]
        self.assertEqual(root['type'],'radical')
        self.assertIsNone(root['index'])
        self.assertEqual(root['raw_source_span'],[0,10])
        self.assertEqual(root['radicand']['delimiters'],'{}')
        self.assertEqual(root['radicand']['body']['items'][0]['value'],'625')
        self.assertEqual(parsed['normalized_ast']['items'][0]['type'],'radical')
        self.assertNotEqual(parsed['normalized_ast'],parse_inline_formula_latex('625=25')['normalized_ast'])

    def test_index_and_script_are_separate_source_scopes(self):
        raw=r'\sqrt[3]{x^{2}+1}'
        p=parse_inline_formula_latex(raw)
        self.assertTrue(p['supported'])
        root=p['ast']['items'][0]
        self.assertEqual(root['index']['delimiters'],'[]')
        self.assertEqual(root['index']['body']['items'][0]['value'],'3')
        self.assertEqual(root['radicand']['body']['items'][0]['type'],'power')
        self.assertEqual(root['raw_source_span'],[0,len(raw)])

    def test_typographic_commands_preserve_their_braced_scope(self):
        p=parse_inline_formula_latex(r'\mathrm{AB}^{2}=20^{2}+15^{2}\mathrm{cm}')
        self.assertTrue(p['supported'])
        power=p['ast']['items'][0]
        self.assertEqual(power['base']['type'],'styled')
        self.assertEqual(power['base']['style'],r'\mathrm')
        self.assertEqual(power['base']['body']['body']['items'][0]['value'],'A')
        self.assertEqual(power['exponent']['body']['items'][0]['value'],'2')
        self.assertEqual(p['ast']['items'][-1]['type'],'styled')

    def test_single_symbol_radical_is_bounded_and_multidigit_requires_braces(self):
        self.assertTrue(parse_inline_formula_latex(r'\sqrt x')['supported'])
        for raw in (r'\sqrt625',r'\sqrt',r'\sqrt{}',r'\sqrt[]{2}',r'\sqrt[3]{2',r'\sqrt[3]'):
            with self.subTest(raw=raw):
                self.assertFalse(parse_inline_formula_latex(raw)['supported'])

    def test_unknown_commands_keep_the_earliest_unparsed_tail(self):
        raw=r'\unknown{2}+\sqrt{625}+中文'
        p=parse_inline_formula_latex(raw)
        self.assertFalse(p['supported'])
        self.assertEqual(p['unparsed_tail'],raw)
        for raw in (r'\sqrt{625}+\bad',r'\text{中文}',r'x^{2}^{3}'):
            self.assertFalse(parse_inline_formula_latex(raw)['supported'])

    def test_historical_profile_does_not_silently_expand_its_accepted_language(self):
        for raw in (r'\sqrt{625}',r'\mathrm{AB}',r'\pi+1',r'\therefore x=1'):
            old=parse_formula_latex(raw)
            self.assertFalse(old['supported'])
            self.assertIsNone(old['ast'])
            self.assertNotIn('syntax_profile',old)
            self.assertTrue(parse_inline_formula_latex(raw)['supported'])

    def test_ratio_colon_is_retained_and_cannot_be_coalesced_into_thirteen(self):
        p=parse_inline_formula_latex('1:3')
        self.assertTrue(p['supported'])
        self.assertEqual([v['value'] for v in p['ast']['items']],['1',':','3'])
        self.assertNotEqual(p['normalized_ast'],parse_inline_formula_latex('13')['normalized_ast'])
        self.assertFalse(parse_formula_latex('1:3')['supported'])

    def test_both_profiles_preserve_all_existing_frozen_tokens_and_asts(self):
        fixture=ROOT/'tests/fixtures/book46007447'
        for filename in ('formula-observations.json','formula-canvas-observations.json'):
            obs=json.loads((fixture/filename).read_text(encoding='utf-8'))
            for unit in obs['payload']['units']:
                for v in unit['variants']:
                    raw=v['raw_latex']
                    old=parse_formula_latex(raw)
                    new=parse_inline_formula_latex(raw)
                    if old['supported']:
                        self.assertTrue(new['supported'])
                        for key in ('tokens','ast','normalized_ast'):
                            self.assertEqual(new[key],old[key])
                    self.assertEqual(new['raw_latex'],raw)

if __name__=='__main__':unittest.main()
