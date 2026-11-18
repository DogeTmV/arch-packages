"""PySide6 editor for blockforge.

A friendly, Scratch-like editor for small C++ and Rust programs. Spirits and
the stage have their own script spaces, blocks are grouped into readable
categories, and source code is only generated when a project is built or
exported. All build/run work uses argument lists and QProcess; no shell is
involved.
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
    QEvent, QRectF, Qt, QTimer, QPoint, QMimeData, QRegularExpression, QSize,
    QProcess, QProcessEnvironment, Signal,
)
from PySide6.QtGui import (
    QAction, QBrush, QColor, QDoubleValidator, QDrag, QFont, QFontMetrics,
    QIcon, QImage, QIntValidator, QKeySequence, QPainter, QPainterPath, QPen,
    QPixmap, QRegularExpressionValidator, QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QDockWidget,
    QFileDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QListView, QMainWindow,
    QMenu, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy,
    QSplitter, QStackedWidget, QStyledItemDelegate, QTabWidget, QToolBar,
    QToolButton, QVBoxLayout, QWidget,
)

import theme
from compiler import ValidationError, build_command, generate_source
from core import (
    BLOCKS, CATEGORIES, STAGE_NAME, FieldDef, Procedure, Project, Sprite,
    Variable, argument_default, block, load_project, save_project,
    script_owner, script_target, scripts_for_target, validate_project,
)
from core import new_script as core_new_script
from editing import blocks_at, container, insert_block, move_block, remove_block
from examples import EXAMPLE_LABELS, EXAMPLES, example_project
from images import encode_rgba_png
from library import (
    SPIRITS, STAGES, apply_stage_preset, spirit_from_preset, spirit_start_script,
    stage_asset_name,
)
from preview import PreviewEngine

PALETTE_MIME = "blockforge:palette:"
MOVE_MIME = "blockforge:move:"
PROJECT_FILTER = "Blockforge project (*.bfproj)"

# Scratch 3.0's category order, from top to bottom in the toolbox.
PALETTE_ORDER = (
    "motion", "looks", "sound", "events", "control", "sensing", "operators",
    "variables", "pen", "custom",
)

# Mirrors core.validate_project's stage restrictions so the editor never offers
# a block that cannot be compiled for the stage.
STAGE_FORBIDDEN_TYPES = frozenset({
    "looks_say", "looks_show", "looks_hide", "looks_set_size",
    "looks_change_size", "looks_set_costume", "looks_next_costume",
})

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

# Small Scratch-specific refinements on top of theme.stylesheet().
_EDITOR_STYLE = """
QListWidget#paletteList { font-size: 12px; padding: 4px; }
QListWidget#paletteList::item { padding: 0; margin: 0; }
QLineEdit#blockSearch {
    background: #FFFFFF;
    border: 1px solid #D9E3F2;
    border-radius: 14px;
    padding: 5px 10px;
}
QToolButton#deleteBlock {
    background: transparent;
    border: none;
    color: #FFFFFF;
    padding: 0;
    min-width: 18px;
}
QFrame#scriptFrame, QFrame#procedureFrame {
    background: transparent;
    border: none;
    margin: 0;
}
QFrame#slot_SUB, QFrame#slot_SUBSTACK {
    background: #FFFFFF;
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 0 0 8px 8px;
    margin: 0 10px 6px 22px;
}
QLabel#slotHint { color: #7D879E; font-size: 10px; }
QToolButton#addVariableButton, QToolButton#addProcedureButton {
    background: #FFFFFF;
    color: #575E75;
    border: 1px solid #D9E3F2;
    border-radius: 12px;
    min-width: 26px;
    min-height: 24px;
}
QFrame#costumePane QLabel, QFrame#soundPane QLabel {
    background: transparent;
    color: #575E75;
}
"""

_BOOLEAN_REPORTERS = frozenset({
    "operator_gt", "operator_lt", "operator_equal",
    "operator_and", "operator_or", "operator_not",
})


def heading_endpoint(x, y, degrees, length):
    """Return the stage-space end of a Scratch-style heading indicator."""
    radians = math.radians(degrees)
    return (x + math.sin(radians) * length, y - math.cos(radians) * length)


def _hex(color):
    return QColor(color).name()


def _category_color(block_type, fallback=None):
    definition = BLOCKS.get(block_type)
    return theme.category_color(definition.category if definition else None,
                                fallback or theme.SCRATCH["accent"])


def _template_label(definition, fields=None):
    """Return a short, human-readable label for a block definition.

    ``label`` is preferred over the compiler-facing template. Placeholders are
    shown as a small square in the palette and replaced with real values inside
    the workspace, so blocks read like "move 10 steps" or "if score > 2 then".
    """
    text = definition.label or definition.template or definition.type
    for field in definition.fields:
        if fields and field.name in fields:
            placeholder = str(fields[field.name])
        elif field.default not in (None, ""):
            placeholder = str(field.default)
        else:
            placeholder = "□"
        text = text.replace("{%s}" % field.name, placeholder)
    return text.replace("{", "").replace("}", "")


def _allowed_for_target(definition, target):
    """Return whether a block can be used by the selected script target."""
    if definition is None or target != STAGE_NAME:
        return True
    return not (definition.category in ("motion", "pen") or
                definition.type in STAGE_FORBIDDEN_TYPES)


def _new_target_script(target, hat_type="event_flag", x=32, y=32):
    """Create a script for a spirit name or ``"Stage"`` using core's helper.

    ``core.new_script`` validates the *kind* of target, so spirit-owned scripts
    are created with the spirit kind and then assigned their owner.
    """
    try:
        return core_new_script(target, hat_type, x, y)
    except ValueError:
        # The current core helper only accepts a target *kind* for spirits.
        script = core_new_script("spirit", hat_type, x, y)
        script["sprite"] = target
        return script


class PaletteDelegate(QStyledItemDelegate):
    """Paint flyout entries as real Scratch puzzle pieces."""

    def paint(self, painter, option, index):
        if index.data(Qt.UserRole + 2) == "section":
            painter.save()
            painter.setPen(QColor(theme.SCRATCH["muted"]))
            font = painter.font()
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(option.rect.adjusted(10, 0, -4, 0),
                             Qt.AlignVCenter, index.data(Qt.DisplayRole) or "")
            painter.restore()
            return
        rect = option.rect.adjusted(5, 3, -12, 3)
        reporter = index.data(Qt.UserRole + 4)
        key = index.data(Qt.UserRole + 3) or "motion"
        theme.paint_block(
            painter, rect, key,
            hat=bool(index.data(Qt.UserRole + 5)),
            reporter="boolean" if reporter == "bool" else (
                "round" if reporter else None),
        )
        painter.save()
        painter.setPen(QColor("#FFFFFF"))
        font = painter.font()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        metrics = QFontMetrics(painter.font())
        text = metrics.elidedText(index.data(Qt.DisplayRole) or "",
                                  Qt.ElideRight, rect.width() - 28)
        flags = Qt.AlignVCenter
        if reporter:
            flags |= Qt.AlignHCenter
        painter.drawText(rect.adjusted(16, 0, -12, 0), flags, text)
        painter.restore()

    def sizeHint(self, option, index):
        if index.data(Qt.UserRole + 2) == "section":
            return QSize(10, 24)
        return QSize(10, 38)


class PaletteList(QListWidget):
    """List widget that starts a block drag from the pressed entry."""

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.position().toPoint())
            if item is not None and item.data(Qt.UserRole):
                self.setCurrentItem(item)
        super().mousePressEvent(event)

    def startDrag(self, supported_actions):
        item = self.currentItem()
        if item is None or not item.data(Qt.UserRole):
            return
        drag = QDrag(self)
        drag.setMimeData(BlockPalette._mime(
            PALETTE_MIME + item.data(Qt.UserRole)
        ))
        drag.setPixmap(BlockPalette._drag_pixmap(item))
        drag.setHotSpot(QPoint(12, 14))
        drag.exec(Qt.CopyAction)


class BlockPalette(QWidget):
    """Sectioned, searchable list of draggable blocks."""

    blockRequested = Signal(str)
    variableRequested = Signal()
    procedureRequested = Signal()
    variableEditRequested = Signal(str)
    variableRemoveRequested = Signal(str)
    procedureEditRequested = Signal(str)
    procedureRemoveRequested = Signal(str)

    def __init__(self, project, target=None, parent=None):
        super().__init__(parent)
        self.project = project
        self.target = target or (
            project.sprites[0].name if project.sprites else STAGE_NAME
        )
        self.sprite = self.target  # compatibility with older callers
        self.active_category = "motion"
        self.setObjectName("palettePanel")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scratch's vertical category rail.
        toolbox = QFrame()
        toolbox.setObjectName("toolboxPanel")
        toolbox.setFixedWidth(80)
        toolbox_layout = QVBoxLayout(toolbox)
        toolbox_layout.setContentsMargins(0, 4, 0, 4)
        toolbox_layout.setSpacing(0)
        self.category_buttons = {}
        ordered = sorted(
            CATEGORIES,
            key=lambda item: (PALETTE_ORDER.index(item.key)
                              if item.key in PALETTE_ORDER else 99),
        )
        for category in ordered:
            button = QToolButton()
            button.setText(category.name)
            button.setObjectName("category_%s" % category.key)
            button.setCheckable(True)
            button.setToolTip(category.help or category.name)
            button.clicked.connect(
                lambda checked=False, key=category.key: self.set_category(key)
            )
            toolbox_layout.addWidget(button)
            self.category_buttons[category.key] = button
        toolbox_layout.addStretch(1)
        outer.addWidget(toolbox)

        # The flyout holds the search field and the category's blocks.
        flyout = QFrame()
        flyout.setObjectName("flyoutPanel")
        flyout.setFixedWidth(250)
        flyout_layout = QVBoxLayout(flyout)
        flyout_layout.setContentsMargins(12, 8, 10, 8)
        flyout_layout.setSpacing(6)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search blocks")
        self.search.setObjectName("blockSearch")
        self.search.textChanged.connect(self._refresh_list)
        # Scratch 3.0's block flyout has no search box; keep the widget for
        # compatibility with callers that filter definitions directly.
        self.search.hide()

        manage_row = QHBoxLayout()
        manage_row.setContentsMargins(0, 0, 0, 0)
        add_variable = QToolButton()
        add_variable.setText("+ Make a variable")
        add_variable.setObjectName("addVariableButton")
        add_variable.setToolTip("Make a variable")
        add_variable.clicked.connect(self.variableRequested.emit)
        self.add_variable_button = add_variable
        add_procedure = QToolButton()
        add_procedure.setText("+ Make a block")
        add_procedure.setObjectName("addProcedureButton")
        add_procedure.setToolTip("Make a My Block")
        add_procedure.clicked.connect(self.procedureRequested.emit)
        self.add_procedure_button = add_procedure
        manage_row.addWidget(add_variable)
        manage_row.addWidget(add_procedure)
        flyout_layout.addLayout(manage_row)

        self.palette_list = PaletteList()
        self.palette_list.setObjectName("paletteList")
        self.palette_list.setItemDelegate(PaletteDelegate())
        self.palette_list.setDragEnabled(True)
        self.palette_list.setDefaultDropAction(Qt.CopyAction)
        self.palette_list.setSelectionMode(QListView.SingleSelection)
        self.palette_list.setVerticalScrollMode(
            QListView.ScrollPerPixel)
        self.palette_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.palette_list.customContextMenuRequested.connect(
            self._show_context_menu)
        self.palette_list.itemActivated.connect(self._item_activated)
        flyout_layout.addWidget(self.palette_list, 1)
        outer.addWidget(flyout)
        self.set_category("motion")

    @staticmethod
    def _label(text, object_name):
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        return label

    def _item_activated(self, item):
        block_type = item.data(Qt.UserRole)
        if block_type:
            self.blockRequested.emit(block_type)

    @staticmethod
    def _add_named_actions(menu, title, names, signal):
        submenu = menu.addMenu(title)
        for name in names:
            submenu.addAction(name,
                              lambda checked=False, value=name: signal.emit(value))

    def _context_menu(self):
        """Build Scratch's right-click variable and My Block actions."""
        menu = QMenu(self.palette_list)
        if self.active_category == "variables":
            names = [item.name for item in self.project.variables]
            self._add_named_actions(menu, "Rename variable", names,
                                    self.variableEditRequested)
            self._add_named_actions(menu, "Delete variable", names,
                                    self.variableRemoveRequested)
        elif self.active_category == "custom":
            names = [item.name for item in self.project.procedures]
            self._add_named_actions(menu, "Edit My Block", names,
                                    self.procedureEditRequested)
            self._add_named_actions(menu, "Delete My Block", names,
                                    self.procedureRemoveRequested)
        else:
            return None
        return None if menu.isEmpty() else menu

    def _show_context_menu(self, position):
        if self.palette_list.itemAt(position) is None:
            return
        menu = self._context_menu()
        if menu is not None:
            menu.exec(self.palette_list.viewport().mapToGlobal(position))

    def set_category(self, key):
        self.active_category = key
        expected = "category_%s" % key
        for name, button in self.category_buttons.items():
            button.setChecked(name == expected)
        self.add_variable_button.setVisible(key == "variables")
        self.add_procedure_button.setVisible(key == "custom")
        self._refresh_list()

    def set_target(self, name):
        """Hide blocks that cannot run on the selected spirit or stage."""
        self.target = name or STAGE_NAME
        self.sprite = self.target
        self._refresh_list()

    def _refresh_list(self):
        query = self.search.text().strip().lower()
        self.palette_list.clear()
        for key in PALETTE_ORDER:
            category = next((item for item in CATEGORIES if item.key == key), None)
            if category is None or (self.active_category and
                                    self.active_category != key):
                continue
            entries = []
            for definition in BLOCKS.values():
                if definition.category != key or \
                        not _allowed_for_target(definition, self.target):
                    continue
                label = _template_label(definition)
                if query and query not in label.lower() and \
                        query not in definition.template.lower() and \
                        query not in definition.type.lower():
                    continue
                entries.append((definition, label))
            if not entries:
                continue
            header = QListWidgetItem(category.name)
            header.setData(Qt.UserRole + 2, "section")
            header.setFlags(Qt.ItemIsEnabled)
            font = header.font()
            font.setBold(True)
            header.setFont(font)
            header.setForeground(QColor(theme.SCRATCH["muted"]))
            self.palette_list.addItem(header)
            for definition, label in entries:
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, definition.type)
                item.setData(Qt.UserRole + 1,
                             theme.category_color(definition.category))
                item.setData(Qt.UserRole + 3, definition.category)
                item.setData(Qt.UserRole + 4, "bool" if definition.type in
                             _BOOLEAN_REPORTERS else (
                                 "round" if definition.reporter else ""))
                item.setData(Qt.UserRole + 5, definition.hat)
                item.setToolTip(definition.help or label)
                self.palette_list.addItem(item)

    @staticmethod
    def _mime(text):
        mime = QMimeData()
        mime.setText(text)
        return mime

    @staticmethod
    def _drag_pixmap(item):
        pixmap = QPixmap(240, 38)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        theme.paint_block(
            painter, pixmap.rect().adjusted(2, 2, -8, -3),
            item.data(Qt.UserRole + 3) or "motion",
            hat=bool(item.data(Qt.UserRole + 5)),
            reporter="boolean" if item.data(Qt.UserRole + 4) == "bool" else (
                "round" if item.data(Qt.UserRole + 4) else None),
        )
        painter.setPen(QColor("#FFFFFF"))
        font = painter.font()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect().adjusted(18, 0, -12, 0),
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
    """Edit every persisted property of a spirit, including its picture."""

    def __init__(self, sprite=None, names=(), parent=None, assets=None):
        super().__init__(parent)
        self.setWindowTitle("Spirit properties")
        self.original_name = sprite.name if sprite else None
        self.names = set(names)
        if self.original_name:
            self.names.discard(self.original_name)
        sprite = sprite or Sprite()
        # Shared with the project so imported pictures are saved with it.
        self.assets = assets if assets is not None else {}
        self._picture_name = sprite.image or ""
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
                           ("costume_count", "Costumes"),
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

        picture_row = QHBoxLayout()
        self.picture_preview = QLabel()
        self.picture_preview.setObjectName("picturePreview")
        self.picture_preview.setFixedSize(96, 72)
        self.picture_preview.setAlignment(Qt.AlignCenter)
        self.picture_preview.setStyleSheet(
            "background: %s; border: 1px solid %s; border-radius: 6px;"
            % (theme.SCRATCH["stage"], theme.SCRATCH["border"])
        )
        picture_row.addWidget(self.picture_preview)
        picture_buttons = QVBoxLayout()
        choose = QPushButton("Choose picture…")
        choose.setObjectName("choosePicture")
        choose.clicked.connect(self._choose_picture)
        clear = QPushButton("Clear picture")
        clear.setObjectName("clearPicture")
        clear.clicked.connect(self._clear_picture)
        picture_buttons.addWidget(choose)
        picture_buttons.addWidget(clear)
        picture_row.addLayout(picture_buttons)
        layout.addRow("Picture", picture_row)
        self._show_preview()
        layout.addRow(_dialog_buttons(self))

    def _show_preview(self):
        data = self.assets.get(self._picture_name) if self._picture_name else None
        image = QImage.fromData(data) if data else QImage()
        if image.isNull():
            self.picture_preview.clear()
            self.picture_preview.setText("no picture")
            return
        pixmap = QPixmap.fromImage(image).scaled(
            self.picture_preview.size(), Qt.KeepAspectRatio,
            Qt.SmoothTransformation)
        self.picture_preview.setPixmap(pixmap)

    def _clear_picture(self):
        self._picture_name = ""
        self._show_preview()

    def _choose_picture(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a spirit picture", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)",
        )
        if not path:
            return
        image = QImage(path)
        if image.isNull():
            QMessageBox.warning(self, "Spirit picture",
                                "That picture could not be opened.")
            return
        if max(image.width(), image.height()) > 512:
            image = image.scaled(512, 512, Qt.KeepAspectRatio,
                                 Qt.SmoothTransformation)
        image = image.convertToFormat(QImage.Format.Format_RGBA8888)
        pointer = image.bits()
        try:
            pointer.setsize(image.sizeInBytes())
        except AttributeError:
            pass
        rgba = bytes(pointer)
        if len(rgba) != image.width() * image.height() * 4:
            QMessageBox.warning(self, "Spirit picture",
                                "That picture could not be converted.")
            return
        stem = re.sub(r"[^A-Za-z0-9_-]+", "-", Path(path).stem).strip("-")[:40]
        base = stem or "spirit"
        name = base + ".png"
        index = 2
        while name in self.assets:
            name = "%s-%d.png" % (base, index)
            index += 1
        try:
            self.assets[name] = encode_rgba_png(
                image.width(), image.height(), rgba)
        except ValueError as error:
            QMessageBox.warning(self, "Spirit picture", str(error))
            return
        self._picture_name = name
        self._show_preview()

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
            image=self._picture_name,
        )

    def accept(self):
        if self.sprite().name in self.names:
            QMessageBox.warning(self, "Spirit properties",
                                "That spirit name is already used.")
            return
        super().accept()


# Both names are kept: "spirit" is the user-facing word, "SpriteDialog" the
# historical class name used by existing callers and tests.
SpiritDialog = SpriteDialog


class StageDialog(QDialog):
    """Choose a built-in stage backdrop or a plain background color."""

    def __init__(self, project=None, parent=None):
        if isinstance(project, QWidget) and parent is None:
            parent, project = project, None
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Choose a stage look")
        layout = QFormLayout(self)
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("stagePreset")
        self.preset_combo.addItem("Plain color", None)
        for preset in STAGES:
            self.preset_combo.addItem(preset.label, preset.key)
        if project is not None:
            current_key = next((preset.key for preset in STAGES
                                if stage_asset_name(preset.key) ==
                                project.backdrop), None)
            if current_key:
                self.preset_combo.setCurrentText(
                    next(p.label for p in STAGES if p.key == current_key))
        self.stage_combo = self.preset_combo
        self.backdrop_combo = self.preset_combo
        layout.addRow("Backdrop", self.preset_combo)

        self.description = QLabel()
        self.description.setObjectName("hint")
        self.description.setWordWrap(True)
        layout.addRow(self.description)
        self.color = ColorField(project.background if project is not None
                                else theme.SCRATCH["stage"])
        self.color.setObjectName("stageColor")
        layout.addRow("Plain color", self.color)
        self.preset_combo.currentIndexChanged.connect(self._update_description)
        self._update_description()
        layout.addRow(_dialog_buttons(self))

    def _update_description(self):
        key = self.preset_combo.currentData()
        preset = next((item for item in STAGES if item.key == key), None)
        self.description.setText(preset.description if preset else
                                 "Use a solid stage color with no picture.")

    def values(self):
        return self.preset_combo.currentData(), self.color.text()

    def apply(self, project):
        key, color = self.values()
        if key:
            apply_stage_preset(project, key, project.width, project.height)
        else:
            project.background = color
            project.backdrop = ""
        return project


class LibraryDialog(QDialog):
    """Browse spirits and stage looks included with blockforge."""

    def __init__(self, project=None, parent=None):
        if isinstance(project, QWidget) and parent is None:
            parent, project = project, None
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Library")
        layout = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.setObjectName("libraryList")
        self.list.setMinimumSize(360, 320)
        for title in ("Spirits", "Stages"):
            header = QListWidgetItem(title)
            header.setData(Qt.UserRole + 2, "section")
            font = header.font()
            font.setBold(True)
            header.setFont(font)
            header.setForeground(QColor(theme.SCRATCH["text"]))
            self.list.addItem(header)
            presets = SPIRITS if title == "Spirits" else STAGES
            for preset in presets:
                item = QListWidgetItem("%s — %s" % (preset.label,
                                                    preset.description))
                item.setData(Qt.UserRole, ("stage" if title == "Stages"
                                           else "spirit", preset.key))
                item.setToolTip(preset.description)
                self.list.addItem(item)
        self.list.itemDoubleClicked.connect(lambda: self.accept())
        first = next((row for row in range(self.list.count())
                      if self.list.item(row).data(Qt.UserRole)), None)
        if first is not None:
            self.list.setCurrentRow(first)
        layout.addWidget(self.list)
        layout.addWidget(_dialog_buttons(self))

    def selected(self):
        item = self.list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return value if isinstance(value, tuple) else None


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
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("QFrame { background: transparent; border: none; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(13, 18 if self.definition.hat else 8,
                                15, 13)
        layout.setSpacing(4)
        header_row = QHBoxLayout()
        header = QLabel(_template_label(self.definition, self.item.fields))
        header.setStyleSheet("color: #FFFFFF; font-weight: 700;")
        header.setWordWrap(True)
        header_row.addWidget(header, 1)
        if not self.definition.hat:
            remove = QToolButton()
            remove.setText("✕")
            remove.setToolTip("Remove this block")
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
            editor.addItems(["mouse"] + [
                spirit.name for spirit in self.workspace.project.sprites
            ])
            editor.setCurrentText(str(value))
            editor.currentTextChanged.connect(
                lambda text, name=field.name: self._set_field(name, text)
            )
        elif field.kind == "variable":
            editor = QComboBox()
            editor.addItems([item.name for item in self.workspace.project.variables])
            editor.setCurrentText(str(value))
            editor.currentTextChanged.connect(
                lambda text, name=field.name: self._set_field(name, text)
            )
        elif field.kind == "procedure":
            editor = QComboBox()
            editor.addItems([item.name for item in self.workspace.project.procedures])
            editor.setCurrentText(str(value))
            editor.currentTextChanged.connect(
                lambda text, name=field.name: self._set_field(name, text)
            )
        elif field.kind == "backdrop":
            editor = QComboBox()
            names = [""] + sorted(self.workspace.project.assets)
            if value and value not in names:
                names.append(str(value))
            editor.addItems(names)
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

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            reporter = None
            if self.definition.reporter:
                reporter = ("boolean" if self.item.type in _BOOLEAN_REPORTERS
                            else "round")
            theme.paint_block(
                painter, QRectF(self.rect()).adjusted(1, 1, -4, -4),
                self.definition.category, hat=self.definition.hat,
                reporter=reporter,
            )
        finally:
            painter.end()
        super().paintEvent(event)

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
            "QFrame#slot_%s { background: %s; border: 1px solid %s;"
            "border-radius: 0 0 7px 7px; margin: 0 0 4px 12px; }"
            % (name, theme.SCRATCH["panel"], theme.SCRATCH["stage_border"])
        )
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 6)
        layout.setSpacing(3)
        label = QLabel(name.title() if name not in ("SUB", "SUBSTACK") else "")
        label.setObjectName("slotHint")
        label.setVisible(name not in ("SUB", "SUBSTACK"))
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
    """A complete top-level script belonging to the selected target."""

    deleteRequested = Signal(int)

    def __init__(self, workspace, script_index):
        super().__init__()
        self.workspace = workspace
        self.script_index = script_index
        self.setObjectName("scriptFrame")
        self.setStyleSheet(
            "QFrame#scriptFrame { background: %s; border: 1px solid %s;"
            "border-radius: 12px; margin: 4px; }"
            % (theme.SCRATCH["panel"], theme.SCRATCH["border"])
        )
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 10)
        layout.setSpacing(5)

        header = QHBoxLayout()
        script = workspace.project.scripts[script_index]
        label = "%s · %s" % (script_owner(script), "script")
        title = QLabel(label)
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        remove = QToolButton()
        remove.setText("✕")
        remove.setToolTip("Remove script")
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
            % (theme.SCRATCH["panel"], theme.SCRATCH["border"])
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
        hint = QLabel("These blocks run whenever you use this My Block.")
        hint.setObjectName("hint")
        layout.addWidget(hint)
        layout.addWidget(SlotWidget("SUB", workspace, -1 - index, (), procedure))


class Workspace(QScrollArea):
    """Scrollable canvas for the selected spirit's or the stage's scripts."""

    projectChanged = Signal()
    structureChanged = Signal()
    error = Signal(str)

    def __init__(self, project):
        super().__init__()
        self.project = project
        self.current_target = (project.sprites[0].name if project.sprites
                               else STAGE_NAME)
        self.current_sprite = self.current_target  # compatibility alias
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
        self.current_target = (project.sprites[0].name if project.sprites
                               else STAGE_NAME)
        self.current_sprite = self.current_target
        self.current_procedure = None
        self.focused_field = None
        self.rebuild()

    def set_current_target(self, name):
        name = name or STAGE_NAME
        if self.current_target == name and not self.current_procedure:
            return
        # Picking a spirit or the stage always returns to its scripts.
        self.current_target = name
        self.current_sprite = name
        self.current_procedure = None
        self.rebuild()

    def set_current_sprite(self, name):
        """Compatibility alias: a spirit name or ``"Stage"``."""
        self.set_current_target(name)

    def target_names(self):
        return ["Scripts"] + [
            "My Block: %s" % procedure.name
            for procedure in self.project.procedures
        ]

    def target_text(self):
        if self.current_procedure:
            return "My Block: %s" % self.current_procedure
        return "Scripts"

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
            visible = scripts_for_target(self.project, self.current_target)
            for index, _ in visible:
                script_widget = ScriptWidget(self, index)
                script_widget.deleteRequested.connect(self.delete_script)
                self.layout.insertWidget(self.layout.count() - 1, script_widget)
            if not visible:
                label = QLabel(
                    "No scripts for %s yet. Drag a green flag here or choose "
                    "New script." % self.current_target
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
            except (ValueError, TypeError, KeyError, IndexError, AttributeError):
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
        if definition is None or not _allowed_for_target(definition,
                                                         self.current_target):
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
            self.project.scripts.append(_new_target_script(
                self._ensure_target(), "event_flag"))
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
            if not _allowed_for_target(definition, self.current_target):
                return False
            if definition.hat:
                if path or script_index is None or script_index < 0:
                    return False
                return self.new_script(type_)
            if self.current_procedure:
                procedure = next(item for item in self.project.procedures
                                 if item.name == self.current_procedure)
                script_index = -1 - self.project.procedures.index(procedure)
                index = len(blocks_at(self.project, script_index))
            insert_block(self.project, script_index, path, index, type_)
        else:
            source = payload[1]
            if BLOCKS[payload[2].type].hat and (path or self.current_procedure):
                return False
            if not _allowed_for_target(BLOCKS[payload[2].type],
                                       self.current_target):
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
    def _ensure_target(self):
        """Return a valid target name for newly created scripts."""
        if self.current_target == STAGE_NAME:
            return STAGE_NAME
        if not self.project.sprites:
            self.current_target = STAGE_NAME
            self.current_sprite = STAGE_NAME
            return STAGE_NAME
        if not any(item.name == self.current_target
                   for item in self.project.sprites):
            self.current_target = self.project.sprites[0].name
            self.current_sprite = self.current_target
        return self.current_target

    def _ensure_sprite(self):
        target = self._ensure_target()
        return "" if target == STAGE_NAME else target

    def _current_script_index(self):
        for index, _ in scripts_for_target(self.project, self._ensure_target()):
            return index
        return None

    def new_script(self, hat_type="event_flag"):
        definition = BLOCKS.get(hat_type)
        if definition is None or not definition.hat:
            return False
        if self.current_procedure:
            self.error.emit("Event blocks belong in scripts, not My Blocks.")
            return False
        self.project.scripts.append(
            _new_target_script(self._ensure_target(), hat_type))
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
        if not _allowed_for_target(definition, self.current_target):
            self.error.emit("That block cannot run on %s." % self.current_target)
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
            self.project.scripts.append(_new_target_script(
                self._ensure_target(), "event_flag"))
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
        """Draw one of the four built-in spirit shapes."""
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

    @staticmethod
    def _pixmap(name, engine):
        """Build a QPixmap from an embedded RGBA picture, if available."""
        if not name:
            return None
        entry = getattr(engine, "images", {}).get(name)
        if not entry:
            return None
        width, height, rgba = entry
        if width <= 0 or height <= 0 or not rgba:
            return None
        try:
            image = QImage(bytes(rgba), width, height,
                           QImage.Format.Format_RGBA8888)
            if image.isNull():
                return None
            return QPixmap.fromImage(image.copy())
        except (TypeError, ValueError):
            return None

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            width, height = self.project.width, self.project.height
            scale = min(self.width() / width, self.height() / height)
            offset_x = (self.width() - width * scale) / 2
            offset_y = (self.height() - height * scale) / 2

            painter.fillRect(self.rect(), QColor(theme.SCRATCH["stage"]))
            painter.fillRect(int(offset_x), int(offset_y),
                             int(width * scale), int(height * scale),
                             QColor(self.engine.background))
            backdrop = self._pixmap(getattr(self.engine, "backdrop", ""),
                                    self.engine)
            if backdrop is not None:
                # Embedded stage pictures are drawn first, under the faint grid.
                painter.drawPixmap(int(offset_x), int(offset_y),
                                   int(width * scale), int(height * scale),
                                   backdrop)
            painter.setPen(QPen(QColor(0, 0, 0, 18), 1))
            painter.drawRect(int(offset_x), int(offset_y),
                             int(width * scale), int(height * scale))

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
            for spirit in sorted(
                    self.engine.sprites,
                    key=lambda item: (item.get("layer", 0), item["name"])):
                if not spirit["visible"]:
                    continue
                x = offset_x + (width / 2 + spirit["x"]) * scale
                y = offset_y + (height / 2 - spirit["y"]) * scale
                size = max(6, spirit["size"] / 100 * 36 * scale)
                picture = self._pixmap(spirit.get("image", ""), self.engine)
                if picture is not None:
                    target = QRectF(x - size / 2, y - size / 2, size, size)
                    painter.drawPixmap(
                        target, picture,
                        QRectF(0, 0, picture.width(), picture.height()))
                else:
                    color = QColor(spirit["color"])
                    for _ in range(1, spirit["costume"]):
                        red, green, blue = color.red(), color.green(), color.blue()
                        color = QColor(green, blue, red)
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(color.lighter(140), 1.5))
                    self._draw_sprite(painter, spirit["shape"], x, y, size)
                end_x, end_y = heading_endpoint(
                    x, y, spirit["direction"], size * 0.45
                )
                painter.setPen(QPen(QColor(theme.SCRATCH["text"]), 1))
                painter.drawLine(x, y, end_x, end_y)
                if spirit["say_until"] > now:
                    rect = QRectF(int(x - 42), int(y - size - 34), 84, 24)
                    painter.setBrush(QBrush(QColor(theme.SCRATCH["panel_alt"])))
                    painter.setPen(QPen(QColor(theme.SCRATCH["text"]), 1))
                    painter.drawRoundedRect(rect, 7, 7)
                    painter.drawText(rect, Qt.AlignCenter,
                                     spirit["say_text"][:22])
        finally:
            painter.end()


class MainWindow(QMainWindow):
    """The Scratch-like blockforge editor window."""

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
        self.setMinimumSize(1120, 700)
        self.resize(1440, 900)
        self.setStyleSheet(theme.stylesheet() + _EDITOR_STYLE)
        self._temp_dir = None
        self._output_cursor = 0
        self.binary_path = None
        self.build_process = None
        self.run_process = None
        self.export_binary_action = None
        self.engine = PreviewEngine(self.project)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._preview_tick)

        self._build_toolbar()
        self._build_body()
        self._connect_signals()
        self.refresh_source()
        self._refresh_lists()
        self.statusBar().showMessage(
            "Ready — drag blocks into the workspace, or open an example.")

    # --- construction ---------------------------------------------------------
    def _build_toolbar(self):
        """Build Scratch's 3rem purple menu bar."""
        toolbar = QToolBar("Main")
        toolbar.setObjectName("toolbar")
        toolbar.setMovable(False)
        toolbar.setFixedHeight(48)
        self.addToolBar(toolbar)

        brand = QLabel("blockforge")
        brand.setObjectName("brandLogo")
        toolbar.addWidget(brand)

        file_button = QToolButton()
        file_button.setText("File")
        file_button.setObjectName("fileMenuButton")
        file_menu = QMenu(file_button)
        actions = (
            ("new", "New", self.new_project, "Ctrl+N"),
            ("open", "Open project", self.open_project, "Ctrl+O"),
            ("save", "Save project", self.save_project, "Ctrl+S"),
            ("save_as", "Save as", self.save_project_as, "Ctrl+Shift+S"),
            ("export", "Export source folder", self.export_source, None),
            ("build", "Build", self.build_project, "Ctrl+B"),
            ("run", "Run", self.run_binary, "F5"),
            ("stop", "Stop", self.stop_all, None),
            ("settings", "Project settings", self.edit_settings, None),
        )
        for key, text, callback, shortcut in actions:
            action = self._action(key, text, callback, shortcut)
            file_menu.addAction(action)
            if key == "run":
                self.run_button = action
        file_button.setMenu(file_menu)
        file_button.setPopupMode(QToolButton.InstantPopup)
        toolbar.addWidget(file_button)

        edit_button = QToolButton()
        edit_button.setText("Edit")
        edit_button.setObjectName("editMenuButton")
        edit_menu = QMenu(edit_button)
        edit_menu.addAction("Add spirit", self.add_sprite)
        edit_menu.addAction("Make a variable", self.add_variable)
        edit_menu.addAction("Make a My Block", self.add_procedure)
        edit_menu.addAction("Change stage look", self.choose_background)
        edit_menu.addAction("Examples", self._show_examples)
        edit_button.setMenu(edit_menu)
        edit_button.setPopupMode(QToolButton.InstantPopup)
        toolbar.addWidget(edit_button)

        self.title_label = QLineEdit(self.project.name)
        self.title_label.setObjectName("projectTitle")
        self.title_label.setToolTip("Project name")
        self.title_label.setSizePolicy(QSizePolicy.Expanding,
                                       QSizePolicy.Fixed)
        self.title_label.editingFinished.connect(self._title_finished)
        toolbar.addWidget(self.title_label)

        self.language_combo = QComboBox()
        self.language_combo.setObjectName("languageCombo")
        self.language_combo.addItems(["C++", "Rust"])
        self.language_combo.setCurrentText(
            "Rust" if self.language == "rust" else "C++")
        toolbar.addWidget(self.language_combo)

        examples = QToolButton()
        examples.setText("Examples")
        examples.setObjectName("examplesButton")
        examples.setIcon(theme.icon("examples", "#FFFFFF"))
        examples.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        examples.setMenu(self._examples_menu(examples))
        examples.setPopupMode(QToolButton.InstantPopup)
        toolbar.addWidget(examples)

    def _examples_menu(self, parent):
        menu = QMenu(parent)
        for key in EXAMPLES:
            menu.addAction(EXAMPLE_LABELS.get(key, key),
                           lambda checked=False, name=key: self.load_example(name))
        return menu

    def _show_examples(self):
        """Open the examples menu from the Edit menu."""
        button = self.findChild(QToolButton, "examplesButton")
        if button is not None:
            button.menu().exec(button.mapToGlobal(QPoint(0, button.height())))

    def _action(self, glyph, text, callback, shortcut=None):
        action = QAction(theme.icon(glyph, "#FFFFFF"), text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
            action.setToolTip("%s (%s)" % (text, shortcut))
        action.triggered.connect(callback)
        return action

    def _build_body(self):
        """Build Scratch's two-column editor and 408px stage column."""
        self.palette = BlockPalette(self.project, self.workspace_target_name())
        self.palette_list = self.palette.palette_list
        self.workspace = Workspace(self.project)
        self.workspace.set_current_target(self.palette.target)

        editor = QFrame()
        editor.setObjectName("editorPane")
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        tabs = QFrame()
        tabs.setObjectName("editorTabs")
        tabs.setFixedHeight(44)
        tabs_layout = QHBoxLayout(tabs)
        tabs_layout.setContentsMargins(0, 8, 0, 0)
        tabs_layout.setSpacing(0)
        tabs_layout.addStretch(1)
        self.editor_tabs = {}
        for name, text in (("tabBlocks", "Blocks"),
                           ("tabCostumes", "Costumes"),
                           ("tabSounds", "Sounds")):
            button = QToolButton()
            button.setText(text)
            button.setObjectName(name)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            tabs_layout.addWidget(button)
            self.editor_tabs[name] = button
        self.editor_tabs["tabBlocks"].setChecked(True)
        tabs_layout.addStretch(1)
        editor_layout.addWidget(tabs)

        self.editor_stack = QStackedWidget()
        self.editor_stack.addWidget(self._build_block_editor())
        self.editor_stack.addWidget(self._build_costume_pane())
        self.editor_stack.addWidget(self._build_sound_pane())
        editor_layout.addWidget(self.editor_stack, 1)
        for index, name in enumerate(("tabBlocks", "tabCostumes", "tabSounds")):
            self.editor_tabs[name].clicked.connect(
                lambda checked=False, row=index: self.editor_stack.setCurrentIndex(row)
            )

        stage_column = QFrame()
        stage_column.setObjectName("stageColumn")
        stage_column.setFixedWidth(424)
        stage_layout = QVBoxLayout(stage_column)
        stage_layout.setContentsMargins(8, 0, 0, 0)
        stage_layout.setSpacing(4)

        header = QFrame()
        header.setObjectName("stageHeader")
        header.setFixedHeight(44)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 4, 8, 4)
        heading = QLabel("Stage")
        heading.setObjectName("stageHeading")
        header_layout.addWidget(heading)
        header_layout.addStretch(1)
        backdrop = QToolButton()
        backdrop.setText("Backdrop")
        backdrop.setObjectName("backdropButton")
        backdrop.clicked.connect(self.choose_background)
        header_layout.addWidget(backdrop)
        self.preview_button = QToolButton()
        self.preview_button.setObjectName("previewButton")
        self.preview_button.setText("")
        self.preview_button.clicked.connect(self.toggle_preview)
        self._set_preview_button(False)
        header_layout.addWidget(self.preview_button)
        stop = QToolButton()
        stop.setObjectName("stopButton")
        stop.setText("")
        stop.setIcon(theme.icon("stop", "#FF661A"))
        stop.setToolTip("Stop")
        stop.clicked.connect(self.stop_all)
        header_layout.addWidget(stop)
        stage_layout.addWidget(header)

        stage_pane = QFrame()
        stage_pane.setObjectName("stagePane")
        stage_pane_layout = QVBoxLayout(stage_pane)
        stage_pane_layout.setContentsMargins(0, 0, 0, 0)
        stage_pane_layout.setAlignment(Qt.AlignCenter)
        stage_frame = QFrame()
        stage_frame.setObjectName("stageFrame")
        stage_frame.setFixedWidth(408)
        stage_frame.setFixedHeight(308)
        stage_frame_layout = QVBoxLayout(stage_frame)
        stage_frame_layout.setContentsMargins(4, 4, 4, 4)
        self.stage = StageWidget(self.project, self.engine)
        stage_frame_layout.addWidget(self.stage)
        stage_pane_layout.addWidget(stage_frame, 0, Qt.AlignCenter)
        stage_layout.addWidget(stage_pane, 1)

        target = QFrame()
        target.setObjectName("targetPane")
        target_layout = QHBoxLayout(target)
        target_layout.setContentsMargins(4, 6, 8, 0)
        target_layout.setSpacing(4)

        self.stage_selector = QToolButton()
        self.stage_selector.setObjectName("stageSelector")
        self.stage_selector.setText("Stage")
        self.stage_selector.setIcon(theme.icon("stage", theme.SCRATCH["text"]))
        self.stage_selector.setIconSize(QSize(36, 36))
        self.stage_selector.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.stage_selector.setCheckable(True)
        self.stage_selector.clicked.connect(
            lambda: self.set_current_target(STAGE_NAME))
        target_layout.addWidget(self.stage_selector)

        sprite_pane = QFrame()
        sprite_pane.setObjectName("spritePane")
        sprite_pane_layout = QVBoxLayout(sprite_pane)
        sprite_pane_layout.setContentsMargins(0, 0, 0, 0)
        sprite_pane_layout.setSpacing(0)

        info = QFrame()
        info.setObjectName("spriteInfo")
        info.setFixedHeight(64)
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(6, 4, 6, 4)
        info_layout.setSpacing(2)
        self.sprite_name_label = QLabel("Sprites")
        self.sprite_name_label.setObjectName("sectionTitle")
        info_layout.addWidget(self.sprite_name_label)
        controls = QHBoxLayout()
        self.editor_target = QComboBox()
        self.editor_target.setObjectName("editorTarget")
        self.editor_target.setMaximumWidth(132)
        controls.addWidget(self.editor_target)
        new_script = QToolButton()
        new_script.setObjectName("newScriptButton")
        new_script.setText("+")
        new_script.setToolTip("New script")
        new_script.clicked.connect(lambda: self.workspace.new_script())
        controls.addWidget(new_script)
        add_sprite = QToolButton()
        add_sprite.setObjectName("addSpriteButton")
        add_sprite.setIcon(theme.icon("sprite", theme.SCRATCH["accent"]))
        add_sprite.setToolTip("Add spirit")
        add_sprite.clicked.connect(self.add_sprite)
        controls.addWidget(add_sprite)
        edit_sprite = QToolButton()
        edit_sprite.setObjectName("editSpriteButton")
        edit_sprite.setIcon(theme.icon("settings"))
        edit_sprite.setToolTip("Edit spirit")
        edit_sprite.clicked.connect(self.edit_sprite)
        controls.addWidget(edit_sprite)
        library = QToolButton()
        library.setObjectName("libraryButton")
        library.setIcon(theme.icon("book"))
        library.setToolTip("Open library")
        library.clicked.connect(self.add_from_library)
        controls.addWidget(library)
        controls.addStretch(1)
        info_layout.addLayout(controls)
        sprite_pane_layout.addWidget(info)

        self.sprite_list = QListWidget()
        self.sprite_list.setObjectName("spriteList")
        self.sprite_list.setViewMode(QListView.IconMode)
        self.sprite_list.setMovement(QListView.Static)
        self.sprite_list.setResizeMode(QListView.Adjust)
        self.sprite_list.setGridSize(QSize(82, 78))
        self.sprite_list.setIconSize(QSize(54, 46))
        self.sprite_list.setSpacing(2)
        self.sprite_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sprite_list.customContextMenuRequested.connect(
            self._show_sprite_context_menu)
        sprite_pane_layout.addWidget(self.sprite_list, 1)
        target_layout.addWidget(sprite_pane, 1)
        stage_layout.addWidget(target, 0, Qt.AlignBottom)

        # Variable and My Block lists are driven by the Data/My Blocks flyouts.
        self.variable_list = QListWidget()
        self.variable_list.setObjectName("variableList")
        self.variable_list.hide()
        self.procedure_list = QListWidget()
        self.procedure_list.setObjectName("procedureList")
        self.procedure_list.hide()

        top = QSplitter(Qt.Horizontal)
        top.setObjectName("mainSplitter")
        top.setChildrenCollapsible(False)
        top.addWidget(editor)
        top.addWidget(stage_column)
        top.setStretchFactor(0, 1)
        top.setStretchFactor(1, 0)
        top.setSizes([1000, 424])
        self.setCentralWidget(top)

        # Build messages only appear when there is something useful to show;
        # the default editor stays as clean as Scratch's.
        self.console = QTabWidget()
        self.console.setObjectName("consolePanel")
        self.console.setMaximumHeight(190)
        self.build_view = QPlainTextEdit()
        self.build_view.setObjectName("buildView")
        self.build_view.setReadOnly(True)
        self.build_view.setMaximumBlockCount(3000)
        self.output_view = QPlainTextEdit()
        self.output_view.setObjectName("outputView")
        self.output_view.setReadOnly(True)
        self.output_view.setMaximumBlockCount(3000)
        self.console.addTab(self.build_view, "Build log")
        self.console.addTab(self.output_view, "Preview output")
        self.console_dock = QDockWidget("Build output", self)
        self.console_dock.setObjectName("consoleDock")
        self.console_dock.setWidget(self.console)
        self.console_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.console_dock)
        self.console.hide()
        self.console_dock.hide()

    def _build_block_editor(self):
        editor = QSplitter(Qt.Horizontal)
        editor.setObjectName("blockEditor")
        editor.setChildrenCollapsible(False)
        editor.addWidget(self.palette)
        editor.addWidget(self.workspace)
        editor.setStretchFactor(0, 0)
        editor.setStretchFactor(1, 1)
        editor.setSizes([330, 700])
        return editor

    def _build_costume_pane(self):
        pane = QFrame()
        pane.setObjectName("costumePane")
        layout = QVBoxLayout(pane)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.addWidget(self._label("Costumes", "sectionTitle"))
        hint = QLabel("Edit the selected spirit's picture, color and size.")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        button = QPushButton("Edit costume")
        button.clicked.connect(self.edit_sprite)
        layout.addWidget(button)
        return pane

    def _build_sound_pane(self):
        pane = QFrame()
        pane.setObjectName("soundPane")
        layout = QVBoxLayout(pane)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.addWidget(self._label("Sounds", "sectionTitle"))
        hint = QLabel(
            "Sound blocks are in the palette. This editor does not bundle "
            "sound files."
        )
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        return pane

    @staticmethod
    def _label(text, object_name):
        label = QLabel(text)
        label.setObjectName(object_name)
        return label

    def _set_preview_button(self, running):
        """Use Scratch's green flag and stop sign for live preview."""
        self.preview_button.setText("")
        self.preview_button.setIcon(theme.icon(
            "flag", "#FF661A" if running else "#0FBD8C"))
        self.preview_button.setToolTip(
            "Stop preview" if running else "Start preview")

    def _title_finished(self):
        name = self.title_label.text().strip().strip("*").strip()
        if not name:
            name = "Untitled"
        if name != self.project.name:
            self.project.name = name
            self._mark_dirty(force_title=True)
        else:
            self._refresh_title(force=True)

    def _sprite_icon(self, spirit):
        """Return a small Scratch-style card icon for a spirit."""
        from images import decode_png

        data = self.project.assets.get(spirit.image or "")
        if data:
            try:
                width, height, rgba = decode_png(data)
                image = QImage(bytes(rgba), width, height,
                               QImage.Format.Format_RGBA8888)
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image).scaled(
                        54, 46, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    if not pixmap.isNull():
                        return QIcon(pixmap)
            except (ValueError, TypeError):
                pass
        return theme.icon("sprite", spirit.color or theme.SCRATCH["accent"])

    def _connect_signals(self):
        self.palette.blockRequested.connect(self.workspace.add_block)
        self.palette.variableRequested.connect(self.add_variable)
        self.palette.procedureRequested.connect(self.add_procedure)
        self.palette.variableEditRequested.connect(self._edit_variable_named)
        self.palette.variableRemoveRequested.connect(self._remove_variable_named)
        self.palette.procedureEditRequested.connect(self._edit_procedure_named)
        self.palette.procedureRemoveRequested.connect(self._remove_procedure_named)
        self.workspace.projectChanged.connect(self._project_changed)
        self.workspace.error.connect(
            lambda message: self.statusBar().showMessage(message)
        )
        self.language_combo.currentTextChanged.connect(self._language_changed)
        self.editor_target.currentTextChanged.connect(self.workspace.set_target)
        self.sprite_list.currentRowChanged.connect(self._sprite_selected)
        self.sprite_list.itemDoubleClicked.connect(self.edit_sprite)
        self.variable_list.itemDoubleClicked.connect(self.edit_variable)
        self.procedure_list.itemDoubleClicked.connect(self.edit_procedure)

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

    def workspace_target_name(self):
        return (self.project.sprites[0].name if self.project.sprites
                else STAGE_NAME)

    def _refresh_title(self, force=False):
        marker = "*" if self.dirty else ""
        text = self.project.name + marker
        if force or not self.title_label.hasFocus():
            self.title_label.setText(text)
        self.setWindowTitle("blockforge — %s%s" % (self.project.name, marker))

    def _mark_dirty(self, force_title=False):
        self.dirty = True
        self._refresh_title(force=force_title)

    def _invalidate_build(self):
        """Forget a binary that no longer matches the current project."""
        self.binary_path = None
        self.run_button.setEnabled(False)
        if self.export_binary_action is not None:
            self.export_binary_action.setEnabled(False)

    def _adopt_project(self, project, message, path=None, dirty=False):
        """Replace the active project and reset all dependent state."""
        if self.engine.running:
            self.engine.stop()
            self._timer.stop()
            self._set_preview_button(False)
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
        self._refresh_lists()
        self.engine.project = self.project
        self.stage.project = self.project
        self.engine.sync_project()
        self.stage.update()

    def _language_changed(self, text):
        self.language = "rust" if text == "Rust" else "cpp"
        self.project.language = self.language
        self._project_changed()
        self.statusBar().showMessage("Language changed to %s" % text)

    def refresh_source(self):
        """Compatibility hook only.

        Generated code is deliberately not produced or displayed while editing;
        it is created lazily by Build and by folder export.
        """
        self.project.language = self.language

    def _refresh_lists(self):
        self._refresh_title()
        target = self.workspace.current_target or self.workspace_target_name()
        stage_selected = target == STAGE_NAME
        self.stage_selector.setChecked(stage_selected)
        self.sprite_list.blockSignals(True)
        self.sprite_list.clear()
        for spirit in self.project.sprites:
            item = QListWidgetItem(self._sprite_icon(spirit), spirit.name)
            item.setToolTip(spirit.name)
            self.sprite_list.addItem(item)
        if not stage_selected:
            matches = self.sprite_list.findItems(target, Qt.MatchExactly)
            if matches:
                self.sprite_list.setCurrentItem(matches[0])
            elif self.sprite_list.count():
                self.sprite_list.setCurrentRow(0)
        self.sprite_list.blockSignals(False)
        if stage_selected:
            actual = STAGE_NAME
        else:
            actual = (self.sprite_list.currentItem().text()
                      if self.sprite_list.currentItem()
                      else self.workspace_target_name())
        if actual != self.workspace.current_target:
            self.workspace.set_current_target(actual)
        self.palette.set_target(actual)
        self._update_target_info(actual)

        self.variable_list.clear()
        self.variable_list.addItems([
            "%s : %s" % (variable.name, variable.type)
            for variable in self.project.variables
        ])
        if self.variable_list.count():
            self.variable_list.setCurrentRow(0)
        self.procedure_list.clear()
        for procedure in self.project.procedures:
            parameters = ", ".join(
                "%s: %s" % (param["name"], param["type"])
                for param in procedure.params
            )
            self.procedure_list.addItem("define %s(%s)" %
                                        (procedure.name, parameters))
        selected_procedure = self.workspace.current_procedure
        if selected_procedure:
            matches = self.procedure_list.findItems(
                "define %s(" % selected_procedure, Qt.MatchStartsWith)
            if matches:
                self.procedure_list.setCurrentItem(matches[0])
        elif self.procedure_list.count():
            self.procedure_list.setCurrentRow(0)

        self.editor_target.blockSignals(True)
        self.editor_target.clear()
        self.editor_target.addItems(self.workspace.target_names())
        self.editor_target.setCurrentText(self.workspace.target_text())
        self.editor_target.blockSignals(False)

    def _update_target_info(self, name):
        if name == STAGE_NAME:
            self.sprite_name_label.setText("Stage · backdrop")
            return
        spirit = next((item for item in self.project.sprites
                       if item.name == name), None)
        if spirit is None:
            self.sprite_name_label.setText(name)
        else:
            self.sprite_name_label.setText(
                "%s · x %d, y %d" % (spirit.name, round(spirit.x),
                                     round(spirit.y))
            )

    def _sprite_selected(self, row):
        if 0 <= row < len(self.project.sprites):
            self.set_current_target(self.project.sprites[row].name)

    def set_current_target(self, name):
        """Show scripts for a spirit name or for ``"Stage"``."""
        name = name or STAGE_NAME
        stage_selected = name == STAGE_NAME
        self.stage_selector.setChecked(stage_selected)
        self.workspace.set_current_target(name)
        self.palette.set_target(name)
        self.sprite_list.blockSignals(True)
        if stage_selected:
            self.sprite_list.clearSelection()
        else:
            matches = self.sprite_list.findItems(name, Qt.MatchExactly)
            if matches:
                self.sprite_list.setCurrentItem(matches[0])
        self.sprite_list.blockSignals(False)
        self._update_target_info(name)

    def set_current_sprite(self, name):
        self.set_current_target(name)

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
    def _suggested_name(self):
        base = re.sub(r"[^A-Za-z0-9_-]+", "-",
                      self.project.name.lower()).strip("-") or "project"
        return base + ".bfproj"

    def load_example(self, name):
        if not self._confirm_discard("loading an example"):
            return
        label = EXAMPLE_LABELS.get(name, name)
        self._adopt_project(deepcopy(example_project(name)),
                            "Loaded example: %s" % label)

    def new_project(self):
        if not self._confirm_discard("creating a new project"):
            return
        spirit = Sprite(name="Sprite")
        project = Project(
            name="Untitled", language=self.language,
            sprites=[spirit],
            scripts=[_new_target_script(spirit.name, "event_flag")],
        )
        self._adopt_project(project, "New project", dirty=True)

    def open_project(self):
        if not self._confirm_discard("opening a project"):
            return
        folder = str(Path(self.project_path).parent) if self.project_path else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open blockforge project", folder, PROJECT_FILTER,
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
            suggested = Path(path).name if path else self._suggested_name()
            initial = str(Path(path)) if path else suggested
            path, _ = QFileDialog.getSaveFileName(
                self, "Save blockforge project", initial, PROJECT_FILTER,
            )
        if not path:
            return False
        path = str(path)
        if not path.lower().endswith(".bfproj"):
            path += ".bfproj"
        try:
            validate_project(self.project)
            self.project.language = self.language
            save_project(self.project, path)
        except ValidationError as error:
            QMessageBox.warning(self, "Cannot save project", str(error))
            return False
        except OSError as error:
            QMessageBox.warning(self, "Cannot save project", str(error))
            return False
        self.project_path = path
        self.dirty = False
        self._refresh_title()
        self.statusBar().showMessage("Saved %s" % path)
        return True

    def save_project_as(self):
        return self.save_project(save_as=True)

    def _export_readme(self, source_name):
        safe = re.sub(r"[^A-Za-z0-9_-]+", "-",
                      self.project.name.lower()).strip("-") or "program"
        if self.language == "cpp":
            return (
                "# %s\n\n"
                "Generated from a Blockforge project. Requires a C++17 compiler "
                "and SDL2.\n\n"
                "Build:\n  g++ -std=c++17 -O2 -pthread %s -o %s -lSDL2\n\n"
                "Run:\n  ./%s\n"
                % (self.project.name, source_name, safe, safe)
            )
        return (
            "# %s\n\n"
            "Generated from a Blockforge project. Requires Rust 2021 and SDL2.\n\n"
            "Build:\n  rustc --edition 2021 -O %s -o %s -l dylib=SDL2\n\n"
            "Run:\n  ./%s\n"
            % (self.project.name, source_name, safe, safe)
        )

    def export_source(self):
        """Write a runnable source folder (not a loose source file)."""
        initial = str(Path(self.project_path).parent) \
            if self.project_path else ""
        folder = QFileDialog.getExistingDirectory(
            self, "Export project folder", initial)
        if not folder:
            return
        source_name = "main.cpp" if self.language == "cpp" else "main.rs"
        target = Path(folder) / source_name
        if target.exists():
            answer = QMessageBox.question(
                self, "Export project folder",
                "%s already exists. Replace it?" % target,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            self.project.language = self.language
            source = generate_source(self.project, self.language)
            target.write_text(source, encoding="utf-8")
            (Path(folder) / "README.md").write_text(
                self._export_readme(source_name), encoding="utf-8")
        except (ValidationError, OSError) as error:
            QMessageBox.warning(self, "Cannot export project", str(error))
            return
        self.statusBar().showMessage("Exported project to %s" % folder)

    def export_binary(self):
        if not self.binary_path or not Path(self.binary_path).exists():
            self.statusBar().showMessage("Build the project before saving it")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save program", self.project.name or "program",
            "Program (*)",
        )
        if not path:
            return
        try:
            shutil.copy2(self.binary_path, path)
        except OSError as error:
            QMessageBox.warning(self, "Cannot save program", str(error))
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

    def _sprite_context_menu(self):
        menu = QMenu(self.sprite_list)
        menu.addAction("Edit spirit", self.edit_sprite)
        remove = menu.addAction("Remove spirit", self.remove_sprite)
        remove.setEnabled(len(self.project.sprites) > 1)
        return menu

    def _show_sprite_context_menu(self, position):
        item = self.sprite_list.itemAt(position)
        if item is None:
            return
        self.sprite_list.setCurrentItem(item)
        self._sprite_context_menu().exec(
            self.sprite_list.viewport().mapToGlobal(position))

    def _select_named(self, widget, items, name):
        for row, item in enumerate(items):
            if item.name == name:
                widget.setCurrentRow(row)
                return True
        return False

    def _edit_variable_named(self, name):
        if self._select_named(self.variable_list, self.project.variables, name):
            self.edit_variable()

    def _remove_variable_named(self, name):
        if self._select_named(self.variable_list, self.project.variables, name):
            self.remove_variable()

    def _edit_procedure_named(self, name):
        if self._select_named(self.procedure_list, self.project.procedures, name):
            self.edit_procedure()

    def _remove_procedure_named(self, name):
        if self._select_named(self.procedure_list, self.project.procedures, name):
            self.remove_procedure()

    # --- spirit, variable, and custom-block management -------------------------
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
        dialog = SpiritDialog(names=self._sprite_names(), parent=self,
                              assets=self.project.assets)
        if not dialog.exec():
            return
        spirit = dialog.sprite()
        self.project.sprites.append(spirit)
        self.set_current_target(spirit.name)
        self._project_changed()
        self.statusBar().showMessage("Added spirit %s" % spirit.name)

    def edit_sprite(self):
        spirit = self._selected_sprite()
        if spirit is None:
            return
        dialog = SpiritDialog(spirit, self._sprite_names(), self,
                              assets=self.project.assets)
        if not dialog.exec():
            return
        updated = dialog.sprite()
        old_name = spirit.name
        for key in ("name", "x", "y", "size", "direction", "costume",
                    "costume_count", "layer", "shape", "color", "visible",
                    "image"):
            setattr(spirit, key, getattr(updated, key))
        if old_name != updated.name:
            for script in self.project.scripts:
                if script_target(script) == "spirit" and \
                        script.get("sprite") == old_name:
                    script["sprite"] = updated.name
            self._rename_expression_references(old_name, updated.name)
            self.workspace.current_target = updated.name
            self.workspace.current_sprite = updated.name
            self.set_current_target(updated.name)
        self._project_changed()

    def remove_sprite(self):
        spirit = self._selected_sprite()
        if spirit is None or len(self.project.sprites) <= 1:
            return
        if not self.isVisible() or QMessageBox.question(
                self, "Remove spirit",
                "Remove %s and all of its scripts?" % spirit.name,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.project.sprites.remove(spirit)
            self.project.scripts = [
                item for item in self.project.scripts
                if script_target(item) != "spirit" or
                item.get("sprite") != spirit.name
            ]
            target = (self.project.sprites[0].name if self.project.sprites
                      else STAGE_NAME)
            self.workspace.current_target = target
            self.workspace.current_sprite = target
            self.set_current_target(target)
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
        if self.workspace.current_procedure == name:
            self.editor_target.setCurrentText("My Block: %s" % name)

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

    def add_from_library(self):
        dialog = LibraryDialog(self.project, self)
        if not dialog.exec():
            return
        selection = dialog.selected()
        if not selection:
            return
        kind, key = selection
        if kind == "spirit":
            spirit = spirit_from_preset(self.project, key)
            self.project.sprites.append(spirit)
            starter = spirit_start_script(key, spirit.name)
            if starter:
                self.project.scripts.append(deepcopy(starter))
            self.set_current_target(spirit.name)
            message = "Added spirit %s" % spirit.name
        else:
            preset = apply_stage_preset(
                self.project, key, self.project.width, self.project.height)
            message = "Stage look changed to %s" % preset.label
        self._project_changed()
        self.statusBar().showMessage(message)

    def choose_background(self):
        dialog = StageDialog(self.project, self)
        if not dialog.exec():
            return
        dialog.apply(self.project)
        self._project_changed()
        self.statusBar().showMessage("Stage look updated")

    # --- preview, build, and run ---------------------------------------------
    def toggle_preview(self):
        if self.engine.running:
            self.engine.stop()
            self._timer.stop()
            self._set_preview_button(False)
            self.statusBar().showMessage("Preview stopped")
        else:
            self.output_view.clear()
            self._output_cursor = 0
            self.engine.start()
            self._timer.start()
            self._set_preview_button(True)
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
            self._set_preview_button(False)

    def _show_console(self, widget):
        self.console.setCurrentWidget(widget)
        self.console.show()
        self.console_dock.show()
        self.console_dock.raise_()

    def build_project(self):
        if self.build_process and \
                self.build_process.state() != QProcess.NotRunning:
            return
        self._show_console(self.build_view)
        self._invalidate_build()
        try:
            self.project.language = self.language
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
            self.statusBar().showMessage("Build failed — see the build log")

    def run_binary(self):
        if self.run_process and \
                self.run_process.state() != QProcess.NotRunning:
            return
        if not self.binary_path or not Path(self.binary_path).exists():
            self.statusBar().showMessage("Build the project before running it")
            return
        self.output_view.clear()
        self._show_console(self.output_view)
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
        if self.run_process and \
                self.run_process.state() != QProcess.NotRunning:
            self._terminate_process(self.run_process)
            self.statusBar().showMessage("Program stopped")
        if self.build_process and \
                self.build_process.state() != QProcess.NotRunning:
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
        prog="blockforge",
        description="Visual block editor for spirits, stages, and C++ or Rust programs",
    )
    parser.add_argument("project", nargs="?",
                        help="optional .bfproj project to open")
    parser.add_argument("--language", choices=["cpp", "rust"],
                        help="initial language")
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
