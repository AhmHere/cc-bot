# cogs/credit_application.py
import discord
from discord.ext import commands
from discord import Interaction, app_commands

class DataPointsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("[DEBUG] DataPointsCog loaded – slash command should be registered.")

    @app_commands.command(name="datapoints", description="Submit your credit card application DataPoints")
    @app_commands.choices(status=[
        app_commands.Choice(name="✅ Accepted", value="✅ Accepted"),
        app_commands.Choice(name="❌ Declined", value="❌ Declined")
    ])
    async def datapoints(
        self,
        interaction: discord.Interaction,
        credit_card_name: str,
        status: str,
        credit_limit: str,
        income: str,
        credit_score: int,
        accounts: str,
        aaoa: str,
        x6inquiries: str,
        x12inquiries: str,
        x24inquiries: str,
        bureau_pulled: str,
        state: str,
        approval_date: str
    ):
        # Determine embed color based on approval or denial
        if status == "✅ Accepted":
            embed_color = 0x00FF00  # green for accepted
        else:
            embed_color = 0xFF0000  # red for declined

        # Process the data points submission
        embed = discord.Embed(
            title="**Credit Card Data Points**",
            color=embed_color
        )

        embed.add_field(name="\n", value=f"**Credit Card Name:** {credit_card_name}", inline=False)
        embed.add_field(name="\n", value=f"**Status:** {status}", inline=False)
        embed.add_field(name="\n", value=f"**Credit Limit:** {credit_limit}", inline=False)
        embed.add_field(name="\n", value=f"**Income:** {income}", inline=False)
        embed.add_field(name="\n", value=f"**Credit Score:** {credit_score}", inline=False)
        embed.add_field(name="\n", value=f"**Number of Accounts:** {accounts}", inline=False)
        embed.add_field(name="\n", value=f"**AAoA:** {aaoa}", inline=False)
        embed.add_field(name="\n", value=f"**Inquiries:** {x6inquiries}, {x12inquiries}, {x24inquiries}", inline=False)
        embed.add_field(name="\n", value=f"**Bureau Pulled:** {bureau_pulled}", inline=False)
        embed.add_field(name="\n", value=f"**State:** {state}", inline=False)
        embed.add_field(name="\n", value=f"**Approval Date:** {approval_date}", inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(DataPointsCog(bot))