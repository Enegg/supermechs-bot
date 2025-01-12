import logging
from collections import abc
from typing import Any

import anyio
import orjson
from aiohttp import ClientSession
from cattrs import ClassValidationError
from orjson import JSONDecodeError

import disnake

from app.core import CONFIG, http
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
    await path.mkdir(exist_ok=True)

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
        _LOG.info("Restored %d players", len(state))


def unstructure_state() -> bytes:
    # FIXME: the keys of a dict need to be str
    _LOG.info("Dumping %d players", len(players.mapping))
    return orjson.dumps(converter.unstructure(players.mapping))


async def move_old_state(from_: anyio.Path, to: anyio.Path) -> bool:
    try:
        await from_.replace(to)

    except FileNotFoundError:
        _LOG.warning("Old state not found")

    except OSError as err:
        _LOG.error("Failed to move state", exc_info=err)
        return False

    return True


async def dump_state(path: anyio.Path, data: bytes) -> None:
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
    _LOG.info(
        "Item pack created: key=%s name=%s (%d items)",
        pack.key,
        pack.name.map(repr).unwrap_or("<missing>"),
        len(pack.items),
    )
    return pack


async def load_default_pack(session: ClientSession, /) -> None:
    data: abc.Mapping[str, Json]
    url: str | None

    match Resource.from_uri(CONFIG.default_pack_url):
        case FileResource(path):
            data = orjson.loads(await anyio.Path(path).read_bytes())
            url = None

        case HttpResource() as web_resource:
            async with session.get(web_resource.url) as response:
                if response.status != http.ResponseStatus.ok:
                    _LOG.error("Pack not available")
                    return

                data = await response.json(encoding="utf8", content_type=None, loads=orjson.loads)
            url = web_resource.uri

        case resource:
            msg = f"Unknown resource type: {resource}"
            raise NotImplementedError(msg) from None

    state.item_pack = item_pack_factory(data, url=url)
