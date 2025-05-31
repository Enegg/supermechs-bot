from typing import Final, NamedTuple, NewType, Protocol

from app import snowflake

import dupermechs.all as sm


class HasId(Protocol):
    @property
    def id(self) -> snowflake.Snowflake: ...


DiscordUserId = NewType("DiscordUserId", int)
PlayerId = NewType("PlayerId", snowflake.Snowflake)
BuildId = NewType("BuildId", snowflake.Snowflake)
PackId = NewType("PackId", snowflake.Snowflake)


class SpriteId(NamedTuple):
    item_id: sm.Item.Id
    item_stage: sm.Item.Rarity


DEFAULT_PACK_ID: Final[PackId] = PackId(snowflake.NIL)
