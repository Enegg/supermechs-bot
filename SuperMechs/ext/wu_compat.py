import typing as t

from attrs import asdict

from ..player import Player

from ..core import MAX_BUFFS
from ..game_types import AnyStats
from ..inv_item import AnyInvItem, InvItem
from ..item import AnyItem
from ..mech import Mech

if t.TYPE_CHECKING:
    from ..pack_interface import PackInterface


# ------------- Serialization -------------


class WUBattleItem(t.TypedDict):
    slotName: str
    id: int
    name: str
    type: str
    stats: AnyStats
    tags: dict[str, bool]
    element: str
    timesUsed: t.Literal[0]


class WUMech(t.TypedDict):
    name: str
    setup: list[int]


class WUSerialized(t.TypedDict):
    name: str
    itemsHash: str
    mech: WUMech


class ExportedMechsJSON(t.TypedDict):
    version: str
    mechs: dict[str, list[WUMech]]


WU_SLOT_NAMES = (
    "torso",
    "legs",
    "sideWeapon1",
    "sideWeapon2",
    "sideWeapon3",
    "sideWeapon4",
    "topWeapon1",
    "topWeapon2",
    "drone",
    "chargeEngine",
    "teleporter",
    "grapplingHook",
)
WU_MODULE_SLOT_NAMES = (
    "module1",
    "module2",
    "module3",
    "module4",
    "module5",
    "module6",
    "module7",
    "module8",
)
_slot_for_slot = {"chargeEngine": "charge", "teleporter": "tele", "grapplingHook": "hook"}


def wu_slot_to_mech_slot(slot: str) -> str:
    if slot.startswith("side"):
        return "side" + slot[-1]

    if slot.startswith("top"):
        return "top" + slot[-1]

    return _slot_for_slot.get(slot, slot)


def mech_items_in_wu_order(mech: Mech) -> t.Iterator[AnyInvItem | None]:
    yield mech.torso
    yield mech.legs
    yield from mech.iter_items(weapons=True)
    yield mech.drone
    yield mech.charge
    yield mech.tele
    yield mech.hook
    yield from mech.iter_items(modules=True)


def iter_mech_item_ids(mech: Mech) -> t.Iterator[int]:
    return (0 if item is None else item.id for item in mech_items_in_wu_order(mech))


def mech_to_id_str(mech: Mech, sep: str = "_") -> str:
    """Helper function to serialize a mech into a string of item IDs."""
    return sep.join(map(str, iter_mech_item_ids(mech)))


def export_mech(mech: Mech) -> WUMech:
    return {"name": mech.name, "setup": list(iter_mech_item_ids(mech))}


def import_mech(data: WUMech, pack: "PackInterface") -> Mech:
    mech = Mech(name=data["name"])

    for item_id, wu_slot in zip(data["setup"], WU_SLOT_NAMES + WU_MODULE_SLOT_NAMES):
        slot = wu_slot_to_mech_slot(wu_slot)
        item = pack.get_item_by_id(item_id)
        mech[slot] = InvItem.from_item(item, maxed=True)

    return mech


def wu_serialize_item(item: AnyItem, slot_name: str) -> WUBattleItem:
    return {
        "slotName": slot_name,
        "id": item.id,
        "name": item.name,
        "type": item.type.name,
        "stats": MAX_BUFFS.buff_stats(item.stats.at(item.transform_range.max)),
        "tags": asdict(item.tags),
        "element": item.element.name,
        "timesUsed": 0,
    }


def wu_serialize_mech(mech: Mech, player_name: str) -> WUSerialized:
    if mech.custom:
        raise TypeError("Cannot serialize a custom mech into WU format")

    serialized_items_without_modules = [
        None if inv_item is None else wu_serialize_item(inv_item.base, slot)
        for slot, inv_item in zip(WU_SLOT_NAMES, mech_items_in_wu_order(mech))
    ]
    # lazy import
    import hashlib
    import json

    json_string = json.dumps(serialized_items_without_modules, indent=None)
    hash = hashlib.sha256(json_string.encode()).hexdigest()

    return {
        "name": str(player_name),
        "itemsHash": hash,
        "mech": export_mech(mech)
    }


def build_to_json(
    player: Player, player_name: str | None = None, build_name: str | None = None
) -> WUSerialized:
    """Parses a build to WU acceptable JSON format."""

    name = player.active_build_name or build_name

    if name is None:
        raise ValueError("Player has no active build and name was not passed.")

    build = player.builds.get(name)

    if build is None:
        raise TypeError(f"Player does not have a build {name}.")

    return wu_serialize_mech(build, player_name or player.name)
