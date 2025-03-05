# cogs/commands.py

import discord
from discord.ext import commands
from discord import app_commands

class TransferCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("[DEBUG] CommandsCog loaded – slash command should be registered.")

    @app_commands.command(name="transfer_partners", description="Sends transfer partner matrix")
    async def transfer(self, interaction: discord.Interaction):
        image_url = "https://images.squarespace-cdn.com/content/v1/5ac24ac545776ed72e3f4f68/0c8681ce-694d-45f5-938f-847edef8e6b5/Transfer-Partner-Matrix-AT101.png?format=2500w"

        embed = discord.Embed(
            title="Transfer Partners",
            description="Here's the list for transfer partners!"
        )
        embed.set_image(url=image_url)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(TransferCog(bot))