import os
import cv2
import numpy as np
from abc import ABC, abstractmethod
from common.utils import repo_path
from common.enums_and_dicts import Orientation
from .vision_model import VisionModel
from typing import Optional, Tuple
from dataclasses import dataclass
from ultralytics import YOLO
from src.perception.ZED.cameralib import Camera
from src.perception.ZED import crop_images
from src.perception.ZED.crop_images import crop_carton_roi


MODEL_PATH: str = repo_path("runs/pose/runs/pose_train/chess_board-2/weights/best.pt")
PREDICTION_OUTPUT_DIR = repo_path("src/perception/yolo/predictions_setup")
IMAGE_OUTPUT_DIR = repo_path("src/perception/yolo/photos_setup")
DEFAULT_CONF: float = 0.5

@dataclass
class PiecePose:
    """Dataclass representing the target piece's pose and metadata."""
    head: Tuple[float, float, float]
    base: Tuple[float, float, float]
    orientation: Orientation
    confidence: float

class OrientationDetector(VisionModel):
    def __init__(self, camera: Optional[Camera] = None, conf: float = 0.25, path_list = None):
        super().__init__(camera=camera, conf = conf, path_list = path_list)

    @abstractmethod
    def detect_pickup_pose(self, image_path: Optional[str] = None) -> Optional[PiecePose]:
        pass

class YoloOrientationDetector(OrientationDetector):
    """
    Wrapper class for running predictions with YOLO Pose to detect orientation 
    and center of chess piece for grabbing.
    """

    def __init__(
        self,
        camera: Optional[Camera] = None,
        model_path: str = MODEL_PATH,
        conf: float = DEFAULT_CONF,
        output_dir: str = PREDICTION_OUTPUT_DIR,
    ):
        """Initializes the YOLO Model wrapper for piece orientation."""

        super().__init__(camera=camera, conf=conf, path_list=[IMAGE_OUTPUT_DIR, PREDICTION_OUTPUT_DIR])

        self.model_path: str = model_path
        print(f"Loading YOLO Pose model from: {self.model_path}")
        self.model: YOLO = YOLO(self.model_path)
        self.output_dir = output_dir

    def set_model(self, model_path: str) -> None:
        """Reloads a new model if needed."""
        self.model_path = model_path
        self.model = YOLO(self.model_path)

    def _load_and_crop_image(self, image_path: Optional[str], output_dir: Optional[str]) -> np.ndarray:
        """
        Load an image from path or camera, crop it using the standard ROI, and return as numpy array.
        Returns the cropped image ready for model inference.
        """
        image_path = self._resolve_image_path(image_path, output_dir)
        image = cv2.imread(image_path)
        
        if image is None:
            raise RuntimeError(f"Failed to load image from {image_path}")
        
        cropped_image = crop_carton_roi(image)
        return cropped_image

    def detect_pickup_pose(self, image_path: Optional[str] = None) -> Optional[PiecePose]:
        """
        Detects piece poses and returns ONLY the piece with the lowest 
        middle coordinate in the picture (highest y-value).
        Loads image, crops it to the standard ROI, runs inference, then adjusts
        detected coordinates back to original image space.
        """
        image_path = self._resolve_image_path(image_path, IMAGE_OUTPUT_DIR)
        
        # Load and crop the image
        cropped_image = self._load_and_crop_image(image_path, IMAGE_OUTPUT_DIR)

        # Run inference on cropped image
        results = self.model.predict(
            source=cropped_image,
            imgsz=[crop_images.HEIGHT, crop_images.WIDTH],
            conf=self.conf,
            # verbose=False if terminal gets messy
        )
        
        result = results[0]
        target_piece: Optional[PiecePose] = None
        max_y_center = -1.0

        if result.boxes is not None and len(result.boxes) > 0 and result.keypoints is not None:
            boxes = result.boxes
            keypoints = result.keypoints

            for box, kp in zip(boxes, keypoints):
                # xywh = [[x_center, y_center, width, height]]
                y_center = float(box.xywh[0, 1])
                
                # Check if this piece is the lowest in the frame
                if y_center > max_y_center:
                    max_y_center = y_center
                    
                    # Class and confidence retrival
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    orientation = Orientation(class_id)

                    # Assumes in the labeling head is first, then base
                    kp_pts = kp.xy[0].tolist()

                    (head_x, head_y), (base_x, base_y) = kp_pts
                    
                    # Adjust coordinates back to original image space by adding crop offsets
                    head_x += crop_images.X_MIN
                    head_y += crop_images.Y_MIN
                    base_x += crop_images.X_MIN
                    base_y += crop_images.Y_MIN

                    if class_id==1:
                    #    head_y += 25
                        head_y += 10

                    head_coords = self.camera.last_image_get_xyz(head_x, head_y)
                    base_coords = self.camera.last_image_get_xyz(base_x, base_y)

                    target_piece = PiecePose(
                        head=head_coords,
                        base=base_coords,
                        orientation=orientation,
                        confidence=confidence
                    )

        # Draw annotations and save
        annotated_image = result.plot()
        filename = os.path.basename(image_path)
        save_path = os.path.join(self.output_dir, f"result_{filename}")
        cv2.imwrite(save_path, annotated_image)
        print(f"Saved prediction result image to: {save_path}")

        return target_piece

class ManualOrientationDetector(OrientationDetector):
    def __init__(self, camera: Optional[Camera] = None, conf: float = 0.25, path_list = None):
        super().__init__(camera=camera, conf = conf, path_list = path_list)

    def detect_pickup_pose(self, image_path: Optional[str] = None) -> Optional[PiecePose]:
        head, base = self.camera.get_two_points()
        oreintation_num = int(input("0 for Lying, 1 for Standing. Choose: "))
        orientation = Orientation(oreintation_num)
        return PiecePose(head=head, base=base, orientation=orientation, confidence=100)





    
    
