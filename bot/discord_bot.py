"""
File: discord_bot.py
Author: Jerry Wang
Date: 2025-08-15

Handles Discord bot setup, slash commands, and roster message updates.

- Starts the Discord client with a random delayed start and retry backoff to reduce rate-limit risk.
- Includes logic for posting/updating the weekly roster with cached content checks.
- Provides slash commands:
    * /roster - Force refresh the roster from Google Sheets.
    * /cancel - Cancel the upcoming Sunday session and announce it.
    * /uncancel - Revert a cancellation.
    * /sync - Manually sync slash commands with Discord.
    * /version - Show the bot version.
- Can send log/status messages to a designated channel.
"""

import discord
import datetime
import logging
import random
import time
import os

from version import __version__
from discord.ext import commands
from sheets import get_confirmed_and_waitlist
from utils import (
    get_next_sunday,
    format_datetime,
    load_message_id,
    save_message_id,
    save_cancel_state,
    load_cached_roster_text,
    save_cached_roster_text
)


ANNOUNCEMENTS_CHANNEL_ID = int(os.getenv("ANNOUNCEMENTS_CHANNEL_ID"))
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ROSTER_CHANNEL_ID = int(os.getenv("ROSTER_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="!", intents=intents)

# === Logger Setup ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Run Discord Client ===
def run_discord():
    # small random delay at cold start so you don't align with other bots on same host
    initial_delay = random.randint(30, 120)
    logger.info(f"Starting Discord client after {initial_delay}s delay...")
    time.sleep(initial_delay)

    while True:
        try:
            client.run(DISCORD_TOKEN)   # blocks until disconnect or crash
            break                       # clean exit
        except Exception as e:
            logger.critical(f"Discord client failed to start: {e}")
            # wait 15–30 minutes before trying again
            wait = random.randint(15 * 60, 30 * 60)
            logger.warning(f"Retrying gateway connect in {wait} seconds...")
            time.sleep(wait)

# === Main Roster Update Function ===
async def update_roster_message(cancelled=False, reason=""):
    sunday = get_next_sunday()
    confirmed, waitlist = get_confirmed_and_waitlist()

    new_content = ""
    if cancelled:
        new_content += f"🚫 Sunday volleyball is CANCELLED - {sunday.strftime('%B %d, %Y')}\nReason: {reason}\n\n"

    new_content += f"""📋 **THM Volleyball Roster - Sunday, {sunday.strftime('%B %d')}**

✅ Confirmed to Play:"""
    new_content += "\n" + "\n".join([f"{i+1}. {name}" for i, name in enumerate(confirmed)]) if confirmed else "\nNone"
    new_content += "\n\n⏳ Waitlist:"
    new_content += "\n" + "\n".join([f"- {name}" for name in waitlist]) if waitlist else "\nNone"
    new_content += """

📍 KMCD Gym | 2-5 PM  
🚪 Enter through the double doors (north side)  
📝 Please arrive on time — late spots may be given to waitlisters."""

    # Only proceed if the content changed
    cached_text = load_cached_roster_text()
    if cached_text == new_content:
        logger.info("ℹ️ Roster content unchanged. Skipping Discord update.")
        return

    channel = client.get_channel(ROSTER_CHANNEL_ID)
    if not channel:
        logger.error("❌ Roster channel not found.")
        return

    did_update = False
    msg_id = load_message_id()

    try:
        if msg_id:
            try:
                fetched_msg = await channel.fetch_message(msg_id)
                await fetched_msg.edit(content=new_content)
                logger.info("✅ Roster message updated.")
                did_update = True
            except Exception as e:
                logger.warning(f"⚠️ Failed to edit existing message: {e}")
        if not msg_id or not did_update:
            msg = await channel.send(new_content)
            save_message_id(msg.id)
            logger.info("✅ Posted new roster message.")
            did_update = True
    except Exception as e:
        logger.error(f"❌ update_roster_message failed: {e}", exc_info=True)
        return

    # Save new content only if message was posted or updated
    if did_update:
        save_cached_roster_text(new_content)

# === Log to Discord Channel Utility ===
async def log_to_channel(channel, prefix, error=None):
    if not channel:
        return

    now = format_datetime(datetime.datetime.now())
    msg = f"{prefix} `{now}`"
    if error:
        msg += f": `{str(error)}`"
    await channel.send(msg)

# === Roster Force Refresh Command ===
@client.tree.command(name="roster", description="Force refresh the roster from Google Sheets")
@discord.app_commands.default_permissions(administrator=True)
async def roster_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    try:
        await update_roster_message()
        await interaction.followup.send("✅ Roster successfully refreshed from Google Sheets.", ephemeral=True)
        logger.info(f"✅ /roster used by {interaction.user.display_name}")
    except Exception as e:
        logger.error(f"❌ /roster failed for {interaction.user.display_name}: {e}", exc_info=True)
        await interaction.followup.send("❌ Failed to refresh the roster. Check logs for details.", ephemeral=True)


# === Discord Cancel Command ===
@client.tree.command(name="cancel", description="Cancel this Sunday's volleyball session")
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(reason="Reason for cancellation")
async def cancel(interaction: discord.Interaction, reason: str = "No reason provided"):
    sunday = get_next_sunday()
    formatted_date = sunday.strftime('%B %d, %Y')

    state = {
        "is_cancelled": True,
        "reason": reason,
        "cancelled_by": interaction.user.display_name,
        "timestamp": datetime.datetime.now().isoformat()
    }
    save_cancel_state(state)
    await interaction.response.send_message("✅ Cancelled! Announcement has been posted to #announcements.", ephemeral=True)

    channel = client.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
    roster_channel = client.get_channel(ROSTER_CHANNEL_ID)
    if channel:
        await channel.send(
            f"@everyone\n🛑 **Sunday volleyball has been CANCELLED – {formatted_date}**\n📝 Reason: {reason}\n👤 By: {interaction.user.mention}"
        )

    if roster_channel:
        await update_roster_message(cancelled=True, reason=reason)

# === Discord Uncancel Command ===
@client.tree.command(name="uncancel", description="Un-cancel this Sunday's volleyball session")
@discord.app_commands.default_permissions(administrator=True)
async def uncancel(interaction: discord.Interaction):
    sunday = get_next_sunday()
    formatted_date = sunday.strftime('%B %d, %Y')

    save_cancel_state({
        "is_cancelled": False,
        "reason": "",
        "cancelled_by": "",
        "timestamp": ""
    })
    await interaction.response.send_message("✅ Uncancelled! Announcement has been posted to #announcements.", ephemeral=True)

    channel = client.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
    roster_channel = client.get_channel(ROSTER_CHANNEL_ID)
    if channel:
        await channel.send(f"✅ **Sunday volleyball is back on – {formatted_date}!**")
    if roster_channel:
        await update_roster_message(cancelled=False)

# === Manual Slash Cmd Sync Command ===
@client.tree.command(name="sync", description="Sync slash commands with Discord")
@discord.app_commands.default_permissions(administrator=True)
async def sync_commands(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        synced = await client.tree.sync()
        await interaction.followup.send(f"✅ Synced {len(synced)} slash commands.", ephemeral=True)
        logger.info(f"✅ /sync used by {interaction.user.display_name} ({len(synced)} commands synced)")
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to sync: {e}", ephemeral=True)
        logger.error(f"❌ /sync failed for {interaction.user.display_name}: {e}", exc_info=True)

# === Discord Version Command ===
@client.tree.command(name="version", description="Show the current bot version")
async def version_command(interaction: discord.Interaction):
    await interaction.response.send_message(f"🤖 THM Volleyball Bot Version: `{__version__}`", ephemeral=True)
