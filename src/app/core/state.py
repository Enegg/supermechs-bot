from collections import abc
from typing import ClassVar, Final, NamedTuple, cast as type_cast, final

import aiohttp
import msgspec
import psutil
from monads import option
from monads.option import Null

import disnake
from app.disnake_types import Bot
from discord.null_objects import NullUser
from disnake import Locale, LocalizationProtocol

from app.models.item_pack import ItemPack
from app.models.sprite_pack import SpritePack

__all__ = ("AppState",)


class LocaleInfo(msgspec.Struct):
    english_name: str
    local_name: str
    flag_emoji: option.Option[str] = Null.null
    region: option.Option[str] = Null.null


class BotUserInfo(NamedTuple):
    owner: disnake.abc.User = NullUser()
    bot_public: bool = False


@final
class AppState:
    bot: ClassVar[Bot]
    bot_user_info: ClassVar[BotUserInfo] = BotUserInfo()

    http_session: ClassVar[aiohttp.ClientSession]
    """App-lifetime HTTP session."""
    app_process: Final[psutil.Process] = psutil.Process()
    app_sloc: int = 0

    item_pack: ClassVar[ItemPack] = ItemPack()
    sprite_pack: ClassVar[SpritePack] = {}

    debug_log_components: ClassVar[bool] = False
    recently_loaded_plugin: ClassVar[str | None] = None

    @final
    class I18n:
        type LocalePair[KT] = tuple[KT, Locale]

        stats: Final[abc.MutableMapping[LocalePair[str], str]] = {}
        messages: Final[abc.MutableMapping[LocalePair[str], str]] = {}
        locale_info: Final[abc.MutableMapping[Locale, LocaleInfo]] = {}

        command_locale: Final[abc.MutableMapping[str, dict[str, str]]] = {}
        # provider only needs .get(_: str, /) -> Mapping[str, str] | None
        localization_provider: Final[LocalizationProtocol] = type_cast(
            "LocalizationProtocol", command_locale
        )
        locale_override: ClassVar[option.Option[Locale]] = option.Null.null

        @classmethod
        def set_locale_override(cls, locale: Locale, /) -> None:
            cls.locale_override = option.Some(locale)

        @classmethod
        def remove_locale_override(cls) -> None:
            cls.locale_override = option.Null.null
