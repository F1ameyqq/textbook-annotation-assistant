"""R2 source publication regressions; synthetic files, strictly offline."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zlib

from PIL import Image, ImageFile
from annotation.contracts import artifact_ref, load_bundle, seal_artifact, write_bundle
from annotation.delivery.usense_readonly.coordinates import DEPENDENCY_COMMIT
from annotation.source.usense import SourceParseError, build_source, parse_capture
from annotation.source.usense import cli

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/a04/source"


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)


def corrupt_png_pixels():
    # Valid complete chunk structure/CRCs; IDAT is not a zlib pixel stream.
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 3, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", b"invalid compressed synthetic pixels") + chunk(b"IEND", b""))


def encoded(fmt):
    stream = io.BytesIO()
    image = Image.new("RGB", (4, 3), "white")
    image.putpixel((1, 1), (20, 40, 60))
    image.save(stream, format=fmt)
    return stream.getvalue()


def reseal_corrupt_hash_only_package(root, blob):
    """Test-only forgery: C01 hashes/headers are not full source decoding."""
    data = load_bundle(root / "bundle.json").model_dump(mode="json")
    source = next(a for a in data["artifacts"] if a["kind"] == "SourceBundle")
    asset = source["payload"]["assets"][0]
    (root / asset["path"]).write_bytes(blob)
    asset_id, sha = asset["asset_id"], hashlib.sha256(blob).hexdigest()
    asset.update(sha256=sha, media_type="image/png")
    def bind(value):
        if isinstance(value, dict):
            if value.get("asset_id") == asset_id and "sha256" in value:
                value["sha256"] = sha
            for child in value.values(): bind(child)
        elif isinstance(value, list):
            for child in value: bind(child)
    bind(data)
    source = seal_artifact(source)
    artifacts = [source]
    for artifact in data["artifacts"]:
        if artifact["kind"] == "SourceBundle": continue
        artifact["input_refs"] = [artifact_ref(source) if ref["artifact_id"] == source["artifact_id"] else ref
                                  for ref in artifact["input_refs"]]
        artifacts.append(seal_artifact(artifact))
    data["artifacts"] = artifacts
    # Never overwrite an exchange revision; this is a distinctly named test file.
    write_bundle(data, root / "hash-only-forged.json")
    return load_bundle(root / "hash-only-forged.json")


class FullOriginalDecodeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="a04 R2 offline with spaces ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / "input"
        shutil.copytree(FIXTURE, self.input)
        self.capture = json.loads((self.input / "capture.json").read_text(encoding="utf-8"))
        self.asset = self.input / self.capture["pages"][0]["asset_path"]

    def parse(self):
        return parse_capture(self.capture, self.input, now=self.capture["observed_at"])

    def invoke(self, name="output"):
        output = self.root / name
        text = io.StringIO()
        with mock.patch.object(cli, "collect_live", side_effect=AssertionError("offline only")), contextlib.redirect_stdout(text):
            result = cli.main(["offline", "--input", str(self.input), "--output", str(output),
                               "--as-of", self.capture["observed_at"]])
        return result, text.getvalue(), output

    def assert_rejected(self, blob):
        self.asset.write_bytes(blob)
        with self.assertRaises(SourceParseError) as raised: self.parse()
        self.assertEqual(raised.exception.code, "RESOURCE_INVALID")
        self.assertEqual(raised.exception.path, "$.pages[0].asset_path")
        result, text, output = self.invoke()
        self.assertEqual(result, 2)
        self.assertEqual(text.strip(), "A04_FAILED:RESOURCE_INVALID; LOCATION=$.pages[0].asset_path")
        self.assertFalse(output.exists())

    def test_original_24_byte_png_public_module_rejects_before_output(self):
        blob = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", 4, 3)
        self.assertEqual(len(blob), 24)
        self.assert_rejected(blob)
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        output = self.root / "module output"
        result = subprocess.run([sys.executable, "-B", "-m", "annotation.source.usense", "offline",
            "--input", str(self.input), "--output", str(output), "--as-of", self.capture["observed_at"]],
            cwd=self.root, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("LOCATION=$.pages[0].asset_path", result.stdout)
        self.assertFalse(output.exists())

    def test_valid_png_structure_crc_but_broken_pixel_stream_is_rejected(self):
        blob = corrupt_png_pixels()
        with Image.open(io.BytesIO(blob)) as image:
            self.assertEqual(image.size, (4, 3))
            image.verify()  # Structural verification alone accepts this input.
        with Image.open(io.BytesIO(blob)) as image:
            with self.assertRaises(OSError): image.load()
        self.assert_rejected(blob)

    def test_truncated_jpeg_with_real_valid_frame_header_is_rejected(self):
        blob = encoded("JPEG")[:-12]
        with Image.open(io.BytesIO(blob)) as image:
            self.assertEqual((image.format, image.size), ("JPEG", (4, 3)))
            image.verify()
        self.assert_rejected(blob)

    def test_pgm_header_without_pixels_is_rejected(self):
        self.assert_rejected(b"P5\n4 3\n255\n")

    def test_png_crc_damage_is_rejected_even_if_pixels_could_load(self):
        blob = bytearray(encoded("PNG"))
        marker = blob.index(b"IDAT")
        length = struct.unpack(">I", blob[marker - 4:marker])[0]
        blob[marker + 4 + length] ^= 1  # IDAT CRC; leave its pixel bytes intact.
        self.assert_rejected(bytes(blob))

    def test_complete_png_jpeg_pgm_and_relocated_public_package(self):
        for fmt, media in (("PNG", "image/png"), ("JPEG", "image/jpeg")):
            with self.subTest(format=fmt):
                self.asset.write_bytes(encoded(fmt))
                parsed = self.parse()
                self.assertEqual(parsed.pages[0]["media_type"], media)
                self.assertEqual((parsed.pages[0]["width"], parsed.pages[0]["height"]), (4, 3))
                result, text, output = self.invoke("output " + fmt)
                self.assertEqual(result, 0, text)
                self.assertNotIn("WAITING_ACCEPTED_COMMIT", text)
                self.assertIn("GEOMETRY_NOT_PERFORMED", text)
                moved = self.root / ("relocated " + fmt + " package with spaces")
                shutil.move(str(output), str(moved))
                source = next(a for a in load_bundle(moved / "bundle.json").artifacts if a.kind == "SourceBundle")
                self.assertEqual(len(source.payload.pages_acquired), 3)
                for asset in source.payload.assets:
                    with Image.open(moved / asset.path) as image:
                        image.load(); self.assertEqual(image.size, (asset.width, asset.height))
                    self.assertEqual(asset.sha256, hashlib.sha256((moved / asset.path).read_bytes()).hexdigest())

    def test_dependency_status_does_not_claim_source_coordinate_verification(self):
        result, text, output = self.invoke()
        self.assertEqual(result, 0, text)
        entry = json.loads((output / "evidence/entry-result.json").read_text())
        self.assertEqual(entry["geometry_dependency_status"], "ACCEPTED")
        self.assertEqual(entry["geometry_dependency_commit"], DEPENDENCY_COMMIT)
        self.assertEqual(entry["geometry_status"], "NOT_PERFORMED_BY_SOURCE")
        self.assertEqual(entry["acceptance"], "NOT_ASSERTED")
        self.assertFalse(entry["network_used"])

    def test_complete_decode_is_rechecked_before_source_publication(self):
        parsed = self.parse()
        self.asset.write_bytes(corrupt_png_pixels())
        with self.assertRaises(SourceParseError) as raised: build_source(parsed, self.input)
        self.assertEqual((raised.exception.code, raised.exception.path), ("RESOURCE_INVALID", "$.pages[0].path"))
        self.assertFalse((self.input / "evidence").exists())

    def test_permissive_ambient_decoder_fails_closed_without_changing_flag(self):
        with mock.patch.object(ImageFile, "LOAD_TRUNCATED_IMAGES", True):
            with self.assertRaises(SourceParseError) as raised: self.parse()
            self.assertEqual(raised.exception.code, "RESOURCE_INVALID")
            self.assertTrue(ImageFile.LOAD_TRUNCATED_IMAGES)

    def test_decode_exception_does_not_expose_raw_error_or_path(self):
        secret = "SYNTHETIC_PRIVATE_MESSAGE"
        with mock.patch.object(ImageFile.ImageFile, "load", side_effect=OSError(secret)):
            with self.assertRaises(SourceParseError) as raised: self.parse()
        self.assertNotIn(secret, str(raised.exception))
        self.assertNotIn(str(self.input), str(raised.exception))

    def test_hash_header_layer_is_separate_from_full_source_decode(self):
        result, text, output = self.invoke()
        self.assertEqual(result, 0, text)
        forged = self.root / "hash only test forgery"
        shutil.copytree(output, forged)
        blob = corrupt_png_pixels()
        accepted_by_hash_layer = reseal_corrupt_hash_only_package(forged, blob)
        self.assertEqual(len(accepted_by_hash_layer.artifacts[0].payload.pages_acquired), 3)
        capture = json.loads((forged / "capture.json").read_text())
        with self.assertRaises(SourceParseError) as raised:
            parse_capture(capture, forged, now=capture["observed_at"])
        self.assertEqual(raised.exception.code, "RESOURCE_INVALID")


if __name__ == "__main__": unittest.main()
