from collections import abc
from difflib import SequenceMatcher
from typing import Any, NamedTuple

from discord import AutocompleteReturnType, InteractionLimits

from app.bridges.sm_utils import get_item_pack_for
from app.bridges.user_input import sanitize_string
from app.disnake_types import CommandInteraction
from app.local_storage import players

from supermechs.abc import ItemData

__all__ = ("item_name_autocomplete", "mech_name_autocomplete")


class MatchResult(NamedTuple):
    name: str
    direct_score: float
    multiword_scores: abc.Sequence[float]
    is_acronym: bool

    def sort_key(self) -> tuple[object, ...]:
        return (
            self.is_acronym,
            max(self.direct_score, max(self.multiword_scores, default=0.0)),
            self.direct_score,
        )


def get_ratio(name: str, matcher: SequenceMatcher[str], cutoff: float = 0.3) -> float:
    matcher.set_seq1(name)

    if (score := matcher.real_quick_ratio()) < cutoff:
        return score

    if (score := matcher.quick_ratio()) < cutoff:
        return score

    return matcher.ratio()


def get_multiword_scores(
    name: str, phrase_parts: abc.Sequence[str], matcher: SequenceMatcher[str]
) -> abc.Sequence[float]:
    name_parts = name.split(" ")

    if len(name_parts) == 1 or len(name_parts) < len(phrase_parts):
        return ()

    scores: list[float] = []

    for phrase_part in phrase_parts:
        matcher.set_seq2(phrase_part)

        max_score: float = 0.0

        for name_part in name_parts:
            max_score = max(get_ratio(name_part, matcher), max_score)

        scores.append(max_score)

    return scores


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


def find_matches(names: abc.Iterable[str], phrase: str) -> list[MatchResult]:
    phrase = phrase.lower()
    phrase_parts = [part for raw_part in phrase.split(" ") if (part := raw_part.strip())]

    whole_matcher = SequenceMatcher(b=phrase)
    multiword_matcher = SequenceMatcher[str]()

    results: list[MatchResult] = []

    for name in names:
        lowercase_name = name.lower()
        direct_score = get_ratio(lowercase_name, whole_matcher)
        multiword_scores = get_multiword_scores(lowercase_name, phrase_parts, multiword_matcher)
        is_acronym = acronym_of(name) == phrase

        results.append(MatchResult(name, direct_score, multiword_scores, is_acronym))

    results.sort(key=MatchResult.sort_key, reverse=True)
    return results


def _get_item_filters(
    options: abc.Mapping[str, Any], /
) -> list[abc.Callable[[ItemData], bool]]:
    filters: list[abc.Callable[[ItemData], bool]] = []

    if (target_type := options.get("type", "ANY")) != "ANY":
        filters.append(lambda item: item.type == target_type)

    if (target_element := options.get("element", "ANY")) != "ANY":
        filters.append(lambda item: item.element == target_element)

    return filters


async def item_name_autocomplete(inter: CommandInteraction, input: str) -> AutocompleteReturnType:
    """Autocomplete for items with regard for type & element."""
    pack = get_item_pack_for(inter)
    filters = _get_item_filters(inter.filled_options)

    def filter_item_names() -> abc.Iterator[str]:
        return (
            item.name
            for item in pack.items.values()
            if all(func(item) for func in filters)
        )  # fmt: skip

    input = input.strip()
    matching = find_matches(filter_item_names(), input)
    del matching[InteractionLimits.autocomplete_options :]
    return [result.name for result in matching]


async def mech_name_autocomplete(inter: CommandInteraction, input: str) -> AutocompleteReturnType:
    """Autocomplete for player builds."""
    player = players(inter.author)
    lowercase = input.lower()

    matching = [
        build.name for build in player.builds.values() if build.name.lower().startswith(lowercase)
    ]

    if not matching and input:
        return [sanitize_string(input)]

    return matching
