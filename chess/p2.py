import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import chess
import chess.engine
import pyautogui
import time
import random
import numpy as np
import sys

# ==========================================
#              CONFIGURATION
# ==========================================

# PASTE YOUR STOCKFISH PATH BELOW (Use forward slashes /)
# Example: "C:/Users/YourName/Downloads/stockfish/stockfish-windows-x86-64-avx2.exe"

STOCKFISH_PATH = r"C:\Users\bhavya.mistry\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"  # <--- UPDATE THIS PATH
GAME_URL = "https://www.chess.com/play/computer"

# Calibration: Height of Chrome's top bar (URL + Tabs) in pixels.
# If bot clicks too high, INCREASE this. If too low, DECREASE this.
BROWSER_OFFSET_Y = 55

# ==========================================
#           HUMAN MOUSE MOVEMENT
# ==========================================

def get_bezier_path(start, end):
    """Generates a smooth curve of points between start and end."""
    start_x, start_y = start
    end_x, end_y = end
    
    # Randomize control point to create an arc
    # The control point pulls the curve away from a straight line
    control_x = (start_x + end_x) / 2 + random.randint(-200, 200)
    control_y = (start_y + end_y) / 2 + random.randint(-200, 200)
    
    # Generate ~50 points along the curve
    points = np.linspace(0, 1, num=random.randint(40, 60))
    path = []
    
    for t in points:
        # Quadratic Bezier formula
        x = (1-t)**2 * start_x + 2*(1-t)*t * control_x + t**2 * end_x
        y = (1-t)**2 * start_y + 2*(1-t)*t * control_y + t**2 * end_y
        path.append((x, y))
        
    return path

def move_mouse_smoothly(target_x, target_y):
    """Moves mouse from CURRENT position to TARGET position human-like."""
    start_x, start_y = pyautogui.position() # Get current mouse pos
    
    path = get_bezier_path((start_x, start_y), (target_x, target_y))
    
    for x, y in path:
        pyautogui.moveTo(x, y)
        # Variable speed: fast in middle, slow at ends (Fitts's Law)
        time.sleep(random.uniform(0.0005, 0.002))
    
    # Ensure we land exactly on the target
    pyautogui.moveTo(target_x, target_y)

def perform_chess_move(start_x, start_y, end_x, end_y):
    """Full sequence: Approach -> Click -> Drag -> Drop."""
    
    # 1. Approach the source square
    move_mouse_smoothly(start_x, start_y)
    time.sleep(random.uniform(0.1, 0.3)) # Hesitate
    pyautogui.click()
    
    # 2. Move to destination square
    move_mouse_smoothly(end_x, end_y)
    time.sleep(random.uniform(0.1, 0.3)) # Hesitate
    pyautogui.click()

# ==========================================
#           SCREEN COORDINATE LOGIC
# ==========================================

def get_board_rect(driver):
    """Finds the chess board element and returns its location/size."""
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
    """Calculates the physical screen pixel (x,y) for a square (e.g. 'e4')."""
    square_size = board_rect['width'] / 8
    
    # File (column): a=0 ... h=7
    file_idx = ord(square_name[0]) - ord('a')
    
    # Rank (row): 1=7 ... 8=0 (inverted because screen Y grows downwards)
    rank_idx = 8 - int(square_name[1])
    
    # Relative pixels inside the board
    rel_x = (file_idx * square_size) + (square_size / 2)
    rel_y = (rank_idx * square_size) + (square_size / 2)
    
    # Absolute pixels on screen
    # board_rect['x'] is usually 0 inside the viewport, so we rely on window pos if needed
    # but selenium usually gives viewport coordinates.
    screen_x = board_rect['x'] + rel_x
    screen_y = board_rect['y'] + rel_y + y_offset
    
    return screen_x, screen_y

# ==========================================
#               MAIN BOT LOOP
# ==========================================

def run_bot():
    print("--- CHESS BOT INITIALIZING ---")
    
    # 1. Launch Browser
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    driver.set_window_position(0, 0) # Force window to top-left
    driver.maximize_window()
    driver.get(GAME_URL)
    
    print("LOG: Browser launched. Please start a game against 'Computer'.")
    input("ACTION: Press ENTER once the board is visible and pieces are set...")
    
    # 2. Setup Logic
    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    except FileNotFoundError:
        print(f"ERROR: Could not find Stockfish at: {STOCKFISH_PATH}")
        driver.quit()
        return

    board = chess.Board()
    board_rect = get_board_rect(driver)
    
    # Confirm Side
    side = input("Are you playing White? (y/n): ").lower()
    if side != 'y':
        print("NOTE: This script assumes White perspective for coordinates.")
        # If you play black, the board is visually flipped, so math needs inversion.
        # For this test version, please play White.
    
    print("\n--- BOT STARTED ---")
    print("To stop, press Ctrl+C in this terminal.")
    
    try:
        while not board.is_game_over():
            
            if board.turn == chess.WHITE:
                print("\n[Thinking...]")
                # 1. Engine decides move
                result = engine.play(board, chess.engine.Limit(time=1.0)) # 1 sec thinking
                best_move = result.move
                
                # 2. Get Coordinates
                start_sq = chess.square_name(best_move.from_square)
                end_sq = chess.square_name(best_move.to_square)
                
                start_px = get_square_center(start_sq, board_rect, BROWSER_OFFSET_Y)
                end_px = get_square_center(end_sq, board_rect, BROWSER_OFFSET_Y)
                
                print(f"Bot Moving: {start_sq} -> {end_sq}")
                
                # 3. Move Mouse
                perform_chess_move(start_px[0], start_px[1], end_px[0], end_px[1])
                
                # 4. Update internal board
                board.push(best_move)
                
            else:
                # Opponent Turn
                move_str = input("\nENTER OPPONENT MOVE (e.g. e7e5): ")
                
                try:
                    # Validate and push move
                    move = chess.Move.from_uci(move_str)
                    if move in board.legal_moves:
                        board.push(move)
                    else:
                        print("Illegal move! Check notation.")
                        continue
                        
                    # DELAY: Give user time to switch windows
                    print(">> SWITCH WINDOW NOW! Moving in 3...")
                    time.sleep(1)
                    print(">> 2...")
                    time.sleep(1)
                    print(">> 1...")
                    time.sleep(1)
                    
                except ValueError:
                    print("Invalid format. Use UCI (e.g., e7e5).")

        print("Game Over:", board.result())
        print("\n!!! VICTORY !!!")
        input("Press ENTER to close the browser...")

    except KeyboardInterrupt:
        print("\nBot stopped by user.")
        
    finally:
        engine.quit()
        driver.quit()

if __name__ == "__main__":
    run_bot()