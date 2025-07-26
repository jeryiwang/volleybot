# 🏐 THM Volleyball Discord Bot

This is a custom-built Discord bot that automates weekly volleyball sign-up tracking, announcements, and roster management for our Sunday 2–5pm KMCD Gym volleyball group.

The bot reads player sign-ups from a Google Form response sheet and keeps the Discord server in sync — posting the weekly roster, handling cancellations, and avoiding repetitive manual work.

---

## 💡 Features

### 📋 Weekly Roster Automation
- Pulls the latest sign-up data from Google Sheets.
- Auto-posts the Sunday roster to the designated Discord channel.
- Separates players into ✅ Confirmed (up to 21) and ⏳ Waitlist.
- Includes location, entrance, and arrival instructions in the message footer.

### 🛑 Slash Commands
- `/cancel [reason]`: Cancels volleyball for the week and updates both the announcements and roster channels with a 🚫 message.
- `/uncancel`: Reverts cancellation and removes the 🚫 notice from the roster.

### 🔁 Weekly Reset Logic
- Each Sunday is treated as a fresh week.
- Cancellation state is scoped per-Sunday and automatically reset.
- Roster refreshes based on each week’s Google Sheet sign-ups.

### 🩺 Heartbeat Monitoring
- Every time the bot updates the roster, it records a timestamp.
- A separate heartbeat loop runs every 15 minutes to check if the last update was within the past 5 minutes.
- Posts a ✅ healthy or ❌ stale warning in the log channel based on this check.

### 🔄 Smart Roster Posting
- Bot runs 24/7 (on Render) and updates the roster every minute.
- If nothing has changed, it skips posting to avoid spam.
- All messages are edited in-place using stored message IDs.

### 🧠 Hosting & Uptime
- Hosted on [Render](https://render.com)
- Uses a minimal Flask app for port binding
- Kept awake with `UptimeRobot` and `cron-job.org` pinging the `/keepalive` endpoint
- Local files store state between runs (`cancel_state.json`, `message_id.txt`)

---

## ⚙️ Tech Stack

- **Python 3.10+**
- [`discord.py`](https://github.com/Rapptz/discord.py) — Discord bot & slash commands
- `gspread` + `oauth2client` — Google Sheets integration
- `Flask` — for the keepalive endpoint
- Hosted on **Render**
- Monitored by **UptimeRobot**, **cron-job.org**, and internal task watchdogs

---

## 🧪 Example Slash Commands

| Command         | Description                                           |
|----------------|-------------------------------------------------------|
| `/cancel`       | Cancels Sunday volleyball and updates all messages   |
| `/uncancel`     | Restores the Sunday event and clears cancel notices  |

---

## 📝 Setup Guide (For Devs)

### 1. Environment Variables
Set these in Render or `.env`:
- `DISCORD_TOKEN`
- `ANNOUNCEMENTS_CHANNEL_ID`
- `ROSTER_CHANNEL_ID`
- `LOG_CHANNEL_ID`
- `GOOGLE_CREDS_JSON` (your service account JSON blob, not a path)
- `PORT` (optional, default = 8080)

### 2. Google Sheets Structure
- Spreadsheet must contain:
  - `Name:` — player name
  - `PARTICIPATION Date (NOT birthday!)` — formatted as MM/DD/YYYY
- The bot filters by the upcoming Sunday’s date.

### 3. Files Used
- `cancel_state.json`: stores cancellation status for the current week
- `message_id.txt`: tracks Discord message ID for roster message reuse

---

## 📊 Monitoring & Reliability

- `last_post_roster_time` is updated after every successful roster update.
- `post_roster_heartbeat()` checks this every 15 minutes.
- Errors are logged to a dedicated Discord log channel (if provided).

---

## ✍️ To-Do / Future Ideas

- ✅ Player reaction signup on Discord
- 📈 Attendance tracking across weeks
- 📣 Auto-post to Facebook
- 🔔 Waitlist promotion notifications
- 🤖 DM reminders for promoted players
- 🔐 Admin dashboard or config via slash commands
