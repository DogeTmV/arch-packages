"""A tiny in-editor interpreter for the live stage preview.

The generated C++ and Rust programs are the real deliverable; this engine is
only a design-time preview, so it intentionally focuses on the blocks that can
be seen on the stage.  It evaluates blockforge expressions from their parsed
AST instead of calling :func:`eval`, which keeps project files untrusted input.
"""

import math
import random

from core import argument_default
from expressions import KEYS, parse_expression
from images import ImageError, decode_png


def _num(value):
    if isinstance(value, bool):
        return 1 if value else 0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _text(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and math.isfinite(value):
        nearest = round(value)
        if abs(value - nearest) <= 1e-12 * max(1.0, abs(value)):
            return str(int(nearest))
    return "" if value is None else str(value)


class _StopScript(Exception):
    """Internal signal for Scratch's 'stop this script' block."""


def _round_half_away(value):
    """Scratch-style rounding: halves go away from zero."""
    value = _num(value)
    return math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)


def _truth(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value)


class PreviewEngine:
    """Step-based interpreter used by the editor's stage widget."""

    def __init__(self, project):
        self.project = project
        self.running = False
        self.elapsed = 0.0
        self.output = []
        self.output_total = 0
        self.keys = {}
        self.pressed_events = set()
        self.mouse = (0.0, 0.0)
        self.variables = {}
        self.sprites = []
        self.images = {}
        self.backdrop = project.backdrop
        self.lines = []
        self.pen_active = False
        self.pen_color = "#2dd4bf"
        self.pen_size = 3
        self.background = project.background
        self._threads = []
        self._has_key_hats = any(
            script["blocks"] and script["blocks"][0].type == "event_key"
            for script in project.scripts
        )
        self._reset_state()

    def _reset_state(self):
        self.elapsed = 0.0
        self.output = []
        self.output_total = 0
        self.pressed_events.clear()
        self.variables.clear()
        self.lines.clear()
        self.pen_active = False
        self.pen_color = "#2dd4bf"
        self.pen_size = 3
        self.background = self.project.background
        self.backdrop = self.project.backdrop
        self._sync_images()
        for variable in self.project.variables:
            self.variables[variable.name] = {
                "number": 0.0, "text": "", "bool": False
            }[variable.type]
        self.sprites = [{
            "name": sprite.name,
            "x": float(sprite.x),
            "y": float(sprite.y),
            "size": float(sprite.size),
            "direction": float(sprite.direction),
            "costume": min(max(1, int(sprite.costume)), max(1, sprite.costume_count)),
            "costume_count": max(1, sprite.costume_count),
            "layer": int(sprite.layer),
            "shape": sprite.shape,
            "color": sprite.color,
            "image": sprite.image,
            "visible": bool(sprite.visible),
            "say_until": 0.0,
            "say_text": "",
        } for sprite in self.project.sprites]

    def _sync_images(self):
        """Decode embedded PNGs once so the stage can draw them as QImages."""
        self.images.clear()
        for name, payload in self.project.assets.items():
            try:
                width, height, rgba = decode_png(payload)
            except ImageError:
                continue
            self.images[name] = (width, height, rgba)

    def _script_thread(self, script):
        sprite = next((index for index, item in enumerate(self.project.sprites)
                       if item.name == script["sprite"]), 0)
        return {"generator": self._run_script(script, sprite), "wait": 0.0}

    def start(self):
        """Reset the stage and start every green-flag script."""
        self._reset_state()
        self._has_key_hats = any(
            script["blocks"] and script["blocks"][0].type == "event_key"
            for script in self.project.scripts
        )
        self.running = True
        self._threads = [
            self._script_thread(script)
            for script in self.project.scripts
            if script["blocks"] and script["blocks"][0].type != "event_key"
        ]
        return self

    def stop(self):
        self.running = False
        self._threads.clear()
        self.keys.clear()
        self.pressed_events.clear()

    def sync_project(self):
        """Reflect editor changes while the preview is stopped."""
        self._has_key_hats = any(
            script["blocks"] and script["blocks"][0].type == "event_key"
            for script in self.project.scripts
        )
        if self.running:
            return
        self.background = self.project.background
        self.backdrop = self.project.backdrop
        self._sync_images()
        self.variables = {
            variable.name: {"number": 0.0, "text": "", "bool": False}[variable.type]
            for variable in self.project.variables
        }
        self.sprites = [{
            "name": sprite.name,
            "x": float(sprite.x),
            "y": float(sprite.y),
            "size": float(sprite.size),
            "direction": float(sprite.direction),
            "costume": min(max(1, int(sprite.costume)),
                           max(1, sprite.costume_count)),
            "costume_count": max(1, sprite.costume_count),
            "layer": int(sprite.layer),
            "shape": sprite.shape,
            "color": sprite.color,
            "image": sprite.image,
            "visible": bool(sprite.visible),
            "say_until": 0.0,
            "say_text": "",
        } for sprite in self.project.sprites]

    def key_down(self, key):
        """Record a key press and wake any scripts watching that key."""
        key = str(key).lower()
        code = KEYS.get(key, key)
        if self.keys.get(code):
            return
        self.keys[code] = True
        self.pressed_events.add(key)
        if not self.running:
            return
        for script in self.project.scripts:
            blocks = script["blocks"]
            if blocks and blocks[0].type == "event_key" and \
                    str(blocks[0].fields.get("key", "space")).lower() == key:
                self._threads.append(self._script_thread(script))

    def key_up(self, key):
        key = str(key).lower()
        self.keys[KEYS.get(key, key)] = False
        self.pressed_events.discard(key)

    def drain_output(self, cursor=0):
        """Return output lines added since *cursor* and the next cursor.

        ``output`` is capped, so the cursor is an absolute line count rather
        than an index into the retained window.
        """
        dropped = self.output_total - len(self.output)
        start = max(0, cursor - dropped)
        return self.output[start:], self.output_total

    def step(self, dt=0.05):
        """Advance the preview by *dt* seconds."""
        if not self.running:
            return
        dt = max(0.0, float(dt))
        self.elapsed += dt
        finished = []
        for thread in list(self._threads):
            thread["wait"] -= dt
            advances = 0
            while thread["wait"] <= 0 and self.running and advances < 2000:
                advances += 1
                try:
                    duration = next(thread["generator"])
                except StopIteration:
                    finished.append(thread)
                    break
                thread["wait"] = max(0.0, _num(duration))
                if thread["wait"] > 0:
                    break
        for thread in finished:
            if thread in self._threads:
                self._threads.remove(thread)
        if not self._threads and not self._has_key_hats:
            self.running = False

    # --- expression evaluation ------------------------------------------------
    def evaluate(self, source, sprite=0, local_values=None):
        return self._eval(parse_expression(str(source)), sprite, local_values or {})

    def _eval(self, node, sprite, locals_):
        kind = node[0]
        if kind == "num":
            return float(node[1])
        if kind == "str":
            return node[1]
        if kind == "bool":
            return node[1]
        if kind == "var":
            name = node[1]
            if name in locals_:
                return locals_[name]
            if name not in self.variables:
                return 0.0
            return self.variables[name]
        if kind == "unary":
            value = self._eval(node[2], sprite, locals_)
            return -_num(value) if node[1] == "-" else not _truth(value)
        if kind == "bin":
            operator = node[1]
            if operator == "and":
                return _truth(self._eval(node[2], sprite, locals_)) and \
                    _truth(self._eval(node[3], sprite, locals_))
            if operator == "or":
                return _truth(self._eval(node[2], sprite, locals_)) or \
                    _truth(self._eval(node[3], sprite, locals_))
            left = self._eval(node[2], sprite, locals_)
            right = self._eval(node[3], sprite, locals_)
            if operator == "==":
                return _text(left) == _text(right) if isinstance(left, str) \
                    and isinstance(right, str) else _num(left) == _num(right)
            if operator == "!=":
                return not self._equal(left, right)
            if operator == "+":
                return _num(left) + _num(right)
            if operator == "-":
                return _num(left) - _num(right)
            if operator == "*":
                return _num(left) * _num(right)
            if operator == "/":
                divisor = _num(right)
                return _num(left) / divisor if divisor else math.inf
            if operator == "%":
                divisor = _num(right)
                return math.fmod(_num(left), divisor) if divisor else math.nan
            if operator == "^":
                return _num(left) ** _num(right)
            if operator == "<":
                return _num(left) < _num(right)
            if operator == ">":
                return _num(left) > _num(right)
            if operator == "<=":
                return _num(left) <= _num(right)
            if operator == ">=":
                return _num(left) >= _num(right)
        if kind == "call":
            return self._call(node[1], node[2], sprite, locals_)
        return 0.0

    @staticmethod
    def _equal(left, right):
        if isinstance(left, str) and isinstance(right, str):
            return left == right
        return _num(left) == _num(right)

    def _call(self, name, arguments, sprite, locals_):
        values = [self._eval(item, sprite, locals_) for item in arguments]
        item = self.sprites[sprite % max(1, len(self.sprites))] \
            if self.sprites else {"x": 0, "y": 0, "direction": 90,
                                   "costume": 1, "size": 100}
        simple = {
            "x position": item["x"],
            "y position": item["y"],
            "direction": item["direction"],
            "costume": item["costume"],
            "size": item["size"],
            "timer": self.elapsed,
            "mouse x": self.mouse[0],
            "mouse y": self.mouse[1],
            "touching edge": self._touching_edge(item),
        }
        if name in simple:
            return simple[name]
        if name == "key pressed":
            key = _text(values[0]).lower() if values else ""
            return _truth(self.keys.get(KEYS.get(key, key), False))
        if name == "touching sprite":
            target = _text(values[0]) if values else ""
            other = next((s for s in self.sprites if s["name"] == target), None)
            if other is None:
                return False
            dx, dy = item["x"] - other["x"], item["y"] - other["y"]
            return math.hypot(dx, dy) < (item["size"] + other["size"]) / 4.0
        if name == "random":
            low, high = _num(values[0]), _num(values[1])
            return random.uniform(min(low, high), max(low, high))
        if name == "abs":
            return abs(_num(values[0]))
        if name == "sqrt":
            return math.sqrt(max(0.0, _num(values[0])))
        if name == "sin":
            return math.sin(_num(values[0]))
        if name == "cos":
            return math.cos(_num(values[0]))
        if name == "floor":
            return float(math.floor(_num(values[0])))
        if name == "ceil":
            return float(math.ceil(_num(values[0])))
        if name == "round":
            return float(_round_half_away(values[0]))
        if name == "min":
            return min(_num(values[0]), _num(values[1]))
        if name == "max":
            return max(_num(values[0]), _num(values[1]))
        if name == "len":
            return float(len(_text(values[0])))
        if name == "to number":
            try:
                return float(str(values[0]).strip())
            except (TypeError, ValueError):
                return 0.0
        if name == "to text":
            return _text(values[0])
        if name == "join":
            return _text(values[0]) + _text(values[1])
        return 0.0

    def _move_to(self, item, x, y):
        """Move a sprite, recording a capped pen segment when the pen is down."""
        if self.pen_active:
            self.lines.append((item["x"], item["y"], x, y,
                               self.pen_color, self.pen_size))
            if len(self.lines) > 5000:
                self.lines.pop(0)
        item["x"], item["y"] = x, y

    @staticmethod
    def _radius(item):
        return max(4.0, float(item["size"]) / 100.0 * 36.0) / 2.0

    def _touching_edge(self, item):
        half = self._radius(item)
        return (abs(item["x"]) + half >= self.project.width / 2 or
                abs(item["y"]) + half >= self.project.height / 2)

    # --- block execution ------------------------------------------------------
    def _run_script(self, script, sprite):
        blocks = list(script["blocks"])
        if blocks and blocks[0].type in ("event_flag", "event_key"):
            blocks = blocks[1:]
        try:
            yield from self._execute(blocks, sprite, {})
        except _StopScript:
            return

    def _execute(self, blocks, sprite, locals_):
        for item in blocks:
            yield from self._execute_block(item, sprite, locals_)

    def _execute_block(self, item, sprite, locals_):
        fields = item.fields
        evaluate = lambda key: self.evaluate(fields.get(key, ""), sprite, locals_)
        value = lambda key: evaluate(key)
        number = lambda key: _num(evaluate(key))
        sub = lambda slot="SUB": self._execute(
            item.children.get(slot, []), sprite, locals_
        )
        kind = item.type
        item_state = self.sprites[sprite % max(1, len(self.sprites))] \
            if self.sprites else None

        if kind == "motion_move":
            steps = number("steps")
            radians = math.radians(item_state["direction"])
            nx = item_state["x"] + math.sin(radians) * steps
            ny = item_state["y"] + math.cos(radians) * steps
            self._move_to(item_state, nx, ny)
        elif kind == "motion_turn_right":
            item_state["direction"] = (item_state["direction"] +
                                       number("degrees")) % 360
        elif kind == "motion_turn_left":
            item_state["direction"] = (item_state["direction"] -
                                       number("degrees")) % 360
        elif kind == "motion_goto":
            self._move_to(item_state, number("x"), number("y"))
        elif kind == "motion_change_x":
            self._move_to(item_state, item_state["x"] + number("value"),
                          item_state["y"])
        elif kind == "motion_change_y":
            self._move_to(item_state, item_state["x"],
                          item_state["y"] + number("value"))
        elif kind == "motion_set_x":
            self._move_to(item_state, number("value"), item_state["y"])
        elif kind == "motion_set_y":
            self._move_to(item_state, item_state["x"], number("value"))
        elif kind == "motion_point_direction":
            item_state["direction"] = number("direction")
        elif kind in ("motion_point_towards", "motion_glide"):
            if kind == "motion_point_towards":
                target = fields.get("target", "mouse")
                other = next((s for s in self.sprites if s["name"] == target), None)
                tx, ty = (other["x"], other["y"]) if other else self.mouse
                item_state["direction"] = math.degrees(
                    math.atan2(tx - item_state["x"], ty - item_state["y"])
                ) % 360
            else:
                start_x, start_y = item_state["x"], item_state["y"]
                end_x, end_y = number("x"), number("y")
                seconds = max(0.0, number("secs"))
                steps = max(1, int(seconds / 0.05) + 1)
                for step in range(1, steps + 1):
                    ratio = step / steps
                    self._move_to(
                        item_state,
                        start_x + (end_x - start_x) * ratio,
                        start_y + (end_y - start_y) * ratio,
                    )
                    yield seconds / steps
        elif kind == "motion_bounce_edge":
            if self._touching_edge(item_state):
                half = self._radius(item_state)
                right = self.project.width / 2
                top = self.project.height / 2
                x_edge = abs(item_state["x"]) + half >= right
                item_state["direction"] = (
                    -item_state["direction"] if x_edge
                    else 180 - item_state["direction"]
                ) % 360
                item_state["x"] = max(-right + half, min(right - half,
                                                         item_state["x"]))
                item_state["y"] = max(-top + half, min(top - half,
                                                       item_state["y"]))
        elif kind == "looks_say":
            item_state["say_text"] = _text(value("text"))
            item_state["say_until"] = self.elapsed + max(0.0, number("secs"))
        elif kind == "looks_show":
            item_state["visible"] = True
        elif kind == "looks_hide":
            item_state["visible"] = False
        elif kind == "looks_set_size":
            item_state["size"] = number("size")
        elif kind == "looks_change_size":
            item_state["size"] += number("value")
        elif kind == "looks_set_costume":
            count = max(1, item_state["costume_count"])
            item_state["costume"] = min(count, max(1, int(number("costume"))))
        elif kind == "looks_next_costume":
            count = max(1, item_state["costume_count"])
            item_state["costume"] = item_state["costume"] % count + 1
        elif kind == "looks_set_background":
            self.background = _text(fields.get("color", "#151a26"))
            self.backdrop = ""
        elif kind == "looks_set_backdrop":
            self.backdrop = _text(fields.get("backdrop", ""))
        elif kind in ("sound_tone", "control_wait"):
            yield max(0.0, number("secs"))
        elif kind == "sound_stop":
            pass
        elif kind == "control_wait_until":
            while not _truth(self.evaluate(fields.get("condition", "false"),
                                           sprite, locals_)) and self.running:
                yield 0.02
        elif kind == "control_repeat":
            for _ in range(max(0, _round_half_away(number("times")))):
                yield from sub()
        elif kind == "control_forever":
            while self.running:
                yield from sub()
        elif kind == "control_if":
            if _truth(self.evaluate(fields.get("condition", "true"),
                                    sprite, locals_)):
                yield from sub()
        elif kind == "control_if_else":
            branch = "THEN" if _truth(self.evaluate(
                fields.get("condition", "true"), sprite, locals_)) else "ELSE"
            yield from self._execute(item.children.get(branch, []), sprite, locals_)
        elif kind == "control_repeat_until":
            while not _truth(self.evaluate(fields.get("condition", "false"),
                                           sprite, locals_)) and self.running:
                yield from sub()
                yield 0.02
        elif kind == "control_stop":
            if fields.get("choice") == "all":
                self.running = False
            raise _StopScript
        elif kind == "control_print":
            line = _text(value("value"))
            self.output.append(line)
            self.output_total += 1
            if len(self.output) > 300:
                self.output.pop(0)
        elif kind == "variable_set":
            self.variables[fields.get("name", "")] = value("value")
        elif kind == "variable_change":
            name = fields.get("name", "")
            self.variables[name] = _num(self.variables.get(name, 0)) + number("value")
        elif kind == "variable_if":
            if _truth(self.variables.get(fields.get("name", ""), False)):
                yield from sub()
        elif kind == "pen_clear":
            self.lines.clear()
        elif kind == "pen_down":
            self.pen_active = True
        elif kind == "pen_up":
            self.pen_active = False
        elif kind == "pen_set_color":
            self.pen_color = _text(fields.get("color", "#2dd4bf"))
        elif kind == "pen_set_size":
            self.pen_size = max(1, int(number("size")))
        elif kind == "procedure_call":
            procedure = next((p for p in self.project.procedures
                              if p.name == fields.get("name")), None)
            if procedure is not None:
                arguments = {}
                for param in procedure.params:
                    source = fields.get("arg_%s" % param["name"],
                                        argument_default(param))
                    arguments[param["name"]] = self.evaluate(source, sprite, locals_)
                yield from self._execute(procedure.blocks, sprite, arguments)
        yield 0.0
