from abc import abstractmethod
from common.enums_and_dicts import *
from .vision_model import VisionModel
from common.utils import repo_path
from common.exceptions import YoloVisionException
from typing import Optional
from ultralytics import YOLO
from src.perception.ZED.cameralib import Camera
import os
import sys
from PIL import Image
import torch
from torchvision import transforms


DEFAULT_CONF = 0.5
IMAGE_OUTPUT_DIR = repo_path("src/perception/yolo/photos_platform")
MODEL_PATH = repo_path("standalone_chess_model.pt")
INFERENCE_TRANSFORM = transforms.Compose([
    transforms.Grayscale(num_output_channels=3),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

class PlatformPieceClassifier(VisionModel):
    """
    Abstract Base Class for piece classification on the platform.
    """

    def __init__(self, camera: Optional[Camera] = None, conf: float = DEFAULT_CONF):
        super().__init__(camera=camera, conf=conf, path_list=[IMAGE_OUTPUT_DIR])

    @abstractmethod
    def identify_piece(self, image_path: Optional[str] = None) -> ColoredPieceType:
        """
        Abstract method to identify the piece on the platform.
        """
        pass



class YOLOPieceClassifier(PlatformPieceClassifier):
    """
    YOLO implementation for platform piece classification.
    """
    def __init__(self, model_path: str, camera: Optional[Camera] = None, conf: float = DEFAULT_CONF):
        super().__init__(camera=camera, conf=conf)
        self.model_path: str = model_path
        print(f"Loading YOLO Classifier from: {self.model_path}")
        self.model: YOLO = YOLO(self.model_path)

    def identify_piece(self, image_path: Optional[str] = None) -> ColoredPieceType:

        image_path = self._resolve_image_path(image_path, IMAGE_OUTPUT_DIR)

        #Run inference
        results = self.model.predict(source=image_path, conf=self.conf)
        result = results[0]

        if result.boxes is not None and len(result.boxes) > 0:
            top_box = max(result.boxes, key=lambda b: float(b.conf[0]))
            class_id = int(top_box.cls[0])
            return ColoredPieceType(class_id)
        else:
            raise YoloVisionException("No class detected on platform")

class ManualPieceClassifier(PlatformPieceClassifier):
    """ (almost) Mock Class"""
    def __init__(self, camera: Optional[Camera] = None, conf: float = DEFAULT_CONF):
        super().__init__(camera=camera, conf=conf)

    def identify_piece(self, image_path: Optional[str] = None) -> ColoredPieceType:
        """
        Get piece class by user shell dialog.
        """
        return ColoredPieceType.parse(input("Choose piece class: "))



#### IF NEEDED ####
class CNNPieceClassifier(PlatformPieceClassifier):
    """
    CNN implementation for platform piece classification. 
    """
    def __init__(self, model_path: str = MODEL_PATH, camera: Optional[Camera] = None, conf: float = DEFAULT_CONF):
        super().__init__(camera=camera, conf=conf)
        self.model_path = model_path
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load model once at startup into memory
        self.model = torch.jit.load(self.model_path, map_location=self.device)
        self.model.eval()

    def crop_image(self, image_path: str, output_dir: str, x: int, y: int, width: int, height: int) -> bool:
        image = Image.open(image_path).convert("RGB")

        img_w, img_h = image.size

        x0 = max(0, min(x, img_w - 1))
        y0 = max(0, min(y, img_h - 1))
        w = min(width, img_w - x0)
        h = min(height, img_h - y0)

        cropped = image.crop((x0, y0, x0 + w, y0 + h))

        filename = os.path.basename(image_path)
        output_path = os.path.join(output_dir, filename)

        cropped.save(output_path)

        return cropped

    def identify_piece(self, image_path: Optional[str] = None) -> ColoredPieceType:
        image_path = self._resolve_image_path(image_path, IMAGE_OUTPUT_DIR)

        # Run inference
        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        if width!=150 or height!=150:
            image = self.crop_image(image_path=image_path, output_dir=IMAGE_OUTPUT_DIR, x=1460,  y=220, width=150,  height=150)
        display_name = os.path.basename(image_path)

        input_tensor = INFERENCE_TRANSFORM(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            outputs = self.model(input_tensor)
            probs = torch.softmax(outputs, dim=1)
            idx = outputs.argmax(dim=1).item()
            conf_score = probs[0][idx].item()
        if conf_score<0.6:
            #probably didn't see anything
            print(f"Source: {display_name} | FAILED PREDICTION | Confidence: {conf_score * 100:.2f}%")
            return None

        print(f"Source: {display_name} | Prediction: {INT_TO_NAME[idx]} | Confidence: {conf_score * 100:.2f}%")

        # Map integer index to ColoredPieceType expected by caller
        return ColoredPieceType(idx)  # Convert to your enum/type as needed



        