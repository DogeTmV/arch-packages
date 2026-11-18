"""Bundled example projects for blockforge.

Examples are ordinary projects: loading one is the fastest way to see how the
blocks map onto generated C++ or Rust source.
"""

from copy import deepcopy

from core import Project, Sprite, Variable, block, validate_project
from images import make_backdrop_png


def _hello():
    return Project(
        name="Hello Console",
        description="A first real C++ or Rust program: print and exit.",
        sprites=[Sprite(name="Mascot")],
        scripts=[{
            "target": "spirit", "sprite": "Mascot", "x": 48, "y": 48,
            "blocks": [
                block("event_flag"),
                block("control_print", value='"Hello, world!"'),
                block("control_print",
                      value='join("Blocks compiled to ", "C++")'),
                block("control_stop", choice="all"),
            ],
        }],
    )


def _bounce():
    return Project(
        name="Bouncing Ball",
        description="A ball that bounces around the stage forever.",
        sprites=[Sprite(name="Ball", shape="circle", color="#38bdf8",
                        x=-140, y=80, direction=42)],
        scripts=[{
            "target": "spirit", "sprite": "Ball", "x": 48, "y": 48,
            "blocks": [
                block("event_flag"),
                block("control_forever", children={"SUB": [
                    block("motion_move", steps="5"),
                    block("motion_bounce_edge"),
                ]}),
            ],
        }],
    )


def _catch():
    return Project(
        name="Catch the Star",
        description="Move with arrow keys and catch a wandering star.",
        variables=[Variable("score", "number")],
        sprites=[
            Sprite(name="Hero", shape="triangle", color="#7c6cff"),
            Sprite(name="Star", shape="star", color="#fbbf24",
                   x=120, y=90),
        ],
        scripts=[
            {
                "target": "spirit", "sprite": "Hero", "x": 40, "y": 40,
                "blocks": [
                    block("event_flag"),
                    block("variable_set", name="score", value="0"),
                    block("control_forever", children={"SUB": [
                        block("control_if", condition='key pressed("left")',
                              children={"SUB": [
                                  block("motion_change_x", value="-5"),
                              ]}),
                        block("control_if", condition='key pressed("right")',
                              children={"SUB": [
                                  block("motion_change_x", value="5"),
                              ]}),
                        block("control_if", condition='key pressed("up")',
                              children={"SUB": [
                                  block("motion_change_y", value="5"),
                              ]}),
                        block("control_if", condition='key pressed("down")',
                              children={"SUB": [
                                  block("motion_change_y", value="-5"),
                              ]}),
                        block("control_if", condition='touching sprite("Star")',
                              children={"SUB": [
                                  block("variable_change", name="score", value="1"),
                                  block("control_print",
                                        value='join("Caught! score=", score)'),
                                  block("motion_goto",
                                        x="random(-180, 180)",
                                        y="random(-120, 120)"),
                                  block("control_wait", secs="0.3"),
                              ]}),
                    ]}),
                ],
            },
            {
                "target": "spirit", "sprite": "Star", "x": 480, "y": 40,
                "blocks": [
                    block("event_flag"),
                    block("control_forever", children={"SUB": [
                        block("motion_turn_right", degrees="7"),
                        block("motion_move", steps="2"),
                        block("motion_bounce_edge"),
                    ]}),
                ],
            },
        ],
    )


def _draw():
    return Project(
        name="Pen Spiral",
        description="Draws a colorful spiral with the pen blocks.",
        sprites=[Sprite(name="Pen", shape="rect", color="#2dd4bf")],
        scripts=[{
            "target": "spirit", "sprite": "Pen", "x": 40, "y": 40,
            "blocks": [
                block("event_flag"),
                block("pen_clear"),
                block("pen_set_color", color="#4ade80"),
                block("pen_down"),
                block("control_repeat", times="180", children={"SUB": [
                    block("motion_move", steps="2"),
                    block("motion_turn_right", degrees="9"),
                ]}),
                block("pen_up"),
                block("control_stop", choice="all"),
            ],
        }],
    )


def _tone():
    return Project(
        name="Tone Practice",
        description="Plays a short melody; great for testing sound blocks.",
        sprites=[Sprite(name="Speaker", shape="circle", color="#d95fd6")],
        scripts=[{
            "target": "spirit", "sprite": "Speaker", "x": 40, "y": 40,
            "blocks": [
                block("event_flag"),
                block("control_repeat", times="4", children={"SUB": [
                    block("sound_tone", freq="440 + 110 * 0", secs="0.15"),
                    block("control_wait", secs="0.05"),
                ]}),
                block("control_stop", choice="all"),
            ],
        }],
    )


def _night():
    return Project(
        name="Night Scene",
        description="A stage script changes the backdrop while a spirit glides.",
        assets={"stage_night.png": make_backdrop_png("night", 64, 48)},
        backdrop="stage_night.png",
        sprites=[Sprite(name="Mascot", shape="star", color="#c4b5fd",
                        x=-80, y=30)],
        scripts=[
            {
                "target": "stage", "x": 32, "y": 32,
                "blocks": [
                    block("event_flag"),
                    block("control_wait", secs="0.5"),
                    block("looks_set_backdrop", backdrop="stage_night.png"),
                    block("control_print", value='"Night has arrived"'),
                ],
            },
            {
                "target": "spirit", "sprite": "Mascot", "x": 32, "y": 32,
                "blocks": [
                    block("event_flag"),
                    block("control_forever", children={"SUB": [
                        block("motion_move", steps="3"),
                        block("motion_bounce_edge"),
                    ]}),
                ],
            },
        ],
    )


EXAMPLES = {
    "hello": _hello,
    "bounce": _bounce,
    "catch": _catch,
    "draw": _draw,
    "tone": _tone,
    "night": _night,
}
EXAMPLE_LABELS = {
    "hello": "Hello Console",
    "bounce": "Bouncing Ball",
    "catch": "Catch the Star",
    "draw": "Pen Spiral",
    "tone": "Tone Practice",
    "night": "Night Scene",
}


def example_project(name):
    """Return a fresh, validated project for one of :data:`EXAMPLES`."""
    if name not in EXAMPLES:
        raise KeyError(name)
    project = deepcopy(EXAMPLES[name]())
    validate_project(project)
    return project
