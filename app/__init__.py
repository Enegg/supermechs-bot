from configparser import ConfigParser

parser = ConfigParser()
parser.read("config.ini")

LOGS_CHANNEL = parser.getint("bot", "LOGS_CHANNEL")
HOME_GUILD_ID = parser.getint("bot", "HOME_GUILD_ID")
TEST_GUILDS = (HOME_GUILD_ID,)
OWNER_ID = parser.getint("bot", "OWNER_ID")
