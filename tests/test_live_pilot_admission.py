"""A11 new fixed admission cases; never import or execute historical business drivers."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent / "fixtures" / "live_pilot"))
from helper import HERE, case_root, request, reseal
from annotation.contracts import ContractError, validate_bundle
from annotation.delivery.live_pilot.plan import create_live_plan
from annotation.delivery.live_pilot.usense import UsenseTransport, build_offline_command, validate_offline_command
from annotation.quality.live_pilot import PilotError, check_input, check_target, global_order


class AdmissionTests(unittest.TestCase):
    def assert_code(self, code, callable_):
        with self.assertRaises(PilotError) as caught: callable_()
        self.assertEqual(caught.exception.code, code)

    def test_T1_valid_and_bound_source(self):
        req = request()
        adm = check_input(req, HERE, offline=True)
        self.assertEqual(len(adm.questions), 2)
        for key, value in (("sha256", "0"*64), ("width", 99), ("viewer_page", 2), ("save_page", -1)):
            bad = copy.deepcopy(req)
            bad["bindings"]["a11-page"][key] = value
            self.assert_code("SOURCE_MAPPING", lambda: check_input(bad, HERE, offline=True))
        bad = copy.deepcopy(req)
        bad["approval"]["questions"][0]["question_id"] = "not-authorized"
        self.assert_code("MANIFEST_IDENTITY_ORDER", lambda: check_input(bad, HERE, offline=True))
        bad = copy.deepcopy(req)
        bad["approval"]["questions"][0]["input_hash"] = "0"*64
        self.assert_code("APPROVAL_CONTENT_BINDING", lambda: check_input(bad, HERE, offline=True))

    def test_T1_manifest_scope(self):
        for size in (0, 6):
            req = request()
            req["approval"]["questions"] = [dict(req["approval"]["questions"][0], question_id="fake-"+str(i)) for i in range(size)]
            self.assert_code("MANIFEST_SIZE_OR_DUPLICATE", lambda: check_input(req, HERE, offline=True))
        for field, value in (("printed_number", "22"), ("platform_question_id", "old-a")):
            req = request()
            graph = next(a for a in req["bundle"]["artifacts"] if a["kind"] == "QuestionGraph")
            graph["payload"]["questions"][0]["external_refs"][field] = value
            reseal(req)
            self.assert_code("EXISTING_OR_Q22", lambda: check_input(req, HERE, offline=True))
        req = request()
        req["approval"]["purpose"] = "A07_Q1_OFFLINE"
        self.assert_code("NEW_APPROVAL_REQUIRED", lambda: check_input(req, HERE, offline=True))

    def test_T2_resealed_stale_option_roles(self):
        req = request()
        req["bundle"]["policies"][0]["role_mapping"]["option"] = "Q"
        reseal(req)
        validate_bundle(req["bundle"], asset_root=HERE)
        # A stale plan and copied readback can agree exactly. Neither overrides R02.
        stale_plan = ["Q", "Q", "Q", "Q", "Q", "A"]
        stale_readback = list(stale_plan)
        self.assertEqual(stale_plan, stale_readback)
        self.assert_code("AUTHORITATIVE_OPTION_ROLE", lambda: check_input(req, HERE, offline=True))

    def test_T2_unsupported_shapes(self):
        for qtype in ("seven_choice", "combination", "free_response"):
            req = request()
            graph = next(a for a in req["bundle"]["artifacts"] if a["kind"] == "QuestionGraph")
            graph["payload"]["questions"][0]["question_type"] = qtype
            reseal(req)
            self.assert_code("UNSUPPORTED_QUESTION", lambda: check_input(req, HERE, offline=True))
        for role in ("shared_material", "explanation", "option"):
            req = request()
            graph = next(a for a in req["bundle"]["artifacts"] if a["kind"] == "QuestionGraph")
            graph["payload"]["fragments"][0]["role"] = role
            reseal(req)
            self.assert_code("SIX_FRAME_SEMANTICS", lambda: check_input(req, HERE, offline=True))

    def test_T3_c01_integrity_and_observed_relabel(self):
        req = request()
        req["bundle"]["artifacts"][0]["payload"]["assets"][0]["width"] = 99
        with self.assertRaises(ContractError): check_input(req, HERE, offline=True)
        req = request()
        req["bundle"]["artifacts"][0]["payload"]["assets"][0]["width"] = 99
        reseal(req)
        with self.assertRaises(ContractError) as caught: check_input(req, HERE, offline=True)
        self.assertIn("IMAGE_DIMENSIONS", str(caught.exception))
        req = request()
        for a in req["bundle"]["artifacts"]: a["producer"]["evidence_mode"] = "OBSERVED"
        reseal(req)
        with self.assertRaises(ContractError): check_input(req, HERE, offline=True)

    def test_T3_capability_and_real_block(self):
        for variant in ("missing_frame", "missing_session", "old_version"):
            req = request()
            snap = next(a for a in req["bundle"]["artifacts"] if a["kind"] == "PlatformSnapshot")
            if variant == "old_version": snap["payload"]["capabilities"][0]["platform_version"] = "old"
            else:
                name = "frame_readback" if variant == "missing_frame" else "same_session_handoff"
                snap["payload"]["capabilities"] = [c for c in snap["payload"]["capabilities"] if c["name"] != name]
            reseal(req)
            adm = check_input(req, HERE, offline=True)
            self.assert_code("CAPABILITY_VERSION" if variant == "old_version" else "CAPABILITY_UNVERIFIED",
                             lambda: create_live_plan(adm, req, "a11-new-alpha", req["observation"]))
        req = request()
        snap = next(a for a in req["bundle"]["artifacts"] if a["kind"] == "PlatformSnapshot")
        snap["payload"]["capabilities"][0]["evidence_refs"] = []
        with self.assertRaises(Exception): reseal(req)
        self.assert_code("NEW_APPROVAL_REQUIRED", lambda: check_input(request(), HERE))
        adapter = UsenseTransport(wire_profile={"status": "VERIFIED", "policy": "JOINT_CONFIRMED"})
        self.assert_code("LIVE_TEXT_WIRE_UNVERIFIED", lambda: adapter.send_once({}))
        self.assert_code("LIVE_READBACK_CODEC_UNAVAILABLE", lambda: adapter.observe("get"))

    def test_T4_global_order_and_target_changes(self):
        req = request()
        adm = check_input(req, HERE, offline=True)
        plan = create_live_plan(adm, req, "a11-new-alpha", req["observation"])
        self.assertEqual(plan["insert_after_order"], 9)
        self.assertEqual(plan["action"]["expected_after"]["platform_order"], 10)
        for variant in ("duplicate_order", "directory_drift", "already_saved"):
            obs = copy.deepcopy(req["observation"])
            if variant == "duplicate_order": obs["view"]["target"]["questions"][1]["platform_order"] = 2
            if variant == "directory_drift": obs["directory_details"][0]["label"] = "changed"
            if variant == "already_saved": obs["view"]["internal_bindings"]["a11-new-alpha"] = "old-a"
            code = {"duplicate_order": "GLOBAL_ORDER_AMBIGUOUS", "directory_drift": "TARGET_CHANGED", "already_saved": "ALREADY_SAVED"}[variant]
            self.assert_code(code, lambda: check_target(adm, req, obs, expected=req["observation"] if variant == "directory_drift" else None))

    def test_T8_forbidden_commands_and_cli(self):
        req = request()
        plan = create_live_plan(check_input(req, HERE, offline=True), req, "a11-new-alpha", req["observation"])
        for field, value in (("ocr", True), ("submit", True), ("deletes", ["old-rect"]),
                             ("book_id", "46006966"), ("uploads", ["unknown"]), ("operation", "UPDATE_FRAMES")):
            command = build_offline_command(plan)
            command[field] = value
            self.assert_code("FORBIDDEN_OPERATION", lambda: validate_offline_command(command))
        root = case_root(self._testMethodName)
        for command in ("inspect-input", "prepare", "apply", "reconcile-readonly", "report"):
            args = [sys.executable, "-m", "annotation.runtime.live_pilot", command, "--offline-fixture"]
            if command in ("inspect-input", "prepare"): args += ["--input", str(HERE/"request.json")]
            if command == "report": args += ["--journal", str(root/"empty-journal")]
            proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=20)
            (root/(command+".json")).write_text(proc.stdout, encoding="utf-8")
            data = json.loads(proc.stdout)
            self.assertEqual(proc.returncode, 2 if command in ("apply", "reconcile-readonly") else 0, proc.stderr)
            if command in ("apply", "reconcile-readonly"): self.assertEqual(data["platform_calls"], 0)


if __name__ == "__main__": unittest.main()
