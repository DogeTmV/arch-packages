"""Offscreen smoke tests for the Scratch-like blockforge editor."""

import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QCloseEvent, QKeyEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QLabel, QLineEdit,
    QListView, QMessageBox, QPlainTextEdit, QToolButton, QWidget,
)
from PySide6.QtCore import QEvent, QPointF, QProcess, QMimeData, Qt

import theme
from core import Procedure, Project, Sprite, Variable, block, save_project
from examples import example_project
from gui import (
    MOVE_MIME,
    PALETTE_MIME,
    LibraryDialog,
    ProcedureDialog,
    ProjectSettingsDialog,
    SpriteDialog,
    MainWindow,
    heading_endpoint,
    main as gui_main,
)
from images import decode_png, encode_rgba_png
from theme import CATEGORIES


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow(example_project("hello"))

    def tearDown(self):
        self.window.dirty = False
        self.window.close()

    def test_minimal_layout_has_the_expected_panels_and_no_source_view(self):
        for name in ("palettePanel", "workspacePanel", "stagePanel",
                     "consolePanel", "toolbar"):
            self.assertIsNotNone(
                self.window.findChild(QWidget, name), "missing %s" % name)
        self.assertIsNone(self.window.findChild(QPlainTextEdit, "sourceView"))

    def test_palette_shows_section_buttons_and_plain_block_labels(self):
        buttons = [self.window.findChild(QToolButton, "category_%s" % item.key)
                   for item in CATEGORIES]
        self.assertTrue(all(buttons))
        self.assertGreaterEqual(self.window.palette_list.count(), 8)
        labels = [self.window.palette_list.item(index).text()
                  for index in range(self.window.palette_list.count())]
        self.assertTrue(any("move" in label.lower() for label in labels))
        self.assertFalse(any("a + b" in label for label in labels))
        self.assertFalse(any("random(" in label for label in labels))

    def test_theme_matches_the_scratch_3_default_palette(self):
        scratch = theme.SCRATCH
        self.assertEqual(scratch["menu"], "#855CD6")
        self.assertEqual(scratch["page"], "#E5F0FF")
        self.assertEqual(scratch["workspace"], "#F9F9F9")
        self.assertEqual(scratch["text"], "#575E75")
        self.assertEqual(scratch["selection"], "#4C97FF")
        stylesheet = self.window.styleSheet()
        self.assertIn("#855CD6", stylesheet)
        self.assertIn("#F9F9F9", stylesheet)
        self.assertNotIn("#0f1420", stylesheet)

    def test_category_colors_match_scratch_3(self):
        expected = {
            "motion": "#4C97FF",
            "looks": "#9966FF",
            "sound": "#CF63CF",
            "events": "#FFBF00",
            "control": "#FFAB19",
            "sensing": "#5CB1D6",
            "operators": "#59C059",
            "variables": "#FF8C1A",
            "pen": "#0FBD8C",
            "custom": "#FF6680",
        }
        self.assertEqual(
            {item.key: item.color for item in CATEGORIES}, expected)

    def test_category_order_matches_scratch_3(self):
        buttons = self.window.palette.category_buttons
        self.assertEqual(list(buttons), [
            "motion", "looks", "sound", "events", "control", "sensing",
            "operators", "variables", "pen", "custom",
        ])
        self.assertIsNone(self.window.findChild(QToolButton, "category_all"))

    def test_palette_blocks_show_scratch_default_values(self):
        labels = [self.window.palette_list.item(index).text()
                  for index in range(self.window.palette_list.count())]
        self.assertIn("move 10 steps", labels)
        self.assertIn("turn right 15 degrees", labels)

    def test_layout_uses_the_scratch_pane_structure(self):
        for name in ("toolboxPanel", "flyoutPanel", "workspacePanel",
                     "editorTabs", "stageHeader", "stagePane", "targetPane",
                     "stageSelector", "spritePane", "spriteInfo"):
            self.assertIsNotNone(
                self.window.findChild(QWidget, name), "missing %s" % name)

    def test_editor_tabs_match_scratch(self):
        expected = {
            "tabBlocks": "Blocks",
            "tabCostumes": "Costumes",
            "tabSounds": "Sounds",
        }
        for name, text in expected.items():
            button = self.window.findChild(QToolButton, name)
            self.assertIsNotNone(button, "missing %s" % name)
            self.assertEqual(button.text(), text)

    def test_stage_header_matches_scratch_controls(self):
        for name in ("previewButton", "stopButton", "backdropButton"):
            self.assertIsNotNone(
                self.window.findChild(QToolButton, name), "missing %s" % name)

    def test_toolbar_is_scratch_style_with_an_editable_project_title(self):
        title = self.window.findChild(QLineEdit, "projectTitle")
        self.assertIs(title, self.window.title_label)
        self.assertTrue(title.isEnabled())
        for name in ("fileMenuButton", "editMenuButton"):
            self.assertIsNotNone(self.window.findChild(QToolButton, name))

    def test_sprite_pane_uses_scratch_icon_cards(self):
        self.assertEqual(self.window.sprite_list.viewMode(), QListView.IconMode)
        self.assertEqual(self.window.sprite_list.item(0).text(),
                         self.window.project.sprites[0].name)
        stage = self.window.findChild(QToolButton, "stageSelector")
        self.assertEqual(stage.text(), "Stage")

    def test_scratch_context_menus_keep_management_actions_available(self):
        self.assertEqual(self.window.sprite_list.contextMenuPolicy(),
                         Qt.CustomContextMenu)
        self.assertEqual(self.window.palette_list.contextMenuPolicy(),
                         Qt.CustomContextMenu)
        for name in ("_show_sprite_context_menu", "_edit_variable_named",
                     "_remove_variable_named", "_edit_procedure_named",
                     "_remove_procedure_named"):
            self.assertTrue(hasattr(self.window, name), "missing %s" % name)

        self.window.project.variables.append(Variable("score", "number"))
        self.window.palette.set_category("variables")
        menu = self.window.palette._context_menu()
        self.assertEqual([action.text() for action in menu.actions()],
                         ["Rename variable", "Delete variable"])
        self.assertEqual(
            [action.text() for action in menu.actions()[0].menu().actions()],
            ["score"])
        sprite_menu = self.window._sprite_context_menu()
        self.assertEqual([action.text() for action in sprite_menu.actions()],
                         ["Edit spirit", "Remove spirit"])

    def test_project_title_can_be_edited_in_the_menu_bar(self):
        title = self.window.findChild(QLineEdit, "projectTitle")
        title.setFocus()
        title.setText("My Game")
        title.editingFinished.emit()
        self.assertEqual(self.window.project.name, "My Game")
        self.assertIn("*", title.text())

    def test_build_console_is_hidden_in_the_default_editor(self):
        self.assertTrue(self.window.console.isHidden())

    def test_block_colors_match_scratch_3(self):
        self.assertEqual(
            theme.block_colors("motion"),
            ("#4C97FF", "#4280D7", "#3373CC"),
        )
        self.assertEqual(
            theme.block_colors("looks"),
            ("#9966FF", "#855CD6", "#774DCB"),
        )

    def test_project_name_is_editable(self):
        title = self.window.findChild(QLineEdit, "projectTitle")
        self.assertEqual(title.text(), "Hello Console")

    def test_stage_paints_a_visible_spirit_without_an_exception(self):
        pixmap = QPixmap(320, 240)
        pixmap.fill()
        self.window.stage.render(pixmap)
        self.assertFalse(pixmap.isNull())

    def test_heading_indicator_points_right_at_ninety_degrees(self):
        end_x, end_y = heading_endpoint(0, 0, 90, 10)
        self.assertAlmostEqual(end_x, 10.0)
        self.assertAlmostEqual(end_y, 0.0)

    def test_inserting_a_block_appends_to_the_current_spirit_script(self):
        before = len(self.window.project.scripts[0]["blocks"])
        self.window.workspace.add_block("motion_move")
        self.assertEqual(len(self.window.project.scripts), 1)
        self.assertEqual(len(self.window.project.scripts[0]["blocks"]), before + 1)
        self.assertEqual(
            self.window.project.scripts[0]["blocks"][-1].type,
            "motion_move",
        )

    def test_selecting_the_stage_adds_blocks_to_stage_scripts(self):
        stage_script = {
            "target": "stage", "x": 32, "y": 32,
            "blocks": [block("event_flag")],
        }
        self.window.project.scripts.append(stage_script)
        self.window.set_current_target("Stage")
        self.window.workspace.rebuild()
        self.window.workspace.add_block("looks_set_backdrop")
        self.assertEqual(stage_script["blocks"][-1].type, "looks_set_backdrop")

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

    def test_spirit_selection_survives_a_project_refresh(self):
        self.window.load_example("catch")
        self.window.sprite_list.setCurrentRow(0)
        self.window._project_changed()
        self.assertEqual(self.window.sprite_list.currentRow(), 0)

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


class GuiWorkflowTests(unittest.TestCase):
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
            path = Path(folder) / "saved.bfproj"
            with mock.patch.object(
                    QFileDialog, "getSaveFileName",
                    return_value=(str(path), "Blockforge project (*.bfproj)")):
                self.assertTrue(self.window.save_project())
            self.assertFalse(self.window.dirty)
            self.assertNotIn("*", self.window.title_label.text())
            with zipfile.ZipFile(path) as archive:
                manifest = json.loads(archive.read("project.json"))
            self.assertEqual(manifest["name"], "Hello Console")

    def test_save_as_updates_the_current_project_path(self):
        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder) / "first.bfproj"
            second = Path(folder) / "second.bfproj"
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
                           path="/tmp/example.bfproj")
        try:
            self.assertEqual(other.language, "rust")
            self.assertEqual(other.project_path, "/tmp/example.bfproj")
            self.assertFalse(other.dirty)
            self.assertEqual(other.language_combo.currentText(), "Rust")
            self.assertIsNone(other.findChild(QPlainTextEdit, "sourceView"))
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

    def test_export_source_writes_a_source_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.object(QFileDialog, "getExistingDirectory",
                                   return_value=folder):
                self.window.language_combo.setCurrentText("Rust")
                self.window.export_source()
            source = (Path(folder) / "main.rs").read_text(encoding="utf-8")
            readme = (Path(folder) / "README.md").read_text(encoding="utf-8")
            self.assertTrue(source.startswith("// Generated by blockforge"))
            self.assertIn("Rust 2021", source)
            self.assertIn("rustc", readme)

    def test_library_adds_a_spirit_with_a_ready_script(self):
        def choose_ball(dialog):
            for row in range(dialog.list.count()):
                item = dialog.list.item(row)
                if item.data(Qt.UserRole) == ("spirit", "ball"):
                    dialog.list.setCurrentItem(item)
                    break
            dialog.accept()
            return 1

        before = len(self.window.project.sprites)
        with mock.patch.object(LibraryDialog, "exec", choose_ball):
            self.window.add_from_library()
        self.assertEqual(len(self.window.project.sprites), before + 1)
        spirit = self.window.project.sprites[-1]
        self.assertEqual(spirit.name, "Ball")
        scripts = [item for item in self.window.project.scripts
                   if item.get("sprite") == "Ball"]
        self.assertTrue(scripts)
        self.assertEqual(scripts[-1]["blocks"][0].type, "event_flag")
        self.assertEqual(self.window.workspace.current_target, "Ball")

    def test_library_switches_the_stage_backdrop(self):
        def choose_ocean(dialog):
            for row in range(dialog.list.count()):
                item = dialog.list.item(row)
                if item.data(Qt.UserRole) == ("stage", "ocean"):
                    dialog.list.setCurrentItem(item)
                    break
            dialog.accept()
            return 1

        with mock.patch.object(LibraryDialog, "exec", choose_ocean):
            self.window.add_from_library()
        backdrop = self.window.project.backdrop
        self.assertEqual(backdrop, "stage_ocean.png")
        self.assertIn(backdrop, self.window.project.assets)
        width, height, _ = decode_png(self.window.project.assets[backdrop])
        self.assertEqual((width, height),
                         (self.window.project.width, self.window.project.height))

    def test_spirit_dialog_imports_a_picture_into_project_assets(self):
        picture = encode_rgba_png(4, 3, bytes([10, 20, 30, 255] * 12))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "hero.png"
            path.write_bytes(picture)
            with mock.patch.object(QFileDialog, "getOpenFileName",
                                   return_value=(str(path), "")):
                dialog = SpriteDialog(names=(), assets=self.window.project.assets)
                dialog.fields["name"].setText("Look")
                dialog._choose_picture()
                self.assertEqual(dialog.sprite().image, "hero.png")
                dialog.accept()
            spirit = dialog.sprite()
        self.assertIn("hero.png", self.window.project.assets)
        width, height, _ = decode_png(self.window.project.assets["hero.png"])
        self.assertEqual((width, height), (4, 3))
        self.assertEqual(spirit.image, "hero.png")

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
        self.assertEqual(procedure.params, [{"name": "who", "type": "text"}])
        self.assertEqual(self.window.editor_target.currentText(),
                         "My Block: greet")
        self.assertEqual(self.window.workspace.current_procedure, "greet")
        self.window.workspace.add_block("control_print")
        self.assertEqual([item.type for item in procedure.blocks],
                         ["control_print"])

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
        self.assertIn("*", self.window.title_label.text())

    def test_stage_forwards_keyboard_and_mouse_input_to_preview(self):
        project = Project(
            name="Input",
            sprites=[Sprite(name="Bot")],
            scripts=[{"target": "spirit", "sprite": "Bot", "x": 0, "y": 0,
                      "blocks": [
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

    def test_invalid_project_is_reported_before_building(self):
        self.window.project.scripts[0]["sprite"] = "Ghost"
        self.window.build_project()
        self.assertIn("Cannot build", self.window.build_view.toPlainText())
        self.assertIsNone(self.window.binary_path)
        self.assertFalse(self.window.run_button.isEnabled())
        self.assertFalse(self.window.console.isHidden())

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

    def test_opening_a_malformed_project_keeps_the_current_one(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "broken.bfproj"
            save_project(self.window.project, str(path))
            with zipfile.ZipFile(path) as archive:
                payload = json.loads(archive.read("project.json"))
                assets = {name: archive.read(name)
                          for name in archive.namelist()
                          if name.startswith("assets/")}
            payload["scripts"][0]["blocks"][0]["type"] = "not_a_block"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("project.json", json.dumps(payload))
                for name, data in assets.items():
                    archive.writestr(name, data)
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
        mime = QMimeData()
        mime.setText(PALETTE_MIME + "pen_down")
        self.assertTrue(self.window.workspace.handle_drop(
            mime, 0, (("SUB", repeat_index),), 1))
        self.assertEqual(
            [item.type for item in repeat.children["SUB"]],
            ["control_print", "pen_down", "control_print"],
        )


if __name__ == "__main__":
    unittest.main()
