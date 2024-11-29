from collections import abc
from datetime import datetime

from cattrs import Converter
from cattrs.strategies import configure_union_passthrough

from supermechs.abc import ItemData, ItemID, MechSlot
from supermechs.mech import Mech


def unstructure_mech(mech: Mech[ItemData], /) -> abc.Mapping[MechSlot, ItemID]:
    return {slot: item.id for slot, item in mech.setup.items()}


converter = Converter(unstruct_collection_overrides={abc.Set: list})


converter.register_structure_hook(datetime, lambda v, _: datetime.fromisoformat(v))
configure_union_passthrough(str | bool | int | float | None, converter)
converter.register_unstructure_hook(Mech, unstructure_mech)
