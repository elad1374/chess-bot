import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader, random_split, Dataset
from PIL import Image
import torch.backends.cudnn as cudnn
import os
import sys

# 1. GPU Configuration and Parameters
if not torch.cuda.is_available():
    raise SystemError("CUDA is not available. Ensure NVIDIA drivers and PyTorch CUDA build are installed.")

device = torch.device("cuda")
cudnn.benchmark = True  # Optimizes convolution algorithms for fixed 150x150 input sizes

DATA_DIR = "/home/checkmate/Documents/chess-bot/zed_platform_images_cropped"  # Target this to your 600-image training directory 
MODEL_SAVE_PATH = "chess_cnn_gpu.pth"
IMG_SIZE = 150
BATCH_SIZE = 32
NUM_CLASSES = 12
EPOCHS = 30
LEARNING_RATE = 0.001
NUM_WORKERS = min(4, os.cpu_count() or 1) 

# Explicitly map classes to bypass ImageFolder dependency during inference
CLASS_NAMES = [
    "black-bishop", "black-king", "black-knight", "black-pawn", "black-queen", "black-rook",
    "white-bishop", "white-king", "white-knight", "white-pawn", "white-queen", "white-rook"
]

# 2. Data Transforms
train_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

val_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

class DatasetWrapper(Dataset):
    def __init__(self, subset, transform=None):
        self.subset = subset
        self.transform = transform
        
    def __getitem__(self, index):
        x, y = self.subset[index]
        if self.transform:
            x = self.transform(x)
        return x, y
        
    def __len__(self):
        return len(self.subset)

# 3. Model Initialization (Base architecture mapped to VRAM)
model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)

for param in model.parameters():
    param.requires_grad = False

num_ftrs = model.fc.in_features
model.fc = nn.Linear(num_ftrs, NUM_CLASSES)
model = model.to(device)

# 4. Training Subroutine
def train_model():
    if not os.path.exists(DATA_DIR):
        raise FileNotFoundError(f"Training data directory '{DATA_DIR}' not found. Cannot compute weights.")
        
    print(f"Loading training data from {DATA_DIR}...")
    dataset_full = datasets.ImageFolder(root=DATA_DIR)
    
    train_size = int(0.8 * len(dataset_full))
    val_size = len(dataset_full) - train_size
    train_subset, val_subset = random_split(dataset_full, [train_size, val_size])

    train_dataset = DatasetWrapper(train_subset, train_transform)
    val_dataset = DatasetWrapper(val_subset, val_transform)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS, pin_memory=True)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.fc.parameters(), lr=LEARNING_RATE)

    print(f"Executing training on: {torch.cuda.get_device_name(0)}")
    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        
        for inputs, labels in train_loader:
            inputs = inputs.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item() * inputs.size(0)
            
        epoch_loss = running_loss / train_size
        print(f"Epoch {epoch+1}/{EPOCHS} - Training Loss: {epoch_loss:.4f}")

    torch.save(model.state_dict(), MODEL_SAVE_PATH)
    print(f"Model state dictionary serialized to {MODEL_SAVE_PATH}\n")

# 5. Inference Function
def predict_image(image_path):
    model.eval()
    
    image = Image.open(image_path).convert('RGB')
    image_tensor = val_transform(image).unsqueeze(0).to(device)
    
    with torch.no_grad():
        outputs = model(image_tensor)
        _, preds = torch.max(outputs, 1)
        
    predicted_class = CLASS_NAMES[preds[0].item()]
    return predicted_class

# 6. Execution Block
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <directory_path_to_predict>")
        sys.exit(1)
        
    target_dir = sys.argv[1]
    
    if not os.path.isdir(target_dir):
        print(f"Error: Directory '{target_dir}' does not exist.")
        sys.exit(1)

    # State validation: Check for serialized weights
    if not os.path.exists(MODEL_SAVE_PATH):
        print(f"Weights file '{MODEL_SAVE_PATH}' not found. Initiating training sequence...")
        train_model()
    else:
        print(f"Loading existing weights from '{MODEL_SAVE_PATH}'...")
        model.load_state_dict(torch.load(MODEL_SAVE_PATH, map_location=device))
        
    valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
    
    # Extract and sort target data
    image_files = [
        f for f in os.listdir(target_dir) 
        if os.path.isfile(os.path.join(target_dir, f)) and f.lower().endswith(valid_exts)
    ]
    image_files.sort()
    
    if not image_files:
        print(f"No valid images found in {target_dir}")
        sys.exit(0)
        
    print(f"Found {len(image_files)} images in target directory. Executing inference...\n")
    
    # Process prediction loop
    for file_name in image_files:
        file_path = os.path.join(target_dir, file_name)
        try:
            prediction = predict_image(file_path)
            print(f"{file_name}: {prediction}")
        except Exception as e:
            print(f"Error processing {file_name}: {e}")