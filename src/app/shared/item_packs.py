from collections import abc
from typing import TYPE_CHECKING

import disnake

from async_utils import Deferred
from config import CONFIG
from factories import item_pack_factory
from models import ItemPack
from stored import players

from supermechs.abc.item import ItemID, Name
from supermechs.ext.deserializers.typedefs import AnyItemPack
from supermechs.ext.platform import json_decoder
from supermechs.item import ItemData

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from aiohttp.typedefs import StrOrURL

DEFAULT_PACK = Deferred[ItemPack]()


async def fetch_item_pack_data(session: "ClientSession", url: "StrOrURL", /) -> AnyItemPack:
    """Fetch and load item pack data."""

    async with session.get(url) as response:
        response.raise_for_status()
        return await response.json(encoding="utf8", content_type=None, loads=json_decoder)


async def load_default_pack(session: "ClientSession", /) -> None:
    data = await fetch_item_pack_data(session, CONFIG.default_pack_url)
    pack = item_pack_factory(data)

    DEFAULT_PACK.set(pack)


def get_item_pack_for(inter: disnake.Interaction, /) -> ItemPack:
    # grab a player if exists, but do not create a new one
    # since this can be invoked in item lookup commands
    # which don't require player
    player = players.mapping.get(players.key(inter.author))
    del player  # TODO: not implemented
    return DEFAULT_PACK.get_nowait()


def get_item_by_name(mapping: abc.Mapping[ItemID, ItemData], name: Name) -> ItemData | None:
    for item in mapping.values():
        if item.name == name:
            return item

    return None
