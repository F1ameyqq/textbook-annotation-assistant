"""Byte-preserving package export, malformed ZIPs, and zero-runtime replay."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"tools")]
from prepare_inline_package_b import main, prepare_inline_package, verify_inline_bundle

BUNDLE = ROOT/"tests/fixtures/book46007447/inline-observed.zip"
MANIFEST = BUNDLE.with_name("inline-observed-manifest.json")


def sha(raw): return hashlib.sha256(raw).hexdigest()


def write_bundle(directory, members=None, *, extra=(), body_change=None, internal_change=None, symlink=None):
    """Small test ZIP with fresh outer hashes, so inner checks are exercised."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    members = {"history/raw.json": b'{"raw":"never discard"}'} if members is None else members
    body = dict(schema_version="b-inline-observed-bundle-trial/0.1", members={name: {"sha256": sha(raw), "bytes": len(raw)}
        for name, raw in members.items()}, decision="HOLD", business_acceptance=False, human_gold=False)
    if body_change: body_change(body)
    internal = json.dumps(body, ensure_ascii=False, indent=2).encode()
    if internal_change: internal = internal_change(internal)
    archive = directory/"saved.zip"
    with warnings.catch_warnings(), zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as stream:
        warnings.simplefilter("ignore", UserWarning)
        for name, raw in [*members.items(), *extra]:
            if name == symlink:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                stream.writestr(info, raw)
            else: stream.writestr(name, raw)
        stream.writestr("MANIFEST.json", internal)
    external = dict(body, archive={"path": archive.name, "sha256": sha(archive.read_bytes()), "bytes": archive.stat().st_size},
                    internal_manifest_sha256=sha(internal))
    manifest = directory/"manifest.json"
    manifest.write_text(json.dumps(external, ensure_ascii=False, indent=2), encoding="utf-8")
    return archive, manifest


class InlinePackageValidation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_small_regular_zip_verifies_without_requiring_real_book_identifiers(self):
        bundle, manifest = write_bundle(self.root)
        checked = verify_inline_bundle(bundle, manifest)
        self.assertEqual(checked["member_count"], 1)
        self.assertEqual(checked["archive_sha256"], sha(bundle.read_bytes()))

    def test_outer_archive_sha_bytecount_and_internal_manifest_sha_are_independent(self):
        for key in ("sha256", "bytes", "internal_manifest_sha256"):
            with self.subTest(key=key):
                bundle, manifest = write_bundle(self.root/key)
                data = json.loads(manifest.read_text())
                if key == "bytes": data["archive"][key] += 1
                elif key == "sha256": data["archive"][key] = "0"*64
                else: data[key] = "0"*64
                manifest.write_text(json.dumps(data))
                with self.assertRaises(ValueError): verify_inline_bundle(bundle, manifest)

    def test_relative_path_rules_reject_traversal_absolute_windows_and_ambiguous_names(self):
        names = ("../escape", "/absolute", "C:/drive", "folder\\escape", "a//b", "a/./b", "a/../b",
                 "a.", "x/CON.txt", "a:b", "a?b", "a\x00b", "a\nb", "Cafe\u0301.txt")
        for index, name in enumerate(names):
            with self.subTest(name=name):
                bundle, manifest = write_bundle(self.root/str(index), {name: b"bad"})
                with self.assertRaises(ValueError): verify_inline_bundle(bundle, manifest)
        self.assertFalse((self.root/"escape").exists())

    def test_zip_duplicates_case_aliases_symlinks_extra_and_missing_members_are_rejected(self):
        cases = {
            "duplicate": ({"same": b"one"}, (("same", b"two"),), None),
            "case": ({"same": b"one"}, (("SAME", b"two"),), None),
            "extra": ({"same": b"one"}, (("extra", b"two"),), None),
            "symlink": ({"link": b"../outside"}, (), "link"),
        }
        for name, (members, extra, link) in cases.items():
            with self.subTest(name=name):
                bundle, manifest = write_bundle(self.root/name, members, extra=extra, symlink=link)
                with self.assertRaises(ValueError): verify_inline_bundle(bundle, manifest)
        bundle, manifest = write_bundle(self.root/"missing", body_change=lambda x: x["members"].update({"absent": {"sha256": "0"*64, "bytes": 0}}))
        with self.assertRaises(ValueError): verify_inline_bundle(bundle, manifest)

    def test_coordinated_outer_rehash_cannot_hide_member_hash_or_count_damage(self):
        for key, value in (("sha256", "0"*64), ("bytes", 0)):
            with self.subTest(key=key):
                bundle, manifest = write_bundle(self.root/key,
                    body_change=lambda body: body["members"]["history/raw.json"].update({key: value}))
                with self.assertRaisesRegex(ValueError, "member SHA or byte count"): verify_inline_bundle(bundle, manifest)

    def test_internal_external_body_disagreement_duplicate_json_keys_and_false_gold_are_rejected(self):
        bundle, manifest = write_bundle(self.root/"different", internal_change=lambda raw: raw.replace(b'"HOLD"', b'"WAIT"'))
        with self.assertRaisesRegex(ValueError, "manifests disagree"): verify_inline_bundle(bundle, manifest)
        bundle, manifest = write_bundle(self.root/"duplicate", internal_change=lambda raw: raw.replace(b'{', b'{"decision":"HOLD",', 1))
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"): verify_inline_bundle(bundle, manifest)
        for key, value in (("human_gold", True), ("business_acceptance", True), ("decision", "PASS")):
            bundle, manifest = write_bundle(self.root/key, body_change=lambda x: x.update({key: value}))
            with self.subTest(key=key), self.assertRaises(ValueError): verify_inline_bundle(bundle, manifest)


class InlinePackageSavedBundle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_committed_bundle_extracts_all_history_byte_identically_and_selects_exact_warm_run(self):
        before = (sha(BUNDLE.read_bytes()), sha(MANIFEST.read_bytes()))
        out = self.root/"out"
        result = prepare_inline_package(BUNDLE, MANIFEST, out)
        external = json.loads(MANIFEST.read_text(encoding="utf-8"))
        package = json.loads((out/"inline-package.json").read_text(encoding="utf-8"))
        for name, descriptor in external["members"].items():
            raw = (out/name).read_bytes()
            self.assertEqual((sha(raw), len(raw)), (descriptor["sha256"], descriptor["bytes"]), name)
        self.assertEqual(result["extracted_files"], len(external["members"])+1)
        journals = {name for name in external["members"] if name.startswith("formula/")}
        expected = journals | {d["path"] for d in package["documents"].values()}
        self.assertEqual(set(package["members"]), expected)
        self.assertEqual(result["journal_files"], len(journals))
        self.assertEqual(set(package), {"schema_version", "artifact_id", "book_id", "scope_id", "asset_id", "line_ids",
            "policy", "documents", "journal_dir", "members"})
        for role, descriptor in package["documents"].items():
            saved = json.loads((out/descriptor["path"]).read_text(encoding="utf-8"))
            expected_ref = None if role == "rows" else {k: saved[k] for k in ("artifact_id", "revision", "content_hash")}
            self.assertEqual(descriptor["artifact_ref"], expected_ref)
        self.assertEqual(package["documents"]["formula_report"]["path"], "formula-observed-trials/formal-warm-report.json")
        self.assertEqual(package["line_ids"], external["requested_line_ids"])
        self.assertEqual(result["source"]["original_sha256"], external["source_sha256"])
        self.assertEqual(result["saved_execution_state"], "READY")
        self.assertTrue(result["source_image_required_for_stage_validation"])
        self.assertEqual((result["decision"], result["new_model_calls"], result["business_acceptance"], result["human_gold"]), ("HOLD", 0, False, False))
        self.assertEqual((sha(BUNDLE.read_bytes()), sha(MANIFEST.read_bytes())), before)

    def test_partial_and_resumed_select_saved_artifacts_without_rewriting_any_journal(self):
        for choice, canonical, state in (("partial8", "formal-partial8", "PARTIAL"), ("resumed", "formal-resumed", "READY")):
            with self.subTest(choice=choice):
                out = self.root/choice
                result = prepare_inline_package(BUNDLE, MANIFEST, out, formula_run=choice)
                package = json.loads((out/"inline-package.json").read_text())
                with zipfile.ZipFile(BUNDLE) as archive:
                    for name in package["members"]:
                        self.assertEqual((out/name).read_bytes(), archive.read(name), name)
                self.assertEqual(result["saved_execution_state"], state)
                self.assertEqual(result["formula_run"], canonical)
                self.assertEqual(package["documents"]["formula_observations"]["path"], "formula-observed-trials/"+canonical+"-observations.json")

    def test_generated_nonbook46007447_package_is_accepted_by_stage_loader_without_new_recognition(self):
        sys.path.insert(0,str(ROOT/"tests"))
        from test_b_inline_stage import make_inline_fixture
        from annotation.recognition.inline_stage import load_inline_package
        from annotation.recognition.baseline import digest
        data=make_inline_fixture(self.root/"synthetic")
        roles={"evidence":"evidence.json","rows":"rows.json","ocr_observations":"observations.json",
            "formula_observations":"formula-observed-trials/formal-warm-observations.json",
            "formula_report":"formula-observed-trials/formal-warm-report.json"}
        members={name:json.dumps(data["documents"][role],ensure_ascii=False,indent=2).encode() for role,name in roles.items()}
        for path in data["journal_dir"].rglob("*"):
            if path.is_file(): members["formula/"+path.relative_to(data["journal_dir"]).as_posix()]=path.read_bytes()
        def metadata(body):
            body.update(requested_line_ids=data["line_ids"],source_sha256=data["layout"]["payload"]["source"]["original_sha256"])
        bundle,manifest=write_bundle(self.root/"bundle",members,body_change=metadata)
        out=self.root/"exported"
        result=prepare_inline_package(bundle,manifest,out)
        loaded=load_inline_package(out/"inline-package.json",data["original"])
        self.assertNotEqual(loaded["manifest"]["book_id"],"46007447")
        self.assertEqual(loaded["documents"],data["documents"])
        self.assertEqual(loaded["receipt"]["package"]["reference"],result["package"]["reference"])
        self.assertEqual(loaded["receipt"]["package"]["reference"]["content_hash"],digest(loaded["manifest"]))
        self.assertEqual(loaded["documents"]["formula_observations"]["producer"]["execution_kind"],"SYNTHETIC_TEST")

    def test_existing_directory_is_never_overwritten_and_cli_rejects_bad_combinations_before_work(self):
        out = self.root/"existing"
        out.mkdir()
        marker = out/"inline-formula.sqlite3"
        marker.write_bytes(b"original-journal")
        with self.assertRaises(ValueError): prepare_inline_package(BUNDLE, MANIFEST, out)
        self.assertEqual(marker.read_bytes(), b"original-journal")
        for args in (["--bundle", str(BUNDLE), "--manifest", str(MANIFEST), "--out", str(out)],
                     ["--bundle", "https://example.invalid/a", "--manifest", str(MANIFEST), "--out", str(self.root/"new")],
                     ["--bundle", str(BUNDLE), "--manifest", str(MANIFEST), "--out", str(self.root/"new"), "--formula-run", "invented"]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main(args)
            self.assertEqual(error.exception.code, 2)
        self.assertFalse((self.root/"new").exists())

    def test_bad_artifact_binding_is_rejected_before_output_creation_even_with_new_zip_hashes(self):
        with zipfile.ZipFile(BUNDLE) as archive:
            members = {name: archive.read(name) for name in archive.namelist() if name != "MANIFEST.json"}
        external = json.loads(MANIFEST.read_text())
        ordinary = json.loads(members["observations.json"])
        ordinary["payload"]["evidence_ref"]["artifact_id"] = "foreign-evidence"
        from annotation.recognition.baseline import digest
        ordinary["content_hash"] = digest(ordinary["payload"])
        members["observations.json"] = json.dumps(ordinary).encode()
        def body_change(body):
            body.update({k: v for k, v in external.items() if k not in {"archive", "internal_manifest_sha256", "members"}})
        bundle, manifest = write_bundle(self.root/"changed", members, body_change=body_change)
        out = self.root/"not-created"
        with self.assertRaisesRegex(ValueError, "reference chain"): prepare_inline_package(bundle, manifest, out)
        self.assertFalse(out.exists())

    def test_inflight_bundle_change_does_not_publish_package(self):
        import prepare_inline_package_b as tool
        bundle = self.root/"saved.zip"
        bundle.write_bytes(BUNDLE.read_bytes())
        original = tool._extract_verified
        def changing(*args):
            original(*args)
            with bundle.open("ab") as stream: stream.write(b"changed")
        out = self.root/"out"
        with patch.object(tool, "_extract_verified", side_effect=changing), self.assertRaisesRegex(ValueError, "inputs changed"):
            prepare_inline_package(bundle, MANIFEST, out)
        self.assertFalse((out/"inline-package.json").exists())

    def test_fresh_process_exports_with_all_model_and_network_entries_blocked(self):
        script = r'''
import sys,runpy,socket
class Block:
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in {'rapidocr_onnxruntime','rapid_latex_ocr','onnxruntime','torch','requests','urllib3'}:
   raise RuntimeError('forbidden model/network import '+fullname)
sys.meta_path.insert(0,Block())
def denied(*a,**k): raise RuntimeError('network forbidden')
socket.socket=denied; socket.create_connection=denied
entry=sys.argv.pop(1)
runpy.run_path(entry,run_name='__main__')
'''
        out = self.root/"fresh"
        completed = subprocess.run([sys.executable, "-c", script, str(ROOT/"tools/prepare_inline_package_b.py"),
            "--bundle", str(BUNDLE), "--manifest", str(MANIFEST), "--out", str(out)], cwd=ROOT,
            capture_output=True, text=True, encoding="utf-8", timeout=45)
        self.assertEqual(completed.returncode, 0, completed.stdout+completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["new_model_calls"], 0)
        self.assertEqual(result["decision"], "HOLD")


if __name__ == "__main__": unittest.main()
