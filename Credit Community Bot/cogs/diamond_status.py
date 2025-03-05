# cogs/diamond_status.py

import discord
from discord.ext import commands, tasks
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
    """Manages Diamond Status, referral cooldowns, link filtering, and DM confirmations, and removes roles for inactivity."""

    def __init__(self, bot):
        self.bot = bot
        # Start the inactivity check task (runs every 24 hours)
        self.check_inactivity.start()

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
        user_id = message.author.id

        # 1. Referral channel handling
        if message.channel.id == REFERRALS_CHANNEL_ID:
            is_mod = any(r.name == MODERATOR_ROLE_NAME for r in member.roles)
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
            # Update referral post timestamp and reset message count/threshold
            globals_data['last_message'][user_id] = datetime.datetime.now()
            globals_data['messages_since_last_referral'][user_id] = 0
            globals_data['required_messages'][user_id] = random.randint(25, 30)

            # **New Check:** Ensure the user is active enough (has Diamond Status)
            diamond_status_role = get(member.guild.roles, name=DIAMOND_STATUS_ROLE_NAME)
            if diamond_status_role not in member.roles:
                await safe_delete(message)
                await safe_dm(member, "🚫 You are not active enough to post in #referrals. Keep chatting in the server to earn Diamond Status!")
                return

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

        # 3. Diamond Status message counting for activity tracking
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

        # When Diamond Status is added, also add Diamond role and send DM confirmation
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

        # If Diamond Status is removed, also remove Diamond role
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
            HELP_COOLDOWN = 300  # Cooldown in seconds (5 minutes)
            now = datetime.datetime.now()
    
            # Ensure the 'last_help' dictionary exists in globals_data
            if 'last_help' not in globals_data:
                globals_data['last_help'] = {}
    
            # Check if the user is on cooldown
            if user.id in globals_data['last_help']:
                elapsed = (now - globals_data['last_help'][user.id]).total_seconds()
                if elapsed < HELP_COOLDOWN:
                    remaining = int(HELP_COOLDOWN - elapsed)
                    await safe_dm(member, f"Your help request is on cooldown. Please wait {remaining} more seconds before requesting help again.")
                    return
    
            # Update the last help timestamp
            globals_data['last_help'][user.id] = now

            help_role = get(guild.roles, name=HELP_NEEDED_ROLE_NAME)
            if help_role:
                await member.add_roles(help_role)
            logs_channel = self.bot.get_channel(DISCORD_LOGS_CHANNEL_ID)
            if logs_channel:
                mod_role = get(guild.roles, name=MODERATOR_ROLE_NAME)
                await logs_channel.send(
                    f"{member.mention} needs help! {mod_role.mention if mod_role else ''}"
                )

    @tasks.loop(hours=24)
    async def check_inactivity(self):
        """Periodically remove Diamond Status and Diamond roles from users inactive beyond a threshold (TBD)."""
        now = datetime.datetime.now()
        # Defined inactivity threshold
        inactivity_threshold = 14 * 24 * 60 * 60  # 14 days in seconds
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        
        for user_id, last_msg_time in self.bot.globals_data.get('last_message', {}).items():
            if (now - last_msg_time).total_seconds() > inactivity_threshold:
                member = guild.get_member(user_id)
                if member:
                    diamond_status_role = get(member.guild.roles, name=DIAMOND_STATUS_ROLE_NAME)
                    diamond_role = get(member.guild.roles, name=DIAMOND_ROLE_NAME)
                    if diamond_status_role in member.roles:
                        try:
                            await member.remove_roles(diamond_status_role)
                            print(f"[INFO] Removed Diamond Status from {member} due to inactivity.")
                        except Exception as e:
                            print(f"[ERROR] Could not remove Diamond Status from {member}: {e}")
                    if diamond_role in member.roles:
                        try:
                            await member.remove_roles(diamond_role)
                            print(f"[INFO] Removed Diamond role from {member} due to inactivity.")
                        except Exception as e:
                            print(f"[ERROR] Could not remove Diamond role from {member}: {e}")

async def setup(bot):
    await bot.add_cog(DiamondStatusCog(bot))