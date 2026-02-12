# root/utils/game_actions.py
import pyautogui
import time
import math
import random
import cv2
import numpy as np
from icecream import ic
from core.logger import ChessLogger
from config.config import *  # This imports RETINA_SCALE, CHESS_USERNAME, etc.
from utils.vision import get_ui_element  # Needed for perform_login_sequence

logger = ChessLogger()


def perform_login_sequence(yolo_handler):
    """
    Executes the strict login sequence:
    login_one -> username -> password -> verification -> login_two
    """

    ic("LOGING: Starting login sequence...")

    logger.log(event="VISION", message=f"Login sequence started")

    steps = [
        ("login_one", None, 10),  # Standard wait (10s)
        ("username", CHESS_USERNAME, 10),  # Standard wait (10s)
        ("password", CHESS_PASSWORD, 10),  # Standard wait (10s)
        ("verification", None, 3),  # <--- LOW TIMEOUT (3s) for optional button
        ("login_two", None, 10),  # Standard wait (10s)
        ("block_notification", None, 10),
    ]

    for target, type_text, max_attempts in steps:
        ic("Login Search", target)

        # logger.log(event="LOGIN", message=f"Looking for {target}")

        found = False
        # Use the specific max_attempts for this step
        for _ in range(max_attempts):
            # 1. Capture screen
            screen = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)

            # 2. Scan with Login Model
            detections = yolo_handler.detect_login_elements(screen)
            element = get_ui_element(detections, target)

            if element:
                # 3. Click
                cx, cy = element

                ic("Clicking", target, cx, cy)

                pyautogui.click(cx / RETINA_SCALE, cy / RETINA_SCALE)

                # 4. Type if needed
                if type_text:
                    time.sleep(0.5)
                    pyautogui.typewrite(type_text, interval=0.1)

                found = True
                time.sleep(1.5)
                break

            time.sleep(1)

        if not found:
            ic("ERROR: Target not found", target)

            logger.log(
                event="ERROR",
                message=f"Could not find {target}, skipping to next step",
            )

    ic("LOGIN: Sequence complete.")

    logger.log(event="VISION", message=f"Sequence completed")


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
