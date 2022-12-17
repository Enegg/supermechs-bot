from __future__ import annotations

import asyncio
import logging
import os

from disnake import AllowedMentions, Game, Intents
from dotenv import load_dotenv

from bot import SMBot
from config import LOGS_CHANNEL, TEST_GUILDS
from library_extensions import FileRecord

load_dotenv()

logging.Formatter.default_time_format = "%d.%m.%Y %H:%M:%S"
logging.setLogRecordFactory(FileRecord)
logging.captureWarnings(True)
stream = logging.StreamHandler()
stream.setLevel(logging.INFO)

if __debug__:
    format = "{asctime} [{levelname}] {name} - {message}"

else:
    # don't append timestamp as heroku does that already
    format = "[{levelname}] {name} - {message}"

stream.setFormatter(logging.Formatter(format, style="{"))
ROOT_LOGGER = logging.getLogger()
ROOT_LOGGER.setLevel(logging.INFO)
ROOT_LOGGER.addHandler(stream)

logging.getLogger("disnake").setLevel(logging.ERROR)
# logging.getLogger("disnake.ext.plugins.plugin").setLevel(logging.INFO)

async def main() -> None:
    bot = SMBot(
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
