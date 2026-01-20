
import cv2
import numpy as np
import os


class KingDetector:
    def __init__(self, templates_folder="images/templates", retina_scale=1):
        self.templates_folder = templates_folder
        self.retina_scale = retina_scale
        
        # Load both king templates
        self.white_king_path = os.path.join(templates_folder, "white_king", "white_king.png")
        self.black_king_path = os.path.join(templates_folder, "black_king", "black_king.png")
        
        # Load templates as BGR (3 channels) to ensure compatibility
        self.white_king_template = cv2.imread(self.white_king_path, cv2.IMREAD_COLOR)
        self.black_king_template = cv2.imread(self.black_king_path, cv2.IMREAD_COLOR)
        
        if self.white_king_template is None:
            raise FileNotFoundError(f"White king template not found at {self.white_king_path}")
        if self.black_king_template is None:
            raise FileNotFoundError(f"Black king template not found at {self.black_king_path}")

    def detect_king_and_side(self, board_image_path, threshold=0.8):
        """
        Detects king in the BOTTOM HALF of the board only and determines playing side.
        Returns the side we're playing ('white' or 'black') based on which king is found.
        
        Args:
            board_image_path (str): Path to the board screenshot
            threshold (float): Confidence threshold for template matching
            
        Returns:
            tuple: (side, king_coords_scaled, king_coords_unscaled, confidence)
                   where side is 'white' or 'black', or (None, None, None, 0) if no king found
        """
        # Load board image as BGR (3 channels) to match templates
        board_img = cv2.imread(board_image_path, cv2.IMREAD_COLOR)
        if board_img is None:
            raise FileNotFoundError(f"Board image not found at {board_image_path}")

        board_height = board_img.shape[0]
        
        # Only check the BOTTOM HALF (our side)
        bottom_half_start = board_height // 2
        bottom_half = board_img[bottom_half_start:, :]
        
        # Try to detect white king in bottom half
        white_result = cv2.matchTemplate(bottom_half, self.white_king_template, cv2.TM_CCOEFF_NORMED)
        _, white_max_val, _, white_max_loc = cv2.minMaxLoc(white_result)
        
        # Try to detect black king in bottom half
        black_result = cv2.matchTemplate(bottom_half, self.black_king_template, cv2.TM_CCOEFF_NORMED)
        _, black_max_val, _, black_max_loc = cv2.minMaxLoc(black_result)
        
        # Determine which king was found with higher confidence
        if white_max_val >= threshold and white_max_val > black_max_val:
            # White king found in bottom half → we're playing white
            king_x_unscaled = white_max_loc[0] + self.white_king_template.shape[1] // 2
            king_y_unscaled = white_max_loc[1] + self.white_king_template.shape[0] // 2 + bottom_half_start
            king_x_scaled = king_x_unscaled / self.retina_scale
            king_y_scaled = king_y_unscaled / self.retina_scale
            return 'white', (king_x_scaled, king_y_scaled), (king_x_unscaled, king_y_unscaled), white_max_val
            
        elif black_max_val >= threshold and black_max_val > white_max_val:
            # Black king found in bottom half → we're playing black
            king_x_unscaled = black_max_loc[0] + self.black_king_template.shape[1] // 2
            king_y_unscaled = black_max_loc[1] + self.black_king_template.shape[0] // 2 + bottom_half_start
            king_x_scaled = king_x_unscaled / self.retina_scale
            king_y_scaled = king_y_unscaled / self.retina_scale
            return 'black', (king_x_scaled, king_y_scaled), (king_x_unscaled, king_y_unscaled), black_max_val
            
        else:
            # No king detected with sufficient confidence
            max_conf = max(white_max_val, black_max_val)
            return None, None, None, max_conf
