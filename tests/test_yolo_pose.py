import argparse
import os
import sys
import tempfile
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Union
from common.utils import repo_path
from ultralytics import YOLO

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.perception.ZED.cameralib import Camera
from src.perception.ZED.crop_images import crop_carton_roi




def capture_frame_from_camera() -> np.ndarray:
    # ZED Camera does not use a CV2 device index like a webcam.
    with Camera() as camera:
        with tempfile.TemporaryDirectory(prefix="yolo_pose_camera_") as tmpdir:
            image_path = camera.take_photo(tmpdir)
            frame = cv2.imread(image_path)

    if frame is None:
        raise RuntimeError("Failed to capture frame from ZED camera")

    frame = crop_carton_roi(frame)

    if np.mean(frame[:, :, 0]) == 0 and np.mean(frame[:, :, 2]) == 0:
        raise RuntimeError("Captured camera frame appears invalid (single green channel).")

    return frame


def annotate_and_save(
    image_source: Union[str, np.ndarray],
    output_dir: str,
    model_path: str = repo_path("runs/train/chess_board_dense_pose/weights/best.pt"),
    conf_threshold: float = 0.25,
    image_name: Optional[str] = None,
):
    """
    Runs YOLOv11 Pose prediction on a still image or camera frame and saves an annotated version with:
    1. Bounding boxes around each piece.
    2. Head and Base keypoints connected by a line.
    3. A clean summary label menu at the bottom panel.
    """
    model = YOLO(model_path)

    if isinstance(image_source, str):
        image_path = image_source
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at: {image_path}")
        image = cv2.imread(image_path)
        image_name = Path(image_path).name
    else:
        image = image_source
        if image_name is None:
            image_name = "camera_frame.png"

    if image is None:
        raise RuntimeError("Failed to load image for annotation.")

    img_h, img_w, _ = image.shape

    # Run inference
    results = model.predict(source=image, imgsz=[320, 960], conf=conf_threshold)[0]

    # Colors (BGR)
    CLASS_COLORS = {
        0: (0, 0, 255),    # Red for Lying
        1: (0, 255, 0)     # Green for Standing
    }

    KP_COLOR_HEAD = (255, 255, 0)   # Cyan for Head
    KP_COLOR_BASE = (255, 0, 255)   # Magenta for Base
    KP_LINE_COLOR = (0, 215, 255)   # Yellow/Orange connecting line

    class_counts = {0: 0, 1: 0}

    boxes = results.boxes
    keypoints = results.keypoints

    if boxes is not None:
        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            class_counts[cls_id] = class_counts.get(cls_id, 0) + 1
            color = CLASS_COLORS.get(cls_id, (255, 255, 255))

            # --- A. Bounding Box ---
            x1, y1, x2, y2 = map(int, boxes.xyxy[i].tolist())
            cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness=2)

            # --- B. Keypoints (Head & Base) ---
            if keypoints is not None and len(keypoints) > i:
                kpts_xy = keypoints.xy[i].cpu().numpy()
                if keypoints.conf is not None:
                    kpts_conf = keypoints.conf[i].cpu().numpy()
                else:
                    kpts_conf = [1.0, 1.0]

                if len(kpts_xy) >= 2:
                    head_x, head_y = int(kpts_xy[0][0]), int(kpts_xy[0][1])
                    base_x, base_y = int(kpts_xy[1][0]), int(kpts_xy[1][1])

                    head_conf = kpts_conf[0]
                    base_conf = kpts_conf[1]

                    if head_x > 0 and base_x > 0:
                        cv2.line(image, (head_x, head_y), (base_x, base_y), KP_LINE_COLOR, 2, cv2.LINE_AA)

                    if head_x > 0 and head_conf >= 0.1:
                        cv2.circle(image, (head_x, head_y), 5, (0, 0, 0), -1, cv2.LINE_AA)
                        cv2.circle(image, (head_x, head_y), 4, KP_COLOR_HEAD, -1, cv2.LINE_AA)

                    if base_x > 0 and base_conf >= 0.1:
                        cv2.circle(image, (base_x, base_y), 5, (0, 0, 0), -1, cv2.LINE_AA)
                        cv2.circle(image, (base_x, base_y), 4, KP_COLOR_BASE, -1, cv2.LINE_AA)

    banner_height = 50
    banner = np.zeros((banner_height, img_w, 3), dtype=np.uint8)

    total_pieces = sum(class_counts.values())
    lying_count = class_counts.get(0, 0)
    standing_count = class_counts.get(1, 0)

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.55
    thickness = 2

    cv2.putText(banner, f"Total: {total_pieces}", (15, 30), font, font_scale, (255, 255, 255), thickness)
    cv2.rectangle(banner, (150, 15), (165, 30), CLASS_COLORS[1], -1)
    cv2.putText(banner, f"Standing: {standing_count}", (175, 30), font, font_scale, (255, 255, 255), thickness)
    cv2.rectangle(banner, (330, 15), (345, 30), CLASS_COLORS[0], -1)
    cv2.putText(banner, f"Lying: {lying_count}", (355, 30), font, font_scale, (255, 255, 255), thickness)
    cv2.circle(banner, (500, 22), 5, KP_COLOR_HEAD, -1)
    cv2.putText(banner, "Head", (512, 28), font, 0.45, (255, 255, 255), 1)
    cv2.circle(banner, (580, 22), 5, KP_COLOR_BASE, -1)
    cv2.putText(banner, "Base", (592, 28), font, 0.45, (255, 255, 255), 1)

    final_image = np.vstack((image, banner))

    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, f"labeled_{Path(image_name).name}")

    cv2.imwrite(save_path, final_image)
    print(f"✅ Prediction saved to: {save_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run YOLO pose inference on an image or camera frame.")
    parser.add_argument("--image_path", default="/home/checkmate/Downloads/data_set_carton/tests/img_161_extra.png",
                        help="Path to the input image.")
    parser.add_argument("--output_dir", default=repo_path("src/perception/yolo/predictions"),
                        help="Directory to save the annotated output.")
    parser.add_argument("--model_path", default=repo_path("runs/pose/runs/pose_train/chess_board-2/weights/best.pt"),
                        help="Path to the YOLO pose model weights.")
    parser.add_argument("--conf_threshold", type=float, default=0.25,
                        help="Confidence threshold for prediction.")
    parser.add_argument("--use_camera", action="store_true",
                        help="Capture a single frame from the default camera instead of using an image file.")

    args = parser.parse_args()

    if args.use_camera:
        frame = capture_frame_from_camera()
        annotate_and_save(
            frame,
            args.output_dir,
            model_path=args.model_path,
            conf_threshold=args.conf_threshold,
            image_name=f"camera.png"
        )
    else:
        annotate_and_save(
            args.image_path,
            args.output_dir,
            model_path=args.model_path,
            conf_threshold=args.conf_threshold
        )