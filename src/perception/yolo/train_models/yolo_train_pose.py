from ultralytics import YOLO

# Load pretrained YOLO11 Pose model (must use -pose weights for keypoint estimation)
model = YOLO("yolo11s-pose.pt")

# Fine-tune
model.train(
    data="/home/checkmate/Documents/chess-bot/yolo/yaml_files/pose_data.yaml",  # Path to your YAML file
    epochs=300,
    patience=40,             # Early stopping if val performance plateaus
    imgsz=[320, 960],        # Exact [Height, Width] aspect ratio
    batch=8,                 # 8 or 16 gives smooth gradient updates
    device=0,
    workers=2,
    project="runs/pose_train",
    amp=True,
    name="chess_board",

    # Augmentations to simulate more than 128 unique board setups
    degrees=10.0,            # Small rotation jitter
    scale=0.25,              # Scale variation
    fliplr=0.5,              # Horizontal flip
    mosaic=1.0
)

# Validate
metrics = model.val()

# Export model to ONNX for robotics deployment
model.export(format="onnx")