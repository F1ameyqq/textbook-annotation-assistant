"""Conventional regression fixtures keep the frozen byte gate strict and local."""
import copy
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("integration_r1_preservation",ROOT/"examples/a01/R3/preservation.py")
preservation=importlib.util.module_from_spec(spec); spec.loader.exec_module(preservation)
FIXTURE=ROOT/"tests/fixtures/a01/integration-R1"


class IntegrationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="a01-i1-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)/"fixed"
        shutil.copytree(FIXTURE/"frozen",self.folder)
        self.reference=preservation.read_manifest(FIXTURE/"reference.json")

    def test_fixed_original_accepts_only_its_explicit_text_representations(self):
        original=self.folder/"tests/test_contracts.py"
        raw=original.read_bytes()
        for data,expected in ((raw,True),(raw.replace(b"\n",b"\r\n"),True),
                              (raw.replace(b"\n",b"\r\n",1),False),(raw+b"\n# actual content changed\n",False)):
            with self.subTest(expected=expected,bytes=len(data)):
                original.write_bytes(data)
                result=preservation.audit(self.folder,self.reference)
                self.assertEqual(result["passed"],expected)
                if not expected:
                    self.assertEqual(result["errors"][0]["code"],"CONTENT_MISMATCH")

    def test_unlisted_checkout_representation_is_still_rejected_for_frozen_input(self):
        path=self.folder/"examples/a01/build.py"
        path.write_bytes(path.read_bytes().replace(b"\n",b"\r\n"))
        result=preservation.audit(self.folder,self.reference)
        self.assertFalse(result["passed"])
        self.assertEqual(result["errors"][0]["path"],"examples/a01/build.py")

    def test_old_coordination_and_binary_are_immutable_only_inside_fixed_fixture(self):
        for relative in ("docs/coordination.md","tests/fixtures/contracts/normal/assets/asset-page-a1.pgm"):
            with self.subTest(path=relative):
                path=self.folder/relative; raw=path.read_bytes()
                path.write_bytes(raw+b"damage")
                result=preservation.audit(self.folder,self.reference)
                self.assertFalse(result["passed"])
                self.assertEqual(result["errors"][0]["path"],relative)
                path.write_bytes(raw)
        self.assertTrue(preservation.audit(self.folder,self.reference)["passed"])


if __name__ == "__main__":
    unittest.main()
