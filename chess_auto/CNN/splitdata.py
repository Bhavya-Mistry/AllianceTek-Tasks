import os
import shutil
import random

# =========================
# CONFIG
# =========================
SOURCE_DIR = "dataset_raw"   # Your captured images
DEST_DIR = "dataset_built"   # Where we will save the clean dataset
SPLIT_RATIO = 0.85           # 85% Training, 15% Validation

CLASSES = [
    "white_pawn", "white_knight", "white_bishop", "white_rook", "white_queen", "white_king",
    "black_pawn", "black_knight", "black_bishop", "black_rook", "black_queen", "black_king",
    "empty"
]

def main():
    if os.path.exists(DEST_DIR):
        shutil.rmtree(DEST_DIR)
        
    print(f"[Data] Creating folder structure in '{DEST_DIR}'...")
    for split in ["train", "val"]:
        for cls in CLASSES:
            os.makedirs(os.path.join(DEST_DIR, split, cls), exist_ok=True)

    total_moved = 0
    
    for cls in CLASSES:
        src_path = os.path.join(SOURCE_DIR, cls)
        if not os.path.exists(src_path):
            print(f"   [WARNING] Missing class folder: {cls}")
            continue
            
        files = [f for f in os.listdir(src_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        random.shuffle(files)
        
        # Calculate split
        split_idx = int(len(files) * SPLIT_RATIO)
        train_files = files[:split_idx]
        val_files = files[split_idx:]
        
        # Copy files
        for f in train_files:
            shutil.copy(os.path.join(src_path, f), os.path.join(DEST_DIR, "train", cls, f))
        for f in val_files:
            shutil.copy(os.path.join(src_path, f), os.path.join(DEST_DIR, "val", cls, f))
            
        print(f"   > {cls}: {len(train_files)} train | {len(val_files)} val")
        total_moved += len(files)

    print(f"\n[Done] Organized {total_moved} images. Ready for PyTorch!")

if __name__ == "__main__":
    main()