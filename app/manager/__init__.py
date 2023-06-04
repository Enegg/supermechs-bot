import logging
import typing as t

from .manager import Manager

from SuperMechs.api import ItemPack, Player, extract_info
from SuperMechs.rendering import PackRenderer
from SuperMechs.typedefs import AnyItemPack

__all__ = ("player_manager", "item_pack_manager", "renderer_manager")

LOGGER = logging.getLogger(__name__)


class UserLike(t.Protocol):
    @property
    def id(self) -> int:
        ...

    @property
    def name(self) -> str:
        ...


def create_player(user: UserLike) -> Player:
    LOGGER.info(f"Player created: {user.id} ({user.name})")
    return Player(id=user.id, name=user.name)


player_manager = Manager(create_player, lambda user: user.id)


def create_item_pack(data: AnyItemPack, custom: bool = False) -> ItemPack:
    pack = ItemPack.from_json(data, custom=custom)
    LOGGER.info(f"Item pack created: {pack.key} ({pack.name})")
    return pack


item_pack_manager = Manager(create_item_pack, lambda data, custom=False: extract_info(data).key)


def create_pack_renderer(data: AnyItemPack) -> PackRenderer:
    key = extract_info(data).key
    return PackRenderer(key)


renderer_manager = Manager(create_pack_renderer, lambda data: extract_info(data).key)
