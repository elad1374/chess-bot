import os
from typing import List

import cv2
import numpy as np

HEIGHT = 320
WIDTH = 960
Y_MIN, Y_MAX = 8, 328   # height = 320
X_MIN, X_MAX = 650, 1610 # width = 960

assert X_MIN + WIDTH == X_MAX
assert Y_MIN + HEIGHT == Y_MAX

VALID_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')


def crop_carton_roi(image: np.ndarray) -> np.ndarray:
    """Crop a BGR image using the fixed ZED carton ROI constants."""
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Input image must be a BGR color image")

    h, w = image.shape[:2]
    if w < X_MAX or h < Y_MAX:
        raise ValueError(
            f"Input image is too small for crop constants: got {w}x{h}, need at least {X_MAX}x{Y_MAX}"
        )

    return image[Y_MIN:Y_MAX, X_MIN:X_MAX].copy()


def crop_carton_roi_dir(input_dir: str, output_dir: str) -> None:
    """Crop every valid image in input_dir and save the results to output_dir."""
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    filenames: List[str] = [
        f for f in os.listdir(input_dir) if f.lower().endswith(VALID_EXTENSIONS)
    ]

    if not filenames:
        print(f"No valid image files found in: {input_dir}")
        return

    print(f"Found {len(filenames)} images. Cropping to ({Y_MAX - Y_MIN}x{X_MAX - X_MIN})...\n")

    processed_count = 0
    for filename in filenames:
        image_path = os.path.join(input_dir, filename)
        img = cv2.imread(image_path)
        if img is None:
            print(f"Warning: Failed to load {filename}, skipping...")
            continue

        carton_roi = crop_carton_roi(img)
        save_path = os.path.join(output_dir, filename)
        cv2.imwrite(save_path, carton_roi)
        processed_count += 1

    print(f"Finished! Successfully cropped and saved {processed_count} images to: {output_dir}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Crop a directory of ZED images using the fixed carton ROI."
    )
    parser.add_argument("input_dir", help="Directory containing source images")
    parser.add_argument("output_dir", help="Directory where cropped images will be saved")
    args = parser.parse_args()

    crop_carton_roi_dir(args.input_dir, args.output_dir)