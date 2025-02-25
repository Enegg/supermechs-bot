from collections import abc

from app.disnake_types import Interaction
from disnake.utils import get as get_matching

from app import state
from app.assets import ASSETS
from app.models import ItemPack
from resources import Resource

import supermechs.all as sm


def get_item_icon(item: sm.abc.ItemData, /) -> Resource:
    if item.type == sm.ItemTypeName.SIDE_WEAPON or item.type == sm.ItemTypeName.TOP_WEAPON:  # noqa: PLR1714
        return ASSETS.sided_types[item.type].right.resource

    return ASSETS.types[item.type].resource


def get_item_by_name(items: abc.Iterable[sm.ItemData], name: str) -> sm.ItemData | None:
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


def acronym_of(name: str, /) -> str | None:
    """Return an acronym of the name, or None if one cannot (shouldn't) be made.

    The acronym consists of capital letters in item's name;
    it will not be made for non-PascalCase single-word names, or names which themselves
    are an acronym for something (like EMP).
    """
    if not name:
        return None
    if name[0].isupper() and name[1:].islower():
        # don't bother with single capital letters
        return None
    # filter out already-acronym names, like "EMP"
    if name.isupper():
        return None
    # names which are partially acronyms are fine
    return "".join(filter(str.isupper, name)).lower()
