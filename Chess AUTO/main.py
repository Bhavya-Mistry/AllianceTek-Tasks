# import rook_detection

import pyautogui
import time
import webbrowser
import cv2
import numpy as np
import os
import tempfile
import uuid
import sys
import traceback
import math

# from timer_detection import detect_timer_in_screenshot

# from king_detection import KingDetector
from playing_side import detect_playing_side

####### from play_started_detection import detect_play_started
from board_state_detector import detect_board_state, draw_house_boxes

#######  from message_sender import detect_and_send_message
#######  from rematch_handler import wait_for_game_end_and_restart
# from human_movement import human_drag
from stockfish import Stockfish
from color_detection import is_our_turn_finished


from yolo_handler import YoloHandler

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

import random  # <--- Ensure this is imported

# =========================
# CONFIG
# =========================
# ... (your existing URL, STOCKFISH_PATH etc) ...

# MARKETING CONFIG
MARKETING_MESSAGES = [
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
# try:
#     print(f"[DEBUG] Initializing Stockfish from {STOCKFISH_PATH}")
#     stockfish = Stockfish(
#         path=STOCKFISH_PATH,
#         parameters={
#             "Threads": 2,
#             "Minimum Thinking Time": 20,
#             "Skill Level": 10,
#         },
#     )
#     print("[DEBUG] Stockfish initialized successfully")
#     print(f"[DEBUG] Initializing YOLO...")

#     yolo_handler = YoloHandler(
#         seg_model_path="segmentation_model.pt",
#         piece_model_path="chess_piece_detection_model_kartik.pt",
#         ui_model_path="best_200epoch.pt",
#     )

# except Exception as e:
#     print(f"[ERROR] : {e}")
#     print(
#         f"[ERROR] Make sure Stockfish is installed at: {STOCKFISH_PATH} and YOLO models are in the ROOT DIRECTORY"
#     )
#     sys.exit(1)


# =========================
# STOCKFISH HELPER
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
                "Skill Level": 10,
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
        ui_model_path="best_200epoch.pt",
    )
except Exception as e:
    print(f"[ERROR] YOLO Init failed: {e}")
    sys.exit(1)


# =========================
# HELPERS
# =========================
#####################################################################
def human_move_to(x1, y1, x2, y2, duration=0.5):
    """
    Moves mouse from (x1, y1) to (x2, y2) in a smooth, human-like arc.
    """
    # 1. Create a random "control point" to curve the path
    dist = math.hypot(x2 - x1, y2 - y1)

    # Random offset (10% to 30% of distance)
    offset = dist * random.uniform(0.1, 0.3)

    # Random direction for the curve (left or right)
    if random.choice([True, False]):
        ctrl_x = (x1 + x2) / 2 + offset
        ctrl_y = (y1 + y2) / 2 - offset
    else:
        ctrl_x = (x1 + x2) / 2 - offset
        ctrl_y = (y1 + y2) / 2 + offset

    # 2. Move in steps along the curve
    # Calculate step count based on distance (smoother for long moves)
    steps = max(10, int(dist / 10))

    # Loop
    for i in range(steps + 1):
        t = i / steps

        # Quadratic Bezier Formula
        bx = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * ctrl_x + t**2 * x2
        by = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * ctrl_y + t**2 * y2

        # Move (If mouse is held down before calling this, it will drag)
        pyautogui.moveTo(bx, by)

        # Variable sleep for acceleration/deceleration
        step_duration = duration / steps
        time.sleep(step_duration * random.uniform(0.8, 1.2))


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


# def get_board_state_from_yolo(board_img, house_dict):
#     # Run inference on the cropped board
#     results = yolo_handler.piece_model(board_img, imgsz=640, conf=0.5, verbose=False)
#     result = results[0]

#     board_state = {sq: None for sq in house_dict}

#     for box in result.boxes:
#         # Get piece class and center
#         cls_id = int(box.cls[0])
#         name = result.names[cls_id]
#         x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
#         px, py = (x1 + x2) // 2, (y1 + y2) // 2

#         # Find which square contains this center
#         for sq, (hx1, hy1, hx2, hy2) in house_dict.items():
#             if hx1 <= px <= hx2 and hy1 <= py <= hy2:
#                 board_state[sq] = name
#                 break
#     return board_state


#####################################################################


def square_center(bbox):
    x1, y1, x2, y2 = bbox
    return (x1 + x2) // 2, (y1 + y2) // 2


# def board_state_to_fen(board_state, side):
#     files = ["A", "B", "C", "D", "E", "F", "G", "H"]
#     fen_rows = []

#     for rank in range(8, 0, -1):
#         empty = 0
#         row = ""

#         for file in files:
#             sq = f"{file}{rank}"
#             piece = board_state.get(sq)

#             if piece is None:
#                 empty += 1
#             else:
#                 if empty:
#                     row += str(empty)
#                     empty = 0

#                 color, name = piece.split("_")

#                 fen_map = {
#                     "pawn": "p",
#                     "rock": "r",
#                     "rook": "r",
#                     "knight": "n",
#                     "bishop": "b",
#                     "queen": "q",
#                     "king": "k",
#                 }

#                 ch = fen_map[name]
#                 row += ch.upper() if color == "white" else ch

#         if empty:
#             row += str(empty)

#         fen_rows.append(row)


#     fen = "/".join(fen_rows)
#     fen += " " + ("w" if side == "white" else "b")
#     fen += " - - 0 1"
#     return fen
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

                # --- ROBUST PIECE PARSING ---
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
                    # Edge case: No separator found (e.g. just "pawn" or "rook")
                    # We can't know the color, but we print an error and guess to avoid crash
                    print(
                        f"[FEN WARNING] Could not parse piece name: '{piece}'. Defaulting to White Pawn."
                    )
                    color = "white"
                    name = "pawn"

                # 3. Map to FEN character
                fen_map = {
                    "pawn": "p",
                    "rock": "r",  # Handle common typo in datasets
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
            webbrowser.open(URL)
            print("[DEBUG] Waiting 5 seconds for page to load...")
            time.sleep(5)
            print("[DEBUG] Page load complete")
        except Exception as e:
            print(f"[ERROR] Failed to open website: {e}")
            traceback.print_exc()
            sys.exit(1)

    # =========================
    # CLICK PLAY BUTTON
    # =========================

    # try:
    #     print("[DEBUG] Taking screenshot to detect Play button...")
    #     screen = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)

    #     if not os.path.exists(TEMPLATE_PATH):
    #         print(f"[ERROR] Template image not found: {TEMPLATE_PATH}")
    #         sys.exit(1)

    #     template = cv2.imread(TEMPLATE_PATH)
    #     if template is None:
    #         print(f"[ERROR] Failed to load template image: {TEMPLATE_PATH}")
    #         sys.exit(1)

    #     print(f"[DEBUG] Template loaded: {template.shape}")
    #     result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    #     _, max_val, _, max_loc = cv2.minMaxLoc(result)

    #     print(f"[Visual AI] Match confidence: {max_val:.2f} (threshold: {CONFIDENCE})")

    #     if max_val < CONFIDENCE:
    #         print(
    #             f"[ERROR] Play button not detected. Confidence {max_val:.2f} < {CONFIDENCE}"
    #         )
    #         sys.exit(1)

    #     h, w = template.shape[:2]
    #     x = (max_loc[0] + w // 2) / RETINA_SCALE
    #     y = (max_loc[1] + h // 2) / RETINA_SCALE

    #     print(f"[DEBUG] Clicking Play button at ({x:.0f}, {y:.0f})")
    #     pyautogui.moveTo(x, y, duration=0.5)
    #     pyautogui.click()
    #     print("[Main] Game started")
    # except Exception as e:
    #     print(f"[ERROR] Failed to click Play button: {e}")
    #     traceback.print_exc()
    #     continue  # Try next game

    # =========================
    # WAIT FOR GAME
    # =========================
    # try:
    #     print("[DEBUG] Waiting for game to start...")
    #     if not detect_play_started("images/play_detector.png", 0.8, RETINA_SCALE):
    #         print("[ERROR] Game did not start within expected time")
    #         continue  # Try next game
    #     print("[DEBUG] Game confirmed started")

    #     counter = counter + 1
    #     print("--------------------------------------")
    #     print(f"[GAME INFO] Game counter : {counter}")
    #     print("--------------------------------------")

    # except Exception as e:
    #     print(f"[ERROR] Error detecting game start: {e}")
    #     traceback.print_exc()
    #     continue  # Try next game

    # =========================
    # 1. UI STATE & START GAME
    # =========================
    print("[Main] checking UI state...")
    board_loaded = False

    # Loop until the board is actually loaded and ready to play
    while not board_loaded:
        # Capture screen
        screen = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)

        # Run YOLO UI Detection
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
            print("[UI] Found 'Play' button - clicking...")
            pyautogui.click(play_btn[0] / RETINA_SCALE, play_btn[1] / RETINA_SCALE)
            time.sleep(2)
            break

        # elif new_game_btn:
        #     print("[UI] Found 'New Game' button - clicking...")
        #     pyautogui.click(
        #         new_game_btn[0] / RETINA_SCALE, new_game_btn[1] / RETINA_SCALE
        #     )
        #     time.sleep(3)  # Wait for animation

        else:
            # Nothing found, wait a bit
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

    # =========================
    # KING DETECTION & SIDE DETERMINATION
    # =========================
    # try:
    #     print("[DEBUG] Initializing king detector...")
    #     detector = KingDetector()
    #     print("[DEBUG] Detecting king in bottom half of board...")
    #     side, king_coords_scaled, king_coords_unscaled, confidence = (
    #         detector.detect_king_and_side(board_path)
    #     )

    #     if not side:
    #         print(
    #             f"[ERROR] Failed to detect king in bottom half (confidence: {confidence:.2f})"
    #         )
    #         print(
    #             "[ERROR] Make sure the game board is visible and templates are correct"
    #         )
    #         continue  # Try next game

    #     print(f"[DEBUG] King detected - Confidence: {confidence:.2f}")
    #     print(f"[DEBUG] King coordinates: {king_coords_unscaled}")
    #     print(f"[Side] Playing as {side.upper()}")

    # except Exception as e:
    #     print(f"[ERROR] King detection failed: {e}")
    #     traceback.print_exc()
    #     continue  # Try next game

    # # =========================
    # # ROOK DETECTION → BOARD GRID
    # # =========================
    # try:
    #     rook_out = os.path.join(TEMP_DIR, f"board_rooks_{uuid.uuid4().hex}.png")
    #     print(f"[DEBUG] Running rook detection to map board grid...")
    #     rook_img_path, house_dict = rook_detection.main(
    #         board_path, out_path=rook_out, side=side
    #     )

    #     if not house_dict:
    #         print("[ERROR] No squares detected on board")
    #         continue  # Try next game

    #     print(f"[Board] Squares detected: {len(house_dict)}")

    #     # ==========================
    #     # DEBUG: DRAW HOUSE BOUNDING BOXES
    #     # ==========================
    #     board_img = cv2.imread(board_path)

    #     debug_board_path = os.path.join(
    #         TEMP_DIR, f"debug_houses_{uuid.uuid4().hex}.png"
    #     )

    #     draw_house_boxes(board_img, house_dict, debug_board_path)
    #     print(f"[DEBUG] House bounding boxes saved → {debug_board_path}")
    # except Exception as e:
    #     print(f"[ERROR] Rook detection failed: {e}")
    #     traceback.print_exc()
    #     continue  # Try next game

    # =========================
    # YOLO BOARD SETUP
    # =========================
    # try:
    #     print("[YOLO] Analyzing board setup...")
    #     # 1. Capture Full Screen
    #     snap_path = os.path.join(TEMP_DIR, f"setup_{uuid.uuid4().hex}.png")
    #     pyautogui.screenshot().save(snap_path)

    #     # 2. Detect Board (Returns Cropped Image + Offset)
    #     board_img, (offset_x, offset_y) = yolo_handler.get_board_from_screenshot(
    #         snap_path
    #     )
    #     print(f"[YOLO] Board Offset: ({offset_x}, {offset_y})")

    #     # 3. Detect Grid & Side (Using Rooks & Kings from crop)
    #     house_dict, side = yolo_handler.analyze_setup(board_img)

    #     if not house_dict or not side:
    #         print("[ERROR] YOLO failed to map grid/side. Retrying...")
    #         continue

    #     print(f"[Side] Playing as: {side.upper()}")

    # except Exception as e:
    #     print(f"[ERROR] Setup failed: {e}")
    #     traceback.print_exc()
    #     continue

    board_img = None
    offset_x = 0
    offset_y = 0
    house_dict = None
    side = None

    setup_success = False

    print("[YOLO] Analyzing board setup (Max 5 attempts)...")

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
                continue

            # If we get here, everything worked
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

                full_img = cv2.cvtColor(np.array(full_screenshot), cv2.COLOR_RGB2BGR)

                h, w = board_img.shape[:2]
                current_board_crop = full_img[
                    offset_y : offset_y + h, offset_x : offset_x + w
                ]

                img = cv2.imread(snap_path)
                if img is None:
                    print(f"[ERROR] Failed to read screenshot at turn {i}")
                    continue

                #####################################################################################################
                # Check if game ended
                # if wait_for_game_end_and_restart(debug=True):
                #     print(f"\n[Main] Game #{game_number} ended. Starting new game...")
                #     game_ended = True
                #     time.sleep(3)  # Wait for new game to load
                #     break
                # =========================
                # CHECK GAME OVER / REMATCH
                # =========================
                # We scan UI again to see if game ended (New Game button or Review appeared)
                ui_scan = yolo_handler.detect_ui_elements(full_img)

                detected_names = [d["name"] for d in ui_scan]
                if detected_names:
                    print(f"[DEBUG UI] Detected elements: {detected_names}")

                new_game_btn = get_ui_element(ui_scan, "new_game")
                game_review_btn = get_ui_element(ui_scan, "game_review")

                if game_review_btn:
                    print(
                        f"\n[Main] Game #{game_number} finished (Game Review detected)."
                    )

                    # Now that we KNOW the game is over, we check for "New Game" to click it
                    if new_game_btn:
                        print(
                            "[UI] Game confirmed over. Clicking 'New Game' immediately..."
                        )
                        pyautogui.click(
                            new_game_btn[0] / RETINA_SCALE,
                            new_game_btn[1] / RETINA_SCALE,
                        )
                        # Wait a moment for the click to register and UI to react
                        time.sleep(2)

                    game_ended = True
                    break

                # if new_game_btn or game_review_btn:
                #     print(f"\n[Main] Game #{game_number} finished (UI detected).")

                #     if new_game_btn:
                #         print("[UI] Clicking 'New Game' immediately...")
                #         pyautogui.click(
                #             new_game_btn[0] / RETINA_SCALE,
                #             new_game_btn[1] / RETINA_SCALE,
                #         )

                #     game_ended = True
                #     time.sleep(3)
                #     break  # Break the turn loop to start new game loop
                #####################################################################################################
                board_offset = (offset_x, offset_y)

                #####################################################################################################
                # if not detect_timer_in_screenshot(
                #     full_img, house_dict, side, board_offset, debug_dir, i
                # ):
                # if is_our_turn_finished(full_img, last_move_coordinates):

                #     # Returns True if our last move is still highlighted -> Opponent hasn't moved yet.
                #     # utilize this time to randomly send marketing messages
                #     # detect_and_send_message(full_img)
                #     pass
                #     continue
                #     # if not detect_timer_in_screenshot(
                #     #     current_board_crop, house_dict, side, debug_dir, i
                #     # ):
                #     # if not detect_timer_in_screenshot(
                #     #     full_img, house_dict, side, debug_dir, i
                #     # ):
                #     # Not our turn - utilize this time to randomly send marketing messages
                #     # detect_and_send_message(img, debug=True)
                #     # continue

                if is_our_turn_finished(full_img, last_move_coordinates):
                    # It is the opponent's turn (our last move is still highlighted)

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
                        msg = random.choice(MARKETING_MESSAGES)
                        print(f"[UI] Sending: '{msg}'")
                        pyautogui.typewrite(msg, interval=0.05)
                        pyautogui.press("enter")

                        # Wait a bit to ensure we don't spam multiple times in one turn
                        time.sleep(2)

                    continue
                #####################################################################################################
                print(f"\n{'=' * 50}")
                print(f"[Turn {i}] Our move")
                print(f"{'=' * 50}")

                # =========================
                # READ BOARD
                # =========================
                try:
                    # ATTEMPT 1: High Confidence (Normal Play)
                    # We start strict (0.5) to avoid detecting ghost pieces.
                    board_state = get_board_state_from_yolo(
                        current_board_crop, house_dict, conf=0.7
                    )
                    fen = board_state_to_fen(board_state, side)

                    # CHECK: Are Kings valid?
                    if fen.count("k") != 1 or fen.count("K") != 1:
                        # ATTEMPT 2: Low Confidence (The "Squint" method)
                        # If a king is missing, lower threshold to 0.15 to find obscured pieces.
                        print(
                            f"[Warning] Invalid Kings (w:{fen.count('K')}, b:{fen.count('k')}). Retrying with low confidence..."
                        )

                        board_state = get_board_state_from_yolo(
                            current_board_crop, house_dict, conf=0.1
                        )
                        fen = board_state_to_fen(board_state, side)

                    # FINAL CHECK
                    if fen.count("k") != 1 or fen.count("K") != 1:
                        # If we still fail, the board is likely covered by a "Game Over" popup.
                        # Force a check for the "New Game" button right now.
                        print(f"[FEN ERROR] Invalid Kings")
                        continue

                        # ui_scan_force = yolo_handler.detect_ui_elements(full_img)
                        # new_game_btn = get_ui_element(ui_scan_force, "new_game")
                        # print("[Error] Invalid Kings.")
                        # if new_game_btn:
                        #     print("[UI] Fallback: Found 'New Game' button! Clicking...")
                        #     pyautogui.click(
                        #         new_game_btn[0] / RETINA_SCALE,
                        #         new_game_btn[1] / RETINA_SCALE,
                        #     )
                        #     game_ended = True
                        #     time.sleep(3)
                        #     break  # Break the turn loop to restart the game
                        # else:
                        #     print("[Error] Invalid Kings.")
                        #     continue

                    # Calculate ACTUAL piece count (fix for the "64 pieces" debug log)
                    piece_count = sum(1 for v in board_state.values() if v is not None)
                    print(f"[DEBUG] Board state detected: {piece_count} pieces")
                    print(f"[FEN] {fen}")

                except Exception as e:
                    print(f"[ERROR] Board processing failed: {e}")
                    traceback.print_exc()
                    continue
                # try:
                #     # board_state = detect_board_state(img, house_dict, debug=True)
                #     board_state = get_board_state_from_yolo(
                #         current_board_crop, house_dict
                #     )
                #     print(f"[DEBUG] Board state detected: {len(board_state)} pieces")
                # except Exception as e:
                #     print(f"[ERROR] Board state detection failed: {e}")
                #     continue

                # try:
                #     fen = board_state_to_fen(board_state, side)
                #     print(f"[FEN] {fen}")
                # except Exception as e:
                #     print(f"[ERROR] FEN conversion failed: {e}")
                #     continue

                # # Safety check
                # if fen.count("k") != 1 or fen.count("K") != 1:
                #     print(
                #         f"[FEN ERROR] Invalid kings (black: {fen.count('k')}, white: {fen.count('K')}) — skipping"
                #     )
                #     continue
                #####################################################################################
                # try:
                #     stockfish.set_fen_position(fen)
                #     best_move = stockfish.get_best_move()
                #     print(f"[Stockfish] Best move: {best_move}")
                # except Exception as e:
                #     print(f"[ERROR] Stockfish analysis failed: {e}")
                #     continue
                try:
                    stockfish.set_fen_position(fen)
                    best_move = stockfish.get_best_move()
                    print(f"[Stockfish] Best move: {best_move}")

                except Exception as e:
                    print(f"[ERROR] Stockfish crashed: {e}")
                    # =========================
                # STOCKFISH CALCULATION (With Crash Prevention)
                # =========================

                # 1. Pre-Check: is_fen_valid() prevents sending garbage to the engine.
                # If the FEN is illegal (e.g. kings touching, active side in check), we skip it.
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

                        # 3. CRITICAL CHANGE: DO NOT RETRY!
                        # The current FEN caused the crash. If we retry now, it will just crash again.
                        # We use 'continue' to skip this frame and force a new screenshot.
                        print(
                            "[Stockfish] Restart successful. Skipping bad frame to prevent infinite loop."
                        )
                        time.sleep(0.5)
                        continue

                    except Exception as e2:
                        print(f"[CRITICAL] Restart failed: {e2}")
                        time.sleep(1)
                        continue
                #####################################################################################

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
                    f_box = house_dict[from_sq]  # (x1, y1, x2, y2)
                    t_box = house_dict[to_sq]

                    # Safe point: Top-Left + 10 pixels
                    safe_fx, safe_fy = f_box[0] + 10, f_box[1] + 10
                    safe_tx, safe_ty = t_box[0] + 10, t_box[1] + 10

                    # --- 2. CONVERT TO GLOBAL SCREEN COORDS ---
                    global_safe_fx = safe_fx + offset_x
                    global_safe_fy = safe_fy + offset_y
                    global_safe_tx = safe_tx + offset_x
                    global_safe_ty = safe_ty + offset_y

                    # For the MOUSE, we still use the CENTER (screen_fx/fy)
                    screen_fx = fx + offset_x
                    screen_fy = fy + offset_y
                    screen_tx = tx + offset_x
                    screen_ty = ty + offset_y

                    # Move mouse (Use CENTER)
                    # pyautogui.moveTo(screen_fx / RETINA_SCALE, screen_fy / RETINA_SCALE)
                    # pyautogui.dragTo(
                    #     screen_tx / RETINA_SCALE,
                    #     screen_ty / RETINA_SCALE,
                    #     button="left",
                    #     duration=0.1,
                    # )
                    ################################
                    # HUMAN MOUSE
                    ################################
                    # NEW HUMAN-LIKE CODE
                    start_x = screen_fx / RETINA_SCALE
                    start_y = screen_fy / RETINA_SCALE
                    end_x = screen_tx / RETINA_SCALE
                    end_y = screen_ty / RETINA_SCALE

                    # 1. Hover over the start piece first (Natural pause)
                    pyautogui.moveTo(start_x, start_y)
                    time.sleep(random.uniform(0.05, 0.15))

                    # 2. Grab the piece
                    pyautogui.mouseDown()

                    # 3. Drag with the curve function
                    human_move_to(
                        start_x,
                        start_y,
                        end_x,
                        end_y,
                        duration=random.uniform(0.3, 0.6),
                    )

                    # 4. Release piece
                    pyautogui.mouseUp()

                    # Save SAFE CORNERS for the check
                    last_move_coordinates = (
                        (global_safe_fx, global_safe_fy),
                        (global_safe_tx, global_safe_ty),
                    )

                    # # ADD OFFSET FOR SCREEN COORDINATES
                    # screen_fx = fx + offset_x
                    # screen_fy = fy + offset_y
                    # screen_tx = tx + offset_x
                    # screen_ty = ty + offset_y

                    # # Move mouse
                    # pyautogui.moveTo(screen_fx / RETINA_SCALE, screen_fy / RETINA_SCALE)
                    # pyautogui.dragTo(
                    #     screen_tx / RETINA_SCALE,
                    #     screen_ty / RETINA_SCALE,
                    #     button="left",
                    #     duration=0.1,
                    # )

                    # last_move_coordinates = (
                    #     (screen_fx, screen_fy),
                    #     (screen_tx, screen_ty),
                    # )

                    print(f"[SUCCESS] Move executed")

                    # Wait 1-2 seconds so the "Game Review" popup has time to appear
                    # before we take the next screenshot.
                    # time.sleep(random.uniform(1.5, 2.5))
                    time.sleep(0.7)
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

print("\n[INFO] Chess automation ended")
