from collections import abc

import disnake
from disnake.utils import get as get_matching

from app.assets import ASSETS
from app.local_storage import players
from app.models import ItemPack
from app.state import state

from supermechs.all import ItemData, ItemTypeName, abc as smabc


def get_item_icon_url(item: smabc.ItemData) -> str | None:
    if item.type == ItemTypeName.SIDE_WEAPON or item.type == ItemTypeName.TOP_WEAPON:  # noqa: PLR1714
        icon_url = ASSETS.sided_types[item.type].right.image_url

    else:
        icon_url = ASSETS.types[item.type].image_url

    return icon_url


def get_item_by_name(items: abc.Iterable[ItemData], name: str) -> ItemData | None:
    return get_matching(items, name=name)


def get_item_pack_for(inter: disnake.Interaction, /) -> ItemPack:
    # grab a player if exists, but do not create a new one
    # since this can be invoked in item lookup commands
    # which don't require player
    try:
        player = players.get(inter.author)

    except LookupError:
        return state.item_pack

    del player  # TODO
    return state.item_pack
