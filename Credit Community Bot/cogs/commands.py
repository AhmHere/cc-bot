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
        image_url = "https://images.squarespace-cdn.com/content/v1/5ac24ac545776ed72e3f4f68/771803d5-2225-4ee5-bc38-865b1fe804b1/Transfer-Partner-Matrix-AT101.png?format=1500w"

        embed = discord.Embed(
            title="Transfer Partners",
            description="Here's the list for transfer partners!"
        )
        embed.set_image(url=image_url)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(TransferCog(bot))
