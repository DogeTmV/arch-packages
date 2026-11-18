"""Tests for the built-in spirit and stage library."""

import unittest

from core import Project, Sprite, validate_project
from images import decode_png
from library import (
    SPIRITS,
    STAGES,
    apply_stage_preset,
    spirit_from_preset,
    spirit_start_script,
    unique_name,
)


class LibraryTests(unittest.TestCase):
    def test_library_offers_spirits_and_stages(self):
        self.assertGreaterEqual(len(SPIRITS), 5)
        self.assertGreaterEqual(len(STAGES), 4)
        self.assertTrue(all(item.label and item.description for item in SPIRITS))
        self.assertTrue(all(item.label and item.description for item in STAGES))

    def test_unique_name_adds_a_number_when_a_name_is_taken(self):
        self.assertEqual(unique_name(["Hero"], "Hero"), "Hero2")
        self.assertEqual(unique_name(["Hero", "Hero2"], "Hero"), "Hero3")

    def test_spirit_preset_uses_a_free_name_and_keeps_its_look(self):
        project = Project(sprites=[Sprite(name="Mascot")])
        spirit = spirit_from_preset(project, "mascot")
        self.assertEqual(spirit.name, "Mascot2")
        self.assertEqual(spirit.shape, "circle")
        self.assertEqual(spirit.color, "#7c6cff")

    def test_library_spirits_can_start_with_a_ready_script(self):
        script = spirit_start_script("ball", "Ball")
        self.assertEqual(script["target"], "spirit")
        self.assertEqual(script["sprite"], "Ball")
        self.assertEqual(script["blocks"][0].type, "event_flag")
        self.assertEqual(script["blocks"][1].type, "control_forever")

    def test_stage_preset_embeds_a_backdrop_at_the_stage_size(self):
        project = Project(width=320, height=240)
        preset = apply_stage_preset(project, "ocean", 320, 240)
        self.assertEqual(preset.label, "Ocean")
        self.assertEqual(project.backdrop, "stage_ocean.png")
        width, height, rgba = decode_png(project.assets[project.backdrop])
        self.assertEqual((width, height), (320, 240))
        self.assertEqual(len(rgba), 320 * 240 * 4)
        validate_project(project)

    def test_every_stage_preset_produces_a_valid_project(self):
        for preset in STAGES:
            with self.subTest(stage=preset.key):
                project = Project(sprites=[Sprite(name="Hero")])
                apply_stage_preset(project, preset.key, 160, 120)
                validate_project(project)
                self.assertIn(project.backdrop, project.assets)


if __name__ == "__main__":
    unittest.main()
