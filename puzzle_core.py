"""
HIT137 Assignment 3 - Core Puzzle Logic
"""
import random
import cv2
import numpy as np


# Tiles in the puzzle

class Tile:
    """
    For a single tile in the puzzle.

    Encapsulation: the tile's pixel data and transformation state are affected
    only through rotate(), flip(), is_correct(), get_display_image().
    """

    def __init__(self, image: np.ndarray, correct_row: int, correct_col: int):
        self.original_image = image.copy()    # pristine, never mutated after creation
        self.image = image.copy()              # current (possibly transformed) pixels

        self.correct_row = correct_row
        self.correct_col = correct_col

        # Current position in the grid (updated on swap)
        self.current_row = correct_row
        self.current_col = correct_col

        # Current orientation state
        self.rotation = 0          # 0, 90, 180, 270 (degrees, clockwise, cumulative)
        self.flipped_h = False
        self.flipped_v = False

    def rotate(self, degrees: int = 90) -> None:
        """Rotate this tile clockwise by 90/180/270 degrees."""
        if degrees not in (90, 180, 270):
            raise ValueError("degrees must be 90, 180 or 270")

        steps = degrees // 90
        for _ in range(steps):
            self.image = cv2.rotate(self.image, cv2.ROTATE_90_CLOCKWISE)

        self.rotation = (self.rotation + degrees) % 360

    def flip(self, direction: str) -> None:
        """
        Flip this tile.
        direction : "horizontal" or "vertical"
        """
        if direction == "horizontal":
            self.image = cv2.flip(self.image, 1)
            self.flipped_h = not self.flipped_h
        elif direction == "vertical":
            self.image = cv2.flip(self.image, 0)
            self.flipped_v = not self.flipped_v
        else:
            raise ValueError('direction must be "horizontal" or "vertical"')

    def is_correct(self) -> bool:
        """True if this tile is in its correct grid position AND has
        no net rotation/flip applied."""
        position_ok = (
            self.current_row == self.correct_row
            and self.current_col == self.correct_col
        )
        orientation_ok = (
            self.rotation == 0
            and not self.flipped_h
            and not self.flipped_v
        )
        return position_ok and orientation_ok

    def get_display_image(self) -> np.ndarray:
        return self.image


# Puzzle

class Puzzle:
    """
    Grid of Tile objects and all puzzle-level logic.

    self.tiles is a flat, row-major list: tiles[row * grid_size + col]
    is whatever tile currently sits at that grid position. Swapping two
    tiles means swapping their entries in this list (and updating each
    tile's current_row/current_col to match its new slot).
    """

    def __init__(self, image: np.ndarray, grid_size: int):
        if grid_size not in (3, 4, 5):
            raise ValueError("grid_size must be 3, 4 or 5")
        if image.shape[0] % grid_size != 0 or image.shape[1] % grid_size != 0:
            raise ValueError(
                "image dimensions must divide evenly by grid_size "
                "(this should be guaranteed by ImageProcessor.prepare_for_grid)"
            )

        self.grid_size = grid_size
        self.tiles: list[Tile] = []
        self.moves = 0
        self.hints_used = 0
        self.max_hints = 3
        self.solved = False
        self._last_hint = None   # remembers the current hint so it can be cleared after the next move

        self._create_tiles(image)

    # setup -------

    def _create_tiles(self, image: np.ndarray) -> None:
        h, w = image.shape[:2]
        tile_h = h // self.grid_size
        tile_w = w // self.grid_size

        self.tiles = []
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                y0, y1 = row * tile_h, (row + 1) * tile_h
                x0, x1 = col * tile_w, (col + 1) * tile_w
                piece = image[y0:y1, x0:x1]
                self.tiles.append(Tile(piece, correct_row=row, correct_col=col))

    def scramble(self, num_transformations: int) -> None:
        operations = ["swap", "rotate", "flip"]
        total = len(self.tiles)

        applied = 0
        while applied < num_transformations:
            op = random.choice(operations)

            if op == "swap":
                i, j = random.sample(range(total), 2)
                self._swap_positions(i, j)

            elif op == "rotate":
                i = random.randrange(total)
                degrees = random.choice([90, 180, 270])
                self.tiles[i].rotate(degrees)

            elif op == "flip":
                i = random.randrange(total)
                direction = random.choice(["horizontal", "vertical"])
                self.tiles[i].flip(direction)

            applied += 1

        # Safety net: if scrambling happened to land back on a fully solved state (rare, but possible with few transformations),
        # force one more swap so the player actually has a puzzle.
        if self.is_solved():
            i, j = random.sample(range(total), 2)
            self._swap_positions(i, j)

    # internal helper ----

    def _swap_positions(self, index_a: int, index_b: int) -> None:
        """Swap two tiles' list slots and update their current_row/col."""
        self.tiles[index_a], self.tiles[index_b] = self.tiles[index_b], self.tiles[index_a]

        for index in (index_a, index_b):
            self.tiles[index].current_row = index // self.grid_size
            self.tiles[index].current_col = index % self.grid_size

    # player actions ------

    def swap_tiles(self, index_a: int, index_b: int) -> None:
        """Player-initiated swap. Counts as one move."""
        self._swap_positions(index_a, index_b)
        self.moves += 1
        self._last_hint = None

    def rotate_tile(self, index: int, degrees: int = 90) -> None:
        """Player-initiated rotate. Counts as one move."""
        self.tiles[index].rotate(degrees)
        self.moves += 1
        self._last_hint = None

    def flip_tile(self, index: int, direction: str) -> None:
        """Player-initiated flip. Counts as one move."""
        self.tiles[index].flip(direction)
        self.moves += 1
        self._last_hint = None

    # queries ----------

    def tile_at(self, row: int, col: int) -> Tile:
        return self.tiles[row * self.grid_size + col]

    def count_incorrect(self) -> int:
        return sum(1 for t in self.tiles if not t.is_correct())

    def is_solved(self) -> bool:
        self.solved = all(t.is_correct() for t in self.tiles)
        return self.solved

    # hints ----

    def get_hint(self) -> dict | None:
        """
        Reveal one incorrect tile. Returns None if out of hints or the
        puzzle is already solved. The GUI is responsible for clearing
        the blue-circle markers after the next move (it can just check
        that self._last_hint has been reset to None, or track its own
        "hint active" flag - either is fine).
        """
        if self.solved or self.hints_used >= self.max_hints:
            return None

        incorrect_indices = [i for i, t in enumerate(self.tiles) if not t.is_correct()]
        if not incorrect_indices:
            return None

        current_index = random.choice(incorrect_indices)
        tile = self.tiles[current_index]

        self.hints_used += 1
        self._last_hint = {
            "current_index": current_index,
            "correct_row": tile.correct_row,
            "correct_col": tile.correct_col,
        }
        return self._last_hint

    # solve ------------

    def solve(self) -> None:
        """Instantly restore every tile to its correct position and
        orientation, and reset moves/hints."""
        self.tiles.sort(key=lambda t: (t.correct_row, t.correct_col))

        # undo any rotation/flip on each one.
        for t in self.tiles:
            t.image = t.original_image.copy()
            t.rotation = 0
            t.flipped_h = False
            t.flipped_v = False
            t.current_row = t.correct_row
            t.current_col = t.correct_col

        self.moves = 0
        self.hints_used = 0
        self._last_hint = None
        self.solved = True

    # display ---------

    def get_display_grid(self) -> np.ndarray:
        """Reassemble all tiles (in their current positions/orientations)
        into a single image for the GUI to draw."""
        rows = []
        for row in range(self.grid_size):
            row_tiles = [
                self.tile_at(row, col).get_display_image()
                for col in range(self.grid_size)
            ]
            rows.append(np.hstack(row_tiles))
        return np.vstack(rows)


# Self-test (run this file directly: python puzzle_core.py)

if __name__ == "__main__":
    # Build a synthetic 300x300 test image (no real file / ImageProcessor needed) - a different flat colour per cell so scrambling is obvious.
    GRID = 3
    CELL = 100
    test_image = np.zeros((CELL * GRID, CELL * GRID, 3), dtype=np.uint8)
    colours = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255),
        (255, 255, 0), (255, 0, 255), (0, 255, 255),
        (128, 128, 128), (255, 128, 0), (128, 0, 255),
    ]
    for i in range(GRID * GRID):
        r, c = divmod(i, GRID)
        test_image[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL] = colours[i]

    puzzle = Puzzle(test_image, GRID)
    print("Freshly created (unscrambled) - solved:", puzzle.is_solved())
    assert puzzle.is_solved()

    puzzle.scramble(6)
    print("After scramble(6) - solved:", puzzle.is_solved(),
          "| incorrect tiles:", puzzle.count_incorrect())
    assert not puzzle.is_solved()
    assert puzzle.moves == 0, "scrambling should not count as player moves"

    hint = puzzle.get_hint()
    print("Hint:", hint, "| hints_used:", puzzle.hints_used)
    assert hint is not None

    puzzle.swap_tiles(0, 1)
    puzzle.rotate_tile(2, 90)
    puzzle.flip_tile(3, "horizontal")
    print("After 3 player moves - moves:", puzzle.moves)
    assert puzzle.moves == 3

    display = puzzle.get_display_grid()
    assert display.shape == test_image.shape
    print("get_display_grid() shape OK:", display.shape)

    puzzle.solve()
    print("After solve() - solved:", puzzle.is_solved(),
          "| moves:", puzzle.moves, "| hints_used:", puzzle.hints_used)
    assert puzzle.is_solved()
    assert puzzle.moves == 0 and puzzle.hints_used == 0
    assert np.array_equal(puzzle.get_display_grid(), test_image)

    print("\nAll self-tests passed.")
