
import cv2
import cv2
import numpy as np
import os


class KingDetector:
    def __init__(self, image_folder="images", template_name="white_king.png", retina_scale=2):
        self.image_folder = image_folder
        self.template_name = template_name
        self.template_path = os.path.join(self.image_folder, self.template_name)
        self.template = cv2.imread(self.template_path, cv2.IMREAD_COLOR)
        if self.template is None:
            raise FileNotFoundError(f"Template image not found at {self.template_path}")
        self.retina_scale = retina_scale

    def detect_king(self, board_image_path, threshold=0.8):
        board_img = cv2.imread(board_image_path, cv2.IMREAD_COLOR)
        if board_img is None:
            raise FileNotFoundError(f"Board image not found at {board_image_path}")

        result = cv2.matchTemplate(board_img, self.template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val >= threshold:
            king_x_unscaled = max_loc[0] + self.template.shape[1] // 2
            king_y_unscaled = max_loc[1] + self.template.shape[0] // 2
            king_x_scaled = king_x_unscaled / self.retina_scale
            king_y_scaled = king_y_unscaled / self.retina_scale
            return (king_x_scaled, king_y_scaled), (king_x_unscaled, king_y_unscaled), max_val
        else:
            return None, None, max_val
