"""Pure JSON formatting logic for jsonpolish. No Qt imports live here."""

import json


class JsonpolishError(ValueError):
    """A user-facing error raised for malformed JSON."""


def _loads(text):
    try:
        return json.loads(text)
    except (TypeError, ValueError) as exc:
        raise JsonpolishError("Invalid JSON: %s" % exc) from exc


def format_json(text, indent=2, sort_keys=False):
    """Return *text* as indented, readable JSON (Unicode kept as-is)."""
    return json.dumps(
        _loads(text), indent=indent, sort_keys=sort_keys, ensure_ascii=False
    )


def minify_json(text):
    """Return *text* as compact JSON with no optional whitespace."""
    return json.dumps(_loads(text), separators=(",", ":"), ensure_ascii=False)


def validate_json(text):
    """Return a short human-readable validity status for *text*."""
    try:
        _loads(text)
    except JsonpolishError as exc:
        return str(exc)
    return "Valid JSON"
