import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
import os
import time

# =========================
# CONFIG
# =========================
DATA_DIR = "dataset_built"
MODEL_SAVE_PATH = r"CNN\chess_model.pth"
EPOCHS = 15
BATCH_SIZE = 32
LEARNING_RATE = 0.001
IMG_SIZE = 73  # Small input for speed

# Check device (GPU is faster, but CPU is fine for this tiny model)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[System] Training on: {device}")

# =========================
# 1. DEFINE THE MODEL
# =========================
class SimpleChessNet(nn.Module):
    def __init__(self, num_classes=13):
        super(SimpleChessNet, self).__init__()
        
        # Feature Extractor (Convolutional Layers)
        self.features = nn.Sequential(
            # Layer 1
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2), # 64x64 -> 32x32
            
            # Layer 2
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2), # 32x32 -> 16x16
            
            # Layer 3
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)  # 16x16 -> 8x8
        )
        
        # Classifier (Dense Layers)
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(5184, 128),
            nn.ReLU(),
            nn.Dropout(0.5), # Prevents memorization
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

# =========================
# 2. DATA LOADERS & AUGMENTATION
# =========================
def get_data_loaders():
    # Training transforms (add randomness to make brain robust)
    train_transforms = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        # Randomly change brightness/color slightly to simulate different screens
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # Validation transforms (No randomness, just resize)
    val_transforms = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    train_data = datasets.ImageFolder(os.path.join(DATA_DIR, 'train'), transform=train_transforms)
    val_data = datasets.ImageFolder(os.path.join(DATA_DIR, 'val'), transform=val_transforms)

    train_loader = torch.utils.data.DataLoader(train_data, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = torch.utils.data.DataLoader(val_data, batch_size=BATCH_SIZE, shuffle=False)
    
    return train_loader, val_loader, train_data.classes

# =========================
# 3. TRAINING LOOP
# =========================
def train():
    if not os.path.exists(DATA_DIR):
        print(f"[Error] Dataset not found at {DATA_DIR}. Run split_data.py first!")
        return

    train_loader, val_loader, class_names = get_data_loaders()
    print(f"[Data] Classes: {class_names}")
    
    model = SimpleChessNet(num_classes=len(class_names)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    print("\n[Start] Training started...")
    start_time = time.time()

    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        # Training Phase
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

        train_acc = 100 * correct / total
        
        # Validation Phase
        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                _, predicted = torch.max(outputs.data, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
        
        val_acc = 100 * val_correct / val_total
        
        print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {running_loss/len(train_loader):.4f} | Train Acc: {train_acc:.1f}% | Val Acc: {val_acc:.1f}%")

    # =========================
    # 4. SAVE MODEL
    # =========================
    print(f"\n[Done] Training finished in {time.time() - start_time:.1f}s")
    
    # Save Model Weights + Class Mappings (Vital for loading later!)
    torch.save({
        'model_state_dict': model.state_dict(),
        'class_map': class_names
    }, MODEL_SAVE_PATH)
    
    print(f"[Saved] Model saved to: {MODEL_SAVE_PATH}")

if __name__ == "__main__":
    train()