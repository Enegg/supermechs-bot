from collections import abc
from difflib import SequenceMatcher
from itertools import islice
from typing import TYPE_CHECKING, Any, NamedTuple, cast as type_cast

from app.disnake_types import CommandInteraction
from discord import AutocompleteReturnType, InteractionLimits

from app.managers import packs, players
from app.text_utils import acronym_of, sanitize_string

import dupermechs.all as sm

if TYPE_CHECKING:
    from .params import FilledOptions

__all__ = ("item_name_autocomplete", "mech_name_autocomplete")


class MatchResult(NamedTuple):
    name: str
    direct_score: float
    multiword_scores: abc.Sequence[float]
    is_acronym: bool

    def sort_key(self) -> tuple[object, ...]:
        return (
            self.is_acronym,
            # max of an iterable, then of the two
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
) -> list[abc.Callable[[sm.IItem], bool]]:
    options = type_cast("FilledOptions", options)

    filters: list[abc.Callable[[sm.IItem], bool]] = []

    if (type_name := options.get("type")) is not None:
        target_type= sm.Item.Type[type_name]
        filters.append(lambda item: item.type is target_type)

    if (element_name := options.get("element")) is not None:
        target_element = sm.Item.Element[element_name]
        filters.append(lambda item: item.element is target_element)

    if (tier_name := options.get("rarity")) is not None:
        min_tier = sm.Item.Rarity[tier_name]
        filters.append(lambda item: item.stages[0].tier >= min_tier)

    return filters


def item_name_autocomplete(inter: CommandInteraction, input: str) -> AutocompleteReturnType:
    """Autocomplete for items with regard for type & element."""
    # TODO: player-chosen item packs
    filters = _get_item_filters(inter.filled_options)
    names = (
        item.name
        for item in packs.iter_items()
        if all(func(item) for func in filters)
    )  # fmt: skip
    input = input.strip()

    if not input:
        return list(islice(names, InteractionLimits.autocomplete_options))

    matching = find_matches(names, input)
    del matching[InteractionLimits.autocomplete_options :]
    return [result.name for result in matching]


def mech_name_autocomplete(inter: CommandInteraction, input: str) -> AutocompleteReturnType:
    """Autocomplete for player builds."""
    player = players.find_player_by_user(inter.author)

    if player is None:
        return [sanitize_string(input)] if input else []  # cannot send an empty string

    lowercase = input.lower()
    matching = [
        build.name for build in player.iter_builds() if build.name.lower().startswith(lowercase)
    ]

    if not matching and input:
        return [sanitize_string(input)]

    return matching
