import os
import tempfile
import configparser
from dotenv import load_dotenv
import random

load_dotenv(override=True)

config = configparser.ConfigParser()

# FIX: Build the absolute path to config.ini so it works from anywhere
# This says: "Look for config.ini in the same folder as this script (config.py)"
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "config.ini")
config.read(config_path)
# --- SECTION: DYNAMIC VARIABLES ---
TEMP_DIR = tempfile.gettempdir()

# --- SECTION: GENERAL SETTINGS ---
URL = config["General"]["URL"]
MESSAGES_FILE = config["General"]["MESSAGES_FILE"]
# TEMPLATE_PATH = config["Paths"]["TEMPLATE_PATH"]

# Cast numbers manually
CONFIDENCE = float(config["General"]["CONFIDENCE"])
RETINA_SCALE = int(config["General"]["RETINA_SCALE"])
MESSAGE_PROBABILITY = float(config["General"]["MESSAGE_PROBABILITY"])

# --- SECTION: PATHS ---
STOCKFISH_PATH = config["Paths"]["STOCKFISH_PATH"]
SEG_MODEL_PATH = config["Paths"]["SEG_MODEL"]
PIECE_MODEL_PATH = config["Paths"]["PIECE_MODEL"]
UI_MODEL_PATH = config["Paths"]["UI_MODEL"]
LOGIN_MODEL_PATH = config["Paths"]["LOGIN_MODEL"]


# --- SECTION: EMAIL (ALL FROM ENV) ---
# We no longer read config['Email'] here
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")
TO_EMAIL = os.getenv("TO_EMAIL")
CC_EMAIL = os.getenv("CC_EMAIL")


MAX_SAME_FEN = int(config["GameSafety"].get("MAX_SAME_FEN", 10))
MAX_INVALID_KINGS = int(config["GameSafety"].get("MAX_INVALID_KINGS", 10))
# Runtime variables (do NOT persist state in config.ini)
LAST_FEN = None
SAME_FEN_COUNTER = 0


accounts = []
i = 1

# 2. Loop to find CHESS_USER_1, CHESS_USER_2, etc.
while True:
    u = os.getenv(f"CHESS_USER_{i}")
    p = os.getenv(f"CHESS_PASS_{i}")

    if u and p:
        accounts.append((u, p))
        i += 1
    else:
        # Stop looking when we don't find the next number
        break

# 3. Select an account
if accounts:
    # Pick a random account from the list found
    selected_account = random.choice(accounts)
    CHESS_USERNAME = selected_account[0]
    CHESS_PASSWORD = selected_account[1]
    print(
        f"CONFIG: Loaded {len(accounts)} accounts. Randomly selected: {CHESS_USERNAME}"
    )
else:
    # 4. Fallback: Check for legacy single variables
    CHESS_USERNAME = os.getenv("CHESS_USERNAME")
    CHESS_PASSWORD = os.getenv("CHESS_PASSWORD")

    if CHESS_USERNAME:
        print(
            f"CONFIG: No indexed accounts found. Using legacy single account: {CHESS_USERNAME}"
        )
    else:
        print("CONFIG ERROR: No chess accounts found in .env!")
