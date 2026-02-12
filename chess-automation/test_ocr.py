import cv2
import pytesseract
import numpy as np
import sys
import os
from icecream import ic

# --- CONFIGURATION ---
# Replace this with your image path or use command line
TEST_IMAGE_PATH = "/home/user/Documents/GITHUB/chess-automation/chess-automation/Screenshot_2026-02-05_17-20-34.png"


class MockLogger:
    def log(self, event, message):
        print(f" >> [LOGGER] {event}: {message}")


logger = MockLogger()


def is_game_over_ocr(full_img):
    """
    Checks the MIDDLE PART of the screen for text indicating the game ended.
    Saves a debug image showing exactly which part was selected.
    """
    if full_img is None:
        ic("ERROR: Image is None")
        return False

    h, w = full_img.shape[:2]

    # --- 1. DEFINE ROI (Middle Screen Selection) ---
    # WIDTH: Middle 50%
    x_start = int(w * 0.20)
    x_end = int(w * 0.55)

    # HEIGHT: Start at 60px (skip title bar) to bottom
    y_start = 60
    y_end = h

    # --- VISUALIZATION (NEW STEP) ---
    # Create a copy of the full image to draw the box on
    debug_viz = full_img.copy()

    # Draw a Green Rectangle around the area we are cropping
    # (0, 255, 0) is Green, thickness=5
    cv2.rectangle(debug_viz, (x_start, y_start), (x_end, y_end), (0, 255, 0), 5)

    # Add text label
    cv2.putText(
        debug_viz,
        "OCR SCAN AREA",
        (x_start + 10, y_start + 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
    )

    cv2.imwrite("debug_roi_visualization.png", debug_viz)
    print(
        f"[DEBUG] Saved visual guide to: {os.path.abspath('debug_roi_visualization.png')}"
    )

    # --- 2. CROP & UPSCALING ---
    middle_roi = full_img[y_start:y_end, x_start:x_end]
    middle_roi = cv2.resize(middle_roi, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    # --- 3. PRE-PROCESSING ---
    gray = cv2.cvtColor(middle_roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)  # Invert for Dark Mode
    _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    # Save the raw OCR view
    cv2.imwrite("debug_ocr_view.png", binary)

    # --- 4. KEYWORD SEARCH ---
    try:
        text = pytesseract.image_to_string(binary, config="--psm 6").lower()
        clean_text = text.replace("\n", " ").strip()
        print(f"[DEBUG] Raw Text Found: '{clean_text}'")
    except Exception as e:
        ic("ERROR: OCR crashed", e)
        return False

    keywords = [
        "game over",
        "winner",
        "checkmate",
        "draw",
        "resigned",
        "rematch",
        "review",
        "aborted",
        "won",
        "lost",
    ]

    for word in keywords:
        if word in text:
            ic("SUCCESS: Found keyword", word)
            return True

    return False


# --- MAIN RUNNER ---
if __name__ == "__main__":
    print("--- STARTING VISUAL DEBUG TEST ---")

    # Get image path from config or arguments
    image_path = TEST_IMAGE_PATH
    if not image_path and len(sys.argv) > 1:
        image_path = sys.argv[1]

    if image_path and os.path.exists(image_path):
        print(f"Processing: {image_path}")
        img = cv2.imread(image_path)
        is_game_over_ocr(img)
        print("\n✅ DONE. Open 'debug_roi_visualization.png' to see the Green Box.")
    else:
        print("⚠️ No image found. Generating Dummy...")
        dummy = np.zeros((800, 1200, 3), dtype=np.uint8)
        # Add 'Game Over' in center
        cv2.putText(
            dummy,
            "GAME OVER",
            (450, 400),
            cv2.FONT_HERSHEY_SIMPLEX,
            2,
            (255, 255, 255),
            3,
        )
        is_game_over_ocr(dummy)
        print(
            "\n✅ DONE. Open 'debug_roi_visualization.png' to see the Green Box on dummy image."
        )
