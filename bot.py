# === IMPORTS ===
import os, json, datetime
from io import StringIO
from threading import Thread
from flask import Flask

import discord
from discord.ext import tasks
import gspread
from oauth2client.service_account import ServiceAccountCredentials

print("🚀 bot.py has started execution")

# === ENVIRONMENT VARIABLES ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
GOOGLE_SHEET_NAME = "KMCD Volleyball Check-In (Responses)"
GOOGLE_SHEET_TAB = "Form Responses"

# === DISCORD BOT SETUP ===
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.presences = True
client = discord.Client(intents=intents)

# === GOOGLE SHEETS SETUP ===
try:
    print("🔐 Initializing Google Sheets access...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.load(StringIO(GOOGLE_CREDS_JSON))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    gc = gspread.authorize(creds)
    sheet = gc.open(GOOGLE_SHEET_NAME).worksheet(GOOGLE_SHEET_TAB)
    print(f"✅ Google Sheets access ready. Sheet title: {sheet.title}")
except Exception as e:
    print(f"🔥 Google Sheets Setup Error: {e}")
    sheet = None

# === DISCORD EVENTS ===
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    if sheet:
        print(f"📄 Sheet is valid: {sheet.title}")
        print("🔄 Starting post_roster loop...")
        post_roster.start()
    else:
        print("❌ Sheet is None. Not starting loop.")

@tasks.loop(minutes=1)
async def post_roster():
    print("⏰ Running post_roster loop")
    try:
        sunday = datetime.date.today() + datetime.timedelta((6 - datetime.date.today().weekday()) % 7)
        formatted_date = sunday.strftime('%-m/%-d/%Y')
        sheet_data = sheet.get_all_records()
        print(f"📄 Fetched {len(sheet_data)} rows from the sheet")

        participants = [
            row['Name:'] for row in sheet_data
            if str(row['PARTICIPA']).startswith(formatted_date)
        ]

        confirmed = participants[:21]
        waitlist = participants[21:]

        message = f"""📋 **THM Volleyball Roster – Sunday, {sunday.strftime('%B %d')}**

✅ Confirmed to Play:"""
        message += "\n" + "\n".join([f"{i+1}. {name}" for i, name in enumerate(confirmed)]) if confirmed else "\nNone"
        message += "\n\n⏳ Waitlist:"
        message += "\n" + "\n".join([f"- {name}" for name in waitlist]) if waitlist else "\nNone"
        message += """
📍 KMCD Gym | 2–5 PM  
🚪 Enter through the double doors (north side)  
📝 Please arrive on time — late spots may be given to waitlisters."""

        channel = client.get_channel(CHANNEL_ID)
        await channel.send(message)

        print(f"📬 Posted roster: {len(confirmed)} confirmed, {len(waitlist)} waitlisted.")
    except Exception as e:
        print(f"❌ Error in post_roster: {e}")

# === KEEP RENDER ALIVE (FLASK) ===
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_web).start()

# === START DISCORD BOT ===
client.run(DISCORD_TOKEN)
