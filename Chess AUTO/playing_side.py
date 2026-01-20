import cv2

def detect_playing_side(white_king_pos, board_height):
    """
    Determines playing side based on white king's position.
    If white king is in bottom half (higher y), we are white. If in top half (lower y), we are black.
    Args:
        white_king_pos (tuple): (x, y) position of the white king.
        board_height (int): Height of the chess board in pixels.
    Returns:
        str: 'white' or 'black'
    """
    # y axis: 0 at top, increases downward
    # If king is in bottom half (y > board_height / 2), we are white
    # If king is in top half (y <= board_height / 2), we are black

    _, y = white_king_pos
    if y >= board_height / 2:
        return 'white'
    else:
        return 'black'


def mark_king_on_image(image_path, king_coords, out_path=None, color=(0, 0, 255), radius=30, thickness=4):
    """
    Draws a circle on the king's position in the image and saves it.
    Args:
        image_path (str): Path to the image file.
        king_coords (tuple): (x, y) coordinates of the king (unscaled).
        out_path (str): Path to save the highlighted image. If None, will overwrite input image.
        color (tuple): BGR color for the circle.
        radius (int): Radius of the circle.
        thickness (int): Thickness of the circle.
    Returns:
        str: Path to the saved image (highlighted).
    """
    img = cv2.imread(image_path)
    if img is not None and king_coords:
        center = (int(king_coords[0]), int(king_coords[1]))
        cv2.circle(img, center, radius, color, thickness)
        if out_path is None:
            out_path = image_path
        cv2.imwrite(out_path, img)
        return out_path
    else:
        raise FileNotFoundError("Could not load image or king coordinates invalid.")
