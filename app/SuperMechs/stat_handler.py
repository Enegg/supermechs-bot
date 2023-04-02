import logging

from attrs import define
from typing_extensions import Self

from typeshed import dict_items_as

from .core import MAX_LVL_FOR_TIER, AnyStats, TransformRange, ValueRange
from .enums import Tier
from .typedefs import ItemDictVer1, ItemDictVer2, ItemDictVer3, RawStats, iter_stat_keys_and_types
from .utils import NaN

__all__ = ("ItemStatsContainer",)

LOGGER = logging.getLogger(__name__)


def as_gradient(lower: int, upper: int, fraction: float) -> int:
    """Returns a value between the lower and upper numbers,
    with fraction denoting how close to the upper the value gets.
    In other words, at fraction = 0 returns lower, and at fraction = 1 returns upper.
    """
    return lower + round((upper - lower) * fraction)


def as_ranges_gradient(minor: ValueRange, major: ValueRange, fraction: float) -> ValueRange:
    """Returns a range between the minor and major ranges,
    with fraction denoting how close to the major the value gets.
    In other words, at fraction = 0 returns minor, and at fraction = 1 returns major.
    """
    return minor + (
        round((major.lower - minor.lower) * fraction),
        round((major.upper - minor.upper) * fraction),
    )


def transform_raw_stats(data: RawStats, *, strict: bool = False) -> AnyStats:
    """Ensures the data is valid by grabbing factual keys and type checking values.
    Transforms None values to NaNs."""
    final_stats: AnyStats = {}

    # TODO: implement extrapolation of missing data

    for key, data_type in iter_stat_keys_and_types():
        if key not in data:
            continue

        match data[key]:
            case int() | None as value if data_type is int:
                final_stats[key] = NaN if value is None else value

            case [int() | None as x, int() | None as y] if data_type is list:
                final_stats[key] = ValueRange(
                    NaN if x is None else x,
                    NaN if y is None else y,
                )

            case unknown:
                msg = (
                    f"Expected {data_type.__name__} on key '{key}'"
                    f", got {type(unknown)}"
                )
                if strict:
                    raise TypeError(msg)

                LOGGER.warning(msg)

    return final_stats


@define
class TierStats:
    """Object representing stats of an item at particular tier."""

    base_stats: AnyStats
    max_level_stats: AnyStats
    tier: Tier

    def at(self, level: int) -> AnyStats:
        """Returns the stats at given level.

        For convenience, levels follow the game logic; the lowest level is 1
        and the maximum is a multiple of 10 depending on tier.
        """
        level -= 1
        max_level = MAX_LVL_FOR_TIER[self.tier]

        if not 0 <= level <= max_level:
            raise ValueError(f"Level outside range 0-{max_level+1}")

        if level == 0:
            return self.base_stats.copy()

        if level == max_level:
            return self.max

        fraction = level / max_level

        stats: AnyStats = self.base_stats.copy()

        for key, value in dict_items_as(int | ValueRange, self.max_level_stats):
            base_value: int | ValueRange = stats[key]

            if isinstance(value, ValueRange):
                assert isinstance(base_value, ValueRange)
                stats[key] = as_ranges_gradient(base_value, value, fraction)

            else:
                assert not isinstance(base_value, ValueRange)
                stats[key] = as_gradient(base_value, value, fraction)

        return stats

    @property
    def max(self) -> AnyStats:
        """Return the max stats of the item."""
        return self.base_stats | self.max_level_stats


@define
class ItemStatsContainer:
    tier_bases: dict[Tier, AnyStats]
    max_stats: dict[Tier, AnyStats]

    def __getitem__(self, key: Tier) -> TierStats:
        base = AnyStats()

        for tier, tier_base in self.tier_bases.items():
            base |= tier_base

            if tier == key:
                break

            base |= self.max_stats.get(tier, {})

        return TierStats(base, self.max_stats.get(key, {}), key)

    def __contains__(self, value: str | Tier | TransformRange) -> bool:
        # literal stat key
        if isinstance(value, str):
            for mapping in self.tier_bases.values():
                if value in mapping:
                    return True

            return False

        if isinstance(value, Tier):
            return value in self.tier_bases

        if isinstance(value, TransformRange):
            return value.min in self.tier_bases and value.max in self.tier_bases

        return False

    def has_any_of_stats(self, *stats: str, tier: Tier | None = None) -> bool:
        """Check if any of the stat keys appear in the item's stats.

        tier: if specified, checks only at that tier. Otherwise, checks all tiers.
        """
        if tier is not None:
            return not self.tier_bases[tier].keys().isdisjoint(stats)

        for mapping in self.tier_bases.values():
            if not mapping.keys().isdisjoint(stats):
                return True

        return False

    @classmethod
    def from_json_v1_v2(cls, data: ItemDictVer1 | ItemDictVer2, *, strict: bool = False) -> Self:
        tier = Tier.from_letter(data["transform_range"][-1])
        bases = {tier: transform_raw_stats(data["stats"], strict=strict)}
        max_stats = {}
        return cls(bases, max_stats)

    @classmethod
    def from_json_v3(cls, data: ItemDictVer3, *, strict: bool = False) -> Self:
        tier_bases = dict[Tier, AnyStats]()
        max_stats = dict[Tier, AnyStats]()
        hit = False

        for rarity in Tier:
            key = rarity.name.lower()

            if key not in data:
                # if we already populated the dict with stats,
                # missing key means we should break as there will be no further stats
                if hit:
                    break

                # otherwise, we haven't yet got to the starting tier, so continue
                continue

            hit = True
            tier_bases[rarity] = transform_raw_stats(data[key], strict=strict)

            try:
                max_level_data = data["max_" + key]

            except KeyError:
                if rarity is not Tier.DIVINE:
                    if strict:
                        raise

                    LOGGER.warning(f"max_{key} key not found for item {data['name']}")

                max_stats[rarity] = {}

            else:
                max_stats[rarity] = transform_raw_stats(max_level_data, strict=strict)

        return cls(tier_bases, max_stats)
