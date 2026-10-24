import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from annotation.recognition.baseline import digest
from annotation.recognition import offline,pipeline_quality,question_quality


ROOT=Path(__file__).resolve().parents[1]
OBSERVATION=ROOT/"tests/fixtures/book46007447/viewer13-observation-v1.zip"
SOURCE_ZIP=ROOT/"handoffs/b/46007447/source-increment-viewer13-20261017.zip"


def _group(group_id,kind,path,line_numbers,segments,*,printed=None,parent=None,material=None,label=None,
           response=None,counting="NOT_A_QUESTION",spanning=()):
    return {"group_id":group_id,"kind":kind,"section_path":path,
            "ordered_line_ids":[f"viewer-13/ocr/{i}" for i in line_numbers],
            "flow_segments":[{"column":column,"line_ids":[f"viewer-13/ocr/{i}" for i in ids]}
                             for column,ids in segments],
            "spanning_line_ids":[f"viewer-13/ocr/{i}" for i in spanning],
            "printed_number":printed,"parent_group_id":parent,"material_id":material,"label":label,
            "response_kind":response,"counting_status":counting,"reason":"explicit model-reviewed source partition"}


def fixture(directory):
    with zipfile.ZipFile(OBSERVATION) as archive:
        recognition=json.loads(archive.read("recognition.json"))
        object_name="recognition-objects/"+recognition["payload"]["bundle"]["path"].split("/")[-1]
        baseline=json.loads(archive.read(object_name))
        source=json.loads(archive.read("source.json"))
        review=json.loads(archive.read("review.json"))
    with zipfile.ZipFile(SOURCE_ZIP) as archive:
        image=archive.read("source/46007447_page_12.jpg")
    source_dir=directory/"source"; source_dir.mkdir()
    (source_dir/"46007447_page_12.jpg").write_bytes(image)
    (source_dir/"source.json").write_text(json.dumps(source,ensure_ascii=False),encoding="utf-8")
    lines=copy.deepcopy(baseline["payload"]["pages"][0]["ocr_lines"])
    for index,line in enumerate(lines): line["line_id"]=f"viewer-13/ocr/{index}"
    question_path=["第一章 勾股定理","1 探索勾股定理","第2课时 勾股定理的验证与应用"]
    material_path=["第一章 勾股定理","阅读材料"]
    material="viewer13-reading-material"
    groups=[
        _group("q8","QUESTION",question_path,[1,3,4,6,7],[(0,[1,3,4,6,7])],printed="8",counting="PRINTED_TOP_LEVEL"),
        _group("q8-variant","VARIANT",question_path,[0,2,5],[(1,[0,2,5])],printed="8:variant",parent="q8",counting="UNKNOWN"),
        _group("material-title","MATERIAL_TITLE",material_path,[9,8],[(0,[9]),(1,[8])],material=material,spanning=[8]),
        _group("material-body","MATERIAL_BODY",material_path,[11,13,14,15,17,19,21,22,23,25,26,27,28,30],[(0,[11,13,14,15,17,19,21,22,23,25,26,27,28,30])],material=material),
        _group("figure-labels","FIGURE_LABELS",material_path,[24,33,32,35,37],[(0,[24,33,32,35,37])],material=material),
        _group("task-heading","TASK_SECTION_HEADING",material_path,[40],[(0,[40])],material=material),
        _group("task-1","TASK",material_path,[41,42,43,44,45,10,12,16],[(0,[41,42,43,44,45]),(1,[10,12,16])],material=material,label="(1)",response="UNKNOWN",counting="UNKNOWN"),
        _group("task-2","TASK",material_path,[18,20],[(1,[18,20])],material=material,label="(2)",response="UNKNOWN",counting="UNKNOWN"),
        _group("task-3","TASK",material_path,[29,31,34,36,38,39],[(1,[29,31,34,36,38,39])],material=material,label="(3)",response="UNKNOWN",counting="UNKNOWN"),
        _group("page-decoration","EXCLUDE",material_path,[46,47],[(1,[46,47])],counting="EXCLUDED")]
    reviewed={"policy":"EXACT_SOURCE_PARTITION/0.1","source_sha256":source["assets"][0]["sha256"],
              "source_size":[source["assets"][0]["width"],source["assets"][0]["height"]],"cut_x":611,
              "baseline_ref":{key:baseline[key] for key in ("artifact_id","revision","content_hash")},
              "baseline_producer":baseline["producer"],"expected_line_count":48,"review_kind":"MODEL_DRAFT",
              "verification_status":"UNVERIFIED","line_snapshots":[{"line_id":v["line_id"],"text":v["text"],"bbox":v["bbox"]} for v in lines],
              "groups":groups}
    context={"schema_version":"b-context-trial/0.2","artifact_id":"46007447-viewer13-context-v2",
             "book_id":source["book_id"],"scope_id":source["scope_id"],"pages":{"viewer-13":{
                 "sha256":source["assets"][0]["sha256"],"role":"question","windows":[
                     {"column":0,"y_range":[55,535],"path":question_path},{"column":0,"y_range":[540,1640],"path":material_path},
                     {"column":1,"y_range":[55,535],"path":question_path},{"column":1,"y_range":[540,1640],"path":material_path}],
                 "reviewed_layout":reviewed}},"reference_quality":"MODEL_VISUAL_DEVELOPMENT_REVIEW",
             "provenance":"Explicit model draft over the frozen 48-row OCR; not human review."}
    return source_dir/"source.json",baseline,context,review


class Viewer13ReviewedLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.source,self.baseline,self.context,self.review=fixture(self.root)

    def tearDown(self): self.temp.cleanup()

    def products(self):
        evidence=offline.refine(self.source,self.baseline,self.context)
        graph=offline.assemble(evidence)
        check=offline.quality_check(evidence,graph,self.review)
        return evidence,graph,check

    def test_explicit_structure_preserves_all_ocr_and_remains_hold(self):
        evidence,graph,check=self.products()
        self.assertEqual((evidence["schema_version"],graph["schema_version"],check["schema_version"]),
                         ("b-evidence-trial/0.4","b-graph-trial/0.9","b-check-trial/0.9"))
        self.assertEqual(len(evidence["payload"]["pages"][0]["ocr_lines"]),48)
        self.assertEqual(len(graph["payload"]["questions"]),2)
        self.assertEqual(len(graph["payload"]["shared_materials"]),1)
        self.assertEqual(len(graph["payload"]["shared_materials"][0]["tasks"]),3)
        self.assertEqual(len(graph["payload"]["question_source_coverage"]),48)
        self.assertEqual(check["payload"]["decision"],"HOLD")
        self.assertEqual(graph["payload"]["shared_materials"][0]["title"],
                         "漫话勾股世界\n教材P6“阅读·思考”变式")
        self.assertEqual([v["evidence_refs"][0] for v in graph["payload"]["shared_materials"][0]["tasks"][0]["fragments"]],
                         [f"viewer-13/ocr/{i}" for i in [41,42,43,44,45,10,12,16]])

    def test_producer_rejects_partition_and_binding_attacks(self):
        attacks=[]
        def case(change):
            value=copy.deepcopy(self.context); change(value["pages"]["viewer-13"]["reviewed_layout"]); attacks.append(value)
        case(lambda r:r["groups"][6]["ordered_line_ids"].__setitem__(0,"viewer-13/ocr/42"))
        case(lambda r:r["groups"][6]["flow_segments"].reverse())
        case(lambda r:r["groups"][5].update(kind="TASK",label="(1)",response_kind="UNKNOWN",counting_status="UNKNOWN"))
        case(lambda r:r["baseline_ref"].update(content_hash="0"*64))
        case(lambda r:r.update(verification_status="VERIFIED"))
        case(lambda r:r.update(unexpected=True))
        for attacked in attacks:
            with self.subTest(attacked=digest(attacked)),self.assertRaises(ValueError):
                offline.refine(self.source,self.baseline,attacked)
        reordered=copy.deepcopy(self.baseline)
        reordered["payload"]["pages"][0]["ocr_lines"][0:2]=reversed(reordered["payload"]["pages"][0]["ocr_lines"][0:2])
        reordered["content_hash"]=digest(reordered["payload"])
        with self.assertRaises(ValueError): offline.refine(self.source,reordered,self.context)

    def test_independent_consumer_rejects_context_and_graph_claim_attacks(self):
        evidence,graph,_=self.products()
        issues=[]
        units=pipeline_quality._source_evidence(evidence,json.loads(self.source.read_text(encoding="utf-8")),self.context,
                                                lambda code,**kw:issues.append(code),self.source)
        self.assertEqual(issues,[])
        attacks=[]
        missing=copy.deepcopy(graph); missing["payload"].pop("shared_materials"); attacks.append(missing)
        unknown=copy.deepcopy(graph); unknown["payload"]["shared_materials"][0]["unknown"]=True; attacks.append(unknown)
        verified=copy.deepcopy(graph); verified["payload"]["shared_materials"][0]["verification_status"]="VERIFIED"; attacks.append(verified)
        promoted=copy.deepcopy(graph); promoted["payload"]["questions"][1]["parent_question_id"]=None; attacks.append(promoted)
        task_promoted=copy.deepcopy(graph); task_promoted["payload"]["shared_materials"][0]["tasks"][0]["counting_status"]="PRINTED_TOP_LEVEL"; attacks.append(task_promoted)
        for attacked in attacks:
            attacked["content_hash"]=digest(attacked["payload"]); found=[]
            pipeline_quality._graph_sources(evidence,attacked,units,lambda code,**kw:found.append(code))
            self.assertTrue(found)

    def test_independent_consumer_derives_entity_ids_and_rejects_coordinated_rebinding(self):
        evidence,graph,_=self.products()
        units={v["line_id"]:(evidence["payload"]["pages"][0],v) for v in evidence["payload"]["pages"][0]["ocr_lines"]}
        attacked=copy.deepcopy(graph); material=attacked["payload"]["shared_materials"][0]
        old_material=material["material_id"]; material["material_id"]="forged-material"
        replacements={}
        for index,task in enumerate(material["tasks"],1):
            replacements[task["task_id"]]=f"forged-task-{index}"
            task["task_id"]=f"forged-task-{index}"; task["material_id"]="forged-material"
        for row in attacked["payload"]["question_source_coverage"]:
            if row["owner_id"]==old_material: row["owner_id"]="forged-material"
            elif row["owner_id"] in replacements: row["owner_id"]=replacements[row["owner_id"]]
        attacked["content_hash"]=digest(attacked["payload"])
        check=offline.quality_check(evidence,attacked,self.review)
        graph_issues=[]; quality_issues=[]
        pipeline_quality._graph_sources(evidence,attacked,units,lambda code,**kw:graph_issues.append(code))
        pipeline_quality._quality_bindings(evidence,attacked,check,self.review,lambda code,**kw:quality_issues.append(code))
        self.assertTrue(graph_issues)
        self.assertIn("PIPELINE_QUALITY_STRUCTURED_SCOPE_MISMATCH",quality_issues)

    def test_independent_consumer_rejects_graph_and_check_self_approval_fields(self):
        evidence,graph,check=self.products()
        units={v["line_id"]:(evidence["payload"]["pages"][0],v) for v in evidence["payload"]["pages"][0]["ocr_lines"]}
        graph_attacks=[]
        value=copy.deepcopy(graph); value["payload"]["selection_status"]="VERIFIED"; graph_attacks.append(value)
        value=copy.deepcopy(graph); value["payload"]["platform_actions"]=[{"action":"PUBLISH"}]; graph_attacks.append(value)
        value=copy.deepcopy(graph); value["payload"]["questions"][0]["flags"].append("HUMAN_VERIFIED"); graph_attacks.append(value)
        value=copy.deepcopy(graph); value["payload"]["shared_materials"][0]["flags"].remove("FIGURE_EXTENT_UNVERIFIED"); graph_attacks.append(value)
        value=copy.deepcopy(graph); value["payload"]["shared_materials"][0]["tasks"][0]["flags"].remove("FIGURE_EXTENT_UNVERIFIED"); graph_attacks.append(value)
        for attacked in graph_attacks:
            attacked["content_hash"]=digest(attacked["payload"]); found=[]
            pipeline_quality._graph_sources(evidence,attacked,units,lambda code,**kw:found.append(code))
            self.assertTrue(found)
        attacked=copy.deepcopy(check)
        attacked["payload"].update(accepted=True,business_acceptance=True,transcription_verified=True,
                                   platform_actions=[{"action":"PUBLISH"}])
        attacked["content_hash"]=digest(attacked["payload"]); found=[]
        pipeline_quality._quality_bindings(evidence,graph,attacked,self.review,lambda code,**kw:found.append(code))
        self.assertIn("PIPELINE_QUALITY_PAYLOAD_SHAPE_MISMATCH",found)

    def test_reviewed_spanning_mode_is_exclusive_to_bound_evidence04(self):
        evidence,graph,_=self.products()
        findings,_=question_quality.audit_questions(evidence,graph,self.review,scope_key=offline.scope_key,
                                                     scalar_issues=offline.scalar_issues)
        self.assertNotIn("UNRESOLVED_LAYOUT",{v["code"] for v in findings})
        legacy=copy.deepcopy(evidence); legacy["schema_version"]="b-evidence-trial/0.2"
        legacy["payload"]["context"]["schema_version"]="b-context-trial/0.1"
        legacy["payload"]["context"]["pages"]["viewer-13"].pop("reviewed_layout")
        legacy["payload"]["pages"][0].pop("reviewed_layout_receipt")
        findings,_=question_quality.audit_questions(legacy,graph,self.review,scope_key=offline.scope_key,
                                                     scalar_issues=offline.scalar_issues)
        self.assertIn("UNRESOLVED_LAYOUT",{v["code"] for v in findings})
        invalid=copy.deepcopy(evidence); invalid["payload"]["pages"][0]["reviewed_layout_receipt"].pop("reviewed_layout_hash")
        findings,_=question_quality.audit_questions(invalid,graph,self.review,scope_key=offline.scope_key,
                                                     scalar_issues=offline.scalar_issues)
        self.assertIn("UNRESOLVED_LAYOUT",{v["code"] for v in findings})

    def test_exact_route_rejects_graph09_in_legacy_consumer(self):
        evidence,graph,check=self.products()
        forged=copy.deepcopy(evidence); forged["schema_version"]="b-evidence-trial/0.3"
        forged["content_hash"]=digest(forged["payload"])
        found=[]; units={v["line_id"]:(evidence["payload"]["pages"][0],v) for v in evidence["payload"]["pages"][0]["ocr_lines"]}
        pipeline_quality._graph_sources(forged,graph,units,lambda code,**kw:found.append(code))
        self.assertIn("PIPELINE_GRAPH_INVALID",found)
        self.assertEqual(check["payload"]["decision"],"HOLD")

    def test_v3_context_and_evidence_draft_claims_are_exact(self):
        context_attacks=[]
        value=copy.deepcopy(self.context); value["pages"]["viewer-13"]["reviewed_layout"]["groups"][0]["printed_number"]="9"; context_attacks.append(value)
        value=copy.deepcopy(self.context); value["pages"]["viewer-13"]["reviewed_layout"]["groups"][6]["response_kind"]="HUMAN_GRADED"; context_attacks.append(value)
        value=copy.deepcopy(self.context); value["reference_quality"]="HUMAN_VERIFIED"; context_attacks.append(value)
        value=copy.deepcopy(self.context); value["provenance"]="HUMAN APPROVED"; context_attacks.append(value)
        for attacked in context_attacks:
            with self.subTest(context=digest(attacked)),self.assertRaises(ValueError):
                offline.refine(self.source,self.baseline,attacked)
        evidence,_,_=self.products(); source=json.loads(self.source.read_text(encoding="utf-8"))
        evidence_attacks=[]
        value=copy.deepcopy(evidence); value["payload"]["pages"][0]["layout"]["verified"]=True; evidence_attacks.append(value)
        value=copy.deepcopy(evidence); value["payload"]["pages"][0]["reviewed_layout_receipt"]["human_verified"]=True; evidence_attacks.append(value)
        value=copy.deepcopy(evidence); value["payload"]["human_verified"]=True; evidence_attacks.append(value)
        for attacked in evidence_attacks:
            attacked["content_hash"]=digest(attacked["payload"]); found=[]
            pipeline_quality._source_evidence(attacked,source,self.context,lambda code,**kw:found.append(code),self.source)
            self.assertTrue(found)

    def test_v3_graph_order_matching_and_source_fields_are_exact(self):
        evidence,graph,_=self.products()
        units={v["line_id"]:(evidence["payload"]["pages"][0],v) for v in evidence["payload"]["pages"][0]["ocr_lines"]}
        attacks=[]
        value=copy.deepcopy(graph); value["payload"]["questions"].reverse(); attacks.append(value)
        value=copy.deepcopy(graph); value["payload"]["shared_materials"][0]["tasks"].reverse(); attacks.append(value)
        value=copy.deepcopy(graph); value["payload"]["questions"][0]["type_candidate"]={"question_type":"open_response","human_verified":True}; attacks.append(value)
        value=copy.deepcopy(graph); value["payload"]["shared_materials"][0]["asset_id"]="forged-asset"; attacks.append(value)
        value=copy.deepcopy(graph); value["payload"]["shared_materials"][0]["section_path"]=["FORGED"]; attacks.append(value)
        value=copy.deepcopy(graph); value["payload"]["matching"]="HUMAN_APPROVED"; attacks.append(value)
        value=copy.deepcopy(graph); value["payload"]["unmatched_answer_ids"]=["approved-answer"]; attacks.append(value)
        value=copy.deepcopy(graph); value["payload"]["issues"]=[{"code":"APPROVED"}]; attacks.append(value)
        for attacked in attacks:
            attacked["content_hash"]=digest(attacked["payload"]); found=[]
            pipeline_quality._graph_sources(evidence,attacked,units,lambda code,**kw:found.append(code))
            self.assertTrue(found)

    def test_v3_check_and_review_are_exact_model_draft_records(self):
        evidence,graph,check=self.products()
        attacks=[]
        value=copy.deepcopy(check); value["payload"]["reason"]="APPROVED FOR PUBLISH"; attacks.append(value)
        value=copy.deepcopy(check); value["payload"]["summary"].update(accepted=True,business_acceptance=True); attacks.append(value)
        value=copy.deepcopy(check); value["payload"]["issues"][0].update(severity="INFO",blocks=[],suggested_strategy="AUTO_PUBLISH"); attacks.append(value)
        value=copy.deepcopy(check); value["payload"]["issues"][0]["accepted"]=True; attacks.append(value)
        value=copy.deepcopy(check); value["payload"]["issues"][0]["code"]="APPROVED"; attacks.append(value)
        for attacked in attacks:
            attacked["content_hash"]=digest(attacked["payload"]); found=[]
            pipeline_quality._quality_bindings(evidence,graph,attacked,self.review,lambda code,**kw:found.append(code))
            self.assertIn("PIPELINE_QUALITY_STRUCTURED_REPORT_MISMATCH",found)
        for field in ("reference_quality","provenance"):
            attacked=copy.deepcopy(self.review); attacked[field]="HUMAN APPROVED"
            with self.subTest(field=field),self.assertRaises(ValueError):
                offline.quality_check(evidence,graph,attacked)


if __name__ == "__main__": unittest.main()
