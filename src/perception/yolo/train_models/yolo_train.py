from ultralytics import YOLO

# Load pretrained YOLO11 model
model = YOLO("yolo11n.pt")

# Fine-tune
model.train(
    data="/home/checkmate/Documents/chess-bot/yolo/datab.yaml",      # path to your yaml
    epochs=100,
    imgsz=800,
    batch=16,
    device=0,
    workers=0,
    project="runs/train",
    amp=True,
    name="chess_board"
)

# Validate
metrics = model.val()

# Save/export if desired
model.export(format="onnx")