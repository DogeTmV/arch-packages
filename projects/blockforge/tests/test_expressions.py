"""Tests for the language-neutral expression parser and translators."""

import unittest

from expressions import (
    ExprContext,
    ExpressionError,
    parse_expression,
    translate_expression,
)

CPP = ExprContext(
    language="cpp",
    sprite=0,
    variables={"score": "number", "name": "text", "flag": "bool"},
    sprites=["Hero", "Star"],
)
RUST = ExprContext(
    language="rust",
    sprite=0,
    variables={"score": "number", "name": "text", "flag": "bool"},
    sprites=["Hero", "Star"],
)


class ParserTests(unittest.TestCase):
    def test_arithmetic_precedence_is_preserved(self):
        self.assertEqual(
            parse_expression("2 + 3 * 4"),
            ("bin", "+", ("num", 2), ("bin", "*", ("num", 3), ("num", 4))),
        )

    def test_exponent_is_right_associative(self):
        self.assertEqual(
            parse_expression("2 ^ 3 ^ 4"),
            ("bin", "^", ("num", 2),
             ("bin", "^", ("num", 3), ("num", 4))),
        )

    def test_multiword_builtins_parse_as_one_call(self):
        self.assertEqual(
            parse_expression('key pressed("space")'),
            ("call", "key pressed", [("str", "space")]),
        )

    def test_unterminated_string_reports_an_error(self):
        with self.assertRaises(ExpressionError) as caught:
            parse_expression('"oops')
        self.assertIn("string", str(caught.exception))

    def test_trailing_operator_reports_an_error(self):
        with self.assertRaises(ExpressionError) as caught:
            parse_expression("2 +")
        self.assertIn("+", str(caught.exception))


class TranslationTests(unittest.TestCase):
    CASES = [
        ("2 + 3 * 4", "(2 + (3 * 4))", "(2.0 + (3.0 * 4.0))"),
        ("-3 + 4", "((-3) + 4)", "((-3.0) + 4.0)"),
        ("score > 2 and flag",
         '((app.var_num("score") > 2) && app.var_bool("flag"))',
         '((app.var_num("score") > 2.0) && app.var_bool("flag"))'),
        ("x position + y position",
         "(app.sprite_x(0) + app.sprite_y(0))",
         "(app.sprite_x(0) + app.sprite_y(0))"),
        ("random(1, 10)", "app.random_range(1, 10)",
         "app.random_range(1.0, 10.0)"),
        ("key pressed(\"space\")", "app.key_pressed(44)",
         "app.key_pressed(44)"),
        ("touching sprite(\"Star\")", "app.touching_sprite(0, 1)",
         "app.touching_sprite(0, 1)"),
        ("timer", "app.timer()", "app.timer()"),
        ("2 % 3", "std::fmod(2, 3)", "(2.0 % 3.0)"),
        ("2 ^ 3", "std::pow(2, 3)", "(2.0).powf(3.0)"),
        ('join("score: ", score)',
         'app.join(std::string("score: "), app.var_num("score"))',
         'app.join(Value::from("score: ".to_string()), '
         'Value::from(app.var_num("score")))'),
        ('"a" == "b"',
         'app.equal(std::string("a"), std::string("b"))',
         'app.equal(Value::from("a".to_string()), '
         'Value::from("b".to_string()))'),
        ('len("abc")', 'app.length(std::string("abc"))',
         'app.length(Value::from("abc".to_string()))'),
        ('to number("12")', 'app.num(std::string("12"))',
         'app.num(Value::from("12".to_string()))'),
    ]

    def test_cpp_and_rust_translations_match_hand_written_output(self):
        for source, expected_cpp, expected_rust in self.CASES:
            with self.subTest(expression=source):
                self.assertEqual(translate_expression(source, CPP), expected_cpp)
                self.assertEqual(translate_expression(source, RUST), expected_rust)

    def test_rust_numbers_are_explicit_floating_point_literals(self):
        self.assertEqual(
            translate_expression("2 + 3 * 4", RUST),
            "(2.0 + (3.0 * 4.0))",
        )
        self.assertEqual(translate_expression("random(1, 10)", RUST),
                         "app.random_range(1.0, 10.0)")

    def test_unknown_key_name_is_rejected(self):
        with self.assertRaises(ExpressionError) as caught:
            translate_expression('key pressed("f13")', CPP)
        self.assertIn("f13", str(caught.exception))

    def test_unknown_variable_is_rejected(self):
        with self.assertRaises(ExpressionError) as caught:
            translate_expression("missing + 1", CPP)
        self.assertIn("missing", str(caught.exception))

    def test_unknown_language_is_rejected(self):
        with self.assertRaises(ValueError):
            translate_expression("1 + 1", ExprContext(language="python"))


if __name__ == "__main__":
    unittest.main()
