from collections import abc
from typing import ClassVar, Final, Literal, NamedTuple, cast as type_cast, final

import msgspec
import psutil
from monads import option
from monads.option import Null

import disnake
from discord.null_objects import NullUser
from disnake import Locale, LocalizationProtocol
from disnake.abc import Messageable

from app.aio import HTTPSession
from app.models.item_pack import ItemPack
from app.models.sprite_pack import SpriteKey, SpritePack
from app.typeshed import Bot
from resources import HttpResource

import supermechs.all as sm

__all__ = ("AppState",)


class LocaleInfo(msgspec.Struct):
    english_name: str
    local_name: str
    flag_emoji: option.Option[str] = Null.null
    region: option.Option[str] = Null.null


class BotUserInfo(NamedTuple):
    owner: disnake.abc.User = NullUser()
    bot_public: bool = False


type CommandName = Literal["item", "legacy-item"]


@final
class AppState:
    bot: ClassVar[Bot]
    bot_user_info: ClassVar[BotUserInfo] = BotUserInfo()

    http_session: ClassVar[HTTPSession]
    """App-lifetime HTTP session."""
    app_process: Final[psutil.Process] = psutil.Process()
    app_sloc: int = 0

    item_pack: ClassVar[ItemPack] = ItemPack()
    sprite_pack: ClassVar[SpritePack] = {}

    debug_log_components: ClassVar[bool] = False
    recently_loaded_plugin: ClassVar[str | None] = None

    command_mentions: Final[abc.MutableMapping[str, str]] = {}
    logs_channel: ClassVar[Messageable | None] = None

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


def get_command_mention(name: CommandName, /) -> str:
    mention = AppState.command_mentions.get(name)

    if mention is not None:
        return mention

    mention = AppState.command_mentions[name] = "/" + name
    return mention


def get_image_url(key: SpriteKey, /) -> str | None:
    resource = AppState.sprite_pack.get(key)

    if isinstance(resource, HttpResource):
        return resource.uri

    return None


def filter_items(
    slot: str | None = None,
    element: str | None = None,
    rarity: str | None = None,
    legacy: bool = False,
) -> abc.Generator[sm.Item]:
    filters: list[abc.Callable[[sm.Item], bool]] = []

    if slot is not None:
        target_slot = sm.Item.Slot[slot]
        filters.append(lambda item: item.slot_id is target_slot)

    if element is not None:
        target_element = sm.Item.Element[element]
        filters.append(lambda item: item.element is target_element)

    if rarity is not None:
        min_tier = sm.Item.Rarity[rarity]
        filters.append(lambda item: item.stages[0].tier >= min_tier)

    bank = AppState.item_pack.legacy_items if legacy else AppState.item_pack.reloaded_items

    if not filters:
        yield from bank.values()
        return

    for item in bank.values():
        if all(f(item) for f in filters):
            yield item
