"""
HIT137 Assignment 3 - Shared Class Interface Skeleton
=======================================================

Purpose:
This file defines the agreed-upon interface between the CORE/ENGINE
team (Tile, Puzzle, ImageProcessor) and the GUI team (Tkinter app).

Everyone should commit this file to GitHub FIRST, then build against
it. Method signatures and docstrings describe what each method should
DO (inputs/outputs) so both halves of the team can work in parallel
without needing the other half's code finished yet.

Fill in the actual logic (marked with `# TODO`) in your half.
Do not change method names / signatures without telling the team,
since the other half depends on them.
"""

import cv2
import numpy as np


# ============================================================
# CORE / ENGINE TEAM
# ============================================================

class Tile:
    """
    Represents a single tile in the puzzle.

    Encapsulates the tile's image data and its current state
    (position, rotation, flip) separately from its "home" (correct)
    state, so the Puzzle/GUI can compare the two to check correctness.
    """

    def __init__(self, image: np.ndarray, correct_row: int, correct_col: int):
        """
        image        : the tile's raw pixel data (as cut from the source image,
                       BEFORE any scrambling transformation is applied)
        correct_row  : the tile's row index in the SOLVED grid
        correct_col  : the tile's column index in the SOLVED grid
        """
        self.original_image = image.copy()   # never mutated after creation
        self.image = image.copy()             # current (possibly transformed) pixels

        self.correct_row = correct_row
        self.correct_col = correct_col

        # Current position in the grid (changes on swap)
        self.current_row = correct_row
        self.current_col = correct_col

        # Current orientation state
        self.rotation = 0          # one of 0, 90, 180, 270 (degrees, clockwise)
        self.flipped_h = False
        self.flipped_v = False

    def rotate(self, degrees: int = 90) -> None:
        """Rotate this tile clockwise by `degrees` (90/180/270) and update
        self.rotation and self.image accordingly."""
        # TODO: use cv2.rotate or a rotation matrix; update self.image and self.rotation
        pass

    def flip(self, direction: str) -> None:
        """
        Flip this tile.
        direction : "horizontal" or "vertical"
        Updates self.flipped_h / self.flipped_v and self.image.
        """
        # TODO: use cv2.flip(self.image, 1 for horizontal / 0 for vertical)
        pass

    def is_correct(self) -> bool:
        """Return True if this tile is in its correct position AND
        correct orientation (rotation == 0, flipped_h == False, flipped_v == False)."""
        # TODO
        pass

    def get_display_image(self) -> np.ndarray:
        """Return the current pixel data to be drawn on the canvas."""
        return self.image


class Puzzle:
    """
    Owns the full grid of Tile objects and all puzzle-level logic:
    scrambling, swapping, win detection, hints, solving, move counting.

    The GUI should only ever talk to a Puzzle instance - it should not
    reach into individual Tile transformation logic directly except via
    these methods, so the two halves stay decoupled.
    """

    def __init__(self, image: np.ndarray, grid_size: int):
        """
        image      : the loaded (already resized/cropped/padded) source image
        grid_size  : 3, 4, or 5 -> grid_size x grid_size tiles
        """
        self.grid_size = grid_size
        self.tiles: list[Tile] = []   # flat list or could be list-of-lists; pick one and document it
        self.moves = 0
        self.hints_used = 0
        self.max_hints = 3
        self.solved = False

        self._create_tiles(image)

    def _create_tiles(self, image: np.ndarray) -> None:
        """Split `image` into grid_size x grid_size pieces and create
        a Tile object for each, storing them in self.tiles."""
        # TODO
        pass

    def scramble(self, num_transformations: int) -> None:
        """Apply `num_transformations` random swap/rotate/flip operations
        to the tiles. This is called once when the image is first loaded
        (does NOT increment self.moves - only player actions count as moves)."""
        # TODO: randomly choose swap/rotate/flip and apply, num_transformations times
        pass

    def swap_tiles(self, index_a: int, index_b: int) -> None:
        """Swap the positions of two tiles (by their current grid index).
        Increments self.moves by 1."""
        # TODO
        self.moves += 1

    def rotate_tile(self, index: int, degrees: int = 90) -> None:
        """Rotate the tile at `index` clockwise. Increments self.moves by 1."""
        # TODO: calls Tile.rotate()
        self.moves += 1

    def flip_tile(self, index: int, direction: str) -> None:
        """Flip the tile at `index`. Increments self.moves by 1."""
        # TODO: calls Tile.flip()
        self.moves += 1

    def tile_at(self, row: int, col: int) -> Tile:
        """Return the Tile currently occupying grid position (row, col)."""
        # TODO
        pass

    def count_incorrect(self) -> int:
        """Return the number of tiles NOT in their correct position/orientation."""
        # TODO
        pass

    def is_solved(self) -> bool:
        """Return True if every tile is correct. Also sets self.solved = True."""
        # TODO
        pass

    def get_hint(self) -> dict | None:
        """
        Return info for ONE currently-incorrect tile, e.g.:
            {
                "current_index": 7,           # index in the transformed/current grid
                "correct_row": 1, "correct_col": 2   # home position, for the original-image overlay
            }
        Increments self.hints_used. Returns None if hints_used >= max_hints
        or the puzzle is already solved.
        """
        # TODO
        pass

    def solve(self) -> None:
        """Instantly restore every tile to its correct position and orientation.
        Resets self.moves and self.hints_used to 0."""
        # TODO
        self.moves = 0
        self.hints_used = 0

    def get_display_grid(self) -> np.ndarray:
        """Reassemble all tiles (in their CURRENT positions/orientations)
        into a single image for the GUI to display on the right-hand canvas."""
        # TODO
        pass


# ============================================================
# CORE / ENGINE TEAM - Image loading/prep helper
# ============================================================

class ImageProcessor:
    """
    Static/utility-style helper for turning a raw file on disk into an
    image that's ready to be handed to a Puzzle (resized + evenly divisible
    by the chosen grid size). Kept separate from Puzzle so it can be
    unit-tested and reused independently.
    """

    @staticmethod
    def load_image(filepath: str) -> np.ndarray:
        """Load an image from disk (jpg/png/bmp) using OpenCV. Raises a
        clear error if the file can't be read."""
        # TODO
        pass

    @staticmethod
    def prepare_for_grid(image: np.ndarray, grid_size: int, target_size: tuple[int, int]) -> np.ndarray:
        """
        Resize `image` to fit within `target_size` (max width, max height),
        then crop or pad so both dimensions divide evenly by `grid_size`.
        Returns the prepared image.
        """
        # TODO
        pass


# ============================================================
# GUI TEAM
# ============================================================

class PuzzleApp:
    """
    Top-level Tkinter application. Should hold ONE Puzzle instance at a
    time and talk to it only through the public methods above.

    Suggested responsibilities (fill in as you build):
    - __init__: build the window, menus/buttons, two canvases (original / transformed)
    - on_load_image_click(): open file dialog -> ImageProcessor.load_image()
      -> ImageProcessor.prepare_for_grid() -> create Puzzle(...) -> puzzle.scramble(...)
      -> render both canvases
    - on_grid_size_change(value): store chosen grid size (3/4/5) before next load
    - render(): draw puzzle.get_display_grid() on the right canvas, original
      image on the left canvas, faint grid lines over the transformed image,
      green ticks on correct tiles
    - on_canvas_click(event): map (event.x, event.y) -> tile index, handle
      left-click select/swap, right-click rotate, shift+left-click flip,
      then call render() and update the move/incorrect counters
    - on_hint_click(): call puzzle.get_hint(), draw blue circles on both
      canvases, disable the button if hints_used == max_hints
    - on_solve_click(): call puzzle.solve(), render(), reset counters display
    - check_win(): after every action, call puzzle.is_solved(); if True,
      show a "Solved!" message and stop accepting canvas clicks
    """

    def __init__(self):
        self.puzzle: Puzzle | None = None
        self.selected_tile_index: int | None = None
        # TODO: build Tkinter widgets
        pass


if __name__ == "__main__":
    app = PuzzleApp()
    # TODO: app.mainloop() once built on top of tk.Tk
