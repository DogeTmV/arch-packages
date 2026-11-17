"""Core tests for jsonpolish (pure JSON, no files or network)."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import format_json, minify_json, validate_json


class FormatJsonTest(unittest.TestCase):
    def test_nested_objects_use_two_space_indent_by_default(self):
        self.assertEqual(
            format_json('{"outer":{"inner":[1,2]}}'),
            '{\n  "outer": {\n    "inner": [\n      1,\n      2\n    ]\n  }\n}',
        )

    def test_key_order_is_preserved_by_default(self):
        self.assertEqual(
            format_json('{"b":2,"a":1}'),
            '{\n  "b": 2,\n  "a": 1\n}',
        )

    def test_sort_keys_reorders_object_keys(self):
        self.assertEqual(
            format_json('{"b":2,"a":1}', sort_keys=True),
            '{\n  "a": 1,\n  "b": 2\n}',
        )

    def test_indent_argument_controls_indentation(self):
        self.assertEqual(
            format_json('{"a":1}', indent=4),
            '{\n    "a": 1\n}',
        )

    def test_unicode_is_kept_readable(self):
        result = format_json('{"drink":"caf\u00e9 \u2615"}')
        self.assertIn("café ☕", result)
        self.assertNotIn("\\u", result)

    def test_invalid_json_raises_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            format_json("{not json")


class MinifyJsonTest(unittest.TestCase):
    def test_whitespace_is_removed(self):
        self.assertEqual(
            minify_json('{"a": 1, "b": [2, 3]}'),
            '{"a":1,"b":[2,3]}',
        )

    def test_invalid_json_raises_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            minify_json("")


class ValidateJsonTest(unittest.TestCase):
    def test_valid_input_reports_valid(self):
        self.assertEqual(validate_json('{"a": 1}'), "Valid JSON")

    def test_invalid_input_reports_invalid_with_reason(self):
        status = validate_json('[1, 2')
        self.assertTrue(status.startswith("Invalid JSON:"), status)
        self.assertGreater(len(status), len("Invalid JSON:"))


class RoundTripTest(unittest.TestCase):
    def test_format_then_minify_returns_compact_json(self):
        text = '{"z":0,"a":{"b":true}}'
        self.assertEqual(
            minify_json(format_json(text, sort_keys=True)),
            '{"a":{"b":true},"z":0}',
        )


if __name__ == "__main__":
    unittest.main()
