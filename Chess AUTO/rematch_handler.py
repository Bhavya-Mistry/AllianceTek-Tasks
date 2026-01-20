import cv2
import numpy as np
import pyautogui
import time
import os

# =========================
# CONFIG
# =========================
# Templates to detect that the game has finished
GAME_REVIEW_TEMPLATE = "images/message_and_rematch/game_review.png"
WIN_TEMPLATE = "images/message_and_rematch/win.png"

# Template for the button used to immediately start a new game
NEW_GAME_TEMPLATE = "images/message_and_rematch/new_game.png"

CONFIDENCE_THRESHOLD = 0.75
RETINA_SCALE = 1
MAX_ATTEMPTS = 30  # 30 seconds max wait


def detect_game_over(img, debug=False):
    """
    Detects if the game has ended by looking for game-over indicators.
    
    Args:
        img: Screenshot image (BGR format)
        debug: If True, prints debug information
        
    Returns:
        bool: True if game over detected, False otherwise
    """
    templates = [
        (GAME_REVIEW_TEMPLATE, "Game Review"),
        (WIN_TEMPLATE, "Win"),
    ]

    for template_path, label in templates:
        if not os.path.exists(template_path):
            if debug:
                print(f"[Rematch] Template not found for game over ({label}): {template_path}")
            continue

        try:
            template = cv2.imread(template_path)
            if template is None:
                if debug:
                    print(f"[Rematch] Failed to load game over template ({label}): {template_path}")
                continue

            result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if debug:
                print(
                    f"[Rematch] Game over check '{label}' confidence: "
                    f"{max_val:.2f} (threshold: {CONFIDENCE_THRESHOLD})"
                )

            if max_val >= CONFIDENCE_THRESHOLD:
                if debug:
                    h, w = template.shape[:2]
                    cx = max_loc[0] + w // 2
                    cy = max_loc[1] + h // 2
                    print(f"[Rematch] Game over detected via {label} at ({cx}, {cy})")
                return True

        except Exception as e:
            if debug:
                print(f"[Rematch] Error during game over detection for {label}: {e}")

    return False


def detect_new_game_button(img, debug=False):
    """
    Detects the "New Game" button on screen.
    
    Args:
        img: Screenshot image (BGR format)
        debug: If True, prints debug information
        
    Returns:
        tuple: (x, y) coordinates if found, None otherwise
    """
    if not os.path.exists(NEW_GAME_TEMPLATE):
        if debug:
            print(f"[Rematch] Template not found for New Game button: {NEW_GAME_TEMPLATE}")
        return None
    
    try:
        template = cv2.imread(NEW_GAME_TEMPLATE)
        if template is None:
            if debug:
                print(f"[Rematch] Failed to load New Game template: {NEW_GAME_TEMPLATE}")
            return None
        
        result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        if debug:
            print(f"[Rematch] New Game button confidence: {max_val:.2f} (threshold: {CONFIDENCE_THRESHOLD})")
        
        if max_val < CONFIDENCE_THRESHOLD:
            return None
        
        h, w = template.shape[:2]
        center_x = max_loc[0] + w // 2
        center_y = max_loc[1] + h // 2
        
        if debug:
            print(f"[Rematch] New Game button detected at ({center_x}, {center_y})")
        
        return (center_x, center_y)
        
    except Exception as e:
        if debug:
            print(f"[Rematch] Error detecting New Game button: {e}")
        return None


def click_new_game(debug=False):
    """
    Waits for and clicks the "New Game" button after a game ends.
    
    Args:
        debug: If True, prints debug information
        
    Returns:
        bool: True if successfully clicked, False otherwise
    """
    if debug:
        print("[Rematch] Waiting for game to end and New Game button to appear...")
    
    for attempt in range(MAX_ATTEMPTS):
        try:
            # Take screenshot
            screenshot = pyautogui.screenshot()
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Detect New Game button
            coords = detect_new_game_button(img, debug=False)
            
            if coords:
                x, y = coords
                # Scale for retina display
                x = x / RETINA_SCALE
                y = y / RETINA_SCALE
                
                if debug:
                    print(f"[Rematch] Clicking New Game button at ({x:.0f}, {y:.0f})")
                
                pyautogui.moveTo(x, y, duration=0.4)
                time.sleep(0.2)
                pyautogui.click()
                time.sleep(1)
                
                if debug:
                    print("[Rematch] ✓ New Game button clicked successfully")
                
                return True
            
            # Wait before next attempt
            time.sleep(1)
            
        except Exception as e:
            if debug:
                print(f"[Rematch] Error on attempt {attempt + 1}: {e}")
            time.sleep(1)
    
    if debug:
        print(f"[Rematch] Failed to find New Game button after {MAX_ATTEMPTS} attempts")
    
    return False


def wait_for_game_end_and_restart(debug=False):
    """
    Monitors for game end and automatically clicks New Game.
    This should be called periodically during the game loop.
    
    Args:
        debug: If True, prints debug information
        
    Returns:
        bool: True if game ended and New Game was clicked, False otherwise
    """
    try:
        screenshot = pyautogui.screenshot()
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        if detect_game_over(img, debug=False):
            if debug:
                print("[Rematch] Game over detected!")
            return click_new_game(debug=debug)
        
        return False
        
    except Exception as e:
        if debug:
            print(f"[Rematch] Error checking for game end: {e}")
        return False
