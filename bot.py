import os
import json
import datetime
from io import StringIO
from flask import Flask, request
import logging

import discord
from discord.ext import tasks, commands
import gspread
import pytz
from oauth2client.service_account import ServiceAccountCredentials

# === Logger Setup ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Environment Variables ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ANNOUNCEMENTS_CHANNEL_ID = int(os.getenv("ANNOUNCEMENTS_CHANNEL_ID"))
ROSTER_CHANNEL_ID = int(os.getenv("ROSTER_CHANNEL_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
GOOGLE_SHEET_NAME = "KMCD Volleyball Check-In (Responses)"
GOOGLE_SHEET_TAB = "Form Responses"
PORT = int(os.environ.get("PORT", 8080))

# === Minimal Flask App (for Render port binding) ===
app = Flask(__name__)

@app.route("/")
def home():
    return "THM Volleyball Bot is running!"

@app.route('/keepalive')
def keepalive():
    user_agent = request.headers.get('User-Agent', 'unknown')
    ip = request.remote_addr
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"[{timestamp}] Keepalive ping received from {ip}, User-Agent: {user_agent}")
    return "Alive and kickin'", 200

# === Google Sheets Setup ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.load(StringIO(GOOGLE_CREDS_JSON))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)
sheet = gc.open(GOOGLE_SHEET_NAME).worksheet(GOOGLE_SHEET_TAB)

# === Discord Setup ===
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="!", intents=intents)

CANCEL_FILE = "cancel_state.json"

# === Helpers ===
def save_message_id(msg_id):
    with open("message_id.txt", "w") as f:
        f.write(str(msg_id))

def load_message_id():
    try:
        with open("message_id.txt", "r") as f:
            return int(f.read().strip())
    except:
        return None

def load_cancel_state():
    try:
        with open(CANCEL_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"is_cancelled": False, "reason": "", "cancelled_by": "", "timestamp": ""}

def save_cancel_state(state):
    with open(CANCEL_FILE, "w") as f:
        json.dump(state, f, indent=2)

# === Slash Commands ===
@client.tree.command(name="cancel", description="Cancel this Sunday's volleyball session")
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(reason="Reason for cancellation")
async def cancel(interaction: discord.Interaction, reason: str = "No reason provided"):
    state = load_cancel_state()
    state["is_cancelled"] = True
    state["reason"] = reason
    state["cancelled_by"] = interaction.user.display_name
    state["timestamp"] = datetime.datetime.now().isoformat()
    save_cancel_state(state)
    await interaction.response.send_message("✅ Cancelled! Announcement has been posted to #announcements.", ephemeral=True)

    channel = client.get_channel(ANNOUNCEMENTS_CHANNEL_ID)  # Already set to announcements channel
    if channel:
        await channel.send(f"🛑 **Sunday volleyball has been CANCELLED.**\nReason: {reason}")

@client.tree.command(name="uncancel", description="Un-cancel this Sunday's volleyball session")
@discord.app_commands.default_permissions(administrator=True)
async def uncancel(interaction: discord.Interaction):
    save_cancel_state({"is_cancelled": False, "reason": "", "cancelled_by": "", "timestamp": ""})
    await interaction.response.send_message("✅ Uncancelled! Announcement has been posted to #announcements.", ephemeral=True)

    channel = client.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
    if channel:
        await channel.send("✅ **Sunday volleyball is back on!**")

# === Roster Posting Task ===
@tasks.loop(minutes=1)
async def post_roster():
    try:
        state = load_cancel_state()
        if state.get("is_cancelled"):
            return

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

        channel = client.get_channel(ROSTER_CHANNEL_ID)
        log_channel = client.get_channel(LOG_CHANNEL_ID)
        msg_id = load_message_id()

        try:
            if msg_id:
                msg = await channel.fetch_message(msg_id)
                if msg.content != message:
                    await msg.edit(content=message)
            else:
                raise ValueError
        except:
            msg = await channel.send(message)
            save_message_id(msg.id)

        if log_channel:
            eastern = pytz.timezone('US/Eastern')
            now_dt = datetime.datetime.now(eastern)
            if now_dt.minute % 15 == 0:
                now = now_dt.strftime('%Y-%m-%d %I:%M:%S %p %Z')
                await log_channel.send(f"✅ Roster updated at `{now}`")
    except Exception as e:
        log_channel = client.get_channel(LOG_CHANNEL_ID)
        eastern = pytz.timezone('US/Eastern')
        now_dt = datetime.datetime.now(eastern)
        if log_channel and now_dt.minute % 15 == 0:
            now = now_dt.strftime('%Y-%m-%d %I:%M:%S %p %Z')
            await log_channel.send(f"❌ Roster update failed at `{now}`: `{str(e)}`")

# === Startup ===
@client.event
async def on_ready():
    try:
        synced = await client.tree.sync()
        logger.info(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        logger.info(f"Slash command sync failed: {e}")

    if not post_roster.is_running():
        post_roster.start()
    else:
        logger.info("post_roster loop already running.")

# === Run both Discord bot and Flask server ===
if __name__ == "__main__":
    import threading

    def run_discord():
        client.run(DISCORD_TOKEN)

    threading.Thread(target=run_discord).start()
    app.run(host="0.0.0.0", port=PORT)
