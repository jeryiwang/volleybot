# 🏐 THM Volleyball Discord Bot

This is a custom-built Discord bot that automates weekly volleyball sign-up tracking, announcements, and roster management for our Sunday 2–5pm KMCD Gym volleyball group.

The bot reads player sign-ups from a Google Form response sheet and keeps the Discord server in sync — posting the weekly roster, handling last-minute cancellations, and avoiding repetitive manual work.

---

## 💡 Features

### 📅 Weekly Roster Automation
- Pulls the latest sign-up data from Google Sheets.
- Auto-posts the Sunday roster to the designated Discord channel.
- Separates players into ✅ Confirmed (up to 21) and ⏳ Waitlist.

### 🛑 Cancellation Commands
- Admins can cancel or uncancel volleyball with:
  - `/cancel` → marks the event as cancelled with a reason
  - `/uncancel` → reverts the cancellation
- Updates both the roster post and announcements channel to reflect the new status.

### 🔁 Smart Weekly Reset
- Every week, the bot automatically:
  - Calculates the next Sunday
  - Clears any previous cancellation state
  - Refreshes the roster from the sheet
- This keeps the JSON lean and avoids clutter from past weeks.

### 🔄 Frequent Roster Updates
- The bot runs continuously (hosted on Render) and updates the roster every minute.
- If the roster hasn’t changed, it doesn’t re-post to avoid spam.
- Posts a log message every 15 minutes for heartbeat monitoring.

### 🧠 Hosting & Uptime
- Hosted on [Render.com](https://render.com)
- Uses a Flask server + `UptimeRobot` and `cron-job.org` to ping `/keepalive` and prevent spin-down
- Stores persistent state in small local files (e.g. `message_id.txt`, `cancel_state.json`)

---

## ⚙️ Tech Stack

- **Python 3.10+**
- `discord.py` (for Discord bot and slash commands)
- `Flask` (for the keepalive endpoint)
- `gspread` + `oauth2client` (for Google Sheets integration)
- Hosted on **Render**
- Monitored with **UptimeRobot** and **cron-job.org**

---

## 🧪 Example Commands

| Slash Command | Description |
|---------------|-------------|
| `/cancel [reason]` | Cancels Sunday volleyball and posts an announcement |
| `/uncancel`        | Uncancels the game and updates all messages |

---

## 📝 Setup Notes (for devs)

1. **Environment Variables**
   - `DISCORD_TOKEN`
   - `ANNOUNCEMENTS_CHANNEL_ID`
   - `ROSTER_CHANNEL_ID`
   - `LOG_CHANNEL_ID`
   - `GOOGLE_CREDS_JSON` (your service account JSON blob)
   - `PORT` (optional; default = 8080)

2. **Google Sheets**
   - Must have columns: `Name:` and `PARTICIPATION Date (NOT birthday!)`
   - Sheet is filtered by the upcoming Sunday's date.

3. **Files used**
   - `cancel_state.json`: holds cancellation info for the *current* Sunday only
   - `message_id.txt`: tracks the latest Discord message ID so it can be edited instead of reposted

---

## ✍️ To-Do / Future Ideas

- ✅ Player reaction signup on Discord
- 📈 Attendance tracking across weeks
- 📣 Auto-post to Facebook
- 🔔 Waitlist promotion notifications
- 🧠 Smarter DM reminders for players
