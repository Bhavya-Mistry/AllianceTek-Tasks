# root/utils/system_utils.py
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from stockfish import Stockfish
from icecream import ic
from core.logger import ChessLogger
from config.config import *
from core.yolo_handler import YoloHandler

logger = ChessLogger()


def get_messages_from_file():
    """Reads messages from a text file, returns a default list if file fails."""
    defaults = ["Good luck!", "Nice move!", "Well played!"]

    if not os.path.exists(MESSAGES_FILE):
        ic("WARNING", MESSAGES_FILE, "not found. Using defaults.")
        return defaults

    try:
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            # Read lines, strip whitespace, and filter out empty lines
            lines = [line.strip() for line in f.readlines()]
            valid_messages = [l for l in lines if l]

            if valid_messages:
                return valid_messages
            else:
                return defaults
    except Exception as e:
        ic("ERROR: Failed to read messages file: ", e)
        return defaults


def send_completion_email(game_count):
    ic("EMAIL: Preparing message for", TO_EMAIL)

    # logger.log(event="EMAIL", message=f"Preparing to send message")

    msg = MIMEMultipart()
    msg["Subject"] = f"Chess Automation Complete ({game_count} Games)"
    msg["From"] = MAIL_DEFAULT_SENDER
    msg["To"] = TO_EMAIL
    msg["Cc"] = CC_EMAIL

    body = f"{game_count} Games completed...exiting the game loop"
    msg.attach(MIMEText(body, "plain"))

    # 2. Create a list of all recipients for the SMTP server
    recipients = [TO_EMAIL, CC_EMAIL]

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)

        # 3. Use the list of recipients here
        server.sendmail(MAIL_DEFAULT_SENDER, recipients, msg.as_string())
        server.quit()

        ic("EMAIL: Sent", TO_EMAIL, "CC:", CC_EMAIL)

        # logger.log(event="EMAIL", message=f"Email sent successfully")

        return True

    except Exception as e:
        ic("ERROR: Email failed to send:", e)

        # logger.log(event="ERROR", message=f"Email failed to send, {e}")

        return False


def load_engine():
    """Helper to load or reload the stockfish engine"""
    ic("DEBUG: Loading Stockfish from", STOCKFISH_PATH)
    try:
        engine = Stockfish(
            path=STOCKFISH_PATH,
            parameters={
                "Threads": 2,
                "Minimum Thinking Time": 20,
                "Skill Level": 8,
            },
        )
        ic("DEBUG: Stockfish loaded successfully")
        return engine
    except Exception as e:
        ic("ERROR: Could not load Stockfish", e)
        logger.log(event="ERROR", message=f"Stockfish initilization failed, {e}")
        sys.exit(1)


def load_yolo():
    """Initializes the YOLO handler with paths from config."""
    ic("DEBUG: Initializing YOLO...")
    try:
        yolo_handler = YoloHandler(
            seg_model_path=SEG_MODEL_PATH,
            piece_model_path=PIECE_MODEL_PATH,
            ui_model_path=UI_MODEL_PATH,
            login_model_path=LOGIN_MODEL_PATH,
        )
        return yolo_handler
    except Exception as e:
        ic("ERROR: YOLO Init failed:", e)
        logger.log(event="ERROR", message="YOLO initialization failed")
        sys.exit(1)
