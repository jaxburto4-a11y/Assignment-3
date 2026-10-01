import pygame
import random
import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk


# puzzle_Core
# Import pygame.locals for easier access to key coordinates
from pygame.locals import (
    K_UP,
    K_DOWN,
    K_LEFT,
    K_RIGHT,
    K_ESCAPE,
    KEYDOWN,
    QUIT,
)
# Define constants for the screen width and height
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

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

    def get_hint(self) -> dict:
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

# Image Processing
class ImageProcessor:
    @staticmethod
    def load_image(filepath: str) -> np.ndarray:
        if not filepath:
            raise ValueError("No image file was selected.")

        filepath = os.fspath(filepath)

        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Image file not found: {filepath}")

        if os.path.splitext(filepath)[1].lower() not in {
            ".jpg", ".jpeg", ".png", ".bmp"
        }:
            raise ValueError("Please select a JPG, PNG or BMP image.")

        try:
            file_data = np.fromfile(filepath, dtype=np.uint8)
        except OSError as error:
            raise OSError(f"Unable to read image: {filepath}") from error

        if file_data.size == 0:
            raise ValueError("The selected file is empty.")

        try:
            image = cv2.imdecode(file_data, cv2.IMREAD_COLOR)
        except cv2.error as error:
            raise ValueError("Unable to decode the selected image.") from error

        if image is None:
            raise ValueError("The selected file is not a readable image.")

        return image

    @staticmethod
    def prepare_for_grid(
        image: np.ndarray,
        grid_size: int,
        target_size: tuple[int, int],
    ) -> np.ndarray:
        if not isinstance(image, np.ndarray) or image.size == 0:
            raise ValueError("A non-empty image is required.")

        if image.dtype != np.uint8:
            raise ValueError("Image pixels must use uint8.")

        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.ndim == 3 and image.shape[2] == 1:
            image = cv2.cvtColor(image[:, :, 0], cv2.COLOR_GRAY2BGR)
        elif image.ndim == 3 and image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        elif image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("Unsupported image format.")

        if (
            isinstance(grid_size, (bool, np.bool_))
            or not isinstance(grid_size, (int, np.integer))
            or grid_size not in (3, 4, 5)
        ):
            raise ValueError("Grid size must be 3, 4 or 5.")

        if not isinstance(target_size, (tuple, list)) or len(target_size) != 2:
            raise ValueError("Target size must contain a width and height.")

        if any(
            isinstance(value, (bool, np.bool_))
            or not isinstance(value, (int, np.integer))
            or value <= 0
            for value in target_size
        ):
            raise ValueError("Target dimensions must be positive integers.")

        max_width, max_height = map(int, target_size)
        grid_size = int(grid_size)
        canvas_size = min(max_width, max_height)
        canvas_size -= canvas_size % grid_size

        if canvas_size == 0:
            raise ValueError("Target size is too small for the selected grid.")

        height, width = image.shape[:2]
        scale = canvas_size / max(width, height)

        new_width = min(canvas_size, max(1, round(width * scale)))
        new_height = min(canvas_size, max(1, round(height * scale)))

        interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR
        resized = cv2.resize(
            image,
            (new_width, new_height),
            interpolation=interpolation,
        )

        horizontal_padding = canvas_size - new_width
        vertical_padding = canvas_size - new_height

        left = horizontal_padding // 2
        top = vertical_padding // 2

        return cv2.copyMakeBorder(
            resized,
            top,
            vertical_padding - top,
            left,
            horizontal_padding - left,
            cv2.BORDER_CONSTANT,
            value=(0, 0, 0),
        )

# GUI and Pygame
# Create the main window
class PuzzleApp(pygame.sprite.Sprite):
  def __init__(self) -> None:
     super(PuzzleApp, self).__init__()
     self.puzzle: Puzzle | None = None
     self.file_path = None
     self.image_path = None
     self.image = None
     self.selected_tile_index: int | None = None
     self.hint_info: dict | None = None  # active hint, cleared after the next move
     self.grid_size = 3
     self.canvas_size = 420    # fixed display size for both canvases
     self.cell_size = self.canvas_size // self.grid_size
     self._win_message_shown = False
     self.screen_width = SCREEN_WIDTH # Use global constants for initial setup
     self.screen_height = SCREEN_HEIGHT # Use global constants for initial setup
     self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
     self.FPS = pygame.time.Clock()
     self.running = True
     self.root = None
     self.grid_size_var = None
     self.hint_button = None
     self.solve_button = None
     self.original_canvas = None
     self.transformed_canvas = None
     self.moves_label = None
     self.incorrect_label = None
     self.image_path = None
     self.show_start_screen = True
     self.selected_img = None
     self.is_game_over = False

     # Initialize Pygame fonts as instance variables
     self.font_title = pygame.font.Font(None, 72)
     self.font_content = pygame.font.Font(None, 36)

     self.title_text = None
     self.title_rect = None
     self.choose_text = None
     self.choose_rect = None
     self.Level1_text = None
     self.Level1_rect = None
     self.Level2_text = None
     self.Level2_rect = None
     self.Level3_text = None
     self.Level3_rect = None
     self.play_again_text = None # Renamed to avoid clash with other 'play_again'
     self.play_again_rect = None
     self.continue_text_render = None # Renamed to avoid clash
     self.continue_rect_render = None # Renamed to avoid clash
     self.show_start_screen = True
     # self.selected_tile_index and self.hint_info are already initialized above

     # Set two different photos
     self.original_photo = None
     self.transformed_photo = None

     # keep references so Tkinter's garbage collector doesn't drop the images
     self.original_photo = None
     self.transformed_photo = None

     self._build_ui_tkinter() # Call Tkinter UI setup
     self._setup_pygame_display_elements() # Call Pygame display setup
     # self.render() # Do not call render here yet, as it expects puzzle/image to be loaded

  def _build_ui_tkinter(self) -> None:
    self.root = tk.Tk()
    self.root.title("Puzzle App")
    self.root.resizable(False, False)

    # menu bar
    menu_bar = tk.Menu(self.root)
    self.root.config(menu=menu_bar)
    file_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="Load Image...", command=self.on_load_image_click)
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=self.root.quit)

    # top controls
    controls = tk.Frame(self.root)
    controls.pack(pady=8)

    tk.Button(controls, text="Load Image", command=self.on_load_image_click).pack(
        side=tk.LEFT, padx=5
    )

    tk.Label(controls, text="Grid size:").pack(side=tk.LEFT, padx=(15, 2))
    self.grid_size_var = tk.StringVar(value=str(self.grid_size))
    tk.OptionMenu(
        controls, self.grid_size_var, "3", "4", "5", command=self.on_grid_size_change
    ).pack(side=tk.LEFT)

    self.hint_button = tk.Button(
        controls, text="Hint", command=self.on_hint_click, state=tk.DISABLED
    )
    self.hint_button.pack(side=tk.LEFT, padx=5)

    self.solve_button = tk.Button(
        controls, text="Solve", command=self.on_solve_click, state=tk.DISABLED
    )
    self.solve_button.pack(side=tk.LEFT, padx=5)

    # canvases, side by side
    canvases_frame = tk.Frame(self.root)
    canvases_frame.pack()

    left = tk.Frame(canvases_frame)
    left.pack(side=tk.LEFT, padx=10, pady=5)
    tk.Label(left, text="Original").pack()
    self.original_canvas = tk.Canvas(
        left, width=self.canvas_size, height=self.canvas_size, bg="#dddddd"
    )
    self.original_canvas.pack()

    right = tk.Frame(canvases_frame)
    right.pack(side=tk.LEFT, padx=10, pady=5)
    tk.Label(right, text="Transformed (click to solve)").pack()
    self.transformed_canvas = tk.Canvas(
        right, width=self.canvas_size, height=self.canvas_size, bg="#dddddd"
    )
    self.transformed_canvas.pack()

    # only the transformed canvas responds to clicks
    self.transformed_canvas.bind("<Button-1>", self.on_canvas_click)        # left click
    self.transformed_canvas.bind("<Button-3>", self.on_canvas_click)        # right click
    self.transformed_canvas.bind("<Shift-Button-1>", self.on_canvas_click)  # shift+left click

    # status bar
    status = tk.Frame(self.root)
    status.pack(pady=8)
    self.moves_label = tk.Label(status, text="Moves: 0")
    self.moves_label.pack(side=tk.LEFT, padx=10)
    self.incorrect_label = tk.Label(status, text="Incorrect: 0")
    self.incorrect_label.pack(side=tk.LEFT, padx=10)

    # Loading an image in pygame - This line needs to be handled when an image is actually loaded
    # self.surf = pygame.image.load().convert() # Removed, as it requires a path
    # self.rect = self.surf.get_rect()
    # self.rect.topleft = (0, 0)
    # self.screen.blit(self.surf, (0, 0))
    # pygame.display.flip()

  def _setup_pygame_display_elements(self) -> None:
    # Start Screen
    self.title_text = self.font_title.render("Puzzle Game", True, (255, 255, 255))
    self.title_rect = self.title_text.get_rect()
    self.title_rect.center = (self.screen_width // 2, self.screen_height // 4)

    # Difficulty levels
    self.choose_text = self.font_content.render("Choose Difficulty:", True, (255, 255, 255))
    self.choose_rect = self.choose_text.get_rect()
    self.choose_rect.center = (self.screen_width // 2, self.screen_height // 2)

    self.Level1_text = self.font_content.render("Level 1: Easy", True, (255, 255, 255))
    self.Level1_rect = self.Level1_text.get_rect()
    self.Level1_rect.center = (self.screen_width // 2, self.screen_height // 2 + 50)

    self.Level2_text = self.font_content.render("Level 2: Medium", True, (255, 255, 255))
    self.Level2_rect = self.Level2_text.get_rect()
    self.Level2_rect.center = (self.screen_width // 2, self.screen_height // 2 + 100)

    self.Level3_text = self.font_content.render("Level 3: Hard", True, (255, 255, 255))
    self.Level3_rect = self.Level3_text.get_rect()
    self.Level3_rect.center = (self.screen_width // 2, self.screen_height // 2 + 150)

    # End screen
    self.play_again_text = self.font_title.render("Play Again?", True, (255, 255, 255))
    self.play_again_rect = self.play_again_text.get_rect()
    self.play_again_rect.center = (self.screen_width // 2, self.screen_height // 2)

    self.continue_text_render = self.font_content.render("Press 'C' to continue", True, (255, 255, 255))
    self.continue_rect_render = self.continue_text_render.get_rect()
    self.continue_rect_render.center = (self.screen_width // 2, self.screen_height // 2 + 50)

  def on_grid_size_change(self, value: str) -> None:
    """Store the chosen grid size; only takes effect on the NEXT load,
    per the spec ('the player must choose grid size before loading')."""
    self.grid_size = int(value)

  def on_load_image_click(self) -> None:
    # Placeholder for ImageProcessor and Puzzle definitions which are not in this cell
    # This part assumes ImageProcessor, Puzzle, and TRANSFORMATIONS_BY_GRID_SIZE are defined elsewhere.
    # For the purpose of fixing the NameError, I'll keep this as is but note potential future errors.
    try:
        # Dummy definitions for types not present in this cell
        class ImageProcessor:
            @staticmethod
            def load_image(file_path):
                # Simulate image loading
                return np.zeros((100, 100, 3), dtype=np.uint8)
            @staticmethod
            def prepare_for_grid(raw_image, grid_size, size):
                # Simulate image preparation
                return np.zeros(size + (3,), dtype=np.uint8)
        class Puzzle:
            def __init__(self, img, grid_size): self.tiles = []; self.moves = 0; self.incorrect = 0; self.hints_used = 0; self.max_hints = 3
            def scramble(self, transformations): pass
            def is_solved(self): return False
            def get_display_grid(self): return np.zeros((100, 100, 3), dtype=np.uint8)
            def rotate_tile(self, index, angle): pass
            def flip_tile(self, index, direction): pass
            def swap_tiles(self, index1, index2): pass
            def get_hint(self): return None
            def solve(self): pass

        TRANSFORMATIONS_BY_GRID_SIZE = {3:[], 4:[], 5:[]}

        self.file_path = filedialog.askopenfilename(
              filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if not self.file_path:
           return


        raw_image = ImageProcessor.load_image(self.file_path) # Use self.file_path
        prepared = ImageProcessor.prepare_for_grid(
            raw_image, self.grid_size, (self.canvas_size, self.canvas_size)
        )
    except Exception as error:
        messagebox.showerror("Could not load image", str(error))
        return

    self.image = prepared
    self.cell_size = self.canvas_size // self.grid_size
    self.puzzle = Puzzle(prepared, self.grid_size)
    self.puzzle.scramble(TRANSFORMATIONS_BY_GRID_SIZE[self.grid_size])

    self.selected_tile_index = None
    self.hint_info = None
    self._win_message_shown = False
    self.hint_button.config(state=tk.NORMAL)
    self.solve_button.config(state=tk.NORMAL)

    self.render()

  def _to_photo(self, bgr_image) -> ImageTk.PhotoImage:
    """Convert an OpenCV BGR numpy image to a Tkinter-displayable PhotoImage."""
    rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
    return ImageTk.PhotoImage(Image.fromarray(rgb_image))

  def render(self) -> None:
    if self.puzzle is None or self.image is None:
          return
    self.transformed_photo = self._to_photo(self.puzzle.get_display_grid())
    self.original_photo = self._to_photo(self.image)

    self.original_canvas.delete("all")
    self.transformed_canvas.delete("all")

    self.original_canvas.create_image(0, 0, anchor=tk.NW, image=self.original_photo)
    self.transformed_canvas.create_image(0, 0, anchor=tk.NW, image=self.transformed_photo)

    self.draw_grid_lines()
    self.draw_ticks()
    if self.selected_tile_index is not None:
          self.draw_selection(self.selected_tile_index)
    if self.hint_info is not None:
          self.draw_hint(self.hint_info)


    self.update_counters()
    self.check_win()

    # Pygame drawing should occur in a dedicated game loop update, not within this Tkinter render method
    # Move the following lines to a Pygame game loop function
    # pressed_keys = pygame.key.get_pressed()
    # self.update(pressed_keys)  # Pass pressed_keys to update
    # self.FPS.tick(60)
    # self.screen.fill((0, 0, 0))
    # self.screen.blit(self.title_text, self.title_rect)
    # pygame.display.flip()

  def update(self, pressed_keys):
    # Keep tile on the screen
    if self.rect.left < 0:
      self.rect.left = 0
    elif self.rect.right > SCREEN_WIDTH:
      self.rect.right = SCREEN_WIDTH
    if self.rect.top < 0:
      self.rect.top = 0
    elif self.rect.bottom > SCREEN_HEIGHT:
      self.rect.bottom = SCREEN_HEIGHT
    if pressed_keys[K_UP]:
        self.rect.move_ip(0, -5)
    if pressed_keys[K_DOWN]:
        self.rect.move_ip(0, 5)
    if pressed_keys[K_LEFT]:
      self.rect.move_ip(-5, 0)
    if pressed_keys[K_RIGHT]:
      self.rect.move_ip(5, 0)

  def draw_grid_lines(self) -> None:
    """Faint grid lines over the transformed image so tile boundaries are visible."""
    cell = self.cell_size
    for i in range(1, self.grid_size):
      x = i * cell
      y = i * cell
      self.transformed_canvas.create_line(x, 0, x, self.canvas_size, fill="gray70")
      self.transformed_canvas.create_line(0, y, self.canvas_size, y, fill="gray70")

  def draw_ticks(self) -> None:
    """Small green tick in the corner of every tile that is currently
    correct (right position AND right orientation)."""
    cell = self.cell_size
    for tile in self.puzzle.tiles:
        if not tile.is_correct():
            continue
        x = tile.current_col * cell + cell - 12
        y = tile.current_row * cell + 12
        self.transformed_canvas.create_text(
            x, y, text="\u2713", fill="green", font=("Arial", 14, "bold")
        )

  def draw_selection(self, index: int) -> None:
    """Coloured border around the currently-selected tile."""
    row, col = divmod(index, self.grid_size)
    cell = self.cell_size
    x0, y0 = col * cell, row * cell
    self.transformed_canvas.create_rectangle(
        x0 + 2, y0 + 2, x0 + cell - 2, y0 + cell - 2, outline="red", width=3
    )

  def draw_hint(self, hint: dict) -> None:
    """Blue circle on the wrong tile (transformed canvas) and on its
    correct home position (original canvas)."""
    cell = self.cell_size

    cur_row, cur_col = divmod(hint["current_index"], self.grid_size)
    cx0, cy0 = cur_col * cell, cur_row * cell
    pad = cell * 0.3
    self.transformed_canvas.create_oval(
        cx0 + pad, cy0 + pad, cx0 + cell - pad, cy0 + cell - pad, fill="blue", outline=""
    )

    ox0 = hint["correct_col"] * cell
    oy0 = hint["correct_row"] * cell
    self.original_canvas.create_oval(
        ox0 + pad, oy0 + pad, ox0 + cell - pad, oy0 + cell - pad, fill="blue", outline=""
    )

  # Interaction
  def get_tile_index(self, x: int, y: int) -> int | None:
    cell = self.cell_size
    col, row = x // cell, y // cell
    if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
          return int(row * self.grid_size + col)
    return None

  def on_canvas_click(self, event) -> None:
    if self.puzzle is None or self.puzzle.is_solved():
          return  # no further input once solved

    tile_index = self.get_tile_index(event.x, event.y)
    if tile_index is None:
          return

    shift_held = bool(event.state & 0x0001)

    if event.num == 3:                      # right click -> rotate
          self.puzzle.rotate_tile(tile_index, 90)
          self.selected_tile_index = None

    elif event.num == 1 and shift_held:      # shift + left click -> flip
          self.puzzle.flip_tile(tile_index, "horizontal")
          self.selected_tile_index = None

    elif event.num == 1:                     # plain left click -> select/swap
          if self.selected_tile_index is None:
              self.selected_tile_index = tile_index
          elif self.selected_tile_index == tile_index:
              self.selected_tile_index = None  # clicking same tile again deselects
          else:
              self.puzzle.swap_tiles(self.selected_tile_index, tile_index)
              self.selected_tile_index = None

    self.hint_info = None  # any move clears the hint marker, per spec
    self.render()


  def update_counters(self) -> None:
     if self.puzzle is None:
      self.moves_label.config(text="Moves: 0")
      self.incorrect_label.config(text="Incorrect: 0")
      return
     self.moves_label.config(text=f"Moves: {self.puzzle.moves}")
     self.incorrect_label.config(text=f"Incorrect: {self.puzzle.incorrect}")


  # Hint / Solve / Win

  def on_hint_click(self) -> None:
     if self.puzzle is None:
        return
     hint = self.puzzle.get_hint()
     if hint is None:
      if self.puzzle.hints_used >= self.puzzle.max_hints:
        messagebox.showinfo("No hints left", "You've used all 3 hints for this image.")
        return

     self.hint_info = hint
     if self.puzzle.hints_used >= self.puzzle.max_hints:
        self.hint_button.config(state=tk.DISABLED)
     self.render()

  def on_solve_click(self) -> None:
     if self.puzzle is None:
      return
     self.puzzle.solve()
     self.selected_tile_index = None
     self.hint_info = None
     self.render()

  def check_win(self) -> None:
     """Called at the end of every render(). Shows the win message once
    per solved puzzle (not on every re-render) and blocks further input
    via the guard at the top of on_canvas_click."""
     if self.puzzle is not None and self.puzzle.is_solved():
        if not self._win_message_shown:
            self._win_message_shown = True
            messagebox.showinfo(
                "Solved!", "You restored the picture! Load another image to keep playing."
            )
     else:
         self._win_message_shown = False

  def run(self) -> None:
    self.root.mainloop() # Tkinter main loop
    # The Pygame main loop should be managed separately or integrated.
    # For now, it will run after Tkinter if `run` finishes.


# Main loop
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


#=======Setting the Screen=========
# Initialize Pygame
pygame.init()
pygame.font.init()

# Setup the clock for decent frametime
clock = pygame.time.Clock()
# Create a screen is handled by PuzzleApp's __init__ (self.screen)

# Create a 'Puzzle' and run it
app = PuzzleApp()

# Main Pygame game loop should be here, after app initialization
# This loop will handle Pygame events and drawing.
while app.running:
    for event in pygame.event.get():
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                app.running = False
        # Did the user click the Load image button? This is handled by Tkinter now.
        # elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        #     mouse_pos = pygame.mouse.get_pos()
        elif event.type == pygame.QUIT:
            app.running = False

    # Pygame drawing logic
    app.screen.fill((0, 0, 0)) # Clear the screen

    if app.show_start_screen:
        app.screen.blit(app.title_text, app.title_rect)
        app.screen.blit(app.choose_text, app.choose_rect)
        app.screen.blit(app.Level1_text, app.Level1_rect)
        app.screen.blit(app.Level2_text, app.Level2_rect)
        app.screen.blit(app.Level3_text, app.Level3_rect)
    # Add game-play drawing here later when game state is managed

    pygame.display.flip() # Update the full display Surface to the screen
    app.FPS.tick(60)

# After the Pygame loop ends, run the Tkinter app
app.run()

pygame.quit()
