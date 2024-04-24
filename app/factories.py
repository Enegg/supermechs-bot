import logging
import typing

import disnake

from async_utils import async_memoize
from models import ItemPack, Player

from supermechs.ext.deserializers import to_item_pack
from supermechs.ext.deserializers.typedefs import AnyItemPack

if typing.TYPE_CHECKING:
    from aiohttp import ClientSession
    from PIL import Image

_LOGGER = logging.getLogger(__name__)


def player_factory(user: disnake.abc.User, /) -> Player:
    _LOGGER.info("Player created: %d (%s)", user.id, user.name)
    return Player(user=user)


def item_pack_factory(data: AnyItemPack, /) -> ItemPack:
    pack = to_item_pack(data)
    _LOGGER.info(
        "Item pack created: %s (%s) (%d items)", pack.data.key, pack.data.name, len(pack.items)
    )
    return pack


@async_memoize
async def image_factory(url: str, /, session: "ClientSession") -> "Image.Image":
    _LOGGER.debug("Requesting %s", url)

    from PIL import ImageFile

    async with session.get(url) as response:
        response.raise_for_status()
        parser = ImageFile.Parser()

        async for chunk, _ in response.content.iter_chunks():
            parser.feed(chunk)

        return parser.close()
