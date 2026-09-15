import torch
import torch.nn as nn

# 1. Class definition required to reconstruct the PyTorch graph before tracing
class DINOv2ChessClassifier(nn.Module):
    def __init__(self, num_classes=12):
        super().__init__()
        self.backbone = torch.hub.load('facebookresearch/dinov2', 'dinov2_vitb14')
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

def export_standalone_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # 2. Load trained weights into the architecture
    model = DINOv2ChessClassifier(num_classes=12).to(device)
    model.load_state_dict(torch.load("/home/checkmate/Documents/chess-bot/best_chess_classifier.pth", map_location=device))
    model.eval()

    # 3. Trace and save into standalone TorchScript format
    dummy_input = torch.randn(1, 3, 224, 224).to(device)
    traced_model = torch.jit.trace(model, dummy_input)
    traced_model.save("standalone_chess_model.pt")

    print("Successfully exported standalone model to 'standalone_chess_model.pt'")

if __name__ == "__main__":
    export_standalone_model()