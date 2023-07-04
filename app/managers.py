import logging

from disnake.abc import User

from shared.manager import Manager

from supermechs.api import ItemPack, Player, extract_key
from supermechs.rendering import PackRenderer
from supermechs.typedefs import AnyItemPack

__all__ = ("player_manager", "item_pack_manager", "renderer_manager")

LOGGER = logging.getLogger(__name__)


def create_player(user: User, /) -> Player:
    LOGGER.info(f"Player created: {user.id} ({user.name})")
    return Player(id=user.id, name=user.name)


player_manager = Manager(create_player, lambda user: user.id)


def create_item_pack(data: AnyItemPack, /, *, custom: bool = False) -> ItemPack:
    pack = ItemPack.from_json(data, custom=custom)
    LOGGER.info(f"Item pack created: {pack.key} ({pack.name})")
    return pack


item_pack_manager = Manager(create_item_pack, lambda data, /, *, custom=False: extract_key(data))


def create_pack_renderer(data: AnyItemPack, /) -> PackRenderer:
    return PackRenderer(key=extract_key(data))


renderer_manager = Manager(create_pack_renderer, extract_key)
