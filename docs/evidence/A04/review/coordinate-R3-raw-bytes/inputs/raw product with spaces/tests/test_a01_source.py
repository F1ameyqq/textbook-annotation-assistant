"""Archive integrity, negative imports, unknown denominator and relocation tests."""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from annotation.contracts import ContractError, load_bundle, seal_artifact, validate_bundle
from annotation.source.static import StaticSourceError, import_book, load_static_bundle

ROOT = Path(__file__).resolve().parents[1]
OLD_MANIFEST = "技术证据/只读样本-46006966/source-images-complete.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path,data):
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def hashes(folder):
    return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob("*") if p.is_file()}


class StaticSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = tempfile.TemporaryDirectory(prefix="a01-tests-")
        cls.base = Path(cls.session.name)
        cls.paths = {book:import_book(ROOT,book,cls.base/book,created_at="2026-10-16T13:00:00Z")
                     for book in ("46006966","46007447")}

    @classmethod
    def tearDownClass(cls):
        cls.session.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="a01-case-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def copy_output(self,book="46006966"):
        folder = self.folder/"output"
        shutil.copytree(self.paths[book].parent,folder)
        return folder/"exchange.json"

    def copy_inputs(self):
        repo = self.folder/"repo"
        for path in self.paths.values():
            for item in read(path.parent/"input-integrity.json")["inputs"]:
                relative = item["archive_path"]
                target = repo/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                if not target.exists():
                    shutil.copy2(ROOT/relative,target)
        return repo

    def rewrite_bundle(self,path,data):
        data["artifacts"] = [seal_artifact(a) for a in data["artifacts"]]
        write(path,data)

    def rewrite_sidecar(self,path,name,mutate):
        data = read(path)
        sidecar = path.parent/name
        value = read(sidecar)
        mutate(value)
        write(sidecar,value)
        sha = hashlib.sha256(sidecar.read_bytes()).hexdigest()
        for evidence in data["evidence"]:
            if evidence["resource"]["path"] == name:
                evidence["resource"]["sha256"] = sha
        for history in data["artifacts"][0]["payload"]["history"]:
            if history["resource"]["path"] == name:
                history["resource"]["sha256"] = sha
        self.rewrite_bundle(path,data)

    def test_public_contract_consumer_and_separate_books(self):
        for book,expected,count in (("46006966",6,250),("46007447",2,214)):
            with self.subTest(book=book):
                bundle = load_bundle(self.paths[book],verify_assets=True)
                self.assertEqual(bundle,load_static_bundle(self.paths[book],expected_book_id=book))
                source = bundle.artifacts[0]
                self.assertEqual(source.book_id,book)
                self.assertEqual(len(source.payload.assets),expected)
                self.assertEqual(source.payload.metadata_page_count,count)
                self.assertEqual(source.payload.pages_expected,source.payload.pages_acquired)
                self.assertTrue(all(a.provenance == "ORIGINAL" for a in source.payload.assets))
                self.assertTrue(all(h.quality == "UNVERIFIED" for h in source.payload.history))

    def test_dedup_preserves_origins_and_only_evidenced_mapping(self):
        for book,count,origin_count,missing in (("46006966",6,10,244),("46007447",2,4,212)):
            p = read(self.paths[book].parent/"provenance.json")
            self.assertEqual(p["acquired_unique_images"],count)
            self.assertEqual(len(p["origins"]),origin_count)
            self.assertEqual(len(p["outside_selected_scope_unacquired_indices"]),missing)
            self.assertEqual(p["selected_missing_source_indices"],[])
            self.assertTrue(all(m["printed_page"] is None for m in p["mappings"]))
        old = read(self.paths["46006966"].parent/"provenance.json")
        self.assertEqual({m["source_index"]:m["viewer_page"] for m in old["mappings"]},
                         {7:8,8:9,9:10,10:None,233:234,234:None})
        self.assertEqual(old["observation"]["precision"],"DATE_ONLY")

    def test_originals_preserved_and_personal_paths_omitted(self):
        for path in self.paths.values():
            integrity = read(path.parent/"input-integrity.json")
            self.assertTrue(integrity["unchanged"])
            for item in integrity["inputs"]:
                actual = hashlib.sha256((ROOT/item["archive_path"]).read_bytes()).hexdigest()
                self.assertEqual(item["before_sha256"],actual)
                self.assertEqual(item["after_sha256"],actual)
            for item in load_bundle(path).artifacts[0].payload.history:
                if item.reason.startswith("Byte-preserved archived reference: "):
                    original = item.reason.split("Byte-preserved archived reference: ",1)[1].split(";",1)[0]
                    self.assertEqual((path.parent/item.resource.path).read_bytes(),(ROOT/original).read_bytes())
            for output in path.parent.rglob("*.json"):
                text = output.read_text(encoding="utf-8")
                self.assertNotIn("C:\\\\Users\\\\",text)
                self.assertNotIn("D:\\\\1800",text)

    def test_unknown_denominator_missing_origins_and_historical_outlier(self):
        old = read(self.paths["46006966"].parent/"limitations.json")
        self.assertEqual(len(old["missing_sources"]),5)
        self.assertEqual(sum(m["missing_original_json"] for m in old["missing_sources"]),4)
        self.assertEqual(sum(m["original_in_repository"] for m in old["missing_sources"]),1)
        self.assertEqual(len(old["historical_box_issues"]),1)
        outlier = old["historical_box_issues"][0]
        self.assertAlmostEqual(outlier["bbox"][2],1181.0944752623527)
        for book,count in (("46006966",14),("46007447",1)):
            limits = read(self.paths[book].parent/"limitations.json")
            self.assertFalse(limits["coverage_eligible"])
            self.assertEqual(limits["reference_count"],count)
            data = read(self.paths[book])
            data["artifacts"][0]["payload"]["scope_manifest"] = []
            with self.assertRaisesRegex(ContractError,"scope_manifest"):
                validate_bundle(data)  # Literal minimal failure for proposal S01.

    def test_copy_to_space_directory_and_different_cwd(self):
        for book in self.paths:
            target = self.folder/("portable exchange "+book)
            shutil.copytree(self.paths[book].parent,target)
            cwd = self.folder/("unrelated cwd "+book)
            cwd.mkdir()
            env = dict(os.environ,PYTHONPATH=str(ROOT/"src"))
            result = subprocess.run([sys.executable,str(ROOT/"examples/a01/consume.py"),
                                     str(target/"exchange.json"),"--book-id",book],cwd=cwd,env=env,
                                    capture_output=True,text=True,check=False)
            self.assertEqual(result.returncode,0,result.stderr)
            summary = json.loads(result.stdout)
            self.assertFalse(summary["coverage_eligible"])
            self.assertEqual(summary["public_resource_validation"],"OK")

    def test_repeat_import_and_new_revision_preserve_old_output(self):
        path = self.copy_output()
        before = hashes(path.parent)
        with self.assertRaisesRegex(StaticSourceError,"OUTPUT_EXISTS"):
            import_book(ROOT,"46006966",path.parent)
        self.assertEqual(hashes(path.parent),before)
        newer = import_book(ROOT,"46006966",self.folder/"revision2",revision=2,previous=path)
        self.assertEqual(load_bundle(newer).artifacts[0].revision,2)
        self.assertEqual(read(newer.parent/"provenance.json")["previous_import"]["artifact"]["content_hash"],
                         load_bundle(path).artifacts[0].content_hash)
        self.assertEqual(hashes(path.parent),before)
        for args in (dict(revision=2),dict(revision=3,previous=path),dict(revision=2,previous=self.paths["46007447"])):
            with self.subTest(args=args),self.assertRaises(StaticSourceError):
                import_book(ROOT,"46006966",self.folder/"bad revision",**args)

    def test_wrong_hash_and_dimensions_on_import_rejected(self):
        repo = self.copy_inputs()
        manifest = repo/OLD_MANIFEST
        original = read(manifest)
        for field,value,code in (("sha256","0"*64,"IMAGE_HASH"),("width",999,"IMAGE_DIMENSIONS")):
            data = copy.deepcopy(original)
            data[0][field] = value
            write(manifest,data)
            target = self.folder/field
            with self.subTest(field=field),self.assertRaisesRegex(StaticSourceError,code):
                import_book(repo,"46006966",target)
            self.assertFalse(target.exists())

    def test_missing_image_fails_before_output(self):
        repo = self.copy_inputs()
        (repo/"技术证据/只读样本-46006966/viewer-page-0008.jpg").unlink()
        target = self.folder/"missing"
        with self.assertRaisesRegex(StaticSourceError,"INPUT_MISSING"):
            import_book(repo,"46006966",target)
        self.assertFalse(target.exists())

    def test_corrupt_image_with_correct_new_digest_is_fully_decoded(self):
        repo = self.copy_inputs()
        image = repo/"技术证据/只读样本-46006966/viewer-page-0008.jpg"
        image.write_bytes(image.read_bytes()[:2000])
        manifest = repo/OLD_MANIFEST
        data = read(manifest)
        data[0]["sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
        write(manifest,data)
        with self.assertRaisesRegex(StaticSourceError,"IMAGE_DECODE"):
            import_book(repo,"46006966",self.folder/"corrupt")

    def test_conflicting_mapping_and_wrong_book_inputs_rejected(self):
        repo = self.copy_inputs()
        manifest = repo/OLD_MANIFEST
        data = read(manifest)
        data[0]["sourceImageIndex"] = 8
        write(manifest,data)
        with self.assertRaisesRegex(StaticSourceError,"MAPPING_CONFLICT"):
            import_book(repo,"46006966",self.folder/"bad mapping")
        book_path = repo/"docs/evidence/A05/review/independent-source-page14.json"
        data = read(book_path)
        data["data"]["file_id"] = "46006966"
        write(book_path,data)
        with self.assertRaisesRegex(StaticSourceError,"BOOK_CONFLICT"):
            import_book(repo,"46007447",self.folder/"bad book")
        with self.assertRaisesRegex(StaticSourceError,"BOOK_CONFLICT"):
            load_static_bundle(self.paths["46006966"],expected_book_id="46007447")

    def test_loaded_resource_tampering_dimensions_and_missing_files(self):
        path = self.copy_output()
        original = read(path)
        asset = path.parent/original["artifacts"][0]["payload"]["assets"][0]["path"]
        data = copy.deepcopy(original)
        data["artifacts"][0]["payload"]["assets"][0]["width"] += 1
        self.rewrite_bundle(path,data)
        with self.assertRaisesRegex(ContractError,"IMAGE_DIMENSIONS"):
            load_static_bundle(path,expected_book_id="46006966")
        write(path,original)
        asset.write_bytes(asset.read_bytes()+b"tampered")
        with self.assertRaisesRegex(ContractError,"RESOURCE_HASH"):
            load_static_bundle(path,expected_book_id="46006966")
        asset.unlink()
        with self.assertRaisesRegex(ContractError,"RESOURCE_MISSING"):
            load_static_bundle(path,expected_book_id="46006966")

    def test_hashed_mapping_conflict_and_fake_coverage_rejected(self):
        path = self.copy_output()
        self.rewrite_sidecar(path,"provenance.json",lambda p:p["mappings"][0].update(viewer_page=999))
        # Public C01 cannot see the sidecar semantics; A01 explicitly checks them.
        load_bundle(path)
        with self.assertRaisesRegex(StaticSourceError,"MAPPING_CONFLICT"):
            load_static_bundle(path,expected_book_id="46006966")
        self.rewrite_sidecar(path,"limitations.json",lambda p:p.update(coverage_eligible=True))
        with self.assertRaisesRegex(StaticSourceError,"DENOMINATOR_UNKNOWN"):
            load_static_bundle(path,expected_book_id="46006966")

    def test_resource_path_escape_and_protected_output_rejected(self):
        path = self.copy_output()
        data = read(path)
        for relative in ("../escape.jpg","C:/Users/example.jpg","assets/../../escape.jpg"):
            with self.subTest(relative=relative):
                changed = copy.deepcopy(data)
                changed["artifacts"][0]["payload"]["assets"][0]["path"] = relative
                write(path,changed)
                with self.assertRaises(ContractError):
                    load_static_bundle(path,expected_book_id="46006966")
        for protected in ("data/new-output","技术证据/new-output","docs/evidence/A05/new-output",".local/new-output"):
            with self.subTest(protected=protected),self.assertRaisesRegex(StaticSourceError,"OUTPUT_LOCATION"):
                import_book(ROOT,"46006966",ROOT/protected)

    def test_symlink_escape_rejected_when_host_permits_symlinks(self):
        path = self.copy_output()
        data = read(path)
        asset = path.parent/data["artifacts"][0]["payload"]["assets"][0]["path"]
        external = self.folder/"external.jpg"
        shutil.copy2(asset,external)
        asset.unlink()
        try:
            asset.symlink_to(external)
        except OSError as error:
            self.skipTest("host cannot create file symlinks; WinError="+str(getattr(error,"winerror",None)))
        with self.assertRaisesRegex(ContractError,"PATH_ESCAPE"):
            load_static_bundle(path,expected_book_id="46006966")

    def test_directory_junction_escape_rejected(self):
        path = self.copy_output()
        data = read(path)
        item = data["artifacts"][0]["payload"]["assets"][0]
        external = self.folder/"external directory"
        external.mkdir()
        shutil.copy2(path.parent/item["path"],external/"image.jpg")
        junction = path.parent/"junction"
        if os.name == "nt":
            result = subprocess.run(["cmd","/c","mklink","/J",str(junction),str(external)],
                                    capture_output=True,text=True,check=False)
            self.assertEqual(result.returncode,0,result.stderr)
            self.addCleanup(lambda:os.rmdir(junction) if junction.exists() else None)
        else:
            junction.symlink_to(external,target_is_directory=True)
        item["path"] = "junction/image.jpg"
        self.rewrite_bundle(path,data)
        with self.assertRaisesRegex(ContractError,"PATH_ESCAPE"):
            load_static_bundle(path,expected_book_id="46006966")


if __name__ == "__main__":
    unittest.main()
