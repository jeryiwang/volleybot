"""
File: discord_bot.py
Author: Jerry Wang
Date: 2025-07-26

Handles Discord bot setup, slash commands, and roster message updates.

Includes logic for posting/updating the weekly roster, handling /cancel and /uncancel
commands, and sending logs to a designated channel.
"""

import discord
import datetime
import logging
import os

from version import __version__
from discord.ext import commands
from sheets import get_confirmed_and_waitlist
from utils import get_next_sunday, format_datetime, load_message_id, save_message_id, save_cancel_state

ANNOUNCEMENTS_CHANNEL_ID = int(os.getenv("ANNOUNCEMENTS_CHANNEL_ID"))
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ROSTER_CHANNEL_ID = int(os.getenv("ROSTER_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="!", intents=intents)
cached_roster_message = None

# === Logger Setup ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Run Discord Client ===
def run_discord():
    try:
        logger.info("Starting Discord client...")
        client.run(DISCORD_TOKEN)
    except Exception as e:
        logger.critical(f"Discord client failed to start: {e}")

# === Main Roster Update Function ===
async def update_roster_message(cancelled=False, reason=""):
    global cached_roster_message

    sunday = get_next_sunday()
    confirmed, waitlist = get_confirmed_and_waitlist()

    message = ""
    if cancelled:
        message += f"🚫 Sunday volleyball is CANCELLED - {sunday.strftime('%B %d, %Y')}\nReason: {reason}\n\n"

    message += f"""📋 **THM Volleyball Roster - Sunday, {sunday.strftime('%B %d')}**

✅ Confirmed to Play:"""
    message += "\n" + "\n".join([f"{i+1}. {name}" for i, name in enumerate(confirmed)]) if confirmed else "\nNone"
    message += "\n\n⏳ Waitlist:"
    message += "\n" + "\n".join([f"- {name}" for name in waitlist]) if waitlist else "\nNone"
    message += """

📍 KMCD Gym | 2-5 PM  
🚪 Enter through the double doors (north side)  
📝 Please arrive on time — late spots may be given to waitlisters."""

    channel = client.get_channel(ROSTER_CHANNEL_ID)
    if not channel:
        logger.error("❌ Roster channel not found.")
        return

    try:
        # Step 1: Fetch from message ID if cache is empty
        if cached_roster_message is None:
            msg_id = load_message_id()
            if msg_id:
                try:
                    cached_roster_message = await channel.fetch_message(msg_id)
                    logger.info("🔄 Cached message loaded from ID.")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to fetch message ID {msg_id}: {e}")
                    cached_roster_message = None

        # Step 2: Use cached message if available
        if cached_roster_message:
            if cached_roster_message.content != message:
                cached_roster_message = await cached_roster_message.edit(content=message)
                logger.info("✅ Roster message updated (cached).")
            else:
                logger.info("ℹ️ No change in roster message (cached).")
            return

        # Step 3: Post new message if no cached or valid ID
        msg = await channel.send(message)
        cached_roster_message = msg
        save_message_id(msg.id)
        logger.info("✅ New roster message posted and cached.")

    except Exception as e:
        logger.error(f"❌ update_roster_message failed: {e}", exc_info=True)


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

# === Discord Version Command ===
@client.tree.command(name="version", description="Show the current bot version")
async def version_command(interaction: discord.Interaction):
    await interaction.response.send_message(f"🤖 THM Volleyball Bot Version: `{__version__}`", ephemeral=True)
