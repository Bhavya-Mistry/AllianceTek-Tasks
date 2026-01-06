import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chess
import chess.engine
import pyautogui
import time
import random
import numpy as np
import sys
import re

# ==========================================
#              CONFIGURATION
# ==========================================

# PASTE YOUR STOCKFISH PATH BELOW (Use forward slashes /)
STOCKFISH_PATH = r"C:\Users\bhavya.mistry\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"  # <--- UPDATE THIS PATH
GAME_URL = "https://www.chess.com/play/computer"

# Calibration: Height of Chrome's top bar
BROWSER_OFFSET_Y = 55

# ==========================================
#           HUMAN MOUSE MOVEMENT
# ==========================================

def get_bezier_path(start, end):
    start_x, start_y = start
    end_x, end_y = end
    control_x = (start_x + end_x) / 2 + random.randint(-200, 200)
    control_y = (start_y + end_y) / 2 + random.randint(-200, 200)
    points = np.linspace(0, 1, num=random.randint(40, 60))
    path = []
    for t in points:
        x = (1-t)**2 * start_x + 2*(1-t)*t * control_x + t**2 * end_x
        y = (1-t)**2 * start_y + 2*(1-t)*t * control_y + t**2 * end_y
        path.append((x, y))
    return path

def move_mouse_smoothly(target_x, target_y):
    start_x, start_y = pyautogui.position()
    path = get_bezier_path((start_x, start_y), (target_x, target_y))
    for x, y in path:
        pyautogui.moveTo(x, y)
        time.sleep(random.uniform(0.0005, 0.002))
    pyautogui.moveTo(target_x, target_y)

def perform_chess_move(start_x, start_y, end_x, end_y):
    move_mouse_smoothly(start_x, start_y)
    time.sleep(random.uniform(0.1, 0.3))
    pyautogui.click()
    move_mouse_smoothly(end_x, end_y)
    time.sleep(random.uniform(0.1, 0.3))
    pyautogui.click()

# ==========================================
#        OPPONENT MOVE DETECTION (NEW)
# ==========================================

def get_last_move_from_highlights(driver, board):
    """
    Scans the DOM for the two highlighted squares (start & end)
    and deduces the move based on legal moves in the current board state.
    """
    # 1. Find all elements with 'highlight' in their class
    # Chess.com uses classes like "highlight square-55"
    squares = driver.find_elements(By.CSS_SELECTOR, "div[class*='highlight']")
    
    if len(squares) < 2:
        return None 

    # 2. Extract the square IDs (e.g. 11, 55, 88)
    # Mapping: square-11 = a1, square-88 = h8
    highlighted_squares = []
    for s in squares:
        class_name = s.get_attribute("class")
        # Regex to find 'square-XX'
        match = re.search(r'square-(\d)(\d)', class_name)
        if match:
            col = int(match.group(1)) # 1-8
            row = int(match.group(2)) # 1-8
            
            # Convert to chess library index (0-63)
            # File: 1->0 (a), 8->7 (h)
            file_idx = col - 1
            # Rank: 1->0 (1), 8->7 (8)
            rank_idx = row - 1
            
            square_idx = chess.square(file_idx, rank_idx)
            highlighted_squares.append(square_idx)

    # 3. We have 2 squares, but don't know which is Start or End.
    # We check the legal moves to see which combination is valid.
    legal_moves = list(board.legal_moves)
    
    # We only care about the last two highlights found (latest move)
    # Sometimes traces of old moves remain, so we take the last 2 in the DOM usually
    current_highlights = highlighted_squares[-2:] 
    
    if len(current_highlights) != 2:
        return None

    sq1 = current_highlights[0]
    sq2 = current_highlights[1]

    # Check if Move(sq1 -> sq2) is legal
    move_1 = chess.Move(sq1, sq2)
    if move_1 in legal_moves:
        return move_1
        
    # Check if Move(sq2 -> sq1) is legal
    move_2 = chess.Move(sq2, sq1)
    if move_2 in legal_moves:
        return move_2
        
    # Edge Case: Promotions (e.g. a7a8q)
    # If it's a promotion, the basic Move(sq1, sq2) won't be in legal_moves
    # because legal_moves includes the promotion piece (a7a8q).
    for move in legal_moves:
        if (move.from_square == sq1 and move.to_square == sq2) or \
           (move.from_square == sq2 and move.to_square == sq1):
            return move

    return None

# ==========================================
#           SCREEN COORDINATE LOGIC
# ==========================================

def get_board_rect(driver):
    try:
        board = driver.find_element(By.TAG_NAME, "chess-board")
    except:
        try:
            board = driver.find_element(By.ID, "board-layout-chessboard")
        except:
            print("ERROR: Could not find the board element on page.")
            sys.exit(1)
    return board.rect

def get_square_center(square_name, board_rect, y_offset):
    square_size = board_rect['width'] / 8
    file_idx = ord(square_name[0]) - ord('a')
    rank_idx = 8 - int(square_name[1])
    rel_x = (file_idx * square_size) + (square_size / 2)
    rel_y = (rank_idx * square_size) + (square_size / 2)
    screen_x = board_rect['x'] + rel_x
    screen_y = board_rect['y'] + rel_y + y_offset
    return screen_x, screen_y

# ==========================================
#               MAIN BOT LOOP
# ==========================================

def run_bot():
    print("--- FULL AUTO CHESS BOT INITIALIZING ---")
    
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    driver.set_window_position(0, 0)
    driver.maximize_window()
    driver.get(GAME_URL)
    
    print("LOG: Browser launched. Please start a game against 'Computer'.")
    input("ACTION: Press ENTER once the board is visible and pieces are set...")
    
    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    except FileNotFoundError:
        print(f"ERROR: Could not find Stockfish at: {STOCKFISH_PATH}")
        driver.quit()
        return

    board = chess.Board()
    board_rect = get_board_rect(driver)
    
    side = input("Are you playing White? (y/n): ").lower()
    bot_color = chess.WHITE if side == 'y' else chess.BLACK
    
    print("\n--- BOT STARTED ---")
    print("To stop, press Ctrl+C.")
    
    try:
        while not board.is_game_over():
            
            # --- BOT TURN ---
            if board.turn == bot_color:
                print("\n[Bot Thinking...]")
                result = engine.play(board, chess.engine.Limit(time=0.5))
                best_move = result.move
                
                start_sq = chess.square_name(best_move.from_square)
                end_sq = chess.square_name(best_move.to_square)
                
                # Check for Promotion (e.g. a7a8q)
                if len(str(best_move)) > 4: 
                    # Simplicity: Just click the square, assume auto-queen is on or handle manually
                    print("NOTE: Promotion detected. Standard logic applied.")

                start_px = get_square_center(start_sq, board_rect, BROWSER_OFFSET_Y)
                end_px = get_square_center(end_sq, board_rect, BROWSER_OFFSET_Y)
                
                print(f"Bot Playing: {start_sq} -> {end_sq}")
                perform_chess_move(start_px[0], start_px[1], end_px[0], end_px[1])
                
                board.push(best_move)
                
                # Move mouse away so we don't block view
                pyautogui.moveRel(200, 0)
                
            # --- OPPONENT TURN ---
            else:
                print("Waiting for opponent...", end="\r")
                start_fen = board.fen()
                
                # Loop until we detect a new move on the board
                while board.fen() == start_fen:
                    detected_move = get_last_move_from_highlights(driver, board)
                    
                    if detected_move:
                        # Found a valid move that matches the highlights
                        print(f"\nOpponent Played: {detected_move}")
                        board.push(detected_move)
                        break
                    
                    time.sleep(0.5) # Poll every 0.5 seconds

        print("Game Over:", board.result())
        print("\n!!! VICTORY !!!")
        input("Press ENTER to close the browser...")

    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"\nError: {e}")
        
    finally:
        engine.quit()
        driver.quit()

if __name__ == "__main__":
    run_bot()