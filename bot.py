import os
import discord
from discord.ext import tasks
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
import threading

# --- Flask App for Render Port Binding ---
app = Flask(__name__)

@app.route('/')
def home():
    return "VolleyBot is running."

# --- Google Sheets Setup ---
GOOGLE_SHEET_NAME = "KMCD Volleyball Check-In (Responses)"
GOOGLE_SHEET_TAB = "Form Responses"
DATE_COLUMN_NAME = "PARTICIPATION Date (NOT birthday!)"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.environ["GOOGLE_CREDS_JSON"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(eval(creds_json), scope)
gc = gspread.authorize(creds)
sheet = gc.open(GOOGLE_SHEET_NAME).worksheet(GOOGLE_SHEET_TAB)

# --- Discord Setup ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    channel = client.get_channel(CHANNEL_ID)

    # Delete old roster messages
    async for msg in channel.history(limit=50):
        if msg.author.id == client.user.id and msg.content.startswith("📋 THM Volleyball Roster"):
            await msg.delete()

    post_roster.start()

@tasks.loop(minutes=60)
async def post_roster():
    today = datetime.date.today()
    sunday = today + datetime.timedelta((6 - today.weekday()) % 7)
    sunday_str = sunday.strftime('%-m/%-d/%Y')

    data = sheet.get_all_records()
    participants = [row["Name"] for row in data if row[DATE_COLUMN_NAME] == sunday_str]

    message = f"📋 **THM Volleyball Roster – Sunday, {sunday.strftime('%B %d')}**\n\n"
    message += "✅ Confirmed to Play:\n"
    for i, name in enumerate(participants[:21], start=1):
        message += f"{i}. {name}\n"

    waitlist = participants[21:]
    message += "\n⏳ Waitlist:\n"
    message += "None\n" if not waitlist else "\n".join(f"- {name}" for name in waitlist)

    message += (
        "\n📍 KMCD Gym | 2–5 PM\n"
        "🚪 Enter through the double doors (north side)\n"
        "📝 Please arrive on time — late spots may be given to waitlisters."
    )

    channel = client.get_channel(CHANNEL_ID)
    await channel.send(message)

# --- Start Flask server to bind a port for Render ---
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))).start()
client.run(DISCORD_TOKEN)
