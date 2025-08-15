"""
File: main.py
Author: Jerry Wang
Date: 2025-07-26

Main entry point for the THM Volleyball bot.

Runs the Flask keepalive server and starts the Discord client with scheduled tasks
to post and monitor the weekly volleyball roster.
"""

import datetime
import logging
import os
import pytz
import threading


from version import __version__
from discord.ext import tasks
from discord_bot import client, log_to_channel, run_discord, update_roster_message
from flask import Flask, request
from utils import  format_datetime, load_cancel_state

# === Logger Setup ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Environment Variables ===
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
PORT = int(os.environ.get("PORT", 8080))

# === Flask Server for Keepalive ===
app = Flask(__name__)

@app.route("/")
def home():
    return "THM Volleyball Bot is running!"

@app.route("/keepalive")
def keepalive():
    try:
        user_agent = request.headers.get('User-Agent', 'unknown')
        ip = request.remote_addr
        timestamp = format_datetime(datetime.datetime.now())
        logger.info(f"[{timestamp}] Keepalive ping from {ip}, User-Agent: {user_agent}")
        return "Alive and kickin'", 200
    except Exception as e:
        logger.error(f"Keepalive error: {e}")
        return "Still kickin' (barely)", 200

# === Post Roster Task ===
@tasks.loop(minutes=43)
async def post_roster():
    logger.info("✅ post_roster() task started.")
    try:
        state = load_cancel_state()
        await update_roster_message(
            cancelled=state.get("is_cancelled"),
            reason=state.get("reason")
        )
    except Exception as e:
        logger.error(f"post_roster() failed: {e}", exc_info=True)

# === Discord Bot Events ===
@client.event
async def on_ready():
    logger.info(f"🤖 Logged in as {client.user}")
    # === Start Tasks ===
    if not post_roster.is_running():
        post_roster.start()

# === Main Entry Point ===
if __name__ == "__main__":
    logger.info(f"Starting THM Volleyball Bot v{__version__}")

    threading.Thread(target=run_discord).start()
    app.run(host="0.0.0.0", port=PORT)
