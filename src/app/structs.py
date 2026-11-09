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
type SpritePack = abc.Mapping[SpriteKey, HttpResource]
type ItemMapping = abc.Mapping[sm.Item.Id, sm.Item]


@attrs.define(kw_only=True)
class ItemPack:
    reloaded_items: ItemMapping = attrs.field(factory=dict, repr=limited_repr)
    legacy_items: ItemMapping = attrs.field(factory=dict, repr=limited_repr)
    hidden_items: ItemMapping = attrs.field(factory=dict, repr=limited_repr)


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
