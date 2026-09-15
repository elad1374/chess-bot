from sys import stdout
import numpy as np
from common.utils import repo_path, OPENED, CLOSED
from common.enums_and_dicts import PieceType, Orientation
from src.arm.hardware.abstract_robot_hardware import AbstractRobotHardware
from src.arm.hardware.mock_robot_hardware import MockRobotHardware
from src.arm.chessbot import RobotHardware, get_base_and_head_camera_points, get_head_camera_point
from src.arm.behaviors.board_setting_robot import BoardSettingArm
from src.arm.measurements import cube_pose

import argparse
import os
import sys
import tempfile
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Union
from ultralytics import YOLO

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.perception.ZED.cameralib import Camera
from src.perception.ZED.crop_images import crop_carton_roi, X_MIN, Y_MIN


def capture_frame_from_camera(camera) -> np.ndarray:
    # ZED Camera does not use a CV2 device index like a webcam.
    with tempfile.TemporaryDirectory(prefix="yolo_pose_camera_") as tmpdir:
        image_path = camera.take_photo(tmpdir)
        frame = cv2.imread(image_path)

    if frame is None:
        raise RuntimeError("Failed to capture frame from ZED camera")

    frame = crop_carton_roi(frame)

    if np.mean(frame[:, :, 0]) == 0 and np.mean(frame[:, :, 2]) == 0:
        raise RuntimeError("Captured camera frame appears invalid (single green channel).")

    return frame


if __name__ == "__main__":
    with RobotHardware(log=stdout, flip=True) as hw, Camera() as camera:
        image = capture_frame_from_camera(camera)
        model = YOLO(repo_path("runs/pose/runs/pose_train/chess_board-2/weights/best.pt"))
        results = model.predict(source=image, imgsz=[320, 960], conf=0.25)[0]

        all_points = []
        for i in range(len(results.boxes)):
            cls_id = int(results.boxes.cls[i].item())
            cls = Orientation(cls_id)

            # --- B. Keypoints (Head & Base) ---
            if results.keypoints is not None and len(results.keypoints) > i:
                kpts_xy = results.keypoints.xy[i].cpu().numpy()
                if results.keypoints.conf is not None:
                    kpts_conf = results.keypoints.conf[i].cpu().numpy()
                else:
                    kpts_conf = [1.0, 1.0]

                if len(kpts_xy) >= 2:
                    head_x, head_y = int(kpts_xy[0][0]), int(kpts_xy[0][1])
                    base_x, base_y = int(kpts_xy[1][0]), int(kpts_xy[1][1])

                    print(kpts_xy[0], kpts_xy[1], cls)
                    all_points.append((
                        (base_x + X_MIN, base_y + Y_MIN),
                        (head_x + X_MIN, head_y + Y_MIN),
                        cls,
                    ))

        robot = BoardSettingArm(hw)
        for i, (base, head, cls) in enumerate(sorted(all_points, key=lambda pt: -pt[0][1]), 1):
            base = hw.camera_vector_to_robot_vector(camera.last_image_get_xyz(*base))
            head = hw.camera_vector_to_robot_vector(camera.last_image_get_xyz(*head))

            robot.move_piece_to_platform(head_pos=head, base_pos=base, orientation=cls)
            robot.move_from_platform_to_target(f"c{i}", type=PieceType.PAWN)
