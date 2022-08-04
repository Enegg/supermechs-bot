from __future__ import annotations

import logging
import os
import typing as t
from argparse import ArgumentParser

from disnake import AllowedMentions, Game, Intents
from dotenv import load_dotenv

from bot import SMBot
from config import LOGS_CHANNEL, OWNER_ID
from lib_helpers import FileRecord

load_dotenv()

parser = ArgumentParser()
parser.add_argument("--local", action="store_true")
parser.add_argument("--log-file", action="store_true")
args = parser.parse_args()
LOCAL: t.Final[bool] = args.local

logging.setLogRecordFactory(FileRecord)
logger = logging.getLogger("main")
logger.level = logging.INFO

stream = logging.StreamHandler()
stream.level = logging.INFO

if LOCAL:
    stream.formatter = logging.Formatter(
        "{asctime} [{levelname}] - {name}: {message}", "%d.%m.%Y %H:%M:%S", style="{"
    )

else:
    # don't append timestamp as heroku does that already
    stream.formatter = logging.Formatter("[{levelname}] - {name}: {message}", style="{")

logger.addHandler(stream)


def main() -> None:
    if LOCAL:
        from config import TEST_GUILDS

        bot = SMBot(
            test_mode=True,
            logs_channel_id=LOGS_CHANNEL,
            owner_id=OWNER_ID,
            intents=Intents(guilds=True),
            activity=Game("SuperMechs"),
            guild_ids=TEST_GUILDS,
            strict_localization=True,
            allowed_mentions=AllowedMentions.none()
            # sync_commands_debug=True,
        )

    else:
        bot = SMBot(
            logs_channel_id=LOGS_CHANNEL,
            owner_id=OWNER_ID,
            intents=Intents(guilds=True),
            activity=Game("SuperMechs"),
            allowed_mentions=AllowedMentions.none(),
        )

    bot.i18n.load("locale/")
    bot.load_extensions("commands")

    logger.info("Bot started")
    bot.run(os.environ.get("TOKEN_DEV" if LOCAL else "TOKEN"))


if __name__ == "__main__":
    main()
    logging.shutdown()
