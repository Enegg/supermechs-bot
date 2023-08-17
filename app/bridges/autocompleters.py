import typing as t

from library_extensions import OPTION_LIMIT
from managers import item_pack_manager, player_manager

from supermechs.api import Element, ItemData, Type
from supermechs.typedefs import Name
from supermechs.user_input import sanitize_string
from supermechs.utils import search_for

if t.TYPE_CHECKING:
    from disnake import CommandInteraction, Localized

__all__ = ("item_name_autocomplete", "mech_name_autocomplete")

AutocompleteRetT = t.Sequence["str | Localized[str]"] | t.Mapping[str, "str | Localized[str]"]


def _get_item_filters(options: t.Mapping[str, t.Any], /) -> list[t.Callable[[ItemData], bool]]:
    filters: list[t.Callable[[ItemData], bool]] = []

    if (type_name := options.get("type", "ANY")) != "ANY":
        target_type = Type[type_name]
        filters.append(lambda item: item.type is target_type)

    if (element_name := options.get("element", "ANY")) != "ANY":
        target_element = Element[element_name]
        filters.append(lambda item: item.element is target_element)

    return filters


async def item_name_autocomplete(inter: "CommandInteraction", input: str) -> AutocompleteRetT:
    """Autocomplete for items with regard for type & element."""

    pack = item_pack_manager.mapping["@Darkstare"]  # TODO: replace with default pack reference

    filters = _get_item_filters(inter.filled_options)
    abbrevs = pack.name_abbrevs.get(input.lower(), set())

    def filter_item_names(names: t.Iterable[Name]) -> t.Iterator[Name]:
        items = map(pack.get_item_by_name, names)

        if filters:
            items = (item for item in items if all(func(item) for func in filters))

        return (item.name for item in items)

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


async def mech_name_autocomplete(inter: "CommandInteraction", input: str) -> AutocompleteRetT:
    """Autocomplete for player builds."""

    player = player_manager.lookup_or_create(inter.author)
    case_insensitive = input.lower()

    matching = [name for name in player.builds if name.lower().startswith(case_insensitive)]

    if matching:
        return matching

    input = sanitize_string(input)

    if input:
        return {f'Enter to create mech "{input}"...': input}

    return []
