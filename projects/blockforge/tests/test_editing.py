"""Tests for nested block insertion, removal, and reordering."""

import unittest

from core import Procedure, Project, Sprite, block
from editing import blocks_at, container, insert_block, move_block, remove_block


def _project():
    return Project(
        name="Editing",
        sprites=[Sprite("Hero"), Sprite("Ball")],
        scripts=[
            {"target": "spirit", "sprite": "Hero", "x": 32, "y": 32,
             "blocks": [
                 block("event_flag"),
                 block("control_repeat", times="2", children={"SUB": []}),
             ]},
            {"target": "spirit", "sprite": "Ball", "x": 32, "y": 32,
             "blocks": [
                 block("event_flag"),
             ]},
        ],
    )


class EditingTests(unittest.TestCase):
    def test_insert_into_a_nested_slot(self):
        project = _project()
        insert_block(project, 0, (("SUB", 1),), 0, "motion_move")
        self.assertEqual(container(project, 0, (("SUB", 1),))[0].type,
                         "motion_move")

    def test_procedure_bodies_use_negative_script_indexes(self):
        project = _project()
        project.procedures.append(Procedure("jump", blocks=[block("motion_move")]))
        self.assertEqual(blocks_at(project, -1), project.procedures[0].blocks)
        insert_block(project, -1, (), 1, "control_print")
        self.assertEqual(
            [item.type for item in project.procedures[0].blocks],
            ["motion_move", "control_print"],
        )
        move_block(project, (-1, (), 1), (0, (), 2))
        self.assertEqual(
            [item.type for item in project.scripts[0]["blocks"]],
            ["event_flag", "control_repeat", "control_print"],
        )
        self.assertEqual([item.type for item in project.procedures[0].blocks],
                         ["motion_move"])

    def test_remove_from_a_nested_slot(self):
        project = _project()
        insert_block(project, 0, (("SUB", 1),), 0, "motion_move")
        removed = remove_block(project, 0, (("SUB", 1),), 0)
        self.assertEqual(removed.type, "motion_move")
        self.assertEqual(container(project, 0, (("SUB", 1),)), [])

    def test_move_between_scripts(self):
        project = _project()
        move_block(project, (0, (), 1), (1, (), 1))
        self.assertEqual([item.type for item in container(project, 0, ())],
                         ["event_flag"])
        self.assertEqual([item.type for item in container(project, 1, ())],
                         ["event_flag", "control_repeat"])

    def test_move_within_one_container_adjusts_the_target_index(self):
        project = _project()
        insert_block(project, 0, (), 2, "motion_move")
        insert_block(project, 0, (), 3, "sound_stop")
        move_block(project, (0, (), 2), (0, (), 3))
        self.assertEqual(
            [item.type for item in container(project, 0, ())],
            ["event_flag", "control_repeat", "sound_stop", "motion_move"],
        )

    def test_move_into_a_later_siblings_nested_slot_adjusts_the_path(self):
        project = _project()
        insert_block(project, 0, (), 1, "motion_move")
        insert_block(project, 0, (), 2, "control_repeat")
        move_block(project, (0, (), 1), (0, (("SUB", 2),), 0))
        self.assertEqual(
            [item.type for item in container(project, 0, ())],
            ["event_flag", "control_repeat", "control_repeat"],
        )
        self.assertEqual(
            [item.type for item in container(project, 0, (("SUB", 1),))],
            ["motion_move"],
        )

    def test_move_into_the_source_blocks_own_slot_is_rejected(self):
        project = _project()
        insert_block(project, 0, (("SUB", 1),), 0, "motion_move")
        with self.assertRaises(ValueError):
            move_block(project, (0, (), 1), (0, (("SUB", 1),), 0))


if __name__ == "__main__":
    unittest.main()
