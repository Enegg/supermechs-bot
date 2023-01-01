import typing as t

from disnake import CommandInteraction
from disnake.ext import commands

from .player_factory import get_player

from SuperMechs.enums import Element, Type
from SuperMechs.item import AnyItem
from SuperMechs.player import Player
from SuperMechs.typedefs import Name
from SuperMechs.utils import search_for

if t.TYPE_CHECKING:
    from bot import SMBot

# TODO: these register as a *side effect* of importing this module
# think of a cleaner way?

@commands.register_injection
def player_injector(inter: CommandInteraction) -> Player:
    return get_player(inter)


@commands.register_injection
def item_injector(inter: CommandInteraction, name: Name) -> AnyItem:
    """Injection taking Item name and returning the Item.

    Parameters
    ----------
    name: The name of the item. {{ ITEM_NAME }}
    """
    assert isinstance(inter.bot, SMBot)
    try:
        return inter.bot.default_pack.get_item_by_name(name)

    except KeyError as err:
        raise commands.UserInputError("Item not found.") from err


def get_item_filters(inter: CommandInteraction) -> list[t.Callable[[AnyItem], bool]]:
    filters: list[t.Callable[[AnyItem], bool]] = []

    if (type_name := inter.filled_options.get("type", "ANY")) != "ANY":
        filters.append(lambda item: item.type is Type[type_name])

    if (element_name := inter.filled_options.get("element", "ANY")) != "ANY":
        filters.append(lambda item: item.element is Element[element_name])

    return filters


@item_injector.autocomplete("name")
async def item_name_autocomplete(inter: CommandInteraction, input: str) -> list[Name]:
    """Autocomplete for items with regard for type & element."""
    assert isinstance(inter.bot, SMBot)
    OPTION_LIMIT = 25

    pack = inter.bot.default_pack
    filters = get_item_filters(inter)
    abbrevs = pack.name_abbrevs.get(input.lower(), set())

    def filter_item_names(names: t.Iterable[Name]) -> t.Iterator[Name]:
        items = map(pack.get_item_by_name, names)
        filtered_items = (item for item in items if all(func(item) for func in filters))
        return (item.name for item in filtered_items)

    # place matching abbreviations at the top
    matching_item_names = sorted(filter_item_names(abbrevs))

    # this shouldn't ever happen, but handle it anyway
    if len(matching_item_names) >= OPTION_LIMIT:
        del matching_item_names[OPTION_LIMIT:]
        return matching_item_names

    # extra filter to exclude duplicates
    filters.append(lambda item: item.name not in abbrevs)

    import heapq

    # extend names up to 25
    matching_item_names += heapq.nsmallest(
        OPTION_LIMIT - len(matching_item_names),
        filter_item_names(search_for(input, pack.iter_item_names())),
    )
    return matching_item_names
