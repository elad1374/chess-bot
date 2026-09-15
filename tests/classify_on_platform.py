import os
import sys
from PIL import Image
import torch
from torchvision import transforms
from common.utils import repo_path

CLASS_NAMES = [
    "black_bishop", "black_king", "black_knight", "black_pawn", "black_queen", "black_rook",
    "white_bishop", "white_king", "white_knight", "white_pawn", "white_queen", "white_rook"
]

transform = transforms.Compose([
    transforms.Grayscale(num_output_channels=3),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def run_standalone_inference(input_path, model_path=repo_path("standalone_chess_model.pt")):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Loads entire architecture + fine-tuned weights instantly
    model = torch.jit.load(model_path, map_location=device)
    model.eval()

    def predict(img_path):
        image = Image.open(img_path).convert("RGB")
        input_tensor = transform(image).unsqueeze(0).to(device)
        with torch.no_grad():
            outputs = model(input_tensor)
            probs = torch.softmax(outputs, dim=1)
            idx = outputs.argmax(dim=1).item()
            return CLASS_NAMES[idx], probs[0][idx].item()

    if os.path.isfile(input_path):
        cls, conf = predict(input_path)
        print(f"File: {os.path.basename(input_path)} | Prediction: {cls} | Confidence: {conf*100:.2f}%")
    elif os.path.isdir(input_path):
        valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')
        files = sorted([f for f in os.listdir(input_path) if f.lower().endswith(valid_exts)])
        for fname in files:
            cls, conf = predict(os.path.join(input_path, fname))
            print(f"{fname:<35} -> {cls:<15} ({conf*100:.2f}%)")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_standalone_inference(sys.argv[1])