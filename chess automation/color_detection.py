import cv2
import numpy as np
from skimage.color import rgb2lab, deltaE_ciede2000


def match_color_at_point(img, point, target_rgbs, threshold=8):
    """
    Checks if a specific point (x, y) in the image matches the target yellow colors.
    """
    x, y = int(point[0]), int(point[1])

    # Safety check for bounds
    h, w = img.shape[:2]
    if x < 0 or x >= w or y < 0 or y >= h:
        return False

    # Extract color (OpenCV loads as BGR, convert to RGB for consistency)
    b, g, r = img[y, x]
    pixel_rgb = np.array([[[r, g, b]]], dtype=np.uint8)

    # Convert to LAB
    pixel_lab = rgb2lab(pixel_rgb / 255.0)[0][0]

    for target_rgb in target_rgbs:
        # Target RGB is expected as [R, G, B]
        target_arr = np.array([[target_rgb]], dtype=np.uint8)
        target_lab = rgb2lab(target_arr / 255.0)[0][0]

        delta_e = deltaE_ciede2000(pixel_lab, target_lab)
        if delta_e <= threshold:
            return True

    return False


def is_our_turn_finished(full_img, last_move_coords):
    """
    Returns True if our last move is still highlighted (meaning it's opponent's turn).
    Returns False if the highlight is gone or changed (meaning it's our turn).

    last_move_coords: tuple ((fx, fy), (tx, ty)) -> Global Screen Coordinates
    """
    if not last_move_coords:
        return False  # No last move recorded, so it must be our turn (start of game)

    (fx, fy), (tx, ty) = last_move_coords

    # Colors for Chess.com yellow highlights (Standard & Dark themes)
    # R, G, B format
    TARGET_COLORS = [
        [185, 202, 67],  # Greenish Yellow (Light square highlight)
        [245, 246, 130],  # Bright Yellow (Dark square highlight)
    ]

    # Check both Start and End squares of our last move
    start_yellow = match_color_at_point(full_img, (fx, fy), TARGET_COLORS)
    end_yellow = match_color_at_point(full_img, (tx, ty), TARGET_COLORS)

    # LOGIC:
    # If BOTH are yellow, our move is still the active highlight -> WAIT
    if start_yellow and end_yellow:
        return True

    # If neither (or only one) is yellow, the board state changed -> PLAY
    return False
