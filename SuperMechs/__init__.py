from configparser import ConfigParser

parser = ConfigParser()
parser.read("config.ini")

DEFAULT_PACK_URL = parser["packs"]["DEFAULT_PACK_URL"]
DEFAULT_PACK_V2_URL = parser["packs"]["DEFAULT_PACK_V2_URL"]
WU_SERVER_URL = parser["socket"]["WU_SERVER_URL"]
CLIENT_VERSION = parser["socket"]["CLIENT_VERSION"]
