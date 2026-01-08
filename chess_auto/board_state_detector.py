import cv2
import numpy as np
import os


TEMPLATE_DIR = "images/templates"


# =========================
# LOAD PIECE TEMPLATES
# =========================
def load_templates():
    templates = {}
    # Recursively walk through all subfolders (piece type folders)
    for root, dirs, files in os.walk(TEMPLATE_DIR):
        for fname in files:
            if fname.endswith(".png"):
                # Key: foldername/filename (without .png), e.g. black_knight/black_knight_1
                rel_dir = os.path.relpath(root, TEMPLATE_DIR)
                name = fname.replace(".png", "")
                if rel_dir == ".":
                    key = name
                else:
                    key = f"{rel_dir}/{name}"
                img = cv2.imread(os.path.join(root, fname), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    templates[key] = img
    return templates


# =========================
# OCCUPANCY CHECK
# =========================
def is_occupied(square_img, std_threshold=12):
    """
    Detect if a square has a piece using pixel variance.
    """
    gray = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)
    return np.std(gray) > std_threshold


# =========================
# TEMPLATE MATCHING
# =========================
def identify_piece(square_img, templates, match_threshold=0.85):
    gray_sq = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)

    best_score = 0
    best_piece = None

    for piece_name, tmpl in templates.items():
        th, tw = tmpl.shape[:2]
        sh, sw = gray_sq.shape[:2]

        # Template must be smaller
        if sh < th or sw < tw:
            continue

        res = cv2.matchTemplate(gray_sq, tmpl, cv2.TM_CCOEFF_NORMED)
        score = float(res.max())

        if score > best_score:
            best_score = score
            best_piece = piece_name

    if best_score >= match_threshold and best_piece is not None:
        # Only return the folder name (piece type)
        if "/" in best_piece:
            return best_piece.split("/")[0]
        else:
            return best_piece
    else:
        return None


# =========================
# MAIN BOARD STATE DETECTOR
# =========================
def detect_board_state(board_img, house_dict, debug=False):
    """
    house_dict format:
    {
        'E4': (x1, y1, x2, y2),
        ...
    }

    returns:
    {
        'E4': 'white_pawn' | None,
        ...
    }
    """

    templates = load_templates()
    board_state = {}

    h, w = board_img.shape[:2]

    for square, (x1, y1, x2, y2) in house_dict.items():

        # Clamp bounds safely
        x1 = max(0, min(w - 1, int(x1)))
        y1 = max(0, min(h - 1, int(y1)))
        x2 = max(0, min(w, int(x2)))
        y2 = max(0, min(h, int(y2)))

        if x2 <= x1 or y2 <= y1:
            board_state[square] = None
            continue

        square_img = board_img[y1:y2, x1:x2]

        if square_img.size == 0:
            board_state[square] = None
            continue

        if not is_occupied(square_img):
            board_state[square] = None
        else:
            board_state[square] = identify_piece(square_img, templates)

        if debug:
            print(f"[BoardState] {square}: {board_state[square]}")

    return board_state

# =========================
def draw_house_boxes(board_img, house_dict, out_path):
    debug = board_img.copy()

    for sq, (x1, y1, x2, y2) in house_dict.items():
        cv2.rectangle(debug, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            debug, sq,
            (x1 + 5, y1 + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5, (0, 0, 255), 1
        )

    cv2.imwrite(out_path, debug)
    return out_path