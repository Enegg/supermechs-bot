from assets import ASSETS

from supermechs.api import ItemData, Tier
from supermechs.tools.item import transform_range


def item_transform_range(item: ItemData, /, at_tier: Tier | None = None) -> str:
    tiers = transform_range(item)

    if at_tier is None:
        at_tier = tiers[-1]

    index = at_tier - tiers[0]
    str_range = [ASSETS.tiers[tier].emoji for tier in tiers]
    str_range[index] = f"({str_range[index]})"
    return "".join(str_range)
