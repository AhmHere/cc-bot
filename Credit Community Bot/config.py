# config.py

# Server ID
GUILD_ID = 931760921825665034

# Channel IDs
RULES_CHANNEL_ID = 932447065370398791
REFERRALS_CHANNEL_ID = 1105204207172190368
DISCORD_LOGS_CHANNEL_ID = 1105328983245082725
NEEDS_HELP_CHANNEL_ID = 1105328983245082725
DELETED_LINKS_CHANNEL_ID = 1343112665840615446

# Role Names
DIAMOND_STATUS_ROLE_NAME = "Diamond Status"
DIAMOND_ROLE_NAME = "Diamond"
MODERATOR_ROLE_NAME = "Moderator"
HELP_NEEDED_ROLE_NAME = "Help"
ALLOWED_ROLE_NAME = "Credit Beginner"

# Other constants
COOLDOWN_TIME = 7 * 24 * 60 * 60  # 7 days in seconds
DATA_FILE = "data.json"
STORAGE_FILE = "posted_entries.json"

# RSS feeds: channel_id -> (url, display_name, embed_color)
RSS_FEEDS = {
    1337930618402770985: ("https://www.doctorofcredit.com/feed/", "Doctor Of Credit", 0x9B59B6),
    1338649589191934042: ("https://dannydealguru.com/feed/", "Danny The Deal Guru", 0x3498DB),
    1338649732771221624: ("https://onemileatatime.com/feed/", "One Mile At A Time", 0xE74C3C),
}