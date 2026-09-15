import os
import glob
from PIL import Image
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms

# ==========================================
# 1. DATASET & SPLITTING LOGIC
# ==========================================
class StructuredChessDataset(Dataset):
    def __init__(self, file_paths, labels, transform=None):
        self.file_paths = file_paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, idx):
        img_path = self.file_paths[idx]
        image = Image.open(img_path).convert("RGB")
        label = self.labels[idx]
        
        if self.transform:
            image = self.transform(image)
            
        return image, label

def prepare_data_splits(data_dir, yellow_val_count=15):
    """
    Sorts files per class:
    - Indices 0..49: White pad
    - Indices 50..99: Yellow pad
    Splits so Validation strictly evaluates on Yellow pads (Indices 100-val_count..99).
    """
    train_paths, train_labels = [], []
    val_paths, val_labels = [], []
    
    class_names = sorted([d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))])
    class_to_idx = {cls_name: i for i, cls_name in enumerate(class_names)}

    for cls_name in class_names:
        cls_dir = os.path.join(data_dir, cls_name)
        # Sort files alphabetically to respect the 0..49 (white) and 50..99 (yellow) ordering
        files = sorted(glob.glob(os.path.join(cls_dir, "*")))
        
        if len(files) < 100:
            print(f"Warning: {cls_name} has {len(files)} files (expected 100).")

        # Split yellow pad images into train and validation
        train_files = files[:-yellow_val_count]
        val_files = files[-yellow_val_count:] # Last N images (Yellow pad only)

        idx = class_to_idx[cls_name]
        
        train_paths.extend(train_files)
        train_labels.extend([idx] * len(train_files))
        
        val_paths.extend(val_files)
        val_labels.extend([idx] * len(val_files))

    return train_paths, train_labels, val_paths, val_labels, class_to_idx

# ==========================================
# 2. MODEL ARCHITECTURE (DINOv2)
# ==========================================
class DINOv2ChessClassifier(nn.Module):
    def __init__(self, num_classes=12):
        super().__init__()
        # Load pre-trained DINOv2-Base backbone
        self.backbone = torch.hub.load('facebookresearch/dinov2', 'dinov2_vitb14')
        
        # Linear classification head
        in_features = self.backbone.embed_dim
        self.head = nn.Sequential(
            nn.Linear(in_features, 256),
            nn.GELU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        features = self.backbone(x)
        return self.head(features)

# ==========================================
# 3. TRAINING PIPELINE
# ==========================================
def main():
    DATA_DIR = "/home/checkmate/Documents/chess-bot/zed_platform_images_cropped"  # Replace with path to your dataset root directory
    BATCH_SIZE = 16
    EPOCHS = 25
    LR_BACKBONE = 1e-5
    LR_HEAD = 1e-3
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print(f"Using device: {DEVICE}")

    # Transforms: Grayscale strips background color dependence; CLAHE-like contrast boost
    train_transform = transforms.Compose([
        transforms.Grayscale(num_output_channels=3),
        transforms.Resize((224, 224)),  # Resized to match DINOv2 patch grid
        transforms.RandomRotation(degrees=12),
        transforms.ColorJitter(brightness=0.3, contrast=0.3),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    val_transform = transforms.Compose([
        transforms.Grayscale(num_output_channels=3),
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    train_paths, train_labels, val_paths, val_labels, class_to_idx = prepare_data_splits(DATA_DIR)
    
    train_dataset = StructuredChessDataset(train_paths, train_labels, transform=train_transform)
    val_dataset = StructuredChessDataset(val_paths, val_labels, transform=val_transform)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=2)

    model = DINOv2ChessClassifier(num_classes=len(class_to_idx)).to(DEVICE)

    # Differential learning rates: slow for backbone, faster for classifier head
    optimizer = torch.optim.AdamW([
        {'params': model.backbone.parameters(), 'lr': LR_BACKBONE},
        {'params': model.head.parameters(), 'lr': LR_HEAD}
    ], weight_decay=1e-2)

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.CrossEntropyLoss()
    scaler = torch.cuda.amp.GradScaler()

    best_acc = 0.0

    for epoch in range(EPOCHS):
        model.train()
        train_loss, train_correct = 0.0, 0
        
        for images, labels in train_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()

            with torch.cuda.amp.autocast():
                outputs = model(images)
                loss = criterion(outputs, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            train_loss += loss.item() * images.size(0)
            train_correct += (outputs.argmax(1) == labels).sum().item()

        scheduler.step()
        train_acc = train_correct / len(train_dataset)

        # Validation evaluation
        model.eval()
        val_loss, val_correct = 0.0, 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(DEVICE), labels.to(DEVICE)
                with torch.cuda.amp.autocast():
                    outputs = model(images)
                    loss = criterion(outputs, labels)

                val_loss += loss.item() * images.size(0)
                val_correct += (outputs.argmax(1) == labels).sum().item()

        val_acc = val_correct / len(val_dataset)

        print(f"Epoch {epoch+1:02d}/{EPOCHS} | "
              f"Train Loss: {train_loss/len(train_dataset):.4f} | Train Acc: {train_acc:.4f} | "
              f"Val Loss: {val_loss/len(val_dataset):.4f} | Val Acc: {val_acc:.4f}")

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), "best_chess_classifier.pth")

    print(f"\nTraining Complete. Best Yellow-Pad Validation Accuracy: {best_acc*100:.2f}%")

if __name__ == "__main__":
    main()