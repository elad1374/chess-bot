from common.utils import repo_path
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from src.perception.yolo.vision_inference.platform_piece_classifier import *


from src.perception.yolo.vision_inference.board_pieces_detector import BoardPiecesDetector
from src.perception.ZED.cameralib import Camera
from src.perception.yolo.vision_inference.orientation_detector import *

if __name__ == "__main__":
    image_path = repo_path("src/perception/yolo/photos_game/00_20260813_194939_aaa.png")
    cropped_path = repo_path("src/perception/yolo/photos_platform/00_20260819_171819_121.png")
    carton_image_path = repo_path("src/perception/yolo/photos_setup/00_20260817_220722_406_aaa.png")
    with Camera() as camera:
        classifier = CNNPieceClassifier(camera = camera)
        classifier.identify_piece(cropped_path)
        detector = YoloOrientationDetector(camera = camera)
        # detector.detect_pickup_pose(carton_image_path)


    
    