import os
import subprocess
import sys
from pyvirtualdisplay import Display
from icecream import ic

ic("SESSION: Starting virtual display (Headless Mode)")
display = Display(visible=0, size=(1920, 1080), backend="xvfb")
display.start()
os.environ["DISPLAY"] = f":{display.display}"
ic("DISPLAY is:", os.environ["DISPLAY"])
ic(display)

ic("SESSION: Starting Fluxbox Window Manager...")
subprocess.Popen(["fluxbox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


import time
import random
import traceback
import math
import uuid
import cv2
import numpy as np
import pyautogui
import webbrowser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from icecream import ic
from stockfish import Stockfish
import pytesseract

# Custom Modules
from config.config import *
from core.color_detection import is_our_turn_finished
from core.yolo_handler import YoloHandler
from core.logger import ChessLogger
from utils.vision import (
    is_game_over_ocr,
    get_ui_element,
    get_board_state_from_yolo,
    square_center,
    board_state_to_fen,
)
from utils.game_actions import perform_login_sequence, human_move_to
from utils.system_utils import (
    load_engine,
    get_messages_from_file,
    send_completion_email,
    load_yolo,
)

logger = ChessLogger()

stockfish = load_engine()
yolo_handler = load_yolo()


ic("GAME: Starting continuous chess automation...")
ic("CONFIG: Active Account", CHESS_USERNAME)
GAMES_LIMIT = random.randint(5, 15)
ic("CONFIG: Session Limit", GAMES_LIMIT)
game_number = 0

logger.log(
    event="SESSION", message=f"Starting continous chess automtion", game_num=game_number
)

try:
    while True:
        game_number += 1
        side = "unknown"
        i = 0
        fen = "unknown"
        best_move = "none"
        print(f"\n{'=' * 60}")

        ic("GAME: Starting Game", game_number)

        logger.log(event="GAME", message=f"Starting Game", game_num=game_number)

        print(f"{'=' * 60}\n")

        # =========================
        # OPEN WEBSITE
        # =========================
        if game_number == 1:
            try:
                ic("Opening chess.com", URL)

                logger.log(
                    event="GAME",
                    message=f"Opening Chess.com, {URL}",
                    game_num=game_number,
                )

                ic("Opening URL", URL)
                env = os.environ.copy()

                subprocess.Popen(
                    [
                        "google-chrome",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--use-gl=swiftshader",
                        "--disable-features=VizDisplayCompositor",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-default-apps",
                        "--start-maximized",
                        "--window-position=0,0",
                        "--window-size=1920,1080",
                        "--app=https://www.chess.com/play/online/new",
                        URL,
                    ],
                    env=env,
                )
                # subprocess.Popen(
                #     [
                #         "chromium-browser",
                #         "--no-sandbox",
                #         "--disable-dev-shm-usage",
                #         "--disable-gpu",
                #         "--disable-software-rasterizer",
                #         "--kiosk",
                #         "--no-first-run",
                #         "--log-level=3",
                #         "--no-default-browser-check",
                #         "--window-position=0,0",
                #         "--window-size=1440,900",
                #         "--force-device-scale-factor=1",
                #         f"--app={URL}",
                #     ]
                # )
                ic("DEBUG: Waiting 15 seconds for page to load...")
                time.sleep(15)
                ic("DEBUG: Page load complete")
                ########################
                screen1 = cv2.cvtColor(
                    np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR
                )
                cv2.imwrite("login.png", screen1)
                ic("DEBUG: Saved login.png")
                ####################
                perform_login_sequence(yolo_handler)

            except Exception as e:
                ic("ERROR: Website access failed", e)

                logger.log(
                    event="ERROR",
                    message=f"Failed to open website, {e}",
                    game_num=game_number,
                )

                traceback.print_exc()
                sys.exit(1)

        # =========================
        # 1. UI STATE & START GAME
        # =========================
        ic("VISION: checking UI state...")

        logger.log(event="VISION", message=f"Checking UI State", game_num=game_number)

        board_loaded = False

        while not board_loaded:
            # Capture screen
            screen = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)

            # =================================
            cv2.imwrite("debug_what_yolo_sees.png", screen)
            ic("DEBUG: Saved debug_what_yolo_sees.png")
            # ================================
            login_scan = yolo_handler.detect_login_elements(screen)
            #  Run YOLO UI Detection
            ui_detections = yolo_handler.detect_ui_elements(screen)

            # Check for specific buttons/states
            play_btn = get_ui_element(ui_detections, "play_button")
            new_game_btn = get_ui_element(ui_detections, "new_game")
            board_state = get_ui_element(ui_detections, "board_loaded")

            # LOGIC
            if board_state:
                ic("VISION: Board loaded! Starting game...")

                logger.log(
                    event="VISION", message=f"Board Loaded", game_num=game_number
                )

                board_loaded = True
                break

            elif play_btn:
                ic("VISION: Found 'Play' button - clicking...")

                logger.log(
                    event="VISION", message=f"Play button found", game_num=game_number
                )

                pyautogui.click(play_btn[0] / RETINA_SCALE, play_btn[1] / RETINA_SCALE)
                time.sleep(4)
                # break

            else:
                time.sleep(0.5)

        # =========================
        # INITIAL BOARD SNAP
        # =========================
        try:
            snap_id = uuid.uuid4().hex
            board_path = os.path.join(TEMP_DIR, f"board_{uuid.uuid4().hex}.png")
            ic("Taking board snapshot", board_path)
            screenshot = pyautogui.screenshot()
            screenshot.save(board_path)

            if not os.path.exists(board_path):
                ic("ERROR: Failed to save initial board snapshot")
                continue  # Try next game
            ic("DEBUG: Board snapshot saved successfully")

        except Exception as e:
            ic("ERROR: Failed to capture initial board snap:", e)

            logger.log(
                event="ERROR",
                message=f"Failed to capture initial board snap, {e}",
                game_num=game_number,
            )

            traceback.print_exc()
            continue  # Try next game

        board_img = None
        offset_x = 0
        offset_y = 0
        house_dict = None
        side = None

        setup_success = False

        ic("VISION: Analyzing board setup (Max 3 attempts)...")

        logger.log(
            event="VISION",
            message=f"Analyzing board (Max 3 attempts)",
            game_num=game_number,
        )

        time.sleep(2)

        for attempt in range(3):
            try:
                snap_path = os.path.join(TEMP_DIR, f"setup_{uuid.uuid4().hex}.png")
                pyautogui.screenshot().save(snap_path)

                try:
                    board_img, (offset_x, offset_y) = (
                        yolo_handler.get_board_from_screenshot(snap_path)
                    )
                except RuntimeError:
                    ic(
                        f"Board detection failed. Retry {attempt + 1}/3",
                        "Waiting 2s...",
                    )
                    time.sleep(2)
                    continue

                ic("Board Offset", offset_x, offset_y)

                house_dict, side = yolo_handler.analyze_setup(board_img)

                if not house_dict or not side:
                    ic(
                        f"Grid/Side detection failed. Attempt {attempt + 1}/3",
                        "Retrying in 2s...",
                    )

                    # logger.log(
                    #     event="ERROR",
                    #     message=f"Grid/Side detection failed. Attempt {attempt + 1}/3",
                    #     game_num=game_number,
                    # )
                    time.sleep(2)
                    continue

                if len(house_dict) != 64:
                    ic(
                        f"ERROR: house_dict incomplete ({len(house_dict)}/64). Retrying..."
                    )
                    # logger.log(
                    #     event="ERROR",
                    #     message=f"House Dictionary Incomplete ({len(house_dict)}/64) Attempt {attempt + 1}/3.",
                    #     game_num=game_number,
                    # )
                    time.sleep(2)
                    continue

                setup_success = True
                break

            except Exception as e:
                ic(f"Setup attempt {attempt + 1} crashed", e)

                logger.log(
                    event="ERROR",
                    message=f"Setup attempt {attempt + 1} crashed: {e}",
                    game_num=game_number,
                )

                time.sleep(2)

        if not setup_success:
            ic(
                "ERROR: Could not set up board after 3 attempts. Restarting game loop..."
            )

            logger.log(
                event="ERROR",
                message=f"Could not set up board after 3 attempts. Restarting game loop...",
                game_num=game_number,
            )

            continue

        ic("Side Assigned", side.upper())

        logger.log(
            event="GAME",
            message=f"Playing as {side.upper()}",
            game_num=game_number,
            side=side,
        )

        game_ended = False
        last_move_coordinates = None
        last_fen = None
        same_fen_counter = 0
        invalid_kings_counter = 0

        try:
            for i in range(1, 9999):
                try:
                    time.sleep(0.5)
                    full_screenshot = pyautogui.screenshot()

                    full_img = cv2.cvtColor(
                        np.array(full_screenshot), cv2.COLOR_RGB2BGR
                    )

                    h, w = board_img.shape[:2]
                    current_board_crop = full_img[
                        offset_y : offset_y + h, offset_x : offset_x + w
                    ]

                    ui_scan = yolo_handler.detect_ui_elements(full_img)

                    detected_names = [d["name"] for d in ui_scan]
                    if detected_names:
                        # print(f"[DEBUG UI] Detected elements: {detected_names}")
                        pass

                    new_game_btn = get_ui_element(ui_scan, "new_game")
                    game_review_btn = get_ui_element(ui_scan, "game_review")
                    aborted_button = get_ui_element(ui_scan, "aborted")

                    if game_review_btn or aborted_button:
                        ic(
                            "GAME: Game Finished",
                            game_number,
                            "Reason: Game Review/Aborted detected",
                        )

                        logger.log(
                            event="VISION",
                            message=f"Game #{game_number} finished (Game Review or Game Aborted detected).",
                            game_num=game_number,
                            side=side,
                            turn_num=i,
                        )

                        game_ended = True

                    elif is_game_over_ocr(full_img):
                        ic("Game Finished (OCR)", game_number)

                        scr = cv2.cvtColor(
                            np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR
                        )

                        cv2.imwrite("OCR.png", scr)
                        ic("DEBUG: OCR.png")

                        logger.log(
                            event="OCR",
                            message=f"Game #{game_number} finished (OCR Detected).",
                            game_num=game_number,
                            side=side,
                            turn_num=i,
                        )

                        game_ended = True

                    if game_ended:
                        if new_game_btn:
                            ic(
                                "VISION: Game confirmed over. Clicking 'New Game' immediately..."
                            )

                            logger.log(
                                event="VISION",
                                message=f"Game over confirmed clicking New Game button",
                                game_num=game_number,
                                side=side,
                                turn_num=i,
                            )

                            pyautogui.click(
                                new_game_btn[0] / RETINA_SCALE,
                                new_game_btn[1] / RETINA_SCALE,
                            )

                            time.sleep(1)

                        break

                    board_offset = (offset_x, offset_y)

                    if is_our_turn_finished(full_img, last_move_coordinates):
                        ui_scan2 = yolo_handler.detect_ui_elements(full_img)
                        game_review_btn = get_ui_element(ui_scan2, "game_review")
                        aborted_button = get_ui_element(ui_scan2, "aborted")
                        new_game_btn = get_ui_element(ui_scan2, "new_game")

                        if (
                            game_review_btn
                            or aborted_button
                            or is_game_over_ocr(full_img)
                        ):
                            game_ended = True
                            break
                        ui_scan = yolo_handler.detect_ui_elements(full_img)
                        msg_icon = get_ui_element(ui_scan, "send_message")

                        if msg_icon and random.random() < MESSAGE_PROBABILITY:
                            ic("VISION: Opportunity to send message detected...")

                            # logger.log(
                            #     event="YOLO",
                            #     message=f"Opportunity to send message detected",
                            #     game_num=game_number,
                            #     side=side,
                            #     turn_num=i,
                            # )

                            pyautogui.click(
                                msg_icon[0] / RETINA_SCALE, msg_icon[1] / RETINA_SCALE
                            )
                            time.sleep(0.2)

                            current_messages = get_messages_from_file()
                            msg = random.choice(current_messages)
                            ic("VISION: Sending message", msg)

                            logger.log(
                                event="VISION",
                                message=f"Opportunity to send message detected, Sending: {msg}",
                                game_num=game_number,
                                side=side,
                                turn_num=i,
                            )

                            pyautogui.typewrite(msg, interval=0.05)
                            pyautogui.press("enter")

                            time.sleep(1)

                        continue

                    print(f"\n{'=' * 50}")
                    ic("Turn", i, "Our move", side)
                    print(f"{'=' * 50}")

                    # =========================
                    # READ BOARD
                    # =========================
                    try:
                        board_state = get_board_state_from_yolo(
                            yolo_handler, current_board_crop, house_dict, conf=0.5
                        )
                        fen = board_state_to_fen(board_state, side)

                        if fen.count("k") != 1 or fen.count("K") != 1:
                            #########################################################

                            cv2.imwrite("invalid_kings_board.png", current_board_crop)
                            from ultralytics import YOLO

                            model = YOLO(
                                "/home/ubuntu/chess-automation/chess-automation/models/chess_piece_detection_model_kartik.pt"
                            )
                            results = model(
                                "/home/ubuntu/chess-automation/chess-automation/invalid_kings_board.png",
                                imgsz=640,
                                conf=0.5,
                            )

                            # cv2.imwrite("output_kings.png", results[0].show())
                            imz = results[0].plot()  # returns a NumPy array
                            cv2.imwrite("output_kings.png", imz)
                            #########################################################
                            invalid_kings_counter += 1
                            ic(
                                f"ERROR: Invalid Kings {invalid_kings_counter}/{MAX_INVALID_KINGS}"
                            )

                            if invalid_kings_counter >= MAX_INVALID_KINGS:
                                logger.log(
                                    event="SHUTDOWN",
                                    message=f"Invalid Kings detected {MAX_INVALID_KINGS} times. Shuting Down.",
                                    game_num=game_number,
                                    side=side,
                                    turn_num=i,
                                    fen=fen,
                                )
                                try:
                                    display.stop()
                                except:
                                    pass
                                subprocess.run(["init", "0"])
                                sys.exit(0)

                            # game_ended = True
                            # ui_scan = yolo_handler.detect_ui_elements(full_img)
                            # new_game_btn = get_ui_element(ui_scan, "new_game")

                            # if new_game_btn:
                            #     pyautogui.click(
                            #         new_game_btn[0] / RETINA_SCALE,
                            #         new_game_btn[1] / RETINA_SCALE,
                            #     )
                            #     time.sleep(2)

                            # break

                            ic(
                                "ERROR: Invalid Kings",
                                fen.count("K"),
                                fen.count("k"),
                                "Retrying...",
                            )
                            print("+" * 60)
                            ic("DEBUG: RAW BOARD STATE", board_state)
                            logger.log(
                                event="ERROR",
                                message=f"Invalid Kings Detected",
                                game_num=game_number,
                                side=side,
                                turn_num=i,
                                fen=fen,
                            )

                            continue
                        else:
                            invalid_kings_counter = 0

                        # board_state = get_board_state_from_yolo(
                        #     yolo_handler, current_board_crop, house_dict, conf=0.1
                        # )
                        # fen = board_state_to_fen(board_state, side)

                        # if fen.count("k") != 1 or fen.count("K") != 1:
                        #     ic("ERROR: Invalid Kings")

                        #     logger.log(
                        #         event="ERROR",
                        #         message=f"Invalid Kings",
                        #         game_num=game_number,
                        #         side=side,
                        #         turn_num=i,
                        #         fen=fen,
                        #     )
                        if fen == last_fen:
                            same_fen_counter += 1
                            ic(f"WARNING: Same FEN {same_fen_counter}/{MAX_SAME_FEN}")
                        else:
                            last_fen = fen
                            same_fen_counter = 0

                        if same_fen_counter >= MAX_SAME_FEN:
                            logger.log(
                                event="SHUTDOWN",
                                message=f"Same FEN detected {MAX_SAME_FEN} times. Shuting Down.",
                                game_num=game_number,
                                side=side,
                                turn_num=i,
                                fen=fen,
                            )
                            try:
                                display.stop()
                            except:
                                pass
                            subprocess.run(["init", "0"])
                            sys.exit(0)
                            # logger.log(
                            #     event="ERROR",
                            #     message=f"Same FEN detected {MAX_SAME_FEN} times. Restarting game.",
                            #     game_num=game_number,
                            #     side=side,
                            #     turn_num=i,
                            #     fen=fen,
                            # )

                            # game_ended = True

                            # # Scan UI and click New Game
                            # ui_scan = yolo_handler.detect_ui_elements(full_img)
                            # new_game_btn = get_ui_element(ui_scan, "new_game")

                            # if new_game_btn:
                            #     pyautogui.click(
                            #         new_game_btn[0] / RETINA_SCALE,
                            #         new_game_btn[1] / RETINA_SCALE,
                            #     )
                            #     time.sleep(2)

                            # break

                        piece_count = sum(
                            1 for v in board_state.values() if v is not None
                        )
                        ic("Board state detected", piece_count)
                        ic(fen)

                        # logger.log(
                        #     event="GAME",
                        #     message=f"Fen generated",
                        #     game_num=game_number,
                        #     side=side,
                        #     turn_num=i,
                        #     fen=fen,
                        # )

                    except Exception as e:
                        ic("ERROR: Board processing failed:", e)
                        cv2.imwrite("board_procession_failed.png", current_board_crop)
                        logger.log(
                            event="ERROR",
                            message=f"Board processing failed, {e}",
                            game_num=game_number,
                            side=side,
                            turn_num=i,
                            fen=fen,
                        )

                        traceback.print_exc()
                        continue

                    # try:
                    #     stockfish.set_fen_position(fen)
                    #     best_move = stockfish.get_best_move()
                    #     ic("Stockfish Calculation", best_move)

                    #     logger.log(
                    #         event="GAME",
                    #         message=f"Best Move, {best_move}",
                    #         game_num=game_number,
                    #         side=side,
                    #         turn_num=i,
                    #         fen=fen,
                    #         move=best_move,
                    #     )

                    # except Exception as e:
                    #     ic("ERROR: Stockfish engine error", e)

                    #     logger.log(
                    #         event="ERROR",
                    #         message=f"Stockfish crashed, {e}",
                    #         game_num=game_number,
                    #         side=side,
                    #         turn_num=i,
                    #         fen=fen,
                    #         move=best_move,
                    #     )

                    # =========================
                    # STOCKFISH CALCULATION
                    # =========================
                    if not stockfish.is_fen_valid(fen):
                        ic("Stockfish: Skipping Invalid FEN", fen)

                        logger.log(
                            event="ERROR",
                            message=f"Invalid FEN",
                            game_num=game_number,
                            side=side,
                            turn_num=i,
                            fen=fen,
                            move=best_move,
                        )

                        continue

                    try:
                        stockfish.set_fen_position(fen)
                        best_move = stockfish.get_best_move()
                        ic("Stockfish Calculation", best_move)

                        # logger.log(
                        #     event="GAME",
                        #     message=f"Best Move, {best_move}",
                        #     game_num=game_number,
                        #     side=side,
                        #     turn_num=i,
                        #     fen=fen,
                        #     move=best_move,
                        # )

                    except Exception as e:
                        ic("CRITICAL: Stockfish crashed", e)
                        ic("Action: Attempting to restart engine...")

                        logger.log(
                            event="ERROR",
                            message=f"Stockfish Crashed ,{e}, attempting restart",
                            game_num=game_number,
                            side=side,
                            turn_num=i,
                            fen=fen,
                            move=best_move,
                        )

                        try:
                            # 1. Kill old instance to free resources
                            del stockfish

                            # 2. Reload the engine
                            stockfish = load_engine()

                            ic(
                                "Stockfish Recovery",
                                "Restart successful",
                                "Action: Skipping bad frame",
                            )

                            logger.log(
                                event="GAME",
                                message=f"Stockfish restart successful",
                                game_num=game_number,
                                side=side,
                                turn_num=i,
                                fen=fen,
                                move=best_move,
                            )

                            time.sleep(0.5)
                            continue

                        except Exception as e2:
                            ic("CRITICAL: Engine restart failed", e2)

                            logger.log(
                                event="GAME",
                                message=f"Restart failed, {e2}",
                                game_num=game_number,
                                side=side,
                                turn_num=i,
                                fen=fen,
                                move=best_move,
                            )

                            time.sleep(1)
                            continue

                    if not best_move:
                        ic("Stockfish Error: No move returned", fen, side)

                        logger.log(
                            event="ERROR",
                            message=f"Stockfish returned no move",
                            game_num=game_number,
                            side=side,
                            turn_num=i,
                            fen=fen,
                            move=best_move,
                        )

                        continue

                    from_sq = best_move[:2].upper()
                    to_sq = best_move[2:4].upper()

                    if from_sq not in house_dict or to_sq not in house_dict:
                        ic("ERROR: Invalid squares detected", from_sq, to_sq)

                        logger.log(
                            event="ERROR",
                            message=f"Invalid squares, {from_sq} → {to_sq}",
                            game_num=game_number,
                            side=side,
                            turn_num=i,
                            fen=fen,
                            move=best_move,
                        )

                        continue

                    try:
                        fx, fy = square_center(house_dict[from_sq])
                        tx, ty = square_center(house_dict[to_sq])

                        f_box = house_dict[
                            from_sq
                        ]  # (x1, y1, x2, y2) relative to board crop
                        t_box = house_dict[to_sq]

                        # Calculate square width/height dynamically
                        sq_width = f_box[2] - f_box[0]
                        sq_height = f_box[3] - f_box[1]

                        # Use 15% padding instead of hardcoded 10px
                        # This lands in the top-left corner, but safely inside the square
                        padding_x = sq_width * 0.15
                        padding_y = sq_height * 0.15

                        # 1. Calculate Local Coordinates (Top-Left + Padding)
                        safe_fx = f_box[0] + padding_x
                        safe_fy = f_box[1] + padding_y
                        safe_tx = t_box[0] + padding_x
                        safe_ty = t_box[1] + padding_y

                        # 2. Convert to Global Screen Coordinates
                        # We use these EXACT coords for both clicking AND color detection
                        global_safe_fx = safe_fx + offset_x
                        global_safe_fy = safe_fy + offset_y
                        global_safe_tx = safe_tx + offset_x
                        global_safe_ty = safe_ty + offset_y

                        # 3. Apply Retina Scale (Which is 1 on Ubuntu)
                        start_x = global_safe_fx / RETINA_SCALE
                        start_y = global_safe_fy / RETINA_SCALE
                        end_x = global_safe_tx / RETINA_SCALE
                        end_y = global_safe_ty / RETINA_SCALE

                        # 4. Move Mouse
                        pyautogui.moveTo(start_x, start_y)
                        # ... continue with drag ...

                        # 1. Hover over the start piece first (Natural pause)
                        pyautogui.moveTo(start_x, start_y)
                        time.sleep(random.uniform(0.05, 0.15))

                        # 2. Grab the piece
                        pyautogui.mouseDown()

                        # 3. Drag with the curve function
                        human_move_to(start_x, start_y, end_x, end_y)

                        # 4. Release piece
                        pyautogui.mouseUp()

                        # Save SAFE CORNERS for the check
                        last_move_coordinates = (
                            (global_safe_fx, global_safe_fy),
                            (global_safe_tx, global_safe_ty),
                        )

                        ic("SUCCESS: Move executed", from_sq, to_sq)

                        logger.log(
                            event="GAME",
                            message=f"Move executed",
                            game_num=game_number,
                            side=side,
                            turn_num=i,
                            fen=fen,
                            move=best_move,
                        )

                        # Wait 1-2 seconds so the "Game Review" popup has time to appear
                        time.sleep(1)

                        ######################################################################################################
                        # screen2 = cv2.cvtColor(
                        #     np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR
                        # )
                        # cv2.imwrite("move executed.png", screen2)
                        # ic("[DEBUG] Saved login.png")
                        ######################################################################################################

                    except Exception as e:
                        ic("ERROR: Move Execution Failed", e, from_sq, to_sq)

                        logger.log(
                            event="ERROR",
                            message=f"Failed to execute move: {e}",
                            game_num=game_number,
                            side=side,
                            turn_num=i,
                            fen=fen,
                            move=best_move,
                        )

                        continue

                except KeyboardInterrupt:
                    ic("GAME: Interrupted by user")

                    logger.log(
                        event="GAME",
                        message=f"Game interrupted by user",
                        game_num=game_number,
                        side=side,
                        turn_num=i,
                        fen=fen,
                        move=best_move,
                    )

                    sys.exit(0)
                except Exception as e:
                    ic("ERROR: Turn Loop Failure", i, side, e)

                    logger.log(
                        event="ERROR",
                        message=f"Turn {i} failed, {e}",
                        game_num=game_number,
                        side=side,
                        turn_num=i,
                        fen=fen,
                        move=best_move,
                    )

                    traceback.print_exc()
                    continue

            # If we exited the loop without game ending naturally, something went wrong
            if not game_ended:
                ic(
                    "ERROR: Session Anomaly",
                    game_number,
                    "Status: Attempting restart...",
                )

                logger.log(
                    event="ERROR",
                    message=f"Game #{game_number} ended unexpectedly. Attempting to restart",
                    game_num=game_number,
                    side=side,
                    turn_num=i,
                    fen=fen,
                    move=best_move,
                )

                continue

        except KeyboardInterrupt:
            ic("GAME0: Interrupted by user")

            logger.log(
                event="GAME",
                message=f"Game interrupted by user",
                game_num=game_number,
                side=side,
                turn_num=i,
                fen=fen,
                move=best_move,
            )

            sys.exit(0)
        except Exception as e:
            ic("ERROR: Game Crashed", game_number, e)

            logger.log(
                event="ERROR",
                message=f"Game #{game_number} crashed: {e}",
                game_num=game_number,
                side=side,
                turn_num=i,
                fen=fen,
                move=best_move,
            )

            traceback.print_exc()
            continue  # Try next game

        if game_number >= GAMES_LIMIT:
            ic("GAME: Session Complete", "Action: Sending summary email")

            logger.log(
                event="GAME",
                message=f"{GAMES_LIMIT} Games finished, sending email",
                game_num=game_number,
                side=side,
                turn_num=i,
                fen=fen,
                move=best_move,
            )

            email_sent = send_completion_email(game_number)

            time.sleep(1)

            # subproces
            subprocess.run(["init", "0"])

            if email_sent:
                ic("SUCCESS: Handover email sent", "Session Finalized")

                logger.log(
                    event="EMAIL",
                    message=f"Email sent successfully",
                    game_num=game_number,
                    side=side,
                    turn_num=i,
                    fen=fen,
                    move=best_move,
                )
            else:
                ic("ERROR: Handover email failed")

                logger.log(
                    event="ERROR",
                    message=f"Failed to send email",
                    game_num=game_number,
                    side=side,
                    turn_num=i,
                    fen=fen,
                    move=best_move,
                )

            ic("SESSION: Stopping virtual display")
            logger.log(
                event="SESSION",
                message=f"Stopping virtual display",
                game_num=game_number,
                side=side,
                turn_num=i,
                fen=fen,
                move=best_move,
            )
            display.stop()
            ic("GAME: Cleanup complete. Exiting.")
            logger.log(
                event="GAME",
                message=f"Cleanup complete, Exiting",
                game_num=game_number,
                side=side,
                turn_num=i,
                fen=fen,
                move=best_move,
            )
            sys.exit(0)


except KeyboardInterrupt:
    ic("GAME: Interrupted by user")

    logger.log(
        event="GAME",
        message=f"Chess automation interrupted by user",
        game_num=game_number,
        side=side,
        turn_num=i,
        fen=fen,
        move=best_move,
    )

except Exception as e:
    ic("ERROR: Main Loop Failure", e)

    logger.log(
        event="ERROR",
        message=f"Critical failure in main loop: {e}",
        game_num=game_number,
        side=side,
        turn_num=i,
        fen=fen,
        move=best_move,
    )

    traceback.print_exc()

finally:
    # =========================
    # CLEANUP
    # =========================
    ic("SESSION: Stopping virtual display")
    logger.log(
        event="SESSION",
        message="Cleanup complete and script exiting",
        game_num=game_number,
    )
    display.stop()
    sys.exit(0)
