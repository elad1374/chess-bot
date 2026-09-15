
import os
from abc import ABC
from typing import Optional
from src.perception.ZED.cameralib import Camera

class VisionModel(ABC):
    """
    Abstract Base Class for all vision models in project.
    """


    def __init__(self, camera: Optional[Camera] = None, conf: float = 0.25, path_list = None):
        
        self.camera: Optional[Camera] = camera
        self.conf: float = conf
        self._ensure_directories(path_list)



    def _resolve_image_path(self, image_path: Optional[str], output_dir: Optional[str]) -> str:
        """
        Shared camera fallback logic. Captures photo if image_path is None.
        """
        if image_path is None:
            if self.camera is None:
                raise RuntimeError("No image path provided and camera is not configured.")
            image_path = self.camera.take_photo(output_dir)

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image path does not exist: {image_path}")

        return image_path

    
    def _ensure_directories(self, path_list):
        """Ensures that the output directory exists."""
        if path_list is None:
            return
        for path in path_list:
            os.makedirs(path, exist_ok=True)