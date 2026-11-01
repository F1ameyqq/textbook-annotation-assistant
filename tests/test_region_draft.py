"""Automatic candidates retain raw observations and never borrow manual text."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from annotation.recognition.baseline import digest
from annotation.recognition.region_runs import plan_region_runs
from annotation.recognition.region_ocr import collect_region_observations
from annotation.recognition.region_draft import build_region_draft,make_region_draft_plan
from annotation.recognition.region_report import render_region_report
from annotation.recognition.content_revision import apply_content_revision
from content_revision_observed import observed_inputs


class RegionDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=ROOT/'tests/fixtures/book46007447'
        cls.read=staticmethod(lambda name:json.loads((cls.fixture/name).read_text(encoding='utf-8')))
        cls.crop=cls.fixture/'recovery-assets/unit2-q16.png'
        cls.plan=plan_region_runs(cls.read('formula-layout.json'),cls.crop)
        cls.obs=collect_region_observations(cls.plan,cls.crop,recognizer=lambda *a,**kw:([['generated body',.8]],[.01]))
        cls.inputs,_=observed_inputs()
        cls.draft=cls.build(cls.obs)
        cls.previous=cls.read('content-region-plan-v1.json')
        cls.author=dict(kind='SYNTHETIC_TEST',id='generated-region-tests',note='Generated body observations, not human review')

    @classmethod
    def build(cls,obs):
        return build_region_draft(cls.plan,obs,cls.read('formula-observations.json'),cls.read('formula-canvas-observations.json'),cls.read('math-role-evidence.json'),cls.crop)

    def make(self,draft=None,author=None):
        d=self.inputs
        return make_region_draft_plan(d['evidence'],d['graph'],d['base-check'],draft or self.draft,
            answer_id='a-7302d4870826c53aea0bcd16',previous_plan=self.previous,author=author or self.author,crop_path=self.crop)

    def test_all_raw_whole_candidates_and_same_fraction_compositions_are_retained(self):
        self.assertEqual(sum(len(f['whole_candidates']) for f in self.draft['payload']['fractions']),44)
        for f in self.draft['payload']['fractions']:
            components={c['component_id']:c for values in f['components'].values() for c in values}
            self.assertTrue(f['composed_candidates'])
            for candidate in f['composed_candidates']:
                selected=[components[c] for c in candidate['component_refs']]
                self.assertEqual([c['role'] for c in selected],['numerator','denominator'])
                self.assertTrue(all(c['fraction_id']==f['fraction_id'] for c in selected))
                self.assertEqual(candidate['kind'],'DERIVED_ROLE_COMPOSITION')
                self.assertFalse(candidate['complete_model_call'])
                self.assertIn(candidate['candidate_id'],{c['candidate_id'] for c in f['composed_candidates']})

    def test_f9_bad_stable_whole_and_duplicate_formula_still_exist_beside_role_compositions(self):
        f=self.draft['payload']['fractions'][8]
        legacy=[c for c in f['whole_candidates'] if c['origin']['kind']=='LEGACY_WHOLE']
        self.assertEqual(legacy[0]['latex'],legacy[1]['latex'])
        self.assertTrue(any(c['parse_result']['supported'] and not c['source_fraction_shape_matches'] for c in f['whole_candidates']))
        selected=next(c for c in f['composed_candidates'] if c['candidate_id']==f['draft_candidate_id'])
        components={c['component_id']:c for values in f['components'].values() for c in values}
        self.assertTrue(all(components[i]['origin']['kind']=='ROLE_OCR' for i in selected['component_refs']))
        self.assertFalse(f['selection_is_content_verification'])

    def test_f5_cross_backend_role_composition_is_explicit_and_not_a_new_cpu_call(self):
        f=self.draft['payload']['fractions'][4]
        components={c['component_id']:c for values in f['components'].values() for c in values}
        self.assertTrue(any(components[c['component_refs'][0]]['origin']['kind']=='CANVAS_WHOLE'
            and components[c['component_refs'][1]]['origin']['kind']=='ROLE_OCR' for c in f['composed_candidates']))
        self.assertEqual(self.draft['payload']['archives']['observations'],self.obs)
        self.assertEqual(self.draft['producer']['execution_kind'],'SYNTHETIC_TEST')

    def test_synthetic_body_cannot_be_promoted_to_model_or_human_author(self):
        for kind in ('MODEL_DRAFT','HUMAN_DRAFT'):
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                self.make(author={**self.author,'kind':kind})

    def test_new_plan_keeps_manual_archive_other_answer_operations_and_raw_sources(self):
        previous=copy.deepcopy(self.previous)
        new=self.make()
        self.assertEqual(self.previous,previous)
        self.assertEqual(new['payload']['previous_plan_archive'],previous)
        aid='a-7302d4870826c53aea0bcd16'
        old_other=[o for o in previous['payload']['operations'] if o['target'].get('answer_id')!=aid] if all('target' in o for o in previous['payload']['operations']) else previous['payload']['operations'][:-1]
        self.assertEqual(new['payload']['operations'][:-1],old_other)
        d=self.inputs;app=apply_content_revision(d['evidence'],d['graph'],d['base-check'],new)
        g=app['payload']['graph']['payload'];old=d['graph']['payload']
        self.assertEqual(g['questions'],old['questions'])
        self.assertEqual(g['answer_coverage'],old['answer_coverage'])
        self.assertEqual(g['inline_content'],old['inline_content'])
        for current,base in zip(g['answers'],old['answers']):self.assertEqual(current['fragments'],base['fragments'])
        target=next(a for a in g['answers'] if a['answer_id']==aid)
        self.assertEqual(len([c for c in target['content_fragments'] if c.get('kind')=='REGION_DRAFT']),3)

    def test_coordinated_changed_text_hash_is_rejected_before_plan(self):
        draft=copy.deepcopy(self.draft)
        draft['payload']['rows'][0]['runs'][0]['text']='not in source observations'
        draft['content_hash']=digest(draft['payload'])
        with self.assertRaises(ValueError):self.make(draft=draft)

    def test_unread_body_uses_whole_row_fallback_without_hiding_partial_alternatives(self):
        calls=0
        limit=len(self.plan['payload']['body_slots'])*2
        def recognizer(*a,**kw):
            nonlocal calls
            calls+=1
            return (None if calls<=limit else [['whole row raw',.6]]),[.01]
        obs=collect_region_observations(self.plan,self.crop,recognizer=recognizer)
        d=self.build(obs)
        self.assertTrue(all(row['full_row_fallback_used'] for row in d['payload']['rows']))
        self.assertTrue(all(row['runs']==[dict(format='plain',text='whole row raw')] for row in d['payload']['rows']))
        self.assertTrue(all(row['segmented_draft']['runs'] for row in d['payload']['rows']))
        self.assertTrue(any(r['code']=='BODY_OCR_UNREAD' for r in d['payload']['risks']))
        self.assertFalse(d['payload']['complete'])

    def test_bad_raw_rows_are_archived_but_not_silently_used_as_text(self):
        obs=collect_region_observations(self.plan,self.crop,recognizer=lambda *a,**kw:([['valid',.8],['invalid',None]],[.01]))
        d=self.build(obs)
        self.assertTrue(any(r['code']=='UNUSABLE_BODY_CANDIDATES_NOT_TRANSCRIBED' for r in d['payload']['risks']))
        self.assertTrue(all('invalid' not in r['text'] for row in d['payload']['rows'] for r in row['runs']))
        self.assertEqual(d['payload']['archives']['observations'],obs)

    def test_context_symbols_are_traceable_and_never_become_verified_character_ownership(self):
        calls=0;limit=len(self.plan['payload']['body_slots'])*2
        def recognizer(*a,**kw):
            nonlocal calls
            calls+=1
            raw=None if calls%2 else [['(',.5]]
            if calls>limit:raw=[['whole fallback',.6]]
            return raw,[.01]
        obs=collect_region_observations(self.plan,self.crop,recognizer=recognizer);d=self.build(obs)
        self.assertTrue(any(r['code']=='CONTEXT_SYMBOL_OWNERSHIP_UNVERIFIED' for r in d['payload']['risks']))
        self.assertTrue(any(b['kind']=='BODY_CONTEXT_SYMBOL' for row in d['payload']['rows'] for b in row['bindings']))
        self.assertFalse(d['payload']['body_context_is_exact_character_alignment'])

    def test_context_letters_or_numbers_cannot_silently_duplicate_fraction_content(self):
        calls=0;limit=len(self.plan['payload']['body_slots'])*2
        def recognizer(*a,**kw):
            nonlocal calls
            calls+=1
            raw=None if calls%2 else [['(x+1)/2',.7]]
            if calls>limit:raw=[['whole fallback',.6]]
            return raw,[.01]
        d=self.build(collect_region_observations(self.plan,self.crop,recognizer=recognizer))
        self.assertTrue(all(r['full_row_fallback_used'] for r in d['payload']['rows']))
        self.assertFalse(any(b['kind']=='BODY_CONTEXT_SYMBOL' for r in d['payload']['rows'] for b in r['bindings']))

    def test_coordinated_rehashed_pixel_risk_deletion_is_not_a_source_plan(self):
        plan=copy.deepcopy(self.plan);plan['payload']['risks']=[];plan['content_hash']=digest(plan['payload'])
        plan['artifact_id']='region-runs-'+digest([plan['input_refs'],plan['producer'],plan['payload']])[:24]
        with self.assertRaises(ValueError):
            build_region_draft(plan,self.obs,self.read('formula-observations.json'),self.read('formula-canvas-observations.json'),self.read('math-role-evidence.json'),self.crop)

    def test_standalone_report_escapes_model_text_and_embeds_existing_source_unchanged(self):
        d=copy.deepcopy(self.draft);d['payload']['rows'][0]['runs'][0]['text']='<script>alert("x")</script>'
        report=render_region_report(d,self.crop)
        self.assertNotIn('<script>',report)
        self.assertIn('&lt;script&gt;',report)
        self.assertIn('data:image/png;base64,',report)
        self.assertIn('DERIVED_ROLE_COMPOSITION',report)
        self.assertIn('HOLD',report)


if __name__=='__main__':unittest.main()
