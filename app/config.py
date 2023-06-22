from configparser import ConfigParser

from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="SM",
    settings_files=["settings.toml", ".secrets.toml", "app/assets/emojis.toml", "app/assets/urls.toml"],
    load_dotenv=True,
)

parser = ConfigParser()
parser.read("config.ini")

# bot
LOGS_CHANNEL = parser.getint("bot", "LOGS_CHANNEL")
"""The ID of a text channel for ChannelHandler to send logs to."""

HOME_GUILD_ID = parser.getint("bot", "HOME_GUILD_ID")
"""The bot's home guild ID."""

TEST_GUILDS = (HOME_GUILD_ID,)
"""The IDs of guilds the bot will register commands in while in dev mode."""


# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
