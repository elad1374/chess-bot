import os
import shutil
from ultralytics import YOLO

def main():
    print("Loading base model...")
    # Load the original model from Hugging Face
    model = YOLO("https://huggingface.co/KanisornPutta/chess-model-yolov8m/resolve/main/chess-model-yolov8m.pt")

    print("Starting training...")
    # Train the model. 
    # (Make sure to change "path/to/your/data.yaml" to your actual dataset file)
    model.train(
        data="/home/checkmate/Documents/chess-bot/yolo/yaml_files/data.yaml", 
        epochs=100, 
        imgsz=800, 
        device=0,               # Change to "cuda" or 0 if you have an NVIDIA GPU
        project="chess_training",   # Forces the output folder name
        name="run_1",               # Forces the sub-folder name
        exist_ok=True               # Overwrites "run_1" if you run this script multiple times
    )

    # Because we specified project and name, we know EXACTLY where the file is saved
    trained_weights_path = os.path.join("chess_training", "run_1", "weights", "best.pt")
    
    # The final name you want for your model
    final_model_name = "testmodel.pt"

    print(f"\nTraining complete. Locating weights at: {trained_weights_path}")
    
    # Check if the file was created successfully, then rename/copy it
    if os.path.exists(trained_weights_path):
        shutil.copy(trained_weights_path, final_model_name)
        print(f"Success! Model successfully exported as '{final_model_name}' in your current directory.")
    else:
        print("Error: Could not find the trained weights. Training may have failed or been interrupted.")

# It is highly recommended to wrap YOLO training in this __main__ block 
# to prevent crashing on Windows machines during multi-threading
if __name__ == '__main__':
    main()
