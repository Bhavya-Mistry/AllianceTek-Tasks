import rook_detection

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

from timer_detection import detect_timer_in_screenshot
from king_detection import KingDetector
from playing_side import detect_playing_side
from play_started_detection import detect_play_started
from board_state_detector import detect_board_state, draw_house_boxes
from message_sender import detect_and_send_message
from rematch_handler import wait_for_game_end_and_restart
from human_movement import human_drag
from stockfish import Stockfish

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

# =========================
# STOCKFISH
# =========================
try:
    print(f"[DEBUG] Initializing Stockfish from {STOCKFISH_PATH}")
    stockfish = Stockfish(
        path=STOCKFISH_PATH,
        parameters={
            "Threads": 2,
            "Minimum Thinking Time": 20,
            "Skill Level": 10,
        }
    )
    print("[DEBUG] Stockfish initialized successfully")
except Exception as e:
    print(f"[ERROR] Failed to initialize Stockfish: {e}")
    print(f"[ERROR] Make sure Stockfish is installed at: {STOCKFISH_PATH}")
    sys.exit(1)

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
# MAIN GAME LOOP - CONTINUOUS PLAY
# =========================
print("[Main] Starting continuous chess automation...")
game_number = 0

while True:
    game_number += 1
    print(f"\n{'='*60}")
    print(f"[Main] Starting Game #{game_number}")
    print(f"{'='*60}\n")
    
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
    try:
        print("[DEBUG] Taking screenshot to detect Play button...")
        screen = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)
        
        if not os.path.exists(TEMPLATE_PATH):
            print(f"[ERROR] Template image not found: {TEMPLATE_PATH}")
            sys.exit(1)
        
        template = cv2.imread(TEMPLATE_PATH)
        if template is None:
            print(f"[ERROR] Failed to load template image: {TEMPLATE_PATH}")
            sys.exit(1)
        
        print(f"[DEBUG] Template loaded: {template.shape}")
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        print(f"[Visual AI] Match confidence: {max_val:.2f} (threshold: {CONFIDENCE})")
        
        if max_val < CONFIDENCE:
            print(f"[ERROR] Play button not detected. Confidence {max_val:.2f} < {CONFIDENCE}")
            sys.exit(1)
        
        h, w = template.shape[:2]
        x = (max_loc[0] + w // 2) / RETINA_SCALE
        y = (max_loc[1] + h // 2) / RETINA_SCALE
        
        print(f"[DEBUG] Clicking Play button at ({x:.0f}, {y:.0f})")
        pyautogui.moveTo(x, y, duration=0.5)
        pyautogui.click()
        print("[Main] Game started")
    except Exception as e:
        print(f"[ERROR] Failed to click Play button: {e}")
        traceback.print_exc()
        continue  # Try next game

    # =========================
    # WAIT FOR GAME
    # =========================
    try:
        print("[DEBUG] Waiting for game to start...")
        if not detect_play_started("images/play_detector.png", 0.8, RETINA_SCALE):
            print("[ERROR] Game did not start within expected time")
            continue  # Try next game
        print("[DEBUG] Game confirmed started")
        
        
        
        counter = counter + 1
        print("--------------------------------------")
        print(f"[GAME INFO] Game counter : {counter}")
        print("--------------------------------------")
        
        
        
    except Exception as e:
        print(f"[ERROR] Error detecting game start: {e}")
        traceback.print_exc()
        continue  # Try next game

    # =========================
    # INITIAL BOARD SNAP
    # =========================
    try:
        snap_id = uuid.uuid4().hex
        board_path = os.path.join(
            TEMP_DIR,
            f"board_{uuid.uuid4().hex}.png"
        )
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
    try:
        print("[DEBUG] Initializing king detector...")
        detector = KingDetector()
        print("[DEBUG] Detecting king in bottom half of board...")
        side, king_coords_scaled, king_coords_unscaled, confidence = detector.detect_king_and_side(board_path)
        
        if not side:
            print(f"[ERROR] Failed to detect king in bottom half (confidence: {confidence:.2f})")
            print("[ERROR] Make sure the game board is visible and templates are correct")
            continue  # Try next game
        
        print(f"[DEBUG] King detected - Confidence: {confidence:.2f}")
        print(f"[DEBUG] King coordinates: {king_coords_unscaled}")
        print(f"[Side] Playing as {side.upper()}")
        
    except Exception as e:
        print(f"[ERROR] King detection failed: {e}")
        traceback.print_exc()
        continue  # Try next game

    # =========================
    # ROOK DETECTION → BOARD GRID
    # =========================
    try:
        rook_out = os.path.join(TEMP_DIR, f"board_rooks_{uuid.uuid4().hex}.png")
        print(f"[DEBUG] Running rook detection to map board grid...")
        rook_img_path, house_dict = rook_detection.main(
            board_path,
            out_path=rook_out,
            side=side
        )
        
        if not house_dict:
            print("[ERROR] No squares detected on board")
            continue  # Try next game
        
        print(f"[Board] Squares detected: {len(house_dict)}")
        
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
    except Exception as e:
        print(f"[ERROR] Rook detection failed: {e}")
        traceback.print_exc()
        continue  # Try next game

    # =========================
    # GAME LOOP
    # =========================
    debug_dir = os.path.join("images", "timer_debug")
    os.makedirs(debug_dir, exist_ok=True)
    print(f"[DEBUG] Game loop started. Debug images → {debug_dir}")

    game_ended = False
    try:
        for i in range(1, 9999):
            try:
                snap_path = os.path.join(debug_dir, f"turn_{i}.png")
                screenshot = pyautogui.screenshot()
                screenshot.save(snap_path)

                img = cv2.imread(snap_path)
                if img is None:
                    print(f"[ERROR] Failed to read screenshot at turn {i}")
                    continue

                # Check if game ended
                if wait_for_game_end_and_restart(debug=True):
                    print(f"\n[Main] Game #{game_number} ended. Starting new game...")
                    game_ended = True
                    time.sleep(3)  # Wait for new game to load
                    break

                if not detect_timer_in_screenshot(img, house_dict, side, debug_dir, i):
                    # Not our turn - utilize this time to randomly send marketing messages
                    detect_and_send_message(img, debug=True)
                    continue

                print(f"\n{'='*50}")
                print(f"[Turn {i}] Our move")
                print(f"{'='*50}")

                # =========================
                # READ BOARD
                # =========================
                try:
                    board_state = detect_board_state(img, house_dict, debug=True)
                    print(f"[DEBUG] Board state detected: {len(board_state)} pieces")
                except Exception as e:
                    print(f"[ERROR] Board state detection failed: {e}")
                    continue

                try:
                    fen = board_state_to_fen(board_state, side)
                    print(f"[FEN] {fen}")
                except Exception as e:
                    print(f"[ERROR] FEN conversion failed: {e}")
                    continue

                # Safety check
                if fen.count("k") != 1 or fen.count("K") != 1:
                    print(f"[FEN ERROR] Invalid kings (black: {fen.count('k')}, white: {fen.count('K')}) — skipping")
                    continue

                try:
                    stockfish.set_fen_position(fen)
                    best_move = stockfish.get_best_move()
                    print(f"[Stockfish] Best move: {best_move}")
                except Exception as e:
                    print(f"[ERROR] Stockfish analysis failed: {e}")
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

                    print(f"[MOVE] {from_sq} ({fx}, {fy}) → {to_sq} ({tx}, {ty})")

                    pyautogui.moveTo(fx / RETINA_SCALE, fy / RETINA_SCALE, duration=0.25)
                    pyautogui.mouseDown()
                    time.sleep(0.08)
                    pyautogui.moveTo(tx / RETINA_SCALE, ty / RETINA_SCALE, duration=0.25)
                    pyautogui.mouseUp()

                    print(f"[SUCCESS] Move executed")
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
            print(f"[WARNING] Game #{game_number} ended unexpectedly. Attempting to restart...")
            continue
                
    except KeyboardInterrupt:
        print("\n[INFO] Chess automation interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Game #{game_number} crashed: {e}")
        traceback.print_exc()
        continue  # Try next game

print("\n[INFO] Chess automation ended")
