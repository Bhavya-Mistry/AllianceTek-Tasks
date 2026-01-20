import pyautogui
import time
import random

# ===================== CONFIG =====================
RETINA_SCALE = 1          # set to 1 if not on Retina / HiDPI
pyautogui.FAILSAFE = True # move mouse to corner to stop
pyautogui.PAUSE = 0
# ==================================================


def human_move(start, end, duration=0.6):
    """
    Move mouse in a human-like curved path using Bezier curve,
    acceleration/deceleration, and micro jitter.
    """
    sx, sy = start
    ex, ey = end

    # Random control point (creates curve)
    cx = (sx + ex) / 2 + random.randint(-120, 120)
    cy = (sy + ey) / 2 + random.randint(-120, 120)

    steps = int(duration * 120)

    for i in range(steps):
        t = i / steps

        # Ease in-out (human acceleration)
        t = t * t * (3 - 2 * t)

        # Quadratic Bezier curve
        x = (1 - t) ** 2 * sx + 2 * (1 - t) * t * cx + t ** 2 * ex
        y = (1 - t) ** 2 * sy + 2 * (1 - t) * t * cy + t ** 2 * ey

        # Micro jitter (hand tremor)
        x += random.uniform(-1.3, 1.3)
        y += random.uniform(-1.3, 1.3)

        pyautogui.moveTo(x / RETINA_SCALE, y / RETINA_SCALE, _pause=False)
        time.sleep(random.uniform(0.003, 0.008))


def human_drag(fx, fy, tx, ty):
    """
    Human-like click and drag from (fx, fy) to (tx, ty)
    """

    # Move to start position first
    current_pos = pyautogui.position()
    human_move(
        current_pos,
        (fx, fy),
        duration=random.uniform(0.3, 0.6)
    )

    # Small human reaction pause
    time.sleep(random.uniform(0.05, 0.12))
    pyautogui.mouseDown()

    # Brief hesitation before drag
    time.sleep(random.uniform(0.06, 0.12))

    # Occasionally overshoot then correct (very human)
    if random.random() < 0.3:
        ox = tx + random.randint(-10, 10)
        oy = ty + random.randint(-10, 10)

        human_move(
            (fx, fy),
            (ox, oy),
            duration=random.uniform(0.3, 0.6)
        )

        human_move(
            (ox, oy),
            (tx, ty),
            duration=random.uniform(0.15, 0.3)
        )
    else:
        human_move(
            (fx, fy),
            (tx, ty),
            duration=random.uniform(0.4, 0.8)
        )

    # Natural pause before release
    time.sleep(random.uniform(0.05, 0.15))
    pyautogui.mouseUp()
