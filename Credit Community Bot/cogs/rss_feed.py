# cogs/rss_feed.py

import discord
from discord.ext import commands, tasks
import feedparser

from config import RSS_FEEDS
from utils import load_posted_entries, add_new_entry, clean_summary

class RSSFeedCog(commands.Cog):
    """Handles fetching RSS feeds and posting new entries."""

    def __init__(self, bot):
        self.bot = bot
        self.check_rss_feeds.start()

    def cog_unload(self):
        self.check_rss_feeds.cancel()

    @tasks.loop(minutes=5)
    async def check_rss_feeds(self):
        try:
            for channel_id, (feed_url, feed_name, embed_color) in RSS_FEEDS.items():
                feed = feedparser.parse(feed_url)
                if not feed.entries:
                    print(f"[DEBUG] No entries found for {feed_url}")
                    continue

                channel = self.bot.get_channel(channel_id)
                if not channel:
                    print(f"[WARN] Could not find channel with ID {channel_id}")
                    continue

                posted_entries = load_posted_entries()
                for entry in reversed(feed.entries):
                    unique_id = entry.get("id") or entry.get("link")
                    if not unique_id:
                        continue
                    if str(channel_id) in posted_entries and unique_id in posted_entries[str(channel_id)]:
                        continue

                    title = entry.get("title", "No title")
                    link = entry.get("link", "")
                    raw_summary = entry.get("summary", "")
                    cleaned = clean_summary(raw_summary)

                    embed = discord.Embed(
                        title=title,
                        url=link,
                        description=cleaned,
                        color=embed_color
                    )
                    embed.set_author(name=feed_name)
                    published = entry.get("published", "")
                    if published:
                        embed.set_footer(text=f"Published: {published}")

                    await channel.send(embed=embed)
                    add_new_entry(channel_id, unique_id)
        except Exception as e:
            print(f"[ERROR] RSS feed task error: {e}")

    @check_rss_feeds.before_loop
    async def before_check_rss_feeds(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(RSSFeedCog(bot))