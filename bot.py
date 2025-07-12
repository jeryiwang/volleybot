import os
import json
import datetime
from io import StringIO

import discord
from discord.ext import tasks

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === ENVIRONMENT VARIABLES ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
GOOGLE_SHEET_NAME = "KMCD Volleyball Check-In (Responses)"
GOOGLE_SHEET_TAB = "Form Responses"

# === SETUP DISCORD BOT ===
 print("🔐 Initializing Discord access...")
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# === GOOGLE SHEETS SETUP ===
try:
    print("🔐 Initializing Google Sheets access...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.load(StringIO(GOOGLE_CREDS_JSON))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    gc = gspread.authorize(creds)
    sheet = gc.open(GOOGLE_SHEET_NAME).worksheet(GOOGLE_SHEET_TAB)
    print("✅ Google Sheets access ready.")
except Exception as e:
    print(f"🔥 Google Sheets Setup Error: {e}")
    sheet = None

# === HELPERS ===
def get_upcoming_sunday():
    today = datetime.date.today()
    return today + datetime.timedelta((6 - today.weekday()) % 7)

def format_roster_message(confirmed, waitlist, sunday):
    msg = f"""📋 **THM Volleyball Roster – Sunday, {sunday.strftime('%B %d')}**

✅ Confirmed to Play:"""
    msg += "\n" + "\n".join([f"{i+1}. {name}" for i, name in enumerate(confirmed)]) if confirmed else "\nNone"
    msg += "\n\n⏳ Waitlist:"
    msg += "\n" + "\n".join([f"- {name}" for name in waitlist]) if waitlist else "\nNone"
    msg += """

📍 KMCD Gym | 2–5 PM  
🚪 Enter through the double doors (north side)  
📝 Please arrive on time — late spots may be given to waitlisters."""
    return msg

# === BOT EVENTS ===
@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')
    if sheet:
        print("🔄 Starting post_roster loop...")
        post_roster.start()
    else:
        print("❌ Google Sheet not available, skipping roster posting.")

@tasks.loop(minutes=1)
async def post_roster():
    print("⏰ Running post_roster loop")
    try:
        sunday = get_upcoming_sunday()
        formatted_date = sunday.strftime('%-m/%-d/%Y')  # e.g., '7/14/2025'
        sheet_data = sheet.get_all_records()
        print(f"📄 Fetched {len(sheet_data)} rows from the sheet")

        participants = [
            row['Name:'] for row in sheet_data
            if str(row['PARTICIPA']).startswith(formatted_date)
        ]

        print(f"✅ Found {len(participants)} participants for {formatted_date}")

        confirmed = participants[:21]
        waitlist = participants[21:]

        message = format_roster_message(confirmed, waitlist, sunday)
        channel = client.get_channel(CHANNEL_ID)
        await channel.send(message)

        print(f"📬 Posted roster: {len(confirmed)} confirmed, {len(waitlist)} waitlisted.")

    except Exception as e:
        print(f"❌ Error in post_roster: {e}")

# === START BOT ===
client.run(DISCORD_TOKEN)
