from __future__ import annotations

import asyncio
import logging
import os
import warnings

from disnake import AllowedMentions, Game, Intents
from dotenv import load_dotenv

from bot import SMBot
from config import LOGS_CHANNEL, TEST_GUILDS
from library_extensions import FileRecord

load_dotenv()

logging.Formatter.default_time_format = "%d.%m.%Y %H:%M:%S"
logging.setLogRecordFactory(FileRecord)
warnings.filterwarnings("ignore", "PyNaCl")
logging.captureWarnings(True)
ROOT_LOGGER = logging.getLogger()
ROOT_LOGGER.setLevel(logging.INFO)
stream = logging.StreamHandler()
stream.setLevel(logging.INFO)
ROOT_LOGGER.addHandler(stream)

logging.getLogger("disnake").setLevel(logging.WARNING)
logging.getLogger("disnake.ext.plugins.plugin").setLevel(logging.INFO)

if __debug__:
    format = "{asctime} [{levelname}] {name} - {message}"

else:
    # don't append timestamp as heroku does that already
    format = "[{levelname}] {name} - {message}"

stream.setFormatter(logging.Formatter(format, style="{"))


async def main() -> None:
    bot = SMBot(
        dev_mode=__debug__,
        logs_channel_id=LOGS_CHANNEL,
        intents=Intents(guilds=True),
        activity=Game("SuperMechs"),
        test_guilds=TEST_GUILDS if __debug__ else None,
        allowed_mentions=AllowedMentions.none(),
        strict_localization=__debug__,
        # sync_commands_debug=True,
    )

    bot.i18n.load("locale/")
    bot.load_extensions("extensions")

    await bot.start(os.environ["TOKEN_DEV" if __debug__ else "TOKEN"])


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        pass
    logging.shutdown()
