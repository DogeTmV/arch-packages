"""Tests for the dependency-free PNG helpers used by .bfproj files."""

import struct
import unittest
import zlib

from images import (
    ImageError,
    decode_png,
    encode_rgba_png,
    make_backdrop_png,
    rgba_rows,
)


class ImageTests(unittest.TestCase):
    def test_rgba_round_trip_preserves_every_pixel(self):
        rgba = bytes([
            12, 34, 56, 255, 255, 0, 0, 128,
            0, 255, 128, 0, 240, 240, 240, 32,
        ])
        png = encode_rgba_png(2, 2, rgba)
        self.assertEqual(decode_png(png), (2, 2, rgba))
        self.assertEqual(
            [row for _, row in rgba_rows(2, 2, rgba)],
            [rgba[:8], rgba[8:]],
        )

    def test_rejects_data_that_is_not_a_png(self):
        with self.assertRaisesRegex(ImageError, "not a PNG"):
            decode_png(b"not an image")

    def test_rejects_a_png_with_a_broken_checksum(self):
        png = bytearray(encode_rgba_png(1, 1, bytes([1, 2, 3, 255])))
        png[-5] ^= 0xFF
        with self.assertRaisesRegex(ImageError, "checksum"):
            decode_png(bytes(png))

    def test_rejects_an_interlaced_png_header(self):
        png = bytearray(encode_rgba_png(1, 1, bytes([1, 2, 3, 255])))
        struct.pack_into("B", png, 16 + 12, 1)
        checksum = zlib.crc32(bytes(png[12:29])) & 0xFFFFFFFF
        struct.pack_into(">I", png, 29, checksum)
        with self.assertRaisesRegex(ImageError, "unsupported PNG encoding"):
            decode_png(bytes(png))

    def test_library_backdrops_decode_and_are_deterministic(self):
        first = make_backdrop_png("night", 64, 48)
        second = make_backdrop_png("night", 64, 48)
        self.assertEqual(first, second)
        width, height, rgba = decode_png(first)
        self.assertEqual((width, height), (64, 48))
        self.assertEqual(len(rgba), 64 * 48 * 4)


if __name__ == "__main__":
    unittest.main()
