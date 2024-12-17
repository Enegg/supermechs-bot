import os
from collections import ChainMap, abc

import attrs
import cattrs
import dotenv
import rtoml
from monads.option import Null, Option, Some

from disnake import Locale

from app import paths
from app.class_utils import BinaryInt

from supermechs.gamerules import BuildRules

__all__ = ("CONFIG",)


@attrs.define(kw_only=True)
class Config:
    indev: bool = __debug__
    """Whether the bot is in development mode."""
    debug_command_sync: bool = __debug__
    """Whether disnake should log detailed sync info."""
    home_guild_id: int
    """The bot's home guild ID."""
    logs_channel_id: int | None = None
    """ID of a text channel to send logs to."""
    bot_token: str = attrs.field(repr=lambda _: "***")
    date_format: str = "%d.%m.%Y %H:%M:%S"
    """General date format for logging purposes."""
    default_pack_url: str
    """The URL of the default item pack."""
    missing_image_url: str
    """Placeholder image url."""
    max_image_size: BinaryInt = BinaryInt(25 * 1024 * 1024)
    """Maximum allowed image size, in bytes."""
    chunk_size: BinaryInt = BinaryInt(1024 * 1024)
    """Size of chunk for iterative download."""
    build_rules: BuildRules = BuildRules.default
    """Set of rules the builds shall obey."""
    command_timeout: float = 180.0
    _locale_override: Option[Locale] = Null.null

    @property
    def test_guild_ids(self) -> abc.Sequence[int]:
        """The IDs of only guilds the bot will register commands in while in dev mode."""
        return (self.home_guild_id,)

    @property
    def locale_override(self) -> Option[Locale]:
        """Override of current locale."""
        return self._locale_override

    @locale_override.setter
    def locale_override(self, locale: Locale | str) -> None:
        if isinstance(locale, str):
            locale = Locale[locale]

        self._locale_override = Some(locale)

    @locale_override.deleter
    def locale_override(self) -> None:
        self._locale_override = Null.null


# TODO: select path from cli arguments
dotenv.load_dotenv(paths.DEV_ENV if __debug__ else paths.DEV_ENV)
CONFIG = cattrs.structure(ChainMap(rtoml.load(paths.CONFIG_TOML), os.environ), Config)
