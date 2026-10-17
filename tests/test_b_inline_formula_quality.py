"""Independent inline ROI/formula/journal faults; all engines are synthetic."""
from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"tests")]
from test_b_inline_formula import formula_fixture,FormulaWorker
from annotation.recognition.baseline import digest
from annotation.recognition.inline_formula import collect_inline_formula
from annotation.recognition.inline_candidates import build_inline_candidates
from annotation.recognition.inline_formula_quality import audit_inline_formula


def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def ref(value):return {k:value[k]for k in ("artifact_id","revision","content_hash")}
def bind(value,prefix):
    value["content_hash"]=digest(value["payload"])
    value["artifact_id"]=prefix+"-"+digest({k:v for k,v in value.items()if k not in {"artifact_id","content_hash"}})[:24]
    return value


class InlineFormulaQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.f=formula_fixture(self.root);self.work=self.root/"work"

    def collect(self,worker=None,**kwargs):
        obs,report=collect_inline_formula(self.f["evidence"],self.f["layout"],self.f["original"],self.work,
            line_ids=self.f["line_ids"],recognizer=worker or FormulaWorker(),**kwargs)
        return obs,build_inline_candidates(obs),report

    def audit(self,obs,candidates,report,layout=None):
        return audit_inline_formula(self.f["evidence"],layout or self.f["layout"],obs,candidates,self.f["original"],
            line_ids=self.f["line_ids"],workdir=self.work,report=report)["payload"]

    def put(self,value):
        data=encode(value);sha=hashlib.sha256(data).hexdigest()
        (self.work/"objects"/(sha+".json")).write_bytes(data)
        return {"path":"objects/"+sha+".json","sha256":sha,"artifact_ref":ref(value)}

    def persist_rebound_report(self,obs,report):
        descriptor=self.put(obs)
        report["payload"]["result_ref"]=ref(obs);report["input_refs"][1]=ref(obs)
        report["payload"]["observation_output"]=descriptor
        with closing(sqlite3.connect(self.work/"inline-formula.sqlite3"))as db:
            row=db.execute("SELECT details_json FROM events WHERE event_id=?",(report["payload"]["terminal_event_id"],)).fetchone()
            detail=json.loads(row[0]);detail["observation_output"]=descriptor
            detail["counts"]=report["payload"]["counts"];detail["state"]=report["payload"]["state"]
            db.execute("UPDATE events SET details_json=? WHERE event_id=?",(encode(detail).decode(),report["payload"]["terminal_event_id"]));db.commit()
        bind(report,"inline-formula-run");self.put(report)

    def test_full_scope_source_and_syntax_are_traceable_but_not_accepted_content(self):
        obs,candidates,report=self.collect(FormulaWorker((r"\sqrt{625}=25",r"625=25^{2}",r"\frac{1}{3}")))
        result=self.audit(obs,candidates,report)
        self.assertTrue(result["accepted"],result["issues"])
        self.assertEqual(result["summary"]["declared_calls"],16)
        self.assertEqual(result["summary"]["done"],16)
        self.assertEqual(result["summary"]["model_calls_during_audit"],0)
        self.assertEqual(result["decision"],"HOLD")
        self.assertFalse(result["entire_answer_reconstructed"])
        self.assertFalse(result["transcription_verified"])
        self.assertFalse(result["business_acceptance"])

    def test_audit_invokes_no_collector_proposer_candidate_parser_or_model(self):
        obs,candidates,report=self.collect()
        with patch("annotation.recognition.inline_formula.collect_inline_formula",side_effect=AssertionError("collect")), \
             patch("annotation.recognition.inline_formula.plan_inline_formula_calls",side_effect=AssertionError("plan")), \
             patch("annotation.recognition.inline_math.build_inline_math_layout",side_effect=AssertionError("ROIproducer")), \
             patch("annotation.recognition.inline_candidates.build_inline_candidates",side_effect=AssertionError("candidate")), \
             patch("annotation.recognition.formula_syntax.parse_inline_formula_latex",side_effect=AssertionError("parser")):
            self.assertTrue(self.audit(obs,candidates,report)["accepted"])

    def test_partial_resume_and_warm_cache_keep_full_declared_scope(self):
        worker=FormulaWorker()
        obs,candidates,report=self.collect(worker,max_items=2)
        result=self.audit(obs,candidates,report)
        self.assertTrue(result["accepted"],result["issues"])
        self.assertEqual(result["summary"]["declared_calls"],16)
        self.assertEqual(result["summary"]["pending"],14)
        obs,candidates,report=self.collect(worker)
        self.assertTrue(self.audit(obs,candidates,report)["accepted"])
        obs,candidates,report=self.collect(worker)
        result=self.audit(obs,candidates,report)
        self.assertTrue(result["accepted"],result["issues"])
        self.assertEqual(report["payload"]["counts"]["new_encoder_decoder_calls"],0)
        self.assertEqual(report["payload"]["counts"]["cache_hits"],16)

    def test_no_eligible_units_need_no_optional_model_and_keep_weak_units(self):
        self.f=formula_fixture(self.root,math_text="A，cm，4")
        with patch("annotation.recognition.inline_formula._local_cpu_backend",side_effect=AssertionError("modelinit")):
            obs,report=collect_inline_formula(self.f["evidence"],self.f["layout"],self.f["original"],self.work,line_ids=self.f["line_ids"])
        result=self.audit(obs,build_inline_candidates(obs),report)
        self.assertTrue(result["accepted"],result["issues"])
        self.assertEqual(result["summary"]["declared_calls"],0)
        self.assertGreater(len(obs["payload"]["not_inference_units"]),0)
        self.assertEqual(report["payload"]["model_initializations"],0)

    def test_ambiguous_ten_bridge_is_reread_without_turning_it_into_plus(self):
        self.f=formula_fixture(self.root,math_text="10十5")
        obs,candidates,report=self.collect()
        self.assertTrue(self.audit(obs,candidates,report)["accepted"])
        self.assertGreater(len(obs["payload"]["calls"]),0)
        self.assertTrue(all(u["raw_text"]=="10十5"for u in self.f["layout"]["payload"]["units"]if u["kind"]=="MATHLIKE_RUN"))

    def test_variable_only_formula_is_eligible_without_inventing_numeric_operands(self):
        self.f=formula_fixture(self.root,math_text="a²+b²=c²，x+y=z，A，cm")
        obs,candidates,report=self.collect()
        result=self.audit(obs,candidates,report)
        self.assertTrue(result["accepted"],result["issues"])
        unit_map={u["unit_id"]:u for u in self.f["layout"]["payload"]["units"]}
        read_text={unit_map[b["unit_id"]]["raw_text"]for call in obs["payload"]["calls"]for b in call["plan"]["unit_bindings"]}
        self.assertEqual(read_text,{"a²+b²=c²","x+y=z"})
        skipped_text={r["raw_text"]for r in obs["payload"]["not_inference_units"]if r["raw_text"]is not None}
        self.assertEqual(skipped_text,{"A","cm"})

    def test_full_line_fallback_cannot_be_removed_after_rehashing_layout(self):
        obs,candidates,report=self.collect();layout=copy.deepcopy(self.f["layout"])
        layout["payload"]["units"]=layout["payload"]["units"][1:]
        layout["content_hash"]=digest(layout["payload"])
        layout["artifact_id"]="inline-math-layout-"+digest([layout["input_refs"],layout["producer"],layout["payload"]])[:24]
        result=self.audit(obs,candidates,report,layout)
        self.assertFalse(result["accepted"])
        self.assertIn("INLINE_FORMULA_MATH_SOURCE_PROJECTION_MISMATCH",{i["code"]for i in result["issues"]})

    def test_fake_layout_header_approval_is_rejected_after_coordinated_archive_and_journal_rebinding(self):
        for key in ("human_verified","precise_glyph_localization"):
            with self.subTest(key=key):
                saved=self.work;self.work=self.root/key
                obs,candidates,report=self.collect()
                layout=copy.deepcopy(self.f["layout"]);original_payload=copy.deepcopy(layout["payload"])
                layout[key]=True
                # The old layout ID recipe binds inputs/producer/payload, so
                # these conflicting header claims did not change its ref.
                self.assertEqual(ref(layout),ref(self.f["layout"]))
                self.assertEqual(layout["payload"],original_payload)
                obs["payload"]["layout_archive"]=layout
                bind(obs,"inline-formula-observations")
                candidates=build_inline_candidates(obs)
                self.persist_rebound_report(obs,report)
                result=self.audit(obs,candidates,report,layout)
                self.assertFalse(result["accepted"])
                self.assertEqual({i["code"]for i in result["issues"]},{"INLINE_FORMULA_LAYOUT_HEADER_INVALID"})
                self.work=saved

    def test_core_crop_cannot_trim_upper_row_ink_with_coordinated_observation_hash(self):
        obs,candidates,report=self.collect()
        call=obs["payload"]["calls"][0];call["plan"]["source_bbox"][1]+=2
        bind(obs,"inline-formula-observations");candidates=build_inline_candidates(obs)
        result=self.audit(obs,candidates,report)
        self.assertFalse(result["accepted"])
        self.assertIn("INLINE_FORMULA_CALL_PLAN_OR_STATE_MISMATCH",{i["code"]for i in result["issues"]})

    def test_coordinated_missing_call_and_terminal_counts_still_violate_source_plan(self):
        obs,candidates,report=self.collect()
        obs["payload"]["calls"].pop();report["payload"]["calls"].pop()
        for key in ("declared_calls","done","new_attempts","new_encoder_decoder_calls"):report["payload"]["counts"][key]-=1
        bind(obs,"inline-formula-observations");candidates=build_inline_candidates(obs)
        self.persist_rebound_report(obs,report)
        result=self.audit(obs,candidates,report)
        self.assertFalse(result["accepted"])
        self.assertIn("INLINE_FORMULA_CALL_SCOPE_MISMATCH",{i["code"]for i in result["issues"]})

    def test_changed_canvas_tensor_cannot_be_hidden_by_valid_raw_latex(self):
        obs,candidates,report=self.collect()
        value=obs["payload"]["calls"][0]["observation"]
        value["payload"]["preprocessing"]["tensor_sha256"]="0"*64
        bind(value,"inline-formula-observed-call");bind(obs,"inline-formula-observations")
        result=self.audit(obs,build_inline_candidates(obs),report)
        self.assertFalse(result["accepted"])
        self.assertIn("INLINE_FORMULA_CANVAS_OR_TENSOR_MISMATCH",{i["code"]for i in result["issues"]})

    def test_unknown_commands_remain_raw_unparsed_not_silently_removed(self):
        obs,candidates,report=self.collect(FormulaWorker((r"\dagger+2",)))
        result=self.audit(obs,candidates,report)
        self.assertTrue(result["accepted"],result["issues"])
        self.assertEqual(result["summary"]["parsed_candidates"],0)
        self.assertEqual(result["summary"]["unparsed_candidates"],16)
        candidate=candidates["payload"]["candidates"][0];candidate["raw_latex"]="2"
        bind(candidates,"inline-formula-candidates")
        self.assertFalse(self.audit(obs,candidates,report)["accepted"])

    def test_unsupported_tail_cannot_start_after_a_known_unknown_command(self):
        obs,candidates,report=self.collect(FormulaWorker((r"\dagger+2",)))
        candidate=candidates["payload"]["candidates"][0]
        parsed=candidate["parse_result"];parsed["errors"][0]["position"]=len(candidate["raw_latex"]);parsed["unparsed_tail"]=""
        bind(candidates,"inline-formula-candidates")
        result=self.audit(obs,candidates,report)
        self.assertFalse(result["accepted"])
        self.assertIn("INLINE_FORMULA_UNKNOWN_SYNTAX_TAIL_DROPPED",{i["code"]for i in result["issues"]})

    def test_radical_and_power_are_distinct_raw_token_owned_roles(self):
        obs,candidates,report=self.collect(FormulaWorker((r"\sqrt{625}=25",)))
        parsed=candidates["payload"]["candidates"][0]["parse_result"]
        self.assertEqual(parsed["ast"]["items"][0]["type"],"radical")
        parsed["ast"]["items"][0]["type"]="power"
        bind(candidates,"inline-formula-candidates")
        result=self.audit(obs,candidates,report)
        self.assertFalse(result["accepted"])
        self.assertIn("INLINE_FORMULA_AST_RAW_PROJECTION_MISMATCH",{i["code"]for i in result["issues"]})

    def test_fraction_order_and_script_value_cannot_be_changed_in_ast(self):
        for raw in (r"\frac{1}{3}",r"25^{2}"):
            with self.subTest(raw=raw):
                work=self.root/("fraction"if "frac"in raw else"power");saved=self.work;self.work=work
                obs,candidates,report=self.collect(FormulaWorker((raw,)))
                ast=candidates["payload"]["candidates"][0]["parse_result"]["ast"]["items"][0]
                if ast["type"]=="fraction":ast["numerator"],ast["denominator"]=ast["denominator"],ast["numerator"]
                else:ast["exponent"]["body"]["items"][0]["value"]="3"
                bind(candidates,"inline-formula-candidates")
                self.assertFalse(self.audit(obs,candidates,report)["accepted"])
                self.work=saved

    def test_normalized_tree_cannot_simplify_away_or_relabel_raw_symbols(self):
        obs,candidates,report=self.collect(FormulaWorker((r"\sqrt[3]{8}:2\because 1=1",)))
        self.assertTrue(self.audit(obs,candidates,report)["accepted"])
        candidates["payload"]["candidates"][0]["parse_result"]["normalized_ast"]={"type":"number","value":"4"}
        bind(candidates,"inline-formula-candidates")
        self.assertFalse(self.audit(obs,candidates,report)["accepted"])

    def test_failed_elapsed_keeps_raw_reading_as_unselected_failed_candidate(self):
        class InvalidElapsed(FormulaWorker):
            def __call__(self,tensor):return r"625=25^{2}",-.1
        obs,candidates,report=self.collect(InvalidElapsed())
        result=self.audit(obs,candidates,report)
        self.assertTrue(result["accepted"],result["issues"])
        self.assertEqual(result["summary"]["failed"],16)
        self.assertEqual(result["summary"]["parsed_candidates"],16)
        self.assertTrue(all(c["raw_latex"]==r"625=25^{2}"and c["state"]=="FAILED"and c["selected"]is False for c in candidates["payload"]["candidates"]))

    def test_warm_cache_without_started_or_succeeded_origin_is_not_a_pass(self):
        obs,candidates,report=self.collect();obs,candidates,report=self.collect()
        with closing(sqlite3.connect(self.work/"inline-formula.sqlite3"))as db:
            db.execute("DELETE FROM events WHERE kind='STARTED' AND attempt_id=?",(report["payload"]["calls"][0]["origin_attempt_id"],));db.commit()
        result=self.audit(obs,candidates,report)
        self.assertFalse(result["accepted"])
        self.assertIn("INLINE_FORMULA_ORIGIN_EVENTS_MISMATCH",{i["code"]for i in result["issues"]})

    def test_sql_success_alone_does_not_replace_actual_immutable_file_bytes(self):
        obs,candidates,report=self.collect()
        descriptor=report["payload"]["calls"][0]["output"]
        (self.work/descriptor["path"]).write_text("{}",encoding="utf8")
        self.assertFalse(self.audit(obs,candidates,report)["accepted"])

    def test_false_complete_human_or_selected_metadata_is_rejected(self):
        obs,candidates,report=self.collect()
        for key in ("complete","business_acceptance","entire_answer_reconstructed","human_verified"):
            value=copy.deepcopy(candidates);value["payload"][key]=True;bind(value,"inline-formula-candidates")
            self.assertFalse(self.audit(obs,value,report)["accepted"])

    def test_synthetic_cannot_be_cpu_by_only_changing_label(self):
        obs,candidates,report=self.collect();obs["producer"]["execution_kind"]="CPU_RAPID_LATEX_OCR_INLINE";bind(obs,"inline-formula-observations")
        result=self.audit(obs,build_inline_candidates(obs),report)
        self.assertFalse(result["accepted"])
        self.assertIn("INLINE_FORMULA_BACKEND_RECEIPT_INVALID",{i["code"]for i in result["issues"]})

    def test_report_immutable_receipt_and_terminal_event_are_required(self):
        obs,candidates,report=self.collect()
        with closing(sqlite3.connect(self.work/"inline-formula.sqlite3"))as db:
            db.execute("DELETE FROM events WHERE event_id=?",(report["payload"]["terminal_event_id"],));db.commit()
        self.assertFalse(self.audit(obs,candidates,report)["accepted"])

    def test_extra_foreign_started_event_cannot_be_covered_by_coordinated_report_counts(self):
        obs,candidates,report=self.collect()
        with closing(sqlite3.connect(self.work/"inline-formula.sqlite3"))as db:
            # A false current-run event is not an additional declared source call.
            db.execute("INSERT INTO events(run_id,call_id,attempt_id,kind,details_json,created_at)VALUES(?,?,?,?,?,?)",
                (report["payload"]["run_id"],"foreign-call","foreign-attempt","STARTED","{}","SYNTHETIC_TEST"));db.commit()
        report["payload"]["counts"]["new_attempts"]+=1
        self.persist_rebound_report(obs,report)
        result=self.audit(obs,candidates,report)
        self.assertFalse(result["accepted"])
        self.assertIn("INLINE_FORMULA_RUN_ATTEMPT_SCOPE_MISMATCH",{i["code"]for i in result["issues"]})

    def test_bad_input_rejects_without_running_anything(self):
        result=audit_inline_formula({}, {}, {}, {}, self.root/"missing",line_ids=["missing"],workdir=self.work,report={})
        self.assertFalse(result["payload"]["accepted"])


if __name__=="__main__":unittest.main()
