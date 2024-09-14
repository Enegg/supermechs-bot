import os
from collections import abc

import dotenv

from disnake import Locale

__all__ = ("ENV",)

dotenv.load_dotenv()


class _Env:
    __slots__ = ()

    @property
    def logs_channel_id(self) -> int:
        """The ID of a text channel to send logs to."""
        return int(os.environ["LOGS_CHANNEL_ID"])

    @property
    def home_guild_id(self) -> int:
        """The bot's home guild ID."""
        return int(os.environ["HOME_GUILD_ID"])

    @property
    def test_guild_ids(self) -> abc.Sequence[int]:
        """The IDs of only guilds the bot will register commands in while in dev mode."""
        return (self.home_guild_id,)

    @property
    def locale_override(self) -> Locale | None:
        """Override of current locale."""
        value = os.getenv("LOCALE_OVERRIDE")
        if value is None:
            return None

        return Locale[value]

    @locale_override.setter
    def locale_override(self, locale: Locale | str) -> None:
        if isinstance(locale, Locale):
            locale = locale.value

        os.environ["LOCALE_OVERRIDE"] = locale

    @locale_override.deleter
    def locale_override(self) -> None:
        os.environ.pop("LOCALE_OVERRIDE", None)

    @property
    def token(self) -> str:
        """The bot's token."""
        return os.environ["BOT_TOKEN_DEV" if __debug__ else "BOT_TOKEN"]


ENV = _Env()
