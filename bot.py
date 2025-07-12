import os
import json
import datetime
from io import StringIO
from flask import Flask

import discord
from discord.ext import tasks
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Environment Variables ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
GOOGLE_SHEET_NAME = "KMCD Volleyball Check-In (Responses)"
GOOGLE_SHEET_TAB = "Form Responses"
PORT = int(os.environ.get("PORT", 8080))

# === Minimal Flask App (for Render port binding) ===
app = Flask(__name__)

@app.route("/")
def home():
    return "THM Volleyball Bot is running!"

# === Google Sheets Setup ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.load(StringIO(GOOGLE_CREDS_JSON))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)
sheet = gc.open(GOOGLE_SHEET_NAME).worksheet(GOOGLE_SHEET_TAB)

# === Discord Setup ===
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# === Helpers for Message ID ===
def save_message_id(msg_id):
    with open("message_id.txt", "w") as f:
        f.write(str(msg_id))

def load_message_id():
    try:
        with open("message_id.txt", "r") as f:
            return int(f.read().strip())
    except:
        return None

# === Startup Event ===
@client.event
async def on_ready():
    channel = client.get_channel(CHANNEL_ID)
    async for msg in channel.history(limit=100):
        if msg.author == client.user and msg.content.startswith("📋 THM Volleyball Roster"):
            await msg.delete()
    post_roster.start()

# === Roster Posting Task ===
@tasks.loop(minutes=1)
async def post_roster():
    today = datetime.date.today()
    sunday = today + datetime.timedelta((6 - today.weekday()) % 7)
    formatted_date = sunday.strftime('%-m/%-d/%Y')

    sheet_data = sheet.get_all_records()
    participants = [
        row['Name:'] for row in sheet_data
        if str(row.get("PARTICIPATION Date (NOT birthday!)", "")).startswith(formatted_date)
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
    msg_id = load_message_id()

    try:
        if msg_id:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(content=message)
        else:
            raise ValueError
    except:
        msg = await channel.send(message)
        save_message_id(msg.id)

# === Run both Discord bot and Flask server ===
if __name__ == "__main__":
    import threading

    # Start Discord bot in a separate thread
    def run_discord():
        client.run(DISCORD_TOKEN)

    threading.Thread(target=run_discord).start()

    # Start Flask app to bind the port
    app.run(host="0.0.0.0", port=PORT)
