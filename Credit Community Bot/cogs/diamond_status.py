# cogs/diamond_status.py

import discord
from discord.ext import commands, tasks
import datetime
import re
from discord.utils import get
import urllib.parse

from config import (
    REFERRALS_CHANNEL_ID,
    MODERATOR_ROLE_NAME,
    MINIMUM_ALLOWED_ROLE_NAME,
    DIAMOND_STATUS_ROLE_NAME,
    DIAMOND_ROLE_NAME,
    HELP_NEEDED_ROLE_NAME,
    DISCORD_LOGS_CHANNEL_ID,
    COOLDOWN_TIME,
    GUILD_ID,
)
from utils import safe_delete, safe_dm

class DiamondStatusCog(commands.Cog):
    """Manages Diamond Status (paid), awards/removes Diamond (activity), referral cooldowns,
    link filtering, DM replies, and inactivity removal based on last_activity."""

    def __init__(self, bot):
        self.bot = bot
        # Start the inactivity check task (runs every 24 hours)
        self.check_inactivity.start()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Process DMs for Diamond confirmation/help
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

        # --- Track last activity for inactivity checks (every message)
        globals_data.setdefault("last_activity", {})
        globals_data["last_activity"][user_id] = datetime.datetime.now()

        # 1) Referral channel handling (gate by DIAMOND/OG/MOD; 7-day cooldown)
        if message.channel.id == REFERRALS_CHANNEL_ID:
            is_mod = any(r.name == MODERATOR_ROLE_NAME for r in member.roles)

            # Cooldown check
            if not is_mod and user_id in globals_data.get("last_message", {}):
                elapsed = (datetime.datetime.now() - globals_data["last_message"][user_id]).total_seconds()
                if elapsed < COOLDOWN_TIME:
                    await safe_delete(message)
                    await safe_dm(
                        member,
                        f"🚫 {message.author.mention} You can only post **once every 7 days** in #referrals.\n"
                        "Your message has been deleted. You can post again on "
                        f"{(globals_data['last_message'][user_id] + datetime.timedelta(seconds=COOLDOWN_TIME)).strftime('%Y-%m-%d %H:%M:%S')} UTC."
                    )
                    return

            # Eligibility requires Diamond (or OG or Moderator)
            diamond_role = get(member.guild.roles, name=DIAMOND_ROLE_NAME)
            og_role = get(member.guild.roles, name="OG")
            allowed = is_mod or (diamond_role in member.roles) or (og_role in member.roles)
            if not allowed:
                await safe_delete(message)
                await safe_dm(
                    member,
                    "🚫 You are not eligible to post in #referrals yet. "
                    "Earn the **Diamond** role by staying active (25 messages)."
                )
                return

            # Only after a valid referral post: stamp last_message and reset the activity counter
            globals_data.setdefault("last_message", {})
            globals_data["last_message"][user_id] = datetime.datetime.now()
            globals_data.setdefault("messages_since_last_referral", {})
            globals_data["messages_since_last_referral"][user_id] = 0

        # 2) Link filtering for users without the minimum allowed role
        decoded_message = urllib.parse.unquote(message.content or "")
        cleaned_message = decoded_message.replace("\n", "").replace(" ", "")

        allowed_role = get(message.guild.roles, name=MINIMUM_ALLOWED_ROLE_NAME)
        has_allowed_role = False
        if allowed_role:
            has_allowed_role = any(role.position >= allowed_role.position for role in member.roles)

        if not has_allowed_role:
            link_pattern = r"\b(?:https?|hxxps?|ftp):\/\/[^\s/$.?#].[^\s]*|\b[a-zA-Z0-9.-]+\.(?:com|net|org|gov|edu|io|gg|xyz|me|co|uk|ca|us|au|info|biz|tv|tech|dev|app)\b"
            if re.search(link_pattern, cleaned_message, re.IGNORECASE):
                await safe_delete(message)
                await safe_dm(
                    member,
                    f"🚫 You are not allowed to post links in this server unless you have the **{MINIMUM_ALLOWED_ROLE_NAME}** role. "
                    "Please keep chatting and leveling up!"
                )
                try:
                    from utils import log_deleted_link
                    await log_deleted_link(message)
                except Exception:
                    pass
                return

        # 3) Activity counting: only for paid (Diamond Status). Award Diamond at 25.
        diamond_status_role = get(member.guild.roles, name=DIAMOND_STATUS_ROLE_NAME)
        if diamond_status_role in member.roles:
            globals_data.setdefault("messages_since_last_referral", {})
            globals_data["messages_since_last_referral"][user_id] = (
                globals_data["messages_since_last_referral"].get(user_id, 0) + 1
            )

            if globals_data["messages_since_last_referral"][user_id] >= 25:
                diamond_role = get(member.guild.roles, name=DIAMOND_ROLE_NAME)
                if diamond_role and diamond_role not in member.roles:
                    try:
                        await member.add_roles(diamond_role, reason="Met 25 message threshold")
                        print(f"[DEBUG] Gave Diamond to {member}.")
                    except discord.Forbidden:
                        print(f"[ERROR] Cannot add '{DIAMOND_ROLE_NAME}' – raise bot role above it.")
                    except Exception as e:
                        print(f"[ERROR] Adding '{DIAMOND_ROLE_NAME}' to {member} failed: {e}")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        globals_data = self.bot.globals_data
        before_roles = set(before.roles)
        after_roles = set(after.roles)

        diamond_status_role = get(after.guild.roles, name=DIAMOND_STATUS_ROLE_NAME)
        diamond_role = get(after.guild.roles, name=DIAMOND_ROLE_NAME)

        # When Diamond Status (paid) is added → grant Diamond immediately (test run).
        # NOTE: Do NOT stamp last_message here, or you'd block their first referral post.
        if diamond_status_role in after_roles and diamond_status_role not in before_roles:
            if diamond_role and diamond_role not in after_roles:
                try:
                    await after.add_roles(diamond_role, reason="New subscriber — provisional Diamond")
                    globals_data.setdefault("messages_since_last_referral", {})
                    globals_data["messages_since_last_referral"][after.id] = 0
                    await safe_dm(
                        after,
                        "🎉 Thanks for subscribing! You’ve been given **Diamond** right away so you can try #referrals.\n"
                        "Keep chatting (25 msgs) to maintain Diamond; inactivity will remove it."
                    )
                except discord.Forbidden:
                    print(f"[ERROR] Cannot add '{DIAMOND_ROLE_NAME}' – raise bot role above it.")
                except Exception as e:
                    print(f"[ERROR] Adding '{DIAMOND_ROLE_NAME}' to {after} failed: {e}")

        # If Diamond Status is removed → remove Diamond too
        if diamond_status_role in before_roles and diamond_status_role not in after_roles:
            if diamond_role in after_roles:
                try:
                    await after.remove_roles(diamond_role, reason="Lost subscription")
                except Exception as e:
                    print(f"[ERROR] Could not remove Diamond from {after}: {e}")
                await safe_dm(after, "Your **Diamond** was removed because your subscription ended.")

    async def process_diamond_member_reply(self, message: discord.Message):
        user = message.author
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        try:
            member = await guild.fetch_member(user.id)
        except discord.NotFound:
            return

        globals_data = self.bot.globals_data
        content = (message.content or "").strip().lower()

        if content == "confirm":
            # No role grant here. Diamond is auto-granted on subscribe, and
            # maintained/removed by activity + inactivity task.
            await safe_dm(
                member,
                "Thanks for confirming! Reminder: **Diamond** stays active with regular chat "
                "(25 messages per window). Keep it up to retain access to #referrals. 💎"
            )
            if "confirmation_sent" in globals_data:
                globals_data["confirmation_sent"].pop(user.id, None)
            return

        elif content == "help":
            HELP_COOLDOWN = 300  # 5 minutes
            now = datetime.datetime.now()

            if "last_help" not in globals_data:
                globals_data["last_help"] = {}

            if user.id in globals_data["last_help"]:
                elapsed = (now - globals_data["last_help"][user.id]).total_seconds()
                if elapsed < HELP_COOLDOWN:
                    remaining = int(HELP_COOLDOWN - elapsed)
                    await safe_dm(member, f"Your help request is on cooldown. Please wait {remaining} more seconds before requesting help again.")
                    return

            globals_data["last_help"][user.id] = now

            help_role = get(guild.roles, name=HELP_NEEDED_ROLE_NAME)
            if help_role:
                try:
                    await member.add_roles(help_role, reason="User requested help via DM")
                except Exception as e:
                    print(f"[ERROR] Could not add help role to {member}: {e}")

            logs_channel = self.bot.get_channel(DISCORD_LOGS_CHANNEL_ID)
            if logs_channel:
                mod_role = get(guild.roles, name=MODERATOR_ROLE_NAME)
                await logs_channel.send(
                    f"{member.mention} needs help! {mod_role.mention if mod_role else ''}"
                )
            return

    @tasks.loop(hours=24)
    async def check_inactivity(self):
        """Periodically remove Diamond role from users inactive beyond a threshold."""
        now = datetime.datetime.now()
        inactivity_threshold = 14 * 24 * 60 * 60  # 14 days
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        # Use last_activity (real chat activity), not last_message (referrals).
        for user_id, last_time in self.bot.globals_data.get("last_activity", {}).items():
            if (now - last_time).total_seconds() > inactivity_threshold:
                member = guild.get_member(user_id)
                if member:
                    diamond_role = get(member.guild.roles, name=DIAMOND_ROLE_NAME)
                    if diamond_role and diamond_role in member.roles:
                        try:
                            await member.remove_roles(diamond_role)
                            print(f"[INFO] Removed Diamond from {member} due to inactivity.")
                            await safe_dm(
                                member,
                                "💤 Your **Diamond** role was removed because you’ve been inactive for 14+ days. "
                                "Stay active (25 msgs) to earn it back!"
                            )
                        except Exception as e:
                            print(f"[ERROR] Could not remove Diamond from {member}: {e}")

    @check_inactivity.before_loop
    async def _wait_ready(self):
        """Ensure the bot is fully ready before the inactivity loop starts."""
        await self.bot.wait_until_ready()
        
async def setup(bot):
    await bot.add_cog(DiamondStatusCog(bot))
