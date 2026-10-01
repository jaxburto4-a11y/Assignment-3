"""
HIT137 Assignment 3 - GUI (Tkinter)

Run this file directly to launch the app

Requires this file to sit in the same folder as:
    puzzle_core.py                (Tile, Puzzle)
    Image_Processor_component.py  (ImageProcessor)
"""

import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
from PIL import Image, ImageTk

from puzzle_core import Puzzle
from Image_Processor_component import ImageProcessor

TRANSFORMATIONS_BY_GRID_SIZE = {3: 6, 4: 12, 5: 20}


class PuzzleApp:
    """should hold a single Puzzle instance at a time."""

    def __init__(self):
        self.puzzle: Puzzle | None = None
        self.image = None                    # prepared (resized/padded) original image, BGR
        self.selected_tile_index: int | None = None
        self.hint_info: dict | None = None   # active hint, cleared after the next move
        self.grid_size = 3
        self.canvas_size = 420               # fixed display size for both canvases
        self.cell_size = self.canvas_size // self.grid_size
        self._win_message_shown = False

        # keep references so Tkinter's garbage collector doesn't drop the images
        self.original_photo = None
        self.transformed_photo = None

        self._build_ui()

    # UI construction

    def _build_ui(self) -> None:
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

    # Loading an image

    def on_grid_size_change(self, value: str) -> None:
        """Store the chosen grid size; only takes effect on the NEXT load,
        per the spec ('the player must choose grid size before loading')."""
        self.grid_size = int(value)

    def on_load_image_click(self) -> None:
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if not file_path:
            return

        try:
            raw_image = ImageProcessor.load_image(file_path)
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

    # Rendering

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
        self.incorrect_label.config(text=f"Incorrect: {self.puzzle.count_incorrect()}")

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
        self.hint_button.config(state=tk.NORMAL)
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

    # -----

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    app = PuzzleApp()
    app.run()
