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
import os

from bot.version import __version__
from discord.ext import commands
from sheets import get_confirmed_and_waitlist
from utils import get_next_sunday, format_datetime, load_message_id, save_message_id, save_cancel_state

ANNOUNCEMENTS_CHANNEL_ID = int(os.getenv("ANNOUNCEMENTS_CHANNEL_ID"))
ROSTER_CHANNEL_ID = int(os.getenv("ROSTER_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="!", intents=intents)

# === Main Roster Update Function ===
async def update_roster_message(cancelled=False, reason=""):
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

    msg_id = load_message_id()
    channel = client.get_channel(ROSTER_CHANNEL_ID)
    try:
        if msg_id and channel:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(content=message)
        else:
            raise ValueError
    except:
        msg = await channel.send(message)
        save_message_id(msg.id)

# === Log to Discord Channel Utility ===
async def log_to_channel(channel, prefix, error=None):
    if not channel:
        return

    now = format_datetime(datetime.datetime.now())
    msg = f"{prefix} `{now}`"
    if error:
        msg += f": `{str(error)}`"
    await channel.send(msg)

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
        await channel.send(f"🛑 **Sunday volleyball has been CANCELLED – {formatted_date}**\nReason: {reason}\nBy: {interaction.user.mention}")
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
