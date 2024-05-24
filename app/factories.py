import logging
import typing

import disnake

from async_utils import async_memoize
from models import ItemPack, Player
from shared.session import IO_SESSION

from supermechs.ext.deserializers import to_item_pack
from supermechs.ext.deserializers.typedefs import AnyItemPack

if typing.TYPE_CHECKING:
    from aiohttp.typedefs import StrOrURL
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


MAX_CONTENT_LENGTH = 1024**2 * 25  # 25MiB


@async_memoize
async def load_image(url: "StrOrURL", /) -> "Image.Image":
    _LOGGER.debug("Requesting %s", url)

    from PIL import ImageFile

    async with IO_SESSION.get().get(url) as response:
        response.raise_for_status()
        _LOGGER.debug(
            "Content type: %s, length: %s", response.content_type, response.content_length
        )
        if not response.content_type.startswith("image"):
            msg = "Content type is not image"
            raise ValueError(msg)

        if response.content_length is not None and response.content_length > MAX_CONTENT_LENGTH:
            msg = "Image too large"
            raise ValueError(msg)

        parser = ImageFile.Parser()

        async for chunk, _ in response.content.iter_chunks():
            parser.feed(chunk)
            assert parser.data is not None

            if len(parser.data) > MAX_CONTENT_LENGTH:
                msg = "Image too large"
                raise ValueError(msg)

        return parser.close()
