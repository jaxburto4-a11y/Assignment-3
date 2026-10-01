# -*- coding: utf-8 -*-
import os

import cv2
import numpy as np


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

