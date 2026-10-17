"""Bounded R7 product migration/API checks; no old static entry is imported."""
import copy
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import annotation.contracts.a03_bridge as bridge
from annotation.contracts import ContractError
from annotation.contracts.a03_bridge import StaticCodecError, open_static_context, select_static_codec, validate_static_bundle

FIX = Path(__file__).resolve().parent / "fixtures/a03/P2-R7-readonly-codec"
INDEX = json.loads((FIX / "index.json").read_bytes())
CASES = {row["id"]: row for row in INDEX["cases"]}
OBSERVATIONS = []


def data(name="registration-positive"):
    row = CASES[name]
    raw = (FIX / row["bundle"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row["bundle_sha256"]
    return json.loads(raw), FIX / row["asset_root"]


class MigrationTests(unittest.TestCase):
    pass


def migration_test(name):
    def run(self):
        bundle, root = data(name)
        expected = CASES[name]["expected"]
        context = open_static_context(asset_root=root)
        if expected == "STATIC_ACCEPTED":
            result = validate_static_bundle(bundle, context=context)
            self.assertEqual(result.model_dump(), bundle)
            actual, path = "STATIC_ACCEPTED", None
            self.assertEqual(result.selection.role, "STATIC_INSPECTION")
            self.assertTrue(result.resources)
        else:
            with self.assertRaises(StaticCodecError) as raised:
                validate_static_bundle(bundle, context=context)
            self.assertIsInstance(raised.exception, ContractError)
            actual, path = raised.exception.code, raised.exception.path
            self.assertEqual(actual, expected)
            if name in ("source-binding-negative", "snapshot-binding-negative"):
                self.assertEqual(path, "r4-static/" + name + "/prefix.json")
            elif name == "target-tuple-negative":
                self.assertTrue(path.endswith("/registration/target"))
            elif name == "r3-original-undeclared-evidence":
                self.assertEqual(path, "origin-a-SourceBundle")
            elif name == "global-resource-hash-corruption":
                self.assertEqual(path, "r5-static/global-only-proof.txt")
                mismatch = CASES[name]["intentional_digest_mismatches_preserved"]
                self.assertEqual(len(mismatch), 1)
                self.assertNotEqual(mismatch[0]["actual_sha256"], mismatch[0]["declared_sha256"])
            else:
                self.assertTrue(path.startswith(("A:", "E:", "R:")))
        OBSERVATIONS.append({"group": "migration", "id": name, "actual": actual, "path": path, "expected_layer": CASES[name]["expected_layer"]})
    return run


for case_name in CASES:
    setattr(MigrationTests, "test_" + case_name.replace("-", "_"), migration_test(case_name))


class SelectionAndSnapshotTests(unittest.TestCase):
    def test_role_and_exact_pins(self):
        _, root = data()
        chosen = select_static_codec()
        self.assertEqual(chosen.codec_id, "a03-static-readonly-v1")
        self.assertFalse(hasattr(chosen, "__dict__"))
        for role in ("CURRENT", "UNKNOWN_ROLE"):
            with self.subTest(role=role), self.assertRaises(StaticCodecError) as raised:
                open_static_context(asset_root=root, selection=replace(chosen, role=role))
            self.assertEqual(raised.exception.code, "ROLE_NOT_ALLOWED")
        for value in (replace(chosen, profile_sha256="0" * 64), replace(chosen, schema_pins=((chosen.schema_pins[0][0], "0" * 64),) + chosen.schema_pins[1:])):
            with self.assertRaises(StaticCodecError) as raised:
                open_static_context(asset_root=root, selection=value)
            self.assertEqual(raised.exception.code, "SELECTION_PINS")
        with self.assertRaises(StaticCodecError) as raised:
            open_static_context(asset_root=root, selection={"role": "STATIC_INSPECTION"})
        self.assertEqual(raised.exception.code, "SELECTION_TYPE")
        with self.assertRaises(FrozenInstanceError):
            chosen.role = "CURRENT"
        OBSERVATIONS.append({"group": "API", "id": "roles_and_exact_pins", "result": "EXPECTED_REJECTIONS"})

    def test_unknown_envelope_and_nonfinite(self):
        bundle, root = data()
        context = open_static_context(asset_root=root)
        bad = copy.deepcopy(bundle)
        bad["format_version"] = "a03-unknown-envelope"
        with self.assertRaises(StaticCodecError) as raised:
            validate_static_bundle(bad, context=context)
        self.assertEqual(raised.exception.code, "EXCHANGE_VERSION")
        for number in (float("nan"), float("inf"), -float("inf")):
            bad = copy.deepcopy(bundle)
            bad["nonfinite"] = number
            with self.assertRaises(StaticCodecError) as raised:
                validate_static_bundle(bad, context=context)
            self.assertEqual(raised.exception.code, "JSON_NONFINITE")
        OBSERVATIONS.append({"group": "API", "id": "envelope_and_nonfinite", "result": "EXPECTED_REJECTIONS"})

    def test_snapshot_isolation(self):
        bundle, root = data()
        original = copy.deepcopy(bundle)
        snapshot = validate_static_bundle(bundle, context=open_static_context(asset_root=root))
        expected = hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf8")).hexdigest()
        self.assertEqual(snapshot.canonical_sha256, expected)
        bundle["artifacts"].clear()
        dump = snapshot.model_dump()
        dump["evidence"].clear()
        self.assertEqual(snapshot.model_dump(), original)
        self.assertFalse(hasattr(snapshot, "__dict__"))
        with self.assertRaises(TypeError):
            snapshot.data["artifacts"][0]["payload"]["changed"] = True
        with self.assertRaises(FrozenInstanceError):
            snapshot.canonical_sha256 = "0" * 64
        with self.assertRaises(FrozenInstanceError):
            snapshot.resources[0].path = "changed"
        self.assertEqual(snapshot.selection.role, "STATIC_INSPECTION")
        self.assertFalse(hasattr(snapshot, "writer"))
        OBSERVATIONS.append({"group": "API", "id": "immutable_full_snapshot", "result": "PASS", "canonical_sha256": expected, "resources": len(snapshot.resources)})

    def test_schema_unknown_assertion_fails_closed(self):
        from annotation.contracts.a03_bridge._schema import validate
        with self.assertRaises(StaticCodecError) as raised:
            validate({}, {"allOf": [{}]})
        self.assertEqual(raised.exception.code, "SCHEMA_KEYWORDS")
        OBSERVATIONS.append({"group": "API", "id": "frozen_dialect_unknown_assertion", "result": "EXPECTED_REJECTION"})


def with_orphan(bundle, path, raw):
    value = copy.deepcopy(bundle)
    record = copy.deepcopy(value["evidence"][0])
    record.update(evidence_id="proof-r7-path-control", resource={"path": path, "sha256": hashlib.sha256(raw).hexdigest(), "media_type": "text/plain", "origin": "SYNTHETIC"})
    value["evidence"].append(record)
    return value


class PathTests(unittest.TestCase):
    def test_relative_and_absolute_escape(self):
        bundle, root = data()
        with tempfile.TemporaryDirectory(dir=os.environ.get("R7_TEMP_ROOT")) as folder:
            outside = Path(folder) / "ordinary.txt"
            outside.write_bytes(b"ordinary R7 path test\n")
            for path in ("../ordinary.txt", str(outside.resolve())):
                with self.subTest(path=path), self.assertRaises(StaticCodecError) as raised:
                    validate_static_bundle(with_orphan(bundle, path, outside.read_bytes()), context=open_static_context(asset_root=root))
                self.assertEqual(raised.exception.code, "RESOURCE_PATH")
        OBSERVATIONS.append({"group": "paths", "id": "relative_and_absolute_escape", "result": "EXPECTED_REJECTIONS"})

    def test_resolved_symlink_escape(self):
        bundle, root = data()
        with tempfile.TemporaryDirectory(dir=os.environ.get("R7_TEMP_ROOT")) as folder:
            folder = Path(folder)
            outside = folder / "ordinary.txt"
            outside.write_bytes(b"ordinary symlink control\n")
            link = root / "r7-temporary-link.txt"
            junction = root / "r7-temporary-junction"
            # The only fixture mutation is a new temporary link, removed below.
            try:
                try:
                    os.symlink(str(outside.resolve()), str(link))
                except OSError as error:
                    if os.name != "nt":
                        self.skipTest("symlink creation unavailable: " + str(error.errno))
                    created = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(folder)], capture_output=True, timeout=10)
                    if created.returncode:
                        self.skipTest("host denies symlink and directory junction creation")
                    resource_path = junction.name + "/ordinary.txt"
                else:
                    resource_path = link.name
                with self.assertRaises(StaticCodecError) as raised:
                    validate_static_bundle(with_orphan(bundle, resource_path, outside.read_bytes()), context=open_static_context(asset_root=root))
                self.assertEqual(raised.exception.code, "RESOURCE_ESCAPE")
                OBSERVATIONS.append({"group": "paths", "id": "resolved_symlink_escape", "result": "EXPECTED_REJECTION"})
            finally:
                if link.is_symlink():
                    link.unlink()
                if junction.exists():
                    self.assertEqual(junction.parent.resolve(), root.resolve())
                    self.assertEqual(junction.resolve(), folder.resolve())
                    os.rmdir(junction)  # Remove only this verified junction link.


if __name__ == "__main__":
    unittest.main()
