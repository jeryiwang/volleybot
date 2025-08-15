"""
File: main.py
Author: Jerry Wang
Date: 2025-08-15

Main entry point for the THM Volleyball bot.

- Runs the Flask keepalive server for Render uptime monitoring.
- Uses a continuous scheduler loop to update the weekly volleyball roster:
    * "Active hours" (Fri 12 PM - Sun 2 PM): ~15 min updates
    * "Quiet hours" (Mon-Thu): ~2 hour updates
"""

import asyncio
import datetime
import logging
import os
import pytz
import threading


from version import __version__
from discord.ext import tasks
from discord_bot import client, run_discord, update_roster_message
from flask import Flask, request
from utils import  format_datetime, get_roster_sleep_seconds, load_cancel_state

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

# === Roster Scheduler Loop ===
async def roster_scheduler():
    while True:
        try:
            state = load_cancel_state()
            await update_roster_message(
                cancelled=state.get("is_cancelled"),
                reason=state.get("reason")
            )
        except Exception as e:
            logger.error(f"roster_scheduler failed: {e}", exc_info=True)
            sleep_s = random.randint(45*60, 60*60)  # backoff 45–60 min
            logger.warning(f"Error occurred, sleeping {sleep_s/60:.1f} min before retry")
            await asyncio.sleep(sleep_s)
            continue

        sleep_s = get_roster_sleep_seconds()
        logger.info(f"Next roster check in {sleep_s/60:.1f} minutes")
        await asyncio.sleep(sleep_s)

# === Discord Bot Events ===
@client.event
async def on_ready():
    logger.info(f"🤖 Logged in as {client.user}")
    client.loop.create_task(roster_scheduler())

# === Main Entry Point ===
if __name__ == "__main__":
    logger.info(f"Starting THM Volleyball Bot v{__version__}")

    threading.Thread(target=run_discord).start()
    app.run(host="0.0.0.0", port=PORT)
