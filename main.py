import discord
from discord.ext import commands, tasks
import datetime
import random
import json
import feedparser
import os
from discord.utils import find
from dotenv import load_dotenv
import html
from bs4 import BeautifulSoup
import re

bot = commands.Bot(command_prefix='+', intents=discord.Intents.all())

RULES_CHANNEL_ID = 932447065370398791
REFERRALS_CHANNEL_ID = 1105204207172190368
DISCORD_LOGS_CHANNEL_ID = 1105328983245082725
NEEDS_HELP_CHANNEL_ID = 1105328983245082725
COOLDOWN_TIME = 7*24*60*60
GUILD_ID = 931760921825665034
DELETED_LINKS_CHANNEL_ID = 1343112665840615446
# RSS Feed Configurations
RSS_FEEDS = {
    1337930618402770985: ("https://www.doctorofcredit.com/feed/", "Doctor Of Credit", 0x9B59B6),
    1338649589191934042: ("https://dannydealguru.com/feed/", "Danny The Deal Guru", 0x3498DB),
    1338649732771221624: ("https://onemileatatime.com/feed/", "One Mile At A Time", 0xE74C3C),
}

DATA_FILE = "data.json"
STORAGE_FILE = "posted_entries.json"

# Load RSS Feed Entry Data
def load_posted_entries():
    if not os.path.exists(STORAGE_FILE):
        return {}  # Return an empty dictionary if file doesn't exist

    with open(STORAGE_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data  # Returns a dictionary
        except json.JSONDecodeError:
            return {}  # Return empty dict if JSON is invalid

def save_posted_entries(entries):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=4)


# Add a new entry to the tracking file
def add_new_entry(channel_id, entry_id):
    posted_entries = load_posted_entries()
    
    # Ensure the channel ID exists in the dictionary
    if str(channel_id) not in posted_entries:
        posted_entries[str(channel_id)] = []  # Initialize empty list

    # Add the new entry if not already posted
    if entry_id not in posted_entries[str(channel_id)]:
        posted_entries[str(channel_id)].append(entry_id)

    save_posted_entries(posted_entries)  # Save updated entries

# Load Diamond Member Data from JSON file
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {"last_message": {}, "messages_since_last_referral": {}, "required_messages": {}, "confirmation_sent": {}}

    if "confirmation_sent" not in data:
        data["confirmation_sent"] = {}

    return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()
last_message = {int(user_id): datetime.datetime.fromisoformat(timestamp) for user_id, timestamp in data["last_message"].items()}
messages_since_last_referral = {int(user_id): count for user_id, count in data["messages_since_last_referral"].items()}
required_messages = {int(user_id): count for user_id, count in data["required_messages"].items()}
confirmation_sent = {int(user_id): datetime.datetime.fromisoformat(timestamp) for user_id, timestamp in data["confirmation_sent"].items()}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

    await create_rules_message() # Waits for Rules Message to post in #Rules channel

    if not check_rss_feeds.is_running():  # Prevent multiple starts if bot reconnects
        check_rss_feeds.start()

# On message to handle Message Deletion for Referals & Link Filtering as well as Diamond Status tracking and role re-deployment after requirements are met again
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if isinstance(message.channel, discord.DMChannel):
        await process_diamond_member_reply(message)
        return

    if message.guild:
        guild = message.guild
        member = guild.get_member(message.author.id)

        if not member:
            return

        # Referrals message deletion
        if message.channel.id == REFERRALS_CHANNEL_ID:
            is_moderator = any(role.name == "Moderator" for role in message.author.roles)

            if not is_moderator and message.author.id in last_message:
                time_since_last_post = (datetime.datetime.now() - last_message[message.author.id]).total_seconds()

                if time_since_last_post < COOLDOWN_TIME:
                    try:
                        await message.delete()
                        user = await bot.fetch_user(message.author.id)
                        await user.send(
                            f"🚫 {message.author.mention} You can only post **once every 7 days** in #referrals. "
                            f"Your message has been deleted. You can post again on "
                            f"{datetime.datetime.fromtimestamp((last_message[message.author.id] + datetime.timedelta(seconds=COOLDOWN_TIME)).timestamp()).strftime('%Y-%m-%d %H:%M:%S')} UTC."
                        )
                        return
                    except discord.Forbidden:
                        print("❌ ERROR: Bot lacks permission to delete messages in #referrals")
                    except discord.HTTPException as e:
                        print(f"❌ ERROR: Failed to delete message in #referrals: {e}")

            last_message[message.author.id] = datetime.datetime.now()
            messages_since_last_referral[message.author.id] = 0
            required_messages[message.author.id] = random.randint(25, 30)

            data["last_message"] = {str(user_id): timestamp.isoformat() for user_id, timestamp in last_message.items()}
            data["messages_since_last_referral"] = messages_since_last_referral
            data["required_messages"] = required_messages
            save_data(data)

        # Link filtering
        allowed_role_name = "Credit Beginner"
        has_allowed_role = discord.utils.get(member.roles, name=allowed_role_name)

        #Regex pattern used to filter.
        link_pattern = r"\b(?:https?://|www\.)\S+\b|\b\S+\.(com|net|org|gov|edu|io|gg|xyz|me|co|uk|ca|us|au|info|biz|tv|tech|dev|app)\b"

        if re.search(link_pattern, message.content) and not has_allowed_role:
            try:
                await message.delete()
                await message.author.send(
                    f"🚫 You are not allowed to post links in this server unless you have the **{allowed_role_name}** role. "
                    "Please continue chatting in the server until you level up so you can gain access!"
                )
                deleted_links_channel = bot.get_channel(DELETED_LINKS_CHANNEL_ID)
                if deleted_links_channel:
                    embed=discord.Embed(
                        title="Malicious Link Detected",
                        description=(
                            f"**Author:** {message.author.mention}\n\n"
                            f"**Channel:** {message.channel.mention}"
                        ),
                        color=0xFF0000,
                        timestamp=datetime.datetime.now()
                    )
                
                    embed.add_field(name="Message Content", value=message.content, inline=False)
                    embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)

                    await deleted_links_channel.send(embed=embed)
                else:
                    print("❌ ERROR: Could not find the deleted links channel.")
                
                return
            except discord.Forbidden:
                print("❌ ERROR: Bot lacks permission to delete messages.")
            except discord.HTTPException as e:
                print(f"❌ ERROR: Failed to delete message: {e}")

    #Incrementing user's message counts to check if they are able to regain diamond status after losing it i.e. (not meeting message requirment criteria)
    #Additionally, this code segment is only run AFTER the users message has been scanned to ensure it is safe for the server i.e. (user has talked enough to have the *Role name subject to change* role)
    user_id = message.author.id

    #Making sure there's a default so there is not keyerrors
    if user_id not in messages_since_last_referral:
        messages_since_last_referral[user_id] = 0
    if user_id not in messages_since_last_referral:
        required_messages[user_id] = random.randint(25, 30)

    #Incrementing message count from all channels (excluding dms)
    messages_since_last_referral[user_id] += 1

    #Test cases to see if the user has reached the required messages
    if messages_since_last_referral[user_id] >= required_messages[user_id]:
        diamond_status_role = discord.utils.get(message.guild.roles, name="Diamond Status")

        #If they do NOT have the Diamond Status role, add it back (this triggers on_member_update to handle the "Diamond" role or DM).
        if diamond_status_role and diamond_status_role not in member.roles:
            await member.add_roles(diamond_status_role)
            print(f"[DEBUG] Gave Diamond Status back to {member}.")
    
    data["messages_since_last_referral"] = messages_since_last_referral
    data["required_messages"] = required_messages
    save_data(data)

    await bot.process_commands(message)

@bot.event
async def on_member_update(before, after):
    diamond_status_role_name = "Diamond Status"
    diamond_role_name = "Diamond"
    had_diamond_status_role = find(lambda r: r.name == diamond_status_role_name, before.roles)
    has_diamond_status_role = find(lambda r: r.name == diamond_status_role_name, after.roles)
    if has_diamond_status_role and not had_diamond_status_role:
        has_higher_level_role = any([r.name.startswith("Level ") and int(r.name.split(" ")[-1]) >= 10 for r in after.roles])
        if has_higher_level_role:
            diamond_role = discord.utils.get(after.guild.roles, name=diamond_role_name)
            await after.add_roles(diamond_role)
            await after.send("Welcome to the Diamond Membership! You are level 10 or above, therefore you have direct access to the full Diamond Membership. Remember to stay active to retain full Diamond Membership.")
        else:
            await after.send("You are now an active Diamond Status member! To receive full access to Diamond Status perks, please confirm that you understand that you must be ACTIVE in the server to retain your Diamond Status membership perks. If you do not meet the requirements, your role will be revoked until you meet those requirements again. Please reply with \"CONFIRM\" or \"HELP\" to indicate your understanding of this message.")
            confirmation_sent[after.id] = datetime.datetime.now()
            data["confirmation_sent"] = {str(user_id): timestamp.isoformat() for user_id, timestamp in confirmation_sent.items()}
            save_data(data)
    if had_diamond_status_role and not has_diamond_status_role:
        diamond_role = find(lambda r: r.name == diamond_role_name, after.roles)
        if diamond_role:
            await after.remove_roles(diamond_role)
            await after.send("Your Diamond role has been removed because you no longer have the Diamond Status role.")

async def process_diamond_member_reply(message):
    user = message.author
    guild = bot.get_guild(GUILD_ID)
    member = await guild.fetch_member(user.id)
    if message.content.lower() == "confirm" and user.id in confirmation_sent:
        diamond_role = discord.utils.get(guild.roles, name="Diamond")
        await member.add_roles(diamond_role)
        await member.send("Thanks for confirming, you have been given the Diamond role. Welcome to the Diamond Status, and thank you for supporting thee server. You can always type \"HELP\" here to get help from a moderator!")
        del confirmation_sent[user.id]
        data["confirmation_sent"] = {str(user_id): timestamp.isoformat() for user_id, timestamp in confirmation_sent.items()}
        save_data(data)
    elif message.content.lower() == "help":
        help_needed_role = discord.utils.get(guild.roles, name="Help")
        await member.add_roles(help_needed_role)
        logs_channel = bot.get_channel(DISCORD_LOGS_CHANNEL_ID)
        moderator_role = discord.utils.get(guild.roles, name='Moderator')
        await logs_channel.send(f"{member.mention} needs help! {moderator_role.mention}")

async def create_rules_message():
    channel_id = RULES_CHANNEL_ID
    channel = bot.get_channel(channel_id)
    if channel is None:
        print("Rules channel not found!")
        return
    
    async for message in channel.history(limit=100):
        if message.author == bot.user:
            await message.delete()

    rules_message_part1 = (
        "Keep your conversations civil.\n\n"
        "No vulgar language.\n\n"
        "No offensive or inappropriate nicknames.\n\n"
        "No offensive or inappropriate Discord profiles.\n\n"
        "No fake identities or catfishing of any kind.\n\n"
        "Do NOT search for a members' personal information.\n\n"
        "Do NOT reveal any personal information such as credit card information, address, medical information, etc.\n\n"
        "Community members are free to express themselves openly and give constructive criticism and feedback.\n\n"
        "Remain on topic and use channels correctly and appropriately. This includes being cautious when introducing conversations regarding controversial or sensitive topics.\n\n"
        "Spamming is strictly prohibited. Examples include spamming mentions of any user or group, sending excessive amounts of messages, emojis, links, videos, memes, pics, etc.\n\n"
        "Scamming is strictly prohibited. Examples of scams include phishing, fraud, etc.\n\n"
        "Payed promotions of any kind is strictly prohibited. Examples include paying people to use your referral links, follow your socials, etc.\n\n"
        "NSFW content is strictly prohibited. Examples include text, images, or links featuring nudity, sex, hard violence, or other graphically disturbing content.\n\n"
        "All members must abide by the official Discord ToS and Guidelines.\n" # Doesnt add an extra space for aesthetics
        "https://discordapp.com/terms\n" # Doesnt add an extra space for aesthetics
        "https://discordapp.com/guidelines\n\n"
        "The ability to post referral links is strictly limited to Verified Diamond Status Members. Referral posts are limited to once per week. A minimum level of engagement is required to retain Verified Diamond Member Status.\n\n"
        "The Credit Community promotes diversity and inclusivity. We expect your interactions in this community to be respectful and guided by these rules.\n\n"
        "Staff reserve the right to take action against any user if they deem the user’s actions to be damaging towards the community.\n\n"
        "By joining The Credit Community, you are certifying/admitting that you are at least 18 years old.\u200B\n\u200B\n"
    )

    rules_message_part2 = (
        "React with a ✅ below to verify that you have read and agree to the rules."
    
    )
    #Rules part 1
    embed = discord.Embed(
        title="The Credit Community's Rules and Guidelines",
        description=rules_message_part1,
        color=0x000000
    )
    #Verification
    embed.add_field(
        name="Verification",
        value=rules_message_part2,
        inline=False
    )
    embed.set_author(name="Welcome to The Credit Community")

    message1 = await channel.send(embed=embed)
    await message1.add_reaction('✅')

''' Server no longer has the Verified role, reinstate if server wants to bring back the role '''
@bot.event
async def on_raw_reaction_add(payload):
    if payload.channel_id == RULES_CHANNEL_ID and payload.emoji.name == "✅":
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        verified_role = discord.utils.get(guild.roles, name="Verified")
        await member.add_roles(verified_role)

@bot.command()
@commands.has_any_role('Moderator', 'Owner', 'Intern')
async def clear(ctx, user: discord.Member):
    if user.id in last_message:
        del last_message[user.id]
        data["last_message"] = {str(user_id): timestamp.isoformat() for user_id, timestamp in last_message.items()}
        save_data(data)
        await ctx.send(f"{user.mention}'s cooldown has been cleared.")
    else:
        await ctx.send(f"{user.mention} doesn't have an active cooldown.")

# RSS Feed Task: This background task fetches the RSS feed every 5 minutes and posts new items
# Store IDs or links of already posted items
@tasks.loop(minutes=5)
async def check_rss_feeds():
    try:
        for channel_id, (feed_url, feed_name, embed_color) in RSS_FEEDS.items():
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                continue  # Skip if no new entries

            discord_channel = bot.get_channel(channel_id)
            if not discord_channel:
                print(f"Could not find channel with ID {channel_id}")
                continue

            for entry in reversed(feed.entries):  # Process from oldest to newest
                unique_id = entry.get("id", entry.link)

                # Check if this entry has already been posted
                posted_entries = load_posted_entries()
                if str(channel_id) in posted_entries and unique_id in posted_entries[str(channel_id)]:
                    continue  # Skip already posted entry

                # Extract info from the feed entry
                title = entry.get("title", "No title")
                link = entry.get("link", "")

                # Clean the summary: Start with raw, then decode HTML entities and strip HTML tags
                raw_summary = entry.get("summary", "")
                decoded_summary = html.unescape(raw_summary)
                cleaned_summary = BeautifulSoup(decoded_summary, "html.parser").get_text()

                # Truncate summary if it's too long
                max_length = 2000
                if len(cleaned_summary) > max_length:
                    cleaned_summary = cleaned_summary[:max_length] + "..."

                # Create an Embed for Discord
                embed = discord.Embed(
                    title=title,
                    url=link,
                    description=cleaned_summary,
                    color=embed_color #Different Color Per Channel
                )
                embed.set_author(name=feed_name)
                embed.set_footer(text=f"Published: {entry.get('published', '')}")

                # Send the embed to the correct Discord channel
                await discord_channel.send(embed=embed)

                # Save this entry as posted
                add_new_entry(channel_id, unique_id)

    except Exception as e:
        print(f"Error fetching RSS feeds: {e}")

# Wait until bot is ready before starting the loop
@check_rss_feeds.before_loop
async def before_check_rss_feeds():
    await bot.wait_until_ready()

# Load environment variables from .env
load_dotenv("secrets/.env")

# Retrieve the token from an environment variable named 'BOT_TOKEN'
my_secret = os.environ['BOT_TOKEN']
bot.run(my_secret)