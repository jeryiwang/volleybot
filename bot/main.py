"""
File: main.py
Author: Jerry Wang
Date: 2025-09-04

Main entry point for the THM Volleyball bot.

- Runs the Flask keepalive server (served via waitress) for Render uptime monitoring.
- Uses a continuous scheduler loop to update the weekly volleyball roster:
    * "Active hours" (Fri 12 PM - Sun 2 PM): ~25 min updates
    * "Quiet hours" (Mon-Thu): ~2 hour updates
"""

import asyncio
import datetime
import logging
import os
import pytz
import random
import threading


from version import __version__
from discord_bot import bootstrap_roster_message, client, run_discord, update_roster_message
from flask import Flask, request
from utils import  format_datetime, get_roster_sleep_seconds, load_cancel_state
from waitress import serve

# === Logger Setup ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Environment Variables ===
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID")) # Unused, but can be used for logging
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
    consecutive_429 = 0
    while True:
        try:
            state = load_cancel_state()
            status = await update_roster_message(
                cancelled=state.get("is_cancelled"),
                reason=state.get("reason")
            )
        except Exception as e:
            logger.error(f"roster_scheduler failed: {e}", exc_info=True)
            status = "error"

        if status == "rate_limited":
            consecutive_429 += 1
        else:
            consecutive_429 = 0

        sleep_s = get_roster_sleep_seconds(status=status, consecutive_429=consecutive_429)
        logger.info(f"Next roster check in {sleep_s/60:.1f} minutes (status={status}, consecutive_429={consecutive_429})")
        await asyncio.sleep(sleep_s)

# === Discord Bot Events ===
@client.event
async def on_ready():
    logger.info(f"🤖 Logged in as {client.user}")

    # Optional one-time slash sync
    if os.getenv("ENABLE_BOOT_SYNC", "false").lower() == "true":
        try:
            synced = await client.tree.sync()
            logger.info(f"✅ Boot-time slash sync completed ({len(synced)} commands synced)")
        except Exception as e:
            logger.error(f"❌ Boot-time sync failed: {e}", exc_info=True)

     # Bootstrap roster link before kicking off the scheduler
    try:
        await bootstrap_roster_message()
    except Exception as e:
        logger.error(f"bootstrap on_ready failed: {e}", exc_info=True)

    client.loop.create_task(roster_scheduler())

# === Main Entry Point ===
if __name__ == "__main__":
    logger.info(f"Starting THM Volleyball Bot v{__version__}")

    threading.Thread(target=run_discord).start()
    serve(app, host="0.0.0.0", port=PORT, threads=2)
