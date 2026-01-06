import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import pyautogui
import time
import sys

# --- ADJUST THIS NUMBER UNTIL IT HITS DEAD CENTER ---
TEST_OFFSET_Y = 60   # <--- Change this, then run again

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_board_rect(driver):
    """
    Robust way to find the chess board. 
    Tries multiple common selectors used by Chess.com.
    """
    # List of possible IDs/Tags for the board
    selectors = [
        (By.TAG_NAME, "chess-board"),             # New standard
        (By.ID, "board-layout-chessboard"),       # Common layout
        (By.ID, "board-single"),                  # Analysis/Puzzles
        (By.CLASS_NAME, "board"),                 # Fallback class
        (By.XPATH, "//div[contains(@class, 'board')]") # Catch-all
    ]
    
    found_element = None
    
    print("LOG: Searching for board element...")
    for strategy, locator in selectors:
        try:
            # Wait up to 2 seconds for this specific selector to appear
            found_element = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((strategy, locator))
            )
            print(f"SUCCESS: Found board using {locator}")
            break # Stop searching if we found it
        except:
            continue # Try the next one

    if not found_element:
        print("CRITICAL ERROR: Could not find the board with ANY method.")
        print("Tip: Make sure you are not in 'Focus Mode' or full screen video.")
        sys.exit(1)
            
    return found_element.rect

def test_aim():
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    driver.set_window_position(0, 0)
    driver.maximize_window()
    driver.get("https://www.chess.com/play/computer")
    
    input("Log in, Start Game, then press ENTER to test aim...")

    board_rect = get_board_rect(driver)
    
    # Calculate e4 Center
    square_size = board_rect['width'] / 8
    
    # e4 coordinates (File e=4, Rank 4=4)
    # File index: 4 (0-based is 4th index? No. a=0, b=1, c=2, d=3, e=4)
    file_idx = 4 
    # Rank index: e4 means rank 4. Screen rows: 8=0, 7=1, ... 4=4.
    rank_idx = 4 

    rel_x = (file_idx * square_size) + (square_size / 2)
    rel_y = (rank_idx * square_size) + (square_size / 2)
    
    target_x = board_rect['x'] + rel_x
    target_y = board_rect['y'] + rel_y + TEST_OFFSET_Y
    
    print(f"Testing Aim on e4 with Offset {TEST_OFFSET_Y}...")
    print("Watch your mouse pointer!")
    
    for i in range(5):
        pyautogui.moveTo(target_x, target_y, duration=1)
        print(f"Pointing at {target_x}, {target_y}")
        time.sleep(1)
        # Move away to show it returning
        pyautogui.moveRel(100, 0, duration=0.5)

    driver.quit()

if __name__ == "__main__":
    test_aim()