import logging

import disnake

from app.models import ItemPack, Player
# from app.sm.convert import to_item_pack

from supermechs.ext.deserializers.typedefs import AnyItemPack

_LOGGER = logging.getLogger(__name__)


def player_factory(user: disnake.abc.User, /) -> Player:
    _LOGGER.info("Player created: %d (%s)", user.id, user.name)
    return Player(id=user.id)


def item_pack_factory(data: AnyItemPack, /) -> ItemPack:
    pack = to_item_pack(data)
    _LOGGER.info("Item pack created: %s (%s) (%d items)", pack.key, pack.name, len(pack.items))
    return pack
