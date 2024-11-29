import logging
from collections import abc
from typing import Any

import anyio
import orjson
from aiohttp import ClientSession
from cattrs import ClassValidationError
from orjson import JSONDecodeError

import disnake

from app.core import CONFIG
from app.core.http import RESPONSE_OK
from app.local_storage.converter import converter
from app.models import ItemPack, PackKey, Player
from app.state import state
from app.typeshed import Json, Pathish
from memo import Memo
from resources import FileResource, HttpResource, Resource
from smparse.packs import structure_pack

STATE_FILE = "state_dev" if __debug__ else "state"
OLD_STATE_FILE = STATE_FILE + ".old"
_LOG = logging.getLogger(__name__)


async def load_state(path: Pathish, /) -> None:
    path = anyio.Path(path, STATE_FILE)
    data = await read_state(path)

    if data is not None:
        structure_state(data)


async def save_state(path: Pathish, /) -> None:
    path = anyio.Path(path)
    state_path = path / STATE_FILE

    if not await move_old_state(from_=state_path, to=path / OLD_STATE_FILE):
        return

    data = unstructure_state()
    await dump_state(state_path, data)


async def read_state(path: anyio.Path, /) -> bytes | None:
    try:
        data = await path.read_bytes()

    except FileNotFoundError:
        _LOG.info("State file not found")
        return None

    except OSError as err:
        _LOG.error("Reading state file failed", exc_info=err)
        return None

    return data


def structure_state(data: bytes, /) -> None:
    try:
        raw_state = orjson.loads(data)

    except JSONDecodeError as err:
        _LOG.error(msg="Invalid json state", exc_info=err)
        return

    try:
        state = converter.structure(raw_state, dict[int, Player])

    except ClassValidationError as err:
        _LOG.error(msg="Cannot structure state", exc_info=err)

    else:
        players.mapping.update(state)


def unstructure_state() -> bytes:
    return orjson.dumps(converter.unstructure(players.mapping))


async def move_old_state(from_: anyio.Path, to: anyio.Path) -> bool:
    try:
        await from_.replace(to)

    except FileNotFoundError:
        _LOG.warning("Old state file doesn't exist")

    except OSError as err:
        _LOG.error("Failed to move state", exc_info=err)
        return False

    return True


async def dump_state(path: anyio.Path, data: bytes) -> None:
    await path.touch()
    try:
        await path.write_bytes(data)

    except OSError as err:
        _LOG.error("Saving state failed", exc_info=err)


def player_factory(user: disnake.abc.User, /) -> Player:
    _LOG.info("Player created: id=%d name=%s", user.id, user.name)
    return Player.from_user(user)


players = Memo(player_factory, lambda user: user.id)


def item_pack_factory(data: abc.Mapping[str, Any], /, url: str | None = None) -> ItemPack:
    pack_data, items = structure_pack(data)
    pack = ItemPack(
        key=PackKey(pack_data.key),
        name=pack_data.name,
        description=pack_data.description,
        url=url,
        items=items,
    )
    _LOG.info("Item pack created: %s (%s) (%d items)", pack.key, pack.name, len(pack.items))
    return pack


async def load_default_pack(session: ClientSession, /) -> None:
    data: abc.Mapping[str, Json]
    url: str | None = None

    match Resource.from_uri(CONFIG.default_pack_url):
        case FileResource() as file:
            data = orjson.loads(await file.read())

        case HttpResource(url):
            async with session.get(url) as response:
                if response.status != RESPONSE_OK:
                    _LOG.error("Pack not available")
                    return

                data = await response.json(encoding="utf8", content_type=None, loads=orjson.loads)

        case resource:
            msg = f"Unknown resource type: {resource}"
            raise NotImplementedError(msg) from None

    state.item_pack = item_pack_factory(data, url=url)
