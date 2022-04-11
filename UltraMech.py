from __future__ import annotations

import logging
import os
import typing as t
from argparse import ArgumentParser

import disnake
from dotenv import load_dotenv

from bot import SMBot
from config import LOGS_CHANNEL, OWNER_ID, TEST_GUILDS
from utils import ChannelHandler, FileRecord

parser = ArgumentParser()
parser.add_argument("--local", action="store_true")
parser.add_argument("--db_enabled", action="store_true")
parser.add_argument("--log-file", action="store_true")
args = parser.parse_args()
LOCAL: t.Final[bool] = args.local
DB_FEATURES: bool = args.db_enabled

logging.setLogRecordFactory(FileRecord)
logger = logging.getLogger("channel_logs")
logger.level = logging.INFO

load_dotenv()
TOKEN = os.environ.get("TOKEN_DEV" if LOCAL else "TOKEN")

if TOKEN is None:
    raise EnvironmentError("TOKEN not found in environment variables")

if DB_FEATURES:
    DB_TOKEN = os.environ.get("DB_TOKEN")

    if DB_TOKEN is None:
        raise EnvironmentError("DB_TOKEN not found in environment variables")

    import certifi
    from motor.motor_asyncio import AsyncIOMotorClient
    from odmantic import AIOEngine

    if LOCAL:
        engine = AIOEngine()

    else:
        engine = AIOEngine(AsyncIOMotorClient(
            DB_TOKEN,
            serverSelectionTimeoutMS=5000,
            tlsCAFile=certifi.where()
        ))

else:
    engine = None

bot = SMBot(
    hosted=LOCAL,
    engine=engine,
    owner_id=OWNER_ID,
    intents=disnake.Intents(guilds=True),
    activity=disnake.Game("under maintenance" if LOCAL else "SuperMechs"),
    guild_ids=TEST_GUILDS if LOCAL else None)

logger.addHandler(ChannelHandler(LOGS_CHANNEL, bot, level=logging.WARNING))
stream = logging.StreamHandler()
stream.level = logging.INFO
logger.addHandler(stream)
bot.load_extensions("commands")

bot.run(TOKEN)
