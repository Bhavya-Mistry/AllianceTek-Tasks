import cv2
import numpy as np
import os
import uuid
import tempfile

# =========================
# CONFIG
# =========================


# WHITE_ROOK_TEMPLATE = os.path.join("images", "white_rock.png")
# BLACK_ROOK_TEMPLATE = os.path.join("images", "black_rock.png")




#WHITE_ROOK_TEMPLATE = [
#    os.path.join("images/templates/white_rock", "white_rock.png"),
#   os.path.join("images/templates/white_rock", "white_rock_1.png") 
#]
#BLACK_ROOK_TEMPLATE = [
#    os.path.join("images/templates/black_rock", "black_rock.png"),
#    os.path.join("images/templates/black_rock", "black_rock_1.png") 
#]




WHITE_ROOK_TEMPLATE = [
    os.path.join("images", "templates", "white_rock", "white_rock.png"),
    os.path.join("images", "templates", "white_rock", "white_rock_1.png")
]

BLACK_ROOK_TEMPLATE = [
    os.path.join("images", "templates", "black_rock", "black_rock.png"),
    os.path.join("images", "templates", "black_rock", "black_rock_1.png")
]










RETINA_SCALE = 1
TEMP_DIR = tempfile.gettempdir()


# =========================
# ROOK DETECTION
# =========================
def find_rooks(board_img_path, template_paths, threshold=0.8):
    """
    Detects rooks using a list of template images.
    """
    board = cv2.imread(board_img_path)
    if board is None:
        raise FileNotFoundError(f"Board image not found: {board_img_path}")

    # Ensure input is a list (in case you pass a single string by mistake)
    if isinstance(template_paths, str):
        template_paths = [template_paths]

    found_centers = []

    # 1. Loop through every template in the list
    for t_path in template_paths:
        if not os.path.exists(t_path):
            print(f"[Warning] Template does not exist, skipping: {t_path}")
            continue

        template = cv2.imread(t_path)
        if template is None:
            continue

        h, w = template.shape[:2]
        result = cv2.matchTemplate(board, template, cv2.TM_CCOEFF_NORMED)
        
        # Get all matches above threshold
        points = np.where(result >= threshold)
        
        for pt in zip(*points[::-1]):
            cx = pt[0] + w // 2
            cy = pt[1] + h // 2
            found_centers.append((cx, cy))

    # 2. Remove Duplicates (Deduplication)
    # Since multiple templates might find the SAME rook, we must filter close points.
    unique_centers = []
    for cx, cy in found_centers:
        # If this point is not close (within 20px) to any point we already saved, keep it
        if not any(np.linalg.norm(np.array((cx, cy)) - np.array(p)) < 20 for p in unique_centers):
            unique_centers.append((cx, cy))

    return unique_centers
    
    
    
# =========================
# MAIN ENTRY
# =========================
def main(board_img_path, out_path=None, side="white"):
    if side not in ("white", "black"):
        raise ValueError("side must be 'white' or 'black'")

    white_rooks = find_rooks(board_img_path, WHITE_ROOK_TEMPLATE)
    black_rooks = find_rooks(board_img_path, BLACK_ROOK_TEMPLATE)
	
	
    all_rooks = [(pt, "white") for pt in white_rooks] + [(pt, "black") for pt in black_rooks]

    if len(all_rooks) < 4:
        raise RuntimeError("Could not detect all 4 corner rooks")

    # Sort by Y to separate top/bottom
    all_rooks.sort(key=lambda r: r[0][1])
    top = all_rooks[:2]
    bottom = all_rooks[-2:]

    # Sort left/right
    top_left, top_right = sorted(top, key=lambda r: r[0][0])
    bottom_left, bottom_right = sorted(bottom, key=lambda r: r[0][0])

    corners = {
        "top_left": top_left[0],
        "top_right": top_right[0],
        "bottom_left": bottom_left[0],
        "bottom_right": bottom_right[0],
    }

    if out_path is None:
        out_path = os.path.join(TEMP_DIR, f"board_rooks_{uuid.uuid4().hex}.png")

    house_dict = draw_board(board_img_path, corners, out_path, side)

    return out_path, house_dict

# =========================
# BOARD GEOMETRY + SQUARES
# =========================
def draw_board(board_img_path, corners, out_path, side):
    img = cv2.imread(board_img_path)

    # Convert to float arrays
    bl = np.array(corners["bottom_left"], dtype=float)
    br = np.array(corners["bottom_right"], dtype=float)
    tr = np.array(corners["top_right"], dtype=float)
    tl = np.array(corners["top_left"], dtype=float)

    # Estimate square size
    square_w = np.linalg.norm(br - bl) / 7
    square_h = np.linalg.norm(tl - bl) / 7

    half_w = square_w * 0.45
    half_h = square_h * 0.45

    house_dict = {}

    for rank in range(8):      # 0 bottom → 7 top
        for file in range(8):  # 0 left → 7 right

            u = file / 7.0
            v = rank / 7.0

            p_bottom = bl * (1 - u) + br * u
            p_top = tl * (1 - u) + tr * u
            cx, cy = (p_bottom * (1 - v) + p_top * v).astype(int)

            if side == "white":
                file_label = chr(ord("A") + file)
                rank_label = str(rank + 1)
            else:
                file_label = chr(ord("H") - file)
                rank_label = str(8 - rank)

            square = f"{file_label}{rank_label}"

            x1 = int(cx - half_w)
            y1 = int(cy - half_h)
            x2 = int(cx + half_w)
            y2 = int(cy + half_h)

            house_dict[square] = (x1, y1, x2, y2)

            # Debug overlay
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 1)
            cv2.putText(
                img, square, (cx - 18, cy + 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1
            )

    # Draw board outline
    for p1, p2 in [(bl, br), (br, tr), (tr, tl), (tl, bl)]:
        cv2.line(img, tuple(p1.astype(int)), tuple(p2.astype(int)), (0, 255, 0), 2)

    cv2.imwrite(out_path, img)
    return house_dict
