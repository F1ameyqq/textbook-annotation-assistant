"""R3 static PNG scanline proof, with independent synthetic pixel construction."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest import mock
import zlib

from PIL import Image
from annotation.contracts import load_bundle
from annotation.source.usense import SourceParseError, build_source, parse_capture
from annotation.source.usense import cli, parser, png_pixels as gate


ROOT = Path(__file__).resolve().parents[1]
COMBINATIONS = ((0, 1), (0, 2), (0, 4), (0, 8), (0, 16), (2, 8), (2, 16),
                (3, 1), (3, 2), (3, 4), (3, 8), (4, 8), (4, 16), (6, 8), (6, 16))
EXACT_SHA = "205543876fb32bb14f003bfeec32279e9fd4886bd1949eee9810999e468969bd"


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)


def png_from_raw(width, height, depth, colour, interlace, raw, palette=None, idats=None, extra=()):
    head = struct.pack(">IIBBBBB", width, height, depth, colour, 0, 0, interlace)
    palette = chunk(b"PLTE", palette) if palette is not None else b""
    compressed = [zlib.compress(raw)] if idats is None else idats
    return (gate.PNG_SIGNATURE + chunk(b"IHDR", head) + palette
            + b"".join(chunk(k, v) for k, v in extra)
            + b"".join(chunk(b"IDAT", value) for value in compressed) + chunk(b"IEND", b""))


def exact_counterexample():
    # Same raw construction as the frozen reviewer script; SHA binds this test.
    row = b"\0" + bytes((i * 13) % 256 for i in range(37 * 3))
    return png_from_raw(37, 29, 8, 2, 0, row)


def _pass_number(x, y):
    # Partition physical pixel coordinates, independent of the gate's pass-size
    # formula. Each image pixel belongs to exactly one Adam7 pass.
    if y % 8 == 0 and x % 8 == 0: return 0
    if y % 8 == 0 and x % 8 == 4: return 1
    if y % 8 == 4 and x % 4 == 0: return 2
    if y % 4 == 0 and x % 4 == 2: return 3
    if y % 4 == 2 and x % 2 == 0: return 4
    if y % 2 == 0 and x % 2 == 1: return 5
    return 6


def make_png(width=13, height=11, depth=8, colour=2, interlace=0, method=0, blank=False):
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colour]
    mask = (1 << depth) - 1
    entries = min(1 << depth, 4) if colour == 3 else 0
    palette = bytes(v for i in range(entries) for v in (i * 61, i * 37, i * 17)) if entries else None
    raw = bytearray()
    rows, covered = [], set()
    for pass_number in range(7 if interlace else 1):
        previous = None
        for y in range(height):
            xs = [x for x in range(width) if not interlace or _pass_number(x, y) == pass_number]
            if not xs: continue
            samples = []
            for x in xs:
                assert (x, y) not in covered
                covered.add((x, y))
                for c in range(channels):
                    samples.append(0 if blank else (x + y * 3) % entries if entries
                                   else (x * 31 + y * 17 + c * 11) & mask)
            row = bytearray()
            if depth < 8:
                for i in range(0, len(samples), 8 // depth):
                    value = 0
                    for j, sample in enumerate(samples[i:i + 8 // depth]):
                        value |= sample << (8 - depth * (j + 1))
                    row.append(value)
            else:
                for sample in samples:
                    row.extend(sample.to_bytes(depth // 8, "big"))
            previous = previous if previous is not None else bytes(len(row))
            assert len(row) == len(previous)
            distance = max(1, (channels * depth + 7) // 8)
            encoded = bytearray()
            for i, value in enumerate(row):
                left = row[i - distance] if i >= distance else 0
                up = previous[i]
                upper_left = previous[i - distance] if i >= distance else 0
                distances = [abs(up - upper_left), abs(left - upper_left), abs(left + up - 2 * upper_left)]
                nearest = (left, up, upper_left)[distances.index(min(distances))]
                predictor = (0, left, up, (left + up) // 2, nearest)[method]
                encoded.append((value - predictor) % 256)
            raw.append(method); raw.extend(encoded)
            rows.append({"pass": pass_number, "y": y, "pixels": len(xs), "bytes": len(row) + 1})
            previous = row
    assert len(covered) == width * height
    return png_from_raw(width, height, depth, colour, interlace, bytes(raw), palette), bytes(raw), rows, palette


class PNGStreamProofTests(unittest.TestCase):
    def reject(self, blob, reason=None):
        with self.assertRaises(gate.PNGPixelError) as raised: gate.verify_png_pixels(blob)
        if reason: self.assertEqual(str(raised.exception), reason)

    def test_exact_frozen_counterexample_and_pillow_gap(self):
        blob = exact_counterexample()
        self.assertEqual((len(blob), hashlib.sha256(blob).hexdigest()), (180, EXACT_SHA))
        with Image.open(io.BytesIO(blob)) as image: image.verify()
        with Image.open(io.BytesIO(blob)) as image: image.load()
        self.reject(blob, "SCANLINE_SIZE")

    def test_all_30_legal_layouts_and_all_five_filters(self):
        for colour, depth in COMBINATIONS:
            for interlace in (0, 1):
                for method in range(5):
                    with self.subTest(colour=colour, depth=depth, interlace=interlace, filter=method):
                        blob, raw, rows, _ = make_png(depth=depth, colour=colour, interlace=interlace, method=method)
                        info = gate.verify_png_pixels(blob)
                        self.assertEqual(info["scanline_bytes"], sum(row["bytes"] for row in rows))
                        self.assertEqual(info["actual_scanline_bytes"], len(raw))
                        with Image.open(io.BytesIO(blob)) as image: image.load()

    def test_adam7_small_images_empty_passes_and_packed_row_rounding(self):
        for width, height in ((1, 1), (1, 9), (9, 1), (2, 2), (3, 5), (8, 8), (9, 9)):
            for colour, depth in ((0, 1), (3, 2), (2, 16), (6, 16)):
                blob, raw, rows, _ = make_png(width, height, depth, colour, 1)
                with self.subTest(size=(width, height), colour=colour, depth=depth):
                    self.assertEqual(gate.verify_png_pixels(blob)["scanline_bytes"], len(raw))
                    self.assertEqual(sum(r["pixels"] for r in rows), width * height)

    def test_same_class_short_and_excess_pixels_across_layouts(self):
        for width, height, depth, colour, interlace in ((5, 7, 1, 0, 0), (19, 6, 16, 2, 0),
                (11, 13, 2, 3, 1), (17, 9, 16, 6, 1)):
            _, raw, _, palette = make_png(width, height, depth, colour, interlace)
            for altered in (raw[:-1], raw[:len(raw)//2], raw + b"\0", b""):
                with self.subTest(size=(width, height), colour=colour, interlace=interlace, length=len(altered)):
                    self.reject(png_from_raw(width, height, depth, colour, interlace, altered, palette), "SCANLINE_SIZE")

    def test_complete_blank_image_is_valid(self):
        blob, _, _, _ = make_png(37, 29, blank=True)
        self.assertEqual(gate.verify_png_pixels(blob)["scanline_bytes"], 3248)

    def test_exact_byte_count_but_invalid_filter_is_rejected(self):
        _, raw, _, _ = make_png()
        self.reject(png_from_raw(13, 11, 8, 2, 0, b"\5" + raw[1:]), "FILTER_METHOD")

    def test_palette_indices_checked_after_every_filter_and_each_pass_reset(self):
        for method in range(5):
            blob, _, _, _ = make_png(depth=8, colour=3, interlace=1, method=method)
            self.assertEqual(gate.verify_png_pixels(blob)["colour_type"], 3)
        self.reject(png_from_raw(1, 1, 2, 3, 0, b"\0\x80", b"\0\0\0"), "PALETTE_INDEX")
        # Seven unused packed bits may be nonzero; they do not name pixels.
        gate.verify_png_pixels(png_from_raw(1, 1, 1, 3, 0, b"\0\x7f", b"\0\0\0"))

    def test_zlib_stream_eof_extra_stream_and_trailing_compressed_bytes(self):
        _, raw, _, _ = make_png()
        compressed = zlib.compress(raw)
        for altered, reason in ((compressed[:-1], "ZLIB_INCOMPLETE"),
                (compressed + b"junk", "ZLIB_TRAILING"), (compressed + zlib.compress(b""), "ZLIB_TRAILING")):
            self.reject(png_from_raw(13, 11, 8, 2, 0, raw, idats=[altered]), reason)
        gate.verify_png_pixels(png_from_raw(13, 11, 8, 2, 0, raw,
                              idats=[b"", compressed[:2], compressed[2:-1], compressed[-1:], b""]))

    def test_crc_including_terminal_iend_and_chunk_truncation(self):
        blob, _, _, _ = make_png()
        for offset in (29, -1):
            damaged = bytearray(blob); damaged[offset] ^= 1
            self.reject(bytes(damaged), "CHUNK_CRC")
        for altered in (blob[:-1], blob[:24], blob + b"extra", blob[:-12]): self.reject(altered)

    def test_chunk_order_unknown_critical_and_animation_explicitly_rejected(self):
        blob, raw, _, _ = make_png()
        for kind in (b"ABCD", b"acTL", b"fcTL", b"fdAT"):
            self.reject(png_from_raw(13, 11, 8, 2, 0, raw, extra=[(kind, b"\0" * 8)]))
        ihdr = blob[8:33]
        self.reject(gate.PNG_SIGNATURE + ihdr + ihdr + blob[33:], "HEADER")
        comp = zlib.compress(raw)
        self.reject(gate.PNG_SIGNATURE + ihdr + chunk(b"IDAT", comp[:2])
                    + chunk(b"tEXt", b"key\0value") + chunk(b"IDAT", comp[2:]) + chunk(b"IEND", b""), "IDAT_ORDER")
        gate.verify_png_pixels(png_from_raw(13, 11, 8, 2, 0, raw, extra=[(b"tEXt", b"key\0value")]))

    def test_illegal_depth_colour_compression_filtering_and_interlace(self):
        for depth, colour in ((8, 1), (8, 5), (4, 2), (16, 3), (1, 4), (4, 6)):
            self.reject(png_from_raw(4, 3, depth, colour, 0, b""), "COLOUR_DEPTH")
        self.reject(png_from_raw(4, 3, 8, 2, 2, b""), "METHOD")
        blob, _, _, _ = make_png()
        for pos in (10, 11):
            header = bytearray(blob[16:29]); header[pos] = 1
            self.reject(gate.PNG_SIGNATURE + chunk(b"IHDR", header) + blob[33:], "METHOD")

    def test_palette_and_transparency_declaration_boundaries(self):
        for palette in (None, b"", b"\0", b"\0" * 771, b"\0" * 9):
            self.reject(png_from_raw(1, 1, 1, 3, 0, b"\0\0", palette))
        self.reject(png_from_raw(1, 1, 8, 0, 0, b"\0\0", b"\0\0\0"), "PALETTE")
        for colour, depth, raw, palette, transparency in ((0, 8, b"\0\0", None, b"\0\0"),
                (2, 8, b"\0\0\0\0", None, b"\0" * 6), (3, 1, b"\0\0", b"\0\0\0", b"\xff")):
            gate.verify_png_pixels(png_from_raw(1, 1, depth, colour, 0, raw, palette,
                                  extra=[(b"tRNS", transparency)]))
        self.reject(png_from_raw(1, 1, 8, 6, 0, b"\0" * 5, extra=[(b"tRNS", b"\0")]), "TRANSPARENCY")

    def test_resource_limits_at_and_one_below_small_actual_sample(self):
        blob, raw, _, _ = make_png(37, 29)
        limits = {"MAX_PNG_BYTES": len(blob), "MAX_PNG_PIXELS": 37 * 29,
                  "MAX_PNG_DIMENSION": 37, "MAX_PNG_SCANLINE_BYTES": len(raw), "MAX_PNG_CHUNKS": 3}
        for name, value in limits.items():
            with self.subTest(limit=name), mock.patch.object(gate, name, value): gate.verify_png_pixels(blob)
            with self.subTest(limit=name), mock.patch.object(gate, name, value - 1): self.reject(blob)
        # Configured bounds reject from IHDR, without allocating declared rows.
        for width, height in ((32769, 1), (32768, 32768), (16384, 1024)):
            self.reject(png_from_raw(width, height, 16, 6, 0, b""))


class PNGPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="a04 R3 offline spaces ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.input = self.root / "input"
        shutil.copytree(ROOT / "tests/fixtures/a04/source", self.input)
        self.capture = json.loads((self.input / "capture.json").read_text(encoding="utf8"))
        self.asset = self.input / self.capture["pages"][0]["asset_path"]

    def parse(self):
        return parse_capture(self.capture, self.input, now=self.capture["observed_at"])

    def test_public_entry_all_30_combinations_and_pgm_relocated_consumer(self):
        for colour, depth in COMBINATIONS:
            for interlace in (0, 1):
                with self.subTest(colour=colour, depth=depth, interlace=interlace):
                    blob, _, _, _ = make_png(depth=depth, colour=colour, interlace=interlace, method=4)
                    self.asset.write_bytes(blob)
                    parsed = self.parse()
                    self.assertEqual(parsed.pages[0]["sha256"], hashlib.sha256(blob).hexdigest())
                    result = build_source(parsed, self.input,
                        history_path="evidence/colour-{}-depth-{}-interlace-{}.json".format(colour, depth, interlace))
                    self.assertIsNotNone(result)
        # PGM positive public entry and relocated consumption, complement R2's
        # existing PNG/JPEG relocation test.
        shutil.copyfile(ROOT / "tests/fixtures/a04/source/assets/page-14.pgm", self.asset)
        out = self.root / "output"; stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = cli.main(["offline", "--input", str(self.input), "--output", str(out),
                           "--as-of", self.capture["observed_at"]])
        self.assertEqual(rc, 0, stdout.getvalue())
        moved = self.root / "relocated PGM package with spaces"; shutil.move(str(out), moved)
        self.assertIsNotNone(load_bundle(moved / "bundle.json"))

    def test_exact_bad_input_fails_before_history_and_final_package(self):
        self.asset.write_bytes(exact_counterexample())
        with mock.patch.object(Image.Image, "load", return_value=None):
            with self.assertRaises(SourceParseError) as raised: self.parse()
        self.assertEqual((raised.exception.code, raised.exception.path), ("RESOURCE_INVALID", "$.pages[0].asset_path"))
        self.assertFalse((self.input / "evidence").exists())
        out = self.root / "rejected"; stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = cli.main(["offline", "--input", str(self.input), "--output", str(out),
                           "--as-of", self.capture["observed_at"]])
        self.assertEqual(rc, 2)
        self.assertEqual(stdout.getvalue().strip(), "A04_FAILED:RESOURCE_INVALID; LOCATION=$.pages[0].asset_path")
        self.assertFalse(out.exists())

    def test_prepublication_swap_same_dimensions_is_rejected_without_history(self):
        self.asset.write_bytes(make_png(37, 29)[0]); parsed = self.parse()
        self.asset.write_bytes(exact_counterexample())
        with self.assertRaises(SourceParseError) as raised: build_source(parsed, self.input)
        self.assertEqual((raised.exception.code, raised.exception.path), ("RESOURCE_INVALID", "$.pages[0].path"))
        self.assertFalse((self.input / "evidence").exists())

    def test_png_input_read_is_capped_before_body_allocation(self):
        blob = make_png()[0]
        source = mock.MagicMock(); source.__enter__.return_value = source
        source.read.side_effect = [gate.PNG_SIGNATURE, blob[8:65]]
        with mock.patch.object(Path, "open", return_value=source), mock.patch.object(parser, "MAX_PNG_BYTES", 64):
            with self.assertRaises(SourceParseError): parser._image_inventory(self.asset, "$.pages[0].asset_path")
        self.assertEqual(source.read.call_args_list, [mock.call(8), mock.call(57)])


if __name__ == "__main__": unittest.main()
