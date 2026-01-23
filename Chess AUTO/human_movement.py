import random
import time
import math
import pyautogui


def move_mouse_humanly(x1, y1, x2, y2, duration=0.5):
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
