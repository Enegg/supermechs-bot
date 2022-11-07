from __future__ import annotations

import asyncio
import logging
import os
import typing as t
from argparse import ArgumentParser

from disnake import AllowedMentions, Game, Intents
from dotenv import load_dotenv

from app.bot import SMBot
from app.config import LOGS_CHANNEL
from app.library_extensions import FileRecord

load_dotenv()

parser = ArgumentParser()
parser.add_argument("--local", action="store_true")
parser.add_argument("--log-file", action="store_true")
args = parser.parse_args()
LOCAL: t.Final[bool] = args.local

logging.setLogRecordFactory(FileRecord)
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
stream = logging.StreamHandler()
stream.setLevel(logging.INFO)
LOGGER.addHandler(stream)

logging.getLogger("disnake").setLevel(logging.WARNING)
logging.getLogger("disnake.ext.plugins.plugin").setLevel(logging.INFO)

if LOCAL:
    stream.formatter = logging.Formatter(
        "{asctime} [{levelname}] - {name}: {message}", "%d.%m.%Y %H:%M:%S", style="{"
    )

else:
    # don't append timestamp as heroku does that already
    stream.formatter = logging.Formatter("[{levelname}] - {name}: {message}", style="{")


async def main() -> None:
    if LOCAL:
        from app.config import TEST_GUILDS

        bot = SMBot(
            logs_channel_id=LOGS_CHANNEL,
            intents=Intents(guilds=True),
            activity=Game("SuperMechs"),
            test_guilds=TEST_GUILDS,
            allowed_mentions=AllowedMentions.none(),
            strict_localization=True,
            # sync_commands_debug=True,
            dev_mode=True,
        )

    else:
        bot = SMBot(
            logs_channel_id=LOGS_CHANNEL,
            intents=Intents(guilds=True),
            activity=Game("SuperMechs"),
            allowed_mentions=AllowedMentions.none(),
        )

    bot.i18n.load("locale/")
    bot.load_extensions("app/extensions")

    LOGGER.info("Starting bot")
    await bot.start(os.environ["TOKEN_DEV" if LOCAL else "TOKEN"])


if __name__ == "__main__":
    asyncio.run(main())
    logging.shutdown()
