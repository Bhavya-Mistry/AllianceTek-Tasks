# # import cv2
# # import numpy as np
# # import os
# # import uuid
# # import tempfile

# # # =========================
# # # CONFIG
# # # =========================
# # WHITE_ROOK_TEMPLATE = os.path.join("images", "white_rock.png")
# # BLACK_ROOK_TEMPLATE = os.path.join("images", "black_rock.png")

# # RETINA_SCALE = 1
# # TEMP_DIR = tempfile.gettempdir()


# # # =========================
# # # ROOK DETECTION
# # # =========================
# # def find_rooks(board_img_path, template_path, threshold=0.8):
# #     board = cv2.imread(board_img_path)
# #     template = cv2.imread(template_path)

# #     if board is None or template is None:
# #         raise FileNotFoundError("Board or template image not found")

# #     result = cv2.matchTemplate(board, template, cv2.TM_CCOEFF_NORMED)
# #     h, w = template.shape[:2]

# #     points = np.where(result >= threshold)
# #     centers = []

# #     for pt in zip(*points[::-1]):
# #         cx = pt[0] + w // 2
# #         cy = pt[1] + h // 2

# #         if not any(np.linalg.norm(np.array((cx, cy)) - np.array(p)) < 20 for p in centers):
# #             centers.append((cx, cy))

# #     return centers


# # # =========================
# # # MAIN ENTRY
# # # =========================
# # def main(board_img_path, out_path=None, side="white"):
# #     if side not in ("white", "black"):
# #         raise ValueError("side must be 'white' or 'black'")

# #     white_rooks = find_rooks(board_img_path, WHITE_ROOK_TEMPLATE)
# #     black_rooks = find_rooks(board_img_path, BLACK_ROOK_TEMPLATE)

# #     all_rooks = [(pt, "white") for pt in white_rooks] + [(pt, "black") for pt in black_rooks]

# #     if len(all_rooks) < 4:
# #         raise RuntimeError("Could not detect all 4 corner rooks")

# #     # Sort by Y to separate top/bottom
# #     all_rooks.sort(key=lambda r: r[0][1])
# #     top = all_rooks[:2]
# #     bottom = all_rooks[-2:]

# #     # Sort left/right
# #     top_left, top_right = sorted(top, key=lambda r: r[0][0])
# #     bottom_left, bottom_right = sorted(bottom, key=lambda r: r[0][0])

# #     corners = {
# #         "top_left": top_left[0],
# #         "top_right": top_right[0],
# #         "bottom_left": bottom_left[0],
# #         "bottom_right": bottom_right[0],
# #     }

# #     if out_path is None:
# #         out_path = os.path.join(TEMP_DIR, f"board_rooks_{uuid.uuid4().hex}.png")

# #     house_dict = draw_board(board_img_path, corners, out_path, side)

# #     return out_path, house_dict

# # # =========================
# # # BOARD GEOMETRY + SQUARES
# # # =========================
# # def draw_board(board_img_path, corners, out_path, side):
# #     img = cv2.imread(board_img_path)

# #     # Convert to float arrays
# #     bl = np.array(corners["bottom_left"], dtype=float)
# #     br = np.array(corners["bottom_right"], dtype=float)
# #     tr = np.array(corners["top_right"], dtype=float)
# #     tl = np.array(corners["top_left"], dtype=float)

# #     # Estimate square size
# #     square_w = np.linalg.norm(br - bl) / 7
# #     square_h = np.linalg.norm(tl - bl) / 7

# #     half_w = square_w * 0.45
# #     half_h = square_h * 0.45

# #     house_dict = {}

# #     for rank in range(8):      # 0 bottom → 7 top
# #         for file in range(8):  # 0 left → 7 right

# #             u = file / 7.0
# #             v = rank / 7.0

# #             p_bottom = bl * (1 - u) + br * u
# #             p_top = tl * (1 - u) + tr * u
# #             cx, cy = (p_bottom * (1 - v) + p_top * v).astype(int)

# #             if side == "white":
# #                 file_label = chr(ord("A") + file)
# #                 rank_label = str(rank + 1)
# #             else:
# #                 file_label = chr(ord("H") - file)
# #                 rank_label = str(8 - rank)

# #             square = f"{file_label}{rank_label}"

# #             x1 = int(cx - half_w)
# #             y1 = int(cy - half_h)
# #             x2 = int(cx + half_w)
# #             y2 = int(cy + half_h)

# #             house_dict[square] = (x1, y1, x2, y2)

# #             # Debug overlay
# #             cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 1)
# #             cv2.putText(
# #                 img, square, (cx - 18, cy + 6),
# #                 cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1
# #             )

# #     # Draw board outline
# #     for p1, p2 in [(bl, br), (br, tr), (tr, tl), (tl, bl)]:
# #         cv2.line(img, tuple(p1.astype(int)), tuple(p2.astype(int)), (0, 255, 0), 2)

# #     cv2.imwrite(out_path, img)
# #     return house_dict

import cv2
import numpy as np
import os
import uuid
import tempfile

# =========================
# CONFIG
# =========================
# We now look for multiple templates to handle Dark vs Light square backgrounds
WHITE_ROOK_TEMPLATES = [
    os.path.join("images", "white_rock.png"),
    os.path.join("images", "white_rock_alt.png") # Light square version
]
BLACK_ROOK_TEMPLATES = [
    os.path.join("images", "black_rock.png"),
    os.path.join("images", "black_rock_alt.png") # Light square version
]

TEMP_DIR = tempfile.gettempdir()

# =========================
# ROOK DETECTION
# =========================
def find_rooks(board_img, template_paths, threshold=0.70):
    """
    Searches for rooks using multiple templates (e.g. dark sq and light sq).
    Returns a list of (x, y) center coordinates.
    """
    all_centers = []
    
    # Try each template (Dark background, Light background)
    for t_path in template_paths:
        if not os.path.exists(t_path):
            continue
            
        template = cv2.imread(t_path)
        if template is None:
            continue

        result = cv2.matchTemplate(board_img, template, cv2.TM_CCOEFF_NORMED)
        h, w = template.shape[:2]
        
        # Find all matches above threshold
        points = np.where(result >= threshold)
        
        for pt in zip(*points[::-1]):
            cx = pt[0] + w // 2
            cy = pt[1] + h // 2
            all_centers.append((cx, cy))

    # Remove duplicates (detections that are very close to each other)
    unique_centers = []
    for cx, cy in all_centers:
        found_close = False
        for ux, uy in unique_centers:
            if np.linalg.norm(np.array((cx, cy)) - np.array((ux, uy))) < 20:
                found_close = True
                break
        if not found_close:
            unique_centers.append((cx, cy))
            
    return unique_centers

# =========================
# MAIN ENTRY
# =========================
def main(board_img_path, out_path=None, side="white"):
    if side not in ("white", "black"):
        raise ValueError("side must be 'white' or 'black'")

    board_img = cv2.imread(board_img_path)
    if board_img is None:
        raise FileNotFoundError(f"Board image not found: {board_img_path}")

    print(f"[Rook Detection] Scanning for rooks...")

    white_rooks = find_rooks(board_img, WHITE_ROOK_TEMPLATES)
    black_rooks = find_rooks(board_img, BLACK_ROOK_TEMPLATES)

    print(f"   > Found {len(white_rooks)} White Rooks")
    print(f"   > Found {len(black_rooks)} Black Rooks")

    all_rooks = [(pt, "white") for pt in white_rooks] + [(pt, "black") for pt in black_rooks]

    # We need exactly 4 corners. If we found more (e.g. promoted rooks), we filter for corners later.
    if len(all_rooks) < 4:
        raise RuntimeError(f"Found {len(all_rooks)}/4 rooks. Need both Dark and Light square versions!")

    # Sort by Y to separate top/bottom (Black/White sides)
    all_rooks.sort(key=lambda r: r[0][1])
    
    # Top 2 rooks (could be White or Black depending on side)
    top_row = all_rooks[:2]
    # Bottom 2 rooks
    bottom_row = all_rooks[-2:]

    # Sort left/right
    top_left = sorted(top_row, key=lambda r: r[0][0])[0]
    top_right = sorted(top_row, key=lambda r: r[0][0])[-1]
    bottom_left = sorted(bottom_row, key=lambda r: r[0][0])[0]
    bottom_right = sorted(bottom_row, key=lambda r: r[0][0])[-1]

    corners = {
        "top_left": top_left[0],
        "top_right": top_right[0],
        "bottom_left": bottom_left[0],
        "bottom_right": bottom_right[0],
    }

    if out_path is None:
        out_path = os.path.join(TEMP_DIR, f"board_rooks_{uuid.uuid4().hex}.png")

    house_dict = draw_board(board_img, corners, out_path, side)

    return out_path, house_dict

# =========================
# BOARD GEOMETRY
# =========================
def draw_board(img, corners, out_path, side):
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

    for rank in range(8):      # 0 bottom -> 7 top
        for file in range(8):  # 0 left -> 7 right

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

    # Draw board outline
    for p1, p2 in [(bl, br), (br, tr), (tr, tl), (tl, bl)]:
        cv2.line(img, tuple(p1.astype(int)), tuple(p2.astype(int)), (0, 255, 0), 2)

    cv2.imwrite(out_path, img)
    return house_dict

# import cv2
# import numpy as np
# import os
# import uuid
# import tempfile

# # =========================
# # CONFIG
# # =========================
# WHITE_ROOK_TEMPLATES = [
#     os.path.join("images", "templates", "white_rock", "white_rock.png"),
#     os.path.join("images", "white_rock.png"), # Fallback
# ]
# BLACK_ROOK_TEMPLATES = [
#     os.path.join("images", "templates", "black_rock", "black_rock.png"),
#     os.path.join("images", "black_rock.png"), # Fallback
# ]

# TEMP_DIR = tempfile.gettempdir()

# # =========================
# # ROOK DETECTION
# # =========================
# def find_rooks_by_color(board_img, template_paths, threshold=0.8):
#     """
#     Finds rooks of a specific color and returns their centers.
#     """
#     all_centers = []
    
#     for t_path in template_paths:
#         if not os.path.exists(t_path):
#             continue
            
#         template = cv2.imread(t_path)
#         if template is None:
#             continue

#         # Using a slightly higher threshold to reduce false positives
#         result = cv2.matchTemplate(board_img, template, cv2.TM_CCOEFF_NORMED)
#         h, w = template.shape[:2]
        
#         points = np.where(result >= threshold)
#         for pt in zip(*points[::-1]):
#             cx = pt[0] + w // 2
#             cy = pt[1] + h // 2
#             all_centers.append((cx, cy))

#     # Remove duplicates (distance < 40px)
#     unique_centers = []
#     for cx, cy in all_centers:
#         found_close = False
#         for ux, uy in unique_centers:
#             if np.linalg.norm(np.array((cx, cy)) - np.array((ux, uy))) < 40:
#                 found_close = True
#                 break
#         if not found_close:
#             unique_centers.append((cx, cy))
            
#     return unique_centers

# def get_best_pair(rooks):
#     """
#     Given a list of rooks, find the pair that is furthest apart horizontally (The Corners).
#     Returns (left_rook, right_rook)
#     """
#     if len(rooks) < 2:
#         return None
    
#     # Sort by X coordinate
#     rooks.sort(key=lambda p: p[0])
    
#     # The corner rooks are simply the leftmost and rightmost
#     left_rook = rooks[0]
#     right_rook = rooks[-1]
    
#     return left_rook, right_rook

# # =========================
# # MAIN ENTRY
# # =========================
# def main(board_img_path, out_path=None, side="white"):
#     board_img = cv2.imread(board_img_path)
#     if board_img is None:
#         raise FileNotFoundError(f"Board image not found: {board_img_path}")

#     # 1. Find all potential rooks
#     white_rooks = find_rooks_by_color(board_img, WHITE_ROOK_TEMPLATES, threshold=0.65)
#     black_rooks = find_rooks_by_color(board_img, BLACK_ROOK_TEMPLATES, threshold=0.70)

#     print(f"[Rook Detection] Raw count -> White: {len(white_rooks)} | Black: {len(black_rooks)}")

#     # 2. Filter for the best 2 (Corners)
#     white_pair = get_best_pair(white_rooks)
#     black_pair = get_best_pair(black_rooks)

#     if not white_pair or not black_pair:
#         raise RuntimeError("Could not find at least 2 rooks of each color!")

#     # 3. Assign Top/Bottom based on Side
#     # If playing WHITE: Black is Top, White is Bottom
#     # If playing BLACK: White is Top, Black is Bottom
#     if side == "white":
#         top_pair = black_pair
#         bottom_pair = white_pair
#     else:
#         top_pair = white_pair
#         bottom_pair = black_pair

#     # 4. Define Corners
#     corners = {
#         "top_left": top_pair[0],     # Leftmost of top pair
#         "top_right": top_pair[1],    # Rightmost of top pair
#         "bottom_left": bottom_pair[0],  # Leftmost of bottom pair
#         "bottom_right": bottom_pair[1], # Rightmost of bottom pair
#     }

#     if out_path is None:
#         out_path = os.path.join(TEMP_DIR, f"board_rooks_{uuid.uuid4().hex}.png")

#     house_dict = draw_board(board_img, corners, out_path, side)

#     return out_path, house_dict

# # =========================
# # BOARD GEOMETRY
# # =========================
# def draw_board(img, corners, out_path, side):
#     bl = np.array(corners["bottom_left"], dtype=float)
#     br = np.array(corners["bottom_right"], dtype=float)
#     tr = np.array(corners["top_right"], dtype=float)
#     tl = np.array(corners["top_left"], dtype=float)

#     house_dict = {}

#     for rank in range(8):      # 0 bottom -> 7 top
#         for file in range(8):  # 0 left -> 7 right

#             u = file / 7.0
#             v = rank / 7.0

#             p_bottom = bl * (1 - u) + br * u
#             p_top = tl * (1 - u) + tr * u
#             cx, cy = (p_bottom * (1 - v) + p_top * v).astype(int)

#             if side == "white":
#                 file_label = chr(ord("A") + file)
#                 rank_label = str(rank + 1)
#             else:
#                 file_label = chr(ord("H") - file)
#                 rank_label = str(8 - rank)

#             square = f"{file_label}{rank_label}"
            
#             # Box size estimate
#             square_w = np.linalg.norm(br - bl) / 8
#             square_h = np.linalg.norm(tl - bl) / 8
#             half_w = square_w * 0.5
#             half_h = square_h * 0.5

#             x1 = int(cx - half_w)
#             y1 = int(cy - half_h)
#             x2 = int(cx + half_w)
#             y2 = int(cy + half_h)

#             house_dict[square] = (x1, y1, x2, y2)
#             cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 1)

#     cv2.imwrite(out_path, img)
#     return house_dict