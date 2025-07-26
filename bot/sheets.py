import gspread
import json
import os

from io import StringIO
from oauth2client.service_account import ServiceAccountCredentials
from utils import get_next_sunday

# === Google Sheets Setup ===
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
GOOGLE_SHEET_NAME = "KMCD Volleyball Check-In (Responses)"
GOOGLE_SHEET_TAB = "Form Responses"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.load(StringIO(GOOGLE_CREDS_JSON))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)
sheet = gc.open(GOOGLE_SHEET_NAME).worksheet(GOOGLE_SHEET_TAB)

# === Returns a list of confirmed and waitlisted participants ===
def get_confirmed_and_waitlist():
    sunday = get_next_sunday()
    formatted_date = sunday.strftime('%-m/%-d/%Y')

    sheet_data = sheet.get_all_records()
    participants = [
        row['Name:'] for row in sheet_data
        if str(row.get("PARTICIPATION Date (NOT birthday!)", "")).startswith(formatted_date)
    ]

    confirmed = participants[:21]
    waitlist = participants[21:]
    return confirmed, waitlist
