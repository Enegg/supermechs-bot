from __future__ import annotations

import logging
import os
import typing as t
from argparse import ArgumentParser

from disnake import AllowedMentions, Game, Intents
from dotenv import load_dotenv

from app.bot import SMBot
from app.lib_helpers import FileRecord
from shared import LOGS_CHANNEL

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
        from shared import TEST_GUILDS

        bot = SMBot(
            logs_channel_id=LOGS_CHANNEL,
            intents=Intents(guilds=True),
            activity=Game("SuperMechs"),
            test_guilds=TEST_GUILDS,
            allowed_mentions=AllowedMentions.none(),
            strict_localization=True,
            # sync_commands_debug=True,
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

    logger.info("Starting bot")
    bot.run(os.environ["TOKEN_DEV" if LOCAL else "TOKEN"])


if __name__ == "__main__":
    main()
    logging.shutdown()
