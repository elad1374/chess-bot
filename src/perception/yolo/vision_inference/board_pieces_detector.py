from ultralytics import YOLO
import os
from typing import Optional
from src.perception.ZED.cameralib import Camera
from .vision_model import VisionModel
import cv2
import random
from pathlib import Path
from abc import ABC, abstractmethod
from common.enums_and_dicts import  MAX_LIMITS
from common.utils import repo_path

BINARY = "binary"
UNARY = "unary"
ADVANCED = "advanced"
MODEL_PATHS = {
    BINARY: repo_path("runs/detect/runs/train/chess_board-4/weights/best.pt"),
    UNARY: repo_path("runs/detect/runs/train/chess_board-3/weights/best.pt"),
    ADVANCED: repo_path("runs/detect/chess_training/run_1/weights/best.pt"),
}
MODEL_CONF = {
    BINARY: 0.4,
    UNARY: 0.6,
    ADVANCED: 0.25
}

PREDICTION_OUTPUT_DIR = repo_path("src/perception/yolo/predictions_game")
IMAGE_OUTPUT_DIR = repo_path("src/perception/yolo/photos_game")


class AbsBoardDetector(VisionModel):
    def __init__(self, camera: Optional[Camera] = None, conf: float = 0.25, path_list = None):
        super().__init__(camera=camera, conf=conf, path_list=path_list)

    @abstractmethod
    def predict(self, image_path: Optional[str] = None)-> str:
        pass


class BoardPiecesDetector(AbsBoardDetector):
    """
    Wrapper class for loading and running predictions with Ultralytics YOLO models.
    """

    def __init__(self, model_name: str = BINARY, camera: Camera = None, save_regularly: bool = True, optimize: bool = False):
        super().__init__(camera=camera, conf=MODEL_CONF[BINARY], path_list=[IMAGE_OUTPUT_DIR, PREDICTION_OUTPUT_DIR])
        self.model_path: str = ""
        self.model: YOLO = None
        self.camera: Camera = camera 
        self.save_regularly: bool = save_regularly
        self.optimize: bool = optimize

        self.set_model(model_name)
        
    def save_yolo_prediction_clean(self, result, image, output_path):
        """
        Saves YOLO prediction with only bounding boxes and a class legend.

        Args:
            result: YOLO result object (result[0])
            image: Original image as numpy array (cv2 image)
            output_path: Path where the image will be saved
        """

        img = image.copy()

        colors = {}

        def get_color(class_id):
            if class_id not in colors:
                colors[class_id] = (
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255)
                )
            return colors[class_id]

        legend = []

        for box in result.boxes:
            cls_id = int(box.cls[0])
            name = result.names[cls_id]

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            color = get_color(cls_id)

            # Draw bounding box only
            cv2.rectangle(
                img,
                (x1, y1),
                (x2, y2),
                color,
                3
            )

            if name not in [item[0] for item in legend]:
                legend.append((name, color))

        # Add legend at bottom
        legend_height = 40 * len(legend)

        canvas = cv2.copyMakeBorder(
            img,
            0,
            legend_height,
            0,
            0,
            cv2.BORDER_CONSTANT,
            value=(30, 30, 30)
        )

        y = img.shape[0] + 30

        for name, color in legend:
            cv2.rectangle(
                canvas,
                (20, y - 20),
                (50, y + 10),
                color,
                -1
            )

            cv2.putText(
                canvas,
                name,
                (70, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

            y += 40

        cv2.imwrite(str(output_path), canvas)


    def set_model(self, name: str):
        """
        Updates the model path field and loads/reloads the YOLO model instance.

        :param name: Path or identifier string for the model weights.
        """
        if name not in MODEL_PATHS:
            raise ValueError(f"Model name '{name}' not recognized. Available models: {list(MODEL_PATHS.keys())}")
        
        self.model_path = MODEL_PATHS[name]
        self.model = YOLO(self.model_path)
        self.conf = MODEL_CONF[name]

    def _optimize_chess_predictions(self, detections, max_limits):
        """
        Optimizes YOLO piece detections based on chess piece maximums and confidence scores.
        
        Args:
            detections: List of dicts [{'label': 'white_queen', 'conf': 0.85, 'box': [...]}, ...]
            max_limits: Dict defining the maximum allowed per piece type.
        """

        # Separate pieces by color (assuming labels are formatted like "white_queen", "black_pawn")
        colors = set(d['label'].split('-')[0] for d in detections)
        
        # Priority order for taking away overabundant pieces
        take_order = ['king', 'queen', 'knight', 'rook', 'bishop', 'pawn']
        # Allowed target classes to redistribute to
        target_classes = ['queen', 'knight', 'rook', 'bishop']
        for color in colors:
            # Get pieces for this color
            color_pieces = [d for d in detections if d['label'].startswith(color)]

            def get_counts():
                counts = {piece: 0 for piece in take_order}
                for d in color_pieces:
                    piece_type = d['label'].split('-')[1]
                    if piece_type in counts:
                        counts[piece_type] += 1
                return counts

            def is_legal(counts):
                # Legal means King is exactly 1 (or within limits) and nothing exceeds max
                return counts['king'] == max_limits['king'] and \
                    all(counts[p] <= max_limits[p] for p in take_order)

            counts = get_counts()
            
            # --- RULE 1: Fix missing King by transforming the lowest confidence Queen ---
            if not is_legal(counts) and counts['king'] < max_limits['king'] and counts['queen'] > 0:
                print("6666666666666666666666666666666666666666666666666666")
                # Find all queens of this color
                queens = [d for d in color_pieces if d['label'].endswith('queen')]
                # Sort by confidence ascending (lowest first)
                queens.sort(key=lambda x: x['conf'])
                
                # Change the lowest confidence queen to a king
                queens[0]['label'] = f"{color}-king"
                counts = get_counts() # Re-evaluate counts
                
            # --- RULE 2: Reallocate overabundant pieces ---
            while not is_legal(counts):
                # Find classes that exceed their maximum allowed amount
                over_max_classes = [p for p in take_order if counts[p] > max_limits.get(p, 0)]
                
                if not over_max_classes:
                    break # Break if invalid for a reason other than overabundance (e.g. missing pieces)
                    
                # Pick the highest priority class to take from (King -> Queen -> etc.)
                source_piece = None
                for p in take_order:
                    if p in over_max_classes:
                        source_piece = p
                        break
                        
                # Find the lowest confidence instance of this source piece
                source_candidates = [d for d in color_pieces if d['label'].endswith(source_piece)]
                source_candidates.sort(key=lambda x: x['conf'])
                piece_to_change = source_candidates[0]
                
                # Find where there is the most space among target classes
                spaces = {p: max_limits[p] - counts[p] for p in target_classes}
                
                # Find the class with the maximum space
                target_piece = max(spaces, key=spaces.get)
                
                # If there's no space anywhere, we are forced to break (or delete the piece)
                if spaces[target_piece] <= 0:
                    # Optional: piece_to_change['delete'] = True
                    break
                    
                # Change the label to the target piece
                piece_to_change['label'] = f"{color}-{target_piece}"
                
                # Update counts for the next while loop iteration
                counts = get_counts()

        return detections

    def predict(self, image_path: Optional[str] = None)-> str:
        """
        Takes an image (if none provided) and runs object detection using the loaded YOLO model.
        Saves the results in png and txt formats in the specified output directory.
        """
        if self.model is None:
            raise RuntimeError("Model is not loaded. Ensure a valid model path is set.")

        image_path = self._resolve_image_path(image_path, IMAGE_OUTPUT_DIR)
        
        results = self.model(image_path, conf=self.conf)
        result = results[0]

        base_name = os.path.splitext(os.path.basename(image_path))[0]
        txt_path = os.path.join(PREDICTION_OUTPUT_DIR, base_name + ".txt")

        # pre txt save fetch
        raw_detections = []
        for box in result.boxes:
            cls_id = int(box.cls[0])
            label = result.names[cls_id]
            conf = float(box.conf[0])

            x1, y1, x2, y2 = box.xyxy[0].tolist()
            center_x = (x1 + x2) / 2
            baseline_y = y2 - 25 #fix offset for baseline.
            raw_detections.append({'label': label, 'conf': conf, 'center_x': center_x, 'baseline_y': baseline_y})                

        detections = raw_detections
        # Optimize
        if self.optimize:
            detections = self._optimize_chess_predictions(raw_detections, MAX_LIMITS)

        # Write to txt file
        with open(txt_path, "w") as f:
            for d in detections:
                f.write(f"{d['label']} {d['center_x']:.1f} {d['baseline_y']:.1f}\n")   
            
        # Save annotated image
        output_image = os.path.join(PREDICTION_OUTPUT_DIR, os.path.basename(image_path))
        if not self.save_regularly:
            self.save_yolo_prediction_clean(result, cv2.imread(image_path), output_image)
        else:
            result.save(filename=output_image)
        return txt_path  # Return the path to the saved coordinates file for further processing

class MockBoardDetector(AbsBoardDetector):
    def __init__(self, camera: Optional[Camera] = None, conf: float = 0.25, path_list = None):
        super().__init__(camera=camera, conf=conf, path_list=path_list)

    def predict(self, image_path: Optional[str] = None)-> str:
        if image_path is None or not Path(image_path).is_file():
            raise FileNotFoundError("The image files does not exists")
        return image_path
            
    
        