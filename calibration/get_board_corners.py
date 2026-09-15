import cv2
import json
import numpy as np
from common.utils import *
from src.perception.ZED.cameralib import Camera

clicked_points = []

def select_corners(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(clicked_points) < 4:
        clicked_points.append([x, y])
        cv2.circle(param["img"], (x, y), 5, (0, 0, 255), -1)
        cv2.imshow("Click 4 Corners", param["img"])

def order_points(pts):
    pts = np.array(pts, dtype="float32")
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]       # Top-Left
    rect[2] = pts[np.argmax(s)]       # Bottom-Right
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]    # Top-Right
    rect[3] = pts[np.argmax(diff)]    # Bottom-Left
    return rect.tolist()

def main(image_path="board.jpg", output_file="corners.json"):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not open image '{image_path}'")
        return

    img_copy = img.copy()
    cv2.imshow("Click 4 Corners", img_copy)
    cv2.setMouseCallback("Click 4 Corners", select_corners, {"img": img_copy})

    print("Click the 4 outer corners of the chessboard. Press any key when done.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    if len(clicked_points) == 4:
        ordered_corners = order_points(clicked_points)
        with open(output_file, "w") as f:
            json.dump(ordered_corners, f, indent=4)
        print(f"Successfully saved 4 corners to '{output_file}'.")
    else:
        print(f"Error: Expected 4 points, but got {len(clicked_points)}.")

if __name__ == "__main__":
    with Camera() as camera:
        path = camera.take_photo("game_photos")
        main(path)