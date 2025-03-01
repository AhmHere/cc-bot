# cogs/diamond_status.py

import discord
from discord.ext import commands
import datetime
import random
import re
from discord.utils import get

from config import (
    REFERRALS_CHANNEL_ID,
    MODERATOR_ROLE_NAME,
    ALLOWED_ROLE_NAME,
    DIAMOND_STATUS_ROLE_NAME,
    DIAMOND_ROLE_NAME,
    HELP_NEEDED_ROLE_NAME,
    DISCORD_LOGS_CHANNEL_ID,
    COOLDOWN_TIME,
    GUILD_ID
)
from utils import safe_delete, safe_dm

class DiamondStatusCog(commands.Cog):
    """Manages Diamond Status, referral cooldowns, link filtering, and DM confirmations."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Process DMs for Diamond confirmation
        if isinstance(message.channel, discord.DMChannel):
            await self.process_diamond_member_reply(message)
            return

        guild = message.guild
        member = guild.get_member(message.author.id)
        if not member:
            return

        # Access shared globals from bot
        globals_data = self.bot.globals_data

        # 1. Referral channel handling
        if message.channel.id == REFERRALS_CHANNEL_ID:
            is_mod = any(r.name == MODERATOR_ROLE_NAME for r in member.roles)
            user_id = message.author.id
            if not is_mod and user_id in globals_data['last_message']:
                elapsed = (datetime.datetime.now() - globals_data['last_message'][user_id]).total_seconds()
                if elapsed < COOLDOWN_TIME:
                    await safe_delete(message)
                    await safe_dm(
                        member,
                        f"🚫 {message.author.mention} You can only post **once every 7 days** in #referrals.\n"
                        "Your message has been deleted. You can post again on "
                        f"{(globals_data['last_message'][user_id] + datetime.timedelta(seconds=COOLDOWN_TIME)).strftime('%Y-%m-%d %H:%M:%S')} UTC."
                    )
                    return
            globals_data['last_message'][user_id] = datetime.datetime.now()
            globals_data['messages_since_last_referral'][user_id] = 0
            globals_data['required_messages'][user_id] = random.randint(25, 30)

        # 2. Link filtering for users without the allowed role
        if not get(member.roles, name=ALLOWED_ROLE_NAME):
            link_pattern = r"\b(?:https?://|www\.)\S+\b|\b\S+\.(com|net|org|gov|edu|io|gg|xyz|me|co|uk|ca|us|au|info|biz|tv|tech|dev|app)\b"
            if re.search(link_pattern, message.content):
                await safe_delete(message)
                await safe_dm(
                    member,
                    f"🚫 You are not allowed to post links in this server unless you have the **{ALLOWED_ROLE_NAME}** role. Please keep chatting and leveling up!"
                )
                from utils import log_deleted_link
                await log_deleted_link(message)
                return

        # 3. Diamond Status message counting
        user_id = message.author.id
        globals_data['messages_since_last_referral'].setdefault(user_id, 0)
        globals_data['required_messages'].setdefault(user_id, random.randint(25, 30))
        globals_data['messages_since_last_referral'][user_id] += 1

        if globals_data['messages_since_last_referral'][user_id] >= globals_data['required_messages'][user_id]:
            diamond_status_role = get(member.guild.roles, name=DIAMOND_STATUS_ROLE_NAME)
            if diamond_status_role and diamond_status_role not in member.roles:
                await member.add_roles(diamond_status_role)
                print(f"[DEBUG] Gave Diamond Status to {member}.")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        globals_data = self.bot.globals_data
        before_roles = set(before.roles)
        after_roles = set(after.roles)

        diamond_status_role = get(after.guild.roles, name=DIAMOND_STATUS_ROLE_NAME)
        diamond_role = get(after.guild.roles, name=DIAMOND_ROLE_NAME)

        # Diamond Status added
        if diamond_status_role in after_roles and diamond_status_role not in before_roles:
            if diamond_role and diamond_role not in after_roles:
                await after.add_roles(diamond_role)
            await safe_dm(
                after,
                "You are now an active Diamond Status member! To receive full Diamond membership perks, "
                "please confirm you understand you **must stay active**. If you do not meet the requirements, "
                "the role will be removed until you meet them again.\n\n"
                "Please reply with **CONFIRM** or **HELP**."
            )
            globals_data['confirmation_sent'][after.id] = datetime.datetime.now()

        # Diamond Status removed
        if diamond_status_role in before_roles and diamond_status_role not in after_roles:
            if diamond_role in after_roles:
                await after.remove_roles(diamond_role)
                await safe_dm(
                    after,
                    "Your Diamond role has been removed because you no longer have Diamond Status."
                )

    async def process_diamond_member_reply(self, message):
        user = message.author
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        try:
            member = await guild.fetch_member(user.id)
        except discord.NotFound:
            return

        globals_data = self.bot.globals_data

        if message.content.lower() == "confirm":
            if user.id in globals_data['confirmation_sent']:
                diamond_role = get(guild.roles, name=DIAMOND_ROLE_NAME)
                if diamond_role and diamond_role not in member.roles:
                    await member.add_roles(diamond_role)
                await safe_dm(
                    member,
                    "Thanks for confirming! You now have the Diamond role. Enjoy your perks, and stay active!"
                )
                del globals_data['confirmation_sent'][user.id]
        elif message.content.lower() == "help":
            help_role = get(guild.roles, name=HELP_NEEDED_ROLE_NAME)
            if help_role:
                await member.add_roles(help_role)
            logs_channel = self.bot.get_channel(DISCORD_LOGS_CHANNEL_ID)
            if logs_channel:
                mod_role = get(guild.roles, name=MODERATOR_ROLE_NAME)
                await logs_channel.send(
                    f"{member.mention} needs help! {mod_role.mention if mod_role else ''}"
                )

async def setup(bot):
    await bot.add_cog(DiamondStatusCog(bot))