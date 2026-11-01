"""Line-wrap eligibility, literal spans and real model disagreement regressions."""
import copy
import json
from pathlib import Path
import sys
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from annotation.recognition.baseline import digest
from annotation.recognition.inline_continuity import build_inline_continuity


def artifact(schema,kind,payload):
    body=dict(schema_version=schema,kind=kind,revision=1,book_id='synthetic',scope_id='synthetic',
        input_refs=[],producer={'execution_kind':'SYNTHETIC_TEST'},payload=payload)
    return {**body,'artifact_id':'synthetic-'+digest(body)[:24],'content_hash':digest(payload)}


def graph_projection(evidence,asset_id,line_ids):
    # Test-only projection; never claimed as the actual complete graph.
    page=next(p for p in evidence['payload']['pages']if p['asset_id']==asset_id)
    rows=[r for r in page['ocr_lines']if r['line_id']in line_ids]
    fs=[];ledger=[];regions=[]
    for row in rows:
        fid='test-fragment-'+row['line_id'];span=[0,len(row['text'])]
        fs.append(dict(asset_id=asset_id,parent_line_id=row['line_id'],fragment_id=fid,
            text_span=span,text=row['text'],content_type='text',role='answer',source_sha256=page['source']['sha256']))
        regions.append(dict(region_id='test-region-'+row['line_id'],asset_id=asset_id,content_type='text',source_fragment_ids=[fid]))
        ledger.append(dict(asset_id=asset_id,line_id=row['line_id'],status='CONSUMED',
            allocations=[dict(answer_id='test-answer',fragment_id=fid,text_span=span)]))
    g=artifact('b-graph-trial/0.3','QuestionGraphTrial',dict(answers=[dict(answer_id='test-answer',fragments=fs,render_regions=regions)],answer_coverage=ledger))
    g['book_id']=evidence['book_id'];g['scope_id']=evidence['scope_id']
    return g


class InlineContinuityTests(unittest.TestCase):
    def setUp(self):
        self.rows=[dict(line_id='p/0',text='说明a=',bbox=[0,0,100,10],location=dict(column=0,window_index=0,section_path=['s'])),
                   dict(line_id='p/1',text='7；下一项',bbox=[0,13,100,23],location=dict(column=0,window_index=0,section_path=['s']))]
        self.e=artifact('b-evidence-trial/0.3','EvidenceBundleTrial',dict(pages=[dict(asset_id='p',source={'sha256':'1'*64},ocr_lines=self.rows)]))
        self.ids=['p/0','p/1'];self.g=graph_projection(self.e,'p',self.ids)
        self.l=artifact('b-inline-math-layout-trial/0.1','InlineMathLayoutTrial',dict(requested_line_ids=self.ids,
            source=dict(asset_id='p',original_sha256='1'*64),units=[dict(unit_id='u',line_id='p/0',raw_text='a=')]))
        self.c=artifact('b-inline-formula-candidate-trial/0.1','InlineFormulaCandidateTrial',dict(candidates=[
            dict(call_id='call1',candidate_id='candidate1',raw_latex='a=1',unit_bindings=[dict(unit_id='u')]),
            dict(call_id='call2',candidate_id='candidate2',raw_latex='a=1',unit_bindings=[dict(unit_id='u')])]))

    def run_case(self):
        for v in(self.e,self.g,self.l,self.c):v['content_hash']=digest(v['payload'])
        return build_inline_continuity(self.e,self.g,self.l,self.c,asset_id='p',line_ids=self.ids)['payload']

    def refresh_graph(self):self.g=graph_projection(self.e,'p',self.ids)

    def test_literal_open_equation_keeps_both_wrong_model_closures(self):
        old=copy.deepcopy((self.e,self.g,self.l,self.c));p=self.run_case();v=p['proposals'][0]
        self.assertEqual(v['joined_raw_text'],'a=7')
        self.assertEqual(v['source_spans'][0]['text_span'],[2,4])
        self.assertEqual(len(p['diagnostics']),2)
        self.assertEqual([d['raw_latex']for d in p['diagnostics']],['a=1','a=1'])
        self.assertEqual(v['bindings'][0]['fragments'][0]['render_region_ids'],['test-region-p/0'])
        self.assertFalse(v['selected']);self.assertFalse(v['transcription_verified'])
        self.assertEqual(p['selected_proposal_ids'],[])
        self.assertEqual((self.e,self.g,self.l,self.c),old)

    def test_relation_chain_keeps_raw_decimal_punctuation_ambiguity(self):
        self.rows[0]['text']='说明925.625<725';self.rows[1]['text']='<925，说明';self.refresh_graph()
        p=self.run_case();v=p['proposals'][0]
        self.assertEqual(v['joined_raw_text'],'925.625<725<925')
        self.assertIn('DOT_MAY_BE_PUNCTUATION_OR_DECIMAL',v['risks'])
        self.assertEqual(p['diagnostics'],[])

    def rejected(self,reason):
        p=self.run_case();self.assertEqual(p['proposals'],[])
        self.assertEqual(p['rejected_adjacent_pairs'][0]['reason'],reason)

    def test_no_implicit_join_of_ordinary_prose_or_numbers(self):
        self.rows[0]['text']='a=12';self.refresh_graph();self.rejected('NO_EXPLICIT_MATH_WRAP_MARKER')

    def test_missing_location_is_not_a_shared_namespace(self):
        for row in self.rows:row['location']={}
        self.refresh_graph();self.rejected('SOURCE_LOCATION_UNKNOWN')

    def test_boolean_column_is_not_the_same_as_column_zero(self):
        self.rows[1]['location']['column']=False
        self.rejected('SOURCE_LOCATION_UNKNOWN')

    def test_different_column_window_or_section(self):
        for field,value in [('column',1),('window_index',1),('section_path',['other'])]:
            with self.subTest(field=field):
                old=copy.deepcopy(self.rows[1]['location']);self.rows[1]['location'][field]=value
                self.rejected('DIFFERENT_COLUMN_WINDOW_OR_SECTION');self.rows[1]['location']=old

    def test_intervening_raw_row_cannot_be_hidden_by_request_scope(self):
        self.rows.append(dict(line_id='p/middle',text='中间行',bbox=[0,11,100,12],location=copy.deepcopy(self.rows[0]['location'])))
        self.rejected('INTERVENING_RAW_SOURCE_ROW')

    def test_reversed_reading_order_is_rejected(self):
        self.ids.reverse();self.l['payload']['requested_line_ids']=self.ids
        self.rejected('REQUESTED_ROWS_NOT_IN_SOURCE_READING_ORDER')

    def test_vertical_gap_and_horizontal_column_geometry(self):
        self.rows[1]['bbox']=[0,40,100,50];self.rejected('VERTICAL_WRAP_GEOMETRY_UNPROVEN')
        self.rows[1]['bbox']=[200,13,300,23];self.rejected('HORIZONTAL_COLUMN_GEOMETRY_UNPROVEN')

    def test_question_option_subpart_and_circled_markers_are_not_operands(self):
        for text in['1.新题','A.选项','（2）下一问','③后续方案']:
            with self.subTest(text=text):
                self.rows[1]['text']=text;self.refresh_graph();self.rejected('NEXT_ROW_LOOKS_LIKE_NEW_QUESTION')

    def test_unassigned_row_stays_unassigned(self):
        self.g['payload']['answer_coverage'][1]['status']='UNASSIGNED'
        self.rejected('SOURCE_NOT_UNIQUELY_CONSUMED')

    def test_source_fragment_coverage_cannot_have_gap_or_overlap(self):
        f=self.g['payload']['answers'][0]['fragments'][0]
        f['text_span']=[0,3];f['text']='说明a';self.g['payload']['answer_coverage'][0]['allocations'][0]['text_span']=[0,3]
        self.rejected('FRAGMENT_COVERAGE_GAP_OR_OVERLAP')

    def test_forged_source_fragment_or_image_diagnostic_cannot_supply_text(self):
        f=self.g['payload']['answers'][0]['fragments'][0]
        f['text']='wrong';self.rejected('FRAGMENT_NOT_LITERAL_TEXT')
        f['text']=self.rows[0]['text'];f['represented_by_image_region']='image'
        self.rejected('FRAGMENT_NOT_LITERAL_TEXT')

    def test_actual_current_answer_and_semantic_role_must_match(self):
        answer=self.g['payload']['answers'][0];f=answer['fragments'].pop()
        self.g['payload']['answers'].append(dict(answer_id='other-answer',fragments=[f]))
        self.g['payload']['answer_coverage'][1]['allocations'][0]['answer_id']='other-answer'
        self.rejected('DIFFERENT_CURRENT_ANSWER_OR_ROLE')
        self.g['payload']['answers'][1]['answer_id']='test-answer'
        self.g['payload']['answer_coverage'][1]['allocations'][0]['answer_id']='test-answer'
        f['role']='explanation';self.rejected('DIFFERENT_CURRENT_ANSWER_OR_ROLE')

    def test_partial_row_fragment_can_bind_exact_span_without_widening(self):
        f=self.g['payload']['answers'][0]['fragments'][0]
        f['text_span']=[2,4];f['text']='a=';self.g['payload']['answer_coverage'][0]['allocations'][0]['text_span']=[2,4]
        p=self.run_case();self.assertEqual(p['proposals'][0]['joined_raw_text'],'a=7')

    def test_invalid_source_or_layout_hash_is_rejected(self):
        self.e['content_hash']='0'*64
        with self.assertRaises(ValueError):build_inline_continuity(self.e,self.g,self.l,self.c,asset_id='p',line_ids=self.ids)

    def test_real_source_spans_and_real_hallucinations_without_new_inference(self):
        with zipfile.ZipFile(ROOT/'tests/fixtures/book46007447/inline-observed.zip')as z:
            read=lambda n:json.loads(z.read(n))
            e=read('evidence.json');l=read('math-layout.json');ids=read('rows.json')
            c=read('formula-observed-trials/formal-warm-candidates.json')
        # Only the source and model observations are real; the graph here is a
        # labelled synthetic projection. Full graph integration is checked in
        # actual pipeline/export runs with all 202 ledger rows.
        g=graph_projection(e,'resource-173',ids)
        p=build_inline_continuity(e,g,l,c,asset_id='resource-173',line_ids=ids)['payload']
        self.assertEqual(len(p['proposals']),2);self.assertEqual(len(p['rejected_adjacent_pairs']),6)
        self.assertEqual(p['proposals'][0]['joined_raw_text'],'AB²=10²+25²=725')
        self.assertEqual(len(p['diagnostics']),4)
        self.assertTrue(all(d['raw_latex'].endswith('=1')for d in p['diagnostics']))
        self.assertIn('5=925.625',p['proposals'][1]['joined_raw_text'])
        self.assertFalse(p['complete']);self.assertFalse(p['business_acceptance'])

if __name__=='__main__':unittest.main()
