from __future__ import annotations

import typing as t
from collections import Counter
from functools import partial
from types import MappingProxyType
from uuid import UUID

from attrs import Attribute, define, field
from typing_extensions import Self

from shared.utils import cached_slot_property

from ..typeshed import XOrTupleXY, dict_items_as
from .core import STATS, WORKSHOP_STATS, ArenaBuffs, GameVars
from .enums import Element, IconData, Type
from .images import Attachment, Attachments, ImageRenderer
from .inv_item import AnyInvItem, InvItem, SlotType
from .utils import format_count

if t.TYPE_CHECKING:
    from PIL.Image import Image

BODY_SLOTS = ("torso", "legs", "drone")
WEAPON_SLOTS = ("side1", "side2", "side3", "side4", "top1", "top2")
SPECIAL_SLOTS = ("tele", "charge", "hook")
MODULE_SLOTS = ("mod1", "mod2", "mod3", "mod4", "mod5", "mod6", "mod7", "mod8")
_SLOTS_SET = frozenset(BODY_SLOTS).union(WEAPON_SLOTS, SPECIAL_SLOTS, MODULE_SLOTS)


# -------------------------------- Converters ---------------------------------

_type_to_slot_lookup = {
    Type.SIDE_WEAPON: "side",
    Type.TOP_WEAPON: "top",
    Type.TELEPORTER: "tele",
    Type.CHARGE_ENGINE: "charge",
    Type.GRAPPLING_HOOK: "hook",
}


def _type_to_partial_slot(type: Type) -> str:
    return _type_to_slot_lookup.get(type) or type.name.lower()


def slot_to_type(slot: str) -> Type:
    """Convert slot literal to corresponding type enum."""
    if slot.startswith("side"):
        return Type.SIDE_WEAPON

    if slot.startswith("top"):
        return Type.TOP_WEAPON

    if slot.startswith("mod"):
        return Type.MODULE

    return Type[slot.upper()]


def slot_to_icon_data(slot: str) -> IconData:
    """Same as slot_to_type but returns alternate icon for items mounted on the right side."""
    if slot.startswith(("top", "side")) and int(slot[-1]) % 2 == 1:
        return slot_to_type(slot).alt

    return slot_to_type(slot)


def slot_name_converter(slot_: XOrTupleXY[str | Type, int], /):
    """Parse a slot to appropriate name. Raises TypeError if invalid."""
    match slot_:
        case (str() as slot, int() as pos):
            slot = slot.lower() + str(pos)

        case (Type() as slot, int() as pos):
            slot = _type_to_partial_slot(slot) + str(pos)

        case Type():
            slot = _type_to_partial_slot(slot_)

        case str() as slot:
            slot = slot.lower()

        case _:
            raise TypeError(f"{slot_!r} is not a valid slot")

    if slot not in _SLOTS_SET:
        raise TypeError(f"{slot_!r} is not a valid slot")

    return slot


def get_weight_utilization_emoji(mech: Mech, weight: int) -> str:
    vars = mech.game_vars
    # fmt: off
    weight_usage = (
        "⛔"
        if weight >  vars.MAX_OVERWEIGHT   else "❕"
        if weight >  vars.MAX_WEIGHT       else "👌"
        if weight == vars.MAX_WEIGHT       else "🆗"
        if weight >= vars.MAX_WEIGHT * .99 else "⚙️"
        if weight >= 0                     else "🗿"
    )
    # fmt: on

    return " " + weight_usage


# -------------------------------- Constraints --------------------------------


def jumping_required(mech: Mech) -> bool:
    # unequipping legs is allowed, so no legs tests positive
    return mech.legs is None or "jumping" in mech.legs.stats


def no_res_stacking(mech: Mech, module: AnyInvItem) -> bool:
    existing_resistances = module.stats.keys() & {"phyRes", "expRes", "eleRes"}

    for equipped_module in mech.iter_items(modules=True):
        if equipped_module is None or equipped_module is module:
            continue

        if equipped_module.has_any_of_stats(*existing_resistances):
            return False

    return True


# -------------------------------- Validators ---------------------------------


def is_valid_type(
    inst: t.Any,
    attr: Attribute[InvItem[t.Any] | None | t.Any],
    value: InvItem[t.Any] | None | t.Any,
) -> None:
    """Performs a check if item assigned to a slot has valid type."""
    if value is None:
        return

    if not isinstance(value, InvItem):
        raise TypeError(f"Invalid object set as item: {type(value)}")

    valid_type = slot_to_type(attr.name)

    if value.type is not valid_type:
        raise ValueError(f"Mech slot {attr.name} expects a type {valid_type}, got {value.type}")


@define(kw_only=True)
class Mech:
    """Represents a mech build."""

    name: str
    custom: bool = False
    game_vars: GameVars = field(factory=GameVars.default)
    constraints: dict[UUID, t.Callable[[Self], bool]] = field(factory=dict, init=False)
    _stats: dict[str, int] = field(init=False, repr=False, eq=False)
    _image: dict[str, int] = field(init=False, repr=False, eq=False)
    _dominant_element: dict[str, int] = field(init=False, repr=False, eq=False)

    # fmt: off
    torso:  SlotType[Attachments] = field(default=None, validator=is_valid_type)
    legs:   SlotType[Attachment]  = field(default=None, validator=is_valid_type)
    drone:  SlotType[None]        = field(default=None, validator=is_valid_type)
    side1:  SlotType[Attachment]  = field(default=None, validator=is_valid_type)
    side2:  SlotType[Attachment]  = field(default=None, validator=is_valid_type)
    side3:  SlotType[Attachment]  = field(default=None, validator=is_valid_type)
    side4:  SlotType[Attachment]  = field(default=None, validator=is_valid_type)
    top1:   SlotType[Attachment]  = field(default=None, validator=is_valid_type)
    top2:   SlotType[Attachment]  = field(default=None, validator=is_valid_type)
    tele:   SlotType[None] = field(default=None, validator=is_valid_type)
    charge: SlotType[None] = field(default=None, validator=is_valid_type)
    hook:   SlotType[None] = field(default=None, validator=is_valid_type)
    mod1:   SlotType[None] = field(default=None, validator=is_valid_type)
    mod2:   SlotType[None] = field(default=None, validator=is_valid_type)
    mod3:   SlotType[None] = field(default=None, validator=is_valid_type)
    mod4:   SlotType[None] = field(default=None, validator=is_valid_type)
    mod5:   SlotType[None] = field(default=None, validator=is_valid_type)
    mod6:   SlotType[None] = field(default=None, validator=is_valid_type)
    mod7:   SlotType[None] = field(default=None, validator=is_valid_type)
    mod8:   SlotType[None] = field(default=None, validator=is_valid_type)
    # fmt: on

    def __setitem__(self, slot: XOrTupleXY[str | Type, int], item: AnyInvItem | None, /) -> None:
        if not isinstance(item, (InvItem, type(None))):
            raise TypeError(f"Expected Item object or None, got {type(item)}")

        slot = slot_name_converter(slot)

        if item is not None:
            if slot_to_type(slot) is not item.type:
                raise TypeError(f"Item type {item.type} does not match slot {slot!r}")

            if item.tags.custom and not self.custom:
                raise TypeError("Cannot set a custom item on this mech")

            if (prev := self[slot]) is not None and prev.UUID in self.constraints:
                del self.constraints[prev.UUID]

            if item.type is Type.MODULE and item.has_any_of_stats("phyRes", "expRes", "eleRes"):
                self.constraints[item.UUID] = partial(no_res_stacking, module=item)

            elif item.tags.require_jump:
                self.constraints[item.UUID] = jumping_required

        del self.stats

        self.try_invalidate_cache(item, self[slot])
        setattr(self, slot, item)

    def __getitem__(self, slot: XOrTupleXY[str | Type, int]) -> AnyInvItem | None:
        return getattr(self, slot_name_converter(slot))

    def __str__(self) -> str:
        string_parts = [
            f"{item.type.name.capitalize()}: {item}"
            for item in self.iter_items(body=True)
            if item is not None
        ]

        if weapon_string := ", ".join(format_count(self.iter_items(weapons=True))):
            string_parts.append("Weapons: " + weapon_string)

        string_parts.extend(
            f"{item.type.name.capitalize()}: {item}"
            for item in self.iter_items(specials=True)
            if item is not None
        )

        if modules := ", ".join(format_count(self.iter_items(modules=True))):
            string_parts.append("Modules: " + modules)

        return "\n".join(string_parts)

    @property
    def weight(self) -> int:
        """The weight of the mech."""
        return self.stats.get("weight", 0)

    def validate(self) -> bool:
        """Check if the mech is battle ready."""
        return (
            # torso present
            self.torso is not None
            # legs present
            and self.legs is not None
            # at least one weapon
            and any(wep is not None for wep in self.iter_items(weapons=True))
            # not over max overload
            and self.weight <= self.game_vars.MAX_OVERWEIGHT
            # no constraints are broken
            and all(constr(self) for constr in self.constraints.values())
        )

    def check_integrity(self) -> None:
        """Go through items and validate that they are of correct type."""
        invalid_slots: list[str] = []

        for item, slot in self.iter_items(slots=True):
            if item is None:
                continue

            if slot_to_type(slot) is not item.type:
                invalid_slots.append(slot)

        if invalid_slots:
            raise TypeError(f"Slots: {', '.join(invalid_slots)} have invalid item type")

    @cached_slot_property
    def stats(self) -> MappingProxyType[str, int]:
        """A dict of the mech's stats, in order as they appear in workshop."""

        # inherit the order of dict keys from workshop stats
        stats: dict[str, int] = dict.fromkeys(WORKSHOP_STATS, 0)

        for item in filter(None, self.iter_items()):
            for stat in stats:
                if (value := item.stats.get(stat)) is not None:
                    stats[stat] += value

        if (overweight := stats["weight"] - self.game_vars.MAX_WEIGHT) > 0:
            for stat, penalty_mult in dict_items_as(int, self.game_vars.PENALTIES):
                stats[stat] -= overweight * penalty_mult

        for stat, value in tuple(stats.items())[2:]:  # keep weight and health
            if value == 0:
                del stats[stat]

        return MappingProxyType(stats)

    def print_stats(
        self,
        included_buffs: ArenaBuffs | None = None,
        /,
        *,
        line_format: str | None = None,
        extra: dict[str, t.Callable[[Mech, int], str]] | None = None,
    ) -> str:
        """Returns a string of lines formatted with mech stats.

        Parameters
        ----------
        included_buffs: `ArenaBuffs` object to apply the buffs from, or None if plain stats are resired.
        line_format: a string which will be used with `.format` to denote the format of each line.
        The keywords available are:
            - `stat` - a `Stat` object.
            - `value` - the integer value of the stat.
            - `extra` - any extra data coming from a callable from the `extra` param.
        """
        if line_format is None:
            line_format = "{stat.emoji} **{value}** {stat.name}{extra}"

        if extra is None:
            extra = {"weight": get_weight_utilization_emoji}

        if included_buffs is None:
            bank = self.stats

        else:
            bank = included_buffs.buff_stats(self.stats, buff_health=True)

        return "\n".join(
            line_format.format(
                value=value,
                stat=STATS[stat_name],
                extra=extra.get(stat_name, lambda mech, value: "")(self, value),
            )
            for stat_name, value in bank.items()
        )

    @cached_slot_property
    def image(self) -> Image:
        """Returns `Image` object merging all item images.
        Requires the torso to be set, otherwise raises `RuntimeError`"""
        canvas = ImageRenderer.from_mech(self)
        return canvas.merge()

    def try_invalidate_cache(self, new: AnyInvItem | None, old: AnyInvItem | None) -> None:
        """Deletes cached image if the new item changes mech appearance."""
        # Setting a displayable item will not change the image
        # only if the old item was the same item
        # For simplicity I don't exclude that case from updating the image
        if new is not None and new.type.displayable:
            del self.image

        # the item was set to None, thus the appearance will change
        # only if the previous one was displayable
        elif old is not None and old.type.displayable:
            del self.image

        if new is None or old is None or new.element is not old.element:
            del self.dominant_element

    @property
    def has_image_cached(self) -> bool:
        """Returns True if the image is in cache, False otherwise.
        Does not check if the cache has been changed."""
        return hasattr(self, type(self).image.slot)

    @t.overload
    def iter_items(self, *, slots: t.Literal[False] = False) -> t.Iterator[AnyInvItem | None]:
        ...

    @t.overload
    def iter_items(self, *, slots: t.Literal[True]) -> t.Iterator[tuple[AnyInvItem | None, str]]:
        ...

    @t.overload
    def iter_items(
        self,
        *,
        weapons: t.Literal[True],
        slots: t.Literal[False] = False,
    ) -> t.Iterator[InvItem[Attachment] | None]:
        ...

    @t.overload
    def iter_items(
        self,
        *,
        weapons: t.Literal[True],
        slots: t.Literal[True],
    ) -> t.Iterator[tuple[InvItem[Attachment] | None, str]]:
        ...

    @t.overload
    def iter_items(
        self,
        *,
        modules: bool = ...,
        specials: bool = ...,
        slots: t.Literal[False] = False,
    ) -> t.Iterator[InvItem[None] | None]:
        ...

    @t.overload
    def iter_items(
        self,
        *,
        modules: bool = ...,
        specials: bool = ...,
        slots: t.Literal[True],
    ) -> t.Iterator[tuple[InvItem[None] | None, str]]:
        ...

    @t.overload
    def iter_items(
        self,
        *,
        body: bool = ...,
        weapons: bool = ...,
        specials: bool = ...,
        modules: bool = ...,
        slots: t.Literal[False] = False,
    ) -> t.Iterator[AnyInvItem | None]:
        ...

    @t.overload
    def iter_items(
        self,
        *,
        body: bool = ...,
        weapons: bool = ...,
        specials: bool = ...,
        modules: bool = ...,
        slots: t.Literal[True],
    ) -> t.Iterator[tuple[AnyInvItem | None, str]]:
        ...

    def iter_items(
        self,
        *,
        body: bool = False,
        weapons: bool = False,
        specials: bool = False,
        modules: bool = False,
        slots: bool = False,
    ) -> t.Iterator[AnyInvItem | None | tuple[AnyInvItem | None, str]]:
        """Iterator over mech's selected items.

        Parameters
        ----------
        body, weapons, specials, modules: `bool`
            Selectors denoting which groups of parts to yield.
            If all set to `False`, acts as if all are set to `True`.
            - `body` yields torso, legs and drone;
            - `weapons` yields side & top weapons;
            - `specials` yields teleport, charge and hook;
            - `modules` yields modules.

        slots: `bool`
            If `True`, yields all selected items as tuple pairs of (`InvItem`, `str`). When False
            yields only the items.

        Yields
        ------
        `InvItem`
            If `slots` is set to `False`.
        `tuple[InvItem, str]`
            If `slots` is set to `True`.
        """

        if not (body or weapons or specials or modules):
            body = weapons = specials = modules = True

        from functools import partial
        from itertools import compress

        if slots:

            def factory(slot: str):
                return (getattr(self, slot), slot)

        else:
            factory = partial(getattr, self)

        for slot_set in compress(
            (BODY_SLOTS, WEAPON_SLOTS, SPECIAL_SLOTS, MODULE_SLOTS),
            (body, weapons, specials, modules),
        ):
            for slot in slot_set:
                yield factory(slot)

    @cached_slot_property
    def dominant_element(self) -> Element | None:
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
