import io
import json
import typing as t

from attrs import asdict

from SuperMechs.utils import truncate_name

from ..core import MAX_BUFFS
from ..inv_item import AnyInvItem, InvItem
from ..item import AnyItem
from ..mech import Mech
from ..player import Player
from ..typedefs.game_types import AnyStats

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


def export_mechs(mechs: t.Iterable[Mech], pack_key: str) -> ExportedMechsJSON:
    wu_mechs = list(map(export_mech, mechs))
    return {"version": 1, "mechs": {pack_key: wu_mechs}}


def dump_mechs(mechs: t.Iterable[Mech], pack_key: str) -> io.StringIO:
    fp = io.StringIO()
    json.dump(export_mechs(mechs, pack_key), fp, indent=2)
    fp.seek(0)
    return fp


def import_mech(data: WUMech, pack: "PackInterface") -> Mech:
    mech = Mech(name=truncate_name(data["name"]))

    for item_id, wu_slot in zip(data["setup"], WU_SLOT_NAMES + WU_MODULE_SLOT_NAMES):
        slot = wu_slot_to_mech_slot(wu_slot)
        if item_id != 0:
            item = pack.get_item_by_id(item_id)
            mech[slot] = InvItem.from_item(item, maxed=True)

        else:
            mech[slot] = None

    return mech


def load_mechs(data: ExportedMechsJSON, pack: "PackInterface") -> tuple[list[Mech], dict[str, str]]:
    try:
        version = data["version"]
        mech_list = data["mechs"][pack.key]

    except KeyError as e:
        raise ValueError(f'Malformed data: key "{e}" not found.') from e

    if version != 1:
        raise ValueError(f"Expected version = 1, got {version}")

    mechs: list[Mech] = []
    failed: dict[str, str] = {}

    for wu_mech in mech_list:
        try:
            mechs.append(import_mech(wu_mech, pack))

        except Exception as e:
            try:
                name = wu_mech["name"]

            except (KeyError, TypeError):
                failed[str(wu_mech)] = str(e)

            else:
                failed[name] = str(e)

    return mechs, failed


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
        for slot, inv_item in zip(WU_SLOT_NAMES, mech_items_in_wu_order(mech))
    ]
    # lazy import
    import hashlib
    import json

    json_string = json.dumps(serialized_items_without_modules, indent=None)
    hash = hashlib.sha256(json_string.encode()).hexdigest()

    return {"name": str(player_name), "itemsHash": hash, "mech": export_mech(mech)}


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
