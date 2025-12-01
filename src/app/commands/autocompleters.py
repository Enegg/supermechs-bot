from collections import abc
from difflib import SequenceMatcher
from itertools import islice
from typing import TYPE_CHECKING, NamedTuple, cast as type_cast

from app.disnake_types import CommandInteraction
from discord import AutocompleteReturnType, InteractionLimits

from app.managers import packs

if TYPE_CHECKING:
    from .params import FilledOptions

__all__ = ("item_name_autocomplete",)


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


def item_name_autocomplete(inter: CommandInteraction, input: str) -> AutocompleteReturnType:
    """Autocomplete for items with regard for type & element."""
    filled_options: FilledOptions = type_cast("FilledOptions", inter.filled_options)

    items = packs.filter_items(
        type=filled_options.get("type"),
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
    return [result.name for result in matching]
