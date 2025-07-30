"""
File: utils.py
Author: Jerry Wang
Date: 2025-07-30

Shared utility functions for datetime handling, file I/O, and state management.

Includes helpers to calculate the next Sunday, read/write JSON files,
read/write persistent cache, and track roster cancellation and message ID state.
"""

import datetime
import json
import pytz

# === State Files ===
MESSAGE_ID_FILE = "message_id.txt"
CANCEL_FILE = "cancel_state.json"
ROSTER_CACHE_FILE = "last_roster.txt"

# === Time Utilities ===
def get_next_sunday():
    today = datetime.date.today()
    return today + datetime.timedelta((6 - today.weekday()) % 7)

def format_datetime(dt):
    eastern = pytz.timezone("US/Eastern")
    return dt.astimezone(eastern).strftime('%Y-%m-%d %I:%M:%S %p %Z')

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
