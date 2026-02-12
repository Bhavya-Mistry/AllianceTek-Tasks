# root/utils/vision.py
import cv2
import numpy as np
import pytesseract
from icecream import ic
from core.logger import ChessLogger
import os

logger = ChessLogger()


# def is_game_over_ocr(full_img):
#     """
#     Checks the right sidebar for text indicating the game ended.
#     Includes Upscaling + Inversion + Header Cropping.
#     """
#     h, w = full_img.shape[:2]

#     # --- 1. DEFINE ROI (Right Sidebar Only) ---
#     # sidebar_x: Start at 25% width (As per your test configuration)
#     # sidebar_y: Start at 60px (SKIPS the Xephyr/Fluxbox Title Bar!)
#     sidebar_x = int(w * 0.25)
#     sidebar_y = 60

#     sidebar = full_img[sidebar_y:h, sidebar_x:w]

#     # --- 2. UPSCALING (CRITICAL FIX) ---
#     # Make the image 3x bigger. Tesseract struggles with small UI text.
#     # This makes "New 10 min" huge and readable.
#     sidebar = cv2.resize(sidebar, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

#     # --- 3. PRE-PROCESSING ---
#     gray = cv2.cvtColor(sidebar, cv2.COLOR_BGR2GRAY)

#     # INVERSION (CRITICAL FIX):
#     # Chess.com is dark (White Text / Black BG).
#     # Tesseract wants Light (Black Text / White BG).
#     # This flips the colors.
#     gray = cv2.bitwise_not(gray)

#     # Threshold: Clean up noise to make it pure Black & White
#     _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

#     # --- DEBUG: SAVE VIEW ---
#     # cv2.imwrite("debug_ocr_view.png", binary)
#     # print("[DEBUG] Saved 'debug_ocr_view.png'")

#     # --- 4. KEYWORD SEARCH ---
#     try:
#         # Get text
#         text = pytesseract.image_to_string(binary, config="--psm 6").lower()

#     except Exception as e:
#         ic("ERROR: OCR crashed", e)

#         logger.log(event="ERROR", message=f"OCR crashed, {e}")

#         return False

#     # Updated comprehensive keyword list
#     keywords = [
#         "review",
#         "rematch",
#         "game over",
#         # "won",
#         # "lost",
#         # "draw",
#         "aborted",
#     ]

#     for word in keywords:
#         if word in text:
#             ic(f"SUCCESS: Found keyword", word)

#             logger.log(event="OCR", message=f"OCR success, found keyword : {word}")

#             return True

#     return False


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
    x_end = int(w * 0.95)

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

    # cv2.imwrite("debug_roi_visualization.png", debug_viz)
    # print(
    #     f"[DEBUG] Saved visual guide to: {os.path.abspath('debug_roi_visualization.png')}"
    # )

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
        # print(f"[DEBUG] Raw Text Found: '{clean_text}'")
    except Exception as e:
        ic("ERROR: OCR crashed", e)
        return False

    keywords = ["game review", "game aborted", "checkmate", "best", "excellent"]

    for word in keywords:
        if word in text:
            ic("SUCCESS: Found keyword", word)

            logger.log(
                event="VISION",
                message=f"Game Over, Keyword Detected via OCR: {word}",
            )
            return True

    return False


def get_ui_element(detections, name):
    """
    Finds a specific UI element by name in the detection list.
    Returns the center (x, y) if found, else None.
    """
    for item in detections:
        if item["name"] == name:
            return item["center"]
    return None


def get_board_state_from_yolo(yolo_handler, board_img, house_dict, conf=0.5):
    # Run inference with DYNAMIC confidence
    results = yolo_handler.piece_model(board_img, imgsz=640, conf=conf, verbose=False)
    result = results[0]

    board_state = {sq: None for sq in house_dict}

    # Temp dictionary to store best detections per square
    # Format: { 'E2': {'name': 'pawn', 'conf': 0.8} }
    temp_state = {}

    for box in result.boxes:
        cls_id = int(box.cls[0])
        name = result.names[cls_id]
        confidence = float(box.conf[0])

        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
        px, py = (x1 + x2) // 2, (y1 + y2) // 2

        # Find which square contains this center
        for sq, (hx1, hy1, hx2, hy2) in house_dict.items():
            if hx1 <= px <= hx2 and hy1 <= py <= hy2:
                # If multiple pieces detected on one square, keep the highest confidence one
                if sq in temp_state:
                    if confidence > temp_state[sq]["conf"]:
                        temp_state[sq] = {"name": name, "conf": confidence}
                else:
                    temp_state[sq] = {"name": name, "conf": confidence}
                break

    # Finalize the board state
    for sq, data in temp_state.items():
        board_state[sq] = data["name"]

    return board_state


def square_center(bbox):
    x1, y1, x2, y2 = bbox
    return (x1 + x2) // 2, (y1 + y2) // 2


def board_state_to_fen(board_state, side):
    files = ["A", "B", "C", "D", "E", "F", "G", "H"]
    fen_rows = []

    for rank in range(8, 0, -1):
        empty = 0
        row = ""

        for file in files:
            sq = f"{file}{rank}"
            piece = board_state.get(sq)

            if piece is None:
                empty += 1
            else:
                if empty:
                    row += str(empty)
                    empty = 0

                # 1. Normalize the string: lowercase and standard separators
                # This handles "White Pawn", "white-pawn", "white_pawn"
                clean_name = piece.lower().replace(" ", "_").replace("-", "_")

                parts = clean_name.split("_")

                # 2. Extract Color and Name safely
                if len(parts) >= 2:
                    # Standard case: "white_pawn" -> ["white", "pawn"]
                    # We look for 'white' or 'black' to be sure which part is which
                    if "white" in parts:
                        color = "white"
                        name = [p for p in parts if p != "white"][0]
                    elif "black" in parts:
                        color = "black"
                        name = [p for p in parts if p != "black"][0]
                    else:
                        # Fallback if no color keyword found (e.g. "player_pawn")
                        color = parts[0]
                        name = parts[1]
                else:
                    ic("ERROR: Defaulting to White Pawn", piece)

                    logger.log(
                        event="ERROR",
                        message=f"Could not parse piece name: {piece}, defaulting to Pawns",
                    )

                    color = "white"
                    name = "pawn"

                # 3. Map to FEN character
                fen_map = {
                    "pawn": "p",
                    "rock": "r",
                    "rook": "r",
                    "knight": "n",
                    "bishop": "b",
                    "queen": "q",
                    "king": "k",
                }

                # Default to 'p' if the name isn't in our map
                ch = fen_map.get(name, "p")

                # Upper case for White, Lower case for Black
                row += ch.upper() if color == "white" else ch

        if empty:
            row += str(empty)

        fen_rows.append(row)

    fen = "/".join(fen_rows)
    fen += " " + ("w" if side == "white" else "b")
    fen += " - - 0 1"
    return fen
