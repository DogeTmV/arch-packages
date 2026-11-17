"""Core tests for hashcheck (offline, temporary files only)."""

import os
import re
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import ALGOS, HashcheckError, hash_file, normalize_expected, verify

EMPTY_SHA256 = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)
BLOB = bytes(range(256))
BLOB_DIGESTS = {
    "md5": "e2c865db4162bed963bfaa9ef6ac18f0",
    "sha1": "4916d6bdb7f78e6803698cab32d1586ea457dfc8",
    "sha256": (
        "40aff2e9d2d8922e47afd4648e6967497158785fbd1da870e7110266bf944880"
    ),
    "sha512": (
        "1e7b80bc8edc552c8feeb2780e111477e5bc70465fac1a77b29b35980c3f0ce4"
        "a036a6c9462036824bd56801e62af7e9feba5c22ed8a5af877bf7de117dcac6d"
    ),
}


class SupportedAlgorithmsTest(unittest.TestCase):
    def test_algorithms_exposed_in_documented_order(self):
        self.assertEqual(ALGOS, ("md5", "sha1", "sha256", "sha512"))


class HashFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def make_file(self, data):
        path = os.path.join(self.tmp.name, "sample.bin")
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def test_empty_file_sha256_matches_known_digest(self):
        path = self.make_file(b"")
        self.assertEqual(hash_file(path, "sha256"), EMPTY_SHA256)

    def test_binary_blob_matches_known_digests_for_every_algorithm(self):
        path = self.make_file(BLOB)
        for algo, expected in BLOB_DIGESTS.items():
            with self.subTest(algo=algo):
                self.assertEqual(hash_file(path, algo), expected)

    def test_small_chunk_size_streams_to_the_same_digest(self):
        path = self.make_file(BLOB)
        self.assertEqual(
            hash_file(path, "sha256", chunk_size=7), BLOB_DIGESTS["sha256"]
        )

    def test_digests_are_lowercase_hexadecimal(self):
        path = self.make_file(BLOB)
        for algo in ALGOS:
            with self.subTest(algo=algo):
                self.assertRegex(hash_file(path, algo), r"^[0-9a-f]+$")

    def test_missing_file_raises_clear_error(self):
        missing = os.path.join(self.tmp.name, "absent.bin")
        with self.assertRaisesRegex(HashcheckError, "file not found"):
            hash_file(missing, "sha256")

    def test_unknown_algorithm_raises_clear_error(self):
        path = self.make_file(BLOB)
        with self.assertRaisesRegex(HashcheckError, "unknown algorithm"):
            hash_file(path, "crc32")


class NormalizeExpectedTest(unittest.TestCase):
    def test_removes_surrounding_and_embedded_whitespace_and_lowercases(self):
        self.assertEqual(normalize_expected("  AB\tCD\nEF  "), "abcdef")

    def test_empty_input_normalizes_to_empty_string(self):
        self.assertEqual(normalize_expected("   \n\t"), "")


class VerifyTest(unittest.TestCase):
    def test_accepts_same_digest_with_different_case_and_spacing(self):
        self.assertTrue(verify("  " + EMPTY_SHA256.upper() + " \n", EMPTY_SHA256))

    def test_rejects_different_digest(self):
        self.assertFalse(verify("00" * 32, EMPTY_SHA256))

    def test_rejects_empty_expected_value(self):
        self.assertFalse(verify("", EMPTY_SHA256))


if __name__ == "__main__":
    unittest.main()
