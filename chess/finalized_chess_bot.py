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

STOCKFISH_PATH = r"C:\Users\bhavya.mistry\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"
# GAME_URL = "https://www.chess.com/play/computer"
GAME_URL = "https://www.chess.com/play/online"

BROWSER_OFFSET_Y = 55

def get_bezier_path(start, end):
    start_x, start_y = start
    end_x, end_y = end
    control_x = (start_x + end_x) / 2 + random.randint(-200, 200)
    control_y = (start_y + end_y) / 2 + random.randint(-200, 200)
    points = np.linspace(0, 1, num=random.randint(20, 50))
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
        time.sleep(random.uniform(0.000001, 0.0001))
    pyautogui.moveTo(target_x, target_y)

def perform_chess_move(start_x, start_y, end_x, end_y):
    #src sq
    move_mouse_smoothly(start_x, start_y)
    time.sleep(random.uniform(0.1, 0.2)) 
    
    pyautogui.mouseDown()
    
    #dest sq
    move_mouse_smoothly(end_x, end_y)
    time.sleep(random.uniform(0.1, 0.2))
    
    pyautogui.mouseUp()


def get_last_move_from_highlights(driver, board):
    squares = driver.find_elements(By.CSS_SELECTOR, "div[class*='highlight']")
    
    if len(squares) < 2:
        return None 

    highlighted_squares = []
    for s in squares:
        class_name = s.get_attribute("class")
        match = re.search(r'square-(\d)(\d)', class_name)
        if match:
            col = int(match.group(1)) # 1-8
            row = int(match.group(2)) # 1-8
            file_idx = col - 1
            rank_idx = row - 1
            square_idx = chess.square(file_idx, rank_idx)
            highlighted_squares.append(square_idx)

    legal_moves = list(board.legal_moves)
    current_highlights = highlighted_squares[-2:] 
    
    if len(current_highlights) != 2:
        return None

    sq1 = current_highlights[0]
    sq2 = current_highlights[1]

    move_1 = chess.Move(sq1, sq2)
    if move_1 in legal_moves:
        return move_1
        
    move_2 = chess.Move(sq2, sq1)
    if move_2 in legal_moves:
        return move_2
        
    for move in legal_moves:
        if (move.from_square == sq1 and move.to_square == sq2) or \
           (move.from_square == sq2 and move.to_square == sq1):
            return move

    return None

def get_board_rect(driver):
    selectors = [
        (By.TAG_NAME, "chess-board"),
        (By.ID, "board-layout-chessboard"),
        (By.CLASS_NAME, "board")
    ]
    for strategy, locator in selectors:
        try:
            element = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((strategy, locator))
            )
            return element.rect
        except:
            continue
    print("ERROR: Could not find the board element on page.")
    sys.exit(1)

def get_square_center(square_name, board_rect, y_offset, is_white_perspective):
    
    square_size = board_rect['width'] / 8
    
    # Standard Chess Indices (0-7)
    # file 'a' = 0, 'h' = 7
    # rank '1' = 0, '8' = 7
    file_idx = ord(square_name[0]) - ord('a')
    rank_idx = int(square_name[1]) - 1 

    if is_white_perspective:
        # WHITE POV: 
        # a (0) is Left. 
        # 8 (7) is Top.
        visual_col = file_idx
        visual_row = 7 - rank_idx
    else:
        # BLACK POV: 
        # h (7) is Left (so we invert file). 
        # 1 (0) is Top (so we don't invert rank).
        visual_col = 7 - file_idx
        visual_row = rank_idx

    # Calculate pixel offset from top-left of board
    rel_x = (visual_col * square_size) + (square_size / 2)
    rel_y = (visual_row * square_size) + (square_size / 2)
    
    screen_x = board_rect['x'] + rel_x
    screen_y = board_rect['y'] + rel_y + y_offset
    return screen_x, screen_y

def run_bot():
    print("----------------START----------------")
    
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    driver.set_window_position(0, 0)
    driver.maximize_window()
    driver.get(GAME_URL)
    
    input("ACTION: Press ENTER once the board is visible and pieces are set...")

    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        engine.configure({
            "UCI_LimitStrength": True,
            "UCI_Elo": 1350  # <--- CHANGE THIS NUMBER TO MATCH YOUR DESIRED RATING
        })
        print(f"LOG: Stockfish strength limited for safety.")

    except FileNotFoundError:
        print(f"ERROR: Could not find Stockfish at: {STOCKFISH_PATH}")
        driver.quit()
        return
    # try:
    #     engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    # except FileNotFoundError:
    #     print(f"ERROR: Could not find Stockfish at: {STOCKFISH_PATH}")
    #     driver.quit()
    #     return

    board = chess.Board()
    board_rect = get_board_rect(driver)
    
    side = input("Are we playing White? (y/n): ").lower()
    bot_color = chess.WHITE if side == 'y' else chess.BLACK
    
    print("To stop, press Ctrl+C.")
    
    try:
        while not board.is_game_over():
            
            if board.turn == bot_color:
                print("\n[Bot Thinking...]")
                
                move_count = board.fullmove_number
                if move_count < 6:
                    think_time = random.uniform(0.5, 0.7)
                else:
                    think_time = random.uniform(2.5, 8.0)
                
                time.sleep(think_time)
                
                result = engine.play(board, chess.engine.Limit(time=0.1))
                best_move = result.move
                
                start_sq = chess.square_name(best_move.from_square)
                end_sq = chess.square_name(best_move.to_square)
                
                print(f"Bot Playing: {start_sq} -> {end_sq}")
                # start_px = get_square_center(start_sq, board_rect, BROWSER_OFFSET_Y)
                # end_px = get_square_center(end_sq, board_rect, BROWSER_OFFSET_Y)
                is_white = (side == 'y')
            
                start_px = get_square_center(start_sq, board_rect, BROWSER_OFFSET_Y, is_white)
                end_px = get_square_center(end_sq, board_rect, BROWSER_OFFSET_Y, is_white)
                
                perform_chess_move(start_px[0], start_px[1], end_px[0], end_px[1])
                board.push(best_move)
                
                # Move mouse slightly away to avoid blocking view
                pyautogui.moveRel(150, 0)
                
            else:
                print("Waiting for opponent...", end="\r")
                start_fen = board.fen()
                
                while board.fen() == start_fen:
                    detected_move = get_last_move_from_highlights(driver, board)
                    
                    if detected_move:
                        print(f"\nOpponent Played: {detected_move}")
                        board.push(detected_move)
                        break
                    
                    time.sleep(0.5)

        print("Game Over:", board.result())
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