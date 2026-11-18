"""Tests for the blockforge project model and custom save container."""

import json
import os
import tempfile
import unittest
import zipfile

from core import (
    BLOCKS,
    PROJECT_ENTRY,
    Sprite,
    Variable,
    Procedure,
    Project,
    ValidationError,
    block,
    load_project,
    new_script,
    save_project,
    script_owner,
    script_target,
    scripts_for_target,
    validate_project,
)
from examples import EXAMPLES, example_project
from images import encode_rgba_png, make_backdrop_png


def script(sprite, *blocks):
    return {"target": "spirit", "sprite": sprite, "x": 32, "y": 48,
            "blocks": list(blocks)}


class ProjectModelTests(unittest.TestCase):
    def test_block_constructor_initializes_declared_slots(self):
        self.assertEqual(block("control_repeat").children, {"SUB": []})
        self.assertEqual(block("control_if_else").children,
                         {"THEN": [], "ELSE": []})

    def test_nested_blocks_survive_a_save_round_trip(self):
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
            path = os.path.join(folder, "project.bfproj")
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

    def test_procedure_arguments_survive_a_save_round_trip(self):
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
            path = os.path.join(folder, "project.bfproj")
            save_project(project, path)
            restored = load_project(path)
        call = restored.scripts[0]["blocks"][1]
        self.assertEqual(call.fields["arg_message"], '"hello"')
        validate_project(restored)

    def test_new_scripts_are_owned_by_the_selected_object(self):
        spirit_script = new_script("Hero")
        stage_script = new_script("Stage")
        self.assertEqual(script_owner(spirit_script), "Hero")
        self.assertEqual(script_owner(stage_script), "Stage")
        project = Project(scripts=[spirit_script, stage_script])
        self.assertEqual(scripts_for_target(project, "Hero"),
                         [(0, spirit_script)])
        self.assertEqual(scripts_for_target(project, "Stage"),
                         [(1, stage_script)])

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

    def test_stage_is_a_reserved_spirit_name(self):
        project = Project(sprites=[Sprite(name="Stage")])
        with self.assertRaisesRegex(ValidationError, "reserved"):
            validate_project(project)

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

    def test_save_uses_a_zip_container_with_a_readable_manifest(self):
        project = Project(name="Container")
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "project.bfproj")
            save_project(project, path)
            with zipfile.ZipFile(path) as archive:
                manifest = json.loads(archive.read(PROJECT_ENTRY).decode("utf-8"))

        self.assertEqual(manifest["format"], "blockforge")
        self.assertEqual(manifest["version"], 2)
        self.assertEqual(manifest["name"], "Container")
        self.assertEqual(manifest["assets"], [])

    def test_pictures_and_backdrops_survive_a_save_round_trip(self):
        hero_png = encode_rgba_png(
            2, 2, bytes([255, 0, 0, 255] * 4))
        backdrop_png = make_backdrop_png("meadow", 64, 48)
        project = Project(
            name="Pictures",
            backdrop="stage_meadow.png",
            sprites=[Sprite(name="Hero", image="hero.png")],
            assets={"hero.png": hero_png, "stage_meadow.png": backdrop_png},
        )
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "pictures.bfproj")
            save_project(project, path)
            restored = load_project(path)
            with zipfile.ZipFile(path) as archive:
                self.assertEqual(
                    archive.namelist(),
                    [PROJECT_ENTRY, "assets/hero.png",
                     "assets/stage_meadow.png"],
                )

        self.assertEqual(restored.assets, project.assets)
        self.assertEqual(restored.backdrop, "stage_meadow.png")
        self.assertEqual(restored.sprites[0].image, "hero.png")

    def test_rejects_a_sprite_without_its_picture(self):
        project = Project(sprites=[Sprite(name="Hero", image="missing.png")])
        with self.assertRaisesRegex(ValidationError, "picture .* is missing"):
            validate_project(project)

    def test_legacy_json_projects_are_migrated_to_targeted_scripts(self):
        project = Project(name="Legacy", sprites=[Sprite(name="Hero")])
        project.scripts.append(script(
            "Hero", block("event_flag"), block("control_print", value='"old"')
        ))
        payload = project.to_dict()
        payload["version"] = 1
        payload["scripts"][0].pop("target")
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "legacy.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            restored = load_project(path)

        self.assertEqual(script_target(restored.scripts[0]), "spirit")
        self.assertEqual(script_owner(restored.scripts[0]), "Hero")

    def test_stage_script_survives_a_save_round_trip(self):
        project = Project(name="Stage")
        project.assets["night.png"] = make_backdrop_png("night", 64, 48)
        project.backdrop = "night.png"
        project.scripts.append({
            "target": "stage", "x": 24, "y": 24,
            "blocks": [block("event_flag"),
                       block("looks_set_backdrop", backdrop="night.png")],
        })
        validate_project(project)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "stage.bfproj")
            save_project(project, path)
            restored = load_project(path)

        self.assertEqual(script_owner(restored.scripts[0]), "Stage")
        self.assertEqual(
            restored.scripts[0]["blocks"][1].fields["backdrop"], "night.png")

    def test_stage_scripts_reject_sprite_motion(self):
        project = Project(name="Stage")
        project.scripts.append({
            "target": "stage", "x": 0, "y": 0,
            "blocks": [block("event_flag"), block("motion_move", steps="5")],
        })
        with self.assertRaisesRegex(ValidationError, "cannot run on the stage"):
            validate_project(project)

    def test_stage_scripts_reject_sprite_sensing(self):
        project = Project(name="Stage")
        project.scripts.append({
            "target": "stage", "x": 0, "y": 0,
            "blocks": [block("event_flag"),
                       block("control_if", condition="x position > 0")],
        })
        with self.assertRaisesRegex(ValidationError,
                                    "sprite sensing cannot run on the stage"):
            validate_project(project)

    def test_reporters_use_plain_language_labels(self):
        self.assertEqual(BLOCKS["operator_add"].label, "add")
        self.assertEqual(BLOCKS["operator_random"].label, "pick random")
        self.assertEqual(BLOCKS["sensing_touching_sprite"].label,
                         "touching spirit?")
        for type_ in ("operator_add", "operator_random",
                      "sensing_touching_sprite"):
            self.assertNotIn("(", BLOCKS[type_].label)


class ExampleTests(unittest.TestCase):
    def test_all_bundled_examples_validate(self):
        for name in EXAMPLES:
            with self.subTest(example=name):
                validate_project(example_project(name))

    def test_example_projects_have_scripts_and_sprites(self):
        for name in EXAMPLES:
            project = example_project(name)
            with self.subTest(example=name):
                self.assertTrue(project.sprites, "example needs a spirit")
                self.assertTrue(project.scripts, "example needs a script")
                self.assertTrue(any(script_target(item) == "spirit"
                                    for item in project.scripts))

    def test_an_example_demonstrates_stage_scripts_and_backdrops(self):
        project = example_project("night")
        self.assertTrue(project.backdrop)
        self.assertIn(project.backdrop, project.assets)
        self.assertTrue(any(script_target(item) == "stage"
                            for item in project.scripts))

    def test_unknown_example_name_is_rejected(self):
        with self.assertRaises(KeyError):
            example_project("not-an-example")


if __name__ == "__main__":
    unittest.main()
