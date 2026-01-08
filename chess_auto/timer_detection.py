import cv2
import os

def detect_timer_in_screenshot(board_img, house_dict, side, debug_dir=None, iteration=None, threshold=0.7):
    """
    Detects the chess timer in a given board screenshot.

    Args:
        board_img (np.array): Screenshot of the board.
        house_dict (dict): Mapping of square names to bounding boxes.
        side (str): "white" or "black".
        debug_dir (str, optional): Directory to save debug images.
        iteration (int, optional): Turn index for debug naming.
        threshold (float): Template match confidence threshold.

    Returns:
        bool: True if timer detected, False otherwise.
    """
    # Timer template path & reference squares based on side
    if side == "white":
        timer_img_path = "images/timer_white.png"
        ref_keys = ["H1", "G1", "F1"]
    else:
        timer_img_path = "images/timer_black.png"
        ref_keys = ["A8", "B8", "C8"]

    timer_template = cv2.imread(timer_img_path)
    if timer_template is None:
        raise FileNotFoundError(f"Timer template not found: {timer_img_path}")
    th, tw = timer_template.shape[:2]

    # Ensure all reference squares exist
    coords = [house_dict.get(k) for k in ref_keys if house_dict.get(k)]
    if len(coords) != 3:
        print("[Timer Detection] Not all reference squares found.")
        return False

    # Crop region around reference squares
    xs = [c[0] for c in coords] + [c[2] for c in coords]
    ys = [c[1] for c in coords] + [c[3] for c in coords]
    margin = 10
    x1 = max(0, min(xs) - margin)
    x2 = min(board_img.shape[1], max(xs) + margin)
    y1 = max(0, min(ys) - margin)
    y2 = board_img.shape[0]

    crop_img = board_img[y1:y2, x1:x2]

    # Save debug cropped image
    if debug_dir and iteration is not None:
        os.makedirs(debug_dir, exist_ok=True)
        cv2.imwrite(os.path.join(debug_dir, f"timer_crop_{iteration}.png"), crop_img)

    # Template matching
    result = cv2.matchTemplate(crop_img, timer_template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    print(f"[Timer Detection] Match confidence: {max_val:.2f}")

    if max_val >= threshold:
        # Timer center coordinates in full board image
        timer_x = x1 + max_loc[0] + tw // 2
        timer_y = y1 + max_loc[1] + th // 2
        print(f"[Timer Detection] Timer found at: ({timer_x}, {timer_y})")

        if debug_dir and iteration is not None:
            marked_img = board_img.copy()
            cv2.circle(marked_img, (timer_x, timer_y), 20, (0, 0, 255), 3)
            cv2.imwrite(os.path.join(debug_dir, f"timer_marked_{iteration}.png"), marked_img)

        return True
    else:
        print("[Timer Detection] Timer not found in cropped area.")
        return False