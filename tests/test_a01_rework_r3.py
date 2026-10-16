"""Literal URL component counterexamples and finite byte-preservation controls."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from annotation.contracts import load_bundle
from annotation.source.static import StaticSourceError, load_static_bundle
from annotation.source.static.importer import url_index

ROOT = Path(__file__).resolve().parents[1]


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


cases = module("r2_cases_for_tests_r3",ROOT/"examples/a01/R2/cases.py")
preservation = module("preservation_for_tests_r3",ROOT/"examples/a01/R3/preservation.py")
fixtures = module("fixtures_for_tests_r3",ROOT/"examples/a01/R3/fixtures.py")


class SourceR3Tests(unittest.TestCase):
    def test_component_swaps_cannot_hide_wrong_actual_path(self):
        correct = "/upload_images/46007447/46007447_page_13.jpg"
        wrong = ("/upload_images/46006966/46007447_page_13.jpg",
                 "/upload_images/46007447/46006966_page_13.jpg",
                 "/upload_images/46007447/46007447_page_172.jpg","/unrelated.jpg")
        with tempfile.TemporaryDirectory(prefix="a01-r3-url-") as folder:
            for i,(path,separator) in enumerate((p,s) for p in wrong for s in ("?echo=","#")):
                with self.subTest(path=path,separator=separator):
                    package = cases.Package(ROOT/"examples/a01/R2/bundles/46007447",Path(folder)/str(i))
                    package.page_url(lambda p:p.update(image="https://archive.example.invalid"+path+separator+correct))
                    target = package.seal(); load_bundle(target,verify_assets=True)
                    with self.assertRaises(StaticSourceError) as error:
                        load_static_bundle(target,expected_book_id="46007447")
                    self.assertEqual(error.exception.code,"SOURCE_URL_COMPONENT")
                    self.assertTrue(error.exception.location.endswith(".image"))

    def test_components_explicitly_unsupported_even_for_correct_or_empty_tail(self):
        for tail in ("?","#","?token=opaque","#view","?echo=/upload_images/46006966/46006966_page_1.jpg"):
            with self.subTest(tail=tail),self.assertRaisesRegex(StaticSourceError,"SOURCE_URL_COMPONENT"):
                url_index("https://archive.example.invalid/upload_images/46007447/46007447_page_13.jpg"+tail,"46007447","test.image")

    def test_actual_path_is_mandatory_and_direct_two_book_urls_remain_valid(self):
        for book,index in (("46006966",7),("46007447",13)):
            for scheme in ("http","https"):
                url=scheme+"://archive.example.invalid/upload_images/"+book+"/"+book+"_page_"+str(index)+".jpg"
                self.assertEqual(url_index(url,book,"test.image"),index)
        for path in ("/upload_images/46006966/46007447_page_13.jpg","/upload_images/46007447/46006966_page_13.jpg",
                     "/prefix/upload_images/46007447/46007447_page_13.jpg","/unrelated.jpg"):
            with self.subTest(path=path),self.assertRaisesRegex(StaticSourceError,"BOOK_CONFLICT"):
                url_index("https://archive.example.invalid"+path,"46007447","test.image")

    def test_exact_frozen_query_fragment_inputs_reconstruct_and_reject(self):
        with tempfile.TemporaryDirectory(prefix="a01-r3-frozen-") as folder:
            paths = fixtures.reconstruct(ROOT,"URL-official",Path(folder)/"cases")
            self.assertEqual(len(paths),2)
            for name,path in paths.items():
                load_bundle(path,verify_assets=True)
                with self.subTest(name=name),self.assertRaisesRegex(StaticSourceError,"SOURCE_URL_COMPONENT"):
                    load_static_bundle(path,expected_book_id="46007447")


class PreservationR3Tests(unittest.TestCase):
    def manifest(self,path,raw,crlf=False):
        sha = lambda data:hashlib.sha256(data).hexdigest()
        values = [dict(kind="GIT_BLOB",sha256=sha(raw),bytes=len(raw))]
        if crlf:
            other = raw.replace(b"\n",b"\r\n")
            values.append(dict(kind="FIXED_CRLF_TEXT_REPRESENTATION",sha256=sha(other),bytes=len(other)))
        return dict(reference_commit="a"*40,files=[dict(path=path,git_blob_oid="b"*40,git_sha256=sha(raw),representations=values)])

    def test_only_two_fixed_uniform_text_hashes_are_accepted(self):
        raw = b"first\nsecond\n"
        with tempfile.TemporaryDirectory(prefix="a01-r3-bytes-") as folder:
            root=Path(folder); path=root/"code.py"; reference=self.manifest("code.py",raw,True)
            for data,expected in ((raw,True),(b"first\r\nsecond\r\n",True),(b"first\nsecond\r\n",False),
                                  (b"changed\nsecond\n",False),(b"first\nsecond\n ",False)):
                path.write_bytes(data)
                self.assertEqual(preservation.audit(root,reference)["passed"],expected)

    def test_history_and_binary_bytes_have_no_implicit_text_tolerance(self):
        with tempfile.TemporaryDirectory(prefix="a01-r3-exact-") as folder:
            root=Path(folder)
            for name,raw,changed in (("evidence.json",b'{"source": 1}\n',b'{"source": 1}\r\n'),
                                     ("image.jpg",b"\xff\xd8binary\xff\xd9",b"\xff\xd8changed\xff\xd9")):
                path=root/name; reference=self.manifest(name,raw)
                path.write_bytes(raw); self.assertTrue(preservation.audit(root,reference)["passed"])
                path.write_bytes(changed); result=preservation.audit(root,reference)
                self.assertFalse(result["passed"]); self.assertEqual(result["errors"][0]["code"],"CONTENT_MISMATCH")

    def test_disk_representation_must_not_change_during_run(self):
        raw=b"one\ntwo\n"
        with tempfile.TemporaryDirectory(prefix="a01-r3-run-") as folder:
            root=Path(folder); path=root/"code.py"; reference=self.manifest("code.py",raw,True)
            path.write_bytes(raw); before=preservation.audit(root,reference)
            path.write_bytes(raw.replace(b"\n",b"\r\n")); after=preservation.audit(root,reference)
            self.assertTrue(before["passed"] and after["passed"])
            self.assertEqual(preservation.disk_changes(before,after)[0]["code"],"DISK_CHANGED_DURING_RUN")

    def test_fixed_baseline_has_only_explicit_twenty_five_variants(self):
        ref=preservation.read_manifest(ROOT/"tests/fixtures/a01/R3/preservation-manifest.json")
        self.assertEqual(ref["reference_commit"],"c3aff9598b6705ab4122062615a13ae3774698b2")
        self.assertEqual(sum(len(e["representations"])>1 for e in ref["files"]),25)
        for e in ref["files"]:
            if e["path"].startswith(("docs/evidence/","技术证据/","原始资料/")) or "/bundles/" in e["path"]:
                self.assertEqual(len(e["representations"]),1,e["path"])
        self.assertTrue(preservation.audit(ROOT,ref)["passed"])


if __name__ == "__main__":
    unittest.main()
