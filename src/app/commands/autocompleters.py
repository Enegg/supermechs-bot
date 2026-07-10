import enum
from collections import abc
from difflib import SequenceMatcher
from itertools import islice
from typing import TYPE_CHECKING, Final, NamedTuple, cast as type_cast

from discord import AutocompleteReturnType, InteractionLimits

from app.core import state
from app.typeshed import CommandInteraction

if TYPE_CHECKING:
    from .params import FilledOptions

__all__ = ("item_name_autocomplete",)


class MatchQuality(enum.IntEnum):
    # match order:
    # 1. name == query (caseless)
    exact = enum.auto()
    # 2. Overcharged Rocket Battery => "ORB" == query (caseless)
    acronym = enum.auto()
    # 3. name.startswith(query); for multi-word names this also considers inner words
    prefix = enum.auto()
    # 4. query in name
    substring = enum.auto()
    # 5. Levenshtein distance
    fuzzy = enum.auto()


class ItemMatch(NamedTuple):
    name: str
    quality: MatchQuality
    word_index: int = 0
    fuzzy_score: float = 0.0


CUTOFF: Final = 2 / 3


def find_matches(item_names: abc.Iterable[str], query: str) -> list[ItemMatch]:
    # TODO: operate on "tokens", i.e. "HeronMark" should be seen as-if it was ["Heron", "Mark"]
    query_lowercase = query.casefold()

    results: list[ItemMatch] = []

    seq_matcher = SequenceMatcher(b=query_lowercase)

    for name in item_names:
        name_lowercase = name.casefold()

        if name_lowercase.startswith(query_lowercase):
            results.append(ItemMatch(
                name=name,
                quality=MatchQuality.exact
                if len(name_lowercase) == len(query_lowercase)
                else MatchQuality.prefix,
            ))  # fmt: skip
            continue

        if acronym_of(name) == query_lowercase:
            results.append(ItemMatch(name, quality=MatchQuality.acronym))
            continue

        last_space_index = 0
        # in "my new item", "new" is word_index == 1
        word_index = 0

        while (last_space_index := name_lowercase.find(" ", last_space_index) + 1) != 0:
            word_index += 1
            if name_lowercase.startswith(query_lowercase, last_space_index):
                results.append(ItemMatch(name, MatchQuality.prefix, word_index=word_index))
                break
        else:
            # this is effectively `query_lowercase in name_lowercase`, but also finds number of spaces
            if (query_index := name_lowercase.find(query_lowercase)) != -1:
                results.append(ItemMatch(
                    name,
                    quality=MatchQuality.substring,
                    # number of spaces preceeding the match == index of first matching word
                    word_index=name_lowercase.count(" ", None, query_index),
                ))  # fmt: skip
                continue

            ratios = [
                get_ratio(name_part, seq_matcher, CUTOFF) for name_part in name_lowercase.split(" ")
            ]

            best_ratio = max(ratios)
            if best_ratio > CUTOFF:
                results.append(
                    ItemMatch(
                        name,
                        quality=MatchQuality.fuzzy,
                        word_index=ratios.index(best_ratio),
                        fuzzy_score=best_ratio,
                    )
                )

    results.sort(key=lambda s: (-s.quality, -s.word_index, s.fuzzy_score), reverse=True)
    return results


def get_ratio(name: str, matcher: SequenceMatcher[str], cutoff: float = 0.3) -> float:
    matcher.set_seq1(name)

    if (score := matcher.real_quick_ratio()) < cutoff:
        return score

    if (score := matcher.quick_ratio()) < cutoff:
        return score

    return matcher.ratio()


def acronym_of(name: str, /) -> str | None:
    """Return an acronym of a name, or None if one cannot be made.

    The acronym consists of capital letters in the name;
    there need to be at least two capital letters, and one lowercase.
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


def item_name_autocomplete(inter: CommandInteraction, input: str) -> AutocompleteReturnType:
    """Autocomplete for items with regard for slot & element."""
    filled_options: FilledOptions = type_cast("FilledOptions", inter.filled_options)

    items = state.filter_items(
        slot=filled_options.get("slot"),
        element=filled_options.get("element"),
        rarity=filled_options.get("rarity"),
        legacy=inter.application_command.name == "legacy-item",  # HACK
    )
    names = (item.name for item in items)
    input = input.strip()

    if not input:
        return list(islice(names, InteractionLimits.autocomplete_options))

    matching = find_matches(names, input)
    del matching[InteractionLimits.autocomplete_options :]
    return [match.name for match in matching]
