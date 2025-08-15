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

def get_roster_sleep_seconds():
    """Returns how many seconds to sleep until next roster update."""
    now = datetime.datetime.now(EASTERN)
    weekday = now.weekday()  # Monday=0 ... Sunday=6
    hour = now.hour

    # Active window: Fri 12:00 PM → Sun 2:00 PM
    active = (
        (weekday == 4 and hour >= 12) or  # Friday noon onward
        (weekday == 5) or                 # Saturday
        (weekday == 6 and hour < 14)      # Sunday before 2pm
    )

    if active:
        return random.randint(14*60, 16*60)   # ~15 min ±1 min
    else:
        return random.randint(115*60, 125*60) # ~2 hr ±5 min
