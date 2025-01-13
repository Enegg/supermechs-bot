from collections import abc

from app.disnake_types import Interaction
from disnake.utils import get as get_matching

from app import state
from app.assets import ASSETS
from app.models import ItemPack
from resources import Resource

from supermechs.all import ItemData, ItemTypeName, abc as smabc


def get_item_icon(item: smabc.ItemData, /) -> Resource:
    if item.type == ItemTypeName.SIDE_WEAPON or item.type == ItemTypeName.TOP_WEAPON:  # noqa: PLR1714
        return ASSETS.sided_types[item.type].right.resource

    return ASSETS.types[item.type].resource


def get_item_by_name(items: abc.Iterable[ItemData], name: str) -> ItemData | None:
    return get_matching(items, name=name)


def get_item_pack_for(inter: Interaction) -> ItemPack:
    # grab a player if exists, but do not create a new one
    # since this can be invoked in item lookup commands
    # which don't require player
    try:
        player = state.players.get(inter.author)

    except LookupError:
        return state.item_pack

    del player  # TODO
    return state.item_pack
