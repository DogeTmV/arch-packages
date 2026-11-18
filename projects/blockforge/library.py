"""Built-in spirit and stage library for the blockforge editor.

Presets are plain data so the GUI can show a browsable library while the
compiler keeps working with ordinary projects.  Spirits are geometric by
default; custom spirits use pictures imported by the user.  Stages have a color
and a generated PNG backdrop that is embedded in saves and exported source.
"""

from dataclasses import dataclass
from typing import List

from core import Sprite, block
from images import make_backdrop_png


@dataclass(frozen=True)
class SpiritPreset:
    key: str
    label: str
    description: str
    shape: str
    color: str
    x: float = 0
    y: float = 0
    direction: float = 90
    size: float = 100
    start_script: bool = False


@dataclass(frozen=True)
class StagePreset:
    key: str
    label: str
    description: str
    background: str
    backdrop: str


SPIRITS = [
    SpiritPreset("mascot", "Mascot", "A friendly all-round starter.",
                 "circle", "#7c6cff", start_script=True),
    SpiritPreset("ball", "Ball", "Bounces around the stage.",
                 "circle", "#38bdf8", -120, 80, 42, start_script=True),
    SpiritPreset("star", "Star", "A bright collectible.",
                 "star", "#fbbf24", 120, 90, size=80),
    SpiritPreset("hero", "Hero", "Move with the arrow keys.",
                 "triangle", "#34d399", start_script=True),
    SpiritPreset("pen", "Pen", "Draws with the pen blocks.",
                 "rect", "#2dd4bf", size=70),
    SpiritPreset("speaker", "Speaker", "Plays tones.",
                 "circle", "#d95fd6"),
]

STAGES = [
    StagePreset("night", "Night", "A quiet starry sky.", "#151a26", "night"),
    StagePreset("meadow", "Meadow", "A green outdoor stage.", "#1a4a36", "meadow"),
    StagePreset("ocean", "Ocean", "A blue underwater stage.", "#082442", "ocean"),
    StagePreset("sunset", "Sunset", "A warm evening stage.", "#381440", "sunset"),
    StagePreset("grid", "Grid", "A simple stage with a faint grid.", "#0c1422",
                "grid"),
]

SPIRIT_BY_KEY = {preset.key: preset for preset in SPIRITS}
STAGE_BY_KEY = {preset.key: preset for preset in STAGES}


def unique_name(names, base):
    """Return *base* or a numbered variant that is not already used."""
    names = set(names)
    if base not in names:
        return base
    index = 2
    while "%s%d" % (base, index) in names:
        index += 1
    return "%s%d" % (base, index)


def spirit_from_preset(project, key):
    """Create a spirit from the library, renamed if its name is taken."""
    preset = SPIRIT_BY_KEY.get(key)
    if preset is None:
        raise KeyError(key)
    name = unique_name([item.name for item in project.sprites], preset.label)
    return Sprite(name=name, x=preset.x, y=preset.y, size=preset.size,
                  direction=preset.direction, shape=preset.shape,
                  color=preset.color)


def spirit_start_script(key, name):
    """Return the starter script for a library spirit, if it has one."""
    if key in ("mascot", "hero"):
        return {
            "target": "spirit", "sprite": name, "x": 40, "y": 40,
            "blocks": [block("event_flag"),
                       block("looks_say", text='"%s here!"' % name, secs="2")],
        }
    if key == "ball":
        return {
            "target": "spirit", "sprite": name, "x": 40, "y": 40,
            "blocks": [block("event_flag"), block("control_forever", children={
                "SUB": [block("motion_move", steps="5"),
                        block("motion_bounce_edge")],
            })],
        }
    return None


def stage_asset_name(key):
    return "stage_%s.png" % key


def apply_stage_preset(project, key, width=480, height=360):
    """Apply a stage preset, adding its backdrop PNG to the project assets."""
    preset = STAGE_BY_KEY.get(key)
    if preset is None:
        raise KeyError(key)
    project.background = preset.background
    project.backdrop = stage_asset_name(key)
    project.assets[project.backdrop] = make_backdrop_png(
        preset.backdrop, width, height)
    return preset
