import logging
from typing import Final, NewType

import aiohttp
import anyio
import orjson

import disnake

from app.core import CONFIG, http
from app.models import ItemPack, PackKey, PartialPlayer, Player
from app.typeshed import JsonObject, Pathish
from memo import Memo
from resources import FileResource, HttpResource
from smparse.packs import structure_pack

from .structuring import load_state, save_state

_LOG = logging.getLogger(__name__)

item_pack: Final[ItemPack]
"""Default item pack. Access via `from app import state; state.item_pack`"""

PartialState = NewType("PartialState", object)


def load(path: Pathish, /) -> list[PartialPlayer]:
    return load_state(path)


async def load_async(session: aiohttp.ClientSession, /, state: list[PartialPlayer]) -> None:
    await load_default_pack(session)

    complete_players: list[Player] = []

    for partial_player in state:
        player = partial_player.as_complete(item_pack)
        complete_players.append(player)

    players.mapping.update((player.id, player) for player in complete_players)


def save(path: Pathish, /) -> None:
    save_state(path, players.mapping.values())


def _player_factory(user: disnake.abc.User, /) -> Player:
    _LOG.info("Player created: id=%d name=%s", user.id, user.name)
    return Player.from_user(user)


players: Final = Memo(_player_factory, lambda user: user.id)


def item_pack_factory(data: JsonObject, /, url: str | None = None) -> ItemPack:
    pack_data, items = structure_pack(data)
    pack = ItemPack(
        key=PackKey(pack_data.key),
        name=pack_data.name,
        description=pack_data.description,
        url=url,
        items=items,
    )
    _LOG.info(
        "Item pack created: key=%s name=%s (%d items)",
        pack.key,
        pack.name.map(repr).unwrap_or("<missing>"),
        len(pack.items),
    )
    return pack


async def load_default_pack(session: aiohttp.ClientSession, /) -> None:
    global item_pack
    data: JsonObject
    url: str | None

    match CONFIG.default_pack_uri:
        case FileResource(path):
            data = orjson.loads(await anyio.Path(path).read_bytes())
            url = None

        case HttpResource() as web_resource:
            async with session.get(web_resource.url) as response:
                if response.status != http.ResponseStatus.ok:
                    _LOG.error("Default pack is not available")
                    return

                data = await response.json(encoding="utf8", content_type=None, loads=orjson.loads)
            url = web_resource.uri

        case resource:
            msg = f"Unknown resource type: {resource}"
            raise NotImplementedError(msg)

    item_pack = item_pack_factory(data, url)
