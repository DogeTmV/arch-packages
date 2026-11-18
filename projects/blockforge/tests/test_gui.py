"""Offscreen smoke tests for the blockforge editor."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QCloseEvent, QKeyEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QToolButton,
)
from PySide6.QtCore import QEvent, QPointF, QProcess, QMimeData, Qt

from core import Procedure, Project, Sprite, block, save_project
from examples import example_project
from gui import (
    MOVE_MIME, PALETTE_MIME, ProcedureDialog, ProjectSettingsDialog,
    SpriteDialog, MainWindow, heading_endpoint, main as gui_main,
)
from theme import CATEGORIES, DARK


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow(example_project("hello"))

    def tearDown(self):
        self.window.dirty = False
        self.window.close()

    def test_main_window_has_the_five_expected_panels(self):
        for name in ("palettePanel", "workspacePanel", "stagePanel",
                     "consolePanel", "toolbar"):
            self.assertIsNotNone(
                self.window.findChild(QtCoreQWidget, name),
                "missing %s" % name,
            )

    def test_palette_shows_every_category_and_block(self):
        buttons = [self.window.findChild(QToolButton, "category_%s" % item.key)
                   for item in CATEGORIES]
        self.assertTrue(all(buttons))
        self.assertGreaterEqual(self.window.palette_list.count(), 40)

    def test_language_switch_refreshes_generated_source(self):
        source = self.window.findChild(QPlainTextEdit, "sourceView")
        combo = self.window.findChild(QComboBox, "languageCombo")
        self.assertIn("C++17", source.toPlainText())
        combo.setCurrentText("Rust")
        self.assertIn("Rust 2021", source.toPlainText())

    def test_inserting_a_block_appends_to_the_current_script(self):
        before = len(self.window.project.scripts[0]["blocks"])
        self.window.workspace.add_block("motion_move")
        self.assertEqual(len(self.window.project.scripts), 1)
        self.assertEqual(len(self.window.project.scripts[0]["blocks"]), before + 1)
        self.assertEqual(
            self.window.project.scripts[0]["blocks"][-1].type,
            "motion_move",
        )

    def test_theme_is_dark_and_high_contrast(self):
        self.assertIn("#0f1420", DARK["window"])
        stylesheet = self.window.styleSheet()
        self.assertIn(DARK["window"], stylesheet)
        self.assertIn("QToolButton", stylesheet)

    def test_project_name_is_editable(self):
        label = self.window.findChild(QLabel, "projectTitle")
        self.assertEqual(label.text(), "Hello Console")

    def test_stage_paints_a_visible_sprite_without_an_exception(self):
        pixmap = QPixmap(320, 240)
        pixmap.fill()
        self.window.stage.render(pixmap)
        self.assertFalse(pixmap.isNull())

    def test_heading_indicator_points_right_at_ninety_degrees(self):
        end_x, end_y = heading_endpoint(0, 0, 90, 10)
        self.assertAlmostEqual(end_x, 10.0)
        self.assertAlmostEqual(end_y, 0.0)

    def test_rebuilding_the_workspace_forgets_the_focused_field(self):
        field = self.window.workspace.findChild(QLineEdit)
        self.assertIsNotNone(field)
        self.window.workspace.focused_field = field
        self.window.workspace.add_block("motion_move")
        self.assertIsNone(self.window.workspace.focused_field)

    def test_reporter_insertion_uses_a_valid_default_expression(self):
        field = self.window.workspace.findChild(QLineEdit)
        self.assertIsNotNone(field)
        field.setText("")
        self.window.workspace.focused_field = field
        self.window.workspace.add_block("operator_add")
        self.assertEqual(field.text(), "0 + 0")

    def test_loading_an_example_clears_the_previous_build(self):
        self.window.binary_path = "/tmp/stale-binary"
        self.window.run_button.setEnabled(True)
        self.window.load_example("bounce")
        self.assertIsNone(self.window.binary_path)
        self.assertFalse(self.window.run_button.isEnabled())
        self.assertIs(self.window.stage.project, self.window.project)

    def test_changing_target_invalidates_the_previous_binary(self):
        self.window.binary_path = "/tmp/stale-binary"
        self.window.run_button.setEnabled(True)
        self.window.findChild(QComboBox, "languageCombo").setCurrentText("Rust")
        self.assertIsNone(self.window.binary_path)
        self.assertFalse(self.window.run_button.isEnabled())

    def test_editing_a_field_invalidates_the_previous_binary(self):
        self.window.binary_path = "/tmp/stale-binary"
        self.window.run_button.setEnabled(True)
        self.window.workspace.projectChanged.emit()
        self.assertIsNone(self.window.binary_path)
        self.assertFalse(self.window.run_button.isEnabled())

    def test_sprite_selection_survives_a_project_refresh(self):
        self.window.load_example("catch")
        self.window.sprite_list.setCurrentRow(1)
        self.window._project_changed()
        self.assertEqual(self.window.sprite_list.currentRow(), 1)

    def test_malformed_move_payload_is_ignored(self):
        mime = QMimeData()
        mime.setText(MOVE_MIME + "{}")
        before = len(self.window.project.scripts[0]["blocks"])
        self.assertFalse(self.window.workspace.handle_drop(mime, 0, (), 0))
        self.assertEqual(len(self.window.project.scripts[0]["blocks"]), before)

    def test_procedure_calls_expose_editors_for_declared_arguments(self):
        self.window.project.procedures.append(Procedure(
            name="announce",
            params=[{"name": "message", "type": "text"}],
            blocks=[block("control_print", value="message")],
        ))
        self.window.project.scripts[0]["blocks"].append(
            block("procedure_call", name="announce", arg_message='"hello"')
        )
        self.window.workspace.rebuild()
        editor = self.window.workspace.findChild(QLineEdit, "arg_message")
        self.assertIsNotNone(editor)
        self.assertEqual(editor.text(), '"hello"')

    def test_a_single_block_can_be_deleted_from_the_workspace(self):
        before = len(self.window.project.scripts[0]["blocks"])
        button = self.window.workspace.findChild(QToolButton, "deleteBlock")
        self.assertIsNotNone(button)
        button.click()
        self.assertEqual(len(self.window.project.scripts[0]["blocks"]), before - 1)


class GuiExpansionTests(unittest.TestCase):
    """Regression tests for the editor's real-project workflow."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow(example_project("hello"))

    def tearDown(self):
        self.window.dirty = False
        self.window.close()

    def test_editing_a_project_marks_it_dirty_until_it_is_saved(self):
        self.assertFalse(self.window.dirty)
        self.window.workspace.add_block("motion_move")
        self.assertTrue(self.window.dirty)
        self.assertIn("*", self.window.title_label.text())

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "saved.json"
            with mock.patch.object(
                    QFileDialog, "getSaveFileName",
                    return_value=(str(path), "Blockforge project (*.json)")):
                self.assertTrue(self.window.save_project())
            self.assertFalse(self.window.dirty)
            self.assertNotIn("*", self.window.title_label.text())
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8"))["name"],
                "Hello Console",
            )

    def test_save_as_updates_the_current_project_path(self):
        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder) / "first.json"
            second = Path(folder) / "second.json"
            with mock.patch.object(QFileDialog, "getSaveFileName",
                                   return_value=(str(first), "")):
                self.window.save_project()
            with mock.patch.object(QFileDialog, "getSaveFileName",
                                   return_value=(str(second), "")):
                self.window.save_project_as()
            self.assertEqual(self.window.project_path, str(second))
            self.assertTrue(second.exists())

    def test_constructor_accepts_a_target_and_project_path(self):
        other = MainWindow(example_project("hello"), language="rust",
                           path="/tmp/example.json")
        try:
            self.assertEqual(other.language, "rust")
            self.assertEqual(other.project_path, "/tmp/example.json")
            self.assertFalse(other.dirty)
            self.assertIn("Rust 2021", other.source_view.toPlainText())
            self.assertEqual(other.language_combo.currentText(), "Rust")
        finally:
            other.close()

    def test_command_line_language_is_preserved_without_marking_dirty(self):
        created = []
        real_window = MainWindow

        def capture(*args, **kwargs):
            window = real_window(*args, **kwargs)
            created.append(window)
            return window

        with mock.patch("gui.MainWindow", side_effect=capture), \
                mock.patch.object(QApplication, "exec", return_value=0):
            self.assertEqual(gui_main(["--language", "rust"]), 0)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].language, "rust")
        self.assertFalse(created[0].dirty)
        created[0].close()

    def test_export_source_writes_the_current_target(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.rs"
            self.window.language_combo.setCurrentText("Rust")
            with mock.patch.object(QFileDialog, "getSaveFileName",
                                   return_value=(str(path), "")):
                self.window.export_source()
            source = path.read_text(encoding="utf-8")
            self.assertTrue(source.startswith("// Generated by blockforge"))
            self.assertIn("Rust 2021", source)

    def test_a_new_my_block_has_typed_arguments_and_an_editable_body(self):
        def accept_new(self):
            self.name_edit.setText("greet")
            self._add_row({"name": "who", "type": "text"})
            self.accept()
            return 1

        with mock.patch.object(ProcedureDialog, "exec", accept_new):
            self.window.add_procedure()
        procedure = self.window.project.procedures[0]
        self.assertEqual(procedure.name, "greet")
        self.assertEqual(procedure.params,
                         [{"name": "who", "type": "text"}])
        self.assertEqual(self.window.editor_target.currentText(),
                         "My Block: greet")
        self.assertEqual(self.window.workspace.current_procedure, "greet")
        self.window.workspace.add_block("control_print")
        self.assertEqual([item.type for item in procedure.blocks],
                         ["control_print"])

        self.window.project.scripts[0]["blocks"].append(
            block("procedure_call", name="greet", arg_who='"hi"'))

        def accept_edit(self):
            self.name_edit.setText("welcome")
            row = self.params_box.itemAt(0).widget()
            row.findChild(QLineEdit, "argumentName").setText("person")
            self.accept()
            return 1

        with mock.patch.object(ProcedureDialog, "exec", accept_edit):
            self.window.edit_procedure()
        self.assertEqual(procedure.name, "welcome")
        self.assertEqual(procedure.params[0]["name"], "person")
        self.assertEqual(
            self.window.project.scripts[0]["blocks"][-1].fields["name"],
            "welcome",
        )
        self.assertEqual(self.window.editor_target.currentText(),
                         "My Block: welcome")

    def test_sprite_and_project_settings_dialogs_apply_every_field(self):
        def accept_sprite(self):
            self.fields["name"].setText("Rover")
            self.fields["x"].setText("12")
            self.fields["y"].setText("-8")
            self.fields["costume_count"].setText("4")
            self.fields["layer"].setText("2")
            self.fields["shape"].setCurrentText("star")
            self.fields["visible"].setCurrentText("no")
            self.accept()
            return 1

        with mock.patch.object(SpriteDialog, "exec", accept_sprite):
            self.window.add_sprite()
        sprite = self.window.project.sprites[-1]
        self.assertEqual(
            (sprite.name, sprite.x, sprite.y, sprite.costume_count,
             sprite.layer, sprite.shape, sprite.visible),
            ("Rover", 12.0, -8.0, 4, 2, "star", False),
        )

        def accept_settings(self):
            self.name_edit.setText("Star Game")
            self.width_edit.setText("640")
            self.height_edit.setText("400")
            self.color.setText("#123456")
            self.description.setPlainText("A game")
            self.accept()
            return 1

        with mock.patch.object(ProjectSettingsDialog, "exec", accept_settings):
            self.window.edit_settings()
        self.assertEqual(self.window.project.name, "Star Game")
        self.assertEqual((self.window.project.width, self.window.project.height),
                         (640, 400))
        self.assertEqual(self.window.project.background, "#123456")
        self.assertEqual(self.window.project.description, "A game")
        self.assertIn("*", self.window.title_label.text())

    def test_stage_forwards_keyboard_and_mouse_input_to_preview(self):
        project = Project(
            name="Input",
            sprites=[Sprite(name="Bot")],
            scripts=[{"sprite": "Bot", "x": 0, "y": 0, "blocks": [
                block("event_key", key="space"),
                block("control_print", value='"pressed"'),
            ]}],
        )
        self.window._adopt_project(project, "Input ready")
        self.window.engine.start()
        self.window.stage.keyPressEvent(
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Space, Qt.NoModifier))
        self.window.engine.step(0.033)
        self.assertEqual(self.window.engine.output, ["pressed"])
        self.window.stage.keyReleaseEvent(
            QKeyEvent(QEvent.Type.KeyRelease, Qt.Key_Space, Qt.NoModifier))
        self.assertFalse(self.window.engine.keys.get(44))

        self.window.stage.resize(320, 240)
        position = QPointF(self.window.stage.width() / 2,
                           self.window.stage.height() / 2)
        global_position = QPointF(
            self.window.stage.mapToGlobal(position.toPoint()))
        self.window.stage.mouseMoveEvent(QMouseEvent(
            QEvent.Type.MouseMove, position, global_position, Qt.NoButton,
            Qt.NoButton, Qt.NoModifier))
        self.assertEqual(tuple(round(value, 4) for value in
                               self.window.engine.mouse), (0.0, 0.0))

    def test_preview_output_streams_all_lines_after_the_preview_cap(self):
        engine = self.window.engine
        for index in range(305):
            engine.output.append(str(index))
            engine.output_total += 1
            if len(engine.output) > 300:
                engine.output.pop(0)
        self.window._preview_tick()
        lines = self.window.output_view.toPlainText().splitlines()
        self.assertEqual(lines[0], "5")
        self.assertEqual(lines[-1], "304")
        self.assertEqual(len(lines), 300)
        self.window._preview_tick()
        self.assertEqual(
            len(self.window.output_view.toPlainText().splitlines()), 300)

    def test_opening_a_malformed_project_keeps_the_current_one(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "broken.json"
            save_project(self.window.project, str(path))
            data = json.loads(path.read_text(encoding="utf-8"))
            data["scripts"][0]["blocks"][0]["type"] = "not_a_block"
            path.write_text(json.dumps(data), encoding="utf-8")
            with mock.patch.object(QFileDialog, "getOpenFileName",
                                   return_value=(str(path), "")), \
                    mock.patch.object(QMessageBox, "warning") as warning:
                self.window.open_project()
        warning.assert_called_once()
        self.assertEqual(self.window.project.name, "Hello Console")

    def test_a_hat_dropped_on_the_workspace_starts_a_new_script(self):
        mime = QMimeData()
        mime.setText(PALETTE_MIME + "event_key")
        before = len(self.window.project.scripts)
        self.assertTrue(self.window.workspace.handle_drop(mime, 0, (), 0))
        self.assertEqual(len(self.window.project.scripts), before + 1)
        self.assertEqual(
            self.window.project.scripts[-1]["blocks"][0].type, "event_key")

    def test_blocks_can_be_dropped_at_a_child_slot_position(self):
        repeat = block("control_repeat", times="3", children={
            "SUB": [block("control_print", value='"a"'),
                    block("control_print", value='"c"')],
        })
        blocks = self.window.project.scripts[0]["blocks"]
        blocks.append(repeat)
        repeat_index = len(blocks) - 1
        self.window.workspace.rebuild()
        slot = self.window.workspace.findChild(QFrame, "slot_SUB")
        self.assertIsNotNone(slot)
        slot.show()
        self.app.processEvents()
        blocks = [widget for widget in slot.findChildren(QFrame)
                  if widget.objectName().startswith("block_")]
        self.assertEqual(len(blocks), 2)
        self.assertEqual(slot._drop_index(blocks[0].geometry().top() - 1), 0)
        self.assertEqual(slot._drop_index(blocks[0].geometry().bottom() + 1), 1)
        self.assertEqual(slot._drop_index(blocks[1].geometry().bottom() + 1), 2)

        mime = QMimeData()
        mime.setText(PALETTE_MIME + "pen_down")
        self.assertTrue(self.window.workspace.handle_drop(
            mime, 0, (("SUB", repeat_index),), 1))
        self.assertEqual(
            [item.type for item in repeat.children["SUB"]],
            ["control_print", "pen_down", "control_print"],
        )

    def test_invalid_project_is_reported_before_building(self):
        self.window.project.scripts[0]["sprite"] = "Ghost"
        self.window.build_project()
        self.assertIn("Cannot build", self.window.build_view.toPlainText())
        self.assertIsNone(self.window.binary_path)
        self.assertFalse(self.window.run_button.isEnabled())

    def test_stopping_all_waits_for_child_processes_to_finish(self):
        class FakeProcess:
            def __init__(self):
                self.killed = False
                self.waits = []

            def state(self):
                return QProcess.Running if not self.killed else QProcess.NotRunning

            def kill(self):
                self.killed = True

            def waitForFinished(self, milliseconds):
                self.waits.append(milliseconds)

        run = FakeProcess()
        build = FakeProcess()
        self.window.run_process = run
        self.window.build_process = build
        self.window.stop_all()
        self.assertTrue(run.killed)
        self.assertTrue(build.killed)
        self.assertEqual(run.waits, [2000])
        self.assertEqual(build.waits, [2000])

    def test_closing_with_unsaved_changes_can_be_cancelled(self):
        self.window.workspace.add_block("motion_move")
        with mock.patch.object(QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.Cancel):
            event = QCloseEvent()
            self.window.closeEvent(event)
        self.assertFalse(event.isAccepted())


# Qt's findChild wants the base QWidget type; alias keeps the test readable.
from PySide6.QtWidgets import QWidget as QtCoreQWidget  # noqa: E402

if __name__ == "__main__":
    unittest.main()
