import typing as t

from disnake import CommandInteraction

from library_extensions import OPTION_LIMIT
from managers import item_pack_manager, player_manager

from supermechs.api import Element, ItemBase, Type, sanitize_name
from supermechs.typedefs import Name
from supermechs.utils import search_for

__all__ = ("item_name_autocomplete", "mech_name_autocomplete")

AutocompleteRetT = list[str] | dict[str, str]


def _get_item_filters(inter: CommandInteraction) -> list[t.Callable[[ItemBase], bool]]:
    filters: list[t.Callable[[ItemBase], bool]] = []

    if (type_name := inter.filled_options.get("type", "ANY")) != "ANY":
        filters.append(lambda item: item.type is Type[type_name])

    if (element_name := inter.filled_options.get("element", "ANY")) != "ANY":
        filters.append(lambda item: item.element is Element[element_name])

    return filters


async def item_name_autocomplete(inter: CommandInteraction, input: str) -> AutocompleteRetT:
    """Autocomplete for items with regard for type & element."""

    pack = item_pack_manager.mapping["@Darkstare"]  # TODO: replace with default pack reference

    filters = _get_item_filters(inter)
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

    # extend names up to OPTION_LIMIT
    matching_item_names += heapq.nsmallest(
        OPTION_LIMIT - len(matching_item_names),
        filter_item_names(search_for(input, pack.iter_item_names())),
    )
    return matching_item_names


async def mech_name_autocomplete(inter: CommandInteraction, input: str) -> AutocompleteRetT:
    """Autocomplete for player builds."""

    player = player_manager.lookup_or_create(inter.author)
    case_insensitive = input.lower()

    matching = [name for name in player.builds if name.lower().startswith(case_insensitive)]

    if matching:
        return matching

    input = sanitize_name(input)

    if input:
        return {f'Enter to create mech "{input}"...': input}

    return []
