"""Tests for the blockforge project model and JSON persistence."""

import json
import os
import tempfile
import unittest

from core import (
    Block,
    Procedure,
    Sprite,
    Variable,
    Project,
    ValidationError,
    block,
    load_project,
    save_project,
    validate_project,
)
from examples import EXAMPLES, example_project


def script(sprite, *blocks):
    return {"sprite": sprite, "x": 32, "y": 48, "blocks": list(blocks)}


class ProjectModelTests(unittest.TestCase):
    def test_block_constructor_initializes_declared_slots(self):
        self.assertEqual(block("control_repeat").children, {"SUB": []})
        self.assertEqual(block("control_if_else").children,
                         {"THEN": [], "ELSE": []})

    def test_nested_blocks_survive_a_json_round_trip(self):
        project = Project(name="Round trip")
        project.sprites.append(Sprite(name="Hero"))
        project.variables.append(Variable(name="score", type="number"))
        project.scripts.append(script(
            "Hero",
            block("event_flag"),
            block("control_if", condition="score > 2", children={
                "SUB": [block("variable_set", name="score", value="0")],
            }),
            block("motion_move", steps="score + 1"),
        ))

        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "project.json")
            save_project(project, path)
            restored = load_project(path)

        self.assertEqual(restored.name, "Round trip")
        self.assertEqual(restored.language, "cpp")
        self.assertEqual(restored.variables[0].name, "score")
        self.assertEqual(restored.sprites[0].shape, "circle")
        self.assertEqual(restored.scripts[0]["x"], 32)
        outer = restored.scripts[0]["blocks"]
        self.assertEqual([item.type for item in outer],
                         ["event_flag", "control_if", "motion_move"])
        self.assertEqual(outer[1].fields["condition"], "score > 2")
        self.assertEqual(outer[1].children["SUB"][0].type, "variable_set")
        self.assertEqual(outer[1].children["SUB"][0].fields["value"], "0")

    def test_procedure_arguments_survive_a_json_round_trip(self):
        project = Project(name="Arguments")
        project.sprites.append(Sprite(name="Hero"))
        project.procedures.append(Procedure(
            name="announce",
            params=[{"name": "message", "type": "text"}],
            blocks=[block("control_print", value="message")],
        ))
        project.scripts.append(script(
            "Hero",
            block("event_flag"),
            block("procedure_call", name="announce",
                  arg_message='"hello"'),
        ))
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "project.json")
            save_project(project, path)
            restored = load_project(path)
        call = restored.scripts[0]["blocks"][1]
        self.assertEqual(call.fields["arg_message"], '"hello"')
        validate_project(restored)

    def test_rejects_unknown_block_type(self):
        project = Project()
        project.sprites.append(Sprite(name="Hero"))
        project.scripts.append(script(
            "Hero", block("event_flag"), block("motion_explode")
        ))
        with self.assertRaises(ValidationError) as caught:
            validate_project(project)
        self.assertIn("motion_explode", str(caught.exception))

    def test_rejects_script_for_missing_sprite(self):
        project = Project()
        project.scripts.append(script("Ghost", block("event_flag")))
        with self.assertRaises(ValidationError) as caught:
            validate_project(project)
        self.assertIn("Ghost", str(caught.exception))

    def test_rejects_duplicate_sprite_names(self):
        project = Project()
        project.sprites.extend([Sprite(name="Twin"), Sprite(name="Twin")])
        with self.assertRaises(ValidationError) as caught:
            validate_project(project)
        self.assertIn("Twin", str(caught.exception))

    def test_rejects_a_text_expression_in_a_number_field(self):
        project = Project(name="Types", sprites=[Sprite(name="Hero")])
        project.scripts.append(script(
            "Hero", block("event_flag"),
            block("motion_move", steps='"not a number"'),
        ))
        with self.assertRaisesRegex(ValidationError, "expected a number"):
            validate_project(project)

    def test_hat_blocks_are_rejected_inside_a_slot(self):
        project = Project(name="Hats", sprites=[Sprite(name="Hero")])
        project.scripts.append(script(
            "Hero", block("event_flag"),
            block("control_repeat", times="2", children={
                "SUB": [block("event_flag")],
            }),
        ))
        with self.assertRaisesRegex(ValidationError, "event block"):
            validate_project(project)

    def test_procedure_cannot_reserve_a_generated_identifier(self):
        project = Project(name="Reserved", sprites=[Sprite(name="Hero")])
        project.procedures.append(Procedure(
            name="announce", params=[{"name": "app", "type": "number"}]
        ))
        with self.assertRaisesRegex(ValidationError, "reserved"):
            validate_project(project)

    def test_rejects_bad_expression_in_a_field(self):
        project = Project()
        project.sprites.append(Sprite(name="Hero"))
        project.scripts.append(script(
            "Hero", block("event_flag"), block("motion_move", steps="2 +")
        ))
        with self.assertRaises(ValidationError) as caught:
            validate_project(project)
        self.assertIn("steps", str(caught.exception))

    def test_rejects_unknown_variable_reference(self):
        project = Project()
        project.sprites.append(Sprite(name="Hero"))
        project.scripts.append(script(
            "Hero", block("event_flag"),
            block("variable_set", name="lives", value="3")
        ))
        with self.assertRaises(ValidationError) as caught:
            validate_project(project)
        self.assertIn("lives", str(caught.exception))

    def test_load_project_reports_a_corrupt_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "bad.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{this is not json")
            with self.assertRaises(ValidationError):
                load_project(path)

    def test_malformed_project_structure_reports_a_validation_error(self):
        payload = {
            "format": "blockforge", "version": 1, "stage": [],
            "sprites": "not a list",
        }
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "bad.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            with self.assertRaisesRegex(ValidationError, "stage must be an object"):
                load_project(path)

    def test_file_contains_a_readable_format_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "p.json")
            save_project(Project(name="Marker"), path)
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
        self.assertEqual(payload["format"], "blockforge")
        self.assertEqual(payload["version"], 1)


class ExampleTests(unittest.TestCase):
    def test_all_bundled_examples_validate(self):
        for name in EXAMPLES:
            with self.subTest(example=name):
                validate_project(example_project(name))

    def test_example_projects_have_scripts_and_sprites(self):
        for name in EXAMPLES:
            project = example_project(name)
            with self.subTest(example=name):
                self.assertTrue(project.sprites, "example needs a sprite")
                self.assertTrue(project.scripts, "example needs a script")

    def test_unknown_example_name_is_rejected(self):
        with self.assertRaises(KeyError):
            example_project("not-an-example")


if __name__ == "__main__":
    unittest.main()
