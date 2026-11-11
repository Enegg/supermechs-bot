from collections import abc
from typing import Literal

import attrs
import msgspec

import disnake
from discord.entities import NullUser

from app.utils import limited_repr
from resources import HttpResource

import supermechs.all as sm

type CommandName = Literal["item", "legacy-item"]

type SpriteKey = tuple[sm.Item.Id, sm.Item.Rarity]
type ItemMapping = abc.MutableMapping[sm.Item.Id, sm.Item]


@attrs.define(kw_only=True)
class ItemPack:
    reloaded_items: ItemMapping = attrs.field(factory=dict, repr=limited_repr)
    legacy_items: ItemMapping = attrs.field(factory=dict, repr=limited_repr)
    hidden_items: ItemMapping = attrs.field(factory=dict, repr=limited_repr)


@attrs.define(kw_only=True)
class SpritePack:
    images: abc.MutableMapping[SpriteKey, HttpResource] = attrs.field(
        factory=dict, repr=limited_repr
    )


class BotUserInfo(msgspec.Struct):
    owner: disnake.abc.User = NullUser()
    team: disnake.Team | None = None
    bot_public: bool = False


class LocaleInfo(msgspec.Struct):
    english_name: str
    local_name: str
    flag_emoji: str | None = None
    region: str | None = None


type LocalePair[KT] = tuple[KT, disnake.Locale]
type I18nKey = Literal[
    "command-dev",
    "command-running",
    "command-timeout",
    "command-error",
    "unknown-item-name",  # {name}
    # ui
    "ui-disallowed",
    "ui-quit",
    "ui-empty-option-label",
    "ui-empty-option-desc",
    "ui-cmd-cancel-button",
    # item-lookup
    "item-lookup-ui-buffs",
    "item-lookup-ui-damage-avg",
    "item-lookup-ui-damage-vs-titans",
    "item-lookup-power-level",
    "item-lookup-power-required",
    "item-lookup-total-upgrade-cost",
    "item-lookup-evolution-cost",
    "item-lookup-ascension-cost",
    "item-lookup-ui-level-select-label",  # {level}
    "item-lookup-ui-level-select-placeholder",
    "item-lookup-ui-tier-select-placeholder",
    "item-lookup-ui-select-next-label",  # {min}, {max}
    "item-lookup-jump-required",
    "item-lookup-no-stats",
    "item-lookup-no-image",
    "item-lookup-stats-header",
    "item-lookup-releases",
    "item-lookup-released",
    "item-lookup-item-not-available",  # {command}
    "item-lookup-item-changed-info",  # {command}
    # item-compare
    "item-compare-ui-buffs",
    "item-compare-jump-required",
    "item-compare-stat-header",
    # tiers
    "tier-common",
    "tier-rare",
    "tier-epic",
    "tier-legendary",
    "tier-mythical",
    "tier-divine",
    "tier-perk",
    # other
    "boost-power",
]
