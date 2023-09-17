import logging
import typing as t

import anyio
from disnake.abc import User

from library_extensions import RESPONSE_TIME_LIMIT
from shared import IO_CLIENT
from shared.manager import Manager
from shared.utils import async_memoize

from supermechs.api import ItemPack, Metadata, PackRenderer, Player
from supermechs.ext.deserializers import extract_key, to_item_pack, to_pack_renderer
from supermechs.ext.deserializers.typedefs import AnyItemPack

if t.TYPE_CHECKING:
    from PIL import Image

__all__ = ("get_default_pack", "player_manager", "item_pack_manager", "renderer_manager")

LOGGER = logging.getLogger(__name__)


def _create_player(user: User, /) -> Player:
    LOGGER.info("Player created: %d (%s)", user.id, user.name)
    return Player(id=user.id, name=user.name)


player_manager = Manager(_create_player, lambda user: user.id)


def _create_item_pack(data: AnyItemPack, /, *, custom: bool = False) -> ItemPack:
    pack = to_item_pack(data, custom=custom)
    LOGGER.info("Item pack created: %s (%s)", pack.key, pack.name)
    return pack


def _pack_key_getter(data: AnyItemPack, /, **kwargs: t.Any) -> str:
    del kwargs
    return extract_key(data)


item_pack_manager = Manager(_create_item_pack, _pack_key_getter)


@async_memoize
async def _image_fetcher(metadata: Metadata, /) -> "Image.Image":
    from io import BytesIO

    from PIL import Image

    assert metadata.source == "url"

    async with IO_CLIENT.get().get(metadata.value) as response:
        response.raise_for_status()
        fp = BytesIO(await response.content.read())
        return Image.open(fp)


def _create_pack_renderer(data: AnyItemPack, /) -> PackRenderer:
    renderer = to_pack_renderer(data, _image_fetcher)
    LOGGER.info("Renderer created: %s", renderer.pack_key)
    return renderer


renderer_manager = Manager(_create_pack_renderer, extract_key)


async def load_default_pack(url: str, /) -> None:
    from events import PACK_LOADED

    async with IO_CLIENT.get().get(url) as response:
        response.raise_for_status()
        data: AnyItemPack = await response.json(encoding="utf8", content_type=None)

    item_pack_manager.create(data)
    renderer_manager.create(data)
    PACK_LOADED.set()


async def get_default_pack() -> tuple[ItemPack, PackRenderer]:
    from events import PACK_LOADED

    async with anyio.fail_after(RESPONSE_TIME_LIMIT - 0.5):
        await PACK_LOADED.wait()

    return item_pack_manager["@Darkstare"], renderer_manager["@Darkstare"]
