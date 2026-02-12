import cv2
import numpy as np
from ultralytics import YOLO
import os
from icecream import ic


class YoloHandler:
    # def __init__(
    #     self,
    #     seg_model_path="segmentation_model.pt",
    #     piece_model_path="chess_piece_detection_model_kartik.pt",
    # ):
    #     print(
    #         f"[YOLO] Loading models...\n  - Seg: {seg_model_path}\n  - Piece: {piece_model_path}"
    #     )
    #     self.seg_model = YOLO(seg_model_path)
    #     self.piece_model = YOLO(piece_model_path)
    #     self.img_size_seg = 416
    #     self.img_size_piece = 640
    def __init__(
        self,
        seg_model_path="segmentation_model.pt",
        piece_model_path="chess_piece_detection_model_kartik.pt",
        ui_model_path="yolo_model_final.pt",
        login_model_path="login.pt",
    ):
        ic("YOLO: Loading models...")
        self.seg_model = YOLO(seg_model_path)
        self.piece_model = YOLO(piece_model_path)
        self.ui_model = YOLO(ui_model_path)
        self.login_model = YOLO(login_model_path)

        self.img_size_seg = 416
        self.img_size_piece = 640
        self.img_size_ui = 640
        self.img_size_login = 960
        ######################################################################

    def detect_ui_elements(self, screenshot_img):
        """
        Runs the UI model to find: play_button, new_game, game_review, send_message, board_loaded.
        """
        # Run inference on the 3rd model
        results = self.ui_model(
            screenshot_img, imgsz=self.img_size_ui, conf=0.1, verbose=False
        )
        result = results[0]

        detections = []
        for box in result.boxes:
            cls_id = int(box.cls[0])
            name = result.names[cls_id]
            conf = float(box.conf[0])

            # Get Box Coordinates
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())

            # Calculate Center (for easy clicking later)
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)

            detections.append(
                {
                    "name": name,
                    "box": (x1, y1, x2, y2),
                    "center": (center_x, center_y),
                    "conf": conf,
                }
            )

        return detections

    def detect_login_elements(self, screenshot_img):
        """
        Runs the Login model to find: login_one, username, password, login_two, verification.
        Returns a list of detections with centers for clicking.
        """
        # Run inference on the login model
        results = self.login_model(
            screenshot_img, imgsz=self.img_size_login, conf=0.1, verbose=False
        )
        result = results[0]

        detections = []
        for box in result.boxes:
            cls_id = int(box.cls[0])
            name = result.names[cls_id]
            conf = float(box.conf[0])

            # Get Box Coordinates
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())

            # Calculate Center (for easy clicking later)
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)

            detections.append(
                {
                    "name": name,
                    "box": (x1, y1, x2, y2),
                    "center": (center_x, center_y),
                    "conf": conf,
                }
            )

        return detections

    ###############################################################

    def get_board_from_screenshot(self, screenshot_path):
        """
        Detects the chess board in a full screenshot.
        Returns:
            cropped_board_img (numpy array),
            offset (tuple x,y of the top-left corner on screen)
        """
        results = self.seg_model(
            screenshot_path, imgsz=self.img_size_seg, conf=0.5, verbose=False
        )
        result = results[0]

        if len(result.boxes) == 0:
            raise RuntimeError("No chess board detected in screenshot.")

        # Get the first detection (assuming one board)
        box = result.boxes.xyxy[0].cpu().numpy()
        x1, y1, x2, y2 = map(int, box)

        # Load original image to crop
        img = cv2.imread(screenshot_path)
        if img is None:
            raise FileNotFoundError(f"Could not read screenshot: {screenshot_path}")

        cropped_board = img[y1:y2, x1:x2]
        ic("YOLO: Board detected at screen coords:", x1, y1)

        return cropped_board, (x1, y1)

    def analyze_setup(self, board_img):
        """
        Detects pieces on the cropped board to determine:
        1. The grid (house_dict) via Rooks
        2. The playing side via Kings

        Returns:
            house_dict, side ('white' or 'black')
        """
        results = self.piece_model(
            board_img, imgsz=self.img_size_piece, conf=0.3, verbose=False
        )
        result = results[0]

        rooks = []
        kings = []

        # Parse detections
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = result.names[class_id].lower()

            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            if "rook" in class_name or "rock" in class_name:
                rooks.append((cx, cy, class_name))

            if "king" in class_name:
                kings.append((cx, cy, class_name))

        # --- 1. DETERMINE SIDE ---
        # Logic: If White King is in the lower half of the image (high Y), we are White.
        h, w = board_img.shape[:2]
        side = None

        # Try to find specific white/black king labels first
        white_king = next((k for k in kings if "white" in k[2]), None)
        black_king = next((k for k in kings if "black" in k[2]), None)

        if white_king:
            _, y, _ = white_king
            side = "white" if y > h / 2 else "black"
        elif black_king:
            _, y, _ = black_king
            side = "black" if y > h / 2 else "white"
        else:
            # Fallback if labels are just 'king' (ambiguous without color training),
            # assume standard setup or wait for better detection.
            # Defaulting to White is risky, but standard.
            print(
                "[YOLO Warning] Kings not clearly distinguished, defaulting to White calculation."
            )
            side = "white"

        # --- 2. BUILD GRID FROM ROOKS ---
        if len(rooks) < 4:
            print(f"[YOLO Error] Only {len(rooks)} rooks found. Need 4 corners.")
            # Fallback: If we can't find 4 rooks, we can't build a reliable grid safely
            # without making assumptions about board edges.
            return None, side

        # Sort rooks to find corners
        rooks_sorted = sorted(rooks, key=lambda r: r[1])  # Sort by Y
        top = rooks_sorted[:2]
        bottom = rooks_sorted[-2:]

        # Sort left/right
        top_left = min(top, key=lambda r: r[0])
        top_right = max(top, key=lambda r: r[0])
        bottom_left = min(bottom, key=lambda r: r[0])
        bottom_right = max(bottom, key=lambda r: r[0])

        corners = {
            "bl": np.array([bottom_left[0], bottom_left[1]], dtype=float),
            "br": np.array([bottom_right[0], bottom_right[1]], dtype=float),
            "tl": np.array([top_left[0], top_left[1]], dtype=float),
            "tr": np.array([top_right[0], top_right[1]], dtype=float),
        }

        # Calculate Grid
        # Estimate square size
        square_w = np.linalg.norm(corners["br"] - corners["bl"]) / 7
        square_h = np.linalg.norm(corners["tl"] - corners["bl"]) / 7

        half_w = square_w * 0.45
        half_h = square_h * 0.45

        house_dict = {}

        for rank in range(8):  # 0 bottom -> 7 top
            for file in range(8):  # 0 left -> 7 right
                u = file / 7.0
                v = rank / 7.0

                # Bilinear interpolation for the center
                p_bottom = corners["bl"] * (1 - u) + corners["br"] * u
                p_top = corners["tl"] * (1 - u) + corners["tr"] * u
                cx, cy = (p_bottom * (1 - v) + p_top * v).astype(int)

                # Determine square label
                if side == "white":
                    file_label = chr(ord("A") + file)
                    rank_label = str(rank + 1)
                else:
                    file_label = chr(ord("H") - file)
                    rank_label = str(8 - rank)

                square_key = f"{file_label}{rank_label}"

                # Define box
                x1 = int(cx - half_w)
                y1 = int(cy - half_h)
                x2 = int(cx + half_w)
                y2 = int(cy + half_h)

                house_dict[square_key] = (x1, y1, x2, y2)

        return house_dict, side

    def save_debug_grid(self, board_img, house_dict, out_path):
        debug_img = board_img.copy()
        for sq, (x1, y1, x2, y2) in house_dict.items():
            cv2.rectangle(debug_img, (x1, y1), (x2, y2), (0, 255, 0), 1)
            cv2.putText(
                debug_img,
                sq,
                (x1 + 2, y1 + 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.3,
                (0, 0, 255),
                1,
            )
        cv2.imwrite(out_path, debug_img)
