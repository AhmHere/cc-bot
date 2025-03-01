import discord
from discord.ext import commands, tasks
from config import RULES_CHANNEL_ID
from utils import safe_delete

class RulesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_rules.start()

    def cog_unload(self):
        self.check_rules.cancel()

    async def create_rules_message(self):
        channel = self.bot.get_channel(RULES_CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(RULES_CHANNEL_ID)
            except Exception as e:
                print(f"[ERROR] Could not fetch rules channel: {e}")
                return

        # Check if a rules message already exists
        rules_message = None
        async for message in channel.history(limit=100):
            if message.author == self.bot.user and message.embeds:
                embed = message.embeds[0]
                if embed.title == "The Credit Community's Rules and Guidelines":
                    rules_message = message
                    break

        if rules_message:
            print("[INFO] Rules message already exists; skipping post.")
            return

        # Create the rules message
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
        rules_message_part2 = "React with a ✅ below to verify that you have read and agree to these rules."

        embed = discord.Embed(
            title="The Credit Community's Rules and Guidelines",
            description=rules_message_part1,
            color=0x000000
        )
        embed.add_field(name="Verification", value=rules_message_part2, inline=False)
        embed.set_author(name="Welcome to The Credit Community")

        new_message = await channel.send(embed=embed)
        await new_message.add_reaction('✅')
        print("[INFO] Rules message posted.")

    @tasks.loop(hours=1)
    async def check_rules(self):
        channel = self.bot.get_channel(RULES_CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(RULES_CHANNEL_ID)
            except Exception as e:
                print(f"[ERROR] Could not fetch rules channel during check: {e}")
                return
        rules_found = False
        async for message in channel.history(limit=100):
            if message.author == self.bot.user and message.embeds:
                embed = message.embeds[0]
                if embed.title == "The Credit Community's Rules and Guidelines":
                    rules_found = True
                    break
        if not rules_found:
            print("[INFO] No rules message found; posting a new one.")
            await self.create_rules_message()

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.channel.id == RULES_CHANNEL_ID and message.author == self.bot.user:
            if message.embeds and message.embeds[0].title == "The Credit Community's Rules and Guidelines":
                print("[INFO] Rules message deleted; reposting...")
                await self.create_rules_message()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.channel_id == RULES_CHANNEL_ID and payload.emoji.name == "✅":
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
            member = guild.get_member(payload.user_id)
            if not member or member.bot:
                return
            verified_role = discord.utils.get(guild.roles, name="Verified")
            if verified_role:
                await member.add_roles(verified_role)

async def setup(bot):
    await bot.add_cog(RulesCog(bot))