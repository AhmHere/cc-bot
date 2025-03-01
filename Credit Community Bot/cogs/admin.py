# cogs/admin.py

import discord
from discord.ext import commands
from config import MODERATOR_ROLE_NAME
from utils import save_bot_data, sync_data_from_globals

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_any_role('Moderator', 'Owner', 'Intern')
    async def clear(self, ctx, user: discord.Member):
        """Force-clear a user's 7-day cooldown in #referrals."""
        globals_data = self.bot.globals_data
        if user.id in globals_data['last_message']:
            del globals_data['last_message'][user.id]
            updated = sync_data_from_globals(globals_data)
            save_bot_data(updated)
            await ctx.send(f"{user.mention}'s referral cooldown has been cleared.")
        else:
            await ctx.send(f"{user.mention} doesn't have an active cooldown.")

async def setup(bot):
    await bot.add_cog(AdminCog(bot))