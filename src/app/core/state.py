from collections import abc
from typing import ClassVar, Final, Self

import attrs

from disnake import Locale
from disnake.abc import Messageable
from disnake.ext import commands

from app import structs
from app.utils import SourceStats

from supermechs.enums import ItemStat


@attrs.define(kw_only=True)
class I18nStore:
    locale_info: Final[abc.MutableMapping[Locale, structs.LocaleInfo]] = attrs.Factory(dict)
    stat_l10ns: Final[abc.MutableMapping[structs.LocalePair[ItemStat], str]] = attrs.Factory(dict)
    message_l10ns: Final[abc.MutableMapping[structs.LocalePair[str], str]] = attrs.Factory(dict)
    command_l10ns: Final[abc.MutableMapping[str, abc.Mapping[str, str]]] = attrs.Factory(dict)


@attrs.define(kw_only=True)
class DebugOptions:
    log_components: bool = False
    reloaded_plugin_name: str | None = None
    locale_override: Locale | None = None


# TODO: Assets
class Assets:
    EMOJIS: Final = ...


@attrs.define(kw_only=True)
class State:
    instance: ClassVar[Self]

    bot: Final[commands.InteractionBot]

    logs_channel: Messageable | None = None
    bot_user_info: structs.BotUserInfo = attrs.Factory(structs.BotUserInfo)
    app_source_stats: SourceStats = SourceStats()  # noqa: RUF009
    command_mentions: Final[abc.MutableMapping[str, str]] = attrs.Factory(dict)

    item_pack: structs.ItemPack = attrs.Factory(structs.ItemPack)
    sprite_pack: structs.SpritePack = attrs.Factory(structs.SpritePack)

    i18n: Final[I18nStore] = attrs.Factory(I18nStore)
    debug: Final[DebugOptions] = attrs.Factory(DebugOptions)
    assets: Assets = attrs.Factory(Assets)

    @classmethod
    def magically_get_state(cls) -> Self:
        # TODO: make it less magical
        return cls.instance
