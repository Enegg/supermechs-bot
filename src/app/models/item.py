from typing import Protocol, Self

import attrs

import dupermechs.all as sm


class HasStats(Protocol):
    @property
    def stats(self) -> sm.IItemStats: ...


@attrs.frozen(kw_only=True)
class Item:
    id: sm.Item.Id
    name: str
    type: sm.Item.Type
    element: sm.Item.Element = sm.Item.Element.other
    tier: sm.Item.Rarity = sm.Item.Rarity.common
    level: int = 0
    power_required: int = 0
    power_contribution: int = 0
    stats: sm.IItemStats = attrs.field(factory=sm.ItemStats)

    @classmethod
    def maxed(cls, item: sm.IItem, /) -> Self:
        stage = item.stages[-1]
        level = len(stage.levels) - 1
        return cls(
            id=item.id,
            name=item.name,
            type=item.type,
            element=item.element,
            tier=stage.tier,
            level=level,
            stats=stage.levels[level].stats,
        )
