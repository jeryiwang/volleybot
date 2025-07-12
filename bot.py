import os
import discord
from discord.ext import tasks
import datetime

# Discord setup
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')
    post_roster.start()

@tasks.loop(minutes=60)
async def post_roster():
    # TEMP MESSAGE (we'll pull real names from Sheets later)
    today = datetime.date.today()
    sunday = today + datetime.timedelta((6 - today.weekday()) % 7)

    message = f"""📋 **THM Volleyball Roster – Sunday, {sunday.strftime('%B %d')}**

✅ Confirmed to Play:
1. Alice
2. Bob
3. Charlie
...

📍 KMCD Gym | 2–5 PM  
🚪 Enter through the double doors (north side)  
📝 Please arrive on time — late spots may be given to waitlisters."""

    channel = client.get_channel(CHANNEL_ID)
    await channel.send(message)

client.run(DISCORD_TOKEN)
