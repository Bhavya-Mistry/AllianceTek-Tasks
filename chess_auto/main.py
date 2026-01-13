import rook_detection

import pyautogui
import time
import webbrowser
import cv2
import numpy as np
import os
import tempfile
import uuid

from timer_detection import detect_timer_in_screenshot
from king_detection import KingDetector
from playing_side import detect_playing_side
from play_started_detection import detect_play_started
from board_state_detector import detect_board_state, draw_house_boxes
from stockfish import Stockfish

from human_mouse import move_mouse_humanly

import random, math
# from smart_yolo import SmartYoloBot
from piece_identifier import SmartClassifierBot







import sys
import os
from datetime import datetime

# ... (Your existing imports like cv2, pyautogui, etc. stay here) ...

# ==========================================
# 📝 AUTO-LOGGER (Paste this after imports)
# ==========================================
class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        # Create a "logs" folder if it doesn't exist
        if not os.path.exists("logs"):
            os.makedirs("logs")
        
        # Unique file name based on time
        filename = f"logs/log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.log = open(filename, "a", encoding="utf-8")
        print(f"[Logger] Saving output to: {filename}")

    def write(self, message):
        self.terminal.write(message) # Print to screen
        self.log.write(message)      # Print to file
        self.log.flush()             # Save immediately

    def flush(self):
        self.terminal.flush()
        self.log.flush()

# Redirect Python's output to our Logger
sys.stdout = Logger()
sys.stderr = sys.stdout # Capture crashes/errors too
# ==========================================
















# =========================
# CONFIG
# =========================
URL = "https://www.chess.com/play/online/new"
TEMPLATE_PATH = "start_game_button.png"
CONFIDENCE = 0.8
RETINA_SCALE = 1

STOCKFISH_PATH = r"C:\Users\bhavya.mistry\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"

TEMP_DIR = tempfile.gettempdir()





# =========================
# LOAD GAME OVER TEMPLATES
# =========================
GAME_OVER_PATHS = [
    "images/game_over_1.png",
    "images/game_over_2.png"
]

game_over_templates = []
for p in GAME_OVER_PATHS:
    t = cv2.imread(p)
    if t is not None:
        game_over_templates.append(t)
    else:
        print(f"[WARNING] Could not load template: {p}")

print(f"[System] Loaded {len(game_over_templates)} game-over templates.")













# =========================
# STOCKFISH
# =========================
# stockfish = Stockfish(
#     path=STOCKFISH_PATH,
#     # depth=20,
#     parameters={
#         "Threads": 2,
#         "Minimum Thinking Time": 300,
#         "Skill Level": 5,
#     }
# )

# =========================
# STOCKFISH MANAGER
# =========================
def get_stockfish_engine():
    try:
        engine = Stockfish(
            path=STOCKFISH_PATH,
            depth=20,
            parameters={
                "Threads": 2,
                "Minimum Thinking Time": 3000,
                "Skill Level": 20,
            }
        )
        return engine
    except Exception as e:
        print(f"[Stockfish Error] Could not start engine: {e}")
        return None

# Initialize first instance
stockfish = get_stockfish_engine()
if not stockfish:
    print("[CRITICAL] Stockfish failed to load. Exiting.")
    exit(1)

# =========================
# HELPERS
# =========================
def square_center(bbox):
    x1, y1, x2, y2 = bbox
    return (x1 + x2) // 2, (y1 + y2) // 2


def board_state_to_fen(board_state, side):
    files = ["A","B","C","D","E","F","G","H"]
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

                color, name = piece.split("_")

                fen_map = {
                    "pawn": "p",
                    "rock": "r",
                    "rook": "r",
                    "knight": "n",
                    "bishop": "b",
                    "queen": "q",
                    "king": "k",
                }

                ch = fen_map[name]
                row += ch.upper() if color == "white" else ch

        if empty:
            row += str(empty)

        fen_rows.append(row)

    fen = "/".join(fen_rows)
    fen += " " + ("w" if side == "white" else "b")
    fen += " - - 0 1"
    return fen


# =========================
# OPEN WEBSITE
# =========================
webbrowser.open(URL)
time.sleep(10)

# =========================
# CLICK PLAY BUTTON
# =========================
screen = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)
template = cv2.imread(TEMPLATE_PATH)

result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
_, max_val, _, max_loc = cv2.minMaxLoc(result)

print(f"[Visual AI] Match confidence: {max_val:.2f}")

if max_val < CONFIDENCE:
    print("Play button not detected.")
    exit(1)

h, w = template.shape[:2]
x = (max_loc[0] + w // 2) / RETINA_SCALE
y = (max_loc[1] + h // 2) / RETINA_SCALE

pyautogui.moveTo(x, y, duration=0.5)
pyautogui.click()
print("[Main] Game started")

# =========================
# WAIT FOR GAME
# =========================
if not detect_play_started("images/play_detector.png", 0.8, RETINA_SCALE):
    print("Game did not start")
    exit(1)

# =========================
# INITIAL BOARD SNAP
# =========================
snap_id = uuid.uuid4().hex
board_path = os.path.join(
    TEMP_DIR,
    f"board_{uuid.uuid4().hex}.png"
)
screenshot = pyautogui.screenshot()
screenshot.save(board_path)

# =========================
# KING DETECTION
# =========================
detector = KingDetector(retina_scale=RETINA_SCALE)
_, king_coords, _ = detector.detect_king(board_path)

board_height = cv2.imread(board_path).shape[0]
side = detect_playing_side(king_coords, board_height)

print(f"[Side] Playing as {side}")

# =========================
# ROOK DETECTION → BOARD GRID
# =========================
rook_out = os.path.join(TEMP_DIR, f"board_rooks_{uuid.uuid4().hex}.png")
rook_img_path, house_dict = rook_detection.main(
    board_path,
    out_path=rook_out,
    side=side
)

# ==========================
# DEBUG: DRAW HOUSE BOUNDING BOXES
# ==========================
board_img = cv2.imread(board_path)

debug_board_path = os.path.join(
    TEMP_DIR,
    f"debug_houses_{uuid.uuid4().hex}.png"
)

draw_house_boxes(board_img, house_dict, debug_board_path)

print(f"[DEBUG] House bounding boxes saved → {debug_board_path}")
print(f"[Board] Squares detected: {len(house_dict)}")














# =========================
# INITIALIZE YOLO
# =========================
# Use the model and confidence that gave you 32 pieces in yolo_test2.py
# yolo_bot = SmartYoloBot(model_path="best 2.pt", confidence=0.20)
# yolo_bot = SmartYoloBot(model_path="best 2.pt", confidence=0.20)
classifier_bot = SmartClassifierBot(model_path="CNN/chess_model.pth")




















# =========================
# GAME LOOP
# =========================
debug_dir = os.path.join("images", "timer_debug")
os.makedirs(debug_dir, exist_ok=True)

for i in range(1, 9999):
    snap_path = os.path.join(debug_dir, f"turn_{i}.png")
    screenshot = pyautogui.screenshot()
    screenshot.save(snap_path)

    img = cv2.imread(snap_path)






    # -------------------------------------------------
    game_ended = False
    for temp in game_over_templates:
        res = cv2.matchTemplate(img, temp, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        if max_val > 0.8:  # 80% confidence
            print(f"[Game Over] Detected termination template! (Confidence: {max_val:.2f})")
            game_ended = True
            break
    
    if game_ended:
        print("[System] Exiting game loop.")
        break
    # -------------------------------------------------











    if not detect_timer_in_screenshot(img, house_dict, side, debug_dir, i):
        continue

    print(f"[Turn {i}] Our move")

    # =========================
    # READ BOARD
    # =========================
    # board_state = detect_board_state(img, house_dict, debug=True)
    # board_state = yolo_bot.get_board_state(img, house_dict)
    board_state = classifier_bot.get_board_state(img, house_dict)

    fen = board_state_to_fen(board_state, side)
    print(f"[FEN] {fen}")

    # Safety check
    if fen.count("k") != 1 or fen.count("K") != 1:
        print("[FEN ERROR] Invalid kings — skipping")
        continue
    
    
    # 1. Validate FEN first
    if not stockfish.is_fen_valid(fen):
        print(f"[FEN ERROR] Stockfish says FEN is invalid/impossible: {fen}")
        # This usually happens if CNN hallucinates. 
        # We skip this frame and hope the next screenshot is clearer.
        continue

    try:
        stockfish.set_fen_position(fen)
        
        # 2. Safety check: Is the game actually over?
        # Sometimes visual detection misses "Checkmate", but Stockfish knows.
        eval_info = stockfish.get_evaluation()
        if eval_info["type"] == "mate" and eval_info["value"] == 0:
            print("[Stockfish] Detects Checkmate. Game Over.")
            break

        best_move = stockfish.get_best_move()
    
    except Exception as e:
        print(f"[Stockfish Crash] The engine died! Restarting... Error: {e}")
        # 3. AUTO-RESTART ENGINE
        # This prevents the script from stopping entirely
        del stockfish
        stockfish = get_stockfish_engine()
        continue

    print(f"[Stockfish] {best_move}")

    if not best_move:
        continue
    
    # ... proceed to move logic ...

    from_sq = best_move[:2].upper()
    to_sq = best_move[2:4].upper()

    if from_sq not in house_dict or to_sq not in house_dict:
        print("[MOVE] Invalid squares")
        continue

    fx, fy = square_center(house_dict[from_sq])
    tx, ty = square_center(house_dict[to_sq])

    print(f"[MOVE] {from_sq} → {to_sq}")


    # Calculate screen coordinates
    start_x = fx / RETINA_SCALE
    start_y = fy / RETINA_SCALE
    end_x = tx / RETINA_SCALE
    end_y = ty / RETINA_SCALE

    # 1. THINKING DELAY
    # Randomly wait between 0.5s and 2.0s before moving to simulate reading
    think_time = random.uniform(0.5, 2.0)
    print(f"   (Thinking for {think_time:.2f}s...)")
    time.sleep(think_time)

    # 2. MOVE TO PIECE (The "Pickup")
    # Get current mouse pos and move to start square in a curve
    curr_x, curr_y = pyautogui.position()
    move_mouse_humanly(curr_x, curr_y, start_x, start_y, duration=random.uniform(0.2, 0.4))
    
    pyautogui.mouseDown()
    
    # 3. DRAG PIECE (The "Action")
    # Drag slower and with a curve to the target
    move_mouse_humanly(start_x, start_y, end_x, end_y, duration=random.uniform(0.3, 0.6))
    
    pyautogui.mouseUp()

    # 4. POST-MOVE CHILL
    # Rest for a split second before scanning again
    time.sleep(random.uniform(0.2, 0.5))