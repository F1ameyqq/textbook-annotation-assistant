"""R2 fixed defects, neighbor contradictions, and legitimate missing-page intent."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from annotation.contracts import load_bundle
from annotation.source.static import StaticSourceError, load_static_bundle

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("a01_r2_cases",ROOT/"examples/a01/R2/cases.py")
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)


class SourceR2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="a01-R2-test-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.next_id = 0

    def package(self,book="46006966",version="R1"):
        self.next_id += 1
        base = ROOT/("examples/a01/bundles" if version == "legacy" else "examples/a01/R1/bundles")/book
        return cases.Package(base,self.folder/str(self.next_id))

    def rejects(self,package,code):
        path = package.seal()
        load_bundle(path,verify_assets=True)
        with self.assertRaises(StaticSourceError) as error:
            load_static_bundle(path,expected_book_id=package.source["book_id"])
        self.assertEqual(error.exception.code,code)
        self.assertTrue(error.exception.location)

    def accepts(self,package):
        path = package.seal()
        public = load_bundle(path,verify_assets=True)
        self.assertEqual(load_static_bundle(path,expected_book_id=package.source["book_id"]),public)
        return public

    def test_primary_five_resealed_counterexamples(self):
        for case,code in (("P01","SCOPE_PARTITION"),("N14","SCOPE_PARTITION"),("P02","BOOK_CONFLICT"),
                          ("P03","MAPPING_CONFLICT"),("P04","OBSERVATION_SOURCE")):
            book = "46006966" if case in ("P01","N14") else "46007447"
            base = ROOT/"examples/a01/R1/bundles"/book
            path = cases.mutated(base,self.folder/case,case)
            load_bundle(path,verify_assets=True)
            with self.subTest(case=case),self.assertRaises(StaticSourceError) as error:
                load_static_bundle(path,expected_book_id=book)
            self.assertEqual(error.exception.code,code)
            self.assertTrue(error.exception.location)

    def test_scope_index_types_duplicates_and_metadata_bounds(self):
        fields = ("selected_source_indices","selected_missing_source_indices","outside_selected_scope_unacquired_indices")
        for book,count in (("46006966",250),("46007447",214)):
            for field in fields:
                for values in ([0,0],[-1],[count],[0.0],[False],None):
                    with self.subTest(book=book,field=field,values=values):
                        package = self.package(book)
                        package.sidecar("provenance.json",lambda p:p.update({field:values}))
                        self.rejects(package,"SCOPE_INDICES")

    def test_incomplete_and_overlapping_scope_partitions(self):
        for book in ("46006966","46007447"):
            for field,mutate in (
                ("selected_source_indices",lambda p:p.update(selected_source_indices=[])),
                ("selected_source_indices",lambda p:p["selected_source_indices"].pop()),
                ("outside_selected_scope_unacquired_indices",lambda p:p.update(outside_selected_scope_unacquired_indices=[])),
                ("outside_selected_scope_unacquired_indices",lambda p:p["outside_selected_scope_unacquired_indices"].pop()),
                ("selected_missing_source_indices",lambda p:p["selected_missing_source_indices"].append(p["selected_source_indices"][0])),
            ):
                with self.subTest(book=book,field=field):
                    package = self.package(book)
                    package.sidecar("provenance.json",mutate)
                    self.rejects(package,"SCOPE_PARTITION")

    def test_public_expected_counts_and_scalar_count_types(self):
        for book in ("46006966","46007447"):
            package = self.package(book)
            package.source["payload"]["pages_expected"].append("expected-undeclared-page")
            self.rejects(package,"SCOPE_COUNT")
            for key in ("metadata_page_count","acquired_unique_images"):
                with self.subTest(book=book,key=key):
                    package = self.package(book)
                    package.sidecar("provenance.json",lambda p:p.update({key:float(p[key])}))
                    self.rejects(package,"SCOPE_COUNT")

    def test_valid_nonzero_missing_and_empty_outside_are_preserved(self):
        for book,count in (("46006966",250),("46007447",214)):
            for full_scope in (False,True):
                with self.subTest(book=book,full_scope=full_scope):
                    package = self.package(book)
                    original_assets = list(package.source["payload"]["assets"])
                    p = cases.read(package.folder/"provenance.json")
                    acquired = {m["source_index"] for m in p["mappings"]}
                    missing = [i for i in range(count) if i not in acquired] if full_scope else [0,count-1]
                    package.select_missing(missing)
                    result = self.accepts(package)
                    current = cases.read(package.folder/"provenance.json")
                    self.assertEqual(current["selected_missing_source_indices"],missing)
                    self.assertEqual(len(result.artifacts[0].payload.pages_expected),len(acquired)+len(missing))
                    self.assertEqual(result.artifacts[0].payload.assets,[a for a in load_bundle(ROOT/"examples/a01/R1/bundles"/book/"exchange.json").artifacts[0].payload.assets])
                    self.assertEqual(package.source["payload"]["assets"],original_assets)
                    self.assertEqual(current["outside_selected_scope_unacquired_indices"] == [],full_scope)
                    self.assertFalse(cases.read(package.folder/"limitations.json")["coverage_eligible"])

    def test_legacy_and_r1_two_book_normal_empty_missing_still_loads(self):
        for version in ("legacy","R1"):
            for book in ("46006966","46007447"):
                with self.subTest(version=version,book=book):
                    package = self.package(book,version)
                    self.accepts(package)
                    self.assertEqual(cases.read(package.folder/"provenance.json")["selected_missing_source_indices"],[])

    def test_historical_url_book_and_index_binding_neighbors(self):
        for new_url,code in (
            ("https://archive.example.invalid/upload_images/46007447/46006966_page_13.jpg","BOOK_CONFLICT"),
            ("https://archive.example.invalid/upload_images/46006966/46007447_page_13.jpg","BOOK_CONFLICT"),
            ("https://archive.example.invalid/upload_images/46007447/46007447_page_12.jpg","MAPPING_CONFLICT"),
            ("https://archive.example.invalid/upload_images/46007447/46007447_page_14.jpg","MAPPING_CONFLICT"),
            ("upload_images/46007447/46007447_page_13.jpg","SOURCE_URL"),
            ("ftp://archive.example.invalid/upload_images/46007447/46007447_page_13.jpg","SOURCE_URL"),
            ("not a URL","SOURCE_URL"),(None,"SOURCE_URL"),
        ):
            with self.subTest(url=new_url):
                package = self.package("46007447")
                package.page_url(lambda p:p.update(image=new_url))
                self.rejects(package,code)
        package = self.package("46007447")
        package.page_url(lambda p:p.update(page_index="13"))
        self.rejects(package,"MAPPING_CONFLICT")

    def test_legal_archived_url_host_text_preserved_without_network_trust(self):
        for scheme in ("https","http"):
            package = self.package("46007447")
            url = scheme+"://archive.example.invalid/upload_images/46007447/46007447_page_13.jpg"
            package.page_url(lambda p:p.update(image=url))
            result = self.accepts(package)
            self.assertEqual(cases.read(package.folder/"history/00-independent-source-page14.json")["data"]["pages"][0]["image"],url)
            self.assertEqual([a.kind for a in result.artifacts],["SourceBundle"])

    def test_observation_index_identity_digest_and_source_neighbors(self):
        for mutate,code in (
            (lambda p:p["observation"].update(observation_index_source=None),"OBSERVATION_SOURCE"),
            (lambda p:p["observation"]["observation_index_source"].update(archive_path="missing-index.json"),"OBSERVATION_SOURCE"),
            (lambda p:p["observation"]["observation_index_source"].update(archive_path="../outside.json"),"SOURCE_PATH"),
            (lambda p:p["observation"]["observation_index_source"].update(sha256="not-a-digest"),"SOURCE_DIGEST"),
            (lambda p:p["observation"].update(source="other-boundary.json"),"OBSERVATION_SOURCE"),
        ):
            with self.subTest(code=code):
                package = self.package("46007447")
                package.sidecar("provenance.json",mutate)
                self.rejects(package,code)
        package = self.package("46007447")
        integrity = cases.read(package.folder/"input-integrity.json")
        other = next(i for i in integrity["inputs"] if i["archive_path"].endswith("independent-book.json"))
        package.sidecar("provenance.json",lambda p:p["observation"].update(observation_index_source={"archive_path":other["archive_path"],"sha256":other["before_sha256"]}))
        self.rejects(package,"OBSERVATION_SOURCE")
        package = self.package("46006966")
        package.sidecar("provenance.json",lambda p:p["observation"].update(source="other-session.json"))
        self.rejects(package,"OBSERVATION_SOURCE")

    def test_n15_precision_label_remains_a_documented_non_authentication_field(self):
        package = self.package()
        package.sidecar("provenance.json",lambda p:p["observation"].update(precision="LIVE_OBSERVATION"))
        result = self.accepts(package)
        self.assertEqual([a.kind for a in result.artifacts],["SourceBundle"])
        self.assertFalse(cases.read(package.folder/"limitations.json")["coverage_eligible"])


if __name__ == "__main__":
    unittest.main()
