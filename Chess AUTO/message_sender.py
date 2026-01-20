import cv2
import numpy as np
import pyautogui
import random
import time

# =========================
# CONFIG
# =========================
MESSAGE_BOX_TEMPLATE = "images/message_and_rematch/message_box.png"
CONFIDENCE_THRESHOLD = 0.7
RETINA_SCALE = 1

# Marketing messages to send randomly
MARKETING_MESSAGES = [
    "Good luck! 🎯",
    "Nice game so far!",
    "Great moves!",
    "This is intense! 😄",
    "You play well!",
    "Enjoying this match!",
    "Good strategy!",
    "Well played!",
    "This is fun!",
]

# Probability of sending a message (20% chance)
MESSAGE_PROBABILITY = 0.20


def detect_and_send_message(img, debug=False):
    """
    Randomly detects message box and sends a marketing message.
    
    Args:
        img: Screenshot image (BGR format)
        debug: If True, prints debug information
        
    Returns:
        bool: True if message was sent, False otherwise
    """
    # Random chance check - only attempt 20% of the time
    if random.random() > MESSAGE_PROBABILITY:
        if debug:
            print(f"[Message] Skipping message send (random chance)")
        return False
    
    try:
        # Load template
        template = cv2.imread(MESSAGE_BOX_TEMPLATE)
        if template is None:
            if debug:
                print(f"[Message] Template not found: {MESSAGE_BOX_TEMPLATE}")
            return False
        
        # Perform template matching
        result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        if debug:
            print(f"[Message] Detection confidence: {max_val:.2f} (threshold: {CONFIDENCE_THRESHOLD})")
        
        if max_val < CONFIDENCE_THRESHOLD:
            if debug:
                print(f"[Message] Message box not detected")
            return False
        
        # Calculate center of message box
        h, w = template.shape[:2]
        center_x = (max_loc[0] + w // 2) / RETINA_SCALE
        center_y = (max_loc[1] + h // 2) / RETINA_SCALE
        
        if debug:
            print(f"[Message] Message box detected at ({center_x:.0f}, {center_y:.0f})")
        
        # Click on message box
        pyautogui.moveTo(center_x, center_y, duration=0.3)
        time.sleep(0.1)
        pyautogui.click()
        time.sleep(0.2)
        
        # Select random message
        message = random.choice(MARKETING_MESSAGES)
        
        if debug:
            print(f"[Message] Sending: '{message}'")
        
        # Type the message
        pyautogui.typewrite(message, interval=0.05)
        time.sleep(0.15)
        
        # Press Enter to send
        pyautogui.press('enter')
        time.sleep(0.2)
        
        if debug:
            print(f"[Message] ✓ Message sent successfully")
        
        return True
        
    except Exception as e:
        if debug:
            print(f"[Message] Error sending message: {e}")
        return False


def should_attempt_message():
    """
    Determines if we should attempt to send a message based on probability.
    
    Returns:
        bool: True if we should attempt, False otherwise
    """
    return random.random() <= MESSAGE_PROBABILITY
