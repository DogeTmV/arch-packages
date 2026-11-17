"""snake_core - deterministic, headless game logic for snakecell.

The Grid class has no curses or terminal dependency, so it can be unit tested
and driven by scripts. Only the CLI imports curses, and only for interactive
play.
"""

import random


class Grid:
    """A Snake board with a seeded random food generator.

    The head is ``snake[0]``. Coordinates are zero-based with (0, 0) in the
    top-left corner; the serialized board adds a '#' border around the grid.
    """

    DIRECTIONS = {
        "up": (0, -1),
        "down": (0, 1),
        "left": (-1, 0),
        "right": (1, 0),
    }
    HEAD, BODY, FOOD, EMPTY, WALL = "O", "o", "*", ".", "#"

    def __init__(self, width=20, height=20, seed=None):
        if width < 5 or height < 5:
            raise ValueError("width and height must be at least 5")
        self.width = width
        self.height = height
        self.seed = seed
        self.rng = random.Random(seed)
        centre_x, centre_y = width // 2, height // 2
        self.snake = [(centre_x, centre_y), (centre_x - 1, centre_y),
                      (centre_x - 2, centre_y)]
        self.direction = (1, 0)
        self.score = 0
        self.steps = 0
        self.game_over = False
        self.food = None
        self._place_food()

    def _place_food(self):
        occupied = set(self.snake)
        free = [(x, y) for y in range(self.height) for x in range(self.width)
                if (x, y) not in occupied]
        self.food = self.rng.choice(free) if free else None

    def change_direction(self, direction):
        """Turn to 'up'/'down'/'left'/'right' (or a (dx, dy) pair).

        Immediate reversal is rejected; the return value says whether the
        turn was accepted.
        """
        if isinstance(direction, str):
            if direction not in self.DIRECTIONS:
                raise ValueError("unknown direction: %s" % direction)
            new = self.DIRECTIONS[direction]
        else:
            new = (int(direction[0]), int(direction[1]))
            if new not in self.DIRECTIONS.values():
                raise ValueError("unknown direction vector: %r" % (direction,))
        if len(self.snake) > 1 and new == (-self.direction[0], -self.direction[1]):
            return False
        self.direction = new
        return True

    def step(self):
        """Advance one tick. Returns True while the snake is still alive."""
        if self.game_over:
            return False
        dx, dy = self.direction
        head_x, head_y = self.snake[0]
        next_cell = (head_x + dx, head_y + dy)
        self.steps += 1
        if not (0 <= next_cell[0] < self.width and 0 <= next_cell[1] < self.height):
            self.game_over = True
            return False
        grows = next_cell == self.food
        occupied = self.snake if grows else self.snake[:-1]
        if next_cell in occupied:
            self.game_over = True
            return False
        self.snake.insert(0, next_cell)
        if grows:
            self.score += 1
            self._place_food()
        else:
            self.snake.pop()
        return True

    def serialize_board(self):
        """Render the board as ASCII text, including the surrounding wall."""
        body = set(self.snake)
        rows = []
        for y in range(-1, self.height + 1):
            row = []
            for x in range(-1, self.width + 1):
                cell = (x, y)
                if x < 0 or x >= self.width or y < 0 or y >= self.height:
                    row.append(self.WALL)
                elif cell == self.snake[0]:
                    row.append(self.HEAD)
                elif cell in body:
                    row.append(self.BODY)
                elif cell == self.food:
                    row.append(self.FOOD)
                else:
                    row.append(self.EMPTY)
            rows.append("".join(row))
        return "\n".join(rows)

    def __str__(self):
        return self.serialize_board()
