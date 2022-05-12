from __future__ import annotations

import asyncio
import typing as t
from dataclasses import dataclass, field

from utils import format_count

from .core import DEFAULT_VARS, STAT_NAMES, WORKSHOP_STATS, ArenaBuffs, GameVars
from .images import MechRenderer
from .inv_item import AnyInvItem, InvItem
from .types import AnyStats, Attachment, Attachments

if t.TYPE_CHECKING:
    from aiohttp import ClientSession
    from PIL.Image import Image

# fmt: off
class _InvItems(t.TypedDict):
    torso:  InvItem[Attachments] | None
    legs:   InvItem[Attachment] | None
    drone:  InvItem[Attachment] | None
    side1:  InvItem[Attachment] | None
    side2:  InvItem[Attachment] | None
    side3:  InvItem[Attachment] | None
    side4:  InvItem[Attachment] | None
    top1:   InvItem[Attachment] | None
    top2:   InvItem[Attachment] | None
    tele:   InvItem[None] | None
    charge: InvItem[None] | None
    hook:   InvItem[None] | None
    mod1:   InvItem[None] | None
    mod2:   InvItem[None] | None
    mod3:   InvItem[None] | None
    mod4:   InvItem[None] | None
    mod5:   InvItem[None] | None
    mod6:   InvItem[None] | None
    mod7:   InvItem[None] | None
    mod8:   InvItem[None] | None
# fmt: on


@dataclass
class Mech:
    """Represents a mech build."""

    game_vars: GameVars = DEFAULT_VARS
    _items: _InvItems = field(
        default_factory=lambda: t.cast(_InvItems, dict.fromkeys(_InvItems.__annotations__, None)),
        init=False,
    )
    _stats: AnyStats = field(default_factory=AnyStats, init=False)
    _image: Image | None = field(default=None, init=False)

    # fmt: off
    if t.TYPE_CHECKING:
        torso:  InvItem[Attachments] | None
        legs:   InvItem[Attachment] | None
        drone:  InvItem[None] | None
        side1:  InvItem[Attachment] | None
        side2:  InvItem[Attachment] | None
        side3:  InvItem[Attachment] | None
        side4:  InvItem[Attachment] | None
        top1:   InvItem[Attachment] | None
        top2:   InvItem[Attachment] | None
        tele:   InvItem[None] | None
        charge: InvItem[None] | None
        hook:   InvItem[None] | None
        mod1:   InvItem[None] | None
        mod2:   InvItem[None] | None
        mod3:   InvItem[None] | None
        mod4:   InvItem[None] | None
        mod5:   InvItem[None] | None
        mod6:   InvItem[None] | None
        mod7:   InvItem[None] | None
        mod8:   InvItem[None] | None
    # fmt: on

    def __getattr__(self, name: t.Any, /):
        try:
            return self._items[name]

        except KeyError:
            raise AttributeError(
                f'{type(self).__name__} object has no attribute "{name}"'
            ) from None

    def __setitem__(self, place: str | tuple[str, int], item: AnyInvItem | None, /) -> None:
        if not isinstance(item, (InvItem, type(None))):
            raise TypeError(f"Expected Item object or None, got {type(item)}")

        pos = None

        if isinstance(place, tuple):
            place, pos = place

        del self.stats

        item_type = place.lower()

        if item_type in self._items:
            self.invalidate_image(item, self._items[item_type])
            self._items[item_type] = item
            return

        if pos is None:
            raise TypeError(f'"{item_type}" requires pos passed')

        item_types: dict[str, tuple[str, int]] = {
            "module": ("mod", 8),
            "side_weapon": ("side", 4),
            "top_weapon": ("top", 2),
        }

        if item_type not in item_types:
            raise TypeError("Invalid item type passed")

        slug, limit = item_types[item_type]

        if not 0 < pos <= limit:
            raise ValueError(f"Position outside range 1-{limit}")

        item_type = slug + str(pos)
        self.invalidate_image(item, self._items[item_type])
        self._items[item_type] = item

    def __getitem__(self, place: str) -> AnyInvItem:
        if not isinstance(place, str):
            raise TypeError("Only string indexing supported")

        try:
            return self._items[place]

        except KeyError:
            raise KeyError(f'"{place}" is not a valid item slot') from None

    def __str__(self) -> str:
        string_parts = [
            f"{item.type.capitalize()}: {item}"
            for item in (self.torso, self.legs, self.drone)
            if item is not None
        ]

        if weapon_string := ", ".join(format_count(self.iter_weapons())):
            string_parts.append("Weapons: " + weapon_string)

        string_parts.extend(
            f"{item.type.capitalize()}: {item}" for item in self.iter_specials() if item is not None
        )

        if modules := ", ".join(format_count(self.iter_modules())):
            string_parts.append("Modules: " + modules)

        return "\n".join(string_parts)

    def __format__(self, spec: str, /) -> str:
        a = "{self:a}"
        return str(self)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} vars={self.game_vars} "
            + ", ".join(f"{slot}={item!r}" for slot, item in self._items.items())
            + f" at 0x{id(self):016X}>"
        )

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
    def stats(self) -> AnyStats:
        if self._stats:
            return self._stats

        stats_cache = self._stats

        for item in self.iter_items():
            if item is None:
                continue

            for key in WORKSHOP_STATS:
                if key in item.underlying.stats:
                    if key not in stats_cache:
                        stats_cache[key] = 0

                    stats_cache[key] += item.underlying.stats[key]

        if (weight := stats_cache.setdefault("weight", 0)) > self.game_vars.MAX_WEIGHT:
            for stat, pen in self.game_vars.PENALTIES.items():
                stats_cache[stat] = (
                    stats_cache.get(stat, 0) - (weight - self.game_vars.MAX_WEIGHT) * pen
                )

        self._stats = stats_cache
        return stats_cache

    @stats.deleter
    def stats(self) -> None:
        t.cast(dict, self._stats).clear()

    @property
    def sorted_stats(self) -> list[tuple[str, int]]:
        return sorted(self.stats.items(), key=lambda stat: WORKSHOP_STATS.index(stat[0]))  # type: ignore


    def buffed_stats(self, buffs: ArenaBuffs, /) -> t.Iterator[tuple[str, int]]:
        for stat, value in self.sorted_stats:
            yield stat, buffs.total_buff(stat, value)

    def print_stats(self, buffs: ArenaBuffs | None = None, /) -> str:
        if buffs is None:
            bank = iter(self.sorted_stats)

        else:
            bank = self.buffed_stats(buffs)

        weight, value = next(bank)
        name, icon = STAT_NAMES[weight]
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
            "{0.emoji} **{1}** {0.name}".format(STAT_NAMES[stat], value)
            for stat, value in bank
        )

    @property
    def image(self) -> Image:
        """Returns `Image` object merging all item images.
        Requires the torso to be set, otherwise raises `RuntimeError`"""
        if self._image is not None:
            return self._image

        if self.torso is None:
            raise RuntimeError("Cannot create image without torso set")

        canvas = MechRenderer(self.torso.underlying)

        if self.legs is not None:
            canvas.add_image(self.legs.underlying, "leg1")
            canvas.add_image(self.legs.underlying, "leg2")

        for item, layer in self.iter_weapon_slots():
            if item is None:
                continue

            canvas.add_image(item.underlying, layer)

        if self.drone is not None:
            canvas.add_image(
                self.drone.underlying,
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

    def iter_weapon_slots(self) -> t.Iterator[tuple[InvItem[Attachment] | None, str]]:
        """Iterator over mech's side and top weapons"""
        items = self._items
        slots = ("side1", "side2", "side3", "side4", "top1", "top2")

        for slot in slots:
            yield items[slot], slot

    def iter_weapons(self) -> t.Iterator[InvItem[Attachment] | None]:
        """Iterator over mech's side and top weapons"""
        items = self._items
        yield items["side1"]
        yield items["side2"]
        yield items["side3"]
        yield items["side4"]
        yield items["top1"]
        yield items["top2"]

    def iter_modules(self) -> t.Iterator[InvItem[None] | None]:
        """Iterator over mech's modules"""
        items = self._items

        for n in range(1, 9):
            yield items[f"mod{n}"]

    def iter_specials(self) -> t.Iterator[InvItem[None] | None]:
        """Iterator over mech's specials, in order: tele, charge, hook"""
        items = self._items
        yield items["tele"]
        yield items["charge"]
        yield items["hook"]

    def iter_items(self) -> t.Iterator[AnyInvItem | None]:
        """Iterator over all mech's items"""
        yield from self._items.values()  # type: ignore
