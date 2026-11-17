"""Pure hashing logic for hashcheck. No Qt imports live here."""

import hashlib
import os

ALGOS = ("md5", "sha1", "sha256", "sha512")


class HashcheckError(Exception):
    """A user-facing error raised by the hashing helpers."""


def hash_file(path, algo, chunk_size=1 << 20):
    """Stream *path* through *algo* and return its lowercase hex digest."""
    key = str(algo).lower()
    if key not in ALGOS:
        raise HashcheckError(
            "unknown algorithm '%s' (choose from %s)" % (algo, ", ".join(ALGOS))
        )
    if not os.path.isfile(path):
        raise HashcheckError("file not found: %s" % path)
    digest = hashlib.new(key)
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_expected(text):
    """Drop all whitespace and fold case so pasted hashes compare cleanly."""
    return "".join(str(text).split()).lower()


def verify(expected, actual):
    """Return True when the two hashes are the same after normalization."""
    return normalize_expected(expected) == normalize_expected(actual)
