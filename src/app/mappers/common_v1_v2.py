from collections import abc

from app.dto.common import ItemStatsDto
from app.mappers.common import LETTER_TO_TIER, TIER_TO_MAX_LEVEL, convert_stats

import dupermechs.all as sm


def stats_to_stages(stats_dto: ItemStatsDto, transform_range: str) -> abc.Sequence[sm.Item.Stage]:
    lo, _, hi = transform_range.lower().partition("-")

    if not hi:
        hi = lo

    lo = LETTER_TO_TIER[lo]
    hi = LETTER_TO_TIER[hi]

    Rarity = sm.Item.Rarity
    tiers = [Rarity(i) for i in range(lo, hi + 1)]

    final_level = sm.Item.Stage.Level(
        level=TIER_TO_MAX_LEVEL[tiers[-1]], stats=convert_stats(stats_dto)
    )

    if len(tiers) == 1:
        return (sm.Item.Stage(tier=tiers[-1], levels=(final_level,)),)

    shared_stats = sm.ItemStats()
    levels: list[sm.Item.Stage.Level] = [
        sm.Item.Stage.Level(level=TIER_TO_MAX_LEVEL[tier], stats=shared_stats)
        for tier in tiers[:-1]
    ]
    levels.append(final_level)

    return tuple(
        sm.Item.Stage(tier=tier, levels=(level,)) for level, tier in zip(levels, tiers, strict=True)
    )
