import os
import subprocess
from pyvirtualdisplay import Display

# We MUST start the display before importing pyautogui
# otherwise pyautogui locks onto the wrong screen!
print("[Display] Starting virtual display (Headless Mode)...")
display = Display(visible=1, size=(1440, 900), backend="xephyr")
display.start()

# Start Window Manager
print("[Display] Starting Fluxbox Window Manager...")
subprocess.Popen(["fluxbox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# =========================
# 2. NOW IMPORT PYAUTOGUI
# =========================
import pyautogui  # <--- Now it sees the Virtual Display!
import random
import time
import webbrowser
import cv2
import numpy as np
import tempfile
import uuid
import sys
import traceback
import math
from stockfish import Stockfish
from color_detection import is_our_turn_finished
from yolo_handler import YoloHandler
import pytesseract


# =========================
# CONFIG
# =========================
URL = "https://www.chess.com/play/online/new"
TEMPLATE_PATH = "start_game_button.png"
CONFIDENCE = 0.8
RETINA_SCALE = 1


counter = 0

STOCKFISH_PATH = r"/usr/games/stockfish"

TEMP_DIR = tempfile.gettempdir()

# # =========================
# # VIRTUAL DISPLAY SETUP
# # =========================
# print("[Display] Starting virtual display (Headless Mode)...")
# # display = Display(visible=1, size=(1600, 900))
# # visible=1 means "Show me the window"
# # backend="xephyr" tells it to open as a nested window on your desktop
# display = Display(visible=1, size=(1440, 900), backend="xephyr")
# display.start()
# print("[Display] Starting Fluxbox Window Manager...")
# subprocess.Popen(["fluxbox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
# # subprocess.Popen(["fluxbox"])

# # Optional: Check if display is set
# print("DISPLAY =", os.environ.get("DISPLAY"))


# =========================
# CONFIG
# =========================


MESSAGES = [
    "Good luck! 🎯",
    "Nice game so far!",
    "Great moves!",
    "This is intense! 😄",
    "You play well!",
    "Enjoying this match!",
    "Good strategy!",
    "Well played!",
]
MESSAGE_PROBABILITY = 0.20  # 20% chance to send a message


# =========================
# STOCKFISH
# =========================
def load_engine():
    """Helper to load or reload the stockfish engine"""
    print(f"[DEBUG] Loading Stockfish from {STOCKFISH_PATH}...")
    try:
        engine = Stockfish(
            path=STOCKFISH_PATH,
            parameters={
                "Threads": 2,
                "Minimum Thinking Time": 20,
                "Skill Level": 8,
            },
        )
        print("[DEBUG] Stockfish loaded successfully")
        return engine
    except Exception as e:
        print(f"[ERROR] Could not load Stockfish: {e}")
        sys.exit(1)


# Initial Load
stockfish = load_engine()

# Initialize YOLO
print(f"[DEBUG] Initializing YOLO...")
try:
    yolo_handler = YoloHandler(
        seg_model_path="segmentation_model.pt",
        piece_model_path="chess_piece_detection_model_kartik.pt",
        ui_model_path="yolo_model_final.pt",
    )
except Exception as e:
    print(f"[ERROR] YOLO Init failed: {e}")
    sys.exit(1)


# =========================
# HELPERS
# =========================
def is_game_over_ocr(full_img):
    """
    Checks the right sidebar for text indicating the game ended.
    Includes Upscaling + Inversion + Header Cropping.
    """
    h, w = full_img.shape[:2]

    # --- 1. DEFINE ROI (Right Sidebar Only) ---
    # sidebar_x: Start at 25% width (As per your test configuration)
    # sidebar_y: Start at 60px (SKIPS the Xephyr/Fluxbox Title Bar!)
    sidebar_x = int(w * 0.25)
    sidebar_y = 60

    sidebar = full_img[sidebar_y:h, sidebar_x:w]

    # --- 2. UPSCALING (CRITICAL FIX) ---
    # Make the image 3x bigger. Tesseract struggles with small UI text.
    # This makes "New 10 min" huge and readable.
    sidebar = cv2.resize(sidebar, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    # --- 3. PRE-PROCESSING ---
    gray = cv2.cvtColor(sidebar, cv2.COLOR_BGR2GRAY)

    # INVERSION (CRITICAL FIX):
    # Chess.com is dark (White Text / Black BG).
    # Tesseract wants Light (Black Text / White BG).
    # This flips the colors.
    gray = cv2.bitwise_not(gray)

    # Threshold: Clean up noise to make it pure Black & White
    _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    # --- DEBUG: SAVE VIEW (Optional in production) ---
    # cv2.imwrite("debug_ocr_view.png", binary)
    # print("[DEBUG] Saved 'debug_ocr_view.png'")

    # --- 4. KEYWORD SEARCH ---
    try:
        # Get text
        text = pytesseract.image_to_string(binary, config="--psm 6").lower()
        # print(f"[DEBUG] Raw OCR Text: {text}") # Uncomment for debugging
    except Exception as e:
        print(f"[ERROR] OCR crashed: {e}")
        return False

    # Updated comprehensive keyword list
    keywords = [
        "review",
        "rematch",
        "game over",
        # "won",
        # "lost",
        # "draw",
        "aborted",
    ]

    for word in keywords:
        if word in text:
            print(f"[OCR] SUCCESS: Found keyword '{word}'")
            return True

    return False


def human_move_to(x1, y1, x2, y2, duration=0.5):
    """
    Moves mouse from (x1, y1) to (x2, y2) in a smooth, human-like arc.
    """
    # 1. Create a random "control point" to curve the path
    # Deviate the path by 10% to 30% of the distance
    dist = math.hypot(x2 - x1, y2 - y1)
    offset = dist * random.uniform(0.1, 0.3)

    # Random direction for the curve (left or right)
    if random.choice([True, False]):
        ctrl_x = (x1 + x2) / 2 + offset
        ctrl_y = (y1 + y2) / 2 - offset
    else:
        ctrl_x = (x1 + x2) / 2 - offset
        ctrl_y = (y1 + y2) / 2 + offset

    # 2. Move in steps along the curve
    steps = 10  # More steps = smoother curve
    for i in range(steps + 1):
        t = i / steps

        bx = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * ctrl_x + t**2 * x2
        by = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * ctrl_y + t**2 * y2

        pyautogui.moveTo(bx, by)

        # Add tiny random sleep to vary speed (acceleration/deceleration)
        time.sleep(duration / steps * random.uniform(0.8, 1.2))


def get_ui_element(detections, name):
    """
    Finds a specific UI element by name in the detection list.
    Returns the center (x, y) if found, else None.
    """
    for item in detections:
        if item["name"] == name:
            return item["center"]
    return None


def get_board_state_from_yolo(board_img, house_dict, conf=0.5):
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
                    print(
                        f"[FEN WARNING] Could not parse piece name: '{piece}'. Defaulting to White Pawn."
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


# =========================
# MAIN GAME LOOP - CONTINUOUS PLAY
# =========================
print("[Main] Starting continuous chess automation...")
game_number = 0


try:
    while True:
        game_number += 1
        print(f"\n{'=' * 60}")
        print(f"[Main] Starting Game #{game_number}")
        print(f"{'=' * 60}\n")

        # =========================
        # OPEN WEBSITE (first game only)
        # =========================
        if game_number == 1:
            try:
                print(f"[DEBUG] Opening chess.com at {URL}")
                # webbrowser.open(URL)
                # # Use subprocess to launch browser with specific flags to force maximization
                # # (Replace 'google-chrome' with 'chromium-browser' or 'firefox' if needed)
                print(f"[DEBUG] Opening {URL}...")
                subprocess.Popen(
                    [
                        "google-chrome",
                        "--kiosk",  # <--- CRITICAL CHANGE: Removes all borders/bars
                        "--no-first-run",
                        "--log-level=3",
                        "--no-default-browser-check",
                        "--window-position=0,0",
                        "--window-size=1440 ,900",
                        "--force-device-scale-factor=1",  # Force standard scaling
                        f"--app={URL}",
                    ],
                    stdout=subprocess.DEVNULL,  # <--- Optional: Add this to silence Chrome terminal output completely
                    stderr=subprocess.DEVNULL,
                )
                print("[DEBUG] Waiting 5 seconds for page to load...")
                time.sleep(5)
                print("[DEBUG] Page load complete")
            except Exception as e:
                print(f"[ERROR] Failed to open website: {e}")
                traceback.print_exc()
                sys.exit(1)

        # =========================
        # 1. UI STATE & START GAME
        # =========================
        print("[Main] checking UI state...")
        board_loaded = False

        # Loop until the board is actually loaded and ready to play
        while not board_loaded:
            # Capture screen
            screen = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)

            # =================================
            cv2.imwrite("debug_what_yolo_sees.png", screen)
            print("[DEBUG] Saved debug_what_yolo_sees.png")
            # ================================

            #  Run YOLO UI Detection
            ui_detections = yolo_handler.detect_ui_elements(screen)

            # Check for specific buttons/states
            play_btn = get_ui_element(ui_detections, "play_button")
            new_game_btn = get_ui_element(ui_detections, "new_game")
            board_state = get_ui_element(ui_detections, "board_loaded")

            # LOGIC
            if board_state:
                print("[UI] Board loaded! Starting game...")
                board_loaded = True
                break

            elif play_btn:
                # --- START DEBUG SECTION -----------------------------------------------------------------------------
                target_x = int(play_btn[0] / RETINA_SCALE)
                target_y = int(play_btn[1] / RETINA_SCALE)

                print(
                    f"[DEBUG] Attempting to click 'Start Game' at: ({target_x}, {target_y})"
                )

                # Draw a bright RED circle where we intend to click
                debug_img = screen.copy()
                cv2.circle(
                    debug_img, (target_x, target_y), 10, (0, 0, 255), -1
                )  # Red filled circle
                cv2.imwrite("debug_click_target.png", debug_img)
                print("[DEBUG] Saved 'debug_click_target.png' - Check this file!")
                # ---------------------------
                print("[UI] Found 'Play' button - clicking...")
                pyautogui.click(play_btn[0] / RETINA_SCALE, play_btn[1] / RETINA_SCALE)
                time.sleep(2)
                # break

            else:
                time.sleep(1)

        counter = counter + 1
        print(f"[GAME INFO] Game counter : {counter}")

        # =========================
        # INITIAL BOARD SNAP
        # =========================
        try:
            snap_id = uuid.uuid4().hex
            board_path = os.path.join(TEMP_DIR, f"board_{uuid.uuid4().hex}.png")
            print(f"[DEBUG] Taking initial board snapshot → {board_path}")
            screenshot = pyautogui.screenshot()
            screenshot.save(board_path)

            if not os.path.exists(board_path):
                print(f"[ERROR] Failed to save initial board snapshot")
                continue  # Try next game
            print(f"[DEBUG] Board snapshot saved successfully")
        except Exception as e:
            print(f"[ERROR] Failed to capture initial board: {e}")
            traceback.print_exc()
            continue  # Try next game

        board_img = None
        offset_x = 0
        offset_y = 0
        house_dict = None
        side = None

        setup_success = False

        print("[YOLO] Analyzing board setup (Max 5 attempts)...")

        time.sleep(2)

        for attempt in range(3):
            try:
                # 1. Capture Full Screen
                snap_path = os.path.join(TEMP_DIR, f"setup_{uuid.uuid4().hex}.png")
                pyautogui.screenshot().save(snap_path)

                # 2. Detect Board
                try:
                    board_img, (offset_x, offset_y) = (
                        yolo_handler.get_board_from_screenshot(snap_path)
                    )
                except RuntimeError:
                    print(
                        f"[Warning] Board detection failed (Attempt {attempt + 1}/5). Retrying in 2s..."
                    )
                    time.sleep(2)
                    continue

                print(f"[YOLO] Board Offset: ({offset_x}, {offset_y})")

                # 3. Detect Grid & Side
                house_dict, side = yolo_handler.analyze_setup(board_img)

                if not house_dict or not side:
                    print(
                        f"[Warning] Grid/Side detection failed (Attempt {attempt + 1}/5). Retrying in 2s..."
                    )
                    time.sleep(2)

                setup_success = True
                break

            except Exception as e:
                print(f"[ERROR] Setup attempt {attempt + 1} crashed: {e}")
                time.sleep(2)

        if not setup_success:
            print(
                "[ERROR] Could not set up board after 5 attempts. Restarting game loop..."
            )
            continue

        print(f"[Side] Playing as: {side.upper()}")

        # =========================
        # GAME LOOP
        # =========================
        debug_dir = os.path.join("images", "timer_debug")
        os.makedirs(debug_dir, exist_ok=True)
        print(f"[DEBUG] Game loop started. Debug images → {debug_dir}")

        game_ended = False
        last_move_coordinates = None
        try:
            for i in range(1, 9999):
                try:
                    snap_path = os.path.join(debug_dir, f"turn_{i}.png")
                    # screenshot = pyautogui.screenshot()
                    # screenshot.save(snap_path)
                    full_screenshot = pyautogui.screenshot()
                    full_screenshot.save(snap_path)

                    full_img = cv2.cvtColor(
                        np.array(full_screenshot), cv2.COLOR_RGB2BGR
                    )

                    h, w = board_img.shape[:2]
                    current_board_crop = full_img[
                        offset_y : offset_y + h, offset_x : offset_x + w
                    ]

                    img = cv2.imread(snap_path)
                    if img is None:
                        print(f"[ERROR] Failed to read screenshot at turn {i}")
                        continue

                    ui_scan = yolo_handler.detect_ui_elements(full_img)

                    detected_names = [d["name"] for d in ui_scan]
                    if detected_names:
                        # print(f"[DEBUG UI] Detected elements: {detected_names}")
                        pass

                    new_game_btn = get_ui_element(ui_scan, "new_game")
                    game_review_btn = get_ui_element(ui_scan, "game_review")
                    aborted_button = get_ui_element(ui_scan, "aborted")

                    if game_review_btn or aborted_button:
                        print(
                            f"\n[Main] Game #{game_number} finished (Game Review or Game Aborted detected)."
                        )
                        game_ended = True

                    elif is_game_over_ocr(full_img):
                        print(
                            f"\n[Main] Game #{game_number} finished (Game Review or Game Aborted (OCR) detected)."
                        )
                        game_ended = True

                    if game_ended:
                        if new_game_btn:
                            print(
                                "[UI] Game confirmed over. Clicking 'New Game' immediately..."
                            )
                            pyautogui.click(
                                new_game_btn[0] / RETINA_SCALE,
                                new_game_btn[1] / RETINA_SCALE,
                            )

                            time.sleep(2)

                        break

                    board_offset = (offset_x, offset_y)

                    if is_our_turn_finished(full_img, last_move_coordinates):
                        # 1. Run YOLO scan to find the "send_message" icon
                        ui_scan = yolo_handler.detect_ui_elements(full_img)
                        msg_icon = get_ui_element(ui_scan, "send_message")

                        # 2. Check probability and if icon exists
                        if msg_icon and random.random() < MESSAGE_PROBABILITY:
                            print(f"[UI] Opportunity to send message detected...")

                            # Click the chat icon
                            pyautogui.click(
                                msg_icon[0] / RETINA_SCALE, msg_icon[1] / RETINA_SCALE
                            )
                            time.sleep(0.2)

                            # Type and send
                            msg = random.choice(MESSAGES)
                            print(f"[UI] Sending: '{msg}'")
                            pyautogui.typewrite(msg, interval=0.05)
                            pyautogui.press("enter")

                            # Wait a bit to ensure we don't spam multiple times in one turn
                            time.sleep(2)

                        continue

                    print(f"\n{'=' * 50}")
                    print(f"[Turn {i}] Our move")
                    print(f"{'=' * 50}")

                    # =========================
                    # READ BOARD
                    # =========================
                    try:
                        board_state = get_board_state_from_yolo(
                            current_board_crop, house_dict, conf=0.7
                        )
                        fen = board_state_to_fen(board_state, side)

                        # CHECK: Are Kings valid?
                        if fen.count("k") != 1 or fen.count("K") != 1:
                            print(
                                f"[Warning] Invalid Kings (w:{fen.count('K')}, b:{fen.count('k')}). Retrying with low confidence..."
                            )

                            board_state = get_board_state_from_yolo(
                                current_board_crop, house_dict, conf=0.1
                            )
                            fen = board_state_to_fen(board_state, side)

                        if fen.count("k") != 1 or fen.count("K") != 1:
                            print(f"[FEN ERROR] Invalid Kings")
                            continue

                        piece_count = sum(
                            1 for v in board_state.values() if v is not None
                        )
                        print(f"[DEBUG] Board state detected: {piece_count} pieces")
                        print(f"[FEN] {fen}")

                    except Exception as e:
                        print(f"[ERROR] Board processing failed: {e}")
                        traceback.print_exc()
                        continue

                    try:
                        stockfish.set_fen_position(fen)
                        best_move = stockfish.get_best_move()
                        print(f"[Stockfish] Best move: {best_move}")

                    except Exception as e:
                        print(f"[ERROR] Stockfish crashed: {e}")

                    # =========================
                    # STOCKFISH CALCULATION
                    # =========================
                    if not stockfish.is_fen_valid(fen):
                        print(f"[Stockfish] Skipping Invalid FEN: {fen}")
                        continue

                    try:
                        stockfish.set_fen_position(fen)
                        best_move = stockfish.get_best_move()
                        print(f"[Stockfish] Best move: {best_move}")

                    except Exception as e:
                        print(f"[ERROR] Stockfish crashed: {e}")
                        print("[Stockfish] Attempting to restart engine...")

                        try:
                            # 1. Kill old instance to free resources
                            del stockfish

                            # 2. Reload the engine
                            stockfish = load_engine()

                            print(
                                "[Stockfish] Restart successful. Skipping bad frame to prevent infinite loop."
                            )
                            time.sleep(0.5)
                            continue

                        except Exception as e2:
                            print(f"[CRITICAL] Restart failed: {e2}")
                            time.sleep(1)
                            continue

                    if not best_move:
                        print("[ERROR] Stockfish returned no move")
                        continue

                    from_sq = best_move[:2].upper()
                    to_sq = best_move[2:4].upper()

                    if from_sq not in house_dict or to_sq not in house_dict:
                        print(f"[ERROR] Invalid squares: {from_sq} → {to_sq}")
                        continue

                    try:
                        fx, fy = square_center(house_dict[from_sq])
                        tx, ty = square_center(house_dict[to_sq])

                        # --- 1. GET SAFE CORNER COORDS (Local Crop) ---
                        # We use the top-left corner of the square + 10px padding
                        # This avoids checking the piece itself (which sits in the center)
                        # f_box = house_dict[from_sq]  # (x1, y1, x2, y2)
                        # t_box = house_dict[to_sq]

                        # # Safe point: Top-Left + 10 pixels
                        # safe_fx, safe_fy = f_box[0] + 10, f_box[1] + 10
                        # safe_tx, safe_ty = t_box[0] + 10, t_box[1] + 10

                        # # --- 2. CONVERT TO GLOBAL SCREEN COORDS ---
                        # global_safe_fx = safe_fx + offset_x
                        # global_safe_fy = safe_fy + offset_y
                        # global_safe_tx = safe_tx + offset_x
                        # global_safe_ty = safe_ty + offset_y

                        # # For the MOUSE, we still use the CENTER (screen_fx/fy)
                        # screen_fx = fx + offset_x
                        # screen_fy = fy + offset_y
                        # screen_tx = tx + offset_x
                        # screen_ty = ty + offset_y

                        # # ===================================
                        # # HUMAN MOUSE
                        # # ===================================

                        # start_x = screen_fx / RETINA_SCALE
                        # start_y = screen_fy / RETINA_SCALE
                        # end_x = screen_tx / RETINA_SCALE
                        # end_y = screen_ty / RETINA_SCALE

                        # --- REPLACEMENT LOGIC FOR COORDINATES ---

                        f_box = house_dict[
                            from_sq
                        ]  # (x1, y1, x2, y2) relative to board crop
                        t_box = house_dict[to_sq]

                        # Calculate square width/height dynamically
                        sq_width = f_box[2] - f_box[0]
                        sq_height = f_box[3] - f_box[1]

                        # Use 15% padding instead of hardcoded 10px
                        # This lands in the top-left corner, but safely inside the square
                        padding_x = sq_width * 0.15
                        padding_y = sq_height * 0.15

                        # 1. Calculate Local Coordinates (Top-Left + Padding)
                        safe_fx = f_box[0] + padding_x
                        safe_fy = f_box[1] + padding_y
                        safe_tx = t_box[0] + padding_x
                        safe_ty = t_box[1] + padding_y

                        # 2. Convert to Global Screen Coordinates
                        # We use these EXACT coords for both clicking AND color detection
                        global_safe_fx = safe_fx + offset_x
                        global_safe_fy = safe_fy + offset_y
                        global_safe_tx = safe_tx + offset_x
                        global_safe_ty = safe_ty + offset_y

                        # 3. Apply Retina Scale (Which is 1 on Ubuntu)
                        start_x = global_safe_fx / RETINA_SCALE
                        start_y = global_safe_fy / RETINA_SCALE
                        end_x = global_safe_tx / RETINA_SCALE
                        end_y = global_safe_ty / RETINA_SCALE

                        # 4. Move Mouse
                        pyautogui.moveTo(start_x, start_y)
                        # ... continue with drag ...

                        # 1. Hover over the start piece first (Natural pause)
                        pyautogui.moveTo(start_x, start_y)
                        time.sleep(random.uniform(0.05, 0.15))

                        # 2. Grab the piece
                        pyautogui.mouseDown()

                        # 3. Drag with the curve function
                        human_move_to(start_x, start_y, end_x, end_y)

                        # 4. Release piece
                        pyautogui.mouseUp()

                        # Save SAFE CORNERS for the check
                        last_move_coordinates = (
                            (global_safe_fx, global_safe_fy),
                            (global_safe_tx, global_safe_ty),
                        )

                        print(f"[SUCCESS] Move executed")

                        # Wait 1-2 seconds so the "Game Review" popup has time to appear
                        time.sleep(1)
                    except Exception as e:
                        print(f"[ERROR] Failed to execute move: {e}")
                        continue

                except KeyboardInterrupt:
                    print("\n[INFO] Game interrupted by user")
                    sys.exit(0)
                except Exception as e:
                    print(f"[ERROR] Turn {i} failed: {e}")
                    traceback.print_exc()
                    continue

            # If we exited the loop without game ending naturally, something went wrong
            if not game_ended:
                print(
                    f"[WARNING] Game #{game_number} ended unexpectedly. Attempting to restart..."
                )
                continue

        except KeyboardInterrupt:
            print("\n[INFO] Chess automation interrupted by user")
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR] Game #{game_number} crashed: {e}")
            traceback.print_exc()
            continue  # Try next game


except KeyboardInterrupt:
    print("\n[INFO] Chess automation interrupted by user")

except Exception as e:
    print(f"[ERROR] Critical failure in main loop: {e}")
    traceback.print_exc()

finally:
    # =========================
    # CLEANUP
    # =========================
    print("[Display] Stopping virtual display...")
    display.stop()
    print("[INFO] Cleanup complete.")
    sys.exit(0)
