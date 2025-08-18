"""
File: utils.py
Author: Jerry Wang
Date: 2025-08-15

Shared utility functions for datetime handling, file I/O, state management, and scheduler timing.

Includes helpers to:
- Calculate the next Sunday
- Read/write JSON files for persistent state
- Read/write roster message cache
- Track roster cancellation and message ID state
- Determine next sleep interval for roster updates based on active/quiet hours
"""


import datetime
import json
import pytz
import random

EASTERN = pytz.timezone("US/Eastern")

# === State Files ===
MESSAGE_ID_FILE = "message_id.txt"
CANCEL_FILE = "cancel_state.json"
ROSTER_CACHE_FILE = "last_roster.txt"

# === Time Utilities ===
def get_next_sunday():
    today = datetime.date.today()
    return today + datetime.timedelta((6 - today.weekday()) % 7)

def format_datetime(dt):
    return dt.astimezone(EASTERN).strftime('%Y-%m-%d %I:%M:%S %p %Z')

# === JSON File Utilities ===
def load_json_file(filepath, default):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json_file(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

# === State Utilities ===
def load_message_id():
    try:
        with open(MESSAGE_ID_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return None

def save_message_id(msg_id):
    with open(MESSAGE_ID_FILE, "w") as f:
        f.write(str(msg_id))

def load_cancel_state():
    sunday = get_next_sunday().isoformat()
    data = load_json_file(CANCEL_FILE, {})
    if sunday not in data:
        data = {
            sunday: {
                "is_cancelled": False,
                "reason": "",
                "cancelled_by": "",
                "timestamp": ""
            }
        }
        save_json_file(CANCEL_FILE, data)
    return data[sunday]

def save_cancel_state(state):
    sunday = get_next_sunday().isoformat()
    data = {sunday: state}
    save_json_file(CANCEL_FILE, data)

def load_cached_roster_text():
    try:
        with open(ROSTER_CACHE_FILE, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def save_cached_roster_text(text):
    with open(ROSTER_CACHE_FILE, "w") as f:
        f.write(text)

def get_roster_sleep_seconds(status="edited", consecutive_429=0):
    """
    Decide how long to sleep before the next roster update.

    Args:
        status (str): Result from update_roster_message.
                      "edited", "nochange", "rate_limited", or "error"
        consecutive_429 (int): Number of consecutive 429s.

    Returns:
        int: Sleep time in seconds.
    """
    # Handle 429 backoff first
    if status == "rate_limited":
        # Exponential backoff-ish: grow with each 429
        # e.g. 1st = 1–1.5h, 2nd = 2–3h, 3rd = 4–6h, etc.
        base_minutes = 60 * (2 ** (consecutive_429 - 1))
        min_sleep = base_minutes
        max_sleep = int(base_minutes * 1.5)
        return random.randint(min_sleep * 60, max_sleep * 60)

    # Handle generic errors
    if status == "error":
        return random.randint(45*60, 60*60)         # 45–60m

    # Normal scheduling
    now = datetime.datetime.now(EASTERN)
    weekday, hour = now.weekday(), now.hour
    active = (
        (weekday == 4 and hour >= 12) or
        (weekday == 5) or
        (weekday == 6 and hour < 14)
    )

    if active:
        base_sleep = random.randint(19*60, 21*60)   # ~20m
    else:
        base_sleep = random.randint(115*60, 125*60) # ~2h

    if status == "nochange" and active:
        base_sleep += random.randint(10*60, 20*60)  # ease off a bit ~10–20m

    return base_sleep

