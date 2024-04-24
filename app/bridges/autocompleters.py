import typing
from collections import abc, defaultdict

from discord_extensions import AutocompleteReturnType, InteractionLimits
from shared.item_packs import get_item_pack_for
from sm.name_utils import acronym_of, search_for
from stored import players

from supermechs.api import ItemData
from supermechs.item import Element, Type
from supermechs.typeshed import Name


if typing.TYPE_CHECKING:
    from disnake import CommandInteraction

__all__ = ("item_name_autocomplete", "mech_name_autocomplete")

acronyms: abc.Mapping[str, set[Name]] = defaultdict(set)


def _make_acronyms(names: abc.Iterable[Name], /) -> None:
    for name in names:
        if acronym := acronym_of(name):
            acronyms[acronym].add(name)


def _get_item_filters(
    options: abc.Mapping[str, typing.Any], /
) -> list[abc.Callable[[ItemData], bool]]:
    filters: list[abc.Callable[[ItemData], bool]] = []

    if (type_name := options.get("type", "ANY")) != "ANY":
        target_type = Type[type_name]
        filters.append(lambda item: item.type is target_type)

    if (element_name := options.get("element", "ANY")) != "ANY":
        target_element = Element[element_name]
        filters.append(lambda item: item.element is target_element)

    return filters


async def item_name_autocomplete(inter: "CommandInteraction", input: str) -> AutocompleteReturnType:
    """Autocomplete for items with regard for type & element."""

    pack = get_item_pack_for(inter)
    filters = _get_item_filters(inter.filled_options)

    if not acronyms:
        _make_acronyms(pack.item_names)

    def filter_item_names(names: abc.Iterable[Name], /) -> t.Iterator[Name]:
        items = map(pack.get_item_by_name, names)

        if filters:
            items = (item for item in items if all(func(item) for func in filters))

        return (item.name for item in items)

    # place matching abbreviations at the top
    if items := acronyms.get(input.lower()):
        matching_item_names = sorted(filter_item_names(items))

        # this shouldn't ever happen, but handle it anyway
        if len(matching_item_names) >= InteractionLimits.autocomplete_options:
            del matching_item_names[InteractionLimits.autocomplete_options :]
            return matching_item_names

        # extra filter to exclude duplicates
        filters.append(lambda item: item.name not in items)

    else:
        matching_item_names = []

    import heapq

    # extend names up to option limit
    matching_item_names += heapq.nsmallest(
        InteractionLimits.autocomplete_options - len(matching_item_names),
        filter_item_names(search_for(input, pack.item_names)),
    )
    return matching_item_names


async def mech_name_autocomplete(inter: "CommandInteraction", input: str) -> AutocompleteReturnType:
    """Autocomplete for player builds."""

    player = players(inter.author)
    lowercase = input.lower()

    matching = [name for name in player.builds if name.lower().startswith(lowercase)]

    if not matching and input:
        return [input]

    return matching
