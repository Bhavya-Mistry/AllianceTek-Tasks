import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import chess
import chess.engine
import pyautogui
import time
import random
import numpy as np

# --- CONFIGURATION ---
STOCKFISH_PATH = r"C:\Users\bhavya.mistry\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"  # <--- UPDATE THIS PATH
GAME_URL = "https://www.chess.com/play/computer"

# --- HUMAN MOUSE MOVEMENT (Bezier Curves) ---
def human_move(start_x, start_y, end_x, end_y):
    """Moves mouse in a curve with variable speed to simulate a hand."""
    # Randomize control point for the curve
    control_x = (start_x + end_x) / 2 + random.randint(-100, 100)
    control_y = (start_y + end_y) / 2 + random.randint(-100, 100)
    
    # Generate points along the curve
    points = np.linspace(0, 1, num=50)
    path = []
    for t in points:
        x = (1-t)**2 * start_x + 2*(1-t)*t * control_x + t**2 * end_x
        y = (1-t)**2 * start_y + 2*(1-t)*t * control_y + t**2 * end_y
        path.append((x, y))
    
    # Move along path
    for x, y in path:
        pyautogui.moveTo(x, y)
        time.sleep(random.uniform(0.001, 0.003)) # Fast but variable speed
        
    # Small hesitation before clicking (fitts's law)
    time.sleep(random.uniform(0.05, 0.15))
    pyautogui.click()

# --- COORDINATE MAPPING ---
def get_board_dimensions(driver):
    """Finds the board on screen and calculates square size."""
    try:
        # Chess.com usually uses this tag for the board
        board = driver.find_element(By.TAG_NAME, "chess-board")
    except:
        # Fallback for some versions of the site
        board = driver.find_element(By.ID, "board-layout-chessboard")

    # Get the element's position relative to the web page
    rect = board.rect # contains {'x', 'y', 'width', 'height'}
    return rect

def get_square_center(square_name, board_rect, browser_offset_y):
    """
    Converts a square (e.g., 'e2') to physical screen coordinates (x, y).
    """
    square_size = board_rect['width'] / 8
    
    # Files: a=0, h=7
    file_idx = ord(square_name[0]) - ord('a')
    # Ranks: 1=7, 8=0 (Screen Y is inverted)
    rank_idx = 8 - int(square_name[1])
    
    # Calculate relative position inside the board
    rel_x = (file_idx * square_size) + (square_size / 2)
    rel_y = (rank_idx * square_size) + (square_size / 2)
    
    # Add absolute screen offsets
    # Note: board_rect['x'] is relative to the browser window, not screen.
    # We add browser_offset_y to account for the URL bar/Tabs.
    screen_x = board_rect['x'] + rel_x
    screen_y = board_rect['y'] + rel_y + browser_offset_y
    
    return screen_x, screen_y

# --- MAIN BOT LOGIC ---
def run_bot():
    # 1. Launch Browser (Undetected)
    options = uc.ChromeOptions()
    # options.add_argument("--start-maximized") # Optional
    driver = uc.Chrome(options=options)
    driver.get(GAME_URL)
    
    print("LOG: Please log in or start a game against the Computer.")
    print("LOG: Position the browser window at the top-left of your screen.")
    input("Press ENTER once the game has started and board is visible...")

    # 2. Calibration (Vital Step)
    # We assume the browser has a top bar (URL/Tabs) of roughly 120px. 
    # You may need to tweak this number if clicks are too high/low.
    BROWSER_OFFSET_Y = 125 
    board_rect = get_board_dimensions(driver)
    
    # 3. Initialize Engine
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    board = chess.Board() # Internal tracking board
    
    is_white = input("Are you playing White? (y/n): ").lower() == 'y'
    if not is_white:
        # If black, we need to flip the internal board reference or logic
        # For simplicity, this script assumes you are White. 
        # Playing Black requires flipping the rank_idx logic in get_square_center.
        print("This simple script currently supports Playing White only.")

    try:
        while not board.is_game_over():
            # A. If it's our turn
            if board.turn == chess.WHITE:
                result = engine.play(board, chess.engine.Limit(time=0.5))
                best_move = result.move
                
                # Convert Move to Strings (e.g., e2 -> e4)
                start_sq = chess.square_name(best_move.from_square)
                end_sq = chess.square_name(best_move.to_square)
                
                # B. Calculate Coordinates
                sx, sy = get_square_center(start_sq, board_rect, BROWSER_OFFSET_Y)
                ex, ey = get_square_center(end_sq, board_rect, BROWSER_OFFSET_Y)
                
                print(f"Bot Playing: {start_sq} -> {end_sq}")
                
                # C. Physical Mouse Move
                human_move(sx, sy, ex, ey)
                
                # Update Internal Board
                board.push(best_move)
            
            else:
                # D. Wait for Opponent (Manual Input for now)
                # In a full version, you would scrape the last move from the DOM.
                # For this test, you must type the opponent's move manually.
                opp_move = input("Enter Opponent's Move (e.g., e7e5): ")
                try:
                    board.push_uci(opp_move)
                except:
                    print("Invalid move! Try again.")

    except KeyboardInterrupt:
        print("Bot stopped.")
    finally:
        engine.quit()
        driver.quit()

if __name__ == "__main__":
    run_bot()