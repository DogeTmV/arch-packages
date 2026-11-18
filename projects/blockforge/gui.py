"""PySide6 editor for blockforge.

The editor is intentionally a real IDE rather than a demo: projects can be
edited, saved, previewed on the stage, compiled to C++ or Rust, and launched as
standalone SDL2 programs.  All build/run work uses argument lists and QProcess;
no shell is involved.
"""

import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile

from PySide6.QtCore import (
    QEvent, QRectF, Qt, QTimer, QPoint, QRegularExpression, QSize, QProcess,
    QProcessEnvironment, Signal,
)
from PySide6.QtGui import (
    QAction, QBrush, QColor, QDoubleValidator, QDrag, QFontMetrics, QIntValidator,
    QKeySequence, QPainter, QPainterPath, QPen, QPixmap,
    QRegularExpressionValidator, QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QStyledItemDelegate, QTabWidget, QToolBar, QToolButton, QVBoxLayout, QWidget,
)

import theme
from compiler import ValidationError, build_command, generate_source
from core import (
    BLOCKS, CATEGORIES, FieldDef, Procedure, Project, Sprite, Variable,
    argument_default, block, load_project, save_project, validate_project,
)
from editing import blocks_at, container, insert_block, move_block, remove_block
from examples import EXAMPLE_LABELS, EXAMPLES, example_project
from preview import PreviewEngine

PALETTE_MIME = "blockforge:palette:"
MOVE_MIME = "blockforge:move:"

# Reporters insert expressions, so the palette must supply a valid default
# rather than the human-readable template (which mentions undefined names).
REPORTER_DEFAULTS = {
    "sensing_key_pressed": 'key pressed("space")',
    "sensing_touching_edge": "touching edge",
    "sensing_touching_sprite": "touching edge",
    "sensing_x_position": "x position",
    "sensing_y_position": "y position",
    "sensing_direction": "direction",
    "sensing_costume": "costume",
    "sensing_size": "size",
    "sensing_timer": "timer",
    "sensing_mouse_x": "mouse x",
    "sensing_mouse_y": "mouse y",
    "operator_add": "0 + 0",
    "operator_subtract": "0 - 0",
    "operator_multiply": "0 * 0",
    "operator_divide": "0 / 1",
    "operator_mod": "0 % 1",
    "operator_random": "random(1, 10)",
    "operator_gt": "0 > 0",
    "operator_lt": "0 < 0",
    "operator_equal": "0 == 0",
    "operator_and": "false and false",
    "operator_or": "false or false",
    "operator_not": "not false",
    "operator_join": 'join("hello ", "world")',
    "operator_length": 'len("text")',
}


def heading_endpoint(x, y, degrees, length):
    """Return the stage-space end of a Scratch-style heading indicator."""
    radians = math.radians(degrees)
    return (x + math.sin(radians) * length, y - math.cos(radians) * length)


def _hex(color):
    return QColor(color).name()


def _category_color(block_type, fallback=None):
    definition = BLOCKS.get(block_type)
    return theme.category_color(definition.category if definition else None,
                                fallback or theme.DARK["accent"])


def _template_label(definition):
    text = definition.template
    for field in definition.fields:
        text = text.replace("{%s}" % field.name, "▭")
    return text.replace("{", "").replace("}", "")


class PaletteDelegate(QStyledItemDelegate):
    """Paint palette entries as rounded, category-colored puzzle pieces."""

    def paint(self, painter, option, index):
        color = QColor(index.data(Qt.UserRole + 1) or theme.DARK["accent"])
        rect = option.rect.adjusted(3, 2, -3, -2)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        background = theme.shade(color, -0.62)
        painter.setPen(QPen(color, 1.2))
        painter.setBrush(QBrush(background))
        painter.drawRoundedRect(rect, 9, 9)
        painter.fillRect(rect.left() + 4, rect.top() + 4, 5, rect.height() - 8,
                         QBrush(color))
        painter.setPen(QColor(theme.DARK["text"]))
        metrics = QFontMetrics(painter.font())
        text = metrics.elidedText(index.data(Qt.DisplayRole) or "",
                                 Qt.ElideRight, rect.width() - 24)
        painter.drawText(rect.adjusted(14, 0, -8, 0), Qt.AlignVCenter, text)
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(10, 34)


class PaletteList(QListWidget):
    """List widget that starts a block drag from the pressed entry."""

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.position().toPoint())
            if item is not None:
                self.setCurrentItem(item)
        super().mousePressEvent(event)

    def startDrag(self, supported_actions):
        item = self.currentItem()
        if item is None:
            return
        drag = QDrag(self)
        drag.setMimeData(BlockPalette._mime(
            PALETTE_MIME + item.data(Qt.UserRole)
        ))
        drag.setPixmap(BlockPalette._drag_pixmap(item))
        drag.setHotSpot(QPoint(12, 14))
        drag.exec(Qt.CopyAction)


class BlockPalette(QWidget):
    """Category tabs and draggable block previews."""

    blockRequested = Signal(str)

    def __init__(self, project):
        super().__init__()
        self.project = project
        self.active_category = None
        self.setObjectName("palettePanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(9)

        layout.addWidget(self._label("Blocks", "sectionTitle"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search blocks…")
        self.search.setObjectName("blockSearch")
        self.search.textChanged.connect(self._refresh_list)
        layout.addWidget(self.search)

        grid = QGridLayout()
        grid.setSpacing(5)
        all_button = QToolButton()
        all_button.setText("All")
        all_button.setObjectName("category_all")
        all_button.setCheckable(True)
        all_button.setChecked(True)
        all_button.clicked.connect(lambda: self.set_category(None))
        grid.addWidget(all_button, 0, 0)
        for index, category in enumerate(CATEGORIES):
            button = QToolButton()
            button.setText(category.name)
            button.setObjectName("category_%s" % category.key)
            button.setCheckable(True)
            button.setToolTip(category.help or category.name)
            button.clicked.connect(
                lambda checked, key=category.key: self.set_category(key)
            )
            grid.addWidget(button, (index + 1) // 3, (index + 1) % 3)
        self.category_buttons = [all_button] + [
            self.findChild(QToolButton, "category_%s" % item.key)
            for item in CATEGORIES
        ]
        layout.addLayout(grid)

        self.palette_list = PaletteList()
        self.palette_list.setObjectName("paletteList")
        self.palette_list.setItemDelegate(PaletteDelegate())
        self.palette_list.setDragEnabled(True)
        self.palette_list.setDefaultDropAction(Qt.CopyAction)
        self.palette_list.itemActivated.connect(
            lambda item: self.blockRequested.emit(item.data(Qt.UserRole))
        )
        layout.addWidget(self.palette_list, 1)
        layout.addWidget(self._label(
            "Drag a block into the workspace, or double-click to add it.", "hint"
        ))
        self._refresh_list()

    @staticmethod
    def _label(text, object_name):
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        return label

    def set_category(self, key):
        self.active_category = key
        for button in self.category_buttons:
            if button is None:
                continue
            name = button.objectName()
            expected = "category_all" if key is None else "category_%s" % key
            button.setChecked(name == expected)
        self._refresh_list()

    def _refresh_list(self):
        query = self.search.text().strip().lower()
        self.palette_list.clear()
        for definition in BLOCKS.values():
            if self.active_category and definition.category != self.active_category:
                continue
            label = _template_label(definition)
            if query and query not in label.lower() and \
                    query not in definition.type.lower():
                continue
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, definition.type)
            item.setData(Qt.UserRole + 1,
                         theme.category_color(definition.category))
            item.setToolTip(definition.help or label)
            self.palette_list.addItem(item)

    @staticmethod
    def _mime(text):
        from PySide6.QtCore import QMimeData
        mime = QMimeData()
        mime.setText(text)
        return mime

    @staticmethod
    def _drag_pixmap(item):
        pixmap = QPixmap(220, 30)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(item.data(Qt.UserRole + 1))
        painter.setBrush(theme.shade(color, -0.55))
        painter.setPen(QPen(color, 1.5))
        painter.drawRoundedRect(0, 1, 219, 27, 8, 8)
        painter.setPen(QColor(theme.DARK["text"]))
        painter.drawText(pixmap.rect().adjusted(10, 0, -6, 0),
                         Qt.AlignVCenter, item.text())
        painter.end()
        return pixmap


class ColorField(QWidget):
    """A text field with a color-picker button."""

    textChanged = Signal(str)

    def __init__(self, value, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.edit = QLineEdit(str(value))
        self.edit.textChanged.connect(self.textChanged.emit)
        self.button = QPushButton("…")
        self.button.setObjectName("colorButton")
        self.button.setMaximumWidth(28)
        self.button.clicked.connect(self._choose)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.button)

    def text(self):
        return self.edit.text()

    def setText(self, value):
        self.edit.setText(str(value))

    def _choose(self):
        color = QColorDialog.getColor(QColor(self.text() or "#7c6cff"), self)
        if color.isValid():
            self.setText(color.name())


def _identifier_validator():
    """Validator shared by every dialog that creates a generated identifier."""
    return QRegularExpressionValidator(
        QRegularExpression(r"^[A-Za-z_][A-Za-z_0-9]*$")
    )


def _dialog_buttons(dialog):
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    return buttons


class ProcedureDialog(QDialog):
    """Create or edit a custom block and its typed parameters."""

    def __init__(self, procedure=None, names=(), parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit My Block" if procedure else "New My Block")
        self.original_name = procedure.name if procedure else None
        self.names = set(names)
        if self.original_name:
            self.names.discard(self.original_name)
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(procedure.name if procedure else "")
        self.name_edit.setObjectName("procedureName")
        self.name_edit.setValidator(_identifier_validator())
        layout.addRow("Name", self.name_edit)

        layout.addRow(QLabel("Arguments"))
        self.params_box = QVBoxLayout()
        controls = QVBoxLayout()
        controls.addLayout(self.params_box)
        add = QPushButton("+ Argument")
        add.setObjectName("addArgument")
        add.clicked.connect(lambda: self._add_row())
        controls.addWidget(add)
        layout.addRow(controls)
        for param in procedure.params if procedure else []:
            self._add_row(param)
        layout.addRow(_dialog_buttons(self))

    def _add_row(self, param=None):
        row = QWidget()
        item = QHBoxLayout(row)
        item.setContentsMargins(0, 0, 0, 0)
        name = QLineEdit((param or {}).get("name", "value"))
        name.setObjectName("argumentName")
        name.setValidator(_identifier_validator())
        kind = QComboBox()
        kind.setObjectName("argumentType")
        kind.addItems(["number", "text", "bool"])
        kind.setCurrentText((param or {}).get("type", "number"))
        remove = QToolButton()
        remove.setText("✕")
        remove.setToolTip("Remove argument")
        remove.clicked.connect(lambda: (self.params_box.removeWidget(row),
                                        row.deleteLater()))
        item.addWidget(name, 1)
        item.addWidget(kind)
        item.addWidget(remove)
        self.params_box.addWidget(row)

    def values(self):
        params = []
        for index in range(self.params_box.count()):
            row = self.params_box.itemAt(index).widget()
            if row is None:
                continue
            params.append({
                "name": row.findChild(QLineEdit, "argumentName").text().strip(),
                "type": row.findChild(QComboBox, "argumentType").currentText(),
            })
        return self.name_edit.text().strip(), params

    def accept(self):
        name, params = self.values()
        if not name or any(name == existing for existing in self.names):
            QMessageBox.warning(self, "My Block", "Choose a unique block name.")
            return
        reserved = {"app", "sprite"}
        seen = set()
        for param in params:
            item = param["name"]
            if not item or item in seen or item in reserved or \
                    item.startswith("bf_"):
                QMessageBox.warning(
                    self, "My Block",
                    "Argument names must be unique and cannot be reserved.",
                )
                return
            seen.add(item)
        super().accept()


class SpriteDialog(QDialog):
    """Edit every persisted property of a sprite."""

    def __init__(self, sprite=None, names=(), parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sprite properties")
        self.original_name = sprite.name if sprite else None
        self.names = set(names)
        if self.original_name:
            self.names.discard(self.original_name)
        sprite = sprite or Sprite()
        layout = QFormLayout(self)
        self.fields = {}
        self.fields["name"] = QLineEdit(sprite.name)
        self.fields["name"].setObjectName("spriteName")
        self.fields["name"].setValidator(_identifier_validator())
        layout.addRow("Name", self.fields["name"])
        for key, label in (("x", "X"), ("y", "Y"), ("size", "Size (%)"),
                           ("direction", "Direction")):
            field = QLineEdit(str(getattr(sprite, key)))
            field.setObjectName("sprite_%s" % key)
            field.setValidator(QDoubleValidator(-100000.0, 100000.0, 3, field))
            self.fields[key] = field
            layout.addRow(label, field)
        for key, label in (("costume", "Costume"),
                           ("costume_count", "Costume count"),
                           ("layer", "Layer")):
            field = QLineEdit(str(getattr(sprite, key)))
            field.setObjectName("sprite_%s" % key)
            field.setValidator(QIntValidator(-100000, 100000, field))
            self.fields[key] = field
            layout.addRow(label, field)
        shape = QComboBox()
        shape.setObjectName("spriteShape")
        shape.addItems(["circle", "rect", "triangle", "star"])
        shape.setCurrentText(sprite.shape)
        self.fields["shape"] = shape
        layout.addRow("Shape", shape)
        color = ColorField(sprite.color)
        color.setObjectName("spriteColor")
        self.fields["color"] = color
        layout.addRow("Color", color)
        visible = QComboBox()
        visible.setObjectName("spriteVisible")
        visible.addItems(["yes", "no"])
        visible.setCurrentText("yes" if sprite.visible else "no")
        self.fields["visible"] = visible
        layout.addRow("Visible", visible)
        layout.addRow(_dialog_buttons(self))

    def sprite(self):
        def number(key, default=0.0):
            try:
                return float(self.fields[key].text())
            except ValueError:
                return default

        def integer(key, default=1):
            try:
                return int(self.fields[key].text())
            except ValueError:
                return default

        return Sprite(
            name=self.fields["name"].text().strip(),
            x=number("x"), y=number("y"),
            size=number("size", 100.0), direction=number("direction", 90.0),
            costume=integer("costume", 1),
            costume_count=max(1, integer("costume_count", 2)),
            layer=integer("layer"),
            shape=self.fields["shape"].currentText(),
            color=self.fields["color"].text(),
            visible=self.fields["visible"].currentText() == "yes",
        )

    def accept(self):
        if self.sprite().name in self.names:
            QMessageBox.warning(self, "Sprite properties",
                                "That sprite name is already used.")
            return
        super().accept()


class VariableDialog(QDialog):
    """Create or rename a typed variable."""

    def __init__(self, variable=None, names=(), parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit variable" if variable else "New variable")
        self.original_name = variable.name if variable else None
        self.names = set(names)
        if self.original_name:
            self.names.discard(self.original_name)
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(variable.name if variable else "")
        self.name_edit.setObjectName("variableName")
        self.name_edit.setValidator(_identifier_validator())
        self.kind = QComboBox()
        self.kind.setObjectName("variableType")
        self.kind.addItems(["number", "text", "bool"])
        if variable:
            self.kind.setCurrentText(variable.type)
        layout.addRow("Name", self.name_edit)
        layout.addRow("Type", self.kind)
        layout.addRow(_dialog_buttons(self))

    def values(self):
        return self.name_edit.text().strip(), self.kind.currentText()

    def accept(self):
        name, _ = self.values()
        if not name or name in self.names:
            QMessageBox.warning(self, "Variable", "Choose a unique variable name.")
            return
        super().accept()


class ProjectSettingsDialog(QDialog):
    """Edit the project name, stage size, background, and description."""

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project settings")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(project.name)
        self.name_edit.setObjectName("settingsName")
        layout.addRow("Name", self.name_edit)
        self.width_edit = QLineEdit(str(project.width))
        self.width_edit.setObjectName("settingsWidth")
        self.width_edit.setValidator(QIntValidator(1, 4096, self))
        self.height_edit = QLineEdit(str(project.height))
        self.height_edit.setObjectName("settingsHeight")
        self.height_edit.setValidator(QIntValidator(1, 4096, self))
        layout.addRow("Stage width", self.width_edit)
        layout.addRow("Stage height", self.height_edit)
        self.color = ColorField(project.background)
        self.color.setObjectName("settingsBackground")
        layout.addRow("Background", self.color)
        self.description = QPlainTextEdit(project.description)
        self.description.setObjectName("settingsDescription")
        self.description.setMaximumHeight(90)
        layout.addRow("Description", self.description)
        layout.addRow(_dialog_buttons(self))

    def accept(self):
        try:
            width = int(self.width_edit.text())
            height = int(self.height_edit.text())
        except ValueError:
            QMessageBox.warning(self, "Project settings",
                                "Stage dimensions must be whole numbers.")
            return
        if not 1 <= width <= 4096 or not 1 <= height <= 4096:
            QMessageBox.warning(self, "Project settings",
                                "Stage dimensions must be between 1 and 4096.")
            return
        super().accept()


class BlockWidget(QFrame):
    """One editable block in a script stack."""

    def __init__(self, item, workspace, script_index, path, index):
        super().__init__()
        self.item = item
        self.workspace = workspace
        self.script_index = script_index
        self.path = path
        self.index = index
        self.definition = BLOCKS[item.type]
        self.field_editors = {}
        self._drag_origin = None
        self.setObjectName("block_%s" % item.type)
        color = _category_color(item.type)
        self.setStyleSheet(
            "QFrame#block_%s { background: %s; border: 1px solid %s;"
            "border-left: 5px solid %s; border-radius: 8px; margin: 2px; }"
            % (item.type, _hex(theme.shade(color, -0.70)), _hex(theme.shade(color, -0.3)),
               _hex(color))
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 6, 9, 7)
        layout.setSpacing(5)
        header_row = QHBoxLayout()
        header = QLabel(_template_label(self.definition))
        header.setStyleSheet("color: %s; font-weight: 700;" % _hex(color))
        header.setWordWrap(True)
        header_row.addWidget(header, 1)
        if not self.definition.hat:
            remove = QToolButton()
            remove.setText("✕")
            remove.setToolTip("Delete this block")
            remove.setObjectName("deleteBlock")
            remove.clicked.connect(lambda: self.workspace.delete_block(
                self.script_index, self.path, self.index
            ))
            header_row.addWidget(remove)
        layout.addLayout(header_row)

        definitions = list(self.definition.fields)
        if self.item.type == "procedure_call":
            procedure = next(
                (p for p in self.workspace.project.procedures
                 if p.name == self.item.fields.get("name")), None
            )
            if procedure:
                definitions.extend(FieldDef(
                    "arg_%s" % param["name"], "text",
                    argument_default(param), param["name"],
                ) for param in procedure.params)
        if definitions:
            fields = QGridLayout()
            fields.setSpacing(4)
            for row, field in enumerate(definitions):
                fields.addWidget(QLabel(field.label), row, 0)
                editor = self._editor_for(field)
                editor.setObjectName(field.name)
                self.field_editors[field.name] = editor
                fields.addWidget(editor, row, 1)
            layout.addLayout(fields)

        for slot in self.definition.slots:
            slot_path = self.path + ((slot, self.index),)
            layout.addWidget(SlotWidget(slot, self.workspace, self.script_index,
                                        slot_path, item))

    def _editor_for(self, field):
        value = self.item.fields.get(field.name, field.default)
        if field.kind == "choice":
            editor = QComboBox()
            editor.addItems(field.options or [])
            editor.setCurrentText(str(value))
            editor.currentTextChanged.connect(
                lambda text, name=field.name: self._set_field(name, text)
            )
        elif field.kind == "key":
            from expressions import KEYS
            editor = QComboBox()
            editor.addItems(sorted(KEYS))
            editor.setCurrentText(str(value))
            editor.currentTextChanged.connect(
                lambda text, name=field.name: self._set_field(name, text)
            )
        elif field.kind == "target":
            editor = QComboBox()
            editor.addItems(["mouse"] + [s.name for s in self.workspace.project.sprites])
            editor.setCurrentText(str(value))
            editor.currentTextChanged.connect(
                lambda text, name=field.name: self._set_field(name, text)
            )
        elif field.kind == "variable":
            editor = QComboBox()
            editor.addItems([v.name for v in self.workspace.project.variables])
            editor.setCurrentText(str(value))
            editor.currentTextChanged.connect(
                lambda text, name=field.name: self._set_field(name, text)
            )
        elif field.kind == "procedure":
            editor = QComboBox()
            editor.addItems([p.name for p in self.workspace.project.procedures])
            editor.setCurrentText(str(value))
            editor.currentTextChanged.connect(
                lambda text, name=field.name: self._set_field(name, text)
            )
        elif field.kind == "color":
            editor = ColorField(value)
            editor.textChanged.connect(
                lambda text, name=field.name: self._set_field(name, text)
            )
        else:
            editor = QLineEdit(str(value))
            editor.setPlaceholderText(field.help or "expression")
            editor.editingFinished.connect(
                lambda name=field.name, widget=editor: self._set_field(name, widget.text())
            )
            editor.installEventFilter(self)
        return editor

    def eventFilter(self, watched, event):
        if isinstance(watched, QLineEdit):
            if event.type() == QEvent.Type.FocusIn:
                self.workspace.focused_field = watched
            elif event.type() == QEvent.Type.FocusOut and \
                    self.workspace.focused_field is watched:
                self.workspace.focused_field = None
        return super().eventFilter(watched, event)

    def _set_field(self, name, value):
        if self.item.fields.get(name) == value:
            return
        self.item.fields[name] = value
        self.workspace.projectChanged.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_origin = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_origin is None or not (event.buttons() & Qt.LeftButton):
            return
        distance = (event.position().toPoint() - self._drag_origin).manhattanLength()
        if distance < QApplication.startDragDistance() or self.definition.hat:
            return
        payload = {
            "script": self.script_index,
            "path": [[slot, index] for slot, index in self.path],
            "index": self.index,
        }
        drag = QDrag(self)
        drag.setMimeData(BlockPalette._mime(MOVE_MIME + json.dumps(payload)))
        drag.setPixmap(self.grab().scaled(240, 60, Qt.KeepAspectRatio,
                                          Qt.SmoothTransformation))
        drag.exec(Qt.MoveAction)
        self._drag_origin = None


class SlotWidget(QFrame):
    """A nested C-slot that accepts blocks."""

    def __init__(self, name, workspace, script_index, path, parent_item):
        super().__init__()
        self.name = name
        self.workspace = workspace
        self.script_index = script_index
        self.path = path
        self.setObjectName("slot_%s" % name)
        self.setStyleSheet(
            "QFrame#slot_%s { background: %s; border: 1px dashed %s;"
            "border-radius: 7px; margin: 3px 0 1px 12px; }"
            % (name, _hex(theme.shade(theme.DARK["panel"], -0.25)),
               _hex(theme.DARK["border"]))
        )
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 6)
        layout.setSpacing(3)
        label = QLabel("%s" % name.title())
        label.setObjectName("hint")
        layout.addWidget(label)
        items = container(workspace.project, script_index, path)
        if not items:
            empty = QLabel("drop blocks here")
            empty.setObjectName("hint")
            empty.setAlignment(Qt.AlignCenter)
            layout.addWidget(empty)
        for index, item in enumerate(items):
            layout.addWidget(BlockWidget(item, workspace, script_index, path, index))

    def dragEnterEvent(self, event):
        if self.workspace.accepts(event):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if self.workspace.accepts(event):
            event.acceptProposedAction()

    def dropEvent(self, event):
        index = self._drop_index(event.position().y())
        if self.workspace.handle_drop(event.mimeData(), self.script_index,
                                      self.path, index):
            event.acceptProposedAction()

    def _drop_index(self, y):
        index = 0
        for position in range(self.layout().count()):
            widget = self.layout().itemAt(position).widget()
            if isinstance(widget, BlockWidget):
                if y < widget.geometry().center().y():
                    return index
                index += 1
        return index


class ScriptWidget(QFrame):
    """A complete top-level script with a hat block."""

    deleteRequested = Signal(int)

    def __init__(self, workspace, script_index):
        super().__init__()
        self.workspace = workspace
        self.script_index = script_index
        script = workspace.project.scripts[script_index]
        self.setObjectName("scriptFrame")
        self.setStyleSheet(
            "QFrame#scriptFrame { background: %s; border: 1px solid %s;"
            "border-radius: 12px; margin: 4px; }"
            % (theme.DARK["panel"], theme.DARK["border"])
        )
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 10)
        layout.setSpacing(5)

        header = QHBoxLayout()
        title = QLabel("Script %d" % (script_index + 1))
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        sprite = QComboBox()
        sprite.addItems([item.name for item in workspace.project.sprites])
        sprite.setCurrentText(script["sprite"])
        sprite.currentTextChanged.connect(
            lambda text, index=script_index: self._set_sprite(index, text)
        )
        header.addWidget(sprite, 1)
        remove = QToolButton()
        remove.setText("✕")
        remove.setToolTip("Delete script")
        remove.clicked.connect(lambda: self.deleteRequested.emit(script_index))
        header.addWidget(remove)
        layout.addLayout(header)

        for index, item in enumerate(script["blocks"]):
            layout.addWidget(BlockWidget(item, workspace, script_index, (), index))
        empty = QLabel("Drop blocks here to start a script")
        empty.setObjectName("hint")
        empty.setAlignment(Qt.AlignCenter)
        empty.setMinimumHeight(46)
        layout.addWidget(empty)

    def _set_sprite(self, index, name):
        self.workspace.project.scripts[index]["sprite"] = name
        self.workspace.projectChanged.emit()

    def dragEnterEvent(self, event):
        if self.workspace.accepts(event):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if self.workspace.accepts(event):
            event.acceptProposedAction()

    def dropEvent(self, event):
        index = self._drop_index(event.position().y())
        if self.workspace.handle_drop(event.mimeData(), self.script_index,
                                      (), index):
            event.acceptProposedAction()

    def _drop_index(self, y):
        index = 0
        for position in range(self.layout().count()):
            widget = self.layout().itemAt(position).widget()
            if isinstance(widget, BlockWidget):
                if y < widget.geometry().center().y():
                    return index
                index += 1
        return index


class ProcedureBodyWidget(QFrame):
    """Editable definition of a custom block, addressed by a negative index."""

    def __init__(self, workspace, index):
        super().__init__()
        self.setObjectName("procedureFrame")
        self.setStyleSheet(
            "QFrame#procedureFrame { background: %s; border: 1px solid %s;"
            "border-radius: 12px; margin: 4px; }"
            % (theme.DARK["panel"], theme.DARK["border"])
        )
        procedure = workspace.project.procedures[index]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 10)
        layout.setSpacing(5)
        parameters = ", ".join(
            "%s: %s" % (param["name"], param["type"])
            for param in procedure.params
        )
        title = QLabel("define %s(%s)" % (procedure.name, parameters))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        hint = QLabel("This is the body of your custom block.")
        hint.setObjectName("hint")
        layout.addWidget(hint)
        layout.addWidget(SlotWidget("SUB", workspace, -1 - index, (), procedure))


class Workspace(QScrollArea):
    """Scrollable canvas for sprite scripts and custom-block definitions."""

    projectChanged = Signal()
    structureChanged = Signal()
    error = Signal(str)

    def __init__(self, project):
        super().__init__()
        self.project = project
        self.current_sprite = project.sprites[0].name if project.sprites else ""
        self.current_procedure = None
        self.focused_field = None
        self.setObjectName("workspacePanel")
        self.setWidgetResizable(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.viewport().installEventFilter(self)
        self.content = QWidget()
        self.content.setObjectName("workspaceContent")
        self.layout = QVBoxLayout(self.content)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(6)
        self.layout.addStretch(1)
        self.setWidget(self.content)
        self.rebuild()

    def eventFilter(self, watched, event):
        if watched is self.viewport():
            if event.type() == QEvent.Type.DragEnter:
                self.dragEnterEvent(event)
                return True
            if event.type() == QEvent.Type.DragMove:
                self.dragMoveEvent(event)
                return True
            if event.type() == QEvent.Type.Drop:
                self.dropEvent(event)
                return True
        return super().eventFilter(watched, event)

    def set_project(self, project):
        self.project = project
        self.current_sprite = project.sprites[0].name if project.sprites else ""
        self.current_procedure = None
        self.focused_field = None
        self.rebuild()

    def set_current_sprite(self, name):
        if self.current_sprite == name:
            return
        self.current_sprite = name
        if not self.current_procedure:
            self.rebuild()

    def target_names(self):
        return ["Sprite scripts"] + [
            "My Block: %s" % procedure.name
            for procedure in self.project.procedures
        ]

    def target_text(self):
        if self.current_procedure:
            return "My Block: %s" % self.current_procedure
        return "Sprite scripts"

    def set_target(self, text):
        name = text[len("My Block: "):] if text.startswith("My Block: ") else None
        if name and not any(item.name == name
                            for item in self.project.procedures):
            name = None
        self.current_procedure = name
        self.rebuild()

    def rebuild(self):
        self.focused_field = None
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        if self.current_procedure:
            index = next((position for position, procedure
                          in enumerate(self.project.procedures)
                          if procedure.name == self.current_procedure), None)
            if index is None:
                self.current_procedure = None
            else:
                self.layout.insertWidget(
                    self.layout.count() - 1,
                    ProcedureBodyWidget(self, index),
                )
        if not self.current_procedure:
            visible = [(index, script)
                       for index, script in enumerate(self.project.scripts)
                       if script["sprite"] == self.current_sprite]
            for index, _ in visible:
                script_widget = ScriptWidget(self, index)
                script_widget.deleteRequested.connect(self.delete_script)
                self.layout.insertWidget(self.layout.count() - 1, script_widget)
            if not visible:
                label = QLabel(
                    "No scripts for %s yet. Drag a green flag here or press "
                    "New script." % (self.current_sprite or "this sprite")
                )
                label.setObjectName("hint")
                label.setWordWrap(True)
                label.setAlignment(Qt.AlignCenter)
                label.setMinimumHeight(70)
                self.layout.insertWidget(0, label)

    # --- drag and drop ---------------------------------------------------------
    def _parse_payload(self, text):
        if text.startswith(PALETTE_MIME):
            type_ = text[len(PALETTE_MIME):]
            definition = BLOCKS.get(type_)
            if definition is None or definition.reporter:
                return None
            return ("palette", type_, definition)
        if text.startswith(MOVE_MIME):
            try:
                payload = json.loads(text[len(MOVE_MIME):])
                source_path = tuple(tuple(step) for step in payload["path"])
                source = (int(payload["script"]), source_path,
                          int(payload["index"]))
                item = self._item_at(source)
                return ("move", source, item)
            except (ValueError, TypeError, KeyError, IndexError):
                return None
        return None

    def _item_at(self, location):
        script_index, path, index = location
        return container(self.project, script_index, path)[index]

    def _valid_move(self, source, target):
        """Reject dropping a block into one of its own child slots."""
        script_index, source_path, source_index = source
        target_script, target_path, _ = target
        if script_index != target_script:
            return True
        for depth in range(len(source_path), len(target_path)):
            prefix = target_path[:depth + 1]
            if prefix[:len(source_path)] == source_path and \
                    prefix[-1][1] == source_index:
                return False
        return True

    def _can_drop(self, text, script_index, path, index):
        payload = self._parse_payload(text)
        if payload is None:
            return False
        kind = payload[0]
        definition = payload[2] if kind == "palette" else \
            BLOCKS.get(payload[2].type)
        if definition is None:
            return False
        if definition.hat:
            return ((not path) and
                    (script_index is None or script_index >= 0)) and \
                not self.current_procedure
        if kind == "move" and script_index is not None:
            target = (script_index, path, index)
            return self._valid_move(payload[1], target)
        return True

    def accepts(self, event):
        mime = event.mimeData()
        text = mime.text() if mime.hasText() else ""
        sender = self.sender()
        script_index = getattr(sender, "script_index", None)
        path = getattr(sender, "path", ())
        return self._can_drop(text, script_index, path, 0)

    def dragEnterEvent(self, event):
        if self.accepts(event):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if self.accepts(event):
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime = event.mimeData()
        text = mime.text() if mime.hasText() else ""
        payload = self._parse_payload(text)
        if payload and payload[0] == "palette" and payload[2].hat:
            if self.new_script(payload[1]):
                event.acceptProposedAction()
            return
        index = self._current_script_index()
        if index is None:
            name = self._ensure_sprite()
            self.project.scripts.append({
                "sprite": name, "x": 32, "y": 32,
                "blocks": [block("event_flag")],
            })
            index = len(self.project.scripts) - 1
        if self.handle_drop(mime, index, (), len(
                self.project.scripts[index]["blocks"])):
            event.acceptProposedAction()

    def handle_drop(self, mime, script_index, path, index):
        text = mime.text() if mime.hasText() else ""
        payload = self._parse_payload(text)
        if payload is None:
            return False
        kind = payload[0]
        if kind == "palette":
            type_, definition = payload[1], payload[2]
            if definition.hat:
                if path or script_index is None or script_index < 0:
                    return False
                return self.new_script(type_)
            if self.current_procedure:
                script_index = -1 - self.project.procedures.index(
                    next(item for item in self.project.procedures
                         if item.name == self.current_procedure)
                )
                index = len(blocks_at(self.project, script_index))
            insert_block(self.project, script_index, path, index, type_)
        else:
            source = payload[1]
            if BLOCKS[payload[2].type].hat and (path or self.current_procedure):
                return False
            target = (script_index, path, index)
            if not self._valid_move(source, target):
                return False
            try:
                move_block(self.project, source, target)
            except (ValueError, IndexError, KeyError):
                return False
        self._structure_changed()
        return True

    def _structure_changed(self):
        self.rebuild()
        self.projectChanged.emit()
        self.structureChanged.emit()

    # --- editing commands ------------------------------------------------------
    def _ensure_sprite(self):
        if not self.project.sprites:
            self.project.sprites.append(Sprite(name="Sprite"))
        if not any(item.name == self.current_sprite
                   for item in self.project.sprites):
            self.current_sprite = self.project.sprites[0].name
        return self.current_sprite

    def _current_script_index(self):
        self._ensure_sprite()
        for index, script in enumerate(self.project.scripts):
            if script["sprite"] == self.current_sprite:
                return index
        return None

    def new_script(self, hat_type="event_flag"):
        definition = BLOCKS.get(hat_type)
        if definition is None or not definition.hat:
            return False
        if self.current_procedure:
            self.error.emit("Event blocks belong in sprite scripts, not My Blocks.")
            return False
        name = self._ensure_sprite()
        self.project.scripts.append({
            "sprite": name, "x": 32, "y": 32, "blocks": [block(hat_type)],
        })
        self._structure_changed()
        return True

    def add_block(self, type_):
        definition = BLOCKS.get(type_)
        if definition is None:
            return
        if definition.reporter:
            field = self.focused_field
            if not isinstance(field, QLineEdit):
                self.error.emit("Click a value field before inserting a reporter.")
                return
            default = REPORTER_DEFAULTS.get(type_, "0")
            if type_ == "sensing_touching_sprite" and self.project.sprites:
                default = 'touching sprite("%s")' % self.project.sprites[0].name
            try:
                position = field.cursorPosition()
                text = field.text()
                field.setText(text[:position] + default + text[position:])
                field.setCursorPosition(position + len(default))
                field.setFocus()
                self.projectChanged.emit()
            except RuntimeError:
                pass
            return
        if definition.hat:
            self.new_script(type_)
            return
        if self.current_procedure:
            procedure = next(item for item in self.project.procedures
                             if item.name == self.current_procedure)
            insert_block(self.project, -1 - self.project.procedures.index(
                procedure), (), len(procedure.blocks), type_)
            self._structure_changed()
            return
        index = self._current_script_index()
        if index is None:
            self.project.scripts.append({
                "sprite": self.current_sprite, "x": 32, "y": 32,
                "blocks": [block("event_flag")],
            })
            index = len(self.project.scripts) - 1
        insert_block(self.project, index, (),
                     len(self.project.scripts[index]["blocks"]), type_)
        self._structure_changed()

    def delete_script(self, index):
        if 0 <= index < len(self.project.scripts):
            self.project.scripts.pop(index)
            self._structure_changed()

    def delete_block(self, script_index, path, index):
        items = container(self.project, script_index, path)
        if 0 <= index < len(items) and not BLOCKS[items[index].type].hat:
            remove_block(self.project, script_index, path, index)
            self._structure_changed()


def _qt_key_name(event):
    """Translate a Qt key event into the names used by blockforge."""
    key = int(event.key())
    special = {
        Qt.Key_Space: "space", Qt.Key_Up: "up", Qt.Key_Down: "down",
        Qt.Key_Left: "left", Qt.Key_Right: "right",
        Qt.Key_Return: "enter", Qt.Key_Enter: "enter",
        Qt.Key_Escape: "escape", Qt.Key_Backspace: "backspace",
        Qt.Key_Tab: "tab", Qt.Key_Minus: "minus", Qt.Key_Equal: "equals",
        Qt.Key_Comma: "comma", Qt.Key_Period: "period", Qt.Key_Slash: "slash",
        Qt.Key_Shift: "shift", Qt.Key_Control: "ctrl", Qt.Key_Alt: "alt",
    }
    if key in special:
        return special[key]
    if Qt.Key_A <= key <= Qt.Key_Z:
        return chr(ord("a") + key - Qt.Key_A)
    if Qt.Key_0 <= key <= Qt.Key_9:
        return chr(ord("0") + key - Qt.Key_0)
    return ""


class StageWidget(QWidget):
    """Live, scaled view of the preview engine's stage."""

    def __init__(self, project, engine):
        super().__init__()
        self.project = project
        self.engine = engine
        self.setObjectName("stagePanel")
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.setToolTip("Click the stage, then use the keyboard and mouse.")

    def _stage_position(self, position):
        width, height = self.project.width, self.project.height
        scale = min(self.width() / width, self.height() / height)
        offset_x = (self.width() - width * scale) / 2
        offset_y = (self.height() - height * scale) / 2
        x = (position.x() - offset_x) / scale - width / 2
        y = height / 2 - (position.y() - offset_y) / scale
        return x, y

    def keyPressEvent(self, event):
        name = _qt_key_name(event)
        if name and not event.isAutoRepeat():
            self.engine.key_down(name)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        name = _qt_key_name(event)
        if name:
            self.engine.key_up(name)
        super().keyReleaseEvent(event)

    def mouseMoveEvent(self, event):
        self.engine.mouse = self._stage_position(event.position())
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
        self.mouseMoveEvent(event)
        super().mousePressEvent(event)

    @staticmethod
    def _draw_sprite(painter, shape, x, y, size):
        """Draw one of the four built-in sprite shapes."""
        radius = size / 2.0
        path = QPainterPath()
        if shape == "circle" or shape not in ("rect", "triangle", "star"):
            path.addEllipse(QRectF(x - radius, y - radius, size, size))
        elif shape == "rect":
            path.addRect(QRectF(x - radius, y - radius, size, size))
        elif shape == "triangle":
            path.moveTo(x, y - radius)
            path.lineTo(x + radius, y + radius)
            path.lineTo(x - radius, y + radius)
            path.closeSubpath()
        else:
            for index in range(10):
                distance = radius if index % 2 == 0 else radius * 0.45
                angle = math.radians(-90 + index * 36)
                point_x = x + math.cos(angle) * distance
                point_y = y + math.sin(angle) * distance
                if index == 0:
                    path.moveTo(point_x, point_y)
                else:
                    path.lineTo(point_x, point_y)
            path.closeSubpath()
        painter.drawPath(path)

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            width, height = self.project.width, self.project.height
            scale = min(self.width() / width, self.height() / height)
            offset_x = (self.width() - width * scale) / 2
            offset_y = (self.height() - height * scale) / 2

            painter.fillRect(self.rect(), QColor(theme.DARK["stage"]))
            painter.fillRect(int(offset_x), int(offset_y),
                             int(width * scale), int(height * scale),
                             QColor(self.engine.background))
            painter.setPen(QPen(QColor(theme.DARK["border"]), 1))
            painter.drawRect(int(offset_x), int(offset_y),
                             int(width * scale), int(height * scale))

            painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
            for x in range(0, width + 1, 40):
                painter.drawLine(int(offset_x + x * scale), int(offset_y),
                                 int(offset_x + x * scale),
                                 int(offset_y + height * scale))
            for y in range(0, height + 1, 40):
                painter.drawLine(int(offset_x), int(offset_y + y * scale),
                                 int(offset_x + width * scale),
                                 int(offset_y + y * scale))

            for line in self.engine.lines:
                color = QColor(line[4])
                painter.setPen(QPen(color, max(1, int(line[5] * scale)),
                                    Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(
                    int(offset_x + (width / 2 + line[0]) * scale),
                    int(offset_y + (height / 2 - line[1]) * scale),
                    int(offset_x + (width / 2 + line[2]) * scale),
                    int(offset_y + (height / 2 - line[3]) * scale),
                )

            now = self.engine.elapsed
            for sprite in sorted(
                    self.engine.sprites,
                    key=lambda item: (item.get("layer", 0), item["name"])):
                if not sprite["visible"]:
                    continue
                x = offset_x + (width / 2 + sprite["x"]) * scale
                y = offset_y + (height / 2 - sprite["y"]) * scale
                size = max(6, sprite["size"] / 100 * 36 * scale)
                color = QColor(sprite["color"])
                for _ in range(1, sprite["costume"]):
                    red, green, blue = color.red(), color.green(), color.blue()
                    color = QColor(green, blue, red)
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(color.lighter(140), 1.5))
                self._draw_sprite(painter, sprite["shape"], x, y, size)
                end_x, end_y = heading_endpoint(
                    x, y, sprite["direction"], size * 0.45
                )
                painter.setPen(QPen(QColor(theme.DARK["text"]), 1))
                painter.drawLine(x, y, end_x, end_y)
                if sprite["say_until"] > now:
                    rect = QRectF(int(x - 42), int(y - size - 34), 84, 24)
                    painter.setBrush(QBrush(QColor(theme.DARK["panel_alt"])))
                    painter.setPen(QPen(QColor(theme.DARK["text"]), 1))
                    painter.drawRoundedRect(rect, 7, 7)
                    painter.drawText(rect, Qt.AlignCenter,
                                     sprite["say_text"][:22])
        finally:
            painter.end()


class MainWindow(QMainWindow):
    """The blockforge editor window."""

    def __init__(self, project=None, language=None, path=None):
        super().__init__()
        self.project = deepcopy(project) if project is not None else example_project("hello")
        self.language = language or self.project.language
        if self.language not in ("cpp", "rust"):
            self.language = "cpp"
        self.project.language = self.language
        self.project_path = path
        self.dirty = False
        self.setWindowTitle("blockforge — %s" % self.project.name)
        self.setMinimumSize(1180, 760)
        self.resize(1480, 940)
        self.setStyleSheet(theme.stylesheet())
        self._temp_dir = None
        self._output_cursor = 0
        self.binary_path = None
        self.build_process = None
        self.run_process = None
        self.engine = PreviewEngine(self.project)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._preview_tick)

        self._build_toolbar()
        self._build_body()
        self._connect_signals()
        self.refresh_source()
        self._refresh_lists()
        self.statusBar().showMessage("Ready — drag blocks from the left, or open an example.")

    # --- construction ---------------------------------------------------------
    def _build_toolbar(self):
        toolbar = QToolBar("Main")
        toolbar.setObjectName("toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.title_label = QLabel(self.project.name)
        self.title_label.setObjectName("projectTitle")
        toolbar.addWidget(self.title_label)

        toolbar.addSeparator()
        self._action(toolbar, "new", "New", self.new_project, "Ctrl+N")
        self._action(toolbar, "open", "Open", self.open_project, "Ctrl+O")
        self._action(toolbar, "save", "Save", self.save_project, "Ctrl+S")
        self._action(toolbar, "save", "Save as", self.save_project_as)
        self._action(toolbar, "export", "Export source", self.export_source)
        self.export_binary_action = self._action(
            toolbar, "export", "Save binary", self.export_binary)
        self.export_binary_action.setEnabled(False)
        self._action(toolbar, "settings", "Settings", self.edit_settings)
        examples = QToolButton()
        examples.setText("Examples")
        examples.setIcon(theme.icon("examples"))
        examples.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        menu = QMenu(examples)
        for key in EXAMPLES:
            menu.addAction(EXAMPLE_LABELS.get(key, key),
                           lambda checked=False, name=key: self.load_example(name))
        examples.setMenu(menu)
        examples.setPopupMode(QToolButton.InstantPopup)
        toolbar.addWidget(examples)

        toolbar.addSeparator()
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("languageCombo")
        self.language_combo.addItems(["C++", "Rust"])
        self.language_combo.setCurrentText(
            "Rust" if self.language == "rust" else "C++")
        toolbar.addWidget(QLabel("Target"))
        toolbar.addWidget(self.language_combo)

        toolbar.addSeparator()
        build = self._action(toolbar, "build", "Build", self.build_project, "Ctrl+B")
        build.setObjectName("buildButton")
        self.run_button = self._action(toolbar, "run", "Run", self.run_binary, "F5")
        self.run_button.setEnabled(False)
        self._action(toolbar, "stop", "Stop", self.stop_all)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)
        status = QLabel("C++17 + SDL2")
        status.setObjectName("statusLabel")
        toolbar.addWidget(status)

    def _action(self, toolbar, glyph, text, callback, shortcut=None):
        action = QAction(theme.icon(glyph), text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
            action.setToolTip("%s (%s)" % (text, shortcut))
        action.triggered.connect(callback)
        toolbar.addAction(action)
        return action

    def _build_body(self):
        self.palette = BlockPalette(self.project)
        self.palette_list = self.palette.palette_list
        self.workspace = Workspace(self.project)

        center = QFrame()
        center.setObjectName("panel")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(12, 12, 12, 12)
        center_layout.setSpacing(8)
        workspace_header = QHBoxLayout()
        title = QLabel("Workspace")
        title.setObjectName("sectionTitle")
        workspace_header.addWidget(title)
        workspace_header.addStretch(1)
        workspace_header.addWidget(QLabel("Editing"))
        self.editor_target = QComboBox()
        self.editor_target.setObjectName("editorTarget")
        workspace_header.addWidget(self.editor_target)
        new_script = QPushButton("+ Script")
        new_script.setObjectName("newScriptButton")
        new_script.clicked.connect(lambda: self.workspace.new_script())
        workspace_header.addWidget(new_script)
        center_layout.addLayout(workspace_header)
        center_layout.addWidget(self.workspace)

        right = QFrame()
        right.setObjectName("panel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)
        right_layout.addWidget(self._label("Stage", "sectionTitle"))
        stage_frame = QFrame()
        stage_frame.setObjectName("stageFrame")
        stage_layout = QVBoxLayout(stage_frame)
        stage_layout.setContentsMargins(8, 8, 8, 8)
        self.stage = StageWidget(self.project, self.engine)
        stage_layout.addWidget(self.stage)
        right_layout.addWidget(stage_frame, 3)

        preview_row = QHBoxLayout()
        self.preview_button = QPushButton("Preview")
        self.preview_button.setObjectName("primaryButton")
        self.preview_button.clicked.connect(self.toggle_preview)
        preview_row.addWidget(self.preview_button)
        self.stage_button = QPushButton("Stage color")
        self.stage_button.clicked.connect(self.choose_background)
        preview_row.addWidget(self.stage_button)
        right_layout.addLayout(preview_row)

        right_layout.addWidget(self._label("Sprites", "sectionTitle"))
        self.sprite_list = QListWidget()
        self.sprite_list.setObjectName("spriteList")
        self.sprite_list.setMaximumHeight(130)
        right_layout.addWidget(self.sprite_list)
        sprite_row = QHBoxLayout()
        add_sprite = QPushButton("+ Sprite")
        add_sprite.clicked.connect(self.add_sprite)
        edit_sprite = QPushButton("Edit")
        edit_sprite.setObjectName("editSpriteButton")
        edit_sprite.clicked.connect(self.edit_sprite)
        remove_sprite = QPushButton("Remove")
        remove_sprite.setObjectName("dangerButton")
        remove_sprite.clicked.connect(self.remove_sprite)
        sprite_row.addWidget(add_sprite)
        sprite_row.addWidget(edit_sprite)
        sprite_row.addWidget(remove_sprite)
        right_layout.addLayout(sprite_row)

        right_layout.addWidget(self._label("Variables", "sectionTitle"))
        self.variable_list = QListWidget()
        self.variable_list.setObjectName("variableList")
        self.variable_list.setMaximumHeight(78)
        right_layout.addWidget(self.variable_list)
        variable_row = QHBoxLayout()
        add_variable = QPushButton("+ Variable")
        add_variable.clicked.connect(self.add_variable)
        rename_variable = QPushButton("Rename")
        rename_variable.clicked.connect(self.edit_variable)
        remove_variable = QPushButton("Remove")
        remove_variable.setObjectName("dangerButton")
        remove_variable.clicked.connect(self.remove_variable)
        variable_row.addWidget(add_variable)
        variable_row.addWidget(rename_variable)
        variable_row.addWidget(remove_variable)
        right_layout.addLayout(variable_row)

        right_layout.addWidget(self._label("My Blocks", "sectionTitle"))
        self.procedure_list = QListWidget()
        self.procedure_list.setObjectName("procedureList")
        self.procedure_list.setMaximumHeight(90)
        right_layout.addWidget(self.procedure_list)
        procedure_row = QHBoxLayout()
        add_procedure = QPushButton("+ My Block")
        add_procedure.clicked.connect(self.add_procedure)
        edit_procedure = QPushButton("Edit")
        edit_procedure.setObjectName("editProcedureButton")
        edit_procedure.clicked.connect(self.edit_procedure)
        remove_procedure = QPushButton("Remove")
        remove_procedure.setObjectName("dangerButton")
        remove_procedure.clicked.connect(self.remove_procedure)
        procedure_row.addWidget(add_procedure)
        procedure_row.addWidget(edit_procedure)
        procedure_row.addWidget(remove_procedure)
        right_layout.addLayout(procedure_row)

        self.console = QTabWidget()
        self.console.setObjectName("consolePanel")
        self.source_view = QPlainTextEdit()
        self.source_view.setObjectName("sourceView")
        self.source_view.setReadOnly(True)
        self.build_view = QPlainTextEdit()
        self.build_view.setObjectName("buildView")
        self.build_view.setReadOnly(True)
        self.build_view.setMaximumBlockCount(3000)
        self.output_view = QPlainTextEdit()
        self.output_view.setObjectName("outputView")
        self.output_view.setReadOnly(True)
        self.output_view.setMaximumBlockCount(3000)
        self.console.addTab(self.source_view, "Generated source")
        self.console.addTab(self.build_view, "Build log")
        self.console.addTab(self.output_view, "Preview output")

        top = QSplitter(Qt.Horizontal)
        top.addWidget(self.palette)
        top.addWidget(center)
        top.addWidget(right)
        top.setStretchFactor(0, 0)
        top.setStretchFactor(1, 1)
        top.setStretchFactor(2, 0)
        top.setSizes([290, 760, 390])

        split = QSplitter(Qt.Vertical)
        split.addWidget(top)
        split.addWidget(self.console)
        split.setStretchFactor(0, 4)
        split.setStretchFactor(1, 1)
        split.setSizes([700, 220])
        self.setCentralWidget(split)

    @staticmethod
    def _label(text, object_name):
        label = QLabel(text)
        label.setObjectName(object_name)
        return label

    def _connect_signals(self):
        self.palette.blockRequested.connect(self.workspace.add_block)
        self.palette.palette_list.itemActivated.connect(
            lambda item: self.workspace.add_block(item.data(Qt.UserRole))
        )
        self.workspace.projectChanged.connect(self._project_changed)
        self.workspace.error.connect(
            lambda message: self.statusBar().showMessage(message)
        )
        self.language_combo.currentTextChanged.connect(self._language_changed)
        self.editor_target.currentTextChanged.connect(self.workspace.set_target)
        self.sprite_list.currentRowChanged.connect(self._sprite_selected)
        self.sprite_list.itemDoubleClicked.connect(
            lambda: self.edit_sprite())
        self.variable_list.itemDoubleClicked.connect(
            lambda: self.edit_variable())
        self.procedure_list.itemDoubleClicked.connect(
            lambda: self.edit_procedure())

    # --- project operations ---------------------------------------------------
    @staticmethod
    def _terminate_process(process):
        if process is not None and process.state() != QProcess.NotRunning:
            process.kill()
            process.waitForFinished(2000)

    @staticmethod
    def _all_blocks(blocks):
        for item in blocks:
            yield item
            for children in item.children.values():
                yield from MainWindow._all_blocks(children)

    def _project_blocks(self):
        for script in self.project.scripts:
            yield from self._all_blocks(script["blocks"])
        for procedure in self.project.procedures:
            yield from self._all_blocks(procedure.blocks)

    def _refresh_title(self):
        marker = "*" if self.dirty else ""
        self.title_label.setText(self.project.name + marker)
        self.setWindowTitle("blockforge — %s%s" % (self.project.name, marker))

    def _mark_dirty(self):
        self.dirty = True
        self._refresh_title()

    def _invalidate_build(self):
        """Forget a binary that no longer matches the current project."""
        self.binary_path = None
        self.run_button.setEnabled(False)
        self.export_binary_action.setEnabled(False)

    def _adopt_project(self, project, message, path=None, dirty=False):
        """Replace the active project and reset all dependent state."""
        if self.engine.running:
            self.engine.stop()
            self._timer.stop()
            self.preview_button.setText("Preview")
        self._terminate_process(self.run_process)
        self._terminate_process(self.build_process)
        self.project = project
        self.language = project.language
        self.project_path = path
        self.dirty = dirty
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentText(
            "Rust" if self.language == "rust" else "C++"
        )
        self.language_combo.blockSignals(False)
        self.sprite_list.clear()
        self.workspace.set_project(self.project)
        self.palette.project = self.project
        self.engine = PreviewEngine(self.project)
        self.stage.project = self.project
        self.stage.engine = self.engine
        self.build_view.clear()
        self.output_view.clear()
        self._output_cursor = 0
        self._invalidate_build()
        self.refresh_source()
        self._refresh_lists()
        self.stage.update()
        self.statusBar().showMessage(message)

    def _project_changed(self):
        self._mark_dirty()
        self._invalidate_build()
        self.refresh_source()
        self._refresh_lists()
        self.engine.project = self.project
        self.stage.project = self.project
        self.engine.sync_project()
        self.stage.update()

    def _language_changed(self, text):
        self.language = "rust" if text == "Rust" else "cpp"
        self.project.language = self.language
        self._project_changed()
        self.statusBar().showMessage("Target changed to %s" % text)

    def refresh_source(self):
        self.project.language = self.language
        try:
            source = generate_source(self.project, self.language)
        except ValidationError as error:
            source = "// Project is not ready to compile yet:\n// %s\n" % error
        self.source_view.setPlainText(source)

    def _refresh_lists(self):
        sprite_item = self.sprite_list.currentItem()
        sprite_name = sprite_item.text() if sprite_item is not None else None
        procedure_item = self.procedure_list.currentItem()
        procedure_name = procedure_item.text().split("(")[0].replace(
            "define ", "") if procedure_item is not None else None
        self._refresh_title()
        self.sprite_list.clear()
        self.sprite_list.addItems([sprite.name for sprite in self.project.sprites])
        matches = self.sprite_list.findItems(sprite_name, Qt.MatchExactly) \
            if sprite_name else []
        if matches:
            self.sprite_list.setCurrentItem(matches[0])
        elif self.project.sprites:
            self.sprite_list.setCurrentRow(0)
        self.variable_list.clear()
        self.variable_list.addItems([
            "%s : %s" % (variable.name, variable.type)
            for variable in self.project.variables
        ])
        self.procedure_list.clear()
        for procedure in self.project.procedures:
            parameters = ", ".join(
                "%s: %s" % (param["name"], param["type"])
                for param in procedure.params
            )
            self.procedure_list.addItem("define %s(%s)" %
                                        (procedure.name, parameters))
        if procedure_name:
            matches = self.procedure_list.findItems(
                "define %s(" % procedure_name, Qt.MatchStartsWith)
            if matches:
                self.procedure_list.setCurrentItem(matches[0])
        elif self.procedure_list.count():
            self.procedure_list.setCurrentRow(0)
        self.editor_target.blockSignals(True)
        self.editor_target.clear()
        self.editor_target.addItems(self.workspace.target_names())
        self.editor_target.setCurrentText(self.workspace.target_text())
        self.editor_target.blockSignals(False)

    def _sprite_selected(self, row):
        if 0 <= row < len(self.project.sprites):
            self.workspace.set_current_sprite(self.project.sprites[row].name)

    def _confirm_discard(self, action):
        if not self.dirty:
            return True
        result = QMessageBox.question(
            self, "Unsaved changes",
            "This project has unsaved changes. What should happen before %s?"
            % action,
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
        )
        if result == QMessageBox.StandardButton.Save:
            return self.save_project()
        if result == QMessageBox.StandardButton.Discard:
            return True
        return False

    # --- project lifecycle -----------------------------------------------------
    def load_example(self, name):
        if not self._confirm_discard("loading an example"):
            return
        label = EXAMPLE_LABELS.get(name, name)
        self._adopt_project(deepcopy(example_project(name)),
                            "Loaded example: %s" % label)

    def new_project(self):
        if not self._confirm_discard("creating a new project"):
            return
        sprite = Sprite(name="Sprite")
        project = Project(
            name="Untitled", language=self.language,
            sprites=[sprite],
            scripts=[{"sprite": sprite.name, "x": 32, "y": 32,
                      "blocks": [block("event_flag")]}],
        )
        self._adopt_project(project, "New project", dirty=True)

    def open_project(self):
        if not self._confirm_discard("opening a project"):
            return
        folder = str(Path(self.project_path).parent) if self.project_path else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open blockforge project", folder,
            "Blockforge project (*.json)",
        )
        if not path:
            return
        try:
            project = load_project(path)
        except ValidationError as error:
            QMessageBox.warning(self, "Cannot open project", str(error))
            return
        self._adopt_project(project, "Opened %s" % path, path=path)

    def save_project(self, save_as=False):
        path = self.project_path
        if not path or save_as:
            suggested = str(Path(path).name) if path else \
                "%s.json" % re.sub(r"[^A-Za-z0-9_-]+", "-",
                                   self.project.name.lower())
            initial = str(Path(path)) if path else suggested
            path, _ = QFileDialog.getSaveFileName(
                self, "Save blockforge project", initial,
                "Blockforge project (*.json)",
            )
        if not path:
            return False
        try:
            validate_project(self.project)
            save_project(self.project, path)
        except ValidationError as error:
            QMessageBox.warning(self, "Cannot save project", str(error))
            return False
        self.project_path = path
        self.dirty = False
        self._refresh_title()
        self.statusBar().showMessage("Saved %s" % path)
        return True

    def save_project_as(self):
        self.save_project(save_as=True)

    def export_source(self):
        suffix = "cpp" if self.language == "cpp" else "rs"
        suggested = "%s.%s" % (
            re.sub(r"[^A-Za-z0-9_-]+", "-", self.project.name.lower()), suffix)
        path, _ = QFileDialog.getSaveFileName(
            self, "Export generated source", suggested,
            "C++ source (*.cpp)" if self.language == "cpp"
            else "Rust source (*.rs)",
        )
        if not path:
            return
        try:
            source = generate_source(self.project, self.language)
            Path(path).write_text(source, encoding="utf-8")
        except (ValidationError, OSError) as error:
            QMessageBox.warning(self, "Cannot export source", str(error))
            return
        self.statusBar().showMessage("Exported source to %s" % path)

    def export_binary(self):
        if not self.binary_path or not Path(self.binary_path).exists():
            self.statusBar().showMessage("Build the project before saving a binary")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save compiled program", self.project.name or "program",
            "Executable (*)",
        )
        if not path:
            return
        try:
            shutil.copy2(self.binary_path, path)
        except OSError as error:
            QMessageBox.warning(self, "Cannot save binary", str(error))
            return
        self.statusBar().showMessage("Saved program to %s" % path)

    def edit_settings(self):
        dialog = ProjectSettingsDialog(self.project, self)
        if not dialog.exec():
            return
        self.project.name = dialog.name_edit.text().strip() or self.project.name
        self.project.width = int(dialog.width_edit.text())
        self.project.height = int(dialog.height_edit.text())
        self.project.background = dialog.color.text()
        self.project.description = dialog.description.toPlainText()
        self._project_changed()

    # --- sprite, variable, and custom-block management -------------------------
    def _sprite_names(self):
        return [item.name for item in self.project.sprites]

    def _variable_names(self):
        return [item.name for item in self.project.variables]

    def _procedure_names(self):
        return [item.name for item in self.project.procedures]

    def _selected_sprite(self):
        row = self.sprite_list.currentRow()
        return self.project.sprites[row] if 0 <= row < len(
            self.project.sprites) else None

    def _selected_variable(self):
        row = self.variable_list.currentRow()
        return self.project.variables[row] if 0 <= row < len(
            self.project.variables) else None

    def _selected_procedure(self):
        row = self.procedure_list.currentRow()
        return self.project.procedures[row] if 0 <= row < len(
            self.project.procedures) else None

    def _rename_expression_references(self, old, new):
        pattern = re.compile(r"\b%s\b" % re.escape(old))
        for item in self._project_blocks():
            for key, value in list(item.fields.items()):
                if isinstance(value, str):
                    item.fields[key] = pattern.sub(new, value)

    def _rename_procedure_calls(self, old, new):
        for item in self._project_blocks():
            if item.type == "procedure_call" and \
                    item.fields.get("name") == old:
                item.fields["name"] = new

    @staticmethod
    def _remove_procedure_calls(blocks, name):
        kept = []
        for item in blocks:
            if item.type == "procedure_call" and item.fields.get("name") == name:
                continue
            for slot, children in list(item.children.items()):
                item.children[slot] = MainWindow._remove_procedure_calls(
                    children, name)
            kept.append(item)
        return kept

    def add_sprite(self):
        dialog = SpriteDialog(names=self._sprite_names(), parent=self)
        if not dialog.exec():
            return
        sprite = dialog.sprite()
        self.project.sprites.append(sprite)
        self.workspace.current_sprite = sprite.name
        self._project_changed()

    def edit_sprite(self):
        sprite = self._selected_sprite()
        if sprite is None:
            return
        dialog = SpriteDialog(sprite, self._sprite_names(), self)
        if not dialog.exec():
            return
        updated = dialog.sprite()
        old_name = sprite.name
        sprite.name, sprite.x, sprite.y = updated.name, updated.x, updated.y
        sprite.size, sprite.direction = updated.size, updated.direction
        sprite.costume, sprite.costume_count = updated.costume, updated.costume_count
        sprite.layer, sprite.shape = updated.layer, updated.shape
        sprite.color, sprite.visible = updated.color, updated.visible
        if old_name != updated.name:
            for script in self.project.scripts:
                if script["sprite"] == old_name:
                    script["sprite"] = updated.name
            self._rename_expression_references(old_name, updated.name)
            self.workspace.current_sprite = updated.name
        self._project_changed()

    def remove_sprite(self):
        sprite = self._selected_sprite()
        if sprite is None or len(self.project.sprites) <= 1:
            return
        if not self.isVisible() or QMessageBox.question(
                self, "Remove sprite",
                "Remove %s and all of its scripts?" % sprite.name,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.project.sprites.remove(sprite)
            self.project.scripts = [
                item for item in self.project.scripts
                if item["sprite"] != sprite.name
            ]
            self.workspace.current_sprite = self.project.sprites[0].name
            self._project_changed()

    def add_variable(self):
        dialog = VariableDialog(names=self._variable_names(), parent=self)
        if not dialog.exec():
            return
        name, kind = dialog.values()
        self.project.variables.append(Variable(name, kind))
        self._project_changed()

    def edit_variable(self):
        variable = self._selected_variable()
        if variable is None:
            return
        dialog = VariableDialog(variable, self._variable_names(), self)
        if not dialog.exec():
            return
        name, kind = dialog.values()
        if name != variable.name:
            self._rename_expression_references(variable.name, name)
        variable.name, variable.type = name, kind
        self._project_changed()

    def remove_variable(self):
        variable = self._selected_variable()
        if variable is None:
            return
        if not self.isVisible() or QMessageBox.question(
                self, "Remove variable", "Remove %s?" % variable.name,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.project.variables.remove(variable)
            self._project_changed()

    def add_procedure(self):
        dialog = ProcedureDialog(names=self._procedure_names(), parent=self)
        if not dialog.exec():
            return
        name, params = dialog.values()
        self.project.procedures.append(Procedure(name, params))
        self._project_changed()
        self.editor_target.setCurrentText("My Block: %s" % name)

    def edit_procedure(self):
        procedure = self._selected_procedure()
        if procedure is None:
            return
        dialog = ProcedureDialog(procedure, self._procedure_names(), self)
        if not dialog.exec():
            return
        name, params = dialog.values()
        if name != procedure.name:
            self._rename_procedure_calls(procedure.name, name)
            if self.workspace.current_procedure == procedure.name:
                self.workspace.current_procedure = name
        procedure.name, procedure.params = name, params
        self._project_changed()

    def remove_procedure(self):
        procedure = self._selected_procedure()
        if procedure is None:
            return
        if not self.isVisible() or QMessageBox.question(
                self, "Remove My Block",
                "Remove %s and every call to it?" % procedure.name,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            if self.workspace.current_procedure == procedure.name:
                self.workspace.current_procedure = None
            self.project.procedures.remove(procedure)
            for script in self.project.scripts:
                script["blocks"] = self._remove_procedure_calls(
                    script["blocks"], procedure.name)
            for item in self.project.procedures:
                item.blocks = self._remove_procedure_calls(
                    item.blocks, procedure.name)
            self._project_changed()

    def choose_background(self):
        color = QColorDialog.getColor(QColor(self.project.background), self)
        if color.isValid():
            self.project.background = color.name()
            self._project_changed()

    # --- preview, build, and run ---------------------------------------------
    def toggle_preview(self):
        if self.engine.running:
            self.engine.stop()
            self._timer.stop()
            self.preview_button.setText("Preview")
            self.statusBar().showMessage("Preview stopped")
        else:
            self.output_view.clear()
            self._output_cursor = 0
            self.engine.start()
            self._timer.start()
            self.preview_button.setText("Stop preview")
            self.statusBar().showMessage("Preview running — edit blocks live")
        self.stage.update()

    def _preview_tick(self):
        self.engine.step(0.033)
        new_lines, self._output_cursor = self.engine.drain_output(
            self._output_cursor)
        if new_lines:
            self.output_view.appendPlainText("\n".join(new_lines))
        self.stage.update()
        if not self.engine.running:
            self._timer.stop()
            self.preview_button.setText("Preview")

    def build_project(self):
        if self.build_process and self.build_process.state() != QProcess.NotRunning:
            return
        try:
            source = generate_source(self.project, self.language)
        except ValidationError as error:
            self.build_view.setPlainText("Cannot build: %s" % error)
            self.console.setCurrentWidget(self.build_view)
            return
        if self._temp_dir is None:
            self._temp_dir = tempfile.mkdtemp(prefix="blockforge-")
        suffix = "cpp" if self.language == "cpp" else "rs"
        source_path = Path(self._temp_dir) / ("main." + suffix)
        self.binary_path = str(Path(self._temp_dir) /
                               ("program-" + self.language))
        source_path.write_text(source, encoding="utf-8")
        command = build_command(self.language, str(source_path), self.binary_path)
        self.build_view.setPlainText("$ %s\n" % " ".join(command))
        self.console.setCurrentWidget(self.build_view)
        self.statusBar().showMessage("Building %s program…" % self.language.upper())
        self.run_button.setEnabled(False)

        process = QProcess(self)
        process.setProgram(command[0])
        process.setArguments(command[1:])
        process.readyReadStandardOutput.connect(
            lambda: self._append_build(process.readAllStandardOutput())
        )
        process.readyReadStandardError.connect(
            lambda: self._append_build(process.readAllStandardError())
        )
        binary = self.binary_path
        process.errorOccurred.connect(self._build_error)
        process.finished.connect(
            lambda code, status: self._build_finished(code, binary)
        )
        self.build_process = process
        process.start()

    def _append_build(self, data):
        text = bytes(data).decode("utf-8", "replace")
        self.build_view.moveCursor(QTextCursor.End)
        self.build_view.insertPlainText(text)

    def _build_error(self, error):
        self.build_view.appendPlainText(
            "\nCould not start the compiler: %s" % error
        )
        self.run_button.setEnabled(False)
        self.statusBar().showMessage("Compiler could not be started")
        self.console.setCurrentWidget(self.build_view)

    def _build_finished(self, code, binary):
        if code == 0:
            self.build_view.appendPlainText("\nBuild succeeded: %s" % binary)
            self.run_button.setEnabled(True)
            self.statusBar().showMessage("Build succeeded — press Run")
        else:
            self.build_view.appendPlainText("\nBuild failed (exit %s)" % code)
            self.run_button.setEnabled(False)
            self.statusBar().showMessage("Build failed — see build log")

    def run_binary(self):
        if self.run_process and self.run_process.state() != QProcess.NotRunning:
            return
        if not self.binary_path or not Path(self.binary_path).exists():
            self.statusBar().showMessage("Build the project before running it")
            return
        self.output_view.clear()
        process = QProcess(self)
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONUNBUFFERED", "1")
        process.setProcessEnvironment(environment)
        process.setProgram(self.binary_path)
        process.readyReadStandardOutput.connect(
            lambda: self._append_output(process.readAllStandardOutput())
        )
        process.readyReadStandardError.connect(
            lambda: self._append_output(process.readAllStandardError())
        )
        process.finished.connect(
            lambda code, status: self.statusBar().showMessage(
                "Program exited with code %s" % code
            )
        )
        self.run_process = process
        process.start()
        self.console.setCurrentWidget(self.output_view)
        self.statusBar().showMessage("Running generated program…")

    def _append_output(self, data):
        self.output_view.moveCursor(QTextCursor.End)
        self.output_view.insertPlainText(bytes(data).decode("utf-8", "replace"))

    def stop_all(self):
        if self.run_process and self.run_process.state() != QProcess.NotRunning:
            self._terminate_process(self.run_process)
            self.statusBar().showMessage("Program stopped")
        if self.build_process and self.build_process.state() != QProcess.NotRunning:
            self._terminate_process(self.build_process)
        if self.engine.running:
            self.toggle_preview()

    def closeEvent(self, event):
        if not self._confirm_discard("closing the editor"):
            event.ignore()
            return
        self.stop_all()
        self._timer.stop()
        if self._temp_dir:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        super().closeEvent(event)


def main(argv=None):
    """Command-line entrypoint for the blockforge editor."""
    parser = argparse.ArgumentParser(
        prog="blockforge", description="Visual block editor for real C++ and Rust programs"
    )
    parser.add_argument("project", nargs="?", help="optional .json project to open")
    parser.add_argument("--language", choices=["cpp", "rust"], help="initial target")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    app = QApplication.instance() or QApplication([])
    theme.install(app)
    try:
        project = load_project(args.project) if args.project \
            else example_project("hello")
    except ValidationError as error:
        parser.error(str(error))
    window = MainWindow(project, language=args.language, path=args.project)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
