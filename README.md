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

### 🔁 Weekly Reset Logic
- Each Sunday is treated as a fresh week.
- Cancellation state is scoped per-Sunday and automatically reset.
- Roster refreshes based on each week’s Google Sheet sign-ups.

### 🔄 Smart Roster Posting
- Bot runs 24/7 (on Render) and updates the roster on a dynamic schedule:
  * Active hours (Fri 12 PM – Sun 2 PM): ~25 min updates
  * Quiet hours (Mon–Thu): ~2.5 hour updates
- If nothing has changed, it skips posting to avoid spam.
- If Discord rate-limits the bot (429s), it automatically backs off with increasing cooldowns before retrying.
- On startup, the bot automatically re-links to the most recent roster message in the channel (if it exists). This prevents duplicate posts after a Render restart or redeploy.
- All subsequent updates edit that roster message in-place using the stored message ID and cached content.

### 🧠 Hosting & Uptime
- Hosted on [Render](https://render.com)
- Uses a minimal Flask app served by waitress for port binding (production-ready WSGI server)
- Kept awake with `UptimeRobot` and `cron-job.org` pinging the `/keepalive` endpoint
- Local files store state between runs (`cancel_state.json`, `message_id.txt`)
- On startup, the bot waits a random 30–120s before connecting to Discord, and uses 15–30 min retry backoff on connection failures.
- During runtime, if the Discord API returns too many requests (429), the bot dynamically scales its cooldown window to reduce load.

### 📦 Bot Versioning
- Displays the current version in logs and via `/version` slash command.
- Version is tracked centrally in `bot/version.py` using Semantic Versioning (e.g., `1.0.0`).

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
| `/version`      | Displays the current bot version                     |
| `/roster`       | Force refresh the roster from Google Sheets          |
| `/sync`         | Sync slash commands with Discord                     |

---

## 📝 Setup Guide (For Devs)

### 1. Environment Variables
Set these in Render or `.env`:
- `DISCORD_TOKEN`
- `ANNOUNCEMENTS_CHANNEL_ID`
- `ROSTER_CHANNEL_ID`
- `LOG_CHANNEL_ID`
- `GOOGLE_CREDS_JSON` (your service account JSON blob, not a path)

### 2. Google Sheets Structure
- Spreadsheet must contain:
  - `Name:` — player name
  - `PARTICIPATION Date (NOT birthday!)` — formatted as MM/DD/YYYY
- The bot filters by the upcoming Sunday’s date.

### 3. Files Used
- `cancel_state.json`: stores cancellation status for the current week
- `message_id.txt`: tracks Discord message ID for roster message reuse

---

## ✍️ To-Do / Future Ideas

- ✅ Player reaction signup on Discord
- 📈 Attendance tracking across weeks
- 📣 Auto-post to Facebook (Scrapped)
- 🔔 Waitlist promotion notifications
- 🤖 DM reminders for promoted players
- 🔐 Admin dashboard or config via slash commands

---

## ✍️ Metadata

- **Current Version:** `1.0.0`
- **Author:** Jerry Wang **#Leaders&TheBest**
