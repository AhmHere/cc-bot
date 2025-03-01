# utils.py

import os
import json
import datetime
import html
from bs4 import BeautifulSoup

from config import DATA_FILE, STORAGE_FILE

def load_bot_data():
    if not os.path.exists(DATA_FILE):
        return {
            "last_message": {},
            "messages_since_last_referral": {},
            "required_messages": {},
            "confirmation_sent": {}
        }
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {
            "last_message": {},
            "messages_since_last_referral": {},
            "required_messages": {},
            "confirmation_sent": {}
        }

def save_bot_data(data_dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data_dict, f, indent=4)

def sync_globals_from_data(data_dict, globals_dict):
    """
    Update the provided global dictionaries based on loaded data.
    """
    globals_dict['last_message'] = {}
    for user_id_str, time_str in data_dict.get("last_message", {}).items():
        try:
            globals_dict['last_message'][int(user_id_str)] = datetime.datetime.fromisoformat(time_str)
        except ValueError:
            continue

    globals_dict['messages_since_last_referral'] = {
        int(k): v for k, v in data_dict.get("messages_since_last_referral", {}).items()
    }
    globals_dict['required_messages'] = {
        int(k): v for k, v in data_dict.get("required_messages", {}).items()
    }
    globals_dict['confirmation_sent'] = {}
    for user_id_str, time_str in data_dict.get("confirmation_sent", {}).items():
        try:
            globals_dict['confirmation_sent'][int(user_id_str)] = datetime.datetime.fromisoformat(time_str)
        except ValueError:
            continue

def sync_data_from_globals(globals_dict):
    """
    Convert in-memory data back to a structure for saving.
    """
    return {
        "last_message": {str(k): v.isoformat() for k, v in globals_dict['last_message'].items()},
        "messages_since_last_referral": globals_dict['messages_since_last_referral'],
        "required_messages": globals_dict['required_messages'],
        "confirmation_sent": {str(k): v.isoformat() for k, v in globals_dict['confirmation_sent'].items()},
    }

def load_posted_entries():
    if not os.path.exists(STORAGE_FILE):
        return {}
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_posted_entries(entries):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=4)

def add_new_entry(channel_id, entry_id):
    posted_entries = load_posted_entries()
    str_chan_id = str(channel_id)
    if str_chan_id not in posted_entries:
        posted_entries[str_chan_id] = []
    if entry_id not in posted_entries[str_chan_id]:
        posted_entries[str_chan_id].append(entry_id)
    save_posted_entries(posted_entries)

def clean_summary(raw_summary):
    decoded = html.unescape(raw_summary)
    cleaned = BeautifulSoup(decoded, "html.parser").get_text()
    if len(cleaned) > 2000:
        cleaned = cleaned[:2000] + "..."
    return cleaned

# Discord helper functions
import discord

async def safe_delete(message: discord.Message):
    try:
        await message.delete()
    except discord.Forbidden:
        print("[ERROR] No permission to delete messages in this channel.")
    except discord.HTTPException as e:
        print(f"[ERROR] Failed to delete message: {e}")

async def safe_dm(member: discord.Member, content: str):
    try:
        await member.send(content)
    except discord.Forbidden:
        print(f"[WARN] Could not DM {member} (privacy settings or block).")
    except discord.HTTPException as e:
        print(f"[ERROR] Failed to send DM to {member}: {e}")

async def log_deleted_link(message: discord.Message):
    from config import DELETED_LINKS_CHANNEL_ID
    channel = message.guild.get_channel(DELETED_LINKS_CHANNEL_ID)
    if not channel:
        print("[ERROR] Deleted links channel not found.")
        return
    embed = discord.Embed(
        title="Link Filter Triggered",
        description=f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}",
        color=0xFF0000,
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name="Message Content", value=message.content, inline=False)
    embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
    await channel.send(embed=embed)