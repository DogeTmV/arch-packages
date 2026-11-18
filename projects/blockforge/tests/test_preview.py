"""Tests for the in-editor stage preview interpreter."""

import unittest

from core import Project, Sprite, Variable, block
from images import encode_rgba_png
from preview import PreviewEngine


def _key_project():
    return Project(
        name="Key",
        sprites=[Sprite(name="Bot")],
        scripts=[{
            "target": "spirit", "sprite": "Bot", "x": 32, "y": 32,
            "blocks": [
                block("event_key", key="space"),
                block("control_print", value='"pressed"'),
            ],
        }],
    )


def _project(*blocks):
    return Project(
        name="Preview",
        variables=[Variable("score", "number")],
        sprites=[Sprite(name="Bot")],
        scripts=[{
            "target": "spirit", "sprite": "Bot", "x": 32, "y": 32,
            "blocks": [block("event_flag"), *blocks],
        }],
    )


class PreviewEngineTests(unittest.TestCase):
    def _run(self, project, steps=80):
        engine = PreviewEngine(project)
        engine.start()
        for _ in range(steps):
            engine.step(0.05)
        return engine

    def test_repeat_updates_variables_and_sprite_position(self):
        project = _project(
            block("variable_set", name="score", value="0"),
            block("control_repeat", times="3", children={"SUB": [
                block("motion_move", steps="5"),
                block("variable_change", name="score", value="2"),
            ]}),
            block("control_stop", choice="all"),
        )
        engine = self._run(project)
        self.assertFalse(engine.running)
        self.assertEqual(engine.variables["score"], 6)
        self.assertAlmostEqual(engine.sprites[0]["x"], 15.0)
        self.assertAlmostEqual(engine.sprites[0]["y"], 0.0)

    def test_if_else_selects_a_branch(self):
        project = _project(
            block("variable_set", name="score", value='0'),
            block("control_if_else", condition="false", children={
                "THEN": [block("variable_set", name="score", value="1")],
                "ELSE": [block("variable_set", name="score", value="2")],
            }),
            block("control_stop", choice="all"),
        )
        engine = self._run(project)
        self.assertEqual(engine.variables["score"], 2)

    def test_wait_does_not_advance_the_script_early(self):
        project = _project(
            block("variable_set", name="score", value="0"),
            block("control_wait", secs="0.2"),
            block("variable_set", name="score", value="9"),
            block("control_stop", choice="all"),
        )
        engine = PreviewEngine(project)
        engine.start()
        engine.step(0.05)
        self.assertEqual(engine.variables["score"], 0)
        for _ in range(5):
            engine.step(0.05)
        self.assertEqual(engine.variables["score"], 9)

    def test_plus_uses_numeric_addition_like_generated_code(self):
        project = _project(block("control_print", value='"1" + 2'))
        engine = self._run(project, steps=2)
        self.assertEqual(engine.output, ["3"])

    def test_stop_this_script_exits_nested_blocks(self):
        project = _project(
            block("control_repeat", times="3", children={"SUB": [
                block("control_if", condition="true", children={"SUB": [
                    block("control_stop", choice="this script"),
                ]}),
            ]}),
            block("variable_set", name="score", value="9"),
        )
        engine = self._run(project)
        self.assertEqual(engine.variables["score"], 0)

    def test_key_hat_waits_for_its_key(self):
        engine = PreviewEngine(_key_project())
        engine.start()
        for _ in range(4):
            engine.step(0.05)
        self.assertEqual(engine.output, [])
        self.assertTrue(engine.running)
        engine.key_down("space")
        engine.step(0.05)
        self.assertEqual(engine.output, ["pressed"])
        engine.key_up("space")

    def test_glide_moves_gradually(self):
        project = _project(
            block("motion_glide", secs="0.2", x="100", y="0"),
            block("control_stop", choice="all"),
        )
        engine = PreviewEngine(project)
        engine.start()
        engine.step(0.05)
        x = engine.sprites[0]["x"]
        self.assertGreater(x, 0.0)
        self.assertLess(x, 100.0)
        for _ in range(4):
            engine.step(0.05)
        self.assertAlmostEqual(engine.sprites[0]["x"], 100.0, delta=0.01)

    def test_output_drain_tracks_lines_after_the_cap(self):
        project = _project(*[
            block("control_print", value=str(index)) for index in range(305)
        ])
        engine = self._run(project, steps=2)
        lines, cursor = engine.drain_output(0)
        self.assertEqual(cursor, 305)
        self.assertEqual(len(lines), 300)
        self.assertEqual(lines[-1], "304")
        engine.evaluate("1", 0)
        engine.output.append("new")
        engine.output_total += 1
        lines, cursor = engine.drain_output(cursor)
        self.assertEqual(lines, ["new"])
        self.assertEqual(cursor, 306)

    def test_pen_marks_are_recorded_when_moving(self):
        project = _project(
            block("pen_down"),
            block("motion_move", steps="10"),
            block("control_stop", choice="all"),
        )
        engine = self._run(project, steps=4)
        self.assertEqual(len(engine.lines), 1)
        self.assertAlmostEqual(engine.lines[0][2], 10.0)


    def test_picture_assets_are_decoded_for_stage_drawing(self):
        picture = encode_rgba_png(2, 2, bytes([9, 8, 7, 255] * 4))
        project = Project(
            name="Picture",
            sprites=[Sprite(name="Bot", image="hero.png")],
            assets={"hero.png": picture},
        )
        engine = PreviewEngine(project)
        self.assertEqual(engine.images["hero.png"][2], bytes([9, 8, 7, 255] * 4))
        self.assertEqual(engine.sprites[0]["image"], "hero.png")

    def test_stage_script_switches_the_backdrop(self):
        backdrop = encode_rgba_png(2, 2, bytes([4, 5, 6, 255] * 4))
        project = Project(
            name="Backdrop",
            assets={"night.png": backdrop},
            backdrop="",
            scripts=[{
                "target": "stage", "x": 0, "y": 0,
                "blocks": [block("event_flag"),
                           block("looks_set_backdrop", backdrop="night.png")],
            }],
        )
        engine = PreviewEngine(project)
        engine.start()
        engine.step(0.05)
        self.assertEqual(engine.backdrop, "night.png")
        self.assertIn("night.png", engine.images)

    def test_setting_a_plain_background_clears_the_backdrop(self):
        project = Project(
            name="Background",
            scripts=[{
                "target": "stage", "x": 0, "y": 0,
                "blocks": [block("event_flag"),
                           block("looks_set_background", color="#123456")],
            }],
        )
        engine = PreviewEngine(project)
        engine.start()
        engine.step(0.05)
        self.assertEqual(engine.background, "#123456")
        self.assertEqual(engine.backdrop, "")


if __name__ == "__main__":
    unittest.main()
