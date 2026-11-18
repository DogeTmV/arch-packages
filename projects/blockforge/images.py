"""Tiny PNG helpers used by blockforge projects and generated programs.

The editor stores uploaded spirit pictures and stage backdrops as PNG bytes in
``.bfproj`` files.  This module decodes those bytes with only the Python
standard library so the compiler can emit raw RGBA arrays; generated C++ and
Rust programs then need nothing but SDL2 at run time.
"""

import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_DIMENSION = 4096
MAX_PIXELS = 2_000_000


class ImageError(ValueError):
    """Raised for malformed or unsupported PNG data."""


def _chunk(kind, payload):
    return (struct.pack(">I", len(payload)) + kind + payload +
            struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))


def encode_rgba_png(width, height, rgba):
    """Encode raw RGBA bytes as a PNG."""
    width, height = int(width), int(height)
    expected = width * height * 4
    if width < 1 or height < 1 or len(rgba) != expected:
        raise ImageError("RGBA buffer does not match the image size")
    raw = bytearray()
    stride = width * 4
    for row in range(height):
        raw.append(0)
        raw.extend(rgba[row * stride:(row + 1) * stride])
    return (SIGNATURE +
            _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6,
                                        0, 0, 0)) +
            _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
            _chunk(b"IEND", b""))


def _paeth(left, above, upper_left):
    prediction = left + above - upper_left
    distance_left = abs(prediction - left)
    distance_above = abs(prediction - above)
    distance_upper = abs(prediction - upper_left)
    if distance_left <= distance_above and distance_left <= distance_upper:
        return left
    if distance_above <= distance_upper:
        return above
    return upper_left


def decode_png(data):
    """Return ``(width, height, rgba_bytes)`` for an 8-bit, non-interlaced PNG.

    Grayscale, grayscale+alpha, RGB, RGBA, and indexed color types are
    supported.  Any unsupported feature raises :class:`ImageError` rather than
    handing malformed bytes to a compiler.
    """
    data = bytes(data)
    if not data.startswith(SIGNATURE):
        raise ImageError("not a PNG image")
    position = len(SIGNATURE)
    width = height = depth = color_type = None
    interlace = compression = filter_method = None
    palette = b""
    transparency = b""
    idat = []
    while position + 8 <= len(data):
        length = struct.unpack(">I", data[position:position + 4])[0]
        kind = data[position + 4:position + 8]
        payload = data[position + 8:position + 8 + length]
        if position + 12 + length > len(data):
            raise ImageError("truncated PNG chunk")
        checksum = struct.unpack(">I", data[position + 8 + length:
                                            position + 12 + length])[0]
        if (zlib.crc32(kind + payload) & 0xFFFFFFFF) != checksum:
            raise ImageError("PNG checksum failed")
        position += 12 + length
        if kind == b"IHDR":
            if len(payload) != 13:
                raise ImageError("invalid PNG header")
            (width, height, depth, color_type, compression,
             filter_method, interlace) = struct.unpack(">IIBBBBB", payload)
        elif kind == b"PLTE":
            palette = payload
        elif kind == b"tRNS":
            transparency = payload
        elif kind == b"IDAT":
            idat.append(payload)
        elif kind == b"IEND":
            break
    if not width or not height:
        raise ImageError("PNG has no image header")
    if width > MAX_DIMENSION or height > MAX_DIMENSION or \
            width * height > MAX_PIXELS:
        raise ImageError("image is too large")
    if depth != 8 or interlace != 0 or compression != 0 or filter_method != 0:
        raise ImageError("unsupported PNG encoding")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    if channels is None:
        raise ImageError("unsupported PNG color type")
    if color_type == 3 and (not palette or len(palette) % 3):
        raise ImageError("indexed PNG has an invalid palette")
    if not idat:
        raise ImageError("PNG has no pixel data")
    try:
        inflater = zlib.decompressobj()
        raw = inflater.decompress(b"".join(idat), MAX_PIXELS * 8 + 4096)
    except zlib.error as exc:
        raise ImageError("PNG pixel data is corrupt") from exc
    if not inflater.eof or inflater.unused_data:
        raise ImageError("PNG pixel data is corrupt")
    stride = width * channels
    if len(raw) < height * (stride + 1):
        raise ImageError("PNG pixel data is truncated")
    rows = []
    previous = bytearray(stride)
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        row = bytearray(raw[cursor:cursor + stride])
        cursor += stride
        if len(row) != stride:
            raise ImageError("PNG pixel data is truncated")
        for index in range(stride):
            left = row[index - channels] if index >= channels else 0
            above = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 1:
                row[index] = (row[index] + left) & 255
            elif filter_type == 2:
                row[index] = (row[index] + above) & 255
            elif filter_type == 3:
                row[index] = (row[index] + ((left + above) >> 1)) & 255
            elif filter_type == 4:
                row[index] = (row[index] + _paeth(left, above, upper_left)) & 255
            elif filter_type != 0:
                raise ImageError("unsupported PNG row filter")
        rows.append(row)
        previous = row
    rgba = bytearray(width * height * 4)
    for y, row in enumerate(rows):
        for x in range(width):
            offset = x * channels
            sample = row[offset:offset + channels]
            alpha = 255
            if color_type == 0:
                color = (sample[0], sample[0], sample[0])
            elif color_type == 2:
                color = (sample[0], sample[1], sample[2])
            elif color_type == 3:
                index = sample[0]
                if index * 3 + 3 > len(palette):
                    raise ImageError("PNG palette index is out of range")
                color = tuple(palette[index * 3:index * 3 + 3])
                if index < len(transparency):
                    alpha = transparency[index]
            elif color_type == 4:
                color = (sample[0], sample[0], sample[0])
                alpha = sample[1]
            else:
                color = (sample[0], sample[1], sample[2])
                alpha = sample[3]
            destination = (y * width + x) * 4
            rgba[destination:destination + 4] = bytes((*color, alpha))
    return width, height, bytes(rgba)


def rgba_rows(width, height, rgba):
    """Yield each scanline as ``(y, bytes)`` for source generation."""
    stride = width * 4
    for y in range(height):
        yield y, rgba[y * stride:(y + 1) * stride]


def make_backdrop_png(kind, width=480, height=360):
    """Create a small, deterministic backdrop PNG for the built-in library."""
    width = max(64, min(int(width), 960))
    height = max(48, min(int(height), 720))
    palettes = {
        "night": ((10, 14, 38), (45, 32, 92), (123, 94, 196)),
        "meadow": ((26, 74, 54), (69, 140, 84), (183, 214, 113)),
        "ocean": ((8, 36, 66), (18, 92, 132), (61, 174, 190)),
        "sunset": ((56, 20, 64), (176, 62, 86), (247, 173, 91)),
        "grid": ((12, 20, 34), (20, 41, 63), (39, 85, 112)),
    }
    first, middle, last = palettes.get(kind, palettes["night"])
    rgba = bytearray(width * height * 4)
    for y in range(height):
        ratio = y / max(1, height - 1)
        for x in range(width):
            blend = ratio * 0.65 + (x / max(1, width - 1)) * 0.35
            if blend < 0.5:
                amount = blend * 2
                color = tuple(round(first[i] + (middle[i] - first[i]) * amount)
                              for i in range(3))
            else:
                amount = (blend - 0.5) * 2
                color = tuple(round(middle[i] + (last[i] - middle[i]) * amount)
                              for i in range(3))
            if kind == "night":
                hash_value = (x * 73 + y * 151 + (x * y) % 97) % 997
                if hash_value == 0:
                    color = (238, 244, 255)
            elif kind == "grid":
                if x % 40 == 0 or y % 40 == 0:
                    color = tuple(min(255, value + 24) for value in color)
            elif kind in ("meadow", "ocean"):
                wave = ((x // 24 + y // 18) % 3) == 0
                if wave:
                    color = tuple(min(255, value + 10) for value in color)
            offset = (y * width + x) * 4
            rgba[offset:offset + 4] = bytes((*color, 255))
    return encode_rgba_png(width, height, bytes(rgba))
