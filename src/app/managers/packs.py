import logging
from collections import abc

from app.core import AppState
from app.models.item_pack import ItemPack

import supermechs.all as sm

_LOG = logging.getLogger("managers")


def filter_items(
    item_pack: ItemPack,
    slot: str | None = None,
    element: str | None = None,
    rarity: str | None = None,
    legacy: bool = False,
) -> abc.Iterator[sm.Item]:
    filters: list[abc.Callable[[sm.Item], bool]] = []

    if slot is not None:
        target_slot = sm.Item.Slot[slot]
        filters.append(lambda item: item.slot_id is target_slot)

    if element is not None:
        target_element = sm.Item.Element[element]
        filters.append(lambda item: item.element is target_element)

    if rarity is not None:
        min_tier = sm.Item.Rarity[rarity]
        filters.append(lambda item: item.stages[0].tier >= min_tier)

    bank = item_pack.legacy_items if legacy else item_pack.reloaded_items

    if not filters:
        yield from bank.values()
        return

    for item in bank.values():
        if all(f(item) for f in filters):
            yield item


def store_item_pack(pack: ItemPack, /) -> None:
    _LOG.info(
        "Storing item pack: reloaded=%d, legacy=%d",
        len(pack.reloaded_items),
        len(pack.legacy_items),
    )
    AppState.item_pack = pack
