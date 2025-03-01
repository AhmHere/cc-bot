# main.py
import os
import asyncio
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
from utils import load_bot_data, sync_globals_from_data, sync_data_from_globals, save_bot_data
from config import GUILD_ID

# Load environment variables
load_dotenv("secrets/.env")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='+', intents=intents)

# Global data for tracking
globals_data = {
    "last_message": {},
    "messages_since_last_referral": {},
    "required_messages": {},
    "confirmation_sent": {}
}
# Load data from file and sync into globals_data
data_dict = load_bot_data()
sync_globals_from_data(data_dict, globals_data)
bot.globals_data = globals_data

# Autosave task: every 5 minutes, save the current globals to data.json and ensure user data is stored
@tasks.loop(minutes=5)
async def autosave_data():
    save_bot_data(sync_data_from_globals(bot.globals_data))
    print("[INFO] Autosaved global data.")

@bot.event
async def on_ready():
    print(f"[INFO] {bot.user} has connected to Discord!")

    guild = discord.Object(id=GUILD_ID)
    try:
        await bot.tree.sync(guild=guild)
        print(f"[INFO] Command tree synced for guild: {GUILD_ID}")
        cmds = bot.tree.get_commands(guild=guild)
        print("Registered commands for guild:", cmds)
    except Exception as e:
        print(f"[ERROR] Failed to sync command tree: {e}")

    autosave_data.start()

# (Extension loading code and other startup tasks would go here)

async def main():
    # List of cogs to load
    initial_extensions = [
        'cogs.rss_feed',
        'cogs.diamond_status',
        'cogs.rules',
        'cogs.admin',
        'cogs.commands'
    ]
    # Load extensions asynchronously
    for ext in initial_extensions:
        try:
            await bot.load_extension(ext)
            print(f"[INFO] Loaded extension {ext}")
        except Exception as e:
            print(f"[ERROR] Failed to load extension {ext}: {e}")

    token = os.getenv("BOT_TOKEN")
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())