"""Blockforge's Qt-free project model.

A project is plain data: sprites, variables, procedures, and scripts made of
nested blocks.  Everything here works without PySide6 so the compiler, tests,
and command-line tools can run on a headless machine.
"""

from copy import deepcopy
from dataclasses import dataclass, field as dataclass_field
import json
import os
import re
from typing import Dict, List, Optional

from expressions import (
    BUILTINS,
    KEYS,
    ExpressionError,
    ExprContext,
    translate_expression,
)

FORMAT = "blockforge"
VERSION = 1
LANGUAGES = ("cpp", "rust")


class ValidationError(ValueError):
    """A user-facing error in a project or saved file."""


@dataclass
class FieldDef:
    name: str
    kind: str
    default: object = ""
    label: str = ""
    options: Optional[List[str]] = None
    help: str = ""


@dataclass
class BlockDef:
    type: str
    category: str
    template: str
    fields: List[FieldDef] = dataclass_field(default_factory=list)
    slots: List[str] = dataclass_field(default_factory=list)
    hat: bool = False
    reporter: bool = False
    help: str = ""


@dataclass
class Category:
    key: str
    name: str
    color: str
    glyph: str
    help: str = ""


CATEGORIES = [
    Category("events", "Events", "#ffab2e", "flag", "Start a script"),
    Category("motion", "Motion", "#4c9ffe", "move", "Move and turn sprites"),
    Category("looks", "Looks", "#a06cff", "eye", "Costumes and visibility"),
    Category("sound", "Sound", "#d95fd6", "wave", "Tones and audio"),
    Category("sensing", "Sensing", "#4fb8d8", "radar", "Ask about the world"),
    Category("control", "Control", "#f3b93b", "loop", "Loops and decisions"),
    Category("operators", "Operators", "#57c785", "braces", "Expressions"),
    Category("variables", "Variables", "#ff8a3d", "variable", "Stored values"),
    Category("pen", "Pen", "#2dd4bf", "pen", "Draw lines as sprites move"),
    Category("custom", "My Blocks", "#ff6f91", "puzzle", "Your own functions"),
]
CATEGORY_BY_KEY = {category.key: category for category in CATEGORIES}


def _field(name, kind, default="", label=None, options=None, help=""):
    return FieldDef(name, kind, default, label or name.replace("_", " ").title(),
                    options, help)


_EXPRESSION = "expression"
_NUMBER = "number"
_TEXT = "text"
_BOOL = "bool"


def argument_default(param):
    """Return a valid expression for a procedure parameter's type."""
    return {"text": '""', "bool": "false"}.get(param.get("type"), "0")

BLOCKS: Dict[str, BlockDef] = {}


def _block(type_, category, template, fields=(), slots=(), hat=False,
           reporter=False, help=""):
    BLOCKS[type_] = BlockDef(type_, category, template, list(fields),
                             list(slots), hat, reporter, help)


# --- Events -----------------------------------------------------------------
_block("event_flag", "events", "when green flag clicked", hat=True,
       help="Runs when the program starts.")
_block("event_key", "events", "when {key} key pressed",
       [_field("key", "key", "space")], hat=True,
       help="Runs whenever the chosen key goes down.")

# --- Motion -----------------------------------------------------------------
_block("motion_move", "motion", "move {steps} steps",
       [_field("steps", _NUMBER, "10")], help="Move forward in the direction faced.")
_block("motion_turn_right", "motion", "turn right {degrees} degrees",
       [_field("degrees", _NUMBER, "15")])
_block("motion_turn_left", "motion", "turn left {degrees} degrees",
       [_field("degrees", _NUMBER, "15")])
_block("motion_goto", "motion", "go to x: {x} y: {y}",
       [_field("x", _NUMBER, "0"), _field("y", _NUMBER, "0")])
_block("motion_change_x", "motion", "change x by {value}",
       [_field("value", _NUMBER, "10")])
_block("motion_change_y", "motion", "change y by {value}",
       [_field("value", _NUMBER, "10")])
_block("motion_set_x", "motion", "set x to {value}",
       [_field("value", _NUMBER, "0")])
_block("motion_set_y", "motion", "set y to {value}",
       [_field("value", _NUMBER, "0")])
_block("motion_point_direction", "motion", "point in direction {direction}",
       [_field("direction", _NUMBER, "90")])
_block("motion_point_towards", "motion", "point towards {target}",
       [_field("target", "target", "mouse")])
_block("motion_glide", "motion", "glide {secs} secs to x: {x} y: {y}",
       [_field("secs", _NUMBER, "1"), _field("x", _NUMBER, "0"),
        _field("y", _NUMBER, "0")])
_block("motion_bounce_edge", "motion", "bounce if on edge",
       help="Reverse direction when touching a stage edge.")

# --- Looks ------------------------------------------------------------------
_block("looks_say", "looks", "say {text} for {secs} secs",
       [_field("text", _TEXT, '"Hello!"'), _field("secs", _NUMBER, "2")])
_block("looks_show", "looks", "show")
_block("looks_hide", "looks", "hide")
_block("looks_set_size", "looks", "set size to {size} %",
       [_field("size", _NUMBER, "100")])
_block("looks_change_size", "looks", "change size by {value}",
       [_field("value", _NUMBER, "10")])
_block("looks_set_costume", "looks", "set costume to {costume}",
       [_field("costume", _NUMBER, "1")])
_block("looks_next_costume", "looks", "next costume")
_block("looks_set_background", "looks", "set background to {color}",
       [_field("color", "color", "#151a26")])

# --- Sound ------------------------------------------------------------------
_block("sound_tone", "sound", "play tone {freq} Hz for {secs} secs",
       [_field("freq", _NUMBER, "440"), _field("secs", _NUMBER, "0.2")])
_block("sound_stop", "sound", "stop all sounds")

# --- Sensing (reporters live in the palette and insert expressions) --------
_REPORTERS = [
    ("sensing_key_pressed", 'key pressed("space")', "Is a key down?"),
    ("sensing_touching_edge", "touching edge", "Touching a stage border?"),
    ("sensing_touching_sprite", 'touching sprite("Hero")', "Touching a sprite?"),
    ("sensing_x_position", "x position", "Sprite x coordinate"),
    ("sensing_y_position", "y position", "Sprite y coordinate"),
    ("sensing_direction", "direction", "Sprite heading"),
    ("sensing_costume", "costume", "Current costume number"),
    ("sensing_size", "size", "Sprite size percentage"),
    ("sensing_timer", "timer", "Seconds since start"),
    ("sensing_mouse_x", "mouse x", "Mouse x coordinate"),
    ("sensing_mouse_y", "mouse y", "Mouse y coordinate"),
]
for _type, _expression, _help in _REPORTERS:
    _block(_type, "sensing", _expression, reporter=True, help=_help)

_OPERATOR_REPORTERS = [
    ("operator_add", "a + b"),
    ("operator_subtract", "a - b"),
    ("operator_multiply", "a * b"),
    ("operator_divide", "a / b"),
    ("operator_mod", "a % b"),
    ("operator_random", "random(1, 10)"),
    ("operator_gt", "a > b"),
    ("operator_lt", "a < b"),
    ("operator_equal", "a == b"),
    ("operator_and", "a and b"),
    ("operator_or", "a or b"),
    ("operator_not", "not a"),
    ("operator_join", 'join("hello ", name)'),
    ("operator_length", 'len("text")'),
]
for _type, _expression in _OPERATOR_REPORTERS:
    _block(_type, "operators", _expression, reporter=True,
           help="Insert this expression into a field.")

# --- Control ----------------------------------------------------------------
_block("control_wait", "control", "wait {secs} secs",
       [_field("secs", _NUMBER, "1")])
_block("control_wait_until", "control", "wait until {condition}",
       [_field("condition", _BOOL, "false")])
_block("control_repeat", "control", "repeat {times}",
       [_field("times", _NUMBER, "10")], slots=["SUB"])
_block("control_forever", "control", "forever", slots=["SUB"])
_block("control_if", "control", "if {condition}",
       [_field("condition", _BOOL, "true")], slots=["SUB"])
_block("control_if_else", "control", "if {condition}",
       [_field("condition", _BOOL, "true")], slots=["THEN", "ELSE"])
_block("control_repeat_until", "control", "repeat until {condition}",
       [_field("condition", _BOOL, "false")], slots=["SUB"])
_block("control_stop", "control", "stop {choice}",
       [_field("choice", "choice", "this script",
               options=["this script", "all"])])
_block("control_print", "control", "print {value}",
       [_field("value", _EXPRESSION, '"Hello, world!"')],
       help="Write a line to the console.")

# --- Variables --------------------------------------------------------------
_block("variable_set", "variables", "set {name} to {value}",
       [_field("name", "variable", ""), _field("value", _EXPRESSION, "0")])
_block("variable_change", "variables", "change {name} by {value}",
       [_field("name", "variable", ""), _field("value", _NUMBER, "1")])
_block("variable_if", "variables", "if {name}",
       [_field("name", "variable", "")], slots=["SUB"])

# --- Pen --------------------------------------------------------------------
_block("pen_clear", "pen", "clear pen marks")
_block("pen_down", "pen", "pen down")
_block("pen_up", "pen", "pen up")
_block("pen_set_color", "pen", "set pen color to {color}",
       [_field("color", "color", "#4ade80")])
_block("pen_set_size", "pen", "set pen size to {size}",
       [_field("size", _NUMBER, "3")])

# --- My Blocks --------------------------------------------------------------
_block("procedure_call", "custom", "call {name}",
       [_field("name", "procedure", "")],
       help="Run a function you defined in My Blocks.")


@dataclass
class Block:
    type: str
    fields: Dict[str, object] = dataclass_field(default_factory=dict)
    children: Dict[str, List["Block"]] = dataclass_field(default_factory=dict)

    def to_dict(self):
        return {
            "type": self.type,
            "fields": dict(self.fields),
            "children": {slot: [item.to_dict() for item in items]
                         for slot, items in self.children.items()},
        }

    @classmethod
    def from_dict(cls, payload):
        if not isinstance(payload, dict) or "type" not in payload:
            raise ValidationError("block is missing its type")
        type_ = payload["type"]
        definition = BLOCKS.get(type_)
        if definition is None:
            raise ValidationError("unknown block type %r" % type_)
        raw_fields = payload.get("fields", {})
        raw_children = payload.get("children", {})
        if not isinstance(raw_fields, dict) or not isinstance(raw_children, dict):
            raise ValidationError("block %r has malformed fields or children" % type_)
        fields = {}
        for definition_field in definition.fields:
            value = raw_fields.get(definition_field.name, definition_field.default)
            fields[definition_field.name] = value
        # Argument fields are procedure-specific and therefore absent from the
        # static block catalog, but they still need to survive save/load.
        for name, value in raw_fields.items():
            if name.startswith("arg_") and name not in fields:
                fields[name] = value
        children = {}
        for slot in definition.slots:
            items = raw_children.get(slot, [])
            if not isinstance(items, list):
                raise ValidationError("block %r slot %r must be a list" % (type_, slot))
            children[slot] = [cls.from_dict(item) for item in items]
        return cls(type_, fields, children)

    def clone(self):
        return Block.from_dict(self.to_dict())

    def walk(self):
        yield self
        for items in self.children.values():
            for item in items:
                yield from item.walk()


def block(type_, **fields):
    """Small constructor used by examples, tests, and the palette."""
    children = fields.pop("children", None)
    definition = BLOCKS.get(type_)
    values = ({item.name: item.default for item in definition.fields}
              if definition else {})
    values.update(fields)
    if children is None:
        children = {slot: [] for slot in definition.slots} if definition else {}
    return Block(type_, values, deepcopy(children))


@dataclass
class Sprite:
    name: str = "Sprite"
    x: float = 0
    y: float = 0
    size: float = 100
    direction: float = 90
    shape: str = "circle"
    color: str = "#4c9ffe"
    costume: int = 1
    costume_count: int = 2
    visible: bool = True
    layer: int = 0

    def to_dict(self):
        return {
            "name": self.name, "x": self.x, "y": self.y,
            "size": self.size, "direction": self.direction,
            "shape": self.shape, "color": self.color,
            "costume": self.costume, "costume_count": self.costume_count,
            "visible": self.visible, "layer": self.layer,
        }

    @classmethod
    def from_dict(cls, payload):
        if not isinstance(payload, dict):
            raise ValidationError("sprite must be an object")
        values = cls().to_dict()
        values.update({key: value for key, value in payload.items()
                       if key in values})
        try:
            values["name"] = str(values["name"])
            for key in ("x", "y", "size", "direction"):
                values[key] = float(values[key])
            for key in ("costume", "costume_count", "layer"):
                values[key] = int(values[key])
        except (TypeError, ValueError) as exc:
            raise ValidationError("sprite has malformed properties") from exc
        return cls(**values)


@dataclass
class Variable:
    name: str
    type: str = "number"

    def to_dict(self):
        return {"name": self.name, "type": self.type}

    @classmethod
    def from_dict(cls, payload):
        if not isinstance(payload, dict):
            raise ValidationError("variable must be an object")
        return cls(str(payload.get("name", "")), payload.get("type", "number"))


@dataclass
class Procedure:
    name: str
    params: List[dict] = dataclass_field(default_factory=list)
    blocks: List[Block] = dataclass_field(default_factory=list)

    def to_dict(self):
        return {
            "name": self.name,
            "params": deepcopy(self.params),
            "blocks": [item.to_dict() for item in self.blocks],
        }

    @classmethod
    def from_dict(cls, payload):
        if not isinstance(payload, dict):
            raise ValidationError("procedure must be an object")
        params = payload.get("params", [])
        blocks = payload.get("blocks", [])
        if not isinstance(params, list) or not isinstance(blocks, list):
            raise ValidationError("procedure %r has malformed params or blocks"
                                  % payload.get("name", ""))
        return cls(
            str(payload.get("name", "")),
            [dict(item) if isinstance(item, dict) else {}
             for item in params],
            [Block.from_dict(item) for item in blocks],
        )


@dataclass
class Project:
    name: str = "Untitled"
    language: str = "cpp"
    width: int = 480
    height: int = 360
    background: str = "#151a26"
    description: str = ""
    sprites: List[Sprite] = dataclass_field(default_factory=list)
    variables: List[Variable] = dataclass_field(default_factory=list)
    procedures: List[Procedure] = dataclass_field(default_factory=list)
    scripts: List[dict] = dataclass_field(default_factory=list)

    def to_dict(self):
        return {
            "format": FORMAT,
            "version": VERSION,
            "name": self.name,
            "language": self.language,
            "stage": {
                "width": self.width, "height": self.height,
                "background": self.background,
            },
            "description": self.description,
            "sprites": [sprite.to_dict() for sprite in self.sprites],
            "variables": [variable.to_dict() for variable in self.variables],
            "procedures": [procedure.to_dict() for procedure in self.procedures],
            "scripts": [
                {
                    "sprite": script["sprite"],
                    "x": script.get("x", 32),
                    "y": script.get("y", 32),
                    "blocks": [item.to_dict() for item in script["blocks"]],
                }
                for script in self.scripts
            ],
        }

    @classmethod
    def from_dict(cls, payload):
        if not isinstance(payload, dict):
            raise ValidationError("project root must be an object")
        if payload.get("format") != FORMAT:
            raise ValidationError("not a blockforge project")
        if payload.get("version") != VERSION:
            raise ValidationError(
                "unsupported project version %r" % payload.get("version")
            )
        stage = payload.get("stage", {})
        if not isinstance(stage, dict):
            raise ValidationError("project stage must be an object")
        for key in ("sprites", "variables", "procedures", "scripts"):
            if not isinstance(payload.get(key, []), list):
                raise ValidationError("project %s must be a list" % key)
        try:
            width = int(stage.get("width", 480))
            height = int(stage.get("height", 360))
        except (TypeError, ValueError) as exc:
            raise ValidationError("project stage has invalid dimensions") from exc
        scripts = []
        for index, item in enumerate(payload.get("scripts", [])):
            if not isinstance(item, dict):
                raise ValidationError("script %d must be an object" % index)
            blocks = item.get("blocks", [])
            if not isinstance(blocks, list):
                raise ValidationError("script %d blocks must be a list" % index)
            try:
                x = int(item.get("x", 32))
                y = int(item.get("y", 32))
            except (TypeError, ValueError) as exc:
                raise ValidationError("script %d has an invalid position" % index) from exc
            scripts.append({
                "sprite": str(item.get("sprite", "")),
                "x": x, "y": y,
                "blocks": [Block.from_dict(value) for value in blocks],
            })
        return cls(
            name=str(payload.get("name", "Untitled")),
            language=payload.get("language", "cpp"),
            width=width,
            height=height,
            background=stage.get("background", "#151a26"),
            description=str(payload.get("description", "")),
            sprites=[Sprite.from_dict(item) for item in payload.get("sprites", [])],
            variables=[Variable.from_dict(item)
                       for item in payload.get("variables", [])],
            procedures=[Procedure.from_dict(item)
                        for item in payload.get("procedures", [])],
            scripts=scripts,
        )


def save_project(project, path):
    """Write *project* as formatted UTF-8 JSON."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(project.to_dict(), handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def load_project(path):
    """Read and validate a project file."""
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError) as exc:
        raise ValidationError("could not read project: %s" % exc) from exc
    project = Project.from_dict(payload)
    validate_project(project)
    return project


_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$")


def _named_items(items, label):
    seen = set()
    for item in items:
        name = item.name
        if not name or name in seen:
            raise ValidationError("duplicate or empty %s name %r" % (label, name))
        if not _IDENTIFIER.match(name):
            raise ValidationError(
                "%s name %r must start with a letter and use letters, "
                "digits, or underscores" % (label, name)
            )
        seen.add(name)


def sprite_name(project, sprite_index):
    """Return the sprite name for an index, or an empty string when absent."""
    if 0 <= sprite_index < len(project.sprites):
        return project.sprites[sprite_index].name
    return ""


def _expression_context(project, sprite_index, params=None):
    variables = {variable.name: variable.type for variable in project.variables}
    if params:
        variables.update({param["name"]: param["type"] for param in params})
    return ExprContext(
        language=project.language,
        sprite=sprite_index,
        variables=variables,
        sprites=[sprite.name for sprite in project.sprites],
    )


def _check_expression(source, context, where):
    try:
        translate_expression(str(source), context)
    except ExpressionError as exc:
        raise ValidationError("%s: %s" % (where, exc)) from exc


def _check_block(item, project, sprite_index, params, where, allow_hat=False):
    definition = BLOCKS.get(item.type)
    if definition is None:
        raise ValidationError("%s: unknown block type %r" % (where, item.type))
    if definition.hat and not allow_hat:
        raise ValidationError("%s: event blocks must start a script" % where)
    context = _expression_context(project, sprite_index, params)
    sprite_names = [sprite.name for sprite in project.sprites]
    variable_names = [variable.name for variable in project.variables]
    procedure_names = [procedure.name for procedure in project.procedures]
    for definition_field in definition.fields:
        value = item.fields.get(definition_field.name, definition_field.default)
        name = definition_field.name
        location = "%s.%s" % (where, name)
        kind = definition_field.kind
        if kind in (_EXPRESSION, _NUMBER, _TEXT, _BOOL):
            _check_expression(value, context, location)
            if kind == _NUMBER:
                try:
                    actual = expression_type(value, project,
                                             sprite_name(project, sprite_index),
                                             params)
                except ExpressionError as exc:
                    raise ValidationError("%s: %s" % (location, exc)) from exc
                if actual != "num":
                    raise ValidationError(
                        "%s: expected a number expression, got %s"
                        % (location, actual)
                    )
        elif kind == "variable":
            if value not in variable_names:
                raise ValidationError("%s: unknown variable %r" % (location, value))
        elif kind == "key":
            key = str(value).lower()
            if key not in KEYS:
                raise ValidationError("%s: unknown key %r" % (location, value))
        elif kind == "target":
            if value != "mouse" and value not in sprite_names:
                raise ValidationError("%s: unknown target %r" % (location, value))
        elif kind == "choice":
            if value not in definition_field.options:
                raise ValidationError("%s: invalid choice %r" % (location, value))
        elif kind == "color":
            if not _COLOR.match(str(value)):
                raise ValidationError("%s: expected a #rrggbb color" % location)
        elif kind == "procedure":
            if value not in procedure_names:
                raise ValidationError("%s: unknown procedure %r" % (location, value))
            procedure = next(p for p in project.procedures if p.name == value)
            for param in procedure.params:
                argument = item.fields.get("arg_%s" % param["name"],
                                           argument_default(param))
                _check_expression(argument, context, "%s.arg_%s" % (location, param["name"]))
    for slot, children in item.children.items():
        if slot not in definition.slots:
            raise ValidationError("%s: unknown slot %r" % (where, slot))
        for index, child in enumerate(children):
            _check_block(child, project, sprite_index, params,
                         "%s/%s[%d]" % (where, slot, index))


def validate_project(project):
    """Raise :class:`ValidationError` if *project* cannot be compiled."""
    if not project.name.strip():
        raise ValidationError("project needs a name")
    if project.language not in LANGUAGES:
        raise ValidationError("unsupported language %r" % project.language)
    if not 160 <= project.width <= 1920 or not 160 <= project.height <= 1080:
        raise ValidationError("stage size must be between 160x160 and 1920x1080")
    if not _COLOR.match(project.background):
        raise ValidationError("stage background must be a #rrggbb color")
    _named_items(project.sprites, "sprite")
    _named_items(project.variables, "variable")
    _named_items(project.procedures, "procedure")
    for sprite in project.sprites:
        if sprite.shape not in ("circle", "rect", "triangle", "star"):
            raise ValidationError("sprite %r has an unknown shape" % sprite.name)
        if not _COLOR.match(sprite.color):
            raise ValidationError("sprite %r needs a #rrggbb color" % sprite.name)
        if sprite.costume_count < 1:
            raise ValidationError("sprite %r needs at least one costume" % sprite.name)
    for variable in project.variables:
        if variable.type not in ("number", "text", "bool"):
            raise ValidationError(
                "variable %r has an unknown type %r" % (variable.name, variable.type)
            )
        if " " in variable.name or variable.name in BUILTINS:
            raise ValidationError("variable %r uses a reserved name" % variable.name)
    sprite_names = [sprite.name for sprite in project.sprites]
    for procedure in project.procedures:
        seen = set()
        for param in procedure.params:
            name = param.get("name", "")
            if not _IDENTIFIER.match(name) or name in seen:
                raise ValidationError(
                    "procedure %r has an invalid parameter %r"
                    % (procedure.name, name)
                )
            if name in ("app", "sprite") or name.startswith("bf_"):
                raise ValidationError(
                    "procedure %r parameter %r uses a reserved name"
                    % (procedure.name, name)
                )
            if param.get("type") not in ("number", "text", "bool"):
                raise ValidationError(
                    "parameter %r has an unknown type" % name
                )
            seen.add(name)
        for index, item in enumerate(procedure.blocks):
            _check_block(item, project, 0, procedure.params,
                         "procedure %s[%d]" % (procedure.name, index))
    for index, script in enumerate(project.scripts):
        sprite = script.get("sprite", "")
        if sprite not in sprite_names:
            raise ValidationError("script %d refers to missing sprite %r" % (index, sprite))
        blocks = script.get("blocks", [])
        if not blocks:
            raise ValidationError("script %d is empty" % index)
        if not BLOCKS[blocks[0].type].hat:
            raise ValidationError(
                "script %d must start with an event block" % index
            )
        sprite_index = sprite_names.index(sprite)
        for block_index, item in enumerate(blocks):
            _check_block(item, project, sprite_index, None,
                         "script %d[%d]" % (index, block_index),
                         allow_hat=block_index == 0)
    return True


def expression_type(source, project, sprite="", params=None):
    """Return the inferred type name of an expression in project context."""
    sprite_index = ([s.name for s in project.sprites].index(sprite)
                    if sprite else 0)
    context = _expression_context(project, sprite_index, params)
    from expressions import parse_expression
    from expressions import _Translator  # local: internal implementation detail
    node = parse_expression(str(source))
    return _Translator(context).visit(node).type
