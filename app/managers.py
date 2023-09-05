import logging
import typing as t

from disnake.abc import User

from shared import SESSION_CTX
from shared.manager import Manager

from supermechs.api import ItemPack, PackRenderer, Player
from supermechs.ext.deserializers.graphic import to_pack_renderer
from supermechs.ext.deserializers.models import AnyItemPack, extract_key, to_item_pack

if t.TYPE_CHECKING:
    from PIL import Image

__all__ = ("player_manager", "item_pack_manager", "renderer_manager")

LOGGER = logging.getLogger(__name__)


def _create_player(user: User, /) -> Player:
    LOGGER.info(f"Player created: {user.id} ({user.name})")
    return Player(id=user.id, name=user.name)


player_manager = Manager(_create_player, lambda user: user.id)


def _create_item_pack(data: AnyItemPack, /, *, custom: bool = False) -> ItemPack:
    pack = to_item_pack(data, custom=custom)
    LOGGER.info(f"Item pack created: {pack.key} ({pack.name})")
    return pack


def _pack_key_getter(data: AnyItemPack, /, **kwargs: t.Any) -> str:
    del kwargs
    return extract_key(data)


item_pack_manager = Manager(_create_item_pack, _pack_key_getter)


async def _image_fetcher(url: str, /) -> "Image.Image":
    from io import BytesIO

    from PIL import Image

    async with SESSION_CTX.get().get(url) as response:
        response.raise_for_status()
        fp = BytesIO(await response.content.read())
        return Image.open(fp)


def _create_pack_renderer(data: AnyItemPack, /) -> PackRenderer:
    return to_pack_renderer(data, _image_fetcher)


renderer_manager = Manager(_create_pack_renderer, extract_key)
