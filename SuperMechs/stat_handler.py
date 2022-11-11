import typing as t

from attrs import define
from typing_extensions import Self

from .core import MAX_LVL_FOR_TIER, TransformRange
from .enums import Tier
from .typedefs.game_types import AnyStats
from .typedefs.pack_versioning import TiersMixin
from .typeshed import dict_items_as


@define
class StatHandler:
    stat_mapping: dict[Tier, tuple[AnyStats, AnyStats]]

    def __contains__(self, stat: str | Tier | TransformRange) -> bool:
        match stat:
            case str():
                for mapping in self.stat_mapping.values():
                    if stat in mapping[0]:
                        return True

            case Tier():
                return stat in self.stat_mapping

            case TransformRange():
                return stat.min in self.stat_mapping and stat.max in self.stat_mapping

        return False

    def has_stat(self, stat: str, tier: Tier | None = None) -> bool:
        """Check whether the item has a given stat.

        tier: if specified, checks only at that tier. Otherwise, checks all tiers.
        """
        if tier is not None:
            return stat in self.stat_mapping[tier][0]

        for mapping in self.stat_mapping.values():
            if stat in mapping[0]:
                return True

        return False

    def has_any_of_stats(self, *stats: str, tier: Tier | None = None) -> bool:
        """Check if any of the stat keys appear in the item's stats.

        tier: if specified, checks only at that tier. Otherwise, checks all tiers.
        """
        if tier is not None:
            return not self.stat_mapping[tier][0].keys().isdisjoint(stats)

        for mapping in self.stat_mapping.values():
            if not mapping[0].keys().isdisjoint(stats):
                return True

        return False

    def iter_tiers_to(
        self, tier: Tier | None = None, include_maxed: bool = True
    ) -> t.Iterator[AnyStats]:
        """Iterate over the stats, such that each next item has exact stats
        you'd find at given tier."""

        if tier is not None and tier not in self:
            raise ValueError("Tier not present in the item")

        stats: AnyStats = {}

        for tier_, (base, max_) in self.stat_mapping.items():
            stats |= base
            yield stats.copy()
            stats |= max_

            if include_maxed and tier_ is not Tier.DIVINE:
                yield stats.copy()

            if tier is tier_:
                break

    def at(self, tier: Tier, level: int = 0) -> AnyStats:
        """Returns the full stats at given tier and level.

        For convenience, levels follow the game logic; the lowest level is 1
        and the maximum is a multiple of 10 depending on tier.
        The default of 0 is equal to passing the maximum level for a given tier.
        """
        if tier not in self:
            raise ValueError("Tier not present in the item")

        # adjust for the fact that items start at lvl 1
        level -= 1
        max_lvl = MAX_LVL_FOR_TIER[tier]

        if level > max_lvl:
            raise ValueError("Level greater than the tier allows")

        elif level == -1:
            level = max_lvl

        elif level < -1:
            raise ValueError("Item levels start at 1")

        stats: AnyStats = {}

        for tier_, (base, max_) in self.stat_mapping.items():
            stats |= base

            if tier is tier_ and level != max_lvl:
                fraction = level / max_lvl

                for key, value in dict_items_as(int | list[int], max_):
                    match (stats[key], value):
                        case (int() as lower, int() as upper):
                            stats[key] += round((upper - lower) * fraction)

                        case (
                            [int() as lower1, int() as lower2],
                            [int() as upper1, int() as upper2],
                        ):
                            stats[key][0] += round((upper1 - lower1) * fraction)
                            stats[key][1] += round((upper2 - lower2) * fraction)

            else:
                stats |= max_

                if tier is tier_:
                    break

        return stats

    @classmethod
    def from_old_format(cls, stats: AnyStats, tier: Tier = Tier.DIVINE) -> Self:
        """Construct the object from a single stats dict."""
        if tier is Tier.DIVINE:
            return cls({Tier.DIVINE: (stats, {})})
        return cls({tier: (stats, stats)})

    @classmethod
    def from_new_format(cls, json: TiersMixin) -> Self:
        """Create the object from a dict containing stats dicts of different tiers."""
        stat_listing = dict[Tier, tuple[AnyStats, AnyStats]]()
        hit = False

        for rarity in Tier:
            key = rarity.name.lower()

            if key not in json:
                # if we already populated the dict with stats,
                # missing key means we should break as there will be no further stats
                if hit:
                    break

                # otherwise, we haven't yet got to the starting tier, so continue
                continue

            hit = True
            base = json[key]
            top = AnyStats()

            if rarity is not Tier.DIVINE:
                try:
                    top = json["max_" + key]

                except KeyError:
                    pass

            stat_listing[rarity] = (base, top)

        return cls(stat_listing)
