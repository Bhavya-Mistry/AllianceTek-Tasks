import torch
import torch.nn as nn
import cv2
import numpy as np
from torchvision import transforms

# ====================================================
# 1. PASTE YOUR NETWORK CLASS HERE
# (It must match train.py EXACTLY)
# ====================================================
class SimpleChessNet(nn.Module):
    def __init__(self, num_classes=13):
        super(SimpleChessNet, self).__init__()
        # Standard 64x64 configuration
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2), 
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2), 
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2) 
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            # ------------------------------------------------------
            # NOTE: If you changed this to 5184 in train.py, change it here too!
            # If you kept it as 64*8*8 (4096) and changed IMG_SIZE to 64, keep this.
            nn.Linear(5184, 128), 
            # ------------------------------------------------------
            nn.ReLU(),
            nn.Dropout(0.5), 
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

# ====================================================
# 2. THE BOT BRAIN
# ====================================================
class SmartClassifierBot:
    def __init__(self, model_path="CNN/chess_model.pth"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[Classifier] Loading model from {model_path} on {self.device}...")
        
        # Load the checkpoint
        checkpoint = torch.load(model_path, map_location=self.device)
        
        # Load Class Mapping (Saved during training)
        self.classes = checkpoint['class_map']
        print(f"[Classifier] Knowledge loaded: {self.classes}")

        # Initialize Model
        self.model = SimpleChessNet(num_classes=len(self.classes))
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.to(self.device)
        self.model.eval()

        # Preprocessing (Must match validation transforms in train.py)
        # We need to resize to whatever IMG_SIZE you used (likely 64 or 72)
        # We'll assume 64 since that is standard, but adjust 'size' if needed.
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((72, 72)), 
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

    def get_board_state(self, full_screen_img, house_dict):
        """
        Takes a full screenshot, crops 64 squares, batches them, 
        and returns a dictionary of square -> piece_name
        """
        squares = []
        sq_names = []

        # 1. Prepare Batch
        # We iterate through A1...H8 to crop every square
        for sq, box in house_dict.items():
            x1, y1, x2, y2 = box
            
            # Safe crop with boundary checks
            h, w = full_screen_img.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            crop = full_screen_img[y1:y2, x1:x2]
            
            # Skip empty/invalid crops
            if crop.size == 0 or crop.shape[0] < 5 or crop.shape[1] < 5:
                # Handle edge case: if crop failed, assume empty
                # Create a black square placeholder
                crop = np.zeros((64, 64, 3), dtype=np.uint8)

            # Convert BGR (OpenCV) to RGB (PyTorch)
            crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            
            # Apply transforms
            tensor = self.transform(crop)
            squares.append(tensor)
            sq_names.append(sq)

        # 2. Run Inference (Batch of 64)
        if not squares:
            return {}

        batch_tensors = torch.stack(squares).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(batch_tensors)
            _, preds = torch.max(outputs, 1)

        # 3. Map Results
        board_state = {}
        for i, sq_name in enumerate(sq_names):
            class_idx = preds[i].item()
            raw_name = self.classes[class_idx]
            
            # Convert 'empty' class to None for your main logic
            if raw_name == "empty":
                board_state[sq_name] = None
            else:
                board_state[sq_name] = raw_name

        return board_state