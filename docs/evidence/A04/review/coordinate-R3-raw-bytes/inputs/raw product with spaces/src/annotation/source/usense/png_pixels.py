"""Bounded, static PNG pixel-stream validation, independent of Pillow's load.

This gate proves that every declared scanline has its filter byte and samples.
It does not judge image content. Original bytes are never repaired or rewritten.
Animated PNG is deliberately unsupported at this original-image boundary.
"""
import struct
import zlib


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PNG_BYTES = 64 * 1024 * 1024
MAX_PNG_PIXELS = 32 * 1024 * 1024
MAX_PNG_DIMENSION = 32768
MAX_PNG_SCANLINE_BYTES = 128 * 1024 * 1024
MAX_PNG_CHUNKS = 16384
_DEPTHS = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8),
           4: (8, 16), 6: (8, 16)}
_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
_ADAM7 = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
          (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))


class PNGPixelError(ValueError):
    """Only fixed local reason codes; never include file bytes or paths."""


def _require(condition, reason):
    if not condition:
        raise PNGPixelError(reason)


def _layout(width, height, depth, colour, interlace):
    bits = depth * _CHANNELS[colour]
    passes = []
    for x, y, dx, dy in _ADAM7 if interlace else ((0, 0, 1, 1),):
        w, h = max(0, (width - x + dx - 1) // dx), max(0, (height - y + dy - 1) // dy)
        if w and h:
            passes.append((w, h, (w * bits + 7) // 8))
    expected = sum(h * (row_bytes + 1) for _, h, row_bytes in passes)
    _require(expected <= MAX_PNG_SCANLINE_BYTES, "SCANLINE_LIMIT")
    return passes, expected


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def _check_rows(raw, passes, depth, colour, palette_entries):
    offset = 0
    for width, height, row_bytes in passes:
        previous = bytearray(row_bytes) if colour == 3 else None
        for _ in range(height):
            method = raw[offset]
            _require(method <= 4, "FILTER_METHOD")
            offset += 1
            if colour == 3:
                # Indexed PNG has one byte per filter unit, even at sub-byte
                # depths. Undo filters before checking actual palette samples;
                # packed padding bits do not describe pixels.
                row = bytearray(raw[offset:offset + row_bytes])
                for i in range(row_bytes):
                    a, b = row[i - 1] if i else 0, previous[i]
                    c = previous[i - 1] if i else 0
                    predictor = (0 if method == 0 else a if method == 1 else b if method == 2
                                 else (a + b) // 2 if method == 3 else _paeth(a, b, c))
                    row[i] = (row[i] + predictor) & 255
                mask = (1 << depth) - 1
                for x in range(width):
                    sample = (row[x * depth // 8] >> (8 - depth - x * depth % 8)) & mask
                    _require(sample < palette_entries, "PALETTE_INDEX")
                previous = row
            offset += row_bytes
    _require(offset == len(raw), "SCANLINE_SIZE")


def verify_png_pixels(blob):
    """Validate legal static PNG layouts and return non-content diagnostics.

    Supports PNG colour types 0/2/3/4/6 at their legal depths, both ordinary and
    Adam7 scanlines. CRCs, chunk ordering, exact bounded zlib output, filters and
    indexed palette references are checked before the existing Pillow gate.
    """
    _require(len(blob) <= MAX_PNG_BYTES, "FILE_LIMIT")
    _require(blob.startswith(PNG_SIGNATURE), "SIGNATURE")
    view = memoryview(blob)
    offset, count = 8, 0
    header = None
    palette_entries = None
    transparency = False
    idats = []
    idat_ended = ended = False
    while offset < len(blob):
        count += 1
        _require(count <= MAX_PNG_CHUNKS, "CHUNK_LIMIT")
        _require(offset + 12 <= len(blob), "CHUNK_TRUNCATED")
        length = struct.unpack_from(">I", blob, offset)[0]
        kind = blob[offset + 4:offset + 8]
        end = offset + 12 + length
        _require(end <= len(blob), "CHUNK_TRUNCATED")
        _require(all(65 <= c <= 90 or 97 <= c <= 122 for c in kind)
                 and 65 <= kind[2] <= 90, "CHUNK_TYPE")
        data = view[offset + 8:offset + 8 + length]
        _require(zlib.crc32(data, zlib.crc32(kind)) & 0xffffffff
                 == struct.unpack_from(">I", blob, end - 4)[0], "CHUNK_CRC")
        _require(header is not None or kind == b"IHDR", "HEADER_FIRST")
        if kind == b"IHDR":
            _require(header is None and length == 13, "HEADER")
            header = struct.unpack(">IIBBBBB", data)
            width, height, depth, colour, compression, filtering, interlace = header
            _require(0 < width <= MAX_PNG_DIMENSION and 0 < height <= MAX_PNG_DIMENSION
                     and width * height <= MAX_PNG_PIXELS, "DIMENSION_LIMIT")
            _require(colour in _DEPTHS and depth in _DEPTHS[colour], "COLOUR_DEPTH")
            _require(compression == 0 and filtering == 0 and interlace in (0, 1), "METHOD")
            passes, expected = _layout(width, height, depth, colour, interlace)
        elif kind == b"PLTE":
            _require(not idats and palette_entries is None and not transparency
                     and colour not in (0, 4) and 0 < length <= 768 and length % 3 == 0, "PALETTE")
            palette_entries = length // 3
            _require(colour != 3 or palette_entries <= 1 << depth, "PALETTE")
        elif kind == b"tRNS":
            _require(not idats and not transparency, "TRANSPARENCY")
            _require((colour == 3 and palette_entries is not None and 0 < length <= palette_entries)
                     or (colour == 0 and length == 2) or (colour == 2 and length == 6), "TRANSPARENCY")
            transparency = True
        elif kind == b"IDAT":
            _require(not idat_ended and (colour != 3 or palette_entries is not None), "IDAT_ORDER")
            idats.append(data)
        elif kind == b"IEND":
            _require(bool(idats) and length == 0 and end == len(blob), "END")
            ended = True
        else:
            _require(kind not in (b"acTL", b"fcTL", b"fdAT"), "ANIMATION_UNSUPPORTED")
            _require(kind[0] & 32, "CRITICAL_UNSUPPORTED")
        if idats and kind != b"IDAT":
            idat_ended = True
        offset = end
    _require(ended, "END")
    stream, raw = zlib.decompressobj(), bytearray()
    try:
        for data in idats:
            # One extra output byte distinguishes excess pixels from a complete
            # stream. Never call unbounded decompress/flush on untrusted IDAT.
            raw.extend(stream.decompress(data, expected - len(raw) + 1))
            _require(len(raw) <= expected, "SCANLINE_SIZE")
            _require(not stream.unconsumed_tail and not stream.unused_data, "ZLIB_TRAILING")
        _require(stream.eof, "ZLIB_INCOMPLETE")
    except zlib.error:
        raise PNGPixelError("ZLIB_INVALID") from None
    _require(len(raw) == expected, "SCANLINE_SIZE")
    _check_rows(raw, passes, depth, colour, palette_entries)
    return {"width": width, "height": height, "bit_depth": depth, "colour_type": colour,
            "interlace": interlace, "passes": len(passes), "scanline_bytes": expected,
            "actual_scanline_bytes": len(raw)}
