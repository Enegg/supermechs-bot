import typing as t

from library_extensions import OPTION_LIMIT
from managers import item_pack_manager, player_manager

from supermechs.api import Element, ItemData, Type
from supermechs.typedefs import Name
from supermechs.utils import acronym_of, search_for

if t.TYPE_CHECKING:
    from disnake import CommandInteraction, Localized

__all__ = ("item_name_autocomplete", "mech_name_autocomplete")

AutocompleteReturnType = t.Sequence["str | Localized[str]"] | t.Mapping[str, "str | Localized[str]"]

acronyms: t.Mapping[str, set[Name]] = {}


def _make_acronyms(names: t.Iterable[Name], /) -> None:
    for name in names:
        if acronym := acronym_of(name):
            try:
                acronyms[acronym].add(name)

            except KeyError:
                acronyms[acronym] = {name}


def _get_item_filters(options: t.Mapping[str, t.Any], /) -> list[t.Callable[[ItemData], bool]]:
    filters: list[t.Callable[[ItemData], bool]] = []

    if (type_name := options.get("type", "ANY")) != "ANY":
        target_type = Type[type_name]
        filters.append(lambda item: item.type is target_type)

    if (element_name := options.get("element", "ANY")) != "ANY":
        target_element = Element[element_name]
        filters.append(lambda item: item.element is target_element)

    return filters


async def item_name_autocomplete(inter: "CommandInteraction", input: str) -> AutocompleteReturnType:
    """Autocomplete for items with regard for type & element."""

    pack = item_pack_manager["@Darkstare"]  # TODO: replace with default pack reference

    filters = _get_item_filters(inter.filled_options)

    if not acronyms:
        _make_acronyms(pack.item_names)

    def filter_item_names(names: t.Iterable[Name]) -> t.Iterator[Name]:
        items = map(pack.get_item_by_name, names)

        if filters:
            items = (item for item in items if all(func(item) for func in filters))

        return (item.name for item in items)

    # place matching abbreviations at the top
    if items := acronyms.get(input.lower()):
        matching_item_names = sorted(filter_item_names(items))

        # this shouldn't ever happen, but handle it anyway
        if len(matching_item_names) >= OPTION_LIMIT:
            del matching_item_names[OPTION_LIMIT:]
            return matching_item_names

        # extra filter to exclude duplicates
        filters.append(lambda item: item.name not in items)

    else:
        matching_item_names = []

    import heapq

    # extend names up to OPTION_LIMIT
    matching_item_names += heapq.nsmallest(
        OPTION_LIMIT - len(matching_item_names),
        filter_item_names(search_for(input, pack.item_names)),
    )
    return matching_item_names


async def mech_name_autocomplete(inter: "CommandInteraction", input: str) -> AutocompleteReturnType:
    """Autocomplete for player builds."""

    player = player_manager(inter.author)
    lowercase = input.lower()

    return [name for name in player.builds if name.lower().startswith(lowercase)]
