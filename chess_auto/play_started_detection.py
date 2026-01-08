import pyautogui
import cv2
import numpy as np
import time
import os

def detect_play_started(template_path="images/play_detector.png", confidence=0.8, retina_scale=2, timeout=20, interval=0.2):
    """
    Continuously take screenshots and search for the play detector image.
    Returns True if found within timeout, else False.
    """
    start_time = time.time()
    template = cv2.imread(template_path)
    if template is None:
        raise FileNotFoundError(f"Template image not found: {template_path}")
    h, w = template.shape[:2]

    while time.time() - start_time < timeout:
        screenshot = pyautogui.screenshot()
        screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val >= confidence:
            x = max_loc[0] + w // 2
            y = max_loc[1] + h // 2
            x = float(x) / float(retina_scale)
            y = float(y) / float(retina_scale)
            print(f"[Play Started Detection] Detected at: ({int(x)}, {int(y)}) with confidence {max_val:.2f}")
            return True
        time.sleep(interval)
    print("[Play Started Detection] Play detector not found within timeout.")
    return False
