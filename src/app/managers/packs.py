import logging
from collections import abc
from typing import Final, overload

from app.models.ids import DEFAULT_PACK_ID, PackId
from app.models.item_pack import ItemPack, ItemPackMetadata

import dupermechs.all as sm

_LOG = logging.getLogger("managers")

_item_packs: Final[abc.Mapping[PackId, ItemPack]] = {DEFAULT_PACK_ID: ItemPack(id=DEFAULT_PACK_ID)}
_metadata: Final[abc.Mapping[PackId, ItemPackMetadata]] = {DEFAULT_PACK_ID: ItemPackMetadata()}


def get_item_pack(id: PackId = DEFAULT_PACK_ID, /) -> ItemPack:
    return _item_packs[id]


def get_item_pack_metadata(id: PackId = DEFAULT_PACK_ID, /) -> ItemPackMetadata:
    return _metadata[id]


def get_item_by_id(id: sm.Item.Id, /, pack_id: PackId = DEFAULT_PACK_ID) -> sm.IItem:
    return get_item_pack(pack_id).reloaded_items[id]


def find_first_by_name(name: str, /, *, ignore_case: bool = False) -> sm.IItem | None:
    if ignore_case:
        name = name.lower()

        for item in iter_items():
            if item.name.lower() == name:
                return item

    else:
        for item in iter_items():
            if item.name == name:
                return item

    return None


def find_items_by_names(*names: str, ignore_case: bool = False) -> list[sm.IItem]:
    if ignore_case:
        names = tuple(map(str.lower, names))
        return [item for item in iter_items() if item.name.lower() in names]

    return [item for item in iter_items() if item.name in names]


@overload
def iter_items() -> abc.Iterator[sm.IItem]: ...
@overload
def iter_items(*pack_ids: PackId) -> abc.Iterator[sm.IItem]: ...
def iter_items(pack_id: PackId = DEFAULT_PACK_ID, /, *pack_ids: PackId) -> abc.Iterator[sm.IItem]:
    yield from get_item_pack(pack_id).reloaded_items.values()

    for pack_id in pack_ids:  # noqa: PLR1704
        pack = get_item_pack(pack_id)
        yield from pack.reloaded_items.values()


def store_item_pack(pack: ItemPack, /) -> None:
    _LOG.info(
        "Storing item pack: %d, reloaded=%d, legacy=%d",
        pack.id,
        len(pack.reloaded_items),
        len(pack.legacy_items),
    )
    _item_packs[pack.id] = pack
