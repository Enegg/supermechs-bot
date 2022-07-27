from __future__ import annotations

import asyncio
import re
import typing as t
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from utils import dict_items_as, format_count

from .core import STATS, WORKSHOP_STATS, ArenaBuffs, GameVars
from .enums import Element, Type
from .images import MechRenderer
from .inv_item import AnyInvItem, InvItem, InvItemSlot
from .types import Attachment, Attachments, WUSerialized

if t.TYPE_CHECKING:
    from aiohttp import ClientSession
    from PIL.Image import Image


# fmt: off
_slots = (
    "torso", "legs", "drone", "side1",
    "side2", "side3", "side4", "top1",
    "top2", "tele", "charge", "hook",
    "mod1", "mod2", "mod3", "mod4",
    "mod5", "mod6", "mod7", "mod8"
)
# fmt: on

_slots_set = frozenset(_slots)


@dataclass
class Mech:
    """Represents a mech build."""

    game_vars: GameVars = GameVars.default()
    is_custom: bool = False
    _stats: defaultdict[str, int] = field(default_factory=lambda: defaultdict(int), init=False)
    _image: Image | None = field(default=None, init=False)

    # fmt: off
    torso:  InvItem[Attachments] | None = None
    legs:   InvItem[Attachment] | None = None
    drone:  InvItem[None] | None = None
    side1:  InvItem[Attachment] | None = None
    side2:  InvItem[Attachment] | None = None
    side3:  InvItem[Attachment] | None = None
    side4:  InvItem[Attachment] | None = None
    top1:   InvItem[Attachment] | None = None
    top2:   InvItem[Attachment] | None = None
    tele:   InvItem[None] | None = None
    charge: InvItem[None] | None = None
    hook:   InvItem[None] | None = None
    mod1:   InvItem[None] | None = None
    mod2:   InvItem[None] | None = None
    mod3:   InvItem[None] | None = None
    mod4:   InvItem[None] | None = None
    mod5:   InvItem[None] | None = None
    mod6:   InvItem[None] | None = None
    mod7:   InvItem[None] | None = None
    mod8:   InvItem[None] | None = None
    # fmt: on

    def __setitem__(
        self, slot: str | Type | tuple[str | Type, int], item: AnyInvItem | None, /
    ) -> None:
        if not isinstance(item, (InvItem, type(None))):
            raise TypeError(f"Expected Item object or None, got {type(item)}")

        match slot:
            case (str() as _slot, int() as pos):
                slot = _slot.lower()

            case (Type() as _slot, int() as pos):
                slot = _slot.name.lower()

            case Type():
                slot = slot.name.lower()
                pos = None

            case str() as _slot:
                slot = _slot.lower()
                pos = None

            case _:
                raise TypeError(f"Invalid type {type(slot)}")

        del self.stats

        if slot in _slots_set:
            self.invalidate_image(item, self[slot])
            setattr(self, slot, item)
            return

        item_types: dict[str, tuple[str, int]] = {
            "module": ("mod", 8),
            "side_weapon": ("side", 4),
            "top_weapon": ("top", 2),
        }

        if slot not in item_types:
            raise TypeError(f"{slot!r} is not a valid slot")

        if pos is None:
            raise TypeError(f'"{slot}" requires pos passed')

        slug, limit = item_types[slot]

        if not 0 < pos <= limit:
            raise ValueError(f"Position outside range 1-{limit}")

        slot = slug + str(pos)
        self.invalidate_image(item, self[slot])
        setattr(self, slot, item)

    def __getitem__(self, place: str) -> AnyInvItem | None:
        if not isinstance(place, str):
            raise TypeError("Only string indexing supported")

        if place not in _slots_set:
            raise KeyError(f'"{place}" is not a valid item slot')

        return getattr(self, place)

    def __str__(self) -> str:
        string_parts = [
            f"{item.type.name.capitalize()}: {item}"
            for item in (self.torso, self.legs, self.drone)
            if item is not None
        ]

        if weapon_string := ", ".join(format_count(self.iter_weapons())):
            string_parts.append("Weapons: " + weapon_string)

        string_parts.extend(
            f"{item.type.name.capitalize()}: {item}"
            for item in self.iter_specials()
            if item is not None
        )

        if modules := ", ".join(format_count(self.iter_modules())):
            string_parts.append("Modules: " + modules)

        return "\n".join(string_parts)

    def __format__(self, spec: str, /) -> str:
        a = "{self:a}"
        return str(self)

    @property
    def weight(self) -> int:
        return self.stats.get("weight", 0)

    @property
    def is_valid(self) -> bool:
        return (
            self.torso is not None
            and self.legs is not None
            and any(wep is not None for wep in self.iter_weapons())
            and self.weight <= self.game_vars.MAX_OVERWEIGHT
        )

    @property
    def stats(self) -> defaultdict[str, int]:
        if self._stats:
            return self._stats

        stats_cache = self._stats

        for item in filter(None, self.iter_items()):
            for key in WORKSHOP_STATS:
                if key in item.stats:
                    stats_cache[key] += item.stats[key]

        if (weight := stats_cache["weight"]) > self.game_vars.MAX_WEIGHT:
            for stat, pen in dict_items_as(int, self.game_vars.PENALTIES):
                stats_cache[stat] -= (weight - self.game_vars.MAX_WEIGHT) * pen

        return stats_cache

    @stats.deleter
    def stats(self) -> None:
        self._stats.clear()

    @property
    def sorted_stats(self) -> list[tuple[str, int]]:
        return sorted(self.stats.items(), key=lambda stat: WORKSHOP_STATS.index(stat[0]))

    def buffed_stats(self, buffs: ArenaBuffs, /) -> t.Iterator[tuple[str, int]]:
        for stat, value in self.sorted_stats:
            yield stat, buffs.total_buff(stat, value)

    def print_stats(self, buffs: ArenaBuffs | None = None, /) -> str:
        if buffs is None:
            bank = iter(self.sorted_stats)

        else:
            bank = self.buffed_stats(buffs)

        weight, value = next(bank)
        name = STATS[weight].name
        icon = STATS[weight].emoji
        vars = self.game_vars

        # fmt: off
        weight_usage = (
            "⛔"
            if value >  vars.MAX_OVERWEIGHT   else "❕"
            if value >  vars.MAX_WEIGHT       else "👌"
            if value >= vars.MAX_WEIGHT       else "🆗"
            if value >= vars.MAX_WEIGHT * .99 else "⚙️"
            if value >= 0                     else "🗿"
        )
        # fmt: on

        return f"{icon} **{value}** {name} {weight_usage}\n" + "\n".join(
            "{0.emoji} **{1}** {0.name}".format(STATS[stat], value) for stat, value in bank
        )

    @property
    def image(self) -> Image:
        """Returns `Image` object merging all item images.
        Requires the torso to be set, otherwise raises `RuntimeError`"""
        if self._image is not None:
            return self._image

        if self.torso is None:
            raise RuntimeError("Cannot create image without torso set")

        canvas = MechRenderer(self.torso)

        if self.legs is not None:
            canvas.add_image(self.legs, "leg1")
            canvas.add_image(self.legs, "leg2")

        for item, layer in self.iter_weapons(True):
            if item is None:
                continue

            canvas.add_image(item, layer)

        if self.drone is not None:
            canvas.add_image(
                self.drone,
                "drone",
                canvas.pixels_left + self.drone.image.width // 2,
                canvas.pixels_above + self.drone.image.height + 25,
            )

        self._image = canvas.finalize()
        return self._image

    @image.deleter
    def image(self) -> None:
        self._image = None

    def invalidate_image(self, new: AnyInvItem | None, old: AnyInvItem | None) -> None:
        if new is not None and new.underlying.displayable:
            del self.image

        elif old is not None and old.underlying.displayable:
            del self.image

    @property
    def has_image_cached(self) -> bool:
        """Returns True if the image is in cache, False otherwise.
        Does not check if the cache has been changed."""
        return self._image is not None

    async def load_images(self, session: ClientSession) -> None:
        """Bulk loads item images"""
        coros = {
            item.underlying.load_image(session)
            for item in self.iter_items()
            if item is not None
            if not item.underlying.has_image
        }

        if coros:
            await asyncio.wait(coros, timeout=5, return_when="ALL_COMPLETED")

    @t.overload
    def iter_weapons(self) -> t.Iterator[InvItemSlot[Attachment]]:
        ...

    @t.overload
    def iter_weapons(
        self, slots: t.Literal[True]
    ) -> t.Iterator[tuple[InvItemSlot[Attachment], str]]:
        ...

    def iter_weapons(
        self, slots: bool = False
    ) -> t.Iterator[tuple[InvItemSlot[Attachment], str] | InvItemSlot[Attachment]]:
        """Iterator over mech's side and top weapons"""
        weapon_slots = ("side1", "side2", "side3", "side4", "top1", "top2")

        if slots:
            for weapon in weapon_slots:
                yield getattr(self, weapon), weapon

        else:
            for weapon in weapon_slots:
                yield getattr(self, weapon)

    def iter_modules(self) -> t.Iterator[InvItemSlot[None]]:
        """Iterator over mech's modules"""
        for i in range(1, 9):
            yield getattr(self, f"mod{i}")

    def iter_specials(self) -> t.Iterator[InvItemSlot[None]]:
        """Iterator over mech's specials, in order: tele, charge, hook"""
        for special in ("tele", "charge", "hook"):
            yield getattr(self, special)

    def iter_items(self) -> t.Iterator[AnyInvItem | None]:
        """Iterator over all mech's items"""
        yield self.torso
        yield self.legs
        yield self.drone
        yield from self.iter_weapons()
        yield from self.iter_specials()
        yield from self.iter_modules()

    def wu_serialize(self, build_name: str, player_name: str) -> WUSerialized:
        if self.is_custom:
            raise TypeError("Cannot serialize a custom mech into WU format")

        def wu_compat_order():
            yield self.torso
            yield self.legs
            yield from self.iter_weapons()
            yield self.drone
            yield self.charge
            yield self.tele
            yield self.hook
            yield from self.iter_modules()

        slot_names = (
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

        serialized_items = [
            None if item is None else item.underlying.wu_serialize(slot)
            for slot, item in zip(slot_names, wu_compat_order())
        ]
        # lazy import
        import hashlib
        import json

        json_string = json.dumps(serialized_items, indent=None)
        hash = hashlib.sha256(json_string.encode()).hexdigest()

        return {
            "name": str(player_name),
            "itemsHash": hash,
            "mech": {
                "name": str(build_name),
                "setup": [item.underlying.id if item else 0 for item in wu_compat_order()],
            },
        }

    def figure_dominant_element(self) -> Element | None:
        """Guesses the mech type by equipped items."""
        excluded = {Type.CHARGE_ENGINE, Type.TELEPORTER, Type.MODULE}
        elements = Counter(
            item.element
            for item in self.iter_items()
            if item is not None
            if item.type not in excluded
        ).most_common(2)

        # return None when there are no elements
        # or the difference between the two most common is small
        if len(elements) == 0 or (len(elements) == 2 and elements[0][1] - elements[1][1] < 2):
            return None

        # otherwise just return the most common one
        return elements[0][0]
