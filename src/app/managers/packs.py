import logging
from collections import abc

from app.models.item_pack import ItemPack, ItemPackMetadata

import dupermechs.all as sm

_LOG = logging.getLogger("managers")
_item_pack: ItemPack = ItemPack()


def get_item_pack() -> ItemPack:
    return _item_pack


def get_item_pack_metadata() -> ItemPackMetadata:
    return ItemPackMetadata()  # TODO


def get_item_by_id(id: sm.Item.Id, /) -> sm.IItem:
    return _item_pack.reloaded_items[id]


def filter_items(
    slot: str | None = None,
    element: str | None = None,
    rarity: str | None = None,
    legacy: bool = False,
) -> abc.Iterator[sm.IItem]:
    filters: list[abc.Callable[[sm.IItem], bool]] = []

    if slot is not None:
        target_slot = sm.Item.Slot[slot]
        filters.append(lambda item: item.slot_id is target_slot)

    if element is not None:
        target_element = sm.Item.Element[element]
        filters.append(lambda item: item.element is target_element)

    if rarity is not None:
        min_tier = sm.Item.Rarity[rarity]
        filters.append(lambda item: item.stages[0].tier >= min_tier)

    bank = _item_pack.legacy_items if legacy else _item_pack.reloaded_items

    if not filters:
        yield from bank.values()
        return

    for item in bank.values():
        if all(f(item) for f in filters):
            yield item


def store_item_pack(pack: ItemPack, /) -> None:
    global _item_pack
    _LOG.info(
        "Storing item pack: reloaded=%d, legacy=%d",
        len(pack.reloaded_items),
        len(pack.legacy_items),
    )
    _item_pack = pack
