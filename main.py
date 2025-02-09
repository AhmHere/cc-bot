import discord
from discord.ext import commands, tasks
import datetime
import random
import json
import feedparser
import os
from discord.utils import find
from dotenv import load_dotenv

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

RULES_CHANNEL_ID = 1114642068464214066
REFERRALS_CHANNEL_ID = 1336915493323542570
DISCORD_LOGS_CHANNEL_ID = 1336915579935920231
NEEDS_HELP_CHANNEL_ID = 1336915657203388438
COOLDOWN_TIME = 7*24*60*60
GUILD_ID = 558108345949749249
NEWS_CHANNEL_ID = 1336955120750952542 # RSS Feed Channel
RSS_FEED_URL = 'https://www.doctorofcredit.com/feed/' #RSS Feed URL for DOC
DATA_FILE = "data.json"
STORAGE_FILE = "posted_entries.json"

# Load RSS Feed Entry Data
def load_posted_entries():
    if not os.path.exists(STORAGE_FILE):
        return set()
    else:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return set(data)
            except json.JSONDecodeError:
                return set()

def save_posted_entries(entries):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(entries), f, indent=4)

# Initialize global set from JSON
posted_entries = load_posted_entries()

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
    await create_rules_message()
    # Start the background loop
    check_rss_feed.start()
    
@bot.event
async def on_message(message):
    if isinstance(message.author, discord.Member):
        diamond_status_role = find(lambda r: r.name == "Diamond Status", message.author.roles)
        diamond_role = find(lambda r: r.name == "Diamond", message.author.roles)
        has_higher_level_role = any([find(lambda r: r.name == f"Level {i}", message.author.roles) for i in range(10, 31, 10)])
    else:
        diamond_status_role = None
        diamond_role = None
        has_higher_level_role = False

    if message.channel.id == REFERRALS_CHANNEL_ID:

        is_moderator = any([role.name == "Moderator" for role in message.author.roles])

        if not is_moderator and message.author.id in last_message:
            if (datetime.datetime.now() - last_message[message.author.id]).total_seconds() < COOLDOWN_TIME:
                await message.delete()

                if message.author == bot.user:
                    return

                user = await bot.fetch_user(message.author.id)
                await user.send(f"{message.author.mention}, You can only post once in 7 days in the #referrals channel. Your message has been deleted and you can post again after {datetime.datetime.fromtimestamp((last_message[message.author.id] + datetime.timedelta(seconds=COOLDOWN_TIME)).timestamp()).strftime('%Y-%m-%d %H:%M:%S')} UTC time.")
                return

            if not has_higher_level_role and messages_since_last_referral.get(message.author.id, 0) < required_messages.get(message.author.id, 50) and diamond_role:
                await message.delete()
                await message.author.remove_roles(diamond_role)
                user = await bot.fetch_user(message.author.id)
                await user.send("Your Diamond role has been removed because you were not active enough. Become active again and you will regain the Diamond role.")
                return

        last_message[message.author.id] = datetime.datetime.now()
        messages_since_last_referral[message.author.id] = 0
        if not has_higher_level_role:
            required_messages[message.author.id] = random.randint(50, 75)

        data["last_message"] = {str(user_id): timestamp.isoformat() for user_id, timestamp in last_message.items()}
        data["messages_since_last_referral"] = messages_since_last_referral
        data["required_messages"] = required_messages
        save_data(data)

    if message.channel.type == discord.ChannelType.private:
        await process_diamond_member_reply(message)

    if message.author.id in last_message:
        messages_since_last_referral[message.author.id] += 1

        if diamond_status_role and not diamond_role and not has_higher_level_role:
            if messages_since_last_referral[message.author.id] >= required_messages.get(message.author.id, 50):
                diamond_role = discord.utils.get(message.guild.roles, name="Diamond")
                await message.author.add_roles(diamond_role)
                user = await bot.fetch_user(message.author.id)
                await user.send("You have regained the Diamond role!")

        data["messages_since_last_referral"] = messages_since_last_referral
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
        "No Vulgar Language.\n\n"
        "No offensive or inappropriate nicknames.\n\n"
        "No offensive or inappropriate Discord profiles.\n\n"
        "No fake identities or catfishing of any kind.\n\n"
        "Do NOT search for a members' personal information.\n\n"
        "Do NOT reveal any personal information such as credit card information, address, medical information, etc.\n\n"
        "Community members are free to express themselves openly and give constructive criticism and feedback.\n\n"
        "Remain on topic and use channels correctly and appropriately. This includes being cautious when introducing conversations regarding controversial or sensitive topics.\n\n"
        "Spamming is strictly prohibited. Examples include spamming mentions of any user or group, sending excessive amounts of messages, emojis, links, videos, memes, pics, etc.\n\n"
        "Scamming is strictly prohibited. Examples of scams include phishing, fraud, etc.\n\n"
        "NSFW content is strictly prohibited. Examples include text, images, or links featuring nudity, sex, hard violence, or other graphically disturbing content.\n\n"
        "All members must abide by the official Discord ToS and Guidelines.\n" # Doesnt add an extra space for aesthetics
        "https://discordapp.com/terms\n" # Doesnt add an extra space for aesthetics
        "https://discordapp.com/guidelines\n\n"
        "The ability to post referral links is strictly limited to Verified Diamond Status Members. Referral posts are limited to once per week. A minimum level of engagement is required to retain Verified Diamond Member Status.\n\n"
        "The Credit Community promotes diversity and inclusivity. We expect your interactions in this community to be respectful and guided by these rules.\n\n"
        "Staff reserve the right to take action against any user if they deem the user’s actions to be damaging towards the community.\n\n"
        "By joining The Credit Community, you are certifying/admitting that you are at least 18 years old.\n\n"
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
async def check_rss_feed():
    try:
        feed = feedparser.parse(RSS_FEED_URL)
        if not feed.entries:
            return

        channel = bot.get_channel(NEWS_CHANNEL_ID)
        if not channel:
            print(f"Could not find channel with ID {NEWS_CHANNEL_ID}")
            return

        for entry in reversed(feed.entries):
            unique_id = entry.get("id", entry.link)
            if unique_id not in posted_entries:
                posted_entries.add(unique_id)

                # Save to disk so we don't lose this if the bot restarts
                save_posted_entries(posted_entries)

                # Extract info
                title = entry.get("title", "No title")
                link = entry.get("link", "")
                summary = entry.get("summary", "")
                published = entry.get("published", "")

                # Optional summary truncation if needed
                max_length = 2000
                if len(summary) > max_length:
                    summary = summary[:max_length] + "..."

                # Create an Embed
                embed = discord.Embed(
                    title=title,
                    url=link,
                    description=summary,
                    color=0x9B59B6
                )
                embed.set_author(name="Doctor Of Credit")
                embed.set_footer(text=f"Published: {published}")

                await channel.send(embed=embed)

    except Exception as e:
        print(f"Error fetching RSS feed: {e}")

@check_rss_feed.before_loop
async def before_check_rss_feed():
    await bot.wait_until_ready()

# Load environment variables from .env
load_dotenv("secrets/.env")

# Retrieve the token from an environment variable named 'BOT_TOKEN'
my_secret = os.environ['BOT_TOKEN']
bot.run(my_secret)