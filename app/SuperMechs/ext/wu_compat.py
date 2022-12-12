import typing as t

import orjson
from attrs import asdict

from ..core import MAX_BUFFS
from ..inv_item import AnyInvItem, InvItem
from ..item import AnyItem
from ..mech import Mech
from ..typedefs import AnyStats
from ..utils import truncate_name

if t.TYPE_CHECKING:
    from ..pack_interface import PackInterface


# ------------------------------------------ typed dicts -------------------------------------------


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
    version: int
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

    if slot.startswith("module"):
        return "mod" + slot[-1]

    return _slot_for_slot.get(slot, slot)


def _mech_items_in_wu_order(mech: Mech) -> t.Iterator[AnyInvItem | None]:
    yield mech.torso
    yield mech.legs
    yield from mech.iter_items(weapons=True)
    yield mech.drone
    yield mech.charge
    yield mech.tele
    yield mech.hook
    yield from mech.iter_items(modules=True)


def _mech_items_ids_in_wu_order(mech: Mech) -> t.Iterator[int]:
    """Iterator yielding mech item IDs in WU compatible order."""
    return (0 if item is None else item.id for item in _mech_items_in_wu_order(mech))


def mech_to_id_str(mech: Mech, sep: str = "_") -> str:
    """Helper function to serialize a mech into a string of item IDs."""
    return sep.join(map(str, _mech_items_ids_in_wu_order(mech)))


# -------------------------------------------- imports ---------------------------------------------


def import_mech(data: WUMech, pack: "PackInterface") -> Mech:
    """Imports a mech from WU mech."""
    mech = Mech(name=truncate_name(data["name"]))

    for item_id, wu_slot in zip(data["setup"], WU_SLOT_NAMES + WU_MODULE_SLOT_NAMES):
        slot = wu_slot_to_mech_slot(wu_slot)
        if item_id != 0:
            item = pack.get_item_by_id(item_id)
            mech[slot] = InvItem.from_item(item, maxed=True)

        else:
            mech[slot] = None

    return mech


def import_mechs(
    json: ExportedMechsJSON, pack: "PackInterface"
) -> tuple[list[Mech], list[tuple[int, str]]]:
    """Imports mechs from parsed .JSON file."""

    # TODO: in 3.11 consider using ExceptionGroups to catch all problems at once
    try:
        version = json["version"]
        mech_list = json["mechs"][pack.key]

    except KeyError as e:
        raise ValueError(f'Malformed data: key "{e}" not found.') from e

    if version != 1:
        raise ValueError(f"Expected version = 1, got {version}")

    if not isinstance(mech_list, list):
        raise TypeError('Expected a list under "mechs" key')

    mechs: list[Mech] = []
    failed: list[tuple[int, str]] = []

    for i, wu_mech in enumerate(mech_list, 1):
        try:
            mechs.append(import_mech(wu_mech, pack))

        except Exception as e:
            failed.append((i, str(e)))

    return mechs, failed


def load_mechs(
    data: bytes, pack: "PackInterface"
) -> tuple[list[Mech], list[tuple[int, str]]]:
    """Loads mechs from bytes object, representing a .JSON file."""
    return import_mechs(orjson.loads(data), pack)


# -------------------------------------------- exports ---------------------------------------------


def export_mech(mech: Mech) -> WUMech:
    """Exports a mech to WU mech."""
    return {"name": mech.name, "setup": list(_mech_items_ids_in_wu_order(mech))}


def export_mechs(mechs: t.Iterable[Mech], pack_key: str) -> ExportedMechsJSON:
    """Exports mechs to WU compatible format."""
    wu_mechs = list(map(export_mech, mechs))
    return {"version": 1, "mechs": {pack_key: wu_mechs}}


def dump_mechs(mechs: t.Iterable[Mech], pack_key: str) -> bytes:
    """Dumps mechs into bytes representing a .JSON file."""
    return orjson.dumps(export_mechs(mechs, pack_key), option=orjson.OPT_INDENT_2)


def wu_serialize_item(item: AnyItem, slot_name: str) -> WUBattleItem:
    return {
        "slotName": slot_name,
        "id": item.id,
        "name": item.name,
        "type": item.type.name,
        "stats": MAX_BUFFS.buff_stats(item.max_stats),
        "tags": asdict(item.tags),
        "element": item.element.name,
        "timesUsed": 0,
    }


def wu_serialize_mech(mech: Mech, player_name: str) -> WUSerialized:
    if mech.custom:
        raise TypeError("Cannot serialize a custom mech into WU format")

    serialized_items_without_modules = [
        None if inv_item is None else wu_serialize_item(inv_item.base, slot)
        for slot, inv_item in zip(WU_SLOT_NAMES, _mech_items_in_wu_order(mech))
    ]
    # lazy import
    import hashlib

    data = orjson.dumps(serialized_items_without_modules)
    hash = hashlib.sha256(data).hexdigest()

    return {"name": str(player_name), "itemsHash": hash, "mech": export_mech(mech)}
