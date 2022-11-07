from configparser import ConfigParser

parser = ConfigParser()
parser.read("config.ini")

# bot
LOGS_CHANNEL = parser.getint("bot", "LOGS_CHANNEL")
"""The ID of a text channel for ChannelHandler to send logs to."""

HOME_GUILD_ID = parser.getint("bot", "HOME_GUILD_ID")
"""The bot's home guild ID."""

TEST_GUILDS = (HOME_GUILD_ID,)
"""The IDs of guilds the bot will register commands in while in dev mode."""

OWNER_ID = parser.getint("bot", "OWNER_ID")
"""The ID of the bot's owner."""
